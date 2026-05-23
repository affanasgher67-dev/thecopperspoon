from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, session, redirect
from flask.typing import ResponseReturnValue

import firebase_admin
from firebase_admin import credentials, firestore

from .agent import build_restaurant_agent
from .auth import admin_required, verify_admin
from .config import load_restaurant_profile
from .feedback import FeedbackError, FeedbackStore
from .menu import MenuCatalog, load_menu_catalog, update_menu_item_stock, add_menu_item, remove_menu_item
from .orders import OrderError, OrderStore
from .reservations import ReservationError, ReservationRequest, ReservationStore
from .webhooks import send_n8n_webhook

from dotenv import load_dotenv
load_dotenv()


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
KEY_PATH = REPO_ROOT / "firebase-key.json"


def create_app(
    *,
    data_dir: Path | str | None = None,
    chat_client=None,
) -> Flask:
    # Initialize Firebase
    if not firebase_admin._apps:
        if KEY_PATH.exists():
            cred = credentials.Certificate(str(KEY_PATH))
            firebase_admin.initialize_app(cred)
        else:
            # Fallback for local dev if key is missing, though we expect it now
            firebase_admin.initialize_app()
    
    db = firestore.client()

    profile = load_restaurant_profile()
    template_folder = PACKAGE_ROOT / "templates"
    static_folder = PACKAGE_ROOT / "static"

    app = Flask(__name__, template_folder=str(template_folder), static_folder=str(static_folder))
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "restaurant-agent-dev-key")
    app.config["JSON_SORT_KEYS"] = False
    local_data_dir = Path(data_dir) if data_dir else None
    
    @app.context_processor
    def inject_admin_status():
        return dict(is_admin=bool(session.get("is_admin")))

    def current_menu() -> MenuCatalog:
        if local_data_dir:
            return load_menu_catalog(local_data_dir)
        return load_menu_catalog(db)

    reservation_store = ReservationStore(db, max_seats_per_slot=profile.max_seats_per_slot)
    feedback_store = FeedbackStore(db)
    order_store = OrderStore(db)

    def context_provider() -> str:
        menu = current_menu()
        return "\n".join([
            menu.chat_context(),
            reservation_store.chat_context(),
            feedback_store.chat_context(),
            order_store.chat_context(),
        ])


    # ── Page routes ──────────────────────────────────────────────

    @app.get("/")
    def index() -> str:
        menu = current_menu()
        return render_template(
            "home.html",
            profile=profile,
            profile_payload=asdict(profile),
            menu=menu,
            menu_payload=menu.as_dict(),
        )

    @app.get("/menu")
    def page_menu() -> str:
        menu = current_menu()
        return render_template(
            "menu.html",
            profile=profile,
            profile_payload=asdict(profile),
            menu=menu,
            menu_payload=menu.as_dict(),
        )

    @app.get("/reservations")
    def page_reservations():
        if session.get("is_admin"):
            return redirect("/")
        menu = current_menu()
        return render_template(
            "reservations.html",
            profile=profile,
            profile_payload=asdict(profile),
            menu=menu,
            menu_payload=menu.as_dict(),
        )


    @app.get("/about")
    def page_about() -> str:
        menu = current_menu()
        return render_template(
            "about.html",
            profile=profile,
            profile_payload=asdict(profile),
            menu=menu,
            menu_payload=menu.as_dict(),
        )

    @app.get("/cart")
    def page_cart():
        if session.get("is_admin"):
            return redirect("/")
        menu = current_menu()
        return render_template(
            "cart.html",
            profile=profile,
            profile_payload=asdict(profile),
            menu=menu,
            menu_payload=menu.as_dict(),
        )

    @app.get("/feedback")
    def page_feedback():
        if session.get("is_admin"):
            return redirect("/")
        menu = current_menu()
        return render_template(
            "feedback.html",
            profile=profile,
            profile_payload=asdict(profile),
            menu=menu,
            menu_payload=menu.as_dict(),
        )

    @app.get("/admin")
    def page_admin_login():
        from flask import redirect, url_for
        if session.get("is_admin"):
            return redirect(url_for("page_admin_dashboard"))
        # Redirect to home page and trigger the login modal via a query parameter
        return redirect(url_for("index", admin="login"))

    @app.get("/admin/dashboard")
    def page_admin_dashboard() -> ResponseReturnValue:
        from flask import redirect, url_for
        if not session.get("is_admin"):
            return redirect(url_for("page_admin_login"))
        menu = current_menu()
        return render_template(
            "admin.html",
            profile=profile,
            profile_payload=asdict(profile),
            menu=menu,
            menu_payload=menu.as_dict(),
        )

    @app.get("/sw.js")
    def service_worker():
        """Serve the service worker from the root scope."""
        return send_from_directory(str(static_folder), "sw.js", mimetype="application/javascript")

    @app.get("/manifest.json")
    def manifest():
        """Serve the PWA manifest from the root scope."""
        return send_from_directory(str(static_folder), "manifest.json", mimetype="application/json")

    # ── Menu API ─────────────────────────────────────────────────

    @app.get("/api/menu")
    def api_menu():
        return jsonify(current_menu().as_dict())

    @app.get("/api/menu/search")
    def api_menu_search():
        menu = current_menu()
        query = request.args.get("q", "").strip()
        tag = request.args.get("tag", "").strip()
        min_price = request.args.get("min_price", type=float)
        max_price = request.args.get("max_price", type=float)

        if query:
            results = menu.search(query)
        elif tag:
            results = menu.filter_by_tag(tag)
        elif min_price is not None or max_price is not None:
            results = menu.price_range(
                min_price=min_price or 0,
                max_price=max_price or float("inf"),
            )
        else:
            results = []

        return jsonify({
            "results": results,
            "count": len(results),
            "tags": menu.all_tags(),
        })

    # ── Chat API ─────────────────────────────────────────────────

    @app.post("/api/chat")
    def api_chat():
        try:
            payload = request.get_json(silent=True) or {}
            user_message = str(payload.get("message", "")).strip()
            if not user_message:
                return jsonify({"error": "Message is required."}), 400

            messages = session.get("messages", [])
            
            # Context for temporal logic (tomorrow, next week, etc)
            from datetime import datetime
            now_str = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
            
            agent = build_restaurant_agent(
                profile=profile,
                client=chat_client,
                context_provider=context_provider,
                messages=messages,
                current_time=now_str
            )
            reply = agent.reply(user_message)
            session["messages"] = agent.snapshot()
            return jsonify({"reply": reply})
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = str(e)
            if "429" in err_msg:
                err_msg = "Groq API quota exceeded. Please wait a few minutes before trying again."
            return jsonify({"error": f"Backend Error: {err_msg}"}), 500

    @app.post("/api/chat/reset")
    def api_chat_reset():
        session.pop("messages", None)
        return jsonify({"message": "Conversation reset."})

    # ── Reservation API ──────────────────────────────────────────

    @app.post("/api/reservations")
    def api_reservations():
        payload = request.get_json(silent=True) or {}

        try:
            reservation_request = ReservationRequest.from_dict(payload)
            record = reservation_store.create(reservation_request)
        except ReservationError as exc:
            return jsonify({"error": str(exc)}), 400

        message = (
            f"Your reservation request was sent! We've noted {record.party_size} seat(s) for {record.guest_name} "
            f"on {record.reservation_date} at {record.reservation_time}. "
            f"Your confirmation code is {record.confirmation_code}. "
            "Please note: your reservation is currently PENDING approval by our staff."
        )

        # Trigger n8n webhook
        send_n8n_webhook(profile.n8n_webhook_url, "reservation.created", record.as_dict())

        if local_data_dir:
            reservations_path = local_data_dir / "reservations.json"
            existing: list[dict] = []
            if reservations_path.exists():
                try:
                    existing = json.loads(reservations_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    existing = []
            existing.append(record.as_dict())
            reservations_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        return jsonify({"message": message, "reservation": record.as_dict()}), 201

    @app.get("/api/reservations/<confirmation_code>")
    def api_reservations_get(confirmation_code: str):
        reservation = reservation_store.get(confirmation_code)
        if not reservation:
            return jsonify({"error": "Reservation not found."}), 404
        return jsonify({"reservation": reservation})

    @app.post("/api/reservations/<confirmation_code>/cancel")
    def api_reservations_cancel(confirmation_code: str):
        try:
            reservation = reservation_store.cancel(confirmation_code)
        except ReservationError as exc:
            return jsonify({"error": str(exc)}), 400

        if not reservation:
            return jsonify({"error": "Reservation not found."}), 404

        message = (
            f"Reservation {reservation['confirmation_code']} for {reservation['guest_name']} "
            f"on {reservation['reservation_date']} at {reservation['reservation_time']} "
            f"has been cancelled."
        )

        send_n8n_webhook(profile.n8n_webhook_url, "reservation.cancelled", reservation)

        return jsonify({"message": message, "reservation": reservation})

    @app.get("/api/reservations/availability")
    def api_reservations_availability():
        date = request.args.get("date", "").strip()
        time = request.args.get("time", "").strip()
        if not date or not time:
            return jsonify({"error": "Both date and time are required."}), 400
        return jsonify(reservation_store.slot_availability(date, time))

    # ── Feedback API ─────────────────────────────────────────────

    @app.post("/api/feedback")
    def api_feedback():
        payload = request.get_json(silent=True) or {}
        try:
            rating = int(payload.get("rating", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Rating must be an integer."}), 400

        try:
            entry = feedback_store.submit(
                guest_name=str(payload.get("guest_name", "")),
                rating=rating,
                comment=str(payload.get("comment", "")),
            )
        except FeedbackError as exc:
            return jsonify({"error": str(exc)}), 400

        response = jsonify({
            "message": "Thank you for your feedback!",
            "feedback": entry.as_dict(),
        })

        # Trigger n8n webhook (non-blocking in response if possible, but here it's simple)
        send_n8n_webhook(profile.n8n_webhook_url, "feedback.submitted", entry.as_dict())

        return response, 201

    @app.get("/api/feedback/recent")
    def api_feedback_recent():
        limit = request.args.get("limit", 5, type=int)
        return jsonify({
            "reviews": feedback_store.recent(min(limit, 100)),
            "average_rating": feedback_store.average_rating(),
            "total": feedback_store.count(),
        })

    # ── Order API ────────────────────────────────────────────────

    @app.post("/api/orders")
    def api_orders_create():
        payload = request.get_json(silent=True) or {}

        # Block out-of-stock items from being ordered
        menu = current_menu()
        order_items = payload.get("items", [])
        for item_data in order_items:
            item_name = str(item_data.get("name", "")).strip()
            if item_name:
                menu_item = menu.find_item(item_name)
                if menu_item and menu_item.out_of_stock:
                    return jsonify({"error": f"'{item_name}' is currently out of stock and cannot be ordered."}), 400

        try:
            record = order_store.create(payload)
        except OrderError as exc:
            return jsonify({"error": str(exc)}), 400

        message = (
            f"Order request received! Your order ID is {record.order_id}. "
            f"Total: ${record.total:.2f} ({record.order_type}). "
            "Your order is currently PENDING and will be processed once approved by our staff."
        )

        # Trigger n8n webhook
        send_n8n_webhook(profile.n8n_webhook_url, "order.created", record.as_dict())

        return jsonify({"message": message, "order": record.as_dict()}), 201

    @app.get("/api/orders/<order_id>")
    def api_orders_get(order_id: str):
        order = order_store.get(order_id)
        if not order:
            return jsonify({"error": "Order not found."}), 404
        return jsonify({"order": order})

    @app.post("/api/orders/<order_id>/cancel")
    def api_orders_cancel(order_id: str):
        try:
            order = order_store.update_status(order_id, "cancelled")
            if not order:
                return jsonify({"error": "Order not found."}), 404
        except OrderError as exc:
            return jsonify({"error": str(exc)}), 400

        message = f"Order {order['order_id']} has been cancelled."
        
        # Trigger n8n webhook
        send_n8n_webhook(profile.n8n_webhook_url, "order.cancelled", order)

        return jsonify({"message": message, "order": order})

    # ── Admin API ────────────────────────────────────────────────

    @app.post("/admin/login")
    def admin_login():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))

        if verify_admin(username, password):
            session["is_admin"] = True
            return jsonify({
                "message": "Authenticated.", 
                "is_admin": True,
                "redirect": "/admin/dashboard"
            })

        return jsonify({"error": "Invalid credentials."}), 401

    @app.post("/admin/logout")
    def admin_logout():
        session.pop("is_admin", None)
        return jsonify({"message": "Logged out."})

    @app.get("/admin/check")
    def admin_check():
        return jsonify({"is_admin": bool(session.get("is_admin"))})

    @app.get("/api/orders/recent")
    @admin_required
    def api_orders_recent():
        limit = request.args.get("limit", 10, type=int)
        return jsonify({"orders": order_store.recent(min(limit, 50))})

    @app.get("/api/reservations/recent")
    @admin_required
    def api_reservations_recent():
        reservations = reservation_store.load_all()
        # Sort descending by created_at
        reservations.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return jsonify({"reservations": reservations[:50]})

    @app.put("/api/menu/stock")
    @admin_required
    def api_update_menu_stock():
        payload = request.get_json(silent=True) or {}
        item_name = payload.get("item_name")
        out_of_stock = bool(payload.get("out_of_stock", False))
        if not item_name:
            return jsonify({"error": "item_name required"}), 400
        
        success = update_menu_item_stock(db, item_name, out_of_stock)
        if success:
            # Trigger n8n webhook
            send_n8n_webhook(profile.n8n_webhook_url, "menu.stock_updated", {
                "item_name": item_name,
                "out_of_stock": out_of_stock
            })
            return jsonify({"message": f"{item_name} stock status updated."})
        return jsonify({"error": "Item not found"}), 404

    @app.post("/api/menu/items")
    @admin_required
    def api_add_menu_item():
        # Support both JSON and multipart form data
        if request.content_type and "multipart" in request.content_type:
            item_name = str(request.form.get("item_name", "")).strip()
            section_name = str(request.form.get("section", "")).strip()
            description = str(request.form.get("description", "")).strip()
            detailed_description = str(request.form.get("detailed_description", "")).strip()
            tags_raw = str(request.form.get("tags", "")).strip()
            price_raw = request.form.get("price", 0)
            image_file = request.files.get("image")
        else:
            payload = request.get_json(silent=True) or {}
            item_name = str(payload.get("item_name", "")).strip()
            section_name = str(payload.get("section", "")).strip()
            description = str(payload.get("description", "")).strip()
            detailed_description = str(payload.get("detailed_description", "")).strip()
            tags_raw = str(payload.get("tags", "")).strip()
            price_raw = payload.get("price", 0)
            image_file = None

        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "Price must be a valid number."}), 400

        if not item_name:
            return jsonify({"error": "Item name is required."}), 400
        if not section_name:
            return jsonify({"error": "Section is required."}), 400
        if not description:
            return jsonify({"error": "Description is required."}), 400
        if price <= 0:
            return jsonify({"error": "Price must be greater than zero."}), 400

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        # Handle image upload
        image_url = None
        if image_file and image_file.filename:
            import re as _re
            # Create a safe filename from the item name
            safe_name = _re.sub(r"[^a-z0-9]+", "_", item_name.lower()).strip("_")
            ext = Path(image_file.filename).suffix.lower() or ".png"
            if ext not in (".png", ".jpg", ".jpeg", ".webp"):
                ext = ".png"
            filename = f"{safe_name}{ext}"
            uploads_dir = static_folder / "uploads"
            uploads_dir.mkdir(exist_ok=True)
            save_path = uploads_dir / filename
            image_file.save(str(save_path))
            image_url = f"/static/uploads/{filename}"

        item_data = {
            "name": item_name,
            "description": description,
            "detailed_description": detailed_description,
            "price": price,
            "tags": tags,
            "highlight": False,
            "out_of_stock": False,
            "image_url": image_url,
        }

        success = add_menu_item(db, section_name, item_data)
        if success:
            send_n8n_webhook(profile.n8n_webhook_url, "menu.item_added", item_data)
            return jsonify({"message": f"{item_name} added to {section_name}.", "item": item_data})
        return jsonify({"error": f"Item '{item_name}' already exists or section could not be found."}), 409

    @app.delete("/api/menu/items")
    @admin_required
    def api_remove_menu_item():
        payload = request.get_json(silent=True) or {}
        item_name = str(payload.get("item_name", "")).strip()
        if not item_name:
            return jsonify({"error": "Item name is required."}), 400

        success = remove_menu_item(db, item_name)
        if success:
            send_n8n_webhook(profile.n8n_webhook_url, "menu.item_removed", {"item_name": item_name})
            return jsonify({"message": f"{item_name} removed from menu."})
        return jsonify({"error": f"Item '{item_name}' not found."}), 404

    @app.put("/api/reservations/<code>/status")
    @admin_required
    def api_reservations_update_status(code: str):
        payload = request.get_json(silent=True) or {}
        status = str(payload.get("status", ""))
        try:
            res = reservation_store.update_status(code, status)
        except ReservationError as exc:
            return jsonify({"error": str(exc)}), 400

        if not res:
            return jsonify({"error": "Reservation not found."}), 404

        # Trigger n8n webhook
        send_n8n_webhook(profile.n8n_webhook_url, "reservation.status_updated", res)

        return jsonify({"message": f"Reservation {code} updated to '{status}'.", "reservation": res})


    _ADMIN_STATS_CACHE = {"data": None, "expiry": 0}
    _ADMIN_STATS_TTL = 600 # 10 minutes

    @app.get("/api/admin/stats")
    @admin_required
    def api_admin_stats():
        now = time.time()
        
        if _ADMIN_STATS_CACHE["data"] and now < _ADMIN_STATS_CACHE["expiry"]:
            return jsonify(_ADMIN_STATS_CACHE["data"])

        try:
            all_orders = order_store.recent(limit=200)
            all_res = reservation_store.load_all(limit=200)
            all_feedback = feedback_store.recent(limit=200)

            total_revenue = sum(o.get("total", 0) for o in all_orders if o.get("status") != "cancelled")
            
            # Daily revenue for last 7 days
            from collections import defaultdict
            daily_rev = defaultdict(float)
            for o in all_orders:
                if o.get("status") == "cancelled": continue
                # created_at is ISO format
                date_str = o.get("created_at", "")[:10]
                daily_rev[date_str] += o.get("total", 0)
            
            sorted_daily_rev = [{"date": k, "total": v} for k, v in sorted(daily_rev.items())][-7:]

            # Popular items
            item_counts = defaultdict(int)
            for o in all_orders:
                if o.get("status") == "cancelled": continue
                for item in o.get("items", []):
                    item_counts[item.get("name")] += item.get("quantity", 0)
            
            popular_items = [{"name": k, "count": v} for k, v in sorted(item_counts.items(), key=lambda x: x[1], reverse=True)][:5]

            res_status_dist = defaultdict(int)
            for r in all_res:
                res_status_dist[r.get("status", "pending")] += 1

            stats_data = {
                "total_revenue": total_revenue,
                "order_count": len(all_orders),
                "res_count": len(all_res),
                "fb_count": len(all_feedback),
                "daily_revenue": sorted_daily_rev,
                "popular_items": popular_items,
                "res_status_dist": dict(res_status_dist),
                "stale": False
            }
            
            # Update cache
            _ADMIN_STATS_CACHE["data"] = stats_data
            _ADMIN_STATS_CACHE["expiry"] = now + _ADMIN_STATS_TTL

            return jsonify(stats_data)
        except Exception as e:
            if ("ResourceExhausted" in str(e) or "429" in str(e)) and _ADMIN_STATS_CACHE["data"]:
                data = _ADMIN_STATS_CACHE["data"].copy()
                data["stale"] = True
                return jsonify(data)
            return jsonify({"error": "Resource Exhausted and no cache available.", "stale": True}), 429

    @app.put("/api/orders/<order_id>/status")
    @admin_required
    def api_orders_update_status(order_id: str):
        payload = request.get_json(silent=True) or {}
        status = str(payload.get("status", ""))
        try:
            order = order_store.update_status(order_id, status)
        except OrderError as exc:
            return jsonify({"error": str(exc)}), 400

        if not order:
            return jsonify({"error": "Order not found."}), 404

        # Trigger n8n webhook
        send_n8n_webhook(profile.n8n_webhook_url, "order.status_updated", order)

        return jsonify({"message": f"Order {order_id} updated to '{status}'.", "order": order})

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the restaurant web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--data-dir", help="Override the data directory.")
    args = parser.parse_args(argv)

    app = create_app(data_dir=args.data_dir)
    print(f"Restaurant Agent web app running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

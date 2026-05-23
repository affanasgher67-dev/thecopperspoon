import os
import logging
from langchain_core.tools import tool
from .reservations import ReservationStore, ReservationRequest, ReservationError
from .orders import OrderStore, OrderError
from .menu import load_menu_catalog
from .webhooks import send_n8n_webhook

_DB_CLIENT = None

def _get_db():
    global _DB_CLIENT
    if _DB_CLIENT is not None:
        return _DB_CLIENT
        
    import firebase_admin
    from firebase_admin import firestore, credentials
    
    if not firebase_admin._apps:
        # Check for key file to avoid generic init errors
        key_path = os.path.join(os.getcwd(), "firebase-key.json")
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
            
    _DB_CLIENT = firestore.client()
    return _DB_CLIENT

@tool
def book_reservation(guest_name: str, phone: str, email: str, reservation_date: str, reservation_time: str, party_size: int, notes: str = "") -> str:
    """CRITICAL: NEVER call this tool until the user has provided ALL required information. 
    If you are missing their name, phone, email, date, time, or party size, you MUST ask them for it first in chat. 
    Only call this when you have valid data for every single parameter."""
    try:
        db = _get_db()
        store = ReservationStore(db)
        req = ReservationRequest.from_dict({
            "guest_name": guest_name,
            "phone": phone,
            "email": email,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "party_size": party_size,
            "notes": notes
        })
        record = store.create(req)
        send_n8n_webhook(os.getenv("N8N_WEBHOOK_URL", ""), "reservation.created", record.as_dict())
        return f"SUCCESS: Reservation created. Confirmation code: {record.confirmation_code}"
    except Exception as e:
        return f"ERROR: {str(e)}"

@tool
def place_order(guest_name: str, phone: str, email: str, order_type: str, items: list, notes: str = "") -> str:
    """CRITICAL: NEVER call this tool until the user has provided ALL required information.
    If you are missing their name, phone, email, order items, or order type (delivery/pickup), you MUST ask them for it first.
    Only call this when the guest explicitly confirms their final order."""
    try:
        db = _get_db()
        menu = load_menu_catalog(db)
        for item_data in items:
            item_name = str(item_data.get("name", "")).strip()
            if item_name:
                menu_item = menu.find_item(item_name)
                if menu_item and menu_item.out_of_stock:
                    return f"ERROR: '{item_name}' is currently out of stock. Please suggest an alternative."

        store = OrderStore(db)
        record = store.create({
            "guest_name": guest_name,
            "phone": phone,
            "email": email,
            "items": items,
            "order_type": order_type,
            "notes": notes
        })
        send_n8n_webhook(os.getenv("N8N_WEBHOOK_URL", ""), "order.created", record.as_dict())
        return f"SUCCESS: Order placed. Order ID: {record.order_id}, Total: {record.total}"
    except Exception as e:
        return f"ERROR: {str(e)}"

@tool
def cancel_reservation(confirmation_code: str) -> str:
    """Cancel a restaurant reservation using the confirmation code."""
    try:
        db = _get_db()
        store = ReservationStore(db)
        confirmation_code = str(confirmation_code).strip().upper()
        reservation = store.cancel(confirmation_code)
        if not reservation:
            return f"ERROR: Reservation with code {confirmation_code} not found."
        
        send_n8n_webhook(os.getenv("N8N_WEBHOOK_URL", ""), "reservation.cancelled", reservation)
        return f"SUCCESS: Reservation {confirmation_code} cancelled successfully."
    except Exception as e:
        return f"ERROR: {str(e)}"

@tool
def cancel_order(order_id: str) -> str:
    """Cancel a food order using the order ID."""
    try:
        db = _get_db()
        store = OrderStore(db)
        order_id = str(order_id).strip().upper()
        order = store.update_status(order_id, "cancelled")
        if not order:
            return f"ERROR: Order with ID {order_id} not found."
        
        send_n8n_webhook(os.getenv("N8N_WEBHOOK_URL", ""), "order.cancelled", order)
        return f"SUCCESS: Order {order_id} cancelled successfully."
    except Exception as e:
        return f"ERROR: {str(e)}"

@tool
def fetch_menu(category: str = "") -> str:
    """Fetch live menu items from our database. Provide an optional category/tag filter."""
    try:
        db = _get_db()
        menu = load_menu_catalog(db)
        
        if category:
            # Try to filter by tag first
            items = menu.filter_by_tag(category)
            # If no items by tag, try to find a section with that name
            if not items:
                category_lower = category.lower().strip()
                for section in menu.sections:
                    if category_lower in section.name.lower():
                        items = [item.as_dict() for item in section.items]
                        break
        else:
            # Return all items (as dicts)
            items = []
            for section in menu.sections:
                for item in section.items:
                    items.append(item.as_dict())
        
        if not items:
            return f"SUCCESS: No menu items found{' for category/tag: ' + category if category else ''}."
        
        # Summarize to keep token count low
        summarized = [{"name": i["name"], "price": i.get("price"), "description": i.get("description")} for i in items[:15]]
        return f"SUCCESS: Found {len(items)} items. Here are some options: {summarized}"
    except Exception as e:
        return f"ERROR: Could not fetch menu: {e}"

# Global list of tools for the LangChain agent
restaurant_tools = [book_reservation, place_order, cancel_reservation, cancel_order, fetch_menu]

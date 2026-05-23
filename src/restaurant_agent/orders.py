from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4
import time
from .utils import normalize_phone, is_valid_phone

try:
    from google.cloud import firestore
except ImportError:
    firestore = None


class OrderError(ValueError):
    """Raised when order validation fails."""


@dataclass(frozen=True)
class OrderItem:
    name: str
    quantity: int
    unit_price: float

    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal(),
        }


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    guest_name: str
    phone: str
    email: str
    items: tuple[OrderItem, ...]
    total: float
    order_type: str
    status: str
    notes: str
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "guest_name": self.guest_name,
            "phone": self.phone,
            "email": self.email,
            "items": [item.as_dict() for item in self.items],
            "total": self.total,
            "order_type": self.order_type,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at,
        }


VALID_ORDER_TYPES = ("dine-in", "takeout", "delivery")
VALID_STATUSES = ("awaiting_approval", "received", "preparing", "ready", "completed", "cancelled")


class OrderStore:
    """Order persistence backed by Cloud Firestore."""

    def __init__(self, db: Any) -> None:
        """
        Initialize the OrderStore with a Firestore client.
        :param db: An initialized firestore.Client instance.
        """
        self.db = db
        self.collection_name = "orders"
        self._recent_cache: tuple[list[dict[str, Any]], float] | None = None
        self._CACHE_TTL = 30 # 30 seconds

    def create(
        self,
        payload: dict[str, Any],
    ) -> OrderRecord:
        guest_name = str(payload.get("guest_name", "")).strip()
        phone = str(payload.get("phone", "")).strip()
        email = str(payload.get("email", "")).strip()
        order_type = str(payload.get("order_type", "takeout")).strip().lower()
        notes = str(payload.get("notes", "")).strip()
        items = payload.get("items", [])

        errors: list[str] = []
        if not guest_name:
            errors.append("Guest name is required.")
        if not phone:
            errors.append("Phone number is required.")
        if not email:
            errors.append("Email is required.")
        if not items:
            errors.append("At least one item is required.")
        if order_type not in VALID_ORDER_TYPES:
            errors.append(f"Order type must be one of: {', '.join(VALID_ORDER_TYPES)}.")
        if errors:
            raise OrderError(" ".join(errors))

        normalized_phone = normalize_phone(phone)
        if not is_valid_phone(normalized_phone):
            raise OrderError("Please provide a valid phone number (at least 9 digits).")

        order_items: list[OrderItem] = []
        for item_data in items:
            name = str(item_data.get("name", "")).strip()
            if not name:
                raise OrderError("Each item must have a name.")
            try:
                quantity = max(1, int(item_data.get("quantity", 1)))
                unit_price = float(item_data.get("unit_price", 0))
            except (TypeError, ValueError) as exc:
                raise OrderError(f"Invalid item data for '{name}'.") from exc

            order_items.append(
                OrderItem(name=name, quantity=quantity, unit_price=unit_price)
            )

        total = round(sum(item.subtotal() for item in order_items), 2)

        record = OrderRecord(
            order_id=uuid4().hex[:8].upper(),
            guest_name=guest_name,
            phone=normalized_phone,
            email=email,
            items=tuple(order_items),
            total=total,
            order_type=order_type,
            status="awaiting_approval",
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

        # Write to Firestore
        self.db.collection(self.collection_name).document(record.order_id).set(record.as_dict())

        # Invalidate cache
        self._recent_cache = None

        return record

    def get(self, order_id: str) -> dict[str, Any] | None:
        """Fetch an order by ID from Firestore."""
        doc = self.db.collection(self.collection_name).document(order_id.upper()).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["order_id"] = doc.id
        return data

    def update_status(self, order_id: str, status: str) -> dict[str, Any] | None:
        """Update an order's status in Firestore."""
        status = status.strip().lower()
        if status not in VALID_STATUSES:
            raise OrderError(f"Status must be one of: {', '.join(VALID_STATUSES)}.")

        doc_ref = self.db.collection(self.collection_name).document(order_id.upper())
        doc = doc_ref.get()
        if not doc.exists:
            return None
        
        doc_ref.update({"status": status})
        data = doc_ref.get().to_dict() # Get fresh state
        if data:
            data["order_id"] = doc_ref.id
        self._recent_cache = None
        return data

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch n most recent orders using Firestore without order_by to avoid index requirements."""
        now = time.time()

        try:
            if self._recent_cache and now < self._recent_cache[1]:
                return self._recent_cache[0][:limit]

            results = []
            for doc in self.db.collection(self.collection_name).stream():
                data = doc.to_dict()
                if data:
                    data["order_id"] = doc.id
                    results.append(data)

            # Sort by created_at in Python
            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)

            self._recent_cache = (results, now + self._CACHE_TTL)
            return results[:limit]

        except Exception as e:
            if ("ResourceExhausted" in str(e) or "429" in str(e)) and self._recent_cache:
                return self._recent_cache[0][:limit]
            return []

    def chat_context(self) -> str:
        # Just provide general instructions
        return (
            "Order handling: All orders are persistence in Cloud Firestore. "
            "Guests can place new orders through the order form on the page. "
            "Staff can update order status from the admin panel."
        )


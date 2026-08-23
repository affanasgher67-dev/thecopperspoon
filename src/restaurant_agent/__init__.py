"""Restaurant Agent package."""

from .auth import admin_required, verify_admin
from .config import RestaurantProfile, load_restaurant_profile
from .feedback import FeedbackEntry, FeedbackError, FeedbackStore
from .menu import MenuCatalog, load_menu_catalog
from .orders import OrderError, OrderItem, OrderRecord, OrderStore
from .reservations import ReservationError, ReservationRecord, ReservationRequest, ReservationStore


def __getattr__(name):
    """Lazy import for heavy agent module to avoid loading langchain at import time."""
    if name in ("RestaurantAgent", "build_restaurant_agent"):
        from .agent import RestaurantAgent, build_restaurant_agent
        return {"RestaurantAgent": RestaurantAgent, "build_restaurant_agent": build_restaurant_agent}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "RestaurantAgent",
    "FeedbackEntry",
    "FeedbackError",
    "FeedbackStore",
    "MenuCatalog",
    "OrderError",
    "OrderItem",
    "OrderRecord",
    "OrderStore",
    "RestaurantProfile",
    "ReservationError",
    "ReservationRecord",
    "ReservationRequest",
    "ReservationStore",
    "admin_required",
    "build_restaurant_agent",
    "load_menu_catalog",
    "load_restaurant_profile",
    "verify_admin",
]

"""Restaurant Agent package."""

from .agent import RestaurantAgent, build_restaurant_agent
from .auth import admin_required, verify_admin
from .config import RestaurantProfile, load_restaurant_profile
from .feedback import FeedbackEntry, FeedbackError, FeedbackStore
from .menu import MenuCatalog, load_menu_catalog
from .orders import OrderError, OrderItem, OrderRecord, OrderStore
from .reservations import ReservationError, ReservationRecord, ReservationRequest, ReservationStore

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

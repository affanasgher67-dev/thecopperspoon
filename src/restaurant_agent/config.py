from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RestaurantProfile:
    name: str
    cuisine: str
    vibe: str
    highlights: str
    hours: str
    phone: str
    reservation_note: str
    max_seats_per_slot: int
    n8n_webhook_url: str | None = None


def load_restaurant_profile(
    *,
    name: str | None = None,
    cuisine: str | None = None,
    vibe: str | None = None,
    highlights: str | None = None,
    hours: str | None = None,
    phone: str | None = None,
    reservation_note: str | None = None,
    max_seats_per_slot: int | None = None,
    n8n_webhook_url: str | None = None,
) -> RestaurantProfile:
    return RestaurantProfile(
        name=name or os.getenv("RESTAURANT_NAME", "The Copper Spoon"),
        cuisine=cuisine or os.getenv("RESTAURANT_CUISINE", "seasonal comfort food"),
        vibe=vibe or os.getenv(
            "RESTAURANT_VIBE",
            "warm neighborhood dining with fast, thoughtful service",
        ),
        highlights=highlights
        or os.getenv(
            "RESTAURANT_HIGHLIGHTS",
            "house-made pasta, grilled specials, and a seasonal dessert board",
        ),
        hours=hours or os.getenv("RESTAURANT_HOURS", "daily from 11:00 AM to 10:00 PM"),
        phone=phone or os.getenv("RESTAURANT_PHONE", "(555) 014-2040"),
        reservation_note=reservation_note
        or os.getenv(
            "RESTAURANT_RESERVATION_NOTE",
            "reservations are welcome for parties of up to 8",
        ),
        max_seats_per_slot=max_seats_per_slot or int(os.getenv("RESTAURANT_MAX_SEATS", "40")),
        n8n_webhook_url=n8n_webhook_url or os.getenv("N8N_WEBHOOK_URL"),
    )

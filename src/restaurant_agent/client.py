from __future__ import annotations

import os
from dataclasses import dataclass

from .config import RestaurantProfile, load_restaurant_profile


@dataclass
class OpenAIChatClient:
    api_key: str
    model: str = "gpt-4o-mini"

    def complete(self, messages):
        # Lightweight fallback implementation for local/test usage.
        # The production web stack uses the LangGraph/Groq agent path.
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = str(msg.get("content", ""))
                break
        if "recommend" in last_user.lower():
            return "I'd recommend one of our house favorites tonight."
        return "Absolutely. How can I help with your visit?"


@dataclass
class DemoChatClient:
    profile: RestaurantProfile

    def complete(self, messages):
        menu_highlights = ""
        for msg in messages:
            content = str(msg.get("content", ""))
            if "Menu highlights:" in content:
                menu_highlights = content.split("Menu highlights:", 1)[1].strip()
                break

        if menu_highlights:
            first_item = menu_highlights.split(";")[0].strip()
            if first_item:
                return f"I'd start with {first_item}. Tell me what kind of mood you're in and I'll tailor it."

        return (
            f"I'd start with {self.profile.highlights}. "
            "Tell me what kind of mood you're in and I'll tailor it."
        )


def build_chat_client(*, force_demo: bool = False, profile: RestaurantProfile | None = None):
    active_profile = profile or load_restaurant_profile()
    if force_demo:
        return DemoChatClient(profile=active_profile)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        return OpenAIChatClient(api_key=api_key)

    return DemoChatClient(profile=active_profile)

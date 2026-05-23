from __future__ import annotations

import argparse

from .agent import build_restaurant_agent
from .client import DemoChatClient, build_chat_client
from .config import load_restaurant_profile


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the restaurant assistant.")
    parser.add_argument("--demo", action="store_true", help="Force offline demo mode.")
    parser.add_argument("--restaurant-name", help="Override the restaurant name.")
    parser.add_argument("--cuisine", help="Override the cuisine description.")
    parser.add_argument("--vibe", help="Override the service vibe.")
    parser.add_argument("--highlights", help="Override the menu highlights.")
    parser.add_argument("--hours", help="Override the opening hours.")
    parser.add_argument("--phone", help="Override the contact phone number.")
    parser.add_argument("--reservation-note", help="Override the reservation note.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    profile = load_restaurant_profile(
        name=args.restaurant_name,
        cuisine=args.cuisine,
        vibe=args.vibe,
        highlights=args.highlights,
        hours=args.hours,
        phone=args.phone,
        reservation_note=args.reservation_note,
    )
    client = build_chat_client(force_demo=args.demo)
    agent = build_restaurant_agent(profile=profile, client=client)

    mode = "demo mode" if isinstance(client, DemoChatClient) else "OpenAI mode"
    print(f"Restaurant Agent is ready in {mode}.")
    print("Type /reset to clear the conversation or /quit to exit.")

    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in {"/quit", "quit", "exit"}:
            break
        if lowered == "/reset":
            agent.reset()
            print("Host: Conversation cleared. What would you like to do next?")
            continue

        reply = agent.reply(user_input)
        print(f"Host: {reply}")

    return 0

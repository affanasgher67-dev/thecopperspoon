from __future__ import annotations

import os
import unittest
from unittest import mock

from tests._support import ensure_src_path

ensure_src_path()

from restaurant_agent.client import DemoChatClient, OpenAIChatClient, build_chat_client
from restaurant_agent.config import load_restaurant_profile


class ClientTests(unittest.TestCase):
    def test_build_chat_client_falls_back_to_demo_without_api_key(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            client = build_chat_client()

        self.assertIsInstance(client, DemoChatClient)

    def test_demo_client_answers_in_a_warm_voice(self) -> None:
        profile = load_restaurant_profile(
            name="Bistro Nova",
            highlights="roasted chicken, lemon pasta, and a warm bread basket",
        )
        client = DemoChatClient(profile=profile)

        response = client.complete(
            [
                {"role": "system", "content": "You are a restaurant host."},
                {"role": "user", "content": "What should I order?"},
            ]
        )

        self.assertIn("roasted chicken", response.lower())
        self.assertIn("tell me what kind of mood you're in", response.lower())

    def test_demo_client_reads_menu_context(self) -> None:
        profile = load_restaurant_profile(name="Bistro Nova")
        client = DemoChatClient(profile=profile)

        response = client.complete(
            [
                {"role": "system", "content": "You are a restaurant host."},
                {
                    "role": "system",
                    "content": "Live menu data from data/menu.json.\nMenu highlights: Burrata Toast; Braised Short Rib.\nUse these names when making recommendations.",
                },
                {"role": "user", "content": "What should I order?"},
            ]
        )

        self.assertIn("burrata toast", response.lower())

    def test_openai_client_can_be_constructed(self) -> None:
        client = OpenAIChatClient(api_key="test-key")
        self.assertEqual(client.model, "gpt-4o-mini")


if __name__ == "__main__":
    unittest.main()

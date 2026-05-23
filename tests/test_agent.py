from __future__ import annotations

import unittest

from tests._support import StubClient

from restaurant_agent.agent import build_restaurant_agent
from restaurant_agent.config import load_restaurant_profile


class RestaurantAgentTests(unittest.TestCase):
    def test_reply_uses_client_and_tracks_messages(self) -> None:
        stub = StubClient("Absolutely, I can help with that.")
        profile = load_restaurant_profile(name="Bistro Nova")
        agent = build_restaurant_agent(profile=profile, client=stub)

        response = agent.reply("What do you recommend?")

        self.assertEqual(response, "Absolutely, I can help with that.")
        self.assertEqual(stub.calls[0][0]["role"], "system")
        self.assertIn("Bistro Nova", stub.calls[0][0]["content"])
        self.assertEqual(stub.calls[0][-1]["role"], "user")
        self.assertEqual(stub.calls[0][-1]["content"], "What do you recommend?")
        self.assertEqual(agent.messages[-1]["role"], "assistant")

    def test_reset_restores_system_prompt_only(self) -> None:
        stub = StubClient("Sure thing.")
        agent = build_restaurant_agent(client=stub)

        agent.reply("Hello")
        agent.reset()

        self.assertEqual(len(agent.messages), 1)
        self.assertEqual(agent.messages[0]["role"], "system")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from tests._support import ensure_src_path

ensure_src_path()

from restaurant_agent.config import load_restaurant_profile
from restaurant_agent.persona import build_system_prompt


class PersonaPromptTests(unittest.TestCase):
    def test_prompt_frames_agent_as_warm_host(self) -> None:
        profile = load_restaurant_profile(
            name="The Copper Spoon",
            cuisine="wood-fired dishes",
        )

        prompt = build_system_prompt(profile)

        self.assertIn("warm, attentive person", prompt)
        self.assertIn("The Copper Spoon", prompt)
        self.assertIn("wood-fired dishes", prompt)
        self.assertIn("Reply like a real host, not a bot.", prompt)
        self.assertIn("Do not use emojis.", prompt)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import unittest

from tests._support import StubClient, ensure_src_path

ensure_src_path()

from restaurant_agent.web import create_app


class WebAppTests(unittest.TestCase):
    def test_chat_endpoint_uses_live_menu_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            menu_path = Path(temp_dir) / "menu.json"
            menu_path.write_text(
                json.dumps(
                    {
                        "restaurant": "Bistro Nova",
                        "currency": "$",
                        "sections": [
                            {
                                "name": "Starters",
                                "items": [
                                    {
                                        "name": "Burrata Toast",
                                        "description": "Tomato jam",
                                        "price": 13,
                                        "highlight": True,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            stub = StubClient("Burrata Toast would be a nice pick.")
            app = create_app(data_dir=temp_dir, chat_client=stub)
            app.config.update(TESTING=True)

            with app.test_client() as client:
                response = client.post("/api/chat", json={"message": "What should I order?"})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["reply"], "Burrata Toast would be a nice pick.")
            self.assertGreaterEqual(len(stub.calls), 1)
            self.assertIn("Menu highlights:", stub.calls[0][1]["content"])

    def test_chat_reset_clears_session_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stub = StubClient("Sure thing.")
            app = create_app(data_dir=temp_dir, chat_client=stub)
            app.config.update(TESTING=True)

            with app.test_client() as client:
                first_response = client.post("/api/chat", json={"message": "Hello"})
                self.assertEqual(first_response.status_code, 200)

                with client.session_transaction() as flask_session:
                    self.assertIn("messages", flask_session)

                reset_response = client.post("/api/chat/reset")
                self.assertEqual(reset_response.status_code, 200)
                self.assertEqual(reset_response.get_json()["message"], "Conversation reset.")

                with client.session_transaction() as flask_session:
                    self.assertNotIn("messages", flask_session)

                second_response = client.post("/api/chat", json={"message": "What should I order?"})

            self.assertEqual(second_response.status_code, 200)
            self.assertEqual(len(stub.calls), 2)
            self.assertEqual(stub.calls[1][-1]["content"], "What should I order?")
            self.assertEqual(stub.calls[1][0]["role"], "system")

    def test_reservations_endpoint_persists_booking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_app(data_dir=temp_dir)
            app.config.update(TESTING=True)
            future = datetime.now() + timedelta(days=1)

            with app.test_client() as client:
                response = client.post(
                    "/api/reservations",
                    json={
                        "guest_name": "Jordan Lee",
                        "phone": "555-014-2040",
                        "reservation_date": future.date().isoformat(),
                        "reservation_time": "19:30",
                        "party_size": 4,
                        "notes": "Birthday dinner",
                    },
                )

            self.assertEqual(response.status_code, 201)
            payload = response.get_json()
            self.assertIn("confirmation code", payload["message"].lower())
            self.assertTrue((Path(temp_dir) / "reservations.json").exists())


if __name__ == "__main__":
    unittest.main()

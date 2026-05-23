from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from tests._support import ensure_src_path

ensure_src_path()

from restaurant_agent.menu import load_menu_catalog


class MenuCatalogTests(unittest.TestCase):
    def test_load_menu_catalog_reads_live_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            menu_path = Path(temp_dir) / "menu.json"
            menu_path.write_text(
                json.dumps(
                    {
                        "restaurant": "Bistro Nova",
                        "currency": "$",
                        "sections": [
                            {
                                "name": "Mains",
                                "items": [
                                    {
                                        "name": "Herb Chicken",
                                        "description": "Roasted with potatoes",
                                        "price": 24,
                                        "highlight": True,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            catalog = load_menu_catalog(menu_path)

        self.assertEqual(catalog.restaurant_name, "Bistro Nova")
        self.assertIn("Herb Chicken", catalog.chat_context())
        self.assertEqual(catalog.highlight_items(), ["Herb Chicken"])


if __name__ == "__main__":
    unittest.main()

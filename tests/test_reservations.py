from __future__ import annotations

from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import unittest

from tests._support import ensure_src_path

ensure_src_path()

from restaurant_agent.reservations import ReservationError, ReservationRequest, ReservationStore


class ReservationStoreTests(unittest.TestCase):
    def test_create_persists_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ReservationStore(Path(temp_dir) / "reservations.json")
            future = datetime.now() + timedelta(days=1)
            request = ReservationRequest(
                guest_name="Jordan Lee",
                phone="555-014-2040",
                reservation_date=future.date().isoformat(),
                reservation_time="19:00",
                party_size=4,
                notes="Window seat if possible",
            )

            record = store.create(request)

            self.assertEqual(record.guest_name, "Jordan Lee")
            self.assertEqual(len(store.load_all()), 1)
            self.assertTrue((Path(temp_dir) / "reservations.json").exists())

    def test_validate_rejects_past_times(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ReservationStore(Path(temp_dir) / "reservations.json")
            past = datetime.now() - timedelta(days=1)
            request = ReservationRequest(
                guest_name="Jordan Lee",
                phone="555-014-2040",
                reservation_date=past.date().isoformat(),
                reservation_time="19:00",
                party_size=4,
            )

            with self.assertRaises(ReservationError):
                store.create(request)


if __name__ == "__main__":
    unittest.main()

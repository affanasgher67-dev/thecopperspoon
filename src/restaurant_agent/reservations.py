from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4
import json
import time
from .utils import normalize_phone, is_valid_phone

try:
    from google.cloud import firestore
except ImportError:
    firestore = None


class ReservationError(ValueError):
    pass


@dataclass(frozen=True)
class ReservationRequest:
    guest_name: str
    phone: str
    reservation_date: str
    reservation_time: str
    party_size: int
    email: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReservationRequest":
        try:
            party_size = int(payload.get("party_size", 0))
        except (TypeError, ValueError) as exc:
            raise ReservationError("Party size must be a whole number.") from exc

        phone = str(payload.get("phone", "")).strip()
        normalized_phone = normalize_phone(phone)
        if not is_valid_phone(normalized_phone):
            raise ReservationError("Please provide a valid phone number (at least 9 digits).")

        return cls(
            guest_name=str(payload.get("guest_name", "")).strip(),
            phone=normalized_phone,
            reservation_date=str(payload.get("reservation_date", "")).strip(),
            reservation_time=str(payload.get("reservation_time", "")).strip(),
            party_size=party_size,
            email=str(payload.get("email", "")).strip(),
            notes=str(payload.get("notes", "")).strip(),
        )

    def scheduled_at(self) -> datetime:
        try:
            return datetime.fromisoformat(f"{self.reservation_date}T{self.reservation_time}")
        except ValueError as exc:
            raise ReservationError("Reservation date and time must be valid ISO values.") from exc


@dataclass(frozen=True)
class ReservationRecord:
    confirmation_code: str
    guest_name: str
    phone: str
    reservation_date: str
    reservation_time: str
    party_size: int
    notes: str
    status: str
    email: str
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "confirmation_code": self.confirmation_code,
            "guest_name": self.guest_name,
            "phone": self.phone,
            "reservation_date": self.reservation_date,
            "reservation_time": self.reservation_time,
            "party_size": self.party_size,
            "notes": self.notes,
            "status": self.status,
            "email": self.email,
            "created_at": self.created_at,
        }


# Default capacity: max total seats per 1-hour window
DEFAULT_MAX_SEATS_PER_SLOT = 40
VALID_STATUSES = ("pending_review", "confirmed", "cancelled")


class ReservationStore:
    def __init__(
        self,
        db: Any,
        max_seats_per_slot: int = DEFAULT_MAX_SEATS_PER_SLOT,
    ) -> None:
        """
        Initialize the ReservationStore with a Firestore client.
        :param db: An initialized firestore.Client instance.
        """
        self._file_path: Path | None = None
        if isinstance(db, (str, Path)):
            self.db = None
            self._file_path = Path(db)
        else:
            self.db = db
        self.max_seats_per_slot = max_seats_per_slot
        self.collection_name = "reservations"
        self._seat_count_cache: dict[str, tuple[int, float]] = {} # (date+time) -> (count, expiry)
        self._load_all_cache: tuple[list[dict[str, Any]], float] | None = None
        self._CACHE_TTL = 60 # 1 minute

    def _read_local(self) -> list[dict[str, Any]]:
        if not self._file_path or not self._file_path.exists():
            return []
        try:
            return list(json.loads(self._file_path.read_text(encoding="utf-8")))
        except Exception:
            return []

    def _write_local(self, rows: list[dict[str, Any]]) -> None:
        if not self._file_path:
            return
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # ── Create ────────────────────────────────────────────

    def create(self, request: ReservationRequest) -> ReservationRecord:
        self.validate(request)

        # Capacity check
        booked = self._seats_for_slot(
            request.reservation_date, request.reservation_time
        )
        if booked + request.party_size > self.max_seats_per_slot:
            available = self.max_seats_per_slot - booked
            alt_msg = self._suggest_alternatives(
                request.reservation_date, request.reservation_time, request.party_size
            )
            if available <= 0:
                raise ReservationError(
                    f"Sorry, the {request.reservation_time} slot on {request.reservation_date} "
                    f"is fully booked (capacity: {self.max_seats_per_slot} seats).{alt_msg}"
                )
            else:
                raise ReservationError(
                    f"Only {available} seat(s) left in the {request.reservation_time} slot on "
                    f"{request.reservation_date}, but your party needs {request.party_size}.{alt_msg}"
                )

        record = ReservationRecord(
            confirmation_code=uuid4().hex[:8].upper(),
            guest_name=request.guest_name,
            phone=request.phone,
            reservation_date=request.reservation_date,
            reservation_time=request.reservation_time,
            party_size=request.party_size,
            notes=request.notes,
            status="pending_review",  # As per Agent Mission constraints
            email=request.email,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

        if self.db is None:
            rows = self._read_local()
            rows.append(record.as_dict())
            self._write_local(rows)
        else:
            # Save to Firestore
            self.db.collection(self.collection_name).document(record.confirmation_code).set(record.as_dict())

        # Invalidate cache for this slot
        cache_key = f"{request.reservation_date}T{request.reservation_time}"
        if cache_key in self._seat_count_cache:
            del self._seat_count_cache[cache_key]
        self._load_all_cache = None

        return record

    # ── Cancel ────────────────────────────────────────────

    def cancel(self, confirmation_code: str) -> dict[str, Any] | None:
        """Cancel a reservation by confirmation code in Firestore."""
        code = confirmation_code.strip().upper()
        if self.db is None:
            rows = self._read_local()
            for res in rows:
                if str(res.get("confirmation_code", "")).upper() == code:
                    if res.get("status") == "cancelled":
                        raise ReservationError("This reservation has already been cancelled.")
                    res["status"] = "cancelled"
                    res["cancelled_at"] = datetime.now().isoformat(timespec="seconds")
                    self._write_local(rows)
                    self._load_all_cache = None
                    self._seat_count_cache.clear()
                    return res
            return None

        doc_ref = self.db.collection(self.collection_name).document(code)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        data = doc.to_dict()
        if data.get("status") == "cancelled":
            raise ReservationError("This reservation has already been cancelled.")
            
        update_data = {
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat(timespec="seconds")
        }
        doc_ref.update(update_data)
        data.update(update_data)
        self._load_all_cache = None
        self._seat_count_cache.clear()
        return data

    def update_status(self, confirmation_code: str, status: str) -> dict[str, Any] | None:
        """Update a reservation's status in Firestore."""
        status = status.strip().lower()
        if status not in VALID_STATUSES:
            raise ReservationError(f"Status must be one of: {', '.join(VALID_STATUSES)}.")

        code = confirmation_code.strip().upper()
        if self.db is None:
            rows = self._read_local()
            for res in rows:
                if str(res.get("confirmation_code", "")).upper() == code:
                    res["status"] = status
                    self._write_local(rows)
                    self._load_all_cache = None
                    self._seat_count_cache.clear()
                    return res
            return None

        doc_ref = self.db.collection(self.collection_name).document(code)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        
        doc_ref.update({"status": status})
        data = doc_ref.get().to_dict()
        if data:
            data["confirmation_code"] = doc_ref.id
        self._load_all_cache = None
        self._seat_count_cache.clear()
        return data

    # ── Lookup ────────────────────────────────────────────

    def get(self, confirmation_code: str) -> dict[str, Any] | None:
        """Look up a reservation by confirmation code from Firestore."""
        code = confirmation_code.strip().upper()
        if self.db is None:
            for res in self._read_local():
                if str(res.get("confirmation_code", "")).upper() == code:
                    return res
            return None

        doc = self.db.collection(self.collection_name).document(code).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["confirmation_code"] = doc.id
        return data

    # ── Capacity ──────────────────────────────────────────

    def _seats_for_slot(self, date: str, time_str: str) -> int:
        """Count total booked seats within a 1-hour window around the given time using Firestore."""
        cache_key = f"{date}T{time_str}"
        now = time.time()
        
        if cache_key in self._seat_count_cache:
            count, expiry = self._seat_count_cache[cache_key]
            if now < expiry:
                return count

        try:
            slot_dt = datetime.fromisoformat(f"{date}T{time_str}")
        except ValueError:
            return 0

        window_start_str = (slot_dt - timedelta(minutes=30)).strftime("%H:%M")
        window_end_str = (slot_dt + timedelta(minutes=30)).strftime("%H:%M")

        if self.db is None:
            total = 0
            for res in self._read_local():
                if res.get("reservation_date") != date:
                    continue
                res_time = str(res.get("reservation_time", ""))
                if window_start_str <= res_time <= window_end_str and res.get("status") != "cancelled":
                    total += int(res.get("party_size", 0))
            self._seat_count_cache[cache_key] = (total, now + self._CACHE_TTL)
            return total
        
        try:
            # Query Firestore for reservations on this date within the time window
            query = (
                self.db.collection(self.collection_name)
                .where("reservation_date", "==", date)
                .where("reservation_time", ">=", window_start_str)
                .where("reservation_time", "<=", window_end_str)
            )
            
            total = 0
            for doc in query.stream():
                res = doc.to_dict()
                if res.get("status") != "cancelled":
                    total += int(res.get("party_size", 0))

            # Update cache
            self._seat_count_cache[cache_key] = (total, now + self._CACHE_TTL)
            return total
        except Exception as e:
            if ("ResourceExhausted" in str(e) or "429" in str(e)) and cache_key in self._seat_count_cache:
                return self._seat_count_cache[cache_key][0]
            return 0

    def slot_availability(self, date: str, time_str: str) -> dict[str, Any]:
        """Return availability info for a given date/time slot."""
        booked = self._seats_for_slot(date, time_str)
        available = max(0, self.max_seats_per_slot - booked)
        return {
            "date": date,
            "time": time_str,
            "booked_seats": booked,
            "available_seats": available,
            "max_seats": self.max_seats_per_slot,
            "is_full": available == 0,
        }

    def _suggest_alternatives(
        self,
        date: str,
        time_str: str,
        party_size: int,
    ) -> str:
        """Find nearby time slots with enough capacity using Firestore."""
        try:
            base_dt = datetime.fromisoformat(f"{date}T{time_str}")
        except ValueError:
            return ""

        alternatives: list[str] = []
        for offset_hours in [-2, -1, 1, 2]:
            alt_dt = base_dt + timedelta(hours=offset_hours)
            if alt_dt.hour < 11 or alt_dt.hour >= 22:
                continue
            alt_time = alt_dt.strftime("%H:%M")
            booked = self._seats_for_slot(date, alt_time)
            if booked + party_size <= self.max_seats_per_slot:
                alternatives.append(alt_time)

        if not alternatives:
            return " No nearby time slots are available on this date."

        return f" Try these available times: {', '.join(alternatives)}."

    # ── Validation ────────────────────────────────────────

    def validate(self, request: ReservationRequest) -> None:
        errors = []
        if not request.guest_name:
            errors.append("Guest name is required.")
        if not request.phone:
            errors.append("Phone number is required.")
        if request.party_size < 1:
            errors.append("Party size must be at least 1.")
        if request.party_size > 12:
            errors.append("Party size cannot exceed 12 for online booking.")

        scheduled_at = request.scheduled_at()
        if scheduled_at <= datetime.now():
            errors.append("Reservation time must be in the future.")

        if errors:
            raise ReservationError(" ".join(errors))

    # ── Public API ────────────────────────────────────────

    def load_all(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch recent reservations from Firestore with fault-tolerant cache."""
        now = time.time()
        if self.db is None:
            rows = sorted(self._read_local(), key=lambda r: r.get("created_at", ""), reverse=True)
            self._load_all_cache = (rows, now + self._CACHE_TTL)
            return rows[:limit]

        try:
            if self._load_all_cache and now < self._load_all_cache[1]:
                return self._load_all_cache[0][:limit]

            # Fetch all and sort in Python to avoid needing a Firestore index for order_by
            results = []
            for doc in self.db.collection(self.collection_name).stream():
                data = doc.to_dict()
                if data:
                    data["confirmation_code"] = doc.id
                    results.append(data)

            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)

            self._load_all_cache = (results, now + self._CACHE_TTL)
            return results[:limit]
        except Exception as e:
            if ("ResourceExhausted" in str(e) or "429" in str(e)) and self._load_all_cache:
                return self._load_all_cache[0][:limit]
            return []

    def chat_context(self) -> str:
        # For chat context, we might not want to query ALL reservations
        # We'll just provide general capacity info and instructions
        return (
            "Reservation handling: All bookings are saved to Cloud Firestore. "
            f"Max capacity is {self.max_seats_per_slot} seats per hour slot. "
            "Guests can book, look up, or cancel reservations using their confirmation code. "
            "New reservations are created in 'pending' status for staff review. "
            "If a time slot is full, suggest available nearby times."
        )


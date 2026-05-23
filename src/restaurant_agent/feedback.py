from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4
import time

try:
    from google.cloud import firestore
except ImportError:
    firestore = None


class FeedbackError(ValueError):
    """Raised when feedback validation fails."""


@dataclass(frozen=True)
class FeedbackEntry:
    feedback_id: str
    guest_name: str
    rating: int
    comment: str
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "guest_name": self.guest_name,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at,
        }


class FeedbackStore:
    """Feedback persistence backed by Cloud Firestore."""

    def __init__(self, db: Any) -> None:
        """
        Initialize the FeedbackStore with a Firestore client.
        :param db: An initialized firestore.Client instance.
        """
        self.db = db
        self.collection_name = "feedback"
        self._stats_cache: tuple[float | None, int, float] | None = None # (avg, count, expiry)
        self._recent_cache: tuple[list[dict[str, Any]], float] | None = None
        self._CACHE_TTL = 60 # 60 seconds

    def submit(self, guest_name: str, rating: int, comment: str) -> FeedbackEntry:
        guest_name = guest_name.strip()
        comment = comment.strip()

        errors: list[str] = []
        if not guest_name:
            errors.append("Guest name is required.")
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            errors.append("Rating must be an integer between 1 and 5.")
        if not comment:
            errors.append("A comment is required.")
        if errors:
            raise FeedbackError(" ".join(errors))

        entry = FeedbackEntry(
            feedback_id=uuid4().hex[:8].upper(),
            guest_name=guest_name,
            rating=rating,
            comment=comment,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

        # Write to Firestore
        self.db.collection(self.collection_name).document(entry.feedback_id).set(entry.as_dict())

        # Invalidate caches
        self._stats_cache = None
        self._recent_cache = None

        return entry

    def average_rating(self) -> float | None:
        """Calculate average rating from Firestore with 30s cache and fault tolerance."""
        now = time.time()
        
        try:
            if self._stats_cache and now < self._stats_cache[2]:
                return self._stats_cache[0]

            # Fetch all ratings - In production, this should be pre-aggregated
            docs = self.db.collection(self.collection_name).stream()
            ratings = []
            for doc in docs:
                data = doc.to_dict()
                if "rating" in data:
                    ratings.append(data["rating"])
            
            avg = round(sum(ratings) / len(ratings), 1) if ratings else None
            count = len(ratings)
            self._stats_cache = (avg, count, now + self._CACHE_TTL)
            return avg
        except Exception as e:
            if ("ResourceExhausted" in str(e) or "429" in str(e)) and self._stats_cache:
                return self._stats_cache[0]
            return None

    def count(self) -> int:
        """Count total feedback entries with fault-tolerant cache."""
        now = time.time()
        try:
            if self._stats_cache and now < self._stats_cache[2]:
                return self._stats_cache[1]
            
            # Update stats cache (which includes count)
            self.average_rating()
            return self._stats_cache[1] if self._stats_cache else 0
        except Exception:
            return self._stats_cache[1] if self._stats_cache else 0

    def recent(self, limit: int = 5) -> list[dict[str, Any]]:
        """Fetch n most recent feedback entries without order_by to avoid index requirements."""
        now = time.time()
        try:
            if self._recent_cache and now < self._recent_cache[1]:
                return self._recent_cache[0][:limit]

            results = []
            for doc in self.db.collection(self.collection_name).stream():
                data = doc.to_dict()
                if data:
                    results.append(data)

            # Sort by created_at in Python
            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)

            self._recent_cache = (results, now + self._CACHE_TTL)
            return results[:limit]
        except Exception as e:
            if ("ResourceExhausted" in str(e) or "429" in str(e)) and self._recent_cache:
                return self._recent_cache[0][:limit]
            return []

    def chat_context(self) -> str:
        avg = self.average_rating()
        total = self.count()
        if avg is None:
            return "No guest feedback has been submitted yet."
        return (
            f"Guest feedback: {total} review(s) with an average rating of {avg}/5. "
            "Guests can leave feedback through the feedback form on the page."
        )


from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def ensure_src_path() -> None:
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))


ensure_src_path()


class StubClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages):
        snapshot = [dict(message) for message in messages]
        self.calls.append(snapshot)
        return self.response

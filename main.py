from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Expose the Flask app for Vercel
from restaurant_agent.web import create_app
app = create_app()

from restaurant_agent.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

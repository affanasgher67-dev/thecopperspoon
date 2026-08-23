from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask

_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


def _build_app() -> Flask:
    try:
        from restaurant_agent.web import create_app

        return create_app()
    except Exception as exc:
        fallback = Flask(__name__)
        message = str(exc)

        @fallback.route("/", defaults={"path": ""})
        @fallback.route("/<path:path>")
        def _configuration_error(path: str):
            return (
                "<!doctype html><html><body style='font-family:sans-serif;max-width:720px;margin:2rem auto;'>"
                "<h1>Server configuration error</h1>"
                f"<p>{message}</p>"
                "<p>Check Vercel Runtime Logs and verify <code>FIREBASE_CREDENTIALS</code>, "
                "<code>GROQ_API_KEY</code>, and <code>VERCEL_SUPPORT_LARGE_FUNCTIONS=1</code>.</p>"
                "</body></html>"
            ), 503

        return fallback


app = _build_app()

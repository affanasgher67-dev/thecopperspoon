from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


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
                "<p>Add <code>FIREBASE_CREDENTIALS</code> in Vercel under "
                "Project Settings → Environment Variables, then redeploy.</p>"
                "</body></html>"
            ), 503

        return fallback


app = _build_app()


if __name__ == "__main__":
    from restaurant_agent.cli import main

    raise SystemExit(main())

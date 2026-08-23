from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _build_app() -> Flask:
    try:
        from restaurant_agent.web import create_app

        return create_app()
    except Exception as exc:
        fallback = Flask(__name__)
        message = str(exc)
        web_module = SRC / "restaurant_agent" / "web.py"

        @fallback.route("/", defaults={"path": ""})
        @fallback.route("/<path:path>")
        def _configuration_error(path: str):
            return (
                "<!doctype html><html><body style='font-family:sans-serif;max-width:720px;margin:2rem auto;'>"
                "<h1>Server configuration error</h1>"
                f"<p>{message}</p>"
                "<ul>"
                f"<li>src directory exists: {SRC.is_dir()}</li>"
                f"<li>web.py exists: {web_module.is_file()}</li>"
                f"<li>PYTHONPATH includes src: {'src' in str(SRC) or str(SRC) in sys.path}</li>"
                "</ul>"
                "<p>Set <code>FIREBASE_CREDENTIALS</code>, <code>GROQ_API_KEY</code>, "
                "and <code>VERCEL_SUPPORT_LARGE_FUNCTIONS=1</code> in Vercel env vars.</p>"
                "</body></html>"
            ), 503

        return fallback


app = _build_app()
application = app
handler = app


if __name__ == "__main__":
    from restaurant_agent.cli import main

    raise SystemExit(main())

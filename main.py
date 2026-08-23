from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Expose the Flask app for Vercel
try:
    from restaurant_agent.web import create_app

    app = create_app()
except Exception as _startup_error:
    from flask import Flask

    app = Flask(__name__)
    _message = str(_startup_error)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def _configuration_error(path: str):
        return (
            "<!doctype html><html><body style='font-family:sans-serif;max-width:720px;margin:2rem auto;'>"
            "<h1>Server configuration error</h1>"
            f"<p>{_message}</p>"
            "<p>Add <code>FIREBASE_CREDENTIALS</code> in Vercel under "
            "Project Settings → Environment Variables, then redeploy.</p>"
            "</body></html>"
        ), 503

from restaurant_agent.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

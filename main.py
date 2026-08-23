from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask

# Try multiple approaches to find the src directory
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Also try the raw __file__ without resolve()
ROOT_RAW = Path(os.path.dirname(os.path.abspath(__file__)))
SRC_RAW = ROOT_RAW / "src"

# Try /var/task/src directly (Vercel's deployment path)
SRC_VERCEL = Path("/var/task/src")

for candidate in [SRC, SRC_RAW, SRC_VERCEL]:
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _build_app() -> Flask:
    try:
        from restaurant_agent.web import create_app

        return create_app()
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        fallback = Flask(__name__)
        message = str(exc)

        # Gather debug info
        debug_lines = [
            f"Error: {message}",
            f"ROOT (resolved): {ROOT}",
            f"ROOT_RAW: {ROOT_RAW}",
            f"SRC (resolved): {SRC}  exists={SRC.is_dir()}",
            f"SRC_RAW: {SRC_RAW}  exists={SRC_RAW.is_dir()}",
            f"SRC_VERCEL: {SRC_VERCEL}  exists={SRC_VERCEL.is_dir()}",
            f"__file__: {__file__}",
            f"cwd: {os.getcwd()}",
            f"sys.path: {sys.path[:8]}",
        ]

        # List ROOT contents
        if ROOT.is_dir():
            try:
                items = sorted(os.listdir(str(ROOT)))[:30]
                debug_lines.append(f"ROOT contents: {items}")
            except Exception:
                debug_lines.append("ROOT contents: (error listing)")

        # List SRC contents if it exists
        for label, src_path in [("SRC", SRC), ("SRC_RAW", SRC_RAW), ("SRC_VERCEL", SRC_VERCEL)]:
            if src_path.is_dir():
                try:
                    items = sorted(os.listdir(str(src_path)))[:20]
                    debug_lines.append(f"{label} contents: {items}")
                    ra_dir = src_path / "restaurant_agent"
                    if ra_dir.is_dir():
                        ra_items = sorted(os.listdir(str(ra_dir)))[:20]
                        debug_lines.append(f"{label}/restaurant_agent contents: {ra_items}")
                except Exception:
                    pass

        debug_html = "".join(f"<li><code>{line}</code></li>" for line in debug_lines)

        @fallback.route("/", defaults={"path": ""})
        @fallback.route("/<path:path>")
        def _configuration_error(path: str):
            return (
                "<!doctype html><html><body style='font-family:monospace;max-width:900px;margin:2rem auto;'>"
                "<h1>Server configuration error</h1>"
                f"<ul>{debug_html}</ul>"
                f"<h2>Traceback</h2><pre>{tb}</pre>"
                "</body></html>"
            ), 503

        return fallback


app = _build_app()
application = app
handler = app


if __name__ == "__main__":
    from restaurant_agent.cli import main

    raise SystemExit(main())


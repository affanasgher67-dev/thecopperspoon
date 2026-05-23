from __future__ import annotations

import json
import threading
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def _send_request(webhook_url: str, event_type: str, data: dict[str, Any]) -> None:
    payload = {
        "event": event_type,
        "data": data,
        "source": "restaurant-agent"
    }
    try:
        request = Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                print(f"n8n webhook failed with status: {response.status}")
            else:
                print(f"n8n webhook sent successfully: {event_type}")
    except (URLError, HTTPError) as e:
        print(f"Failed to send n8n webhook: {e}")
    except Exception as e:
        print(f"An unexpected error occurred sending n8n webhook: {e}")

def send_n8n_webhook(webhook_url: str | None, event_type: str, data: dict[str, Any]) -> None:
    """
    Sends a JSON payload to an n8n webhook URL in the background.
    """
    if not webhook_url:
        # Keep the app non-blocking, but make missing integration config obvious in logs.
        print(f"n8n webhook skipped (N8N_WEBHOOK_URL missing). event={event_type}")
        return

    # Run in a background thread so we don't block the main web response
    thread = threading.Thread(target=_send_request, args=(webhook_url, event_type, data))
    thread.daemon = True
    thread.start()

import sys
from pathlib import Path

# Add src to sys.path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from restaurant_agent.webhooks import send_n8n_webhook

# Mock data
webhook_url = "http://localhost:5678/webhook-test/afde56be-a610-414c-bab5-8acfb19f96f4"
event = "test.event"
data = {"test": "data", "message": "hello from verification script"}

print(f"Sending test webhook to {webhook_url}...")
send_n8n_webhook(webhook_url, event, data)
print("Done. Check your n8n 'Listen for test event' output.")

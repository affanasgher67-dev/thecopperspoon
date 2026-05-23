import logging
logging.basicConfig(level=logging.DEBUG)
import os, json
os.environ["OLLAMA_MODEL"] = "llama3.2:latest"
from src.restaurant_agent.client import OllamaChatClient
client = OllamaChatClient()
messages = [
    {"role": "user", "content": "I want to book a table for 2."},
    {"role": "assistant", "content": "Tomorrow is today. How about tomorrow at 2 PM?"},
    {"role": "user", "content": "yes sounds good"}
]
try:
    print(client.complete(messages))
except Exception as e:
    import traceback
    traceback.print_exc()

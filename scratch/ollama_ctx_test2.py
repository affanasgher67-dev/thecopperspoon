import urllib.request, json

def _test():
    messages = [
        {"role": "system", "content": "You are a professional restaurant agent."},
        {"role": "system", "content": "INTERNAL RESTAURANT CONTEXT: MENU CATALOG"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Tomorrow is today. How about tomorrow at 2 PM?"},
        {"role": "user", "content": "yes sounds good"}
    ]
    tools_config = [
            {
                "type": "function",
                "function": {
                    "name": "book_reservation",
                    "description": "Book a restaurant reservation. Call this when the guest explicitly confirms they want to book a table for a party.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "guest_name": {"type": "string", "description": "Name under the reservation"},
                            "phone": {"type": "string", "description": "Contact phone number"},
                            "email": {"type": "string", "description": "Guest email address (required for confirmation)"},
                            "reservation_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "reservation_time": {"type": "string", "description": "Time in HH:MM format in 24hr"},
                            "party_size": {"type": "integer", "description": "Number of guests"},
                            "notes": {"type": "string", "description": "Any special requests"}
                        },
                        "required": ["guest_name", "phone", "email", "reservation_date", "reservation_time", "party_size"]
                    }
                }
            }
        ]
    
    payload = {
        "model": "llama3.2:latest",
        "messages": messages,
        "tools": tools_config,
        "temperature": 0.5,
    }
    request = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request)
        print("SUCCESS")
    except Exception as e:
        print("ERROR:", str(e))
        try:
            print(e.read().decode())
        except:
            pass

_test()

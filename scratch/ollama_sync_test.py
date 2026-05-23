import sys, json, traceback

def _test():
    import urllib.request
    messages = [
        {"role": "user", "content": "I want to book a table for 2."},
        {"role": "assistant", "content": "Tomorrow is today. How about tomorrow at 2 PM?"},
        {"role": "user", "content": "yes sounds good"}
    ]
    tools_config = [{"type":"function","function":{"name":"test","description":"test"}}]
    
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
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            print("SUCCESS")
            print(json.dumps(body, indent=2))
    except Exception as e:
        print("ERROR:", str(e))
        traceback.print_exc()

_test()

import urllib.request, json

def _test():
    payload = {
        "model": "llama3.2:latest",
        "messages": [{"role": "user", "content": "word " * 3000}],
        "temperature": 0.5,
    }
    request = urllib.request.Request(
        "http://localhost:11434/api/chat",
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

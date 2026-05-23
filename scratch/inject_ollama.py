import os
import json
import logging

def inject_ollama_client():
    filepath = r"d:\Restaurant Agent\src\restaurant_agent\client.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    ollama_class = """

@dataclass
class OllamaChatClient:
    model: str = "llama3.2:latest"
    base_url: str = "http://localhost:11434/v1"
    timeout_seconds: int = 300

    def complete(self, messages: Sequence[ChatMessage]) -> str:
        formatted_msgs = list(messages)
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
            },
            {
                "type": "function",
                "function": {
                    "name": "place_order",
                    "description": "Place a food order. Call this when the guest explicitly confirms their final order items.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "guest_name": {"type": "string"},
                            "phone": {"type": "string"},
                            "email": {"type": "string"},
                            "order_type": {"type": "string", "enum": ["pickup", "delivery"]},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Exact name of menu item"},
                                        "quantity": {"type": "integer"}
                                    },
                                    "required": ["name", "quantity"]
                                }
                            },
                            "notes": {"type": "string", "description": "Any special instructions or dietary notes"}
                        },
                        "required": ["guest_name", "phone", "email", "order_type", "items"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_reservation",
                    "description": "Cancel a restaurant reservation using the confirmation code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "confirmation_code": {"type": "string", "description": "The reservation confirmation code to cancel"}
                        },
                        "required": ["confirmation_code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_order",
                    "description": "Cancel a food order using the order ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string", "description": "The order ID to cancel"}
                        },
                        "required": ["order_id"]
                    }
                }
            }
        ]

        for iteration in range(5):
            payload = {
                "model": self.model,
                "messages": formatted_msgs,
                "tools": tools_config,
                "temperature": 0.5,
            }
            request = Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                error_text = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Ollama request failed: {exc.code} {exc.reason}: {error_text}") from exc
            except URLError as exc:
                raise RuntimeError(f"Ollama connection failed: {exc.reason}") from exc

            choices = body.get("choices") or []
            if not choices:
                raise RuntimeError("Ollama response did not contain any choices.")

            message = choices[0].get("message") or {}
            
            # Ollama requires we feed back the assistant message exactly
            formatted_msgs.append(message)

            tool_calls = message.get("tool_calls")
            if tool_calls:
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    name = func.get("name")
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    
                    try:
                        result = self._execute_tool(name, args)
                    except Exception as e:
                        result = {"success": False, "error": str(e)}

                    formatted_msgs.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "123"), # Safe fallback if ollama omits id
                        "name": name,
                        "content": json.dumps(result)
                    })
                
                # Execute another loop to let the model generate the final response
                continue

            content = message.get("content")
            if not content:
                # Sometimes models output empty strings with tool responses
                return "I couldn't generate a response."

            return str(content).strip()

        return "Internal Error: I reached maximum tool calls."

    def _execute_tool(self, name: str, args: dict) -> dict:
        # Re-using the same function as Gemini
        return GeminiChatClient(api_key="mock")._execute_tool(name, args)

def build_chat_client(*, force_demo: bool = False) -> ChatClient:
"""

    # Inject OllamaChatClient
    old_target = "def build_chat_client(*, force_demo: bool = False) -> ChatClient:"
    if "OllamaChatClient" not in content:
        content = content.replace(old_target, ollama_class)

    # Now inject Ollama into the factory precedence
    old_factory = '''    if gemini_key:
        return GeminiChatClient(
            api_key=gemini_key,
            model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        )'''
    
    new_factory = '''    ollama_model = os.getenv("OLLAMA_MODEL", "").strip()
    if ollama_model:
        return OllamaChatClient(model=ollama_model)
        
    if gemini_key:
        return GeminiChatClient(
            api_key=gemini_key,
            model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        )'''
        
    if "OLLAMA_MODEL" not in content:
        content = content.replace(old_factory, new_factory)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    inject_ollama_client()
    print("Ollama injected successfully!")

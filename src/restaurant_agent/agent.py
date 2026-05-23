from __future__ import annotations
import os
import re
from typing import Callable

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .config import RestaurantProfile, load_restaurant_profile
from .persona import build_system_prompt
from .tz_langchain_tools import restaurant_tools

ContextProvider = Callable[[], str]

class RestaurantAgent:
    def __init__(self, profile: RestaurantProfile, context_provider: ContextProvider | None = None, messages: list[dict[str, str]] | None = None, current_time: str | None = None, client=None):
        self.profile = profile
        self.context_provider = context_provider
        self.system_prompt = build_system_prompt(profile, current_time=current_time)
        self.client = client
        self.messages = list(messages or [])

        # Compatibility mode for tests/CLI: when an explicit client is provided,
        # maintain a classic role/content message list and skip Groq runtime.
        if self.client is not None:
            if not self.messages:
                self.messages = [{"role": "system", "content": self.system_prompt}]
            self.llm = None
            self.executor = None
            return

        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set!")

        self.llm = ChatGroq(
            api_key=api_key,
            model="llama-3.1-8b-instant",
            temperature=0.1,
        )

        self.executor = create_react_agent(self.llm, tools=restaurant_tools)

    def reply(self, user_message: str) -> str:
        user_message = user_message.strip()
        if not user_message:
            return "I'm here whenever you're ready."

        context_string = ""
        if self.context_provider:
             context_string = self.context_provider() or ""

        if self.client is not None:
            if not self.messages or self.messages[0].get("role") != "system":
                self.reset()

            outgoing = [dict(msg) for msg in self.messages]
            if context_string:
                outgoing.insert(1, {"role": "system", "content": context_string})
            outgoing.append({"role": "user", "content": user_message})

            final_response = self.client.complete(outgoing)
            self.messages.append({"role": "user", "content": user_message})
            self.messages.append({"role": "assistant", "content": final_response})

            max_messages = 21  # 1 system + up to 10 user/assistant turns
            if len(self.messages) > max_messages:
                self.messages = [self.messages[0], *self.messages[-20:]]
            return final_response

        chat_history = []
        
        sys_msg = self.system_prompt
        if context_string:
            sys_msg += "\n\n" + context_string
        chat_history.append(SystemMessage(content=sys_msg))
        
        for msg in self.messages:
             if msg["role"] == "user":
                  chat_history.append(HumanMessage(content=msg["content"]))
             elif msg["role"] == "assistant":
                  chat_history.append(AIMessage(content=msg["content"]))

        chat_history.append(HumanMessage(content=user_message))
        
        # Limit recursion to prevent quota-wasting loops (Default is 25)
        result = self.executor.invoke({"messages": chat_history}, config={"recursion_limit": 15})
        # Clean up technical artifacts from the response
        final_response = self._clean_response(result["messages"][-1].content)
        
        self.messages.append({"role": "user", "content": user_message})
        self.messages.append({"role": "assistant", "content": final_response})

        # Reduced cap to minimize token payload and preserve quota
        max_messages = 10
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]

        return final_response

    def reset(self) -> None:
        if self.client is not None:
            self.messages = [{"role": "system", "content": self.system_prompt}]
        else:
            self.messages = []

    def snapshot(self) -> list[dict[str, str]]:
        return self.messages

    def _clean_response(self, text: str) -> str:
        """Strip raw tool-calling tags and JSON blocks from the response."""
        if not text:
            return text
        
        # Remove patterns like: <tag>...</tag>, function=... </function>, {json...}
        patterns = [
            r"function=.*?</function>",    # function=... </function>
            r"<[^>]+>.*?</[^>]+>",        # Any other XML-style tags
            r"\{.*?\}",                    # JSON-like blocks
            r"book_reservation=.*",        # Specific label artifacts
            r"place_order=.*",
            r"cancel_reservation=.*",
            r"cancel_order=.*",
            r"fetch_menu=.*",
            r"(?i)SUCCESS:\s*Reservation\s*created[^\n]*",
            r"(?i)SUCCESS:\s*Order\s*placed[^\n]*",
        ]
        
        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # Final trim
        cleaned = cleaned.strip()
        # If we accidentally stripped EVERYTHING, return a fallback
        if not cleaned and text:
            # Try to find the last sentence if everything else was technical
            return "Your request has been processed. Is there anything else I can help with?"
            
        return cleaned

def build_restaurant_agent(
    *,
    profile: RestaurantProfile | None = None,
    client=None, # Absorbing old args
    context_provider: ContextProvider | None = None,
    messages: list[dict[str, str]] | None = None,
    current_time: str | None = None,
) -> RestaurantAgent:
    active_profile = profile or load_restaurant_profile()
    return RestaurantAgent(
        profile=active_profile,
        context_provider=context_provider,
        messages=list(messages or []),
        current_time=current_time,
        client=client,
    )

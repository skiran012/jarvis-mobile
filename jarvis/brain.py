"""Brain — reasoning with the Anthropic Claude API, using the tool-use (function-calling) loop.

Algorithm for one turn:
    1. Append the user's text to short-term memory.
    2. Send system prompt + memory + tool schemas to Claude.
    3. While Claude returns stop_reason == "tool_use":
         run each requested skill locally -> send results back as tool_result blocks.
    4. When Claude returns plain text, store it in memory and return it.
"""

from __future__ import annotations

import anthropic

from .config import CONFIG
from .memory import ShortTermMemory
from .skills import TOOLS, get_datetime, run_tool

MAX_TOOL_ROUNDS = 5


def system_prompt() -> str:
    return (
        f"You are {CONFIG.assistant_name}, a calm, witty, highly capable personal AI assistant "
        f"in the style of a British butler. You address the user as '{CONFIG.user_name}'. "
        f"The current time is {get_datetime()}.\n"
        "Your replies are spoken aloud on a phone, so: keep them to 1–3 short sentences unless asked "
        "for detail, never use markdown, bullet points, tables or emojis, and say numbers naturally. "
        "Use tools whenever they give a more accurate answer (time, maths, weather, facts, notes, "
        "reminders). If the user speaks Hindi or Kannada, reply in that language."
    )


class Brain:
    def __init__(self):
        if not CONFIG.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is missing. In Colab, add it under the 🔑 Secrets panel."
            )
        self.client = anthropic.Anthropic(api_key=CONFIG.anthropic_api_key)
        self.memory = ShortTermMemory()

    def think(self, user_text: str) -> tuple[str, list[str]]:
        """Return (reply_text, list_of_tools_used)."""
        self.memory.add("user", user_text)
        messages = list(self.memory.messages)
        tools_used: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.messages.create(
                model=CONFIG.model,
                max_tokens=CONFIG.max_tokens,
                system=system_prompt(),
                tools=TOOLS,
                messages=messages,
            )
            if response.stop_reason != "tool_use":
                break
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_used.append(block.name)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": run_tool(block.name, block.input),
                    })
            messages.append({"role": "user", "content": results})

        reply = "".join(b.text for b in response.content if b.type == "text").strip()
        reply = reply or "I'm afraid I couldn't complete that, " + CONFIG.user_name + "."
        self.memory.add("assistant", reply)
        return reply, tools_used

    def reset(self) -> None:
        self.memory.clear()

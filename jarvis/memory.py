"""Memory — short-term conversation window + long-term notes and reminders on disk."""

from __future__ import annotations

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import CONFIG


class ShortTermMemory:
    """Rolling window of the last N user/assistant turns sent to the LLM."""

    def __init__(self, max_turns: int = CONFIG.history_turns):
        self.max_turns = max_turns
        self.messages: list[dict] = []

    def add(self, role: str, content) -> None:
        self.messages.append({"role": role, "content": content})
        self._trim()

    def _trim(self) -> None:
        # Keep the window, and always start on a plain user text turn so the API accepts it.
        while len(self.messages) > self.max_turns * 2:
            self.messages.pop(0)
        while self.messages and not (
            self.messages[0]["role"] == "user" and isinstance(self.messages[0]["content"], str)
        ):
            self.messages.pop(0)

    def clear(self) -> None:
        self.messages.clear()


class LongTermMemory:
    """Notes and reminders persisted as JSON (survives across chats in the same session/Drive)."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(CONFIG.data_dir, "memory.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data = {"notes": [], "reminders": []}
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self.data.update(json.load(f))

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _now(self) -> str:
        return datetime.now(ZoneInfo(CONFIG.timezone)).strftime("%Y-%m-%d %H:%M")

    def add_note(self, text: str) -> str:
        self.data["notes"].append({"text": text, "at": self._now()})
        self._save()
        return f"Noted: {text}"

    def list_notes(self) -> list[dict]:
        return self.data["notes"]

    def add_reminder(self, text: str, when: str) -> str:
        self.data["reminders"].append({"text": text, "when": when, "created": self._now()})
        self._save()
        return f"Reminder set for {when}: {text}"

    def list_reminders(self) -> list[dict]:
        return self.data["reminders"]

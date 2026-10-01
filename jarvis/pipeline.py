"""The JARVIS loop — one function that ties Ears -> Brain -> Skills -> Voice together.

    audio/text ─► STT ─► wake-word gate ─► Brain (Claude + tools) ─► TTS ─► reply audio + text
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .config import CONFIG


@dataclass
class TurnResult:
    heard: str = ""
    reply: str = ""
    audio_path: str | None = None
    tools_used: list[str] = field(default_factory=list)
    latency_s: float = 0.0
    skipped: bool = False


def strip_wake_word(text: str) -> tuple[bool, str]:
    """Return (wake_word_found, text_without_wake_word)."""
    lowered = text.lower().strip()
    for w in sorted(CONFIG.wake_words, key=len, reverse=True):
        if lowered.startswith(w):
            return True, re.sub(r"^[\s,.!?]+", "", text.strip()[len(w):])
    return False, text


class Jarvis:
    def __init__(self, brain=None, transcribe=None, speak=None):
        # Dependencies are injectable so the loop can be unit-tested without GPU/API keys.
        if brain is None:
            from .brain import Brain
            brain = Brain()
        if transcribe is None:
            from .stt import transcribe
        if speak is None:
            from .tts import speak
        self.brain, self.transcribe, self.speak = brain, transcribe, speak

    def turn(self, audio_path: str | None = None, text: str | None = None, voice: bool = True) -> TurnResult:
        start = time.time()
        result = TurnResult()

        # 1. LISTEN — typed text wins; otherwise transcribe the recording
        result.heard = (text or "").strip() or (self.transcribe(audio_path) if audio_path else "")
        if not result.heard:
            result.skipped = True
            return result

        # 2. WAKE-WORD GATE — only for voice input, and only when enabled
        query = result.heard
        if audio_path and not text:
            found, query = strip_wake_word(result.heard)
            if CONFIG.require_wake_word and not found:
                result.skipped = True
                return result
            query = query or "Yes?"

        # 3. THINK + ACT — Claude reasons and calls skills as needed
        result.reply, result.tools_used = self.brain.think(query)

        # 4. SPEAK
        if voice:
            result.audio_path = self.speak(result.reply)

        result.latency_s = round(time.time() - start, 2)
        return result

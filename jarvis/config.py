"""Central configuration. Every value can be overridden with an environment variable."""

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Config:
    # --- Identity ---
    assistant_name: str = _env("JARVIS_NAME", "JARVIS")
    user_name: str = _env("JARVIS_USER", "Sir")
    timezone: str = _env("JARVIS_TZ", "Asia/Kolkata")

    # --- Brain (LLM) ---
    anthropic_api_key: str = _env("ANTHROPIC_API_KEY", "")
    model: str = _env("JARVIS_MODEL", "claude-sonnet-5-5")
    max_tokens: int = int(_env("JARVIS_MAX_TOKENS", "600"))
    history_turns: int = int(_env("JARVIS_HISTORY_TURNS", "10"))  # short-term memory window

    # --- Ears (Speech-to-Text) ---
    whisper_model: str = _env("JARVIS_WHISPER_MODEL", "small")  # tiny | base | small | medium | large-v3
    stt_language: str = _env("JARVIS_STT_LANG", "")  # "" = auto-detect; "en", "hi", "kn" to force

    # --- Voice (Text-to-Speech) ---
    tts_engine: str = _env("JARVIS_TTS_ENGINE", "edge")  # edge | gtts
    edge_voice: str = _env("JARVIS_EDGE_VOICE", "en-GB-RyanNeural")  # the classic British butler voice
    gtts_lang: str = _env("JARVIS_GTTS_LANG", "en")
    gtts_tld: str = _env("JARVIS_GTTS_TLD", "co.uk")

    # --- Wake word (optional) ---
    require_wake_word: bool = _env("JARVIS_WAKE_WORD", "false").lower() == "true"
    wake_words: tuple = field(default_factory=lambda: ("jarvis", "hey jarvis", "ok jarvis"))

    # --- Storage ---
    data_dir: str = _env("JARVIS_DATA_DIR", "jarvis_data")

    # --- Optional web search (Tavily) ---
    tavily_api_key: str = _env("TAVILY_API_KEY", "")


CONFIG = Config()

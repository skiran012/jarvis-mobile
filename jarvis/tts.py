"""Voice — Text-to-Speech. edge-tts (neural voices, free) with gTTS as fallback."""

from __future__ import annotations

import asyncio
import os
import re
import uuid

from .config import CONFIG


def _clean(text: str) -> str:
    """Strip markdown so the voice doesn't read out asterisks and hashes."""
    text = re.sub(r"```.*?```", " code block omitted. ", text, flags=re.S)
    text = re.sub(r"[*_#`>|]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _out_path() -> str:
    folder = os.path.join(CONFIG.data_dir, "audio")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"reply_{uuid.uuid4().hex[:8]}.mp3")


def _edge(text: str, path: str) -> None:
    import edge_tts

    async def run():
        await edge_tts.Communicate(text, CONFIG.edge_voice).save(path)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():  # inside Jupyter/Colab's event loop
        import nest_asyncio

        nest_asyncio.apply()
        loop.run_until_complete(run())
    else:
        asyncio.run(run())


def _gtts(text: str, path: str) -> None:
    from gtts import gTTS

    gTTS(text=text, lang=CONFIG.gtts_lang, tld=CONFIG.gtts_tld).save(path)


def speak(text: str) -> str | None:
    """Return the path of an MP3 containing the spoken reply (None if TTS fails)."""
    text = _clean(text)
    if not text:
        return None
    path = _out_path()
    engines = [_edge, _gtts] if CONFIG.tts_engine == "edge" else [_gtts, _edge]
    for engine in engines:
        try:
            engine(text, path)
            return path
        except Exception as exc:  # network hiccup, missing package, etc.
            print(f"[TTS] {engine.__name__} failed: {exc}")
    return None

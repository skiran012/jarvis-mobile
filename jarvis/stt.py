"""Ears — Speech-to-Text using faster-whisper (CTranslate2 build of OpenAI Whisper)."""

from __future__ import annotations

from functools import lru_cache

from .config import CONFIG


def _device() -> tuple[str, str]:
    """Use the Colab GPU (T4) with float16 when present, otherwise CPU with int8."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"


@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel

    device, compute_type = _device()
    print(f"[STT] Loading Whisper '{CONFIG.whisper_model}' on {device} ({compute_type})")
    return WhisperModel(CONFIG.whisper_model, device=device, compute_type=compute_type)


def transcribe(audio_path: str) -> str:
    """Convert a recorded audio file to text. Voice Activity Detection trims silence."""
    if not audio_path:
        return ""
    segments, _info = _model().transcribe(
        audio_path,
        language=CONFIG.stt_language or None,
        vad_filter=True,
        beam_size=5,
    )
    return " ".join(s.text.strip() for s in segments).strip()

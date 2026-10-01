"""JARVIS Mobile — a voice assistant you run in Google Colab and use from your phone.

Pipeline (the "J.A.R.V.I.S. loop"):
    Listen  -> Speech-to-Text (faster-whisper)
    Understand & Reason -> LLM with tool use (Anthropic Claude API)
    Act     -> Skills (time, maths, notes, reminders, web lookup)
    Respond -> Text-to-Speech (gTTS / edge-tts)
    Remember -> Short-term chat memory + long-term notes (JSON)
"""

__version__ = "1.0.0"

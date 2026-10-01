# 🤖 JARVIS Mobile

**Build your own voice assistant in Google Colab and use it from your phone.**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/skiran012/jarvis-mobile/blob/main/notebooks/Jarvis_Mobile_Colab.ipynb)

Tap the mic on your phone, speak, and JARVIS answers out loud — it can tell the time, do maths, check the weather, look things up, and remember notes and reminders.

---

## ⚡ Quick start (5 minutes)

1. Click **Open in Colab** above.
2. `Runtime → Change runtime type → T4 GPU`.
3. In the 🔑 **Secrets** panel add `ANTHROPIC_API_KEY` (get one at [console.anthropic.com](https://console.anthropic.com)) and switch on *Notebook access*.
4. `Runtime → Run all`.
5. Open the `https://….gradio.live` link printed at the bottom **on your phone** → allow the microphone → talk.
6. Optional: **Add to Home screen** (Chrome ⋮ menu / Safari Share menu) for an app-like JARVIS icon.

---

## 🧠 The algorithm

```
                ┌──────────────────────── PHONE (browser) ────────────────────────┐
                │   🎙 mic recording / ⌨ typed text          🔊 auto-played reply │
                └──────────────┬──────────────────────────────────────▲──────────┘
                               │ HTTPS (Gradio share link)            │
┌──────────────────────────────▼──────── GOOGLE COLAB (T4 GPU) ───────┴───────────┐
│ 1 LISTEN    faster-whisper (Whisper 'small', CUDA fp16, VAD) ─► text             │
│ 2 GATE      wake word "Jarvis / Hey Jarvis" detected & stripped (optional)      │
│ 3 THINK     Anthropic Claude API  +  short-term memory (last 10 turns)          │
│ 4 ACT       tool-use loop ─► skills: time · calculator · weather · web ·        │
│             notes · reminders   (results fed back to Claude, max 5 rounds)      │
│ 5 SPEAK     edge-tts neural voice (fallback gTTS) ─► MP3                        │
│ 6 REMEMBER  conversation window + notes/reminders in jarvis_data/memory.json    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Pseudocode for one turn** (`jarvis/pipeline.py` + `jarvis/brain.py`):

```
function JARVIS_TURN(audio, text):
    heard ← text  if text else  WHISPER_TRANSCRIBE(audio)          # Listen
    if heard is empty: return SKIP
    if voice input:
        found, query ← STRIP_WAKE_WORD(heard)                        # Gate
        if WAKE_WORD_REQUIRED and not found: return SKIP
    MEMORY.append(user: query)
    messages ← MEMORY.window(10 turns)
    repeat up to 5 times:                                            # Think + Act
        response ← CLAUDE(system_prompt, messages, TOOL_SCHEMAS)
        if response.stop_reason ≠ "tool_use": break
        for each tool_call in response:
            result ← RUN_SKILL(tool_call.name, tool_call.args)
        messages.append(tool_results)
    reply ← response.text
    MEMORY.append(assistant: reply)                                  # Remember
    audio_reply ← EDGE_TTS(reply) or GTTS(reply)                     # Speak
    return reply, audio_reply
```

---

## 🧰 Technology stack

| Layer | Technology | Why |
|---|---|---|
| Runtime | Google Colab (T4 GPU) | Free GPU, nothing to install on the phone |
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI Whisper, CTranslate2) | Fast, accurate, multilingual (English, Hindi, Kannada) |
| Reasoning | [Anthropic Claude API](https://docs.claude.com) — tool use / function calling | Decides which skill to call and writes the spoken reply |
| Skills | Python + [Open-Meteo](https://open-meteo.com) (weather, no key) + Wikipedia / [Tavily](https://tavily.com) (search) | Real-world actions and live data |
| Text-to-Speech | [edge-tts](https://github.com/rany2/edge-tts) neural voices, [gTTS](https://github.com/pndurette/gTTS) fallback | Natural British "butler" voice by default |
| Mobile UI | [Gradio](https://gradio.app) 5 Blocks + `share=True` | Instant HTTPS link with mic access on any phone |
| Memory | In-process window + JSON file | Context across turns, notes that persist |
| Tests | pytest (offline, mocked STT/LLM/TTS) | `python -m pytest -q` |

---

## 📁 Repository layout

```
jarvis-mobile/
├── notebooks/Jarvis_Mobile_Colab.ipynb   ← run this in Colab
├── jarvis/
│   ├── config.py     settings (env-var driven)
│   ├── stt.py        Listen  – faster-whisper
│   ├── brain.py      Think   – Claude tool-use loop
│   ├── skills.py     Act     – tools + JSON schemas
│   ├── tts.py        Speak   – edge-tts / gTTS
│   ├── memory.py     Remember – short & long-term memory
│   ├── pipeline.py   the JARVIS loop that wires it all together
│   └── app.py        mobile web UI (Gradio)
├── tests/test_pipeline.py
└── requirements.txt
```

---

## 🎛 Configuration

Set these as environment variables (cell 4 of the notebook):

| Variable | Default | Options |
|---|---|---|
| `JARVIS_USER` | `Sir` | how JARVIS addresses you |
| `JARVIS_MODEL` | `claude-sonnet-5-5` | any Claude model ID, e.g. `claude-haiku-4-5-20251001` for lower cost |
| `JARVIS_WHISPER_MODEL` | `small` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `JARVIS_EDGE_VOICE` | `en-GB-RyanNeural` | `en-IN-PrabhatNeural`, `hi-IN-MadhurNeural`, `kn-IN-GaganNeural` … |
| `JARVIS_WAKE_WORD` | `false` | `true` = only respond to "Jarvis …" |
| `JARVIS_TZ` | `Asia/Kolkata` | any IANA time zone |
| `TAVILY_API_KEY` | – | optional, upgrades web search |

---

## ➕ Add your own skill

```python
# jarvis/skills.py
def open_salon_bookings() -> str:
    return "You have 3 bookings today."

TOOLS.append(_tool("open_salon_bookings", "Today's salon bookings."))
REGISTRY["open_salon_bookings"] = open_salon_bookings
```

Claude will start calling it automatically when a request matches the description.

---

## 🚀 Keep it running 24×7

Colab links only live while the notebook is running. For a permanent phone app, push this repo to a **Hugging Face Space** (SDK: Gradio, entry file `app.py`, add `ANTHROPIC_API_KEY` as a Space secret) — the Space URL can then be added to your home screen. Use `JARVIS_WHISPER_MODEL=base` on the free CPU tier.

---

## 🗺 Roadmap ideas

- Streaming replies (speak while Claude is still writing)
- Always-listening wake word on-device with [openWakeWord](https://github.com/dscripka/openWakeWord)
- Google Calendar / Gmail skills via their APIs
- Native Android wrapper (Capacitor / Kivy) around the web app

---

## 📄 License

MIT — see [LICENSE](LICENSE).

Built by **Sandeep Gaikwad**.

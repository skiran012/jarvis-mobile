"""Phone-friendly web app (Gradio). Run in Colab with share=True to get a public HTTPS link
you open on your phone — tap the mic, talk, and JARVIS answers out loud."""

from __future__ import annotations

import gradio as gr

from .config import CONFIG
from .pipeline import Jarvis

CSS = """
.gradio-container {max-width: 520px !important; margin: auto;}
#title {text-align:center; letter-spacing: .25em;}
#title h1 {color:#4fd1ff; text-shadow: 0 0 12px #4fd1ff88; margin-bottom: 0}
#reactor {width:90px;height:90px;margin:8px auto;border-radius:50%;
  background: radial-gradient(circle,#e6fbff 0%,#4fd1ff 35%,#0a3d62 70%,transparent 72%);
  box-shadow:0 0 30px #4fd1ff, inset 0 0 20px #4fd1ff; animation:pulse 2.4s ease-in-out infinite;}
@keyframes pulse {0%,100%{transform:scale(1);opacity:.9} 50%{transform:scale(1.07);opacity:1}}
footer {display:none !important}
"""

HEAD = """
<meta name="theme-color" content="#0b1220">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="JARVIS">
"""


def build_app(jarvis: Jarvis | None = None) -> gr.Blocks:
    jarvis = jarvis or Jarvis()

    def handle(audio, text, history):
        history = history or []
        r = jarvis.turn(audio_path=audio, text=text)
        if r.skipped:
            hint = "Say 'Jarvis …' first." if CONFIG.require_wake_word else "I didn't catch that."
            return history, None, "", None, hint
        history += [
            {"role": "user", "content": r.heard},
            {"role": "assistant", "content": r.reply},
        ]
        status = f"⏱ {r.latency_s}s" + (f" · 🛠 {', '.join(r.tools_used)}" if r.tools_used else "")
        return history, r.audio_path, "", None, status

    def reset():
        jarvis.brain.reset()
        return [], None, "", None, "Memory cleared."

    with gr.Blocks(css=CSS, head=HEAD, theme=gr.themes.Soft(primary_hue="cyan"), title="JARVIS") as app:
        gr.HTML(f"<div id='title'><h1>{CONFIG.assistant_name}</h1>"
                "<small>Just A Rather Very Intelligent System</small></div><div id='reactor'></div>")
        chat = gr.Chatbot(type="messages", height=360, show_label=False)
        voice_out = gr.Audio(label="Reply", autoplay=True, interactive=False, type="filepath")
        mic = gr.Audio(sources=["microphone"], type="filepath", label="🎙 Tap to talk")
        with gr.Row():
            box = gr.Textbox(placeholder="…or type a command", show_label=False, scale=4)
            send = gr.Button("Send", variant="primary", scale=1)
        status = gr.Markdown()
        clear = gr.Button("Reset memory", size="sm")

        outputs = [chat, voice_out, box, mic, status]
        mic.stop_recording(handle, [mic, box, chat], outputs)
        send.click(handle, [mic, box, chat], outputs)
        box.submit(handle, [mic, box, chat], outputs)
        clear.click(reset, None, outputs)
    return app


def launch(share: bool = True, **kwargs):
    app = build_app()
    return app.queue().launch(share=share, **kwargs)


if __name__ == "__main__":
    launch()

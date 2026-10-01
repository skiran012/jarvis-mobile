"""Offline tests for the JARVIS loop — no GPU, microphone or API key needed.
Run:  python -m pytest -q
"""

from jarvis import skills
from jarvis.pipeline import Jarvis, strip_wake_word


class FakeBrain:
    def __init__(self):
        self.seen = []

    def think(self, text):
        self.seen.append(text)
        return f"echo: {text}", ["get_datetime"]

    def reset(self):
        self.seen.clear()


def make(transcript="Jarvis, what time is it?"):
    brain = FakeBrain()
    j = Jarvis(brain=brain, transcribe=lambda p: transcript, speak=lambda t: "reply.mp3")
    return j, brain


def test_wake_word_is_stripped():
    assert strip_wake_word("Hey Jarvis, open notes") == (True, "open notes")
    assert strip_wake_word("what's up") == (False, "what's up")


def test_voice_turn_runs_full_loop():
    j, brain = make()
    r = j.turn(audio_path="clip.wav")
    assert brain.seen == ["what time is it?"]
    assert r.reply == "echo: what time is it?" and r.audio_path == "reply.mp3"
    assert r.tools_used == ["get_datetime"]


def test_text_turn_skips_stt_and_wake_word():
    j, brain = make()
    r = j.turn(text="Jarvis status report")
    assert brain.seen == ["Jarvis status report"] and not r.skipped


def test_empty_input_is_skipped():
    j, _ = make(transcript="")
    assert j.turn(audio_path="silence.wav").skipped


def test_calculator_is_safe():
    assert skills.calculate("2^10") == "2^10 = 1024"
    assert "Could not" in skills.calculate("__import__('os').system('ls')")


def test_notes_roundtrip(tmp_path):
    skills.LTM.path = str(tmp_path / "m.json")
    skills.LTM.data = {"notes": [], "reminders": []}
    skills.save_note("parking on level B2")
    assert "B2" in skills.list_notes()


def test_tool_schemas_match_registry():
    assert {t["name"] for t in skills.TOOLS} == set(skills.REGISTRY)

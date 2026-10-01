"""Entry point for Hugging Face Spaces or local runs:  python app.py"""
from jarvis.app import build_app

if __name__ == "__main__":
    build_app().queue().launch()

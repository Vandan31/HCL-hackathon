"""
COMPONENT : tts
PURPOSE   : Speak every demo answer once ahead of time, so on stage the voice plays instantly from the disk cache.
INPUTS    : src/ui/mock/ask_fixtures.json (gu + hi answers and refusals); later, the real demo answers
OUTPUTS   : WAV files in config.tts.CACHE_DIR, plus a timing line per answer
DEPENDS ON: src/tts/engine.py, config/tts.py
PANEL NOTE: The demo never waits on the model: answers we will show are pre-spoken; anything new is made live.

Run (repo root, TTS virtual environment):  C:\\Users\\vaidu\\indic-tts\\.venv\\Scripts\\python -m src.tts.pregenerate
"""
import json
import time
from pathlib import Path

from config.tts import DEFAULT_SPEAKER
from src.tts.engine import TTSEngine

FIXTURES = Path(__file__).resolve().parents[1] / "ui" / "mock" / "ask_fixtures.json"


def demo_texts(langs):
    """(lang, text) for every answer and refusal in the UI fixtures, for the languages we can speak."""
    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for lang in langs:
        for topic in fx["topics"]:
            yield lang, topic["answers"][lang]
        yield lang, fx["refusal"]["answers"][lang]


def main():
    engine = TTSEngine()
    for lang, text in demo_texts(engine.langs):
        t0 = time.perf_counter()
        _, hit = engine.synthesize(text, lang, DEFAULT_SPEAKER)
        print(f"{lang} {'cached' if hit else 'made'} in {time.perf_counter() - t0:.2f}s: {text[:40]}…", flush=True)


if __name__ == "__main__":
    main()

"""
COMPONENT : API
PURPOSE   : Store full /api/ask responses for the demo questions so the demo works with Wi-Fi or the LLM down.
INPUTS    : query text, a response dict; data/cache/demo_answers.json
OUTPUTS   : the stored response, or None
DEPENDS ON: config/api.py (CACHE_PATH, OFFLINE_MODE, RECORD_CACHE)
PANEL NOTE: Recorded from real runs (RECORD_CACHE=true), never hand-written, so offline answers are genuine.
"""
import json
import os
import re
import threading
import unicodedata

_SPACES = re.compile(r"\s+")


def normalise_query(q: str) -> str:
    """Same key for small typing differences: case, spacing, punctuation (incl. Hindi danda '।')."""
    q = unicodedata.normalize("NFC", q).casefold()
    # WHY: punctuation becomes a space, so "PM-Kisan" and "pm kisan" match.
    q = "".join(" " if unicodedata.category(ch).startswith("P") else ch for ch in q)
    return _SPACES.sub(" ", q).strip()


class AnswerCache:
    """A small JSON file of {normalised query: response}; whole file rewritten on each put."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        try:
            with open(path, encoding="utf-8") as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # FALLBACK: no cache yet (or a broken file) -> start empty; offline misses return passages.
            self._data = {}

    def get(self, query: str) -> dict | None:
        return self._data.get(normalise_query(query))

    def put(self, query: str, response: dict) -> None:
        with self._lock:
            self._data[normalise_query(query)] = response
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                # WHY: ensure_ascii=False keeps Gujarati/Tamil readable in the file for a human check.
                json.dump(self._data, f, ensure_ascii=False, indent=1)

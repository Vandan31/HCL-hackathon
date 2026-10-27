"""
COMPONENT : answer engine
PURPOSE   : Check that the LLM's answer is really in the asker's language before we send it.
INPUTS    : answer text, asker's lang + code_mixed, optional language detector (black box, src/lang)
OUTPUTS   : True / False
DEPENDS ON: src/lang/detect.py when merged (passed in as `detector`); Unicode script ranges otherwise
PANEL NOTE: LLMs sometimes drift to Hindi or English; a rule catches it and we refuse instead of mis-answering.
"""
import re
from typing import Callable

from config.answer import HINGLISH_MARKERS, HINGLISH_MIN_MARKERS

# WHY: Unicode blocks are fixed by the standard, so script detection is free and deterministic.
SCRIPT_RANGES = {"Deva": (0x0900, 0x097F), "Gujr": (0x0A80, 0x0AFF), "Taml": (0x0B80, 0x0BFF)}
EXPECTED_SCRIPT = {"hi": "Deva", "mr": "Deva", "gu": "Gujr", "ta": "Taml", "en": "Latn"}
CITE_RE = re.compile(r"\[S\d+\]")
WORD_RE = re.compile(r"[a-z]+")


def looks_hinglish(text: str) -> bool:
    """Latin script plus enough Hindi function words (ke, hai, liye...) to rule out plain English."""
    words = WORD_RE.findall(CITE_RE.sub("", text).lower())
    return dominant_script(text) == "Latn" and sum(w in HINGLISH_MARKERS for w in words) >= HINGLISH_MIN_MARKERS


def dominant_script(text: str) -> str | None:
    """Most frequent script among the letters in text (citation markers ignored); None if no letters."""
    counts: dict[str, int] = {}
    for ch in CITE_RE.sub("", text):
        cp = ord(ch)
        script = next((s for s, (lo, hi) in SCRIPT_RANGES.items() if lo <= cp <= hi), None)
        if script is None and ch.isascii() and ch.isalpha():
            script = "Latn"
        if script:
            counts[script] = counts.get(script, 0) + 1
    return max(counts, key=counts.get) if counts else None


def language_matches(answer_text: str, lang: str, code_mixed: bool,
                     detector: Callable[[str], dict] | None = None) -> bool:
    """True if the answer is in the asker's language (Hinglish = hi + code_mixed, Roman script)."""
    if lang == "hi" and code_mixed:
        # WHY: Hinglish answers keep scheme words in English, so detectors often call them English (seen live
        # 2026-10-27). Hindi function words in Latin script are the reliable signal; plain English has none.
        return looks_hinglish(answer_text)
    if detector is not None:
        # WHY: [S1] markers aren't words in any language; don't let them sway the detector.
        d = detector(CITE_RE.sub("", answer_text))
        # WHY: only the detector can tell Hindi from Marathi (same script) or English from Hinglish.
        return d["lang"] == lang and (lang != "hi" or d["code_mixed"] == code_mixed)
    # FALLBACK: src/lang not merged yet -> script check only. It cannot tell hi from mr, or en from Hinglish.
    expected = EXPECTED_SCRIPT.get(lang)
    return expected is None or dominant_script(answer_text) == expected

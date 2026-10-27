"""
COMPONENT : lang (language detection)
PURPOSE   : Tell which language a citizen's question is in, so we search and reply in that language.
INPUTS    : the question text (typed, or transcribed from voice)
OUTPUTS   : {"lang": "en"|"hi"|"gu", "script": "Latn"|"Deva"|"Gujr", "code_mixed": bool, "confidence": float}
DEPENDS ON: config/lang.py (all thresholds and word lists)
PANEL NOTE: Pure rules on Unicode scripts + a Hinglish word list: zero cost, <1 ms, fully explainable.
"""
import re

from config.lang import (
    DEFAULT_LANG,
    HINGLISH_MIN_RATIO,
    HINGLISH_MIN_WORDS,
    HINGLISH_WORDS,
    MIXED_SCRIPT_MIN_RATIO,
    SCRIPT_RANGES,
    SCRIPT_TO_LANG,
)

# Latin words: letters only, so "PM-Kisan" gives "pm" and "kisan".
_LATIN_WORD = re.compile(r"[A-Za-z]+")


def _script_of(ch):
    """Return the script code of one character, or None for digits, spaces and punctuation."""
    if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
        return "Latn"
    code = ord(ch)
    for script, (start, end) in SCRIPT_RANGES.items():
        if start <= code <= end:
            return script
    return None  # WHY: digits/punctuation say nothing about language, so they don't vote


def _count_scripts(text):
    """Count letters per script, e.g. {"Deva": 18, "Latn": 2}."""
    counts = {}
    for ch in text:
        script = _script_of(ch)
        if script:
            counts[script] = counts.get(script, 0) + 1
    return counts


def _hinglish_score(text):
    """Return (number of Hindi words, share of Hindi words) among the Latin-script words."""
    words = [w.lower() for w in _LATIN_WORD.findall(text)]
    if not words:
        return 0, 0.0
    hindi = sum(1 for w in words if w in HINGLISH_WORDS)
    return hindi, hindi / len(words)


def detect_language(text):
    """Detect the language of `text`. Matches the interface frozen in docs/COMPONENTS.md."""
    counts = _count_scripts(text or "")
    total = sum(counts.values())

    # FALLBACK: no letters at all ("", "123", "?") -> default language, zero confidence,
    # so the answer engine knows it's a guess.
    if total == 0:
        return {"lang": DEFAULT_LANG, "script": "Latn", "code_mixed": False, "confidence": 0.0}

    # The script with the most letters wins; its share of letters is our confidence.
    script = max(counts, key=counts.get)
    share = counts[script] / total

    if script == "Latn":
        # Latin text is English unless enough of its words are Hindi -> Hinglish
        # (Hindi written in Roman letters). We then reply in Hindi, in Roman script.
        hindi_words, ratio = _hinglish_score(text)
        if hindi_words >= HINGLISH_MIN_WORDS and ratio >= HINGLISH_MIN_RATIO:
            # PANEL: Why reply in Roman script? -> people who type Hinglish often can't read
            # Devanagari comfortably; we mirror how they wrote.
            return {"lang": "hi", "script": "Latn", "code_mixed": True,
                    "confidence": round(min(1.0, ratio * 2), 2)}
        return {"lang": SCRIPT_TO_LANG["Latn"], "script": "Latn", "code_mixed": False,
                "confidence": round(share * (1 - ratio), 2)}

    # Devanagari or Gujarati is the main script. Some Latin (scheme names like "PM") is normal;
    # a lot of Latin means the question mixes languages.
    latin_share = counts.get("Latn", 0) / total
    return {"lang": SCRIPT_TO_LANG[script], "script": script,
            "code_mixed": latin_share >= MIXED_SCRIPT_MIN_RATIO,
            "confidence": round(share, 2)}

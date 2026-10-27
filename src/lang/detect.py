"""
COMPONENT : lang (language detection)
PURPOSE   : Tell which language a citizen's question is in (typed or transcribed from speech),
            so we search and reply in that language.
INPUTS    : the question text; optionally Whisper's language guess when the question was spoken
OUTPUTS   : {"lang": ISO 639-1 code ("en","hi","gu","mr","ta",...), "script": ISO 15924 code,
             "code_mixed": bool, "confidence": float, "source": "rules"|"indiclid"|"whisper",
             "supported": bool (our documents/answer templates cover this language)}
DEPENDS ON: config/lang.py; optional fasttext-predict + IndicLID model files (rules-only without them)
PANEL NOTE: Three layers, cheapest first: Unicode script rules (free, <1 ms) settle most queries;
            the IndicLID model only judges scripts shared by several languages; for speech we
            reuse the language faster-whisper already detected instead of running another model.
"""
import logging
import os
import re

from config import lang as cfg

log = logging.getLogger(__name__)

# Latin words: letters only, so "PM-Kisan" gives "pm" and "kisan".
_LATIN_WORD = re.compile(r"[A-Za-z]+")


def _script_of(ch):
    """Return the script code of one character, or None for digits, spaces and punctuation."""
    if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
        return "Latn"
    code = ord(ch)
    for script, (start, end) in cfg.SCRIPT_RANGES.items():
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
    hindi = sum(1 for w in words if w in cfg.HINGLISH_WORDS)
    return hindi, hindi / len(words)


# ---------------------------------------------------------------- IndicLID model (lazy)
_models = None  # {"native": model, "roman": model} once loaded; {} if unavailable


def _lid_models():
    """Load both IndicLID fastText models on first use. Returns {} if they can't be loaded."""
    global _models
    if _models is not None:
        return _models
    _models = {}
    try:
        # fasttext-predict: prediction-only fastText build with Windows/Python 3.13 wheels.
        import fasttext
    except ImportError:
        # FALLBACK: package not installed -> rules only, the original detector.
        log.warning("fasttext not installed: language detection runs on rules only")
        return _models
    for key, path in (("native", cfg.LID_NATIVE_MODEL), ("roman", cfg.LID_ROMAN_MODEL)):
        if not os.path.exists(path):
            # FALLBACK: model files not downloaded (they aren't in git) -> rules only.
            log.warning("IndicLID model %s missing: language detection runs on rules only", path)
            _models = {}
            return _models
        _models[key] = fasttext.load_model(path)
    return _models


def reset_lid():
    """Forget the loaded models (tests use this after changing USE_LID or paths)."""
    global _models
    _models = None


def _lid_predict(text, script):
    """Ask IndicLID. Returns (iso_lang, probability) or None if the guess fails our guards."""
    # Checked per call (not at load) so USE_LID can be flipped live without reloading ~540 MB.
    if not cfg.USE_LID:
        return None
    models = _lid_models()
    if not models:
        return None
    # Guard: too few words carry too little signal ("apply online" -> romanised Gujarati, measured).
    if len(text.split()) < cfg.LID_MIN_WORDS:
        return None
    model = models["roman"] if script == "Latn" else models["native"]
    # fastText rejects newlines; Whisper transcripts and pasted text can contain them.
    labels, probs = model.predict(text.replace("\n", " "), k=1)
    if not labels:
        return None
    code = labels[0].replace("__label__", "").split("_")[0]  # "hin_Deva" -> "hin"
    iso = cfg.LID_TO_ISO.get(code)
    prob = float(probs[0])
    # Guard: ignore languages the model confuses with Hindi (Maithili, Kashmiri, ...) and
    # low-confidence guesses; the caller then keeps the rules' answer.
    if iso not in cfg.LID_ACCEPT or prob < cfg.LID_MIN_CONF:
        return None
    return iso, min(prob, 1.0)


# ---------------------------------------------------------------- main entry point
def _result(lang, script, code_mixed, confidence, source):
    """Build the output dict in the shape frozen in docs/COMPONENTS.md."""
    return {"lang": lang, "script": script, "code_mixed": code_mixed,
            "confidence": round(confidence, 2), "source": source,
            "supported": lang in cfg.DOC_LANGS}


def _detect_text(text):
    """Detect from the text alone: script rules, then IndicLID for shared scripts."""
    counts = _count_scripts(text)
    total = sum(counts.values())

    # FALLBACK: no letters at all ("", "123", "?") -> default language, zero confidence,
    # so the answer engine knows it's a guess.
    if total == 0:
        return _result(cfg.DEFAULT_LANG, "Latn", False, 0.0, "rules")

    # The script with the most letters wins; its share of letters is our confidence.
    script = max(counts, key=counts.get)
    share = counts[script] / total

    if script == "Latn":
        # Layer 1: Hinglish word list. WHY first: measured, IndicLID labels Hinglish "Maithili".
        hindi_words, ratio = _hinglish_score(text)
        if hindi_words >= cfg.HINGLISH_MIN_WORDS and ratio >= cfg.HINGLISH_MIN_RATIO:
            # PANEL: Why reply in Roman script? -> people who type Hinglish often can't read
            # Devanagari comfortably; we mirror how they wrote.
            return _result("hi", "Latn", True, min(1.0, ratio * 2), "rules")
        # Layer 2: IndicLID roman model: catches romanised Gujarati/Marathi/Tamil/... and English.
        guess = _lid_predict(text, "Latn")
        if guess:
            lang, prob = guess
            # An Indian language in Roman letters counts as code-mixed, like Hinglish.
            return _result(lang, "Latn", lang != "en", prob, "indiclid")
        # Nothing confirmed it: English is only the default for Roman letters, so cap the
        # confidence (a confident Whisper guess for a spoken query can then overrule it).
        return _result("en", "Latn", False,
                       min(share * (1 - ratio), cfg.LATIN_DEFAULT_CONF), "rules")

    # Native script. Some Latin (scheme names like "PM") is normal; a lot of Latin means the
    # question mixes languages.
    code_mixed = counts.get("Latn", 0) / total >= cfg.MIXED_SCRIPT_MIN_RATIO
    if script in cfg.AMBIGUOUS_SCRIPTS:
        # Devanagari could be Hindi or Marathi/Nepali; Bengali script could be Assamese.
        guess = _lid_predict(text, script)
        if guess:
            return _result(guess[0], script, code_mixed, guess[1], "indiclid")
    return _result(cfg.SCRIPT_TO_LANG[script], script, code_mixed, share, "rules")


def detect_language(text, speech_hint=None):
    """Detect the language of `text`. Matches the interface frozen in docs/COMPONENTS.md.

    speech_hint: for spoken questions, faster-whisper's guess as {"lang": "hi", "prob": 0.93}
                 (from `info.language`, `info.language_probability`). Omit for typed text.
    """
    result = _detect_text(text or "")
    if not speech_hint or not speech_hint.get("lang"):
        return result

    hint_lang, hint_prob = speech_hint["lang"], float(speech_hint.get("prob") or 0.0)
    if hint_lang == result["lang"]:
        # Speech and text agree: keep the text result, take the stronger confidence.
        result["confidence"] = round(max(result["confidence"], hint_prob), 2)
        return result
    # They disagree. Whisper wins only if it is very sure AND surer than the text detector.
    # WHY: a Devanagari transcript is hard evidence of Hindi even if Whisper said "ur".
    if hint_prob >= cfg.WHISPER_MIN_PROB and hint_prob > result["confidence"]:
        return _result(hint_lang, result["script"], result["code_mixed"], hint_prob, "whisper")
    return result

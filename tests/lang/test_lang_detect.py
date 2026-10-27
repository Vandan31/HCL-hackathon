"""
COMPONENT : lang (tests)
PURPOSE   : Prove detect_language() handles each language plus the tricky cases judges may try,
            with the IndicLID model on and off, and with a Whisper speech hint.
INPUTS    : hand-written example questions
OUTPUTS   : pass/fail
DEPENDS ON: src/lang/detect.py, config/lang.py (IndicLID tests skip if the model files are missing)
PANEL NOTE: Run `python -m pytest tests/lang -q` live to show detection is tested, not hoped for.
"""
import os

import pytest

from config import lang as cfg
from src.lang import detect
from src.lang.detect import detect_language

HAVE_LID = os.path.exists(cfg.LID_NATIVE_MODEL) and os.path.exists(cfg.LID_ROMAN_MODEL)
needs_lid = pytest.mark.skipif(not HAVE_LID, reason="IndicLID models not downloaded")


@pytest.fixture(params=["rules_only", "with_lid"])
def mode(request, monkeypatch):
    """Run a test twice: once rules-only (the FALLBACK path), once with IndicLID."""
    if request.param == "with_lid" and not HAVE_LID:
        pytest.skip("IndicLID models not downloaded")
    # USE_LID is read per call, so the loaded models are reused across tests (no reload).
    monkeypatch.setattr(cfg, "USE_LID", request.param == "with_lid")
    return request.param


# Cases both layers must get right: the model must never make these worse.
@pytest.mark.parametrize("text, lang, script, mixed", [
    # Plain languages
    ("What documents do I need for PM Awas Yojana?", "en", "Latn", False),
    ("प्रधानमंत्री आवास योजना के लिए कौन से दस्तावेज़ चाहिए?", "hi", "Deva", False),
    ("મને ખેડૂત તરીકે કઈ સહાય મળી શકે?", "gu", "Gujr", False),
    # Hinglish: Hindi words in Roman letters -> Hindi, Latin script, code-mixed
    ("PM awas yojana ke liye kaunse documents chahiye?", "hi", "Latn", True),
    ("mujhe kisan credit card kaise milega", "hi", "Latn", True),   # IndicLID alone: Maithili
    ("driving licence kaise banwaye?", "hi", "Latn", True),          # IndicLID alone: Maithili
    # English that mentions Hindi scheme names must stay English
    ("How to apply for PM Kisan Samman Nidhi", "en", "Latn", False),
    ("apply online", "en", "Latn", False),                           # IndicLID alone: Gujarati
    # Devanagari with a scheme name in English is still plain Hindi
    ("PM किसान का पैसा कब आएगा?", "hi", "Deva", False),              # IndicLID alone: Kashmiri
    # Mostly Latin letters with a Devanagari tail -> treated as Hinglish (reply in Roman Hindi)
    ("Ayushman Bharat card ke liye आवेदन कैसे करें", "hi", "Latn", True),
    # Mostly Devanagari with many English words -> Hindi, flagged code-mixed
    ("आयुष्मान भारत card online apply कैसे करें", "hi", "Deva", True),
    # Scripts used by one language only: certain from the script, no model needed
    ("எனக்கு விவசாய உதவித்தொகை கிடைக்குமா?", "ta", "Taml", False),
    ("ਕਿਸਾਨ ਸਨਮਾਨ ਨਿਧੀ ਲਈ ਕਿਵੇਂ ਅਪਲਾਈ ਕਰੀਏ?", "pa", "Guru", False),
])
def test_languages(mode, text, lang, script, mixed):
    r = detect_language(text)
    assert (r["lang"], r["script"], r["code_mixed"]) == (lang, script, mixed), r


# Cases only the model can solve: the rules alone would say Hindi / English.
@needs_lid
@pytest.mark.parametrize("text, lang, script, mixed", [
    ("मला शेतकरी म्हणून कोणती मदत मिळू शकते?", "mr", "Deva", False),   # Marathi, same script as Hindi
    ("mala shetkari mhanun kay madat milel?", "mr", "Latn", True),     # romanised Marathi
    ("mane kheduto mate kai yojana male?", "gu", "Latn", True),        # romanised Gujarati
    ("enakku vivasayi uthavi thogai kidaikuma", "ta", "Latn", True),   # romanised Tamil
])
def test_lid_only_cases(monkeypatch, text, lang, script, mixed):
    monkeypatch.setattr(cfg, "USE_LID", True)
    r = detect_language(text)
    assert (r["lang"], r["script"], r["code_mixed"], r["source"]) == (lang, script, mixed, "indiclid"), r


def test_rules_only_misses_marathi_honestly(monkeypatch):
    """Documents the known gap of the FALLBACK path: Marathi in Devanagari reads as Hindi."""
    monkeypatch.setattr(cfg, "USE_LID", False)
    assert detect_language("मला शेतकरी म्हणून कोणती मदत मिळू शकते?")["lang"] == "hi"


@pytest.mark.parametrize("text", ["", "   ", "12345", "???", None])
def test_no_letters_falls_back_with_zero_confidence(mode, text):
    r = detect_language(text)
    assert r["lang"] == "en" and r["confidence"] == 0.0


def test_missing_model_files_fall_back_to_rules(monkeypatch):
    monkeypatch.setattr(cfg, "USE_LID", True)
    monkeypatch.setattr(cfg, "LID_NATIVE_MODEL", "does/not/exist.bin")
    detect.reset_lid()
    r = detect_language("मला शेतकरी म्हणून कोणती मदत मिळू शकते?")
    assert (r["lang"], r["source"]) == ("hi", "rules")
    detect.reset_lid()


# ---- Speech: faster-whisper's own language guess as a hint
def test_whisper_hint_agreeing_raises_confidence(mode):
    r = detect_language("PM किसान का पैसा कब आएगा?", speech_hint={"lang": "hi", "prob": 0.99})
    assert r["lang"] == "hi" and r["confidence"] == 0.99


def test_devanagari_transcript_beats_unsure_whisper(mode):
    # Whisper says Urdu at 0.6 but wrote Devanagari: the script is stronger evidence.
    r = detect_language("प्रधानमंत्री आवास योजना के लिए कौन से दस्तावेज़ चाहिए?",
                        speech_hint={"lang": "ur", "prob": 0.6})
    assert (r["lang"], r["source"]) == ("hi", "rules" if mode == "rules_only" else "indiclid")


def test_confident_whisper_wins_on_ambiguous_short_text(mode):
    # 2-word romanised clip: text says English (low confidence), Whisper is sure it's Gujarati.
    r = detect_language("kem cho", speech_hint={"lang": "gu", "prob": 0.95})
    assert (r["lang"], r["source"]) == ("gu", "whisper")


def test_output_matches_interface(mode):
    r = detect_language("नमस्ते")
    assert set(r) == {"lang", "script", "code_mixed", "confidence", "source", "supported"}
    assert 0.0 <= r["confidence"] <= 1.0
    assert r["supported"] is True
    assert detect_language("எனக்கு உதவி வேண்டும்")["supported"] is False  # Tamil: no documents

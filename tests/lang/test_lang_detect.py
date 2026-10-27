"""
COMPONENT : lang (tests)
PURPOSE   : Prove detect_language() handles each language plus the tricky cases judges may try.
INPUTS    : hand-written example questions
OUTPUTS   : pass/fail
DEPENDS ON: src/lang/detect.py
PANEL NOTE: Run `python -m pytest tests/lang -q` live to show detection is tested, not hoped for.
"""
import pytest

from src.lang.detect import detect_language


@pytest.mark.parametrize("text, lang, script, mixed", [
    # Plain languages
    ("What documents do I need for PM Awas Yojana?", "en", "Latn", False),
    ("प्रधानमंत्री आवास योजना के लिए कौन से दस्तावेज़ चाहिए?", "hi", "Deva", False),
    ("મને ખેડૂત તરીકે કઈ સહાય મળી શકે?", "gu", "Gujr", False),
    # Hinglish: Hindi words in Roman letters -> Hindi, Latin script, code-mixed
    ("PM awas yojana ke liye kaunse documents chahiye?", "hi", "Latn", True),
    ("mujhe kisan credit card kaise milega", "hi", "Latn", True),
    # English that mentions Hindi scheme names must stay English
    ("How to apply for PM Kisan Samman Nidhi", "en", "Latn", False),
    ("apply online", "en", "Latn", False),
    # Devanagari with a scheme name in English is still plain Hindi
    ("PM किसान का पैसा कब आएगा?", "hi", "Deva", False),
    # Mostly Latin letters with a Devanagari tail -> treated as Hinglish (reply in Roman Hindi)
    ("Ayushman Bharat card ke liye आवेदन कैसे करें", "hi", "Latn", True),
    # Mostly Devanagari with many English words -> Hindi, flagged code-mixed
    ("आयुष्मान भारत card online apply कैसे करें", "hi", "Deva", True),
])
def test_languages(text, lang, script, mixed):
    r = detect_language(text)
    assert (r["lang"], r["script"], r["code_mixed"]) == (lang, script, mixed), r


@pytest.mark.parametrize("text", ["", "   ", "12345", "???", None])
def test_no_letters_falls_back_with_zero_confidence(text):
    r = detect_language(text)
    assert r["lang"] == "en" and r["confidence"] == 0.0


def test_output_matches_interface():
    r = detect_language("नमस्ते")
    assert set(r) == {"lang", "script", "code_mixed", "confidence"}
    assert 0.0 <= r["confidence"] <= 1.0

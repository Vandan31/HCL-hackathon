"""
COMPONENT : answer engine
PURPOSE   : Prove a reply in the wrong language is caught (incl. Hindi-for-Marathi, English-for-Hinglish).
INPUTS    : answer text, asker's lang + code_mixed, optional fake detector
OUTPUTS   : pass/fail
DEPENDS ON: src/answer/langcheck.py
PANEL NOTE: "Reply in the user's language" is a must-build, so we verify it with a rule, not trust.
"""
from src.answer.langcheck import dominant_script, language_matches


def test_scripts():
    assert [dominant_script(t) for t in ["नमस्ते", "નમસ્તે", "வணக்கம்", "hello", "123"]] == \
        ["Deva", "Gujr", "Taml", "Latn", None]


def test_citations_and_scheme_names_dont_flip_the_script():
    assert dominant_script("તમે PM-KISAN માટે અરજી કરી શકો છો [S1]") == "Gujr"


def test_tamil_answer_for_tamil_user():
    assert language_matches("உங்களுக்கு விண்ணப்பிக்கலாம் [S1]", "ta", False)


def test_english_answer_for_gujarati_user_fails():
    assert not language_matches("You can apply [S1]", "gu", False)


def test_hinglish_user_needs_latin():
    assert not language_matches("आप आवेदन कर सकते हैं", "hi", True)
    assert language_matches("Aap apply kar sakte hain [S1]", "hi", True)


def test_detector_catches_hindi_for_marathi():
    fake = lambda t: {"lang": "hi", "script": "Deva", "code_mixed": False, "confidence": 0.9}
    assert not language_matches("आप आवेदन कर सकते हैं", "mr", False, detector=fake)


def test_detector_catches_english_for_hinglish():
    fake = lambda t: {"lang": "en", "script": "Latn", "code_mixed": False, "confidence": 0.9}
    assert not language_matches("You can apply", "hi", True, detector=fake)


def test_detector_agrees():
    fake = lambda t: {"lang": "mr", "script": "Deva", "code_mixed": False, "confidence": 0.9}
    assert language_matches("तुम्ही अर्ज करू शकता", "mr", False, detector=fake)

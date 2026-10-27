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


# ---- Live finding 2026-10-27: real Hinglish answers carry many English words ----
LIVE_HINGLISH = ("PM-KISAN ke liye landholding farmer families eligible hoti hain, lekin yeh kuch exclusions "
                 "ke adheen (subject to exclusions) hai [S1].")


def test_english_heavy_hinglish_passes_even_if_detector_says_english():
    says_en = lambda t: {"lang": "en", "script": "Latn", "code_mixed": False, "confidence": 0.5}
    assert language_matches(LIVE_HINGLISH, "hi", True, detector=says_en)


def test_pure_english_for_hinglish_fails_with_detector():
    says_en = lambda t: {"lang": "en", "script": "Latn", "code_mixed": False, "confidence": 0.5}
    assert not language_matches("Landholding farmer families are eligible for PM-KISAN [S1].", "hi", True,
                                detector=says_en)


def test_pure_english_for_hinglish_fails_in_script_mode():
    assert not language_matches("Landholding farmer families are eligible for PM-KISAN [S1].", "hi", True)
    assert language_matches(LIVE_HINGLISH, "hi", True)


def test_detector_sees_text_without_citation_markers():
    seen = []
    def spy(t):
        seen.append(t)
        return {"lang": "mr", "script": "Deva", "code_mixed": False, "confidence": 0.9}
    language_matches("तुम्ही अर्ज करू शकता [S1][S2]", "mr", False, detector=spy)
    assert "[S" not in seen[0]

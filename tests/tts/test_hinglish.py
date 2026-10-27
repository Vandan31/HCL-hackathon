"""
COMPONENT : tts (tests)
PURPOSE   : Check the Hinglish -> Devanagari step: fixed word lists win over the model, acronyms are spelled,
            model junk is cleaned, words are cached, and the real model (if installed) handles the demo sentence.
INPUTS    : src/tts/hinglish.py, config/tts.py
OUTPUTS   : pass/fail
DEPENDS ON: standard library (a fake converter stands in for the model); real-model test skips without hindi-xlit
PANEL NOTE: The model misspelled "par" and "aur" in our first test; these tests keep the fixed list in front of it.

Run from the repo root:  python -m unittest discover -s tests/tts -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.tts.hinglish import HinglishConverter, load_xlit  # noqa: E402


class FakeModel:
    """Pretends to be hindi-xlit, including its habit of adding a zero-width non-joiner and a dangling halant."""
    def __init__(self):
        self.calls = []

    def __call__(self, word):
        self.calls.append(word)
        return {"income": "इनकम", "certificate": "सर्टिफिकेट", "aur": "अउर्‌"}.get(word, "?")


class TestHinglishConverter(unittest.TestCase):
    def test_fixed_words_beat_the_model(self):
        model = FakeModel()
        out = HinglishConverter(model).convert("PM Awas Yojana ke liye aur par chahiye")
        self.assertEqual(out, "पीएम आवास योजना के लिए और पर चाहिए")
        self.assertEqual(model.calls, [], "words in the fixed lists must never reach the model")

    def test_model_used_for_other_words_and_cleaned(self):
        model = FakeModel()
        conv = HinglishConverter(model)
        self.assertEqual(conv.convert("income certificate"), "इनकम सर्टिफिकेट")
        self.assertEqual(conv.word("xyzabc"), "?")   # a word in no list -> the model's output, as is
        self.assertNotIn("‌", HinglishConverter(lambda w: "अउर्‌").word("aurr"))
        self.assertEqual(HinglishConverter(lambda w: "अउर्‌").word("aurr"), "अउर")

    def test_acronyms_are_spelled(self):
        self.assertEqual(HinglishConverter(FakeModel()).convert("SC aur OBC"), "एस सी और ओ बी सी")

    def test_numbers_untouched_and_citations_removed(self):
        # Numbers/₹ are left for normalize() (spoken the Hindi way); the [S1] marker must go, not become "[?1]".
        self.assertEqual(HinglishConverter(FakeModel()).convert("₹6,000 [S1]."), "₹6,000.")

    def test_words_are_cached(self):
        model = FakeModel()
        conv = HinglishConverter(model)
        conv.convert("income income Income")
        self.assertEqual(model.calls, ["income"])

    def test_no_model_means_unavailable(self):
        self.assertFalse(HinglishConverter(None).available)


REAL = load_xlit()


@unittest.skipUnless(REAL, "hindi-xlit is not installed here")
class TestRealConverter(unittest.TestCase):
    def test_demo_sentence(self):
        out = HinglishConverter(REAL).convert(
            "PM Awas Yojana ke liye aam taur par Aadhaar card, income certificate aur bank account details chahiye.")
        self.assertEqual(out, "पीएम आवास योजना के लिए आम तौर पर आधार कार्ड, इनकम सर्टिफिकेट और बैंक अकाउंट डिटेल्स चाहिए.")


if __name__ == "__main__":
    unittest.main()

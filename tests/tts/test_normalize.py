"""
COMPONENT : tts (tests)
PURPOSE   : Check the text rules that make answers speakable: citations removed, numbers and ₹ as words,
            English terms in native script, Hinglish detected.
INPUTS    : src/tts/normalize.py, config/tts.py
OUTPUTS   : pass/fail
DEPENDS ON: Python standard library only (no models needed)
PANEL NOTE: Our first real test spoke "PM-KISAN" as silence; these tests keep that from coming back.

Run from the repo root:  python -m unittest discover -s tests/tts -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.tts import LATIN_WORDS, LETTER_NAMES, NUMBER_WORDS  # noqa: E402
from src.tts.normalize import is_speakable, normalize, number_to_words  # noqa: E402


class TestNumbers(unittest.TestCase):
    def test_tables_have_0_to_99(self):
        for lang, words in NUMBER_WORDS.items():
            self.assertEqual(len(words), 100, lang)
            self.assertEqual(len(set(words)), 100, f"{lang}: duplicate number word")

    def test_indian_system(self):
        self.assertEqual(number_to_words(6000, "hi"), "छह हज़ार")
        self.assertEqual(number_to_words(125000, "hi"), "एक लाख पच्चीस हज़ार")
        self.assertEqual(number_to_words(6000, "gu"), "છ હજાર")
        self.assertEqual(number_to_words(20_00_00_000, "gu"), "વીસ કરોડ")
        self.assertEqual(number_to_words(250, "hi"), "दो सौ पचास")

    def test_rupees_go_after_the_amount(self):
        self.assertEqual(normalize("₹6,000", "gu"), "છ હજાર રૂપિયા")
        self.assertEqual(normalize("₹1,25,000", "hi"), "एक लाख पच्चीस हज़ार रुपये")

    def test_decimal_and_percent(self):
        self.assertEqual(normalize("2.5%", "hi"), "दो दशमलव पाँच प्रतिशत")


class TestText(unittest.TestCase):
    def test_citations_removed(self):
        self.assertEqual(normalize("મળે છે [S1]. નથી [S2].", "gu"), "મળે છે. નથી.")

    def test_scheme_name_in_native_script(self):
        self.assertEqual(normalize("PM-KISAN", "gu"), "પીએમ કિસાન")
        self.assertEqual(normalize("PM-Kisan", "hi"), "पीएम किसान")

    def test_unknown_acronym_is_spelled_not_dropped(self):
        self.assertEqual(normalize("SC", "hi"), "एस सी")

    def test_no_latin_letters_left(self):
        out = normalize("PM Awas Yojana: Aadhaar, CSC, myscheme.gov.in, XYZ [S1]।", "hi")
        self.assertFalse(any("a" <= c.lower() <= "z" for c in out), out)
        self.assertNotIn("।", out)

    def test_hinglish_is_not_speakable_but_gujarati_is(self):
        self.assertFalse(is_speakable("PM awas yojana ke liye kaunse documents chahiye?"))
        self.assertTrue(is_speakable("PM-KISAN હેઠળ ખેડૂત પરિવારોને સહાય મળે છે."))

    def test_word_lists_cover_both_languages(self):
        self.assertEqual(set(LATIN_WORDS["gu"]), set(LATIN_WORDS["hi"]))
        for lang in ("gu", "hi"):
            self.assertEqual(len(LETTER_NAMES[lang]), 26, lang)

    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            normalize("வணக்கம்", "ta")


class TestEnglishAndHinglish(unittest.TestCase):
    """'en' mode: English and Hinglish, spoken by the en+hi model in Latin letters."""

    def test_english_numbers_indian_system(self):
        self.assertEqual(normalize("₹6,000", "en"), "six thousand rupees")
        self.assertEqual(normalize("₹1,25,000", "en"), "one lakh twenty five thousand rupees")
        self.assertEqual(normalize("21", "en"), "twenty one")

    def test_scheme_name_and_acronyms(self):
        self.assertEqual(normalize("PM-KISAN", "en"), "P M Kisan")
        self.assertEqual(normalize("SC, OBC and PMAY", "en"), "S C, O B C and P M A Y")
        self.assertEqual(normalize("myscheme.gov.in", "en"), "my scheme dot gov dot in")

    def test_hinglish_words_kept(self):
        self.assertEqual(normalize("PM Awas Yojana ke liye documents chahiye [S1].", "en"),
                         "P M Awas Yojana ke liye documents chahiye.")


if __name__ == "__main__":
    unittest.main()

"""
COMPONENT : eligibility (tests)
PURPOSE   : Prove the rules engine gives the right verdict, asks the right next question, and never guesses.
INPUTS    : src/eligibility/mock_schemes.json (MOCK criteria), config/eligibility.py
OUTPUTS   : pass/fail
DEPENDS ON: Python standard library only
PANEL NOTE: Eligibility is the highest-stakes output, so every verdict path has a test.

Run from the repo root:  python -m unittest discover -s tests/eligibility -v
"""
import sys
import unittest
from pathlib import Path

# WHY: lets the test import src/ and config/ when run from any folder, with no package install.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.eligibility import FIELD_QUESTIONS  # noqa: E402
from src.eligibility.rules import next_question  # noqa: E402

KISAN_ALL_MET = {"occupation": "farmer", "land_owner": True, "income_tax_payer": False, "govt_employee": False}


class TestVerdicts(unittest.TestCase):
    def test_no_answers_asks_first_rule(self):
        r = next_question("pm-kisan", {})
        self.assertEqual(r["verdict"], "need_more_info")
        self.assertEqual(r["question"]["field"], "occupation")
        self.assertTrue(all(c["status"] == "unknown" for c in r["checklist"]))

    def test_all_met_is_likely_eligible(self):
        r = next_question("pm-kisan", KISAN_ALL_MET)
        self.assertEqual(r["verdict"], "likely_eligible")
        self.assertIsNone(r["question"])

    def test_one_failed_rule_stops_and_says_not_eligible(self):
        r = next_question("pm-kisan", {"occupation": "farmer", "income_tax_payer": True})
        self.assertEqual(r["verdict"], "not_eligible")
        self.assertIsNone(r["question"])   # STOP_ON_FIRST_FAIL: no pointless questions after a clear "no"

    def test_next_question_skips_answered_fields(self):
        r = next_question("pm-kisan", {"occupation": "farmer"})
        self.assertEqual(r["question"]["field"], "land_owner")


class TestAnswerTypes(unittest.TestCase):
    def test_string_answers_from_a_form_are_converted(self):
        r = next_question("atal-pension", {"age": "30", "has_bank_account": "true", "income_tax_payer": "false"})
        self.assertEqual(r["verdict"], "likely_eligible")

    def test_age_range_upper_bound(self):
        r = next_question("atal-pension", {"age": 45})
        self.assertEqual([c["status"] for c in r["checklist"]][:2], ["met", "not_met"])
        self.assertEqual(r["verdict"], "not_eligible")

    def test_unreadable_answer_is_unknown_not_guessed(self):
        r = next_question("atal-pension", {"age": "abc"})
        self.assertEqual(r["checklist"][0]["status"], "unknown")
        self.assertNotEqual(r["verdict"], "not_eligible")
        self.assertEqual(r["question"]["field"], "has_bank_account")   # doesn't loop on the same question


class TestFallbacks(unittest.TestCase):
    def test_rule_without_a_question_stays_unknown(self):
        # bpl_household has no entry in FIELD_QUESTIONS on purpose: it must end as "verify at office".
        answers = {"gender": "female", "age": 30, "lpg_connection_at_home": False}
        r = next_question("pm-ujjwala", answers)
        self.assertEqual(r["verdict"], "need_more_info")
        self.assertIsNone(r["question"])
        self.assertEqual(r["checklist"][-1]["status"], "unknown")

    def test_unknown_scheme_raises(self):
        with self.assertRaises(KeyError):
            next_question("no-such-scheme", {})

    def test_max_questions_stops_asking(self):
        from config import eligibility as cfg
        from src.eligibility import rules
        old = rules.MAX_QUESTIONS
        rules.MAX_QUESTIONS = 1
        try:
            r = next_question("pm-kisan", {"occupation": "farmer"})
            self.assertIsNone(r["question"])
        finally:
            rules.MAX_QUESTIONS = old
        self.assertEqual(cfg.MAX_QUESTIONS, old)


class TestLanguages(unittest.TestCase):
    def test_gujarati_question_and_checklist(self):
        r = next_question("pm-kisan", {}, lang="gu")
        self.assertEqual(r["question"]["text"], FIELD_QUESTIONS["occupation"]["text"]["gu"])
        self.assertEqual(r["question"]["options"][0]["label"], "ખેડૂત")
        self.assertEqual(r["checklist"][0]["criterion"], "ખેડૂત પરિવાર હોવો જોઈએ")

    def test_missing_translation_falls_back_to_english(self):
        r = next_question("atal-pension", {}, lang="gu")
        self.assertEqual(r["checklist"][0]["criterion"], "Age must be at least 18")
        r = next_question("pm-kisan", {}, lang="hinglish")
        self.assertEqual(r["question"]["text"], FIELD_QUESTIONS["occupation"]["text"]["en"])

    def test_every_question_translated(self):
        for field, q in FIELD_QUESTIONS.items():
            self.assertEqual(set(q["text"]), {"en", "hi", "gu"}, field)
            for o in q["options"]:
                self.assertEqual(set(o["label"]), {"en", "hi", "gu"}, f"{field}={o['value']}")


if __name__ == "__main__":
    unittest.main()

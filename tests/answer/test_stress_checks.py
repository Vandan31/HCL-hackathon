"""
COMPONENT : answer engine (stress test tooling)
PURPOSE   : Prove the stress-test grader passes/fails cases correctly, so its live results can be trusted.
INPUTS    : fake case specs + fake answer() results
OUTPUTS   : pass/fail
DEPENDS ON: scripts/stress_answer.py
PANEL NOTE: A grader that can't fail is worthless; these tests show it fails for the right reasons.
"""
from scripts.stress_answer import grade, percentile

ANS = {"refused": False, "refusal_reason": None, "answer": "₹6,000 per year [S1]",
       "citations": [{"id": "S1"}]}
REF = {"refused": True, "refusal_reason": "not_in_documents", "answer": "template", "citations": []}


def test_answer_case_passes():
    assert grade({"expect": "answer", "must_cite": ["S1"], "expect_any": ["6,000", "6000"]}, ANS) == []


def test_answer_case_fails_when_refused():
    assert grade({"expect": "answer"}, REF) == ["expected an answer, got refusal (not_in_documents)"]


def test_missing_expected_content_fails():
    assert grade({"expect": "answer", "expect_any": ["2,000"]}, ANS) == ["none of ['2,000'] in answer"]


def test_wrong_citation_fails():
    assert grade({"expect": "answer", "must_cite": ["S3"]}, ANS) == ["did not cite S3"]


def test_forbidden_text_fails_even_when_refused_flag_ok():
    assert grade({"expect": "any", "forbid": ["50,000"]}, {**ANS, "answer": "you get 50,000 [S1]"}) == \
        ["forbidden text '50,000' in answer"]


def test_refuse_case():
    assert grade({"expect": "refuse"}, REF) == []
    assert grade({"expect": "refuse"}, ANS) == ["expected a refusal, got an answer"]
    assert grade({"expect": "low_score"}, {**REF, "refusal_reason": "low_score"}) == []


def test_percentile():
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5.5
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 9.55

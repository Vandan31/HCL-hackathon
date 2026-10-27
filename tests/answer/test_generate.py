"""
COMPONENT : answer engine
PURPOSE   : Prove answer() applies every rule in order: score gate, retry budget, refusal, citation and
            language checks, and builds source cards only for cited passages.
INPUTS    : fake LLM (queued replies/exceptions), chunks, lang_info
OUTPUTS   : pass/fail
DEPENDS ON: src/answer/generate.py
PANEL NOTE: Rules gate every answer; the LLM only writes. Each rule has a test here.
"""
import json

import pytest

from src.answer.generate import answer
from src.answer.llm_pool import LLMCallFailed, LLMUnavailable
from src.answer.refusals import TEMPLATES


class FakeLLM:
    """Returns queued replies in order; an Exception in the queue is raised instead."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def __call__(self, prompt):
        self.calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r, "gemini#0"


def reply(answer_text, cited=("S1",), answerable=True):
    return json.dumps({"answer": answer_text, "cited": list(cited), "answerable": answerable}, ensure_ascii=False)


def chunk(cid, score=0.8, lang="en"):
    return {"chunk_id": cid, "scheme_id": "pm-kisan", "scheme_name": "PM-KISAN", "section": "eligibility",
            "text": f"passage {cid}", "lang": lang, "source_url": "u", "score": score}


GU = {"lang": "gu", "script": "Gujr", "code_mixed": False, "confidence": 0.9}
MR = {"lang": "mr", "script": "Deva", "code_mixed": False, "confidence": 0.9}
TA = {"lang": "ta", "script": "Taml", "code_mixed": False, "confidence": 0.9}
HINGLISH = {"lang": "hi", "script": "Latn", "code_mixed": True, "confidence": 0.9}
GU_TEXT = "તમે અરજી કરી શકો છો [S1]"


def test_low_score_refuses_without_calling_llm():
    llm = FakeLLM()
    r = answer("q", GU, [chunk("a", score=0.1)], llm=llm)
    assert r["refused"] and r["refusal_reason"] == "low_score" and llm.calls == 0
    assert r["answer"] == TEMPLATES["gu"]


def test_no_chunks_refuses_low_score():
    r = answer("q", GU, [], llm=FakeLLM())
    assert r["refusal_reason"] == "low_score"


def test_happy_path_gujarati():
    tr = {("a", "gu"): "ગુજરાતી અનુવાદ"}
    r = answer("q", GU, [chunk("a", score=0.82)], llm=FakeLLM(reply(GU_TEXT)), translations=tr)
    assert r["refused"] is False and r["refusal_reason"] is None
    assert r["answer"] == GU_TEXT and r["lang"] == "gu"
    assert r["citations"][0]["translation"] == "ગુજરાતી અનુવાદ" and r["citations"][0]["translation_lang"] == "gu"
    assert r["confidence"] == 0.82 and r["provider"] == "gemini#0"


def test_only_cited_chunks_become_citations():
    r = answer("q", GU, [chunk("a"), chunk("b"), chunk("c")],
               llm=FakeLLM(reply("તમે અરજી કરી શકો છો [S2]", cited=["S2"])))
    assert [c["chunk_id"] for c in r["citations"]] == ["b"] and r["citations"][0]["id"] == "S2"


def test_bad_json_retried_once_then_bad_output():
    llm = FakeLLM("garbage", "still garbage")
    r = answer("q", GU, [chunk("a")], llm=llm)
    assert r["refusal_reason"] == "bad_output" and llm.calls == 2


def test_bad_json_then_good_output_succeeds():
    llm = FakeLLM("garbage", reply(GU_TEXT))
    assert answer("q", GU, [chunk("a")], llm=llm)["refused"] is False and llm.calls == 2


def test_call_failed_then_success_uses_retry():
    llm = FakeLLM(LLMCallFailed("gemini#0: HTTP 429"), reply(GU_TEXT))
    assert answer("q", GU, [chunk("a")], llm=llm)["refused"] is False and llm.calls == 2


def test_two_call_failures_raise_unavailable():
    llm = FakeLLM(LLMCallFailed("x"), LLMCallFailed("y"))
    with pytest.raises(LLMUnavailable):
        answer("q", GU, [chunk("a")], llm=llm)
    assert llm.calls == 2


def test_pool_unavailable_propagates():
    with pytest.raises(LLMUnavailable):
        answer("q", GU, [chunk("a")], llm=FakeLLM(LLMUnavailable("none")))


def test_not_answerable_uses_template_in_input_language():
    r = answer("q", MR, [chunk("a")], llm=FakeLLM(reply("काहीही", cited=[], answerable=False)))
    assert r["answer"] == TEMPLATES["mr"] and r["refusal_reason"] == "not_in_documents" and r["citations"] == []


def test_hinglish_refusal_is_hinglish():
    r = answer("q", HINGLISH, [chunk("a")], llm=FakeLLM(reply("x", cited=[], answerable=False)))
    assert r["answer"] == TEMPLATES["hinglish"]


def test_invalid_citation_refuses():
    r = answer("q", GU, [chunk("a")], llm=FakeLLM(reply("તમે અરજી કરી શકો છો [S4]", cited=["S4"])))
    assert r["refusal_reason"] == "invalid_citation"


def test_wrong_language_refuses_without_retry():
    llm = FakeLLM(reply("You can apply [S1]"))
    r = answer("q", TA, [chunk("a")], llm=llm)
    assert r["refusal_reason"] == "wrong_language" and r["answer"] == TEMPLATES["ta"] and llm.calls == 1


def test_detector_is_used_for_language_check():
    says_hindi = lambda t: {"lang": "hi", "script": "Deva", "code_mixed": False, "confidence": 0.9}
    r = answer("q", MR, [chunk("a")], llm=FakeLLM(reply("आप आवेदन कर सकते हैं [S1]")), detector=says_hindi)
    assert r["refusal_reason"] == "wrong_language"


# ---- Final-review fixes ----

class ProviderAwareLLM:
    """Fails on gemini unless told to avoid it, like a pool whose Gemini keys are all rate-limited."""

    def __init__(self, good_reply):
        self.good = good_reply
        self.avoided = []

    def __call__(self, prompt, avoid_provider=None):
        self.avoided.append(avoid_provider)
        if avoid_provider != "gemini":
            e = LLMCallFailed("gemini#0: HTTP 429")
            e.provider = "gemini"
            raise e
        return self.good, "groq#0"


def test_retry_goes_to_other_provider():
    llm = ProviderAwareLLM(reply(GU_TEXT))
    r = answer("q", GU, [chunk("a")], llm=llm)
    assert r["refused"] is False and r["provider"] == "groq#0" and llm.avoided == [None, "gemini"]


def test_missing_or_null_score_refuses_instead_of_crashing():
    for bad in ({k: v for k, v in chunk("a").items() if k != "score"}, {**chunk("a"), "score": None}):
        r = answer("q", GU, [bad], llm=FakeLLM())
        assert r["refusal_reason"] == "low_score"


def test_empty_reply_from_safety_block_is_bad_output():
    llm = FakeLLM("", "")
    assert answer("q", GU, [chunk("a")], llm=llm)["refusal_reason"] == "bad_output"

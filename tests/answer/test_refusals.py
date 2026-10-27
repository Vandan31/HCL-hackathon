"""
COMPONENT : answer engine
PURPOSE   : Prove refusals are fixed templates in the asker's language (incl. Hinglish), never LLM text.
INPUTS    : lang code, code_mixed flag, refusal reason
OUTPUTS   : pass/fail
DEPENDS ON: src/answer/refusals.py
PANEL NOTE: "Refuse clearly" is a must-build; these tests pin the wording source and the language routing.
"""
from src.answer.refusals import TEMPLATES, refusal, template_key


def test_hinglish_input_gets_hinglish_template():
    assert template_key("hi", True) == "hinglish"
    assert template_key("hi", False) == "hi"


def test_templates_exist_for_every_final_language():
    assert set(TEMPLATES) == {"en", "hi", "gu", "mr", "ta", "hinglish"}
    assert all("myscheme.gov.in" in t for t in TEMPLATES.values())


def test_refusal_shape():
    r = refusal("ta", False, "low_score")
    assert r == {"answer": TEMPLATES["ta"], "lang": "ta", "refused": True,
                 "refusal_reason": "low_score", "citations": [], "confidence": 0.0}


def test_unknown_lang_falls_back_to_english_template():
    assert refusal("xx", False, "low_score")["answer"] == TEMPLATES["en"]

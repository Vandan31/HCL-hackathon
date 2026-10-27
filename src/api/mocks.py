"""
COMPONENT : API
PURPOSE   : Fixture responses shaped exactly like the frozen contract, so the UI can be built before the AI exists.
INPUTS    : the request query / scheme_id
OUTPUTS   : dicts matching POST /api/ask and POST /api/eligibility responses
DEPENDS ON: config/api.py (MOCK_REFUSAL_KEYWORDS)
PANEL NOTE: Lets four people build in parallel; deleted from the request path when USE_MOCKS=false.
"""
# MOCK: everything in this file is fixture data, not real retrieval or LLM output.
from config.api import MOCK_REFUSAL_KEYWORDS

# MOCK: passage text paraphrased for testing only; real text comes from data/schemes/ (Jaya's component).
_PM_KISAN_CITATION = {
    "id": "S1",
    "chunk_id": "pm-kisan#eligibility#en#0",
    "scheme_name": "PM-KISAN",
    "passage": "MOCK passage: landholding farmer families are eligible, subject to exclusions.",
    "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan",
}


def mock_ask(query: str) -> dict:
    """Return a canned answer, or a canned refusal if the query hits a refusal keyword."""
    q = query.lower()
    # WHY: gives the UI a refusal path to render (PLAN §9.1 demo step 4: "Passport kaise banaye?").
    if any(word in q for word in MOCK_REFUSAL_KEYWORDS):
        return {
            "answer": "MOCK refusal: my scheme documents do not cover this. Please check myscheme.gov.in or visit your nearest CSC.",
            "lang": "en",
            "code_mixed": False,
            "refused": True,
            "citations": [],
            "confidence": 0.0,
        }
    return {
        "answer": "MOCK answer: landholding farmer families can apply for PM-KISAN [S1].",
        "lang": "en",
        "code_mixed": False,
        "refused": False,
        "citations": [_PM_KISAN_CITATION],
        "confidence": 0.8,
    }


_SCRIPT_TO_LANG = {"Deva": "hi", "Gujr": "gu", "Taml": "ta"}


def mock_detect(text: str) -> dict:
    """MOCK of src/lang detect_language (Vandan): script only, so it can't spot Marathi or Hinglish."""
    from src.answer.langcheck import dominant_script
    script = dominant_script(text) or "Latn"
    return {"lang": _SCRIPT_TO_LANG.get(script, "en"), "script": script, "code_mixed": False, "confidence": 0.5}


def mock_search(query: str, lang: str, k: int = 5) -> list[dict]:
    """MOCK of src/retrieval search (Vandan): always the same PM-KISAN passage, so the real LLM path can be tried."""
    return [{"chunk_id": "pm-kisan#eligibility#en#0", "scheme_id": "pm-kisan", "scheme_name": "PM-KISAN",
             "section": "eligibility", "lang": "en", "score": 0.8,
             "text": _PM_KISAN_CITATION["passage"], "source_url": _PM_KISAN_CITATION["source_url"]}]


def mock_eligibility(scheme_id: str, answers: dict) -> dict:
    """Ask one follow-up until 'occupation' is answered, then return a checklist (Vaidehi owns the real engine)."""
    if "occupation" not in answers:
        return {
            "question": {"field": "occupation", "text": "MOCK: What is your occupation?", "options": ["farmer", "other"]},
            "checklist": [{"criterion": "Landholding farmer family", "status": "unknown", "source": "S1"}],
            "verdict": "need_more_info",
        }
    met = answers["occupation"] == "farmer"
    return {
        "question": None,
        "checklist": [{"criterion": "Landholding farmer family", "status": "met" if met else "not_met", "source": "S1"}],
        "verdict": "likely_eligible" if met else "not_eligible",
    }

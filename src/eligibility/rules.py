"""
COMPONENT : eligibility
PURPOSE   : Decide, from a scheme's own written rules, whether a person looks eligible, and pick the one
            follow-up question that matters next.
INPUTS    : scheme_id, the answers given so far ({field: value}), language code
OUTPUTS   : {"question": {...} | None, "checklist": [...], "verdict": ...} (contract in docs/COMPONENTS.md)
DEPENDS ON: data/schemes/<id>.json "criteria" (Jaya, human-verified), config/eligibility.py
PANEL NOTE: The AI never decides eligibility. Transparent rules from the scheme's own text do, and an
            unanswered rule is shown as "verify at office", never guessed.
"""
import json

from config.eligibility import (
    DEFAULT_LANG, FIELD_QUESTIONS, MAX_QUESTIONS, MOCK_SCHEMES_FILE, SCHEMES_DIR,
    STOP_ON_FIRST_FAIL, USE_MOCK_SCHEMES,
)

MET, NOT_MET, UNKNOWN = "met", "not_met", "unknown"

# Comparison for each "op" a criterion may use. Inputs are already converted to the rule's type.
OPS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}

_cache = {}


def load_scheme(scheme_id: str) -> dict:
    """Return the scheme dict (id, name, source_url, criteria). Raises KeyError for an unknown id."""
    if scheme_id in _cache:
        return _cache[scheme_id]
    path = SCHEMES_DIR / f"{scheme_id}.json"
    # WHY: the real, human-checked file always wins; the mock only fills gaps while data is being collected.
    if path.exists():
        scheme = json.loads(path.read_text(encoding="utf-8"))
    elif USE_MOCK_SCHEMES:
        # MOCK: simplified criteria from src/eligibility/mock_schemes.json until data/schemes/ is filled.
        mock = json.loads(MOCK_SCHEMES_FILE.read_text(encoding="utf-8"))
        scheme = next((s for s in mock["schemes"] if s["id"] == scheme_id), None)
        if scheme is None:
            raise KeyError(f"unknown_scheme: {scheme_id}")
    else:
        raise KeyError(f"unknown_scheme: {scheme_id}")
    _cache[scheme_id] = scheme
    return scheme


def _coerce(answer, rule_value):
    """Convert an answer to the rule value's type ("45" -> 45, "true" -> True). Returns None if impossible."""
    # WHY: answers arrive from a browser form, often as strings; comparing "45" >= 18 would crash or lie.
    target = rule_value[0] if isinstance(rule_value, list) and rule_value else rule_value
    try:
        if isinstance(target, bool):   # check bool before int: in Python, True is also an int
            if isinstance(answer, bool):
                return answer
            text = str(answer).strip().lower()
            if text in ("true", "yes", "1"):
                return True
            if text in ("false", "no", "0"):
                return False
            return None
        if isinstance(target, (int, float)):
            return float(answer)
        return str(answer).strip().lower()
    except (TypeError, ValueError):
        return None


def evaluate(criterion: dict, answers: dict) -> str:
    """Status of one rule: met / not_met / unknown (field not answered, or answer unusable)."""
    field = criterion["field"]
    if field not in answers or answers[field] in (None, ""):
        return UNKNOWN
    value = _coerce(answers[field], criterion["value"])
    if value is None or criterion["op"] not in OPS:
        # FALLBACK: an answer we can't read, or a rule type we don't know -> "unknown", never a guess.
        return UNKNOWN
    rule = criterion["value"]
    if isinstance(rule, str):
        rule = rule.lower()
    elif isinstance(rule, list):
        rule = [r.lower() if isinstance(r, str) else r for r in rule]
    try:
        return MET if OPS[criterion["op"]](value, rule) else NOT_MET
    except TypeError:
        return UNKNOWN


def _pick(texts: dict, lang: str) -> str:
    """Text in the requested language, falling back to DEFAULT_LANG, then to whatever exists."""
    return texts.get(lang) or texts.get(DEFAULT_LANG) or next(iter(texts.values()), "")


def _criterion_text(criterion: dict, lang: str) -> str:
    texts = {k[len("text_"):]: v for k, v in criterion.items() if k.startswith("text_")}
    return _pick(texts, lang) or criterion["field"]


def _question(field: str, lang: str) -> dict:
    """The follow-up question for a field, in the user's language. options == [] means 'type a number'."""
    q = FIELD_QUESTIONS[field]
    return {
        "field": field,
        "text": _pick(q["text"], lang),
        "options": [{"value": o["value"], "label": _pick(o["label"], lang)} for o in q["options"]],
    }


def next_question(scheme_id: str, answers: dict, lang: str = DEFAULT_LANG) -> dict:
    """
    Evaluate every rule of the scheme against the answers so far, then return the next question to ask
    (or None when done), the checklist, and an overall verdict.
    """
    scheme = load_scheme(scheme_id)
    source = _pick(scheme.get("source_url", {}), lang)
    criteria = scheme.get("criteria", [])

    checklist = [
        {"criterion": _criterion_text(c, lang), "status": evaluate(c, answers), "source": source}
        for c in criteria
    ]
    statuses = [item["status"] for item in checklist]

    # WHY: one failed rule is enough to say "not eligible"; all met is only "likely", because the
    # department makes the final decision (PLAN §4.6).
    if NOT_MET in statuses:
        verdict = "not_eligible"
    elif statuses and all(s == MET for s in statuses):
        verdict = "likely_eligible"
    else:
        verdict = "need_more_info"

    question = None
    stop = (verdict == "not_eligible" and STOP_ON_FIRST_FAIL) or len(answers) >= MAX_QUESTIONS
    if not stop:
        # Ask about the first unanswered field we have a question for, in the order the scheme lists its rules.
        for c, status in zip(criteria, statuses):
            # FALLBACK: a field with no question in config stays "unknown" -> user verifies it at the office.
            if status == UNKNOWN and c["field"] not in answers and c["field"] in FIELD_QUESTIONS:
                question = _question(c["field"], lang)
                break

    return {"question": question, "checklist": checklist, "verdict": verdict}

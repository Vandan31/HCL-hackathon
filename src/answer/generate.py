"""
COMPONENT : answer engine
PURPOSE   : Turn the retrieved passages into an answer in the user's language with source cards, or refuse.
INPUTS    : question, lang_info from detect_language(), chunks from search(), an LLM callable (KeyPool.complete)
OUTPUTS   : {answer, lang, refused, refusal_reason, citations, confidence, provider}  (contract in COMPONENTS.md;
            "provider" is for the audit log only and is stripped by the API)
DEPENDS ON: src/answer/{refusals, translations, prompting, langcheck, llm_pool}.py, config/answer.py
PANEL NOTE: Rules gate every answer; the LLM only writes. Score gate, citation check and language check are code.
"""
from typing import Callable

from config.answer import MAX_RETRIES, MIN_SCORE
from src.answer.langcheck import language_matches
from src.answer.llm_pool import LLMCallFailed, LLMUnavailable
from src.answer.prompting import build_prompt, citations_valid, parse_llm_output
from src.answer.refusals import refusal, template_key
from src.answer.translations import build_citation


def answer(query: str, lang_info: dict, chunks: list[dict], llm: Callable[[str], tuple[str, str]],
           translations: dict | None = None, detector: Callable | None = None) -> dict:
    """Answer from the passages only; raises LLMUnavailable when no LLM reply could be obtained."""
    lang, code_mixed = lang_info["lang"], lang_info.get("code_mixed", False)

    def refuse(reason: str, provider: str | None) -> dict:
        return {**refusal(lang, code_mixed, reason), "provider": provider}

    # FALLBACK: nothing relevant retrieved -> refuse without spending an LLM call.
    if not chunks or chunks[0]["score"] < MIN_SCORE:
        return refuse("low_score", None)

    prompt = build_prompt(query, template_key(lang, code_mixed), chunks)
    parsed, provider, last_error = None, None, None
    # WHY: one shared budget for failed calls and unreadable replies keeps worst-case latency ≈ 2 × timeout.
    for _ in range(1 + MAX_RETRIES):
        try:
            text, provider = llm(prompt)
        except LLMCallFailed as e:
            last_error = e
            continue
        last_error = None
        parsed = parse_llm_output(text)
        if parsed is not None:
            break
    if parsed is None:
        if last_error is not None:
            # FALLBACK: every attempt failed at the provider -> API returns 503 with the source passages.
            raise LLMUnavailable(str(last_error))
        # FALLBACK: the model replied but never in the required JSON shape.
        return refuse("bad_output", provider)

    if not parsed["answerable"]:
        # WHY: the refusal text is our template, never the LLM's own wording.
        return refuse("not_in_documents", provider)
    if not citations_valid(parsed, len(chunks)):
        # FALLBACK: a cited id that wasn't retrieved means the answer can't be trusted.
        return refuse("invalid_citation", provider)
    if not language_matches(parsed["answer"], lang, code_mixed, detector):
        # FALLBACK: wrong language -> refuse, no retry (the retry budget is for failures, see §6 of the design).
        return refuse("wrong_language", provider)

    cited = sorted(set(parsed["cited"]), key=lambda s: int(s[1:]))
    citations = [build_citation(sid, chunks[int(sid[1:]) - 1], lang, code_mixed, translations or {})
                 for sid in cited]
    return {"answer": parsed["answer"], "lang": lang, "refused": False, "refusal_reason": None,
            "citations": citations, "confidence": chunks[0]["score"], "provider": provider}

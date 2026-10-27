"""
COMPONENT : API
PURPOSE   : The single HTTP entry point the UI talks to: ask a question, check eligibility, check health.
INPUTS    : JSON requests (contract in docs/COMPONENTS.md "Interfaces")
OUTPUTS   : JSON responses in the same contract
DEPENDS ON: config/api.py, config/answer.py; src/answer (answer engine); src/lang + src/retrieval (black boxes,
            MOCKed until merged); src/eligibility (MOCKed)
PANEL NOTE: Thin, stateless FastAPI layer, so it scales horizontally and every AI decision lives in a testable module.
Run       : USE_MOCKS=false .venv/bin/uvicorn src.api.main:app --reload   (then open http://127.0.0.1:8000/docs)
"""
import os
import time
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.answer import GEMINI_MODEL, GROQ_MODEL, KEY_COOLDOWN_S, LLM_TIMEOUT_S, TRANSLATIONS_PATH
from config.api import AUDIT_PATH, CACHE_PATH, CORS_ORIGINS, OFFLINE_MODE, RECORD_CACHE, USE_MOCKS
from src.answer.generate import answer as answer_fn
from src.answer.llm_pool import KeyPool, LLMUnavailable, entries_from_env, load_env_file
from src.answer.translations import build_citation, load_translations
from src.api.audit import write_audit
from src.api.cache import AnswerCache
from src.api.mocks import mock_ask, mock_detect, mock_eligibility, mock_search

try:
    from src.lang.detect import detect_language as detect
    # WHY: the real detector also checks the answer's language (it can tell Hindi from Marathi).
    DETECTOR = detect
except ImportError:
    # MOCK: src/lang not merged yet -> script-only detector; answer language check falls back to scripts.
    detect, DETECTOR = mock_detect, None
try:
    from src.retrieval.search import search
except ImportError:
    # MOCK: src/retrieval not merged yet -> one fixed PM-KISAN passage.
    search = mock_search

# WHY: built once at startup; keys come only from .env / environment, never from code or config.
load_env_file()
POOL = KeyPool(entries_from_env(os.environ, GEMINI_MODEL, GROQ_MODEL), KEY_COOLDOWN_S, timeout_s=LLM_TIMEOUT_S)
TRANSLATIONS = load_translations(TRANSLATIONS_PATH)
CACHE = AnswerCache(CACHE_PATH)

app = FastAPI(title="Yojana Saathi API")
# WHY: the UI is a static HTML page on a different origin/port, so the browser needs CORS to call us.
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

# The /api/ask response contract (docs/COMPONENTS.md); anything else answer() returns stays internal.
ASK_FIELDS = ("answer", "lang", "refused", "citations", "confidence")


class AskRequest(BaseModel):
    # WHY: defaults instead of required fields, so a missing query returns our 400 contract, not FastAPI's 422.
    query: str = ""
    session_id: str = ""


class EligibilityRequest(BaseModel):
    scheme_id: str
    answers: dict = {}
    lang: str = "en"


@app.get("/api/health")
def health():
    """Tell the UI (and judges) whether the index and LLM are ready."""
    # MOCK: index_chunks stays 0 until src/retrieval exposes its size.
    return {"ok": True, "index_chunks": 0, "llm": "up" if POOL.has_usable_key() else "down",
            "offline_mode": OFFLINE_MODE}


def _audit(lang_info: dict, chunks: list, refused: bool, reason, provider, latency_ms: int) -> None:
    """One audit line per question; never the question or answer text (see src/api/audit.py)."""
    try:
        write_audit(AUDIT_PATH, {"time": datetime.now(timezone.utc).isoformat(), "lang": lang_info["lang"],
                                 "code_mixed": lang_info.get("code_mixed", False),
                                 "chunk_ids": [c["chunk_id"] for c in chunks], "refused": refused,
                                 "refusal_reason": reason, "provider": provider, "latency_ms": latency_ms})
    except OSError:
        # FALLBACK: a full disk or read-only folder must never break the citizen's answer.
        pass


def _fallback_503(lang_info: dict, chunks: list) -> JSONResponse:
    """LLM unavailable: still show the source passages (same card shape as a normal answer)."""
    # FALLBACK: "AI summary unavailable" in the UI, but the official passages are still useful.
    passages = [build_citation(f"S{i}", c, lang_info["lang"], lang_info.get("code_mixed", False), TRANSLATIONS)
                for i, c in enumerate(chunks, start=1)]
    return JSONResponse(status_code=503, content={"error": "llm_unavailable", "fallback_passages": passages})


@app.post("/api/ask")
def ask(req: AskRequest):
    """Answer a scheme question in the user's language, with sources, or refuse."""
    if not req.query.strip():
        return JSONResponse(status_code=400, content={"error": "empty_query"})
    start = time.perf_counter()

    def ms() -> int:
        # WHY: latency is measured here so every answer (mock, cached or live) reports it the same way.
        return round((time.perf_counter() - start) * 1000)

    if USE_MOCKS:
        # MOCK: fixture answers so the UI can be built before the real pipeline is merged.
        return {**mock_ask(req.query), "latency_ms": ms()}
    if OFFLINE_MODE and (hit := CACHE.get(req.query)) is not None:
        # FALLBACK: Wi-Fi-off demo -> recorded real answer, no LLM call.
        return {**hit, "latency_ms": ms()}

    lang_info = detect(req.query)
    chunks = search(req.query, lang_info["lang"])
    if OFFLINE_MODE:
        # FALLBACK: offline and not recorded -> passages only (detect + search run locally).
        _audit(lang_info, chunks, True, "offline_cache_miss", None, ms())
        return _fallback_503(lang_info, chunks)
    try:
        result = answer_fn(req.query, lang_info, chunks, llm=POOL.complete,
                           translations=TRANSLATIONS, detector=DETECTOR)
    except LLMUnavailable:
        _audit(lang_info, chunks, True, "llm_unavailable", None, ms())
        return _fallback_503(lang_info, chunks)

    body = {k: result[k] for k in ASK_FIELDS} | {"code_mixed": lang_info.get("code_mixed", False)}
    if RECORD_CACHE and not result["refused"]:
        CACHE.put(req.query, body)
    _audit(lang_info, chunks, result["refused"], result["refusal_reason"], result["provider"], ms())
    return {**body, "latency_ms": ms()}


@app.post("/api/eligibility")
def eligibility(req: EligibilityRequest):
    """Return the next follow-up question plus the checklist so far."""
    # MOCK: Vaidehi's rules engine (src/eligibility/rules.py) replaces this at integration.
    return mock_eligibility(req.scheme_id, req.answers)

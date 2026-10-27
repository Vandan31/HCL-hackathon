"""
COMPONENT : API
PURPOSE   : The single HTTP entry point the UI talks to: ask a question, check eligibility, check health.
INPUTS    : JSON requests (contract in docs/COMPONENTS.md "Interfaces")
OUTPUTS   : JSON responses in the same contract
DEPENDS ON: config/api.py; src/api/mocks.py now; src/lang, src/retrieval, src/answer, src/eligibility at integration
PANEL NOTE: Thin, stateless FastAPI layer, so it scales horizontally and every AI decision lives in a testable module.
Run       : .venv/bin/uvicorn src.api.main:app --reload   (then open http://127.0.0.1:8000/docs)
"""
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.api import CORS_ORIGINS, OFFLINE_MODE
from src.api.mocks import mock_ask, mock_eligibility

app = FastAPI(title="Yojana Saathi API")
# WHY: the UI is a static HTML page on a different origin/port, so the browser needs CORS to call us.
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


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
    # MOCK: no index or LLM is wired yet, so report 0 chunks and llm "down" honestly.
    return {"ok": True, "index_chunks": 0, "llm": "down", "offline_mode": OFFLINE_MODE}


@app.post("/api/ask")
def ask(req: AskRequest):
    """Answer a scheme question in the user's language, with sources, or refuse."""
    if not req.query.strip():
        return JSONResponse(status_code=400, content={"error": "empty_query"})
    start = time.perf_counter()
    # MOCK: fixture answer. At integration (PLAN §5.3, 2:45) the USE_MOCKS=False branch will call
    # detect_language -> search -> answer and write the audit log line; until then both paths use the mock.
    result = mock_ask(req.query)
    # WHY: latency is measured here so every answer (mock or real) reports it the same way for the eval table.
    result["latency_ms"] = round((time.perf_counter() - start) * 1000)
    return result


@app.post("/api/eligibility")
def eligibility(req: EligibilityRequest):
    """Return the next follow-up question plus the checklist so far."""
    # MOCK: Vaidehi's rules engine (src/eligibility/rules.py) replaces this at integration.
    return mock_eligibility(req.scheme_id, req.answers)

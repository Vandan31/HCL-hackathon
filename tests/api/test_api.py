"""
COMPONENT : API
PURPOSE   : Prove the HTTP contract in docs/COMPONENTS.md ("Interfaces") holds, so the UI can build on it.
INPUTS    : HTTP requests via FastAPI's TestClient (no server needed)
OUTPUTS   : pass/fail per contract rule
DEPENDS ON: src/api/main.py
PANEL NOTE: The API shape is frozen; these tests break the moment anyone changes it by accident.
"""
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

# WHY: the exact keys the UI reads, copied from the frozen contract in docs/COMPONENTS.md.
ASK_KEYS = {"answer", "lang", "code_mixed", "refused", "citations", "confidence", "latency_ms"}
CITATION_KEYS = {"id", "chunk_id", "scheme_name", "passage", "source_url"}


def test_health_reports_contract_fields():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert set(r.json()) == {"ok", "index_chunks", "llm", "offline_mode"}
    assert r.json()["llm"] in ("up", "down")


def test_ask_returns_answer_with_citations():
    r = client.post("/api/ask", json={"query": "PM Kisan ke liye kaun eligible hai?", "session_id": "t1"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == ASK_KEYS
    assert body["refused"] is False
    assert body["citations"], "an answer must carry at least one source"
    assert set(body["citations"][0]) == CITATION_KEYS


def test_ask_empty_query_is_400():
    r = client.post("/api/ask", json={"query": "   ", "session_id": "t1"})
    assert r.status_code == 400
    assert r.json() == {"error": "empty_query"}


def test_ask_missing_query_is_400_not_422():
    # WHY: the contract promises {"error": "empty_query"}, not FastAPI's default 422 validation blob.
    r = client.post("/api/ask", json={"session_id": "t1"})
    assert r.status_code == 400
    assert r.json() == {"error": "empty_query"}


def test_ask_out_of_scope_query_is_refused_without_citations():
    # WHY: the UI needs a refusal state to build against before the real answer engine exists.
    r = client.post("/api/ask", json={"query": "Passport kaise banaye?", "session_id": "t1"})
    assert r.status_code == 200
    body = r.json()
    assert body["refused"] is True
    assert body["citations"] == []
    assert body["answer"]


def test_eligibility_returns_question_checklist_verdict():
    r = client.post("/api/eligibility", json={"scheme_id": "pm-kisan", "answers": {}, "lang": "en"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"question", "checklist", "verdict"}
    assert body["verdict"] in ("likely_eligible", "not_eligible", "need_more_info")

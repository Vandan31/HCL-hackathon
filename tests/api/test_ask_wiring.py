"""
COMPONENT : API
PURPOSE   : Prove /api/ask runs detect -> search -> answer when mocks are off, and every fallback path:
            LLM down -> 503 with passages, offline cache hit/miss, cache recording, health.
INPUTS    : HTTP requests via TestClient; fakes monkeypatched into src.api.main
OUTPUTS   : pass/fail
DEPENDS ON: src/api/main.py
PANEL NOTE: The demo survives a dead LLM or dead Wi-Fi; these tests prove each path.
"""
import json

import pytest
from fastapi.testclient import TestClient

import src.api.main as main
from src.answer.llm_pool import LLMUnavailable
from src.api.cache import AnswerCache

ASK_KEYS = {"answer", "lang", "code_mixed", "refused", "citations", "confidence", "latency_ms"}
CHUNK = {"chunk_id": "pm-kisan#elig#en#0", "scheme_id": "pm-kisan", "scheme_name": "PM-KISAN",
         "section": "eligibility", "text": "Landholding farmers", "lang": "en", "source_url": "u", "score": 0.8}
CITATION = {"id": "S1", "chunk_id": CHUNK["chunk_id"], "scheme_name": "PM-KISAN", "passage": "Landholding farmers",
            "source_url": "u", "passage_lang": "en", "translation": None, "translation_lang": None}
GOOD = {"answer": "તમે અરજી કરી શકો છો [S1]", "lang": "gu", "refused": False, "refusal_reason": None,
        "citations": [CITATION], "confidence": 0.8, "provider": "gemini#0"}


class FakePool:
    def __init__(self, usable=True):
        self.usable = usable

    def complete(self, prompt):
        raise AssertionError("tests use a fake answer(), the pool must not be called directly")

    def has_usable_key(self):
        return self.usable


@pytest.fixture
def wired(monkeypatch, tmp_path):
    """Mocks off; detect/search/answer replaced with fakes; audit + cache in tmp."""
    calls = {"answer": 0}

    def fake_answer(query, lang_info, chunks, llm, translations=None, detector=None):
        calls["answer"] += 1
        return dict(GOOD)

    monkeypatch.setattr(main, "USE_MOCKS", False)
    monkeypatch.setattr(main, "OFFLINE_MODE", False)
    monkeypatch.setattr(main, "RECORD_CACHE", False)
    monkeypatch.setattr(main, "detect", lambda q: {"lang": "gu", "script": "Gujr", "code_mixed": False, "confidence": 1})
    monkeypatch.setattr(main, "search", lambda q, lang, k=5: [CHUNK])
    monkeypatch.setattr(main, "answer_fn", fake_answer)
    monkeypatch.setattr(main, "POOL", FakePool())
    monkeypatch.setattr(main, "AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setattr(main, "CACHE", AnswerCache(str(tmp_path / "cache.json")))
    return {"client": TestClient(main.app), "calls": calls, "tmp": tmp_path}


def ask(client, q="PM કિસાન?"):
    return client.post("/api/ask", json={"query": q, "session_id": "s"})


def test_ask_happy_path_returns_contract_and_audits(wired):
    r = ask(wired["client"])
    assert r.status_code == 200
    body = r.json()
    assert set(body) == ASK_KEYS and "provider" not in body
    assert body["lang"] == "gu" and body["citations"] == [CITATION]
    line = json.loads((wired["tmp"] / "audit.jsonl").read_text(encoding="utf-8"))
    assert "query" not in line and "answer" not in line
    assert line["provider"] == "gemini#0" and line["chunk_ids"] == [CHUNK["chunk_id"]]


def test_ask_llm_unavailable_returns_503_with_passages(wired, monkeypatch):
    def down(*a, **k):
        raise LLMUnavailable("no keys")
    monkeypatch.setattr(main, "answer_fn", down)
    r = ask(wired["client"])
    assert r.status_code == 503
    body = r.json()
    assert body["error"] == "llm_unavailable"
    assert body["fallback_passages"][0]["passage"] == "Landholding farmers"
    assert "translation" in body["fallback_passages"][0]


def test_offline_mode_serves_cache_without_llm(wired, monkeypatch):
    stored = {k: v for k, v in GOOD.items() if k not in ("provider", "refusal_reason")} | {"code_mixed": False}
    wired_cache = main.CACHE
    wired_cache.put("PM કિસાન?", stored)
    monkeypatch.setattr(main, "OFFLINE_MODE", True)
    r = ask(wired["client"], "pm  કિસાન")
    assert r.status_code == 200 and r.json()["answer"] == GOOD["answer"]
    assert wired["calls"]["answer"] == 0


def test_offline_cache_miss_returns_503(wired, monkeypatch):
    monkeypatch.setattr(main, "OFFLINE_MODE", True)
    r = ask(wired["client"], "never cached")
    assert r.status_code == 503 and r.json()["fallback_passages"]
    assert wired["calls"]["answer"] == 0


def test_record_cache_saves_successful_answer(wired, monkeypatch):
    monkeypatch.setattr(main, "RECORD_CACHE", True)
    ask(wired["client"], "PM કિસાન?")
    assert main.CACHE.get("pm કિસાન")["answer"] == GOOD["answer"]


def test_health_reports_llm_down_when_no_keys(wired, monkeypatch):
    monkeypatch.setattr(main, "POOL", FakePool(usable=False))
    assert wired["client"].get("/api/health").json()["llm"] == "down"
    monkeypatch.setattr(main, "POOL", FakePool(usable=True))
    assert wired["client"].get("/api/health").json()["llm"] == "up"


# ---- Final-review fixes ----

def test_record_cache_also_saves_refusals_for_offline_demo(wired, monkeypatch):
    # Review #5: the planned refusal demo step must work with Wi-Fi off.
    refused = {**GOOD, "refused": True, "refusal_reason": "not_in_documents", "citations": [],
               "answer": "Mujhe yeh jaankari ... nahi mili", "provider": "groq#0"}
    monkeypatch.setattr(main, "answer_fn", lambda *a, **k: dict(refused))
    monkeypatch.setattr(main, "RECORD_CACHE", True)
    ask(wired["client"], "Passport kaise banaye?")
    monkeypatch.setattr(main, "OFFLINE_MODE", True)
    r = ask(wired["client"], "passport kaise banaye")
    assert r.status_code == 200 and r.json()["refused"] is True


def test_recorded_cache_is_gitignored():
    # Review #6: recorded queries are user text; they must never reach git.
    import subprocess
    rc = subprocess.run(["git", "check-ignore", "-q", "data/cache/demo_answers.json"]).returncode
    assert rc == 0


def test_use_mock_search_switch_forces_test_paragraph(monkeypatch):
    # WHY: after merging real retrieval, local UI testing on the smoke-test passage needs an explicit switch.
    import importlib
    import config.api
    from src.api import mocks
    monkeypatch.setenv("USE_MOCK_SEARCH", "true")
    importlib.reload(config.api)
    m = importlib.reload(main)
    try:
        assert m.search is mocks.mock_search
    finally:
        monkeypatch.delenv("USE_MOCK_SEARCH")
        importlib.reload(config.api)
        importlib.reload(main)


def test_startup_warms_up_detect_and_search(monkeypatch):
    # WHY: without warm-up the first citizen waits ~16 s (IndicLID) + the embedding model load (Vandan, D-012).
    calls = []
    monkeypatch.setattr(main, "USE_MOCKS", False)
    monkeypatch.setattr(main, "detect", lambda q: calls.append(("detect", q)) or {"lang": "en", "code_mixed": False})
    monkeypatch.setattr(main, "search", lambda q, lang, k=5: calls.append(("search", q, lang)) or [])
    with TestClient(main.app):
        pass
    assert ("detect", "warm up") in calls and ("search", "warm up", "en") in calls


def test_warm_up_failure_does_not_stop_the_server(monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("model missing")
    monkeypatch.setattr(main, "USE_MOCKS", False)
    monkeypatch.setattr(main, "detect", broken)
    monkeypatch.setattr(main, "search", broken)
    with TestClient(main.app) as c:
        assert c.get("/api/health").status_code == 200

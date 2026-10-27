"""
COMPONENT : answer engine
PURPOSE   : Prove the free-tier key pool rotates keys, rests rate-limited ones, falls back to Groq,
            and never leaks a key value.
INPUTS    : fake HTTP responses via httpx.MockTransport (no network), a fake clock
OUTPUTS   : pass/fail
DEPENDS ON: src/answer/llm_pool.py
PANEL NOTE: "What if the free tier runs out on stage?" -> these tests are the answer.
"""
import threading
from collections import Counter

import httpx
import pytest

from src.answer.llm_pool import (KeyEntry, KeyPool, LLMCallFailed, LLMUnavailable,
                                 entries_from_env, load_env_file)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _key_of(request: httpx.Request) -> str:
    # WHY: Gemini sends the key in x-goog-api-key, Groq as a Bearer token.
    return request.headers.get("x-goog-api-key") or request.headers["authorization"].removeprefix("Bearer ")


def make_pool(status_by_key=None, entries=None, clock=None, seen=None):
    """Pool whose fake server answers 'OK' unless status_by_key says otherwise for that key."""
    status_by_key = status_by_key or {}

    def handler(request):
        key = _key_of(request)
        if seen is not None:
            seen.append(request)
        status = status_by_key.get(key, 200)
        if isinstance(status, Exception):
            raise status
        if status != 200:
            return httpx.Response(status, text=f"error for key {key}")
        if request.url.host == "api.groq.com":
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})

    entries = entries or [KeyEntry("gemini", 0, "k1", "gm"), KeyEntry("gemini", 1, "k2", "gm"),
                          KeyEntry("groq", 0, "k3", "qm")]
    return KeyPool(entries, cooldown_s=60, clock=clock or FakeClock(), transport=httpx.MockTransport(handler))


def test_entries_from_env_strips_and_drops_empty():
    e = entries_from_env({"GEMINI_API_KEYS": " k1, k2 ,", "GROQ_API_KEYS": "k3"}, "gm", "qm")
    assert [(x.label, x.key) for x in e] == [("gemini#0", "k1"), ("gemini#1", "k2"), ("groq#0", "k3")]


def test_entries_from_env_accepts_numbered_vars():
    # WHY: Harsh's real .env uses GEMINI_API_KEY_1, _2 ...; both formats must work, in number order.
    env = {"GEMINI_API_KEY_2": "k2", "GEMINI_API_KEY_1": "k1", "GROQ_API_KEY_1": " k3 ", "GROQ_API_KEY_2": ""}
    e = entries_from_env(env, "gm", "qm")
    assert [(x.label, x.key) for x in e] == [("gemini#0", "k1"), ("gemini#1", "k2"), ("groq#0", "k3")]


def test_numbered_vars_sort_numerically_and_join_list_format():
    env = {f"GEMINI_API_KEY_{i}": f"n{i}" for i in (10, 2, 1)} | {"GEMINI_API_KEYS": "a"}
    assert [x.key for x in entries_from_env(env, "gm", "")] == ["a", "n1", "n2", "n10"]


def test_provider_with_empty_model_is_skipped():
    e = entries_from_env({"GEMINI_API_KEYS": "k1", "GROQ_API_KEYS": "k3"}, "gm", "")
    assert [x.provider for x in e] == ["gemini"]


def test_load_env_file_sets_missing_vars_only(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("# comment\n\nGEMINI_API_KEYS=a,b\nGROQ_API_KEYS=c\n", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.setenv("GROQ_API_KEYS", "already-set")
    load_env_file(str(p))
    import os
    assert os.environ["GEMINI_API_KEYS"] == "a,b"
    assert os.environ["GROQ_API_KEYS"] == "already-set"


def test_load_env_file_missing_is_noop(tmp_path):
    load_env_file(str(tmp_path / "nope.env"))


def test_round_robin_over_gemini_keys():
    pool = make_pool()
    assert [pool.complete("p") for _ in range(2)] == [("OK", "gemini#0"), ("OK", "gemini#1")]


def test_429_cools_key_and_next_call_uses_next_key():
    pool = make_pool({"k1": 429})
    with pytest.raises(LLMCallFailed):
        pool.complete("p")
    assert pool.complete("p")[1] == "gemini#1"
    assert pool.complete("p")[1] == "gemini#1"


def test_timeout_cools_key():
    pool = make_pool({"k1": httpx.ReadTimeout("slow")})
    with pytest.raises(LLMCallFailed):
        pool.complete("p")
    assert pool.complete("p")[1] == "gemini#1"


def test_malformed_success_body_is_a_failed_call():
    def handler(request):
        return httpx.Response(200, json={"unexpected": True})
    pool = KeyPool([KeyEntry("gemini", 0, "k1", "gm")], 60, clock=FakeClock(), transport=httpx.MockTransport(handler))
    with pytest.raises(LLMCallFailed):
        pool.complete("p")


def test_groq_used_only_when_all_gemini_cooling():
    pool = make_pool({"k1": 429, "k2": 429})
    for _ in range(2):
        with pytest.raises(LLMCallFailed):
            pool.complete("p")
    assert pool.complete("p")[1] == "groq#0"


def test_cooldown_expires_with_clock():
    clock = FakeClock()
    status = {"k1": 429}
    pool = make_pool(status, clock=clock)
    with pytest.raises(LLMCallFailed):
        pool.complete("p")
    assert pool.complete("p")[1] == "gemini#1"
    status.clear()
    clock.t += 61
    assert pool.complete("p")[1] == "gemini#0"


def test_401_disables_key_permanently():
    clock = FakeClock()
    pool = make_pool({"k1": 401}, clock=clock)
    with pytest.raises(LLMCallFailed):
        pool.complete("p")
    clock.t += 10_000
    assert [pool.complete("p")[1] for _ in range(2)] == ["gemini#1", "gemini#1"]


def test_all_keys_unusable_raises_unavailable():
    pool = make_pool({"k1": 429, "k2": 429, "k3": 429})
    for _ in range(3):
        with pytest.raises(LLMCallFailed):
            pool.complete("p")
    assert pool.has_usable_key() is False
    with pytest.raises(LLMUnavailable):
        pool.complete("p")


def test_empty_pool_is_unavailable():
    pool = KeyPool([], 60)
    assert pool.has_usable_key() is False
    with pytest.raises(LLMUnavailable):
        pool.complete("p")


def test_key_never_in_exception_repr_or_url():
    seen = []
    entry = KeyEntry("gemini", 0, "SECRETKEY", "gm")
    pool = make_pool({"SECRETKEY": 400}, entries=[entry], seen=seen)
    with pytest.raises(LLMCallFailed) as exc:
        pool.complete("p")
    assert "SECRETKEY" not in str(exc.value)
    assert "SECRETKEY" not in repr(entry)
    assert "SECRETKEY" not in str(seen[0].url)


def test_threads_share_pool_safely():
    pool = make_pool(entries=[KeyEntry("gemini", 0, "k1", "gm"), KeyEntry("gemini", 1, "k2", "gm")])
    labels, errors = [], []

    def worker():
        try:
            labels.append(pool.complete("p")[1])
        except Exception as e:  # noqa: BLE001 - any error fails the test below
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert Counter(labels) == {"gemini#0": 10, "gemini#1": 10}


# ---- Final-review fixes ----

def test_retry_avoids_failed_provider():
    # Review #1: Gemini down (429) must not cost the user a 503 when Groq is healthy.
    pool = make_pool({"k1": 429, "k2": 429})
    with pytest.raises(LLMCallFailed) as exc:
        pool.complete("p")
    assert exc.value.provider == "gemini"
    assert pool.complete("p", avoid_provider="gemini")[1] == "groq#0"


def test_avoid_provider_still_uses_it_if_nothing_else():
    pool = make_pool(entries=[KeyEntry("gemini", 0, "k1", "gm"), KeyEntry("gemini", 1, "k2", "gm")])
    assert pool.complete("p", avoid_provider="gemini")[1] == "gemini#0"


def test_gemini_invalid_key_400_disables_key():
    def handler(request):
        return httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT",
                                                   "details": [{"reason": "API_KEY_INVALID"}]}})
    clock = FakeClock()
    pool = KeyPool([KeyEntry("gemini", 0, "bad", "gm")], 60, clock=clock, transport=httpx.MockTransport(handler))
    with pytest.raises(LLMCallFailed):
        pool.complete("p")
    clock.t += 10_000
    assert pool.has_usable_key() is False


def test_gemini_safety_block_is_empty_reply_not_key_failure():
    # Review #2: a blocked prompt is the model's answer, not a broken key; don't rest the key.
    def handler(request):
        return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})
    pool = KeyPool([KeyEntry("gemini", 0, "k1", "gm")], 60, clock=FakeClock(), transport=httpx.MockTransport(handler))
    assert pool.complete("p") == ("", "gemini#0")
    assert pool.has_usable_key() is True


def test_groq_null_content_is_empty_reply():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
    pool = KeyPool([KeyEntry("groq", 0, "k3", "qm")], 60, clock=FakeClock(), transport=httpx.MockTransport(handler))
    assert pool.complete("p") == ("", "groq#0")


def test_quoted_and_exported_env_values(tmp_path, monkeypatch):
    # Review #4: GEMINI_API_KEYS="k1,k2" and `export X=...` are common .env styles.
    p = tmp_path / ".env"
    p.write_text('GEMINI_API_KEYS="k1,k2"\nexport GROQ_API_KEY_1=\'k3\'\n', encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_1", raising=False)
    load_env_file(str(p))
    import os
    e = entries_from_env(os.environ, "gm", "qm")
    assert [x.key for x in e if x.key in ("k1", "k2", "k3")] == ["k1", "k2", "k3"]

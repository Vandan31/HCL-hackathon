"""
COMPONENT : answer engine
PURPOSE   : Send a prompt to a free-tier LLM, rotating over a pool of keys: Gemini first, Groq as fallback.
INPUTS    : prompt text; keys from .env (GEMINI_API_KEYS, GROQ_API_KEYS); model names from config/answer.py
OUTPUTS   : (reply text, key label such as "gemini#0"), or LLMCallFailed / LLMUnavailable
DEPENDS ON: httpx; Gemini generateContent REST API; Groq OpenAI-compatible REST API
PANEL NOTE: Free-tier limits are per project/account, so we fall back across providers, and if every key
            is resting the user still gets the source passages (FALLBACK in src/api/main.py).
"""
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping

import httpx

# WHY: Gemini keys are tried before any Groq key (Harsh's decision, D-007).
PROVIDER_ORDER = ("gemini", "groq")
ENV_VARS = {"gemini": "GEMINI_API_KEYS", "groq": "GROQ_API_KEYS"}


class LLMCallFailed(Exception):
    """One attempt failed; the pool has already rested or disabled that key."""

    def __init__(self, message: str, provider: str | None = None):
        super().__init__(message)
        # WHY: answer() retries on the OTHER provider, so a Gemini outage doesn't cost a 503 (review #1).
        self.provider = provider


class LLMUnavailable(Exception):
    """No key can be used right now (all resting, disabled, or none configured)."""


@dataclass
class KeyEntry:
    provider: str
    index: int
    # WHY: repr=False so printing or logging an entry can never show the key value.
    key: str = field(repr=False)
    model: str = ""

    @property
    def label(self) -> str:
        """Safe name for logs and the audit file, e.g. 'gemini#0'."""
        return f"{self.provider}#{self.index}"


def load_env_file(path: str = ".env") -> None:
    """Copy KEY=VALUE lines from .env into os.environ, without overriding variables already set."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        # FALLBACK: no .env -> no keys -> /api/health says llm "down" and answers fall back to passages.
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        # WHY: accept common .env styles: `export NAME=...` and quoted values "..." / '...'.
        name = name.strip().removeprefix("export ").strip()
        os.environ.setdefault(name, _unquote(value.strip()))


def _unquote(v: str) -> str:
    """Strip one matching pair of surrounding quotes."""
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def entries_from_env(env: Mapping[str, str], gemini_model: str, groq_model: str) -> list[KeyEntry]:
    """Build the key pool from comma-separated env vars; a provider with no model name is skipped."""
    models = {"gemini": gemini_model, "groq": groq_model}
    entries = []
    for provider in PROVIDER_ORDER:
        if not models[provider]:
            continue
        # WHY: tolerate "k1, k2 ," as people actually type it into .env.
        keys = [_unquote(k.strip()) for k in env.get(ENV_VARS[provider], "").split(",") if k.strip()]
        # WHY: also accept one key per numbered var (GEMINI_API_KEY_1, _2, ...), the format the team's .env
        # uses; sorted by number so _10 comes after _2.
        prefix = ENV_VARS[provider][:-1] + "_"  # "GEMINI_API_KEYS" -> "GEMINI_API_KEY_"
        numbered = sorted((int(n[len(prefix):]), v.strip()) for n, v in env.items()
                          if n.startswith(prefix) and n[len(prefix):].isdigit())
        keys += [_unquote(v) for _, v in numbered if v]
        entries += [KeyEntry(provider, i, k, models[provider]) for i, k in enumerate(keys)]
    return entries


class KeyPool:
    """Round-robin over usable keys, Gemini before Groq; rests keys that hit limits."""

    def __init__(self, entries: list[KeyEntry], cooldown_s: float,
                 clock: Callable[[], float] = time.monotonic,
                 transport: httpx.BaseTransport | None = None, timeout_s: float = 6):
        self._entries = entries
        self._cooldown_s = cooldown_s
        self._clock = clock
        self._resting_until = {id(e): 0.0 for e in entries}
        self._disabled: set[int] = set()
        self._next = {p: 0 for p in PROVIDER_ORDER}
        # WHY: FastAPI runs sync routes in a threadpool, so pick/rest decisions must not interleave.
        self._lock = threading.Lock()
        self._client = httpx.Client(transport=transport, timeout=timeout_s)

    def _usable(self, e: KeyEntry, now: float) -> bool:
        return id(e) not in self._disabled and self._resting_until[id(e)] <= now

    def _pick(self, avoid_provider: str | None = None) -> KeyEntry | None:
        """Next usable key of the first provider that has one; avoid_provider goes last (caller holds the lock)."""
        now = self._clock()
        order = [p for p in PROVIDER_ORDER if p != avoid_provider] + [p for p in PROVIDER_ORDER if p == avoid_provider]
        for provider in order:
            group = [e for e in self._entries if e.provider == provider]
            for offset in range(len(group)):
                i = (self._next[provider] + offset) % len(group)
                if self._usable(group[i], now):
                    self._next[provider] = (i + 1) % len(group)
                    return group[i]
        return None

    def has_usable_key(self) -> bool:
        """For /api/health: is any key ready right now?"""
        with self._lock:
            now = self._clock()
            return any(self._usable(e, now) for e in self._entries)

    def _fail(self, e: KeyEntry, disable: bool, why: str) -> LLMCallFailed:
        with self._lock:
            if disable:
                self._disabled.add(id(e))
            else:
                self._resting_until[id(e)] = self._clock() + self._cooldown_s
        # WHY: message carries only the label and status, never the key or the provider's response body.
        return LLMCallFailed(f"{e.label}: {why}", provider=e.provider)

    def complete(self, prompt: str, avoid_provider: str | None = None) -> tuple[str, str]:
        """One attempt on the next usable key (other providers before avoid_provider); returns (text, label)."""
        with self._lock:
            entry = self._pick(avoid_provider)
        if entry is None:
            raise LLMUnavailable("no usable LLM key")
        try:
            resp = self._send(entry, prompt)
        except httpx.TransportError as e:  # timeouts and connection errors
            raise self._fail(entry, False, type(e).__name__) from None
        # WHY: Gemini reports a wrong key as HTTP 400 API_KEY_INVALID, not 401/403 (review #1).
        if resp.status_code in (401, 403) or (resp.status_code == 400 and "API_KEY_INVALID" in resp.text):
            # WHY: a revoked/wrong key won't recover by waiting, so stop wasting attempts on it.
            raise self._fail(entry, True, f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            # 429 quota, 5xx outage, other 4xx: rest the key and let the caller retry on the next one.
            raise self._fail(entry, False, f"HTTP {resp.status_code}")
        try:
            return self._extract(entry, resp.json()), entry.label
        except (ValueError, KeyError, IndexError, TypeError):
            raise self._fail(entry, False, "unexpected response shape") from None

    def _send(self, e: KeyEntry, prompt: str) -> httpx.Response:
        if e.provider == "gemini":
            # WHY: key in a header, not ?key= in the URL, so it can't appear in URL-bearing error messages.
            return self._client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{e.model}:generateContent",
                headers={"x-goog-api-key": e.key},
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"responseMimeType": "application/json"}})
        return self._client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"authorization": f"Bearer {e.key}"},
            json={"model": e.model, "messages": [{"role": "user", "content": prompt}],
                  "response_format": {"type": "json_object"}})

    @staticmethod
    def _extract(e: KeyEntry, body: dict) -> str:
        """Reply text; "" when the model replied but gave no text (safety block, null content)."""
        if e.provider == "gemini":
            if "candidates" not in body:
                # WHY: a safety block is the model's answer, not a broken key -> "" ends as bad_output and the
                # key stays usable (review #2). Any other shape is a real failure (KeyError below).
                if "promptFeedback" in body:
                    return ""
                raise KeyError("candidates")
            parts = body["candidates"][0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts)
        return body["choices"][0]["message"].get("content") or ""

# Coordination board

> Claim a component here BEFORE editing its files. Remove your row when done and add a handoff note.
> If a component is already claimed by someone else, do not edit it.

## Active claims

| Component | Agent / person | Branch | Started (date time) | Files touched |
|-----------|----------------|--------|---------------------|---------------|
| API + answer engine (#4, #5) | harsh/claude | `harsh` | 2026-10-27 11:19 | `src/api/`, `src/answer/`, `config/api.py`, `config/answer.py`, `tests/api/`, `tests/answer/`, `requirements.txt`, `pytest.ini` |

## Shared-file change notices
_Announce here before editing shared files (config, requirements, API contracts)._

- 2026-10-27 · harsh (integrator) · **contract update, please read**:
  - **Vandan (lang):** `detect_language` now returns `lang` ∈ en/hi/gu/mr/ta and `script` adds `Taml`. Marathi vs Hindi (same script) needs more than script rules. The answer engine also calls your detector on the ANSWER text.
  - **Vandan (retrieval):** `score` must be 0–1 dense cosine (higher = better); RRF only orders. IndicQA goes in a separate test index, never the answer index.
  - **Vandan (PARAM):** need `data/processed/translations.jsonl` from IndicTrans2, rows `{"chunk_id","lang","text","model"}` for targets en/hi/gu/mr/ta.
  - **Vaidehi (UI/TTS):** citations gain `passage_lang`, `translation`, `translation_lang` (show original, translation below, labelled machine translation). 503 `fallback_passages` use the same card shape. Hinglish = `lang:"hi"` + `code_mixed:true`. IndicTTS reads `answer` in `lang`.

- 2026-10-27 11:19 · harsh (integrator): creating root `requirements.txt` (fastapi, uvicorn, pytest, httpx) and `pytest.ini`. Others: post new packages here and Harsh adds them.

## Handoff log (newest on top)

<!--
### YYYY-MM-DD HH:MM · <component> · <agent/person>
- Changed: ...
- How to run: `...`
- Tested: `<command>` → <real result> (or NOT RUN: reason)
- Broken / open issues: ...
- Next step: ...
-->

### 2026-10-27 13:50 · answer engine (#4) + API (#5) · harsh/claude
- Changed: `src/answer/` (refusals, translations, llm_pool, prompting, langcheck, generate), `config/answer.py`; `/api/ask` wired detect → search → answer with offline cache (`src/api/cache.py`), audit log without question text (`src/api/audit.py`), 503 fallback passages; `.env.example`; contracts in COMPONENTS.md.
- How to run: `cp .env.example .env` (paste keys) → set `GEMINI_MODEL` / `GROQ_MODEL` in `config/answer.py` → `USE_MOCKS=false .venv/bin/uvicorn src.api.main:app --reload`
- Tested: `.venv/bin/pytest -q` → 74 passed (LLM faked; no network). Live server with no model names: health `llm:"down"`, Gujarati question → 503 with passage, audit line has no query text.
- Broken / open issues: no live LLM call made yet; gu/mr/ta refusals need a native speaker; lang check is script-only until src/lang merges; search is a MOCK passage until src/retrieval merges.
- Next step: Harsh fills model names + `.env`, runs one live question per language; then record demo answers with `RECORD_CACHE=true`. Claim stays active.

### 2026-10-27 11:35 · API (#5) · harsh/claude
- Changed: FastAPI skeleton `src/api/main.py` with MOCK `/api/ask`, `/api/eligibility`, `/api/health` (contract shapes from COMPONENTS.md); fixtures in `src/api/mocks.py`; knobs in `config/api.py`; root `requirements.txt`, `pytest.ini`.
- How to run: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn src.api.main:app --reload` → http://127.0.0.1:8000/docs
- Tested: `.venv/bin/pytest -q` → 6 passed; curl smoke test on a live server (health 200, ask 200 with citation, empty query 400).
- For Vaidehi (UI): build against this now. Any query containing "passport" / "income tax" returns a refusal (`refused: true`, no citations).
- Broken / open issues: mocks only; no audit log yet; starlette warns `httpx` is deprecated for TestClient (harmless).
- Next step: answer engine (`src/answer/`): citation check + refusal templates, tests first. Claim stays active.

### 2026-10-26 · setup · Vandan
- Changed: created CLAUDE.md, AGENTS.md, docs/ (COMPONENTS, BOARD, DECISIONS, TEAM_WORKFLOW), installed skills into `.claude/skills/`.
- Tested: NOT RUN (no code yet).
- Next step: add the hackathon problem statement to `docs/COMPONENTS.md` and run `/hackathon-ai-chief-engineer`.

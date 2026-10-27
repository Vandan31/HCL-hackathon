# Coordination board

> Claim a component here BEFORE editing its files. Remove your row when done and add a handoff note.
> If a component is already claimed by someone else, do not edit it.

## Active claims

| Component | Agent / person | Branch | Started (date time) | Files touched |
|-----------|----------------|--------|---------------------|---------------|
| API + answer engine (#4, #5) | harsh/claude | `harsh` | 2026-10-27 11:19 | `src/api/`, `src/answer/`, `config/api.py`, `config/answer.py`, `tests/api/`, `tests/answer/`, `requirements.txt`, `pytest.ini` |

## Shared-file change notices
_Announce here before editing shared files (config, requirements, API contracts)._

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

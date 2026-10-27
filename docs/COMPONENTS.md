# Components: progress tracker (single source of truth)

> Update this file at the end of every task. A new session must be able to continue from here alone.
> Full plan, timeline, and reasoning: `docs/PLAN.md`.

## Project

- **Problem statement:** Case 1: Multilingual Citizen Services Assistant. Answer scheme eligibility/procedure
  questions in English, Hindi + one more Indian language (text or speech) from 20–30 scheme documents,
  reply in the user's language, show the source passage, refuse clearly when the documents don't contain the answer.
  Bonus: voice in/out, Hinglish, eligibility checklist via follow-up questions.
- **Working name / pitch:** Yojana Saathi. *Ask in your language, get the answer with proof, or an honest "I don't know".*
- **Third language:** Gujarati (default). **Switch if the organisers' 100 sample questions use another one.**
- **Team & time:** 4 people, 5–6 hours. Stack: Option 1 (FastAPI + BM25/BGE-M3 hybrid + Claude + HTML/JS).
- **Data rule:** myScheme pages are collected **by hand** (Terms of Use ban bots/scrapers). Agents never fetch them.

## Status legend
`TODO` → `IN PROGRESS` → `WORKING (tested)` → `DEMO-READY`

## Component registry

| # | Component | Folders | Owner | Status | Next step |
|---|-----------|---------|-------|--------|-----------|
| 0 | Planning | `docs/` | A. Harsh | WORKING | Confirm 3rd language from the 100 sample questions; freeze interfaces at 0:45 |
| 1 | Data + ingestion | `data/schemes/`, `src/ingest/`, `config/ingest.py` | B. Jaya | WORKING (tested) on `comp/ingest` | 26 schemes → 137 chunks, validator 0 errors. Criteria drafted (124 rules, `verified: false`). Next: a human checks each rule against `source_text` and sets `verified: true`; optional real `source_url`s; then re-run `python -m src.ingest.build_chunks` + `python scripts/validate_data.py` |
| 2 | Language detection | `src/lang/`, `config/lang.py` | C. Vandan | TODO | Unicode script rules (Deva/Gujr/Latn) + Hinglish word list + tests |
| 3 | Retrieval | `src/retrieval/`, `config/retrieval.py` | C. Vandan | TODO | BM25 + BGE-M3 + RRF over `data/processed/`; MOCK chunks until ingest is ready |
| 4 | Answer engine | `src/answer/`, `config/answer.py` | A. Harsh | TODO | Prompt → JSON {answer, citations, answerable}; citation check; refusal templates en/hi/gu/Hinglish |
| 5 | API | `src/api/` | A. Harsh | TODO | FastAPI `/api/ask`, `/api/eligibility`, `/api/health` returning MOCKs first |
| 6 | UI + voice | `src/ui/`, `config/ui.js` | D. Vaidehi | WORKING (tested, MOCK API; accessibility pass done) | Set `USE_MOCK: false` in `config/ui.js` once `/api/ask` is live; test en/hi/gu/Hinglish end to end; test mic + voices on the demo laptop |
| 7 | Eligibility checklist | `src/eligibility/`, `config/eligibility.py` | D. Vaidehi | WORKING (tested, MOCK criteria) | Add questions for Jaya's new fields: `state`, `citizen_of_india`, `annual_family_income`, `social_category`, `applicant_type` (BOARD notice, D-011); criteria are drafts (`verified: false`) until a human checks; Harsh wires `/api/eligibility` to `next_question` |
| 8 | Evaluation | `scripts/eval.py`, `data/eval/` | C. Vandan | TODO | Label sample questions with scheme ids; 20 unanswerable questions; metrics table (PLAN §6) |
| 9 | Demo & pitch | `docs/pitch/` | D. Vaidehi + A. Harsh | IN PROGRESS (architecture diagram done: `docs/pitch/architecture.svg`) | Deck draft; 90-s demo script (PLAN §9); offline mode + backup video |
| 10 | Final output: text + speech (IndicTTS) | `src/tts/`, `config/tts.py`, `src/ui/` | D. Vaidehi | IN PROGRESS: speech backend WORKING (tested, real models: gu, hi, English, Hinglish); UI wiring waits for teammates | UI: auto-play `/api/tts` audio when the question was spoken, Listen otherwise, browser-voice fallback on 422/503; Harsh to confirm `/api/tts` (BOARD) |

## Interfaces (contracts between components): freeze at 0:45

> Changing anything here = stop and ask Harsh (integrator), and update in the same commit.

```python
# src/lang/detect.py
detect_language(text: str, speech_hint: {"lang", "prob"} | None = None)
    -> {"lang": ISO 639-1 code ("en","hi","gu","mr","ta",...), "script": ISO 15924 ("Latn","Deva","Gujr",...),
        "code_mixed": bool, "confidence": float, "source": "rules"|"indiclid"|"whisper",
        "supported": bool}   # supported = we have documents + refusal templates (en/hi/gu)
# speech_hint = faster-whisper's {"lang": info.language, "prob": info.language_probability}
# supported == False -> answer engine replies/refuses in `lang` via the LLM (no native template).
# Agreed with Harsh 2026-10-27 (IndicLID layer, D-006).

# src/retrieval/search.py
search(query: str, lang: str, k: int = 5) -> list[{"chunk_id", "scheme_id", "scheme_name", "section",
                                                    "text", "lang", "source_url", "score"}]

# src/answer/generate.py
answer(query: str, lang_info: dict, chunks: list) -> {"answer", "lang", "refused", "refusal_reason",
    "citations": [{"id": "S1", "chunk_id", "scheme_name", "passage", "source_url"}], "confidence"}

# src/eligibility/rules.py
next_question(scheme_id: str, answers: dict) -> {"question": {"field", "text", "options"} | None,
    "checklist": [{"criterion", "status": "met"|"not_met"|"unknown", "source"}],
    "verdict": "likely_eligible"|"not_eligible"|"need_more_info"}
```
```
POST /api/ask          {"query", "session_id"}                      → {"answer","lang","code_mixed","refused","citations","confidence","latency_ms"}
POST /api/eligibility  {"scheme_id","answers","lang"}               → {"question","checklist","verdict"}
GET  /api/health                                                    → {"ok","index_chunks","llm","offline_mode"}
Errors: 400 {"error":"empty_query"} · 503 {"error":"llm_unavailable","fallback_passages":[...]}
```
Data files: **exact format in `docs/DATA_FORMAT.md`** (schemes JSON, `data/processed/chunks.jsonl`,
`data/eval/questions.jsonl`). Check before pushing data: `python scripts/validate_data.py`.
Chunk `text` is the clean passage; retrieval adds scheme name + section to the searched text itself.

## Honest disclosure (what is mocked / estimated / not built)

| Item | Type | Where |
|------|------|-------|
| Market stats in pitch | Sourced (links in PLAN.md) | docs/PLAN.md §1 |
| Cost per 1,000 questions | Estimated (formula; prices filled on the day) | docs/PLAN.md §4.5 |
| All accuracy/latency numbers | Not measured yet | scripts/eval.py |
| Scheme `source_url` = myScheme search page, not the scheme's own page (26 schemes) | MOCK (team decision, D-008) | config/ingest.py, data/schemes/*.json |
| Eval set = 98 questions written by our team (organisers' 100 not provided; team decision D-010) | Disclosed: ours, not the organisers' | data/eval/questions.jsonl |
| Eligibility `criteria`: agent drafts from scheme text, not yet human-checked (`verified: false`) | Draft (D-011) | data/schemes/*.json |
| Scheme text is English only; answers translated by the LLM at answer time (D-009) | Design choice | data/schemes/*.json |
| `/api/ask` answers in the UI | MOCK (`CONFIG.USE_MOCK`, "Mock data" label on screen) | src/ui/mock_api.js, src/ui/mock/ask_fixtures.json |
| Eligibility criteria for 3 schemes | MOCK (simplified, not verified) | src/eligibility/mock_schemes.json |
| `/api/eligibility` route | MOCK dev stand-in until comp/api | src/ui/dev_server.py |

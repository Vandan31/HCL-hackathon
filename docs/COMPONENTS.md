# Components: progress tracker (single source of truth)

> Update this file at the end of every task. A new session must be able to continue from here alone.
> Full plan, timeline, and reasoning: `docs/PLAN.md`.

## Project

- **Problem statement:** Case 1: Multilingual Citizen Services Assistant. Answer scheme eligibility/procedure
  questions in English, Hindi + one more Indian language (text or speech) from 20–30 scheme documents,
  reply in the user's language, show the source passage, refuse clearly when the documents don't contain the answer.
  Bonus: voice in/out, Hinglish, eligibility checklist via follow-up questions.
- **Working name / pitch:** Yojana Saathi. *Ask in your language, get the answer with proof, or an honest "I don't know".*
- **Languages (final, Harsh 2026-10-27):** English, Hindi, Gujarati, Marathi, Tamil + Hinglish (`hi` + `code_mixed`). Replies and refusals are always in the input's language.
- **Team & time:** 4 people, 5–6 hours. Stack: Option 1 (FastAPI + BM25/BGE-M3 hybrid + **Gemini free tier, Groq fallback** (D-007) + IndicTrans2 for passage translations + AI4Bharat IndicTTS + HTML/JS).
- **Data rule:** myScheme pages are collected **by hand** (Terms of Use ban bots/scrapers). Agents never fetch them.

## Status legend
`TODO` → `IN PROGRESS` → `WORKING (tested)` → `DEMO-READY`

## Component registry

| # | Component | Folders | Owner | Status | Next step |
|---|-----------|---------|-------|--------|-----------|
| 0 | Planning | `docs/` | A. Harsh | WORKING | Confirm 3rd language from the 100 sample questions; freeze interfaces at 0:45 |
| 1 | Data + ingestion | `data/schemes/`, `src/ingest/`, `config/ingest.py` | B. Jaya | TODO | Pick 25 schemes from the sample questions; everyone hand-collects 6–8 into the JSON template (PLAN §4.4) |
| 2 | Language detection | `src/lang/`, `config/lang.py` | C. Vandan | TODO | Unicode script rules (Deva/Gujr/Latn) + Hinglish word list + tests |
| 3 | Retrieval | `src/retrieval/`, `config/retrieval.py` | C. Vandan | TODO | BM25 + BGE-M3 + RRF over `data/processed/`; MOCK chunks until ingest is ready |
| 4 | Answer engine | `src/answer/`, `config/answer.py` | A. Harsh | WORKING (live-tested 2026-10-27) | Native-speaker check of gu/mr/ta refusals; record demo answers with `RECORD_CACHE=true` once real retrieval is merged |
| 5 | API | `src/api/`, `config/api.py` | A. Harsh | WORKING (tested) | `USE_MOCKS=false` runs detect → search → answer (lang/retrieval MOCKed until merged); offline cache + audit log done. Next: swap in real src/lang + src/retrieval at integration; record demo answers with `RECORD_CACHE=true` |
| 6 | UI + voice | `src/ui/`, `config/ui.js` | D. Vaidehi | TODO | Chat + passage cards + language badge against MOCK API; Web Speech mic/TTS as bonus |
| 7 | Eligibility checklist | `src/eligibility/`, `config/eligibility.py` | D. Vaidehi | TODO | Rules engine over `criteria` in scheme JSON; next-question logic |
| 8 | Evaluation | `scripts/eval.py`, `data/eval/` | C. Vandan | TODO | Label sample questions with scheme ids; 20 unanswerable questions; metrics table (PLAN §6) |
| 9 | Demo & pitch | `docs/pitch/` | D. Vaidehi + A. Harsh | TODO | Deck draft; 90-s demo script (PLAN §9); offline mode + backup video |

## Interfaces (contracts between components): freeze at 0:45

> Changing anything here = stop and ask Harsh (integrator), and update in the same commit.

```python
# src/lang/detect.py
detect_language(text: str) -> {"lang": "en"|"hi"|"gu"|"mr"|"ta", "script": "Latn"|"Deva"|"Gujr"|"Taml",
                               "code_mixed": bool, "confidence": float}

# src/retrieval/search.py
# score: 0–1, higher = more relevant = the dense (BGE-M3) cosine of the chunk; RRF decides only the ORDER.
# The answer engine refuses below MIN_SCORE, so score must be on this fixed scale (Harsh, 2026-10-27).
search(query: str, lang: str, k: int = 5) -> list[{"chunk_id", "scheme_id", "scheme_name", "section",
                                                    "text", "lang", "source_url", "score"}]

# src/answer/generate.py
answer(query: str, lang_info: dict, chunks: list, llm, translations=None, detector=None) -> {"answer", "lang",
    "refused", "refusal_reason": None|"low_score"|"not_in_documents"|"invalid_citation"|"bad_output"|"wrong_language",
    "citations": [{"id": "S1", "chunk_id", "scheme_name", "passage", "source_url",
                   "passage_lang", "translation": str|None, "translation_lang": str|None}], "confidence"}

# src/eligibility/rules.py
next_question(scheme_id: str, answers: dict) -> {"question": {"field", "text", "options"} | None,
    "checklist": [{"criterion", "status": "met"|"not_met"|"unknown", "source"}],
    "verdict": "likely_eligible"|"not_eligible"|"need_more_info"}
```
```
POST /api/ask          {"query", "session_id"}                      → {"answer","lang","code_mixed","refused","citations","confidence","latency_ms"}
POST /api/eligibility  {"scheme_id","answers","lang"}               → {"question","checklist","verdict"}
GET  /api/health                                                    → {"ok","index_chunks","llm","offline_mode"}
Errors: 400 {"error":"empty_query"} · 503 {"error":"llm_unavailable","fallback_passages":[<citation shape above>]}
Hinglish = `lang: "hi"` + `code_mixed: true` (no separate "hinglish" value). TTS reads `answer` + `lang`.
```
Data files: `data/schemes/<id>.json` (template in PLAN §4.4) · `data/processed/chunks.jsonl` (one chunk per line, fields as `search()` output minus `score`) · `data/processed/translations.jsonl` (IndicTrans2, made offline on PARAM: `{"chunk_id","lang","text","model"}`, one row per chunk × target language en/hi/gu/mr/ta).
Search space = the 20–30 myScheme pages ONLY. IndicQA is for retrieval testing and must live in a separate test index, never the answer index.

## Honest disclosure (what is mocked / estimated / not built)

| Item | Type | Where |
|------|------|-------|
| Market stats in pitch | Sourced (links in PLAN.md) | docs/PLAN.md §1 |
| Cost per 1,000 questions | Estimated (formula; prices filled on the day) | docs/PLAN.md §4.5 |
| All accuracy/latency numbers | Not measured yet | scripts/eval.py |
| `/api/ask` and `/api/eligibility` responses | MOCK (fixture data, `USE_MOCKS` knob) | src/api/mocks.py |
| `/api/health` index_chunks | MOCK (reports 0 until retrieval exposes its size) | src/api/main.py |
| detect_language / search inside the API | MOCK until src/lang, src/retrieval merge (script-only detector, one fixed passage) | src/api/mocks.py |
| gu / mr / ta refusal templates | Not yet checked by a native speaker | src/answer/refusals.py |
| Answer-language check | Script-only until src/lang merges (can't tell hi from mr) | src/answer/langcheck.py |
| LLM answers on real questions | Measured 2026-10-27: 1 live question per language (en/hi/Hinglish/gu/mr/ta) answered in the right language with [S1], out-of-scope refused; 0.8–1.9 s; against ONE mock passage, not real retrieval | config/answer.py |

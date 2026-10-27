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
- **Team & time:** 4 people, 5–6 hours. Stack: Option 1 (FastAPI + BM25/BGE-M3 hybrid + **Gemini free tier, Groq fallback** (D-019) + IndicTrans2 for passage translations + AI4Bharat IndicTTS + HTML/JS).
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
| 4 | Answer engine | `src/answer/`, `config/answer.py` | A. Harsh | WORKING (live-tested 2026-10-27) | Native-speaker check of gu/mr/ta refusals; record demo answers with `RECORD_CACHE=true` once real retrieval is merged |
| 5 | API | `src/api/`, `config/api.py` | A. Harsh | WORKING (tested) | `USE_MOCKS=false` runs detect → search → answer (lang/retrieval MOCKed until merged); offline cache + audit log done. Next: swap in real src/lang + src/retrieval at integration; record demo answers with `RECORD_CACHE=true` |
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
# Harsh's contract update (2026-10-27): native refusal templates for en/hi/gu/mr/ta; script adds "Taml".
# Merged by Vaidehi: Vandan's newer signature kept (both say agreed with Harsh). @Harsh please confirm (BOARD).

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
Data files: **exact format in `docs/DATA_FORMAT.md`** (schemes JSON, `data/processed/chunks.jsonl`,
`data/eval/questions.jsonl`). Check before pushing data: `python scripts/validate_data.py`.
Chunk `text` is the clean passage; retrieval adds scheme name + section to the searched text itself.
Also (Harsh): `data/processed/translations.jsonl` (IndicTrans2, made offline on PARAM: `{"chunk_id","lang","text","model"}`, one row per chunk × target language en/hi/gu/mr/ta).
Search space = the 20–30 myScheme pages ONLY. IndicQA is for retrieval testing and must live in a separate test index, never the answer index.

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
| `/api/ask` and `/api/eligibility` responses | MOCK (fixture data, `USE_MOCKS` knob) | src/api/mocks.py |
| `/api/health` index_chunks | MOCK (reports 0 until retrieval exposes its size) | src/api/main.py |
| detect_language / search inside the API | MOCK until src/lang, src/retrieval merge (script-only detector, one fixed passage) | src/api/mocks.py |
| gu / mr / ta refusal templates | Not yet checked by a native speaker | src/answer/refusals.py |
| Answer-language check | Script-only until src/lang merges (can't tell hi from mr) | src/answer/langcheck.py |
| Answer-engine stress test | Measured 2026-10-27, one run: 26/26 hard cases passed (16 answerable in all 5 langs + Hinglish, 7 must-refuse, 3 prompt-injection); LLM p50 1.2 s, p95 3.2 s; 5 concurrent all answered (2.8 s wall). Passages are paraphrased MOCK text, graded by script, not by native speakers. Re-run: `.venv/bin/python scripts/stress_answer.py` | scripts/stress_answer.py |
| LLM answers on real questions | Measured 2026-10-27: 1 live question per language (en/hi/Hinglish/gu/mr/ta) answered in the right language with [S1], out-of-scope refused; 0.8–1.9 s; against ONE mock passage, not real retrieval | config/answer.py |

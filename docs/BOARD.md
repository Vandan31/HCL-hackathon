# Coordination board

> Claim a component here BEFORE editing its files. Remove your row when done and add a handoff note.
> If a component is already claimed by someone else, do not edit it.

## Active claims

| Component | Agent / person | Branch | Started (date time) | Files touched |
|-----------|----------------|--------|---------------------|---------------|
| C: language + retrieval + eval | Vandan/claude | `comp/retrieval` | 2026-10-27 | `src/lang/`, `src/retrieval/`, `scripts/eval.py`, `data/eval/`, `config/lang.py`, `config/retrieval.py`, `tests/lang/`, `tests/retrieval/` |

## Shared-file change notices
_Announce here before editing shared files (config, requirements, API contracts)._

- **2026-10-27 · Vandan · data contract + lang interface.** New `docs/DATA_FORMAT.md` (exact format for
  `data/schemes/*.json`, `chunks.jsonl`, eval questions) + `scripts/validate_data.py`. **@Jaya: build ingest
  to this and run the validator before pushing data.** `detect_language()` output gained `source` and
  `supported`, and `lang` can now be any ISO code (agreed with Harsh; see COMPONENTS.md Interfaces, D-006).
- **2026-10-27 · Jaya · `data/eval/questions.jsonl`.** @Vandan: adding this NEW file inside your `data/eval/`
  (DATA_FORMAT §3, asked in the ingest brief). Your `sample_questions.jsonl`, `scripts/eval.py` and the
  validator are not touched. Questions are MOCK (organisers' 100 not received yet) and will be swapped in later.
- **2026-10-27 · Jaya · answer language (D-009).** @Harsh: scheme text stays English only. The answer engine
  should write the answer in the user's language from English passages; source cards show the English text.
- **2026-10-27 · Jaya · eligibility criteria (D-011).** @Vaidehi: all 26 `data/schemes/<id>.json` now have draft
  `criteria` in your engine's format (+ `source_text`, `verified`, `review_note`, which your code ignores). Field
  names: `config/ingest.py` `CRITERIA_FIELDS` (on `comp/ingest`). Tested with your `rules.py`. Please add questions
  for the most-used new fields: `state` (9 schemes), `citizen_of_india` (5), `annual_family_income` (4),
  `social_category` (4), `applicant_type` (3). Without them the checklist stops after `age`/`gender`/`occupation`.

## Handoff log (newest on top)

<!--
### YYYY-MM-DD HH:MM · <component> · <agent/person>
- Changed: ...
- How to run: `...`
- Tested: `<command>` → <real result> (or NOT RUN: reason)
- Broken / open issues: ...
- Next step: ...
-->

### 2026-10-27 · 1: Data + ingestion · Jaya/claude
- Changed (branch `comp/ingest`, not merged yet): `src/ingest/convert_txt.py` (pasted pages in
  `docs/schemes/*.txt` → `data/schemes/<id>.json`), `src/ingest/build_chunks.py` (→ `data/processed/chunks.jsonl`),
  `config/ingest.py` (ids, `MAX_WORDS` DEMO-KNOB), `tests/ingest/`, 26 scheme files, 137 chunks,
  `data/eval/questions.jsonl` (98 MOCK questions: 78 over all 26 schemes in en/hi/gu incl. Hinglish + 20 null).
- How to run: `python -m src.ingest.convert_txt` → `python -m src.ingest.build_chunks` → `python scripts/validate_data.py`
- Tested: `python scripts/validate_data.py` → `0 errors, 53 warnings` (52 = no hi/gu text yet; 1 = MDA benefits
  text really starts with the scheme name on myScheme, left as is). `python -m pytest tests/ingest` → `6 passed`.
  `python scripts/eval.py data/eval/questions.jsonl --bm25-only` → NOT RUN: `rank_bm25` not installed here.
- Broken / open issues: `source_url` is "not available" (MOCK, D-008). Questions are MOCK (organisers' 100 not
  received). English text only. FAQ blocks dropped (questions without answers). Data conflict in the source
  page: National Savings Time Deposit says minimum ₹1,000 (benefits) and ₹500 (how to apply).
- Next step: @Vandan run eval on `comp/ingest`; replace MOCK questions with the organisers' 100; paste URLs.

### 2026-10-26 · setup · Vandan
- Changed: created CLAUDE.md, AGENTS.md, docs/ (COMPONENTS, BOARD, DECISIONS, TEAM_WORKFLOW), installed skills into `.claude/skills/`.
- Tested: NOT RUN (no code yet).
- Next step: add the hackathon problem statement to `docs/COMPONENTS.md` and run `/hackathon-ai-chief-engineer`.

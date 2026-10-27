# Coordination board

> Claim a component here BEFORE editing its files. Remove your row when done and add a handoff note.
> If a component is already claimed by someone else, do not edit it.

## Active claims

| Component | Agent / person | Branch | Started (date time) | Files touched |
|-----------|----------------|--------|---------------------|---------------|
| C: language + retrieval + eval | Vandan/claude | `comp/retrieval` | 2026-10-27 | `src/lang/`, `src/retrieval/`, `scripts/eval.py`, `data/eval/`, `config/lang.py`, `config/retrieval.py`, `tests/lang/`, `tests/retrieval/` |
| 1: Data + ingestion | Jaya/claude | `comp/ingest` | 2026-10-27 | `data/schemes/`, `data/processed/`, `src/ingest/`, `config/ingest.py`, `tests/ingest/`, `data/eval/questions.jsonl` (new file only) |

## Shared-file change notices
_Announce here before editing shared files (config, requirements, API contracts)._

- **2026-10-27 · Vandan · data contract + lang interface.** New `docs/DATA_FORMAT.md` (exact format for
  `data/schemes/*.json`, `chunks.jsonl`, eval questions) + `scripts/validate_data.py`. **@Jaya: build ingest
  to this and run the validator before pushing data.** `detect_language()` output gained `source` and
  `supported`, and `lang` can now be any ISO code (agreed with Harsh; see COMPONENTS.md Interfaces, D-006).
- **2026-10-27 · Jaya · `data/eval/questions.jsonl`.** @Vandan: adding this NEW file inside your `data/eval/`
  (DATA_FORMAT §3, asked in the ingest brief). Your `sample_questions.jsonl`, `scripts/eval.py` and the
  validator are not touched. Questions are MOCK (organisers' 100 not received yet) and will be swapped in later.

## Handoff log (newest on top)

<!--
### YYYY-MM-DD HH:MM · <component> · <agent/person>
- Changed: ...
- How to run: `...`
- Tested: `<command>` → <real result> (or NOT RUN: reason)
- Broken / open issues: ...
- Next step: ...
-->

### 2026-10-26 · setup · Vandan
- Changed: created CLAUDE.md, AGENTS.md, docs/ (COMPONENTS, BOARD, DECISIONS, TEAM_WORKFLOW), installed skills into `.claude/skills/`.
- Tested: NOT RUN (no code yet).
- Next step: add the hackathon problem statement to `docs/COMPONENTS.md` and run `/hackathon-ai-chief-engineer`.

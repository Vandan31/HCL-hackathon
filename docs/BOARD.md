# Coordination board

> Claim a component here BEFORE editing its files. Remove your row when done and add a handoff note.
> If a component is already claimed by someone else, do not edit it.

## Active claims

| Component | Agent / person | Branch | Started (date time) | Files touched |
|-----------|----------------|--------|---------------------|---------------|
| 6. UI (mic input fix) | Vaidehi/claude | `Vaidehi` | 2026-10-27 17:00 | `src/ui/`, `config/ui.js`, `tests/ui/` |
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

- **2026-10-27 · Vaidehi → Harsh: speech output (component 10) is built; please wire or proxy it.** Separate service
  `src/tts/` on port 5600 (own venv, see `src/tts/requirements.txt`; not in the team requirements.txt). Contract:
  `POST /api/tts {text, lang: "gu"|"hi"|"en", speaker?: "female"|"male"}` → 200 `audio/wav`; Hinglish = `lang "hi"` in
  Latin letters (handled automatically); 400 bad_json/empty_text/text_too_long/unknown_speaker; 422 unsupported_lang
  (e.g. `mr`, `ta` from the new lang interface → UI uses the browser voice) / unsupported_script; 503 model_unavailable;
  `GET /api/tts/health`. Decisions D-012, D-013, D-014.

- **2026-10-27 · Vaidehi → Harsh (comp/api), to settle at integration; nothing changed in shared files:**
  the UI + eligibility code assumes (1) each `/api/ask` citation carries `"scheme_id"` (UI falls back to the
  `chunk_id` prefix before `#`); (2) `next_question(scheme_id, answers, lang="en")`, so `/api/eligibility` passes
  its `lang` through; (3) question `options` are `[{"value", "label"}]`, and `[]` means "type a number";
  (4) unknown scheme → `404 {"error": "unknown_scheme"}`. Dev stand-in: `src/ui/dev_server.py`.

## Handoff log (newest on top)

<!--
### YYYY-MM-DD HH:MM · <component> · <agent/person>
- Changed: ...
- How to run: `...`
- Tested: `<command>` → <real result> (or NOT RUN: reason)
- Broken / open issues: ...
- Next step: ...
-->

### 2026-10-27 16:30 · 6. UI (3D syllables on landing page) · Vaidehi/claude
- Changed: small syllables of English, Hindi and Gujarati float in 3D behind the language card (`src/ui/landing3d.js`). Three.js r170 (MIT) saved in `src/ui/vendor/three/` (675 KB + LICENSE) so it works offline; loaded only on the landing page. Letters drawn with the browser's text engine (Three.js 3D text can't shape Devanagari/Gujarati). Knobs: `ENABLE_3D_LANDING`, `LANDING_GLYPH_COUNT`, `LANDING_GLYPHS` in `config/ui.js`. D-015.
- Safeguards: no Three.js / no WebGL → plain landing page; hidden from screen readers; one still frame under "reduce motion"; pauses when the tab is hidden; fully stopped and GPU memory freed once a language is chosen.
- Tested: `tests/ui` → OK (new: Three.js local + licensed, never from a CDN); Chrome: renders, no console errors; measured 60 frames/s on the landing page (= browser refresh rate) and 0 frames/s after choosing a language.
- Next step: UI wiring after teammates (unchanged).

### 2026-10-27 15:55 · 6. UI + voice (lemon theme, language dropdowns) · Vaidehi/claude
- Changed: lighter lemon-yellow palette (tokens at the top of `src/ui/styles.css`; new `--accent-edge` replaces two hard-coded borders). Language selection is now a dropdown: opening page = dropdown + Continue (button text follows the chosen language; new `continue` string in en/hi/gu), header = dropdown that switches language at once (fresh conversation, focus stays on it). Old globe button and picker buttons removed.
- Tested: `python -m unittest discover -s tests/ui` → OK (contrast test: every pair passes, e.g. header text 14.1:1, control edges ≥ 5.95:1); Chrome: dropdown → Continue by keyboard → Gujarati → question → header switch to Hindi; 320px width × en/hi/gu × normal/large text: no horizontal scroll; no console errors.
- Next step: UI wiring after teammates (unchanged).

### 2026-10-27 15:10 · 10. Final output (accent fix: Hindi + Hinglish) · Vaidehi/claude
- Changed: picked by ear from A/B samples (Vaidehi): Hindi now uses the Hindi model's **male** voice (`VOICE_FOR_LANG`); Hinglish is **converted to Devanagari** and read by the Hindi model's female voice (`HINGLISH_MODE = "devanagari"`). New `src/tts/hinglish.py`: fixed word lists first (`HINGLISH_WORDS`, scheme names, acronyms), then `hindi-xlit` (MIT, 45 MB, IndicXlit-based, audited: no network/shell calls) at beam 1, with a word cache and clean-up of stray zero-width/halant characters. FALLBACK: without hindi-xlit, Hinglish uses the en+hi Latin voice. English unchanged (confirmed correct by ear). D-014.
- Tested: system Python `tests/tts` → OK (4 real-model tests skipped there); TTS venv: `tests.tts.test_hinglish` → 7 OK (real converter reproduces the hand-written demo sentence exactly), `tests.tts.test_engine_real` → 3 OK; Hinglish full sentence 2.8 s incl. conversion. Demo answers re-generated. Bug caught by tests: `[S1]` markers were being converted ("[?1]"); now stripped first.
- Open: Vaidehi to confirm the two final samples (`Desktop/tts-final-check`). From Vandan's lang update: `lang` may now be any ISO code (`mr`, `ta`…) → the UI badge must not default to "English" for those (fix during UI wiring).
- Next step: UI wiring after teammates.

### 2026-10-27 14:30 · 10. Final output (English + Hinglish voice) · Vaidehi/claude
- Changed: added AI4Bharat `en+hi.zip` (code-mixed model, 1.5 GB, lowercase a-z + Devanagari, voices female/male/hindifemale/hindimale). `lang: "en"` now spoken; Hinglish (`lang: "hi"` in Latin letters) routed to en+hi automatically and spoken with the Hindi-accent voice (`HINGLISH_VOICE` in `config/tts.py`). Latin-mode text rules: numbers in English words (Indian system: lakh, crore), ₹ → rupees, acronyms spelled ("P M Kisan"). Fixed: capital letters were being dropped before the en+hi model; real-model test no longer deletes the demo audio cache.
- Contract change for comp/api: `POST /api/tts` now accepts `lang: "en"`; Hinglish is spoken instead of 422; `unsupported_script` only if en+hi isn't loaded.
- Tested: `python -m unittest discover -s tests/tts` → 26 OK + 3 skipped; venv real-model test → 3 OK (routing, speech in 4 languages, cache). Measured (CPU, per long sentence): gu 4.0 s, hi 2.6 s, en 2.5 s, Hinglish 2.3 s; on a hot laptop up to ~7.5 s for gu (same code, re-measured: thread count barely matters). All 12 demo answers (gu/hi/en/Hinglish) pre-spoken: cache hit 1 ms. Live HTTP: English 3.1 s, Hinglish 2.0 s, male Hinglish 0.9 s. Service memory: 2.8 GB with 3 models.
- Broken / open issues: nobody has listened to the audio yet. Same licence note as before (IIT Madras IndicTTS data).
- Next step: UI wiring after teammates (auto-play when the question was spoken).

### 2026-10-27 13:40 · 10. Final output (IndicTTS backend) · Vaidehi/claude
- Changed: speech service `src/tts/` (engine, server, text normaliser, pre-generator), knobs + word lists in `config/tts.py`, pinned packages in `src/tts/requirements.txt` (own venv, not the team's requirements.txt). Model: AI4Bharat IndicTTS FastPitch + HiFi-GAN, `gu.zip` + `hi.zip` from the v1 release (1.5 GB each), unzipped to `%USERPROFILE%\indic-tts\checkpoints` (outside the repo). Chosen over Indic Parler-TTS for lower latency (one-pass model vs ~0.9B autoregressive).
- Contract (proposed to comp/api): `POST /api/tts {text, lang: gu|hi, speaker?: female|male}` → 200 audio/wav (headers X-TTS-Cache, X-TTS-Ms); 400 bad_json/empty_text/text_too_long/unknown_speaker; 422 unsupported_lang/unsupported_script (Hinglish, English → UI uses browser voice); 503 model_unavailable; `GET /api/tts/health`. Runs on port 5600, CORS for the UI on 5500.
- How to run: `%USERPROFILE%\indic-tts\.venv\Scripts\python -m src.tts.server` (repo root). Pre-speak demo answers: `... -m src.tts.pregenerate`.
- Tested: `python -m unittest discover -s tests/tts` → 18 OK + 2 skipped (no models in system Python); real models in the venv: `-m unittest tests.tts.test_engine_real` → 2 OK. Measured on this laptop (CPU): load + warm-up 7.9 s for gu+hi; one sentence gu 4.5 s → 13.3 s audio, hi 3.0 s → 7.6 s; full two-sentence demo answers 3.5–6.3 s; repeat = cache hit 0 ms. Live HTTP: 200 WAV in 3.3 s, then hit; Hinglish → 422. No characters dropped after normalisation.
- Broken / open issues: English and Hinglish not spoken by IndicTTS (needs `en+hi.zip`, 1.5 GB, not downloaded). Hindi/Gujarati number words (1–99) typed by hand: a native speaker should check `config/tts.py`. Voices trained on the IIT Madras IndicTTS data: check its licence before any commercial use. Nobody has listened to the audio yet (only measured: length, loudness).
- Next step (UI part, after teammates): play `/api/tts` audio automatically when the question was spoken, Listen button otherwise; fall back to browser voice on 422/503; consider sentence-by-sentence requests so the first words play after ~2 s.

### 2026-10-27 12:50 · 9. Demo & pitch (architecture diagram) · Vaidehi/claude
- Changed: `docs/pitch/architecture.svg`, redrawn from Vaidehi's sketch `design-arch.jpeg` (on branch `Vaidehi`) plus built/planned parts: offline lane (25 schemes → chunks → BM25 + embeddings index; eval on 100 + 20 unanswerable questions), online path (input → speech-to-text → LID → retrieval BM25 + BGE-M3 + RRF → reranker → threshold → answer with citations / refusal → UI → TTS), eligibility rules engine, fallbacks, and a key (AI model vs rules vs data).
- How to use: drag the .svg onto a Figma canvas; boxes, arrows and text import as editable, named layers.
- Tested: renders in Chrome with no overlaps; valid XML. NOT tested: the Figma import itself.
- Open issues: diagram shows "Whisper / Web Speech" and "Indic TTS / browser" because the sketch says Whisper while the build uses the browser; pick one before the pitch.
- Next step: use it on the pitch "Solution" / "Tech stack" slide.

### 2026-10-27 12:30 · 6. UI + voice (accessibility pass) · Vaidehi/claude
- Changed: WCAG 2.2 AA fixes in `src/ui/`: button/input/chip edges now 4.7–6.6:1 (were 1.3–2.2:1, 1.4.11); explicit placeholder colour; no horizontal scroll at 320px in en/hi/gu, normal and large text (1.4.10); focus moves to the verdict after the checklist and to the passage on `[S1]` (2.4.3); `lang` on example questions and user messages (3.1.2); emoji hidden from screen readers, "opens in new tab" hint (1.1.1); hidden live region announces "Listening…" (4.1.3); language button's spoken name includes its visible text (2.5.3); Escape closes the picker (2.1.1); reduced-motion respected; heading levels h1→h2; question form is a named landmark.
- How to run: `python src/ui/dev_server.py`, open http://127.0.0.1:5500/src/ui/. Contrast table: `python tests/ui/test_contrast.py`.
- Tested: `python -m unittest discover -s tests/ui` → 16 OK (new `test_contrast.py` measures 21 colour pairs from styles.css); `tests/eligibility` → 13 OK; Chrome: keyboard-only flow (Tab/Enter/Shift+Tab/Escape), 320px frames ×3 languages ×2 text sizes, no console errors. NOT tested: a real screen reader (NVDA/TalkBack), real mic.
- Broken / open issues: none known.
- Next step: test once with NVDA (free) if time; integration with `/api/ask` (`USE_MOCK: false`).

### 2026-10-27 12:05 · 6. UI + voice (theme + language picker) · Vaidehi/claude
- Changed: yellow theme (colour tokens at the top of `src/ui/styles.css`); opening page asks for the language (English / हिन्दी / ગુજરાતી), then every label, button, message, example question, date and eligibility question is in that language. All UI text lives in `CONFIG.STRINGS` in `config/ui.js`; globe button in the header switches language (starts a fresh conversation). Answers still come back in the question's own language, as the brief requires.
- How to run: `python src/ui/dev_server.py`, open http://127.0.0.1:5500/src/ui/
- Tested: `python -m unittest discover -s tests/ui` → 14 OK (incl. every HTML label translated in en/hi/gu); `tests/eligibility` → 13 OK; Chrome: picker → Gujarati → question → checklist → switch to Hindi, all labels in the picked language, no console errors.
- Broken / open issues: mock passages are English placeholder text (real passages come from the documents).
- Next step: accessibility pass; integration with `/api/ask` (`USE_MOCK: false`).

### 2026-10-27 11:44 · 7. Eligibility checklist · Vaidehi/claude
- Changed: rules engine `src/eligibility/rules.py` (`next_question`), knobs + en/hi/gu question wording in `config/eligibility.py`, MOCK criteria for pm-kisan / atal-pension / pm-ujjwala in `src/eligibility/mock_schemes.json` (real `data/schemes/<id>.json` wins when present). Checklist screen in `src/ui/app.js`; dev route in `src/ui/dev_server.py`.
- How to run: `python src/ui/dev_server.py`, open http://127.0.0.1:5500/src/ui/, ask a sample question, press "Check if I'm eligible".
- Tested: `python -m unittest discover -s tests/eligibility` → 13 OK; `python -m unittest discover -s tests/ui` → 12 OK; Chrome: Gujarati PM-KISAN flow to "likely eligible", PMAY → "checklist not available", no console errors. NOT tested: number-input question in the browser (engine path is unit-tested).
- Broken / open issues: integration assumptions listed under "Shared-file change notices". Criteria are MOCK until Jaya's verified files exist.
- Next step: Jaya's `criteria` in `data/schemes/` replace the mock; Harsh's `/api/eligibility` calls `next_question`; then remove `dev_server.py` from the demo path.

### 2026-10-27 11:33 · 6. UI + voice · Vaidehi/claude
- Changed: chat screen (`src/ui/`), knobs in `config/ui.js`, MOCK `/api/ask` in `src/ui/mock_api.js` + `src/ui/mock/ask_fixtures.json`. Language badge, `[S1]` links to passage cards, refusal / AI-down / network-error states, Web Speech mic + "Listen", large-text mode.
- How to run: from repo root `python -m http.server 5500`, open http://127.0.0.1:5500/src/ui/
- Tested: `python -m unittest discover -s tests/ui` → 8 tests OK; clicked through all 4 sample questions + forced error states in Chrome, no console errors. NOT tested: real mic/TTS, real API.
- Broken / open issues: none known. Still `USE_MOCK: true`.
- Next step: when `/api/ask` is live set `USE_MOCK: false` in `config/ui.js` and test en/hi/gu/Hinglish end to end; accessibility pass.

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

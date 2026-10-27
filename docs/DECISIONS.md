# Decision log + panel answers

> One entry per real design choice. The "Panel answer" is what we say out loud if a judge asks.
> Claims must be labeled Measured / Sourced / Estimated / Hypothesized.

<!--
## D-00X · <short title> · <component> · YYYY-MM-DD
- **Decision:** ...
- **Alternatives considered:** ...
- **Why:** ...
- **Evidence:** <Measured/Sourced/Estimated/Hypothesized> ...
- **Panel answer (≤2 sentences):** ...
- **What would make us change it:** ...
-->

## D-001 · Hand-collect scheme pages, no scraping · data · 2026-10-27
- **Decision:** 25 myScheme pages are copied by hand into JSON; agents only structure pasted text.
- **Alternatives:** scraper/bot (fast but prohibited).
- **Evidence:** Sourced: myScheme Terms of Use prohibit bots/scrapers unless authorised in writing.
- **Panel answer:** "The site's terms ban scrapers, so we collected 25 schemes by hand with URL and date; in production we'd use an official data feed."
- **Change if:** written authorisation or an official API becomes available.

## D-002 · Option 1 stack: FastAPI + hybrid retrieval + Claude + HTML/JS · all · 2026-10-27
- **Decision:** single Python service, in-memory BM25 + BGE-M3 index, one LLM call per answer.
- **Alternatives:** Streamlit + ChromaDB (faster UI, merge clashes); open models on PARAM GPUs (₹0 API, high setup risk).
- **Why:** module boundaries map 1:1 to 4 people; 25 schemes fit in memory; no vector DB needed.
- **Panel answer:** "A few hundred chunks don't need a vector database; we kept it simple so every part is testable and explainable."
- **Change if:** corpus grows past ~100k chunks, or API budget is zero (→ open models).

## D-003 · Hybrid BM25 + multilingual dense retrieval with RRF · retrieval · 2026-10-27
- **Decision:** BM25 for exact scheme names, BGE-M3 for cross-language meaning, merged by Reciprocal Rank Fusion.
- **Evidence:** Sourced: BGE-M3 leads Hindi-BEIR; mE5 strong on some Hindi tasks (kept as fallback knob). Our own Recall@5: not measured yet.
- **Panel answer:** "Dense embeddings match a Gujarati question to an English passage; BM25 never misses 'PM-Kisan'. RRF fuses ranks because the two score scales differ."
- **Change if:** eval shows BM25 adds nothing → drop it.

## D-004 · Rules decide eligibility and refusals, LLM only writes · answer/eligibility · 2026-10-27
- **Decision:** score threshold + citation-id check gate every answer; eligibility verdicts come from human-verified `criteria`.
- **Why:** welfare answers are high-stakes; an invented "you're eligible" sends someone to the wrong office.
- **Panel answer:** "The AI never decides if you're eligible. Transparent rules from the scheme's own text do, and the AI explains."
- **Change if:** never for verdicts; threshold is tuned on the eval set.

## D-005 · Third language = Gujarati (default) · lang · 2026-10-27
- **Decision:** Gujarati unless the organisers' 100 sample questions use another language.
- **Why:** team location (Gujarat), IndicQA has Gujarati, demo story with a Gujarat citizen.
- **Change if:** sample questions are in another language. It's one config value plus documents.

## D-006 · Layered language ID: script rules → IndicLID → Whisper hint · lang · 2026-10-27
- **Decision:** Unicode script rules + Hinglish word list first; AI4Bharat IndicLID (fastText FTN/FTR, via
  `fasttext-predict`) only for shared scripts (Devanagari, Bengali, Arabic, Roman); faster-whisper's own
  language guess as a hint for speech. Rules-only fallback when the models are missing.
- **Alternatives:** rules only (can't tell Marathi from Hindi, misses romanised Gujarati); IndicLID alone
  (wrong on short/Hinglish queries); IndicLID-BERT (968 MB, slower).
- **Evidence:** Measured on our probes: IndicLID right on Marathi, romanised Marathi/Gujarati/Tamil; wrong
  alone on Hinglish (→ Maithili 0.77–0.92), "PM किसान का पैसा कब आएगा?" (→ Kashmiri 1.00), "apply online"
  (→ Gujarati 0.68), hence guards (≥3 words, ≥0.5 prob, accepted-language list). 50/50 lang tests pass;
  0.03 ms/query avg over 1,000 queries after a one-time 16 s model load (laptop CPU).
- **Panel answer:** "Free rules settle most queries instantly; the IndicLID model only judges the scripts
  several languages share, and we measured where it fails and guard against it."
- **Change if:** eval on the organisers' questions shows the guards reject correct model answers.

## D-007 · Ingest: pasted pages → fixed-id scheme files → one chunk per section · data · 2026-10-27
- **Decision:** `src/ingest/convert_txt.py` structures hand-pasted myScheme pages (`docs/schemes/*.txt`)
  into `data/schemes/<id>.json`; `src/ingest/build_chunks.py` writes one chunk per scheme × section ×
  language. Scheme ids come from a fixed map in `config/ingest.py`, not auto-slugs. FAQ blocks are dropped
  (the pasted pages hold FAQ questions only, no answers). Sections over `MAX_WORDS` (400) are split into
  the same number of parts in every language, at line/sentence ends.
- **Why:** ids are permanent (eval labels and citations point at them); a FAQ question without its answer
  is not a fact; same-count splits let retrieval pair `eligibility#2:en` with `eligibility#2:hi`.
- **Evidence:** Measured: 26 schemes → 137 chunks, 2 sections split; `validate_data.py` 0 errors;
  `tests/ingest` 6 passed.
- **Panel answer:** "Every passage is a named section of a named, dated scheme page that a person copied by
  hand, so every answer can be traced back to it."
- **Change if:** pages arrive with FAQ answers (map them to a section after asking Vandan), or hi/gu text
  is added (paste it into the JSON; re-run `build_chunks`).

## D-008 · source_url = myScheme search page for now · data · 2026-10-27
- **Decision:** team chose (Jaya, 2026-10-27) to use `https://www.myscheme.gov.in/search` as `source_url.en`
  for all 26 schemes, because none of the pasted pages included its own URL and agents may not look them
  up (D-001). Replaces the first placeholder "not available". Tagged `MOCK` in config/ingest.py.
- **Panel answer:** "The link opens myScheme's search, where the scheme name on the card finds the page;
  per-scheme links are a one-line fix in each scheme file."
- **Change if:** someone pastes the real myScheme page URLs into `data/schemes/<id>.json` (converter keeps them).

## D-009 · Hindi/Gujarati answers: translate at answer time, not in the data · data/answer · 2026-10-27
- **Decision:** team chose (Jaya, 2026-10-27) to keep scheme text English-only and have the answer engine
  write the answer in the user's language from the English passages (one LLM call, same as today).
- **Alternatives:** translate every section once at ingest (lowest per-question latency, works offline,
  but unofficial text to check by hand for 26 schemes).
- **Evidence:** Estimated: replying in Hindi from an English passage costs about the same output tokens as
  replying in English; only translating the full passage for the source card would add latency.
- **Panel answer:** "Our source of truth is the official English page; the AI only translates the answer,
  and the proof card shows the exact official wording."
- **Change if:** the demo needs native-language proof cards, or offline mode must answer in Hindi/Gujarati.

## D-010 · Eval set = 98 team-written questions · eval/data · 2026-10-27
- **Decision:** team chose (Jaya, 2026-10-27) to use the 98 questions in `data/eval/questions.jsonl` as the
  official eval set in place of the organisers' 100, which were not provided: 3 per scheme (en / hi incl.
  Hinglish / gu) for all 26 schemes + 20 unanswerable. Ids stay `mock-001`..`mock-098`.
- **Why:** eval and refusal tuning can't wait; every scheme gets equal coverage in all three languages.
- **Panel answer:** "The organisers didn't share their questions, so we wrote our own: 3 per scheme in three
  languages plus 20 out-of-scope ones. They're ours, and we say so."
- **Change if:** the organisers' questions arrive: copy them in exactly as asked and re-run the eval.

## D-011 · Eligibility criteria drafted from scheme text, AND-only, lenient where unsure · data/eligibility · 2026-10-27
- **Decision:** 124 draft rules for 26 schemes in `data/schemes/<id>.json` → `criteria`, in the eligibility
  engine's format (`field`, `op`, `value`, `text_en`) plus `source_text` (the exact sentence, checked by a
  test), `verified: false` (until a human checks) and `review_note` (where the text didn't fit a rule).
  Field names are one shared list in `config/ingest.py` `CRITERIA_FIELDS`.
- **Why:** the engine only does AND, so "60% (50% for some categories)" or "35 (40 with relaxation)" is drafted
  at the lenient limit: wrongly telling an eligible citizen "not eligible" is the worse error; the
  department still makes the final call. Vague conditions ("aptitude for research") stay as yes/no fields
  that show "verify at office".
- **Evidence:** Measured: `tests/ingest` 7 passed; Vaidehi's `rules.py` (branch `Vaidehi`) run on the drafts
  gives `not_eligible` for RTI age 42, `likely_eligible` for a fully answered widow-pension case.
- **Panel answer:** "Every rule quotes the sentence it came from, and a person ticks it off before it's trusted."
- **Change if:** a human reviewer corrects a rule (edit the JSON, set `verified: true`).

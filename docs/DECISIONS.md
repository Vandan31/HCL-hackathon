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

## D-012 · Retrieval runs on multilingual-e5-small (threshold superseded by D-013) · retrieval/eval · 2026-10-27
- **Decision:** `EMBED_MODEL = intfloat/multilingual-e5-small`, refusal threshold `MIN_SCORE = 0.82`
  (config/retrieval.py). The threshold is calibrated for this model only.
- **Alternatives:** BGE-M3 (planned in D-003): crashed out of memory (segfault on first encode; 5.9 GB RAM,
  0.6 GB free; weights 2.27 GB). Threshold 0.83: more refusals but false refusal 0.115 (> 0.1 target).
- **Evidence:** Measured, `scripts/eval.py data/eval/questions.jsonl --sweep --model intfloat/multilingual-e5-small`
  on 98 team-written questions (D-010; 78 answerable, 20 null), 137 English chunks:
  recall@5 0.949 with no threshold (en 1.0, hi 0.923, gu 0.923), p50 29 ms / p95 37 ms per query (laptop CPU).
  Top-1 scores overlap: answerable 0.800–0.928, unanswerable 0.775–0.854, so no threshold meets both targets.
  At 0.82: recall@5 0.910, false refusal 0.090, refusal recall 0.60 (12 of 20 refused).
  BM25-only for comparison: recall@5 0.577 (en 1.0, hi 0.462, gu 0.269).
- **Panel answer:** "Search alone refuses 60% of off-topic questions without ever calling the AI; the answer
  engine's grounding and citation checks (D-004) are the second gate for the rest. We picked the threshold from
  a measured sweep, keeping false refusals under 10%."
- **Change if:** a machine with ≥ 16 GB RAM is available (re-test BGE-M3 and re-sweep), or Hindi/Gujarati queries
  are translated to English before search (expected to sharpen the score gap; not measured).

## D-013 · BM25 only for languages with documents + "stands-out" refusal gate · retrieval · 2026-10-27
- **Decision:** (1) BM25 joins the RRF fusion only when the question's language has chunks (`BM25_SAME_LANG_ONLY`);
  Hindi/Gujarati questions use dense search alone while chunks are English-only (D-009). (2) A question gets
  passages only if the best chunk scores ≥ `MIN_SCORE` 0.81 **and** stands ≥ `MIN_Z` 2.8 standard deviations above
  the average chunk; otherwise `search()` returns `[]`. (3) English function-word rule before IndicLID.
- **Alternatives tested (Measured, same 98 questions):** hubness corrections (mean-centering, CSLS): no gain
  (right-scheme-first 0.936–0.962 vs 0.974 baseline); absolute score only (D-012): refusal 0.60 at false refusal 0.090.
- **Evidence:** Measured, `scripts/eval.py data/eval/questions.jsonl --sweep` (e5-small, IndicLID on):
  recall@5 0.936, right scheme first 0.923, false refusal 0.064, refusal recall 0.75, language accuracy 1.0,
  p50 29 ms / p95 41 ms. Per language: en 1.0/1.0/0.0/0.714 · hi 0.962/0.962/0.038/0.714 · gu 0.846/0.808/0.154/0.833
  (recall / first / false refusal / refusal). Before (D-012 config): recall 0.910, refusal 0.60, first ≈0.60.
  Refusal signal separation (AUC): z-score 0.947 vs raw top score 0.886.
- **Caveat:** thresholds were tuned and measured on the same 98 team-written questions (no held-out set), so
  expect lower numbers on the organisers' questions. z depends on corpus size: re-run the sweep if chunks change a lot.
- **Panel answer:** "Keyword search can't match a Hindi question to English text, so we only use it where it can
  help; and we refuse when no passage clearly stands out, which caught 75% of off-topic questions before any AI call."
- **Change if:** chunks get Hindi/Gujarati text (BM25 turns back on automatically), or the organisers' questions
  show a different trade-off in the sweep.

## D-014 · Speech output with AI4Bharat IndicTTS (FastPitch + HiFi-GAN), own service · tts · 2026-10-27
- **Decision:** a separate speech service (`src/tts/`, port 5600) runs AI4Bharat IndicTTS FastPitch + HiFi-GAN for Gujarati and Hindi on the laptop CPU, with a memory + disk cache and pre-spoken demo answers. Answers are always shown as text; spoken automatically when the question was spoken.
- **Alternatives considered:** browser voices (this laptop's Chrome has Hindi only, online, no Gujarati: Measured); Indic Parler-TTS (~0.9B, autoregressive, GPU preferred: slower); Sarvam/Bhashini APIs (keys, network dependence).
- **Why:** lowest latency of the IndicTTS options; free and open (code MIT); works offline once downloaded.
- **Evidence:** Measured on the demo laptop: 3.0–4.5 s per sentence, ~3x faster than playback; full demo answers 3.5–6.3 s; repeats 0 ms (cache). Dependencies: torch 2.8.0 CPU (2.9+ needs torchcodec/ffmpeg) and coqui-tts 0.28.0, in their own venv.
- **Panel answer:** "We use AI4Bharat's open IndicTTS: FastPitch speaks a whole sentence in one pass, so it runs on a plain laptop CPU about three times faster than real time, and demo answers are pre-spoken."
- **Change if:** English/Hinglish speech is needed (add `en+hi.zip`), a GPU is available, or a native speaker finds the voice quality poor.

## D-015 · English and Hinglish speech via AI4Bharat's code-mixed en+hi model · tts · 2026-10-27
- **Decision:** add `en+hi.zip`; route English and any Latin-letter answer (Hinglish) to it, using its Hindi-accent voice for Hinglish.
- **Alternatives considered:** `en.zip` (English only, no Hinglish); browser voice (no Indian-English voice on this laptop: Measured).
- **Why:** one 1.5 GB model covers both English and Hinglish; same fast FastPitch architecture.
- **Evidence:** Measured: English 2.5 s and Hinglish 2.3 s per long sentence on the laptop CPU; demo answers pre-spoken (1 ms).
- **Panel answer:** "Hinglish isn't an afterthought: AI4Bharat trained a code-mixed English-Hindi voice, and we send any romanised answer to it automatically."
- **Change if:** listeners find the Hinglish voice unclear → try the plain "female"/"male" voices via HINGLISH_VOICE in config/tts.py.

## D-016 · Voices chosen by ear; Hinglish spoken via Devanagari · tts · 2026-10-27
- **Decision:** Hindi uses the Hindi model's male voice; Hinglish is converted to Devanagari (fixed word list + hindi-xlit) and read by the Hindi model's female voice.
- **Alternatives considered:** 8 A/B samples (Hindi: hi female/male, en+hi Hindi female/male; Hinglish: Latin with Hindi-accent or English voice, Devanagari with hi or en+hi voice). Converters: AI4Bharat ai4bharat-transliteration (needs fairseq, hard on Windows), rule-based indic-transliteration (misspells casual Hinglish), LLM-provided Devanagari (depends on comp/api).
- **Why:** a teammate listened and found the Latin-letter Hinglish and the female Hindi voice off in accent; samples B (Hindi) and C (Hinglish) sounded right.
- **Evidence:** Human listening test (Vaidehi, 2026-10-27). Measured: converter 53 ms/word at beam 1 (vs 111 ms at the default 3); demo sentence 14/17 words correct from the model alone, 17/17 with the fixed word list.
- **Panel answer:** "Romanised Hindi read letter by letter sounds foreign, so we first convert it to Devanagari and let the Hindi voice read it; we picked the voices by listening, not by guessing."
- **Change if:** the answer engine starts returning a Devanagari copy of Hinglish answers (use that instead), or listeners prefer another sample.

## D-017 · Three.js for the landing-page decoration, vendored locally · ui · 2026-10-27
- **Decision:** add Three.js r170 (MIT, 675 KB) in `src/ui/vendor/three/`, loaded only on the language page, to float small syllables of all three languages behind the card.
- **Alternatives considered:** loading from a CDN (breaks the offline demo); a 3D globe (replaced by syllables at the team's request); Three.js 3D text (cannot shape Devanagari/Gujarati).
- **Why:** a memorable first screen that shows "three languages" at a glance, without touching the chat screen's speed or accessibility.
- **Evidence:** Measured in Chrome on the demo laptop: 60 frames/s on the landing page, 0 after a language is chosen (animation stopped, GPU freed).
- **Panel answer:** "It's decoration, so it's optional: no WebGL, no library or 'reduce motion' simply means a calm, plain page, and it switches off the moment you pick a language."
- **Change if:** it stutters on the demo phone → lower `LANDING_GLYPH_COUNT` or set `ENABLE_3D_LANDING: false`.

## D-018 · API ships MOCK-first; missing/blank query → 400 not 422 · api · 2026-10-27
- **Decision:** `/api/*` return fixture data (`src/api/mocks.py`) until real components merge; request fields default to "" so the API returns the contract's `400 {"error":"empty_query"}` instead of FastAPI's 422.
- **Alternatives:** wait for lang/retrieval/answer before exposing endpoints (blocks the UI for ~2 h).
- **Evidence:** Measured: `pytest tests/api` → 6 passed on 2026-10-27.
- **Panel answer:** "We froze the API contract first and served mock answers, so the UI and the AI were built in parallel and plugged together at integration."
- **Change if:** never for the contract; the mock is removed once `USE_MOCKS=false` works end to end.

## D-019 · LLM = Gemini (free tier) first, Groq fallback, round-robin key pool · answer · 2026-10-27
- **Decision:** answers are written by Gemini Flash (free tier); Groq is the fallback provider. 4 keys (2 Gemini, 2 Groq) in `.env`, round-robin with cooldown on 429/quota/timeout. Replaces Claude from D-002.
- **Alternatives:** Claude (no free tier), Sarvam (small one-time credits), Groq only (weaker Gujarati/Marathi/Tamil, Hypothesized).
- **Evidence:** Sourced (web, 2026-10-27, third-party, conflicting): Gemini Flash free tier ~20–1,500 req/day; Groq ~1,000–14,400 req/day; both limit per project/account, not per key. Quality on our languages: not measured yet.
- **Panel answer:** "Free-tier Gemini writes the answer, Groq takes over if Gemini is rate-limited, and if both fail we still show the source passages; on stage, recorded answers cover the demo questions."
- **Models (Measured 2026-10-27):** `gemini-3.5-flash-lite` (1.7 s) because `gemini-3.8-flash` timed out / returned 503 "high demand"; Groq `openai/gpt-oss-120b`. A failed call retries on the *other* provider.
- **Change if:** eval shows poor mr/ta quality, or free-tier limits break the demo.

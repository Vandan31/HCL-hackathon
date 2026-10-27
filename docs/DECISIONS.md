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

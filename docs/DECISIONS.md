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

## D-006 · API ships MOCK-first; missing/blank query → 400 not 422 · api · 2026-10-27
- **Decision:** `/api/*` return fixture data (`src/api/mocks.py`) until real components merge; request fields default to "" so the API returns the contract's `400 {"error":"empty_query"}` instead of FastAPI's 422.
- **Alternatives:** wait for lang/retrieval/answer before exposing endpoints (blocks the UI for ~2 h).
- **Evidence:** Measured: `pytest tests/api` → 6 passed on 2026-10-27.
- **Panel answer:** "We froze the API contract first and served mock answers, so the UI and the AI were built in parallel and plugged together at integration."
- **Change if:** never for the contract; the mock is removed once `USE_MOCKS=false` works end to end.

## D-007 · LLM = Gemini (free tier) first, Groq fallback, round-robin key pool · answer · 2026-10-27
- **Decision:** answers are written by Gemini Flash (free tier); Groq is the fallback provider. 4 keys (2 Gemini, 2 Groq) in `.env`, round-robin with cooldown on 429/quota/timeout. Replaces Claude from D-002.
- **Alternatives:** Claude (no free tier), Sarvam (small one-time credits), Groq only (weaker Gujarati/Marathi/Tamil, Hypothesized).
- **Evidence:** Sourced (web, 2026-10-27, third-party, conflicting): Gemini Flash free tier ~20–1,500 req/day; Groq ~1,000–14,400 req/day; both limit per project/account, not per key. Quality on our languages: not measured yet.
- **Panel answer:** "Free-tier Gemini writes the answer, Groq takes over if Gemini is rate-limited, and if both fail we still show the source passages; on stage, recorded answers cover the demo questions."
- **Change if:** eval shows poor mr/ta quality, or free-tier limits break the demo.

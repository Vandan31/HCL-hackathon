/**
 * COMPONENT : ui
 * PURPOSE   : Pretend to be the backend's POST /api/ask so the UI can be built before the API exists.
 * INPUTS    : the user's question text
 * OUTPUTS   : {status, body}, shaped exactly like the HTTP response in docs/COMPONENTS.md "Interfaces"
 * DEPENDS ON: src/ui/mock/ask_fixtures.json, config/ui.js
 * PANEL NOTE: Building against a mock of the agreed contract let the UI and the backend be built in parallel.
 */
// MOCK: this whole file is a stand-in for Harsh's src/api. It is switched off by CONFIG.USE_MOCK = false.

import { CONFIG } from "../../config/ui.js";

// WHY: load the fixtures once and reuse the promise, so repeated questions don't refetch the file.
let fixturesPromise = null;
function loadFixtures() {
  if (!fixturesPromise) {
    fixturesPromise = fetch(new URL("./mock/ask_fixtures.json", import.meta.url)).then((r) => r.json());
  }
  return fixturesPromise;
}

// A few very common Hinglish words. MOCK: the real detector is Vandan's src/lang/detect.py.
const HINGLISH_WORDS = ["ke", "ka", "ki", "kya", "hai", "chahiye", "kaise", "liye", "mujhe", "kaun", "kaunse", "mein", "milega", "banaye"];

/** Rough language guess used only by the mock: returns {lang, script, code_mixed}. */
export function mockDetect(text) {
  // WHY: Unicode script ranges are a free, instant signal; Gujarati and Devanagari never overlap.
  if (/[઀-૿]/.test(text)) return { lang: "gu", script: "Gujr", code_mixed: false };
  if (/[ऀ-ॿ]/.test(text)) return { lang: "hi", script: "Deva", code_mixed: false };
  const words = text.toLowerCase().split(/[^a-z]+/);
  const hits = words.filter((w) => HINGLISH_WORDS.includes(w)).length;
  // WHY: 2+ Hindi function words in Latin script is a strong Hinglish signal; one could be a coincidence.
  if (hits >= 2) return { lang: "hi", script: "Latn", code_mixed: true };
  return { lang: "en", script: "Latn", code_mixed: false };
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Fake POST /api/ask. Returns {status, body} like a fetch response would, or throws like a network failure. */
export async function mockAsk(query) {
  await sleep(CONFIG.MOCK_DELAY_MS);
  const fx = await loadFixtures();

  if (CONFIG.MOCK_FORCE_ERROR === "network") throw new TypeError("MOCK: simulated network failure");

  const det = mockDetect(query);
  const key = det.code_mixed ? "hinglish" : det.lang;   // which answer variant to show
  const q = query.toLowerCase();
  const topic = fx.topics.find((t) => t.match.some((m) => q.includes(m.toLowerCase())));

  if (CONFIG.MOCK_FORCE_ERROR === "llm_unavailable") {
    // Mirrors the 503 contract: the LLM is down but retrieval still worked.
    const passages = (topic || fx.topics[0]).citations.map((c) => ({
      chunk_id: c.chunk_id, scheme_name: c.scheme_name, text: c.passage, source_url: c.source_url,
    }));
    return { status: 503, body: { error: "llm_unavailable", fallback_passages: passages } };
  }

  if (!query.trim()) return { status: 400, body: { error: "empty_query" } };

  // WHY: anything the mock doesn't recognise is refused, same as the real system should do,
  // so the demo never shows a confident answer the documents don't support.
  if (!topic || fx.refusal.match.some((m) => q.includes(m.toLowerCase()))) {
    return {
      status: 200,
      body: { answer: fx.refusal.answers[key], lang: det.lang, code_mixed: det.code_mixed,
              refused: true, citations: [], confidence: 0.0, latency_ms: CONFIG.MOCK_DELAY_MS },
    };
  }

  return {
    status: 200,
    body: { answer: topic.answers[key], lang: det.lang, code_mixed: det.code_mixed, refused: false,
            citations: topic.citations, confidence: topic.confidence, latency_ms: CONFIG.MOCK_DELAY_MS },
  };
}

/**
 * COMPONENT : ui
 * PURPOSE   : The only place the UI talks to the backend: send a question, get an answer or a typed error.
 * INPUTS    : question text, session id
 * OUTPUTS   : the /api/ask JSON body on success; throws ApiError(kind) otherwise
 * DEPENDS ON: config/ui.js, src/ui/mock_api.js (while CONFIG.USE_MOCK is true), backend /api/ask and /api/health
 * PANEL NOTE: Real API and mock go through the same code path, so switching at integration is one config flag.
 */

import { CONFIG } from "../../config/ui.js";
import { mockAsk } from "./mock_api.js";

/** Error with a machine-readable kind: empty_query | llm_unavailable | timeout | network | server. */
export class ApiError extends Error {
  constructor(kind, message, data = null) {
    super(message);
    this.kind = kind;
    this.data = data;   // for llm_unavailable: the response body holding fallback_passages
  }
}

/** POST /api/ask (or the mock). Returns the response body, or throws ApiError. */
export async function ask(query, sessionId) {
  const q = query.trim();
  if (!q) throw new ApiError("empty_query", "Please type or say a question.");

  let status, body;
  if (CONFIG.USE_MOCK) {
    try {
      ({ status, body } = await mockAsk(q));
    } catch (e) {
      throw new ApiError("network", "Could not reach the server.");
    }
  } else {
    // WHY: without a timeout a hung request leaves the user staring at a spinner forever.
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), CONFIG.REQUEST_TIMEOUT_MS);
    let res;
    try {
      res = await fetch(`${CONFIG.API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, session_id: sessionId }),
        signal: ctrl.signal,
      });
    } catch (e) {
      // FALLBACK: timeout or no network -> the UI shows a retry message; the typed question stays in the box.
      throw new ApiError(e.name === "AbortError" ? "timeout" : "network", "Could not reach the server.");
    } finally {
      clearTimeout(timer);
    }
    status = res.status;
    try { body = await res.json(); } catch { body = null; }
  }

  if (status === 200 && body) return body;
  if (status === 400) throw new ApiError("empty_query", "Please type or say a question.");
  // FALLBACK: LLM down but retrieval worked -> the UI shows the official passages without an AI summary.
  if (status === 503 && body && body.error === "llm_unavailable") {
    throw new ApiError("llm_unavailable", "AI summary unavailable.", body);
  }
  throw new ApiError("server", `Server error (HTTP ${status}).`);
}

/**
 * POST /api/eligibility. Returns {question, checklist, verdict}, or throws ApiError
 * (kind "unknown_scheme" when no checklist exists for that scheme yet).
 */
export async function eligibility(schemeId, answers, lang) {
  // WHY: same timeout reasoning as ask(); a stuck checklist must not freeze the screen.
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), CONFIG.REQUEST_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(`${CONFIG.API_BASE}/api/eligibility`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scheme_id: schemeId, answers, lang }),
      signal: ctrl.signal,
    });
  } catch (e) {
    throw new ApiError(e.name === "AbortError" ? "timeout" : "network", "Could not reach the server.");
  } finally {
    clearTimeout(timer);
  }
  let body = null;
  try { body = await res.json(); } catch { body = null; }
  if (res.ok && body) return body;
  if (body && body.error === "unknown_scheme") throw new ApiError("unknown_scheme", "No checklist for this scheme.");
  throw new ApiError("server", `Server error (HTTP ${res.status}).`);
}

/** GET /api/health. Returns the body, or null if the server can't be reached (never throws). */
export async function health() {
  if (CONFIG.USE_MOCK) return { ok: true, mock: true };
  try {
    const res = await fetch(`${CONFIG.API_BASE}/api/health`);
    return res.ok ? await res.json() : null;
  } catch {
    return null;   // FALLBACK: health is informational only; a failure just shows "server unreachable".
  }
}

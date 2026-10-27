/**
 * COMPONENT : ui
 * PURPOSE   : Wire the chat screen: send questions, render answers with [S1] links to source passage cards,
 *             show refusals and errors clearly, and handle voice and large-text mode.
 * INPUTS    : user actions on src/ui/index.html
 * OUTPUTS   : DOM updates in #chat-log
 * DEPENDS ON: src/ui/api.js, src/ui/voice.js, config/ui.js
 * PANEL NOTE: Every answer is shown with its proof (the passage and link); a refusal looks visibly different from an answer.
 */

import { CONFIG } from "../../config/ui.js";
import { ask, eligibility, health, ApiError } from "./api.js";
import { sttSupported, ttsSupported, startListening, speak } from "./voice.js";

const $ = (id) => document.getElementById(id);
const els = {
  log: $("chat-log"), form: $("ask-form"), query: $("query"), send: $("send-btn"),
  chips: $("sample-chips"), pill: $("status-pill"), largeText: $("large-text-toggle"),
  micGroup: $("mic-group"), micBtn: $("mic-btn"), micLang: $("mic-lang"),
};

// WHY: the API contract asks for a session_id so follow-up questions can share context later.
const sessionId = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
let answerCount = 0;   // gives each answer's passage cards unique element ids
let busy = false;

/** Small DOM helper: el("p", {class: "x"}, "text", childNode). Text is always inserted as text, never HTML. */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
}

/** Which UI-string set and speech voice to use: Hinglish is Hindi written in Latin script. */
function langKey(resp) {
  if (resp.lang === "hi" && resp.code_mixed) return "hinglish";
  return CONFIG.STRINGS[resp.lang] ? resp.lang : "en";
}

/** HTML lang attribute for an answer, so screen readers and fonts pick the right language. */
const htmlLang = { en: "en", hi: "hi", gu: "gu", hinglish: "hi-Latn" };

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

/** Answer text with every "[S1]" turned into a button that jumps to that passage card. */
function renderAnswerText(text, prefix) {
  const p = el("p", { class: "answer-text" });
  // WHY: split keeps the [S#] markers as separate parts, so the text around them stays plain text (no HTML injection).
  for (const part of text.split(/(\[S\d+\])/)) {
    const m = part.match(/^\[(S\d+)\]$/);
    if (!m) { p.append(part); continue; }
    p.append(el("button", {
      class: "cite-ref", type: "button", "aria-label": `Source ${m[1]}`,
      onclick: () => {
        const card = document.getElementById(`${prefix}-${m[1]}`);
        if (!card) return;
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        card.classList.add("flash");
        setTimeout(() => card.classList.remove("flash"), 1500);
      },
    }, `[${m[1]}]`));
  }
  return p;
}

/** One source passage card: id, scheme name, passage text, official link. */
function renderPassage(c, prefix, strings) {
  return el("article", { class: "passage", id: `${prefix}-${c.id}`, tabindex: "-1" },
    el("div", { class: "passage-head" },
      c.id ? el("span", { class: "passage-id" }, `[${c.id}]`) : null,
      el("span", {}, c.scheme_name || "")),
    el("p", { class: "passage-text" }, c.passage || c.text || ""),
    c.source_url
      ? el("a", { href: c.source_url, target: "_blank", rel: "noopener noreferrer" }, `${strings.openPage} ↗`)
      : null);
}

/** "Listen" button that reads the answer aloud in its language. */
function renderListenButton(text, key, strings) {
  if (!CONFIG.ENABLE_VOICE_OUTPUT || !ttsSupported()) return null;
  const note = el("p", { class: "toast", hidden: "" });
  const btn = el("button", {
    class: "btn btn-small", type: "button",
    onclick: () => {
      const r = speak(text, key);
      // FALLBACK: no voice installed for this language -> tell the user instead of failing silently.
      if (!r.ok) {
        note.textContent = r.reason === "no_voice"
          ? `No ${CONFIG.LANG_LABELS[key]} voice is installed in this browser.`
          : "This browser can't read text aloud.";
        note.hidden = false;
      }
    },
  }, `🔊 ${strings.listen}`);
  return el("div", {}, btn, note);
}

/** A normal answer, or a refusal, from a 200 response. */
function renderAnswer(resp) {
  const key = langKey(resp);
  const strings = CONFIG.STRINGS[key];
  const prefix = `a${++answerCount}`;
  const refused = Boolean(resp.refused);

  const card = el("article", { class: refused ? "card card-refused" : "card", lang: htmlLang[key] });
  const head = el("div", { class: "card-head" },
    el("span", { class: "lang-badge", title: "Detected language" }, CONFIG.LANG_LABELS[key]),
    renderListenButton(resp.answer || "", key, strings));
  card.append(head);

  if (refused) {
    // WHY: icon + title + colour, so a refusal is never mistaken for an answer (colour alone isn't enough).
    card.append(el("p", { class: "state-title" }, "⚠️ ", strings.refusedTitle));
  }
  card.append(renderAnswerText(resp.answer || "", prefix));

  const cites = resp.citations || [];
  if (cites.length) {
    const box = el("section", { class: "sources", "aria-label": strings.sources },
      el("p", { class: "sources-title" }, strings.sources));
    cites.forEach((c) => box.append(renderPassage(c, prefix, strings)));
    card.append(box);
  }
  if (!refused) {
    card.append(renderEligibilityButtons(cites, key, strings));
    card.append(el("p", { class: "disclaimer" }, strings.disclaimer.replace("{date}", CONFIG.DATA_AS_OF)));
  }
  if (typeof resp.latency_ms === "number") {
    card.append(el("p", { class: "meta" }, `${(resp.latency_ms / 1000).toFixed(1)} s`));
  }

  if (CONFIG.AUTO_SPEAK_ANSWERS && CONFIG.ENABLE_VOICE_OUTPUT) speak(resp.answer || "", key);
  return card;
}

/** The LLM is down but retrieval worked: show the official passages with a plain explanation. */
function renderFallbackPassages(body) {
  const strings = CONFIG.STRINGS.en;   // no detected language in a 503 body, so use English
  const prefix = `a${++answerCount}`;
  const card = el("article", { class: "card card-refused" },
    el("p", { class: "state-title" }, "⚠️ ", strings.aiUnavailable));
  const box = el("section", { class: "sources" });
  (body.fallback_passages || []).forEach((p, i) =>
    box.append(renderPassage({ ...p, id: p.id || `S${i + 1}` }, prefix, strings)));
  card.append(box);
  return card;
}

const ERROR_MESSAGES = {
  timeout: "The server took too long to answer. Please try again.",
  network: "Can't reach the server. Check the connection and try again.",
  server: "Something went wrong on the server. Please try again.",
  empty_query: "Please type or say a question.",
};

/** Network / timeout / server error: say what happened and how to recover. */
function renderError(err) {
  return el("article", { class: "card card-error", role: "alert" },
    el("p", { class: "state-title" }, "✖ ", ERROR_MESSAGES[err.kind] || err.message));
}

// ---------------------------------------------------------------------------
// Eligibility checklist (bonus): rules engine asks follow-ups, UI shows ✅/❌/❓
// ---------------------------------------------------------------------------

/** Scheme id behind a citation, or null. */
function schemeIdOf(c) {
  // MOCK: "scheme_id" in citations is an assumption, not yet in the /api/ask contract (to settle with comp/api
  // at integration). Fallback: the chunk_id prefix ("pm-kisan#benefits#0" -> "pm-kisan"), a naming convention only.
  return c.scheme_id || (c.chunk_id || "").split("#")[0] || null;
}

/** One "Check if I'm eligible for X" button per scheme cited in the answer. */
function renderEligibilityButtons(cites, key, strings) {
  if (!CONFIG.ENABLE_ELIGIBILITY) return null;
  const schemes = new Map();   // scheme id -> display name, in citation order, no duplicates
  for (const c of cites) {
    const id = schemeIdOf(c);
    if (id && !schemes.has(id)) schemes.set(id, c.scheme_name || id);
  }
  if (!schemes.size) return null;
  const row = el("div", { class: "elig-actions" });
  for (const [id, name] of schemes) {
    row.append(el("button", {
      class: "btn btn-small btn-elig", type: "button",
      // WHY: disable after one click so a double tap doesn't start two checklists.
      onclick: (e) => { e.currentTarget.disabled = true; startChecklist(id, name, key); },
    }, strings.checkEligibility.replace("{scheme}", name)));
  }
  return row;
}

const STATUS_ICON = { met: "✅", not_met: "❌", unknown: "❓" };

/** Draw the checklist card for one engine response; onAnswer(field, value) is called when the user answers. */
function renderChecklist(card, res, schemeName, strings, onAnswer) {
  card.replaceChildren(el("h3", { class: "elig-title" }, `${strings.eligibilityTitle}: ${schemeName}`));
  let firstControl = null;

  if (res.question) {
    const q = res.question;
    const box = el("div", { class: "elig-question" }, el("p", { class: "q-text" }, q.text));
    if (q.options.length) {
      const opts = el("div", { class: "options", role: "group", "aria-label": q.text });
      for (const o of q.options) {
        const b = el("button", { class: "btn chip-option", type: "button", onclick: () => onAnswer(q.field, o.value) }, o.label);
        firstControl = firstControl || b;
        opts.append(b);
      }
      box.append(opts);
    } else {
      // Empty options = the engine wants a number (e.g. age).
      const input = el("input", { type: "number", inputmode: "numeric", min: "0", class: "num-input", "aria-label": q.text });
      const form = el("form", { class: "options", onsubmit: (e) => {
        e.preventDefault();
        if (input.value !== "") onAnswer(q.field, Number(input.value));
      } }, input, el("button", { class: "btn btn-primary", type: "submit" }, strings.ok));
      firstControl = input;
      box.append(form);
    }
    card.append(box);
  } else {
    // WHY: words + icon, not colour alone, so the verdict is clear to colour-blind users and screen readers.
    card.append(el("p", { class: `verdict verdict-${res.verdict}`, role: "status" },
      strings.verdict[res.verdict] || res.verdict));
  }

  const list = el("ul", { class: "checklist" });
  for (const item of res.checklist) {
    list.append(el("li", { class: `check-${item.status}` },
      el("span", { class: "check-icon", "aria-hidden": "true" }, STATUS_ICON[item.status] || "❓"),
      el("span", { class: "check-text" }, item.criterion),
      el("span", { class: "check-status" }, strings.status[item.status] || item.status)));
  }
  card.append(list);

  const source = res.checklist.find((i) => i.source)?.source;
  if (source) card.append(el("a", { href: source, target: "_blank", rel: "noopener noreferrer", class: "elig-source" }, `${strings.openPage} ↗`));

  // WHY: move keyboard focus to the new question so keyboard and screen-reader users can answer straight away.
  if (firstControl) firstControl.focus({ preventScroll: true });
}

/** Run the follow-up loop for one scheme: ask, record the answer, ask again until the engine stops. */
function startChecklist(schemeId, schemeName, key) {
  const strings = CONFIG.STRINGS[key];
  const lang = CONFIG.ELIGIBILITY_LANG[key] || "en";
  const answers = {};   // lives only in this page: no personal data is stored (PLAN §4.6)
  const card = el("article", { class: "card card-elig", lang: htmlLang[lang] || "en" });
  els.log.append(card);

  const step = async () => {
    card.replaceChildren(el("p", { class: "thinking", "aria-busy": "true" }, strings.eligibilityTitle));
    try {
      const res = await eligibility(schemeId, answers, lang);
      renderChecklist(card, res, schemeName, strings, (field, value) => { answers[field] = value; step(); });
    } catch (err) {
      // FALLBACK: no criteria for this scheme yet, or the server is down -> say so; the answer above still stands.
      const msg = err.kind === "unknown_scheme" ? strings.noChecklist : (ERROR_MESSAGES[err.kind] || err.message);
      card.replaceChildren(el("p", { class: "state-title" }, "⚠️ ", msg));
    }
    scrollToBottom();
  };
  step();
}

// ---------------------------------------------------------------------------
// Asking a question
// ---------------------------------------------------------------------------

async function submitQuestion(text) {
  const q = text.trim();
  if (busy) return;
  if (!q) { els.query.focus(); return; }

  busy = true;
  els.send.disabled = true;
  els.log.append(el("div", { class: "msg-user" }, q));
  const pending = el("p", { class: "thinking", "aria-busy": "true" }, "Searching the scheme documents");
  els.log.append(pending);
  els.query.value = "";
  autoGrow();
  scrollToBottom();

  let node;
  try {
    node = renderAnswer(await ask(q, sessionId));
  } catch (err) {
    if (err instanceof ApiError && err.kind === "llm_unavailable") node = renderFallbackPassages(err.data);
    else {
      node = renderError(err instanceof ApiError ? err : new ApiError("server", String(err)));
      // FALLBACK: put the question back in the box so the user doesn't have to retype or re-speak it.
      els.query.value = q;
      autoGrow();
    }
  }
  pending.replaceWith(node);
  busy = false;
  els.send.disabled = false;
  scrollToBottom();
}

/** Let the textarea grow with its content up to the CSS max-height. */
function autoGrow() {
  els.query.style.height = "auto";
  // WHY: add the border width (offset - client), since box-sizing:border-box counts borders in the height.
  const border = els.query.offsetHeight - els.query.clientHeight;
  els.query.style.height = `${els.query.scrollHeight + border}px`;
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

function setupSamples() {
  for (const s of CONFIG.SAMPLE_QUESTIONS) {
    els.chips.append(el("button", { class: "chip", type: "button", onclick: () => submitQuestion(s) }, s));
  }
}

function setupLargeText() {
  let on = CONFIG.LARGE_TEXT_DEFAULT;
  // WHY: remember the choice per device; wrapped in try because storage can be blocked (private mode).
  try { const saved = localStorage.getItem("ys-large-text"); if (saved !== null) on = saved === "1"; } catch {}
  const apply = () => {
    document.documentElement.classList.toggle("large-text", on);
    els.largeText.setAttribute("aria-pressed", String(on));
  };
  apply();
  els.largeText.addEventListener("click", () => {
    on = !on;
    apply();
    try { localStorage.setItem("ys-large-text", on ? "1" : "0"); } catch {}
  });
}

function setupMic() {
  // FALLBACK: no speech recognition (e.g. Firefox) or switched off -> hide the mic; typing always works.
  if (!CONFIG.ENABLE_VOICE_INPUT || !sttSupported()) { els.micGroup.hidden = true; return; }
  els.micLang.value = CONFIG.DEFAULT_MIC_LANG;
  let stop = null;
  els.micBtn.addEventListener("click", () => {
    if (stop) { stop(); return; }   // second click stops listening
    els.micBtn.setAttribute("aria-pressed", "true");
    els.query.placeholder = "Listening…";
    stop = startListening(els.micLang.value, {
      // WHY: show the transcript in the box first, so a wrong recognition can be fixed before sending.
      onResult: (text) => { els.query.value = text; autoGrow(); els.query.focus(); },
      onError: (code) => {
        const msg = code === "not-allowed"
          ? "Microphone permission was denied. You can type instead."
          : "Couldn't hear that. Please try again or type your question.";
        els.log.append(renderError(new ApiError("voice", msg)));
        scrollToBottom();
      },
      onEnd: () => {
        stop = null;
        els.micBtn.setAttribute("aria-pressed", "false");
        els.query.placeholder = "Type your question… / अपना सवाल लिखें… / તમારો પ્રશ્ન લખો…";
      },
    });
  });
}

async function setupStatus() {
  if (CONFIG.USE_MOCK) {
    // MOCK: honest disclosure on screen, so nobody mistakes demo fixtures for real answers.
    els.pill.textContent = "Mock data";
    els.pill.className = "pill pill-mock";
    return;
  }
  const h = await health();
  if (!h) { els.pill.textContent = "Server unreachable"; els.pill.className = "pill pill-bad"; }
  else if (h.offline_mode) { els.pill.textContent = "Offline mode"; els.pill.className = "pill pill-mock"; }
  else if (h.llm === "down") { els.pill.textContent = "AI summary down"; els.pill.className = "pill pill-bad"; }
  else { els.pill.textContent = "Live"; els.pill.className = "pill pill-ok"; }
}

els.form.addEventListener("submit", (e) => { e.preventDefault(); submitQuestion(els.query.value); });
els.query.addEventListener("input", autoGrow);
// WHY: Enter sends (like a chat app); Shift+Enter adds a new line.
els.query.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitQuestion(els.query.value); }
});

setupSamples();
setupLargeText();
autoGrow();   // WHY: size the empty box to one line on load, otherwise it shows a needless scrollbar
setupMic();
setupStatus();

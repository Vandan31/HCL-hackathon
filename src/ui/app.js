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
import { ask, health, ApiError } from "./api.js";
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

/** Network / timeout / server error: say what happened and how to recover. */
function renderError(err) {
  const messages = {
    timeout: "The server took too long to answer. Please try again.",
    network: "Can't reach the server. Check the connection and try again.",
    server: "Something went wrong on the server. Please try again.",
    empty_query: "Please type or say a question.",
  };
  return el("article", { class: "card card-error", role: "alert" },
    el("p", { class: "state-title" }, "✖ ", messages[err.kind] || err.message));
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

/**
 * COMPONENT : ui
 * PURPOSE   : Wire the app: language picker first, then send questions, render answers with [S1] links to
 *             source passage cards, show refusals and errors clearly, run the eligibility checklist, and handle
 *             voice and large-text mode. Every word on screen comes from CONFIG.STRINGS in the picked language.
 * INPUTS    : user actions on src/ui/index.html
 * OUTPUTS   : DOM updates
 * DEPENDS ON: src/ui/api.js, src/ui/voice.js, config/ui.js
 * PANEL NOTE: Every answer is shown with its proof (the passage and link); a refusal looks visibly different from an answer.
 */

import { CONFIG } from "../../config/ui.js";
import { ask, eligibility, health, ApiError } from "./api.js";
import { ensureMicPermission, sttSupported, ttsSupported, startListening, speak } from "./voice.js";
import { startLanding3D } from "./landing3d.js";   // small; Three.js itself loads only when the landing page shows

const $ = (id) => document.getElementById(id);
const els = {
  log: $("chat-log"), form: $("ask-form"), query: $("query"), send: $("send-btn"),
  chips: $("sample-chips"), pill: $("status-pill"), largeText: $("large-text-toggle"),
  micGroup: $("mic-group"), micBtn: $("mic-btn"), micLang: $("mic-lang"),
  pickerForm: $("picker-form"), pickerSelect: $("picker-select"), pickerContinue: $("picker-continue"),
  headerLang: $("header-lang"),
  picker: $("lang-picker"), srStatus: $("sr-status"), landingCanvas: $("landing-canvas"),
};

// WHY: the API contract asks for a session_id so follow-up questions can share context later.
let sessionId = newSessionId();
let uiLang = null;        // language picked on the opening page: "en" | "hi" | "gu"
let statusKey = null;     // which server-status text the pill shows (re-translated when the language changes)
let answerCount = 0;      // gives each answer's passage cards unique element ids
let busy = false;
let lastInputWasVoice = false;   // true when the current question came from the mic (its answer will be spoken)

function newSessionId() {
  return (crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
}

/** All UI text for the picked language. */
const S = () => CONFIG.STRINGS[uiLang] || CONFIG.STRINGS.en;

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

/** Which language an ANSWER is in (for its badge and voice): Hinglish is Hindi written in Latin script. */
function answerLang(resp) {
  if (resp.lang === "hi" && resp.code_mixed) return "hinglish";
  return CONFIG.LANG_LABELS[resp.lang] ? resp.lang : "en";
}

/** HTML lang attribute values, so screen readers and fonts pick the right language. */
const htmlLang = { en: "en", hi: "hi", gu: "gu", hinglish: "hi-Latn" };

/** "2026-10-27" -> the date written in the page language (month names in Gujarati/Hindi). */
function formatDate(iso) {
  // WHY: noon UTC so the day can't shift in any time zone; FALLBACK: show the raw text if the browser can't format.
  try {
    return new Intl.DateTimeFormat(`${uiLang}-IN`, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
      .format(new Date(`${iso}T12:00:00Z`));
  } catch {
    return iso;
  }
}

// WHY: people who turn on "reduce motion" (vestibular disorders) get instant jumps instead of smooth scrolling.
const scrollBehavior = () =>
  (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: scrollBehavior() });
}

/** A decorative symbol (emoji/arrow) that screen readers skip, so they don't read "speaker high volume". */
const icon = (ch) => el("span", { "aria-hidden": "true" }, ch);

/** Link that opens in a new tab, with a hidden "opens in a new tab" note for screen-reader users. */
function externalLink(href, text, cls) {
  return el("a", { href, target: "_blank", rel: "noopener noreferrer", ...(cls ? { class: cls } : {}) },
    text, " ", icon("↗"), el("span", { class: "visually-hidden" }, ` (${S().newTab})`));
}

/** Guess the HTML lang of a piece of text from its script, so screen readers use the right voice. */
function textLang(text) {
  if (/[઀-૿]/.test(text)) return "gu";
  if (/[ऀ-ॿ]/.test(text)) return "hi";
  // Latin script on a Hindi or Gujarati page is almost always Hinglish (romanised Hindi).
  return uiLang === "en" ? "en" : "hi-Latn";
}

/** Say something to screen-reader users only (through the hidden live region in index.html). */
function announce(message) {
  // WHY: clear first, so repeating the same message ("Listening…" twice) is still announced.
  els.srStatus.textContent = "";
  setTimeout(() => { els.srStatus.textContent = message; }, 50);
}

// ---------------------------------------------------------------------------
// Language: picker on the opening page, and translating the static page
// ---------------------------------------------------------------------------

/** Put the picked language's words into every element marked data-i18n / data-i18n-attr in index.html. */
function applyLanguage() {
  const s = S();
  document.documentElement.lang = uiLang;
  document.title = s.appName;
  document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = s[node.dataset.i18n] ?? ""; });
  document.querySelectorAll("[data-i18n-attr]").forEach((node) => {
    for (const pair of node.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":");
      node.setAttribute(attr, s[key] ?? "");
    }
  });
  els.headerLang.value = uiLang;   // the header dropdown always shows the current language

  // Example questions in the picked language (lang per chip: some are Hinglish on a Hindi page).
  els.chips.replaceChildren(...(CONFIG.SAMPLE_QUESTIONS[uiLang] || []).map((q) =>
    el("button", { class: "chip", type: "button", lang: textLang(q), onclick: () => submitQuestion(q) }, q)));

  // WHY: people usually speak the language they picked, so the mic starts there (they can still switch).
  els.micLang.value = uiLang;
  renderStatusPill();
}

/** One <option> per language, each written in its own script so anyone can find theirs. */
const languageOptions = (langs) =>
  langs.map((l) => el("option", { value: l, lang: l }, CONFIG.LANG_LABELS[l]));

/** The Continue button speaks the language currently chosen in the opening dropdown. */
function updateContinueButton() {
  const lang = els.pickerSelect.value;
  els.pickerContinue.textContent = (CONFIG.STRINGS[lang] || CONFIG.STRINGS.en).continue;
  els.pickerContinue.lang = lang;
}

let stopLanding3D = null;   // stop() for the floating syllables while the landing page is open

/** Show the opening page: a language dropdown and a Continue button, with floating syllables behind it. */
function showPicker() {
  document.body.classList.add("picking");
  els.picker.hidden = false;
  updateContinueButton();
  els.pickerSelect.focus();
  if (CONFIG.ENABLE_3D_LANDING && !stopLanding3D) {
    startLanding3D(els.landingCanvas).then((stop) => {
      // WHY: if a language was chosen before Three.js finished loading, shut it down straight away.
      if (stop && !document.body.classList.contains("picking")) stop();
      else stopLanding3D = stop;
    }).catch(() => {});   // FALLBACK: any 3D error -> the plain landing page, which already works
  }
}

/** User picked a language: translate the page and open the app. */
function chooseLanguage(lang) {
  // WHY: a new language starts a fresh conversation, so old cards in another language don't linger on screen.
  if (uiLang && uiLang !== lang) {
    els.log.replaceChildren();
    sessionId = newSessionId();
  }
  uiLang = lang;
  try { localStorage.setItem("ys-lang", lang); } catch {}
  applyLanguage();
  closePicker();
}

/** Hide the picker and return to the app (the `hidden` attribute keeps only one <main> in the page at a time). */
function closePicker() {
  document.body.classList.remove("picking");
  els.picker.hidden = true;
  // WHY: free the GPU and stop the animation loop, so the chat screen stays fast on low-end phones.
  if (stopLanding3D) { stopLanding3D(); stopLanding3D = null; }
  autoGrow();   // WHY: the box can only be measured once visible; sizes it to one line (no needless scrollbar)
  els.query.focus();
}

function setupLanguage() {
  // Three dropdowns share the same list: opening page, header, and the mic's spoken-language menu.
  els.pickerSelect.replaceChildren(...languageOptions(CONFIG.UI_LANGUAGES));
  els.headerLang.replaceChildren(...languageOptions(CONFIG.UI_LANGUAGES));
  els.micLang.replaceChildren(...languageOptions(["en", "hi", "gu"]));

  els.pickerSelect.addEventListener("change", updateContinueButton);
  els.pickerForm.addEventListener("submit", (e) => { e.preventDefault(); chooseLanguage(els.pickerSelect.value); });
  // WHY: switching in the header applies at once (no extra click); it starts a fresh conversation in that language.
  els.headerLang.addEventListener("change", () => {
    chooseLanguage(els.headerLang.value);
    els.headerLang.focus();   // keep keyboard focus on the dropdown the user just used
  });

  let saved = null;
  if (CONFIG.REMEMBER_LANGUAGE) {
    // WHY: wrapped in try because storage can be blocked (private mode); then we just show the picker.
    try { saved = localStorage.getItem("ys-lang"); } catch {}
  }
  if (saved && CONFIG.UI_LANGUAGES.includes(saved)) chooseLanguage(saved);
  else showPicker();
}

// ---------------------------------------------------------------------------
// Rendering answers
// ---------------------------------------------------------------------------

/** Answer text with every "[S1]" turned into a button that jumps to that passage card. */
function renderAnswerText(text, prefix, lang) {
  const p = el("p", { class: "answer-text", lang: htmlLang[lang] });
  // WHY: split keeps the [S#] markers as separate parts, so the text around them stays plain text (no HTML injection).
  for (const part of text.split(/(\[S\d+\])/)) {
    const m = part.match(/^\[(S\d+)\]$/);
    if (!m) { p.append(part); continue; }
    p.append(el("button", {
      class: "cite-ref", type: "button", "aria-label": `${S().sources} ${m[1]}`,
      onclick: () => {
        const card = document.getElementById(`${prefix}-${m[1]}`);
        if (!card) return;
        card.scrollIntoView({ behavior: scrollBehavior(), block: "center" });
        card.focus({ preventScroll: true });   // WHY: keyboard/screen-reader users land on the passage too, not just sighted users
        card.classList.add("flash");
        setTimeout(() => card.classList.remove("flash"), 1500);
      },
    }, `[${m[1]}]`));
  }
  return p;
}

/** One source passage card: id, scheme name, passage text, official link. */
function renderPassage(c, prefix) {
  return el("article", { class: "passage", id: `${prefix}-${c.id}`, tabindex: "-1" },
    el("div", { class: "passage-head" },
      c.id ? el("span", { class: "passage-id" }, `[${c.id}]`) : null,
      el("span", {}, c.scheme_name || "")),
    el("p", { class: "passage-text" }, c.passage || c.text || ""),
    c.source_url ? externalLink(c.source_url, S().openPage) : null);
}

/** "Listen" button that reads the answer aloud in the answer's language. */
function renderListenButton(text, lang) {
  if (!CONFIG.ENABLE_VOICE_OUTPUT || !ttsSupported()) return null;
  const note = el("p", { class: "toast", hidden: "" });
  const btn = el("button", {
    class: "btn btn-small", type: "button",
    onclick: () => {
      const r = speak(text, lang);
      // FALLBACK: no voice installed for this language -> tell the user instead of failing silently.
      if (!r.ok) {
        note.textContent = r.reason === "no_voice"
          ? S().errors.noVoice.replace("{lang}", CONFIG.LANG_LABELS[lang])
          : S().errors.noTts;
        note.hidden = false;
      }
    },
  }, icon("🔊 "), S().listen);
  return el("div", {}, btn, note);
}

/** A normal answer, or a refusal, from a 200 response. Labels in the page language, answer in its own. */
function renderAnswer(resp) {
  const s = S();
  const lang = answerLang(resp);
  const prefix = `a${++answerCount}`;
  const refused = Boolean(resp.refused);

  const card = el("article", { class: refused ? "card card-refused" : "card" });
  card.append(el("div", { class: "card-head" },
    el("span", { class: "lang-badge", title: s.detectedLanguage }, CONFIG.LANG_LABELS[lang]),
    renderListenButton(resp.answer || "", lang)));

  if (refused) {
    // WHY: icon + title + colour, so a refusal is never mistaken for an answer (colour alone isn't enough).
    card.append(el("p", { class: "state-title" }, icon("⚠️"), s.refusedTitle));
  }
  card.append(renderAnswerText(resp.answer || "", prefix, lang));

  const cites = resp.citations || [];
  if (cites.length) {
    const box = el("section", { class: "sources", "aria-label": s.sources },
      el("p", { class: "sources-title" }, s.sources));
    cites.forEach((c) => box.append(renderPassage(c, prefix)));
    card.append(box);
  }
  if (!refused) {
    card.append(renderEligibilityButtons(cites));
    card.append(el("p", { class: "disclaimer" }, s.disclaimer.replace("{date}", formatDate(CONFIG.DATA_AS_OF))));
  }
  if (typeof resp.latency_ms === "number") {
    card.append(el("p", { class: "meta" }, `${(resp.latency_ms / 1000).toFixed(1)} s`));
  }

  if (CONFIG.AUTO_SPEAK_ANSWERS && CONFIG.ENABLE_VOICE_OUTPUT) speak(resp.answer || "", lang);
  return card;
}

/** The LLM is down but retrieval worked: show the official passages with a plain explanation. */
function renderFallbackPassages(body) {
  const prefix = `a${++answerCount}`;
  const card = el("article", { class: "card card-refused" },
    el("p", { class: "state-title" }, icon("⚠️"), S().aiUnavailable));
  const box = el("section", { class: "sources" });
  (body.fallback_passages || []).forEach((p, i) =>
    box.append(renderPassage({ ...p, id: p.id || `S${i + 1}` }, prefix)));
  card.append(box);
  return card;
}

/** Network / timeout / server / voice error, in the page language. */
function renderError(kindOrMessage) {
  const text = S().errors[kindOrMessage] || kindOrMessage;
  return el("article", { class: "card card-error", role: "alert" },
    el("p", { class: "state-title" }, icon("✖"), text));
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
function renderEligibilityButtons(cites) {
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
      onclick: (e) => { e.currentTarget.disabled = true; startChecklist(id, name); },
    }, S().checkEligibility.replace("{scheme}", name)));
  }
  return row;
}

const STATUS_ICON = { met: "✅", not_met: "❌", unknown: "❓" };

/** Draw the checklist card for one engine response; onAnswer(field, value) is called when the user answers. */
function renderChecklist(card, res, schemeName, onAnswer) {
  const s = S();
  // WHY h2: the page's only h1 is the app name, so h2 keeps the heading outline without a skipped level.
  card.replaceChildren(el("h2", { class: "elig-title" }, `${s.eligibilityTitle}: ${schemeName}`));
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
      } }, input, el("button", { class: "btn btn-primary", type: "submit" }, s.ok));
      firstControl = input;
      box.append(form);
    }
    card.append(box);
  } else {
    // WHY: words + icon, not colour alone, so the verdict is clear to colour-blind users and screen readers.
    // tabindex=-1 lets us move focus here: the answer buttons just disappeared, and focus must not fall to the page top.
    firstControl = el("p", { class: `verdict verdict-${res.verdict}`, role: "status", tabindex: "-1" },
      s.verdict[res.verdict] || res.verdict);
    card.append(firstControl);
  }

  const list = el("ul", { class: "checklist" });
  for (const item of res.checklist) {
    list.append(el("li", { class: `check-${item.status}` },
      el("span", { class: "check-icon", "aria-hidden": "true" }, STATUS_ICON[item.status] || "❓"),
      el("span", { class: "check-text" }, item.criterion),
      el("span", { class: "check-status" }, s.status[item.status] || item.status)));
  }
  card.append(list);

  const source = res.checklist.find((i) => i.source)?.source;
  if (source) card.append(externalLink(source, s.openPage, "elig-source"));

  // WHY: move keyboard focus to the new question (or the verdict) so keyboard and screen-reader users continue from there.
  if (firstControl) firstControl.focus({ preventScroll: true });
}

/** Run the follow-up loop for one scheme in the page language: ask, record the answer, repeat until the engine stops. */
function startChecklist(schemeId, schemeName) {
  const lang = uiLang;
  const answers = {};   // lives only in this page: no personal data is stored (PLAN §4.6)
  const card = el("article", { class: "card card-elig" });
  els.log.append(card);

  const step = async () => {
    card.replaceChildren(el("p", { class: "thinking", "aria-busy": "true" }, S().eligibilityTitle));
    try {
      const res = await eligibility(schemeId, answers, lang);
      renderChecklist(card, res, schemeName, (field, value) => { answers[field] = value; step(); });
    } catch (err) {
      // FALLBACK: no criteria for this scheme yet, or the server is down -> say so; the answer above still stands.
      const msg = err.kind === "unknown_scheme" ? S().noChecklist : (S().errors[err.kind] || err.message);
      card.replaceChildren(el("p", { class: "state-title" }, icon("⚠️"), msg));
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
  els.log.append(el("div", { class: "msg-user", lang: textLang(q) }, q));
  const pending = el("p", { class: "thinking", "aria-busy": "true" }, S().thinking);
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
      node = renderError(err instanceof ApiError ? err.kind : "server");
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
  // WHY: only show a scrollbar once the box hits its max height; sub-pixel rounding otherwise shows a useless one.
  els.query.style.overflowY = els.query.scrollHeight + border > els.query.offsetHeight + 1 ? "auto" : "hidden";
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

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
    autoGrow();   // WHY: bigger text means a taller line; resize the question box so it doesn't show a scrollbar
    try { localStorage.setItem("ys-large-text", on ? "1" : "0"); } catch {}
  });
}

// Recognition error code -> message key in CONFIG.STRINGS[lang].errors.
const MIC_ERRORS = {
  "not-allowed": "micDenied", "service-not-allowed": "micDenied", "audio-capture": "micNoDevice",
  "network": "micNetwork", "no-speech": "micNoSpeech", "start-timeout": "micTimeout",
  "language-not-supported": "micLanguage",
};

/** Show the mic's state: "idle" | "asking" (waiting for permission) | "starting" (allowed, mic warming up)
 *  | "listening" (really capturing audio). */
function setMicState(state) {
  els.micBtn.dataset.state = state;
  els.micBtn.setAttribute("aria-pressed", String(state !== "idle"));
  const text = { asking: S().micAsk, starting: S().micStarting, listening: S().listening };
  els.query.placeholder = text[state] || S().placeholder;
}

function setupMic() {
  if (!CONFIG.ENABLE_VOICE_INPUT) { els.micGroup.hidden = true; return; }
  let stop = null, busyMic = false;

  const showMicError = (key) => { els.log.append(renderError(key)); scrollToBottom(); };

  els.micBtn.addEventListener("click", async () => {
    if (stop) { stop(); return; }    // second press = stop listening and keep what was heard
    if (busyMic) return;             // already asking for permission
    // FALLBACK: browser without speech recognition (e.g. Firefox) -> say so instead of a dead button.
    if (!sttSupported()) { showMicError("micUnsupported"); return; }

    busyMic = true;
    setMicState("asking");
    announce(S().micAsk);            // WHY: tell screen-reader users too, not only the placeholder
    const permission = await ensureMicPermission();
    if (permission !== "granted") {
      busyMic = false;
      setMicState("idle");
      showMicError(permission === "no_device" ? "micNoDevice" : permission === "unsupported" ? "micUnsupported" : "micDenied");
      return;
    }

    // WHY: the real mic took over a second to start after permission (measured); don't keep saying "allow it".
    setMicState("starting");
    const before = els.query.value;  // restored if nothing is heard, so typed text is never lost
    stop = startListening(els.micLang.value, {
      onAudioStart: () => { setMicState("listening"); announce(S().listening); },
      // WHY: words appear while the person speaks, greyed until final, so they can see they are heard.
      onInterim: (text) => { els.query.value = text; els.query.classList.add("interim"); autoGrow(); },
      onResult: (text) => {
        els.query.classList.remove("interim");
        els.query.value = text;
        autoGrow();
        announce(text);
        lastInputWasVoice = true;    // the answer to a spoken question will be spoken too (UI wiring, component 10)
        // DEMO-KNOB VOICE_AUTO_SEND: by default the person checks the text and presses Ask (wrong words can be fixed).
        if (CONFIG.VOICE_AUTO_SEND) submitQuestion(text); else els.query.focus();
      },
      onError: (code) => { if (code !== "aborted") showMicError(MIC_ERRORS[code] || "micFailed"); },
      onEnd: () => {
        stop = null;
        busyMic = false;
        els.query.classList.remove("interim");
        if (!els.query.value.trim()) els.query.value = before;
        setMicState("idle");
      },
    });
  });
}

/** Translate and colour the server-status pill from the last known status. */
function renderStatusPill() {
  const classes = { mock: "pill-mock", offline: "pill-mock", live: "pill-ok", aiDown: "pill-bad", unreachable: "pill-bad" };
  els.pill.textContent = statusKey ? S().pill[statusKey] : "";
  els.pill.className = `pill ${classes[statusKey] || ""}`;
}

async function setupStatus() {
  if (CONFIG.USE_MOCK) {
    // MOCK: honest disclosure on screen, so nobody mistakes demo fixtures for real answers.
    statusKey = "mock";
  } else {
    const h = await health();
    statusKey = !h ? "unreachable" : h.offline_mode ? "offline" : h.llm === "down" ? "aiDown" : "live";
  }
  if (uiLang) renderStatusPill();
}

els.form.addEventListener("submit", (e) => { e.preventDefault(); submitQuestion(els.query.value); });
els.query.addEventListener("input", () => { lastInputWasVoice = false; autoGrow(); });   // typing = not a spoken question
// WHY: Enter sends (like a chat app); Shift+Enter adds a new line.
els.query.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitQuestion(els.query.value); }
});

setupLargeText();
setupMic();
setupStatus();
setupLanguage();

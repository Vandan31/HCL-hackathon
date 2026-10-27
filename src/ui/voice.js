/**
 * COMPONENT : ui (voice)
 * PURPOSE   : Speech in (mic -> text) and speech out (answer -> audio) using the browser's free Web Speech API.
 * INPUTS    : a language code (en | hi | gu | hinglish), text to speak
 * OUTPUTS   : recognised text via callbacks; audio through the speakers
 * DEPENDS ON: config/ui.js (SPEECH_LANG); browser support (Chrome/Edge best, Firefox has no speech recognition)
 * PANEL NOTE: Voice is for users who can't comfortably type or read; it costs nothing and needs no API key.
 */

import { CONFIG } from "../../config/ui.js";

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

/** True if this browser can turn speech into text. */
export function sttSupported() {
  return Boolean(Recognition);
}

/** True if this browser can read text aloud. */
export function ttsSupported() {
  return "speechSynthesis" in window;
}

/**
 * Start listening once. Calls onResult(text) with the final transcript, onEnd() when the mic stops,
 * onError(code) on failure (e.g. "not-allowed" when mic permission is denied). Returns a stop() function.
 */
export function startListening(langKey, { onResult, onEnd, onError }) {
  const rec = new Recognition();
  rec.lang = CONFIG.SPEECH_LANG[langKey] || "en-IN";
  rec.interimResults = false;   // WHY: only the final text; partial guesses would flicker in the box
  rec.maxAlternatives = 1;
  rec.onresult = (e) => onResult(e.results[0][0].transcript);
  // FALLBACK: any recognition error -> caller shows a message and the text box still works.
  rec.onerror = (e) => onError(e.error);
  rec.onend = () => onEnd();
  rec.start();
  return () => rec.stop();
}

// WHY: browsers load their voice list asynchronously; the first getVoices() call is often empty.
let voices = [];
function refreshVoices() { voices = window.speechSynthesis.getVoices(); }
if (ttsSupported()) {
  refreshVoices();
  window.speechSynthesis.onvoiceschanged = refreshVoices;
}

/** Remove citation markers like [S1] so they aren't read aloud as "S one". */
export function cleanForSpeech(text) {
  return text.replace(/\s*\[S\d+\]/g, "");
}

/**
 * Read text aloud in the given language. Returns {ok: true} or {ok: false, reason: "unsupported" | "no_voice"}.
 */
export function speak(text, langKey) {
  if (!ttsSupported()) return { ok: false, reason: "unsupported" };
  const tag = (CONFIG.SPEECH_LANG[langKey] || "en-IN").toLowerCase();
  const base = tag.slice(0, 2);
  const norm = (v) => v.lang.replace("_", "-").toLowerCase();
  // Prefer an exact match (gu-IN), then any voice of the same language (gu-*).
  const voice = voices.find((v) => norm(v) === tag) || voices.find((v) => norm(v).startsWith(base));
  // FALLBACK: no Gujarati/Hindi voice installed -> say so instead of reading it with an English voice,
  // which would be unintelligible.
  if (!voice && base !== "en") return { ok: false, reason: "no_voice" };

  window.speechSynthesis.cancel();   // stop anything already playing
  const utter = new SpeechSynthesisUtterance(cleanForSpeech(text));
  utter.lang = tag;
  if (voice) utter.voice = voice;
  window.speechSynthesis.speak(utter);
  return { ok: true };
}

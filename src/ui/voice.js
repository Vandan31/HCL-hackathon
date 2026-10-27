/**
 * COMPONENT : ui (voice)
 * PURPOSE   : Speech in (mic -> text) and speech out (answer -> audio) using the browser's free Web Speech API.
 * INPUTS    : a language code (en | hi | gu | hinglish), text to speak
 * OUTPUTS   : recognised text via callbacks; audio through the speakers
 * DEPENDS ON: config/ui.js (SPEECH_LANG); browser support (Chrome/Edge best, Firefox has no speech recognition)
 * PANEL NOTE: Voice is for users who can't comfortably type or read; it costs nothing and needs no API key.
 */

import { CONFIG } from "../../config/ui.js";

// WHY looked up on each use (not once at load): works if the engine appears late, and lets tests swap in a fake.
const getRecognition = () => window.SpeechRecognition || window.webkitSpeechRecognition;

/** True if this browser can turn speech into text. */
export function sttSupported() {
  return Boolean(getRecognition());
}

/** True if this browser can read text aloud. */
export function ttsSupported() {
  return "speechSynthesis" in window;
}

/**
 * Make sure we may use the microphone BEFORE starting recognition.
 * Returns "granted" | "denied" | "no_device" | "unsupported".
 * WHY: started directly, Chrome silently waits on its small "Allow microphone?" bubble while the page looks
 * frozen (measured: no event at all for 6 s). Asking first lets the UI tell the user what to do.
 */
export async function ensureMicPermission() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return "unsupported";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop());   // only checking access; recognition opens its own stream
    return "granted";
  } catch (e) {
    if (e.name === "NotAllowedError" || e.name === "SecurityError") return "denied";
    if (e.name === "NotFoundError" || e.name === "OverconstrainedError") return "no_device";
    return "denied";
  }
}

/**
 * Listen once in `langKey`. Callbacks:
 *   onAudioStart()      the mic is really capturing (only now show "Listening…")
 *   onInterim(text)     words so far, while the person is still speaking
 *   onResult(text)      the final transcript
 *   onError(code)       "no-speech" | "audio-capture" | "not-allowed" | "network" | "language-not-supported" | "start-timeout" | ...
 *   onEnd()             the mic has stopped (always called last)
 * Returns stop(), which ends listening and keeps what was heard so far.
 */
export function startListening(langKey, { onAudioStart, onInterim, onResult, onError, onEnd }) {
  const Recognition = getRecognition();
  const rec = new Recognition();
  rec.lang = CONFIG.SPEECH_LANG[langKey] || "en-IN";
  // WHY interim results: people need to SEE that they are being heard; words appear as they speak.
  rec.interimResults = true;
  rec.maxAlternatives = 1;
  let started = false, finalText = "";
  rec.onaudiostart = () => { started = true; onAudioStart && onAudioStart(); };
  rec.onresult = (e) => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i];
      if (r.isFinal) finalText += r[0].transcript;
      else interim += r[0].transcript;
    }
    if (interim && onInterim) onInterim((finalText + " " + interim).trim());
  };
  // FALLBACK: any recognition error -> the caller shows a clear message; the text box always still works.
  rec.onerror = (e) => onError && onError(e.error);
  rec.onend = () => {
    clearTimeout(timer);
    if (finalText.trim()) onResult(finalText.trim());
    onEnd && onEnd();
  };
  // WHY: if audio never starts (blocked device, stuck prompt), stop instead of looking frozen forever.
  const timer = setTimeout(() => {
    if (!started) { onError && onError("start-timeout"); try { rec.abort(); } catch (e) { /* already stopped */ } }
  }, CONFIG.MIC_START_TIMEOUT_MS);
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

// ---------------------------------------------------------------------------
// IndicTTS (component 10): the team's own speech service, src/tts/server.py
// ---------------------------------------------------------------------------

let currentAudio = null;   // the answer playing now; a new one (or Stop) ends it

/** Stop any answer that is being read aloud (IndicTTS audio or browser voice). */
export function stopSpeaking() {
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  if (ttsSupported()) window.speechSynthesis.cancel();
}

/**
 * Read an answer aloud, preferring the IndicTTS service (AI4Bharat voices chosen by ear: D-020).
 * langKey: "en" | "hi" | "gu" | "hinglish". Hinglish is sent as "hi"; the service converts it to Devanagari.
 * onEnd() is called when playback finishes or is stopped.
 * Returns {ok: true, via: "indictts" | "browser"} or {ok: false, reason: "no_voice" | "unsupported"}.
 */
export async function speakAnswer(text, langKey, { onEnd } = {}) {
  stopSpeaking();
  if (CONFIG.USE_INDIC_TTS) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), CONFIG.TTS_TIMEOUT_MS);
    try {
      const res = await fetch(`${CONFIG.TTS_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, lang: langKey === "hinglish" ? "hi" : langKey }),
        signal: ctrl.signal,
      });
      if (res.ok) {
        const url = URL.createObjectURL(await res.blob());
        const audio = new Audio(url);
        currentAudio = audio;
        const done = () => { URL.revokeObjectURL(url); if (currentAudio === audio) currentAudio = null; onEnd && onEnd(); };
        audio.onended = done;
        audio.onpause = () => { if (audio.currentTime < audio.duration) done(); };   // stopped early
        await audio.play();
        return { ok: true, via: "indictts" };
      }
      // FALLBACK: 422 (e.g. Marathi/Tamil not in IndicTTS here) or 503 (model failed) -> browser voice below.
    } catch (e) {
      // FALLBACK: speech service not running, slow, or blocked -> browser voice below.
    } finally {
      clearTimeout(timer);
    }
  }
  const r = speak(text, langKey);
  if (r.ok) {
    // The browser voice has no reliable "finished" event across browsers; poll until it stops talking.
    const poll = setInterval(() => { if (!window.speechSynthesis.speaking) { clearInterval(poll); onEnd && onEnd(); } }, 250);
    return { ok: true, via: "browser" };
  }
  onEnd && onEnd();
  return r;
}

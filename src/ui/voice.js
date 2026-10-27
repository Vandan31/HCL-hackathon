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

let currentAudio = null;   // the sentence playing now
let playback = 0;          // bumped by every new answer and by Stop, so an older sentence loop knows to quit

/** Stop any answer that is being read aloud (IndicTTS audio or browser voice). */
export function stopSpeaking() {
  playback++;
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  if (ttsSupported()) window.speechSynthesis.cancel();
}

/**
 * Split an answer into sentences for the voice. Very short pieces are joined to the previous one,
 * so the voice doesn't pause every few words.
 * WHY sentences: a real 7-sentence Gujarati answer took 36 s to synthesise in one go (measured), all before the
 * first word; one sentence takes a few seconds, and the next is made while this one plays.
 */
export function splitSentences(text) {
  const clean = text.replace(/\s*\[S\d+\]/g, "");
  // Split after . ! ? or the Hindi danda when a space follows ("1.5 lakh" stays whole), and at line breaks.
  const parts = clean.split(/(?<=[.!?।])\s+|\n+/).map((x) => x.trim()).filter(Boolean);
  const out = [];
  for (const part of parts) {
    if (out.length && out[out.length - 1].length < CONFIG.TTS_MIN_CHUNK_CHARS) out[out.length - 1] += " " + part;
    else out.push(part);
  }
  return out;
}

/** Ask the IndicTTS service for one sentence. Returns an audio Blob, or null (service off, slow, 422/503). */
async function fetchSentence(text, lang) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), CONFIG.TTS_TIMEOUT_MS);
  try {
    const res = await fetch(`${CONFIG.TTS_BASE}/api/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang }),
      signal: ctrl.signal,
    });
    return res.ok ? await res.blob() : null;   // FALLBACK: 422 (e.g. mr/ta) or 503 -> caller uses the browser voice
  } catch (e) {
    return null;                               // FALLBACK: service not running, too slow, or blocked
  } finally {
    clearTimeout(timer);
  }
}

/** Play one sentence; resolves when it ends, is stopped, or can't play. */
function playBlob(blob, id) {
  return new Promise((resolve) => {
    if (id !== playback) return resolve();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentAudio = audio;
    const finish = () => { URL.revokeObjectURL(url); resolve(); };
    audio.onended = finish;
    audio.onpause = finish;                    // Stop pressed (pause) also ends this sentence
    audio.play().catch(finish);                // e.g. the browser blocked autoplay
  });
}

/**
 * Read an answer aloud, preferring the IndicTTS service (AI4Bharat voices chosen by ear: D-020), sentence by
 * sentence: the first sentence plays after a few seconds and the next one is made while it plays.
 * langKey: "en" | "hi" | "gu" | "hinglish" (sent as "hi"; the service converts it to Devanagari).
 * onEnd() is called when the whole answer finishes or is stopped.
 * Returns {ok: true, via: "indictts" | "browser"} or {ok: false, reason: "no_voice" | "unsupported"}.
 */
export async function speakAnswer(text, langKey, { onEnd } = {}) {
  stopSpeaking();
  const id = playback;
  if (CONFIG.USE_INDIC_TTS) {
    const lang = langKey === "hinglish" ? "hi" : langKey;
    const sentences = splitSentences(text);
    const first = sentences.length ? await fetchSentence(sentences[0], lang) : null;
    if (id !== playback) { onEnd && onEnd(); return { ok: true, via: "indictts" }; }   // stopped while loading
    if (first) {
      (async () => {
        let blob = first;
        for (let i = 0; i < sentences.length && blob && id === playback; i++) {
          // Make the NEXT sentence while this one plays, so there is (almost) no gap between them.
          const ahead = i + 1 < sentences.length ? fetchSentence(sentences[i + 1], lang) : Promise.resolve(null);
          await playBlob(blob, id);
          blob = id === playback ? await ahead : null;   // FALLBACK: a later sentence failed -> stop quietly
        }
        if (id === playback) currentAudio = null;
        onEnd && onEnd();
      })();
      return { ok: true, via: "indictts" };
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

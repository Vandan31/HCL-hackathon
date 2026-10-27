"""
COMPONENT : tts
PURPOSE   : Load AI4Bharat IndicTTS (FastPitch + HiFi-GAN) once per language and turn text into WAV audio, reusing
            audio already made for the same text.
INPUTS    : text, language ("gu" | "hi" | "en"), speaker ("female" | "male"). Hinglish = "hi" in Latin letters.
OUTPUTS   : WAV bytes (22,050 Hz mono) and whether it came from the cache
DEPENDS ON: coqui-tts + torch (see src/tts/requirements.txt), checkpoints in config.tts.CHECKPOINT_DIR,
            src/tts/normalize.py, config/tts.py
PANEL NOTE: FastPitch makes a whole sentence in one pass, so on a laptop CPU it speaks ~3x faster than real time
            (measured: 3.6 s for 10.5 s of Gujarati audio); repeated answers come from the cache instantly.
"""
import hashlib
import io
import json
import threading
import time
import unicodedata
from collections import OrderedDict

import soundfile as sf

from config.tts import (CACHE_DIR, CHECKPOINT_DIR, DEFAULT_SPEAKER, HINGLISH_DEFAULT_SPEAKER, HINGLISH_MODE,
                        HINGLISH_VOICE, LANGS, LATIN_MODEL, MEMORY_CACHE_ITEMS, MODEL_FOR_LANG, VOICE_FOR_LANG, WARM_UP)
from src.tts.hinglish import HinglishConverter
from src.tts.normalize import is_speakable, normalize

WARM_UP_TEXT = {"gu": "નમસ્તે.", "hi": "नमस्ते.", "en+hi": "Namaste. Hello."}


class UnsupportedLanguage(ValueError):
    """Raised when no loaded model can speak this language/script."""


def _local_config(lang: str):
    """Copy config.json with speakers_file pointing at our folder (AI4Bharat's points at their training machine)."""
    src = CHECKPOINT_DIR / lang / "fastpitch" / "config.json"
    cfg = json.loads(src.read_text(encoding="utf-8"))
    speakers = (CHECKPOINT_DIR / lang / "fastpitch" / "speakers.pth").as_posix()
    cfg["speakers_file"] = speakers
    cfg.setdefault("model_args", {})["speakers_file"] = speakers
    dst = src.with_name("config.local.json")   # the original file is never modified
    dst.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return dst, set(cfg["characters"]["characters"]) | set(cfg["characters"]["punctuations"])


class TTSEngine:
    """One FastPitch + HiFi-GAN pair per model folder (gu, hi, en+hi), loaded at start-up and kept in memory.
    Note: self.models / self.vocab / self.locks are keyed by MODEL folder; callers pass a LANGUAGE ("gu"/"hi"/"en")."""

    def __init__(self, langs=LANGS):
        # WHY import here: lets the server and tests import this module without the 1.5 GB models or torch.
        from TTS.utils.synthesizer import Synthesizer

        self.models, self.vocab, self.locks = {}, {}, {}
        self.cache = OrderedDict()            # (lang, speaker, text) -> wav bytes, most recent last
        self.cache_lock = threading.Lock()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Hinglish -> Devanagari converter (~0.1 s to load, measured); None-model if hindi-xlit isn't installed.
        self.hinglish = HinglishConverter("load" if HINGLISH_MODE == "devanagari" else None)
        # Load each needed model folder once (two languages could share one model).
        for lang in dict.fromkeys(MODEL_FOR_LANG[l] for l in langs):
            t0 = time.perf_counter()
            cfg_path, vocab = _local_config(lang)
            self.models[lang] = Synthesizer(
                tts_checkpoint=CHECKPOINT_DIR / lang / "fastpitch" / "best_model.pth",
                tts_config_path=cfg_path,
                tts_speakers_file=CHECKPOINT_DIR / lang / "fastpitch" / "speakers.pth",
                vocoder_checkpoint=CHECKPOINT_DIR / lang / "hifigan" / "best_model.pth",
                vocoder_config=CHECKPOINT_DIR / lang / "hifigan" / "config.json",
                use_cuda=False,   # PANEL: CPU is enough: ~3x faster than real time on this laptop (measured)
            )
            self.vocab[lang] = vocab
            # WHY a lock per language: one Synthesizer isn't safe to call from two threads at once.
            self.locks[lang] = threading.Lock()
            if WARM_UP:
                # The first call is ~2x slower (measured 7.8 s vs 3.6 s); pay that at start-up, not on stage.
                self.models[lang].tts(WARM_UP_TEXT[lang], speaker_name=DEFAULT_SPEAKER)
            print(f"[tts] {lang} ready in {time.perf_counter() - t0:.1f}s", flush=True)

    @property
    def langs(self):
        """Languages a request may ask for: those whose model loaded."""
        return [l for l in LANGS if MODEL_FOR_LANG[l] in self.models]

    def route(self, text: str, lang: str):
        """(model folder, mode) for a request, or None if nothing loaded can speak it.
        mode: "gu" | "hi" | "en" | "hinglish" (Hinglish converted to Devanagari, then read by the Hindi model)."""
        if lang not in self.langs:
            return None
        latin = (LATIN_MODEL, "en") if LATIN_MODEL in self.models else None
        if lang == "en":
            return latin
        if not is_speakable(text):
            # Hinglish ("hi" in Latin letters). Preferred: convert to Devanagari for the Hindi voice (chosen by ear).
            if lang == "hi" and HINGLISH_MODE == "devanagari" and self.hinglish.available and "hi" in self.models:
                return "hi", "hinglish"
            # FALLBACK: no converter -> the code-mixed en+hi model reads the Latin letters (gu/hi models can't).
            return latin
        return MODEL_FOR_LANG[lang], lang

    def speakers(self, lang: str):
        """Voice names for a language's main model (each AI4Bharat model has "female" and "male")."""
        return list(self.models[MODEL_FOR_LANG[lang]].tts_model.speaker_manager.name_to_id)

    def _fit_vocab(self, text: str, model: str) -> str:
        """Keep only characters the model was trained on; split letters like 'ज़' into 'ज' + nukta first."""
        vocab = self.vocab[model]
        out = []
        # WHY lower(): the en+hi vocabulary has only lowercase a-z; without this every capital letter would be
        # dropped ("Under" -> "nder"). No effect on Gujarati/Devanagari, which have no case.
        for ch in text.lower():
            if ch in vocab:
                out.append(ch)
            else:
                # FALLBACK: a precomposed letter the model lacks -> its base letter(s); anything else is dropped.
                out.extend(c for c in unicodedata.normalize("NFD", ch) if c in vocab)
        return "".join(out)

    def default_speaker(self, text: str, lang: str) -> str:
        """Voice to use when the request names none (chosen by ear: see VOICE_FOR_LANG in config/tts.py)."""
        routed = self.route(text, lang)
        if routed and lang == "hi" and (routed[1] == "hinglish" or routed[0] == LATIN_MODEL):
            return HINGLISH_DEFAULT_SPEAKER   # Hinglish keeps its own voice even though plain Hindi is male
        return VOICE_FOR_LANG.get(lang, DEFAULT_SPEAKER)

    def synthesize(self, text: str, lang: str, speaker: str | None = None):
        """Return (wav_bytes, cache_hit). speaker=None -> the language's default voice.
        Raises UnsupportedLanguage, or ValueError for an unknown speaker."""
        routed = self.route(text, lang)
        if routed is None:
            raise UnsupportedLanguage(lang)
        model, mode = routed
        speaker = speaker or self.default_speaker(text, lang)
        rule_lang = mode
        if mode == "hinglish":
            text, rule_lang = self.hinglish.convert(text), "hi"   # then numbers/₹ are spoken the Hindi way
        if model == LATIN_MODEL and lang == "hi":
            speaker = HINGLISH_VOICE.get(speaker, speaker)   # Hinglish -> the Hindi-accented voice of the en+hi model
        if speaker not in self.models[model].tts_model.speaker_manager.name_to_id:
            raise ValueError(f"unknown speaker: {speaker}")
        spoken = self._fit_vocab(normalize(text, rule_lang), model)
        key = (model, speaker, spoken)

        with self.cache_lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key], True
        # Disk cache: survives restarts and holds the pre-generated demo answers (src/tts/pregenerate.py).
        digest = hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()[:32]
        disk = CACHE_DIR / f"{model.replace('+', '')}-{speaker}-{digest}.wav"
        if disk.exists():
            wav = disk.read_bytes()
            self._remember(key, wav)
            return wav, True

        with self.locks[model]:
            samples = self.models[model].tts(spoken, speaker_name=speaker)
        buf = io.BytesIO()
        sf.write(buf, samples, self.models[model].output_sample_rate, format="WAV", subtype="PCM_16")
        wav = buf.getvalue()
        disk.write_bytes(wav)
        self._remember(key, wav)
        return wav, False

    def _remember(self, key, wav):
        with self.cache_lock:
            self.cache[key] = wav
            self.cache.move_to_end(key)
            while len(self.cache) > MEMORY_CACHE_ITEMS:   # drop the least recently used answer
                self.cache.popitem(last=False)

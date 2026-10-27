"""
COMPONENT : tts
PURPOSE   : Load AI4Bharat IndicTTS (FastPitch + HiFi-GAN) once per language and turn text into WAV audio, reusing
            audio already made for the same text.
INPUTS    : text, language ("gu" | "hi"), speaker ("female" | "male")
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

from config.tts import CACHE_DIR, CHECKPOINT_DIR, DEFAULT_SPEAKER, LANGS, MEMORY_CACHE_ITEMS, WARM_UP
from src.tts.normalize import normalize

WARM_UP_TEXT = {"gu": "નમસ્તે.", "hi": "नमस्ते."}


class UnsupportedLanguage(ValueError):
    """Raised for a language whose model isn't loaded (e.g. English/Hinglish until en+hi.zip is added)."""


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
    """One FastPitch + HiFi-GAN pair per language, loaded at start-up and kept in memory."""

    def __init__(self, langs=LANGS):
        # WHY import here: lets the server and tests import this module without the 1.5 GB models or torch.
        from TTS.utils.synthesizer import Synthesizer

        self.models, self.vocab, self.locks = {}, {}, {}
        self.cache = OrderedDict()            # (lang, speaker, text) -> wav bytes, most recent last
        self.cache_lock = threading.Lock()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        for lang in langs:
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
        return list(self.models)

    def speakers(self, lang: str):
        return list(self.models[lang].tts_model.speaker_manager.name_to_id)

    def _fit_vocab(self, text: str, lang: str) -> str:
        """Keep only characters the model was trained on; split letters like 'ज़' into 'ज' + nukta first."""
        vocab = self.vocab[lang]
        out = []
        for ch in text:
            if ch in vocab:
                out.append(ch)
            else:
                # FALLBACK: a precomposed letter the model lacks -> its base letter(s); anything else is dropped.
                out.extend(c for c in unicodedata.normalize("NFD", ch) if c in vocab)
        return "".join(out)

    def synthesize(self, text: str, lang: str, speaker: str = DEFAULT_SPEAKER):
        """Return (wav_bytes, cache_hit). Raises UnsupportedLanguage or ValueError for unknown speaker."""
        if lang not in self.models:
            raise UnsupportedLanguage(lang)
        if speaker not in self.speakers(lang):
            raise ValueError(f"unknown speaker: {speaker}")
        spoken = self._fit_vocab(normalize(text, lang), lang)
        key = (lang, speaker, spoken)

        with self.cache_lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key], True
        # Disk cache: survives restarts and holds the pre-generated demo answers (src/tts/pregenerate.py).
        digest = hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()[:32]
        disk = CACHE_DIR / f"{lang}-{speaker}-{digest}.wav"
        if disk.exists():
            wav = disk.read_bytes()
            self._remember(key, wav)
            return wav, True

        with self.locks[lang]:
            samples = self.models[lang].tts(spoken, speaker_name=speaker)
        buf = io.BytesIO()
        sf.write(buf, samples, self.models[lang].output_sample_rate, format="WAV", subtype="PCM_16")
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

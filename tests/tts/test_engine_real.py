"""
COMPONENT : tts (tests)
PURPOSE   : Load the real AI4Bharat models, speak a demo answer in Gujarati and Hindi, and measure how long it takes.
INPUTS    : checkpoints in config.tts.CHECKPOINT_DIR, coqui-tts + torch
OUTPUTS   : pass/fail plus measured timings (skipped automatically where the models aren't installed)
DEPENDS ON: src/tts/engine.py
PANEL NOTE: The latency numbers we quote come from this test, run on the demo laptop.

Run (repo root, TTS virtual environment):
    C:\\Users\\vaidu\\indic-tts\\.venv\\Scripts\\python -m unittest tests.tts.test_engine_real -v
"""
import io
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config.tts import CACHE_DIR, CHECKPOINT_DIR  # noqa: E402

try:
    import numpy as np
    import soundfile as sf
    import TTS  # noqa: F401
    HAVE_TTS = all((CHECKPOINT_DIR / l / "fastpitch" / "best_model.pth").exists() for l in ("gu", "hi"))
except ImportError:
    HAVE_TTS = False

DEMO = {
    "gu": "PM-KISAN હેઠળ જમીન ધરાવતા ખેડૂત પરિવારોને વર્ષે ₹6,000 ત્રણ હપ્તામાં સીધા બેંક ખાતામાં મળે છે [S1].",
    "hi": "पीएम-किसान के तहत भूमिधारक किसान परिवारों को साल में ₹6,000 तीन किस्तों में सीधे बैंक खाते में मिलते हैं [S1]।",
}


@unittest.skipUnless(HAVE_TTS, "coqui-tts or the gu/hi checkpoints are not installed here")
class TestRealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.tts.engine import TTSEngine
        t0 = time.perf_counter()
        cls.engine = TTSEngine(["gu", "hi"])
        print(f"\n  load + warm-up, both languages: {time.perf_counter() - t0:.1f}s")

    def test_speaks_demo_answers_fast_enough(self):
        for lang, text in DEMO.items():
            with self.subTest(lang=lang):
                # WHY: clear both caches so this measures a fresh synthesis, not a cached replay.
                self.engine.cache.clear()
                for f in CACHE_DIR.glob(f"{lang}-female-*.wav"):
                    f.unlink()
                t0 = time.perf_counter()
                wav, hit = self.engine.synthesize(text, lang, "female")
                took = time.perf_counter() - t0
                samples, sr = sf.read(io.BytesIO(wav))
                secs = len(samples) / sr
                print(f"  {lang}: {took:.2f}s for {secs:.2f}s of audio (cache {'hit' if hit else 'miss'}), "
                      f"RMS {float(np.sqrt((samples ** 2).mean())):.3f}")
                self.assertEqual(sr, 22050)
                self.assertGreater(secs, 2.0)                             # it said something sentence-length
                self.assertGreater(float(np.sqrt((samples ** 2).mean())), 0.01)   # not silence

    def test_second_request_is_instant(self):
        self.engine.synthesize(DEMO["gu"], "gu", "female")
        t0 = time.perf_counter()
        _, hit = self.engine.synthesize(DEMO["gu"], "gu", "female")
        self.assertTrue(hit)
        self.assertLess(time.perf_counter() - t0, 0.05)


if __name__ == "__main__":
    unittest.main()

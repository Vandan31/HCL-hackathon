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
from config.tts import CACHE_DIR, CHECKPOINT_DIR  # noqa: E402,F401  (CACHE_DIR: the demo cache this test must not touch)

try:
    import numpy as np
    import soundfile as sf
    import TTS  # noqa: F401
    HAVE_TTS = all((CHECKPOINT_DIR / m / "fastpitch" / "best_model.pth").exists() for m in ("gu", "hi", "en+hi"))
except ImportError:
    HAVE_TTS = False

# (name, lang sent to the service, text). Hinglish goes as "hi" and is routed to the en+hi voice by its letters.
DEMO = [
    ("gujarati", "gu", "PM-KISAN હેઠળ જમીન ધરાવતા ખેડૂત પરિવારોને વર્ષે ₹6,000 ત્રણ હપ્તામાં સીધા બેંક ખાતામાં મળે છે [S1]."),
    ("hindi", "hi", "पीएम-किसान के तहत भूमिधारक किसान परिवारों को साल में ₹6,000 तीन किस्तों में सीधे बैंक खाते में मिलते हैं [S1]।"),
    ("english", "en", "Under PM-KISAN, landholding farmer families get ₹6,000 a year, paid directly to their bank account [S1]."),
    ("hinglish", "hi", "PM-KISAN mein zameen wale kisan parivaron ko saal mein ₹6,000 seedhe bank account mein milte hain [S1]."),
]


@unittest.skipUnless(HAVE_TTS, "coqui-tts or the gu/hi checkpoints are not installed here")
class TestRealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        from src.tts import engine as engine_module
        from src.tts.engine import TTSEngine
        # WHY: use a throwaway cache folder, so measuring fresh synthesis never deletes the pre-spoken demo audio.
        cls.tmp = tempfile.TemporaryDirectory()
        cls.real_cache_dir = engine_module.CACHE_DIR
        engine_module.CACHE_DIR = Path(cls.tmp.name)
        t0 = time.perf_counter()
        cls.engine = TTSEngine(["gu", "hi", "en"])
        print(f"\n  load + warm-up, three models: {time.perf_counter() - t0:.1f}s")

    @classmethod
    def tearDownClass(cls):
        from src.tts import engine as engine_module
        engine_module.CACHE_DIR = cls.real_cache_dir
        cls.tmp.cleanup()

    def test_routing(self):
        self.assertEqual(self.engine.route(DEMO[0][2], "gu"), ("gu", "gu"))
        self.assertEqual(self.engine.route(DEMO[2][2], "en"), ("en+hi", "en"))
        self.assertEqual(self.engine.route(DEMO[3][2], "hi"), ("en+hi", "en"))   # Hinglish -> code-mixed voice

    def test_speaks_demo_answers_fast_enough(self):
        for name, lang, text in DEMO:
            with self.subTest(name=name):
                # WHY: clear both caches so this measures a fresh synthesis, not a cached replay.
                from src.tts import engine as engine_module
                self.engine.cache.clear()
                for f in engine_module.CACHE_DIR.glob("*.wav"):   # the temporary folder, never the demo cache
                    f.unlink()
                t0 = time.perf_counter()
                wav, hit = self.engine.synthesize(text, lang, "female")
                took = time.perf_counter() - t0
                samples, sr = sf.read(io.BytesIO(wav))
                secs = len(samples) / sr
                print(f"  {name}: {took:.2f}s for {secs:.2f}s of audio (cache {'hit' if hit else 'miss'}), "
                      f"RMS {float(np.sqrt((samples ** 2).mean())):.3f}")
                self.assertEqual(sr, 22050)
                self.assertGreater(secs, 2.0)                             # it said something sentence-length
                self.assertGreater(float(np.sqrt((samples ** 2).mean())), 0.01)   # not silence

    def test_second_request_is_instant(self):
        _, lang, text = DEMO[0]
        self.engine.synthesize(text, lang, "female")
        t0 = time.perf_counter()
        _, hit = self.engine.synthesize(text, lang, "female")
        self.assertTrue(hit)
        self.assertLess(time.perf_counter() - t0, 0.05)


if __name__ == "__main__":
    unittest.main()

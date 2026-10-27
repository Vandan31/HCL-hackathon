"""
COMPONENT : tts (tests)
PURPOSE   : Check the /api/tts HTTP contract (audio, errors, CORS) with a fake engine, so it runs in a second.
INPUTS    : src/tts/server.py
OUTPUTS   : pass/fail
DEPENDS ON: Python standard library only (the real models are tested in test_engine_real.py)
PANEL NOTE: The UI and the team's API build against this contract, so every documented response is tested.

Run from the repo root:  python -m unittest discover -s tests/tts -v
"""
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.tts.server import make_handler  # noqa: E402

FAKE_WAV = b"RIFF\x24\x00\x00\x00WAVEfmt "   # just the start of a WAV header; enough to check bytes pass through


class FakeEngine:
    """Stands in for TTSEngine: no models, records calls, can be told to fail.
    `latin` = whether the en+hi model is "loaded" (English and Hinglish need it)."""
    langs = ["gu", "hi", "en"]
    cache = {}
    fail = False
    latin = True

    def route(self, text, lang):
        latin_text = sum(c.isascii() for c in text if c.isalpha()) > 0.5 * max(1, sum(c.isalpha() for c in text))
        if lang == "en" or latin_text:
            return ("en+hi", "en") if self.latin else None
        return lang, lang

    def speakers(self, lang):
        return ["female", "male"]

    def synthesize(self, text, lang, speaker):
        if self.fail:
            raise RuntimeError("model crashed")
        self.last = (text, lang, speaker)
        return FAKE_WAV, False


class TestTTSServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = FakeEngine()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.engine))   # port 0 = any free port
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, method, path, body=None, origin=None):
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", **({"Origin": origin} if origin else {})})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_returns_wav_audio(self):
        status, headers, body = self.request("POST", "/api/tts", {"text": "ખેડૂત સહાય", "lang": "gu"})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "audio/wav")
        self.assertEqual(body, FAKE_WAV)
        self.assertEqual(headers["X-TTS-Cache"], "miss")
        self.assertEqual(self.engine.last, ("ખેડૂત સહાય", "gu", None))   # no speaker sent -> engine picks the default

    def test_errors_match_contract(self):
        cases = [
            ({"text": "", "lang": "gu"}, 400, "empty_text"),
            ({"text": "x" * 5000, "lang": "gu"}, 400, "text_too_long"),
            ({"text": "வணக்கம்", "lang": "ta"}, 422, "unsupported_lang"),
            ({"text": "नमस्ते", "lang": "hi", "speaker": "robot"}, 400, "unknown_speaker"),
        ]
        for body, code, error in cases:
            with self.subTest(error=error):
                status, _, raw = self.request("POST", "/api/tts", body)
                self.assertEqual((status, json.loads(raw)["error"]), (code, error))

    def test_english_and_hinglish_are_spoken(self):
        for body in ({"text": "Farmers get six thousand rupees a year.", "lang": "en"},
                     {"text": "PM awas yojana ke liye documents chahiye", "lang": "hi"}):
            with self.subTest(text=body["text"]):
                status, headers, _ = self.request("POST", "/api/tts", body)
                self.assertEqual((status, headers["Content-Type"]), (200, "audio/wav"))

    def test_latin_text_refused_when_en_hi_model_missing(self):
        self.engine.latin = False
        try:
            status, _, raw = self.request("POST", "/api/tts", {"text": "PM awas yojana ke liye", "lang": "hi"})
        finally:
            self.engine.latin = True
        self.assertEqual((status, json.loads(raw)["error"]), (422, "unsupported_script"))

    def test_bad_json(self):
        status, _, raw = self.request("POST", "/api/tts", b"{not json")
        self.assertEqual((status, json.loads(raw)["error"]), (400, "bad_json"))

    def test_model_failure_is_503(self):
        self.engine.fail = True
        try:
            status, _, raw = self.request("POST", "/api/tts", {"text": "नमस्ते", "lang": "hi"})
        finally:
            self.engine.fail = False
        self.assertEqual((status, json.loads(raw)["error"]), (503, "model_unavailable"))

    def test_cors_only_for_the_ui_origin(self):
        _, ok, _ = self.request("POST", "/api/tts", {"text": "नमस्ते", "lang": "hi"}, origin="http://127.0.0.1:5500")
        _, other, _ = self.request("POST", "/api/tts", {"text": "नमस्ते", "lang": "hi"}, origin="https://evil.example")
        self.assertEqual(ok.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5500")
        self.assertNotIn("Access-Control-Allow-Origin", other)

    def test_preflight(self):
        status, headers, _ = self.request("OPTIONS", "/api/tts", origin="http://127.0.0.1:5500")
        self.assertEqual(status, 204)
        self.assertIn("POST", headers["Access-Control-Allow-Methods"])

    def test_health(self):
        status, _, raw = self.request("GET", "/api/tts/health")
        body = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual(body["langs"], ["gu", "hi", "en"])


if __name__ == "__main__":
    unittest.main()

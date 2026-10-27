"""
COMPONENT : tts
PURPOSE   : Small web service that speaks an answer: POST /api/tts {text, lang, speaker} -> WAV audio.
INPUTS    : HTTP requests from the UI (or from the team's API as a proxy)
OUTPUTS   : audio/wav, or JSON errors; GET /api/tts/health for status
DEPENDS ON: src/tts/engine.py (models), config/tts.py; Python standard library http.server
PANEL NOTE: Speech runs as its own service because the voice models are large (~1.5 GB per language); the rest of
            the app stays light and keeps working, text-only, if this service is down.

Run (from the repo root, with the TTS virtual environment):
    C:\\Users\\vaidu\\indic-tts\\.venv\\Scripts\\python -m src.tts.server
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config.tts import ALLOWED_ORIGINS, HOST, MAX_CHARS, PORT

# Contract (proposed to comp/api on docs/BOARD.md):
#   POST /api/tts  {"text": str, "lang": "gu"|"hi"|"en", "speaker"?: "female"|"male"}
#     Hinglish: send lang "hi" with the Latin-letter text; it is routed to the en+hi voice automatically.
#     200 audio/wav            headers: X-TTS-Cache: hit|miss, X-TTS-Ms: synthesis time
#     400 {"error": "bad_json" | "empty_text" | "text_too_long" | "unknown_speaker"}
#     422 {"error": "unsupported_lang" | "unsupported_script", "supported": [...]}   -> UI uses the browser voice instead
#     503 {"error": "model_unavailable"}
#   GET /api/tts/health -> {"ok": true, "langs": [...], "speakers": {...}, "cached": n}


def make_handler(engine):
    """Build the request handler around an engine (a fake one in tests, the real models in production)."""

    class Handler(BaseHTTPRequestHandler):
        def _cors(self):
            # WHY: the UI is served from port 5500 and this service from 5600; browsers block that unless allowed.
            origin = self.headers.get("Origin")
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Expose-Headers", "X-TTS-Cache, X-TTS-Ms")

        def _json(self, status, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self):
            """CORS preflight for the JSON POST."""
            self.send_response(204)
            self._cors()
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_GET(self):
            if self.path != "/api/tts/health":
                return self._json(404, {"error": "not_found"})
            return self._json(200, {"ok": True, "langs": engine.langs,
                                    "speakers": {l: engine.speakers(l) for l in engine.langs},
                                    "cached": len(engine.cache)})

        def do_POST(self):
            if self.path != "/api/tts":
                return self._json(404, {"error": "not_found"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                text, lang = str(req.get("text", "")).strip(), str(req.get("lang", ""))
                speaker = str(req["speaker"]) if req.get("speaker") else None   # None = the language's default voice
            except (ValueError, json.JSONDecodeError, AttributeError):
                return self._json(400, {"error": "bad_json"})
            if not text:
                return self._json(400, {"error": "empty_text"})
            if len(text) > MAX_CHARS:
                return self._json(400, {"error": "text_too_long", "max": MAX_CHARS})
            if lang not in engine.langs:
                # FALLBACK: a language with no model loaded -> the UI speaks with the browser voice instead.
                return self._json(422, {"error": "unsupported_lang", "supported": engine.langs})
            if engine.route(text, lang) is None:
                # FALLBACK: Latin-letter text (English/Hinglish) while the en+hi model isn't loaded -> browser voice.
                return self._json(422, {"error": "unsupported_script", "supported": engine.langs})
            if speaker is not None and speaker not in engine.speakers(lang):
                return self._json(400, {"error": "unknown_speaker", "speakers": engine.speakers(lang)})
            t0 = time.perf_counter()
            try:
                wav, hit = engine.synthesize(text, lang, speaker)
            except Exception as e:   # FALLBACK: any model failure -> 503; the answer text is still on screen
                print(f"[tts] synthesis failed: {e!r}", flush=True)
                return self._json(503, {"error": "model_unavailable"})
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-TTS-Cache", "hit" if hit else "miss")
            self.send_header("X-TTS-Ms", str(round((time.perf_counter() - t0) * 1000)))
            self.end_headers()
            self.wfile.write(wav)

        def log_message(self, fmt, *args):   # one short line per request instead of the default noisy log
            print(f"[tts] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}", flush=True)

    return Handler


def main():
    from src.tts.engine import TTSEngine   # WHY here: loading models takes a few seconds and needs torch
    engine = TTSEngine()
    server = ThreadingHTTPServer((HOST, PORT), make_handler(engine))
    print(f"[tts] listening on http://{HOST}:{PORT}/api/tts  (Ctrl+C to stop)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

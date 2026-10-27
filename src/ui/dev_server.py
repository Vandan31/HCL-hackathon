"""
COMPONENT : ui (dev server)
PURPOSE   : Serve the UI and answer POST /api/eligibility with the real rules engine, so the checklist screen
            can be built and demoed before the team's FastAPI app (comp/api) exists.
INPUTS    : HTTP requests; optional port number as the first command-line argument (default 5500)
OUTPUTS   : static files from the repo root; JSON from src/eligibility/rules.next_question
DEPENDS ON: src/eligibility/rules.py, config/eligibility.py; Python standard library only
PANEL NOTE: A throwaway stand-in for one API route, so UI work never waited on the backend.

Run from anywhere:  python src/ui/dev_server.py        then open  http://127.0.0.1:5500/src/ui/
"""
# MOCK: this replaces Harsh's /api/eligibility route during development only. Not used in the final demo.
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))   # WHY: lets "from src.eligibility..." work without installing anything

from src.eligibility.rules import next_question  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    # WHY: Windows sometimes maps .js to text/plain, and browsers refuse to run modules served that way.
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".json": "application/json"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, status: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        """POST /api/eligibility {scheme_id, answers, lang} -> {question, checklist, verdict} (PLAN §4.3)."""
        if self.path != "/api/eligibility":
            return self._json(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "bad_json"})
        scheme_id = req.get("scheme_id")
        if not scheme_id:
            return self._json(400, {"error": "missing_scheme_id"})
        try:
            result = next_question(scheme_id, req.get("answers") or {}, req.get("lang") or "en")
        except KeyError:
            # FALLBACK: no criteria for this scheme yet -> the UI says the checklist isn't available.
            return self._json(404, {"error": "unknown_scheme"})
        return self._json(200, result)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"UI dev server: http://127.0.0.1:{port}/src/ui/  (Ctrl+C to stop)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

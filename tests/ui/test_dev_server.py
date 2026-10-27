"""
COMPONENT : ui (tests)
PURPOSE   : Check the dev server's POST /api/eligibility returns the contract shape and the documented errors.
INPUTS    : src/ui/dev_server.py running on a free local port
OUTPUTS   : pass/fail
DEPENDS ON: Python standard library only
PANEL NOTE: The checklist screen is built against this route, so its responses must match PLAN §4.3.

Run from the repo root:  python -m unittest discover -s tests/ui -v
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
from src.ui.dev_server import Handler  # noqa: E402


class TestDevServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Port 0 = let the OS pick a free port, so the test never clashes with a server you have running.
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def post(self, body):
        req = urllib.request.Request(f"{self.base}/api/eligibility", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_contract_shape(self):
        status, body = self.post({"scheme_id": "pm-kisan", "answers": {}, "lang": "gu"})
        self.assertEqual(status, 200)
        self.assertEqual(set(body), {"question", "checklist", "verdict"})
        self.assertEqual(set(body["question"]), {"field", "text", "options"})
        self.assertEqual(set(body["checklist"][0]), {"criterion", "status", "source"})

    def test_unknown_scheme_is_404(self):
        self.assertEqual(self.post({"scheme_id": "pmay", "answers": {}}), (404, {"error": "unknown_scheme"}))

    def test_missing_scheme_id_is_400(self):
        self.assertEqual(self.post({"answers": {}})[0], 400)

    def test_serves_js_as_javascript(self):
        # WHY: browsers refuse to run ES modules served as text/plain (a Windows default).
        with urllib.request.urlopen(f"{self.base}/src/ui/app.js") as r:
            self.assertIn("javascript", r.headers["Content-Type"])


if __name__ == "__main__":
    unittest.main()

"""
COMPONENT : ui (tests)
PURPOSE   : Check the UI's mock data matches the agreed /api/ask contract and that every JS import resolves.
INPUTS    : src/ui/mock/ask_fixtures.json, src/ui/*.js, config/ui.js
OUTPUTS   : pass/fail
DEPENDS ON: Python standard library only (Node and pytest aren't installed on every laptop)
PANEL NOTE: If the mock drifts from the contract, the UI would break at integration; this catches it early.

Run from the repo root:  python -m unittest discover -s tests/ui -v
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "ui"
FIXTURES = json.loads((UI / "mock" / "ask_fixtures.json").read_text(encoding="utf-8"))

# Keys every citation must carry, per docs/COMPONENTS.md "Interfaces" (answer() citations), plus
# "scheme_id": an assumed addition the eligibility button needs; to be agreed with comp/api at integration.
CITATION_KEYS = {"id", "chunk_id", "scheme_id", "scheme_name", "passage", "source_url"}
# Answer variants the UI can show: en, hi, gu plus Hinglish (hi in Latin script).
LANG_VARIANTS = {"en", "hi", "gu", "hinglish"}


class TestMockFixtures(unittest.TestCase):
    def test_every_topic_has_all_languages(self):
        for t in FIXTURES["topics"]:
            self.assertEqual(set(t["answers"]), LANG_VARIANTS, t["id"])

    def test_refusal_has_all_languages(self):
        self.assertEqual(set(FIXTURES["refusal"]["answers"]), LANG_VARIANTS)

    def test_citations_match_contract(self):
        for t in FIXTURES["topics"]:
            for c in t["citations"]:
                self.assertEqual(set(c), CITATION_KEYS, f"{t['id']} {c.get('id')}")
                self.assertTrue(c["source_url"].startswith("https://"))

    def test_every_marker_points_to_a_citation(self):
        # WHY: an [S3] with no S3 card would be a dead link in the UI, which is the exact bug the
        # backend's citation checker exists to prevent.
        for t in FIXTURES["topics"]:
            ids = {c["id"] for c in t["citations"]}
            for lang, text in t["answers"].items():
                for marker in re.findall(r"\[(S\d+)\]", text):
                    self.assertIn(marker, ids, f"{t['id']}/{lang}")

    def test_mock_passages_are_labelled(self):
        # Honest disclosure: fixture passages must never look like real retrieved text.
        for t in FIXTURES["topics"]:
            for c in t["citations"]:
                self.assertTrue(c["passage"].startswith("MOCK"), c["chunk_id"])


class TestJsImports(unittest.TestCase):
    def test_relative_imports_resolve(self):
        # WHY: a typo in an import path silently breaks the whole page in the browser, with no Node here to catch it.
        for js in UI.glob("*.js"):
            src = js.read_text(encoding="utf-8")
            paths = re.findall(r'from\s+"(\.{1,2}/[^"]+)"', src)
            paths += re.findall(r'new URL\("(\.{1,2}/[^"]+)"', src)
            for rel in paths:
                self.assertTrue((js.parent / rel).resolve().exists(), f"{js.name} -> {rel}")

    def test_html_assets_exist(self):
        html = (UI / "index.html").read_text(encoding="utf-8")
        for rel in re.findall(r'(?:src|href)="([^":]+\.(?:js|css))"', html):
            self.assertTrue((UI / rel).exists(), rel)

    def test_config_has_strings_for_every_language(self):
        cfg = (ROOT / "config" / "ui.js").read_text(encoding="utf-8")
        for lang in LANG_VARIANTS:
            self.assertRegex(cfg, rf"\n\s+{lang}: \{{", f"STRINGS.{lang} missing")


if __name__ == "__main__":
    unittest.main()

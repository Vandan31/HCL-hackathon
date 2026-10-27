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
            paths += re.findall(r'import\("(\.{1,2}/[^"]+)"\)', src)   # dynamic imports, e.g. the local Three.js
            for rel in paths:
                self.assertTrue((js.parent / rel).resolve().exists(), f"{js.name} -> {rel}")

    def test_three_js_is_local_and_licensed(self):
        # WHY: the demo must work offline, so Three.js is served from the repo, never a CDN, with its MIT licence.
        vendor = UI / "vendor" / "three"
        self.assertTrue((vendor / "three.module.min.js").stat().st_size > 500_000)
        self.assertIn("MIT License", (vendor / "LICENSE").read_text(encoding="utf-8"))
        for js in UI.glob("*.js"):
            self.assertNotRegex(js.read_text(encoding="utf-8"), r"https?://[^\s\"']*three", js.name)

    def test_html_assets_exist(self):
        html = (UI / "index.html").read_text(encoding="utf-8")
        for rel in re.findall(r'(?:src|href)="([^":]+\.(?:js|css))"', html):
            self.assertTrue((UI / rel).exists(), rel)


class TestTranslations(unittest.TestCase):
    """Every word on the page must exist in all three page languages (the language picker promises it)."""
    PAGE_LANGS = ("en", "hi", "gu")
    CFG = (ROOT / "config" / "ui.js").read_text(encoding="utf-8")
    # WHY: strip <!-- comments -->, whose usage example would otherwise look like a real label.
    HTML = re.sub(r"<!--.*?-->", "", (UI / "index.html").read_text(encoding="utf-8"), flags=re.S)

    def strings_block(self, lang):
        # The text between "    <lang>: {" and the next language block (or the end of STRINGS).
        m = re.search(rf"\n    {lang}: \{{(.*?)(?=\n    [a-z]+: \{{|\n  \}},\n\}};)", self.CFG, re.S)
        self.assertIsNotNone(m, f"STRINGS.{lang} missing")
        return m.group(1)

    def keys(self, lang):
        return set(re.findall(r"\n\s+(\w+):", self.strings_block(lang)))

    def test_all_languages_have_the_same_keys(self):
        en = self.keys("en")
        for lang in self.PAGE_LANGS[1:]:
            self.assertEqual(self.keys(lang), en, f"STRINGS.{lang} differs from STRINGS.en")

    def test_every_html_label_is_translated(self):
        used = set(re.findall(r'data-i18n="(\w+)"', self.HTML))
        for attr_list in re.findall(r'data-i18n-attr="([^"]+)"', self.HTML):
            used |= {pair.split(":")[1] for pair in attr_list.split(",")}
        for lang in self.PAGE_LANGS:
            missing = used - self.keys(lang)
            self.assertFalse(missing, f"STRINGS.{lang} lacks {missing}")

    def test_sample_questions_for_every_language(self):
        for lang in self.PAGE_LANGS:
            self.assertRegex(self.CFG, rf"\n    {lang}: \[\n", f"SAMPLE_QUESTIONS.{lang} missing")


if __name__ == "__main__":
    unittest.main()

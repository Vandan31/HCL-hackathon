"""
COMPONENT : ui (tests)
PURPOSE   : Measure the contrast of every colour pair the UI uses, straight from the tokens in src/ui/styles.css,
            and fail if any drops below WCAG 2.2 AA.
INPUTS    : the :root colour tokens in src/ui/styles.css
OUTPUTS   : pass/fail (run with -v to see each measured ratio)
DEPENDS ON: Python standard library only
PANEL NOTE: "Is it accessible?" -> every text colour is measured, not eyeballed; this test fails the build if a
            theme change makes text or button edges too faint.

Run from the repo root:  python -m unittest discover -s tests/ui -v
"""
import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parents[2] / "src" / "ui" / "styles.css").read_text(encoding="utf-8")
ROOT_BLOCK = re.search(r":root\s*\{(.*?)\n\}", CSS, re.S).group(1)
TOKENS = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", ROOT_BLOCK))

# WCAG 1.4.3: normal text needs 4.5:1. WCAG 1.4.11: edges that show where a control is need 3:1.
TEXT, NON_TEXT = 4.5, 3.0

# (foreground token, background token, minimum, where it is used)
PAIRS = [
    ("ink", "bg", TEXT, "body text"),
    ("ink", "surface", TEXT, "card text"),
    ("ink", "band", TEXT, "header and composer text"),
    ("accent-ink", "accent", TEXT, "text on yellow buttons, badges, user bubbles"),
    ("ink-soft", "bg", TEXT, "secondary text"),
    ("ink-soft", "surface", TEXT, "disclaimer, placeholder, labels on cards"),
    ("ink-soft", "band", TEXT, "tagline in the header"),
    ("ink-soft", "warn-tint", TEXT, "meta text on refusal cards"),
    ("accent-text", "bg", TEXT, "links and citation markers"),
    ("accent-text", "surface", TEXT, "links on cards"),
    ("good", "good-tint", TEXT, "likely-eligible verdict"),
    ("good", "bg", TEXT, "'Meets' in the checklist"),
    ("bad", "bad-tint", TEXT, "error cards, not-eligible verdict"),
    ("bad", "bg", TEXT, "'Doesn't meet' in the checklist"),
    ("warn", "warn-tint", TEXT, "refusal and need-more-info"),
    ("warn", "surface", TEXT, "mock-data status pill"),
    ("band", "ink", TEXT, "pressed large-text button"),
    ("control-border", "surface", NON_TEXT, "button / input / chip edges on cards"),
    ("control-border", "band", NON_TEXT, "button / input edges in header and composer"),
    ("control-border", "bg", NON_TEXT, "chip edges on the page"),
    ("ink", "accent", NON_TEXT, "focus ring and primary-button edge on yellow"),
]


def luminance(hex_colour: str) -> float:
    """WCAG relative luminance of '#rrggbb'."""
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class TestContrast(unittest.TestCase):
    def test_tokens_found(self):
        # Guards against the regex silently matching nothing (which would make every test vacuous).
        for fg, bg, _, _ in PAIRS:
            self.assertIn(fg, TOKENS)
            self.assertIn(bg, TOKENS)

    def test_pairs_meet_wcag_aa(self):
        for fg, bg, minimum, where in PAIRS:
            with self.subTest(pair=f"{fg} on {bg}", used_for=where):
                ratio = contrast(TOKENS[fg], TOKENS[bg])
                self.assertGreaterEqual(ratio, minimum, f"{fg} on {bg} = {ratio:.2f}:1 ({where})")


if __name__ == "__main__":
    # Print the measured table, handy for the pitch slide.
    for fg, bg, minimum, where in PAIRS:
        print(f"{contrast(TOKENS[fg], TOKENS[bg]):6.2f}:1  (min {minimum})  {fg} on {bg}  - {where}")

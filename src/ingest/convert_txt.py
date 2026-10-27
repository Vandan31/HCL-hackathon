"""
COMPONENT : ingest (data + ingestion)
PURPOSE   : Turn hand-pasted myScheme pages (docs/schemes/*.txt) into data/schemes/<id>.json files.
INPUTS    : docs/schemes/<page name>.txt (English myScheme page text, pasted by a human)
OUTPUTS   : data/schemes/<id>.json in the DATA_FORMAT §1 template (text copied as is, no summaries)
DEPENDS ON: config/ingest.py (heading map, id map, paths), docs/DATA_FORMAT.md
PANEL NOTE: We never scrape myScheme (its Terms ban bots, D-001); this only structures text a person pasted.

Usage (from the repo root):
  python -m src.ingest.convert_txt
"""
import glob
import json
import os
import sys

from config import ingest as cfg

# Contract order of sections, so every scheme file reads the same way.
SECTION_ORDER = ["details", "benefits", "eligibility", "exclusions", "documents", "how_to_apply"]


def clean_line(line):
    """Strip invisible byte-order marks (pasted from the web page) and surrounding spaces."""
    return line.replace("﻿", "").strip()


def parse_page(raw):
    """Split one pasted page into (scheme name, {section: text}).

    Page layout: [ministry/state] / scheme name / tag strip / buttons / "Details" / sections...
    """
    lines = [clean_line(l) for l in raw.splitlines()]
    if "Details" not in lines:
        raise ValueError("no 'Details' heading: is this a full myScheme page?")
    start = lines.index("Details")
    header = [l for l in lines[:start] if l and l not in cfg.SKIP_LINES]
    if len(header) < 2:
        raise ValueError(f"header too short to find the scheme name: {header}")
    # WHY header[-2]: the last header line is the tag strip ("CommunicationInternshipJournalism..."),
    # the scheme name sits right above it; the ministry/state line above that is optional.
    name = header[-2]

    parts, current = {}, None
    for line in lines[start:]:
        if line in cfg.HEADINGS:
            # A repeated heading (two "Application Process" blocks) appends to the same section.
            current = cfg.HEADINGS[line]
            continue
        if not line or current is None:  # blank line, or inside a dropped block (FAQ, sources)
            continue
        parts.setdefault(current, []).append(line)
    sections = {s: "\n".join(parts[s]) for s in SECTION_ORDER if s in parts}
    return name, sections


def merge_scheme(existing, scheme_id, name, sections):
    """Write the English text into the scheme dict, keeping anything a human added by hand.

    WHY merge instead of overwrite: teammates may add hi/gu text, a real source_url or `criteria`
    to data/schemes/<id>.json; re-running the converter must not wipe that work.
    """
    s = dict(existing) if existing else {}
    s["id"] = scheme_id
    s.setdefault("name", {})[cfg.RAW_LANG] = name
    s.setdefault("source_url", {}).setdefault(cfg.RAW_LANG, cfg.SOURCE_URL_MISSING)
    s.setdefault("collected_on", cfg.COLLECTED_ON)
    s.setdefault("collected_by", cfg.COLLECTED_BY)
    s.setdefault("sections", {})
    for sec, text in sections.items():
        s["sections"].setdefault(sec, {})[cfg.RAW_LANG] = text
    return s


def convert(raw_dir=cfg.RAW_DIR, out_dir=cfg.SCHEMES_DIR):
    """Convert every .txt page in raw_dir. Returns a list of (scheme_id, {section: word count})."""
    os.makedirs(out_dir, exist_ok=True)
    report = []
    for path in sorted(glob.glob(os.path.join(raw_dir, "*.txt"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem not in cfg.SCHEME_IDS:
            # FALLBACK: refuse to invent an id; a new page needs a deliberate, permanent id.
            raise SystemExit(f"{path}: no id for {stem!r}; add it to SCHEME_IDS in config/ingest.py")
        sid = cfg.SCHEME_IDS[stem]
        with open(path, encoding="utf-8") as f:
            name, sections = parse_page(f.read())
        out_path = os.path.join(out_dir, f"{sid}.json")
        existing = None
        if os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as f:
                existing = json.load(f)
        scheme = merge_scheme(existing, sid, name, sections)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(scheme, f, ensure_ascii=False, indent=2)
            f.write("\n")
        report.append((sid, {s: len(t.split()) for s, t in sections.items()}))
    return report


def main():
    report = convert()
    for sid, counts in report:
        print(f"{sid:36s} " + "  ".join(f"{s}={n}" for s, n in counts.items()))
    print(f"\nwrote {len(report)} scheme files to {cfg.SCHEMES_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

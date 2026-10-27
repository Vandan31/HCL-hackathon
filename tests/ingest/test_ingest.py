"""
COMPONENT : ingest (tests)
PURPOSE   : Prove pasted pages become contract-shaped scheme files and chunks, without losing or inventing text.
INPUTS    : small inline pages and scheme dicts (no files from data/ are needed)
OUTPUTS   : pass/fail
DEPENDS ON: src/ingest/convert_txt.py, src/ingest/build_chunks.py, config/ingest.py
PANEL NOTE: The split test checks that every word survives splitting and that en/hi get the same parts.
"""
from config import ingest as cfg
from src.ingest.build_chunks import scheme_chunks, split_text
from src.ingest.convert_txt import merge_scheme, parse_page

PAGE = "\n".join([
    "Ministry Of Testing",
    "Demo Scheme",
    "TagOneTagTwo",
    "Check Eligibility",
    "Details",
    "A demo scheme.﻿",
    "Benefits",
    "₹ 5,000/- per month.",
    "Application Process",
    "Offline",
    "Send by post.",
    "Frequently Asked Questions",
    "Who can apply?",
    "",
    "Application Process",
    "Second block of steps.",
    "Documents Required",
    "Aadhaar Card",
    "Sources And References",
])


def test_parse_page_maps_headings_and_drops_faq():
    name, sections = parse_page(PAGE)
    assert name == "Demo Scheme"  # line above the tag strip, not the ministry line
    assert sections == {
        "details": "A demo scheme.",                 # byte-order mark stripped
        "benefits": "₹ 5,000/- per month.",         # numbers kept as is
        "documents": "Aadhaar Card",
        # both "Application Process" blocks merged; the FAQ question in between is dropped
        "how_to_apply": "Offline\nSend by post.\nSecond block of steps.",
    }


def test_merge_keeps_hand_added_languages_and_urls():
    existing = {"id": "demo", "name": {"en": "Old", "hi": "डेमो"}, "source_url": {"en": "https://x"},
                "sections": {"benefits": {"en": "old", "hi": "हिंदी पाठ"}}, "criteria": [1]}
    s = merge_scheme(existing, "demo", "Demo Scheme", {"benefits": "new"})
    assert s["name"] == {"en": "Demo Scheme", "hi": "डेमो"}
    assert s["source_url"] == {"en": "https://x"}            # real URL not replaced by the placeholder
    assert s["sections"]["benefits"] == {"en": "new", "hi": "हिंदी पाठ"}
    assert s["criteria"] == [1]


def test_chunk_fields_and_language_fallback():
    scheme = {"id": "demo", "name": {"en": "Demo", "hi": "डेमो"}, "source_url": {"en": "https://x"},
              "sections": {"benefits": {"en": "Five rupees.", "hi": "पाँच रुपये।", "gu": "  "}}}
    chunks = scheme_chunks(scheme)
    assert [c["chunk_id"] for c in chunks] == ["demo:benefits:en", "demo:benefits:hi"]  # blank gu skipped
    hi = chunks[1]
    assert hi["scheme_name"] == "डेमो" and hi["source_url"] == "https://x"   # url falls back to en
    assert hi["text"] == "पाँच रुपये।"                                       # clean passage, no name added


def test_long_section_split_same_way_in_every_language():
    en = "\n".join(f"Line {i} has some english words here." for i in range(60))   # 420 words
    hi = "\n".join(f"पंक्ति {i} में कुछ हिंदी शब्द हैं।" for i in range(60))          # 420 words
    scheme = {"id": "demo", "name": {"en": "Demo"}, "source_url": {"en": "u"},
              "sections": {"eligibility": {"en": en, "hi": hi}}}
    chunks = scheme_chunks(scheme, max_words=400)
    assert [c["chunk_id"] for c in chunks] == [
        "demo:eligibility#1:en", "demo:eligibility#1:hi", "demo:eligibility#2:en", "demo:eligibility#2:hi"]
    assert all(len(c["text"].split()) <= 400 for c in chunks)
    # Nothing lost or reordered: the parts glue back into the original text.
    assert "\n".join(c["text"] for c in chunks if c["lang"] == "en") == en


def test_split_breaks_one_long_line_at_sentences():
    text = " ".join(f"Sentence number {i} is here." for i in range(100))  # one 500-word line
    parts = split_text(text, 2, max_words=400)
    assert len(parts) == 2 and " ".join(parts) == text
    assert parts[0].endswith(".")                               # cut at a sentence end, not mid-sentence


def test_criteria_match_engine_format_and_quote_the_scheme():
    # WHY: the eligibility engine silently treats a bad op or field as "unknown", so a typo would
    # hide a rule instead of failing; and every rule must be traceable to the scheme's own words.
    import glob
    import json
    import os
    for path in glob.glob(os.path.join(cfg.SCHEMES_DIR, "*.json")):
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        full = "\n".join(t for sec in s["sections"].values() for t in sec.values())
        for c in s.get("criteria", []):
            where = f"{s['id']}:{c.get('field')}"
            assert c["op"] in cfg.CRITERIA_OPS, where
            kind = cfg.CRITERIA_FIELDS[c["field"]]              # KeyError = field not in the shared list
            values = c["value"] if isinstance(c["value"], list) else [c["value"]]
            for v in values:
                if kind == "bool":
                    assert isinstance(v, bool), where
                elif kind == "number":
                    assert isinstance(v, (int, float)) and not isinstance(v, bool), where
                else:
                    assert v in kind, where                     # allowed lowercase string values
            assert (c["op"] in {"in", "not_in"}) == isinstance(c["value"], list), where
            assert c["text_en"].strip(), where
            assert c["source_text"] in full, where              # quoted word for word
            assert isinstance(c["verified"], bool), where


def test_every_raw_page_has_an_id():
    # WHY: ids are permanent; a new page must get one deliberately in config/ingest.py.
    import glob
    import os
    stems = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(cfg.RAW_DIR, "*.txt"))}
    assert stems <= set(cfg.SCHEME_IDS), stems - set(cfg.SCHEME_IDS)

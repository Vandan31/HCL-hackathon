"""
COMPONENT : ingest (data + ingestion)
PURPOSE   : Turn the scheme files into the one passage file that search reads.
INPUTS    : data/schemes/*.json (DATA_FORMAT §1)
OUTPUTS   : data/processed/chunks.jsonl, one chunk per scheme x section x language (DATA_FORMAT §2)
DEPENDS ON: config/ingest.py (paths, MAX_WORDS), docs/DATA_FORMAT.md
PANEL NOTE: One chunk per myScheme section keeps every answer traceable to a named section of a
            named scheme; long sections are split the same way in every language so the Hindi
            part 1 still pairs with the English part 1.

Usage (from the repo root):
  python -m src.ingest.build_chunks
  python scripts/validate_data.py
"""
import glob
import json
import math
import os
import re
import sys

from config import ingest as cfg

SECTION_ORDER = ["details", "benefits", "eligibility", "exclusions", "documents", "how_to_apply"]
LANG_ORDER = ["en", "hi", "gu"]

# Sentence end in English or Hindi (danda "।"), followed by spaces. Used only to break an
# over-long single line, so normal lists stay split at their line breaks.
_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


def word_count(text):
    return len(text.split())


def _units(text, max_words):
    """Cut text into (joiner, piece) units: one per line, plus sentences inside any over-long line.

    The joiner is what originally preceded the piece ("\n" between lines, " " between sentences),
    so gluing the units of a part back together reproduces the original text.
    """
    units = []
    for line in text.split("\n"):
        pieces = _SENTENCE_END.split(line) if word_count(line) > max_words else [line]
        for i, piece in enumerate(pieces):
            units.append(("\n" if i == 0 else " ", piece))
    return units


def _join(units):
    return "".join(j + p for j, p in units)[1:] if units else ""  # [1:] drops the leading joiner


def split_text(text, n, max_words):
    """Split text into exactly n parts of roughly equal word count, cutting at line/sentence ends."""
    if n <= 1:
        return [text]
    units = _units(text, max_words)
    total = sum(word_count(p) for _, p in units)
    parts, done = [[] for _ in range(n)], 0
    for unit in units:
        # WHY the midpoint: a unit goes to the part its middle word falls in, so parts stay balanced.
        mid = done + word_count(unit[1]) / 2
        parts[min(n - 1, int(mid * n / total))].append(unit)
        done += word_count(unit[1])
    if all(parts):
        return [_join(p) for p in parts]
    # FALLBACK: too few lines/sentences to fill n parts -> cut on words (still n parts, same order).
    words = text.split()
    size = math.ceil(len(words) / n)
    return [" ".join(words[i * size:(i + 1) * size]) for i in range(n)]


def scheme_chunks(scheme, max_words=cfg.MAX_WORDS):
    """All chunks for one scheme dict, in contract section order then en/hi/gu order."""
    sid, chunks = scheme["id"], []
    names, urls = scheme.get("name", {}), scheme.get("source_url", {})
    sections = scheme.get("sections", {})
    for sec in [s for s in SECTION_ORDER if s in sections]:
        texts = {lang: t.strip() for lang, t in sections[sec].items() if isinstance(t, str) and t.strip()}
        if not texts:
            continue
        # WHY the max over languages: every language must get the same number of parts so that
        # retrieval can swap "eligibility#2:en" for "eligibility#2:hi" (DATA_FORMAT §2).
        n = max(math.ceil(word_count(t) / max_words) for t in texts.values())
        split = {lang: split_text(t, n, max_words) for lang, t in texts.items()}
        for i in range(n):
            label = sec if n == 1 else f"{sec}#{i + 1}"
            for lang in sorted(split, key=lambda l: LANG_ORDER.index(l) if l in LANG_ORDER else 99):
                chunks.append({
                    "chunk_id": f"{sid}:{label}:{lang}",
                    "scheme_id": sid,
                    # Name and link in the chunk's language, falling back to English.
                    "scheme_name": names.get(lang) or names.get("en", sid),
                    "section": label,
                    "lang": lang,
                    "source_url": urls.get(lang) or urls.get("en", cfg.SOURCE_URL_MISSING),
                    "text": split[lang][i],
                })
    return chunks


def build(schemes_dir=cfg.SCHEMES_DIR, out_path=cfg.CHUNKS_PATH, max_words=cfg.MAX_WORDS):
    """Read every scheme file and write chunks.jsonl. Returns the list of chunks written."""
    chunks = []
    for path in sorted(glob.glob(os.path.join(schemes_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            chunks.extend(scheme_chunks(json.load(f), max_words))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in chunks:
            # ensure_ascii=False keeps ₹ and Hindi/Gujarati readable in the file (DATA_FORMAT rules).
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return chunks


def main():
    chunks = build()
    split = sorted({c["chunk_id"].rsplit(":", 1)[0] for c in chunks if "#" in c["section"]})
    print(f"wrote {len(chunks)} chunks from {len({c['scheme_id'] for c in chunks})} schemes "
          f"to {cfg.CHUNKS_PATH}")
    print(f"split sections (>{cfg.MAX_WORDS} words): {split or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

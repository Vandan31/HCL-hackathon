"""
COMPONENT : retrieval / eval (data contract check)
PURPOSE   : Catch data mistakes (wrong field names, language codes, ids) before they silently break search.
INPUTS    : data/schemes/*.json, data/processed/chunks.jsonl, data/eval/questions.jsonl (any that exist)
OUTPUTS   : list of ERROR / WARN lines; exit code 1 if any error
DEPENDS ON: docs/DATA_FORMAT.md (the rules checked here); Python standard library only
PANEL NOTE: The data contract is enforced by a script, not by hope: run it before every data push.

Usage:
  python scripts/validate_data.py
  python scripts/validate_data.py --schemes data/schemes --chunks data/processed/chunks.jsonl --questions data/eval/questions.jsonl
"""
import argparse
import glob
import json
import os
import re
import sys

# Must match docs/DATA_FORMAT.md and config/lang.py DOC_LANGS. Change all three together.
LANGS = {"en", "hi", "gu"}
SECTIONS = {"details", "benefits", "eligibility", "exclusions", "documents", "how_to_apply"}
CHUNK_FIELDS = ["chunk_id", "scheme_id", "scheme_name", "section", "lang", "source_url", "text"]
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")       # pm-kisan, pmjay
SECTION_RE = re.compile(r"^([a-z_]+)(#\d+)?$")         # eligibility, eligibility#2
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_WORDS, MIN_WORDS = 400, 5  # chunk size warnings (DATA_FORMAT §2: aim for 100-300 words)

errors, warnings = [], []


def err(where, msg):
    errors.append(f"ERROR {where}: {msg}")


def warn(where, msg):
    warnings.append(f"WARN  {where}: {msg}")


def read_jsonl(path):
    """Yield (line_number, object) for each non-blank line; report lines that aren't valid JSON."""
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                yield n, json.loads(line)
            except json.JSONDecodeError as e:
                err(f"{path}:{n}", f"not valid JSON ({e.msg}). One object per line, no trailing commas")


def check_lang_dict(where, value, required_en=True):
    """A {lang: text} dict: known languages only, no empty strings."""
    if not isinstance(value, dict):
        err(where, "must be a dict like {\"en\": \"...\", \"hi\": \"...\"}")
        return
    for lang, text in value.items():
        if lang not in LANGS:
            err(where, f"unknown language code {lang!r}; use one of {sorted(LANGS)}")
        if not isinstance(text, str) or not text.strip():
            err(where, f"{lang!r} is empty: leave the key out instead of writing \"\"")
    if required_en and "en" not in value:
        err(where, "missing \"en\"")


def check_schemes(folder):
    """Validate every data/schemes/<id>.json. Returns the set of scheme ids found."""
    ids = set()
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                s = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            err(path, f"cannot read as UTF-8 JSON: {e}")
            continue
        sid = s.get("id")
        stem = os.path.splitext(os.path.basename(path))[0]
        if not isinstance(sid, str) or not ID_RE.match(sid):
            err(path, f"id {sid!r} must be lowercase letters/digits joined by '-' (e.g. pm-kisan)")
        elif sid != stem:
            err(path, f"id {sid!r} must equal the file name {stem!r}")
        ids.add(sid)
        check_lang_dict(f"{path} name", s.get("name"))
        check_lang_dict(f"{path} source_url", s.get("source_url"))
        if not DATE_RE.match(str(s.get("collected_on", ""))):
            err(path, "collected_on must be YYYY-MM-DD")
        sections = s.get("sections")
        if not isinstance(sections, dict) or not sections:
            err(path, "sections must be a non-empty dict")
            continue
        for name, texts in sections.items():
            if name not in SECTIONS:
                err(path, f"unknown section {name!r}; use one of {sorted(SECTIONS)}")
            check_lang_dict(f"{path} sections.{name}", texts, required_en=False)
        langs = {lang for texts in sections.values() if isinstance(texts, dict) for lang in texts}
        for lang in sorted(LANGS - langs):
            warn(path, f"no section in {lang!r}: questions in that language rely on cross-language search")
    return ids


def check_chunks(path, scheme_ids):
    """Validate chunks.jsonl. Returns the set of scheme ids found in chunks."""
    seen, ids = set(), set()
    for n, c in read_jsonl(path):
        where = f"{path}:{n}"
        missing = [k for k in CHUNK_FIELDS if not isinstance(c.get(k), str) or not c.get(k).strip()]
        if missing:
            err(where, f"missing or empty fields {missing}")
            continue
        m = SECTION_RE.match(c["section"])
        if not m or m.group(1) not in SECTIONS:
            err(where, f"section {c['section']!r} must be one of {sorted(SECTIONS)} (optionally '#2' for parts)")
        if c["lang"] not in LANGS:
            err(where, f"lang {c['lang']!r} must be one of {sorted(LANGS)}")
        expected_id = f"{c['scheme_id']}:{c['section']}:{c['lang']}"
        if c["chunk_id"] != expected_id:
            err(where, f"chunk_id {c['chunk_id']!r} must be {expected_id!r}")
        if c["chunk_id"] in seen:
            err(where, f"duplicate chunk_id {c['chunk_id']!r}")
        seen.add(c["chunk_id"])
        if scheme_ids and c["scheme_id"] not in scheme_ids:
            err(where, f"scheme_id {c['scheme_id']!r} has no data/schemes/{c['scheme_id']}.json")
        words = len(c["text"].split())
        if words > MAX_WORDS:
            warn(where, f"{words} words: split into '#1', '#2' parts (same split in every language)")
        elif words < MIN_WORDS:
            warn(where, f"only {words} words: is the text complete?")
        if c["text"].startswith(c["scheme_name"]):
            warn(where, "text starts with the scheme name: not needed, retrieval adds it")
        ids.add(c["scheme_id"])
    if not seen:
        err(path, "no chunks found")
    return ids


def check_questions(path, known_ids):
    """Validate the eval question file against the scheme ids we actually have."""
    seen, total, unanswerable = set(), 0, 0
    for n, q in read_jsonl(path):
        where = f"{path}:{n}"
        total += 1
        if not q.get("id") or q["id"] in seen:
            err(where, f"id {q.get('id')!r} missing or duplicate")
        seen.add(q.get("id"))
        if not isinstance(q.get("question"), str) or not q["question"].strip():
            err(where, "question is missing or empty")
        if "lang" in q and q["lang"] not in LANGS:
            err(where, f"lang {q['lang']!r} must be one of {sorted(LANGS)} (Hinglish = \"hi\")")
        if "expected_scheme" not in q:
            err(where, "expected_scheme missing: use a scheme id, or null if the documents can't answer")
            continue
        exp = q["expected_scheme"]
        if exp is None:
            unanswerable += 1
        elif not isinstance(exp, str) or exp.strip().lower() in {"", "none", "null"}:
            err(where, f"expected_scheme {exp!r}: write JSON null, not a string")
        elif known_ids and exp not in known_ids:
            err(where, f"expected_scheme {exp!r} is not a scheme id we have (typo, or scheme not collected)")
    if total and unanswerable == 0:
        warn(path, "no unanswerable questions (expected_scheme: null): refusal can't be measured")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--schemes", default="data/schemes")
    p.add_argument("--chunks", default="data/processed/chunks.jsonl")
    p.add_argument("--questions", default="data/eval/questions.jsonl")
    a = p.parse_args()

    checked = []
    scheme_ids = check_schemes(a.schemes) if os.path.isdir(a.schemes) else set()
    if os.path.isdir(a.schemes):
        checked.append(f"{len(scheme_ids)} scheme files")
    chunk_ids = set()
    if os.path.exists(a.chunks):
        chunk_ids = check_chunks(a.chunks, scheme_ids)
        checked.append(a.chunks)
    if os.path.exists(a.questions):
        # Labels must point at schemes we can actually retrieve (chunks win over scheme files).
        check_questions(a.questions, chunk_ids or scheme_ids)
        checked.append(a.questions)

    if not checked:
        print("nothing to check: none of the data files exist yet")
        return 0
    for line in errors + warnings:
        print(line)
    print(f"\nchecked: {', '.join(checked)} | {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

# Data format contract (schemes → chunks → eval questions)

> Owner: Vandan (retrieval + eval). Producer: Jaya (data + ingest).
> Changing any field name, section name or language code here = stop and ask (CLAUDE.md §3.2).
> **Check your files before pushing:** `python scripts/validate_data.py` (stdlib only, no installs).

```
data/schemes/<id>.json        ← humans fill in, one file per scheme (copied by hand from myScheme)
        │  ingest (src/ingest/, Jaya)
        ▼
data/processed/chunks.jsonl   ← the ONLY file retrieval reads
data/eval/questions.jsonl     ← labelled test questions, read by scripts/eval.py
```

General rules for every file:
- **UTF-8** encoding (otherwise Hindi/Gujarati turn into garbage). In Python: `open(path, "w", encoding="utf-8")`
  and `json.dumps(obj, ensure_ascii=False)`.
- Language codes are exactly **`en`, `hi`, `gu`** (lowercase), the same codes `detect_language()` returns.
  If the 3rd language changes, it changes here, in `scripts/validate_data.py` and in `config/lang.py` together.
- Section names are exactly these 6:
  **`details`, `benefits`, `eligibility`, `exclusions`, `documents`, `how_to_apply`**.

---

## 1. `data/schemes/<id>.json`: one scheme (humans fill in)

```json
{
  "id": "pm-kisan",
  "name": {"en": "PM-KISAN", "hi": "पीएम-किसान", "gu": "પીએમ-કિસાન"},
  "source_url": {"en": "https://www.myscheme.gov.in/schemes/pm-kisan",
                 "hi": "https://www.myscheme.gov.in/hi/schemes/pm-kisan"},
  "collected_on": "2026-10-27",
  "collected_by": "Jaya",
  "sections": {
    "benefits":    {"en": "Rs 6,000 per year in three instalments...", "hi": "...", "gu": "..."},
    "eligibility": {"en": "...", "hi": "..."},
    "documents":   {"en": "..."}
  },
  "criteria": [ ... ]
}
```

| Field | Rule | Why |
|---|---|---|
| `id` | lowercase letters/digits joined by `-` (`pm-kisan`, `pmjay`), **same as the file name**, never renamed | Becomes `scheme_id`; eval labels point at it |
| `name` | dict of language → official name; `en` required | Shown on source cards; also added to the searched text |
| `source_url` | dict of language → exact page URL; `en` required | The proof link on every source card |
| `collected_on` | `YYYY-MM-DD` | Shows judges the data is dated and hand-collected (D-001) |
| `sections` | only the 6 names above; each is a dict language → text | Sections are matched across languages by name |
| section text | copy the page text **as is**: keep numbers (₹6,000), ages, lists. No summaries | Search can only find words that are in the text |
| missing language | **leave the key out**, never `"gu": ""` | An empty text becomes a useless chunk |
| `criteria` | used by the eligibility checklist only (PLAN §4.4); retrieval ignores it | — |

## 2. `data/processed/chunks.jsonl`: what search reads

**JSONL = one complete JSON object per line**, no commas between lines, no outer `[ ]`.
Ingest writes **one chunk per scheme × section × language**:

```json
{"chunk_id": "pm-kisan:benefits:hi", "scheme_id": "pm-kisan", "scheme_name": "पीएम-किसान", "section": "benefits", "lang": "hi", "source_url": "https://www.myscheme.gov.in/hi/schemes/pm-kisan", "text": "पात्र भूमिधारक किसान परिवारों को प्रति वर्ष 6,000 रुपये..."}
```

| Field | Exact format | What retrieval does with it |
|---|---|---|
| `chunk_id` | `<scheme_id>:<section>:<lang>`, **unique** | De-duplication; the answer engine cites it |
| `scheme_id` | = the scheme file's `id` | Eval checks "right scheme found?"; pairs language versions |
| `scheme_name` | name **in this chunk's language** (fall back to `en`) | Source card title; **added to the searched text automatically** |
| `section` | one of the 6 names (`eligibility#2` if split, see below) | Pairs language versions; added to the searched text |
| `lang` | `en` / `hi` / `gu` | Swaps in the passage in the user's language |
| `source_url` | URL for this language (fall back to `en`) | Source card link |
| `text` | **the clean passage only**: don't prepend the name, retrieval does that | Searched (BM25 + BGE-M3) and shown to the user |

**Size:** aim for **~100–300 words per chunk**. A myScheme section is usually one chunk.
If a section is longer than ~400 words, split it **the same way in every language** and number the parts:
`"section": "eligibility#1"`, `"chunk_id": "pm-kisan:eligibility#1:hi"`. Otherwise Hindi part 1 can't be paired
with English part 1.

**How search uses the file** (src/retrieval/search.py):
1. Loads every line. Searched text = `scheme_name + section + text`.
2. BM25 keyword index (lower-cased, split on spaces/punctuation incl. `-` and `।`; "PM-KISAN" → `pm`, `kisan`).
3. BGE-M3 meaning vectors, cached in `.cache/retrieval/` (rebuilt automatically when any chunk changes).
4. Per question: top 20 by keywords + top 20 by meaning → merged by rank (RRF) → chunks with meaning score
   below `MIN_SCORE` dropped (none left = refusal) → swap to the user's-language version of the same
   `scheme_id` + `section` → top 5.

## 3. `data/eval/questions.jsonl`: labelled test questions

```json
{"id": "q001", "question": "PM Kisan ka paisa kitna milta hai?", "lang": "hi", "expected_scheme": "pm-kisan"}
{"id": "q101", "question": "How do I renew my passport?", "lang": "en", "expected_scheme": null}
```

| Field | Rule |
|---|---|
| `id` | unique; keep the organisers' numbering if they have one |
| `question` | **exactly as asked**: don't fix spelling, Hinglish or mixed scripts |
| `lang` | correct answer for language detection: `en` / `hi` / `gu`; **Hinglish = `hi`** |
| `expected_scheme` | the `scheme_id` that answers it, or JSON **`null`** (not `"none"`, not `""`) if our documents can't answer it |

Build it from the organisers' 100 questions: copy each one unchanged, tag `lang` and `expected_scheme`
(the tag counts tell us **which 25 schemes to collect**), then add ~20 unanswerable questions across all 3 languages.

## 4. Before you push data

```bash
python scripts/validate_data.py            # checks all three files that exist
```
Errors (exit code 1) must be fixed; warnings are worth a look (e.g. very long chunks, a scheme with no Hindi).

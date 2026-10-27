"""
COMPONENT : API
PURPOSE   : Append one line per question to an audit log: what happened, never what was asked.
INPUTS    : a record dict with only the allowed fields
OUTPUTS   : one JSON line in data/logs/audit.jsonl (gitignored)
DEPENDS ON: config/api.py (AUDIT_PATH)
PANEL NOTE: Citizens may type income, caste or Aadhaar numbers, so the log refuses to store question text.
"""
import json
import os

# WHY: an allow-list (not a block-list), so a new field can't leak personal data by accident (Harsh's decision).
ALLOWED = {"time", "lang", "code_mixed", "chunk_ids", "refused", "refusal_reason", "provider", "latency_ms"}


def write_audit(path: str, record: dict) -> None:
    """Append record as one JSON line; raises ValueError for any field outside ALLOWED."""
    extra = set(record) - ALLOWED
    if extra:
        raise ValueError(f"audit field(s) not allowed: {sorted(extra)}")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

"""
COMPONENT : API
PURPOSE   : Prove the audit log can never store the citizen's question, answer or a key.
INPUTS    : audit records, a temp file
OUTPUTS   : pass/fail
DEPENDS ON: src/api/audit.py
PANEL NOTE: Privacy: we log what happened (language, sources, refused, latency), never what was asked.
"""
import json

import pytest

from src.api.audit import write_audit

OK = {"time": "t", "lang": "gu", "code_mixed": False, "chunk_ids": ["a"], "refused": False,
      "refusal_reason": None, "provider": "gemini#0", "latency_ms": 12}


def test_audit_rejects_query_text(tmp_path):
    with pytest.raises(ValueError):
        write_audit(str(tmp_path / "a.jsonl"), {**OK, "query": "my aadhaar is 1234"})


def test_audit_appends_lines(tmp_path):
    p = tmp_path / "logs" / "a.jsonl"
    write_audit(str(p), OK)
    write_audit(str(p), {**OK, "lang": "ta"})
    lines = p.read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["lang"] for x in lines] == ["gu", "ta"]

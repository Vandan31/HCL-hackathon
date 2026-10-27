"""
COMPONENT : answer engine
PURPOSE   : Prove the prompt confines the LLM to our passages, and that bad output or fake citations are caught.
INPUTS    : chunks, target language key, raw LLM text
OUTPUTS   : pass/fail
DEPENDS ON: src/answer/prompting.py, config/answer.py
PANEL NOTE: "How do you stop hallucinations?" -> answer only from S1..Sk, and every cited id is checked.
"""
from src.answer.prompting import build_prompt, citations_valid, parse_llm_output

CHUNK = {"chunk_id": "a", "scheme_name": "PM-KISAN", "section": "eligibility", "lang": "en",
         "text": "Landholding farmer families are eligible.", "source_url": "u", "score": 0.8}
CHUNK2 = {**CHUNK, "chunk_id": "b", "text": "Income-tax payers are excluded."}


def test_prompt_labels_passages_and_names_language():
    p = build_prompt("PM kisan?", "mr", [CHUNK, CHUNK2])
    assert "S1" in p and "S2" in p and "Marathi" in p and CHUNK["text"] in p and "PM kisan?" in p


def test_prompt_keeps_llm_inside_passages():
    p = build_prompt("q", "en", [CHUNK])
    assert "only" in p.lower() and "answerable" in p and "JSON" in p


def test_hinglish_prompt_asks_for_roman_script_mix():
    assert "Roman-script" in build_prompt("q", "hinglish", [CHUNK])


def test_parse_plain_json():
    assert parse_llm_output('{"answer":"x [S1]","cited":["S1"],"answerable":true}')["cited"] == ["S1"]


def test_parse_strips_markdown_fences():
    assert parse_llm_output('```json\n{"answer":"x","cited":[],"answerable":false}\n```') is not None
    assert parse_llm_output('```\n{"answer":"x","cited":[],"answerable":false}\n```') is not None


def test_parse_rejects_missing_fields_and_garbage():
    assert parse_llm_output('{"answer":"x"}') is None
    assert parse_llm_output('{"answer":"x","cited":"S1","answerable":true}') is None
    assert parse_llm_output("Sure! Here is") is None
    assert parse_llm_output('["not", "an", "object"]') is None


def test_citation_unknown_id_invalid():
    assert not citations_valid({"answer": "x [S3]", "cited": ["S3"], "answerable": True}, k=2)


def test_citation_in_text_but_not_listed_invalid():
    assert not citations_valid({"answer": "x [S1][S2]", "cited": ["S1"], "answerable": True}, k=2)


def test_answerable_with_no_citations_invalid():
    assert not citations_valid({"answer": "x", "cited": [], "answerable": True}, k=2)


def test_valid_citations():
    assert citations_valid({"answer": "x [S2]", "cited": ["S2"], "answerable": True}, k=2)

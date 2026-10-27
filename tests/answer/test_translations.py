"""
COMPONENT : answer engine
PURPOSE   : Prove source cards show the original passage with the right IndicTrans2 translation below it.
INPUTS    : a chunk dict, user language, a translations table / jsonl file
OUTPUTS   : pass/fail
DEPENDS ON: src/answer/translations.py
PANEL NOTE: "Show the source passage" in the user's language, without ever hiding the official text.
"""
from src.answer.translations import build_citation, load_translations, translation_target

CHUNK = {"chunk_id": "pm-kisan#elig#en#0", "scheme_id": "pm-kisan", "scheme_name": "PM-KISAN",
         "section": "eligibility", "text": "Landholding farmers...", "lang": "en",
         "source_url": "https://www.myscheme.gov.in/schemes/pm-kisan", "score": 0.8}
TR = {("pm-kisan#elig#en#0", "gu"): "જમીન ધરાવતા ખેડૂતો...", ("pm-kisan#elig#en#0", "hi"): "भूमिधारक किसान..."}


def test_gujarati_user_gets_gujarati_translation_under_original():
    c = build_citation("S1", CHUNK, "gu", False, TR)
    assert c["passage"] == CHUNK["text"] and c["passage_lang"] == "en"
    assert (c["translation"], c["translation_lang"]) == (TR[("pm-kisan#elig#en#0", "gu")], "gu")
    assert set(c) == {"id", "chunk_id", "scheme_name", "passage", "source_url",
                      "passage_lang", "translation", "translation_lang"}


def test_hinglish_user_gets_devanagari_hindi_translation():
    assert translation_target("hi", True) == "hi"
    c = build_citation("S1", CHUNK, "hi", True, TR)
    assert c["translation_lang"] == "hi" and c["translation"] == TR[("pm-kisan#elig#en#0", "hi")]


def test_same_language_passage_has_no_translation():
    c = build_citation("S1", CHUNK, "en", False, TR)
    assert c["translation"] is None and c["translation_lang"] is None


def test_missing_translation_is_none_not_error():
    c = build_citation("S1", CHUNK, "ta", False, TR)
    assert c["translation"] is None and c["translation_lang"] is None


def test_load_translations_missing_file_is_empty(tmp_path):
    assert load_translations(str(tmp_path / "nope.jsonl")) == {}


def test_load_translations_skips_bad_lines(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"chunk_id":"a","lang":"gu","text":"x","model":"indictrans2"}\nnot json\n', encoding="utf-8")
    assert load_translations(str(p)) == {("a", "gu"): "x"}

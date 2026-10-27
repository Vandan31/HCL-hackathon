"""
COMPONENT : API
PURPOSE   : Prove the offline cache finds a demo question however it is typed, and keeps Indic text intact.
INPUTS    : query strings, a temp cache file
OUTPUTS   : pass/fail
DEPENDS ON: src/api/cache.py
PANEL NOTE: The Wi-Fi-off safety net must hit on stage even if the presenter types "PM Kisan?" not "pm kisan".
"""
from src.api.cache import AnswerCache, normalise_query


def test_normalise_query_variants_match():
    assert normalise_query("PM Kisan?") == normalise_query("pm  kisan")
    assert normalise_query("PM-Kisan") == normalise_query("pm kisan")
    assert normalise_query("पैसा कैसे मिलेगा।") == normalise_query("पैसा कैसे मिलेगा")


def test_cache_roundtrip_keeps_unicode(tmp_path):
    path = tmp_path / "c.json"
    resp = {"answer": "ગુજરાતી જવાબ [S1]", "lang": "gu", "refused": False}
    AnswerCache(str(path)).put("PM Kisan?", resp)
    assert AnswerCache(str(path)).get("pm kisan") == resp
    assert "ગ" in path.read_text(encoding="utf-8")


def test_cache_miss_and_missing_file(tmp_path):
    assert AnswerCache(str(tmp_path / "none.json")).get("anything") is None

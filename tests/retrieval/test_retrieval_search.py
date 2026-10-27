"""
COMPONENT : retrieval (tests)
PURPOSE   : Prove search finds the right scheme, refuses irrelevant questions, and prefers the user's language.
INPUTS    : MOCK chunks in tests/retrieval/fixtures/mock_chunks.jsonl
OUTPUTS   : pass/fail
DEPENDS ON: src/retrieval/search.py, rank_bm25 (+ sentence-transformers for the dense tests)
PANEL NOTE: Fast tests run BM25-only; set RUN_DENSE_TESTS=1 to also test cross-language meaning search.
"""
import os

import pytest

from config import retrieval as cfg
from src.retrieval.search import Retriever, load_chunks, tokenize

CHUNKS = load_chunks(cfg.MOCK_CHUNKS_PATH)
FIELDS = {"chunk_id", "scheme_id", "scheme_name", "section", "text", "lang", "source_url",
          "score", "rrf_score"}


@pytest.fixture(scope="module")
def bm25_only():
    return Retriever(CHUNKS, use_dense=False)


def test_tokenize_keeps_hindi_words_whole():
    # WHY: a naive \w+ split would break "किसान" at its vowel signs.
    assert tokenize("पीएम किसान का पैसा।") == ["पीएम", "किसान", "का", "पैसा"]


def test_exact_scheme_name_english(bm25_only):
    r = bm25_only.search("How many instalments in PM-KISAN?", "en")
    assert r and r[0]["scheme_id"] == "pm-kisan"
    assert set(r[0]) == FIELDS


def test_hindi_query_hits_hindi_passage(bm25_only):
    r = bm25_only.search("मुफ्त एलपीजी कनेक्शन के लिए कौन आवेदन कर सकती है", "hi")
    assert r[0]["scheme_id"] == "ujjwala" and r[0]["lang"] == "hi"


def test_prefers_users_language_version(bm25_only):
    # English words match the English passage, but a Hindi user should see the Hindi twin.
    r = bm25_only.search("PM-KISAN income support instalments bank account", "hi")
    assert r[0]["chunk_id"] == "pm-kisan:benefits:hi"


def test_irrelevant_question_returns_nothing(bm25_only):
    # FALLBACK path for the answer engine: [] means "refuse".
    assert bm25_only.search("passport renewal tatkal fees", "en") == []


@pytest.mark.parametrize("q", ["", "   ", None])
def test_empty_query(bm25_only, q):
    assert bm25_only.search(q, "en") == []


def test_empty_corpus():
    assert Retriever([], use_dense=False).search("PM-KISAN", "en") == []


def test_scheme_name_is_searchable_even_if_passage_omits_it():
    # The passage text never says "Jal Seva"; index_text() adds the scheme name for search.
    # (Added to the full mock corpus: BM25 word weights are meaningless with only 2 chunks.)
    chunk = {"chunk_id": "jal:benefits:en", "scheme_id": "jal", "scheme_name": "Gram Jal Seva",
             "section": "benefits", "lang": "en", "source_url": "MOCK",
             "text": "A free tap connection for every rural household."}
    r = Retriever(CHUNKS + [chunk], use_dense=False).search("Jal Seva", "en")
    assert r and r[0]["scheme_id"] == "jal" and r[0]["text"] == chunk["text"]  # card text unchanged


def test_respects_k(bm25_only):
    assert len(bm25_only.search("scheme eligibility documents apply", "en", k=2)) <= 2


# ---- Dense (cross-language) tests: opt-in because they download an embedding model ----
dense = pytest.mark.skipif(os.environ.get("RUN_DENSE_TESTS") != "1",
                           reason="set RUN_DENSE_TESTS=1 to run dense tests (downloads a model)")


@pytest.fixture(scope="module")
def hybrid():
    # The small model keeps the test quick; the live app uses cfg.EMBED_MODEL (BGE-M3).
    return Retriever(CHUNKS, use_dense=True, model_name=os.environ.get(
        "DENSE_TEST_MODEL", cfg.FALLBACK_EMBED_MODEL))


@dense
def test_gujarati_question_finds_scheme(hybrid):
    r = hybrid.search("દીકરી માટે ખાતું કેવી રીતે ખોલવું?", "gu")
    assert r and r[0]["scheme_id"] == "ssy"


@dense
def test_cross_language_hindi_to_english_only_scheme(hybrid):
    # PM-JAY documents exist only in English; a Hindi question must still find them.
    r = hybrid.search("आयुष्मान कार्ड के लिए कौन से कागज़ चाहिए?", "hi")
    assert any(c["chunk_id"] == "pmjay:documents:en" for c in r)

"""
COMPONENT : retrieval (tests)
PURPOSE   : Prove search finds the right scheme, refuses irrelevant questions, and prefers the user's language.
INPUTS    : MOCK chunks in tests/retrieval/fixtures/mock_chunks.jsonl
OUTPUTS   : pass/fail
DEPENDS ON: src/retrieval/search.py, rank_bm25 (+ sentence-transformers for the dense tests)
PANEL NOTE: Fast tests run BM25-only; set RUN_DENSE_TESTS=1 to also test cross-language meaning search.
"""
import os

import numpy as np
import pytest

from config import retrieval as cfg
from src.retrieval.search import Retriever, load_chunks, passes_gate, tokenize

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


def _stub_dense(chunks, dense_scores):
    """A Retriever with fixed 'dense' scores instead of a model (no download, no RAM)."""
    r = Retriever(chunks, use_dense=False)
    r.embeddings = np.zeros((len(chunks), 1))           # marks dense mode as on
    r._dense_scores = lambda query: np.array(dense_scores, dtype=float)
    return r


def test_bm25_skipped_when_question_language_has_no_documents():
    # English-only chunks. Dense prefers chunk 1; BM25 (word "Ujjwala") prefers chunk 0.
    en = [c for c in CHUNKS if c["lang"] == "en"][:3]
    r = _stub_dense(en, [0.50, 0.90, 0.10])
    q = f"{en[0]['scheme_name']} {en[0]['text']}"
    assert r.rank(q, "hi")[0][0] == 1          # Hindi: no Hindi docs -> dense ranking only
    assert r.rank(q, "hi")[0] == [1, 0, 2]
    assert len(r.rank(q, "en")[0]) == 3         # English: BM25 + dense fused (both lists used)


@pytest.mark.parametrize("stats, ok", [
    ({"top": 0.90, "z": 4.0}, True),           # clear peak, high score -> answer
    ({"top": 0.90, "z": 2.0}, False),          # high score but flat (off-topic) -> refuse
    ({"top": 0.70, "z": 4.0}, False),          # peak but weak score -> refuse
])
def test_refusal_gate(stats, ok):
    assert passes_gate(stats, dense=True, min_score=0.81, min_z=2.8) is ok


def test_flat_scores_return_nothing():
    # Every chunk equally similar = off-topic question -> [] (answer engine refuses).
    r = _stub_dense(CHUNKS, [0.85] * len(CHUNKS))
    assert r.search("anything", "en") == []


def test_respects_k(bm25_only):
    assert len(bm25_only.search("scheme eligibility documents apply", "en", k=2)) <= 2


# ---- Dense (cross-language) tests: opt-in because they download an embedding model ----
dense = pytest.mark.skipif(os.environ.get("RUN_DENSE_TESTS") != "1",
                           reason="set RUN_DENSE_TESTS=1 to run dense tests (downloads a model)")


@pytest.fixture(scope="module")
def hybrid():
    return Retriever(CHUNKS, use_dense=True, model_name=os.environ.get(
        "DENSE_TEST_MODEL", cfg.FALLBACK_EMBED_MODEL))


# WHY rank() and not search(): these test cross-language RANKING. The refusal gate's z-score needs a
# realistic corpus (137 chunks); on 12 mock chunks z can't reach MIN_Z, so search() would refuse.
@dense
def test_gujarati_question_finds_scheme(hybrid):
    order = hybrid.rank("દીકરી માટે ખાતું કેવી રીતે ખોલવું?", "gu")[0]
    assert CHUNKS[order[0]]["scheme_id"] == "ssy"


@dense
def test_cross_language_hindi_to_english_only_scheme(hybrid):
    # PM-JAY documents exist only in English; a Hindi question must still find them.
    order = hybrid.rank("आयुष्मान कार्ड के लिए कौन से कागज़ चाहिए?", "hi")[0]
    assert any(CHUNKS[i]["chunk_id"] == "pmjay:documents:en" for i in order[:5])

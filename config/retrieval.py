"""
COMPONENT : retrieval
PURPOSE   : Every tunable value for search, in one place so it can be changed live in the demo.
INPUTS    : none (constants imported by src/retrieval/search.py)
OUTPUTS   : file paths, model names, ranking and refusal thresholds
DEPENDS ON: nothing
PANEL NOTE: MIN_SCORE is our "honesty dial": raise it and the assistant refuses more readily.
"""

# Where the chunks come from. Jaya's ingest writes CHUNKS_PATH; until it exists we fall back
# to the mock file below so everyone can build and test today.
CHUNKS_PATH = "data/processed/chunks.jsonl"
# MOCK: hand-written test passages (4 schemes, en/hi/gu), NOT copied from myScheme.
MOCK_CHUNKS_PATH = "tests/retrieval/fixtures/mock_chunks.jsonl"

# DEMO-KNOB: dense (meaning-based) search on/off. False = BM25 keyword search only
# (instant start-up, no model download, but no cross-language matching).
USE_DENSE = True

# DEMO-KNOB: embedding model. BGE-M3 is the strongest open multilingual retriever on Hindi
# benchmarks; if the laptop is too slow, switch to the small model (~470 MB vs ~2.2 GB).
EMBED_MODEL = "BAAI/bge-m3"
FALLBACK_EMBED_MODEL = "intfloat/multilingual-e5-small"

# Some models expect a prefix on the text (E5 was trained with "query: " / "passage: ").
MODEL_PREFIXES = {
    "BAAI/bge-m3": ("", ""),
    "intfloat/multilingual-e5-small": ("query: ", "passage: "),
    "intfloat/multilingual-e5-base": ("query: ", "passage: "),
}

# DEMO-KNOB: number of passages returned to the answer engine (= source cards shown).
TOP_K = 5

# How many results each method contributes before fusion. WHY: fusing 20 + 20 candidates
# lets a passage that's 8th by keywords but 1st by meaning still reach the top 5.
CANDIDATES = 20

# Reciprocal Rank Fusion constant: score = sum 1 / (RRF_K + rank). 60 is the standard value
# from the original RRF paper; lower = top ranks dominate more.
RRF_K = 60

# DEMO-KNOB: refusal threshold on dense cosine similarity (0-1). Passages below it are dropped;
# if none survive, search returns [] and the answer engine refuses.
# Tune on the eval set (scripts/eval.py): it trades wrong answers against false refusals.
MIN_SCORE = 0.45

# DEMO-KNOB: same idea when running BM25-only (USE_DENSE=False or the model failed to load).
# BM25 scores aren't 0-1, so this is a separate, rougher threshold.
BM25_MIN_SCORE = 1.0

# DEMO-KNOB: show the passage in the user's language when the same scheme section exists in it
# (Hindi question -> Hindi passage even if the English one ranked higher).
PREFER_USER_LANG = True

# Where chunk embeddings are cached so restarts are fast (keyed by model + chunk file contents).
CACHE_DIR = ".cache/retrieval"

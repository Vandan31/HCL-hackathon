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

# DEMO-KNOB: embedding model. MIN_SCORE below is calibrated for THIS model (D-012): change both together.
# WHY e5-small and not BGE-M3: measured, BGE-M3 (2.27 GB) crashed out of memory on a 6 GB laptop;
# e5-small ran the 98-question eval at recall@5 0.949, ~29 ms/query. Switch back to "BAAI/bge-m3"
# only on a machine with >= 16 GB RAM, then re-run `scripts/eval.py --sweep` and re-tune MIN_SCORE.
EMBED_MODEL = "intfloat/multilingual-e5-small"
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
# Tune on the eval set (scripts/eval.py --sweep): it trades wrong answers against false refusals.
# e5 scores sit in 0.77-0.93, so the old 0.45 never refused. Used together with MIN_Z below (D-013).
MIN_SCORE = 0.81

# DEMO-KNOB: second refusal gate: how many standard deviations the best chunk must stand above the
# average chunk for this question. Off-topic questions score evenly against everything.
# Measured (D-013, 98 questions): MIN_Z 2.8 + MIN_SCORE 0.81 -> recall@5 0.936, false refusal 0.064,
# refusal recall 0.75. Raise MIN_Z -> refuses more (3.05: refusal 0.90 but false refusal 0.13).
# NOTE: z grows with corpus size; re-tune with the sweep if the number of chunks changes a lot (137 now).
MIN_Z = 2.8

# DEMO-KNOB: use BM25 only when the question's language has documents. WHY: measured (D-013), a Hindi or
# Gujarati question against English-only chunks gets a noise BM25 ranking that pushed the wrong scheme
# to 1st place (right-scheme-first 0.603 -> 0.974 with this on).
BM25_SAME_LANG_ONLY = True

# DEMO-KNOB: same idea when running BM25-only (USE_DENSE=False or the model failed to load).
# BM25 scores aren't 0-1, so this is a separate, rougher threshold.
BM25_MIN_SCORE = 1.0

# DEMO-KNOB: show the passage in the user's language when the same scheme section exists in it
# (Hindi question -> Hindi passage even if the English one ranked higher).
PREFER_USER_LANG = True

# Where chunk embeddings are cached so restarts are fast (keyed by model + chunk file contents).
CACHE_DIR = ".cache/retrieval"

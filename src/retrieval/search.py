"""
COMPONENT : retrieval
PURPOSE   : Find the scheme passages most relevant to a citizen's question, in any of our languages.
INPUTS    : question text + detected language (from src/lang)
OUTPUTS   : up to TOP_K chunks: chunk_id, scheme_id, scheme_name, section, text, lang, source_url,
            score (dense cosine 0-1, the refusal signal) and rrf_score (ranking). [] = nothing relevant.
DEPENDS ON: config/retrieval.py, data/processed/chunks.jsonl (Jaya's ingest) or the MOCK fixture
PANEL NOTE: Hybrid search: BM25 catches exact scheme names, BGE-M3 matches meaning across languages,
            Reciprocal Rank Fusion merges the two rankings.
"""
import hashlib
import json
import logging
import os
import re

import numpy as np

from config import retrieval as cfg

log = logging.getLogger(__name__)

# Split on spaces and punctuation, including the Devanagari danda "।".
# WHY not \w+? Python's \w treats Hindi/Gujarati vowel signs (matras) as non-letters and would
# cut "किसान" into pieces; splitting on separators keeps whole words.
_TOKEN = re.compile(r"[^\s.,;:!?\"'()\[\]{}।॥|/\\\-–—]+")


def tokenize(text):
    """Lower-cased word tokens for BM25 (works for Latin, Devanagari and Gujarati)."""
    return _TOKEN.findall(text.lower())


def index_text(chunk):
    """Text that is searched: scheme name + section + passage.

    WHY: a passage like "Rs 6,000 per year in three instalments" never names its scheme, so a
    question saying "PM Kisan" would miss it. Adding the name here (not in the data) keeps the
    stored `text` clean for the source card and means ingest can't forget it.
    """
    section = chunk.get("section", "").split("#")[0].replace("_", " ")  # "how_to_apply#2" -> "how to apply"
    return f"{chunk.get('scheme_name', '')} {section}: {chunk['text']}"


def load_chunks(path=None):
    """Read chunks.jsonl (one JSON object per line). Falls back to the MOCK file if missing."""
    path = path or cfg.CHUNKS_PATH
    if not os.path.exists(path):
        # FALLBACK: ingest hasn't produced real chunks yet -> use the mock passages so the
        # rest of the team can build against a working search today.
        log.warning("chunks file %s not found, using MOCK chunks %s", path, cfg.MOCK_CHUNKS_PATH)
        path = cfg.MOCK_CHUNKS_PATH
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class Retriever:
    """Holds the BM25 index and (optionally) the dense embeddings for one set of chunks."""

    def __init__(self, chunks, use_dense=cfg.USE_DENSE, model_name=cfg.EMBED_MODEL):
        self.chunks = chunks
        self.model = None
        self.model_name = None
        self.embeddings = None

        # BM25 keyword index over all chunks (every language in one index; a query only
        # matches words in its own language, which is exactly what we want from BM25).
        from rank_bm25 import BM25Okapi
        self.bm25 = BM25Okapi([tokenize(index_text(c)) for c in chunks]) if chunks else None

        if use_dense and chunks:
            self._load_dense(model_name)

    def _load_dense(self, model_name):
        """Load the embedding model and embed all chunks (cached on disk between runs)."""
        from sentence_transformers import SentenceTransformer
        for name in (model_name, cfg.FALLBACK_EMBED_MODEL):
            try:
                self.model = SentenceTransformer(name)
                self.model_name = name
                break
            except Exception as e:  # FALLBACK: download/memory failure -> try the small model
                log.warning("could not load embedding model %s: %s", name, e)
        if self.model is None:
            # FALLBACK: no embedding model at all -> BM25-only search instead of crashing.
            log.warning("dense search disabled, running BM25-only")
            return
        self.embeddings = self._cached_chunk_embeddings()

    def _cached_chunk_embeddings(self):
        """Embed chunk texts, reusing a cache file keyed by model name + chunk contents."""
        texts = [index_text(c) for c in self.chunks]
        key = hashlib.sha1((self.model_name + "\n".join(texts)).encode("utf-8")).hexdigest()[:16]
        path = os.path.join(cfg.CACHE_DIR, f"emb_{key}.npy")
        if os.path.exists(path):
            return np.load(path)
        _, passage_prefix = cfg.MODEL_PREFIXES.get(self.model_name, ("", ""))
        # normalize_embeddings=True -> a dot product equals cosine similarity (0-1 range here).
        emb = self.model.encode([passage_prefix + t for t in texts], normalize_embeddings=True,
                                batch_size=16, show_progress_bar=False)
        os.makedirs(cfg.CACHE_DIR, exist_ok=True)
        np.save(path, emb)
        return emb

    def _dense_scores(self, query):
        """Cosine similarity between the query and every chunk."""
        query_prefix, _ = cfg.MODEL_PREFIXES.get(self.model_name, ("", ""))
        q = self.model.encode([query_prefix + query], normalize_embeddings=True,
                              show_progress_bar=False)[0]
        return self.embeddings @ q

    def search(self, query, lang, k=cfg.TOP_K):
        """Return up to k relevant chunks for `query`; [] means the documents don't cover it."""
        if not self.chunks or not (query or "").strip():
            return []

        bm25 = self.bm25.get_scores(tokenize(query))
        dense = self._dense_scores(query) if self.embeddings is not None else None

        # Each method nominates its top CANDIDATES; RRF gives 1/(RRF_K + rank) per list.
        # PANEL: Why RRF and not a weighted sum? -> BM25 scores (0..~20) and cosine (0..1) aren't
        # on the same scale; RRF only uses ranks, so no fragile weight tuning.
        rrf = {}
        rankings = [np.argsort(-bm25)[:cfg.CANDIDATES]]
        if dense is not None:
            rankings.append(np.argsort(-dense)[:cfg.CANDIDATES])
        for ranking in rankings:
            for rank, i in enumerate(ranking):
                rrf[int(i)] = rrf.get(int(i), 0.0) + 1.0 / (cfg.RRF_K + rank + 1)

        results = []
        for i in sorted(rrf, key=rrf.get, reverse=True):
            # Refusal gate: drop passages that aren't actually relevant. RRF can't do this
            # (the best of a bad bunch still ranks 1st), so we use an absolute score.
            if dense is not None:
                score = float(dense[i])
                if score < cfg.MIN_SCORE:
                    continue
            else:
                score = float(bm25[i])
                if score < cfg.BM25_MIN_SCORE:
                    continue
            results.append({**self.chunks[i], "score": round(score, 4),
                            "rrf_score": round(rrf[i], 6)})

        if cfg.PREFER_USER_LANG:
            results = self._prefer_language(results, lang)
        return self._dedupe(results)[:k]

    def _prefer_language(self, results, lang):
        """Swap a passage for the same scheme section in the user's language, if we have it."""
        by_key = {(c["scheme_id"], c["section"], c["lang"]): c for c in self.chunks}
        swapped = []
        for r in results:
            twin = by_key.get((r["scheme_id"], r["section"], lang))
            if twin and r["lang"] != lang:
                # Keep the ranking/score that earned the slot; show the user's-language text.
                r = {**twin, "score": r["score"], "rrf_score": r["rrf_score"]}
            swapped.append(r)
        return swapped

    @staticmethod
    def _dedupe(results):
        """Keep one passage per chunk_id (language swaps can create duplicates)."""
        seen, out = set(), []
        for r in results:
            if r["chunk_id"] not in seen:
                seen.add(r["chunk_id"])
                out.append(r)
        return out


# One shared retriever for the API, built on first use. WHY lazy: loading BGE-M3 takes
# seconds, and importing this module (e.g. in tests) shouldn't trigger it.
_default = None


def search(query, lang, k=cfg.TOP_K):
    """Interface function from docs/COMPONENTS.md: search(query, lang, k) -> list of chunks."""
    global _default
    if _default is None:
        _default = Retriever(load_chunks())
    return _default.search(query, lang, k)


def reset():
    """Forget the shared retriever (call after ingest rebuilds chunks.jsonl, or in tests)."""
    global _default
    _default = None

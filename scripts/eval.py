"""
COMPONENT : eval
PURPOSE   : Measure language detection + retrieval on a labelled question set, so every number
            we show judges is measured, not guessed.
INPUTS    : a JSONL file, one question per line:
              {"id": "q1", "question": "...", "lang": "hi", "expected_scheme": "pm-kisan"}
            expected_scheme = null  -> the documents can't answer it (we expect a refusal: []).
            lang is optional (skip language accuracy for that row if missing).
OUTPUTS   : metrics table (overall + per language); --sweep prints a MIN_SCORE tuning table;
            --json writes per-question results for debugging.
DEPENDS ON: src/lang/detect.py, src/retrieval/search.py, config/retrieval.py
PANEL NOTE: Run `python scripts/eval.py data/eval/questions.jsonl` live: real numbers in seconds.

Usage:
  python scripts/eval.py data/eval/sample_questions.jsonl
  python scripts/eval.py data/eval/questions.jsonl --sweep
  python scripts/eval.py data/eval/questions.jsonl --bm25-only --json out.json
"""
import argparse
import json
import os
import sys
import time

# WHY: lets `python scripts/eval.py` import config/ and src/ from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import retrieval as cfg  # noqa: E402
from src.lang.detect import detect_language  # noqa: E402
from src.retrieval.search import Retriever, load_chunks  # noqa: E402


def load_questions(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run(questions, retriever, k):
    """Run every question once with NO score threshold, keeping raw scores for later filtering."""
    rows = []
    saved_min, saved_bm25_min = cfg.MIN_SCORE, cfg.BM25_MIN_SCORE
    # WHY: collect everything once (threshold 0) so --sweep can test many thresholds
    # without re-running the model for each one.
    cfg.MIN_SCORE, cfg.BM25_MIN_SCORE = -1.0, -1.0
    try:
        for q in questions:
            t0 = time.perf_counter()
            lang_info = detect_language(q["question"])
            hits = retriever.search(q["question"], lang_info["lang"], k=k)
            ms = (time.perf_counter() - t0) * 1000
            rows.append({**q, "detected": lang_info, "latency_ms": round(ms, 1),
                         "hits": [(h["scheme_id"], h["score"]) for h in hits]})
    finally:
        cfg.MIN_SCORE, cfg.BM25_MIN_SCORE = saved_min, saved_bm25_min
    return rows


def metrics(rows, threshold):
    """Compute the metric table for one refusal threshold."""
    answerable = [r for r in rows if r.get("expected_scheme")]
    unanswerable = [r for r in rows if not r.get("expected_scheme")]

    def kept(r):
        return [s for s, score in r["hits"] if score >= threshold]

    recall = [r["expected_scheme"] in kept(r) for r in answerable]
    false_refusal = [not kept(r) for r in answerable]
    refused = [not kept(r) for r in unanswerable]
    lang_ok = [r["detected"]["lang"] == r["lang"] for r in rows if r.get("lang")]
    lat = sorted(r["latency_ms"] for r in rows)

    def pct(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    def quantile(p):
        return lat[min(len(lat) - 1, int(p * len(lat)))] if lat else None

    return {"n": len(rows), "n_answerable": len(answerable), "n_unanswerable": len(unanswerable),
            "recall_at_k": pct(recall), "false_refusal_rate": pct(false_refusal),
            "refusal_recall": pct(refused), "lang_accuracy": pct(lang_ok),
            "p50_ms": quantile(0.5), "p95_ms": quantile(0.95)}


def print_table(title, m):
    print(f"\n{title}")
    for key, val in m.items():
        print(f"  {key:<20} {val}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("questions", help="JSONL question file")
    p.add_argument("--chunks", default=None, help="chunks.jsonl (default: config, else MOCK)")
    p.add_argument("--k", type=int, default=cfg.TOP_K)
    p.add_argument("--bm25-only", action="store_true", help="skip the embedding model")
    p.add_argument("--model", default=cfg.EMBED_MODEL, help="embedding model name")
    p.add_argument("--sweep", action="store_true", help="try several MIN_SCORE values")
    p.add_argument("--json", help="write per-question results here")
    a = p.parse_args()

    retriever = Retriever(load_chunks(a.chunks), use_dense=not a.bm25_only, model_name=a.model)
    mode = f"dense={retriever.model_name}" if retriever.embeddings is not None else "BM25-only"
    rows = run(load_questions(a.questions), retriever, a.k)
    threshold = cfg.MIN_SCORE if retriever.embeddings is not None else cfg.BM25_MIN_SCORE

    print(f"Measured on {len(rows)} questions | {mode} | k={a.k} | threshold={threshold}")
    print_table("OVERALL", metrics(rows, threshold))
    for lang in sorted({r.get("lang") for r in rows if r.get("lang")}):
        print_table(f"LANG = {lang}", metrics([r for r in rows if r.get("lang") == lang], threshold))

    if a.sweep:
        # Higher threshold -> more refusals: refusal_recall goes up, but so do false refusals.
        # Pick the value where both are acceptable, then set MIN_SCORE in config/retrieval.py.
        print("\nMIN_SCORE sweep   recall@k  false_refusal  refusal_recall")
        steps = [x / 100 for x in range(20, 80, 5)] if retriever.embeddings is not None \
            else [0.5, 1, 2, 3, 4, 5, 6, 8, 10]
        for t in steps:
            m = metrics(rows, t)
            print(f"  {t:<14}  {m['recall_at_k']!s:<8}  {m['false_refusal_rate']!s:<13}  {m['refusal_recall']}")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print(f"\nper-question results -> {a.json}")


if __name__ == "__main__":
    main()

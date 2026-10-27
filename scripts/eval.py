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
from src.retrieval.search import Retriever, load_chunks, passes_gate  # noqa: E402


def load_questions(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run(questions, retriever, k):
    """Rank every question once with NO refusal gate, keeping the gate stats for later filtering."""
    rows = []
    # WHY: rank once and store the gate stats so --sweep can test many thresholds without
    # re-running the model; the gate itself is the same passes_gate() that search() uses.
    for q in questions:
        t0 = time.perf_counter()
        lang_info = detect_language(q["question"])
        order, scores, _, stats = retriever.rank(q["question"], lang_info["lang"])
        ms = (time.perf_counter() - t0) * 1000
        hits = [(retriever.chunks[i]["scheme_id"], round(float(scores[i]), 4)) for i in order[:k]]
        rows.append({**q, "detected": lang_info, "latency_ms": round(ms, 1), "hits": hits,
                     "gate": stats})
    return rows


def metrics(rows, dense, min_score=None, min_z=None):
    """Compute the metric table for one refusal setting (None = values from config)."""
    answerable = [r for r in rows if r.get("expected_scheme")]
    unanswerable = [r for r in rows if not r.get("expected_scheme")]

    def kept(r):
        if not passes_gate(r["gate"], dense, min_score, min_z):
            return []
        if dense:
            return [s for s, _ in r["hits"]]
        # BM25-only: same per-passage floor as search()
        return [s for s, score in r["hits"] if score >= (cfg.BM25_MIN_SCORE if min_score is None else min_score)]

    recall = [r["expected_scheme"] in kept(r) for r in answerable]
    # Right scheme as the FIRST passage: what the answer engine leans on most.
    top1 = [kept(r)[:1] == [r["expected_scheme"]] for r in answerable]
    false_refusal = [not kept(r) for r in answerable]
    refused = [not kept(r) for r in unanswerable]
    lang_ok = [r["detected"]["lang"] == r["lang"] for r in rows if r.get("lang")]
    lat = sorted(r["latency_ms"] for r in rows)

    def pct(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    def quantile(p):
        return lat[min(len(lat) - 1, int(p * len(lat)))] if lat else None

    return {"n": len(rows), "n_answerable": len(answerable), "n_unanswerable": len(unanswerable),
            "recall_at_k": pct(recall), "top1_accuracy": pct(top1),
            "false_refusal_rate": pct(false_refusal),
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
    dense = retriever.embeddings is not None
    gate = f"MIN_SCORE={cfg.MIN_SCORE} MIN_Z={cfg.MIN_Z}" if dense else f"BM25_MIN_SCORE={cfg.BM25_MIN_SCORE}"

    print(f"Measured on {len(rows)} questions | {mode} | k={a.k} | {gate}")
    print_table("OVERALL", metrics(rows, dense))
    for lang in sorted({r.get("lang") for r in rows if r.get("lang")}):
        print_table(f"LANG = {lang}", metrics([r for r in rows if r.get("lang") == lang], dense))

    if a.sweep:
        # Stricter gate -> more refusals: refusal_recall goes up, but so do false refusals.
        # Pick the setting where both are acceptable, then set it in config/retrieval.py.
        def line(label, m):
            print(f"  {label:<14}  {m['recall_at_k']!s:<8}  {m['top1_accuracy']!s:<6}  "
                  f"{m['false_refusal_rate']!s:<13}  {m['refusal_recall']}")
        head = "recall@k  top1    false_refusal  refusal_recall"
        if dense:
            print(f"\nMIN_Z sweep (MIN_SCORE={cfg.MIN_SCORE})  {head}")
            for t in [x / 100 for x in range(200, 361, 10)]:
                line(f"MIN_Z {t}", metrics(rows, dense, min_z=t))
            print(f"\nMIN_SCORE sweep (MIN_Z={cfg.MIN_Z})  {head}")
            # WHY up to 0.95: e5 cosine scores sit around 0.77-0.93 (D-012)
            for t in [x / 100 for x in range(70, 96, 1)]:
                line(f"MIN_SCORE {t}", metrics(rows, dense, min_score=t))
        else:
            print(f"\nBM25_MIN_SCORE sweep  {head}")
            for t in [0.5, 1, 2, 3, 4, 5, 6, 8, 10]:
                line(f"BM25 {t}", metrics(rows, dense, min_score=t))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print(f"\nper-question results -> {a.json}")


if __name__ == "__main__":
    main()

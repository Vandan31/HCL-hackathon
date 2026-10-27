"""
COMPONENT : answer engine (stress test + benchmark tooling)
PURPOSE   : Run hard, realistic cases through the real answer engine with the live LLM keys, grade each one,
            and measure speed (p50/p95, plus a concurrent burst).
INPUTS    : tests/answer/fixtures/stress_cases.json; keys from .env; models from config/answer.py
OUTPUTS   : a printed pass/fail table + latency numbers; full results in data/logs/stress_<time>.json (gitignored)
DEPENDS ON: src/answer (answer, KeyPool); network access to Gemini/Groq
PANEL NOTE: Our "measured" numbers come from this script. Re-run it before the demo:
            .venv/bin/python scripts/stress_answer.py            (all cases + burst)
            .venv/bin/python scripts/stress_answer.py --no-burst
"""
import json
import os
import sys
import threading
import time
from collections import Counter
from datetime import datetime

# WHY: run from the repo root as a plain script, so make `config` and `src` importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CASES_PATH = "tests/answer/fixtures/stress_cases.json"
BURST_SIZE = 5  # concurrent requests in the burst test (keep small: free-tier quota)


def grade(spec: dict, r: dict) -> list[str]:
    """Return the list of problems with result r against the case spec ([] = pass)."""
    problems = []
    expect = spec.get("expect", "any")
    if expect == "answer" and r["refused"]:
        problems.append(f"expected an answer, got refusal ({r['refusal_reason']})")
    elif expect == "refuse" and not r["refused"]:
        problems.append("expected a refusal, got an answer")
    elif expect == "low_score" and r["refusal_reason"] != "low_score":
        problems.append(f"expected low_score refusal, got {r['refusal_reason'] or 'an answer'}")
    if not r["refused"]:
        cited = {c["id"] for c in r["citations"]}
        problems += [f"did not cite {s}" for s in spec.get("must_cite", []) if s not in cited]
        if spec.get("expect_any") and not any(x in r["answer"] for x in spec["expect_any"]):
            problems.append(f"none of {spec['expect_any']} in answer")
    # WHY: forbidden text is checked even on refusals (a leaked injection is a failure either way).
    problems += [f"forbidden text {f!r} in answer" for f in spec.get("forbid", []) if f in r["answer"]]
    return problems


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolated percentile (same method as numpy's default)."""
    v = sorted(values)
    k = (len(v) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 2)


def run_case(case: dict, pool) -> dict:
    """One case through answer(); 503-style failures are recorded, not raised."""
    from src.answer.generate import answer
    from src.answer.llm_pool import LLMUnavailable
    t = time.perf_counter()
    try:
        r = answer(case["query"], case["lang_info"], case["chunks"], llm=pool.complete)
    except LLMUnavailable as e:
        r = {"refused": True, "refusal_reason": f"LLM_UNAVAILABLE ({e})", "answer": "", "citations": [],
             "provider": None}
    r["ms"] = round((time.perf_counter() - t) * 1000)
    return r


def main() -> int:
    from config.answer import GEMINI_MODEL, GROQ_MODEL, KEY_COOLDOWN_S, LLM_TIMEOUT_S
    from src.answer.llm_pool import KeyPool, entries_from_env, load_env_file

    load_env_file(".env")
    pool = KeyPool(entries_from_env(os.environ, GEMINI_MODEL, GROQ_MODEL), KEY_COOLDOWN_S, timeout_s=LLM_TIMEOUT_S)
    cases = json.load(open(CASES_PATH, encoding="utf-8"))["cases"]
    print(f"models: gemini={GEMINI_MODEL} groq={GROQ_MODEL} · {len(cases)} cases\n")

    results = []
    for case in cases:
        r = run_case(case, pool)
        problems = grade(case, r)
        results.append({"id": case["id"], "pass": not problems, "problems": problems, **r})
        mark = "PASS" if not problems else "FAIL"
        print(f"{mark} {case['id']:<32} {r['ms']:>6} ms  {r.get('provider') or '-':<8} "
              f"{'refused:' + str(r['refusal_reason']) if r['refused'] else 'answered'}"
              + (f"  <- {'; '.join(problems)}" if problems else ""))
        if not r["refused"] or problems:
            print(f"     {r['answer'][:220]}")

    passed = sum(x["pass"] for x in results)
    llm_ms = [x["ms"] for x in results if x.get("provider")]
    print(f"\nRESULT: {passed}/{len(results)} passed")
    if llm_ms:
        print(f"LATENCY (cases that called the LLM, n={len(llm_ms)}): p50={percentile(llm_ms, 50)} ms "
              f"p95={percentile(llm_ms, 95)} ms max={max(llm_ms)} ms")
    print("PROVIDERS:", dict(Counter(x.get("provider") or "none" for x in results)))

    burst = []
    if "--no-burst" not in sys.argv:
        # WHY: several citizens at once; FastAPI runs requests in threads, so we do the same.
        case = next(c for c in cases if c["id"].startswith("A01"))
        lock = threading.Lock()

        def worker():
            r = run_case(case, pool)
            with lock:
                burst.append(r)

        t = time.perf_counter()
        threads = [threading.Thread(target=worker) for _ in range(BURST_SIZE)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        wall = round((time.perf_counter() - t) * 1000)
        ok = sum(not r["refused"] for r in burst)
        print(f"BURST: {BURST_SIZE} concurrent -> {ok}/{BURST_SIZE} answered, wall {wall} ms, "
              f"per-request p50={percentile([r['ms'] for r in burst], 50)} ms max={max(r['ms'] for r in burst)} ms, "
              f"providers={dict(Counter(r.get('provider') or 'none' for r in burst))}")

    os.makedirs("data/logs", exist_ok=True)
    path = f"data/logs/stress_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "burst": burst}, f, ensure_ascii=False, indent=1)
    print("full results:", path)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

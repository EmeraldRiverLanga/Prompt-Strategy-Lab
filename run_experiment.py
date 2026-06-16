import json
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.dataset import load_data
from src.questions import QUESTIONS, answer_key
from src.strategies import zero_shot, chain_of_thought, role_prompting, code_writing
from src.llm_client import ask, reset_usage, get_usage
from src.evaluation import is_correct, extract_answer

REPEATS = 3  # repeat the whole suite to expose run-to-run variance

# pandas expressions may legitimately use these; everything else (open, __import__, ...) stays blocked
SAFE_BUILTINS = {"len": len, "round": round, "sum": sum, "min": min, "max": max,
                 "abs": abs, "sorted": sorted, "int": int, "float": float, "str": str}


def run(strategy, table_text, truths):
    """Send every question through one prompt-building strategy."""
    results = []
    for q in QUESTIONS:
        built = strategy(table_text, q.text)
        reply = ask(built["prompt"], system=built["system"])
        results.append((q, reply, is_correct(reply, truths[q.id])))
    return results


def run_self_consistency(table_text, truths, n=5):
    """Run Chain-of-Thought n times at higher temperature and take the majority answer."""
    results = []
    for q in QUESTIONS:
        built = chain_of_thought(table_text, q.text)
        answers = [extract_answer(ask(built["prompt"], system=built["system"], temperature=0.7))
                   for _ in range(n)]
        voted = Counter(answers).most_common(1)[0][0]
        reply = f"Answer: {voted}"
        results.append((q, reply, is_correct(reply, truths[q.id])))
    return results


def run_iterative(table_text, truths):
    """Self-refinement: the model answers, then reviews and revises its own answer."""
    results = []
    for q in QUESTIONS:
        built = chain_of_thought(table_text, q.text)
        draft = ask(built["prompt"], system=built["system"])
        review = (
            f"{built['prompt']}\n\n"
            f"Your previous answer was:\n{draft}\n\n"
            "Review it critically and fix any mistake. End with 'Answer: <final answer>'."
        )
        final = ask(review, system=built["system"])
        results.append((q, final, is_correct(final, truths[q.id])))
    return results


def run_code_writing(df, truths, max_retries=2):
    """Ask for pandas code, execute it, and on error feed the error back and retry.

    Self-refinement applied to code: a syntax/runtime error is an objective signal,
    unlike a wrong reasoning answer, so retrying here actually helps.
    """
    results = []
    for q in QUESTIONS:
        built = code_writing(None, q.text)
        prompt = built["prompt"]
        result = None
        for _ in range(max_retries + 1):
            code = ask(prompt, system=built["system"]).strip().strip("`")
            code = code.removeprefix("python").strip()
            try:
                result = eval(code, {"__builtins__": SAFE_BUILTINS, "df": df, "pd": pd})
                break
            except Exception as exc:
                result = f"ERROR: {exc}"
                prompt = (
                    f"{built['prompt']}\n\n"
                    f"Your previous code was:\n{code}\n"
                    f"It failed with this error: {exc}\n"
                    "Output a corrected single-line expression, code only."
                )
        reply = f"Answer: {result}"
        results.append((q, reply, is_correct(reply, truths[q.id])))
    return results


def accuracy(results):
    """Fraction of correct answers."""
    return sum(c for _, _, c in results) / len(results)


def by_difficulty(results):
    """Correct/total per difficulty level as 'k/n' strings."""
    out = {}
    for level in ("easy", "medium", "hard"):
        marks = [c for q, _, c in results if q.difficulty == level]
        out[level] = f"{sum(marks)}/{len(marks)}"
    return out


def print_detail(name, results, truths):
    """Print per-question pass/fail for one strategy."""
    print(f"\nStrategy: {name}")
    for q, reply, correct in results:
        mark = "PASS" if correct else "FAIL"
        print(f"  [{mark}] [{q.difficulty:6}] {q.id}: model={extract_answer(reply)!r} truth={truths[q.id]!r}")
    d = by_difficulty(results)
    total = sum(c for _, _, c in results)
    print(f"  easy: {d['easy']}  medium: {d['medium']}  hard: {d['hard']}  TOTAL: {total}/{len(results)}")


def evaluate_all(df, table_text, truths):
    """Run every strategy once, measuring accuracy, token usage, and latency."""
    runners = [
        ("zero_shot (baseline)", lambda: run(zero_shot, table_text, truths)),
        ("chain_of_thought", lambda: run(chain_of_thought, table_text, truths)),
        ("role_prompting", lambda: run(role_prompting, table_text, truths)),
        ("self_consistency (CoT x5, vote)", lambda: run_self_consistency(table_text, truths)),
        ("iterative (self-refine)", lambda: run_iterative(table_text, truths)),
        ("code_writing (super-prompt)", lambda: run_code_writing(df, truths)),
    ]
    measured = {}
    for name, runner in runners:
        reset_usage()
        start = time.perf_counter()
        results = runner()
        latency = time.perf_counter() - start
        measured[name] = {"results": results, "usage": get_usage(), "latency_s": round(latency, 1)}
    return measured


def _jsonable(value):
    """Coerce numpy scalars (from pandas) into plain Python types for JSON."""
    return value.item() if hasattr(value, "item") else str(value)


def save_run(measured, truths, path):
    """Write one run's full results to JSON for offline auditing and re-grading."""
    payload = {"timestamp": datetime.now().isoformat(timespec="seconds"), "strategies": {}}
    for name, m in measured.items():
        payload["strategies"][name] = {
            "accuracy": round(accuracy(m["results"]), 3),
            "by_difficulty": by_difficulty(m["results"]),
            "usage": m["usage"],
            "latency_s": m["latency_s"],
            "questions": [
                {"id": q.id, "difficulty": q.difficulty,
                 "answer": extract_answer(reply), "truth": truths[q.id], "correct": correct}
                for q, reply, correct in m["results"]
            ],
        }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_jsonable), encoding="utf-8")


if __name__ == "__main__":
    df = load_data()
    table_text = df.to_csv(index=False)
    truths = answer_key(df)

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    scores, costs, latencies, calls = {}, {}, {}, {}

    for r in range(REPEATS):
        print(f"\n========== RUN {r + 1} / {REPEATS} ==========")
        measured = evaluate_all(df, table_text, truths)

        for name, m in measured.items():
            if r == 0:
                print_detail(name, m["results"], truths)
            scores.setdefault(name, []).append(round(accuracy(m["results"]) * len(QUESTIONS)))
            costs.setdefault(name, []).append(m["usage"]["est_cost_usd"])
            latencies.setdefault(name, []).append(m["latency_s"])
            calls[name] = m["usage"]["calls"]

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_run(measured, truths, results_dir / f"run_{r + 1}_{stamp}.json")

    print(f"\n========== SUMMARY over {REPEATS} runs ==========")
    n = len(QUESTIONS)
    for name in scores:
        runs = scores[name]
        mean, std = statistics.mean(runs), statistics.pstdev(runs)
        cost, lat = statistics.mean(costs[name]), statistics.mean(latencies[name])
        print(f"{name:34} {mean:4.1f}/{n} +/- {std:.1f}  runs={runs}  calls={calls[name]:3}  ~${cost:.4f}  {lat:.0f}s")
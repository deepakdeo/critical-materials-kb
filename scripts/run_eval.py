"""Regression-test the RAG pipeline against a golden Q/A set.

Loads questions from eval/golden_set.json, runs each through the query chain,
and grades the response against per-question rubrics (must_cite_any,
must_mention_any, must_not_contain, expected_verdict, min_confidence).

Unlike exact-match evaluation, this uses rubric-based grading because LLM
answers vary run-to-run. A question passes if ALL of its rubric checks pass.

Usage:
    python scripts/run_eval.py                      # run full golden set
    python scripts/run_eval.py --filter factual     # run one category
    python scripts/run_eval.py --id factual_001     # run a single question
    python scripts/run_eval.py --quiet              # only summary table
    python scripts/run_eval.py --save results.json  # custom output path

Output:
    - Per-question results printed to stdout
    - Summary table at the end (per-category + overall pass rate)
    - Detailed JSON written to eval/results/<timestamp>.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path when running as a script
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.generation.chains import query  # noqa: E402

logging.basicConfig(level=logging.WARNING)  # Quiet chain logs during eval


GOLDEN_SET_PATH = _ROOT / "eval" / "golden_set.json"
RESULTS_DIR = _ROOT / "eval" / "results"


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> list[dict[str, Any]]:
    """Load the golden question set from disk."""
    with path.open() as f:
        data = json.load(f)
    return data["questions"]


def grade_response(
    question_record: dict[str, Any],
    response: Any,
) -> dict[str, Any]:
    """Grade a response against a question's rubric.

    Returns a dict of individual check results plus an overall `passed` bool.
    A question passes only if every applicable check passes.
    """
    checks: dict[str, bool] = {}

    answer_lower = (response.answer or "").lower()
    source_names = {s.name for s in response.sources}

    # --- verdict check ---
    # Grading is permissive: when a question expects PASS, a FAIL(minor) is
    # also accepted because the verifier treats those as usable answers with
    # a small nitpick (the user sees the amber "minor" badge, not a fallback).
    # Only FAIL(major) and FAIL(minor) without the expected keywords count as
    # a real miss. Unanswerable questions expect FAIL with any severity.
    expected_verdict = question_record.get("expected_verdict")
    actual_verdict = response.verification.verdict
    actual_severity = response.verification.severity
    if expected_verdict == "PASS":
        checks["verdict"] = actual_verdict == "PASS" or (
            actual_verdict == "FAIL" and actual_severity in {"none", "minor"}
        )
    elif expected_verdict == "FAIL":
        checks["verdict"] = actual_verdict == "FAIL"
    elif expected_verdict:
        checks["verdict"] = actual_verdict == expected_verdict

    # --- confidence check ---
    min_confidence = question_record.get("min_confidence", 0.0)
    actual_confidence = response.metadata.get("confidence", 0.0)
    checks["min_confidence"] = actual_confidence >= min_confidence

    # --- must cite any ---
    must_cite_any = question_record.get("must_cite_any", [])
    if must_cite_any:
        checks["must_cite_any"] = any(src in source_names for src in must_cite_any)
    else:
        checks["must_cite_any"] = True  # no requirement

    # --- must mention any (case-insensitive substring) ---
    must_mention_any = question_record.get("must_mention_any", [])
    if must_mention_any:
        checks["must_mention_any"] = any(
            kw.lower() in answer_lower for kw in must_mention_any
        )
    else:
        checks["must_mention_any"] = True

    # --- must not contain ---
    must_not_contain = question_record.get("must_not_contain", [])
    if must_not_contain:
        checks["must_not_contain"] = not any(
            bad.lower() in answer_lower for bad in must_not_contain
        )
    else:
        checks["must_not_contain"] = True

    passed = all(checks.values())

    return {
        "passed": passed,
        "checks": checks,
        "actual": {
            "verdict": actual_verdict,
            "severity": response.verification.severity,
            "confidence": round(actual_confidence, 3),
            "is_fallback": response.metadata.get("is_fallback", False),
            "retrieval_method": response.metadata.get("retrieval_method"),
            "latency_ms": response.metadata.get("latency_ms"),
            "sources_cited": sorted(source_names),
            "answer_preview": (response.answer or "")[:200],
        },
    }


def run_eval(
    questions: list[dict[str, Any]],
    quiet: bool = False,
) -> list[dict[str, Any]]:
    """Run the golden set and return per-question results."""
    results = []
    total = len(questions)

    for i, q in enumerate(questions, start=1):
        qid = q["id"]
        category = q["category"]
        question = q["question"]

        if not quiet:
            print(f"\n[{i}/{total}] {qid} ({category})")
            print(f"  Q: {question}")

        start = time.time()
        try:
            response = query(question)
            grade = grade_response(q, response)
            elapsed = int((time.time() - start) * 1000)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            grade = {
                "passed": False,
                "checks": {"exception": False},
                "actual": {"error": str(e)},
            }

        result = {
            "id": qid,
            "category": category,
            "question": question,
            "wall_ms": elapsed,
            **grade,
        }
        results.append(result)

        if not quiet:
            status = "PASS" if grade["passed"] else "FAIL"
            marker = "✓" if grade["passed"] else "✗"
            print(f"  {marker} {status} ({elapsed}ms)")
            if not grade["passed"]:
                failed_checks = [
                    k for k, v in grade["checks"].items() if not v
                ]
                print(f"    Failed checks: {', '.join(failed_checks)}")
                actual = grade["actual"]
                if "verdict" in actual:
                    print(
                        f"    Got verdict={actual.get('verdict')}, "
                        f"confidence={actual.get('confidence')}, "
                        f"sources={len(actual.get('sources_cited', []))}"
                    )

    return results


def print_summary(results: list[dict[str, Any]]) -> None:
    """Print a per-category and overall pass-rate summary."""
    categories: dict[str, dict[str, int]] = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1

    total_passed = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_latency = (
        sum(r.get("wall_ms", 0) for r in results) // total if total else 0
    )

    print("\n" + "=" * 60)
    print("EVAL SUMMARY")
    print("=" * 60)
    print(f"{'Category':<20} {'Passed':>10} {'Total':>10} {'Rate':>10}")
    print("-" * 60)
    for cat in sorted(categories):
        stats = categories[cat]
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] else 0
        print(
            f"{cat:<20} {stats['passed']:>10} {stats['total']:>10} "
            f"{rate:>9.1f}%"
        )
    print("-" * 60)
    overall_rate = total_passed / total * 100 if total else 0
    print(
        f"{'OVERALL':<20} {total_passed:>10} {total:>10} {overall_rate:>9.1f}%"
    )
    print(f"{'Avg latency':<20} {avg_latency:>10} ms")
    print("=" * 60)


def save_results(
    results: list[dict[str, Any]], path: Path | None = None
) -> Path:
    """Write detailed results to disk."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if path is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = RESULTS_DIR / f"eval-{timestamp}.json"

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    payload = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": round(passed / total, 3) if total else 0,
        },
        "results": results,
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the golden Q/A eval set against the RAG pipeline."
    )
    parser.add_argument(
        "--filter",
        help="Only run questions in this category (e.g. 'factual').",
    )
    parser.add_argument(
        "--id", help="Only run the question with this specific id."
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Only print summary, not per-question."
    )
    parser.add_argument(
        "--save", help="Custom path to write detailed results JSON."
    )
    args = parser.parse_args()

    questions = load_golden_set()

    if args.filter:
        questions = [q for q in questions if q["category"] == args.filter]
    if args.id:
        questions = [q for q in questions if q["id"] == args.id]

    if not questions:
        print("No questions matched the filter.")
        return 1

    print(f"Running {len(questions)} question(s)...")
    results = run_eval(questions, quiet=args.quiet)

    print_summary(results)

    save_path = Path(args.save) if args.save else None
    saved_to = save_results(results, save_path)
    print(f"\nDetailed results: {saved_to}")

    # Exit code: 0 if all passed, 1 otherwise (for CI)
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

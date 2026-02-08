"""
Genie Space Optimization Script

Complete optimization loop: load benchmarks → query Genie → evaluate → report.

Usage:
    # From Databricks notebook
    %run ./genie_optimizer

    # Or standalone with SDK configured
    python genie_optimizer.py --space-id <ID> --benchmarks golden-queries.yaml

Requirements:
    - databricks-sdk
    - pyyaml
"""

import time
import hashlib
import json
import yaml
import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
except ImportError:
    print("WARNING: databricks-sdk not installed. Install with: pip install databricks-sdk")
    w = None


# =============================================================================
# Core Query Functions
# =============================================================================

def run_genie_query(space_id: str, question: str, max_wait: int = 120) -> dict:
    """Execute a query against Genie and return SQL + status.

    Args:
        space_id: Genie Space ID
        question: Natural language question
        max_wait: Maximum wait time in seconds

    Returns:
        dict with keys: status, sql, error (optional), conversation_id, message_id
    """
    if w is None:
        return {"status": "ERROR", "sql": None, "error": "SDK not initialized"}

    try:
        resp = w.genie.start_conversation(space_id=space_id, content=question)
        conversation_id = resp.conversation_id
        message_id = resp.message_id

        poll_interval = 3
        start = time.time()
        msg = None

        while time.time() - start < max_wait:
            time.sleep(poll_interval)
            msg = w.genie.get_message(
                space_id=space_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )
            status = str(msg.status) if hasattr(msg, "status") else "UNKNOWN"

            if any(s in status for s in ["COMPLETED", "FAILED", "CANCELLED"]):
                break
            if poll_interval < 10:
                poll_interval += 1

        # Extract SQL from response
        sql = None
        if msg and hasattr(msg, "attachments") and msg.attachments:
            for att in msg.attachments:
                if hasattr(att, "query") and att.query:
                    sql = (
                        att.query.query
                        if hasattr(att.query, "query")
                        else str(att.query)
                    )

        return {
            "status": status,
            "sql": sql,
            "conversation_id": conversation_id,
            "message_id": message_id,
        }
    except Exception as e:
        return {"status": "ERROR", "sql": None, "error": str(e)}


# =============================================================================
# Evaluation Functions
# =============================================================================

def detect_asset_type(sql: str) -> str:
    """Detect which asset type a SQL query uses."""
    sql_lower = sql.lower()
    if "mv_" in sql_lower or "measure(" in sql_lower:
        return "MV"
    elif "get_" in sql_lower:
        return "TVF"
    else:
        return "TABLE"


def evaluate_accuracy(result: dict, expected: dict) -> dict:
    """Evaluate if Genie returned correct SQL for a benchmark question.

    Args:
        result: Output from run_genie_query
        expected: Benchmark question dict with expected_sql, expected_asset

    Returns:
        Evaluation dict with pass/fail details
    """
    generated_sql = (result.get("sql") or "").strip()
    expected_asset = expected.get("expected_asset", "").upper()

    sql_generated = result.get("status", "").upper() == "COMPLETED" and bool(
        generated_sql
    )
    actual_asset = detect_asset_type(generated_sql) if generated_sql else "NONE"

    return {
        "question_id": expected.get("id", "unknown"),
        "question": expected["question"],
        "sql_generated": sql_generated,
        "correct_asset": actual_asset == expected_asset,
        "actual_asset": actual_asset,
        "expected_asset": expected_asset,
        "generated_sql": generated_sql[:200] if generated_sql else None,
        "status": result.get("status", "UNKNOWN"),
    }


def test_repeatability(
    space_id: str, question: str, iterations: int = 3
) -> dict:
    """Test if a question produces consistent SQL across multiple runs.

    Args:
        space_id: Genie Space ID
        question: Question to test
        iterations: Number of times to run (default 3)

    Returns:
        dict with repeatability_pct, unique_variants, dominant_asset, hashes
    """
    hashes = []
    assets = []

    for i in range(iterations):
        print(f"   Iteration {i + 1}/{iterations}...", end=" ", flush=True)

        result = run_genie_query(space_id, question)
        sql = result.get("sql", "")

        if sql:
            asset = detect_asset_type(sql)
            sql_hash = hashlib.md5(sql.lower().encode()).hexdigest()[:8]
            hashes.append(sql_hash)
            assets.append(asset)
            print(f"OK ({sql_hash}, {asset})")
        else:
            hashes.append("NONE")
            assets.append("NONE")
            print("NO SQL")

        time.sleep(12)  # Rate limiting

    hash_counts = Counter(hashes)
    most_common_count = hash_counts.most_common(1)[0][1]
    repeatability = (most_common_count / len(hashes)) * 100

    return {
        "question": question,
        "repeatability_pct": repeatability,
        "unique_variants": len(set(hashes)),
        "dominant_asset": Counter(assets).most_common(1)[0][0],
        "hashes": hashes,
    }


# =============================================================================
# Optimization Session
# =============================================================================

def run_optimization_session(
    space_id: str,
    benchmarks: list,
    run_repeatability: bool = True,
    repeatability_iterations: int = 3,
    repeatability_sample: int = 5,
) -> dict:
    """Run a complete optimization assessment session.

    Args:
        space_id: Genie Space ID
        benchmarks: List of benchmark question dicts
        run_repeatability: Whether to run repeatability tests
        repeatability_iterations: Iterations per repeatability test
        repeatability_sample: Number of questions to test for repeatability

    Returns:
        Session report dict with accuracy, repeatability, and failures
    """
    print("=" * 60)
    print(f"Genie Optimization Session")
    print(f"Space ID: {space_id}")
    print(f"Benchmarks: {len(benchmarks)} questions")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Phase 1: Accuracy Testing
    print("\n--- Phase 1: Accuracy Testing ---\n")
    accuracy_results = []
    for q in benchmarks:
        print(f"  [{q.get('id', '?')}] {q['question'][:55]}...", end=" ")
        result = run_genie_query(space_id, q["question"])
        evaluation = evaluate_accuracy(result, q)
        accuracy_results.append(evaluation)

        status = "PASS" if evaluation["correct_asset"] else "FAIL"
        print(f"{status} (expected={q['expected_asset']}, got={evaluation['actual_asset']})")
        time.sleep(12)

    # Calculate accuracy metrics
    total = len(accuracy_results)
    sql_generated = sum(1 for r in accuracy_results if r["sql_generated"])
    correct_asset = sum(1 for r in accuracy_results if r["correct_asset"])

    accuracy_report = {
        "total_questions": total,
        "sql_generation_rate": (sql_generated / total * 100) if total else 0,
        "asset_accuracy_rate": (correct_asset / total * 100) if total else 0,
        "failures": [r for r in accuracy_results if not r["correct_asset"]],
    }

    print(f"\n  SQL Generation: {sql_generated}/{total} ({accuracy_report['sql_generation_rate']:.0f}%)")
    print(f"  Asset Accuracy: {correct_asset}/{total} ({accuracy_report['asset_accuracy_rate']:.0f}%)")

    # Phase 2: Repeatability Testing
    repeatability_report = None
    if run_repeatability:
        print(f"\n--- Phase 2: Repeatability Testing ({repeatability_sample} questions) ---\n")
        repeat_results = []
        sample = benchmarks[:repeatability_sample]

        for q in sample:
            print(f"  [{q.get('id', '?')}] {q['question'][:50]}...")
            repeat = test_repeatability(
                space_id, q["question"], iterations=repeatability_iterations
            )
            repeat_results.append(repeat)
            print(f"  Score: {repeat['repeatability_pct']:.0f}% "
                  f"({repeat['unique_variants']} variant{'s' if repeat['unique_variants'] > 1 else ''})")

        avg_repeat = sum(r["repeatability_pct"] for r in repeat_results) / len(repeat_results)
        repeatability_report = {
            "average_repeatability": avg_repeat,
            "results": repeat_results,
            "low_repeatability": [r for r in repeat_results if r["repeatability_pct"] < 70],
        }

        print(f"\n  Average Repeatability: {avg_repeat:.0f}%")
        print(f"  Low Repeatability (<70%): {len(repeatability_report['low_repeatability'])} questions")

    # Summary
    print("\n" + "=" * 60)
    print("SESSION SUMMARY")
    print("=" * 60)
    print(f"  Accuracy:      {accuracy_report['asset_accuracy_rate']:.0f}%")
    if repeatability_report:
        print(f"  Repeatability: {repeatability_report['average_repeatability']:.0f}%")
    print(f"  Failures:      {len(accuracy_report['failures'])}")
    print("=" * 60)

    return {
        "space_id": space_id,
        "timestamp": datetime.now().isoformat(),
        "accuracy": accuracy_report,
        "repeatability": repeatability_report,
    }


# =============================================================================
# Report Generation
# =============================================================================

def generate_report(session: dict, domain: str, output_dir: str = "docs/genie_space_optimizer") -> str:
    """Generate a markdown optimization report.

    Args:
        session: Output from run_optimization_session
        domain: Domain name (e.g., "cost_intelligence")
        output_dir: Output directory for report

    Returns:
        Path to generated report
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{output_dir}/{domain}_optimization_{date_str}.md"

    accuracy = session["accuracy"]
    repeatability = session.get("repeatability")

    report = f"""# {domain.replace('_', ' ').title()} Genie Space Optimization Report

**Date:** {date_str}
**Space ID:** `{session['space_id']}`
**Domain:** {domain}

## Executive Summary

| Metric | Score |
|--------|-------|
| **SQL Generation Rate** | {accuracy['sql_generation_rate']:.0f}% |
| **Asset Accuracy** | {accuracy['asset_accuracy_rate']:.0f}% |
"""

    if repeatability:
        report += f"| **Avg Repeatability** | {repeatability['average_repeatability']:.0f}% |\n"

    report += f"""
## Accuracy Results

Total questions tested: {accuracy['total_questions']}

### Failures ({len(accuracy['failures'])} questions)

| Question ID | Question | Expected | Actual |
|-------------|----------|----------|--------|
"""

    for f in accuracy["failures"]:
        q_short = f["question"][:40] + "..." if len(f["question"]) > 40 else f["question"]
        report += f"| {f['question_id']} | {q_short} | {f['expected_asset']} | {f['actual_asset']} |\n"

    if repeatability:
        report += f"""
## Repeatability Results

Average: {repeatability['average_repeatability']:.0f}%

| Question | Score | Variants |
|----------|-------|----------|
"""
        for r in repeatability["results"]:
            q_short = r["question"][:40] + "..." if len(r["question"]) > 40 else r["question"]
            report += f"| {q_short} | {r['repeatability_pct']:.0f}% | {r['unique_variants']} |\n"

    report += """
## Next Steps

- [ ] Apply control lever fixes for failing questions
- [ ] Re-test after optimizations
- [ ] Update dual persistence (API + repository)
- [ ] Generate follow-up report
"""

    with open(filename, "w") as f:
        f.write(report)

    print(f"\nReport saved to: {filename}")
    return filename


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Genie Space Optimization")
    parser.add_argument("--space-id", required=True, help="Genie Space ID")
    parser.add_argument("--benchmarks", required=True, help="Path to golden queries YAML")
    parser.add_argument("--domain", default="unknown", help="Domain name")
    parser.add_argument("--no-repeatability", action="store_true", help="Skip repeatability tests")
    parser.add_argument("--iterations", type=int, default=3, help="Repeatability iterations")
    parser.add_argument("--sample", type=int, default=5, help="Repeatability sample size")
    parser.add_argument("--output-dir", default="docs/genie_space_optimizer", help="Report output dir")

    args = parser.parse_args()

    # Load benchmarks
    with open(args.benchmarks) as f:
        all_benchmarks = yaml.safe_load(f)

    # Extract domain-specific benchmarks
    if args.domain in all_benchmarks:
        benchmarks = all_benchmarks[args.domain]
    elif "benchmarks" in all_benchmarks:
        benchmarks = all_benchmarks["benchmarks"]
    else:
        benchmarks = all_benchmarks if isinstance(all_benchmarks, list) else []

    if not benchmarks:
        print(f"ERROR: No benchmarks found for domain '{args.domain}'")
        return

    # Run session
    session = run_optimization_session(
        space_id=args.space_id,
        benchmarks=benchmarks,
        run_repeatability=not args.no_repeatability,
        repeatability_iterations=args.iterations,
        repeatability_sample=args.sample,
    )

    # Generate report
    generate_report(session, args.domain, args.output_dir)


if __name__ == "__main__":
    main()

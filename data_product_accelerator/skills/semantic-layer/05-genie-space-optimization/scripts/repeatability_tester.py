"""
Genie Space Repeatability Tester

Standalone script for testing Genie Space response consistency.
Runs each question multiple times and measures SQL consistency.

Usage:
    python repeatability_tester.py --space-id <ID> --benchmarks golden-queries.yaml
    python repeatability_tester.py --space-id <ID> --question "What is total cost?"
    python repeatability_tester.py --space-id <ID> --benchmarks queries.yaml --iterations 5

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

try:
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
except ImportError:
    print("ERROR: databricks-sdk not installed. Install with: pip install databricks-sdk")
    exit(1)


# Rate limit: 5 POST requests/minute/workspace → minimum 12s between queries
RATE_LIMIT_SECONDS = 12


def run_genie_query(space_id: str, question: str, max_wait: int = 120) -> dict:
    """Execute a query against Genie and return SQL + status."""
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

        sql = None
        if msg and hasattr(msg, "attachments") and msg.attachments:
            for att in msg.attachments:
                if hasattr(att, "query") and att.query:
                    sql = (
                        att.query.query
                        if hasattr(att.query, "query")
                        else str(att.query)
                    )
        return {"status": status, "sql": sql}
    except Exception as e:
        return {"status": "ERROR", "sql": None, "error": str(e)}


def detect_asset_type(sql: str) -> str:
    """Detect which asset type a SQL query uses."""
    sql_lower = sql.lower()
    if "mv_" in sql_lower or "measure(" in sql_lower:
        return "MV"
    elif "get_" in sql_lower:
        return "TVF"
    return "TABLE"


def test_repeatability(
    space_id: str, question: str, iterations: int = 3
) -> dict:
    """Test SQL consistency across multiple runs."""
    hashes = []
    sqls = []
    assets = []

    for i in range(iterations):
        print(f"   Iteration {i + 1}/{iterations}...", end=" ", flush=True)

        result = run_genie_query(space_id, question)
        sql = result.get("sql", "")

        if sql:
            asset = detect_asset_type(sql)
            sql_hash = hashlib.md5(sql.lower().encode()).hexdigest()[:8]
            hashes.append(sql_hash)
            sqls.append(sql)
            assets.append(asset)
            print(f"OK ({sql_hash}, {asset})")
        else:
            hashes.append("NONE")
            sqls.append("")
            assets.append("NONE")
            print(f"NO SQL (status={result.get('status', '?')})")

        time.sleep(RATE_LIMIT_SECONDS)

    hash_counts = Counter(hashes)
    most_common_count = hash_counts.most_common(1)[0][1]
    repeatability = (most_common_count / len(hashes)) * 100

    # Classify
    if repeatability == 100:
        classification = "IDENTICAL"
    elif repeatability >= 70:
        classification = "MINOR_VARIANCE"
    elif repeatability >= 50:
        classification = "SIGNIFICANT_VARIANCE"
    else:
        classification = "CRITICAL_VARIANCE"

    return {
        "question": question,
        "repeatability_pct": repeatability,
        "classification": classification,
        "unique_variants": len(set(hashes)),
        "dominant_asset": Counter(assets).most_common(1)[0][0],
        "hashes": hashes,
        "sqls": sqls,
    }


def main():
    parser = argparse.ArgumentParser(description="Genie Repeatability Tester")
    parser.add_argument("--space-id", required=True, help="Genie Space ID")
    parser.add_argument("--question", help="Single question to test")
    parser.add_argument("--benchmarks", help="Path to benchmark YAML file")
    parser.add_argument("--domain", default=None, help="Domain key in YAML")
    parser.add_argument("--iterations", type=int, default=3, help="Runs per question")
    parser.add_argument("--sample", type=int, default=None, help="Max questions to test")
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    # Collect questions
    questions = []
    if args.question:
        questions = [{"question": args.question, "id": "manual_001"}]
    elif args.benchmarks:
        with open(args.benchmarks) as f:
            data = yaml.safe_load(f)
        if args.domain and args.domain in data:
            questions = data[args.domain]
        elif "benchmarks" in data:
            questions = data["benchmarks"]
        elif isinstance(data, list):
            questions = data
        else:
            # Try first key that has a list value
            for key, val in data.items():
                if isinstance(val, list):
                    questions = val
                    break
    else:
        parser.error("Provide either --question or --benchmarks")

    if args.sample:
        questions = questions[: args.sample]

    if not questions:
        print("ERROR: No questions to test")
        return

    print("=" * 60)
    print(f"Genie Repeatability Test")
    print(f"Space ID:   {args.space_id}")
    print(f"Questions:  {len(questions)}")
    print(f"Iterations: {args.iterations}")
    print(f"Started:    {datetime.now().isoformat()}")
    est_minutes = len(questions) * args.iterations * RATE_LIMIT_SECONDS / 60
    print(f"Est. time:  ~{est_minutes:.0f} minutes")
    print("=" * 60)

    results = []
    for i, q in enumerate(questions):
        q_text = q["question"] if isinstance(q, dict) else q
        q_id = q.get("id", f"q_{i+1:03d}") if isinstance(q, dict) else f"q_{i+1:03d}"

        print(f"\n[{q_id}] {q_text[:55]}...")
        result = test_repeatability(args.space_id, q_text, args.iterations)
        result["id"] = q_id
        results.append(result)

        icon = {
            "IDENTICAL": "OK",
            "MINOR_VARIANCE": "WARN",
            "SIGNIFICANT_VARIANCE": "WARN",
            "CRITICAL_VARIANCE": "FAIL",
        }.get(result["classification"], "?")

        print(
            f"   Result: {icon} {result['repeatability_pct']:.0f}% "
            f"({result['classification']}, {result['unique_variants']} variants, "
            f"dominant={result['dominant_asset']})"
        )

    # Summary
    avg_repeat = sum(r["repeatability_pct"] for r in results) / len(results)
    critical = [r for r in results if r["classification"] == "CRITICAL_VARIANCE"]
    significant = [r for r in results if r["classification"] == "SIGNIFICANT_VARIANCE"]

    print("\n" + "=" * 60)
    print("REPEATABILITY SUMMARY")
    print("=" * 60)
    print(f"  Average:    {avg_repeat:.0f}%")
    print(f"  Identical:  {sum(1 for r in results if r['classification'] == 'IDENTICAL')}")
    print(f"  Minor:      {sum(1 for r in results if r['classification'] == 'MINOR_VARIANCE')}")
    print(f"  Significant: {len(significant)}")
    print(f"  Critical:   {len(critical)}")

    if critical:
        print(f"\n  CRITICAL VARIANCE (needs fixing):")
        for r in critical:
            print(f"    - [{r['id']}] {r['question'][:50]}... ({r['repeatability_pct']:.0f}%)")

    # Save results
    if args.output:
        output_data = {
            "space_id": args.space_id,
            "timestamp": datetime.now().isoformat(),
            "iterations": args.iterations,
            "average_repeatability": avg_repeat,
            "results": [
                {
                    "id": r["id"],
                    "question": r["question"],
                    "repeatability_pct": r["repeatability_pct"],
                    "classification": r["classification"],
                    "unique_variants": r["unique_variants"],
                    "dominant_asset": r["dominant_asset"],
                }
                for r in results
            ],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")

    print("=" * 60)


if __name__ == "__main__":
    main()

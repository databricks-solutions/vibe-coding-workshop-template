#!/usr/bin/env python3
"""Genie Space benchmark regression test template.

Runs a suite of benchmark questions against a deployed Genie Space via the
Conversation API, compares results to expected outcomes, and generates a
pass/fail report.

Usage:
    python genie-space-regression-test.py \
        --space-id <SPACE_ID> \
        --benchmarks-json benchmarks.json \
        [--output results.json] \
        [--fail-threshold 100] \
        [--timeout 60]

benchmarks.json format:
    [
        {
            "question": "What is total revenue for Q1 2026?",
            "expected_sql_contains": ["MEASURE(total_revenue)", "2026-01-01", "2026-03-31"],
            "expected_tables": ["catalog.schema.revenue_metrics"],
            "expected_row_count_range": [1, 100],
            "category": "aggregation"
        },
        ...
    ]

Environment:
    DATABRICKS_HOST           - Workspace URL
    DATABRICKS_TOKEN          - Personal access token or OAuth token
    BENCHMARK_ANCHOR_DATE     - Optional anchor date for temporal benchmarks (default: none)
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests


@dataclass
class BenchmarkResult:
    question: str
    category: str
    status: str  # "pass", "fail", "error", "timeout"
    genie_status: str = ""
    returned_sql: str = ""
    row_count: int = 0
    checks: dict = field(default_factory=dict)
    error: str = ""
    duration_seconds: float = 0.0


def ask_genie(
    host: str, token: str, space_id: str, question: str, timeout: int = 60
) -> dict:
    """Submit a question to Genie and poll until completion or timeout."""
    base_url = f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    start_resp = requests.post(
        f"{base_url}/conversations",
        headers=headers,
        json={"content": question},
    )
    start_resp.raise_for_status()
    data = start_resp.json()

    conversation_id = data.get("conversation_id", "")
    message_id = data.get("message_id", "")

    if not conversation_id or not message_id:
        return {"status": "ERROR", "error": "Missing conversation_id or message_id"}

    poll_url = f"{base_url}/conversations/{conversation_id}/messages/{message_id}"
    deadline = time.time() + timeout

    while time.time() < deadline:
        poll_resp = requests.get(poll_url, headers=headers)
        poll_resp.raise_for_status()
        msg = poll_resp.json()

        status = msg.get("status", "")
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            return msg
        time.sleep(2)

    return {"status": "TIMEOUT", "error": f"Timed out after {timeout}s"}


def extract_sql_from_response(msg: dict) -> str:
    """Extract the generated SQL from a Genie response."""
    for attachment in msg.get("attachments", []):
        query = attachment.get("query", {})
        if query.get("query"):
            return query["query"]
        if attachment.get("text", {}).get("content"):
            content = attachment["text"]["content"]
            sql_match = re.search(r"```sql\n(.*?)\n```", content, re.DOTALL)
            if sql_match:
                return sql_match.group(1)
    return ""


def extract_row_count(msg: dict) -> int:
    """Extract the row count from a Genie response."""
    for attachment in msg.get("attachments", []):
        query = attachment.get("query", {})
        result = query.get("result", {})
        if "row_count" in result:
            return result["row_count"]
        rows = result.get("data_array", [])
        if rows:
            return len(rows)
    return 0


def check_sql_contains(sql: str, expected_fragments: list[str]) -> dict:
    """Verify that the returned SQL contains expected fragments."""
    results = {}
    sql_upper = sql.upper()
    for frag in expected_fragments:
        results[frag] = frag.upper() in sql_upper
    return results


def check_table_references(sql: str, expected_tables: list[str]) -> dict:
    """Verify that the returned SQL references expected tables."""
    results = {}
    sql_lower = sql.lower()
    for table in expected_tables:
        results[table] = table.lower() in sql_lower
    return results


def check_row_count_range(
    actual: int, expected_range: Optional[list[int]]
) -> dict:
    """Verify row count falls within expected range."""
    if not expected_range or len(expected_range) != 2:
        return {"row_count_in_range": True}
    low, high = expected_range
    in_range = low <= actual <= high
    return {
        "row_count_in_range": in_range,
        "actual": actual,
        "expected_range": expected_range,
    }


def run_benchmark(
    host: str,
    token: str,
    space_id: str,
    benchmark: dict,
    timeout: int,
) -> BenchmarkResult:
    """Run a single benchmark question and evaluate the result."""
    question = benchmark["question"]
    category = benchmark.get("category", "unknown")

    start_time = time.time()
    try:
        msg = ask_genie(host, token, space_id, question, timeout=timeout)
    except Exception as e:
        return BenchmarkResult(
            question=question,
            category=category,
            status="error",
            error=str(e),
            duration_seconds=time.time() - start_time,
        )

    duration = time.time() - start_time
    genie_status = msg.get("status", "UNKNOWN")

    if genie_status == "TIMEOUT":
        return BenchmarkResult(
            question=question,
            category=category,
            status="timeout",
            genie_status=genie_status,
            duration_seconds=duration,
        )

    if genie_status != "COMPLETED":
        return BenchmarkResult(
            question=question,
            category=category,
            status="fail",
            genie_status=genie_status,
            error=f"Genie returned status: {genie_status}",
            duration_seconds=duration,
        )

    sql = extract_sql_from_response(msg)
    row_count = extract_row_count(msg)

    checks = {}
    all_pass = True

    if benchmark.get("expected_sql_contains"):
        sql_checks = check_sql_contains(sql, benchmark["expected_sql_contains"])
        checks["sql_contains"] = sql_checks
        if not all(sql_checks.values()):
            all_pass = False

    if benchmark.get("expected_tables"):
        table_checks = check_table_references(sql, benchmark["expected_tables"])
        checks["table_references"] = table_checks
        if not all(table_checks.values()):
            all_pass = False

    if benchmark.get("expected_row_count_range"):
        rc_check = check_row_count_range(row_count, benchmark["expected_row_count_range"])
        checks["row_count"] = rc_check
        if not rc_check.get("row_count_in_range", True):
            all_pass = False

    return BenchmarkResult(
        question=question,
        category=category,
        status="pass" if all_pass else "fail",
        genie_status=genie_status,
        returned_sql=sql,
        row_count=row_count,
        checks=checks,
        duration_seconds=duration,
    )


def generate_report(results: list[BenchmarkResult], space_id: str) -> str:
    """Generate a markdown summary report."""
    total = len(results)
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    errors = sum(1 for r in results if r.status == "error")
    timeouts = sum(1 for r in results if r.status == "timeout")
    pass_rate = (passed / total * 100) if total > 0 else 0

    lines = [
        "# Genie Space Regression Test Report",
        "",
        f"**Space ID:** `{space_id}`",
        f"**Total:** {total} | **Passed:** {passed} | **Failed:** {failed} | **Errors:** {errors} | **Timeouts:** {timeouts}",
        f"**Pass Rate:** {pass_rate:.1f}%",
        "",
        "---",
        "",
    ]

    by_category: dict[str, list[BenchmarkResult]] = {}
    for r in results:
        by_category.setdefault(r.category, []).append(r)

    for cat, cat_results in sorted(by_category.items()):
        cat_passed = sum(1 for r in cat_results if r.status == "pass")
        lines.append(f"### {cat.title()} ({cat_passed}/{len(cat_results)})")
        for r in cat_results:
            icon = {"pass": "✅", "fail": "❌", "error": "💥", "timeout": "⏰"}.get(r.status, "❓")
            lines.append(f"- {icon} {r.question} ({r.duration_seconds:.1f}s)")
            if r.status == "fail" and r.checks:
                for check_name, check_detail in r.checks.items():
                    if isinstance(check_detail, dict):
                        failures = [k for k, v in check_detail.items() if v is False]
                        if failures:
                            lines.append(f"  - {check_name}: missing {failures}")
            if r.error:
                lines.append(f"  - Error: {r.error}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Run Genie Space benchmark regression tests."
    )
    parser.add_argument("--space-id", required=True, help="Genie Space ID")
    parser.add_argument(
        "--benchmarks-json", required=True, help="Path to benchmarks JSON file"
    )
    parser.add_argument(
        "--output", default=None, help="Output file for results JSON"
    )
    parser.add_argument(
        "--fail-threshold",
        type=float,
        default=100.0,
        help="Minimum pass rate %% to succeed (default: 100)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Per-question timeout in seconds (default: 60)",
    )
    args = parser.parse_args()

    host = os.environ.get("DATABRICKS_HOST", "")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not host or not token:
        print(
            "❌ Set DATABRICKS_HOST and DATABRICKS_TOKEN environment variables",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(args.benchmarks_json, "r") as f:
        benchmarks = json.load(f)

    print(f"🧪 Running {len(benchmarks)} benchmark questions against space {args.space_id}...")
    print()

    results: list[BenchmarkResult] = []
    for i, bm in enumerate(benchmarks, 1):
        print(f"  [{i}/{len(benchmarks)}] {bm['question'][:80]}...", end=" ", flush=True)
        result = run_benchmark(host, token, args.space_id, bm, args.timeout)
        results.append(result)
        icon = {"pass": "✅", "fail": "❌", "error": "💥", "timeout": "⏰"}.get(result.status, "❓")
        print(f"{icon} ({result.duration_seconds:.1f}s)")

    report = generate_report(results, args.space_id)
    print()
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        print(f"📄 Results written to {args.output}")

    total = len(results)
    passed = sum(1 for r in results if r.status == "pass")
    pass_rate = (passed / total * 100) if total > 0 else 0

    if pass_rate < args.fail_threshold:
        print(f"❌ Pass rate {pass_rate:.1f}% is below threshold {args.fail_threshold}%")
        sys.exit(1)
    else:
        print(f"✅ Pass rate {pass_rate:.1f}% meets threshold {args.fail_threshold}%")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Audit a Genie Space for configuration drift.

Compares a live Genie Space (via REST API) against a version-controlled
source JSON file. Produces a diff report flagging changes to trusted assets,
instructions, benchmarks, SQL expressions, and warehouse assignment.

Usage:
    python audit_genie_space.py \
        --space-id <SPACE_ID> \
        --source-json src/project_semantic/genie_configs/space.json \
        [--output audit_report.md] \
        [--fail-on-drift]

Environment:
    DATABRICKS_HOST  - Workspace URL (e.g., https://workspace.cloud.databricks.com)
    DATABRICKS_TOKEN - Personal access token or OAuth token
"""

import argparse
import json
import os
import sys
from typing import Any

import requests


def get_live_space(host: str, token: str, space_id: str) -> dict:
    """Fetch the current Genie Space configuration from the REST API."""
    url = f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching space {space_id}: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def load_source_json(path: str) -> dict:
    """Load the version-controlled source JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Source file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def parse_serialized_space(space: dict) -> dict:
    """Parse serialized_space string into a dict if needed."""
    raw = space.get("serialized_space", {})
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def extract_asset_names(serialized: dict) -> set:
    """Extract trusted asset identifiers from data_sources."""
    names = set()
    for ds in serialized.get("data_sources", []):
        for table in ds.get("tables", []):
            names.add(table.get("identifier", table.get("name", "")))
        for mv in ds.get("metric_views", []):
            names.add(mv.get("identifier", mv.get("name", "")))
    return names


def extract_instruction_text(serialized: dict) -> str:
    """Extract the text instructions block."""
    instructions = serialized.get("instructions", {})
    return instructions.get("text", "")


def extract_sql_snippets(serialized: dict) -> dict:
    """Extract sql_snippets (measures, filters, expressions)."""
    instructions = serialized.get("instructions", {})
    return instructions.get("sql_snippets", {})


def extract_benchmarks(serialized: dict) -> list:
    """Extract benchmark questions."""
    return serialized.get("benchmarks", [])


def extract_sample_questions(serialized: dict) -> list:
    """Extract sample questions from config."""
    config = serialized.get("config", {})
    return config.get("sample_questions", [])


SEVERITY = {
    "trusted_assets": "🔴 HIGH",
    "instructions": "🔴 HIGH",
    "sql_snippets": "🔴 HIGH",
    "warehouse_id": "🔴 HIGH",
    "benchmarks": "🟡 MEDIUM",
    "sample_questions": "🟢 LOW",
}


def diff_sets(label: str, live_set: set, source_set: set) -> list[str]:
    """Diff two sets and return human-readable lines."""
    lines = []
    added = live_set - source_set
    removed = source_set - live_set
    if added:
        lines.append(f"  **Added** in live (not in source): {sorted(added)}")
    if removed:
        lines.append(f"  **Removed** from live (present in source): {sorted(removed)}")
    if not added and not removed:
        lines.append(f"  ✅ No drift")
    return lines


def audit(live_space: dict, source_space: dict) -> tuple[list[str], bool]:
    """Compare live vs source and produce a report.

    Returns (report_lines, has_drift).
    """
    report: list[str] = []
    has_drift = False

    live_ser = parse_serialized_space(live_space)
    src_ser = parse_serialized_space(source_space)

    # 1. Trusted assets
    report.append(f"### Trusted Assets ({SEVERITY['trusted_assets']})")
    live_assets = extract_asset_names(live_ser)
    src_assets = extract_asset_names(src_ser)
    asset_lines = diff_sets("assets", live_assets, src_assets)
    report.extend(asset_lines)
    if live_assets != src_assets:
        has_drift = True
    report.append("")

    # 2. Instructions text
    report.append(f"### Instructions ({SEVERITY['instructions']})")
    live_instr = extract_instruction_text(live_ser)
    src_instr = extract_instruction_text(src_ser)
    live_line_count = len(live_instr.strip().splitlines()) if live_instr.strip() else 0
    src_line_count = len(src_instr.strip().splitlines()) if src_instr.strip() else 0
    if live_instr.strip() != src_instr.strip():
        has_drift = True
        report.append(f"  ⚠️ Instructions differ (live: {live_line_count} lines, source: {src_line_count} lines)")
        if live_line_count > 20:
            report.append(f"  🔴 CRITICAL: Live instructions exceed 20-line limit ({live_line_count} lines)")
    else:
        report.append("  ✅ No drift")
    report.append("")

    # 3. SQL Expressions (sql_snippets)
    report.append(f"### SQL Expressions ({SEVERITY['sql_snippets']})")
    live_snippets = extract_sql_snippets(live_ser)
    src_snippets = extract_sql_snippets(src_ser)
    if live_snippets != src_snippets:
        has_drift = True
        for key in ("measures", "filters", "expressions"):
            live_names = {s.get("display_name", "") for s in live_snippets.get(key, [])}
            src_names = {s.get("display_name", "") for s in src_snippets.get(key, [])}
            if live_names != src_names:
                report.append(f"  {key}: {diff_sets(key, live_names, src_names)[0]}")
    else:
        report.append("  ✅ No drift")
    report.append("")

    # 4. Benchmarks
    report.append(f"### Benchmark Questions ({SEVERITY['benchmarks']})")
    live_bm = extract_benchmarks(live_ser)
    src_bm = extract_benchmarks(src_ser)
    live_bm_qs = {b.get("question", "") for b in live_bm}
    src_bm_qs = {b.get("question", "") for b in src_bm}
    bm_lines = diff_sets("benchmarks", live_bm_qs, src_bm_qs)
    report.extend(bm_lines)
    if live_bm_qs != src_bm_qs:
        has_drift = True
    report.append(f"  Count: live={len(live_bm)}, source={len(src_bm)}")
    report.append("")

    # 5. Sample questions
    report.append(f"### Sample Questions ({SEVERITY['sample_questions']})")
    live_sq = set(extract_sample_questions(live_ser))
    src_sq = set(extract_sample_questions(src_ser))
    sq_lines = diff_sets("sample_questions", live_sq, src_sq)
    report.extend(sq_lines)
    if live_sq != src_sq:
        has_drift = True
    report.append("")

    # 6. Warehouse ID
    report.append(f"### Warehouse Assignment ({SEVERITY['warehouse_id']})")
    live_wh = live_space.get("warehouse_id", "")
    src_wh = source_space.get("warehouse_id", "")
    if live_wh != src_wh:
        has_drift = True
        report.append(f"  ⚠️ Warehouse changed: source=`{src_wh}` → live=`{live_wh}`")
    else:
        report.append("  ✅ No drift")
    report.append("")

    return report, has_drift


def main():
    parser = argparse.ArgumentParser(
        description="Audit a Genie Space for configuration drift."
    )
    parser.add_argument("--space-id", required=True, help="Genie Space ID to audit")
    parser.add_argument(
        "--source-json",
        required=True,
        help="Path to version-controlled source JSON file",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file for the audit report (default: stdout)",
    )
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit with code 1 if any drift is detected (for CI/CD gates)",
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

    print(f"🔍 Auditing Genie Space {args.space_id}...")
    live_space = get_live_space(host, token, args.space_id)
    source_space = load_source_json(args.source_json)

    report_lines, has_drift = audit(live_space, source_space)

    header = [
        f"# Genie Space Configuration Audit",
        f"",
        f"**Space ID:** `{args.space_id}`",
        f"**Source:** `{args.source_json}`",
        f"**Status:** {'🔴 DRIFT DETECTED' if has_drift else '✅ NO DRIFT'}",
        f"",
        "---",
        "",
    ]

    full_report = "\n".join(header + report_lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(full_report)
        print(f"📄 Report written to {args.output}")
    else:
        print(full_report)

    if has_drift:
        print("⚠️ Configuration drift detected.")
        if args.fail_on_drift:
            sys.exit(1)
    else:
        print("✅ No configuration drift. Space matches source.")


if __name__ == "__main__":
    main()

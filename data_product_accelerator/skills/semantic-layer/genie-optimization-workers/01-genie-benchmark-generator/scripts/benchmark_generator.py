#!/usr/bin/env python3
"""Genie Benchmark Generator — standalone CLI for benchmark creation and validation.

Creates, validates, and syncs benchmark questions for Genie Space evaluation.
Supports three intake paths: full user input, partial + augmentation, or
fully synthetic generation from Genie Space trusted assets.

Usage:
    python benchmark_generator.py --space-id <ID> --domain cost --uc-schema catalog.schema
    python benchmark_generator.py --space-id <ID> --domain cost --validate-only
    python benchmark_generator.py --space-id <ID> --domain cost --benchmarks golden-queries.yaml

Dependencies: databricks-sdk, mlflow[databricks]>=3.4.0, pyyaml
"""

import argparse
import hashlib
import json
import yaml
import time
from datetime import datetime
from pathlib import Path

try:
    from databricks.sdk import WorkspaceClient
except ImportError:
    WorkspaceClient = None

try:
    import mlflow
except ImportError:
    mlflow = None


import re as _re
import random as _random


def assign_splits(benchmarks: list, ratios=(0.6, 0.2, 0.2), seed=42) -> list:
    """Tag each benchmark with split: train|val|held_out.

    Held-out split is never used during optimization -- only for
    post-deploy overfitting checks (P12).
    """
    _random.seed(seed)
    indices = list(range(len(benchmarks)))
    _random.shuffle(indices)

    n = len(benchmarks)
    train_end = int(n * ratios[0])
    val_end = train_end + int(n * ratios[1])

    for i in indices[:train_end]:
        benchmarks[i]["split"] = "train"
    for i in indices[train_end:val_end]:
        benchmarks[i]["split"] = "val"
    for i in indices[val_end:]:
        benchmarks[i]["split"] = "held_out"

    counts = {"train": train_end, "val": val_end - train_end, "held_out": n - val_end}
    print(f"  Splits assigned: {counts}")
    return benchmarks


def parse_sql_dependencies(sql: str) -> dict:
    """Extract required_tables, required_columns, required_joins from GT SQL.

    Uses regex-based parsing on FROM, JOIN, WHERE, SELECT clauses.
    This is a best-effort heuristic for Databricks SQL patterns.
    """
    if not sql:
        return {"required_tables": [], "required_columns": [], "required_joins": []}

    clean = sql.replace("${catalog}.", "").replace("${gold_schema}.", "")

    tables = set()
    for match in _re.finditer(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_.]+)', clean, _re.IGNORECASE):
        table = match.group(1).split(".")[-1]
        tables.add(table)

    columns = set()
    for match in _re.finditer(r'(?:SELECT|WHERE|ON|GROUP\s+BY|ORDER\s+BY)\s+(.+?)(?:FROM|WHERE|GROUP|ORDER|LIMIT|UNION|$)',
                               clean, _re.IGNORECASE | _re.DOTALL):
        clause = match.group(1)
        for col_match in _re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:[,\s=<>!]|$)', clause):
            col = col_match.group(1).lower()
            skip = {"select", "from", "where", "and", "or", "as", "on", "join", "inner",
                     "left", "right", "full", "outer", "cross", "group", "by", "order",
                     "asc", "desc", "limit", "distinct", "all", "union", "null", "not",
                     "in", "between", "like", "is", "case", "when", "then", "else", "end",
                     "cast", "string", "int", "date", "current_date", "measure"}
            if col not in skip and len(col) > 1:
                columns.add(col)

    joins = []
    for match in _re.finditer(r'((?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN)\s+(\S+)\s+(?:\w+\s+)?ON\s+(.+?)(?:WHERE|GROUP|ORDER|LIMIT|JOIN|$)',
                               clean, _re.IGNORECASE | _re.DOTALL):
        join_type = match.group(1).strip()
        join_table = match.group(2).split(".")[-1]
        join_cond = match.group(3).strip().rstrip(";").strip()
        joins.append(f"{join_type} {join_table} ON {join_cond[:100]}")

    return {
        "required_tables": sorted(tables),
        "required_columns": sorted(columns)[:20],
        "required_joins": joins,
    }


def validate_ground_truth_sql(sql: str, spark) -> dict:
    """Execute ground truth SQL and return validation result with hash."""
    try:
        df = spark.sql(sql)
        pdf = df.toPandas()
        row_count = len(pdf)
        result_bytes = pdf.to_csv(index=False).encode("utf-8")
        result_hash = hashlib.md5(result_bytes).hexdigest()
        sample_rows = pdf.head(5).to_dict(orient="records")
        result_sample = json.dumps(sample_rows, default=str)
        return {
            "valid": True,
            "result_hash": result_hash,
            "result_sample": result_sample,
            "row_count": row_count,
            "error": None,
        }
    except Exception as e:
        return {
            "valid": False,
            "result_hash": None,
            "result_sample": None,
            "row_count": 0,
            "error": str(e),
        }


def validate_with_retry(sql, spark, llm_regenerate_fn=None, max_attempts=3):
    """Validate GT SQL with optional LLM regeneration on failure."""
    current_sql = sql
    for attempt in range(max_attempts):
        result = validate_ground_truth_sql(current_sql, spark)
        if result["valid"]:
            result["final_sql"] = current_sql
            result["attempts"] = attempt + 1
            return result
        if llm_regenerate_fn and attempt < max_attempts - 1:
            current_sql = llm_regenerate_fn(current_sql, result["error"])
        else:
            break
    result["final_sql"] = current_sql
    result["attempts"] = max_attempts
    return result


def sync_yaml_to_mlflow_dataset(yaml_path, uc_schema, domain):
    """Sync golden-queries.yaml to an MLflow Evaluation Dataset in Unity Catalog."""
    with open(yaml_path) as f:
        all_benchmarks = yaml.safe_load(f)

    questions = all_benchmarks.get(domain, all_benchmarks.get("benchmarks", []))
    records = []
    for q in questions:
        records.append({
            "inputs": {
                "question": q["question"],
                "space_id": q.get("space_id", ""),
                "category": q.get("category", ""),
            },
            "expectations": {
                "expected_response": q.get("expected_sql", ""),
                "expected_facts": q.get("expected_facts", []),
                "guidelines": q.get("guidelines", ""),
                "expected_result_hash": q.get("expected_result_hash", ""),
                "expected_result_sample": q.get("expected_result_sample", ""),
                "expected_row_count": q.get("expected_row_count", 0),
                "required_tables": q.get("required_tables", []),
                "required_columns": q.get("required_columns", []),
                "required_joins": q.get("required_joins", []),
                "required_business_logic": q.get("required_business_logic", []),
                "expected_asset": q.get("expected_asset", ""),
                "category": q.get("category", ""),
            },
        })

    dataset_name = f"{uc_schema}.genie_benchmarks_{domain}"
    mlflow.genai.datasets.create_dataset(uc_table_name=dataset_name, records=records)
    return dataset_name


def load_benchmarks(yaml_path, domain):
    """Load benchmarks from golden-queries.yaml."""
    with open(yaml_path) as f:
        all_benchmarks = yaml.safe_load(f)
    return all_benchmarks.get(domain, all_benchmarks.get("benchmarks", []))


def save_benchmarks(benchmarks, domain, yaml_path):
    """Save benchmarks to golden-queries.yaml."""
    data = {domain: benchmarks}
    with open(yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    print(f"Saved {len(benchmarks)} benchmarks to {yaml_path}")


def validate_benchmarks(benchmarks, spark):
    """Validate all benchmark GT SQL, populate result hashes, and auto-parse SQL dependencies."""
    report = {"valid": 0, "invalid": 0, "details": []}
    for q in benchmarks:
        qid = q.get("id", "unknown")
        sql = q.get("expected_sql", "")
        if not sql:
            report["invalid"] += 1
            report["details"].append({"id": qid, "status": "missing_sql"})
            continue

        if not q.get("required_tables"):
            deps = parse_sql_dependencies(sql)
            q.setdefault("required_tables", deps["required_tables"])
            q.setdefault("required_columns", deps["required_columns"])
            q.setdefault("required_joins", deps["required_joins"])

        result = validate_ground_truth_sql(sql, spark)
        if result["valid"]:
            q["expected_result_hash"] = result["result_hash"]
            q["expected_result_sample"] = result["result_sample"]
            q["expected_row_count"] = result["row_count"]
            try:
                df = spark.sql(sql)
                q["expected_columns"] = df.columns
            except Exception:
                pass
            report["valid"] += 1
            print(f"  [PASS] {qid}: {result['row_count']} rows, hash={result['result_hash'][:8]}")
        else:
            report["invalid"] += 1
            print(f"  [FAIL] {qid}: {result['error'][:100]}")

        report["details"].append({
            "id": qid,
            "status": "valid" if result["valid"] else "invalid",
            "error": result.get("error"),
        })

    print(f"\nValidation: {report['valid']} passed, {report['invalid']} failed")
    return report


def main():
    parser = argparse.ArgumentParser(description="Genie Benchmark Generator")
    parser.add_argument("--space-id", required=True, help="Genie Space ID")
    parser.add_argument("--domain", default="unknown", help="Domain name")
    parser.add_argument("--uc-schema", default=None, help="Unity Catalog schema")
    parser.add_argument("--benchmarks", default=None, help="Path to existing golden-queries.yaml")
    parser.add_argument("--output", default="golden-queries.yaml", help="Output YAML path")
    parser.add_argument("--validate-only", action="store_true", help="Validate GT SQL only")
    parser.add_argument("--sync-mlflow", action="store_true", help="Sync to MLflow after validation")
    parser.add_argument("--assign-splits", action="store_true", help="Assign train/val/held_out splits (60/20/20)")
    parser.add_argument("--split-ratios", default="0.6,0.2,0.2", help="Split ratios (train,val,held_out)")
    args = parser.parse_args()

    print("=" * 60)
    print("Genie Benchmark Generator v2.0")
    print(f"  Space ID: {args.space_id}")
    print(f"  Domain:   {args.domain}")
    print("=" * 60)

    if args.benchmarks:
        benchmarks = load_benchmarks(args.benchmarks, args.domain)
        print(f"\nLoaded {len(benchmarks)} benchmarks from {args.benchmarks}")
    else:
        print("\nNo benchmarks file provided. Use --benchmarks to load existing.")
        print("In orchestrator mode, the agent generates benchmarks interactively.")
        return

    if args.validate_only or True:
        print("\nValidating ground truth SQL...")
        try:
            report = validate_benchmarks(benchmarks, spark)
        except NameError:
            print("WARNING: spark not available (not running in Databricks notebook)")
            print("GT validation requires a Databricks Spark session.")
            return

    if args.assign_splits:
        ratios = tuple(float(x) for x in args.split_ratios.split(","))
        print(f"\nAssigning splits with ratios {ratios}...")
        assign_splits(benchmarks, ratios=ratios)

    if not args.validate_only:
        save_benchmarks(benchmarks, args.domain, args.output)

    if args.uc_schema:
        print(f"\nSyncing to MLflow Evaluation Dataset...")
        try:
            dataset_name = sync_yaml_to_mlflow_dataset(args.output, args.uc_schema, args.domain)
            print(f"Synced to {dataset_name}")
            print(f"eval_dataset_name={dataset_name}")
        except Exception as e:
            print(f"WARNING: MLflow dataset sync failed: {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()


if __name__ == "__main__":
    main()

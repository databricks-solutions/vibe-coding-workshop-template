#!/usr/bin/env python3
# /// script
# dependencies = [
#   "mlflow[databricks]>=3.10",
# ]
# ///
"""Create an evaluation dataset from a JSON questions file and persist to UC Delta.

Usage:
    python create_eval_dataset.py \
        --catalog main \
        --schema my_agent \
        --questions questions.json \
        [--app-name my_agent] \
        [--experiment-id 12345] \
        [--validate-sql]

Questions JSON format (array of objects):
    [
        {
            "question": "What is the total cost?",
            "expected_sql": "SELECT SUM(cost) FROM billing",
            "category": "aggregation",
            "expectations": {"reference": "..."}
        },
        ...
    ]

Each row must include ``question``. Any other top-level keys (except ``id``,
``expectations``) are copied into ``inputs``. If ``expectations`` is a dict,
it is used as the record's expectations; otherwise expectations default to {}.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def build_records(questions: list[dict], app_name: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    records: list[dict[str, Any]] = []

    for idx, q in enumerate(questions):
        text = (q.get("question") or "").strip()
        if not text:
            logger.warning("Skipping entry %d: empty question", idx)
            continue
        key = text.lower()
        if key in seen:
            logger.warning("Skipping duplicate question: %s", text[:60])
            continue
        seen.add(key)

        qid = q.get("id", f"{app_name}_{idx + 1:03d}")
        reserved = {"question", "expectations", "id"}
        inputs: dict[str, Any] = {"question_id": qid, "question": text}
        for k, v in q.items():
            if k not in reserved:
                inputs[k] = v

        exp = q.get("expectations")
        expectations: dict[str, Any] = dict(exp) if isinstance(exp, dict) else {}

        records.append({
            "inputs": inputs,
            "expectations": expectations,
        })

    return records


def validate_sql_records(
    records: list[dict[str, Any]],
    spark: Any,
    catalog: str,
    schema: str,
) -> tuple[list[dict[str, Any]], list[dict]]:
    valid: list[dict[str, Any]] = []
    quarantined: list[dict] = []

    for r in records:
        sql = r["inputs"].get("expected_sql", "")
        if not sql:
            valid.append(r)
            continue
        try:
            spark.sql(f"USE CATALOG `{catalog}`")
            spark.sql(f"USE SCHEMA `{schema}`")
            spark.sql(f"EXPLAIN {sql}")
            valid.append(r)
        except Exception as exc:
            qid = r["inputs"]["question_id"]
            logger.warning("Quarantined %s: %s", qid, str(exc)[:200])
            quarantined.append({
                "question_id": qid,
                "error": str(exc)[:500],
            })
            r["expectations"]["validation_status"] = "invalid"
            r["expectations"]["validation_error"] = str(exc)[:500]
            valid.append(r)

    return valid, quarantined


def save_to_delta(
    records: list[dict[str, Any]],
    uc_table_name: str,
    experiment_id: str,
) -> None:
    import mlflow

    try:
        eval_dataset = mlflow.genai.datasets.get_dataset(name=uc_table_name)
        logger.info("Reusing existing dataset: %s", uc_table_name)
    except Exception:
        create_kwargs: dict[str, Any] = {"name": uc_table_name}
        if experiment_id:
            create_kwargs["experiment_id"] = [experiment_id]
        eval_dataset = mlflow.genai.datasets.create_dataset(**create_kwargs)
        logger.info("Created new dataset: %s", uc_table_name)

    eval_dataset.merge_records(records)
    logger.info("Merged %d records into %s", len(records), uc_table_name)

    with mlflow.start_run(run_name="dataset_creation"):
        mlflow.log_param("dataset", uc_table_name)
        mlflow.log_param("record_count", len(records))
        mlflow.log_dict(
            {"records_summary": [r["inputs"]["question_id"] for r in records]},
            artifact_file="dataset_creation/record_ids.json",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create evaluation dataset from JSON questions")
    parser.add_argument("--catalog", required=True, help="UC catalog name")
    parser.add_argument("--schema", required=True, help="UC schema name")
    parser.add_argument("--questions", required=True, help="Path to questions JSON file")
    parser.add_argument(
        "--app-name",
        default="my_agent",
        help="Application name used in UC table name (default: my_agent)",
    )
    parser.add_argument("--experiment-id", default="", help="MLflow experiment ID for linkage")
    parser.add_argument("--validate-sql", action="store_true", help="Validate SQL via EXPLAIN")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build records and print summary JSON without writing to Delta / MLflow",
    )
    args = parser.parse_args()

    with open(args.questions) as f:
        questions = json.load(f)

    if not isinstance(questions, list):
        logger.error("Questions file must contain a JSON array")
        sys.exit(1)

    logger.info("Loaded %d questions from %s", len(questions), args.questions)

    records = build_records(questions, args.app_name)
    logger.info("Built %d records (after dedup)", len(records))

    quarantined: list[dict] = []
    if args.validate_sql and not args.dry_run:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        records, quarantined = validate_sql_records(records, spark, args.catalog, args.schema)
        if quarantined:
            logger.warning("Quarantined %d records with SQL errors", len(quarantined))
    elif args.validate_sql and args.dry_run:
        logger.info("[DRY RUN] Skipping SQL validation (no Spark session)")

    uc_table_name = f"{args.catalog}.{args.schema}.{args.app_name}_benchmarks"

    if args.dry_run:
        summary = {
            "dry_run": True,
            "dataset_table": uc_table_name,
            "record_count": len(records),
            "quarantined_count": len(quarantined),
            "validate_sql_requested": args.validate_sql,
        }
        print(json.dumps(summary, indent=2))
        logger.info("Done (dry run). Would write to: %s", uc_table_name)
        return

    save_to_delta(records, uc_table_name, args.experiment_id)

    logger.info("Done. Dataset: %s (%d records)", uc_table_name, len(records))
    print(json.dumps({
        "dataset_table": uc_table_name,
        "record_count": len(records),
        "quarantined_count": len(quarantined),
        "experiment_id": args.experiment_id or None,
    }, indent=2))


if __name__ == "__main__":
    main()

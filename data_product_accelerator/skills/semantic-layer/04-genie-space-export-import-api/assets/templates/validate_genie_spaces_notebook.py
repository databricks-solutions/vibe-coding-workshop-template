# Databricks notebook source
# ===========================================================================
# PATH SETUP FOR ASSET BUNDLE IMPORTS
# ===========================================================================
import sys

try:
    _notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
    _bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]
    if _bundle_root not in sys.path:
        sys.path.insert(0, _bundle_root)
        print(f"Added bundle root to sys.path: {_bundle_root}")
except Exception as e:
    print(f"Path setup skipped (local execution): {e}")
# ===========================================================================
"""
Genie Space Benchmark SQL Validation Notebook

Validates all benchmark SQL queries in Genie Space JSON configs by executing
each with LIMIT 1. Designed for Databricks Asset Bundle deployment.

Parameters (via dbutils.widgets):
    catalog: Target catalog name
    gold_schema: Target Gold schema name
    config_dir: Path to directory containing Genie Space JSON configs
"""
# COMMAND ----------

from pathlib import Path
from validate_genie_benchmark_sql import validate_benchmarks

# COMMAND ----------

catalog = dbutils.widgets.get("catalog")
gold_schema = dbutils.widgets.get("gold_schema")
config_dir = dbutils.widgets.get("config_dir")

print(f"Catalog: {catalog}")
print(f"Gold Schema: {gold_schema}")
print(f"Config Dir: {config_dir}")

# COMMAND ----------

_notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
_bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]
config_path = Path(f"{_bundle_root}/{config_dir}")

print(f"Looking for JSON configs in: {config_path}")

json_files = sorted(config_path.glob("*.json"))
if not json_files:
    print(f"No JSON config files found in {config_path}")
    dbutils.notebook.exit("No configs found")

print(f"Found {len(json_files)} Genie Space config(s)")

# COMMAND ----------

variables = {
    "catalog": catalog,
    "gold_schema": gold_schema,
}

all_reports = []
total_pass = 0
total_fail = 0
total_error = 0

for config_file in json_files:
    print(f"\n{'='*60}")
    print(f"Validating: {config_file.name}")
    print(f"{'='*60}")

    report = validate_benchmarks(
        spark=spark,
        config_path=str(config_file),
        variables=variables,
    )
    all_reports.append(report)
    total_pass += report.passed
    total_fail += report.failed
    total_error += report.errors

    print(report.summary())

# COMMAND ----------

print(f"\n{'='*60}")
print(f"OVERALL VALIDATION SUMMARY")
print(f"{'='*60}")
print(f"Configs validated: {len(all_reports)}")
print(f"Total benchmarks: {sum(r.total for r in all_reports)}")
print(f"Passed: {total_pass}")
print(f"Failed: {total_fail}")
print(f"Errors: {total_error}")

if total_fail > 0 or total_error > 0:
    print(f"\n⚠️ {total_fail + total_error} benchmark(s) need attention!")
    failing_questions = [
        r.question for report in all_reports for r in report.results if r.status != "PASS"
    ]
    for q in failing_questions:
        print(f"  ❌ {q[:100]}")

dbutils.notebook.exit(
    f'{{"total": {sum(r.total for r in all_reports)}, "passed": {total_pass}, "failed": {total_fail}, "errors": {total_error}}}'
)

# Databricks notebook source
# ===========================================================================
# PATH SETUP FOR ASSET BUNDLE IMPORTS
# ===========================================================================
# Enables imports from src modules when deployed via Databricks Asset Bundles.
# Reference: https://docs.databricks.com/aws/en/notebooks/share-code
import sys
import os

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
Run Genie Space Evaluation — Query + Judge + MLflow Log.

Self-contained Databricks notebook that evaluates a Genie Space against
benchmark questions using the MLflow GenAI evaluation framework. Runs
@scorer-decorated judges, registers them to the experiment, and calls
mlflow.genai.evaluate() so all MLflow GenAI tabs (Judges, Evaluation
runs, Traces, Datasets, Prompts) are populated.

IMPORTANT: Do NOT stack @mlflow.trace on @scorer. The mlflow.genai.evaluate()
harness traces scorer execution automatically. Stacking @mlflow.trace strips
the .register() method and leaves the Judges tab empty.

PRINCIPLE: This template IS the spec. Every checklist item in the
evaluator SKILL.md is implemented here. Checklists validate the template;
they must never disagree.

Parameters (via dbutils.widgets):
    space_id:              Genie Space ID
    experiment_name:       MLflow experiment path (MUST be /Users/<email>/...)
    iteration:             Optimization iteration number (string, converted to int)
    benchmarks_yaml_path:  Workspace path to golden-queries.yaml
    domain:                Domain name for benchmark filtering
    warehouse_id:          SQL warehouse ID for EXPLAIN / result comparison
    catalog:               Unity Catalog name for template variable resolution
    gold_schema:           Gold schema name for template variable resolution
    model_id:              (Optional) LoggedModel ID for version tracking
    dataset_mode:          "yaml" or "uc" (default: "yaml")
    uc_schema:             (Optional) Unity Catalog schema for Prompt Registry (e.g., catalog.schema)

For CLI/CI usage, use scripts/genie_evaluator.py --job-mode instead.
"""

# COMMAND ----------

import json
import time
import yaml
import hashlib
import tempfile
import mlflow
import pandas as pd
from datetime import datetime
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from mlflow.genai.scorers import scorer
# make_judge removed: all judges now use @scorer with _call_llm_for_scoring() for structured ASI
from mlflow.entities import Feedback, AssessmentSource
from typing import Union, Any

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 0a: ASI Schema, Failure Taxonomy & Eval Scope Constants (P4/P5/P9)

# COMMAND ----------

FAILURE_TAXONOMY = {
    "wrong_table", "wrong_column", "wrong_join", "missing_filter",
    "missing_temporal_filter",
    "wrong_aggregation", "wrong_measure", "missing_instruction",
    "ambiguous_question", "asset_routing_error", "tvf_parameter_error",
    "compliance_violation", "performance_issue", "repeatability_issue",
    "missing_synonym", "description_mismatch", "other",
}

ASI_SCHEMA = {
    "failure_type": "str (from FAILURE_TAXONOMY)",
    "severity": "str (critical|major|minor)",
    "confidence": "float (0.0-1.0)",
    "wrong_clause": "str|None (SELECT, FROM, WHERE, JOIN, GROUP BY, ORDER BY, MEASURE)",
    "blame_set": "list[str] (metadata fields blamed: table names, column names, instructions)",
    "quoted_metadata_text": "str|None (exact text from Genie config that caused the issue)",
    "missing_metadata": "str|None (what should exist but doesn't)",
    "ambiguity_detected": "bool",
    "expected_value": "str|None",
    "actual_value": "str|None",
    "counterfactual_fix": "str|None (suggested metadata change to fix)",
    "affected_question_pattern": "str|None (regex or description of affected questions)",
}

EVAL_SCOPES = {"full", "slice", "p0", "held_out"}


def filter_benchmarks_by_scope(benchmarks, eval_scope="full", patched_objects=None):
    """Filter benchmarks based on evaluation scope (P5).

    Args:
        benchmarks: Full benchmark list.
        eval_scope: One of "full", "slice", "p0", "held_out".
        patched_objects: List of metadata object names modified by patches (for slice scope).

    Returns:
        Filtered benchmark list.
    """
    if eval_scope == "full":
        return benchmarks
    if eval_scope == "slice" and patched_objects:
        patched = set(o.lower() for o in patched_objects)
        return [b for b in benchmarks if any(
            t.lower() in patched
            for t in b.get("required_tables", []) + b.get("required_columns", [])
        )]
    if eval_scope == "p0":
        return [b for b in benchmarks if b.get("priority", "P1") == "P0"]
    if eval_scope == "held_out":
        return [b for b in benchmarks if b.get("split") == "held_out"]
    return benchmarks


def normalize_result_df(df):
    """Deterministic normalization of a result DataFrame (P9).

    Sort columns alphabetically, sort rows, round floats to 6 decimals,
    normalize timestamps to UTC, strip whitespace.
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[sorted(df.columns)]
    for col in df.select_dtypes(include=["float64", "float32"]).columns:
        df[col] = df[col].round(6)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
        df[col] = pd.to_datetime(df[col], utc=True)
    df = df.sort_values(by=list(df.columns)).reset_index(drop=True)
    return df


def result_signature(df):
    """Quick schema hash + rowcount + numeric sums for result comparison (P9)."""
    if df is None or df.empty:
        return {"schema_hash": "", "row_count": 0, "numeric_sums": {}}
    schema_str = ",".join(f"{c}:{df[c].dtype}" for c in sorted(df.columns))
    schema_hash = hashlib.md5(schema_str.encode()).hexdigest()[:8]
    numeric_sums = {}
    for col in df.select_dtypes(include=["number"]).columns:
        numeric_sums[col] = round(float(df[col].sum()), 6)
    return {
        "schema_hash": schema_hash,
        "row_count": len(df),
        "numeric_sums": numeric_sums,
    }


def build_asi_metadata(failure_type="other", severity="minor", confidence=0.5,
                       wrong_clause=None, blame_set=None, quoted_metadata_text=None,
                       missing_metadata=None, ambiguity_detected=False,
                       expected_value=None, actual_value=None,
                       counterfactual_fix=None, affected_question_pattern=None):
    """Build an ASI metadata dict for Feedback.metadata (P4)."""
    return {
        "failure_type": failure_type if failure_type in FAILURE_TAXONOMY else "other",
        "severity": severity,
        "confidence": confidence,
        "wrong_clause": wrong_clause,
        "blame_set": blame_set or [],
        "quoted_metadata_text": quoted_metadata_text,
        "missing_metadata": missing_metadata,
        "ambiguity_detected": ambiguity_detected,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "counterfactual_fix": counterfactual_fix,
        "affected_question_pattern": affected_question_pattern,
    }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 0b: Configuration

# COMMAND ----------

space_id = dbutils.widgets.get("space_id")
experiment_name = dbutils.widgets.get("experiment_name")
iteration = int(dbutils.widgets.get("iteration"))
benchmarks_yaml_path = dbutils.widgets.get("benchmarks_yaml_path")
domain = dbutils.widgets.get("domain")
warehouse_id = dbutils.widgets.get("warehouse_id")

try:
    catalog = dbutils.widgets.get("catalog")
    if not catalog or catalog.strip() == "":
        catalog = ""
except Exception:
    catalog = ""

try:
    gold_schema = dbutils.widgets.get("gold_schema")
    if not gold_schema or gold_schema.strip() == "":
        gold_schema = ""
except Exception:
    gold_schema = ""

try:
    model_id = dbutils.widgets.get("model_id")
    if not model_id or model_id.strip() == "":
        model_id = None
except Exception:
    model_id = None

try:
    dataset_mode = dbutils.widgets.get("dataset_mode")
    if not dataset_mode or dataset_mode.strip() == "":
        dataset_mode = "uc" if uc_schema else "yaml"
except Exception:
    dataset_mode = "uc" if uc_schema else "yaml"

try:
    uc_schema = dbutils.widgets.get("uc_schema")
    if not uc_schema or uc_schema.strip() == "":
        uc_schema = f"{catalog}.{gold_schema}" if catalog and gold_schema else ""
except Exception:
    uc_schema = f"{catalog}.{gold_schema}" if catalog and gold_schema else ""

try:
    eval_scope = dbutils.widgets.get("eval_scope")
    if not eval_scope or eval_scope.strip() == "":
        eval_scope = "full"
except Exception:
    eval_scope = "full"

try:
    import base64 as _b64
    patched_b64 = dbutils.widgets.get("patched_objects_b64")
    if patched_b64 and patched_b64.strip():
        patched_objects = json.loads(_b64.b64decode(patched_b64).decode())
    else:
        patched_objects = []
except Exception:
    try:
        patched_objects_str = dbutils.widgets.get("patched_objects")
        patched_objects = json.loads(patched_objects_str) if patched_objects_str else []
    except Exception:
        patched_objects = []

try:
    eval_dataset_name = dbutils.widgets.get("eval_dataset_name")
    if not eval_dataset_name or eval_dataset_name.strip() == "":
        eval_dataset_name = None
except Exception:
    eval_dataset_name = None

try:
    run_repeatability = dbutils.widgets.get("run_repeatability")
    run_repeatability = run_repeatability.strip().lower() in ("true", "1", "yes")
except Exception:
    run_repeatability = False

try:
    min_benchmarks = int(dbutils.widgets.get("min_benchmarks"))
except Exception:
    min_benchmarks = 20

RATE_LIMIT_SECONDS = 12
MAX_GENIE_WAIT = 120
LLM_ENDPOINT = "databricks-claude-sonnet-4-6"

print(f"Space ID:        {space_id}")
print(f"Experiment:      {experiment_name}")
print(f"Iteration:       {iteration}")
print(f"Benchmarks:      {benchmarks_yaml_path}")
print(f"Domain:          {domain}")
print(f"Warehouse ID:    {warehouse_id}")
print(f"Catalog:         {catalog or '(not set)'}")
print(f"Gold Schema:     {gold_schema or '(not set)'}")
print(f"UC Schema:       {uc_schema or '(not set — prompt registry disabled)'}")
print(f"Model ID:        {model_id or '(none — version tracking disabled)'}")
print(f"Dataset Mode:    {dataset_mode}")
print(f"Eval Scope:      {eval_scope}")
if patched_objects:
    print(f"Patched Objects: {patched_objects}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 0b: LoggedModel Auto-Creation (Fallback when model_id is empty)
# MAGIC
# MAGIC When the evaluator is triggered directly (e.g., `databricks bundle run`) without
# MAGIC the orchestrator, no LoggedModel exists. This cell auto-creates one by fetching
# MAGIC the live Genie config and UC metadata snapshots, enabling config version tracking.

# COMMAND ----------

if not model_id:
    print("WARNING: model_id is empty. Auto-creating LoggedModel with UC metadata...")
    try:
        from databricks.sdk import WorkspaceClient as _WC
        _w = _WC()

        _genie_resp = _w.api_client.do(
            "GET", f"/api/2.0/genie/spaces/{space_id}",
            query_params={"include_serialized_space": "true"}
        )
        _genie_config = _genie_resp if isinstance(_genie_resp, dict) else {}
        print(f"  Fetched Genie config: {len(json.dumps(_genie_config))} chars")

        _uc_columns = []
        _uc_tags = []
        _uc_routines = []
        if catalog and gold_schema:
            try:
                _col_df = spark.sql(
                    f"SELECT table_name, column_name, data_type, comment "
                    f"FROM {catalog}.information_schema.columns "
                    f"WHERE table_schema = '{gold_schema}'"
                )
                _uc_columns = [row.asDict() for row in _col_df.collect()]
                print(f"  UC columns snapshot: {len(_uc_columns)} rows")
            except Exception as _col_err:
                print(f"  WARNING: UC columns query failed: {_col_err}")

            try:
                _tag_df = spark.sql(
                    f"SELECT * FROM {catalog}.information_schema.table_tags "
                    f"WHERE schema_name = '{gold_schema}'"
                )
                _uc_tags = [row.asDict() for row in _tag_df.collect()]
                print(f"  UC tags snapshot: {len(_uc_tags)} rows")
            except Exception as _tag_err:
                print(f"  WARNING: UC tags query failed: {_tag_err}")

            try:
                _rtns_df = spark.sql(
                    f"SELECT routine_name, routine_type, routine_definition, "
                    f"data_type AS return_type, routine_schema "
                    f"FROM {catalog}.INFORMATION_SCHEMA.ROUTINES "
                    f"WHERE routine_schema = '{gold_schema}'"
                )
                _uc_routines = [row.asDict() for row in _rtns_df.collect()]
                print(f"  UC routines snapshot: {len(_uc_routines)} rows")
            except Exception as _rtn_err:
                print(f"  WARNING: UC routines query failed: {_rtn_err}")

        _combined = json.dumps({
            "genie_config": _genie_config,
            "uc_columns": _uc_columns,
            "uc_tags": _uc_tags,
            "uc_routines": _uc_routines,
        }, sort_keys=True, default=str)
        _config_hash = hashlib.md5(_combined.encode()).hexdigest()

        _model_name = f"genie-space-{space_id}"
        _logged_model = mlflow.set_active_model(name=_model_name)
        model_id = _logged_model.model_id if hasattr(_logged_model, "model_id") else str(_logged_model)

        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"auto_logged_model_{_config_hash[:8]}"):
            _state_dir = os.path.join(tempfile.gettempdir(), f"model_state_{_config_hash[:8]}")
            os.makedirs(_state_dir, exist_ok=True)

            for _fname, _data in [
                ("genie_config.json", _genie_config),
                ("uc_columns.json", _uc_columns),
                ("uc_tags.json", _uc_tags),
                ("uc_routines.json", _uc_routines),
            ]:
                _fpath = os.path.join(_state_dir, _fname)
                with open(_fpath, "w") as _f:
                    json.dump(_data, _f, indent=2, default=str)
                mlflow.log_artifact(_fpath, artifact_path="model_state")

            mlflow.log_params({"config_hash": _config_hash, "auto_created": True})

            import shutil as _state_shmod
            _state_shmod.rmtree(_state_dir, ignore_errors=True)

        print(f"  Auto-created LoggedModel: {model_id} (hash={_config_hash[:8]})")
    except Exception as _model_err:
        print(f"  WARNING: LoggedModel auto-creation failed: {type(_model_err).__name__}: {_model_err}")
        import traceback; traceback.print_exc()
        model_id = None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 1: SQL Preprocessing Helpers (MANDATORY)

# COMMAND ----------

def resolve_sql(sql: str, cat: str = None, schema: str = None) -> str:
    """Substitute ${catalog} and ${gold_schema} template variables."""
    if not sql:
        return sql
    cat = cat or catalog
    schema = schema or gold_schema
    return sql.replace("${catalog}", cat).replace("${gold_schema}", schema)


def sanitize_sql(sql: str) -> str:
    """Extract the first SQL statement, strip comments and trailing semicolons.
    Genie may return multi-statement SQL for compound questions."""
    if not sql:
        return sql
    sql = sql.strip().rstrip(";").strip()
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if not statements:
        return sql
    first = statements[0]
    lines = [l for l in first.split("\n") if not l.strip().startswith("--")]
    return "\n".join(lines).strip()


def _extract_response_text(outputs: Union[dict, Any]) -> str:
    """Extract response text from mlflow.genai.evaluate() serialized format."""
    if isinstance(outputs, str):
        return outputs
    if isinstance(outputs, dict):
        if "response" in outputs:
            return outputs["response"]
        if "output" in outputs:
            output_list = outputs["output"]
            if output_list and len(output_list) > 0:
                item = output_list[0]
                if "content" in item and item["content"]:
                    return item["content"][0].get("text", "")
    return ""

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 2: MLflow Experiment Setup

# COMMAND ----------

mlflow.set_experiment(experiment_name)
exp = mlflow.get_experiment_by_name(experiment_name)
assert exp is not None, f"Experiment creation failed: {experiment_name}"

host = spark.conf.get("spark.databricks.workspaceUrl", "")
if host and not host.startswith("https://"):
    host = f"https://{host}"
exp_url = f"{host}/#mlflow/experiments/{exp.experiment_id}"

print(f"Experiment ID:   {exp.experiment_id}")
print(f"Experiment URL:  {exp_url}")

if model_id:
    print(f"Active Model:    {model_id} (will be linked inside evaluation run — HC #15)")
else:
    print("WARNING: No model_id provided. Config version tracking DISABLED.")
    print("  Pass model_id from orchestrator for full lifecycle tracking.")
    print("  Without it: no config snapshots, no parent chain, no promote/rollback.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 2b: UC Trace Storage Setup
# MAGIC
# MAGIC Store MLflow traces in Unity Catalog for SQL-queryable, governed observability.
# MAGIC Requires mlflow[databricks]>=3.9.0.

# COMMAND ----------

_uc_trace_catalog = catalog or ""
_uc_trace_schema = gold_schema or ""

if _uc_trace_catalog and _uc_trace_schema:
    try:
        from mlflow.entities import UCSchemaLocation
        from mlflow.tracing.enablement import set_experiment_trace_location

        _uc_location = UCSchemaLocation(
            catalog_name=_uc_trace_catalog,
            schema_name=_uc_trace_schema,
        )
        set_experiment_trace_location(
            location=_uc_location,
            experiment_id=exp.experiment_id,
        )
        mlflow.tracing.set_destination(destination=_uc_location)

        try:
            from databricks.sdk.service.ml import SetDatabricksMonitoringSqlWarehouseId
            _w_trace = WorkspaceClient()
            _w_trace.experiments.set_databricks_monitoring_sql_warehouse_id(
                warehouse_id=warehouse_id,
                experiment_id=exp.experiment_id,
            )
        except Exception as _mon_err:
            print(f"  NOTE: Monitoring warehouse setup skipped: {_mon_err}")

        print(f"UC Trace Storage: {_uc_trace_catalog}.{_uc_trace_schema}")
    except ImportError:
        print("WARNING: UC trace storage requires mlflow[databricks]>=3.9.0. Traces stored in default location.")
    except Exception as _trace_err:
        print(f"WARNING: UC trace storage setup failed: {_trace_err}. Traces stored in default location.")
else:
    print("NOTE: UC trace storage skipped (catalog/gold_schema not set).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 3: Load Benchmarks

# COMMAND ----------

_yaml_path = benchmarks_yaml_path
if not _yaml_path.startswith("/"):
    _yaml_path = os.path.join(_bundle_root, _yaml_path) if "_bundle_root" in dir() else f"/Workspace/{_yaml_path}"
elif not _yaml_path.startswith("/Workspace"):
    _yaml_path = f"/Workspace{_yaml_path}"

with open(_yaml_path) as f:
    all_benchmarks = yaml.safe_load(f)

if domain in all_benchmarks:
    benchmarks = all_benchmarks[domain]
elif "benchmarks" in all_benchmarks:
    benchmarks = all_benchmarks["benchmarks"]
else:
    benchmarks = all_benchmarks if isinstance(all_benchmarks, list) else []

assert len(benchmarks) > 0, f"No benchmarks found for domain '{domain}' in {benchmarks_yaml_path}"
print(f"Loaded {len(benchmarks)} benchmark questions for domain '{domain}'")

if eval_scope != "full":
    all_count = len(benchmarks)
    benchmarks = filter_benchmarks_by_scope(benchmarks, eval_scope, patched_objects)
    print(f"  eval_scope='{eval_scope}': filtered {all_count} -> {len(benchmarks)} benchmarks")
    assert len(benchmarks) > 0, f"No benchmarks match eval_scope='{eval_scope}'"

if eval_scope == "full" and len(benchmarks) < min_benchmarks:
    raise ValueError(
        f"Insufficient benchmarks: {len(benchmarks)} < {min_benchmarks}. "
        f"Run the Generator worker to produce more benchmarks."
    )

for b in benchmarks:
    print(f"  {b.get('id', '?')}: {b.get('question', '')[:60]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 3a: GT Validation Pre-Check
# MAGIC
# MAGIC Validates each benchmark's expected SQL by executing with LIMIT 1.
# MAGIC Failed queries go through auto-remediation (LLM + schema context).
# MAGIC Unrepairable benchmarks are excluded; if below min_benchmarks, the job fails.

# COMMAND ----------

_gt_passed = []
_gt_auto_corrected = []
_gt_excluded = []
_gt_remediation_queue = []

for _b in benchmarks:
    _b_id = _b.get("id", "?")
    _expected_sql = _b.get("expected_sql", "")
    if not _expected_sql:
        _gt_excluded.append({"id": _b_id, "reason": "empty expected_sql"})
        continue

    _resolved_sql = resolve_sql(_expected_sql, catalog, gold_schema)
    _sanitized_sql = sanitize_sql(_resolved_sql)

    try:
        _gt_result = spark.sql(f"{_sanitized_sql} LIMIT 1")
        _gt_count = _gt_result.count()
        _b["_gt_validated"] = True
        _b["expected_row_count_sample"] = _gt_count
        _gt_passed.append(_b_id)
    except Exception as _gt_err:
        _err_msg = str(_gt_err)
        print(f"  GT validation FAILED for {_b_id}: {_err_msg[:100]}")

        _remediated = False
        for _retry in range(2):
            try:
                _schema_ctx = ""
                if catalog and gold_schema:
                    try:
                        _cols = spark.sql(
                            f"SELECT table_name, column_name, data_type, comment "
                            f"FROM {catalog}.information_schema.columns "
                            f"WHERE table_schema = '{gold_schema}'"
                        ).toPandas().to_string(index=False, max_rows=200)
                        _schema_ctx += f"\n\nAvailable columns:\n{_cols}"
                    except Exception:
                        pass
                    try:
                        _rtns = spark.sql(
                            f"SELECT routine_name, routine_type, routine_definition, "
                            f"data_type AS return_type "
                            f"FROM {catalog}.INFORMATION_SCHEMA.ROUTINES "
                            f"WHERE routine_schema = '{gold_schema}'"
                        ).toPandas().to_string(index=False, max_rows=50)
                        _schema_ctx += f"\n\nAvailable TVFs/routines:\n{_rtns}"
                    except Exception:
                        pass

                _fix_prompt = (
                    f"Fix this SQL query that produces an error.\n\n"
                    f"SQL:\n{_expected_sql}\n\n"
                    f"Error:\n{_err_msg[:500]}\n\n"
                    f"Schema context:{_schema_ctx}\n\n"
                    f"Return ONLY the corrected SQL, no explanation."
                )
                _fix_resp = _call_llm_for_scoring(_fix_prompt)
                _fixed_sql = _fix_resp.strip().strip("`").strip()
                if _fixed_sql.startswith("sql"):
                    _fixed_sql = _fixed_sql[3:].strip()

                _fixed_resolved = resolve_sql(_fixed_sql, catalog, gold_schema)
                _fixed_sanitized = sanitize_sql(_fixed_resolved)
                spark.sql(f"{_fixed_sanitized} LIMIT 1")

                _b["expected_sql"] = _fixed_sql
                _b["source"] = "auto_corrected_structural"
                _b["_gt_validated"] = True
                _gt_auto_corrected.append(_b_id)
                _remediated = True
                print(f"    Auto-corrected {_b_id} (retry {_retry + 1})")
                break
            except Exception as _fix_err:
                print(f"    Auto-remediation retry {_retry + 1} failed: {str(_fix_err)[:80]}")

        if not _remediated:
            _gt_excluded.append({"id": _b_id, "reason": str(_gt_err)[:200]})
            _gt_remediation_queue.append({
                "id": _b_id,
                "question": _b.get("question", ""),
                "original_sql": _expected_sql,
                "error": str(_gt_err)[:500],
            })

benchmarks = [b for b in benchmarks if b.get("_gt_validated", False)]

print(f"\nGT Validation Summary:")
print(f"  Passed:         {len(_gt_passed)}")
print(f"  Auto-corrected: {len(_gt_auto_corrected)}")
print(f"  Excluded:       {len(_gt_excluded)}")
print(f"  Queued:         {len(_gt_remediation_queue)}")

if _gt_remediation_queue:
    _remed_dir = os.path.join(tempfile.gettempdir(), "gt_remediation")
    os.makedirs(_remed_dir, exist_ok=True)
    _remed_path = os.path.join(_remed_dir, "gt_remediation_queue.yaml")
    with open(_remed_path, "w") as _rf:
        yaml.dump(_gt_remediation_queue, _rf, default_flow_style=False)
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="gt_remediation"):
        mlflow.log_artifact(_remed_path, artifact_path="evaluation")
    import shutil as _remed_shmod
    _remed_shmod.rmtree(_remed_dir, ignore_errors=True)
    print(f"  Emitted gt_remediation_queue.yaml ({len(_gt_remediation_queue)} questions)")

if eval_scope == "full" and len(benchmarks) < min_benchmarks:
    raise ValueError(
        f"After GT validation, only {len(benchmarks)} valid benchmarks remain "
        f"(< {min_benchmarks}). Run the Generator worker to produce replacements."
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 3b: Create / Sync UC Evaluation Dataset (Populates Datasets Tab)
# MAGIC
# MAGIC When uc_schema is available, create a UC evaluation dataset so the MLflow
# MAGIC Datasets tab is populated. Falls back to DataFrame if UC creation fails.

# COMMAND ----------

def _build_inputs(b):
    """Shared inputs schema for UC dataset and DataFrame paths (HC #16)."""
    return {
        "question_id": b.get("id", ""),
        "question": b["question"],
        "space_id": space_id,
        "expected_sql": b.get("expected_sql", ""),
        "catalog": catalog,
        "gold_schema": gold_schema,
    }


def _build_expectations(b):
    """Shared expectations schema for UC dataset and DataFrame paths."""
    return {
        "expected_response": b.get("expected_sql", ""),
        "expected_asset": b.get("expected_asset", "TABLE"),
    }


eval_dataset_uc_name = None
eval_dataset = None
if (uc_schema or eval_dataset_name) and dataset_mode != "yaml_only":
    try:
        eval_dataset_uc_name = eval_dataset_name or f"{uc_schema}.genie_benchmarks_{domain}"
        eval_dataset = mlflow.genai.datasets.create_dataset(
            uc_table_name=eval_dataset_uc_name,
        )
        records = []
        for b in benchmarks:
            records.append({
                "inputs": _build_inputs(b),
                "expectations": _build_expectations(b),
            })
        eval_dataset.merge_records(records)
        print(f"UC Evaluation Dataset: {eval_dataset_uc_name} ({len(records)} records)")
    except Exception as e:
        print(f"WARNING: UC dataset creation failed ({type(e).__name__}: {e}), falling back to DataFrame")
        import traceback; traceback.print_exc()
        eval_dataset_uc_name = None
        eval_dataset = None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 4: Define Predict Function & Genie Query

# COMMAND ----------

w = WorkspaceClient()


def run_genie_query(sid, question, max_wait=MAX_GENIE_WAIT):
    """Execute a query against Genie and return SQL + status."""
    try:
        resp = w.genie.start_conversation(space_id=sid, content=question)
        conversation_id = resp.conversation_id
        message_id = resp.message_id

        poll_interval = 3
        start = time.time()
        msg = None
        while time.time() - start < max_wait:
            time.sleep(poll_interval)
            msg = w.genie.get_message(
                space_id=sid,
                conversation_id=conversation_id,
                message_id=message_id,
            )
            status = str(msg.status) if hasattr(msg, "status") else "UNKNOWN"
            if any(s in status for s in ["COMPLETED", "FAILED", "CANCELLED"]):
                break
            poll_interval = min(poll_interval + 1, 10)

        sql = None
        if msg and hasattr(msg, "attachments") and msg.attachments:
            for att in msg.attachments:
                if hasattr(att, "query") and att.query:
                    sql = att.query.query if hasattr(att.query, "query") else str(att.query)

        return {"status": status, "sql": sql, "conversation_id": conversation_id}
    except Exception as e:
        return {"status": "ERROR", "sql": None, "error": str(e)}


@mlflow.trace
def genie_predict_fn(question: str, expected_sql: str = "", **kwargs) -> dict:
    """MLflow predict function: query Genie, execute both SQLs, return response + comparison.

    mlflow.genai.evaluate() unpacks the inputs dict as keyword arguments, so
    the signature must match the keys in eval_records["inputs"].  Additional
    keys (question_id, space_id, catalog, gold_schema) are captured via
    **kwargs; space_id/catalog/gold_schema are available from outer scope.

    SQL execution is lifted here so every scorer reads pre-computed results.
    Neither result_correctness nor arbiter_scorer calls spark.sql().
    Respects 12s rate limit between Genie API calls.
    """
    _eff_sql = expected_sql
    if not _eff_sql:
        _qid = kwargs.get("question_id", "")
        if _qid:
            _match = next((b for b in benchmarks if b.get("id") == _qid), None)
            if _match:
                _eff_sql = _match.get("expected_sql", "")

    time.sleep(RATE_LIMIT_SECONDS)
    result = run_genie_query(space_id, question)
    genie_sql = sanitize_sql(result.get("sql") or "")
    gt_sql = resolve_sql(_eff_sql)

    comparison = {"match": False, "match_type": "mismatch", "gt_rows": 0,
                  "genie_rows": 0, "gt_hash": None, "genie_hash": None,
                  "gt_signature": None, "genie_signature": None, "error": None}
    if genie_sql and gt_sql:
        try:
            gt_df = normalize_result_df(spark.sql(gt_sql).toPandas())
            genie_df = normalize_result_df(spark.sql(genie_sql).toPandas())
            gt_hash = hashlib.md5(gt_df.to_csv(index=False).encode()).hexdigest()[:8]
            genie_hash = hashlib.md5(genie_df.to_csv(index=False).encode()).hexdigest()[:8]
            exact_match = gt_df.shape == genie_df.shape and gt_df.equals(genie_df)
            hash_match = gt_hash == genie_hash
            gt_sig = result_signature(gt_df)
            genie_sig = result_signature(genie_df)
            sig_match = (gt_sig["schema_hash"] == genie_sig["schema_hash"]
                         and gt_sig["row_count"] == genie_sig["row_count"])
            comparison = {
                "match": exact_match or hash_match,
                "match_type": "exact" if exact_match else ("hash" if hash_match else ("signature" if sig_match else "mismatch")),
                "gt_rows": len(gt_df),
                "genie_rows": len(genie_df),
                "gt_hash": gt_hash,
                "genie_hash": genie_hash,
                "gt_signature": gt_sig,
                "genie_signature": genie_sig,
                "error": None,
            }
        except Exception as e:
            comparison["error"] = str(e)[:200]
    else:
        comparison["error"] = "Missing SQL for comparison"

    return {
        "response": genie_sql,
        "status": result.get("status", "UNKNOWN"),
        "conversation_id": result.get("conversation_id", ""),
        "comparison": comparison,
    }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 4b: Prompt Registry — Register, Load, Tag
# MAGIC
# MAGIC Judge prompts are versioned in the MLflow Prompt Registry using `{{double_brace}}`
# MAGIC template syntax. On iteration 1, prompts are registered with dual storage
# MAGIC (Prompt Registry + experiment artifacts). On every iteration, prompts are loaded
# MAGIC by `@production` alias so `make_judge()` uses the versioned prompt, not an inline string.

# COMMAND ----------

MAKE_JUDGE_ALLOWED_VARS = {"inputs", "outputs", "trace", "expectations", "conversation"}


def _sanitize_prompt_for_make_judge(prompt: str) -> str:
    """Strip unsupported template vars and ensure at least one allowed var exists.

    make_judge() only permits: {{ inputs }}, {{ outputs }}, {{ trace }},
    {{ expectations }}, {{ conversation }}.  Custom vars raise MlflowException;
    zero vars also raises MlflowException.  This helper is a safety net for
    prompts loaded from the Prompt Registry (which accepts any variable names).
    """
    import re
    all_vars = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', prompt))
    custom_vars = all_vars - MAKE_JUDGE_ALLOWED_VARS
    cleaned = prompt
    for v in custom_vars:
        cleaned = re.sub(r'\{\{\s*' + v + r'\s*\}\}', '', cleaned)
    remaining = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', cleaned))
    if not remaining & MAKE_JUDGE_ALLOWED_VARS:
        cleaned += (
            "\n\nUser question: {{ inputs }}\n"
            "Generated output: {{ outputs }}\n"
            "Expected result: {{ expectations }}"
        )
    return cleaned


JUDGE_PROMPTS = {
    "schema_accuracy": (
        "You are a SQL schema expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL references the correct tables, columns, and joins.\n\n"
        "User question: {{ inputs }}\n"
        "Generated SQL: {{ outputs }}\n"
        "Expected SQL: {{ expectations }}\n\n"
        "Respond with yes if the generated SQL references the correct tables, columns, "
        "and joins for the question, or no if it does not."
    ),
    "logical_accuracy": (
        "You are a SQL logic expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL applies correct aggregations, filters, GROUP BY, "
        "ORDER BY, and WHERE clauses for the business question.\n\n"
        "User question: {{ inputs }}\n"
        "Generated SQL: {{ outputs }}\n"
        "Expected SQL: {{ expectations }}\n\n"
        "Respond with yes if the generated SQL applies the correct logic "
        "for the question, or no if it does not."
    ),
    "semantic_equivalence": (
        "You are a SQL semantics expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the two SQL queries measure the SAME business metric and would "
        "answer the same question, even if written differently.\n\n"
        "User question: {{ inputs }}\n"
        "Generated SQL: {{ outputs }}\n"
        "Expected SQL: {{ expectations }}\n\n"
        "Respond with yes if the two queries are semantically equivalent "
        "for the question, or no if they are not."
    ),
    "completeness": (
        "You are a SQL completeness expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL fully answers the user's question without "
        "missing dimensions, measures, or filters.\n\n"
        "User question: {{ inputs }}\n"
        "Generated SQL: {{ outputs }}\n"
        "Expected SQL: {{ expectations }}\n\n"
        "Respond with yes if the generated SQL fully answers the question, "
        "or no if it is missing dimensions, measures, or filters."
    ),
    "arbiter": (
        "You are a senior SQL arbiter for a Databricks Genie Space evaluation.\n"
        "Two SQL queries attempted to answer the same business question but produced different results.\n"
        "Analyze both queries and determine which is correct.\n\n"
        "User question and expected SQL: {{ inputs }}\n"
        "Genie response and comparison: {{ outputs }}\n"
        "Expected result: {{ expectations }}\n\n"
        "Return one of: genie_correct, ground_truth_correct, both_correct, neither_correct\n"
        'Respond with JSON: {"verdict": "...", "rationale": "explanation"}'
    ),
}


def register_judge_prompts(uc_schema, domain, experiment_name):
    """Register all judge prompts to MLflow Prompt Registry + experiment artifacts.

    Dual storage:
      1. Prompt Registry (versioned, aliased) — programmatic loading via @production
      2. Experiment artifacts — visibility in MLflow UI Artifacts tab

    Only call on iteration 1. Subsequent iterations load by alias.
    """
    registered = {}

    if uc_schema:
        for name, template in JUDGE_PROMPTS.items():
            prompt_name = f"{uc_schema}.genie_opt_{name}"
            try:
                version = mlflow.genai.register_prompt(
                    name=prompt_name,
                    template=template,
                    commit_message=f"Genie eval judge: {name} (domain: {domain})",
                    tags={"domain": domain, "type": "judge"},
                )
                mlflow.genai.set_prompt_alias(
                    name=prompt_name,
                    alias="production",
                    version=version.version,
                )
                registered[name] = {
                    "prompt_name": prompt_name,
                    "version": version.version,
                }
                print(f"  [Prompt Registry] {prompt_name} v{version.version}")
            except Exception as e:
                print(f"  [PROMPT REGISTRATION FAILED] {prompt_name}: {type(e).__name__}: {e}")
                import traceback; traceback.print_exc()

    mlflow.set_experiment(experiment_name)
    run_name = f"register_prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with mlflow.start_run(run_name=run_name):
        for name, template in JUDGE_PROMPTS.items():
            tmp = os.path.join(tempfile.gettempdir(), f"genie_opt_{name}.txt")
            with open(tmp, "w") as f:
                f.write(template)
            mlflow.log_artifact(tmp, artifact_path=f"judge_prompts/{name}")
            os.unlink(tmp)
        mlflow.log_params({
            "num_prompts": len(JUDGE_PROMPTS),
            "prompt_keys": ",".join(JUDGE_PROMPTS.keys()),
            "domain": domain,
        })

    print(f"  Registered {len(JUDGE_PROMPTS)} prompts (registry={bool(uc_schema)}, artifacts=True)")
    return registered


def load_judge_prompts(uc_schema, alias="production"):
    """Load judge prompts from Prompt Registry by alias.
    Falls back to inline JUDGE_PROMPTS if registry is unavailable."""
    prompts = {}
    for name in JUDGE_PROMPTS:
        if uc_schema:
            prompt_name = f"{uc_schema}.genie_opt_{name}"
            try:
                prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@{alias}")
                prompts[name] = prompt.template
                print(f"  [Load] {prompt_name}@{alias} -> OK")
                continue
            except Exception as e:
                print(f"  [Load] {prompt_name}@{alias} -> fallback ({e})")
        prompts[name] = JUDGE_PROMPTS[name]
    return prompts


def _prompts_already_registered(schema):
    """Check if judge prompts are already registered in the Prompt Registry."""
    if not schema:
        return False
    try:
        mlflow.genai.load_prompt(f"prompts:/{schema}.genie_opt_schema_accuracy@production")
        return True
    except Exception:
        return False


_should_register = iteration == 1 or (uc_schema and not _prompts_already_registered(uc_schema))
if _should_register:
    print(f"Iteration {iteration}: registering judge prompts to Prompt Registry...")
    _registered_prompts = register_judge_prompts(uc_schema, domain, experiment_name)
else:
    print(f"Iteration {iteration}: prompts already registered, skipping.")

print("Loading judge prompts...")
loaded_prompts = load_judge_prompts(uc_schema, alias="production")
print(f"  Loaded {len(loaded_prompts)} prompts ({sum(1 for _ in loaded_prompts)} from registry or fallback)")

if uc_schema:
    mlflow.set_experiment(experiment_name)
    mlflow.set_experiment_tags({"mlflow.promptRegistryLocation": uc_schema})
    print(f"  Experiment tag: mlflow.promptRegistryLocation = {uc_schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 5: Define Judges (@scorer + Feedback)
# MAGIC
# MAGIC DO NOT stack @mlflow.trace on @scorer. The mlflow.genai.evaluate() harness
# MAGIC traces scorer execution automatically. Stacking @mlflow.trace wraps the scorer
# MAGIC in a generic wrapper that strips .register(), leaving the Judges tab empty.

# COMMAND ----------

CODE_SOURCE = AssessmentSource(source_type="CODE", source_id="genie-optimizer-v2")
LLM_SOURCE = AssessmentSource(source_type="LLM_JUDGE", source_id=f"databricks:/{LLM_ENDPOINT}")


def _call_llm_for_scoring(prompt: str, max_retries: int = 3) -> dict:
    """Call LLM using Databricks SDK with retry + backoff (HC #14)."""
    import time as _time
    last_err = None
    for attempt in range(max_retries):
        try:
            response = w.serving_endpoints.query(
                name=LLM_ENDPOINT,
                messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
                temperature=0,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise ValueError(f"Empty LLM response on attempt {attempt + 1}")
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                content = content.rsplit("```", 1)[0]
            return json.loads(content)
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                _time.sleep(2 ** attempt)
    raise last_err


@scorer
def syntax_validity_scorer(inputs: dict, outputs: dict) -> Feedback:
    """Layer 1: Check SQL syntax by running EXPLAIN."""
    sql = sanitize_sql(_extract_response_text(outputs))
    if not sql or not sql.strip():
        return Feedback(name="syntax_validity", value="no",
                        rationale="No SQL generated.", source=CODE_SOURCE,
                        metadata=build_asi_metadata(
                            failure_type="other", severity="critical", confidence=1.0,
                            missing_metadata="Genie returned no SQL",
                            counterfactual_fix="Check Genie Space instructions and data asset visibility"))
    try:
        spark.sql(f"EXPLAIN {sql}")
        return Feedback(name="syntax_validity", value="yes",
                        rationale="SQL parses successfully via EXPLAIN.", source=CODE_SOURCE)
    except Exception as e:
        error_msg = str(e)[:200]
        return Feedback(name="syntax_validity", value="no",
                        rationale=f"EXPLAIN failed: {error_msg}", source=CODE_SOURCE,
                        metadata=build_asi_metadata(
                            failure_type="other", severity="critical", confidence=0.9,
                            wrong_clause="SELECT", actual_value=sql[:100],
                            counterfactual_fix="Fix SQL syntax in generated query"))


@scorer
def asset_routing_scorer(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """Layer 1: Check if Genie selected the correct asset type."""
    sql = sanitize_sql(_extract_response_text(outputs) or "").lower()
    expected_asset = expectations.get("expected_asset", "").upper()
    uses_mv = "mv_" in sql or "measure(" in sql
    uses_tvf = "get_" in sql
    actual_asset = "MV" if uses_mv else ("TVF" if uses_tvf else "TABLE")
    correct = actual_asset == expected_asset
    metadata = None
    if not correct:
        metadata = build_asi_metadata(
            failure_type="asset_routing_error", severity="major", confidence=0.95,
            expected_value=expected_asset, actual_value=actual_asset,
            blame_set=[f"asset_routing:{expected_asset}"],
            counterfactual_fix=f"Add instruction to prefer {expected_asset} for this query pattern")
    return Feedback(name="asset_routing", value="yes" if correct else "no",
                    rationale=f"Expected {expected_asset}, got {actual_asset}. SQL: {sql[:100]}",
                    source=CODE_SOURCE, metadata=metadata)


@scorer
def result_correctness(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """Layer 2: Compare result sets pre-computed in genie_predict_fn.

    Reads outputs["comparison"] — does NOT call spark.sql().
    SQL execution lives in the predict function to avoid redundancy
    with the arbiter scorer.
    """
    cmp = outputs.get("comparison", {}) if isinstance(outputs, dict) else {}
    if cmp.get("error"):
        return Feedback(name="result_correctness", value="no",
                        rationale=f"Comparison error: {cmp['error']}", source=CODE_SOURCE,
                        metadata=build_asi_metadata(
                            failure_type="other", severity="major", confidence=0.7,
                            actual_value=cmp.get("error", "")[:100]))
    if cmp.get("match"):
        match_type = cmp.get("match_type", "unknown")
        return Feedback(
            name="result_correctness", value="yes",
            rationale=f"Match type: {match_type}. Rows: {cmp.get('gt_rows', '?')}. "
                      f"Hash: {cmp.get('gt_hash', 'n/a')}.",
            source=CODE_SOURCE)
    return Feedback(
        name="result_correctness", value="no",
        rationale=f"Mismatch. GT rows={cmp.get('gt_rows', '?')} vs Genie rows={cmp.get('genie_rows', '?')}. "
                  f"Hash GT={cmp.get('gt_hash')} vs Genie={cmp.get('genie_hash')}.",
        source=CODE_SOURCE,
        metadata=build_asi_metadata(
            failure_type="wrong_aggregation", severity="major", confidence=0.8,
            expected_value=f"rows={cmp.get('gt_rows')}, hash={cmp.get('gt_hash')}",
            actual_value=f"rows={cmp.get('genie_rows')}, hash={cmp.get('genie_hash')}",
            counterfactual_fix="Review Genie metadata for missing joins, filters, or aggregation logic"))


@scorer
def schema_accuracy_judge(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """LLM judge: schema correctness with structured ASI output."""
    genie_sql = sanitize_sql(_extract_response_text(outputs))
    gt_sql = resolve_sql(expectations.get("expected_response", ""))
    question = inputs.get("question", "")
    prompt = (
        "You are a SQL schema expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL references the correct tables, columns, and joins.\n\n"
        f"User question: {question}\n"
        f"Expected SQL: {gt_sql}\n"
        f"Generated SQL: {genie_sql}\n\n"
        'Respond with JSON only: {"correct": true/false, "failure_type": "<wrong_table|wrong_column|wrong_join|missing_column>", '
        '"wrong_clause": "<the problematic SQL clause>", "blame_set": ["<table_or_column>"], '
        '"rationale": "<brief explanation>"}\n'
        'If correct, set failure_type to "" and blame_set to [].'
    )
    try:
        result = _call_llm_for_scoring(prompt)
    except Exception as e:
        return Feedback(name="schema_accuracy", value="unknown",
                        rationale=f"LLM call failed: {e}", source=LLM_SOURCE,
                        metadata=build_asi_metadata(
                            failure_type="other", severity="info", confidence=0.0,
                            counterfactual_fix="LLM judge unavailable — retry or check endpoint"))
    if result.get("correct", False):
        return Feedback(name="schema_accuracy", value="yes",
                        rationale=result.get("rationale", "Schema correct"), source=LLM_SOURCE)
    return Feedback(name="schema_accuracy", value="no",
                    rationale=result.get("rationale", "Schema mismatch"),
                    source=LLM_SOURCE,
                    metadata=build_asi_metadata(
                        failure_type=result.get("failure_type", "wrong_column"),
                        severity="major", confidence=0.85,
                        wrong_clause=result.get("wrong_clause", ""),
                        blame_set=result.get("blame_set", []),
                        counterfactual_fix="Review table/column references in Genie metadata"))


@scorer
def logical_accuracy_judge(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """LLM judge: logical correctness with structured ASI output."""
    genie_sql = sanitize_sql(_extract_response_text(outputs))
    gt_sql = resolve_sql(expectations.get("expected_response", ""))
    question = inputs.get("question", "")
    prompt = (
        "You are a SQL logic expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL applies correct aggregations, filters, "
        "GROUP BY, ORDER BY, and WHERE clauses for the business question.\n\n"
        f"User question: {question}\n"
        f"Expected SQL: {gt_sql}\n"
        f"Generated SQL: {genie_sql}\n\n"
        'Respond with JSON only: {"correct": true/false, "failure_type": "<wrong_aggregation|wrong_filter|wrong_groupby|wrong_orderby>", '
        '"wrong_clause": "<the problematic SQL clause>", "blame_set": ["<column_or_function>"], '
        '"rationale": "<brief explanation>"}\n'
        'If correct, set failure_type to "" and blame_set to [].'
    )
    try:
        result = _call_llm_for_scoring(prompt)
    except Exception as e:
        return Feedback(name="logical_accuracy", value="unknown",
                        rationale=f"LLM call failed: {e}", source=LLM_SOURCE,
                        metadata=build_asi_metadata(
                            failure_type="other", severity="info", confidence=0.0,
                            counterfactual_fix="LLM judge unavailable — retry or check endpoint"))
    if result.get("correct", False):
        return Feedback(name="logical_accuracy", value="yes",
                        rationale=result.get("rationale", "Logic correct"), source=LLM_SOURCE)
    return Feedback(name="logical_accuracy", value="no",
                    rationale=result.get("rationale", "Logic mismatch"),
                    source=LLM_SOURCE,
                    metadata=build_asi_metadata(
                        failure_type=result.get("failure_type", "wrong_aggregation"),
                        severity="major", confidence=0.85,
                        wrong_clause=result.get("wrong_clause", ""),
                        blame_set=result.get("blame_set", []),
                        counterfactual_fix="Review aggregation/filter logic in Genie metadata"))


@scorer
def semantic_equivalence_judge(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """LLM judge: semantic equivalence with structured ASI output."""
    genie_sql = sanitize_sql(_extract_response_text(outputs))
    gt_sql = resolve_sql(expectations.get("expected_response", ""))
    question = inputs.get("question", "")
    prompt = (
        "You are a SQL semantics expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the two SQL queries measure the SAME business metric and would "
        "answer the same question, even if written differently.\n\n"
        f"User question: {question}\n"
        f"Expected SQL: {gt_sql}\n"
        f"Generated SQL: {genie_sql}\n\n"
        'Respond with JSON only: {"equivalent": true/false, "failure_type": "<different_metric|different_grain|different_scope>", '
        '"blame_set": ["<metric_or_dimension>"], '
        '"rationale": "<brief explanation>"}\n'
        'If equivalent, set failure_type to "" and blame_set to [].'
    )
    try:
        result = _call_llm_for_scoring(prompt)
    except Exception as e:
        return Feedback(name="semantic_equivalence", value="unknown",
                        rationale=f"LLM call failed: {e}", source=LLM_SOURCE,
                        metadata=build_asi_metadata(
                            failure_type="other", severity="info", confidence=0.0,
                            counterfactual_fix="LLM judge unavailable — retry or check endpoint"))
    if result.get("equivalent", False):
        return Feedback(name="semantic_equivalence", value="yes",
                        rationale=result.get("rationale", "Semantically equivalent"), source=LLM_SOURCE)
    return Feedback(name="semantic_equivalence", value="no",
                    rationale=result.get("rationale", "Semantic mismatch"),
                    source=LLM_SOURCE,
                    metadata=build_asi_metadata(
                        failure_type=result.get("failure_type", "different_metric"),
                        severity="major", confidence=0.80,
                        blame_set=result.get("blame_set", []),
                        counterfactual_fix="Review measure definitions and grain in Genie metadata"))


@scorer
def completeness_judge(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """LLM judge: completeness with structured ASI output."""
    genie_sql = sanitize_sql(_extract_response_text(outputs))
    gt_sql = resolve_sql(expectations.get("expected_response", ""))
    question = inputs.get("question", "")
    prompt = (
        "You are a SQL completeness expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the generated SQL fully answers the user's question without "
        "missing dimensions, measures, or filters.\n\n"
        f"User question: {question}\n"
        f"Expected SQL: {gt_sql}\n"
        f"Generated SQL: {genie_sql}\n\n"
        'Respond with JSON only: {"complete": true/false, "failure_type": "<missing_column|missing_filter|missing_temporal_filter|missing_aggregation|partial_answer>", '
        '"blame_set": ["<missing_element>"], '
        '"rationale": "<brief explanation>"}\n'
        'If complete, set failure_type to "" and blame_set to [].'
    )
    try:
        result = _call_llm_for_scoring(prompt)
    except Exception as e:
        return Feedback(name="completeness", value="unknown",
                        rationale=f"LLM call failed: {e}", source=LLM_SOURCE,
                        metadata=build_asi_metadata(
                            failure_type="other", severity="info", confidence=0.0,
                            counterfactual_fix="LLM judge unavailable — retry or check endpoint"))
    if result.get("complete", False):
        return Feedback(name="completeness", value="yes",
                        rationale=result.get("rationale", "Complete"), source=LLM_SOURCE)
    return Feedback(name="completeness", value="no",
                    rationale=result.get("rationale", "Incomplete"),
                    source=LLM_SOURCE,
                    metadata=build_asi_metadata(
                        failure_type=result.get("failure_type", "missing_column"),
                        severity="major", confidence=0.80,
                        blame_set=result.get("blame_set", []),
                        counterfactual_fix="Review column visibility and filter completeness in Genie metadata"))


def _parse_arbiter_verdict(feedback) -> str:
    """Extract verdict from arbiter feedback text."""
    text = str(feedback.rationale if hasattr(feedback, "rationale") else feedback).lower()
    for v in ["genie_correct", "both_correct", "neither_correct", "ground_truth_correct"]:
        if v in text:
            return v
    return "ground_truth_correct"


@scorer
def arbiter_scorer(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """Layer 3: Arbiter — conditional scorer that fires only when results disagree.

    Reads outputs["comparison"] pre-computed in genie_predict_fn.
    Returns value="skipped" when results match (no LLM call).
    When results disagree, invokes the LLM arbiter and returns one of:
    genie_correct, ground_truth_correct, both_correct, neither_correct.
    """
    cmp = outputs.get("comparison", {}) if isinstance(outputs, dict) else {}

    if cmp.get("match"):
        return Feedback(name="arbiter", value="skipped",
                        rationale="Results match — arbiter not invoked.",
                        source=CODE_SOURCE)

    if cmp.get("error"):
        return Feedback(name="arbiter", value="skipped",
                        rationale=f"SQL execution error — cannot arbitrate: {cmp['error']}",
                        source=CODE_SOURCE)

    genie_sql = sanitize_sql(_extract_response_text(outputs))
    gt_sql = resolve_sql(expectations.get("expected_response", ""))
    question = inputs.get("question", "")

    _arbiter_instructions = loaded_prompts.get("arbiter", JUDGE_PROMPTS.get("arbiter", ""))
    prompt = (
        f"{_arbiter_instructions}\n\n"
        f"Question: {question}\n"
        f"Ground Truth SQL: {gt_sql}\n"
        f"Genie SQL: {genie_sql}\n"
        f"Result comparison: {json.dumps(cmp)}\n\n"
        'Respond with JSON only: {"verdict": "<genie_correct|ground_truth_correct|both_correct|neither_correct>", '
        '"failure_type": "<wrong_aggregation|wrong_filter|wrong_table|other>", '
        '"blame_set": ["<blamed_object>"], '
        '"rationale": "<brief explanation>"}'
    )
    try:
        result = _call_llm_for_scoring(prompt)
        verdict = result.get("verdict", "ground_truth_correct")
        if verdict not in ("genie_correct", "ground_truth_correct", "both_correct", "neither_correct"):
            verdict = _parse_arbiter_verdict(type("F", (), {"rationale": result.get("rationale", str(result))})())
        _meta = None
        if verdict in ("ground_truth_correct", "neither_correct"):
            _meta = build_asi_metadata(
                failure_type=result.get("failure_type", "other"),
                severity="major", confidence=0.85,
                blame_set=result.get("blame_set", []),
                counterfactual_fix=result.get("rationale", ""))
        return Feedback(
            name="arbiter", value=verdict,
            rationale=result.get("rationale", verdict),
            source=LLM_SOURCE, metadata=_meta)
    except Exception as e:
        verdict = "ground_truth_correct"
        return Feedback(
            name="arbiter", value=verdict,
            rationale=f"Arbiter LLM call failed, defaulting to ground_truth_correct: {e}",
            source=LLM_SOURCE,
            metadata=build_asi_metadata(
                failure_type="other", severity="info", confidence=0.0,
                counterfactual_fix="LLM judge unavailable — retry or check endpoint"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 6: Register Judges to Experiment (Populates Judges Tab)

# COMMAND ----------

all_scorers = [
    syntax_validity_scorer,
    schema_accuracy_judge,
    logical_accuracy_judge,
    semantic_equivalence_judge,
    completeness_judge,
    asset_routing_scorer,
    result_correctness,
    arbiter_scorer,
]

registered_judges = {}
_registration_failures = []
for s in all_scorers:
    name = getattr(s, "name", getattr(s, "__name__", str(s)))
    try:
        reg = s.register(name=name)
        registered_judges[name] = reg
        print(f"  [Registered] {name}")
    except Exception as e:
        _registration_failures.append((name, e))
        print(f"  [FAILED to register] {name}: {type(e).__name__}: {e}")

print(f"\nRegistered {len(registered_judges)}/{len(all_scorers)} judges to experiment.")
if _registration_failures:
    print(f"  WARNING: {len(_registration_failures)} scorer(s) failed to register.")
    print("  The Judges tab will be missing these scorers.")
    for fname, ferr in _registration_failures:
        print(f"    - {fname}: {ferr}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 7: Prepare Evaluation Data

# COMMAND ----------

eval_records = []
for b in benchmarks:
    eval_records.append({
        "inputs": _build_inputs(b),
        "expectations": _build_expectations(b),
    })
eval_data = pd.DataFrame(eval_records)
print(f"Prepared {len(eval_records)} evaluation records as DataFrame.")

# Cell 7.5: Pre-evaluation assertion — catch missing fields before wasting compute
if eval_records:
    _sample = eval_records[0]["inputs"]
    assert "expected_sql" in _sample and _sample["expected_sql"], \
        "expected_sql missing from inputs — result_correctness will score 0%"
    assert "catalog" in _sample, "catalog missing from inputs — SQL templates won't resolve"

if eval_dataset_uc_name:
    print(f"UC Evaluation Dataset '{eval_dataset_uc_name}' also created (populates Datasets tab).")
elif not uc_schema:
    print("TIP: Set uc_schema to auto-create a UC evaluation dataset and populate the Datasets tab.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 8: Run mlflow.genai.evaluate() (Populates Evaluation Runs + Traces Tabs)

# COMMAND ----------

run_name = f"genie_eval_iter{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"Starting evaluation: {run_name}")
print(f"  Scorers: {len(all_scorers)}")
print(f"  Benchmarks: {len(benchmarks)}")
print(f"  Estimated time: ~{len(benchmarks) * (RATE_LIMIT_SECONDS + 15)}s\n")

with mlflow.start_run(run_name=run_name) as run:
    run_params = {
        "space_id": space_id,
        "iteration": iteration,
        "dataset": f"{domain}_benchmarks",
        "eval_dataset_name": eval_dataset_uc_name or eval_dataset_name or "",
        "dataset_mode": dataset_mode,
        "eval_scope": eval_scope,
        "num_scorers": len(all_scorers),
        "scorer_names": ",".join(
            getattr(s, "name", getattr(s, "__name__", str(s))) for s in all_scorers
        ),
        "domain": domain,
        "warehouse_id": warehouse_id,
        "benchmark_count": len(benchmarks),
    }
    if model_id:
        run_params["model_id"] = model_id
    if catalog:
        run_params["catalog"] = catalog
    if gold_schema:
        run_params["gold_schema"] = gold_schema
    if uc_schema:
        run_params["uc_schema"] = uc_schema
    mlflow.log_params(run_params)

    if model_id:
        mlflow.set_active_model(model_id=model_id)

    evaluate_kwargs = {
        "predict_fn": genie_predict_fn,
        "data": eval_data,
        "scorers": all_scorers,
    }
    if model_id:
        evaluate_kwargs["model_id"] = model_id

    eval_result = mlflow.genai.evaluate(**evaluate_kwargs)

    from collections import Counter
    thresholds = {
        "syntax_validity/mean": 0.98,
        "schema_accuracy/mean": 0.95,
        "logical_accuracy/mean": 0.90,
        "semantic_equivalence/mean": 0.90,
        "completeness/mean": 0.90,
        "result_correctness/mean": 0.85,
        "asset_routing/mean": 0.95,
    }
    all_pass = True
    for metric_name, threshold in thresholds.items():
        value = eval_result.metrics.get(metric_name)
        if value is not None:
            status = "PASS" if value >= threshold else "FAIL"
            if value < threshold:
                all_pass = False
            print(f"  [{status}] {metric_name}: {value:.3f} (target: {threshold})")

    mlflow.log_metric("thresholds_passed", 1.0 if all_pass else 0.0)

    run_url = f"{host}/#mlflow/experiments/{exp.experiment_id}/runs/{run.info.run_id}"

print("=" * 60)
print(f"  EVALUATION COMPLETE")
print(f"  Run:        {run_name}")
print(f"  Run ID:     {run.info.run_id}")
print(f"  Run URL:    {run_url}")
print(f"  Thresholds: {'ALL PASSED' if all_pass else 'SOME FAILED'}")
print("=" * 60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 9: Output Result

# COMMAND ----------

per_judge = {}
for metric_name in eval_result.metrics:
    if "/mean" in metric_name:
        judge_name = metric_name.replace("/mean", "")
        per_judge[judge_name] = eval_result.metrics[metric_name]

_JUDGE_METRIC_NAMES = [
    "result_correctness", "asset_routing", "syntax_validity",
    "schema_accuracy", "semantic_equivalence", "completeness",
    "logical_accuracy",
]
for _jname in _JUDGE_METRIC_NAMES:
    if _jname in per_judge:
        mlflow.log_metric(f"eval_{_jname}_pct", per_judge[_jname] * 100)

overall_accuracy = per_judge.get("result_correctness", 0.0)

failure_ids = []
arbiter_verdicts = {"genie_correct": 0, "ground_truth_correct": 0,
                    "both_correct": 0, "neither_correct": 0, "skipped": 0}
if hasattr(eval_result, "tables") and "eval_results" in eval_result.tables:
    results_df = eval_result.tables["eval_results"]
    for _, row in results_df.iterrows():
        rc = row.get("result_correctness/value", row.get("result_correctness", ""))
        if str(rc).lower() in ("no", "false", "0", "0.0"):
            qid = row.get("inputs/question_id", row.get("inputs", {}).get("question_id", ""))
            if qid:
                failure_ids.append(str(qid))
        av = str(row.get("arbiter/value", row.get("arbiter", "skipped")))
        if av in arbiter_verdicts:
            arbiter_verdicts[av] += 1
        else:
            arbiter_verdicts["skipped"] += 1

arbiter_fired = sum(v for k, v in arbiter_verdicts.items() if k != "skipped")
print(f"\nArbiter verdicts: {arbiter_verdicts}")
print(f"Arbiter fired on {arbiter_fired}/{len(benchmarks)} questions")

output = {
    "run_id": run.info.run_id,
    "run_name": run_name,
    "experiment_id": exp.experiment_id,
    "iteration": iteration,
    "overall_accuracy": overall_accuracy,
    "questions_total": len(benchmarks),
    "thresholds_passed": all_pass,
    "per_judge": per_judge,
    "failure_question_ids": failure_ids,
    "arbiter_verdicts": arbiter_verdicts,
    "model_id": model_id,
    "dataset_mode": dataset_mode,
    "uc_schema": uc_schema or None,
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 9b: Emit Structured Artifacts for Orchestrator Consumption

# COMMAND ----------

rows_for_output = []
failures_artifact = []
arbiter_actions_artifact = []

if hasattr(eval_result, "tables") and "eval_results" in eval_result.tables:
    results_df = eval_result.tables["eval_results"]
    import tempfile as _tmpmod
    import os as _osmod

    for _, row in results_df.iterrows():
        row_dict = {}
        for col in results_df.columns:
            val = row[col]
            if hasattr(val, "item"):
                val = val.item()
            row_dict[col] = val
        rows_for_output.append(row_dict)

        rc = row.get("result_correctness/value", row.get("result_correctness", ""))
        is_failure = str(rc).lower() in ("no", "false", "0", "0.0")
        if is_failure:
            failures_artifact.append(row_dict)

        av = str(row.get("arbiter/value", row.get("arbiter", "skipped")))
        if av in ("genie_correct", "ground_truth_correct", "both_correct", "neither_correct"):
            arbiter_actions_artifact.append({
                "question_id": row.get("inputs/question_id", ""),
                "question": row.get("inputs/question", ""),
                "verdict": av,
                "expected_sql": row.get("inputs/expected_sql", ""),
                "generated_sql": row.get("outputs/generated_sql", row.get("outputs", "")),
                "rationale": str(row.get("arbiter/rationale", row.get("rationale/arbiter", ""))),
            })

    artifact_dir = _tmpmod.mkdtemp(prefix="genie_eval_artifacts_")

    eval_results_path = _osmod.path.join(artifact_dir, "eval_results.json")
    with open(eval_results_path, "w") as f:
        json.dump(rows_for_output, f, indent=2, default=str)

    failures_path = _osmod.path.join(artifact_dir, "failures.json")
    with open(failures_path, "w") as f:
        json.dump(failures_artifact, f, indent=2, default=str)

    arbiter_path = _osmod.path.join(artifact_dir, "arbiter_actions.json")
    with open(arbiter_path, "w") as f:
        json.dump(arbiter_actions_artifact, f, indent=2, default=str)

    with mlflow.start_run(run_id=run.info.run_id):
        mlflow.log_artifact(eval_results_path, artifact_path="evaluation")
        mlflow.log_artifact(failures_path, artifact_path="evaluation")
        mlflow.log_artifact(arbiter_path, artifact_path="evaluation")

    print(f"\nArtifacts logged to evaluation/:")
    print(f"  eval_results.json: {len(rows_for_output)} rows")
    print(f"  failures.json: {len(failures_artifact)} failures")
    print(f"  arbiter_actions.json: {len(arbiter_actions_artifact)} actions")

    import shutil as _shmod
    _shmod.rmtree(artifact_dir, ignore_errors=True)

    # --- ASI UC Table Write ---
    # Persist structured ASI to genie_eval_asi_results UC Delta table for optimizer consumption.
    _ASI_JUDGES = ["syntax_validity", "schema_accuracy", "logical_accuracy",
                   "semantic_equivalence", "completeness", "asset_routing",
                   "result_correctness", "arbiter"]
    if catalog and gold_schema:
        _asi_table = f"{catalog}.{gold_schema}.genie_eval_asi_results"
        try:
            spark.sql(f"""
                CREATE TABLE IF NOT EXISTS {_asi_table} (
                    run_id STRING, iteration INT, question_id STRING, judge STRING,
                    value STRING, failure_type STRING, severity STRING,
                    confidence DOUBLE, blame_set STRING, counterfactual_fix STRING,
                    wrong_clause STRING, expected_value STRING, actual_value STRING,
                    missing_metadata STRING, ambiguity_detected BOOLEAN,
                    logged_at TIMESTAMP
                ) USING DELTA
            """)
            _asi_rows = []
            for _row_dict in rows_for_output:
                _q_id = (_row_dict.get("inputs/question_id") or
                         (_row_dict.get("inputs", {}) or {}).get("question_id", ""))
                for _jname in _ASI_JUDGES:
                    _val = str(_row_dict.get(f"{_jname}/value",
                               _row_dict.get(_jname, "")))
                    _meta = _row_dict.get(f"{_jname}/metadata", {})
                    if not isinstance(_meta, dict):
                        _meta = {}
                    if _val and _val.lower() not in ("", "none"):
                        _blame = _meta.get("blame_set", [])
                        _asi_rows.append((
                            run.info.run_id, int(iteration), str(_q_id), _jname,
                            _val,
                            _meta.get("failure_type", ""),
                            _meta.get("severity", ""),
                            float(_meta.get("confidence", 0.0)),
                            json.dumps(_blame) if isinstance(_blame, list) else str(_blame),
                            _meta.get("counterfactual_fix", ""),
                            _meta.get("wrong_clause", ""),
                            _meta.get("expected_value", ""),
                            _meta.get("actual_value", ""),
                            _meta.get("missing_metadata", ""),
                            bool(_meta.get("ambiguity_detected", False)),
                        ))
            if _asi_rows:
                _asi_df = spark.createDataFrame(
                    _asi_rows,
                    schema="run_id STRING, iteration INT, question_id STRING, judge STRING, "
                           "value STRING, failure_type STRING, severity STRING, "
                           "confidence DOUBLE, blame_set STRING, counterfactual_fix STRING, "
                           "wrong_clause STRING, expected_value STRING, actual_value STRING, "
                           "missing_metadata STRING, ambiguity_detected BOOLEAN"
                )
                from pyspark.sql.functions import current_timestamp
                _asi_df = _asi_df.withColumn("logged_at", current_timestamp())
                _asi_df.write.mode("append").saveAsTable(_asi_table)
                print(f"\n  ASI UC table: {len(_asi_rows)} rows written to {_asi_table}")
            else:
                print(f"\n  ASI UC table: no ASI rows to write")
        except Exception as _asi_err:
            print(f"\n  WARNING: ASI UC table write failed: {_asi_err}")
    else:
        print("\n  ASI UC table: skipped (catalog/gold_schema not set)")

    _genie_correct_actions = [a for a in arbiter_actions_artifact if a.get("verdict") == "genie_correct"]
    if _genie_correct_actions:
        _corrections_applied = 0
        for _gc in _genie_correct_actions:
            _gc_qid = _gc.get("question_id", "")
            _gc_sql = _gc.get("generated_sql", "")
            if _gc_qid and _gc_sql:
                for _b in benchmarks:
                    if _b.get("id") == _gc_qid:
                        _b["expected_sql"] = _gc_sql
                        _b["source"] = "arbiter_correction"
                        _corrections_applied += 1
                        break

        if _corrections_applied > 0:
            try:
                _updated_yaml = {domain: benchmarks}
                with open(_yaml_path, "w") as _yf:
                    yaml.dump(_updated_yaml, _yf, default_flow_style=False)
                print(f"  Arbiter auto-persistence: updated {_corrections_applied} benchmarks in golden-queries.yaml")
            except Exception as _persist_err:
                print(f"  WARNING: Arbiter auto-persistence failed: {_persist_err}")

        with mlflow.start_run(run_id=run.info.run_id):
            mlflow.log_metric("arbiter_corrections_count", len(_genie_correct_actions))

        print(f"  Arbiter genie_correct verdicts: {len(_genie_correct_actions)}")
else:
    print("WARNING: eval_result.tables['eval_results'] not available. No artifacts emitted.")

_gt_correction_threshold_reached = len(
    [a for a in arbiter_actions_artifact if a.get("verdict") == "genie_correct"]
) >= 3

output["total_questions"] = len(benchmarks)
output["rows"] = rows_for_output
output["arbiter_actions"] = arbiter_actions_artifact
output["gt_correction_threshold_reached"] = _gt_correction_threshold_reached
output["artifact_paths"] = {
    "eval_results": "evaluation/eval_results.json",
    "failures": "evaluation/failures.json",
    "arbiter_actions": "evaluation/arbiter_actions.json",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 9c: Repeatability Check
# MAGIC
# MAGIC Optional post-evaluation step that re-queries Genie for each benchmark question
# MAGIC to measure SQL generation consistency. Gated behind the `run_repeatability`
# MAGIC widget parameter. Each question is re-queried 2 additional times; the original
# MAGIC SQL from predict_fn is included in the hash comparison (3 total samples).

# COMMAND ----------

REPEATABILITY_EXTRA_QUERIES = 2
REPEATABILITY_CLASSIFICATIONS = {
    100: "IDENTICAL",
    70: "MINOR_VARIANCE",
    50: "SIGNIFICANT_VARIANCE",
    0: "CRITICAL_VARIANCE",
}

def _classify_repeatability(pct: float) -> str:
    for threshold in sorted(REPEATABILITY_CLASSIFICATIONS.keys(), reverse=True):
        if pct >= threshold:
            return REPEATABILITY_CLASSIFICATIONS[threshold]
    return "CRITICAL_VARIANCE"

def detect_asset_type(sql: str) -> str:
    if not sql:
        return "NONE"
    sql_lower = sql.lower()
    if "mv_" in sql_lower or "measure(" in sql_lower:
        return "MV"
    elif "get_" in sql_lower:
        return "TVF"
    return "TABLE"

if run_repeatability:
    print("\n" + "=" * 60)
    print("Cell 9c: Repeatability Check")
    print(f"  Re-querying each question {REPEATABILITY_EXTRA_QUERIES} extra times")
    est_secs = len(rows_for_output) * REPEATABILITY_EXTRA_QUERIES * (RATE_LIMIT_SECONDS + 15)
    print(f"  Estimated time: ~{est_secs}s ({est_secs / 60:.1f} min)")
    print("=" * 60)

    from collections import Counter as _RepCounter

    def _extract_field(row, primary_key, *fallback_paths):
        val = row.get(primary_key)
        if val:
            return val
        for path in fallback_paths:
            if isinstance(path, tuple):
                nested = row.get(path[0])
                if isinstance(nested, dict):
                    val = nested.get(path[1], "")
                    if val:
                        return val
            else:
                val = row.get(path, "")
                if val:
                    return val
        return ""

    repeatability_results = []
    for idx, row_data in enumerate(rows_for_output):
        question = _extract_field(
            row_data, "inputs/question", "request/question",
            ("request", "question"), ("inputs", "question"))
        original_sql = _extract_field(
            row_data, "outputs/response", "response",
            ("outputs", "response"), ("response", "sql"))
        question_id = _extract_field(
            row_data, "inputs/question_id",
            ("inputs", "question_id"), ("request", "question_id"))
        if not question:
            continue

        original_hash = (
            hashlib.md5(original_sql.lower().encode()).hexdigest()[:8]
            if original_sql else "NONE"
        )
        hashes = [original_hash]
        sqls = [original_sql or ""]

        print(f"  [{idx + 1}/{len(rows_for_output)}] {question[:50]}...", end=" ", flush=True)
        for retry_i in range(REPEATABILITY_EXTRA_QUERIES):
            time.sleep(RATE_LIMIT_SECONDS)
            retry_result = run_genie_query(space_id, question)
            retry_sql = retry_result.get("sql", "") or ""
            retry_hash = (
                hashlib.md5(retry_sql.lower().encode()).hexdigest()[:8]
                if retry_sql else "NONE"
            )
            hashes.append(retry_hash)
            sqls.append(retry_sql)

        hash_counts = _RepCounter(hashes)
        most_common_count = hash_counts.most_common(1)[0][1]
        pct = (most_common_count / len(hashes)) * 100
        asset_type = detect_asset_type(original_sql) if original_sql else "NONE"
        classification = _classify_repeatability(pct)

        print(f"{classification} ({pct:.0f}%, {len(set(hashes))} variants, asset={asset_type})")

        repeatability_results.append({
            "question_id": question_id,
            "question": question,
            "repeatability_pct": pct,
            "classification": classification,
            "unique_variants": len(set(hashes)),
            "dominant_asset": asset_type,
            "hashes": hashes,
        })

    avg_repeatability = (
        sum(r["repeatability_pct"] for r in repeatability_results)
        / len(repeatability_results)
        if repeatability_results else 0
    )

    critical_count = sum(1 for r in repeatability_results if r["classification"] == "CRITICAL_VARIANCE")
    significant_count = sum(1 for r in repeatability_results if r["classification"] == "SIGNIFICANT_VARIANCE")
    identical_count = sum(1 for r in repeatability_results if r["classification"] == "IDENTICAL")

    print(f"\n  Repeatability Summary:")
    print(f"    Average:      {avg_repeatability:.0f}%")
    print(f"    Identical:    {identical_count}")
    print(f"    Critical:     {critical_count}")
    print(f"    Significant:  {significant_count}")

    import tempfile as _rep_tmpmod
    import os as _rep_osmod

    rep_artifact_dir = _rep_tmpmod.mkdtemp(prefix="genie_repeatability_")
    rep_path = _rep_osmod.path.join(rep_artifact_dir, "repeatability.json")
    with open(rep_path, "w") as f:
        json.dump({
            "average_repeatability_pct": avg_repeatability,
            "total_questions": len(repeatability_results),
            "identical": identical_count,
            "critical_variance": critical_count,
            "significant_variance": significant_count,
            "results": repeatability_results,
        }, f, indent=2, default=str)

    with mlflow.start_run(run_id=run.info.run_id):
        mlflow.log_metric("repeatability/mean", avg_repeatability / 100)
        mlflow.log_metric("repeatability/identical_count", identical_count)
        mlflow.log_metric("repeatability/critical_count", critical_count)
        mlflow.log_artifact(rep_path, artifact_path="evaluation")

        _SEVERITY_MAP = {
            "CRITICAL_VARIANCE": "critical",
            "SIGNIFICANT_VARIANCE": "major",
            "MINOR_VARIANCE": "minor",
            "IDENTICAL": "info",
        }
        _rep_asi_rows = []
        for rep_result in repeatability_results:
            _classification = rep_result["classification"]
            _pct = rep_result["repeatability_pct"]
            _dominant_asset = rep_result.get("dominant_asset", "NONE")
            _unique_count = rep_result["unique_variants"]
            _is_failure = _classification != "IDENTICAL"
            _rep_meta = None
            if _is_failure:
                _rep_meta = build_asi_metadata(
                    failure_type="repeatability_issue",
                    severity=_SEVERITY_MAP.get(_classification, "minor"),
                    confidence=max(0.0, 1.0 - _pct / 100),
                    blame_set=[f"asset_routing:{_dominant_asset}"],
                    expected_value="IDENTICAL (100% consistency)",
                    actual_value=f"{_classification} ({_pct:.0f}%, {_unique_count} unique variants)",
                    counterfactual_fix="Disambiguate routing metadata for competing assets",
                    ambiguity_detected=True,
                )
            try:
                mlflow.log_assessment(
                    trace_id=rep_result.get("trace_id", run.info.run_id),
                    name="repeatability",
                    source=mlflow.AssessmentSource(
                        source_type="CODE",
                        source_id="cell_9c_repeatability",
                    ),
                    value=rep_result["classification"],
                    rationale=f"Repeatability: {_pct:.0f}%, "
                              f"{_unique_count} variants, "
                              f"asset={_dominant_asset}",
                    metadata=_rep_meta,
                )
            except Exception as _assess_err:
                print(f"  WARNING: mlflow.log_assessment() failed for {rep_result.get('question_id', '?')}: {_assess_err}")

            if _is_failure and catalog and gold_schema:
                _rep_asi_rows.append((
                    run.info.run_id, int(iteration),
                    str(rep_result.get("question_id", "")),
                    "repeatability", _classification,
                    "repeatability_issue",
                    _SEVERITY_MAP.get(_classification, "minor"),
                    max(0.0, 1.0 - _pct / 100),
                    json.dumps([f"asset_routing:{_dominant_asset}"]),
                    "Disambiguate routing metadata for competing assets",
                    "", "IDENTICAL (100% consistency)",
                    f"{_classification} ({_pct:.0f}%, {_unique_count} unique variants)",
                    "", True,
                ))

        if _rep_asi_rows and catalog and gold_schema:
            _asi_table = f"{catalog}.{gold_schema}.genie_eval_asi_results"
            try:
                _rep_asi_df = spark.createDataFrame(
                    _rep_asi_rows,
                    schema="run_id STRING, iteration INT, question_id STRING, judge STRING, "
                           "value STRING, failure_type STRING, severity STRING, "
                           "confidence DOUBLE, blame_set STRING, counterfactual_fix STRING, "
                           "wrong_clause STRING, expected_value STRING, actual_value STRING, "
                           "missing_metadata STRING, ambiguity_detected BOOLEAN"
                )
                from pyspark.sql.functions import current_timestamp as _rep_ts
                _rep_asi_df = _rep_asi_df.withColumn("logged_at", _rep_ts())
                _rep_asi_df.write.mode("append").saveAsTable(_asi_table)
                print(f"  ASI UC table: {len(_rep_asi_rows)} repeatability rows appended")
            except Exception as _rep_asi_err:
                print(f"  WARNING: Repeatability ASI UC table write failed: {_rep_asi_err}")

    import shutil as _rep_shmod
    _rep_shmod.rmtree(rep_artifact_dir, ignore_errors=True)

    print(f"  Logged repeatability/mean={avg_repeatability / 100:.3f} to MLflow run {run.info.run_id}")
    print(f"  Logged {len(repeatability_results)} per-trace repeatability assessments (with structured ASI)")

    output["repeatability_pct"] = avg_repeatability
    output["repeatability_details"] = repeatability_results
    output["artifact_paths"]["repeatability"] = "evaluation/repeatability.json"
else:
    print("\nRepeatability check: SKIPPED (run_repeatability=false)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 10: Exit

# COMMAND ----------

dbutils.notebook.exit(json.dumps(output, default=str))

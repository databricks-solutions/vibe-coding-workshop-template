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

For CLI/CI usage, use scripts/genie_optimizer.py --job-mode instead.
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
from mlflow.genai.judges import make_judge
from mlflow.entities import Feedback, AssessmentSource
from typing import Union, Any

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 0a: ASI Schema, Failure Taxonomy & Eval Scope Constants (P4/P5/P9)

# COMMAND ----------

FAILURE_TAXONOMY = {
    "wrong_table", "wrong_column", "wrong_join", "missing_filter",
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
    mlflow.set_active_model(model_id=model_id)
    print(f"Active Model:    {model_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 3: Load Benchmarks

# COMMAND ----------

with open(f"/Workspace/{benchmarks_yaml_path}") as f:
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

for b in benchmarks:
    print(f"  {b.get('id', '?')}: {b.get('question', '')[:60]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cell 3b: Create / Sync UC Evaluation Dataset (Populates Datasets Tab)
# MAGIC
# MAGIC When uc_schema is available, create a UC evaluation dataset so the MLflow
# MAGIC Datasets tab is populated. Falls back to DataFrame if UC creation fails.

# COMMAND ----------

eval_dataset_uc_name = None
if uc_schema and dataset_mode != "yaml_only":
    try:
        eval_dataset_uc_name = f"{uc_schema}.genie_bench_{domain}"
        eval_dataset = mlflow.genai.datasets.create_dataset(
            uc_table_name=eval_dataset_uc_name,
        )
        records = []
        for b in benchmarks:
            records.append({
                "inputs": {"question": b["question"], "space_id": space_id},
                "expectations": {
                    "expected_response": b.get("expected_sql", ""),
                    "expected_asset": b.get("expected_asset", "TABLE"),
                },
            })
        eval_dataset.merge_records(records)
        print(f"UC Evaluation Dataset: {eval_dataset_uc_name} ({len(records)} records)")
    except Exception as e:
        print(f"WARNING: UC dataset creation failed ({type(e).__name__}: {e}), falling back to DataFrame")
        import traceback; traceback.print_exc()
        eval_dataset_uc_name = None

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
def genie_predict_fn(inputs: dict) -> dict:
    """MLflow predict function: query Genie, execute both SQLs, return response + comparison.

    SQL execution is lifted here so every scorer reads pre-computed results.
    Neither result_correctness nor arbiter_scorer calls spark.sql().
    Respects 12s rate limit between Genie API calls.
    """
    question = inputs.get("question", "")
    expected_sql = inputs.get("expected_sql", "")
    time.sleep(RATE_LIMIT_SECONDS)
    result = run_genie_query(space_id, question)
    genie_sql = sanitize_sql(result.get("sql") or "")
    gt_sql = resolve_sql(expected_sql)

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

JUDGE_PROMPTS = {
    "schema_accuracy": (
        "You are a SQL schema expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL references the correct tables, columns, and joins.\n\n"
        "Question: {{question}}\nExpected SQL: {{expected_sql}}\nGenerated SQL: {{genie_sql}}\n\n"
        'Respond with JSON: {"score": "yes" or "no", "rationale": "explanation"}'
    ),
    "logical_accuracy": (
        "You are a SQL logic expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL applies correct aggregations, filters, GROUP BY, "
        "ORDER BY, and WHERE clauses for the business question.\n\n"
        "Question: {{question}}\nExpected SQL: {{expected_sql}}\nGenerated SQL: {{genie_sql}}\n\n"
        'Respond with JSON: {"score": "yes" or "no", "rationale": "explanation"}'
    ),
    "semantic_equivalence": (
        "You are a SQL semantics expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the two SQL queries measure the SAME business metric and would "
        "answer the same question, even if written differently.\n\n"
        "Question: {{question}}\nExpected SQL: {{expected_sql}}\nGenerated SQL: {{genie_sql}}\n\n"
        'Respond with JSON: {"score": "yes" or "no", "rationale": "explanation"}'
    ),
    "completeness": (
        "You are a SQL completeness expert evaluating SQL for a Databricks Genie Space.\n"
        "Determine if the GENERATED SQL fully answers the user's question without "
        "missing dimensions, measures, or filters.\n\n"
        "Question: {{question}}\nExpected SQL: {{expected_sql}}\nGenerated SQL: {{genie_sql}}\n\n"
        'Respond with JSON: {"score": "yes" or "no", "rationale": "explanation"}'
    ),
    "arbiter": (
        "You are a senior SQL arbiter for a Databricks Genie Space evaluation.\n"
        "Two SQL queries attempted to answer the same business question but produced different results.\n"
        "Analyze both queries and determine which is correct.\n\n"
        "Question: {{question}}\nGround Truth SQL: {{gt_sql}}\nGenie SQL: {{genie_sql}}\n"
        "Result comparison: {{comparison}}\n\n"
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


def _call_llm_for_scoring(prompt: str) -> dict:
    """Call LLM using Databricks SDK for scorer evaluation."""
    response = w.serving_endpoints.query(
        name=LLM_ENDPOINT,
        messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


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


schema_accuracy_judge = make_judge(
    name="schema_accuracy",
    instructions=loaded_prompts.get("schema_accuracy", (
        "You are a SQL schema expert. Determine if the generated SQL references "
        "the correct tables, columns, and joins for the given question."
    )),
    model=f"databricks:/{LLM_ENDPOINT}",
)

logical_accuracy_judge = make_judge(
    name="logical_accuracy",
    instructions=loaded_prompts.get("logical_accuracy", (
        "You are a SQL logic expert. Determine if the generated SQL applies correct "
        "aggregations, filters, GROUP BY, ORDER BY, and WHERE clauses for the question."
    )),
    model=f"databricks:/{LLM_ENDPOINT}",
)

semantic_equivalence_judge = make_judge(
    name="semantic_equivalence",
    instructions=loaded_prompts.get("semantic_equivalence", (
        "You are a SQL semantics expert. Determine if two SQL queries are measuring "
        "the SAME business metric despite syntactic differences."
    )),
    model=f"databricks:/{LLM_ENDPOINT}",
)

completeness_judge = make_judge(
    name="completeness",
    instructions=loaded_prompts.get("completeness", (
        "You are a SQL completeness expert. Determine if the generated SQL fully "
        "answers the user's question without missing dimensions, measures, or filters."
    )),
    model=f"databricks:/{LLM_ENDPOINT}",
)


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

    arbiter = make_judge(
        name="arbiter",
        instructions=loaded_prompts.get("arbiter", JUDGE_PROMPTS["arbiter"]),
        model=f"databricks:/{LLM_ENDPOINT}",
    )

    context = (
        f"Question: {question}\n"
        f"Ground Truth SQL: {gt_sql}\n"
        f"Genie SQL: {genie_sql}\n"
        f"Result comparison: {json.dumps(cmp)}"
    )
    feedback = arbiter.evaluate(
        request=context,
        response=genie_sql,
        expected_response=gt_sql,
    )

    verdict = _parse_arbiter_verdict(feedback)
    return Feedback(
        name="arbiter", value=verdict,
        rationale=feedback.rationale if hasattr(feedback, "rationale") else str(feedback),
        source=AssessmentSource(source_type="LLM_JUDGE", source_id=f"databricks:/{LLM_ENDPOINT}"),
    )

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

if eval_dataset_uc_name:
    eval_data = eval_dataset_uc_name
    print(f"Using UC Evaluation Dataset: {eval_dataset_uc_name}")
elif dataset_mode == "uc":
    try:
        eval_dataset_name = dbutils.widgets.get("eval_dataset_name")
        eval_data = eval_dataset_name
        print(f"Using UC Evaluation Dataset (from widget): {eval_dataset_name}")
    except Exception:
        print("WARNING: dataset_mode='uc' but eval_dataset_name not set. Falling back to YAML.")
        dataset_mode = "yaml"

if not eval_dataset_uc_name and dataset_mode == "yaml":
    eval_records = []
    for b in benchmarks:
        eval_records.append({
            "inputs": {
                "question": b["question"],
                "space_id": space_id,
                "catalog": catalog,
                "gold_schema": gold_schema,
                "expected_sql": b.get("expected_sql", ""),
            },
            "expectations": {
                "expected_response": b.get("expected_sql", ""),
                "expected_asset": b.get("expected_asset", "TABLE"),
            },
        })
    eval_data = pd.DataFrame(eval_records)
    print(f"Prepared {len(eval_records)} evaluation records from YAML (dataset_mode='yaml').")
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

dbutils.notebook.exit(json.dumps(output, default=str))

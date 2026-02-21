# Databricks notebook source
# MAGIC %md
# MAGIC # GEPA Optimization Notebook
# MAGIC
# MAGIC Runs GEPA (Genie Evolution through Prompt Adaptation) L2 optimization
# MAGIC against a Genie Space, targeting **Lever 6 only** (Genie Instructions +
# MAGIC Example SQLs).
# MAGIC
# MAGIC **Prerequisite:** Levers 1-5 must be exhausted first. This notebook should
# MAGIC only be invoked when introspection-based optimization for UC tables, metric
# MAGIC views, TVFs, etc. has been completed and scores are still below target.
# MAGIC
# MAGIC Required parameters:
# MAGIC - `space_id`: Genie Space ID
# MAGIC - `experiment_name`: MLflow experiment path
# MAGIC - `iteration`: Current optimization iteration
# MAGIC - `domain`: Domain name
# MAGIC - `benchmarks_yaml_path`: Path to golden queries YAML
# MAGIC - `catalog`, `gold_schema`: Unity Catalog references
# MAGIC - `max_rounds`: GEPA optimization rounds (default 3)

# COMMAND ----------

# Cell 1: Configuration
dbutils.widgets.text("space_id", "", "Genie Space ID")
dbutils.widgets.text("experiment_name", "", "MLflow Experiment")
dbutils.widgets.text("iteration", "1", "Iteration")
dbutils.widgets.text("domain", "", "Domain")
dbutils.widgets.text("benchmarks_yaml_path", "", "Benchmarks YAML Path")
dbutils.widgets.text("catalog", "", "Catalog")
dbutils.widgets.text("gold_schema", "", "Gold Schema")
dbutils.widgets.text("max_rounds", "3", "GEPA Max Rounds")
dbutils.widgets.text("model_id", "", "LoggedModel ID")
dbutils.widgets.text("warehouse_id", "", "SQL Warehouse ID")

space_id = dbutils.widgets.get("space_id")
experiment_name = dbutils.widgets.get("experiment_name")
iteration = int(dbutils.widgets.get("iteration"))
domain = dbutils.widgets.get("domain")
benchmarks_yaml_path = dbutils.widgets.get("benchmarks_yaml_path")
catalog = dbutils.widgets.get("catalog")
gold_schema = dbutils.widgets.get("gold_schema")
max_rounds = int(dbutils.widgets.get("max_rounds"))
model_id = dbutils.widgets.get("model_id") or None
warehouse_id = dbutils.widgets.get("warehouse_id") or None

print(f"Space ID: {space_id}")
print(f"Experiment: {experiment_name}")
print(f"Iteration: {iteration}")
print(f"Domain: {domain}")
print(f"Max GEPA rounds: {max_rounds}")
print(f"Target: Lever 6 (Genie Instructions) ONLY")

# COMMAND ----------

# Cell 2: Install dependencies
%pip install "gepa>=0.1.0" "mlflow[databricks]>=3.4.0" "pyyaml>=6.0" "databricks-sdk>=0.40.0"
dbutils.library.restartPython()

# COMMAND ----------

# Cell 3: Imports and MLflow setup
import copy
import json
import time
import yaml
import mlflow

mlflow.set_experiment(experiment_name)

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# COMMAND ----------

# Cell 4: Helper functions (all self-contained)

NON_EXPORTABLE_FIELDS = {
    "id", "title", "description", "creator", "creator_id",
    "updated_by", "updated_at", "created_at", "warehouse_id",
    "execute_as_user_id", "space_status",
}


def strip_non_exportable_fields(config: dict) -> dict:
    """Remove fields from GET response that are invalid in PATCH serialized_space.

    The GET /api/2.0/genie/spaces/{id} response includes top-level metadata
    fields that are NOT part of the GenieSpaceExport protobuf. Including them
    causes: InvalidParameterValue: Cannot find field: <field> in message
    databricks.datarooms.export.GenieSpaceExport
    """
    return {k: v for k, v in config.items() if k not in NON_EXPORTABLE_FIELDS}


def sort_genie_config(config: dict) -> dict:
    """Sort all arrays in Genie config - API rejects unsorted data."""
    if "data_sources" in config:
        for key in ["tables", "metric_views"]:
            if key in config["data_sources"]:
                config["data_sources"][key] = sorted(
                    config["data_sources"][key],
                    key=lambda x: x.get("identifier", ""),
                )
    if "instructions" in config:
        if "sql_functions" in config["instructions"]:
            config["instructions"]["sql_functions"] = sorted(
                config["instructions"]["sql_functions"],
                key=lambda x: (x.get("id", ""), x.get("identifier", "")),
            )
        for key in ["text_instructions", "example_question_sqls"]:
            if key in config["instructions"]:
                config["instructions"][key] = sorted(
                    config["instructions"][key],
                    key=lambda x: x.get("id", ""),
                )
    return config


def fetch_space_config(space_id: str) -> dict:
    """Fetch Genie Space config via API."""
    return w.api_client.do("GET", f"/api/2.0/genie/spaces/{space_id}")


def apply_candidate_to_space(space_id: str, config: dict) -> dict:
    """Apply a modified config to a Genie Space via PATCH API.

    CRITICAL: Strips non-exportable fields before PATCH to avoid
    InvalidParameterValue errors.
    """
    config = strip_non_exportable_fields(config)
    config = sort_genie_config(config)
    payload = {"serialized_space": json.dumps(config)}
    result = w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=payload)
    return result


def build_seed_candidate(config: dict) -> dict:
    """Extract Lever 6 fields from config as the seed candidate for GEPA."""
    instructions = config.get("instructions", {})
    text_instructions = instructions.get("text_instructions", [])
    example_sqls = instructions.get("example_question_sqls", [])
    sql_functions = instructions.get("sql_functions", [])

    return {
        "text_instructions": text_instructions,
        "example_question_sqls": example_sqls,
        "sql_functions": sql_functions,
    }


def apply_seed_to_config(config: dict, seed: dict) -> dict:
    """Apply a GEPA candidate (Lever 6 fields) back to a config copy."""
    config_copy = copy.deepcopy(config)
    instructions = config_copy.setdefault("instructions", {})
    if "text_instructions" in seed:
        instructions["text_instructions"] = seed["text_instructions"]
    if "example_question_sqls" in seed:
        instructions["example_question_sqls"] = seed["example_question_sqls"]
    if "sql_functions" in seed:
        instructions["sql_functions"] = seed["sql_functions"]
    return config_copy


def run_genie_query(space_id: str, question: str, warehouse_id: str = None) -> dict:
    """Send a question to Genie and return the response with generated SQL."""
    create_body = {"space_id": space_id, "content": question}
    if warehouse_id:
        create_body["warehouse_id"] = warehouse_id
    conversation = w.api_client.do(
        "POST", f"/api/2.0/genie/spaces/{space_id}/conversations", body={}
    )
    conv_id = conversation.get("conversation_id", conversation.get("id", ""))
    msg = w.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages",
        body={"content": question},
    )
    msg_id = msg.get("message_id", msg.get("id", ""))

    for _ in range(60):
        time.sleep(2)
        status = w.api_client.do(
            "GET",
            f"/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}",
        )
        s = status.get("status", "")
        if s in ("COMPLETED", "FAILED", "CANCELLED"):
            break

    attachments = status.get("attachments", [])
    generated_sql = ""
    for att in attachments:
        query = att.get("query", {})
        if query.get("query"):
            generated_sql = query["query"]
            break

    return {
        "question": question,
        "generated_sql": generated_sql,
        "status": status.get("status", "UNKNOWN"),
        "message_id": msg_id,
        "conversation_id": conv_id,
    }


def score_genie_response(response: dict, benchmark: dict, catalog: str, gold_schema: str) -> float:
    """Score a Genie response against a benchmark's ground truth SQL.

    Simple scoring: 1.0 if SQL executes and produces matching results, 0.0 otherwise.
    """
    generated_sql = response.get("generated_sql", "")
    gt_sql = benchmark.get("ground_truth_sql", "")

    if not generated_sql or not gt_sql:
        return 0.0

    gt_sql = gt_sql.replace("${catalog}", catalog).replace("${gold_schema}", gold_schema)

    try:
        gen_df = spark.sql(generated_sql).limit(100).toPandas()
        gt_df = spark.sql(gt_sql).limit(100).toPandas()

        if gen_df.shape == gt_df.shape:
            gen_sorted = gen_df.sort_values(by=list(gen_df.columns)).reset_index(drop=True)
            gt_sorted = gt_df.sort_values(by=list(gt_df.columns)).reset_index(drop=True)
            if gen_sorted.equals(gt_sorted):
                return 1.0

        return 0.5 if set(gen_df.columns) == set(gt_df.columns) else 0.0
    except Exception:
        return 0.0

# COMMAND ----------

# Cell 5: Load benchmarks
with open(benchmarks_yaml_path) as f:
    benchmarks_data = yaml.safe_load(f)

benchmarks = benchmarks_data.get("questions", benchmarks_data.get("benchmarks", []))
print(f"Loaded {len(benchmarks)} benchmark questions")

# COMMAND ----------

# Cell 6: Fetch current config and build seed
current_config = fetch_space_config(space_id)
seed_candidate = build_seed_candidate(current_config)
print(f"Seed candidate extracted: {len(seed_candidate.get('text_instructions', []))} instructions, "
      f"{len(seed_candidate.get('example_question_sqls', []))} example SQLs")

# COMMAND ----------

# Cell 7: Define evaluator function for GEPA
def evaluate_genie(candidate_config: dict, benchmarks: list) -> tuple[float, list[dict]]:
    """Evaluate a candidate config against all benchmarks.

    Applies candidate to space, runs each benchmark question, scores results.
    Returns (overall_score, per_question_results).
    """
    apply_candidate_to_space(space_id, candidate_config)
    time.sleep(10)

    results = []
    scores = []
    for bm in benchmarks:
        question = bm.get("question", bm.get("user_question", ""))
        response = run_genie_query(space_id, question, warehouse_id)
        score = score_genie_response(response, bm, catalog, gold_schema)
        scores.append(score)
        results.append({
            "question": question,
            "score": score,
            "generated_sql": response.get("generated_sql", ""),
            "status": response.get("status", ""),
        })

    overall = sum(scores) / max(len(scores), 1)
    return overall, results

# COMMAND ----------

# Cell 8: Run GEPA optimization
try:
    from gepa import optimize_anything, GEPAConfig, EngineConfig, ReflectionConfig

    gepa_config = GEPAConfig(
        engine=EngineConfig(
            max_metric_calls=150,
            cache_evaluation=True,
        ),
        reflection=ReflectionConfig(
            reflection_lm="databricks:/databricks-claude-sonnet-4-6",
        ),
    )

    def gepa_metric_fn(candidate: dict) -> float:
        """GEPA metric function: apply candidate to config, evaluate, return score."""
        config_with_candidate = apply_seed_to_config(current_config, candidate)
        score, _ = evaluate_genie(config_with_candidate, benchmarks)
        return score

    run_name = f"gepa_optimization_iter{iteration}_{int(time.time())}"
    with mlflow.start_run(run_name=run_name) as run:
        if model_id:
            mlflow.log_param("model_id", model_id)
        mlflow.log_param("space_id", space_id)
        mlflow.log_param("iteration", iteration)
        mlflow.log_param("max_rounds", max_rounds)
        mlflow.log_param("lever", 6)
        mlflow.log_param("tier", "gepa_l2")
        mlflow.log_param("num_benchmarks", len(benchmarks))

        result = optimize_anything(
            seed=seed_candidate,
            metric=gepa_metric_fn,
            config=gepa_config,
        )

        best_candidate = result.best_candidate
        best_score = result.best_score

        mlflow.log_metric("best_score", best_score)
        mlflow.log_metric("total_metric_calls", result.total_metric_calls)
        mlflow.log_dict(best_candidate, "best_candidate.json")

        best_config = apply_seed_to_config(current_config, best_candidate)
        apply_candidate_to_space(space_id, best_config)

        print(f"\nGEPA optimization complete:")
        print(f"  Best score: {best_score:.2%}")
        print(f"  Total metric calls: {result.total_metric_calls}")
        print(f"  Applied best candidate to space {space_id}")

        output = {
            "best_score": best_score,
            "total_metric_calls": result.total_metric_calls,
            "run_id": run.info.run_id,
            "model_id": model_id,
            "lever": 6,
            "tier": "gepa_l2",
        }

except ImportError as e:
    print(f"ERROR: gepa package not installed: {e}")
    print("Install via: pip install 'gepa>=0.1.0'")
    print("Or add to cluster libraries in Databricks workspace.")
    output = {"error": str(e), "status": "gepa_not_installed"}

# COMMAND ----------

# Cell 9: Return results
import json
dbutils.notebook.exit(json.dumps(output))

# Judge Definitions & Evaluation Orchestration

This reference documents all judge implementations, the predict function, threshold checking, and evaluation orchestration for the Genie Benchmark Evaluator.

---

## 3-Layer Architecture (All 8 Scorers in `mlflow.genai.evaluate()`)

SQL execution is lifted into `genie_predict_fn` so no scorer calls `spark.sql()`. Both `result_correctness` and `arbiter_scorer` read the pre-computed `outputs["comparison"]` dict.

```
genie_predict_fn (runs ONCE per row)
├── Call Genie API
├── spark.sql(gt_sql)      ← only SQL execution point
├── spark.sql(genie_sql)   ← only SQL execution point
├── Compare DataFrames
└── Return {response, comparison}

All 8 Scorers (read outputs, NO SQL execution)
├── Layer 1 — Quality Judges (always run)
│   ├── syntax_validity       (code: EXPLAIN)
│   ├── schema_accuracy       (LLM judge)
│   ├── logical_accuracy      (LLM judge)
│   ├── semantic_equivalence  (LLM judge)
│   ├── completeness          (LLM judge)
│   └── asset_routing         (code: prefix match)
├── Layer 2 — Result Comparison (reads comparison)
│   └── result_correctness    (code: reads outputs["comparison"])
└── Layer 3 — Arbiter (conditional scorer, reads comparison)
    └── arbiter_scorer        (LLM: fires only when results disagree)
        ├── "skipped"            → results match, no LLM call
        ├── "genie_correct"      → auto-update benchmark
        ├── "ground_truth_correct" → optimize metadata
        ├── "both_correct"       → add disambiguation instruction
        └── "neither_correct"    → flag for human review
```

The arbiter runs inside `mlflow.genai.evaluate()` as the 8th scorer. Its verdicts appear in the Judges tab, Traces, and Evaluation Runs. It returns `value="skipped"` when results match (zero LLM cost for passing rows).

---

## Predict Function

The predict function executes both SQLs and stores comparison data. This runs once per row before any scorer, so `result_correctness` and `arbiter_scorer` read pre-computed results with zero redundant SQL execution.

```python
import mlflow
import time
import hashlib

@mlflow.trace
def genie_predict_fn(inputs: dict) -> dict:
    """MLflow predict function: query Genie, execute both SQLs, return response + comparison.

    SQL execution is lifted here so every scorer reads pre-computed results.
    Neither result_correctness nor arbiter_scorer calls spark.sql().
    Respects 12s rate limit between Genie API calls.
    """
    space_id = inputs["space_id"]
    question = inputs["question"]
    expected_sql = inputs.get("expected_sql", "")

    time.sleep(12)
    result = run_genie_query(space_id, question)
    genie_sql = sanitize_sql(result.get("sql") or "")
    gt_sql = resolve_sql(expected_sql)

    comparison = {"match": False, "match_type": "mismatch", "gt_rows": 0,
                  "genie_rows": 0, "gt_hash": None, "genie_hash": None, "error": None}
    if genie_sql and gt_sql:
        try:
            gt_df = spark.sql(gt_sql).toPandas()
            genie_df = spark.sql(genie_sql).toPandas()
            gt_hash = hashlib.md5(gt_df.to_csv(index=False).encode()).hexdigest()[:8]
            genie_hash = hashlib.md5(genie_df.to_csv(index=False).encode()).hexdigest()[:8]
            exact_match = gt_df.shape == genie_df.shape and gt_df.equals(genie_df)
            hash_match = gt_hash == genie_hash
            comparison = {
                "match": exact_match or hash_match,
                "match_type": "exact" if exact_match else ("hash" if hash_match else "mismatch"),
                "gt_rows": len(gt_df),
                "genie_rows": len(genie_df),
                "gt_hash": gt_hash,
                "genie_hash": genie_hash,
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
```

**Important:** `expected_sql` must be included in the `inputs` dict when building evaluation records, so the predict function can resolve and execute the ground truth SQL.

---

## run_genie_query

```python
import time
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

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
            poll_interval = min(poll_interval + 1, 10)

        sql = None
        if msg and hasattr(msg, "attachments") and msg.attachments:
            for att in msg.attachments:
                if hasattr(att, "query") and att.query:
                    sql = att.query.query if hasattr(att.query, "query") else str(att.query)

        return {
            "status": status,
            "sql": sql,
            "conversation_id": conversation_id,
            "message_id": message_id,
        }
    except Exception as e:
        return {"status": "ERROR", "sql": None, "error": str(e)}
```

---

## Response Extraction Helper (MANDATORY)

Adopted from `mlflow-genai-evaluation` skill. `mlflow.genai.evaluate()` serializes responses to dicts before passing to scorers. Without this helper, scorers receive raw dicts and silently return wrong values.

```python
from typing import Union, Any

def _extract_response_text(outputs: Union[dict, Any]) -> str:
    """Extract response text from mlflow.genai.evaluate() serialized format.

    Handles: dict with 'response' key (Genie predict_fn format),
    dict with 'output' list (ResponsesAgent format), or raw string.
    """
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
```

---

## LLM Call Helper for Scorers

Use Databricks SDK (NOT `langchain_databricks`) for LLM calls in custom scorers. Adopted from `mlflow-genai-evaluation` skill — prevents serverless deployment failures and auth issues.

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import json

def _call_llm_for_scoring(prompt: str, endpoint: str = "databricks-claude-sonnet-4-6") -> dict:
    """Call LLM using Databricks SDK for scorer evaluation.

    Returns parsed JSON with 'score' and 'rationale' keys.
    Uses temperature=0 for deterministic judge consistency.
    """
    w = WorkspaceClient()
    response = w.serving_endpoints.query(
        name=endpoint,
        messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)
```

---

## Threshold Checking

Check evaluation metrics against deployment targets. Handles metric name variations across MLflow versions.

```python
GENIE_THRESHOLDS = {
    "syntax_validity/mean": 0.98,
    "schema_accuracy/mean": 0.95,
    "logical_accuracy/mean": 0.90,
    "semantic_equivalence/mean": 0.90,
    "completeness/mean": 0.90,
    "result_correctness/mean": 0.85,
    "asset_routing/mean": 0.95,
}

def check_genie_thresholds(metrics: dict, thresholds: dict = None) -> bool:
    """Check if evaluation metrics meet Genie optimization targets.

    Returns True if all thresholds met. Prints per-metric pass/fail.
    """
    thresholds = thresholds or GENIE_THRESHOLDS
    all_pass = True
    for metric_name, threshold in thresholds.items():
        value = metrics.get(metric_name)
        if value is None:
            print(f"  [SKIP] {metric_name} — not found in metrics")
            continue
        if value >= threshold:
            print(f"  [PASS] {metric_name}: {value:.3f} >= {threshold}")
        else:
            print(f"  [FAIL] {metric_name}: {value:.3f} < {threshold}")
            all_pass = False
    return all_pass
```

---

## SQL Preprocessing Helpers (MANDATORY)

Apply these helpers to ALL SQL before execution. Genie can return multi-statement SQL (compound questions) and ground truth SQL uses `${catalog}` / `${gold_schema}` template variables from `golden-queries.yaml`.

```python
def resolve_sql(sql: str, catalog: str, gold_schema: str) -> str:
    """Substitute ${catalog} and ${gold_schema} template variables.

    Ground truth SQL in golden-queries.yaml uses template variables that must
    be resolved before spark.sql() or EXPLAIN. Without this, Spark throws
    PARSE_SYNTAX_ERROR: Syntax error at or near '$'.
    """
    if not sql:
        return sql
    return sql.replace("${catalog}", catalog).replace("${gold_schema}", gold_schema)


def sanitize_sql(sql: str) -> str:
    """Extract the first SQL statement, strip comments and trailing semicolons.

    Genie may return multi-statement SQL for compound questions (e.g., "Top
    customers and revenue summary" → two SELECT statements separated by ';').
    EXPLAIN and spark.sql() cannot handle multi-statement input.
    """
    if not sql:
        return sql
    sql = sql.strip().rstrip(";").strip()
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if not statements:
        return sql
    first = statements[0]
    lines = [l for l in first.split("\n") if not l.strip().startswith("--")]
    return "\n".join(lines).strip()
```

**Usage in scorers:**
- `sanitize_sql()` → apply to all Genie-returned SQL before EXPLAIN or spark.sql()
- `resolve_sql()` → apply to all ground truth SQL before spark.sql()
- Order: `sanitize_sql()` first (Genie SQL), then `resolve_sql()` (GT SQL)

---

## Judge Suite

All judges organized into the 3-layer architecture. LLM judges load prompts from the Prompt Registry via alias.

**IMPORTANT:** Do NOT stack `@mlflow.trace` on `@scorer`. The `mlflow.genai.evaluate()` harness traces scorer execution automatically. Stacking `@mlflow.trace` wraps the scorer in a generic wrapper that strips `.register()`, leaving the Judges tab empty. Keep `@mlflow.trace` only on the predict function.

```python
import mlflow
from mlflow.genai.judges import make_judge
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback, AssessmentSource

CODE_SOURCE = AssessmentSource(source_type="CODE", source_id="genie-optimizer-v2")
LLM_SOURCE = AssessmentSource(
    source_type="LLM_JUDGE",
    source_id="databricks:/databricks-claude-sonnet-4-6",
)


def create_judge_suite(uc_schema: str = None, alias: str = "production") -> dict:
    """Create all judges organized by layer.

    Args:
        uc_schema: Unity Catalog schema for Prompt Registry. If None, uses inline prompts.
        alias: Prompt alias to load ("production" or "staging").

    Returns:
        dict with keys: layer1, layer2, layer3_fn
    """
    prompts = load_judge_prompts(uc_schema, alias) if uc_schema else {}

    schema_accuracy_judge = make_judge(
        name="schema_accuracy",
        instructions=prompts.get("schema_accuracy", (
            "You are a SQL schema expert. Determine if the generated SQL references "
            "the correct tables, columns, and joins for the given question. Consider "
            "the expected tables and columns in the expectations."
        )),
        model="databricks:/databricks-claude-sonnet-4-6",
    )

    logical_accuracy_judge = make_judge(
        name="logical_accuracy",
        instructions=prompts.get("logical_accuracy", (
            "You are a SQL logic expert. Determine if the generated SQL applies correct "
            "aggregations, filters, GROUP BY, ORDER BY, and WHERE clauses for the question. "
            "Compare against the expected SQL logic."
        )),
        model="databricks:/databricks-claude-sonnet-4-6",
    )

    semantic_equivalence_judge = make_judge(
        name="semantic_equivalence",
        instructions=prompts.get("semantic_equivalence", (
            "You are a SQL semantics expert. Determine if two SQL queries are measuring "
            "the SAME business metric despite syntactic differences. Two queries are "
            "semantically equivalent if they would answer the same business question "
            "with the same result, even if written differently. Consider column aliases, "
            "join order, filter phrasing, and aggregation approach."
        )),
        model="databricks:/databricks-claude-sonnet-4-6",
    )

    completeness_judge = make_judge(
        name="completeness",
        instructions=prompts.get("completeness", (
            "You are a SQL completeness expert. Determine if the generated SQL fully "
            "answers the user's question. Check that all requested dimensions, measures, "
            "filters, and sorting are present. A partial answer is not complete."
        )),
        model="databricks:/databricks-claude-sonnet-4-6",
    )

    return {
        "layer1": [
            syntax_validity_scorer,
            schema_accuracy_judge,
            logical_accuracy_judge,
            semantic_equivalence_judge,
            completeness_judge,
            asset_routing_scorer,
        ],
        "layer2": [result_correctness],
        "layer3": [arbiter_scorer],
    }


def get_all_scorers(judge_suite: dict) -> list:
    """Flatten judge suite into a single list for mlflow.genai.evaluate(scorers=...)."""
    return judge_suite["layer1"] + judge_suite["layer2"] + judge_suite["layer3"]


@scorer
def syntax_validity_scorer(inputs: dict, outputs: dict) -> Feedback:
    """Layer 1: Check SQL syntax by running EXPLAIN."""
    sql = sanitize_sql(_extract_response_text(outputs))
    if not sql or not sql.strip():
        return Feedback(
            name="syntax_validity",
            value="no",
            rationale="No SQL generated.",
            source=CODE_SOURCE,
        )
    try:
        spark.sql(f"EXPLAIN {sql}")
        return Feedback(
            name="syntax_validity",
            value="yes",
            rationale="SQL parses successfully via EXPLAIN.",
            source=CODE_SOURCE,
        )
    except Exception as e:
        return Feedback(
            name="syntax_validity",
            value="no",
            rationale=f"EXPLAIN failed: {str(e)[:200]}",
            source=CODE_SOURCE,
        )


@scorer
def asset_routing_scorer(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """Layer 1: Check if Genie selected the correct asset type."""
    sql = (_extract_response_text(outputs) or "").lower()
    expected_asset = expectations.get("expected_asset", "").upper()

    uses_mv = "mv_" in sql or "measure(" in sql
    uses_tvf = "get_" in sql
    actual_asset = "MV" if uses_mv else ("TVF" if uses_tvf else "TABLE")

    correct = actual_asset == expected_asset
    return Feedback(
        name="asset_routing",
        value="yes" if correct else "no",
        rationale=f"Expected {expected_asset}, got {actual_asset}. SQL: {sql[:100]}",
        source=CODE_SOURCE,
    )


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
                        rationale=f"Comparison error: {cmp['error']}", source=CODE_SOURCE)
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
        source=CODE_SOURCE)


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
        model="databricks:/databricks-claude-sonnet-4-6",
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
        source=AssessmentSource(source_type="LLM_JUDGE",
                                source_id="databricks:/databricks-claude-sonnet-4-6"),
    )
```

---

## Judge Registration Lifecycle (REQUIRED for Judges Tab)

After creating judges with `make_judge()` / `@scorer`, call `.register(name=...)` on each to make them visible in the MLflow Judges tab. Without registration, the Judges tab shows "Add a judge to your experiment" with zero scorers — even if evaluation runs 8 judges across all benchmarks.

**CRITICAL:** Do NOT stack `@mlflow.trace` on `@scorer`. This wraps the scorer in a generic trace wrapper that strips the `.register()` method, causing silent failures in the registration loop.

The three-step scorer lifecycle:

1. **Create** — `make_judge()` or `@scorer` defines the judge (NO `@mlflow.trace`)
2. **Register** — `.register(name=...)` makes the experiment aware of it (Judges tab). Use `try/except` with explicit error logging, NOT silent catch.
3. **Start** (optional) — `.start(sampling_config=...)` enables continuous monitoring on future traces

```python
from mlflow.genai.scorers import ScorerSamplingConfig

def register_judges_to_experiment(judge_suite: dict) -> dict:
    """Register all judges to the current MLflow experiment for UI visibility.

    Call AFTER mlflow.set_experiment() and BEFORE mlflow.genai.evaluate().
    Returns dict of {name: registered_scorer} for lifecycle management.

    Without this call:
    - Judges tab is empty
    - Cannot use backfill_scorers() for historical traces
    - Cannot enable production monitoring
    - Cannot share judge definitions across experiments
    """
    registered = {}
    for scorer_obj in get_all_scorers(judge_suite):
        name = getattr(scorer_obj, "name", getattr(scorer_obj, "__name__", str(scorer_obj)))
        reg = scorer_obj.register(name=name)
        registered[name] = reg
    return registered
```

Optionally enable continuous monitoring on registered judges:

```python
def start_continuous_monitoring(registered_judges: dict, sample_rate: float = 1.0):
    """Enable continuous monitoring for all registered judges."""
    for name, reg_scorer in registered_judges.items():
        reg_scorer.start(
            sampling_config=ScorerSamplingConfig(sample_rate=sample_rate)
        )
        print(f"  [Monitor] Started {name} (sample_rate={sample_rate})")
```

---

## Evaluation Orchestration

Uses `mlflow.genai.evaluate()` (NOT `mlflow.evaluate()`) so results appear in the MLflow Evaluation tab with per-row judge feedback. Follows run-naming convention from `mlflow-genai-evaluation` skill for programmatic querying.

```python
import mlflow
from datetime import datetime

def run_mlflow_evaluation(dataset_name: str, space_id: str,
                          experiment_name: str, judge_suite: dict,
                          iteration: int = 1,
                          model_id: str = None) -> dict:
    """Run a full MLflow evaluation with the 3-layer judge suite.

    Uses mlflow.genai.evaluate() to ensure results display in the
    MLflow Evaluation tab with per-row feedback and trace lineage.
    When model_id is provided, evaluation results are linked to the
    specific Genie Space config version in the MLflow Versions tab.

    Args:
        dataset_name: MLflow Evaluation Dataset name in UC.
        space_id: Genie Space ID (injected into predict fn).
        experiment_name: MLflow experiment name.
        judge_suite: Output from create_judge_suite().
        iteration: Current optimization iteration number.
        model_id: Optional LoggedModel ID from create_genie_model_version().

    Returns:
        dict with eval_result, run_id, per-judge metrics, thresholds_passed.
    """
    mlflow.set_experiment(experiment_name)

    def predict_fn(inputs):
        inputs["space_id"] = space_id
        return genie_predict_fn(inputs)

    all_scorers = get_all_scorers(judge_suite)
    run_name = f"genie_eval_iter{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params({
            "space_id": space_id,
            "iteration": iteration,
            "dataset": dataset_name,
            "num_scorers": len(all_scorers),
            "scorer_names": ",".join(s.__name__ if hasattr(s, '__name__') else str(s) for s in all_scorers),
        })

        evaluate_kwargs = {
            "predict_fn": predict_fn,
            "data": dataset_name,
            "scorers": all_scorers,
        }
        if model_id:
            evaluate_kwargs["model_id"] = model_id

        eval_result = mlflow.genai.evaluate(**evaluate_kwargs)

        thresholds_passed = check_genie_thresholds(eval_result.metrics)
        mlflow.log_metric("thresholds_passed", 1.0 if thresholds_passed else 0.0)

        run_url = f"{mlflow.get_tracking_uri()}/#mlflow/experiments/{run.info.experiment_id}/runs/{run.info.run_id}"
        print(f"\nMLflow Run:   {run_name}")
        print(f"MLflow URL:   {run_url}")
        print(f"Thresholds:   {'ALL PASSED' if thresholds_passed else 'SOME FAILED'}")

        return {
            "eval_result": eval_result,
            "run_id": run.info.run_id,
            "run_name": run_name,
            "metrics": eval_result.metrics,
            "thresholds_passed": thresholds_passed,
        }


def query_latest_evaluation(experiment_name: str, iteration: int = None) -> dict:
    """Query the latest evaluation run for threshold checking and CI/CD gates.

    Args:
        experiment_name: MLflow experiment path.
        iteration: Optional iteration to filter by.

    Returns:
        dict with run_id, metrics, thresholds_passed.
    """
    filter_str = "tags.mlflow.runName LIKE 'genie_eval_%'"
    if iteration is not None:
        filter_str = f"tags.mlflow.runName LIKE 'genie_eval_iter{iteration}_%'"

    runs = mlflow.search_runs(
        experiment_names=[experiment_name],
        filter_string=filter_str,
        order_by=["start_time DESC"],
        max_results=1,
    )
    if runs.empty:
        return None
    row = runs.iloc[0]
    return {
        "run_id": row["run_id"],
        "metrics": {k.replace("metrics.", ""): v for k, v in row.items() if k.startswith("metrics.")},
        "thresholds_passed": row.get("metrics.thresholds_passed", 0.0) == 1.0,
    }
```

---

## Job-Based Evaluation

When running evaluation as a Databricks Job instead of inline, the agent uses these functions to trigger, poll, and read results.

### Triggering the Job

```python
def trigger_evaluation_job(
    space_id: str,
    experiment_name: str,
    iteration: int,
    benchmarks_path: str,
    domain: str,
    target: str = "dev",
    job_name: str = "genie_evaluation_job",
) -> dict:
    """Trigger genie_evaluation_job via 'databricks bundle run'.

    Override the iteration parameter at runtime so the same job definition
    supports multiple optimization cycles.

    Returns:
        {"status": "TRIGGERED", "run_id": "12345", "run_url": "https://..."}
    """
    import subprocess, re

    cmd = [
        "databricks", "bundle", "run", "-t", target, job_name,
        "--params", f"iteration={iteration}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"status": "TRIGGER_FAILED", "error": result.stderr, "run_id": None}

    run_id = re.search(r"run_id[:\s]+(\d+)", result.stdout)
    return {
        "status": "TRIGGERED",
        "run_id": run_id.group(1) if run_id else None,
        "stdout": result.stdout,
    }
```

### Polling Job Completion

```python
def poll_job_completion(run_id: str, poll_interval: int = 30, max_wait: int = 3600) -> dict:
    """Poll a Databricks job run until TERMINATED, INTERNAL_ERROR, or timeout.

    Reads notebook output from the first task if available.

    Returns:
        {
          "life_cycle_state": "TERMINATED",
          "result_state": "SUCCESS",
          "notebook_output": '{"run_id":"...","overall_accuracy":0.85,...}'
        }
    """
    import subprocess
    start = time.time()
    while time.time() - start < max_wait:
        cmd = ["databricks", "jobs", "get-run", str(run_id), "--output", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        run_data = json.loads(result.stdout)
        state = run_data.get("state", {})
        lifecycle = state.get("life_cycle_state", "UNKNOWN")

        if lifecycle == "TERMINATED":
            # Read notebook output from task
            tasks = run_data.get("tasks", [])
            notebook_output = None
            if tasks:
                task_run_id = tasks[0].get("run_id")
                out_cmd = ["databricks", "jobs", "get-run-output", str(task_run_id), "--output", "json"]
                out_result = subprocess.run(out_cmd, capture_output=True, text=True)
                if out_result.returncode == 0:
                    notebook_output = json.loads(out_result.stdout).get("notebook_output", {}).get("result")

            return {
                "life_cycle_state": lifecycle,
                "result_state": state.get("result_state", ""),
                "notebook_output": notebook_output,
            }

        time.sleep(poll_interval)

    return {"life_cycle_state": "TIMEOUT", "result_state": "Exceeded max_wait", "notebook_output": None}
```

### End-to-End: Trigger → Poll → Read MLflow

```python
def run_evaluation_via_job(space_id, experiment_name, iteration, benchmarks_path, domain, target="dev", model_id=None):
    """Trigger job, poll completion, parse output or fall back to mlflow.search_runs().
    When model_id is provided, it is forwarded as a job parameter so the notebook
    can pass it to mlflow.genai.evaluate(model_id=...) for version tracking."""
    trigger = trigger_evaluation_job(space_id, experiment_name, iteration, benchmarks_path, domain, target)
    if trigger["status"] != "TRIGGERED":
        return {"iteration": iteration, "overall_accuracy": 0, "failures": [], "job_error": trigger["error"]}

    completion = poll_job_completion(trigger["run_id"])
    if completion["result_state"] != "SUCCESS":
        return {"iteration": iteration, "overall_accuracy": 0, "failures": [], "job_error": completion["result_state"]}

    # Primary: parse notebook exit output
    job_result = json.loads(completion["notebook_output"]) if completion.get("notebook_output") else {}

    # Fallback: query MLflow directly
    if not job_result:
        latest = query_latest_evaluation(experiment_name, iteration)
        if latest:
            job_result = {
                "run_id": latest["run_id"],
                "overall_accuracy": latest["metrics"].get("overall_accuracy", 0),
                "thresholds_passed": latest["thresholds_passed"],
            }

    return {
        "iteration": iteration,
        "mlflow_run_id": job_result.get("run_id"),
        "overall_accuracy": job_result.get("overall_accuracy", 0) * 100,
        "failures": job_result.get("failure_question_ids", []),
        "scores": job_result.get("per_judge", {}),
    }
```

---

## Asset Routing Decision Matrix

TVF vs Metric View decision matrix for the `asset_routing_scorer`:

| Query Type | Preferred Asset | Reason |
|------------|-----------------|--------|
| **Aggregations** (total, average) | Metric View | Pre-optimized for MEASURE() |
| **Lists** (show me, which, top N) | TVF | Parameterized, returns rows |
| **Time-series with params** | TVF | Date range parameters |
| **Dashboard KPIs** | Metric View | Single-value aggregations |
| **Detail drilldowns** | TVF | Full row data |

---

## Judge Prompt Templates (JUDGE_PROMPTS)

Default prompt templates for each LLM judge. These are registered to the MLflow Prompt Registry and loaded by alias at evaluation time.

**IMPORTANT:** All templates use `{{double_brace}}` syntax (`{{variable}}`), NOT Python `{single_brace}` format strings. The MLflow Prompt Registry requires this for its `.format()` method. Using `{single_brace}` will cause `KeyError` when calling `prompt_obj.format(...)`.

```python
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
```

## Prompt Registration Lifecycle

Judge prompts follow a register-once, load-every-iteration pattern with dual storage for maximum visibility:

**Iteration 1 — Registration (dual storage):**

1. **MLflow Prompt Registry** (versioned, aliased) — enables programmatic loading by alias and A/B testing of prompt changes across iterations
2. **MLflow Experiment Artifacts** — visible in the Artifacts tab for quick inspection

```python
def register_judge_prompts(uc_schema, domain, experiment_name):
    """Register all judge prompts to Prompt Registry + experiment artifacts.
    Only call on iteration 1. Subsequent iterations load by alias."""
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
                    name=prompt_name, alias="production", version=version.version,
                )
                registered[name] = {"prompt_name": prompt_name, "version": version.version}
            except Exception as e:
                print(f"  [Prompt Registry] Skipped {prompt_name}: {e}")

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=f"register_prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        for name, template in JUDGE_PROMPTS.items():
            tmp = os.path.join(tempfile.gettempdir(), f"genie_opt_{name}.txt")
            with open(tmp, "w") as f:
                f.write(template)
            mlflow.log_artifact(tmp, artifact_path=f"judge_prompts/{name}")
            os.unlink(tmp)
        mlflow.log_params({"num_prompts": len(JUDGE_PROMPTS), "domain": domain})
    return registered
```

**Every iteration — Loading (MANDATORY):**

`load_judge_prompts()` loads the `@production` alias from the Prompt Registry. Falls back to inline `JUDGE_PROMPTS` if the registry is unavailable. This function is **mandatory** — do NOT skip it and use inline strings directly.

```python
def load_judge_prompts(uc_schema: str, alias: str = "production") -> dict:
    """Load all judge prompts from MLflow Prompt Registry by alias.
    Falls back to inline JUDGE_PROMPTS if registry is unavailable.
    MANDATORY: Must be called before creating judges."""
    prompts = {}
    for name in JUDGE_PROMPTS:
        if uc_schema:
            prompt_name = f"{uc_schema}.genie_opt_{name}"
            try:
                prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@{alias}")
                prompts[name] = prompt.template
                continue
            except Exception:
                pass
        prompts[name] = JUDGE_PROMPTS[name]
    return prompts
```

**Experiment tagging:** After setup, tag the experiment so the Prompts tab links to the registry:

```python
if uc_schema:
    mlflow.set_experiment_tags({"mlflow.promptRegistryLocation": uc_schema})
```

**Iteration 2+ — Prompt evolution:** When judge prompts need refinement based on evaluation feedback:

```
register_prompt() creates v2, alias @staging
  -> Compare v1 vs v2 results in Evaluation tab
  -> If v2 is better: set_prompt_alias(@production, v2)
  -> If v2 is worse: keep @production pointing to v1
load_prompt(@production) always gets the best version
```

---

## TVF-First Design: Repeatability Learnings

**Production Results:**
- Quality domain: 100% repeatability (TVF-first routing)
- Reliability domain: 80% repeatability (mixed routing)
- Security domain: 67% repeatability (MV-heavy routing)

**Why TVFs Improve Repeatability:**
1. **Function signature constrains output** — Less room for LLM variation
2. **Parameterized queries** — Consistent parameter handling
3. **Encapsulated logic** — LLM doesn't need to construct complex SQL

**Why MVs Have Higher Variance:**
1. **LLM makes column choices** — Different GROUP BY columns across runs
2. **MEASURE() syntax variations** — LLM constructs different measure expressions
3. **Dimension selection** — LLM picks different dimensions for grouping

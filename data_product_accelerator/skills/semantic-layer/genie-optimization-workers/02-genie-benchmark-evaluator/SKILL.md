---
name: genie-benchmark-evaluator
description: >
  Evaluates Genie Space responses against benchmarks using 8 scorers in
  mlflow.genai.evaluate(). Layer 1: quality judges (syntax, schema, logic,
  semantics, completeness, routing). Layer 2: result correctness. Layer 3:
  conditional arbiter (fires only on disagreement). SQL execution is lifted
  into genie_predict_fn for zero-redundancy — no scorer calls spark.sql().
  Supports job-based and inline evaluation modes.
metadata:
  author: prashanth subrahmanyam
  version: "4.1.0"
  domain: semantic-layer
  role: worker
  called_by:
    - genie-optimization-orchestrator
  standalone: true
  common_dependencies:
    - mlflow-genai-evaluation
    - prompt-registry-patterns
---

# Genie Benchmark Evaluator

Evaluates Genie Space responses using a multi-dimensional 3-layer judge architecture with MLflow tracking. Supports both Databricks Job and inline evaluation modes.

## When to Use This Skill

- Scoring Genie Space accuracy against benchmark questions
- Comparing evaluation results across optimization iterations
- Running post-deploy verification after bundle deployment
- Testing repeatability of Genie SQL generation

### Inputs (from Orchestrator)

| Input | Type | Description |
|-------|------|-------------|
| `space_id` | str | Genie Space ID to evaluate |
| `eval_dataset_name` | str | MLflow Evaluation Dataset name |
| `experiment_name` | str | MLflow experiment path |
| `iteration` | int | Current optimization iteration |
| `model_id` | str \| None | LoggedModel ID for version tracking — links evaluation results to a specific Genie Space config version in the MLflow Versions tab (optional) |
| `uc_schema` | str \| None | Unity Catalog schema for Prompt Registry (e.g., `catalog.schema`). Enables versioned judge prompts and populates the Prompts tab. |
| `eval_scope` | str | Evaluation scope: `full` (default), `slice`, `p0`, `held_out`. Controls which benchmarks are evaluated. |
| `patched_objects` | list[str] | Metadata objects modified by patches (for `eval_scope="slice"` filtering). |

### DABs Bundle Root Path Resolution

When deployed via Databricks Asset Bundles, the notebook runs from the bundle root (e.g., `/Workspace/Users/<email>/bundle/<project>/dev/files/`), not `/Workspace/`. All file paths (`golden-queries.yaml`, genie configs, MV YAML definitions) must be resolved relative to `_bundle_root`.

The template derives `_bundle_root` from `dbutils.notebook.entry_point`:
- Split notebook path at `/src/` to find bundle root
- Add bundle root to `sys.path` for imports
- Resolve all file paths as `os.path.join(_bundle_root, relative_path)`

If the notebook runs outside a bundle context (e.g., local testing), the path setup is skipped gracefully.

### Outputs (to Orchestrator)

| Output | Type | Description |
|--------|------|-------------|
| `eval_results` | dict | Per-question evaluation results |
| `scores` | dict | Per-judge aggregate scores |
| `judge_feedback` | list | Judge rationales for each question |
| `arbiter_verdicts` | list | Arbiter decisions (Layer 2 disagreements only) |

## 3-Layer Judge Architecture (All 8 Scorers in `mlflow.genai.evaluate()`)

SQL execution is lifted into `genie_predict_fn` — no scorer calls `spark.sql()`. Both `result_correctness` and `arbiter_scorer` read the pre-computed `outputs["comparison"]` dict.

```
genie_predict_fn (runs ONCE per row — only SQL execution point)
├── Call Genie API → genie_sql
├── spark.sql(gt_sql)  + spark.sql(genie_sql)
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
└── Layer 3 — Arbiter (conditional @scorer)
    └── arbiter_scorer        (LLM: fires only when results disagree)
        ├── "skipped"              → results match, no LLM call
        ├── "genie_correct"        → auto-update benchmark
        ├── "ground_truth_correct" → optimize metadata
        ├── "both_correct"         → add disambiguation instruction
        └── "neither_correct"      → flag for human review
```

**Load:** Read [judge-definitions.md](references/judge-definitions.md) for all 8 judge implementations, thresholds, and the predict function.

**Load:** Read [result-comparison.md](references/result-comparison.md) for DataFrame comparison patterns (exact, approximate, structural).

**Load:** Read [arbiter-workflow.md](references/arbiter-workflow.md) for arbiter invocation rules and benchmark auto-correction.

## Actionable Side Information (ASI) (P4)

Every judge's `Feedback.metadata` includes structured ASI fields that enable the Optimizer to propose targeted patch sets. The `FAILURE_TAXONOMY` and `ASI_SCHEMA` constants are defined in the evaluation template.

**FAILURE_TAXONOMY:** wrong_table, wrong_column, wrong_join, missing_filter, missing_temporal_filter, wrong_aggregation, wrong_measure, missing_instruction, ambiguous_question, asset_routing_error, tvf_parameter_error, compliance_violation, performance_issue, repeatability_issue, missing_synonym, description_mismatch, other.

**ASI_SCHEMA fields:** failure_type, severity, confidence, wrong_clause, blame_set, quoted_metadata_text, missing_metadata, ambiguity_detected, expected_value, actual_value, counterfactual_fix, affected_question_pattern.

### Per-Judge Metric Logging (Data Contract)

The evaluator MUST log `eval_{judge}_pct` as MLflow run metrics for: `result_correctness`, `asset_routing`, `syntax_validity`, `schema_accuracy`, `semantic_equivalence`, `completeness`, `logical_accuracy`. These MUST be accessible via `mlflow.get_run(run_id).data.metrics`. Values are in 0-100 scale (percentage). This enables the orchestrator to read per-judge scores without downloading and parsing evaluation artifacts.

Use `build_asi_metadata()` helper to construct ASI metadata dicts for `Feedback(metadata=...)`.

### ASI Serialization & UC Table Contract (Cross-Skill Data Transport)

`Feedback.metadata` appears as `{judge}/metadata` columns in `eval_result.tables["eval_results"]`, but the `assessments` list (which contains the full metadata object) is NOT reliably available in the DataFrame. This serialization boundary caused silent data loss -- the optimizer read column names that didn't exist.

**Canonical storage:** The `genie_eval_asi_results` UC Delta table is the primary ASI transport mechanism. The evaluator writes one row per (question, judge) pair after every evaluation. The optimizer reads from this table as its primary source via `read_asi_from_uc()`.

**Table schema:**

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | STRING | MLflow run ID |
| `iteration` | INT | Optimization iteration number |
| `question_id` | STRING | Benchmark question ID |
| `judge` | STRING | Judge name (e.g., `schema_accuracy`) |
| `value` | STRING | Judge verdict (`yes`/`no`/`skipped`) |
| `failure_type` | STRING | From FAILURE_TAXONOMY |
| `severity` | STRING | `critical`/`major`/`minor`/`info` |
| `confidence` | DOUBLE | 0.0 to 1.0 |
| `blame_set` | STRING | JSON array of blamed objects |
| `counterfactual_fix` | STRING | Suggested remediation |
| `wrong_clause` | STRING | SQL clause with the error |
| `expected_value` | STRING | What was expected |
| `actual_value` | STRING | What was observed |
| `missing_metadata` | STRING | Metadata that should exist but doesn't |
| `ambiguity_detected` | BOOLEAN | Whether ambiguity caused the failure |

Cell 9b writes to this table after all scorers run. The write is additive (INSERT INTO), preserving history across iterations.

### UC Trace Storage

MLflow traces MUST be stored in Unity Catalog for SQL-queryable, governed observability. Configure in Cell 2 after experiment setup:

1. Create `UCSchemaLocation`:
   ```python
   from mlflow.entities import UCSchemaLocation
   uc_location = UCSchemaLocation(catalog_name=uc_trace_catalog, schema_name=uc_trace_schema)
   ```
2. Set experiment trace location:
   ```python
   from mlflow.tracing.enablement import set_experiment_trace_location
   set_experiment_trace_location(location=uc_location, experiment_id=exp.experiment_id)
   ```
3. Set destination and monitoring:
   ```python
   mlflow.tracing.set_destination(destination=uc_location)
   set_databricks_monitoring_sql_warehouse_id(warehouse_id=warehouse_id, experiment_id=exp.experiment_id)
   ```

**Requires:** `mlflow[databricks]>=3.9.0`. UC trace catalog and schema are derived from the existing `catalog` and `gold_schema` widgets — no separate `uc_trace_catalog`/`uc_trace_schema` widgets.

This enables `SELECT * FROM traces WHERE judge='arbiter'`, UC access control governance, cross-experiment dashboards, and correlation with the `genie_eval_asi_results` table.

## Evaluation Scopes (P5)

The `eval_scope` parameter controls which benchmarks are evaluated:

| Scope | When | Filter |
|-------|------|--------|
| `full` | Default, baseline, final verification | All benchmarks |
| `slice` | After apply, cheap verification | Only benchmarks whose required_tables/required_columns overlap with patched_objects |
| `p0` | Hard constraint gate after slice passes | Only priority="P0" benchmarks |
| `held_out` | Post-deploy overfitting check | Only split="held_out" benchmarks |

The `filter_benchmarks_by_scope()` function handles all filtering.

## Deterministic Normalization (P9)

Result comparison uses deterministic normalization for reproducibility:

- `normalize_result_df(df)`: Sort columns alphabetically, sort rows, round floats to 6 decimals, normalize timestamps to UTC, strip whitespace
- `result_signature(df)`: Quick schema hash + rowcount + numeric sums for fast comparison

Both are applied in `genie_predict_fn` before computing the `comparison` dict.

## Quality Dimensions & Targets

| Dimension | Target | Judge Type | Judge Name |
|-----------|--------|------------|------------|
| Syntax Validity | 98% | Code (`EXPLAIN`) | `syntax_validity_scorer` |
| Schema Accuracy | 95% | LLM | `schema_accuracy_judge` |
| Logical Accuracy | 90% | LLM | `logical_accuracy_judge` |
| Semantic Equivalence | 90% | LLM | `semantic_equivalence_judge` |
| Completeness | 90% | LLM | `completeness_judge` |
| Result Correctness | 85% | Code (executes SQL) | `result_correctness` |
| Asset Routing | 95% | Code (prefix match) | `asset_routing_scorer` |
| Repeatability | 90% | Code (cross-iteration + Cell 9c final) | `repeatability_scorer` (post-eval, final only) |

## Evaluation Modes

| Mode | When to Use | How |
|------|-------------|-----|
| **Job mode** (`--job-mode`) | Production, CI/CD, >= 10 benchmarks | `databricks bundle run genie_evaluation_job` |
| **Inline** (default) | Quick iteration, < 10 benchmarks | `run_evaluation_iteration()` in-process |

In job mode, the agent triggers the job and reads results from `dbutils.notebook.exit()` or `mlflow.search_runs()`.

### Agent Orchestration Pattern (Job Mode)

```
Agent                          Databricks Job              MLflow
  |                                 |                        |
  |-- create_genie_model_version() -|----------------------->|-- LoggedModel
  |-- trigger_evaluation_job() ---->|                        |
  |     (model_id as parameter)     |-- query Genie -------->|
  |     (polls every 30s)           |-- run judges --------->|
  |                                 |-- evaluate(model_id) ->|-- iter N run
  |<-- notebook.exit(JSON) ---------|                        |
  |                                                          |
  |-- mlflow.search_runs() --------------------------------->|
  |<-- metrics, artifacts, Versions tab --------------------|
```

### Template Files

| File | Purpose |
|------|---------|
| [run_genie_evaluation.py](assets/templates/run_genie_evaluation.py) | Self-contained notebook: load → query → judge → log → exit |
| [genie-evaluation-job-template.yml](assets/templates/genie-evaluation-job-template.yml) | DABs job definition with parameters and dependencies |

### HARD CONSTRAINTS

1. **Every scorer MUST use `@scorer` decorator. DO NOT stack `@mlflow.trace` on top** — `mlflow.genai.evaluate()` traces scorer execution automatically. Stacking `@mlflow.trace` wraps the scorer in a generic wrapper that strips `.register()`, leaving the Judges tab empty.
2. **Every scorer MUST call `.register(name=...)` after creation** — unregistered scorers leave the Judges tab empty and block continuous monitoring. Use `try/except` with explicit error logging (not silent catch) to surface registration failures immediately.
3. **All SQL MUST pass through `sanitize_sql()` then `resolve_sql()` before `EXPLAIN` or `spark.sql()`** — Genie returns multi-statement SQL; ground truth uses `${catalog}` template variables.
4. **Use `mlflow.genai.evaluate()` NOT manual `mlflow.log_metric()`** — manual logging leaves the Evaluation tab empty.
5. **Template code in `run_genie_evaluation.py` IS the spec** — if the checklist says "use X" but the template uses "Y", agents follow the template. The template must implement every checklist item.
6. **Judge prompts MUST be registered to the Prompt Registry** on iteration 1 via `register_judge_prompts()` and loaded by `@production` alias via `load_judge_prompts()` on every iteration. Inline prompt strings without registry integration leave the Prompts tab empty and block A/B testing of prompt changes.
7. **`arbiter_scorer` MUST be the 8th entry in `all_scorers`** — it is a conditional `@scorer` that returns `value="skipped"` when results match and invokes the LLM only when they disagree. Without it, arbiter verdicts are invisible in MLflow.
8. **SQL execution MUST live in `genie_predict_fn`, NOT in scorers** — the predict function runs once per row and stores comparison data in `outputs["comparison"]`. Both `result_correctness` and `arbiter_scorer` read this dict. No scorer calls `spark.sql()` directly.
9. **`make_judge()` instructions MUST only use template variables from the allowlist: `{{ inputs }}`, `{{ outputs }}`, `{{ trace }}`, `{{ expectations }}`, `{{ conversation }}`** — custom variables like `{{question}}`, `{{genie_sql}}` raise `MlflowException: unsupported variables`. The Prompt Registry accepts any variable names, but `make_judge()` does not. Prompts MUST also contain at least one allowed variable (plain text is rejected with `MlflowException: must contain at least one variable`).
10. **`predict_fn` signature MUST use keyword arguments matching the `inputs` dict keys, NOT `inputs: dict`** — `mlflow.genai.evaluate()` unpacks the `inputs` dict as keyword arguments: `predict_fn(**inputs_dict)`. Use `def genie_predict_fn(question: str, expected_sql: str = "", **kwargs)`. The `inputs: dict` signature causes `MlflowException: inputs column must be a dictionary`.
11. **Repeatability check (Cell 9c) MUST only run in the final dedicated test (Phase 3b)** — the check re-queries Genie 2 extra times per question (~24s each). During the optimization loop, the orchestrator uses free cross-iteration SQL comparison instead. Cell 9c fires once after all levers complete, gated behind the `run_repeatability` job parameter. **Cell 9c MUST also log per-trace assessments via `mlflow.log_assessment()`** for each question's repeatability result — artifact-only logging (`evaluation/repeatability.json`) is invisible in the MLflow Evaluations UI.
12. **Cell 9c MUST emit structured ASI via `build_asi_metadata()` for all non-repeatable results.** Free-text summaries (e.g., `CRITICAL_VARIANCE: 33% consistency`) are insufficient -- the ASI pipeline requires `failure_type`, `blame_set`, `severity`, `counterfactual_fix` fields for the optimizer to generate targeted proposals. Repeatability rows MUST also be appended to the `genie_eval_asi_results` UC table. Severity mapping: `CRITICAL_VARIANCE -> "critical"`, `SIGNIFICANT_VARIANCE -> "major"`, `MINOR_VARIANCE -> "minor"`.
13. **ALL judges MUST return structured ASI metadata via `Feedback(metadata=build_asi_metadata(...))` on failure verdicts.** `make_judge()` CANNOT emit structured `metadata` -- it produces only free-text `rationale`. Convert all LLM judges to custom `@scorer` functions that call `_call_llm_for_scoring()` and parse JSON responses for ASI fields. This includes `unknown` verdicts from failed LLM calls — they MUST also carry `build_asi_metadata(failure_type="other", severity="info", confidence=0.0, counterfactual_fix="LLM judge unavailable — retry or check endpoint")`. See "Judge ASI Requirements" section below.
14. **`_call_llm_for_scoring()` MUST retry transient failures with exponential backoff (default: 3 attempts).** Empty or non-JSON responses MUST be retried, not silently degraded to "unknown". Markdown code fence wrapping (```` ```json ... ``` ````) MUST be stripped before JSON parsing. Without retry, a 10% transient failure rate across 25 benchmarks x 4 LLM judges produces ~10 meaningless "unknown" verdicts.
15. **`set_active_model()` MUST be called INSIDE `with mlflow.start_run()` in Cell 8, not in Cell 2.** Calling it outside the run context means the evaluation run is not tagged with `mlflow.loggedModelId`, so the MLflow UI's Evaluation Runs tab will not show the LoggedModel association. Cell 2 should only print the model_id for diagnostics.
16. **UC dataset `inputs` and DataFrame `inputs` MUST use the same schema via `_build_inputs(b)`.** Extract a shared helper to prevent field drift between the two data paths. The `data` parameter to `mlflow.genai.evaluate()` MUST always be the DataFrame (`eval_data`), never the UC dataset object — the UC dataset populates the Datasets tab but cannot reliably carry all required input fields.

## Critical Patterns

- Scorers use `@scorer` only (no `@mlflow.trace` stacking); `mlflow.genai.evaluate()` traces automatically
- Code-based scorers use `_extract_response_text(outputs)` to handle serialized dict format
- LLM-based scorers use `_call_llm_for_scoring()` via Databricks SDK (NOT `langchain_databricks`)
- Run names follow `genie_eval_iter{N}_{YYYYMMDD_HHMMSS}` for programmatic querying
- Pass `model_id` to `mlflow.genai.evaluate(model_id=...)` to link evaluation results to the specific Genie Space config version in the MLflow Versions tab
- Rate limit: **12s between every Genie API call**
- Apply `sanitize_sql()` before any `EXPLAIN` or `spark.sql()` on Genie-returned SQL
- Apply `resolve_sql(sql, catalog, gold_schema)` before executing ground truth SQL
- Judge prompts registered to Prompt Registry with `@production` alias; loaded via `load_judge_prompts()` at startup — `make_judge(instructions=...)` uses versioned prompts, not inline strings
- SQL execution lifted into `genie_predict_fn` — returns `comparison` dict consumed by `result_correctness` and `arbiter_scorer` with zero redundant `spark.sql()` calls
- Arbiter runs as 8th scorer in `all_scorers`; returns `value="skipped"` when results match (zero LLM cost on passing rows)
- Cell 3a runs GT validation pre-check before evaluation — see **GT Validation Handoff** subsection below

### LoggedModel Content Requirements

A LoggedModel MUST capture the full model state, not just the Genie config:

1. **Genie Space config JSON** — from `GET /api/2.0/genie/spaces/{id}?include_serialized_space=true`
2. **UC column metadata** — from `{catalog}.information_schema.columns WHERE table_schema = '{gold_schema}'` for all tables/views in the space (captures table/column comments for Lever 1, MV column definitions for Lever 2)
3. **UC tags** — from `{catalog}.information_schema.table_tags WHERE schema_name = '{gold_schema}'` (captures structured metadata tags for Lever 1)
4. **TVF routines** — from `{catalog}.INFORMATION_SCHEMA.ROUTINES WHERE routine_schema = '{gold_schema}'` (captures TVF names, signatures, parameters, and return types for Lever 3)
5. **Config hash** — MD5 of the combined Genie config + UC metadata for quick identity comparison

Artifacts are logged under `model_state/`: `genie_config.json`, `uc_columns.json`, `uc_tags.json`, `uc_routines.json`. This enables meaningful iteration diffs across all levers.

When `model_id` is not provided by the orchestrator (e.g., direct `databricks bundle run`), the evaluator auto-creates a LoggedModel as a fallback by fetching the live Genie config and UC metadata snapshots.

### make_judge() Returns a Scorer Callable

`make_judge()` returns an `InstructionsJudge` scorer — a callable intended for use inside `mlflow.genai.evaluate(scorers=[...])`. Scorers have **no `.evaluate()` method**. For inline/conditional LLM calls outside the `mlflow.genai.evaluate()` harness (e.g., arbiter conditional scoring when Layer 1/2 judges disagree), use `_call_llm_for_scoring()` via the Databricks SDK `w.serving_endpoints.query()`, which parses JSON verdicts from the LLM response.

### Judge ASI Requirements

**ALL judges MUST return `Feedback(metadata=build_asi_metadata(...))` on failure verdicts.** This is required because the optimizer's `cluster_failures()` and `generate_metadata_proposals()` consume structured ASI fields to generate targeted patch proposals. Without structured metadata, the optimizer falls back to regex parsing of free-text rationale, which is unreliable.

**`make_judge()` limitation:** `make_judge()` produces only free-text `rationale` in its `Feedback` object. It has no mechanism to return structured `metadata`. This makes it unsuitable for judges that feed the ASI pipeline (which is all judges in the optimization loop).

**Conversion pattern:** Convert each `make_judge()` judge to a custom `@scorer` that:
1. Constructs a prompt requesting JSON output with ASI fields (`failure_type`, `wrong_clause`, `blame_set`, etc.)
2. Calls `_call_llm_for_scoring(prompt)` via Databricks SDK
3. Parses the JSON response
4. Returns `Feedback(metadata=build_asi_metadata(...))` on failure, `Feedback(value="yes")` on pass

Each judge's JSON schema is tailored to its failure domain:
- `schema_accuracy`: `failure_type` in `{wrong_table, wrong_column, wrong_join, missing_column}`
- `logical_accuracy`: `failure_type` in `{wrong_aggregation, wrong_filter, wrong_groupby, wrong_orderby}`
- `semantic_equivalence`: `failure_type` in `{different_metric, different_grain, different_scope}`
- `completeness`: `failure_type` in `{missing_column, missing_filter, missing_aggregation, partial_answer}`

**When to keep `make_judge()`:** Quick prototyping, one-off evaluations, or scenarios where structured ASI is not consumed downstream. For the optimization loop, always use `@scorer` with ASI.

### Repeatability Judge Visibility

Cell 9c MUST log per-trace assessments via `mlflow.log_assessment()` for each question's repeatability result. Artifact-only logging (`evaluation/repeatability.json`) is invisible in the MLflow Evaluations UI. Use the same `trace_id` as the original evaluation trace so assessments appear alongside other judge results.

### Runtime Parameter Overrides

Notebook widget values (`dbutils.widgets.get()`) are set via `base_parameters` in the job YAML. The CLI `--params` flag only works with the `parameters` block (job parameters), **not** `base_parameters` (notebook widgets). To override a widget value at runtime, modify `base_parameters` in the job YAML and redeploy via `databricks bundle deploy`.

### GT Validation Handoff (Cell 3a)

Cell 3a calls `validate_ground_truth_sql()` logic (from the Generator's `references/gt-validation.md`) as a structural pre-check before evaluation begins. For each benchmark, the expected SQL is executed with `LIMIT 1`. Failed queries go through a two-pass remediation:
1. **Auto-remediation:** LLM-based correction using `information_schema.columns` + `INFORMATION_SCHEMA.ROUTINES` schema context
2. **Gate and queue:** Unrepairable benchmarks are excluded; if below `min_benchmarks`, the job fails; otherwise `gt_remediation_queue.yaml` is emitted as an MLflow artifact for the orchestrator to route to the Generator

### Benchmark Coverage Guard

For `full`-scope evaluations, Cell 3 asserts `len(benchmarks) >= min_benchmarks` (configurable widget, default 20). Insufficient benchmarks produce statistically unreliable results and must be addressed by running the Generator worker first.

## Asset Routing Context

TVF vs Metric View decision matrix for the `asset_routing_scorer`:

| Query Type | Preferred Asset | Reason |
|------------|-----------------|--------|
| Aggregations (total, average) | Metric View | Pre-optimized for MEASURE() |
| Lists (show me, top N) | TVF | Parameterized, returns rows |
| Time-series with params | TVF | Date range parameters |
| Dashboard KPIs | Metric View | Single-value aggregations |

TVF-first design improves repeatability (100% in quality domain vs 67% in MV-heavy routing).

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Using `mlflow.evaluate()` instead of `mlflow.genai.evaluate()` | Evaluation tab empty | Use `mlflow.genai.evaluate()` |
| Stacking `@mlflow.trace` on `@scorer` | Judges tab empty — `.register()` stripped by trace wrapper | Remove `@mlflow.trace` from scorers; `mlflow.genai.evaluate()` traces automatically |
| Accessing `outputs["response"]` directly | KeyError or silent 0.0 | Use `_extract_response_text(outputs)` |
| No delay between Genie queries | Rate limit exceeded | `time.sleep(12)` between every API call |
| Using `langchain_databricks` for LLM | Auth issues | Use `_call_llm_for_scoring()` via SDK |
| DABs `parameters` block with `{{job.parameters.X}}` | Silent `INTERNAL_ERROR` with zero diagnostic output | Use `base_parameters` with `${var.X}` |
| Bare experiment path `/genie-optimization/...` | `RESOURCE_DOES_NOT_EXIST` — parent dir doesn't exist | Use `/Users/<email>/genie-optimization/...` and pre-create parent |
| Assuming single-statement SQL from Genie | GRPC/EXPLAIN crash on multi-statement | Apply `sanitize_sql()` before all SQL execution |
| Unresolved `${catalog}`/`${gold_schema}` in GT SQL | `PARSE_SYNTAX_ERROR` on every benchmark | Apply `resolve_sql(sql, catalog, gold_schema)` before `spark.sql()` |
| Judges defined as plain functions (no `@scorer`) | Judges tab empty, no continuous monitoring | Use `make_judge()` / `@scorer` + `.register(name=...)` |
| Inline prompt strings in `make_judge()` | Prompts tab empty, no versioning, no A/B testing | Use `register_judge_prompts()` on iter 1, `load_judge_prompts()` on every run |
| Arbiter not in `all_scorers` | Arbiter verdicts invisible in MLflow Judges/Traces tabs | Include `arbiter_scorer` as 8th entry in `all_scorers` |
| SQL execution inside scorers | Redundant `spark.sql()` calls, doubled latency | SQL execution lives in `genie_predict_fn`; scorers read `outputs["comparison"]` |
| Missing `expected_sql` in eval_records `inputs` | `genie_predict_fn` cannot compute comparison | Add `"expected_sql": b.get("expected_sql", "")` to `inputs` dict |
| Leaving `dataset_mode` as `"yaml"` when UC dataset exists | Datasets tab empty, Generator UC sync wasted | Default is now `"uc"` when `uc_schema` is set; falls back to `"yaml"` when UC unavailable |
| Custom template variables in `make_judge()` (e.g., `{{question}}`, `{{genie_sql}}`) | `MlflowException: unsupported variables` — crashes before any benchmark runs | Use only `{{ inputs }}`, `{{ outputs }}`, `{{ expectations }}` in judge instructions |
| Plain text instructions without any template variables in `make_judge()` | `MlflowException: must contain at least one variable` — exposed after stripping custom vars | Include at least one of `{{ inputs }}`, `{{ outputs }}`, `{{ expectations }}`; use `_sanitize_prompt_for_make_judge()` as safety net |
| `predict_fn(inputs: dict)` signature | `MlflowException: inputs column must be a dictionary` — `mlflow.genai.evaluate()` unpacks inputs as kwargs | Use keyword args matching inputs keys: `def genie_predict_fn(question: str, expected_sql: str = "", **kwargs)` |
| Hardcoding `/Workspace/` prefix for file paths | `FileNotFoundError` in DABs deployments | Use `_bundle_root` derived from notebook context |
| Assuming orchestrator always provides `model_id` | No LoggedModel, no config version tracking, silent degradation | Auto-create LoggedModel in evaluator when `model_id` is empty: fetch config + UC metadata, compute hash, call `mlflow.set_active_model()` |
| Passing UC dataset name string to `data` parameter | `MlflowException: Invalid type for parameter 'data'` | Always convert to DataFrame before `mlflow.genai.evaluate()`; UC dataset is still created for Datasets tab |
| Bare `mlflow.log_artifact()` outside run context | `Exception: Run with UUID ... is already active` — blocks prompt registration | Wrap all `mlflow.log_artifact()` calls in `with mlflow.start_run()` context |
| Calling `make_judge().evaluate()` for conditional scoring | `AttributeError: 'InstructionsJudge' object has no attribute 'evaluate'` | Use `_call_llm_for_scoring()` via Databricks SDK for inline/conditional LLM calls |
| Cell 9c using `inputs/question` column name | Repeatability check produces 0% results — all questions skipped | Use fallback access: `row.get("request", row.get("inputs", {})).get("question")` |
| Using `make_judge()` for judges that feed the ASI pipeline | Optimizer receives empty/regex-parsed metadata, proposals are generic not targeted | Convert to `@scorer` with `_call_llm_for_scoring()` + `build_asi_metadata()`. `make_judge()` cannot emit structured metadata. |
| `_call_llm_for_scoring()` with no retry | Transient empty responses cascade to "unknown" verdicts across all LLM judges | Add 3-retry exponential backoff with empty-response validation and code fence stripping (HC #14) |
| Hardcoded `model_id` in job YAML across iterations | All eval runs link to stale iter0 model, lever changes not captured | Leave `model_id` empty for auto-creation, or update dynamically per iteration from orchestrator |
| `unknown` verdict with no ASI metadata | Optimizer receives no structured guidance for failed LLM judges | Add `build_asi_metadata(failure_type="other", severity="info", confidence=0.0)` to all `except` handlers in LLM judge scorers (HC #13) |
| UC dataset `inputs` missing fields vs DataFrame `inputs` | `result_correctness` scores 0% when UC path is used — `expected_sql`, `catalog`, `gold_schema` absent | Use shared `_build_inputs(b)` helper for both UC and DataFrame paths (HC #16) |

## Scripts

### [genie_evaluator.py](scripts/genie_evaluator.py)

Standalone evaluation CLI with inline and job-based modes.

### [repeatability_tester.py](scripts/repeatability_tester.py)

Standalone CLI for testing SQL consistency across multiple runs (MD5 hash comparison). The same logic is integrated into `run_genie_evaluation.py` Cell 9c as a post-evaluation step, gated by `run_repeatability=true`. The orchestrator enables this during full-scope evaluations; results are emitted as `evaluation/repeatability.json` artifact and `repeatability/mean` metric.

```bash
python scripts/repeatability_tester.py --space-id <ID> --iterations 3
```

## Template Cell Contract

Specifies each evaluator template cell's inputs, outputs, side effects, and error modes. This is the authoritative contract between SKILL.md prose and template code.

| Cell | Purpose | Inputs | Outputs | Side Effects | Error Modes |
|------|---------|--------|---------|-------------|-------------|
| Cell 1 | Path setup + imports | notebook context | `_bundle_root`, modules | `sys.path` modification | Path setup skipped in local execution |
| Cell 2 | Widget parsing + config | `dbutils.widgets` | All config variables, `model_id` | LoggedModel auto-creation (if `model_id` empty), MLflow artifact logging. **Does NOT call `set_active_model()`** (HC #15 — moved to Cell 8) | Widget not found (defaults used) |
| Cell 3 | Benchmark loading | `benchmarks_yaml_path`, `domain`, `eval_scope` | `benchmarks` list | None | `FileNotFoundError` (wrong path), empty list (no matching domain) |
| Cell 3a | GT validation pre-check | `benchmarks`, `catalog`, `gold_schema` | Validated `benchmarks`, `gt_remediation_queue.yaml` artifact | MLflow artifact (remediation queue) | `ValueError` (below `min_benchmarks` after exclusions) |
| Cell 4 | Define predict function | `space_id`, `warehouse_id`, config | `genie_predict_fn`, `run_genie_query` | None | None (definitions only) |
| Cell 5 | Register judge prompts | `uc_schema`, `JUDGE_PROMPTS` | Registered prompts in Prompt Registry | MLflow run (prompt artifacts) | `MlflowException` (invalid variables) |
| Cell 6 | Create scorers | Loaded prompts | `all_scorers` list (8 entries) | Scorer registration via `.register()` | Registration failures logged explicitly |
| Cell 7 | Prepare eval data | `benchmarks`, `eval_dataset_uc_name` | `eval_data` (always `pd.DataFrame`) | UC dataset creation (Datasets tab). Uses `_build_inputs(b)` shared helper (HC #16) | `MlflowException` if string passed to `data` param |
| Cell 7.5 | Pre-evaluation assertion | `eval_records` | None | None | `AssertionError` if `expected_sql` or `catalog` missing from inputs |
| Cell 8 | Run `mlflow.genai.evaluate()` | `genie_predict_fn`, `eval_data`, `all_scorers` | `eval_result`, MLflow run | Calls `set_active_model(model_id)` inside run context (HC #15), MLflow run with metrics, traces, evaluations | Rate limit errors, Genie API timeouts |
| Cell 9 | Compute summary metrics | `eval_result` | `output` dict with aggregate scores | None | Empty `eval_result.tables` |
| Cell 9b | Emit structured artifacts + ASI UC table | `eval_result`, `rows_for_output` | `eval_results.json`, `failures.json`, `arbiter_actions.json` | MLflow artifacts, arbiter auto-persistence to `golden-queries.yaml`, writes one row per (question, judge) to `genie_eval_asi_results` UC table | Missing `eval_result.tables["eval_results"]` |
| Cell 9c | Repeatability check | `rows_for_output`, `run_repeatability` | `repeatability_results`, per-trace assessments | MLflow metrics, artifact, `mlflow.log_assessment()` | Column name mismatch (use fallbacks) |
| Cell 10 | Exit | `output` dict | `dbutils.notebook.exit(json)` | None | Serialization errors |

## Template Verification

Maps each critical pattern from the SKILL.md to its template cell and expected behavior, enabling verification that documentation and code agree.

| Pattern | Template Cell | Expected Behavior | Violation Signal |
|---------|--------------|-------------------|------------------|
| `data` param must be DataFrame | Cell 7, line ~957 | `eval_data` always assigned as `pd.DataFrame` | Cell 7 assigns a string -> `MlflowException` |
| `mlflow.log_artifact()` inside run | Cell 2/5, line ~652 | All artifact logging wrapped in `with mlflow.start_run()` | Bare call -> implicit run conflict |
| Scorer has no `.evaluate()` | Cell 6 arbiter | Uses `_call_llm_for_scoring()` for inline LLM calls | `.evaluate()` call -> `AttributeError` |
| `model_id` fallback | Cell 2, line ~270 | Auto-creates LoggedModel with UC metadata when empty | No LoggedModel -> silent degradation |
| Cell 9c column access | Cell 9c, line ~1249 | Uses fallback: `row.get("request", row.get("inputs", {}))` | Flat column names -> 0% repeatability |
| Cell 9c assessment logging | Cell 9c, line ~1327 | Calls `mlflow.log_assessment()` per question | Artifact-only -> invisible in UI |
| GT validation pre-check | Cell 3a | Validates all GT SQL via `spark.sql(LIMIT 1)` | Missing Cell 3a -> broken GT SQL passes through |
| Benchmark coverage guard | Cell 3 | Asserts `len(benchmarks) >= min_benchmarks` | Missing guard -> unreliable metrics from few benchmarks |
| Bundle root path | Cell 1, line ~10-16 | `_bundle_root` derived from notebook context | Hardcoded `/Workspace/` -> `FileNotFoundError` in DABs |
| Prompt registration lifecycle | Cell 5 | `register_judge_prompts()` on iter 1, `load_judge_prompts()` on every run | Inline strings -> Prompts tab empty |
| `_call_llm_for_scoring` retry | Cell 6 scorers | 3-retry with exponential backoff, empty-response validation, code fence stripping | Single attempt -> cascading "unknown" verdicts |
| `set_active_model()` inside run | Cell 8, after `log_params` | Called after `mlflow.start_run()`, inside run context | Cell 2 call -> run not tagged with `mlflow.loggedModelId` |
| UC and DataFrame inputs identical | Cell 5 + Cell 7 | Both use `_build_inputs(b)` shared helper | Field drift -> 0% `result_correctness` on UC path |
| Pre-evaluation assertion | Cell 7.5 | Asserts `expected_sql` and `catalog` present in first record | Missing fields -> silent 0% scores |

## Template Self-Consistency Check

Each Common Mistake documented above MUST map to a specific template line or assertion that prevents it. When adding a new Common Mistake, also add a corresponding entry to the Template Verification table above. When modifying template code, cross-check against the Common Mistakes table to ensure no documented constraint is violated.

This bidirectional mapping catches regressions where documentation and code diverge — e.g., SKILL.md warns "Always convert to DataFrame" but the template passes the UC dataset object.

## Reference Index

| Reference | What to Find |
|-----------|-------------|
| [judge-definitions.md](references/judge-definitions.md) | All 8 judges, predict function, thresholds, LLM call helper |
| [result-comparison.md](references/result-comparison.md) | DataFrame comparison (exact, approximate, structural) |
| [arbiter-workflow.md](references/arbiter-workflow.md) | Arbiter invocation, verdict handling, benchmark auto-correction |

## Version History

- **v4.1.0** (Feb 23, 2026) — Evaluator template bug fixes (4 critical bugs from production run). Bug 1: UC dataset `inputs` missing `expected_sql`/`catalog`/`gold_schema` — extracted shared `_build_inputs(b)` helper for both UC and DataFrame paths (HC #16), added predict function fallback lookup, added Cell 7.5 pre-evaluation assertion. Bug 2: `_call_llm_for_scoring()` had no retry — added 3-retry exponential backoff with empty-response validation and code fence stripping (HC #14). Bug 3: `set_active_model()` called outside run context — moved into Cell 8 `with mlflow.start_run()` block (HC #15). Bug 4: LLM judge `unknown` paths missing ASI metadata — added `build_asi_metadata()` to all 5 exception handlers. Added Template Self-Consistency Check section. Added 4 new Common Mistakes rows and 4 Template Verification rows. Version bumped from v4.0.0.
- **v4.0.0** (Feb 23, 2026) — Phase 6 architectural lessons (7 lessons). Added ASI Serialization & UC Table Contract section with `genie_eval_asi_results` schema. Added UC Trace Storage section (UCSchemaLocation + mlflow[databricks]>=3.9.0). Added Judge ASI Requirements section: ALL judges must emit structured ASI via `build_asi_metadata()`; `make_judge()` replaced by `@scorer` with `_call_llm_for_scoring()`. Added HC #12 (Cell 9c structured ASI), HC #13 (judge ASI requirement). Updated Template Cell Contract for ASI UC table writes. Version bumped from v3.9.0.
- **v3.9.0** (Feb 22, 2026) — Phase 5 feedback remediation (18 errors + 4 patterns). Added DABs Bundle Root Path Resolution section. Added LoggedModel Content Requirements (Genie config + `information_schema.columns` + `table_tags` + `INFORMATION_SCHEMA.ROUTINES`). Added make_judge() scorer semantics note, Repeatability Judge Visibility mandate (`mlflow.log_assessment()`), Runtime Parameter Overrides documentation, GT Validation Handoff (Cell 3a), Benchmark Coverage Guard. Expanded HC #11 to require per-trace assessments. Added Template Cell Contract and Template Verification sections. Added 7 new Common Mistakes rows. Version bumped from v3.8.0.
- **v3.8.0** (Feb 22, 2026) — Repeatability v2. Cell 9c now only fires in the final dedicated test (Phase 3b), not on every full-scope evaluation. During the loop, the orchestrator uses free cross-iteration SQL comparison. Hard constraint #11 updated to reflect final-only gating. Added `detect_asset_type()` local definition in Cell 9c (fixes missing function bug). Repeatability scorer description updated.
- **v3.7.0** (Feb 22, 2026) — Repeatability judge integration. Added Cell 9c post-evaluation repeatability check: re-queries Genie 2 extra times per question, computes per-question SQL consistency via MD5 hash comparison, classifies as IDENTICAL/MINOR_VARIANCE/SIGNIFICANT_VARIANCE/CRITICAL_VARIANCE. Gated behind `run_repeatability` widget parameter (default false). Emits `evaluation/repeatability.json` artifact and `repeatability/mean` metric to MLflow. Results include per-question breakdown with `dominant_asset` type for TVF-first optimization routing. Added hard constraint #11 (repeatability only during full scope). Updated `repeatability_tester.py` documentation to reference Cell 9c integration.
- **v3.6.0** (Feb 22, 2026) — Phase 4 runtime error fixes. JUDGE_PROMPTS rewritten to use only `make_judge()` allowed template variables (`{{ inputs }}`, `{{ outputs }}`, `{{ expectations }}`), replacing custom variables (`{{question}}`, `{{genie_sql}}`, `{{expected_sql}}`) that raised `MlflowException`. Added `_sanitize_prompt_for_make_judge()` safety net helper. Fixed `genie_predict_fn` signature from `(inputs: dict)` to `(question: str, expected_sql: str = "", **kwargs)` to match `mlflow.genai.evaluate()` keyword-argument unpacking. Added hard constraints #9 (make_judge allowlist) and #10 (predict_fn kwargs). Added 3 new Common Mistakes entries for cascading evaluation errors.
- **v3.0.0** (Feb 2026) — Initial structured evaluator with 8 scorers, MLflow GenAI integration, Prompt Registry lifecycle, arbiter as 8th scorer, SQL execution lifted into predict function.

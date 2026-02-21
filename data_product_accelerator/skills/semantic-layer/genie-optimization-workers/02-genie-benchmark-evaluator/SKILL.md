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
  version: "3.0.0"
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

**FAILURE_TAXONOMY:** wrong_table, wrong_column, wrong_join, missing_filter, wrong_aggregation, wrong_measure, missing_instruction, ambiguous_question, asset_routing_error, tvf_parameter_error, compliance_violation, performance_issue, repeatability_issue, missing_synonym, description_mismatch, other.

**ASI_SCHEMA fields:** failure_type, severity, confidence, wrong_clause, blame_set, quoted_metadata_text, missing_metadata, ambiguity_detected, expected_value, actual_value, counterfactual_fix, affected_question_pattern.

Use `build_asi_metadata()` helper to construct ASI metadata dicts for `Feedback(metadata=...)`.

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
| Repeatability | 90% | Code (hash) | `test_repeatability` |

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

## Scripts

### [genie_evaluator.py](scripts/genie_evaluator.py)

Standalone evaluation CLI with inline and job-based modes.

### [repeatability_tester.py](scripts/repeatability_tester.py)

Tests SQL consistency across multiple runs (MD5 hash comparison).

```bash
python scripts/repeatability_tester.py --space-id <ID> --iterations 3
```

## Reference Index

| Reference | What to Find |
|-----------|-------------|
| [judge-definitions.md](references/judge-definitions.md) | All 8 judges, predict function, thresholds, LLM call helper |
| [result-comparison.md](references/result-comparison.md) | DataFrame comparison (exact, approximate, structural) |
| [arbiter-workflow.md](references/arbiter-workflow.md) | Arbiter invocation, verdict handling, benchmark auto-correction |

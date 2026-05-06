---
name: genie-optimization-orchestrator
description: >
  Orchestrates the Genie Space optimization loop by routing to 4 workers
  on demand. Maintains session state in MLflow experiment tags. Loop:
  generate benchmarks -> evaluate -> optimize -> apply -> re-evaluate,
  max 5 iterations with plateau detection. Each worker is loaded, used,
  and released. Use when optimizing Genie Space accuracy, debugging SQL
  generation, or running automated evaluation sessions.
metadata:
  author: prashanth subrahmanyam
  version: "4.3.0"
  domain: semantic-layer
  role: orchestrator
  pipeline_stage: 6
  pipeline_stage_name: semantic-layer
  called_by:
    - semantic-layer-setup
  workers:
    - genie-benchmark-generator
    - genie-benchmark-evaluator
    - genie-metadata-optimizer
    - genie-optimization-applier
  standalone: true
  common_dependencies:
    - mlflow-genai-evaluation
  source: genie-optimization-orchestrator
  last_verified: "2026-02-21"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-genie/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
    - name: "mlflow-genai-evaluation"
      paths:
        - "skills/genai-agents/02-mlflow-genai-evaluation/SKILL.md"
      relationship: "adopts-patterns"
    - name: "prompt-registry-patterns"
      paths:
        - "skills/genai-agents/04-prompt-registry-patterns/SKILL.md"
      relationship: "adopts-patterns"
---

# Genie Optimization Orchestrator

Routes to 4 worker skills on demand to optimize Genie Space accuracy through MLflow-backed evaluation, introspective analysis, and structured progress tracking.

## Section 1: When to Use This Skill

- Optimizing Genie Space accuracy (target 95%+) or repeatability (target 90%+)
- Writing and validating benchmark questions with ground truth SQL
- Running MLflow-scored evaluation experiments against live Genie Spaces
- Debugging incorrect SQL generation with multi-dimensional judges
- Improving asset routing (TVF vs Metric View selection)
- Optimizing Genie Space metadata using GEPA or LLM introspection

### Hand Off to Related Skills

| User Says / Task Involves | Load Instead |
|---|---|
| "create Genie Space from scratch" | `genie-space-patterns` |
| "deploy Genie Space via API" | `genie-space-export-import-api` |
| "create metric view" | `metric-views-patterns` |
| "create TVF" | `databricks-table-valued-functions` |

## Section 2: Session State Schema

The orchestrator maintains a `session` dict across iterations, persisted in `optimization-progress.json` and MLflow experiment tags.

**Load:** Read [session-state-schema.md](references/session-state-schema.md) for the full schema, MLflow setup, space discovery, progress tracking functions, and prompt registration.

**BEFORE any Databricks API call:** resolve the CLI profile from `databricks.yml`:

1. Read `databricks.yml` -> extract `workspace.profile`
2. Use that profile for all CLI and SDK calls: `WorkspaceClient(profile=<profile>)`
3. Verify access: `databricks genie list-spaces --profile <profile>`

```python
session = {
    "space_id": str,             # Genie Space being optimized
    "domain": str,               # Domain name (e.g., "cost")
    "cli_profile": str | None,   # Databricks CLI profile (from databricks.yml)
    "experiment_name": str,      # MLflow experiment path
    "experiment_id": str,        # MLflow experiment ID
    "model_id": str | None,      # Active LoggedModel ID for current iteration
    "uc_schema": str | None,     # Unity Catalog schema
    "current_iteration": int,    # 0-based iteration counter
    "max_iterations": int,       # Default 5
    "status": str,               # in_progress | converged | stalled | max_iterations
    "best_overall_accuracy": float,
    "best_iteration": int,
    "remaining_failures": list,
    "convergence_reason": str | None,
    "iterations": list[dict],    # Per-iteration results
    "lever_impacts": dict,       # Per-lever before/after score tracking
}
```

### LoggedModel Lifecycle

Each iteration creates a LoggedModel that serves as a metadata hub:

1. **Create** — `create_genie_model_version(space_id, config, N, domain, patch_set, parent_model_id, prompt_versions, uc_schema)` before evaluation
2. **Link** — Pass `model_id` to evaluator; `mlflow.genai.evaluate(model_id=...)` links results
3. **Chain** — Each model references its parent via `parent_model_id` param
4. **Promote** — `promote_best_model(session)` tags the best-performing model after convergence
5. **Rollback** — `rollback_to_model(model_id, space_id)` restores config from a model's artifact

The MLflow Versions tab becomes the central dashboard showing progression, params, and linked evaluations.

### HARD CONSTRAINTS — Read Before Any Step

1. **Every evaluation MUST be logged to an MLflow experiment.** No judges without `mlflow.start_run()`.
2. **Create the MLflow experiment before Step 2.** Confirm via printed experiment URL.
3. **MLflow environment setup (required outside Databricks notebooks):**
   ```python
   import os
   os.environ['DATABRICKS_HOST'] = '<workspace_url>'
   os.environ['DATABRICKS_TOKEN'] = '<token>'
   os.environ['MLFLOW_TRACKING_URI'] = 'databricks'
   ```
4. **Verify after creation:** Print experiment URL and run URL. Stop if either fails.
5. **Every metric, artifact, and parameter must be logged within a run.**
6. **Every iteration MUST create a LoggedModel** via `mlflow.set_active_model()` before evaluation. Pass `model_id` to the Evaluator so `mlflow.genai.evaluate(model_id=...)` links results to the config version.
7. **Experiment path MUST be under `/Users/<email>/`** — bare paths like `/genie-optimization/...` cause `RESOURCE_DOES_NOT_EXIST`. Pre-create parent directory via `databricks workspace mkdirs` before `mlflow.set_experiment()`.
8. **All SQL from Genie must be sanitized** via `sanitize_sql()` (extract first statement, strip comments) before `EXPLAIN` or `spark.sql()`. Genie can return multi-statement SQL for compound questions.
9. **The evaluator job owns UC dataset creation, prompt registration, and trace setup.** The orchestrator computes the `eval_dataset_name` string (`{uc_schema}.genie_benchmarks_{domain}`) and passes it as a job parameter, but does NOT call `sync_yaml_to_mlflow_dataset()` or `register_judge_prompts()`. The evaluator notebook creates the UC dataset via `mlflow.genai.datasets.create_dataset()` + `merge_records()`, registers prompts on iteration 1 via `register_judge_prompts()`, and configures UC traces via `set_experiment_trace_location()`. This avoids duplication and ensures all MLflow state is created within the Databricks cluster context.
10. **All ground truth SQL containing `${catalog}` or `${gold_schema}`** must be resolved via `resolve_sql()` before execution. Unresolved template variables cause `PARSE_SYNTAX_ERROR`.
11. **Judge prompts are registered by the evaluator job**, not the orchestrator. The evaluator calls `register_judge_prompts()` on iteration 1 and `load_judge_prompts()` on every iteration. The orchestrator passes `uc_schema` as a job parameter so the evaluator can construct prompt registry names (`{uc_schema}.genie_opt_{name}`).
12. **Every worker invocation MUST read the worker SKILL.md.** The routing table is not advisory — it is mandatory. Before executing any step that maps to a worker, read that worker's SKILL.md file and follow its prescribed workflow. Do NOT perform the worker's function inline.

    Verification: After completing a worker step, confirm you read:
    - The worker SKILL.md
    - At least one reference file loaded via a `Load:` directive
13. **Dual persistence is verified, not assumed.** After applying any proposal, confirm BOTH the API command succeeded AND the repository file was modified. Run `git diff` on the repo file to verify. If the repo file was not updated, the proposal is NOT complete — stop and fix before proceeding to re-evaluation.
14. **Proposals MUST be applied in lever priority order (1 → 6).** Re-evaluate after each lever group. Do not invoke GEPA (L2) for Lever 6 until Levers 1-5 are exhausted and scores are still below target. Lever 6 is a last resort with limited character budget (~4000 chars). **Exception:** Non-overlapping lever proposals (targeting completely different question sets with zero intersection) MAY be applied in the same iteration to save evaluation cycles. The optimizer MUST verify zero question overlap before combining. Log: "Combining levers {A, B} -- non-overlapping question sets verified."
15. **Optimization decisions MUST be based on per-row evaluation data**, not aggregate metrics. **Per-judge scores are also available as top-level MLflow run metrics** (`eval_{judge}_pct` in 0-100 scale) via `mlflow.get_run(run_id).data.metrics`, logged by the evaluator. The evaluator emits `evaluation/failures.json` and `evaluation/arbiter_actions.json` as MLflow artifacts. Download and parse these before generating proposals. Use `cluster_failures()` with the per-row data, not synthesized fallback rows.
16. **Arbiter verdicts MUST be triaged after every evaluation.** If `genie_correct >= 3`, load the Generator worker to update benchmark expected SQL. All `ground_truth_correct` verdicts are confirmed failures and must be passed to `cluster_failures()`.
17. **LoggedModel MUST be created via `create_external_model()` inside a creation run.** This ensures: (a) "Logged From" in the UI points to the creation run (`source_run_id`), (b) all artifacts are persisted in the run (not silently dropped), (c) evaluation runs link back via `mlflow.genai.evaluate(model_id=...)`. **Artifact layout per creation run:**
    - `model_state/genie_config.json` — full Genie Space config
    - `model_state/uc_columns.json` — complete rows from `information_schema.columns`
    - `model_state/uc_tags.json` — complete rows from `information_schema.table_tags`
    - `model_state/uc_routines.json` — complete rows from `INFORMATION_SCHEMA.ROUTINES`
    - `model_state/uc_metadata_diff.json` — structured diff vs parent model (added/removed/modified columns, tags, routines)
    - `patches/patch_set.json` — full Patch DSL array (when patches applied)
    - `patches/patch_summary.json` — structured summary by type, lever, risk, and targets
    **Params for filtering:** `patch_levers`, `patch_targets`, `uc_columns_changed`, `uc_tags_changed`, `uc_routines_changed`.
    **Model-level metrics:** After every evaluation, `link_eval_scores_to_model(model_id, eval_result)` logs per-judge scores (`overall_accuracy`, `schema_accuracy`, `logical_accuracy`, etc.) and `repeatability_pct` as model-level metrics via `mlflow.log_metrics(metrics=..., model_id=...)`. This enables cross-model comparison in the Models tab and filtering via `search_logged_models(filter_string="metrics.schema_accuracy >= 80")`.
    **Do NOT use `set_active_model()` for creation** — it does not set `source_run_id` and leaves "Logged From" empty; `mlflow.log_artifact()` outside a run context silently drops artifacts. After `create_external_model()`, call `set_active_model(model_id=...)` to link subsequent traces. `rollback_to_model()` downloads `model_state/genie_config.json` from the creation run via `model.source_run_id`. Concrete implementations: `create_genie_model_version()` (~line 274), `_compute_uc_metadata_diff()` (~line 315), `link_eval_scores_to_model()` (~line 414), `promote_best_model()` (~line 570), `rollback_to_model()` (~line 603) in `orchestrator.py`.
18. **Proposals MUST be applied via `apply_patch_set()` (Patch DSL)** for programmatic execution and rollback. Do NOT use `apply_proposal_batch()` which returns `pending_agent_execution` and requires manual intervention. The `use_patch_dsl` flag (default `True`) controls this in session state. Store `apply_log` in iteration results for precise rollback. **Bridge:** When the optimizer emits `proposals` (ASI-enriched dicts) instead of `patches`, use `proposals_to_patches()` to convert them into Patch DSL format via `_lever_to_patch_type` mapping before calling `apply_patch_set()`.
19. **Cross-iteration repeatability MUST be computed from iteration 2 onward.** Compare per-question SQL hashes between current and previous iteration before proceeding to the next lever. This is free (no API calls) and mandatory. Questions whose SQL changed AND were previously correct are flagged as `repeatability_issue` synthetic failures. See `_compute_cross_iteration_repeatability()` in `orchestrator.py`.
20. **Optimization report MUST be generated as a mandatory final step in Phase 4.** Use the applier's `assets/templates/optimization-report.md` template. Populate from MLflow experiment data (per-iteration metrics, judge breakdown, config diffs) + `golden-queries.yaml` + config files. Emit the report as an MLflow artifact.
21. **Evaluator MUST persist per-row ASI to `genie_eval_asi_results` UC Delta table after every evaluation.** The optimizer MUST read from this UC table as its primary ASI source via `read_asi_from_uc()`. Fallback chain: UC table -> `{judge}/metadata` columns -> assessments list -> regex on rationale. Without UC table persistence, structured ASI from judges is lost at the `mlflow.genai.evaluate()` serialization boundary and the optimizer falls back to unreliable regex parsing.
22. **Evaluator MUST configure UC trace storage via `UCSchemaLocation` + `set_experiment_trace_location()` before evaluation.** Requires `mlflow[databricks]>=3.9.0`. This enables SQL-queryable traces governed by Unity Catalog access controls, cross-experiment dashboards, and correlation with the `genie_eval_asi_results` table.
23. **`--job-mode` is REQUIRED for lever-aware optimization.** The inline evaluator (`run_evaluation_iteration()`) only checks asset routing (1 judge). It does NOT run the 8-judge `mlflow.genai.evaluate()` harness, does NOT produce structured ASI metadata, does NOT write to the UC `genie_eval_asi_results` table, and does NOT create UC evaluation datasets. Without ASI, the optimizer receives no judge feedback and generates empty proposals. The orchestrator raises `RuntimeError` if `lever_aware=True` and `job_mode=False`. The inline evaluator exists only for quick `--evaluate-only` smoke tests.

## Section 3: Routing Table (MANDATORY)

> **Every row in this table is a mandatory worker invocation, not a suggestion.** When the situation matches, you MUST load the corresponding worker's SKILL.md and follow its workflow. See hard constraint #12.

| Situation | Worker to Load | Inputs | Expected Outputs |
|-----------|---------------|--------|-----------------|
| Need benchmarks (Step 1) | `genie-benchmark-generator` | space_id, domain, uc_schema | eval_dataset_name, yaml_path |
| Need evaluation (Step 3/6) | `genie-benchmark-evaluator` | space_id, eval_dataset, experiment, iteration, uc_schema, eval_scope="full" | eval_results, scores, judge_feedback |
| Scores below target (Step 4) | `genie-metadata-optimizer` | eval_results, judge_feedback, metadata_snapshot, use_asi, use_patch_dsl | patch_set, lever_mapping, proposals |
| Apply changes (Step 5) | `genie-optimization-applier` | space_id, patch_set, space_config, use_patch_dsl | apply_log, apply_status |
| **After apply: slice eval** | `genie-benchmark-evaluator` | space_id, eval_scope="slice", patched_objects | slice_results (cheap verification) |
| **After slice passes: P0 gate** | `genie-benchmark-evaluator` | space_id, eval_scope="p0" | p0_results (hard constraint) |
| **P0 gate fails: rollback** | `genie-optimization-applier` | space_id, rollback=True, apply_log | rollback_status |
| Deploy bundle (Step 7) | `genie-optimization-applier` | space_id, domain, deploy_target | deploy_status |
| **Post-deploy: overfitting check** | `genie-benchmark-evaluator` | space_id, eval_scope="held_out" | held_out_results |
| Post-deploy verify (Step 8) | `genie-benchmark-evaluator` | space_id, eval_dataset, iteration=999, uc_schema | post_deploy_results |
| **Arbiter corrected >=3 GTs** | `genie-benchmark-generator` | corrected_questions | updated yaml_path |
| Repeatability test | `genie-benchmark-evaluator` | space_id, iterations=3, uc_schema | repeatability_pct |

### Worker Paths (Relative)

| Worker | SKILL.md Path |
|--------|-------------|
| Generator | `../genie-optimization-workers/01-genie-benchmark-generator/SKILL.md` |
| Evaluator | `../genie-optimization-workers/02-genie-benchmark-evaluator/SKILL.md` |
| Optimizer | `../genie-optimization-workers/03-genie-metadata-optimizer/SKILL.md` |
| Applier | `../genie-optimization-workers/04-genie-optimization-applier/SKILL.md` |

## Section 4: Loop Logic (Lever-Aware)

```
function optimize(space_id, domain):
    session = init_progress(space_id, domain)  # or load_progress() to resume
    _verify_mlflow_tracking()

    if session.current_iteration == 0:
        load Generator → create benchmarks (with splits) → sync to MLflow
        register_judge_prompts(session.experiment_name, domain)

    # ─── Step 0b: Verify Space State ──────────────────────────
    config = GET /api/2.0/genie/spaces/{space_id}?include_serialized_space=true
    Log: tables={N}, metric_views={N}, tvfs={N}, instructions={present/absent}
    If serialized_space is empty → space is genuinely unconfigured, deploy first
    If serialized_space has assets → space is configured, proceed to evaluation

    # ─── Step 0c: Benchmark Temporal Freshness Check ────────────
    stale = _check_temporal_freshness(benchmarks)
    for s in stale:
        WARN: "{s.question_id} has hardcoded dates but temporal phrasing —
               GT may be stale. Consider dynamic date expressions."
    if stale:
        Log: "{len(stale)} benchmarks flagged for potential date staleness"

    # ─── Phase 1: Evaluate Baseline ─────────────────────────────
    config = _fetch_space_config(space_id)
    model_id = create_genie_model_version(space_id, config, 0, domain)
    load Evaluator → evaluate(iteration=0, model_id, eval_scope="full") → baseline_scores
    update_progress(session, baseline_scores)
    prev_scores = baseline_scores

    if all_thresholds_met(baseline_scores):
        session.status = "converged"
        → skip to Phase 4

    # ─── Phase 2: Per-Lever Optimization (priority order) ──────

    # **CRITICAL: NEVER apply multiple levers in the same iteration.**
    # Each lever gets its own evaluate-measure-decide cycle. Combining levers
    # (e.g., Lever 1 + Lever 6) confounds impact measurement — you cannot
    # determine which lever drove the improvement. This is the most common
    # mistake in optimization sessions.

    # lever_audit tracks per-lever attempts for hard constraint #14 enforcement
    lever_audit = {1..6: {attempted, proposals_generated, proposals_applied, skip_reason}}

    for lever in [1, 2, 3, 4, 5]:
        if all_thresholds_met(prev_scores):
            break  # Converged — no need for lower-priority levers

        lever_audit[lever].attempted = True

        # 2a. Download per-row failures artifact (hard constraint #15)
        #     Use evaluation/failures.json, not aggregate metrics
        load Optimizer → introspect(failures_artifact, target_lever=lever, use_asi=True) → proposals
        lever_audit[lever].proposals_generated = len(proposals)
        if not proposals:
            lever_audit[lever].skip_reason = "no_proposals_generated"
            continue  # No issues mapped to this lever

        # 2b. Apply proposals via apply_patch_set() (hard constraint #18)
        patches = proposals_to_patches(proposals)
        load Applier → apply_patch_set(space_id, patches, space_config, use_patch_dsl=True) → apply_log
        VERIFY: For each applied proposal (hard constraint #13):
          - API command executed successfully
          - Repository file updated (git diff shows change)
          If any repo file NOT updated → STOP and fix before proceeding

        wait(30)  # Propagation delay

        # 2c. Re-evaluate after this lever
        config = _fetch_space_config(space_id)
        model_id = create_genie_model_version(space_id, config, lever, domain,
            patch_set=proposals, parent_model_id=prev_model_id)
        load Evaluator → evaluate(eval_scope="full") → lever_scores

        # 2d. Track per-lever impact
        log_lever_impact(session, lever, before=prev_scores, after=lever_scores, proposals)

        # 2e. Regression check — revert if this lever hurt accuracy
        if regression_detected(prev_scores, lever_scores):
            load Applier → rollback(apply_log, space_id)
            continue  # Skip this lever, move to next

        # 2f. Cross-iteration repeatability (hard constraint #19)
        if session.current_iteration >= 2:
            cross_rep = _compute_cross_iteration_repeatability(prev_rows, current_rows)
            if cross_rep.changed_questions:
                synth_failures = _synthesize_repeatability_failures_from_cross_iter(cross_rep)
                # Inject into next lever's cluster_failures()

        # 2g. Check for gt_correction_threshold_reached (arbiter auto-persistence)
        if lever_scores.get("gt_correction_threshold_reached"):
            load Generator → review and regenerate affected benchmarks
        if lever_scores.get("gt_remediation_queue"):
            load Generator → replace questions from gt_remediation_queue.yaml

        # 2h. VERIFY: lever N-1's evaluation is recorded before starting lever N
        assert lever in session.lever_audit and session.lever_audit[lever].attempted

        prev_scores = lever_scores
        session.current_iteration += 1

    # ─── Phase 3: GEPA for Lever 6 (only if still below target) ─
    # Lever exhaustion gate: warn if any levers 1-5 were not attempted (hard constraint #14)
    for lv in [1, 2, 3, 4, 5]:
        if not lever_audit[lv].attempted and not lever_audit[lv].skip_reason:
            WARNING: "Lever {lv} never attempted before GEPA"
    if not all_thresholds_met(prev_scores):
        load Optimizer → run_gepa(scores, target_lever=6) → lever_6_candidate
        if lever_6_candidate:
            load Applier → apply(lever_6_candidate, dual_persist=True)
            VERIFY: dual persistence (hard constraint #13)
            load Evaluator → evaluate(eval_scope="full") → gepa_scores
            log_lever_impact(session, lever=6, before=prev_scores, after=gepa_scores)
            if regression_detected(prev_scores, gepa_scores):
                load Applier → rollback(apply_log, space_id)

    # ─── Phase 4: Deploy and Verify ────────────────────────────
    promote_best_model(session)

    if deploy_target:
        load Applier → deploy_bundle(target)
        load Evaluator → evaluate(eval_scope="held_out") → overfitting check
        load Evaluator → post_deploy_verify(iteration=999)

    # Handle arbiter corrections
    if len(session.benchmark_corrections) >= 3:
        load Generator → update benchmarks with corrections

    # Generate optimization report (hard constraint #20)
    # Template lives in the applier worker:
    #   ../genie-optimization-workers/04-genie-optimization-applier/assets/templates/optimization-report.md
    generate_report(session, domain, output_dir)  # Includes per-lever impact section
    return session
```

### Convergence Criteria

| Condition | Action |
|-----------|--------|
| All judges meet targets | Proceed to deploy |
| Improving after 5 iterations | Accept, document remaining issues |
| No improvement for 2 iterations | Escalate — LLM limitation likely |
| Regression detected | Revert last change, try alternative |

## Progress Tracking & Long-Running Sessions

The optimization loop can run for up to 2.5 hours across 5 iterations. To maintain coherence across context windows, the agent maintains `optimization-progress.json`:

- **On startup:** Read progress file + git log + MLflow experiment to reconstruct state
- **Per iteration:** Update with scores, proposals, regressions, next action
- **On completion:** Write final scores and convergence reason

See [optimization-progress.json template](assets/templates/optimization-progress.json) for the schema.

## Quality Dimensions

| Dimension | Target | Judge Type | Judge Name |
|-----------|--------|------------|------------|
| Syntax Validity | 98% | Code | `syntax_validity_scorer` |
| Schema Accuracy | 95% | LLM | `schema_accuracy_judge` |
| Logical Accuracy | 90% | LLM | `logical_accuracy_judge` |
| Semantic Equivalence | 90% | LLM | `semantic_equivalence_judge` |
| Completeness | 90% | LLM | `completeness_judge` |
| Result Correctness | 85% | Code | `result_correctness` |
| Asset Routing | 95% | Code | `asset_routing_scorer` |
| Arbiter (conditional) | n/a | LLM | `arbiter_scorer` |
| Repeatability | 90% | Code (cross-iteration + Cell 9c final) | `repeatability_scorer` |

The **Pareto frontier** tracks 4 objectives: `correctness` (up), `repeatability` (up), `regressions` (down), `patch_cost` (down). **During the loop** (iteration 2+), repeatability is measured via cross-iteration SQL comparison (free -- no extra queries). **After all iterations**, a final dedicated Cell 9c re-query test measures true point-in-time repeatability. Non-repeatable questions are synthesized as `repeatability_issue` failures and routed to Lever 1 (structured metadata: tags, column comments) for TABLE/MV assets, or Lever 6 (instructions) for TVF assets.

## Scripts

### [orchestrator.py](scripts/orchestrator.py)

```bash
python scripts/orchestrator.py --discover
python scripts/orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --uc-schema catalog.schema
python scripts/orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --resume
python scripts/orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --evaluate-only
python scripts/orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --job-mode --target dev
python scripts/orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --lever-aware --worker-dir ../genie-optimization-workers
python scripts/orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --no-lever-aware
python scripts/orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --deploy-target dev
```

### [test_optimization_e2e.py](scripts/test_optimization_e2e.py)

End-to-end integration test script covering the full optimization loop across all 4 workers.

## Validation Checklist

### Preconditions (STOP if any fail)

- [ ] Correct Space ID identified and `GET /api/2.0/genie/spaces/{id}` returns 200
- [ ] **MLflow experiment created** — experiment URL printed
- [ ] **MLflow tracking URI is `databricks`** — not local filesystem
- [ ] **Judge prompts registered** — `register_prompts_*` run visible
- [ ] User prompted for benchmarks before synthetic generation
- [ ] Ground truth SQL validated via `spark.sql()`
- [ ] Benchmarks with temporal phrasing checked for date staleness (`_check_temporal_freshness()`)
- [ ] Benchmarks synced to MLflow Evaluation Dataset

### Per-Iteration Gates

- [ ] **LoggedModel created BEFORE evaluation** with `patch_set`, `parent_model_id`, `prompt_versions` params
- [ ] **`mlflow.genai.evaluate()` used** — NOT manual metric logging
- [ ] **MLflow run exists** with `genie_eval_iter{N}_{timestamp}` name
- [ ] Params logged: `space_id`, `iteration`, `dataset`, `num_scorers`, `eval_scope`
- [ ] Per-judge metrics and `thresholds_passed` logged
- [ ] All scorers use `@scorer` only (NO `@mlflow.trace` stacking)
- [ ] Arbiter invoked on Layer 2 disagreements
- [ ] Slice eval runs after apply (eval_scope="slice")
- [ ] P0 gate runs after slice passes (eval_scope="p0")
- [ ] Rollback triggered if P0 gate fails
- [ ] `optimization-progress.json` updated with `score_history`, `patch_history`

### Postconditions

- [ ] Every control lever change uses dual persistence
- [ ] Full-suite re-benchmark after every change
- [ ] `databricks bundle deploy` + `genie_spaces_deployment_job` succeeds
- [ ] Post-deploy re-assessment confirms results match
- [ ] **MLflow experiment has: registered judges, evaluation runs, prompt artifacts, traces, datasets**

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Running evaluation without MLflow | Invisible run | `mlflow.set_experiment()` + `mlflow.start_run()` |
| Manual metric logging | Evaluation tab empty | Use `mlflow.genai.evaluate()` |
| Missing MLflow env vars (local/CLI) | Silent local file store | Set `DATABRICKS_HOST`, `TOKEN`, `TRACKING_URI` |
| Loading all reference files upfront | Context rot | Use `Load:` directives per step |
| Registering prompts or syncing datasets from the orchestrator CLI | Duplicated work (evaluator job already does this), plus CLI may lack Spark/dbutils context | Orchestrator only computes `eval_dataset_name` string and passes it as a job param; evaluator owns creation (hard constraint #9) |
| Bare experiment path `/genie-optimization/...` | `RESOURCE_DOES_NOT_EXIST` | Use `/Users/<email>/genie-optimization/...` and pre-create parent via `databricks workspace mkdirs` |
| Wrong CLI profile | `403 You need "Can View" permission` | Read `databricks.yml` for `workspace.profile`, verify with `databricks genie list-spaces --profile <profile>` |
| Skipping worker SKILL.md and analyzing inline | Inconsistent with prescribed workflow, missed reference patterns | Always read worker SKILL.md before proceeding (hard constraint #12) |
| API-only update without repo file change | Lever 1-5 changes lost on next `databricks bundle deploy` | Verify BOTH API + repo file via `git diff` (hard constraint #13) |
| Applying Lever 6 (GEPA) before Levers 1-5 | Optimization budget wasted on lowest-priority lever | Apply in lever order 1→6, re-evaluate after each lever (hard constraint #14) |
| Optimizing from aggregate metrics only | Untargeted changes that may not fix root cause | Download per-row `evaluation/failures.json` artifact and use `cluster_failures()` (hard constraint #15) |
| Ignoring arbiter verdicts | Stale benchmarks degrade measured accuracy | Check arbiter threshold, route corrections to Generator (hard constraint #16) |
| GET space without `?include_serialized_space=true` | Space appears empty, unnecessary redeployment | Always include query parameter in `_fetch_space_config()` |
| Skipping LoggedModel creation | No config snapshots, no rollback capability | Ensure `create_genie_model_version()` returns non-None `model_id` before evaluation (hard constraint #17) |
| Using `apply_proposal_batch()` instead of `apply_patch_set()` | Changes not actually applied, agent must manually execute | Set `use_patch_dsl=True` and call `apply_patch_set()` for programmatic apply + rollback (hard constraint #18) |
| Running lever-aware optimization without `--job-mode` | Inline evaluator only checks routing (1 judge), optimizer gets no ASI, generates empty proposals | Always use `--job-mode --target dev` for optimization (hard constraint #23). Inline is only for quick `--evaluate-only` smoke tests |
| Running Cell 9c re-query on every iteration | Wastes ~24s per question of API budget per iteration | Cell 9c only fires in the final dedicated test (Phase 3b); during the loop, cross-iteration SQL comparison provides free repeatability signal |
| Routing all repeatability issues to TVFs (Lever 3) | Misses root cause when unstructured metadata creates ambiguous search space | Route TABLE/MV to Lever 1 (structured metadata: tags, column comments) first; TVF conversion is secondary |
| Applying overlapping levers in same iteration | Cannot determine which lever drove improvement — confounded measurement | One lever per iteration unless question sets are non-overlapping (verify zero intersection, log warning). See HC #14 exception |
| Skipping cross-iteration repeatability in iteration 2+ | SQL-changing regressions go undetected until final Cell 9c test | Compute `_compute_cross_iteration_repeatability()` after every evaluation from iteration 2 onward (hard constraint #19) |
| Skipping Lever 3 (TVF negative routing) when Lever 1/2 alone don't resolve oscillation | Disambiguation is one-sided — preferred asset has positive routing but competing asset still claims the question | Bilateral: positive routing (Lever 1/2) tells the preferred asset it IS the right choice; negative routing (Lever 3) tells the competing asset it is NOT. Both sides must be addressed. |
| Treating routing regressions as metadata failures when bilateral disambiguation is already applied | Infinite metadata iteration loop with no convergence | Genie routing is probabilistic (KGL-2). After bilateral disambiguation, run 3-5 passes for routing-sensitive questions. If variance > 40%, document as platform limitation and stop iterating. |
| Repeatedly proposing column comments for complex temporal expressions ("last quarter", "YoY") | Metadata changes have no effect, wasting 2+ iterations | Check optimizer's Metadata Effectiveness table. LOW-effectiveness patterns need escalation: TVF with temporal parameter or pre-computed columns (KGL-3). Column comments only work for simple patterns ("this year", "last N days"). |

## Repeatability

Two distinct mechanisms measure repeatability at different points in the optimization lifecycle:

### 1. Cross-Iteration SQL Hash Comparison (Free, Iteration 2+)

Computed by `_compute_cross_iteration_repeatability()` after every evaluation from iteration 2 onward. Compares per-question SQL hashes between current and previous iteration. Questions whose SQL changed AND were previously correct are flagged as `repeatability_issue` synthetic failures and injected into `cluster_failures()`.

- **Timing:** After every evaluation, iteration 2+
- **Data needed:** Current and previous iteration `rows` data (from evaluator output)
- **Cost:** Zero (no API calls — pure hash comparison)
- **Output:** Synthetic failure rows with `failure_type="repeatability_issue"`, `blame_set` pointing to dominant asset type

### 2. Cell 9c Re-Query Test (Expensive, Phase 3b Final Only)

Fires once after all levers complete, gated behind `run_repeatability=true`. Re-queries Genie 2 extra times per question (~24s each). Computes per-question SQL consistency via MD5 hash comparison across the 3 runs (original + 2 retries). Results emitted as `evaluation/repeatability.json` artifact and per-trace assessments via `mlflow.log_assessment()`.

- **Timing:** Phase 3b, after all optimization levers complete and GEPA finishes
- **Data needed:** Active Genie Space, rate limit budget
- **Cost:** `N_questions * 2 * ~24s` (expensive)
- **Output:** `repeatability/mean` metric, `evaluation/repeatability.json` artifact, per-trace assessments in MLflow Evaluations UI

### Handoff Between Mechanisms

During the optimization loop (Phase 2), only cross-iteration comparison is used — it provides a free signal for detecting SQL instability between lever applications. After the loop ends and GEPA completes (Phase 3b), Cell 9c fires for a final dedicated point-in-time repeatability test. Cross-iteration comparison feeds synthetic failures to the optimizer for targeted fixes; Cell 9c produces the final repeatability score for the Pareto frontier.

## Version History

- **v4.3.0** (Feb 23, 2026) - Phase 8: Optimization loop feedback (Issues 14-16). 2 new Common Mistakes: probabilistic routing regression loop (KGL-2) and complex temporal expression re-proposal (KGL-3). Cross-references to optimizer's Known Genie Limitations table for escalation.
- **v4.2.0** (Feb 23, 2026) - Phase 7: ASI-to-metadata loop gap remediation (13 issues). HC #14 expanded with non-overlapping lever exception (zero question-set intersection allows combining). Phase 0c benchmark temporal freshness check added (`_check_temporal_freshness()` in orchestrator.py). HC #15 expanded with per-judge metric data contract (`eval_{judge}_pct` logged by evaluator). Common Mistake row updated for non-overlapping levers. Validation Checklist updated with date staleness precondition.
- **v4.1.0** (Feb 23, 2026) - Enrich LoggedModel for cross-model comparison. **Structured Patch DSL:** Patches now logged under `patches/` with both full `patch_set.json` and `patch_summary.json` (breakdowns by type, lever, risk, with target list). New filterable params: `patch_levers`, `patch_targets`. **UC metadata diffs:** `_compute_uc_metadata_diff()` downloads parent model's UC metadata via `source_run_id`, computes added/removed/modified rows for columns, tags, and routines, logs `model_state/uc_metadata_diff.json` + `uc_columns_changed`/`uc_tags_changed`/`uc_routines_changed` metrics. **Model-level judge scores:** `link_eval_scores_to_model()` called after every evaluation to log per-judge scores (`overall_accuracy`, `schema_accuracy`, etc.) and `repeatability_pct` as model-level metrics via `mlflow.log_metrics(model_id=...)`, enabling comparison in the Models tab and `search_logged_models()` filtering. Updated HC #17 with full artifact layout.
- **v4.0.0** (Feb 23, 2026) - Phase 6 architectural lessons (7 lessons). Added HC #21 (ASI UC table contract: evaluator MUST persist per-row ASI to `genie_eval_asi_results`; optimizer reads via `read_asi_from_uc()`). Added HC #22 (UC trace storage via UCSchemaLocation). Expanded HC #18 with `proposals_to_patches()` bridge for ASI-enriched proposals. Added Common Mistake for bilateral disambiguation (Lever 3 negative routing). Version bumped from v3.9.0.
- **v3.12.0** (Feb 22, 2026) - Fix LoggedModel creation to use `create_external_model()` inside `mlflow.start_run()`. Previous `set_active_model()` approach left "Logged From" empty (no `source_run_id`), silently dropped artifacts (`log_artifact()` outside a run context is a no-op), and prevented `rollback_to_model()` from downloading config artifacts. Now: creation run persists full UC metadata as artifacts (`model_state/uc_columns.json` with complete `information_schema` rows, not just counts), `source_run_id` links the LoggedModel to its creation run ("Logged From" populated), evaluation runs link via `mlflow.genai.evaluate(model_id=...)` ("Runs linked" populated). `rollback_to_model()` updated to download from `model_state/` artifact path and guard against missing `source_run_id`. Updated HC #17.
- **v3.11.0** (Feb 22, 2026) - Consolidate MLflow setup into the evaluator job. Removed orchestrator-side `sync_yaml_to_mlflow_dataset()` and `_register_judge_prompts_to_experiment()` — both are redundant with the evaluator notebook which already creates UC datasets (Cell 3b), registers prompts (Cell 5), and configures UC traces (Cell 2). Orchestrator now only computes `eval_dataset_name` as a naming convention string and passes it as a job parameter. Arbiter correction helper no longer re-syncs to UC; the next evaluator job run picks up the corrected `benchmarks.yaml` automatically. Removed ~75 lines of dead code. Updated hard constraints #9 and #11 to clarify evaluator-job ownership. Updated Common Mistakes table.
- **v3.10.0** (Feb 22, 2026) - Enforce `--job-mode` as hard requirement for lever-aware optimization. Removed `--inline-routing-only` flag — inline evaluator (`run_evaluation_iteration()`) only checks asset routing (1 judge) and does not produce ASI, UC datasets, or UC traces; optimizer would receive zero judge feedback. Orchestrator now raises `RuntimeError` instead of silently downgrading. Added hard constraint #23. Added Common Mistake row.
- **v3.9.0** (Feb 22, 2026) - Phase 5 feedback remediation (18 errors + 4 patterns). Added standalone lever-sequencing warning (CRITICAL: one lever per iteration). Added HC #19 (mandatory cross-iteration repeatability from iteration 2), HC #20 (mandatory optimization report generation in Phase 4). Expanded HC #17 to require full model state (Genie config + UC columns + tags + INFORMATION_SCHEMA.ROUTINES) with evaluator auto-creation fallback. Added lever-gate verification step, gt_remediation_queue consumption, and report generation to pseudocode. Added 2 new Common Mistakes rows. Added standalone Repeatability section documenting both mechanisms (cross-iteration + Cell 9c) and handoff.
- **v3.8.0** (Feb 22, 2026) - Repeatability v2: cross-iteration comparison and structured metadata routing. **Cross-iteration repeatability:** `_run_eval` no longer auto-enables `run_repeatability` on every full-scope eval; instead, from iteration 2+, `_compute_cross_iteration_repeatability()` compares per-question SQL hashes with the previous iteration (free, no extra queries). Only questions whose SQL changed AND were previously correct are flagged as concerning. Cell 9c re-query test fires once in Phase 3b (final dedicated test after all levers). **Structured metadata routing:** `_synthesize_repeatability_failures()` and `_synthesize_repeatability_failures_from_cross_iter()` now recommend structured metadata (business_definition, synonyms, join_keys, do_not_use_when, UC tags) for TABLE/MV assets instead of TVF conversion. Optimizer routing changed: TABLE/MV → Lever 1 (structured metadata), TVF → Lever 6 (instructions). Common mistakes updated.
- **v3.7.0** (Feb 22, 2026) - Repeatability judge integration (Approach C: Combined). Evaluator: Cell 9c post-evaluation repeatability check added to `run_genie_evaluation.py` — re-queries each question 2 extra times, computes SQL consistency via MD5 hash, emits `evaluation/repeatability.json` artifact and `repeatability/mean` metric; gated behind `run_repeatability` widget/job parameter. Orchestrator: `init_progress()` now tracks `repeatability_pct`, `best_repeatability`, and `repeatability_target` (90%); `_run_eval` enables repeatability for full-scope evaluations; `run_evaluation_via_job()` downloads repeatability artifacts; `_update_pareto_frontier()` includes `repeatability` dimension; `_synthesize_repeatability_failures()` converts non-repeatable questions into synthetic failure rows with ASI metadata (`failure_type="repeatability_issue"`, `blame_set` pointing to dominant asset type) for the optimizer; version bumped to v3.7.0. Optimizer: `_map_to_lever()` now maps `repeatability_issue` to lever 3 (TVFs — TVF-first design constrains LLM output, reducing SQL variance); `_describe_fix()` generates asset-type-specific recommendations for repeatability clusters (MV→TVF conversion, TABLE→TVF wrapper, TVF→instruction clarification).
- **v3.6.0** (Feb 22, 2026) - Phase 4 runtime error fixes across evaluator and export-import API skills. Evaluator: JUDGE_PROMPTS rewritten to use only `make_judge()` allowed template variables (`{{ inputs }}`, `{{ outputs }}`, `{{ expectations }}`); `_sanitize_prompt_for_make_judge()` safety net added; `genie_predict_fn` signature fixed to keyword-args pattern matching `mlflow.genai.evaluate()` unpacking behavior; hard constraints #9-10 and 3 new Common Mistakes added. Export-import API: Section 8 sort keys corrected from `table_name`/`function_name` to `identifier`/`id`; `sort_all_arrays()` replaced with canonical `sort_genie_config()`. MLflow GenAI Evaluation skill: `make_judge()` template variable constraints and `predict_fn` keyword argument contract documented.
- **v3.5.0** (Feb 22, 2026) - Wire the producer-consumer data pipeline end-to-end (Phase 3 feedback, Gaps 16-21). **Gap 16 (P0):** Evaluator now emits `evaluation/eval_results.json`, `evaluation/failures.json`, and `evaluation/arbiter_actions.json` as MLflow artifacts with full per-row data including ASI metadata; orchestrator downloads these artifacts in `run_evaluation_via_job()` and passes rich data to `cluster_failures()`. **Gap 17 (P0):** `question_id` added to eval record inputs (fixes empty `failure_ids`); arbiter threshold check added after every evaluation — if `genie_correct >= 3`, sets `benchmark_correction_needed` flag and stores `corrected_questions` for Generator. **Gap 18 (P1):** LoggedModel lifecycle hardened — evaluator now prints WARNING when `model_id` is None; `references/logged-model-lifecycle.md` created with implementation pointers and data flow diagram; job template YAML commented. **Gap 19 (P1):** `lever_audit` dict added to session state tracking per-lever attempts, proposals generated/applied, and skip reasons; lever exhaustion gate before GEPA warns if any levers 1-5 were never attempted; per-lever proposal examples added to optimizer `feedback-to-metadata-mapping.md`. **Gap 20 (P1):** `_fetch_space_config()` now uses `?include_serialized_space=true` with asset count logging; Step 0b added to loop pseudocode; export-import API table fixed. **Gap 21 (P2):** Output JSON now includes `total_questions`, `rows`, and `arbiter_actions`. **Patch DSL wiring:** `apply_patch_set()` now called in lever loop (replacing `apply_proposal_batch()`), GEPA patches routed through Patch DSL, `rollback()` wired alongside `rollback_to_model()`, `use_patch_dsl` flag added to session state. **ASI-aware clustering:** `cluster_failures()` now prefers `failure_type`/`blame_set` from ASI metadata over keyword extraction; `_describe_fix()` uses `counterfactual_fix`; `_map_to_lever()` accepts ASI failure type. **Hard constraints #15-18** added. 5 new common mistakes.
- **v3.4.0** (Feb 21, 2026) - Data contracts and score scales: Fix 5 issues from v3.3.0 rerun audit. **P0 fixes:** (1) Optimizer now receives full iteration result with row-level feedback instead of empty failure ID list — `cluster_failures()` gets row dicts with `feedback/*` and `rationale/*` columns, with fallback synthesis from failure IDs when rich data unavailable. (2) `_normalize_scores()` helper converts per-judge 0-1 scores to 0-100 at evaluation boundary so `all_thresholds_met()` compares like-for-like — applied in both `run_evaluation_via_job()` and `run_evaluation_iteration()`. (3) P0 gate now checks signal quality — warns if `eval_scope="p0"` returns zero total questions (gate inconclusive, not silent pass). **P1 fixes:** (4) Generator dataset contract wired into orchestrator — `sync_yaml_to_mlflow_dataset()` called at startup when `uc_schema` is set, `eval_dataset_name` stored in progress and passed through to evaluator (honors hard constraint #9). (5) `patched_objects` now Base64-encoded in job params to avoid comma-delimiter conflicts; evaluator template decodes `patched_objects_b64` with fallback to legacy `patched_objects` param.
- **v3.3.0** (Feb 21, 2026) - Audit remediation: Enforce gates in code, not prose. **P0 fixes:** (1) Slice→P0 gate sequence now executed in `_run_lever_aware_loop()` between apply and full eval — slice gate fails if accuracy drops >5%, P0 gate fails on any P0 question failure, both trigger rollback. (2) Dual persistence failure upgraded from warning to hard stop (rollback + skip lever). (3) Lever-aware mode without `--job-mode` now raises `RuntimeError` (hardened further in v3.10.0). **P1 fixes:** (4) `trigger_evaluation_job()` and `run_evaluation_via_job()` now pass `eval_scope`, `model_id`, and `patched_objects` through to `databricks bundle run --params`. (5) `_resolve_cli_profile()` reads `databricks.yml` to resolve workspace profile for `WorkspaceClient` initialization. (6) Job template `dataset_mode` default changed from `"yaml"` to `"uc"`. **P2 fixes:** (7) `_validate_experiment_path()` now pre-creates parent directory via `workspace.mkdirs`. (8) `worker_reads` audit trail added to session progress tracking.
- **v3.2.0** (Feb 21, 2026) - Resolved 20 logical inconsistencies from walkthrough audit. `orchestrator.py` rewritten from evaluate-only to lever-aware loop (Phase 1: baseline, Phase 2: per-lever optimize/apply/verify/eval with regression rollback, Phase 3: GEPA lever 6, Phase 4: deploy + held-out). Worker import wiring via `_setup_worker_imports()` with `--worker-dir` CLI. Experiment path default now `/Users/<email>/genie-optimization/<domain>` (hard constraint #7). Rollback made unconditional (no longer gated on `USE_PATCH_DSL`). `rollback_to_model()` artifact path bug fixed. Prompt registration upgraded to `mlflow.genai.register_prompt()` with `@production` alias. Pareto frontier metric renamed from `patch_count` to `patch_cost` (risk-weighted). `_map_to_lever()` extended to levers 4-5 (Monitoring, ML tables). `_convert_patch_set_to_proposals()` uses `_patch_to_lever()` instead of hardcoded lever 6. `verify_repo_update()` detects Databricks runtime and skips git. `dataset_mode` default changed to `"uc"` in evaluator template. `add_benchmark_correction()` helper for arbiter tracking. `test_optimization_e2e.py` created. `--recommended` CLI flag for optimizer feature flags.
- **v3.1.0** (Feb 21, 2026) - Phase 2 feedback: Closing the aspiration-implementation gap (Gaps 10-15). Hard constraints #12 (mandatory worker SKILL.md reads), #13 (dual persistence verified via `git diff`), #14 (lever-priority ordering 1→6). Routing table renamed to MANDATORY. Loop logic rewritten to lever-aware sequence (per-lever optimize→apply→evaluate, GEPA gated on "still below target"). `lever_impacts` tracking, `log_lever_impact()` helper, per-lever impact section in report. `strip_non_exportable_fields()` for PATCH API. GEPA template notebook + job YAML. `target_lever` filter across optimizer and feedback mapping. `verify_repo_update()` and `verify_dual_persistence()` in applier.
- **v3.0.0** (Feb 21, 2026) - Introspective AI refactor: Patch DSL (31 PATCH_TYPES, CONFLICT_RULES), ASI (FAILURE_TAXONOMY, blame_set), evaluation scopes (full/slice/p0/held_out), GEPA L2 with patch set JSON candidates, risk-gated apply with rollback, multi-objective Pareto tracking, tightened LoggedModel integration (parent chain, patch params, promote/rollback), deterministic result normalization (P9), benchmark splits (P12). All new behavior behind feature flags (default OFF).
- **v2.4** (Feb 21, 2026) - Arbiter as MLflow scorer: promoted arbiter from standalone post-hoc function to 8th `@scorer` in `mlflow.genai.evaluate()`. SQL execution lifted into `genie_predict_fn` for zero-redundancy — no scorer calls `spark.sql()`. Arbiter verdicts now appear in MLflow Judges tab, Traces, and Evaluation Runs.
- **v2.3** (Feb 21, 2026) - Prompt Registry integration: judge prompts registered to MLflow Prompt Registry on iteration 1 with dual storage (registry + artifacts), loaded by `@production` alias on every iteration. Added `uc_schema` parameter flow through routing table to evaluator. Prompts tab now populated.
- **v2.2** (Feb 21, 2026) - Deployment feedback fixes: 5 P0 (CLI profile, DABs params, experiment path, template vars, multi-statement SQL) + 4 P1 (mlflow.genai.evaluate, @mlflow.trace, UC datasets, judge registration). Template-checklist divergence eliminated.
- **v2.1** (Feb 21, 2026) - Decomposed into orchestrator + 4 workers
- **v2.0** (Feb 20, 2026) - Introspective AI Architecture
- **v1.2** (Feb 20, 2026) - Interactive benchmark question intake
- **v1.1** (Feb 2026) - Autonomous operations integration
- **v1.0** (Feb 2026) - Initial skill

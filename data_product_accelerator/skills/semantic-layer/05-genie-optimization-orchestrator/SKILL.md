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
  version: "3.4.0"
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

1. **Create** — `create_genie_model_version(space_id, config, N, domain, patch_set, parent_model_id, prompt_versions)` before evaluation
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
9. **Generator MUST produce `eval_dataset_name`.** Agent MUST NOT skip the Generator worker and go directly to the Evaluator. Skipping dataset sync leaves the Datasets and Evaluation tabs empty.
10. **All ground truth SQL containing `${catalog}` or `${gold_schema}`** must be resolved via `resolve_sql()` before execution. Unresolved template variables cause `PARSE_SYNTAX_ERROR`.
11. **Judge prompts MUST be registered to the MLflow Prompt Registry** before the first evaluation. Pass `uc_schema` from the session to the Evaluator worker so it can call `register_judge_prompts()` on iteration 1 and `load_judge_prompts()` on every iteration.
12. **Every worker invocation MUST read the worker SKILL.md.** The routing table is not advisory — it is mandatory. Before executing any step that maps to a worker, read that worker's SKILL.md file and follow its prescribed workflow. Do NOT perform the worker's function inline.

    Verification: After completing a worker step, confirm you read:
    - The worker SKILL.md
    - At least one reference file loaded via a `Load:` directive
13. **Dual persistence is verified, not assumed.** After applying any proposal, confirm BOTH the API command succeeded AND the repository file was modified. Run `git diff` on the repo file to verify. If the repo file was not updated, the proposal is NOT complete — stop and fix before proceeding to re-evaluation.
14. **Proposals MUST be applied in lever priority order (1 → 6).** Re-evaluate after each lever group. Do not invoke GEPA (L2) for Lever 6 until Levers 1-5 are exhausted and scores are still below target. Lever 6 is a last resort with limited character budget (~4000 chars).

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
    session = init_or_resume_session(space_id, domain)
    verify_mlflow_tracking(session.experiment_name)

    if session.current_iteration == 0:
        load Generator → create benchmarks (with splits) → sync to MLflow
        register_judge_prompts(session.experiment_name, domain)

    # ─── Phase 1: Evaluate Baseline ─────────────────────────────
    snapshot = snapshot_genie_metadata(space_id, iteration=0, domain)
    model_id = create_genie_model_version(space_id, config, 0, domain)
    load Evaluator → evaluate(iteration=0, model_id, eval_scope="full") → baseline_scores
    update_session(baseline_scores)
    prev_scores = baseline_scores

    if all_thresholds_met(baseline_scores):
        session.status = "converged"
        → skip to Phase 4

    # ─── Phase 2: Per-Lever Optimization (priority order) ──────
    for lever in [1, 2, 3, 4, 5]:
        if all_thresholds_met(prev_scores):
            break  # Converged — no need for lower-priority levers

        # 2a. Generate proposals for THIS lever only
        load Optimizer → introspect(scores, target_lever=lever, use_asi=True) → proposals
        if not proposals:
            continue  # No issues mapped to this lever

        # 2b. Apply proposals with dual persistence verification
        load Applier → apply(proposals, dual_persist=True) → apply_log
        VERIFY: For each applied proposal (hard constraint #13):
          - API command executed successfully
          - Repository file updated (git diff shows change)
          If any repo file NOT updated → STOP and fix before proceeding

        wait(30)  # Propagation delay

        # 2c. Re-evaluate after this lever
        snapshot = snapshot_genie_metadata(space_id)
        model_id = create_genie_model_version(space_id, config, lever, domain,
            patch_set=proposals, parent_model_id=prev_model_id)
        load Evaluator → evaluate(eval_scope="full") → lever_scores

        # 2d. Track per-lever impact
        log_lever_impact(session, lever, before=prev_scores, after=lever_scores, proposals)

        # 2e. Regression check — revert if this lever hurt accuracy
        if regression_detected(prev_scores, lever_scores):
            load Applier → rollback(apply_log)
            continue  # Skip this lever, move to next

        prev_scores = lever_scores
        session.current_iteration += 1

    # ─── Phase 3: GEPA for Lever 6 (only if still below target) ─
    if not all_thresholds_met(prev_scores):
        load Optimizer → run_gepa(scores, target_lever=6) → lever_6_candidate
        if lever_6_candidate:
            load Applier → apply(lever_6_candidate, dual_persist=True)
            VERIFY: dual persistence (hard constraint #13)
            load Evaluator → evaluate(eval_scope="full") → gepa_scores
            log_lever_impact(session, lever=6, before=prev_scores, after=gepa_scores)
            if regression_detected(prev_scores, gepa_scores):
                load Applier → rollback(apply_log)

    # ─── Phase 4: Deploy and Verify ────────────────────────────
    promote_best_model(session)

    if deploy_target:
        load Applier → deploy_bundle(target)
        load Evaluator → evaluate(eval_scope="held_out") → overfitting check
        load Evaluator → post_deploy_verify(iteration=999)

    # Handle arbiter corrections
    if len(session.benchmark_corrections) >= 3:
        load Generator → update benchmarks with corrections

    generate_report(session)  # Includes per-lever impact section
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
| Repeatability | 90% | Code | `test_repeatability` |

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

End-to-end integration test notebook covering the full optimization loop across all 4 workers.

## Validation Checklist

### Preconditions (STOP if any fail)

- [ ] Correct Space ID identified and `GET /api/2.0/genie/spaces/{id}` returns 200
- [ ] **MLflow experiment created** — experiment URL printed
- [ ] **MLflow tracking URI is `databricks`** — not local filesystem
- [ ] **Judge prompts registered** — `register_prompts_*` run visible
- [ ] User prompted for benchmarks before synthetic generation
- [ ] Ground truth SQL validated via `spark.sql()`
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
| Prompts not registered | No artifacts | Call `register_optimizer_prompts()` in Step 2 |
| Bare experiment path `/genie-optimization/...` | `RESOURCE_DOES_NOT_EXIST` | Use `/Users/<email>/genie-optimization/...` and pre-create parent via `databricks workspace mkdirs` |
| Skipping Generator worker | Datasets tab empty, no versioning | Generator MUST produce `eval_dataset_name` before evaluation |
| Wrong CLI profile | `403 You need "Can View" permission` | Read `databricks.yml` for `workspace.profile`, verify with `databricks genie list-spaces --profile <profile>` |
| Skipping worker SKILL.md and analyzing inline | Inconsistent with prescribed workflow, missed reference patterns | Always read worker SKILL.md before proceeding (hard constraint #12) |
| API-only update without repo file change | Lever 1-5 changes lost on next `databricks bundle deploy` | Verify BOTH API + repo file via `git diff` (hard constraint #13) |
| Applying Lever 6 (GEPA) before Levers 1-5 | Optimization budget wasted on lowest-priority lever | Apply in lever order 1→6, re-evaluate after each lever (hard constraint #14) |

## Version History

- **v3.4.0** (Feb 21, 2026) - Data contracts and score scales: Fix 5 issues from v3.3.0 rerun audit. **P0 fixes:** (1) Optimizer now receives full iteration result with row-level feedback instead of empty failure ID list — `cluster_failures()` gets row dicts with `feedback/*` and `rationale/*` columns, with fallback synthesis from failure IDs when rich data unavailable. (2) `_normalize_scores()` helper converts per-judge 0-1 scores to 0-100 at evaluation boundary so `all_thresholds_met()` compares like-for-like — applied in both `run_evaluation_via_job()` and `run_evaluation_iteration()`. (3) P0 gate now checks signal quality — warns if `eval_scope="p0"` returns zero total questions (gate inconclusive, not silent pass). **P1 fixes:** (4) Generator dataset contract wired into orchestrator — `sync_yaml_to_mlflow_dataset()` called at startup when `uc_schema` is set, `eval_dataset_name` stored in progress and passed through to evaluator (honors hard constraint #9). (5) `patched_objects` now Base64-encoded in job params to avoid comma-delimiter conflicts; evaluator template decodes `patched_objects_b64` with fallback to legacy `patched_objects` param.
- **v3.3.0** (Feb 21, 2026) - Audit remediation: Enforce gates in code, not prose. **P0 fixes:** (1) Slice→P0 gate sequence now executed in `_run_lever_aware_loop()` between apply and full eval — slice gate fails if accuracy drops >5%, P0 gate fails on any P0 question failure, both trigger rollback. (2) Dual persistence failure upgraded from warning to hard stop (rollback + skip lever). (3) Lever-aware mode without `--job-mode` now downgrades to evaluate-only unless `--inline-routing-only` is explicitly set. **P1 fixes:** (4) `trigger_evaluation_job()` and `run_evaluation_via_job()` now pass `eval_scope`, `model_id`, and `patched_objects` through to `databricks bundle run --params`. (5) `_resolve_cli_profile()` reads `databricks.yml` to resolve workspace profile for `WorkspaceClient` initialization. (6) Job template `dataset_mode` default changed from `"yaml"` to `"uc"`. **P2 fixes:** (7) `_validate_experiment_path()` now pre-creates parent directory via `workspace.mkdirs`. (8) `worker_reads` audit trail added to session progress tracking.
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

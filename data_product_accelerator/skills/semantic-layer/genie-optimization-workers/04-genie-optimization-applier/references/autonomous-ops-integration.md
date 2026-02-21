# Autonomous Operations Integration

How the Genie Space optimization loop integrates with `databricks-autonomous-operations` for end-to-end deploy, test, fix, and redeploy cycles.

---

## 1. Three-Phase Deployment Model

The optimization loop uses three deployment phases to balance fast iteration speed with bundle-as-source-of-truth consistency.

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE A: During Optimization Loop (per iteration)          │
│                                                             │
│  1. Apply control lever fix via Direct API/SQL              │
│     - ALTER TABLE ... SET TBLPROPERTIES (levers 1, 4, 5)    │
│     - CREATE OR REPLACE VIEW ... WITH METRICS (lever 2)     │
│     - CREATE OR REPLACE FUNCTION (lever 3)                  │
│     - PATCH /api/2.0/genie/spaces/{id} (lever 6)            │
│                                                             │
│  2. Simultaneously update bundle repository file            │
│     - gold_layer_design/yaml/...  (lever 1)                 │
│     - src/semantic/metric_views/...  (lever 2)              │
│     - src/semantic/tvfs/...  (lever 3)                      │
│     - src/genie/*_genie_export.json  (lever 6)              │
│                                                             │
│  3. Wait 30s → re-test → measure improvement                │
│  4. Loop back if targets not met (max 5 iterations)         │
├─────────────────────────────────────────────────────────────┤
│  PHASE B: After Loop (bundle deploy)                        │
│                                                             │
│  databricks bundle validate -t <target>                     │
│  databricks bundle deploy -t <target>                       │
│                                                             │
│  Pushes all repository file changes to the workspace.       │
├─────────────────────────────────────────────────────────────┤
│  PHASE C: After Deploy (Genie Space job)                    │
│                                                             │
│  databricks bundle run -t <target>                          │
│      genie_spaces_deployment_job                            │
│                                                             │
│  Rebuilds Genie Spaces from src/genie/*_genie_export.json.  │
│  OVERWRITES any direct API patches from Phase A.            │
│  Bundle is now the single source of truth.                  │
├─────────────────────────────────────────────────────────────┤
│  POST-DEPLOY: Re-Assessment                                 │
│                                                             │
│  Re-run benchmarks → confirm bundle-deployed results match  │
│  API-patched results from Phase A.                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Per-Lever Bundle File Mapping

| Lever | Direct Update Command | Bundle Repository File | Rebuilt by Genie Job? |
|-------|----------------------|------------------------|-----------------------|
| **1. UC Tables** | `ALTER TABLE ... SET TBLPROPERTIES` | `gold_layer_design/yaml/{domain}/*.yaml` | No |
| **2. Metric Views** | `CREATE OR REPLACE VIEW ... WITH METRICS` | `src/semantic/metric_views/*.yaml` | No |
| **3. TVFs** | `CREATE OR REPLACE FUNCTION` | `src/semantic/tvfs/*.sql` | No |
| **4. Monitoring** | `ALTER TABLE ... SET TBLPROPERTIES` | `src/monitoring/*.py` | No |
| **5. ML Tables** | `ALTER TABLE ... SET TBLPROPERTIES` | `src/ml/config/*.py` | No |
| **6. Genie Instructions** | `PATCH /api/2.0/genie/spaces/{id}` | `src/genie/{domain}_genie_export.json` | **Yes** |

**"Rebuilt by Genie Job?"** — The `genie_spaces_deployment_job` reads the Genie Space JSON configs and recreates/updates Genie Spaces via the API. Only Lever 6 (Genie Instructions, sample questions, benchmarks, data sources) is managed through this JSON and therefore rebuilt by the job. Levers 1-5 are SQL DDL changes that persist independently in Unity Catalog.

**Critical implication:** If you apply a Lever 6 change via direct API (`PATCH`) but do NOT update `src/genie/*_genie_export.json`, the deployment job will overwrite your change with the stale JSON. Always update both.

---

## 3. Why the Deployment Job Matters

API patches applied during Phase A are **ephemeral** in the context of the deployment lifecycle:

- Next `bundle deploy` + job run will overwrite the Genie Space from bundle JSON
- Other developers deploying the bundle will lose API-only changes
- CI/CD pipelines will recreate Genie Spaces from the bundle

The deployment job ensures:
1. The live Genie Space matches exactly what is in the bundle
2. All environments (dev, staging, prod) can be recreated deterministically
3. Version control captures the full Genie Space configuration

---

## 4. Self-Healing Deploy + Job Pattern

Adapted from `databricks-autonomous-operations` Section 5.

### Step 1: Validate

```bash
databricks bundle validate -t <target>
```

If validate fails, read the error, fix the YAML/JSON, re-validate. Common issues:
- Malformed JSON in Genie export files
- Missing template variable substitution
- Invalid resource references

### Step 2: Deploy

```bash
databricks bundle deploy -t <target>
```

If deploy fails, common causes:
- Auth expired (403) → `databricks auth login --host <url> --profile <name>`
- Path resolution errors → check `databricks.yml` includes
- Resource conflicts → check for name collisions

### Step 3: Run Genie Space Deployment Job

```bash
databricks bundle run -t <target> genie_spaces_deployment_job
```

Parse the RUN_ID from the output URL.

### Step 4: Poll for Completion

```bash
databricks jobs get-run <RUN_ID> --output json | jq -r '.state.life_cycle_state'
# PENDING → RUNNING → TERMINATED
```

When `life_cycle_state == TERMINATED`, check:

```bash
databricks jobs get-run <RUN_ID> --output json | jq -r '.state.result_state'
# SUCCESS → proceed to re-assessment
# FAILED → diagnose
```

### Step 5: Diagnose Failures

If the job fails:

```bash
# Find failed tasks
databricks jobs get-run <RUN_ID> --output json \
  | jq '.tasks[] | select(.state.result_state == "FAILED") | {task: .task_key, run_id: .run_id, error: .state.state_message}'

# Get task output
databricks jobs get-run-output <TASK_RUN_ID> --output json \
  | jq -r '.notebook_output.result // .error // "No output"'
```

Common Genie deployment job failures:

| Error | Cause | Fix |
|-------|-------|-----|
| `data_sources.tables must be sorted` | Arrays not sorted in JSON | Call `sort_genie_config()` on the JSON, save, redeploy |
| `INTERNAL_ERROR: Failed to retrieve schema` | Missing `id` in sql_functions | Add 32-char hex `id` field |
| `Exceeded maximum number (50)` | Too many TVFs/benchmarks | Truncate to 50 |
| `401 Unauthorized` | Token expired | Re-authenticate CLI profile |

### Step 6: Fix and Redeploy (Max 3 Attempts)

```
Attempt 1: Deploy → Run Job → [FAIL] → Diagnose → Fix source file → Redeploy
Attempt 2: Deploy → Run Job → [FAIL] → Diagnose → Fix source file → Redeploy
Attempt 3: Deploy → Run Job → [FAIL] → ESCALATE TO USER
```

---

## 5. Post-Deploy Verification

After the deployment job succeeds, re-run the benchmark questions to verify the bundle-deployed Genie Space matches the API-patched results from the optimization loop.

```python
import time

print("Post-deploy re-assessment...")
print("Waiting 30s for Genie Space to stabilize...")
time.sleep(30)

post_deploy_results = []
for q in benchmark_questions:
    result = run_genie_query(SPACE_ID, q["question"])
    evaluation = evaluate_accuracy(result, q)
    post_deploy_results.append(evaluation)
    status = "PASS" if evaluation["correct_asset"] else "FAIL"
    print(f"  {status}: {q['question'][:55]}")
    time.sleep(12)

post_accuracy = sum(1 for r in post_deploy_results if r["correct_asset"]) / len(post_deploy_results) * 100
print(f"\nPost-deploy accuracy: {post_accuracy:.0f}%")
print(f"In-loop accuracy was: {in_loop_accuracy:.0f}%")

if post_accuracy >= in_loop_accuracy:
    print("SUCCESS: Bundle-deployed state matches or exceeds API-tested results.")
else:
    print("DISCREPANCY: Post-deploy accuracy is lower than in-loop accuracy.")
    print("A change was likely applied via API but NOT written to bundle files.")
    print("Fix the missing bundle file and repeat Phase B + C.")
```

### Discrepancy Resolution

| Situation | Cause | Fix |
|-----------|-------|-----|
| Post-deploy matches in-loop | Bundle files are complete | Optimization done |
| Post-deploy is lower | API patch not in bundle file | Find missing change, update file, redeploy |
| Specific question regressed | Genie Instructions change lost | Update `src/genie/*_genie_export.json`, redeploy |

The most common cause of discrepancy is a Lever 6 change (Genie Instructions, sample queries, routing rules) that was applied via `PATCH` API but the `src/genie/*_genie_export.json` file was not updated with the same change.

---

## 6. MLflow Artifact Management

During the optimization loop, the following MLflow artifacts are produced per iteration:

| Artifact | Type | Purpose |
|----------|------|---------|
| Genie metadata snapshot | JSON file | Before-state for rollback |
| Evaluation results | MLflow Evaluation | Per-judge scores per question |
| Introspection proposals | JSON | Proposed changes with net impact |
| Progress file | JSON | Session state for resume |

All artifacts are logged to the experiment run for that iteration. The progress file (`optimization-progress.json`) is also written to the working directory for the agent to read on resume.

### Batched Proposals from GEPA/Introspection

Phase A now applies batched proposals from the optimization engine rather than single manual fixes:

1. GEPA or introspection generates proposals for the highest-impact failure cluster
2. Non-conflicting proposals are batched (different levers can be applied simultaneously)
3. Each proposal includes explicit `dual_persistence` paths
4. After applying the batch, a full-suite re-benchmark detects regressions
5. If regression detected, the batch is reverted and proposals are tried individually

---

## 7. Evaluation Job in the Deploy Lifecycle

The `genie_evaluation_job` fits into the deployment lifecycle alongside the existing `genie_spaces_deployment_job`. During optimization, the evaluation job replaces inline evaluation. After deployment, it serves as a post-deploy verification step.

### Where It Fits

```
  Optimization Loop                   Deploy Phase              Post-Deploy
  ==================                  ============              ===========
  ┌──────────────────┐
  │ genie_evaluation  │◄── iter 1
  │     _job          │
  └────────┬─────────┘
           ▼
  Agent reads MLflow
  Agent applies fixes
           │
  ┌──────────────────┐
  │ genie_evaluation  │◄── iter 2
  │     _job          │
  └────────┬─────────┘
           ▼
  Accuracy met? ──Yes──►  ┌───────────────────┐    ┌──────────────────┐
                          │ bundle deploy     │──► │ genie_spaces     │
                          │                   │    │ _deployment_job  │
                          └───────────────────┘    └────────┬─────────┘
                                                            ▼
                                                   ┌──────────────────┐
                                                   │ genie_evaluation  │◄── post-deploy
                                                   │     _job          │    verification
                                                   └────────┬─────────┘
                                                            ▼
                                                   Agent checks: accuracy same
                                                   as pre-deploy? If not, fix.
```

### Pre-Deploy vs Post-Deploy Evaluation

| Phase | Job Used | Purpose | What Changes |
|-------|----------|---------|--------------|
| **During optimization** | `genie_evaluation_job` | Measure accuracy after each control lever change | `iteration` param increments (1, 2, 3...) |
| **Post-deploy** | `genie_evaluation_job` | Verify bundle-deployed state matches pre-deploy accuracy | `iteration` param set to `post_deploy` |
| **CI/CD gate** | `genie_evaluation_job` | Block merge if accuracy below threshold | Same job, triggered from CI pipeline |

### Post-Deploy Re-Assessment with Job

Instead of running inline re-benchmarking after `genie_spaces_deployment_job`, the agent triggers the evaluation job:

```python
post_deploy_result = run_evaluation_via_job(
    space_id=space_id,
    experiment_name=exp_name,
    iteration=999,  # sentinel for post-deploy
    benchmarks_path=benchmarks_path,
    domain=domain,
    target=target,
)

pre_deploy_result = query_latest_evaluation(exp_name, iteration=last_optimization_iter)

if post_deploy_result["overall_accuracy"] < pre_deploy_result["metrics"]["overall_accuracy"] - 2.0:
    print("WARNING: Post-deploy regression detected!")
    # Agent triggers fix cycle
```

### DABs Configuration

Both jobs should be defined in the same bundle. The evaluation job is added via:

```yaml
include:
  - "resources/genie_evaluation_job.yml"
  - "resources/genie_spaces_deployment_job.yml"
```

Copy `genie-evaluation-job-template.yml` from the skill's `assets/templates/` directory into your bundle's `resources/` directory.

---

## 8. Escalation

### When to Escalate

| Condition | Action |
|-----------|--------|
| 5 optimization iterations with no improvement | Escalate — LLM limitation likely |
| 3 deploy attempts all fail | Escalate — infrastructure/config issue |
| Post-deploy discrepancy persists after 2 fix attempts | Escalate — missing change not identifiable |

### What to Present to User

1. **All errors encountered** — question IDs, error messages, run IDs
2. **All fixes attempted** — which levers, what was changed, in which iteration
3. **Root cause hypothesis** — best guess based on failure patterns
4. **Current scores** — accuracy and repeatability, before and after
5. **Deploy status** — bundle deploy success/failure, job run ID, run page URL
6. **Recommendation** — next steps (e.g., TVF redesign, manual UI testing)

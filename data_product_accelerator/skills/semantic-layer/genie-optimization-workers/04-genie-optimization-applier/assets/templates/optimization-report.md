# {Domain} Genie Space Optimization Report

**Date:** {date}
**Space ID:** `{space_id}`
**Domain:** {domain_name}
**MLflow Experiment:** `{experiment_name}`
**Iterations:** {iterations_used} of {max_iterations}

---

## Executive Summary

| Dimension | Initial | Final | Target | Change |
|-----------|---------|-------|--------|--------|
| **Syntax Validity** | {init_syntax}% | {final_syntax}% | 98% | {change_syntax} |
| **Schema Accuracy** | {init_schema}% | {final_schema}% | 95% | {change_schema} |
| **Logical Accuracy** | {init_logical}% | {final_logical}% | 90% | {change_logical} |
| **Semantic Equivalence** | {init_semantic}% | {final_semantic}% | 90% | {change_semantic} |
| **Completeness** | {init_complete}% | {final_complete}% | 90% | {change_complete} |
| **Result Correctness** | {init_result}% | {final_result}% | 85% | {change_result} |
| **Asset Routing** | {init_asset}% | {final_asset}% | 95% | {change_asset} |
| **Repeatability** | {init_repeat}% | {final_repeat}% | 90% | {change_repeat} |

---

## Iteration History

| Iter | Accuracy | Failures | Clusters | Proposals Applied | Regressions |
|------|----------|----------|----------|-------------------|-------------|
| {iter} | {accuracy}% | {fail_count} | {cluster_count} | {proposal_ids} | {regression_count} |

---

## Introspective Analysis

### Failure Clusters

| Cluster ID | Root Cause | Questions Affected | Judge | Proposed Lever | Net Impact |
|-----------|-----------|-------------------|-------|---------------|------------|
| {cluster_id} | {root_cause} | {question_ids} | {judge} | {lever} | {net_impact} |

### Proposal Outcomes

| Proposal | Cluster | Predicted Fix | Actual Fix | Regressions |
|----------|---------|---------------|------------|-------------|
| {proposal_id} | {cluster_id} | {predicted_questions} | {actual_questions} | {regressions} |

---

## Arbiter Corrections

| Question ID | Verdict | Old GT SQL | New GT SQL | Reason |
|-------------|---------|-----------|-----------|--------|
| {question_id} | {verdict} | {old_sql} | {new_sql} | {reason} |

**Total arbiter invocations:** {arbiter_count}
**Auto-corrections (genie_correct):** {auto_correct_count}
**Disambiguation instructions added (both_correct):** {disambig_count}

---

## Per-Question Results

| Question ID | Question | Expected Asset | Actual Asset | Syntax | Schema | Logic | Semantic | Complete | Result | Status |
|-------------|----------|---------------|--------------|--------|--------|-------|----------|----------|--------|--------|
| {id} | {question} | {expected} | {actual} | {syntax} | {schema} | {logic} | {semantic} | {complete} | {result} | PASS/FAIL |

---

## Per-Lever Impact

Accuracy delta attributed to each lever applied during the optimization loop. Levers are applied in priority order (1 → 6); GEPA (Lever 6) runs only if Levers 1-5 are insufficient.

| Lever | Before Accuracy | After Accuracy | Delta | Proposals Applied | Status |
|-------|----------------|----------------|-------|-------------------|--------|
| Lever 1: UC Tables & Columns | {before_1}% | {after_1}% | {delta_1}% | {proposals_1} | {status_1} |
| Lever 2: Metric Views | {before_2}% | {after_2}% | {delta_2}% | {proposals_2} | {status_2} |
| Lever 3: TVFs | {before_3}% | {after_3}% | {delta_3}% | {proposals_3} | {status_3} |
| Lever 4: Monitoring Tables | {before_4}% | {after_4}% | {delta_4}% | {proposals_4} | {status_4} |
| Lever 5: ML Tables | {before_5}% | {after_5}% | {delta_5}% | {proposals_5} | {status_5} |
| Lever 6: Genie Instructions (GEPA) | {before_6}% | {after_6}% | {delta_6}% | {proposals_6} | {status_6} |

**Lever attribution source:** `session.lever_impacts` from `optimization-progress.json`

---

## Control Lever Changes

| Lever | Change Description | Affected Questions | Dual Persistence |
|-------|-------------------|--------------------|-----------------|
| Lever {N}: {name} | {description} | {question_ids} | API: {api_cmd} / Repo: {repo_path} |

---

## MLflow Experiment Link

**Experiment:** `{experiment_name}`
**Runs:** {run_count} (one per iteration)
**Best run:** `{best_run_id}` (iteration {best_iter})

---

## GEPA Pareto Evolution

| Generation | Best Score | Candidate Summary | Improvement |
|-----------|-----------|-------------------|-------------|
| {gen} | {score} | {summary} | {delta} |

**Optimization tier used:** {tier}
**Total metric calls:** {metric_calls}

---

## Dual Persistence Confirmation

| Step | Status | Details |
|------|--------|---------|
| Direct API Updates | {status} | {details} |
| Repository Files Updated | {status} | {details} |
| Template Variables Preserved | {status} | `${catalog}`, `${gold_schema}` |
| Arrays Sorted | {status} | `sort_genie_config()` applied |
| Bundle Deploy (Phase B) | {status} | {details} |
| Genie Job (Phase C) | {status} | {details} |
| Post-Deploy Match | {status} | {details} |

---

## Files Updated

1. `src/genie/{domain}_genie_export.json` - Genie Space configuration
2. `gold_layer_design/yaml/{domain}/*.yaml` - UC table metadata (if changed)
3. `src/semantic/metric_views/*.yaml` - Metric views (if changed)
4. `src/semantic/tvfs/*.sql` - TVFs (if changed)
5. `tests/optimizer/genie_golden_queries.yml` - Benchmark updates (arbiter corrections)
6. `optimization-progress.json` - Session progress
7. This report

---

## Remaining Issues

| Question | Issue | Root Cause | Recommended Fix | Priority |
|----------|-------|-----------|-----------------|----------|
| {question} | {issue} | {cause} | {fix} | High/Medium/Low |

---

## Key Learnings

1. {learning_1}
2. {learning_2}
3. {learning_3}

---

## Next Steps

- [ ] Re-test remaining failures after next deployment
- [ ] Review arbiter corrections for accuracy
- [ ] Monitor user feedback for new failure patterns
- [ ] Schedule follow-up optimization session in {timeframe}
- [ ] Consider GEPA judge prompt optimization if judge accuracy is low

---
name: genie-metadata-optimizer
description: >
  Optimizes Genie Space metadata using L1 (ASI-grounded introspection),
  L2 (GEPA), or L3 (multi-objective Pareto). Maps judge rationales to
  metadata fields via propose_patch_set_from_asi(), generates patch proposals
  with blast radius tracking, and produces lever mappings for the Applier.
  Use when evaluation scores are below target and metadata changes are needed.
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

# Genie Metadata Optimizer

Analyzes evaluation failures and generates metadata change proposals using GEPA or structured LLM introspection. Produces control lever mappings consumed by the Applier worker.

## When to Use This Skill

- Evaluation scores are below target after benchmarking
- Need to generate metadata change proposals from failure patterns
- Running GEPA-powered metadata evolution (L2)
- Running failure clustering and ASI-grounded introspective analysis (L1)
- Optimizing judge prompt accuracy (SIMBA)

### Inputs (from Orchestrator)

| Input | Type | Description |
|-------|------|-------------|
| `eval_results` | dict | Evaluation results from the Evaluator worker |
| `judge_feedback` | list | Judge rationales per question |
| `metadata_snapshot` | dict | Current Genie metadata snapshot (for GEPA or introspection) |
| `space_id` | str | Genie Space ID |
| `use_asi` | bool | Enable ASI-grounded patch proposals (default: False) |
| `use_patch_dsl` | bool | Enable Patch DSL validation and conflict checking (default: False) |
| `use_gepa` | bool | Enable GEPA evaluation of candidate patch sets (default: False) |
| `target_lever` | int or None | When provided, filter proposals to this lever only (1-6). Used by the orchestrator for per-lever optimization (default: None = all levers) |

### Outputs (to Orchestrator)

| Output | Type | Description |
|--------|------|-------------|
| `patch_set` | list | List of patch dicts (when use_patch_dsl=True) |
| `validation_result` | dict | Conflict check and blast radius enforcement result |
| `proposals` | list | Legacy format proposals (for backward compatibility) |
| `optimized_candidate` | dict | GEPA-optimized metadata (L2) or proposals (L1) |
| `lever_mapping` | list | Control lever proposals with dual persistence paths |
| `pareto_stats` | dict | GEPA optimization statistics (L2 only) |

## Optimization Tiers (L1/L2/L3 Maturity Model)

| Tier | Engine | Description | When to Use |
|------|--------|-------------|-------------|
| **L1** | Greedy / Introspection | ASI-grounded patch proposals via `propose_patch_set_from_asi()`. Uses FAILURE_TAXONOMY and blame_set grouping. **Default mode.** | Optimizing UC table/column descriptions from judge feedback |
| **L2** | GEPA | GenieMetadataAdapter evaluates candidate patch set JSONs. Enabled via `use_gepa=True` flag. **Lever 6 only.** | Optimizing Genie instructions + example SQLs with >=15 benchmarks |
| **L3** | Multi-Objective | Pareto frontier tracking with multiple objectives. **Future work.** | When multi-objective tradeoffs are needed |

**SEQUENCING:** Always run L1 introspection for Levers 1-5 BEFORE running L2 (GEPA) for Lever 6. GEPA is NOT a replacement for introspection — it is a complement that handles the lowest-priority lever. Running GEPA first wastes the optimization budget on the least durable lever (~4000 char limit). The orchestrator enforces this via hard constraint #14.

**Load:** Read [gepa-integration.md](references/gepa-integration.md) for L2 GEPA implementation: seed extraction, evaluator, orchestration.

**Load:** Read [feedback-to-metadata-mapping.md](references/feedback-to-metadata-mapping.md) for L1 introspection: failure clustering, proposal generation, conflict detection.

**Load:** Read [prompt-registry-patterns.md](references/prompt-registry-patterns.md) for judge prompt optimization and the prompt lifecycle.

## Patch DSL (P2)

Structured patch language for metadata changes with conflict detection and blast radius enforcement.

- **31 PATCH_TYPES** with defined scopes and risk levels (e.g., `ALTER_TABLE_COMMENT`, `ALTER_COLUMN_COMMENT`, `CREATE_METRIC_VIEW`, etc.)
- **16 CONFLICT_RULES** pairs: patches that cannot be applied together (e.g., same table + different descriptions)
- **validate_patch_set()** for conflict checking and blast radius enforcement (max 5 objects per patch set)
- **Feature flag:** `use_patch_dsl=True` / `False` (default: False)

## Actionable Side Information (ASI) (P4)

ASI structures judge feedback for patch synthesis and scoring.

- **FAILURE_TAXONOMY:** 16 failure types (e.g., wrong_table, wrong_column, wrong_aggregation, wrong_filter, hallucination, etc.)
- **ASI_SCHEMA:** 12 fields per judge feedback (e.g., question_id, failure_type, blame_set, rationale, suggested_fix, etc.)
- **propose_patch_set_from_asi()** workflow:
  1. Collect failures from judge feedback
  2. Group by blame_set (root cause clustering)
  3. Synthesize patches per group
  4. Score patches (impact, blast radius)
  5. Select best patch set
- **Feature flag:** `use_asi=True` / `False` (default: False)

## Blast Radius Tracking (P13)

Penalizes patch sets that touch too many objects to limit regression risk.

- **adjusted_score** = raw_score - 0.1 × (blast_objects / total_objects)
- **Max 5 objects** per patch set (enforced by validate_patch_set when use_patch_dsl=True)

## Introspective Analysis (L1)

When L2 (GEPA) is not used, the optimizer clusters failures and generates proposals:

1. **Cluster failures** by systemic root cause (>=2 questions per cluster)
2. **Map** each cluster to a control lever (1-6)
3. **Generate proposals** with dual persistence paths and net impact scores
4. **Detect conflicts** and batch non-conflicting proposals together
5. **Sort** by net impact descending — highest impact applied first

Judge `rationale` fields are the primary learning signal. GEPA receives rationales as Actionable Side Information (ASI); introspection clusters by root cause pattern.

### Root Cause → Lever Mapping

| Root Cause | Lever | API Command |
|------------|-------|-------------|
| Wrong table | 1 (UC Tables) | `ALTER TABLE ... SET TBLPROPERTIES` |
| Wrong column | 1 (UC Columns) | `ALTER COLUMN ... COMMENT` |
| Wrong aggregation | 2 (Metric Views) | `CREATE OR REPLACE VIEW` |
| Wrong filter | 3 (TVFs) | `CREATE OR REPLACE FUNCTION` |
| Wrong asset routing | 6 (Instructions) | `PATCH /api/2.0/genie/spaces/{id}` |

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Bare boolean scores (no rationale) | GEPA/introspection can't learn | Always use `Feedback(value=..., rationale=...)` |
| Batch-applying all proposals at once | Can't isolate regressions | Apply one cluster's proposals per iteration |
| Running L2 (GEPA) and judge optimization together | Confounding effects | Always separate: metadata first, judge prompts only if judges are bottleneck |
| Running GEPA before exhausting Levers 1-5 | Optimization budget wasted on lowest-priority lever | Always introspect Levers 1-5 first; GEPA is Lever 6 only |
| Assuming GEPA is unavailable without checking | L2 tier never attempted | Install `gepa>=0.1.0` and use the GEPA template notebook |

## Installation

GEPA L2 requires the `gepa` package. Install before running the GEPA tier:

```bash
# Local / CI
pip install "gepa>=0.1.0"

# Databricks cluster library (via UI or CLI)
databricks libraries install --cluster-id <CLUSTER_ID> --pypi-package "gepa>=0.1.0"
```

The GEPA template job YAML ([gepa-optimization-job-template.yml](assets/templates/gepa-optimization-job-template.yml)) includes `gepa>=0.1.0` in its environment dependencies automatically.

## Scripts

### [metadata_optimizer.py](scripts/metadata_optimizer.py)

Standalone introspection and proposal generation CLI.

### [run_gepa_optimization.py](assets/templates/run_gepa_optimization.py) (template)

Databricks notebook for GEPA L2 optimization. All helper functions are inlined (self-contained). Includes `strip_non_exportable_fields()`, `build_seed_candidate()`, `evaluate_genie()`, `apply_candidate_to_space()`, and `score_genie_response()`.

### [gepa-optimization-job-template.yml](assets/templates/gepa-optimization-job-template.yml) (template)

DABs job definition for deploying GEPA optimization as a Databricks job. Includes `gepa>=0.1.0` dependency.

## Reference Index

| Reference | What to Find |
|-----------|-------------|
| [gepa-integration.md](references/gepa-integration.md) | GEPA optimize_anything, seed extraction, evaluator, configuration |
| [feedback-to-metadata-mapping.md](references/feedback-to-metadata-mapping.md) | Failure clustering, proposal generation, conflict detection, regression detection |
| [prompt-registry-patterns.md](references/prompt-registry-patterns.md) | Prompt lifecycle, GEPA judge optimization, rollback, tag conventions |
| [run_gepa_optimization.py](assets/templates/run_gepa_optimization.py) | GEPA notebook template (all helpers inlined, self-contained) |
| [gepa-optimization-job-template.yml](assets/templates/gepa-optimization-job-template.yml) | DABs job definition for GEPA optimization |

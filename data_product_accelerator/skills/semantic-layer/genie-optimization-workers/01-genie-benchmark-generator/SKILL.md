---
name: genie-benchmark-generator
description: >
  Generates and validates benchmark questions for Genie Space evaluation.
  Three-path intake (user provides 10+, 1-9, or 0 questions), synthetic
  generation from MVs/TVFs/tables, ground truth SQL validation via warehouse
  execution, result hashing, and MLflow Evaluation Dataset sync. Use when
  creating or refreshing benchmarks before an optimization loop, or when
  arbiter corrections require GT updates.
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
---

# Genie Benchmark Generator

Creates, validates, and syncs benchmark question suites for Genie Space evaluation. Handles three intake paths, ground truth SQL validation, and MLflow Evaluation Dataset synchronization.

## When to Use This Skill

- Creating benchmark questions for a new Genie Space optimization
- Refreshing benchmarks after arbiter corrections (ground truth was wrong)
- Generating synthetic benchmarks from Genie Space trusted assets
- Validating ground truth SQL against the live warehouse

### Inputs (from Orchestrator)

| Input | Type | Description |
|-------|------|-------------|
| `space_id` | str | Genie Space ID |
| `uc_schema` | str | Unity Catalog schema for MLflow datasets |
| `domain` | str | Domain key (e.g., "cost") |
| `user_questions` | list | Optional user-provided benchmark questions |

### Outputs (to Orchestrator)

| Output | Type | Description |
|--------|------|-------------|
| `eval_dataset_name` | str | MLflow Evaluation Dataset name in UC (always produced when `uc_schema` is set) |
| `gt_validation_report` | dict | Per-question validation results |
| `yaml_path` | str | Path to saved golden-queries.yaml |
| `benchmark_count` | int | Number of benchmarks created |

> **Warning:** The evaluator REQUIRES `eval_dataset_name` to use `mlflow.genai.evaluate()`. Skipping dataset sync means the Datasets and Evaluation tabs will be empty. Always run `sync_yaml_to_mlflow_dataset()`.

> **Template variable handoff:** Ground truth SQL in `expected_sql` may use `${catalog}` and `${gold_schema}` template variables. The evaluator must receive `catalog` and `gold_schema` as job parameters and call `resolve_sql()` before any `spark.sql()` execution.

## Workflow

```
User provides questions?
├── YES (10+) → Validate → Report → Save
├── YES (1-9) → Validate → Augment → Review → Save
└── NO (0)    → Inspect assets → Generate → Review → Save
                                    ↓
                        Validate GT SQL (spark.sql)
                                    ↓
                        Sync to MLflow Evaluation Dataset
```

1. **Prompt the user** for benchmark questions (always ask before generating synthetic)
2. **Validate** each question against the live Genie Space trusted assets
3. **Generate / Augment** synthetic benchmarks to fill coverage gaps
4. **Show to user** for review before proceeding
5. **Validate ground truth SQL** — execute via `spark.sql()`, store result hash + sample
6. **Save** to `golden-queries.yaml`
7. **Sync** to MLflow Evaluation Dataset in Unity Catalog

**Load:** Read [benchmark-intake-workflow.md](references/benchmark-intake-workflow.md) for the full three-path intake implementation.

**Load:** Read [benchmark-patterns.md](references/benchmark-patterns.md) for question writing rules, category coverage, and domain-specific patterns.

**Load:** Read [gt-validation.md](references/gt-validation.md) for ground truth SQL validation, retry logic, and MLflow dataset sync code.

## Benchmark Question Schema

Every benchmark question requires these fields:

```yaml
- id: "domain_NNN"
  question: "Natural language question"
  expected_sql: "Full SQL that returns correct result"
  expected_asset: "MV|TVF|TABLE"
  category: "aggregation|ranking|time-series|comparison|list"
  source: "user|synthetic|augmented"
  priority: "P0|P1|P2"   # P0 = hard gate, P1 = default, P2 = nice-to-have
```

Optional fields (auto-populated by GT validation):
- `required_tables`, `required_columns`, `required_joins`
- `expected_result_hash`, `expected_result_sample`, `expected_row_count`, `expected_columns`

See [golden-queries.yaml](assets/templates/golden-queries.yaml) for the full template.

## Benchmark Splits (P12)

- `assign_splits()` assigns `train` / `val` / `held_out` with 60/20/20 ratios.
- The `held_out` split is never used during optimization; it is reserved only for post-deploy overfitting checks.
- The `split` field is optional and backward-compatible.

## SQL Dependency Map

- `parse_sql_dependencies()` auto-extracts `required_tables`, `required_columns`, and `required_joins` from GT SQL.
- These fields are auto-populated during `validate_benchmarks()` if not already set.
- Used by the evaluator's `eval_scope="slice"` to filter benchmarks by patched objects.

## Enhanced GT Validation

- `validate_benchmarks()` now also populates `expected_columns` from the GT SQL result.
- All validation output fields: `expected_result_hash`, `expected_result_sample`, `expected_row_count`, `expected_columns`.

## Coverage Requirements

| Domain Size | Min Questions | Min Categories |
|-------------|---------------|----------------|
| Small (1-3 tables) | 10 | 4 |
| Medium (4-8 tables) | 15 | 6 |
| Large (9+ tables) | 20-25 | 8 |

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Generating benchmarks without asking user first | Misses real user intent | Always prompt before synthetic generation |
| Skipping GT SQL validation | Chasing wrong ground truth | Execute every GT SQL via `spark.sql()` before acceptance |
| Not validating against live space | Questions reference non-trusted assets | Check all SQL references against space config |
| Insufficient category coverage | Missing failure patterns in evaluation | Ensure 4+ categories, fill gaps with synthetic |
| Template variables in `expected_sql` without documenting handoff | Evaluator gets `PARSE_SYNTAX_ERROR` | Document that evaluator must receive `catalog` and `gold_schema` as parameters and call `resolve_sql()` |
| Skipping dataset sync to UC | Evaluator can't use `mlflow.genai.evaluate(data=...)`, Evaluation tab empty | Always run `sync_yaml_to_mlflow_dataset()` — it's required for the MLflow GenAI evaluation flow |

## HARD CONSTRAINTS

- `sync_yaml_to_mlflow_dataset()` MUST run when `uc_schema` is available. Skipping leaves the Datasets tab empty.

## Scripts

### [benchmark_generator.py](scripts/benchmark_generator.py)

Standalone CLI for benchmark generation, validation, and MLflow sync:

```bash
python scripts/benchmark_generator.py --space-id <ID> --domain cost --uc-schema catalog.schema
python scripts/benchmark_generator.py --space-id <ID> --domain cost --validate-only
```

## Reference Index

| Reference | What to Find |
|-----------|-------------|
| [benchmark-intake-workflow.md](references/benchmark-intake-workflow.md) | Three-path intake, validation pipeline, augmentation strategy |
| [benchmark-patterns.md](references/benchmark-patterns.md) | Question writing rules, SQL expectations, domain patterns, validation checklist |
| [gt-validation.md](references/gt-validation.md) | GT SQL execution, retry logic, hash storage, MLflow dataset sync |
| [golden-queries.yaml](assets/templates/golden-queries.yaml) | Template with example cost domain benchmarks |

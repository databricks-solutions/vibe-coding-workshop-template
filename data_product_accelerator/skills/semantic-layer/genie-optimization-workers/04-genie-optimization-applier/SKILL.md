---
name: genie-optimization-applier
description: >
  Applies metadata change proposals to Genie Space via dual persistence
  (API + repo files). Six control levers in priority order. Two call modes:
  during-loop (API + repo only) and post-loop (+ bundle deploy + Genie job).
  Handles sort_genie_config, template variable preservation, and self-healing
  deploy with max 3 retries. Use when applying optimization proposals or
  deploying the optimized Genie Space.
metadata:
  author: prashanth subrahmanyam
  version: "3.0.0"
  domain: semantic-layer
  role: worker
  called_by:
    - genie-optimization-orchestrator
  standalone: true
  common_dependencies:
    - databricks-autonomous-operations
    - genie-space-export-import-api
---

# Genie Optimization Applier

Applies metadata change proposals using six control levers with dual persistence, and deploys the optimized Genie Space via the three-phase deployment model.

## When to Use This Skill

- Applying metadata change proposals from the Optimizer worker
- Deploying optimized Genie Space via bundle + Genie job
- Running post-deploy verification
- Reverting a bad change after regression detection

### Inputs (from Orchestrator)

| Input | Type | Description |
|-------|------|-------------|
| `space_id` | str | Genie Space ID |
| `candidate` | dict | Optimized metadata from Optimizer |
| `lever_map` | list | Control lever proposals with dual persistence paths |
| `domain` | str | Domain name |
| `patch_set` | list | List of patch dicts (when using Patch DSL) |
| `space_config` | dict | Space configuration for patch application |
| `use_patch_dsl` | bool | Enable Patch DSL renderer (default: False) |
| `deploy_target` | str or None | Bundle target (None = no deploy, "dev" = deploy) |

### Outputs (to Orchestrator)

| Output | Type | Description |
|--------|------|-------------|
| `apply_status` | str or list | Overall apply status or per-proposal results |
| `apply_log` | dict | Actions executed, rollback commands, snapshots (for rollback) |
| `files_modified` | list | Repository files updated |
| `deploy_status` | dict | Bundle deploy + job status (if deploy_target set) |

## Two Call Modes

| Mode | When | What Happens |
|------|------|-------------|
| **During loop** (`deploy_target=None`) | Each iteration | Apply via API + update repo files only |
| **After loop** (`deploy_target="dev"`) | End of optimization | Apply + bundle deploy + Genie job |

## Control Levers (Priority Order)

| Priority | Lever | Durability |
|----------|-------|-----------|
| 1 | UC Tables & Columns | Highest — survives Space rebuilds |
| 2 | Metric Views | High — rich semantics |
| 3 | TVFs (Functions) | High — parameterized logic |
| 4 | Monitoring Tables | Medium |
| 5 | ML Model Tables | Medium |
| 6 | Genie Instructions | Lowest — ~4000 char limit |

**Load:** Read [control-levers.md](references/control-levers.md) for per-lever SQL/API commands, dual persistence patterns, sort function, and proposal mapping.

**Load:** Read [autonomous-ops-integration.md](references/autonomous-ops-integration.md) for three-phase deployment, self-healing deploy, post-deploy verification.

## Dual Persistence

Every change must be applied to BOTH the live API/SQL AND the repository file:

| Lever | Direct Update | Repository File | Rebuilt by Genie Job? |
|-------|--------------|-----------------|----------------------|
| UC Tables | `ALTER TABLE ... SET TBLPROPERTIES` | `gold_layer_design/yaml/{domain}/*.yaml` | No |
| Metric Views | `CREATE OR REPLACE VIEW` | `src/semantic/metric_views/*.yaml` | No |
| TVFs | `CREATE OR REPLACE FUNCTION` | `src/semantic/tvfs/*.sql` | No |
| Genie Instructions | `PATCH /api/2.0/genie/spaces/{id}` | `src/genie/{domain}_genie_export.json` | **Yes** |

## Patch DSL Renderer

When `use_patch_dsl=True`, the applier uses a declarative patch renderer:

- **`render_patch()`** converts each of 31 `PATCH_TYPES` into executable actions
- Each action has: `action_type`, `target`, `command`, `rollback_command`, `risk_level`
- **Metric view operations:** read current YAML → apply mutation → `CREATE OR REPLACE VIEW`
- **Feature flag:** `use_patch_dsl=True` / `False` (default: `False`)

## Apply Log with Rollback (P11)

- **`apply_patch_set()` workflow:** snapshot → render → classify → execute → snapshot → log
- Apply is **idempotent** using `old_text` guards
- **Rollback** executes `rollback_command`s from `apply_log` in **reverse order**
- Called by orchestrator when P0 gate fails

## Risk-Gated Application (P10)

| Risk | Behavior | Examples |
|------|----------|----------|
| **low** | Auto-apply | Synonyms, descriptions, instructions |
| **medium** | Auto-apply + P0 gate after | Tables, joins, filters, MV measures |
| **high** | Proposed only, user notified | Remove table, remove instruction, remove MV, compliance tags |
| — | **Never** auto-remove | Compliance tags |

## Three-Phase Deployment

| Phase | When | What Happens |
|-------|------|-------------|
| A | During loop | Direct API/SQL + update repo files |
| B | End of loop | `databricks bundle validate` + `deploy` |
| C | End of loop | `databricks bundle run genie_spaces_deployment_job` |

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| API-only update (no repo file) | Changes lost on next deploy | Always dual-persist |
| Everything in Genie Instructions | Exceeds ~4000 char limit | Use levers 1-5 first |
| Missing `sort_genie_config()` | API rejects unsorted arrays | Always sort before PATCH |
| Missing template variables | Hardcoded catalog/schema | Preserve `${catalog}`, `${gold_schema}` |
| Passing full GET response to PATCH | `InvalidParameterValue: Cannot find field` | Strip non-exportable fields via `strip_non_exportable_fields()` before serializing |

## Scripts

### [optimization_applier.py](scripts/optimization_applier.py)

Standalone CLI for applying proposals and deploying bundles.

## Reference Index

| Reference | What to Find |
|-----------|-------------|
| [control-levers.md](references/control-levers.md) | Per-lever SQL/API commands, sort function, dual persistence, proposal mapping |
| [autonomous-ops-integration.md](references/autonomous-ops-integration.md) | Three-phase deploy, self-healing, post-deploy verification, escalation |
| [optimization-report.md](assets/templates/optimization-report.md) | Report template with per-judge metrics and iteration history |

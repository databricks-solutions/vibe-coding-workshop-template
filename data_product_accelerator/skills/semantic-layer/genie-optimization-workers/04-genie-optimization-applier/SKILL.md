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
  version: "4.2.0"
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
| `use_patch_dsl` | bool | Enable Patch DSL renderer (default: True) |
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

> **`description` vs `serialized_space` for instructions:** The Genie Space has TWO places for instructions:
> 1. **`description`** — a top-level field on the space, separate from `serialized_space`. Updated via `PATCH {"description": "new text"}` directly.
> 2. **`text_instructions`** — inside `serialized_space.instructions.text_instructions[]`. Updated via `PATCH {"serialized_space": "{...}"}` with the full serialized config.
>
> The `description` field is visible in the Genie Space UI header. The `text_instructions` are the structured instruction objects used for routing rules. Both should be kept in sync. When updating routing instructions (Lever 6), update `text_instructions` inside `serialized_space`, not `description`.

### Asset Type Detection for Lever 1

> **Note:** `detect_asset_type()` is **not implemented in the applier**. Asset type inspection (TABLE vs VIEW) is handled by the **orchestrator's asset inspection** before proposals reach the applier. The applier receives proposals that have already been routed to the correct lever.

Before applying `ALTER TABLE ... ALTER COLUMN ... COMMENT` for Lever 1 changes, the orchestrator determines if the target is a TABLE or VIEW. Metric Views (which are VIEWs in Unity Catalog) cannot use `ALTER TABLE` DDL. If the target is a VIEW:

1. Route to Lever 2 — update the MV YAML definition and execute `CREATE OR REPLACE VIEW` instead
2. Log a warning: "Detected VIEW, routing to Lever 2 (MV YAML + CREATE OR REPLACE VIEW)"
3. Do NOT attempt `ALTER TABLE` on a VIEW — it will fail with `AnalysisException`

## Patch DSL Renderer

When `use_patch_dsl=True`, the applier uses a declarative patch renderer:

- **`render_patch()`** converts each of 31 `PATCH_TYPES` into executable actions
- Each action has: `action_type`, `target`, `command`, `rollback_command`, `risk_level`
- **Metric view operations:** read current YAML → apply mutation → `CREATE OR REPLACE VIEW`
- **Feature flag:** `use_patch_dsl=True` / `False` (default: `True`)

### Patch DSL is Default

`USE_PATCH_DSL = True` is now the default. The legacy `apply_proposal_batch()` path only returns `pending_agent_execution` — it does not actually apply anything. All proposals MUST flow through the Patch DSL for programmatic execution and rollback.

**`proposals_to_patches(proposals)`** bridges ASI-enriched proposals from the optimizer into Patch DSL patches using `_lever_to_patch_type` mapping:

| `failure_type` + `lever` | `patch_type` |
|--------------------------|-------------|
| `wrong_column` + lever 1 | `update_column_description` |
| `wrong_table` + lever 1 | `update_table_comment` |
| `wrong_aggregation` + lever 2 | `update_mv_measure` |
| `wrong_filter` + lever 3 | `update_tvf_comment` |
| `repeatability_issue` + lever 3 | `update_tvf_comment` |
| `asset_routing_error` + lever 6 | `add_instruction` |
| `missing_column` + lever 1 | `update_column_description` |
| `missing_filter` + lever 6 | `add_instruction` |

The `blame_set` from ASI maps to `target`, and `counterfactual_fixes` maps to `new_text`. The `main()` CLI auto-converts proposals to patches when input has `proposals` but no `patches`.

**`apply_log.json` sidecar:** Every `apply_patch_set()` call writes a sidecar file for rollback traceability.

Legacy `apply_proposal_batch()` is only accessible via explicit `--no-patch-dsl`.

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
| Missing template variables in repo files | Hardcoded catalog/schema | Preserve `${catalog}`, `${gold_schema}` in repo files |
| Sending repo config to API without resolving `${catalog}`/`${gold_schema}` | Genie API receives literal `${catalog}` strings, query routing fails silently | Resolve template variables before API calls, re-template before repo writes |
| Passing full GET response to PATCH | `InvalidParameterValue: Cannot find field` | Strip non-exportable fields via `strip_non_exportable_fields()` before serializing |
| `serialized_space` as nested object in PATCH | API rejects malformed payload | Use `json.dumps(config)` to serialize as JSON string, not nested dict |
| Human-readable IDs for `example_question_sqls` | `InvalidParameterValue: Invalid ID format` | Use `uuid.uuid4().hex` for all entity IDs (32-hex UUID format) |
| `ALTER TABLE` on a Metric View | `AnalysisException: Cannot alter a view` | Run `DESCRIBE EXTENDED` first to detect VIEWs; route to Lever 2 (MV YAML + `CREATE OR REPLACE VIEW`) |
| Using `ALTER COLUMN COMMENT` on Metric View | `[EXPECT_TABLE_NOT_VIEW.NO_ALTERNATIVE]` error | Read MV YAML, update dimension comment, execute full `DROP VIEW IF EXISTS` + `CREATE VIEW ... WITH METRICS LANGUAGE YAML ... AS $$ ... $$` |
| Attempting `COMMENT ON FUNCTION` or `ALTER FUNCTION SET COMMENT` | `[PARSE_SYNTAX_ERROR] Syntax error at or near 'FUNCTION'` | Execute full `CREATE OR REPLACE FUNCTION` with the updated COMMENT section; read SQL from repo file, modify COMMENT, resolve template vars, execute full CREATE |
| Leaving `USE_PATCH_DSL=False` (legacy default) | Proposals return `pending_agent_execution` and nothing is actually applied | `USE_PATCH_DSL=True` is the proven, working path. Legacy path only accessible via explicit `--no-patch-dsl` |
| TVF optional param receives `'NULL'` string from Genie despite COMMENT guidance | WHERE clause matches no rows (string `'NULL'` ≠ SQL `NULL`) | Add coercion in TVF body: `CASE WHEN param IS NULL OR param = 'NULL' THEN TRUE ELSE col = param END`. This is a known Genie platform limitation (KGL-1 in optimizer skill) — metadata alone does not fix it |

## API Contract Gotchas

Non-obvious requirements of the Genie Space API that cause silent failures or rejections:

| Gotcha | Error Symptom | Fix |
|--------|---------------|-----|
| Arrays must be sorted by key before PATCH | `SORTING_ERROR` or silent config corruption | Call `sort_genie_config()` before every `PATCH /api/2.0/genie/spaces/{id}` |
| `serialized_space` must be a JSON string | API rejects nested object with `InvalidParameterValue` | Use `json.dumps(config)` to produce a JSON string, not a nested dict |
| All entity IDs must be 32-hex UUIDs | `InvalidParameterValue: Invalid ID format` for `example_question_sqls`, `sql_functions` | Generate via `uuid.uuid4().hex` — human-readable IDs are invalid |
| Template variables must be resolved before API | Genie receives literal `${catalog}` strings, routing and SQL fail silently | Replace `${catalog}`, `${gold_schema}` with actual values before API calls; re-template before repo file writes |
| Metric Views cannot use `ALTER TABLE` DDL | `AnalysisException: Cannot alter a view with ALTER TABLE` | Detect asset type via `DESCRIBE EXTENDED`; route VIEWs to `CREATE OR REPLACE VIEW` (Lever 2) |

## Orchestrator Integration

The orchestrator calls `apply_patch_set()` and `rollback()` directly (not via CLI) during the lever-aware loop:

- **Levers 1-5:** After `generate_metadata_proposals()` returns proposals, the orchestrator first converts them with `proposals_to_patches(proposals)`, then calls `apply_patch_set(space_id, patches, space_config, use_patch_dsl=True)` for programmatic execution with risk gating.
- **Lever 6 (GEPA):** GEPA patches are passed directly to `apply_patch_set()` instead of being converted to synthetic proposal dicts.
- **Rollback:** When regression is detected, the orchestrator calls `rollback(apply_log, space_id)` using the stored `apply_log` from the iteration result, alongside `rollback_to_model()` for LoggedModel-based restore.
- **Backward compatibility:** The `use_patch_dsl` flag in session state (default `True`) controls whether the Patch DSL or `apply_proposal_batch()` is used. Set to `False` only for manual/agent-driven execution.

## Scripts

### [optimization_applier.py](scripts/optimization_applier.py)

Standalone CLI for applying proposals and deploying bundles.

## Reference Index

| Reference | What to Find |
|-----------|-------------|
| [control-levers.md](references/control-levers.md) | Per-lever SQL/API commands, sort function, dual persistence, proposal mapping |
| [autonomous-ops-integration.md](references/autonomous-ops-integration.md) | Three-phase deploy, self-healing, post-deploy verification, escalation |
| [optimization-report.md](assets/templates/optimization-report.md) | Report template with per-judge metrics and iteration history |

## Version History

- **v4.2.0** (Feb 23, 2026) - Phase 8: Optimization loop feedback (Issues 14-16). New Common Mistake for TVF `'NULL'` string literal coercion (KGL-1 cross-ref to optimizer skill).
- **v4.1.0** (Feb 23, 2026) - Phase 7: ASI-to-metadata loop gap remediation. MV column comment requires full VIEW recreation documented in control-levers.md Lever 2 (DROP + CREATE VIEW WITH METRICS LANGUAGE YAML). TVF COMMENT requires full function replacement documented in Lever 3 (no ALTER FUNCTION SET COMMENT). TVF COMMENT Format section with structured bullet-point template. Lever 6 Instruction Specificity Rules with overcorrection prevention. `description` vs `serialized_space` clarified for Genie instructions. `missing_filter` and `missing_temporal_filter` added to `_LEVER_TO_PATCH_TYPE`. 2 new Common Mistakes (ALTER COLUMN on MV, COMMENT ON FUNCTION).
- **v4.0.0** (Feb 23, 2026) - Phase 6 architectural lessons. Flipped `USE_PATCH_DSL` default to `True`. Added "Patch DSL is Default" section with `proposals_to_patches()` bridge function, `_lever_to_patch_type` mapping, `apply_log.json` sidecar. Added Common Mistake for `USE_PATCH_DSL=False`. Version bumped from v3.1.0.
- **v3.1.0** (Feb 2026) - API Contract Gotchas, Orchestrator Integration, strip_non_exportable_fields(), risk-gated application, three-phase deployment.

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
  version: "4.2.0"
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
| `eval_results` | dict | Evaluation results with per-row `rows` list containing `feedback/*`, `rationale/*`, and `metadata/*` columns. **MUST include per-row data from the evaluator's `evaluation/failures.json` artifact, not just aggregate metrics.** When ASI metadata fields (`metadata/failure_type`, `metadata/blame_set`, `metadata/counterfactual_fix`) are present in rows, `cluster_failures()` uses them for higher-precision clustering instead of keyword extraction. |
| `judge_feedback` | list | Judge rationales per question |
| `metadata_snapshot` | dict | Current Genie metadata snapshot (for GEPA or introspection) |
| `space_id` | str | Genie Space ID |
| `use_asi` | bool | Enable ASI-grounded patch proposals (default: True) |
| `use_patch_dsl` | bool | Enable Patch DSL validation and conflict checking (default: True) |
| `use_gepa` | bool | Enable GEPA evaluation of candidate patch sets (default: False) |
| `target_lever` | int or None | When provided, filter proposals to this lever only (1-6). Used by the orchestrator for per-lever optimization (default: None = all levers) |

### Hard Constraint

Optimizer MUST consume the evaluator's per-row failures artifact (with ASI metadata), not aggregate metrics. When ASI fields (`failure_type`, `blame_set`, `counterfactual_fix`) are present, use them for clustering instead of keyword extraction from rationale text.

### Outputs (to Orchestrator)

| Output | Type | Description |
|--------|------|-------------|
| `patch_set` | list | List of patch dicts (when use_patch_dsl=True) |
| `validation_result` | dict | Conflict check and blast radius enforcement result |
| `proposals` | list | Legacy format proposals (for backward compatibility) |
| `optimized_candidate` | dict | GEPA-optimized metadata (L2) or proposals (L1) |
| `lever_mapping` | list | Control lever proposals with dual persistence paths |
| `pareto_stats` | dict | GEPA optimization statistics (L2 only) |
| `judge_quality_feedback` | list | Per-judge quality signals when counterfactual_fix values are too generic to drive optimization. Each entry: `{judge_name, feedback_type, example, desired, count}`. Feeds into SIMBA Tier 3 judge alignment when judges are the bottleneck. |

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

- **32 PATCH_TYPES** with defined scopes and risk levels (e.g., `ALTER_TABLE_COMMENT`, `ALTER_COLUMN_COMMENT`, `CREATE_METRIC_VIEW`, etc.)
- **16 CONFLICT_RULES** pairs: patches that cannot be applied together (e.g., same table + different descriptions)
- **validate_patch_set()** for conflict checking and blast radius enforcement (max 5 objects per patch set)
- **Feature flag:** `use_patch_dsl=True` / `False` (default: True)

## Actionable Side Information (ASI) (P4)

ASI structures judge feedback for patch synthesis and scoring.

- **FAILURE_TAXONOMY:** 23 failure types (e.g., wrong_table, wrong_column, wrong_aggregation, wrong_filter, hallucination, etc.)
- **ASI_SCHEMA:** 12 fields per judge feedback (e.g., question_id, failure_type, blame_set, rationale, suggested_fix, etc.)
- **propose_patch_set_from_asi()** workflow:
  1. Collect failures from judge feedback
  2. Group by blame_set (root cause clustering)
  3. Synthesize patches per group
  4. Score patches (impact, blast radius)
  5. Select best patch set
- **Feature flag:** `use_asi=True` / `False` (default: True)

### ASI Consumption Contract

The optimizer reads structured ASI from the evaluator using a priority chain:

1. **UC table (primary):** `read_asi_from_uc(catalog, schema, run_id, warehouse_id)` queries `genie_eval_asi_results` via Databricks SQL Statement API. Returns one dict per (question, judge) pair with all ASI fields.
2. **`{judge}/metadata` columns:** Fall back to reading metadata columns from `eval_result.tables["eval_results"]` DataFrame.
3. **Assessments list:** Parse the `assessments` list from evaluation results via `_extract_asi_from_assessments()`.
4. **Regex on rationale (last resort):** `_infer_blame_from_rationale()` parses free-text judge rationale for blame keywords.

**Structured fields consumed by `cluster_failures()`:** `asi_severity`, `asi_confidence`, `asi_wrong_clause`, `asi_expected_value`, `asi_actual_value`, `asi_missing_metadata`, `asi_ambiguity_detected`.

**Generic counterfactual_fix handling:** When `counterfactual_fix` contains only generic guidance (e.g., "Review table/column references in Genie metadata", "Check X in metadata", "Verify Y"), the optimizer SHOULD ignore it and use `blame_set` + `wrong_clause` to synthesize a specific fix. Generic fixes are treated as equivalent to "no fix provided." The `_describe_fix()` function detects these by checking if the fix starts with generic verbs ("Review", "Check", "Verify") without referencing a specific asset, column, or TVF name.

**Proposal enrichment:** Each proposal emitted by `generate_metadata_proposals()` includes an `asi` dict with `failure_type`, `blame_set`, `severity`, `counterfactual_fixes`, `ambiguity_detected` from the source cluster. This enables the applier's `proposals_to_patches()` to generate targeted Patch DSL patches.

## Blast Radius Tracking (P13)

Penalizes patch sets that touch too many objects to limit regression risk.

- **adjusted_score** = raw_score - 0.1 × (blast_objects / total_objects)
- **Max 5 objects** per patch set (enforced by validate_patch_set when use_patch_dsl=True)

## Introspective Analysis (L1)

When L2 (GEPA) is not used, the optimizer clusters failures and generates proposals:

1. **Cluster failures** by systemic root cause (>=2 questions per cluster). `cluster_failures()` returns cluster dicts with: `cluster_id`, `root_cause`, `question_ids`, `affected_judge`, `confidence`, `asi_failure_type`, `asi_blame_set`, `asi_counterfactual_fixes`.
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
| Wrong join | 1 (UC Tables) | `ALTER TABLE ... SET TBLPROPERTIES` |
| Wrong aggregation | 2 (Metric Views) | `CREATE OR REPLACE VIEW` |
| Wrong filter | 3 (TVFs) | `CREATE OR REPLACE FUNCTION` |
| Missing filter (TVF param format) | 3 (TVFs) | `CREATE OR REPLACE FUNCTION` — fix COMMENT PARAMS section |
| Missing filter (temporal on MV) | 2 (Metric Views) | `CREATE OR REPLACE VIEW` — add temporal filtering guidance to date dimension |
| Missing filter (date param value) | 3 (TVFs) | `CREATE OR REPLACE FUNCTION` — fix COMMENT SYNTAX example |
| Missing temporal filter | 2 (Metric Views) | `CREATE OR REPLACE VIEW` — add date dimension comment with temporal patterns |
| Monitoring gap, stale data, data freshness | 4 (Monitoring) | `ALTER TABLE ... SET TBLPROPERTIES (monitoring config)` |
| ML feature missing, model scoring error, feature store mismatch | 5 (ML Tables) | `ALTER TABLE ... SET TBLPROPERTIES (ML feature metadata)` |
| Repeatability issue (TABLE/MV) | 1 (UC Tables/Columns) | `ALTER TABLE SET TBLPROPERTIES`, `ALTER COLUMN COMMENT` |
| Repeatability issue (TVF) | 6 (Instructions) | `PATCH /api/2.0/genie/spaces/{id}` |
| Wrong asset routing | 6 (Instructions) | `PATCH /api/2.0/genie/spaces/{id}` |

**Repeatability → Lever routing rationale:** Repeatability issues often stem from unstructured metadata creating an ambiguous search space for the LLM. Structured metadata (Lever 1) -- `business_definition`, `synonyms[]`, `grain`, `join_keys[]`, `do_not_use_when[]`, `preferred_questions[]` in column comments, plus UC tags like `preferred_for_genie=true`, `deprecated_for_genie=true`, `domain=<value>` -- narrows the search space and reduces SQL variance. Structured metadata can be added as **tags** (via `TBLPROPERTIES`/`ALTER TABLE SET TAGS`) or within **descriptions/column comments** depending on the situation. When the asset is already a TVF (output is already constrained by function signature), the optimizer falls back to Lever 6 (instructions for deterministic parameter selection). TVF conversion remains a secondary recommendation for TABLE/MV assets when structured metadata alone is insufficient.

### TVF COMMENT Format (Lever 3)

TVF COMMENTs are the primary mechanism for guiding Genie's parameter selection. The COMMENT must follow this structured bullet-point layout — Genie parses these sections to understand when/how to call the function:

```
• PURPOSE: What this function returns and when to use it
• BEST FOR: Specific query patterns that should use this TVF
• NOT FOR: Patterns that should use a different asset (with redirect to preferred asset)
• RETURNS: Column list (helps Genie understand output schema)
• PARAMS:
  - param_name (TYPE): Description. Format: <format_rule>.
    Pass NULL (not the string 'NULL') to omit this filter.
  - date_param (STRING): Start date. Format: CAST(DATE_ADD(CURRENT_DATE(), -N) AS STRING).
    Do NOT use hardcoded dates like '2025-01-01'.
• SYNTAX: SELECT * FROM schema.tvf_name(CAST(DATE_ADD(CURRENT_DATE(), -365) AS STRING), NULL)
• NOTE: Additional constraints (e.g., ROW_NUMBER ranking, no GROUP BY needed)
```

**Critical:** The `PARAMS` and `SYNTAX` sections directly control Genie's parameter handling. Without explicit NULL-handling guidance and dynamic date syntax examples, Genie consistently: (1) passes the string literal `'NULL'` instead of SQL `NULL` for optional parameters, and (2) uses hardcoded dates like `'2025-02-23'` instead of dynamic expressions.

### Metadata Effectiveness by Complexity

Column comments and Genie Space instructions have varying effectiveness depending on expression complexity. The optimizer MUST factor this into proposal generation — do not waste iterations on metadata changes for patterns with LOW effectiveness.

| Temporal Pattern | Example Phrasing | Required SQL | Metadata Lever | Effectiveness |
|-----------------|------------------|-------------|----------------|---------------|
| "this year" | "total revenue this year" | `WHERE YEAR(date_col) = YEAR(CURRENT_DATE())` | Column comment (Lever 1) | **HIGH** — single function, Genie reliably applies |
| "last N days" | "bookings last 30 days" | `WHERE date_col >= DATE_ADD(CURRENT_DATE(), -30)` | Column comment or TVF SYNTAX (Lever 1/3) | **HIGH** — single function, Genie reliably applies |
| "last month" | "revenue last month" | `WHERE date_col >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1)) AND date_col < DATE_TRUNC('month', CURRENT_DATE())` | Genie Space instruction (Lever 6) | **MEDIUM** — range with two boundaries, sometimes partially applied |
| "last quarter" | "total revenue last quarter" | `WHERE date_col >= ADD_MONTHS(DATE_TRUNC('quarter', CURRENT_DATE()), -3) AND date_col < DATE_TRUNC('quarter', CURRENT_DATE())` | Genie Space instruction (Lever 6) | **LOW** — nested functions, Genie frequently ignores |
| "YoY comparison" | "revenue growth vs last year" | Window functions with `LAG(..., 12)` | TVF (Lever 3) or pre-computed column | **LOW** — complex logic beyond metadata influence |

**Escalation ladder for LOW-effectiveness patterns:**

1. **Column comment** (try first, expect failure for complex expressions)
2. **Genie Space instruction** with explicit SQL example (try second)
3. **TVF with temporal parameter** (absorb complexity into function signature)
4. **Schema simplification** — pre-computed columns (e.g., `fiscal_quarter`, `is_last_quarter` boolean, `quarter_start_date`) that reduce the expression to a simple equality filter

When the optimizer generates a proposal for a LOW-effectiveness pattern and it fails in the subsequent evaluation, it SHOULD escalate to the next rung instead of re-proposing the same lever.

## Repeatability Failure Clustering

When cross-iteration repeatability checks detect questions whose SQL changed between iterations (flagged as `repeatability_issue` synthetic failures), the optimizer uses specialized clustering to identify and fix the root cause:

### 1. Detect Asset-Type Oscillation

Examine the SQL variants across iterations for each non-repeatable question. Look for oscillation patterns:
- **TABLE ↔ MV oscillation:** Genie alternates between querying a base table and its metric view (e.g., `SELECT ... FROM dim_product` vs `SELECT ... FROM mv_product_summary`)
- **TVF ↔ TABLE/MV oscillation:** Genie alternates between calling a TVF and direct table/MV queries
- **Parameter oscillation:** TVF calls with different parameter values across runs

### 2. Map to Lever Sequence

Based on the oscillation type, apply fixes in this specific order:

1. **Lever 1 (Structured Metadata):** Add decisive metadata to disambiguate:
   - `preferred_for_genie=true` UC tag on the canonical asset
   - `deprecated_for_genie=true` tag on the non-canonical asset
   - `business_definition` in column comments with synonym phrases
   - `do_not_use_when[]` in column comments for the non-preferred asset
2. **Lever 2 (MV YAML + negative routing):** If oscillation involves metric views, add measure-level comments with negative routing (e.g., "Use this MV for aggregated KPIs, NOT for row-level lists")
3. **Lever 6 (Instructions, last resort):** If structured metadata alone is insufficient, add explicit routing instructions to the Genie Space instructions

### 3. Bilateral Disambiguation (MANDATORY)

**Genie routing is probabilistic, not deterministic.** Bilateral disambiguation improves routing odds but does not guarantee consistency across runs. A question that routes correctly in iteration N may regress in iteration N+1 when routing remains ambiguous. This is a known platform behavior (KGL-2), and usually indicates metadata authoring needs clearer positive and negative routing guidance to reduce ambiguity.

When a question oscillates between two asset types, **BOTH sides** of the disambiguation must be addressed:
- **Positive routing** (Lever 1/2): Tell the preferred asset it IS the right choice for this question pattern
- **Negative routing** (Lever 3): Tell the competing asset it is NOT the right choice

Applying only one side is insufficient -- both assets will continue competing. Example: if a TVF COMMENT says "BEST FOR: total revenue last quarter" and the MV has positive routing for the same pattern, the TVF COMMENT must add `NOT FOR: Simple total revenue without destination breakdown (use booking_analytics_metrics MEASURE(total_revenue))`.

The optimizer MUST auto-detect asset-type oscillation in failure clusters and generate proposals for BOTH the preferred and competing assets.

**Routing-sensitive benchmarks require repeatability testing:** For any question where bilateral disambiguation was applied, the evaluator SHOULD run 3-5 passes of the same question and flag inconsistent routing. If routing variance exceeds 40% (e.g., 2 of 5 passes route incorrectly), document the question as routing-sensitive in benchmark metadata and accept the variance as a platform limitation rather than generating additional metadata iterations.

**Template pair:**

```sql
-- Positive routing (preferred asset — Lever 1 or 2):
ALTER TABLE catalog.schema.<preferred_table>
ALTER COLUMN <dimension> COMMENT '... ALWAYS use this column with MEASURE(<measure>) for <pattern>. Do NOT use <competing_tvf> for this pattern.';

-- Or for Metric Views (Lever 2):
-- Update MV YAML dimension description: "ALWAYS use this for <pattern>"

-- Negative routing (competing asset — Lever 3):
-- In the competing TVF's COMMENT, update:
--   BEST FOR: Remove <pattern> from the list
--   NOT FOR: "<pattern> (use <preferred_asset> MEASURE(<measure>) instead)"
```

**Concrete example:**

```sql
-- Positive: Tell MV it IS the right choice for "revenue by destination country"
ALTER TABLE catalog.schema.booking_analytics_metrics
ALTER COLUMN destination_country COMMENT 'Country of destination property. ALWAYS use this dimension with MEASURE(total_revenue) for revenue by country queries.';

-- Negative: Tell TVF it is NOT the right choice for simple country revenue
-- In get_revenue_summary COMMENT, change:
--   BEST FOR: "Revenue trends by time period with multi-metric breakdown"
--   NOT FOR: "Revenue by destination country (use booking_analytics_metrics MEASURE(total_revenue))"
```

### 4. Verify

After each lever application, re-run the specific non-repeatable question 3x to confirm oscillation is resolved. Only proceed to the next lever if the question still oscillates.

## Lever 6 Instruction Specificity Rules

Lever 6 (Genie Space instructions) is prone to overcorrection when routing instructions are too broad. An overly generic instruction like "Revenue by destination → MV" can inadvertently redirect TVF-appropriate queries to the MV.

**Rules:**

1. Every routing instruction MUST include both the POSITIVE case and NEGATIVE exclusion
2. Use the question's exact phrasing or a close paraphrase, not generic patterns
3. Distinguish simple aggregations (MV) from date-ranged or parameterized detail queries (TVF)

**GOOD:**
```
"Revenue by destination country this year" → booking_analytics_metrics (MV).
"Revenue by destination for last 6 months with breakdown" → get_revenue_summary (TVF).
```

**BAD:**
```
"Revenue by destination" → booking_analytics_metrics (MV).
```
The bad example is too broad — it matches "Revenue by destination for last 6 months" which should route to the TVF, causing an overcorrection.

**Overcorrection recovery:** If a Lever 6 instruction causes a regression (a previously correct question now fails), immediately narrow the instruction by adding the negative exclusion, or remove the instruction and rely on Lever 1/2/3 metadata instead.

## Known Genie Limitations

Documented platform behaviors that metadata guidance alone cannot resolve. When the optimizer encounters these, it should recommend code-level workarounds instead of additional metadata iterations.

| # | Limitation | Observed Behavior | Metadata Attempted | Outcome | Recommended Workaround |
|---|-----------|-------------------|-------------------|---------|----------------------|
| KGL-1 | Optional TVF parameters: `'NULL'` string literal | Genie generates `param => 'NULL'` instead of `NULL` when using named argument syntax | COMMENT with "pass NULL not 'NULL'", SYNTAX with positional NULL, Genie Space instructions to avoid named args | **Not fixed** after 3+ iterations | TVF body coercion: `IF param = 'NULL' THEN NULL ELSE param END`; SYNTAX examples with positional args only |
| KGL-2 | Probabilistic asset routing | Genie non-deterministically routes questions between competing assets (e.g., MV vs TVF) even with bilateral disambiguation | Positive + negative routing on both assets, Genie Space routing instructions | **Improved** but not guaranteed — routing is probabilistic | Bilateral disambiguation (mandatory), repeatability testing (3-5 passes), accept variance as platform behavior |
| KGL-3 | Complex temporal expressions ignored | Genie does not apply complex date filters (`ADD_MONTHS(DATE_TRUNC('quarter', CURRENT_DATE()), -3)`) despite column comments and instructions | Column comments with explicit SQL, Genie Space instructions | **Not fixed** for nested date functions | Schema simplification (pre-computed quarter columns), or TVF with temporal parameter |

**Escalation rule:** If the same failure persists for 2+ iterations with targeted metadata changes, check this table before generating another metadata proposal. If the failure matches a known limitation, emit the code-level workaround as the proposal instead of additional COMMENT changes.

**TVF body coercion pattern (KGL-1):**

```sql
CREATE OR REPLACE FUNCTION schema.my_tvf(
  start_date STRING,
  optional_filter STRING
)
RETURNS TABLE(...)
COMMENT '...'
RETURN
  SELECT * FROM my_table
  WHERE date_col >= start_date
    AND (
      CASE WHEN optional_filter IS NULL OR optional_filter = 'NULL'
           THEN TRUE
           ELSE category = optional_filter
      END
    );
```

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| TVF COMMENT missing PARAMS null-handling guidance | Genie passes `'NULL'` string literal for optional params | Add "pass NULL, do NOT pass the string literal 'NULL'" to each optional param in PARAMS section |
| TVF COMMENT SYNTAX shows hardcoded dates | Genie uses hardcoded dates instead of dynamic expressions | Show `CAST(DATE_ADD(CURRENT_DATE(), -N) AS STRING)` in SYNTAX |
| Overly broad Lever 6 routing instruction | Overcorrects — redirects TVF-appropriate queries to MV | Include both positive routing AND negative exclusion per instruction; use exact question phrasing |
| Bare boolean scores (no rationale) | GEPA/introspection can't learn | Always use `Feedback(value=..., rationale=...)` |
| Batch-applying all proposals at once | Can't isolate regressions | Apply one cluster's proposals per iteration |
| Running L2 (GEPA) and judge optimization together | Confounding effects | Always separate: metadata first, judge prompts only if judges are bottleneck |
| Running GEPA before exhausting Levers 1-5 | Optimization budget wasted on lowest-priority lever | Always introspect Levers 1-5 first; GEPA is Lever 6 only |
| Assuming GEPA is unavailable without checking | L2 tier never attempted | Install `gepa>=0.1.0` and use the GEPA template notebook |
| Re-proposing column comments for complex temporal patterns after failure | Wasted iterations with no improvement | Check Metadata Effectiveness table — LOW patterns ("last quarter", "YoY") need escalation to TVF or schema simplification, not more comments (KGL-3) |
| Generating 3+ metadata iterations for same failure without checking Known Genie Limitations | Infinite loop against platform ceiling | After 2 failed iterations on the same failure, check KGL table; if it matches, emit code-level workaround instead |

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

**Note:** UC/ASI reading (`read_asi_from_uc(catalog, schema, run_id, warehouse_id)`) is triggered by the orchestrator when passing `eval_results` with `run_id` and UC connection params — not via CLI args. The CLI uses `--eval-results`, `--metadata-snapshot`, `--output`, `--tier`, `--use-asi`, `--use-patch-dsl`, `--use-gepa`, `--space-id`, `--target-lever`, and `--recommended`.

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

## Version History

- **v4.2.0** (Feb 23, 2026) - Phase 8: Optimization loop feedback (Issues 14-16). Known Genie Limitations table (KGL-1 through KGL-3) with code-level workaround patterns. TVF body coercion pattern for `'NULL'` string literal (KGL-1). Bilateral disambiguation updated with probabilistic routing language and 3-5 pass repeatability testing guidance (KGL-2). Metadata Effectiveness by Complexity table with escalation ladder for temporal patterns (KGL-3). 2 new Common Mistakes (complex temporal re-proposal, infinite iteration loop). Escalation rule: after 2 failed iterations on the same failure, check KGL table before generating more metadata proposals.
- **v4.1.0** (Feb 23, 2026) - Phase 7: ASI-to-metadata loop gap remediation (13 issues). `missing_filter` sub-type routing in `_map_to_lever()` (TVF param -> L3, temporal -> L2, default -> L3). TVF COMMENT Format section with structured bullet-point template (PURPOSE, BEST FOR, NOT FOR, RETURNS, PARAMS, SYNTAX, NOTE). Concrete bilateral disambiguation templates (positive + negative routing SQL examples). Lever 6 Instruction Specificity Rules with overcorrection prevention (GOOD/BAD examples). `missing_temporal_filter` added to FAILURE_TAXONOMY (23 types). Generic counterfactual_fix detection in `_describe_fix()` — skips vague fixes and falls through to `blame_set` + `wrong_clause` synthesis. `judge_quality_feedback` output added to optimizer for SIMBA Tier 3 alignment. 3 new Common Mistakes (TVF COMMENT PARAMS, TVF COMMENT SYNTAX, Lever 6 overcorrection).
- **v4.0.0** (Feb 23, 2026) - Phase 6 architectural lessons. Added ASI Consumption Contract section with UC-first priority chain (`read_asi_from_uc()` -> columns -> assessments -> regex). Flipped feature flag defaults: `use_asi=True`, `use_patch_dsl=True`. Added bilateral disambiguation to Repeatability Failure Clustering (positive + negative routing mandatory). UC/ASI reading is triggered by the orchestrator (not CLI args). Version bumped from v3.8.0.
- **v3.8.0** (Feb 22, 2026) - Repeatability v2: structured metadata routing. Changed `_map_to_lever()` for `repeatability_issue`: TABLE/MV now routes to Lever 1 (structured metadata -- tags, column comments with business_definition, synonyms, grain, join_keys, do_not_use_when) instead of Lever 3 (TVFs); TVF routes to Lever 6 (instructions). Added `blame_set` parameter to `_map_to_lever()` for context-aware routing. Rewrote `_REPEATABILITY_FIX_BY_ASSET` with structured metadata recommendations. Fixed `_describe_fix()` bug reading `dominant_asset` instead of `asi_blame_set`. Updated `generate_metadata_proposals()` and `_dual_persist_paths()` to pass `blame_set` through.
- **v3.7.0** (Feb 22, 2026) - Repeatability judge integration. Added `repeatability_issue` to `_map_to_lever()` mapping (lever 3, TVFs). Enhanced `_describe_fix()` with asset-type-specific recommendations for repeatability clusters: MV-routed questions recommend TVF conversion, TABLE-routed recommend TVF wrappers, TVF-routed recommend deterministic parameter instructions. Updated Root Cause to Lever Mapping table in SKILL.md.
- **v3.5.0** (Feb 22, 2026) - ASI-aware clustering (Phase 3). `cluster_failures()` now prefers `failure_type`/`blame_set` from ASI metadata over keyword extraction; `_describe_fix()` uses `counterfactual_fix`; `_map_to_lever()` accepts optional `asi_failure_type` parameter for precise routing.
- **v3.0.0** (Feb 2026) - Initial optimizer with introspection, GEPA L2, Patch DSL, blast radius tracking.

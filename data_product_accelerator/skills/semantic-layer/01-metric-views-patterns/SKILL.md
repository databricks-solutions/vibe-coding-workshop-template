---
name: metric-views-patterns
description: Standard patterns for creating Databricks Metric Views with semantic metadata for Genie and AI/BI. Use when creating metric views, troubleshooting metric view creation errors, validating schema references before deployment, implementing joins (including snowflake schema patterns), or optimizing metric views for Genie natural language queries.
metadata:
  author: prashanth subrahmanyam
  version: "2.0"
  domain: semantic-layer
  role: worker
  pipeline_stage: 6
  pipeline_stage_name: semantic-layer
  called_by:
    - semantic-layer-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-metric-views/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "latest"
    - name: "databricks-docs-composability"
      url: "https://docs.databricks.com/aws/en/metric-views/data-modeling/composability"
      relationship: "upstream"
      last_synced: "2026-02-20"
    - name: "databricks-docs-semantic-metadata"
      url: "https://docs.databricks.com/aws/en/metric-views/data-modeling/semantic-metadata"
      relationship: "upstream"
      last_synced: "2026-02-20"
    - name: "databricks-docs-joins"
      url: "https://docs.databricks.com/aws/en/metric-views/data-modeling/joins"
      relationship: "upstream"
      last_synced: "2026-02-20"
    - name: "databricks-docs-window-measures"
      url: "https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures"
      relationship: "upstream"
      last_synced: "2026-02-20"
    - name: "databricks-docs-syntax"
      url: "https://docs.databricks.com/aws/en/metric-views/data-modeling/syntax"
      relationship: "upstream"
      last_synced: "2026-02-20"
    - name: "databricks-docs-materialization"
      url: "https://docs.databricks.com/aws/en/metric-views/materialization"
      relationship: "upstream"
      last_synced: "2026-02-20"
    - name: "databricks-docs-create-sql"
      url: "https://docs.databricks.com/aws/en/metric-views/create/sql"
      relationship: "upstream"
      last_synced: "2026-02-20"
---

# Metric Views Patterns for Genie & AI/BI

## Overview

Metric Views provide a semantic layer for natural language queries via Genie and AI/BI dashboards. This skill standardizes the YAML structure for comprehensive, LLM-friendly metric definitions following Databricks Metric View Specification v1.1.

**Predecessor:** Gold tables must exist before creating metric views. Use `gold-layer-design` + `gold-layer-setup` skills first.

**Key Capabilities:**
- Create metric views with proper SQL syntax (`WITH METRICS LANGUAGE YAML`)
- Validate schemas before deployment to prevent 100% of common errors
- Structure joins (direct and snowflake schema patterns)
- Optimize comments for Genie natural language queries
- Handle SCD2 dimensions with proper `is_current` filtering

## When to Use This Skill

Use this skill when:
- Creating new metric views for Genie Spaces
- Troubleshooting metric view creation errors
- Validating schema references before deployment
- Implementing joins (including transitive relationships)
- Optimizing metric views for Genie natural language queries
- Ensuring compliance with v1.1 specification
- Following the requirements gathering template to design metric views

## Prerequisites

⚠️ **MANDATORY:** Complete these before creating metric views:
- [ ] Gold layer tables exist in Unity Catalog (use `gold-layer-design` + `gold-layer-setup` skills)
- [ ] Gold layer YAML schemas exist in `gold_layer_design/yaml/` (for validation script)
- [ ] Serverless SQL warehouse available (for metric view creation and querying)
- [ ] Databricks Runtime 17.2+ (required for YAML version 1.1)

## MCP Tools (from upstream databricks-metric-views)

The `manage_metric_views` MCP tool supports all metric view operations:

| Action | Description |
|--------|-------------|
| `create` | Create a metric view with dimensions and measures |
| `alter` | Update a metric view's YAML definition |
| `describe` | Get the full definition and metadata |
| `query` | Query measures grouped by dimensions |
| `drop` | Drop a metric view |
| `grant` | Grant SELECT privileges to users/groups |

## Quick Start (2 hours)

**What You'll Create:**
1. `metric_views/{view_name}.yaml` — Semantic definitions (dimensions, measures, joins, formats)
2. `create_metric_views.py` — Script reads YAML, creates views with `WITH METRICS LANGUAGE YAML`
3. `metric_views_job.yml` — Asset Bundle job for deployment

**Deploy:** `databricks bundle deploy -t dev && databricks bundle run metric_views_job -t dev`

## Critical Rules

### ⚠️ CRITICAL: Correct SQL Syntax

**Metric views MUST be created using `WITH METRICS LANGUAGE YAML` syntax:**

```python
create_sql = f"""
CREATE OR REPLACE VIEW {fully_qualified_name}
WITH METRICS
LANGUAGE YAML
COMMENT '{view_comment_escaped}'
AS $$
{yaml_str}
$$
"""
```

**Key Requirements:**
1. `WITH METRICS` — Identifies the view as a metric view
2. `LANGUAGE YAML` — Specifies YAML format
3. `AS $$ ... $$` — YAML content wrapped in dollar-quote delimiters
4. No SELECT statement — The YAML definition IS the view definition
5. `version` field — Must be included in each metric view YAML

**❌ WRONG:** Regular view with TBLPROPERTIES (creates regular VIEW, not METRIC_VIEW)

### ⚠️ CRITICAL: v1.1 Unsupported Fields

**These fields will cause errors and MUST NOT be used:**

| Field | Error | Action |
|-------|-------|--------|
| `name` | `Unrecognized field "name"` | ❌ NEVER include — name is in CREATE VIEW statement |
| `time_dimension` | `Unrecognized field "time_dimension"` | ❌ Remove entirely |
| `window_measures` | `Unrecognized field "window_measures"` | ❌ Remove top-level `window_measures:` array. Individual measure `window:` property is Experimental (v0.1 only, DBR 16.4-17.1). See `references/composability-patterns.md` for details. |
| `join_type` | Unsupported | ❌ Remove — defaults to LEFT OUTER JOIN |
| `table` (in joins) | `Missing required creator property 'source'` | ✅ Use `source` instead |

### ⚠️ MANDATORY: Pre-Creation Schema Validation

**ALWAYS validate schemas BEFORE creating metric view YAML. 100% of deployment failures are preventable schema issues.**

**Schema Validation Checklist:**
- [ ] Verified source table schema (ran DESCRIBE TABLE or checked YAML)
- [ ] Verified all joined table schemas
- [ ] Created column reference checklist for all tables
- [ ] Validated every dimension `expr` column exists
- [ ] Validated every measure `expr` column exists
- [ ] Validated join key columns exist in both tables
- [ ] Verified no transitive joins (all joins are source → table)
- [ ] For COUNT measures, verified primary key column exists
- [ ] For SCD2 joins, verified `is_current` column exists

See `references/validation-checklist.md` for detailed validation steps.

### ⚠️ CRITICAL: Source Table Selection

**Rule:** Revenue/bookings/transactions → FACT table. Property/host counts → DIMENSION table.

**❌ WRONG:** Revenue from dimension table (under-reports by 4x)
```yaml
source: ${catalog}.${schema}.dim_property  # ❌ Wrong for revenue!
```

**✅ CORRECT:** Revenue from fact table
```yaml
source: ${catalog}.${schema}.fact_booking_daily  # ✅ Correct for revenue!
```

### ⚠️ CRITICAL: Transitive Join Limitations

**Metric Views DO NOT support transitive/chained joins** (where join B's `on` clause references join A instead of `source`).

**How to detect:** If ANY join's `on` clause references a join alias (not `source`), it is transitive and will fail.

**❌ WRONG:** Transitive join (join B references join A)
```yaml
joins:
  - name: dim_property                              # Join A
    source: catalog.schema.dim_property
    'on': source.property_id = dim_property.property_id
  - name: dim_destination                            # Join B
    source: catalog.schema.dim_destination
    'on': dim_property.destination_id = dim_destination.destination_id  # ❌ References dim_property!
```

**✅ FIX 1 (Preferred — simplest): Use denormalized columns from existing dimension**

If `dim_property` already has `destination_name` and `destination_country`, reference them directly — no second join needed:
```yaml
dimensions:
  - name: destination_name
    expr: dim_property.destination_name  # ✅ Already in dim_property
  - name: destination_country
    expr: dim_property.destination_country
```

**✅ FIX 2: Snowflake schema (nested joins) — requires DBR 17.1+**
```yaml
joins:
  - name: dim_property
    source: catalog.schema.dim_property
    'on': source.property_id = dim_property.property_id
    joins:  # ✅ Nested under dim_property — snowflake schema
      - name: dim_destination
        source: catalog.schema.dim_destination
        'on': dim_property.destination_id = dim_destination.destination_id
```

**Validation gate:** Before generating YAML, inspect all join `on` clauses. If the left side of any `on` references a join name (not `source`), restructure as nested joins or use denormalized columns.

See `references/advanced-patterns.md` for additional snowflake schema examples.

## Implementation Workflow

### Phase 1: Design (30 min)

**Read:** `references/requirements-template.md`

- [ ] Identify fact table as primary source
- [ ] List dimensions to join (2-5 dimension tables)
- [ ] Define key measures (5-10 measures with aggregation type)
- [ ] List common user questions (guides synonym creation)
- [ ] Map synonyms for each dimension and measure (3-5 each)

### Phase 2: YAML Creation (1 hour)

**Read:** `references/yaml-reference.md` and `references/advanced-patterns.md`

- [ ] Create one YAML file per metric view (filename = view name)
- [ ] Define `source` table (fully qualified with `${catalog}` and `${gold_schema}` placeholders)
- [ ] Add `joins` with `name`, `source`, `'on'` (include `is_current = true` for SCD2)
- [ ] Define dimensions with correct prefix (`source.` or `{join_name}.`)
  - [ ] Business-friendly comments and display names
  - [ ] 3-10 synonyms each (max 10 per field, max 255 chars each)
- [ ] Define measures with correct aggregation (SUM, AVG, COUNT)
  - [ ] Proper formatting (currency, number, percentage)
  - [ ] Comprehensive comments for Genie
  - [ ] 3-10 synonyms each (max 10 per field, max 255 chars each)

### Phase 3: Script & Bundle (30 min)

**Read:** `references/implementation-workflow.md`

- [ ] Validate YAML with `scripts/validate_metric_view.py`
- [ ] Use `scripts/create_metric_views.py` for deployment
- [ ] Configure Asset Bundle job (see `assets/templates/metric-views-job-template.yml`)
- [ ] Add YAML file sync to `databricks.yml`

### Phase 4: Deploy & Test (30 min)

**Read:** `references/validation-queries.md`

- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run: `databricks bundle run metric_views_job -t dev`
- [ ] Verify: `DESCRIBE EXTENDED` shows Type: METRIC_VIEW
- [ ] Test: `SELECT ... MEASURE(\`Total Revenue\`) ... GROUP BY ...`
- [ ] Test with Genie: Ask natural language questions

## Quick Reference

### YAML Structure (v1.1)

```yaml
version: "1.1"
comment: >
  PURPOSE: [One-line description]
  BEST FOR: [Question 1] | [Question 2] | [Question 3]
  NOT FOR: [What to avoid] (use [correct_asset] instead)
  DIMENSIONS: [dim1], [dim2], [dim3]
  MEASURES: [measure1], [measure2], [measure3]
  SOURCE: [fact_table] ([domain] domain)
  JOINS: [dim_table1] ([description])
  NOTE: [Critical caveats]

source: ${catalog}.${gold_schema}.<fact_table>
filter: <sql_boolean_expression>  # Optional: WHERE clause applied to all queries

joins:
  - name: <dim_table_alias>
    source: ${catalog}.${gold_schema}.<dim_table>
    'on': source.<fk> = <dim_table_alias>.<pk> AND <dim_table_alias>.is_current = true

dimensions:
  - name: <dimension_name>
    expr: source.<column>
    comment: <Business description>
    display_name: <User-Friendly Name>
    synonyms: [<alt1>, <alt2>]

measures:
  - name: <measure_name>
    expr: SUM(source.<column>)
    comment: <Business description>
    display_name: <User-Friendly Name>
    format:
      type: currency|number|percentage
      currency_code: USD
      decimal_places:
        type: exact|all
        places: 2
    synonyms: [<alt1>, <alt2>]
```

**Valid format types (exhaustive):**

| Type | Use For | Common Mistake |
|------|---------|----------------|
| `byte` | Data sizes (storage, memory) | — |
| `currency` | Monetary values (revenue, cost) | — |
| `date` | Date-only values | — |
| `date_time` | Timestamp values | — |
| `number` | Counts, averages, decimals, integers | ❌ `decimal`, ❌ `integer` |
| `percentage` | Ratios, rates, percentages | ❌ `percent` |

**⚠️ `percent` is NOT valid** (use `percentage`). **`decimal` is NOT valid** (use `number`).

### Column References

- **Main table columns:** Use `source.` prefix in all `expr` fields
- **Joined table columns:** Use join `name` as prefix (e.g., `dim_store.column_name`)
- **Never reference table names directly:** Use `source.` or `{join_name}.`

### Join Requirements

- Each join **MUST have** `name`, `source`, and either `'on'` or `using`
- `ON` clause: boolean expression using `source.` for main table, join name for joined table (quote the key: `'on'`)
- `USING` clause: array of column names shared between source and join table
- Each first-level join must reference `source` (NOT another join alias — that's transitive)
- For transitive relationships, use nested `joins:` (snowflake schema, DBR 17.1+) or denormalized columns
- SCD2 joins must include `AND {dim_table}.is_current = true`
- **MAP type columns are NOT supported** in joined tables

## Core Patterns

### Composability (MEASURE Function)

Metric views support **composability** — building complex metrics by referencing simpler measures via the `MEASURE()` function. Define atomic measures first, then compose derived KPIs:

```yaml
measures:
  - name: total_revenue
    expr: SUM(source.net_revenue)
  - name: order_count
    expr: COUNT(source.order_id)
  - name: avg_order_value
    expr: MEASURE(total_revenue) / MEASURE(order_count)  # ✅ Composed measure
```

**Measure-level filtering** with `FILTER` clause:
```yaml
  - name: fulfilled_orders
    expr: COUNT(1) FILTER (WHERE source.order_status = 'F')
  - name: fulfillment_rate
    expr: MEASURE(fulfilled_orders) / MEASURE(order_count)
    format:
      type: percentage
```

**Best practices:** Define atomic measures (SUM, COUNT, AVG) first; always use `MEASURE()` to reference other measures (never repeat the aggregation logic).

See `references/composability-patterns.md` for full guide including conditional logic, window measures (Experimental), and complete examples.

### Standardized Comment Format (v3.0)

Use structured format for Genie optimization:

```yaml
comment: >
  PURPOSE: Comprehensive cost analytics for Databricks billing and usage analysis.
  
  BEST FOR: Total spend by workspace | Cost trend over time | SKU cost breakdown
  
  NOT FOR: Commit/contract tracking (use commit_tracking) | Real-time cost alerts
  
  DIMENSIONS: usage_date, workspace_name, sku_name, owner, tag_team
  
  MEASURES: total_cost, total_dbus, cost_7d, cost_30d
  
  SOURCE: fact_usage (billing domain)
  
  JOINS: dim_workspace (workspace details), dim_sku (SKU details)
  
  NOTE: Cost values are list prices. Actual billed amounts may differ.
```

### Dimension & Measure Patterns

See `references/advanced-patterns.md` for complete dimension patterns (geographic, product, time), measure patterns (revenue, count, percentage), and a full worked retail example.

## Common Mistakes to Avoid

Top 5 mistakes (with paired wrong/correct examples): wrong syntax (TBLPROPERTIES), unsupported fields (`time_dimension`, `window_measures`), wrong column references, including `name` in YAML, transitive joins.

See `references/advanced-patterns.md` for detailed wrong/correct code examples for each mistake.

## Python Script Error Handling

Key rules: strip `name` before `yaml.dump()`, drop existing VIEW/TABLE before CREATE, track failures and raise `RuntimeError`, verify METRIC_VIEW type via `DESCRIBE EXTENDED`.

See `scripts/create_metric_views.py` for the full working script and `references/implementation-workflow.md` for the detailed error handling patterns.

## Time Estimates

| Metric Views | Design | YAML Creation | Deploy & Test | Total |
|---|---|---|---|---|
| 1 view | 20 min | 30 min | 20 min | ~1 hour |
| 2-3 views | 30 min | 1 hour | 30 min | ~2 hours |
| 5+ views | 1 hour | 2 hours | 30 min | ~3.5 hours |

## Reference Files

- **`references/yaml-reference.md`** — Complete YAML fields, syntax, format options
- **`references/advanced-patterns.md`** — Dimension/measure patterns, joins, snowflake schema, worked examples
- **`references/composability-patterns.md`** — MEASURE() function, FILTER clause, window measures (Experimental)
- **`references/validation-checklist.md`** — Pre-creation validation steps
- **`references/requirements-template.md`** — Design template for dimensions, measures, joins
- **`references/implementation-workflow.md`** — Step-by-step creation workflow
- **`references/validation-queries.md`** — SQL queries for deployment verification

## Scripts & Assets

- **`scripts/validate_metric_view.py`** — Pre-deployment column reference validation
- **`scripts/create_metric_views.py`** — YAML loading, parameter substitution, METRIC_VIEW verification
- **`assets/templates/metric-view-template.yaml`** — Starter YAML template
- **`assets/templates/metric-views-job-template.yml`** — Asset Bundle job template

## Materialization (Experimental)

Metric views support optional materialization for pre-computed aggregations. Lakeflow Spark Declarative Pipelines orchestrates materialized views, and the query optimizer automatically routes queries to the best materialized view using aggregate-aware query rewriting.

```yaml
materialization:
  schedule: every 6 hours
  mode: relaxed
  materialized_views:
    - name: baseline
      type: unaggregated
    - name: revenue_breakdown
      type: aggregated
      dimensions: [category, color]
      measures: [total_revenue]
```

**Materialized view types:** `unaggregated` (full data) and `aggregated` (pre-computed for specific dimension/measure combinations). Check refresh status with `DESCRIBE TABLE EXTENDED`.

Requires serverless compute enabled. Currently experimental — use for high-query-volume metric views where pre-computation reduces latency.

## Common Issues

| Issue | Solution |
|-------|----------|
| `SELECT *` not supported | Must explicitly list dimensions and use `MEASURE()` for measures |
| "Cannot resolve column" | Dimension/measure names with spaces need backtick quoting |
| JOIN at query time fails | Joins must be in the YAML definition, not in the SELECT query |
| `MEASURE()` required | All measure references must be wrapped: `MEASURE(\`name\`)` |
| DBR version error | Requires Runtime 17.2+ for YAML v1.1, or 16.4+ for v0.1 |
| Materialization not working | Requires serverless compute enabled; currently experimental |

## External References

### Official Documentation
- [Metric Views SQL Creation](https://docs.databricks.com/aws/en/metric-views/create/sql)
- [Metric Views YAML Syntax Reference](https://docs.databricks.com/aws/en/metric-views/data-modeling/syntax)
- [Metric Views Joins](https://docs.databricks.com/aws/en/metric-views/data-modeling/joins)
- [Metric Views Semantic Metadata](https://docs.databricks.com/aws/en/metric-views/data-modeling/semantic-metadata)
- [Composability in Metric Views](https://docs.databricks.com/aws/en/metric-views/data-modeling/composability)
- [Window Measures (Experimental)](https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures)
- [Materialization for Metric Views](https://docs.databricks.com/aws/en/metric-views/materialization)

### Related Skills
- `databricks-table-valued-functions` — TVF patterns for Genie
- `genie-space-patterns` — Genie Space setup
- `databricks-aibi-dashboards` — AI/BI dashboard patterns

## Version History

- **v5.0** (Feb 2026) — Expanded transitive joins with inline fixes; exhaustive format type table (6 types); composability (MEASURE function) patterns; FILTER clause; USING join clause; filter top-level field; window measures clarification (Experimental v0.1); materialization expansion; progressive disclosure restructure (Notes to Carry Forward + Next Step); 7 upstream_sources from official docs; new composability-patterns.md reference
- **v4.0** (Feb 2026) — Merged prompt content: Quick Start, implementation workflow, requirements template, creation script, validation queries, worked examples, common mistakes with paired examples
- **v3.0** (Dec 19, 2025) — Standardized structured comment format
- **v2.0** (Dec 16, 2025) — Genie optimization patterns from production post-mortem
- **v1.0** (Oct 2025) — Initial rule based on metric view deployment learnings

## Metric Views Notes to Carry Forward

After completing metric view creation, carry these notes to the next worker:
- **Metric View names and paths:** List of all created MVs with YAML file paths
- **Grain per view:** Which fact table sources each MV
- **Measure counts:** Number of dimensions and measures per MV
- **Validation status:** Which MVs passed schema validation, any unresolved issues
- **Composability notes:** Any composed measures using MEASURE() that downstream workers should know about

## Next Step

After metric views are deployed and validated, proceed to:
**`semantic-layer/02-databricks-table-valued-functions/SKILL.md`** — Create TVFs for Genie Spaces using the Gold tables referenced by your metric views.

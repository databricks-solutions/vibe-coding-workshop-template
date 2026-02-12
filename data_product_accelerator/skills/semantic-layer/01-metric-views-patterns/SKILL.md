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
  upstream_sources: []  # Internal metric view patterns
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

## Quick Start (2 hours)

**What You'll Create:**
1. `metric_views/{view_name}.yaml` — Semantic definitions (dimensions, measures, joins, formats)
2. `create_metric_views.py` — Script reads YAML, creates views with `WITH METRICS LANGUAGE YAML`
3. `metric_views_job.yml` — Asset Bundle job for deployment

**Deliverables Checklist:**
- [ ] Metric view YAML files (one per view) with dimensions, measures, synonyms, formats
- [ ] Creation script (`create_metric_views.py`) with error handling
- [ ] Asset Bundle job (`metric_views_job.yml`) for deployment
- [ ] Validation queries passing (METRIC_VIEW type verified)

**Fast Track:**
```bash
# 1. Create metric view YAML files
# 2. Deploy and run
databricks bundle deploy -t dev
databricks bundle run metric_views_job -t dev

# 3. Query with natural language via Genie
# "Show total revenue by store last 30 days"
```

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
| `window_measures` | `Unrecognized field "window_measures"` | ❌ Remove entirely — calculate in SQL/Python |
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

**Metric Views v1.1 DO NOT support transitive/chained joins.**

**❌ WRONG:** Transitive join (not supported)
```yaml
joins:
  - name: dim_property
    source: catalog.schema.dim_property
    'on': source.property_id = dim_property.property_id
  - name: dim_destination
    source: catalog.schema.dim_destination
    'on': dim_property.destination_id = dim_destination.destination_id  # ❌ ERROR!
```

**✅ CORRECT:** Use snowflake schema (nested joins) or denormalize fact table

See `references/advanced-patterns.md` for snowflake schema patterns and transitive join solutions.

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
  - [ ] 3-5 synonyms each
- [ ] Define measures with correct aggregation (SUM, AVG, COUNT)
  - [ ] Proper formatting (currency, number, percentage)
  - [ ] Comprehensive comments for Genie
  - [ ] 3-5 synonyms each

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

### Column References

- **Main table columns:** Use `source.` prefix in all `expr` fields
- **Joined table columns:** Use join `name` as prefix (e.g., `dim_store.column_name`)
- **Never reference table names directly:** Use `source.` or `{join_name}.`

### Join Requirements

- Each join **MUST have** `name`, `source`, and `'on'` fields (quoted!)
- ON clause uses `source.` for main table, join name for joined table
- Each join must be direct: `source.fk = dim.pk` (NOT `dim1.fk = dim2.pk`)
- SCD2 joins must include `AND {dim_table}.is_current = true`

## Core Patterns

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

### Dimension Patterns

**Geographic:**
```yaml
- name: store_number
  expr: source.store_number
  comment: Store identifier for location-based analysis
  display_name: Store Number
  synonyms: [store id, location number, store code]
```

**Time (from dim_date):**
```yaml
- name: month_name
  expr: dim_date.month_name
  comment: Month name for seasonal analysis
  display_name: Month
  synonyms: [month]
```

### Measure Patterns

**Revenue:**
```yaml
- name: total_revenue
  expr: SUM(source.net_revenue)
  comment: Total net revenue after discounts and returns
  display_name: Total Revenue
  format:
    type: currency
    currency_code: USD
    decimal_places:
      type: exact
      places: 2
    abbreviation: compact
  synonyms: [revenue, sales, net revenue]
```

**Count:**
```yaml
- name: booking_count
  expr: COUNT(source.booking_id)  # ✅ Use primary key, not SUM(count_column)
  comment: Total number of transactions
  display_name: Booking Count
  format:
    type: number
    decimal_places:
      type: all
  synonyms: [bookings, transactions]
```

See `references/advanced-patterns.md` for complete examples including a full worked retail example.

## Common Mistakes to Avoid

### ❌ Mistake 1: Wrong Syntax (TBLPROPERTIES)
```python
# ❌ WRONG: Creates regular VIEW, not METRIC_VIEW
create_sql = f"""CREATE VIEW {view_name} COMMENT '{comment}'
TBLPROPERTIES ('metric_view_spec' = '{yaml}')
AS SELECT 1 as __metric_view_placeholder__"""

# ✅ CORRECT: Creates METRIC_VIEW
create_sql = f"""CREATE VIEW {view_name}
WITH METRICS LANGUAGE YAML COMMENT '{comment}'
AS $$ {yaml_str} $$"""
```

### ❌ Mistake 2: Using Unsupported Fields
```yaml
# ❌ WRONG: v1.1 doesn't support time_dimension or window_measures
time_dimension:
  name: transaction_date
window_measures:
  - name: revenue_last_30_days
    base_measure: total_revenue

# ✅ CORRECT: Use regular dimension instead
dimensions:
  - name: transaction_date
    expr: source.transaction_date
    comment: Transaction date for time-based analysis
```

### ❌ Mistake 3: Wrong Column References
```yaml
# ❌ WRONG: Using table name instead of 'source.' / missing join prefix
measures:
  - name: total_revenue
    expr: SUM(fact_sales_daily.net_revenue)  # ❌ Use source.net_revenue
dimensions:
  - name: store_name
    expr: store_name  # ❌ Use dim_store.store_name
```

### ❌ Mistake 4: Including `name` in YAML Content
```yaml
# ❌ WRONG: 'name' inside AS $$...$$ causes "Unrecognized field" error
name: sales_performance_metrics  # ❌ Remove! Name is in CREATE VIEW only
version: "1.1"
```

### ❌ Mistake 5: Transitive Joins / Wrong Source Table
```yaml
# ❌ WRONG: Chained join (dim1 → dim2) — not supported
'on': dim_property.destination_id = dim_destination.destination_id

# ❌ WRONG: Revenue from dimension table (under-reports by 4x)
source: catalog.schema.dim_property  # Use fact table instead!
```

## Python Script Error Handling

**⚠️ CRITICAL: Jobs Must Fail if Metric Views Don't Create**

Key patterns (see `scripts/create_metric_views.py` for the full working script):

1. **Strip `name` before dumping YAML** — `metric_view.pop('name', None)` before `yaml.dump()`
2. **Drop existing VIEW/TABLE** before CREATE to avoid conflicts
3. **Track failed views** and raise `RuntimeError` at the end (no silent success)
4. **Verify METRIC_VIEW type** via `DESCRIBE EXTENDED` after creation
5. **Support dual mode** — per-file (preferred) or multi-file YAML loading

**Scripts:**
- **`scripts/create_metric_views.py`** — Complete creation script with YAML loading, parameter substitution (`${catalog}`, `${gold_schema}`), dual-mode support, METRIC_VIEW verification, error handling
- **`scripts/validate_metric_view.py`** — Pre-deployment column reference validation against Gold layer YAML schemas

## Time Estimates

| Metric Views | Design | YAML Creation | Deploy & Test | Total |
|---|---|---|---|---|
| 1 view | 20 min | 30 min | 20 min | ~1 hour |
| 2-3 views | 30 min | 1 hour | 30 min | ~2 hours |
| 5+ views | 1 hour | 2 hours | 30 min | ~3.5 hours |

## Next Steps

After metric views are deployed and validated:

1. **Test with Genie** — Ask natural language questions to verify synonyms and measures work
2. **Create TVFs** — Use `databricks-table-valued-functions` skill for parameterized queries
3. **Setup Genie Space** — Use `genie-space-patterns` skill to configure Genie with metric views, TVFs, and tables
4. **Create Dashboards** — Use `databricks-aibi-dashboards` skill for Lakeview AI/BI dashboards

## Reference Files

- **`references/yaml-reference.md`** — Complete YAML structure, fields, syntax, format options
- **`references/validation-checklist.md`** — Detailed pre-creation validation steps
- **`references/advanced-patterns.md`** — Dimension/measure patterns, joins, snowflake schema, complete worked example
- **`references/requirements-template.md`** — Design template for dimensions, measures, joins, business questions
- **`references/implementation-workflow.md`** — Detailed step-by-step creation workflow
- **`references/validation-queries.md`** — SQL queries for deployment verification

## Scripts

- **`scripts/validate_metric_view.py`** — Pre-deployment validation of column references against Gold layer YAML schemas
- **`scripts/create_metric_views.py`** — Metric view creation script with YAML loading, parameter substitution, and error handling

**Usage:**
```bash
# Validate before deployment
python scripts/validate_metric_view.py \
  --yaml-file src/semantic/metric_views/revenue_analytics_metrics.yaml \
  --gold-yaml-dir gold_layer_design/yaml

# Deploy (via Asset Bundle job)
databricks bundle run metric_views_job -t dev
```

## Assets

- **`assets/templates/metric-view-template.yaml`** — Starter template for new metric views
- **`assets/templates/metric-views-job-template.yml`** — Asset Bundle job template for deployment

## External References

### Official Documentation
- [Metric Views SQL Creation](https://docs.databricks.com/aws/en/metric-views/create/sql)
- [Metric Views YAML Reference](https://docs.databricks.com/aws/en/metric-views/yaml-ref)
- [Metric Views Semantic Metadata](https://docs.databricks.com/aws/en/metric-views/semantic-metadata)
- [Metric Views Joins](https://docs.databricks.com/aws/en/metric-views/joins)
- [Metric Views Measure Formats](https://docs.databricks.com/aws/en/metric-views/measure-formats)

### Related Skills
- `databricks-table-valued-functions` — TVF patterns for Genie
- `genie-space-patterns` — Genie Space setup
- `databricks-aibi-dashboards` — AI/BI dashboard patterns

## Version History

- **v4.0** (Feb 2026) — Merged prompt content: Quick Start, implementation workflow, requirements template, creation script, validation queries, worked examples, common mistakes with paired examples
- **v3.0** (Dec 19, 2025) — Standardized structured comment format
- **v2.0** (Dec 16, 2025) — Genie optimization patterns from production post-mortem
- **v1.0** (Oct 2025) — Initial rule based on metric view deployment learnings

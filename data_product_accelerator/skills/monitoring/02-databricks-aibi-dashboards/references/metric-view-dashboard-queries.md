# Metric View Dashboard Queries Using MEASURE()

When Metric Views exist in the semantic layer, use `MEASURE()` for aggregate datasets. Use direct Gold SQL only for detail tables and filter value datasets.

> **Placeholders below** (`sales_performance_metrics`, `transaction_date`, `total_revenue`, `dimension_name`, etc.) are generic. Replace with your actual Metric View names, measure names, and dimensions from the semantic layer manifest (`plans/manifests/semantic-layer-manifest.yaml`).

## Dataset Strategy

| Dataset Type | Query Pattern | Example |
|---|---|---|
| KPI totals | `MEASURE()` against Metric View | `SELECT MEASURE(\`total_revenue\`) AS total_revenue FROM mv` |
| Trend by date | `MEASURE()` with dimension | `SELECT transaction_date, MEASURE(\`total_revenue\`) AS revenue FROM mv` |
| Category breakdown | `MEASURE()` with dimension | `SELECT dimension_name, MEASURE(\`total_revenue\`) AS revenue FROM mv` |
| Detail / drill-down | Direct Gold SQL with JOINs | `SELECT cols FROM fact JOIN dim ... LIMIT 200` |
| Filter values | Direct Gold SQL | `SELECT 'All' UNION ALL SELECT DISTINCT col FROM dim` |

## SQL Templates

### KPI Totals (no dimensions — global aggregation)

```sql
SELECT
  MEASURE(`total_revenue`) AS total_revenue,
  MEASURE(`transaction_count`) AS transaction_count,
  MEASURE(`avg_transaction_value`) AS avg_transaction_value
FROM ${catalog}.${gold_schema}.sales_performance_metrics
WHERE transaction_date BETWEEN :start_date AND :end_date
```

### Trend with Temporal Dimension

```sql
SELECT
  transaction_date,
  MEASURE(`total_revenue`) AS revenue,
  MEASURE(`transaction_count`) AS transaction_count
FROM ${catalog}.${gold_schema}.sales_performance_metrics
WHERE transaction_date BETWEEN :start_date AND :end_date
```

### Categorical Breakdown

```sql
SELECT
  dimension_name,
  MEASURE(`total_revenue`) AS revenue,
  MEASURE(`transaction_count`) AS transaction_count
FROM ${catalog}.${gold_schema}.sales_performance_metrics
WHERE transaction_date BETWEEN :start_date AND :end_date
```

## MEASURE() Syntax Rules

- **No explicit `GROUP BY`** — aggregation is implicit from dimensions in the SELECT clause
- **Backtick-quote measure names** — must match the Metric View definition exactly (e.g., `` MEASURE(`total_revenue`) ``)
- **Dimensions appear as bare column names** — no `MEASURE()` wrapper on dimensions
- **WHERE clause filters on dimension columns directly** — same as regular SQL
- **Use `${catalog}.${gold_schema}` variable substitution** — same pattern as Gold tables
- **Widget `fieldName` must match the `AS alias` exactly** — e.g., `AS revenue` means widget uses `fieldName: "revenue"`
- **Reference dimensions by metric view `name`** — not by source table alias (e.g., `WHERE is_same_store = 1`, not `WHERE dim_location.is_same_store = 1`)

## Mixed-Strategy Example

A typical dashboard combines MEASURE() datasets for aggregates with direct Gold SQL for details and filters:

```
Datasets using MEASURE():
  ds_kpi_totals            → KPI counters (total revenue, transaction count, avg value)
  ds_revenue_trend         → Line chart (revenue over time)
  ds_dimension_breakdown   → Bar chart (revenue by dimension)

Datasets using direct Gold SQL:
  ds_transaction_details   → Data table (row-level records with JOINs)
  ds_dimension_filter      → Filter widget (SELECT DISTINCT dimension_name)
  ds_category_filter       → Filter widget (SELECT DISTINCT category)
```

## Anti-Pattern: Substituting Direct SQL for MEASURE()

When the user requests `MEASURE()` queries, **never substitute direct Gold table SQL** even if:
- Metric Views may not be deployed yet
- Direct SQL seems "safer" or "more practical"
- You are uncertain about MEASURE() syntax

Instead:
1. Use the MEASURE() patterns above
2. Note any Metric View deployment dependencies in comments
3. If genuinely uncertain, **ask the user** — do not resolve the tradeoff silently

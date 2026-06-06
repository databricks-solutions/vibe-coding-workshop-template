# Querying Metric Views

Metric views have strict query syntax that differs from standard SQL views. Read this before writing any SQL (or Genie-generated SQL you intend to validate) against a metric view.

## Core Rules

1. **Wrap every measure in `MEASURE()`** — you cannot reference a measure column directly.
2. **Use `GROUP BY ALL`** — metric views require explicit grouping; `GROUP BY ALL` groups by every non-aggregated column in the `SELECT`.
3. **No `SELECT *`** — list each dimension explicitly and wrap each measure with `MEASURE()`.
4. **Reference dimensions directly** — no wrapping needed for dimension columns.
5. **`agg()` is an alias for `MEASURE()`** (DBR 18.1+).
6. **Backtick-escape names** with spaces, hyphens, or special characters wherever referenced.

## Basic Query Pattern

```sql
SELECT
  `dimension_name`,
  MEASURE(`measure_name`) AS measure_alias
FROM ${catalog}.${gold_schema}.my_metric_view
GROUP BY ALL
ORDER BY ALL;
```

## Filtering Dimensions (WHERE)

```sql
SELECT
  o_orderpriority,
  MEASURE(`Total Revenue`)
FROM ${catalog}.${gold_schema}.orders_metrics
WHERE `Order Status` = 'Fulfilled'
GROUP BY o_orderpriority;
```

## Filtering by Measure Values (HAVING)

Use `HAVING` to filter on a computed measure. Reference the **alias**, not the `MEASURE()` expression:

```sql
SELECT
  `cloud`,
  MEASURE(`revenue`) AS `revenue`
FROM ${catalog}.${gold_schema}.metrics
GROUP BY ALL
HAVING `revenue` > 100000;
```

## Top-K Queries

Use `ROW_NUMBER()` with `MEASURE()` in the `ORDER BY`, then filter on the rank in an outer query:

```sql
WITH ranked AS (
  SELECT
    `employee`,
    MEASURE(`sales`) AS `total_sales`,
    ROW_NUMBER() OVER (ORDER BY MEASURE(`sales`) DESC) AS `rank`
  FROM ${catalog}.${gold_schema}.metrics
  GROUP BY ALL
)
SELECT `employee`, `total_sales`
FROM ranked
WHERE `rank` <= 3;
```

## Casting Measure Results

You can cast the result of `MEASURE()` for formatting:

```sql
SELECT
  EXTRACT(month FROM month) AS month,
  MEASURE(`total_revenue_per_customer`)::bigint AS total_revenue_per_customer
FROM ${catalog}.${gold_schema}.region_sales_metrics
WHERE EXTRACT(year FROM month) = 1995
GROUP BY ALL
ORDER BY ALL;
```

## Querying Window Measures

Window measures are queried exactly like regular measures:

```sql
SELECT
  state,
  DATE_TRUNC('month', date),
  MEASURE(`t7d_customers`) AS m
FROM ${catalog}.${gold_schema}.my_metric_view
WHERE date >= DATE'2024-06-01'
GROUP BY ALL;
```

## Common Mistakes

| Mistake | Why it fails | Fix |
|---------|--------------|-----|
| `SELECT *` | Measures need `MEASURE()` wrapping | List columns explicitly |
| `SELECT measure_name` (unwrapped) | Raw measure reference is invalid | `MEASURE(measure_name)` |
| Missing `GROUP BY` | Metric views require grouping | Add `GROUP BY ALL` |
| `MEASURE(dim)` on a dimension | Dimensions are not aggregates | Reference dimensions directly |
| Nested `MEASURE()` | Cannot nest aggregate calls | Compose in YAML with `MEASURE()` instead |
| `HAVING MEASURE(x) > n` referencing the expression | HAVING expects the alias | `HAVING x_alias > n` |
| JOIN at query time | Joins live in the YAML definition | Add the join to the metric view YAML |

## Verifying Materialization Usage

To check whether a query was rewritten to read from a materialization:

```sql
EXPLAIN EXTENDED
SELECT `dim`, MEASURE(`metric`) AS m
FROM ${catalog}.${gold_schema}.my_metric_view
GROUP BY ALL;
```

Look for `__materialization_mat___metric_view` in the plan output. If present, the query used the materialized view; otherwise it computed from source.

See also: [composability-patterns.md](composability-patterns.md), [level-of-detail.md](level-of-detail.md), and `references/validation-queries.md` for deployment verification queries.

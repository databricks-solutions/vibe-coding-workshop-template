# Asset Routing: TVF vs Metric View Decision Matrix

## Decision Matrix

| Query Type | Preferred Asset | Reason |
|------------|-----------------|--------|
| **Aggregations** (total, average) | Metric View | Pre-optimized for MEASURE() |
| **Lists** (show me, which, top N) | TVF | Parameterized, returns rows |
| **Time-series with params** | TVF | Date range parameters |
| **Dashboard KPIs** | Metric View | Single-value aggregations |
| **Detail drilldowns** | TVF | Full row data |

## When to Use TVFs

### Parameterized Queries

TVFs excel when queries need parameters:

```sql
-- ✅ GOOD: TVF with date range parameters
SELECT * FROM TABLE(get_daily_cost_summary('2025-01-01', '2025-01-31'))

-- ❌ BAD: Metric View can't handle parameters easily
SELECT MEASURE(total_cost) FROM mv_cost_analytics
WHERE usage_date BETWEEN '2025-01-01' AND '2025-01-31'  -- Requires WHERE clause
```

### Complex Joins

TVFs can encapsulate complex join logic:

```sql
CREATE OR REPLACE FUNCTION get_top_cost_contributors(
    limit_count INT
)
RETURNS TABLE (
    workspace_name STRING,
    total_cost DECIMAL(18,2),
    dbus_consumed DOUBLE
)
COMMENT 'Returns top cost contributors with workspace names. Handles complex joins between fact_usage and dim_workspace.'
AS $$
    SELECT 
        w.workspace_name,
        SUM(f.dbus_used * f.sku_price) AS total_cost,
        SUM(f.dbus_used) AS dbus_consumed
    FROM fact_usage f
    JOIN dim_workspace w ON f.workspace_id = w.workspace_id
    GROUP BY w.workspace_name
    ORDER BY total_cost DESC
    LIMIT limit_count
$$;
```

### List Queries

TVFs return full row data, perfect for "show me" queries:

```sql
-- ✅ GOOD: TVF returns full rows
SELECT * FROM TABLE(get_failed_jobs(7))  -- Returns: job_name, failure_reason, timestamp, etc.

-- ❌ BAD: Metric View only returns aggregated measures
SELECT MEASURE(failure_count) FROM mv_job_metrics  -- Only count, no details
```

## When to Use Metric Views

### Simple Aggregations

Metric Views excel at standard KPIs:

```sql
-- ✅ GOOD: Metric View for simple aggregation
SELECT MEASURE(total_cost) FROM mv_cost_analytics

-- ❌ BAD: TVF overkill for simple aggregation
SELECT total_cost FROM TABLE(get_total_cost())  -- Unnecessary function call
```

### Dashboard KPIs

Metric Views are optimized for single-value queries:

```sql
-- ✅ GOOD: Metric View for dashboard KPI
SELECT 
    MEASURE(total_cost) AS total_cost,
    MEASURE(dbus_consumed) AS dbus_consumed
FROM mv_cost_analytics

-- ❌ BAD: TVF requires parameters even for simple queries
SELECT * FROM TABLE(get_cost_summary(NULL, NULL))  -- Awkward parameter handling
```

### Standard KPIs

Metric Views provide consistent KPI definitions:

```yaml
# Metric View defines standard KPIs
measures:
  - name: total_cost
    expr: SUM(dbus_used * sku_price)
    description: "Total cost in USD"
  - name: dbus_consumed
    expr: SUM(dbus_used)
    description: "Total DBUs consumed"
```

## Key Learning: TVF-First Design Improves Repeatability

**Production Results:**
- Quality domain: 100% repeatability (TVF-first routing)
- Reliability domain: 80% repeatability (mixed routing)
- Security domain: 67% repeatability (MV-heavy routing)

**Why TVFs Improve Repeatability:**
1. **Function signature constrains output** - Less room for LLM variation
2. **Parameterized queries** - Consistent parameter handling
3. **Encapsulated logic** - LLM doesn't need to construct complex SQL

**Why MVs Have Higher Variance:**
1. **LLM makes column choices** - Different GROUP BY columns across runs
2. **MEASURE() syntax variations** - LLM constructs different measure expressions
3. **Dimension selection** - LLM picks different dimensions for grouping

## Standard Instruction Pattern

Include explicit routing rules in Genie Instructions:

```
=== ASSET ROUTING RULES ===

1. **Aggregations** (total, overall, average)
   → USE: Metric View with MEASURE()
   → Example: SELECT MEASURE(total_cost) FROM mv_cost_analytics

2. **Lists** (show me, which, top N, list)
   → USE: TVF with TABLE() wrapper
   → Example: SELECT * FROM TABLE(get_failed_jobs(7))

3. **Parameterized queries** (date range, filters)
   → USE: TVF (supports parameters)
   → Example: SELECT * FROM TABLE(get_daily_cost_summary('2025-01-01', '2025-01-31'))
```

## Domain Examples

### Cost Domain

- **Total cost**: Metric View (`mv_cost_analytics`)
- **Top contributors**: TVF (`get_top_cost_contributors`)
- **Daily trends**: TVF (`get_daily_cost_summary`)

### Reliability Domain

- **Failure rate**: Metric View (`mv_job_metrics`)
- **Failed jobs list**: TVF (`get_failed_jobs`)
- **Job history**: TVF (`get_job_history`)

### Quality Domain (100% Repeatability)

- **Most queries**: TVF-first routing
- **Standard KPIs**: Metric Views for simple aggregations
- **Complex queries**: TVFs with explicit parameters

## Best Practices

1. **Start with TVFs** for parameterized queries
2. **Use Metric Views** for simple aggregations
3. **Document routing rules** in Genie Instructions
4. **Test repeatability** after routing changes
5. **Prefer TVFs** when repeatability is critical

# Deployment Guide

## Monitor Output Tables

After a monitor completes its first refresh, two output tables are created:

| Table | Contents | Custom Metrics |
|-------|----------|---------------|
| `{table}_profile_metrics` | Column stats + AGGREGATE + DERIVED metrics | ✅ New columns |
| `{table}_drift_metrics` | Drift analysis + DRIFT metrics | ✅ New columns |

**Location:** Both tables are created in the output schema specified by `output_schema_id`.

## Query Patterns

### Pattern 1: Profile Metrics (Basic Stats)

```sql
-- Query null rates and basic column statistics
SELECT
  window,
  column_name,
  null_count,
  row_count,
  ROUND(null_count / NULLIF(row_count, 0) * 100, 2) AS null_pct,
  avg,
  min,
  max
FROM {catalog}.{monitoring_schema}.{table}_profile_metrics
WHERE window IS NOT NULL
ORDER BY window.start DESC, column_name;
```

### Pattern 2: Custom Aggregate Metrics

```sql
-- Query custom business metrics (appear as columns)
SELECT
  window,
  total_revenue,       -- custom AGGREGATE metric
  total_transactions,  -- custom AGGREGATE metric
  avg_basket_size      -- custom DERIVED metric
FROM {catalog}.{monitoring_schema}.{table}_profile_metrics
WHERE column_name = ":table"  -- table-level metrics use ":table" as column
ORDER BY window.start DESC;
```

### Pattern 3: Drift Metrics

```sql
-- Query drift analysis
SELECT
  window,
  column_name,
  revenue_drift_pct,           -- custom DRIFT metric
  wasserstein_distance,        -- built-in drift statistic
  ks_test.statistic AS ks_stat
FROM {catalog}.{monitoring_schema}.{table}_drift_metrics
WHERE window IS NOT NULL
ORDER BY window.start DESC;
```

### Pattern 4: Ad-Hoc Ratio Calculation

Alternative to DERIVED metrics — calculate ratios directly from profile output:

```sql
-- Calculate ratios from profile metrics (no DERIVED metric needed)
WITH metrics AS (
  SELECT
    window,
    MAX(CASE WHEN column_name = ':table' THEN total_revenue END) AS revenue,
    MAX(CASE WHEN column_name = ':table' THEN total_transactions END) AS txns
  FROM {catalog}.{monitoring_schema}.{table}_profile_metrics
  GROUP BY window
)
SELECT
  window,
  revenue,
  txns,
  ROUND(revenue / NULLIF(txns, 0), 2) AS avg_revenue_per_txn
FROM metrics
ORDER BY window.start DESC;
```

### Pattern 5: Null Rate Monitoring

```sql
-- Monitor null rates for data quality
SELECT
  window,
  column_name,
  null_count,
  row_count,
  ROUND(null_count * 100.0 / NULLIF(row_count, 0), 2) AS null_pct
FROM {catalog}.{monitoring_schema}.{table}_profile_metrics
WHERE null_count > 0
  AND column_name != ':table'  -- exclude table-level row
ORDER BY null_pct DESC;
```

## Genie Space Documentation

When adding monitored Gold tables to a Genie Space, include monitoring context in table/column comments.

### Table Comment Template

```sql
COMMENT ON TABLE {catalog}.{schema}.{table} IS
'Gold layer table with Lakehouse Monitoring enabled.
Monitoring output tables:
- Profile metrics: {catalog}.{monitoring_schema}.{table}_profile_metrics
- Drift metrics: {catalog}.{monitoring_schema}.{table}_drift_metrics
Custom metrics: total_revenue, total_transactions, avg_basket_size, revenue_drift_pct.
Monitoring mode: TimeSeries (daily granularity on transaction_date).
Slicing: store_number.';
```

### Column Comment for Monitored Metrics

```sql
COMMENT ON COLUMN {catalog}.{schema}.{table}.net_revenue IS
'Net revenue per transaction in USD. Monitored metric: total_revenue = SUM(net_revenue). Drift tracked: revenue_drift_pct (period-over-period % change).';
```

## Asset Bundle Job Configuration

### Setup Job

```yaml
resources:
  jobs:
    monitoring_setup:
      name: "${bundle.target}-monitoring-setup"
      tasks:
        - task_key: setup_monitors
          notebook_task:
            notebook_path: src/monitoring/setup_monitors.py
            base_parameters:
              catalog: "${var.catalog}"
              schema: "${var.gold_schema}"
              monitoring_schema: "${var.gold_schema}_monitoring"
          environment_key: default

        - task_key: wait_for_initialization
          depends_on:
            - task_key: setup_monitors
          notebook_task:
            notebook_path: src/monitoring/wait_for_initialization.py
            base_parameters:
              catalog: "${var.catalog}"
              schema: "${var.gold_schema}"
              monitoring_schema: "${var.gold_schema}_monitoring"
          environment_key: default

      environments:
        - environment_key: default
          spec:
            client: "1"
```

### Scheduled Refresh Job

```yaml
resources:
  jobs:
    monitoring_refresh:
      name: "${bundle.target}-monitoring-refresh"
      schedule:
        quartz_cron_expression: "0 0 6 * * ?"  # Daily at 6 AM
        timezone_id: "America/New_York"
      tasks:
        - task_key: refresh_monitors
          notebook_task:
            notebook_path: src/monitoring/refresh_monitors.py
            base_parameters:
              catalog: "${var.catalog}"
              schema: "${var.gold_schema}"
          environment_key: default

      environments:
        - environment_key: default
          spec:
            client: "1"
```

## Production Deployment Checklist

- [ ] Monitoring schema exists (`CREATE SCHEMA IF NOT EXISTS`)
- [ ] All Gold tables have data (non-empty)
- [ ] Custom metrics use correct syntax (see `references/custom-metrics.md`)
- [ ] `output_data_type` uses `T.StructField().json()` format
- [ ] Table UUIDs resolve correctly
- [ ] Monitoring schema UUID resolves correctly
- [ ] Wait for initialization completes (15-20 min)
- [ ] Profile metrics table has data
- [ ] Drift metrics table has data (if drift metrics defined)
- [ ] Genie Space table comments include monitoring context
- [ ] Alert queries work (see `references/alert-patterns.md` or `sql-alerting-patterns` skill)

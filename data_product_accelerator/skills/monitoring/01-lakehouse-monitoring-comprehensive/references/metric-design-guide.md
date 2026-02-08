# Metric Design Guide

## Fill-in-the-Blank Requirements Template

Use this template to plan monitoring for each Gold table before writing code.

```
TABLE: _____________________ (e.g., fact_sales_daily)
MONITOR MODE: [ ] TimeSeries  [ ] Snapshot
TIMESTAMP COLUMN: ______________ (required for TimeSeries)
GRANULARITY: [ ] 1 day  [ ] 1 hour  [ ] 1 week  [ ] 1 month
SLICING COLUMNS: _____________________ (low-cardinality only)
PRIORITY: [ ] P1-Critical  [ ] P2-Important  [ ] P3-Nice-to-have

CUSTOM METRICS:
  AGGREGATE:
    1. Name: ____________  Definition: ____________  Type: Double/Long
    2. Name: ____________  Definition: ____________  Type: Double/Long
    3. Name: ____________  Definition: ____________  Type: Double/Long

  DERIVED (from above aggregates):
    1. Name: ____________  Definition: ____________
    2. Name: ____________  Definition: ____________

  DRIFT (period-over-period):
    1. Name: ____________  References: ____________
```

For a ready-to-fill markdown version, see `assets/templates/monitoring-requirements-template.md`.

## Monitor Priority Definitions

| Priority | Criteria | Max Init Time | Alert Threshold |
|----------|----------|--------------|----------------|
| **P1-Critical** | Revenue tables, customer-facing | 30 min wait | Immediate alert |
| **P2-Important** | Operational tables, internal KPIs | 45 min wait | Within 1 hour |
| **P3-Nice-to-have** | Reference tables, low-change | 60 min wait | Daily digest |

### P1 Tables (Monitor First)
- Fact tables driving revenue dashboards
- Tables consumed by Genie Spaces
- Tables feeding ML inference pipelines

### P2 Tables (Monitor Next)
- Dimension tables (especially SCD Type 2)
- Aggregated fact tables
- Operational reporting tables

### P3 Tables (Monitor Later)
- Reference/lookup tables
- Historical archive tables
- Low-query-volume tables

## Custom Metric Templates by Category

### Revenue Metrics

```python
# Total revenue
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="total_revenue",
    input_columns=[":table"],
    definition="SUM(net_revenue)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)

# Average order value
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="avg_order_value",
    input_columns=[":table"],
    definition="AVG(order_total)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)

# Revenue per transaction (DERIVED)
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
    name="revenue_per_transaction",
    input_columns=[":table"],
    definition="total_revenue / NULLIF(transaction_count, 0)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

### Volume Metrics

```python
# Transaction count
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="transaction_count",
    input_columns=[":table"],
    definition="COUNT(*)",
    output_data_type=T.StructField("output", T.LongType()).json()
)

# Distinct customers
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="unique_customers",
    input_columns=[":table"],
    definition="COUNT(DISTINCT customer_id)",
    output_data_type=T.StructField("output", T.LongType()).json()
)
```

### Quality Metrics

```python
# Null rate for critical column
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="revenue_null_rate",
    input_columns=[":table"],
    definition="SUM(CASE WHEN net_revenue IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)

# Duplicate rate
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="duplicate_rate",
    input_columns=[":table"],
    definition="(COUNT(*) - COUNT(DISTINCT transaction_id)) * 100.0 / NULLIF(COUNT(*), 0)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

### Dimension Health Metrics (Snapshot)

```python
# Total active records
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="total_active_records",
    input_columns=[":table"],
    definition="SUM(CASE WHEN is_current = true THEN 1 ELSE 0 END)",
    output_data_type=T.StructField("output", T.LongType()).json()
)

# SCD2 history depth
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="avg_versions_per_entity",
    input_columns=[":table"],
    definition="COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT entity_id), 0)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

### Drift Metrics (Period-over-Period)

```python
# Revenue drift (absolute)
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DRIFT,
    name="revenue_drift",
    input_columns=[":table"],
    definition="{{current_df}}.total_revenue - {{base_df}}.total_revenue",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)

# Revenue drift percentage
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DRIFT,
    name="revenue_drift_pct",
    input_columns=[":table"],
    definition="(({{current_df}}.total_revenue - {{base_df}}.total_revenue) / NULLIF({{base_df}}.total_revenue, 0)) * 100",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)

# Volume drift
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DRIFT,
    name="volume_drift_pct",
    input_columns=[":table"],
    definition="(({{current_df}}.transaction_count - {{base_df}}.transaction_count) / NULLIF({{base_df}}.transaction_count, 0)) * 100",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

## Alert Strategy Table

| Metric Type | Alert When | Severity | Action |
|-------------|-----------|----------|--------|
| Revenue total | Drops >20% vs previous period | P1-Critical | Page on-call |
| Transaction count | Drops >30% | P1-Critical | Page on-call |
| Null rate | Exceeds 5% | P2-Important | Email data team |
| Duplicate rate | Exceeds 1% | P2-Important | Email data team |
| Dimension count | Changes >10% | P3-Nice-to-have | Daily digest |
| Revenue drift % | Exceeds +/-25% | P1-Critical | Page on-call |

## Metric Design Best Practices

1. **Start small:** 3-5 metrics per table initially
2. **Use DERIVED for ratios:** Avoid recomputing from raw data
3. **Track nulls explicitly:** Don't rely only on built-in null stats
4. **Name consistently:** Use `{domain}_{measure}` pattern (e.g., `revenue_total`, `revenue_drift_pct`)
5. **Document intent:** Add Python comments explaining business meaning
6. **Avoid high-cardinality slicing:** >100 unique values causes performance issues
7. **Test incrementally:** Add 1-2 metrics, validate, then add more

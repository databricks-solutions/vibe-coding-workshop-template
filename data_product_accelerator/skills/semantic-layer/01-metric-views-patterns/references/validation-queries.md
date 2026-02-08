# Metric View Validation Queries

SQL queries for verifying metric view deployment and functionality.

---

## List All Metric Views

```sql
SHOW VIEWS IN {catalog}.{schema};
```

## Verify Metric View Type

```sql
DESCRIBE EXTENDED {catalog}.{schema}.{view_name};
-- Expected: Type column shows METRIC_VIEW
-- If it shows VIEW, the creation used wrong syntax (TBLPROPERTIES instead of WITH METRICS)
```

## Basic Data Query

```sql
SELECT * FROM {catalog}.{schema}.{view_name} LIMIT 10;
```

## Test MEASURE() Function

The `MEASURE()` function is specific to metric views and uses **display names** (not column names):

```sql
SELECT
  store_name,
  MEASURE(`Total Revenue`) as revenue,
  MEASURE(`Total Units`) as units,
  MEASURE(`Transaction Count`) as transactions
FROM {catalog}.{schema}.sales_performance_metrics
GROUP BY store_name
ORDER BY revenue DESC
LIMIT 10;
```

**Expected:** Returns aggregated results using the measure definitions from YAML.

## Test Dimension Filtering

```sql
SELECT
  brand,
  MEASURE(`Total Revenue`) as revenue
FROM {catalog}.{schema}.sales_performance_metrics
WHERE state = 'CA'
GROUP BY brand
ORDER BY revenue DESC;
```

**Expected:** Returns results filtered by the dimension value.

## Test Time-Based Queries

```sql
SELECT
  month_name,
  MEASURE(`Total Revenue`) as revenue,
  MEASURE(`Total Units`) as units
FROM {catalog}.{schema}.sales_performance_metrics
WHERE year = 2025
GROUP BY month_name
ORDER BY month_name;
```

---

## Troubleshooting Queries

### Check if View Exists

```sql
SHOW VIEWS IN {catalog}.{schema} LIKE '{view_name}';
```

### Check View Definition

```sql
SHOW CREATE VIEW {catalog}.{schema}.{view_name};
```

### Verify Column Names

```sql
DESCRIBE {catalog}.{schema}.{view_name};
```

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Type: VIEW (not METRIC_VIEW) | Used TBLPROPERTIES syntax | Recreate with `WITH METRICS LANGUAGE YAML` |
| `Unrecognized field "name"` | `name` field inside YAML content | Remove `name` from YAML (it belongs in CREATE VIEW) |
| `Unrecognized field "time_dimension"` | Used v1.0 field | Remove `time_dimension`, use regular dimension |
| `Missing required creator property 'source'` | Used `table` in joins | Replace `table` with `source` in joins |
| Column not found | Column name doesn't exist in source table | Run `DESCRIBE TABLE` and verify column names |
| Empty results | Wrong source table (dimension vs fact) | Revenue → FACT table, counts → DIMENSION table |

---

## Deployment Commands

```bash
# Deploy bundle
databricks bundle deploy -t dev

# Run metric views creation job
databricks bundle run metric_views_job -t dev

# Check job output
databricks bundle run metric_views_job -t dev --output json
```

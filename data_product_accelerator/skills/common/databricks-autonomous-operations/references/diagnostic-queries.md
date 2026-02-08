# Diagnostic SQL Queries

Ready-to-run queries for investigating Databricks operational issues. Replace `${...}` placeholders with actual values.

---

## Table & Schema Existence

```sql
-- Check if table exists
SHOW TABLES IN ${catalog}.${schema} LIKE '${table_pattern}';

-- Check if schema exists
SHOW SCHEMAS IN ${catalog} LIKE '${schema_pattern}';

-- Check full table metadata
DESCRIBE TABLE EXTENDED ${catalog}.${schema}.${table};

-- Check table storage metrics (size)
SELECT table_name, row_count, size_in_bytes / 1e9 AS size_gb
FROM system.information_schema.table_storage_metrics
WHERE table_catalog = '${catalog}'
  AND table_schema = '${schema}'
  AND table_name = '${table}';
```

---

## Permissions

```sql
-- Check grants on a table
SHOW GRANTS ON TABLE ${catalog}.${schema}.${table};

-- Check grants on a schema
SHOW GRANTS ON SCHEMA ${catalog}.${schema};

-- Check current user
SELECT current_user();
```

---

## Lakehouse Monitor Diagnostics

```sql
-- Check if monitors exist for a catalog
SELECT *
FROM system.information_schema.lakehouse_monitors
WHERE table_catalog = '${catalog}';

-- Check monitoring schema exists
SHOW SCHEMAS IN ${catalog} LIKE '%monitoring%';

-- Check monitoring output tables exist
SHOW TABLES IN ${catalog}.${monitoring_schema};

-- Check profile metrics table row count
SELECT COUNT(*) AS row_count
FROM ${catalog}.${monitoring_schema}.${table}_profile_metrics;

-- Check what column_name values exist (debugging NULL custom metrics)
SELECT DISTINCT column_name, COUNT(*) AS rows
FROM ${catalog}.${monitoring_schema}.${table}_profile_metrics
GROUP BY column_name
ORDER BY column_name;

-- Check what slice_key values exist
SELECT DISTINCT slice_key, COUNT(*) AS rows
FROM ${catalog}.${monitoring_schema}.${table}_profile_metrics
GROUP BY slice_key
ORDER BY slice_key;

-- Check source data date range (for monitor time window debugging)
SELECT
  COUNT(*) AS total_rows,
  MIN(${timestamp_col}) AS earliest,
  MAX(${timestamp_col}) AS latest,
  DATEDIFF(MAX(${timestamp_col}), MIN(${timestamp_col})) AS days_span
FROM ${catalog}.${schema}.${table};

-- Check custom metrics values (CORRECT query pattern)
SELECT window.start, window.end,
  ${metric_name_1}, ${metric_name_2}
FROM ${catalog}.${monitoring_schema}.${table}_profile_metrics
WHERE column_name = ':table'      -- REQUIRED for custom metrics
  AND log_type = 'INPUT'          -- REQUIRED for source data
  AND slice_key IS NULL           -- For overall (non-sliced) metrics
ORDER BY window.start DESC
LIMIT 10;

-- Check drift metrics
SELECT window.start, drift_type,
  ${metric_name}
FROM ${catalog}.${monitoring_schema}.${table}_drift_metrics
WHERE drift_type = 'CONSECUTIVE'   -- REQUIRED for period-over-period
  AND column_name = ':table'
ORDER BY window.start DESC
LIMIT 10;

-- Check number of time periods (drift requires 2+)
SELECT COUNT(DISTINCT window.start) AS periods
FROM ${catalog}.${monitoring_schema}.${table}_profile_metrics
WHERE column_name = ':table'
  AND log_type = 'INPUT';
```

---

## Alert Diagnostics

```sql
-- Check alert sync status
SELECT alert_id, alert_name, last_sync_status, last_sync_error, last_synced_at
FROM ${catalog}.${schema}.alert_configurations
WHERE last_sync_status = 'ERROR'
ORDER BY last_synced_at DESC;

-- Check validation failures
SELECT alert_id, error_message
FROM ${catalog}.${schema}.alert_validation_results
WHERE is_valid = FALSE;

-- Check sync performance over last week
SELECT
  AVG(total_duration_seconds) AS avg_duration_sec,
  AVG(success_count * 100.0 / total_alerts) AS avg_success_pct,
  COUNT(*) AS sync_runs
FROM ${catalog}.${schema}.alert_sync_metrics
WHERE sync_started_at >= CURRENT_DATE() - 7;

-- Check notification destinations
SELECT destination_id, destination_type, databricks_destination_id
FROM ${catalog}.${schema}.notification_destinations
WHERE databricks_destination_id IS NULL;  -- Missing = not synced

-- Test an alert query manually
EXPLAIN ${alert_query};  -- Validate syntax first
${alert_query};          -- Then run it
```

---

## Job & Pipeline Diagnostics

```sql
-- Check recent job runs (via system table if available)
SELECT *
FROM system.lakeflow.jobs
WHERE job_id = ${job_id}
ORDER BY run_start_time DESC
LIMIT 10;

-- Check DLT pipeline expectations results
SELECT *
FROM ${catalog}.${schema}.__apply_changes_storage_${table}
ORDER BY _commit_timestamp DESC
LIMIT 10;
```

---

## Gold Layer Diagnostics

```sql
-- Check Gold table row counts
SELECT '${table1}' AS table_name, COUNT(*) AS rows FROM ${catalog}.${gold_schema}.${table1}
UNION ALL
SELECT '${table2}', COUNT(*) FROM ${catalog}.${gold_schema}.${table2}
UNION ALL
SELECT '${table3}', COUNT(*) FROM ${catalog}.${gold_schema}.${table3};

-- Check for duplicate primary keys (pre-merge validation)
SELECT ${pk_column}, COUNT(*) AS cnt
FROM ${catalog}.${silver_schema}.${silver_table}
GROUP BY ${pk_column}
HAVING COUNT(*) > 1
LIMIT 20;

-- Check column names match between Silver and Gold
DESCRIBE TABLE ${catalog}.${silver_schema}.${silver_table};
DESCRIBE TABLE ${catalog}.${gold_schema}.${gold_table};

-- Check constraints on Gold table
SHOW CONSTRAINTS ON ${catalog}.${gold_schema}.${gold_table};
```

---

## Cluster Diagnostics

```sql
-- Check cluster events (if using system tables)
SELECT *
FROM system.compute.cluster_events
WHERE cluster_id = '${cluster_id}'
ORDER BY timestamp DESC
LIMIT 20;
```

---

## General Debugging

```sql
-- Check Unity Catalog objects
SELECT *
FROM system.information_schema.tables
WHERE table_catalog = '${catalog}'
  AND table_schema = '${schema}';

-- Check column metadata
SELECT column_name, data_type, comment, is_nullable
FROM system.information_schema.columns
WHERE table_catalog = '${catalog}'
  AND table_schema = '${schema}'
  AND table_name = '${table}'
ORDER BY ordinal_position;
```

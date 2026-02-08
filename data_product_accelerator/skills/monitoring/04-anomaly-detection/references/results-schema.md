# Anomaly Detection Results Schema

## System Table

All anomaly detection results are stored in:
```
system.data_quality_monitoring.table_results
```

**Access:** Only account admins by default. Contains data from ALL catalogs in the metastore.

**Important:** This table includes sample values from tables in each catalog. Use caution when granting access.

## Table Schema

Each row corresponds to a single scanned table.

### Top-Level Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `event_time` | `TIMESTAMP` | When the row was generated | `2025-06-27T12:00:00` |
| `catalog_name` | `STRING` | Catalog name | `main` |
| `schema_name` | `STRING` | Schema name | `gold` |
| `table_name` | `STRING` | Table name | `fact_sales_daily` |
| `catalog_id` | `STRING` | Stable UUID for catalog | `3f1a7d6e-...` |
| `schema_id` | `STRING` | Stable UUID for schema | `3f1a7d6e-...` |
| `table_id` | `STRING` | Stable UUID for table | `3f1a7d6e-...` |
| `status` | `STRING` | Consolidated health status | `Healthy`, `Unhealthy`, `Unknown` |
| `freshness` | `STRUCT` | Freshness check results | See below |
| `completeness` | `STRUCT` | Completeness check results | See below |
| `downstream_impact` | `STRUCT` | Summary of downstream impact (Experimental) | See below |
| `root_cause_analysis` | `STRUCT` | Upstream job information | See below |

### Freshness Struct

```sql
freshness.status              -- STRING: Overall freshness status
freshness.commit_freshness    -- STRUCT: Commit-based freshness check
```

#### commit_freshness Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | `STRING` | `Healthy`, `Unhealthy` |
| `error_code` | `STRING` | Error if check failed (e.g., `FAILED_TO_FIT_MODEL`) |
| `last_value` | `TIMESTAMP` | Last commit timestamp |
| `predicted_value` | `TIMESTAMP` | Predicted time for next commit |

### Completeness Struct

```sql
completeness.status           -- STRING: Overall completeness status
completeness.total_row_count  -- STRUCT: Total rows over time
completeness.daily_row_count  -- STRUCT: Rows added each day
```

#### Row Count Fields (total_row_count / daily_row_count)

| Field | Type | Description |
|-------|------|-------------|
| `status` | `STRING` | `Healthy`, `Unhealthy` |
| `error_code` | `STRING` | Error if check failed |
| `last_value` | `INT` | Actual rows observed in last 24 hours |
| `min_predicted_value` | `INT` | Minimum expected rows |
| `max_predicted_value` | `INT` | Maximum expected rows |

### Downstream Impact Struct (Experimental)

```sql
downstream_impact.impact_level                -- INT: 0=none, 1=low, 2=medium, 3=high, 4=very high
downstream_impact.num_downstream_tables       -- INT: Number of affected downstream tables
downstream_impact.num_queries_on_affected_tables -- INT: Queries on affected tables (last 30 days)
```

### Root Cause Analysis Struct

```sql
root_cause_analysis.upstream_jobs  -- ARRAY<STRUCT>: Metadata for upstream jobs
```

#### Upstream Jobs Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `STRING` | Databricks job ID |
| `workspace_id` | `STRING` | Workspace ID |
| `job_name` | `STRING` | Job display name |
| `last_run_status` | `STRING` | Status of most recent run |
| `run_page_url` | `STRING` | URL to Databricks job run page |

## Query Patterns

### Pattern 1: Unhealthy Tables Overview

```sql
SELECT
  CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
  status,
  freshness.status AS freshness_status,
  completeness.status AS completeness_status,
  downstream_impact.impact_level,
  downstream_impact.num_downstream_tables,
  downstream_impact.num_queries_on_affected_tables AS impacted_queries
FROM system.data_quality_monitoring.table_results
WHERE catalog_name = :catalog
  AND schema_name = :schema
  AND status = 'Unhealthy'
ORDER BY downstream_impact.impact_level DESC, event_time DESC;
```

### Pattern 2: Freshness Issues (Stale Tables)

```sql
SELECT
  table_name,
  freshness.commit_freshness.last_value AS last_commit,
  freshness.commit_freshness.predicted_value AS expected_by,
  TIMESTAMPDIFF(MINUTE,
    freshness.commit_freshness.predicted_value,
    freshness.commit_freshness.last_value
  ) AS minutes_late
FROM system.data_quality_monitoring.table_results
WHERE catalog_name = :catalog
  AND schema_name = :schema
  AND freshness.status = 'Unhealthy'
ORDER BY minutes_late DESC;
```

### Pattern 3: Completeness Issues (Missing Rows)

```sql
SELECT
  table_name,
  completeness.daily_row_count.last_value AS actual_rows,
  completeness.daily_row_count.min_predicted_value AS expected_min,
  completeness.daily_row_count.max_predicted_value AS expected_max,
  ROUND(
    completeness.daily_row_count.last_value * 100.0 /
    NULLIF(completeness.daily_row_count.min_predicted_value, 0), 1
  ) AS pct_of_expected
FROM system.data_quality_monitoring.table_results
WHERE catalog_name = :catalog
  AND schema_name = :schema
  AND completeness.status = 'Unhealthy'
ORDER BY pct_of_expected ASC;
```

### Pattern 4: Root Cause Analysis

```sql
SELECT
  table_name,
  status,
  rca.job_id,
  rca.job_name,
  rca.last_run_status,
  rca.run_page_url
FROM system.data_quality_monitoring.table_results
LATERAL VIEW EXPLODE(root_cause_analysis.upstream_jobs) AS rca
WHERE catalog_name = :catalog
  AND schema_name = :schema
  AND status = 'Unhealthy'
ORDER BY table_name;
```

### Pattern 5: High-Impact Issues (Triage Priority)

```sql
SELECT
  CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
  CASE downstream_impact.impact_level
    WHEN 4 THEN 'VERY HIGH'
    WHEN 3 THEN 'HIGH'
    WHEN 2 THEN 'MEDIUM'
    WHEN 1 THEN 'LOW'
    ELSE 'NONE'
  END AS impact,
  downstream_impact.num_downstream_tables,
  downstream_impact.num_queries_on_affected_tables,
  freshness.status AS freshness_status,
  completeness.status AS completeness_status
FROM system.data_quality_monitoring.table_results
WHERE status = 'Unhealthy'
  AND downstream_impact.impact_level >= 3  -- HIGH or VERY HIGH
ORDER BY downstream_impact.impact_level DESC,
         downstream_impact.num_queries_on_affected_tables DESC;
```

### Pattern 6: Schema Health Summary

```sql
SELECT
  catalog_name,
  schema_name,
  COUNT(*) AS total_tables,
  SUM(CASE WHEN status = 'Healthy' THEN 1 ELSE 0 END) AS healthy,
  SUM(CASE WHEN status = 'Unhealthy' THEN 1 ELSE 0 END) AS unhealthy,
  SUM(CASE WHEN status = 'Unknown' THEN 1 ELSE 0 END) AS unknown,
  ROUND(
    SUM(CASE WHEN status = 'Healthy' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
  ) AS health_pct
FROM system.data_quality_monitoring.table_results
WHERE event_time >= current_timestamp() - INTERVAL 24 HOURS
GROUP BY catalog_name, schema_name
ORDER BY health_pct ASC;
```

## Metastore-Level Dashboard

Databricks provides a downloadable Lakeview dashboard template for viewing quality results across the entire metastore.

**Prerequisites:** Access to `system.data_quality_monitoring.table_results`

**Steps:**
1. Download `metastore-quality-dashboard.lvdash.json` from Databricks documentation
2. In workspace sidebar, click **Dashboards**
3. Click **Create dashboard** > **Import dashboard from file**
4. Select the downloaded template file
5. Click **Import dashboard**

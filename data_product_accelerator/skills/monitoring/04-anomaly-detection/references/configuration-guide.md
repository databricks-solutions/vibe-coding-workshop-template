# Anomaly Detection Configuration Guide

## REST API Endpoint

```
POST /api/data-quality/v1/monitors
GET /api/data-quality/v1/monitors/{object_type}/{object_id}
PUT /api/data-quality/v1/monitors/{object_type}/{object_id}
DELETE /api/data-quality/v1/monitors/{object_type}/{object_id}
```

**Status:** Public Preview

## SDK Module

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import (
    Monitor,
    AnomalyDetectionConfig,
)
```

## Enable Anomaly Detection

### Step 1: Get Schema UUID

The API requires a UUID (`schema_id`), not the three-level name.

```python
w = WorkspaceClient()

# Get schema UUID
schema_info = w.schemas.get(full_name=f"{catalog}.{schema}")
schema_id = schema_info.schema_id
print(f"Schema UUID: {schema_id}")
```

**Alternative:** Find the Schema ID in Catalog Explorer > select schema > Details tab > Schema ID field.

### Step 2: Create Monitor

```python
from databricks.sdk.service.dataquality import AnomalyDetectionConfig

# Basic enable (monitor all tables)
monitor = w.data_quality.create_monitor(
    monitor=Monitor(
        object_type="schema",
        object_id=schema_id,
        anomaly_detection_config=AnomalyDetectionConfig()
    )
)

# With exclusions
monitor = w.data_quality.create_monitor(
    monitor=Monitor(
        object_type="schema",
        object_id=schema_id,
        anomaly_detection_config=AnomalyDetectionConfig(
            excluded_table_full_names=[
                f"{catalog}.{schema}.staging_raw",
                f"{catalog}.{schema}.temp_processing",
                f"{catalog}.{schema}._quarantine",
            ]
        )
    )
)
```

## Update Configuration

```python
# Update excluded tables list
# update_monitor() requires a Monitor object and an update_mask string
w.data_quality.update_monitor(
    monitor=Monitor(
        object_type="schema",
        object_id=schema_id,
        anomaly_detection_config=AnomalyDetectionConfig(
            excluded_table_full_names=[
                f"{catalog}.{schema}.staging_raw",
                f"{catalog}.{schema}.new_table_to_exclude",
            ]
        )
    ),
    update_mask="anomaly_detection_config",
)
```

## Get Monitor Status

```python
monitor = w.data_quality.get_monitor(
    object_type="schema",
    object_id=schema_id
)
print(f"Object Type: {monitor.object_type}")
print(f"Object ID: {monitor.object_id}")
if monitor.anomaly_detection_config:
    excluded = monitor.anomaly_detection_config.excluded_table_full_names or []
    print(f"Excluded tables: {excluded}")
```

## Delete Monitor

```python
# ⚠️ WARNING: This deletes ALL anomaly detection data. Cannot be undone.
w.data_quality.delete_monitor(
    object_type="schema",
    object_id=schema_id
)
```

## List All Monitors

**Note:** `list_monitor()` is marked as (Unimplemented) in the SDK as of v0.68.0. This may fail until the SDK implements it. Use `get_monitor()` for individual lookups instead.

```python
# List all monitors in the workspace (may fail — see note above)
monitors = w.data_quality.list_monitor()
for monitor in monitors:
    print(f"  {monitor.object_type}/{monitor.object_id}")
    if monitor.anomaly_detection_config:
        print(f"    Type: Anomaly Detection (schema)")
    if monitor.data_profiling_config:
        print(f"    Type: Data Profiling (table)")
```

## Advanced Configuration (REST API)

For fine-grained control over freshness and completeness thresholds, use the REST API task parameters on the background job. These parameters are configured as `metric_configs` JSON.

### Default metric_configs

```json
[
  {
    "disable_check": false,
    "tables_to_skip": null,
    "tables_to_scan": null,
    "table_threshold_overrides": null,
    "table_latency_threshold_overrides": null,
    "static_table_threshold_override": null,
    "event_timestamp_col_names": null,
    "metric_type": "FreshnessConfig"
  },
  {
    "disable_check": true,
    "tables_to_skip": null,
    "tables_to_scan": null,
    "table_threshold_overrides": null,
    "metric_type": "CompletenessConfig"
  }
]
```

### Freshness Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `tables_to_scan` | Only scan these tables | `["table_a", "table_b"]` |
| `tables_to_skip` | Skip these tables during scan | `["staging_table"]` |
| `disable_check` | Disable freshness check entirely | `true` / `false` |
| `table_threshold_overrides` | Max seconds since last update before marking Unhealthy | `{"fact_sales": 86400}` (24 hours) |
| `table_latency_threshold_overrides` | Max seconds since last timestamp value before marking Unhealthy | `{"fact_sales": 3600}` (1 hour) |
| `static_table_threshold_override` | Seconds before a table is considered static (no longer updated) | `2592000` (30 days) |
| `event_timestamp_col_names` | Timestamp columns to check for event freshness | `["event_time", "created_at"]` |

### Completeness Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `tables_to_scan` | Only scan these tables | `["table_a"]` |
| `tables_to_skip` | Skip these tables | `["staging_table"]` |
| `disable_check` | Disable completeness check | `true` / `false` |
| `table_threshold_overrides` | Min rows expected in last 24 hours | `{"fact_sales": 1000}` |

**Note:** By default, `completeness` is disabled (`"disable_check": true`). Enable it by setting `"disable_check": false`.

## Permissions Reference

### To Enable Anomaly Detection
Either:
- `MANAGE` + `USE_CATALOG` on the catalog
- `USE_CATALOG` on the catalog + `MANAGE` + `USE_SCHEMA` on the schema

### To Query Results
- `SELECT` on `system.data_quality_monitoring.table_results`
- Default: Only account admins have access
- Admin must explicitly grant access to other users/groups

## Integration with Catalog Explorer

After enabling, the schema page shows:
1. **Data Quality Monitoring** toggle in the Details tab
2. **View results** link to see quality incidents
3. **Table Quality Details** for per-table freshness/completeness trends
4. Root cause analysis linking to upstream jobs

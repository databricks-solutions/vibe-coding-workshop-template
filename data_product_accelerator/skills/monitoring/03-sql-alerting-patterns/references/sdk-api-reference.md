# SDK & V2 API Reference

## SDK Version Requirements

| Feature | Minimum SDK Version | Notes |
|---------|-------------------|-------|
| Typed SDK Classes (`AlertCondition`, etc.) | `>=0.28.0` | Pattern 2a in SKILL.md |
| V2 Dict-Based API (`AlertV2.from_dict()`) | `>=0.40.0` | Pattern 2b in SKILL.md (recommended) |

## SDK Setup Ceremony

**⚠️ CRITICAL:** The SDK must be upgraded at runtime in Databricks notebooks:

```python
# Databricks notebook source
# MAGIC %pip install --upgrade databricks-sdk>=0.40.0 --quiet

# COMMAND ----------

# MAGIC %restart_python

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import AlertV2
```

**Why `%restart_python`?** After `%pip install`, the Python environment needs a restart to pick up the new package version. Without it, you'll get `ImportError` for `AlertV2`.

## V2 API Payload Structure

Complete dict structure for creating alerts via V2 API:

```python
alert_dict = {
    # Required: Display name shown in Databricks UI
    "display_name": "[CRITICAL] Alert Name",

    # Required: Full SQL query (fully qualified table names, no parameters)
    "query_text": "SELECT column FROM catalog.schema.table WHERE condition",

    # Required: SQL Warehouse ID to execute the query
    "warehouse_id": "warehouse-id",

    # Required: Schedule configuration
    "schedule": {
        "quartz_cron_schedule": "0 0 * * * ?",  # Quartz cron format
        "timezone_id": "America/Los_Angeles",     # IANA timezone
        "pause_status": "UNPAUSED"                # UNPAUSED or PAUSED
    },

    # Required: Evaluation configuration
    "evaluation": {
        # Which column and aggregation to evaluate
        "source": {
            "name": "column_name",       # Column from query result
            "aggregation": "SUM"         # See Aggregation Types below
        },

        # Comparison operator (see table below)
        "comparison_operator": "GREATER_THAN",

        # Threshold value to compare against
        "threshold": {
            "value": {
                "double_value": 1000     # Numeric threshold
            }
        },

        # What to do when query returns empty results
        "empty_result_state": "OK",      # OK, TRIGGERED, or UNKNOWN

        # Notification configuration
        "notification": {
            "notify_on_ok": False,       # Send notification when alert resolves
            "subscriptions": [
                {"user_email": "user@company.com"}
            ]
        }
    }
}

# Create alert using V2 API
alert_v2 = AlertV2.from_dict(alert_dict)
ws.alerts_v2.create_alert(alert_v2)
```

## Comparison Operators

| Operator | API Value | Example Use |
|----------|-----------|-------------|
| `>` | `GREATER_THAN` | Revenue exceeds threshold |
| `>=` | `GREATER_THAN_OR_EQUAL` | Count at or above minimum |
| `<` | `LESS_THAN` | Rate below baseline |
| `<=` | `LESS_THAN_OR_EQUAL` | Cost at or under budget |
| `=` | `EQUAL` | Exact match (INFO always_trigger) |
| `!=` | `NOT_EQUAL` | Status changed |
| `IS NULL` | `IS_NULL` | Missing data detection |

## Aggregation Types

| Type | API Value | Notes |
|------|-----------|-------|
| Sum | `SUM` | Total of all values |
| Count | `COUNT` | Number of rows |
| Count Distinct | `COUNT_DISTINCT` | Unique values |
| Average | `AVG` | Mean of values |
| Median | `MEDIAN` | Middle value |
| Minimum | `MIN` | Smallest value |
| Maximum | `MAX` | Largest value |
| Standard Deviation | `STDDEV` | Spread of values |
| First Value | `null` (or omit) | Use `FIRST` in config, maps to null in API |

**Note:** When `aggregation_type` is `FIRST` in your config table, pass `null` or omit the `aggregation` field in the API payload.

## API Gotchas

### 1. Correct API Endpoint

**✅ CORRECT:** `/api/2.0/alerts`

**❌ WRONG:** `/api/2.0/sql/alerts-v2`

The V2 alerts use the same base endpoint as V1. The "v2" is in the SDK class names, not the URL.

### 2. List Response Format

V2 API returns alerts under the `alerts` key:

```python
# ✅ CORRECT: V2 response format
response = ws.alerts_v2.list_alerts()
alerts = response.alerts  # NOT response.results

# Build lookup dict
existing_alerts = {a.display_name: a for a in alerts}
```

### 3. PATCH Requires update_mask

When updating an existing alert, you MUST specify which fields to update:

```python
# ✅ CORRECT: Include update_mask
ws.alerts_v2.update_alert(
    alert_id=existing.id,
    alert=alert_v2,
    update_mask="query_text,evaluation,schedule"
)

# ❌ WRONG: Missing update_mask (silently fails or errors)
ws.alerts_v2.update_alert(alert_id=existing.id, alert=alert_v2)
```

### 4. RESOURCE_ALREADY_EXISTS Handling

When creating an alert that already exists (same display name):

```python
try:
    new_alert = ws.alerts_v2.create_alert(alert_v2)
except Exception as e:
    if "RESOURCE_ALREADY_EXISTS" in str(e):
        # Refresh alert list (might have been created by another process)
        existing_alerts = {a.display_name: a for a in ws.alerts_v2.list_alerts().alerts}
        existing = existing_alerts.get(alert_name)
        if existing:
            # Update instead of create
            ws.alerts_v2.update_alert(
                alert_id=existing.id,
                alert=alert_v2,
                update_mask="query_text,evaluation,schedule"
            )
    else:
        raise
```

### 5. Authentication

In Databricks notebooks, use auto-authentication:

```python
# ✅ CORRECT: Auto-auth in notebook context
ws = WorkspaceClient()

# ❌ WRONG: Don't hardcode credentials
ws = WorkspaceClient(host="...", token="...")
```

## SDK Class Reference

### V2 Dict-Based (Recommended)

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import AlertV2

ws = WorkspaceClient()
alert_v2 = AlertV2.from_dict(alert_dict)

# Create
ws.alerts_v2.create_alert(alert_v2)

# List
response = ws.alerts_v2.list_alerts()
alerts = response.alerts

# Update (requires update_mask)
ws.alerts_v2.update_alert(
    alert_id="alert-id",
    alert=alert_v2,
    update_mask="query_text,evaluation,schedule"
)

# Delete
ws.alerts_v2.delete_alert(alert_id="alert-id")
```

### Typed Classes (Legacy)

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    AlertCondition,
    AlertConditionOperand,
    AlertConditionThreshold,
    AlertOperandColumn,
    AlertOperandValue,
    AlertConditionOperator,
)

ws = WorkspaceClient()

# Build condition
condition = AlertCondition(
    op=AlertConditionOperator.GREATER_THAN,
    operand=AlertConditionOperand(
        column=AlertOperandColumn(name="column_name")
    ),
    threshold=AlertConditionThreshold(
        value=AlertOperandValue(string_value="100")
    )
)

# Create
ws.alerts.create(
    display_name="Alert Name",
    query_text="SELECT ...",
    warehouse_id="warehouse-id",
    condition=condition,
    cron_schedule="0 0 * * * ?",
    cron_timezone="America/Los_Angeles",
)
```

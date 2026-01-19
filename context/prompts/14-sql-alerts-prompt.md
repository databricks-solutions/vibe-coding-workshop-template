# SQL Alerts V2 Implementation Prompt

Use this prompt to create a config-driven SQL alerting framework using Databricks SQL Alerts V2 API.

---

## Prompt

```
I need to implement a config-driven SQL alerting framework for Databricks using SQL Alerts V2.

Requirements:
1. Store alert configurations in a Delta table (alert_configurations)
2. Use Databricks SDK with AlertV2 types for deployment
3. Support CRITICAL, WARNING, and INFO severity levels
4. Enable runtime enable/disable without code changes
5. Track sync status (created, updated, error) in the config table

Technical Requirements:
- API: SQL Alerts V2 (/api/2.0/alerts endpoint)
- SDK: databricks-sdk>=0.40.0 (requires %pip install --upgrade at runtime)
- Queries: Fully qualified table names (no parameters supported)
- Authentication: Auto via WorkspaceClient() in notebook context

Please follow @.cursor/rules/monitoring/19-sql-alerting-patterns.mdc for:
- Alert ID convention: {DOMAIN}-{NUMBER}-{SEVERITY}
- Config table schema
- SDK integration patterns
- V2 API payload structure
```

---

## Quick Reference

### Alert ID Convention
```
{DOMAIN}-{NUMBER}-{SEVERITY}
Examples:
- COST-001-CRIT
- SECURITY-003-WARN
- PERF-005-INFO
```

### SDK Setup (Critical!)
```python
# Databricks notebook source
# MAGIC %pip install --upgrade databricks-sdk>=0.40.0 --quiet

# COMMAND ----------

# MAGIC %restart_python

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import AlertV2
```

### V2 API Payload Structure
```python
alert_dict = {
    "display_name": "[CRITICAL] Alert Name",
    "query_text": "SELECT column FROM catalog.schema.table WHERE condition",
    "warehouse_id": "warehouse-id",
    "schedule": {
        "quartz_cron_schedule": "0 0 * * * ?",  # Every hour
        "timezone_id": "America/Los_Angeles",
        "pause_status": "UNPAUSED"
    },
    "evaluation": {
        "source": {"name": "column_name", "aggregation": "SUM"},
        "comparison_operator": "GREATER_THAN",
        "threshold": {"value": {"double_value": 1000}},
        "empty_result_state": "OK",
        "notification": {
            "notify_on_ok": False,
            "subscriptions": [{"user_email": "user@company.com"}]
        }
    }
}

alert_v2 = AlertV2.from_dict(alert_dict)
ws.alerts_v2.create_alert(alert_v2)
```

### Comparison Operators
| Operator | API Value |
|----------|-----------|
| `>` | `GREATER_THAN` |
| `>=` | `GREATER_THAN_OR_EQUAL` |
| `<` | `LESS_THAN` |
| `<=` | `LESS_THAN_OR_EQUAL` |
| `=` | `EQUAL` |
| `!=` | `NOT_EQUAL` |
| `IS NULL` | `IS_NULL` |

### Aggregation Types
`SUM`, `COUNT`, `COUNT_DISTINCT`, `AVG`, `MEDIAN`, `MIN`, `MAX`, `STDDEV`, `FIRST` (null in API)

---

## Key Learnings

1. **API Endpoint**: Use `/api/2.0/alerts` (NOT `/api/2.0/sql/alerts-v2`)
2. **SDK Version**: Requires `%pip install --upgrade databricks-sdk>=0.40.0` + `%restart_python`
3. **List Response**: V2 API returns `alerts` key (NOT `results`)
4. **Update Mask**: PATCH requests require `update_mask` parameter
5. **RESOURCE_ALREADY_EXISTS**: Handle by refreshing alert list and updating instead
6. **Fully Qualified Names**: Alerts don't support query parameters
7. **⚠️ SQL Escaping**: Use DataFrame (not SQL INSERT) for inserting queries - LIKE patterns lose quotes otherwise
8. **Proactive Validation**: Run EXPLAIN on all queries before deployment to catch column/table errors
9. **Hierarchical Jobs**: Atomic jobs (single notebook) + Composite jobs (`run_job_task`) - see below
10. **Partial Success**: Allow ≥90% success rate - don't fail entire deployment for single alert issues
11. **Unity Catalog**: No CHECK constraints, no DEFAULT values in DDL - validate in code

---

## Proactive Query Validation

Create a validation job that tests all alert queries before deployment:

```python
def validate_alert_query(spark, alert_id: str, query: str) -> tuple:
    """Validate query using EXPLAIN."""
    try:
        spark.sql(f"EXPLAIN {query}")
        return (alert_id, True, None)
    except Exception as e:
        if "UNRESOLVED_COLUMN" in str(e):
            return (alert_id, False, "Column not found")
        elif "TABLE_OR_VIEW_NOT_FOUND" in str(e):
            return (alert_id, False, "Table not found")
        return (alert_id, False, f"Error: {str(e)[:100]}")
```

### ⚠️ SQL Escaping Issue

**Problem:** SQL INSERT with `replace("'", "''")` breaks LIKE patterns:
```sql
-- Original: WHERE sku_name LIKE '%ALL_PURPOSE%'
-- After INSERT escaping: WHERE sku_name LIKE %ALL_PURPOSE% (quotes lost!)
```

**Solution:** Use DataFrame with explicit schema:
```python
# ✅ CORRECT: DataFrame handles escaping automatically
rows = [(alert_id, alert_name, alert_query, ...)]
df = spark.createDataFrame(rows, schema)
df.write.mode("append").saveAsTable(cfg_table)
```

---

## Hierarchical Job Architecture

**⚠️ CRITICAL:** Use atomic + composite jobs pattern:

```
Layer 1 (Atomic - single notebook per job):
├── alerting_tables_setup_job.yml    → setup_alerting_tables.py
├── seed_all_alerts_job.yml          → seed_all_alerts.py
├── alert_query_validation_job.yml   → validate_alert_queries.py
├── notification_destinations_sync_job.yml → sync_notification_destinations.py
└── sql_alert_deployment_job.yml     → sync_sql_alerts.py

Layer 2 (Composite - orchestrates via run_job_task):
└── alerting_layer_setup_job.yml     → References all atomic jobs
```

**Composite Job Pattern:**
```yaml
tasks:
  - task_key: setup_alerting_tables
    run_job_task:  # ✅ NOT notebook_task!
      job_id: ${resources.jobs.alerting_tables_setup_job.id}
  
  - task_key: deploy_sql_alerts
    depends_on:
      - task_key: validate_alert_queries
    run_job_task:
      job_id: ${resources.jobs.sql_alert_deployment_job.id}
```

**Benefits:** Test atomic jobs independently, debug failures at specific step, run subsets of pipeline.

---

## Partial Success Pattern

```python
# Allow job to succeed if ≥90% of alerts deploy successfully
if success_rate >= 90:
    print(f"⚠️ Partial success: {success_rate:.0f}% ({success_count}/{total})")
else:
    raise RuntimeError(f"Too many failures: {len(errors)} errors")
```

---

## File Structure

```
src/alerting/
├── alerting_config.py              # Config helpers, dataclasses
├── alerting_metrics.py             # Metrics collection
├── setup_alerting_tables.py        # Creates Delta config tables
├── seed_all_alerts.py              # Seeds alert configs (DataFrame-based)
├── validate_alert_queries.py       # EXPLAIN-based query validation
├── sync_notification_destinations.py # Syncs notification channels
└── sync_sql_alerts.py              # SDK-based sync engine

resources/alerting/
├── alerting_layer_setup_job.yml          # Layer 2: Composite orchestrator
├── alerting_tables_setup_job.yml         # Layer 1: Atomic
├── seed_all_alerts_job.yml               # Layer 1: Atomic
├── alert_query_validation_job.yml        # Layer 1: Atomic
├── notification_destinations_sync_job.yml # Layer 1: Atomic
└── sql_alert_deployment_job.yml          # Layer 1: Atomic
```

---

## References

- [Cursor Rule](../.cursor/rules/monitoring/19-sql-alerting-patterns.mdc)
- [SDK Docs](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/sql/alerts_v2.html)
- [V2 API Docs](https://docs.databricks.com/api/workspace/alertsv2/createalert)
- [SQL Alerts UI](https://docs.databricks.com/aws/en/sql/user/alerts/)


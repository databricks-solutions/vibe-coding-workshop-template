# Dashboard Deployment Guide

## UPDATE-or-CREATE Deployment Pattern

### Overview

Use the Workspace Import API with `overwrite: true` to implement UPDATE-or-CREATE pattern. This preserves dashboard URLs, permissions, and provides a single code path for both CREATE and UPDATE operations.

### Benefits

- **Preserves dashboard URLs** - Users' bookmarks continue to work
- **Preserves permissions** - Existing grants remain intact
- **Single code path** - No conditional logic for CREATE vs UPDATE
- **No manual creation** - Fully automated deployment

### API Pattern

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

def deploy_dashboard(
    workspace_client: WorkspaceClient,
    dashboard_path: Path,
    target_path: str,
    variables: dict
) -> str:
    """Deploy dashboard using UPDATE-or-CREATE pattern."""
    
    # Read dashboard JSON
    with open(dashboard_path) as f:
        dashboard_json = f.read()
    
    # Substitute variables
    for key, value in variables.items():
        dashboard_json = dashboard_json.replace(f"${{{key}}}", value)
    
    # Import with overwrite
    workspace_client.workspace.import_(
        path=target_path,
        content=dashboard_json.encode('utf-8'),
        format=ImportFormat.AUTO,
        overwrite=True  # CRITICAL: Enables UPDATE-or-CREATE
    )
    
    return target_path
```

### Variable Substitution Pattern

**NEVER hardcode schemas.** Always use variables in dashboard JSON:

```sql
-- ✅ CORRECT - Uses variables
FROM ${catalog}.${gold_schema}.fact_usage
FROM ${catalog}.${gold_schema}_monitoring.fact_usage_profile_metrics

-- ❌ WRONG - Hardcoded schema
FROM prashanth_catalog.gold.fact_usage
```

**Substitution in Python:**

```python
variables = {
    'catalog': 'health_monitor',
    'gold_schema': 'system_gold',
    'feature_schema': 'system_gold_ml',
    'warehouse_id': 'abc123xyz'
}

# Simple string replacement
for key, value in variables.items():
    dashboard_json = dashboard_json.replace(f"${{{key}}}", value)
```

**Standard Variables:**

| Variable | Purpose | Example Value |
|---|---|---|
| `${catalog}` | Unity Catalog name | `health_monitor` |
| `${gold_schema}` | Gold layer schema | `system_gold` |
| `${feature_schema}` | ML/Feature schema | `system_gold_ml` |
| `${warehouse_id}` | SQL Warehouse ID | `abc123xyz` |

## Pre-Deployment SQL Validation

### Strategy

Validate all queries using `SELECT LIMIT 1` before deployment. This catches errors at once rather than one-by-one during dashboard testing.

### Benefits

- **90% reduction in dev loop time** - Catch errors before deployment
- **Catches ALL errors at once** - Not one-by-one during testing
- **Validates runtime errors** - Not just syntax, but actual execution

### Implementation

Use `scripts/validate_dashboard_queries.py`:

```bash
python scripts/validate_dashboard_queries.py
```

**What It Catches:**

- Column doesn't exist (`UNRESOLVED_COLUMN`)
- Table doesn't exist (`TABLE_OR_VIEW_NOT_FOUND`)
- Parameter binding issues (`UNBOUND_SQL_PARAMETER`)
- Type mismatches (`DATATYPE_MISMATCH`)
- Ambiguous column references (`AMBIGUOUS_REFERENCE`)

### Parameter Substitution for Validation

The validation script substitutes dashboard parameters with test values:

```python
substitutions = {
    # Time range parameters
    r':time_range\.min': "CURRENT_DATE() - INTERVAL 30 DAYS",
    r':time_range\.max': "CURRENT_DATE()",
    
    # Multi-select parameters (return ARRAY)
    r':param_workspace': "ARRAY('All')",
    r':param_catalog': "ARRAY('All')",
    
    # Single-select parameters
    r':monitor_slice_key': "'No Slice'",
    
    # Text input parameters
    r':annual_commit': "1000000",
}
```

## Monitoring Table Query Patterns

### Window Struct Access

**CRITICAL:** Use `window.start` not `window_start`:

```sql
-- ✅ CORRECT
SELECT 
  window.start AS window_start,
  window.end AS window_end
FROM fact_usage_profile_metrics
WHERE window.start BETWEEN :time_range.min AND :time_range.max

-- ❌ WRONG
SELECT window_start FROM ...  -- Column doesn't exist!
```

### Generic Metrics (CASE Pivot)

For generic metrics stored in `column_name` field, use CASE pivot:

```sql
SELECT 
  window.start AS window_start,
  MAX(CASE WHEN column_name = 'success_rate' THEN avg END) AS success_rate_pct,
  MAX(CASE WHEN column_name = 'error_count' THEN avg END) AS error_count
FROM fact_job_run_timeline_profile_metrics
WHERE window.start BETWEEN :time_range.min AND :time_range.max
  AND column_name IN ('success_rate', 'error_count')
GROUP BY window.start
```

### Custom Drift Metrics

Custom AGGREGATE/DERIVED metrics are stored as **direct columns** (not in `avg_delta`):

```sql
-- ✅ CORRECT - Direct column access
SELECT 
  window.start AS window_start,
  success_rate_drift,  -- Direct column!
  cost_drift_pct       -- Direct column!
FROM fact_job_run_timeline_drift_metrics
WHERE column_name = ':table' 
  AND drift_type = 'CONSECUTIVE'
  AND window.start BETWEEN :time_range.min AND :time_range.max

-- ❌ WRONG - Not in avg_delta
SELECT avg_delta.success_rate_drift FROM ...  -- Doesn't exist!
```

### Monitoring Schema Pattern

Always use the monitoring schema suffix:

```sql
-- ✅ CORRECT
FROM ${catalog}.${gold_schema}_monitoring.fact_usage_profile_metrics
FROM ${catalog}.${gold_schema}_monitoring.fact_usage_drift_metrics

-- ❌ WRONG
FROM ${catalog}.${gold_schema}.fact_usage_profile_metrics  -- Wrong schema!
```

### Filter Patterns

**Table-level metrics:**

```sql
WHERE column_name = ':table' AND slice_key IS NULL
```

**Slice-level metrics:**

```sql
WHERE column_name = ':table' 
  AND slice_key = :monitor_slice_key
  AND slice_value = :monitor_slice_value
```

## SQL Best Practices

### Always Use Explicit Aliases

Match widget `fieldName` exactly:

```sql
-- ✅ CORRECT - Matches widget fieldName
SELECT COUNT(*) AS total_queries FROM ...

-- ❌ WRONG - Mismatch with widget
SELECT COUNT(*) AS query_count FROM ...  -- Widget expects "total_queries"
```

### Return Raw Numbers

Let widgets handle formatting:

```sql
-- ✅ CORRECT - Raw number for currency
SELECT SUM(cost) AS total_cost FROM ...

-- ❌ WRONG - Pre-formatted string
SELECT CONCAT('$', FORMAT_NUMBER(SUM(cost), 2)) AS total_cost FROM ...
```

### Percentages as 0-1 Decimal

Return 0-1 decimal, widget multiplies by 100:

```sql
-- ✅ CORRECT - 0-1 decimal
SELECT ROUND(success_count * 1.0 / NULLIF(total_count, 0), 3) AS success_rate FROM ...

-- ❌ WRONG - Already multiplied
SELECT ROUND(success_count * 100.0 / NULLIF(total_count, 0), 1) AS success_rate FROM ...
```

### Use NULLIF for Division

Prevent division by zero:

```sql
-- ✅ CORRECT
SELECT value / NULLIF(total, 0) AS ratio FROM ...

-- ❌ WRONG
SELECT value / total AS ratio FROM ...  -- Fails when total = 0
```

### Date Filtering

Always filter by time range parameter:

```sql
-- ✅ CORRECT
WHERE usage_date BETWEEN :time_range.min AND :time_range.max

-- ❌ WRONG - Hardcoded dates
WHERE usage_date >= '2025-01-01' AND usage_date <= '2025-01-31'
```

## Validation Checklist

### Pre-Deployment

- [ ] SQL Validation passed - All queries return results without error
- [ ] Widget Encoding Validation passed - All fieldNames match query aliases
- [ ] Git diff reviewed - No accidental deletions or regressions
- [ ] Local testing done - Validated in dev environment

### Widget-Query Alignment

- [ ] Widget `fieldName` matches query output alias exactly
- [ ] Format type matches expected value type (raw numbers for percent/currency)
- [ ] All parameters are defined in dataset's `parameters` array
- [ ] Time range uses correct access pattern (`:time_range.min`, `:time_range.max`)

### Monitoring Query Validation

- [ ] Uses `window.start` not `window_start`
- [ ] Custom AGGREGATE/DERIVED metrics selected as direct columns
- [ ] Schema is `${catalog}.${gold_schema}_monitoring`
- [ ] Includes `WHERE column_name = ':table' AND slice_key IS NULL` for table-level metrics

### Chart Validation

- [ ] Pie charts: `color.scale: categorical`, `angle.scale: quantitative`
- [ ] Bar charts: `x.scale: categorical`, `y.scale: quantitative`
- [ ] Line charts: `x.scale: temporal`, `y.scale: quantitative`, `color.scale: categorical`
- [ ] Area charts: `x.scale: temporal`, `y.scale: quantitative`, `color.scale: categorical`
- [ ] Table widgets: Uses `version: 2`, no invalid properties

### Variable Substitution

- [ ] No hardcoded schemas in queries
- [ ] All variables defined in deployment script
- [ ] Variable substitution tested in dev environment

## Deployment Workflow

1. **Validate Queries**
   ```bash
   python scripts/validate_dashboard_queries.py
   ```

2. **Validate Widget Encodings**
   ```bash
   python scripts/validate_widget_encodings.py
   ```

3. **Deploy Dashboards**
   ```python
   from scripts.deploy_dashboard import deploy_dashboards
   
   deploy_dashboards(
       workspace_client,
       dashboard_dir=Path("src/dashboards"),
       catalog="health_monitor",
       gold_schema="system_gold",
       warehouse_id="abc123",
       dashboard_folder="/Shared/dashboards"
   )
   ```

4. **Verify Deployment**
   - Check dashboard URLs are accessible
   - Verify widgets render correctly
   - Test parameter filters
   - Validate monitoring queries return data

## Troubleshooting Deployment Issues

### Dashboard Not Found After Deployment

**Cause:** Dashboard path doesn't match existing dashboard.

**Fix:** Ensure `target_path` matches existing dashboard path exactly, or use `overwrite: true` to create new.

### Variables Not Substituted

**Cause:** Variable syntax mismatch or missing variables.

**Fix:** 
- Check variable names match `${variable_name}` format
- Verify all variables provided in deployment script
- Check for typos in variable names

### Queries Fail After Deployment

**Cause:** Schema changes or missing tables.

**Fix:**
- Run pre-deployment validation
- Check table existence: `SHOW TABLES IN catalog.schema`
- Verify column names match: `DESCRIBE TABLE catalog.schema.table`

### Widgets Show "No Fields to Visualize"

**Cause:** Widget `fieldName` doesn't match query alias.

**Fix:**
- Run `validate_widget_encodings.py`
- Check query aliases match widget `fieldName` exactly
- Verify case sensitivity matches

# Widget Patterns and Configurations

## Widget-Query Column Alignment (CRITICAL)

### The Rule
**Widget `fieldName` in encodings MUST exactly match query output column alias.**

### ❌ WRONG - Column name mismatch
```json
// Widget expects "total_queries"
"encodings": {
  "value": { "fieldName": "total_queries" }
}
```
```sql
-- Query returns "query_count" - MISMATCH!
SELECT COUNT(*) AS query_count FROM ...
```

### ✅ CORRECT - Aligned column names
```json
// Widget expects "total_queries"
"encodings": {
  "value": { "fieldName": "total_queries" }
}
```
```sql
-- Query returns "total_queries" - MATCH!
SELECT COUNT(*) AS total_queries FROM ...
```

### Common Mismatches to Avoid

| Widget Expects | Query Often Returns | Fix |
|----------------|---------------------|-----|
| `total_queries` | `query_count` | Alias as `total_queries` |
| `warehouse_name` | `compute_type` | Alias as `warehouse_name` |
| `unique_users` | `distinct_users` | Alias as `unique_users` |
| `query_id` | `statement_id` | Alias as `query_id` |
| `failure_count` | `failed_queries` | Alias as `failure_count` |
| `total_cost` | `cost_30d` | Match widget expectation |

## Number Formatting Rules (CRITICAL)

### Format Behavior Reference

| Format Type | Expects | Multiplies? | Example Input → Output |
|-------------|---------|-------------|------------------------|
| `number-plain` | Raw number | No | `1234` → `1,234` |
| `number-percent` | 0-1 decimal | Yes (×100) | `0.85` → `85%` |
| `number-currency` | Raw number | No | `1234.56` → `$1,234.56` |

### ❌ WRONG - Formatted strings
```sql
-- Widget uses number-currency format
SELECT CONCAT('$', FORMAT_NUMBER(SUM(cost), 2)) AS total_cost  -- WRONG!
```
**Result:** Empty or error - widget can't parse formatted string

### ✅ CORRECT - Raw numbers
```sql
-- Widget uses number-currency format
SELECT ROUND(SUM(cost), 2) AS total_cost  -- CORRECT!
```

### ❌ WRONG - Percentage as 85
```sql
-- Widget uses number-percent format
SELECT ROUND(success_count * 100.0 / total_count, 1) AS success_rate  -- Shows 8500%!
```

### ✅ CORRECT - Percentage as 0.85
```sql
-- Widget uses number-percent format
SELECT ROUND(success_count * 1.0 / NULLIF(total_count, 0), 3) AS success_rate  -- Shows 85%
```

### Key Rules
1. **NEVER use `FORMAT_NUMBER()`** in queries for KPI widgets
2. **NEVER use `CONCAT('$', ...)` or `CONCAT(..., '%')`** for formatted widgets
3. For percentages: Return 0-1 decimal, let widget multiply by 100
4. For currency: Return raw numeric, let widget add symbol and commas

## Parameter Configuration (CRITICAL)

### Complete Parameter Definition

Every dataset using parameters MUST define them in the `parameters` array:

```json
{
  "name": "ds_kpi_revenue",
  "query": "SELECT SUM(cost) FROM table WHERE date BETWEEN :time_range.min AND :time_range.max",
  "parameters": [
    {
      "keyword": "time_range",
      "dataType": "DATETIME_RANGE",
      "defaultSelection": {
        "range": {
          "min": { "dataType": "DATETIME", "value": "now-30d/d" },
          "max": { "dataType": "DATETIME", "value": "now/d" }
        }
      }
    }
  ]
}
```

### Time Range Parameter Access
```sql
-- Access min and max from time_range parameter
WHERE usage_date BETWEEN :time_range.min AND :time_range.max
```

### Multi-Select Parameter
```json
{
  "keyword": "param_workspace",
  "dataType": "STRING",
  "multiValuesOptions": { "enabled": true },
  "defaultSelection": {
    "values": {
      "dataType": "STRING",
      "values": [{ "value": "All" }]
    }
  }
}
```

### Filter Widget with Parameter Queries
```json
{
  "widget": {
    "name": "filter_time_range",
    "spec": {
      "widgetType": "filter-date-range-picker",
      "encodings": {
        "start": { "parameterKeyword": "time_range.min" },
        "end": { "parameterKeyword": "time_range.max" }
      }
    },
    "param_queries": [
      { "paramDatasetName": "ds_kpi_revenue", "queryName": "param_ds_kpi_revenue" },
      { "paramDatasetName": "ds_trend", "queryName": "param_ds_trend" }
    ]
  }
}
```

### Text Input Parameter (e.g., Annual Commit)
```json
{
  "widget": {
    "name": "param_annual_commit",
    "spec": {
      "widgetType": "filter-text-input",
      "encodings": {
        "fields": [{
          "displayName": "Annual Commit ($)",
          "fieldName": "annual_commit",
          "parameterKeyword": "annual_commit"
        }]
      }
    },
    "param_queries": [
      { "paramDatasetName": "ds_commit_status", "queryName": "param_commit" },
      { "paramDatasetName": "ds_variance", "queryName": "param_commit" }
    ]
  }
}
```

## Pie Chart Configuration (CRITICAL)

### Required Scale Properties

Pie charts MUST have explicit `scale` properties or they won't render:

```json
{
  "spec": {
    "widgetType": "pie",
    "encodings": {
      "color": {
        "fieldName": "category",
        "displayName": "Category",
        "scale": { "type": "categorical" }  // REQUIRED!
      },
      "angle": {
        "fieldName": "value",
        "displayName": "Value",
        "scale": { "type": "quantitative" }  // REQUIRED!
      }
    }
  }
}
```

### ❌ WRONG - Missing scale
```json
"encodings": {
  "color": { "fieldName": "category" },
  "angle": { "fieldName": "value" }
}
```
**Result:** Empty pie chart

## Bar Chart Configuration (CRITICAL)

### Required Scale Properties

Bar charts ALSO require explicit `scale` properties or they show "Select fields to visualize":

```json
{
  "spec": {
    "version": 3,
    "widgetType": "bar",
    "encodings": {
      "x": {
        "fieldName": "category_name",
        "displayName": "Category",
        "scale": { "type": "categorical" }  // REQUIRED!
      },
      "y": {
        "fieldName": "value",
        "displayName": "Value",
        "scale": { "type": "quantitative" }  // REQUIRED!
      }
    }
  }
}
```

### ❌ WRONG - Missing scale
```json
"encodings": {
  "x": { "fieldName": "category_name" },
  "y": { "fieldName": "value" }
}
```
**Result:** "Select fields to visualize" error

### Charts Requiring Scale Properties

| Widget Type | Encodings Requiring Scale |
|-------------|---------------------------|
| **pie** | `color.scale: categorical`, `angle.scale: quantitative` |
| **bar** | `x.scale: categorical`, `y.scale: quantitative` |
| **line** | `x.scale: temporal`, `y.scale: quantitative`, `color.scale: categorical` |
| **area** | `x.scale: temporal`, `y.scale: quantitative`, `color.scale: categorical` |

## Table Widget Configuration

### Version 2 Structure
```json
{
  "spec": {
    "version": 2,
    "widgetType": "table",
    "encodings": {
      "columns": [
        { "fieldName": "job_name", "title": "Job Name", "type": "string" },
        { "fieldName": "total_cost", "title": "Total Cost", "type": "number" },
        { "fieldName": "runs", "title": "Runs", "type": "number" }
      ]
    },
    "frame": {
      "showTitle": true,
      "title": "Most Expensive Jobs"
    }
  }
}
```

### ❌ Invalid Properties (v1 only)
Remove these properties when using version 2:
```json
// REMOVE THESE:
"itemsPerPage": 50,
"condensed": true,
"withRowNumber": true
```

## Multi-Series Line Charts

### Use UNION ALL for Multiple Series
```sql
SELECT 
  DATE(start_time) AS date,
  'Average' AS metric,
  AVG(duration_ms) / 60000 AS duration_min
FROM fact_query_history
WHERE start_time BETWEEN :time_range.min AND :time_range.max
GROUP BY 1

UNION ALL

SELECT 
  DATE(start_time) AS date,
  'P95 (Slow)' AS metric,
  PERCENTILE_APPROX(duration_ms, 0.95) / 60000 AS duration_min
FROM fact_query_history
WHERE start_time BETWEEN :time_range.min AND :time_range.max
GROUP BY 1

ORDER BY date, metric
```

### Widget Encoding for Multi-Series
```json
{
  "spec": {
    "widgetType": "line",
    "encodings": {
      "x": {
        "fieldName": "date",
        "scale": { "type": "temporal" }
      },
      "y": {
        "fieldName": "duration_min",
        "scale": { "type": "quantitative" }
      },
      "color": {
        "fieldName": "metric",
        "scale": { "type": "categorical" }
      }
    }
  }
}
```

## Stacked Area Charts

### Configuration for Status Breakdown
```json
{
  "spec": {
    "widgetType": "area",
    "encodings": {
      "x": {
        "fieldName": "run_date",
        "scale": { "type": "temporal" }
      },
      "y": {
        "fieldName": "run_count",
        "scale": { "type": "quantitative" },
        "stack": "zero"  // CRITICAL for stacking
      },
      "color": {
        "fieldName": "status",
        "scale": {
          "type": "categorical",
          "domain": ["Success", "Failed"],
          "range": ["#00A972", "#FF3621"]  // Green, Red
        }
      }
    }
  }
}
```

### Query Pattern for Status Breakdown
```sql
SELECT 
  run_date,
  'Success' AS status,
  SUM(CASE WHEN result_state IN ('SUCCESS', 'SUCCEEDED') THEN 1 ELSE 0 END) AS run_count
FROM fact_job_run_timeline
WHERE run_date BETWEEN :time_range.min AND :time_range.max
GROUP BY run_date

UNION ALL

SELECT 
  run_date,
  'Failed' AS status,
  SUM(CASE WHEN result_state NOT IN ('SUCCESS', 'SUCCEEDED') THEN 1 ELSE 0 END) AS run_count
FROM fact_job_run_timeline
WHERE run_date BETWEEN :time_range.min AND :time_range.max
GROUP BY run_date

ORDER BY run_date, status
```

## Common Error Messages and Fixes

| Error Message | Cause | Fix |
|---------------|-------|-----|
| "no fields to visualize" | Widget `fieldName` doesn't match query alias | Align column aliases |
| "UNRESOLVED_COLUMN" | Column doesn't exist in table | Check schema, use correct column |
| "UNBOUND_SQL_PARAMETER" | Parameter not defined in dataset | Add to `parameters` array |
| "Unable to render visualization" | Pie chart missing scale | Add `scale` to encodings |
| Empty chart with data | Wrong number format | Return raw numbers, not strings |
| 0% or 0 in counter | Formatted string or wrong percentage | Return 0-1 decimal for percent |
| "Invalid spec version" | Wrong version for widget type | KPI=2, Chart=3, Table=2, Filter=2 |

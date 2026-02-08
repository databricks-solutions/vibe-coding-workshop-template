# Dashboard JSON Structure Reference

## Page Layout and Positioning

### Page Structure
```json
{
  "name": "page_name",
  "displayName": "Page Display Name",
  "pageType": "PAGE_TYPE_DEFAULT",
  "layout": [
    {
      "widget": { /* widget definition */ },
      "position": { "x": 0, "y": 0, "width": 2, "height": 1 }
    }
  ]
}
```

### Global Filters Page
```json
{
  "name": "page_global_filters",
  "displayName": "Global Filters",
  "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
  "layout": [
    {
      "widget": {
        "name": "filter_time_range",
        "spec": {
          "widgetType": "filter-date-range-picker"
        }
      },
      "position": { "x": 0, "y": 0, "width": 2, "height": 1 }
    }
  ]
}
```

### Grid Layout System
- **6-column grid** (standard)
- Widgets span 1-6 columns
- Height measured in rows (typically 1-3)
- Position: `{ "x": 0-5, "y": 0+, "width": 1-6, "height": 1+ }`

### Page Naming Conventions

| Old Name | New Name | Why |
|----------|----------|-----|
| `📊 Lakehouse Monitoring` | `📈 Cost Metrics Overview` | Describes content |
| `Lakehouse Monitoring - fact_usage` | `🔬 Advanced Cost Metrics` | Indicates detail level |
| `📊 Lakehouse Monitoring` | `📈 Job Metrics Overview` | Domain-specific |
| `Lakehouse Monitoring - fact_job_run_timeline` | `🔬 Advanced Job Metrics` | Table reference |

## Dataset Structure

### Basic Dataset
```json
{
  "name": "ds_dataset_name",
  "query": "SELECT ... FROM ... WHERE ...",
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

### Schema Variable Substitution

**Standard Variables:**
```sql
-- Gold layer tables
FROM ${catalog}.${gold_schema}.fact_usage

-- Monitoring tables
FROM ${catalog}.${gold_schema}_monitoring.fact_usage_profile_metrics

-- ML/Feature tables
FROM ${catalog}.${feature_schema}.budget_forecaster_predictions
```

**❌ NEVER Hardcode Schemas:**
```sql
-- WRONG
FROM prashanth_catalog.gold.fact_usage

-- CORRECT
FROM ${catalog}.${gold_schema}.fact_usage
```

## Widget Version Reference

| Widget Type | Version | Notes |
|-------------|---------|-------|
| Counter (KPI) | 2 | Do NOT include `period` |
| Bar Chart | 3 | |
| Line Chart | 3 | |
| Area Chart | 3 | Use `stack: "zero"` for stacked |
| Pie Chart | 3 | MUST have `scale` on both encodings |
| Table | 2 | Remove v1 properties |
| Filter (date range) | 2 | |
| Filter (single/multi select) | 2 | |
| Filter (text input) | 2 | |

## Variable Substitution Reference

| Variable | Purpose | Example Value |
|---|---|---|
| `${catalog}` | Unity Catalog name | `health_monitor` |
| `${gold_schema}` | Gold layer schema | `system_gold` |
| `${feature_schema}` | ML/Feature schema | `system_gold_ml` |
| `${warehouse_id}` | SQL Warehouse ID | `abc123xyz` |

## Dashboard File Structure

```
src/dashboards/
├── deploy_dashboards.py       # Deployment script
├── validate_dashboard_queries.py  # SQL validation
├── validate_widget_encodings.py   # Widget-query alignment
├── cost.lvdash.json           # Cost & Commitment dashboard
├── performance.lvdash.json    # Performance dashboard
├── reliability.lvdash.json    # Reliability dashboard
├── security.lvdash.json       # Security dashboard
├── quality.lvdash.json        # Quality & Governance dashboard
└── unified.lvdash.json        # Executive summary
```

## Professional Naming Conventions

### File Naming Pattern

**Use simple, descriptive names - NOT branded prefixes**

| ✅ GOOD | ❌ BAD |
|---------|--------|
| `cost.lvdash.json` | `Health_Monitor_Cost_and_Commitment.lvdash.json` |
| `performance.lvdash.json` | `DBX_Performance_Dashboard_v2.lvdash.json` |
| `reliability.lvdash.json` | `[Health Monitor] Reliability 2026.lvdash.json` |

**Why simple names:**
- Clean workspace paths: `/Shared/dashboards/cost.lvdash.json`
- Easy to reference in code: `dashboard_dir / "cost.lvdash.json"`
- Git-friendly (no spaces, no special characters)
- Professional appearance in file listings

### Display Name Pattern

**Use branded, user-friendly display names**

```python
DASHBOARDS = [
    ("cost.lvdash.json", "Databricks Cost Intelligence"),
    ("performance.lvdash.json", "Databricks Performance Analytics"),
    ("reliability.lvdash.json", "Databricks Reliability Monitor"),
    ("security.lvdash.json", "Databricks Security & Compliance"),
    ("quality.lvdash.json", "Databricks Data Quality Hub"),
    ("unified.lvdash.json", "Databricks Health Monitor"),
]
```

**Pattern:**
- `Databricks {Domain} {Type}`
- Examples: "Databricks Cost Intelligence", "Databricks Security & Compliance"
- Consistent branding across all dashboards
- Domain-specific keywords for discoverability

# AI/BI Lakeview Dashboard Creation Prompt

## 🚀 Quick Start (2 hours)

**Goal:** Create visual dashboards with AI-powered insights for business users

**What You'll Create:**
1. SQL queries from Metric Views or Gold tables
2. AI/BI Dashboard via UI (drag-and-drop layout)
3. Auto-refresh schedule

**Fast Track (UI-Based):**
```
1. Navigate to: Databricks Workspace → Dashboards → Create AI/BI Dashboard
2. Add Data → Query Metric View or Gold table
3. Add Visualizations:
   - Counter tiles for KPIs (Total Revenue, Units, Transactions)
   - Bar charts for comparisons (Revenue by Store)
   - Line charts for trends (Daily Revenue Trend)
   - Tables for drill-down (Top Products Detail)
4. Add Filters (Date Range, Store, Category)
5. Configure Layout (Canvas: 1280px wide, tiles sized to fit)
6. Enable Auto-refresh (Hourly/Daily)
7. Share with business users
```

**Query Pattern (Metric Views):**
```sql
-- Use MEASURE() function for semantic metrics
SELECT 
  store_name,
  MEASURE(`Total Revenue`) as revenue,
  MEASURE(`Total Units`) as units,
  MEASURE(`Transaction Count`) as transactions
FROM sales_performance_metrics
WHERE transaction_date BETWEEN :start_date AND :end_date
ORDER BY revenue DESC
LIMIT 10
```

**Best Practices:**
- ✅ **Use Metric Views** (not raw tables) for consistent metrics
- ✅ **Add filters** for date range, key dimensions
- ✅ **Counter tiles** for top KPIs (large, prominent)
- ✅ **Charts** for trends and comparisons
- ✅ **Auto-refresh** for near real-time dashboards

**Output:** Professional dashboard with AI-powered insights

📖 **Full guide below** for detailed layout patterns →

---

## Quick Reference

**Use this prompt when creating Databricks AI/BI Lakeview dashboards for any project.**

---

## 📋 Your Requirements (Fill These In First)

**Before creating dashboards, define these specifications:**

### Dashboard Purpose
- **Dashboard Name:** _________________ (e.g., "Sales Performance Dashboard", "Patient Outcomes Dashboard")
- **Audience:** _________________ (e.g., "Sales Managers", "Hospital Administrators", "Finance Team")
- **Update Frequency:** [ ] Real-time [ ] Hourly [ ] Daily [ ] Weekly
- **Primary Goal:** _________________ (e.g., "Track daily KPIs", "Monitor data quality", "Analyze trends")

### Data Sources
- **Catalog:** _________________ (e.g., my_catalog)
- **Schema:** _________________ (e.g., my_project_gold)
- **Primary Data Source:** [ ] Metric View [ ] Gold Fact Table [ ] System Tables
- **Table/View Name:** _________________ (e.g., sales_performance_metrics, fact_sales_daily)

### KPIs to Display (3-6 key metrics)

| # | KPI Name | Source Field | Format |
|---|----------|--------------|--------|
| 1 | Total Revenue | SUM(net_revenue) | Currency (USD) |
| 2 | _____________ | ______________ | _____________ |
| 3 | _____________ | ______________ | _____________ |
| 4 | _____________ | ______________ | _____________ |

**Example - Retail:**
- Total Revenue (Currency), Total Units (Number), Transaction Count (Number)

**Example - Healthcare:**
- Patient Count (Number), Readmission Rate (Percentage), Avg Length of Stay (Number)

**Example - Finance:**
- Transaction Volume (Number), Total Amount (Currency), Fraud Rate (Percentage)

### Filters Required

| Filter Name | Type | Values Source |
|------------|------|---------------|
| Date Range | Date Range | start_date, end_date |
| __________ | Single Select | Dimension table |
| __________ | Multi Select | Dimension table |

**Common Filters:**
- Date Range (always include)
- Location/Store/Facility (dimension)
- Category/Type (dimension)
- Status/State (dimension)

### Charts to Include (3-5 visualizations)

| # | Chart Type | Purpose | Data |
|---|-----------|---------|------|
| 1 | Line Chart | Revenue Trend | Daily revenue over time |
| 2 | Bar Chart | Top 10 by metric | Category comparison |
| 3 | _________ | ______________ | __________________ |
| 4 | _________ | ______________ | __________________ |

**Chart Types Available:**
- Line Chart (trends over time)
- Bar Chart (category comparisons)
- Pie Chart (distribution)
- Table (detailed data)
- Counter/KPI (single metric)

### Dashboard Pages

| Page Name | Purpose | Widgets |
|-----------|---------|---------|
| Overview | High-level KPIs | 6 KPIs + 2 charts |
| Details | Detailed analysis | 1 table + 2 charts |
| Global Filters | Cross-page filters | Date, dimensions |

---

## Input Required Summary
- Gold layer tables or Metric Views
- KPI requirements (metrics to display)
- Filter requirements (date range, dimensions)
- Visualization preferences (charts, tables)

**Output:** Production-ready Lakeview dashboard JSON with KPIs, charts, filters, and proper grid layout.

**Time Estimate:** 2-4 hours

---

## Core Philosophy: Self-Service Analytics

**⚠️ CRITICAL PRINCIPLE:**

AI/BI Lakeview dashboards provide **visual analytics for business users**:

- ✅ **6-Column Grid:** NOT 12-column! Widths must be 1-6
- ✅ **Version Specs:** KPIs use v2, Charts use v3, Tables use v1
- ✅ **Global Filters:** Cross-dashboard filtering on a dedicated page
- ✅ **DATE Parameters:** Static dates, not DATETIME with dynamic expressions
- ✅ **Proper JOINs:** Include workspace_id AND entity ID
- ❌ **No 12-Column Grid:** Widget widths are 1-6, never 1-12
- ❌ **No Assumed Field Names:** Verify system table schemas

**Why This Matters:**
- Visual insights for non-technical users
- Consistent metrics across the organization
- Self-service analytics (no SQL required)
- Professional, branded appearance

---

## Critical: Grid System

### ⚠️ ALWAYS Use 6-Column Grid (NOT 12!)

This is the #1 cause of widget snapping issues.

```json
{
  "position": {
    "x": 0,     // Column position: 0-5 (6-column grid)
    "y": 0,     // Row position: any positive integer
    "width": 3, // Width: 1, 2, 3, 4, or 6 (must sum to ≤6 per row)
    "height": 6 // Height: 1, 2, 6, 9 are common values
  }
}
```

### Grid Layout Patterns

```json
// Two widgets side-by-side (each 3 columns)
{"x": 0, "y": 0, "width": 3, "height": 6}  // Left
{"x": 3, "y": 0, "width": 3, "height": 6}  // Right

// Three widgets across (each 2 columns)
{"x": 0, "y": 0, "width": 2, "height": 6}  // Left
{"x": 2, "y": 0, "width": 2, "height": 6}  // Center
{"x": 4, "y": 0, "width": 2, "height": 6}  // Right

// KPI row (6 counters, 1 column each)
{"x": 0, "y": 0, "width": 1, "height": 2}
{"x": 1, "y": 0, "width": 1, "height": 2}
{"x": 2, "y": 0, "width": 1, "height": 2}
{"x": 3, "y": 0, "width": 1, "height": 2}
{"x": 4, "y": 0, "width": 1, "height": 2}
{"x": 5, "y": 0, "width": 1, "height": 2}

// Full-width chart
{"x": 0, "y": 0, "width": 6, "height": 6}
```

### Common Height Values
| Widget Type | Height |
|------------|--------|
| Filters | 1-2 |
| KPI Counters | 2 |
| Charts (standard) | 6 |
| Charts (large) | 9 |
| Tables | 6+ |

---

## Step 1: Dashboard Structure

### Standard Dashboard Layout

```
Page 1: Overview
├── Row 0: Filters (height: 2)
│   ├── Date Range Filter (width: 2)
│   ├── Store Filter (width: 2)
│   └── Product Filter (width: 2)
│
├── Row 2: KPIs (height: 2)
│   ├── Total Revenue (width: 2)
│   ├── Total Units (width: 2)
│   └── Transaction Count (width: 2)
│
├── Row 4: Main Charts (height: 6)
│   ├── Revenue Trend (line, width: 3)
│   └── Revenue by Category (bar, width: 3)
│
└── Row 10: Detail Table (height: 6)
    └── Transaction Details (width: 6)

Page: Global Filters
└── Cross-dashboard filters
```

---

## Step 2: Dashboard JSON Template

### Base Structure

```json
{
  "datasets": [
    // Dataset definitions (queries)
  ],
  "pages": [
    // Page definitions with widgets
  ],
  "parameters": [
    // Dashboard parameters (filters)
  ],
  "uiSettings": {
    // Theme and appearance
  }
}
```

### Complete Dashboard Template

```json
{
  "datasets": [
    {
      "name": "kpi_totals",
      "displayName": "KPI Totals",
      "query": "SELECT SUM(net_revenue) as total_revenue, SUM(net_units) as total_units, SUM(transaction_count) as total_transactions FROM ${catalog}.${schema}.fact_sales_daily WHERE transaction_date BETWEEN :start_date AND :end_date"
    },
    {
      "name": "revenue_trend",
      "displayName": "Revenue Trend",
      "query": "SELECT transaction_date, SUM(net_revenue) as revenue FROM ${catalog}.${schema}.fact_sales_daily WHERE transaction_date BETWEEN :start_date AND :end_date GROUP BY transaction_date ORDER BY transaction_date"
    },
    {
      "name": "revenue_by_category",
      "displayName": "Revenue by Category",
      "query": "SELECT p.category, SUM(f.net_revenue) as revenue FROM ${catalog}.${schema}.fact_sales_daily f JOIN ${catalog}.${schema}.dim_product p ON f.upc_code = p.upc_code WHERE f.transaction_date BETWEEN :start_date AND :end_date GROUP BY p.category ORDER BY revenue DESC"
    },
    {
      "name": "store_filter_values",
      "displayName": "Store Filter Values",
      "query": "SELECT 'All' as store_name UNION ALL SELECT DISTINCT store_name FROM ${catalog}.${schema}.dim_store WHERE is_current = true ORDER BY store_name"
    }
  ],
  
  "pages": [
    {
      "name": "page_overview",
      "displayName": "Overview",
      "layout": [
        // Widgets go here (see widget examples below)
      ]
    },
    {
      "name": "page_global_filters",
      "displayName": "Global Filters",
      "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
      "layout": [
        // Global filter widgets
      ]
    }
  ],
  
  "parameters": [
    {
      "displayName": "Start Date",
      "keyword": "start_date",
      "dataType": "DATE",
      "defaultSelection": {
        "values": {
          "dataType": "DATE",
          "values": [{"value": "2024-01-01"}]
        }
      }
    },
    {
      "displayName": "End Date",
      "keyword": "end_date",
      "dataType": "DATE",
      "defaultSelection": {
        "values": {
          "dataType": "DATE",
          "values": [{"value": "2024-12-31"}]
        }
      }
    }
  ],
  
  "uiSettings": {
    "theme": {
      "canvasBackgroundColor": {"light": "#F7F9FA", "dark": "#0B0E11"},
      "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#1A1D21"},
      "widgetBorderColor": {"light": "#E0E4E8", "dark": "#2A2E33"},
      "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
      "selectionColor": {"light": "#077A9D", "dark": "#8ACAE7"},
      "visualizationColors": [
        "#077A9D", "#00A972", "#FFAB00", "#FF3621",
        "#8BCAE7", "#99DDB4", "#FCA4A1", "#AB4057",
        "#6B4FBB", "#BF7080"
      ],
      "widgetHeaderAlignment": "LEFT"
    },
    "genieSpace": {"isEnabled": false}
  }
}
```

---

## Step 3: Widget Specifications

### KPI Counter (Version 2)

```json
{
  "widget": {
    "name": "kpi_total_revenue",
    "queries": [
      {
        "name": "main_query",
        "query": {
          "datasetName": "kpi_totals",
          "fields": [
            {"name": "total_revenue", "expression": "`total_revenue`"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 2,
      "widgetType": "counter",
      "encodings": {
        "value": {
          "fieldName": "total_revenue"
        }
      },
      "frame": {
        "showTitle": true,
        "title": "Total Revenue",
        "showDescription": true,
        "description": "Total sales revenue for selected period"
      }
    }
  },
  "position": {"x": 0, "y": 2, "width": 2, "height": 2}
}
```

**⚠️ Note:** KPIs use version 2. Do NOT include `period` in encodings.

### Bar Chart (Version 3)

```json
{
  "widget": {
    "name": "chart_revenue_by_category",
    "queries": [
      {
        "name": "main_query",
        "query": {
          "datasetName": "revenue_by_category",
          "fields": [
            {"name": "category", "expression": "`category`"},
            {"name": "revenue", "expression": "`revenue`"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 3,
      "widgetType": "bar",
      "encodings": {
        "x": {
          "fieldName": "category",
          "displayName": "Category",
          "scale": {"type": "categorical"}
        },
        "y": {
          "fieldName": "revenue",
          "displayName": "Revenue",
          "scale": {"type": "quantitative"}
        }
      },
      "frame": {
        "showTitle": true,
        "title": "Revenue by Category",
        "showDescription": true,
        "description": "Sales revenue breakdown by product category"
      }
    }
  },
  "position": {"x": 3, "y": 4, "width": 3, "height": 6}
}
```

### Line Chart (Version 3)

```json
{
  "widget": {
    "name": "chart_revenue_trend",
    "queries": [
      {
        "name": "main_query",
        "query": {
          "datasetName": "revenue_trend",
          "fields": [
            {"name": "transaction_date", "expression": "`transaction_date`"},
            {"name": "revenue", "expression": "`revenue`"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 3,
      "widgetType": "line",
      "encodings": {
        "x": {
          "fieldName": "transaction_date",
          "displayName": "Date",
          "scale": {"type": "temporal"}
        },
        "y": {
          "fieldName": "revenue",
          "displayName": "Revenue",
          "scale": {"type": "quantitative"}
        }
      },
      "frame": {
        "showTitle": true,
        "title": "Revenue Trend",
        "showDescription": true,
        "description": "Daily revenue over time"
      }
    }
  },
  "position": {"x": 0, "y": 4, "width": 3, "height": 6}
}
```

### Pie Chart (Version 3)

```json
{
  "widget": {
    "name": "chart_revenue_distribution",
    "queries": [
      {
        "name": "main_query",
        "query": {
          "datasetName": "revenue_by_category",
          "fields": [
            {"name": "category", "expression": "`category`"},
            {"name": "revenue", "expression": "`revenue`"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 3,
      "widgetType": "pie",
      "encodings": {
        "angle": {
          "fieldName": "revenue",
          "displayName": "Revenue",
          "scale": {"type": "quantitative"}
        },
        "color": {
          "fieldName": "category",
          "displayName": "Category",
          "scale": {"type": "categorical"}
        }
      },
      "frame": {
        "showTitle": true,
        "title": "Revenue Distribution",
        "showDescription": true,
        "description": "Revenue share by category"
      }
    }
  },
  "position": {"x": 0, "y": 10, "width": 3, "height": 6}
}
```

### Table Widget (Version 1)

```json
{
  "widget": {
    "name": "table_sales_detail",
    "queries": [
      {
        "name": "main_query",
        "query": {
          "datasetName": "sales_detail",
          "fields": [
            {"name": "store_name", "expression": "`store_name`"},
            {"name": "product", "expression": "`product`"},
            {"name": "revenue", "expression": "`revenue`"},
            {"name": "units", "expression": "`units`"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 1,
      "widgetType": "table",
      "encodings": {
        "columns": [
          {"fieldName": "store_name", "title": "Store"},
          {"fieldName": "product", "title": "Product"},
          {
            "fieldName": "revenue", 
            "title": "Revenue",
            "type": "number"
          },
          {"fieldName": "units", "title": "Units"}
        ]
      },
      "frame": {
        "showTitle": true,
        "title": "Sales Detail",
        "showDescription": true,
        "description": "Detailed sales by store and product"
      },
      "itemsPerPage": 50,
      "condensed": true,
      "withRowNumber": true
    }
  },
  "position": {"x": 0, "y": 16, "width": 6, "height": 6}
}
```

### Filter Widget (Single Select)

```json
{
  "widget": {
    "name": "filter_store",
    "queries": [
      {
        "name": "main_query",
        "query": {
          "datasetName": "store_filter_values",
          "fields": [
            {"name": "store_name", "expression": "`store_name`"}
          ],
          "disaggregated": false
        }
      }
    ],
    "spec": {
      "version": 2,
      "widgetType": "filter-single-select",
      "encodings": {
        "fields": [
          {
            "displayName": "Store",
            "fieldName": "store_name",
            "queryName": "main_query"
          }
        ]
      },
      "frame": {
        "showTitle": true,
        "title": "Store Filter"
      }
    }
  },
  "position": {"x": 0, "y": 0, "width": 2, "height": 2}
}
```

---

## Step 4: Query Best Practices

### Pattern: "All" Option for Filters

```sql
SELECT 'All' AS filter_value
UNION ALL
SELECT DISTINCT actual_value AS filter_value
FROM source_table
ORDER BY filter_value
```

### Pattern: Dynamic Filtering

```sql
WHERE (:store_filter = 'All' OR store_name = :store_filter)
  AND transaction_date BETWEEN :start_date AND :end_date
```

### Pattern: Handle NULL Values

```sql
COALESCE(store_name, 'Unknown')
COALESCE(category, 'Uncategorized')
```

### Pattern: Date Range

```sql
WHERE DATE(timestamp_field) >= :start_date 
  AND DATE(timestamp_field) <= :end_date
```

### Pattern: SCD2 Latest Records

```sql
WITH latest AS (
  SELECT *,
    ROW_NUMBER() OVER(PARTITION BY entity_id ORDER BY change_time DESC) as rn
  FROM source_table
  WHERE delete_time IS NULL
  QUALIFY rn = 1
)
SELECT * FROM latest
```

---

## Step 5: System Tables Reference

### ⚠️ Always Verify Field Names!

When using system tables, verify schema against [official docs](https://docs.databricks.com/aws/en/admin/system-tables/).

### `system.lakeflow.jobs` (SCD2)

```sql
-- Note: Column is 'name', NOT 'job_name'
SELECT workspace_id, job_id, name, description, run_as
FROM system.lakeflow.jobs
WHERE delete_time IS NULL
```

### `system.lakeflow.job_task_run_timeline`

```sql
-- Note: NO job_name column! JOIN with jobs table
SELECT jtr.*, 
  COALESCE(j.name, 'Job ' || jtr.job_id) AS job_name
FROM system.lakeflow.job_task_run_timeline jtr
LEFT JOIN (
  SELECT workspace_id, job_id, name,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, job_id 
                      ORDER BY change_time DESC) as rn
  FROM system.lakeflow.jobs
  WHERE delete_time IS NULL
  QUALIFY rn = 1
) j ON jtr.workspace_id = j.workspace_id AND jtr.job_id = j.job_id
```

### `system.compute.clusters`

```sql
SELECT workspace_id, cluster_id, 
       MAX_BY(dbr_version, change_time) AS dbr_version
FROM system.compute.clusters
WHERE delete_time IS NULL
GROUP BY workspace_id, cluster_id
```

---

## Step 6: Date Parameters

### ✅ Correct: DATE with Static Values

```json
{
  "displayName": "Start Date",
  "keyword": "start_date",
  "dataType": "DATE",
  "defaultSelection": {
    "values": {
      "dataType": "DATE",
      "values": [{"value": "2024-01-01"}]
    }
  }
}
```

### ❌ Wrong: DATETIME with Dynamic Expressions

```json
// This will NOT work
{
  "dataType": "DATETIME",
  "values": [{"value": "now-12M/M"}]
}
```

---

## Step 7: Global Filters Page

Always include a Global Filters page for cross-dashboard filtering:

```json
{
  "name": "page_global_filters",
  "displayName": "Global Filters",
  "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
  "layout": [
    {
      "widget": {
        "name": "global_date_range",
        "spec": {
          "version": 2,
          "widgetType": "filter-date-range",
          "frame": {
            "showTitle": true,
            "title": "Date Range"
          }
        }
      },
      "position": {"x": 0, "y": 0, "width": 2, "height": 2}
    },
    {
      "widget": {
        "name": "global_store_filter",
        "spec": {
          "version": 2,
          "widgetType": "filter-single-select",
          "frame": {
            "showTitle": true,
            "title": "Store"
          }
        }
      },
      "position": {"x": 2, "y": 0, "width": 2, "height": 2}
    }
  ]
}
```

---

## Implementation Checklist

### Phase 1: Planning (30 min)
- [ ] Identify KPIs to display
- [ ] List required filters (date, dimensions)
- [ ] Plan page structure and layout
- [ ] Sketch widget placement (grid positions)

### Phase 2: Datasets (30 min)
- [ ] Create dataset for each unique query
- [ ] Add "All" option to filter datasets
- [ ] Handle NULL values with COALESCE
- [ ] Test queries in SQL editor first

### Phase 3: Widgets (1-2 hours)
- [ ] Create KPI counters (version 2)
- [ ] Create charts (version 3)
- [ ] Create tables (version 1)
- [ ] Create filter widgets (version 2)
- [ ] Position using 6-column grid

### Phase 4: Parameters (15 min)
- [ ] Add date parameters (DATE type, static defaults)
- [ ] Link parameters to dataset queries
- [ ] Test parameter binding

### Phase 5: Styling (15 min)
- [ ] Apply Databricks theme colors
- [ ] Add titles and descriptions to all widgets
- [ ] Verify consistent formatting

### Phase 6: Testing (30 min)
- [ ] Import dashboard JSON
- [ ] Test all filters
- [ ] Verify widget snapping (6-column grid)
- [ ] Check data accuracy

---

## Verification Checklist

Before deploying dashboard:

- [ ] All widget positions use 6-column grid (widths: 1-6)
- [ ] KPIs use version 2 (not version 3)
- [ ] Charts use version 3
- [ ] Tables use version 1
- [ ] Date parameters use DATE type (not DATETIME)
- [ ] Global Filters page included
- [ ] All filters have "All" option
- [ ] NULL values handled with COALESCE
- [ ] System table fields verified against docs
- [ ] SCD2 tables handled with QUALIFY pattern
- [ ] JOINs include both workspace_id AND entity ID

---

## Key Principles

### 1. 6-Column Grid (NOT 12!)
```json
// ✅ Correct
{"width": 3}  // Half width

// ❌ Wrong
{"width": 6}  // This is full width in 6-column grid!
```

### 2. Version Numbers
| Widget | Version |
|--------|---------|
| KPI Counter | 2 |
| Bar Chart | 3 |
| Line Chart | 3 |
| Pie Chart | 3 |
| Table | 1 |
| Filter | 2 |

### 3. DATE, Not DATETIME
```json
// ✅ Correct
"dataType": "DATE"

// ❌ Wrong
"dataType": "DATETIME"
```

### 4. Always Include Global Filters
```json
"pageType": "PAGE_TYPE_GLOBAL_FILTERS"
```

### 5. Handle NULL Values
```sql
COALESCE(field, 'Default Value')
```

---

## Common Mistakes to Avoid

### ❌ Mistake 1: 12-Column Grid
```json
// Wrong - widget won't position correctly
{"width": 6}  // This is FULL width, not half!
```

### ❌ Mistake 2: Wrong Widget Version
```json
// Wrong - KPIs must use version 2
"version": 3,
"widgetType": "counter"
```

### ❌ Mistake 3: DATETIME Parameters
```json
// Wrong - use DATE type
"dataType": "DATETIME"
```

### ❌ Mistake 4: Missing "All" Option
```sql
-- Wrong - no way to clear filter
SELECT DISTINCT store_name FROM stores
```

### ❌ Mistake 5: Assuming Field Names
```sql
-- Wrong - job_name doesn't exist in this table!
SELECT job_name FROM system.lakeflow.job_task_run_timeline
```

---

## Dashboard File Management

### File Location
```
project/
├── docs/
│   └── dashboards/
│       └── {project}_dashboard.lvdash.json
```

### Naming Convention
```
{project}_{purpose}_dashboard.lvdash.json

Examples:
- lakehouse_monitoring_dashboard.lvdash.json
- sales_analytics_dashboard.lvdash.json
- executive_kpi_dashboard.lvdash.json
```

### Version Control
- Track dashboard JSON in git
- Use meaningful commit messages
- Document changes in comments

---

## References

### Official Documentation
- [AI/BI Dashboards](https://docs.databricks.com/dashboards/lakeview/)
- [System Tables Overview](https://docs.databricks.com/aws/en/admin/system-tables/)
- [Jobs System Tables](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
- [Compute System Tables](https://docs.databricks.com/aws/en/admin/system-tables/compute)

### Framework Rules
- [databricks-aibi-dashboards.mdc](mdc:framework/rules/18-databricks-aibi-dashboards.mdc)

---

## Summary

**What to Create:**
1. Dashboard JSON file with proper structure
2. Datasets (queries for each widget)
3. Pages with widget layouts
4. Parameters (date filters)
5. Global Filters page

**Critical Rules:**
- 6-column grid (NOT 12!)
- KPIs: v2, Charts: v3, Tables: v1
- DATE type for parameters (not DATETIME)
- Include Global Filters page
- Verify system table field names

**Time Estimate:** 2-4 hours

**Next Action:** Plan layout, create datasets, build widgets, test in Databricks



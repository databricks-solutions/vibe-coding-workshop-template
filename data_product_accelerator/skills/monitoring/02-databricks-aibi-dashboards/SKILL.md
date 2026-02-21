---
name: databricks-aibi-dashboards
description: Production-grade patterns for Databricks AI/BI (Lakeview) dashboards. Prevents visualization errors, deployment failures, and maintenance issues through widget-query alignment, number formatting, parameter configuration, monitoring table patterns, chart scale properties, and automated deployment workflows. Includes complete JSON templates, validation scripts, and step-by-step implementation guide.
metadata:
  author: prashanth subrahmanyam
  version: "2.0"
  domain: monitoring
  role: worker
  pipeline_stage: 7
  pipeline_stage_name: observability
  called_by:
    - observability-setup
  standalone: true
  keywords:
    - databricks
    - ai/bi
    - lakeview
    - dashboards
    - monitoring
    - visualization
    - deployment
    - widget configuration
    - sql validation
    - automation
    - production-grade
  last_verified: "2026-02-07"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-aibi-dashboards/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---

# Databricks AI/BI Dashboards

## Overview

This skill provides comprehensive patterns for building production-grade Databricks AI/BI (Lakeview) dashboards. These patterns were developed from 100+ production deployments and prevent common visualization errors, deployment failures, and maintenance issues.

**Core Philosophy: Self-Service Analytics**

AI/BI Lakeview dashboards provide **visual analytics for business users** with **no SQL required**. This skill emphasizes:

- ✅ **Visual insights** for non-technical users
- ✅ **Consistent metrics** across the organization
- ✅ **Self-service analytics** without coding knowledge
- ✅ **Professional, branded** appearance
- ✅ **Automated deployment** with validation
- ✅ **Error prevention** through pre-deployment checks

**Key Capabilities:**

- Widget-query column alignment validation
- Number formatting rules (percentages, currency, plain numbers)
- Parameter configuration (time ranges, multi-select, text input)
- Monitoring table query patterns (window structs, CASE pivots, custom drift metrics)
- Chart configuration (pie, bar, line, area, table widgets)
- Pre-deployment SQL validation (90% reduction in dev loop time)
- UPDATE-or-CREATE deployment pattern (preserves URLs and permissions)
- Variable substitution (no hardcoded schemas)
- Complete JSON templates for all widget types
- Phase-by-phase implementation guide
- **Production example** - Complete Jobs System Tables Dashboard demonstrating all patterns

## When to Use This Skill

Use this skill when:

- **Building AI/BI dashboards** - Creating new dashboards with proper widget configurations
- **Troubleshooting visualization errors** - Fixing "no fields to visualize", empty charts, or formatting issues
- **Deploying dashboards via API** - Automating dashboard deployment with UPDATE-or-CREATE pattern
- **Validating dashboard queries** - Pre-deployment SQL validation to catch errors before deployment
- **Querying monitoring tables** - Accessing Lakehouse Monitoring profile and drift metrics
- **Configuring parameters** - Setting up time ranges, filters, and multi-select parameters
- **Planning dashboard projects** - Using templates to gather requirements and plan implementation
- **Onboarding new developers** - Teaching AI/BI dashboard best practices with working examples

## 🚀 Quick Start (2 Hours)

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

**Time Estimate:** 2-4 hours for complete dashboard

**Production Example:** See `references/Jobs System Tables Dashboard.lvdash.json` for a complete working example demonstrating all patterns from this skill.

---

## 📋 Project Planning Template

**Use this template to gather requirements before building your dashboard.**

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

### Input Required Summary

- Gold layer tables or Metric Views
- KPI requirements (metrics to display)
- Filter requirements (date range, dimensions)
- Visualization preferences (charts, tables)

---

## Quick Reference

### Top 5 Critical Rules

| Rank | Issue | Prevention |
|------|-------|------------|
| 1 | Widget-Query Column Mismatch | Always use explicit SQL aliases matching widget `fieldName` |
| 2 | Incorrect Number Formatting | Return raw numbers, not formatted strings |
| 3 | Missing Parameter Definitions | Define ALL parameters in dataset's `parameters` array |
| 4 | Monitoring Table Schema | Use `CASE` pivots on `column_name`, access `window.start` |
| 5 | Pie Chart Scale Missing | Add explicit `scale` to both `color` and `angle` encodings |

### Widget-Query Alignment

**Rule:** Widget `fieldName` MUST exactly match query output column alias.

```sql
-- ✅ CORRECT
SELECT COUNT(*) AS total_queries FROM ...
-- Widget: "fieldName": "total_queries"

-- ❌ WRONG
SELECT COUNT(*) AS query_count FROM ...
-- Widget: "fieldName": "total_queries"  -- MISMATCH!
```

### Number Formatting

| Format Type | Expects | Example |
|-------------|---------|---------|
| `number-plain` | Raw number | `1234` → `1,234` |
| `number-percent` | 0-1 decimal (×100) | `0.85` → `85%` |
| `number-currency` | Raw number | `1234.56` → `$1,234.56` |

**Never use:** `FORMAT_NUMBER()`, `CONCAT('$', ...)`, or `CONCAT(..., '%')` in queries.

### Monitoring Table Patterns

```sql
-- ✅ CORRECT - Access window struct
SELECT window.start AS window_start FROM monitoring_table
WHERE window.start BETWEEN :time_range.min AND :time_range.max

-- ✅ CORRECT - CASE pivot for generic metrics
SELECT 
  window.start AS window_start,
  MAX(CASE WHEN column_name = 'success_rate' THEN avg END) AS success_rate_pct
FROM fact_job_run_timeline_profile_metrics
WHERE window.start BETWEEN :time_range.min AND :time_range.max
GROUP BY window.start

-- ✅ CORRECT - Custom drift metrics are direct columns
SELECT 
  window.start AS window_start,
  success_rate_drift,  -- Direct column!
  cost_drift_pct       -- Direct column!
FROM fact_job_run_timeline_drift_metrics
WHERE column_name = ':table' AND drift_type = 'CONSECUTIVE'
```

### Chart Scale Requirements

**Pie Charts:**
```json
{
  "encodings": {
    "color": { "fieldName": "category", "scale": { "type": "categorical" } },
    "angle": { "fieldName": "value", "scale": { "type": "quantitative" } }
  }
}
```

**Bar Charts:**
```json
{
  "encodings": {
    "x": { "fieldName": "category", "scale": { "type": "categorical" } },
    "y": { "fieldName": "value", "scale": { "type": "quantitative" } }
  }
}
```

---

## Critical Rules (Production-Grade)

### ⚠️ CRITICAL PRINCIPLES

**These are non-negotiable for production dashboards:**

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

### 1. Grid System (6-Column, NOT 12!)

#### ⚠️ ALWAYS Use 6-Column Grid (NOT 12!)

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

#### Grid Layout Patterns

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

#### Common Height Values

| Widget Type | Height |
|------------|--------|
| Filters | 1-2 |
| KPI Counters | 2 |
| Charts (standard) | 6 |
| Charts (large) | 9 |
| Tables | 6+ |

---

### 2. Widget-Query Column Alignment

**MUST:** Widget `fieldName` exactly matches query output alias.

**Common Mismatches:**
- Widget expects `total_queries`, query returns `query_count` → Alias as `total_queries`
- Widget expects `warehouse_name`, query returns `compute_type` → Alias as `warehouse_name`
- Widget expects `unique_users`, query returns `distinct_users` → Alias as `unique_users`

**Validation:** Use `validate_widget_encodings.py` script before deployment.

---

### 3. Number Formatting

**MUST:** Return raw numbers, let widgets format them.

**Rules:**
- Percentages: Return 0-1 decimal (e.g., `0.85` for 85%)
- Currency: Return raw numeric (e.g., `1234.56` for $1,234.56)
- Never use `FORMAT_NUMBER()` or string concatenation in queries

**Example:**
```sql
-- ✅ CORRECT - Return raw decimal
SELECT 
  COUNT(CASE WHEN status = 'success' THEN 1 END) * 1.0 / COUNT(*) AS success_rate
FROM job_runs
-- Returns: 0.85 → Widget displays as "85%"

-- ❌ WRONG - Formatted string
SELECT 
  CONCAT(ROUND(success_count * 100.0 / total_count, 2), '%') AS success_rate
FROM job_runs
-- Returns: "85.00%" → Widget cannot parse
```

---

### 4. Parameter Configuration

**MUST:** Define ALL parameters in dataset's `parameters` array.

#### Time Range Pattern

```json
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
```

**SQL Access:**
```sql
WHERE date BETWEEN :time_range.min AND :time_range.max
```

#### Date Parameters (Static Dates)

##### ✅ Correct: DATE with Static Values

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

##### ❌ Wrong: DATETIME with Dynamic Expressions

```json
// This will NOT work
{
  "dataType": "DATETIME",
  "values": [{"value": "now-12M/M"}]
}
```

---

### 5. Monitoring Table Schema

**MUST:** Use correct access patterns for monitoring tables.

#### Window Struct

- Use `window.start` not `window_start`
- Access as `window.start AS window_start`

#### Generic Metrics

- Use `CASE` pivot on `column_name` field
- Pattern: `MAX(CASE WHEN column_name = 'metric_name' THEN avg END) AS metric_name`

#### Custom Drift Metrics

- Stored as **direct columns** (not in `avg_delta`)
- Filter: `WHERE column_name = ':table' AND drift_type = 'CONSECUTIVE'`

**Complete Example:**
```sql
-- Generic metrics from profile table
SELECT 
  window.start AS window_start,
  MAX(CASE WHEN column_name = 'row_count' THEN avg END) AS avg_row_count,
  MAX(CASE WHEN column_name = 'null_count' THEN avg END) AS avg_null_count
FROM ${catalog}.${gold_schema}_monitoring.fact_usage_profile_metrics
WHERE window.start BETWEEN :time_range.min AND :time_range.max
  AND slice_key IS NULL
GROUP BY window.start
ORDER BY window.start

-- Custom drift metrics (direct columns)
SELECT 
  window.start AS window_start,
  success_rate_drift,
  cost_per_dbu_drift
FROM ${catalog}.${gold_schema}_monitoring.fact_usage_drift_metrics
WHERE column_name = ':table' 
  AND drift_type = 'CONSECUTIVE'
  AND window.start BETWEEN :time_range.min AND :time_range.max
ORDER BY window.start
```

---

### 6. Chart Scale Properties

**MUST:** Add explicit `scale` to chart encodings.

#### Required Scales

**Pie Charts:**
- `color.scale: categorical`
- `angle.scale: quantitative`

**Bar Charts:**
- `x.scale: categorical`
- `y.scale: quantitative`

**Line Charts:**
- `x.scale: temporal`
- `y.scale: quantitative`
- `color.scale: categorical` (for multi-series)

**Area Charts:**
- `x.scale: temporal`
- `y.scale: quantitative`
- `color.scale: categorical` (for multi-series)

---

## Complete Widget Specifications

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
          "fieldName": "total_revenue",
          "displayName": "Total Revenue",
          "booleanValues": ["False", "True"]
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

---

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

---

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

---

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

---

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

---

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

## Dashboard Structure Patterns

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
        // Widgets go here (see widget examples above)
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

### Global Filters Page

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

## Query Patterns & Best Practices

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

### Pattern: Multi-Series Charts

Use `UNION ALL` to combine series:

```sql
SELECT date, 'Average' AS metric, AVG(value) AS value FROM table GROUP BY date
UNION ALL
SELECT date, 'P95' AS metric, PERCENTILE_APPROX(value, 0.95) AS value FROM table GROUP BY date
ORDER BY date, metric
```

**Widget Encoding:**
```json
{
  "x": { "fieldName": "date", "scale": { "type": "temporal" } },
  "y": { "fieldName": "value", "scale": { "type": "quantitative" } },
  "color": { "fieldName": "metric", "scale": { "type": "categorical" } }
}
```

### Pattern: Stacked Area Charts

Use `stack: "zero"` in y encoding:

```json
{
  "y": {
    "fieldName": "run_count",
    "scale": { "type": "quantitative" },
    "stack": "zero"  // CRITICAL for stacking
  }
}
```

---

## System Tables Reference

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

## Core Patterns (Deployment-Ready)

### Variable Substitution

**NEVER hardcode schemas.** Always use variables:

```sql
-- ✅ CORRECT
FROM ${catalog}.${gold_schema}.fact_usage
FROM ${catalog}.${gold_schema}_monitoring.fact_usage_profile_metrics

-- ❌ WRONG
FROM prashanth_catalog.gold.fact_usage
```

**Substitution in Python:**
```python
json_str = json_str.replace('${catalog}', catalog)
json_str = json_str.replace('${gold_schema}', gold_schema)
```

---

### UPDATE-or-CREATE Deployment

**Pattern:** Use Workspace Import API with `overwrite: true`

**Benefits:**
- Preserves dashboard URLs and permissions
- Single code path for CREATE and UPDATE
- No manual dashboard creation required

**Implementation:** See `scripts/deploy_dashboard.py`

---

### Pre-Deployment Validation

**Strategy:** Validate queries with `SELECT LIMIT 1` before deployment

**Benefits:**
- 90% reduction in dev loop time
- Catches ALL errors at once (not one-by-one)
- Validates runtime errors (not just syntax)

**Scripts:**
- `validate_dashboard_queries.py` - SQL validation
- `validate_widget_encodings.py` - Widget-query alignment

---

## Implementation Guide

### Phase-by-Phase Checklist

#### Phase 1: Planning (30 min)

- [ ] Identify KPIs to display
- [ ] List required filters (date, dimensions)
- [ ] Plan page structure and layout
- [ ] Sketch widget placement (grid positions)

#### Phase 2: Datasets (30 min)

- [ ] Create dataset for each unique query
- [ ] Add "All" option to filter datasets
- [ ] Handle NULL values with COALESCE
- [ ] Test queries in SQL editor first

#### Phase 3: Widgets (1-2 hours)

- [ ] Create KPI counters (version 2)
- [ ] Create charts (version 3)
- [ ] Create tables (version 1)
- [ ] Create filter widgets (version 2)
- [ ] Position using 6-column grid

#### Phase 4: Parameters (15 min)

- [ ] Add date parameters (DATE type, static defaults)
- [ ] Link parameters to dataset queries
- [ ] Test parameter binding

#### Phase 5: Styling (15 min)

- [ ] Apply Databricks theme colors
- [ ] Add titles and descriptions to all widgets
- [ ] Verify consistent formatting

#### Phase 6: Testing (30 min)

- [ ] Import dashboard JSON
- [ ] Test all filters
- [ ] Verify widget snapping (6-column grid)
- [ ] Check data accuracy

---

### Verification Checklist

#### Pre-Deployment

- [ ] SQL Validation passed - All queries return results without error
- [ ] Widget Encoding Validation passed - All fieldNames match query aliases
- [ ] Git diff reviewed - No accidental deletions or regressions
- [ ] Local testing done - Validated in dev environment

#### Widget-Query Alignment

- [ ] Widget `fieldName` matches query output alias exactly
- [ ] Format type matches expected value type (raw numbers for percent/currency)
- [ ] All parameters are defined in dataset's `parameters` array
- [ ] Time range uses correct access pattern (`:time_range.min`, `:time_range.max`)

#### Monitoring Query Validation

- [ ] Uses `window.start` not `window_start`
- [ ] Custom AGGREGATE/DERIVED metrics selected as direct columns
- [ ] Schema is `${catalog}.${gold_schema}_monitoring`
- [ ] Includes `WHERE column_name = ':table' AND slice_key IS NULL`

#### Chart Validation

- [ ] Pie charts: `color.scale: categorical`, `angle.scale: quantitative`
- [ ] Bar charts: `x.scale: categorical`, `y.scale: quantitative`
- [ ] Table widgets: Uses `version: 2`, no invalid properties

#### Before Deploying Dashboard

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

## Scripts & Automation

### deploy_dashboard.py

UPDATE-or-CREATE deployment with variable substitution:

```python
from scripts.deploy_dashboard import deploy_dashboards
deploy_dashboards(workspace_client, dashboard_dir, catalog, gold_schema, warehouse_id)
```

### validate_dashboard_queries.py

Pre-deployment SQL validation:

```bash
python scripts/validate_dashboard_queries.py
```

Catches: `UNRESOLVED_COLUMN`, `TABLE_OR_VIEW_NOT_FOUND`, `UNBOUND_SQL_PARAMETER`, `DATATYPE_MISMATCH`

### validate_widget_encodings.py

Widget-query alignment validation:

```bash
python scripts/validate_widget_encodings.py
```

Catches: Column alias mismatches, missing columns

---

## Assets & Templates

### dashboard-template.json

Starter dashboard JSON with dataset, time range parameter, KPI widget, and page layout. Copy and modify for new dashboards.

Location: `assets/templates/dashboard-template.json`

### Jobs System Tables Dashboard (Production Example)

**Complete, production-ready dashboard** demonstrating best practices for Databricks System Tables monitoring. This real-world example showcases:

- ✅ **System Tables Integration** - Queries `system.lakeflow.jobs`, `system.lakeflow.job_task_run_timeline`, `system.compute.clusters`
- ✅ **Proper JOIN Patterns** - Demonstrates correct workspace_id + entity_id JOIN requirements
- ✅ **SCD2 Handling** - Shows QUALIFY pattern for latest records from SCD2 tables
- ✅ **Widget Configuration** - All widget types properly configured (counters, bar charts, line charts, tables)
- ✅ **6-Column Grid Layout** - Correct positioning with 6-column grid system
- ✅ **Parameter Configuration** - Time range parameters with proper DATE type
- ✅ **Variable Substitution** - Uses ${catalog} and ${schema} patterns
- ✅ **Multi-Page Dashboard** - Overview + Global Filters pages
- ✅ **Number Formatting** - Raw numbers for proper widget formatting
- ✅ **Field Name Verification** - Uses actual system table column names (not assumptions)

**Use this as a reference for:**
- Building system tables dashboards
- Understanding complete dashboard JSON structure
- Seeing all patterns from this skill in action
- Learning proper widget-query alignment
- Implementing multi-page layouts

Location: `references/Jobs System Tables Dashboard.lvdash.json`

**Dashboard Includes:**
- Job success rate and failure tracking
- Task execution timeline and durations
- Cluster utilization and DBR version distribution
- Job run history with filters by workspace and date range
- Detailed tables for job configuration and task details

---

## Common Mistakes & Error Messages

### Common Mistakes to Avoid

#### ❌ Mistake 1: 12-Column Grid

```json
// Wrong - widget won't position correctly
{"width": 6}  // This is FULL width, not half!
```

#### ❌ Mistake 2: Wrong Widget Version

```json
// Wrong - KPIs must use version 2
"version": 3,
"widgetType": "counter"
```

#### ❌ Mistake 3: DATETIME Parameters

```json
// Wrong - use DATE type
"dataType": "DATETIME"
```

#### ❌ Mistake 4: Missing "All" Option

```sql
-- Wrong - no way to clear filter
SELECT DISTINCT store_name FROM stores
```

#### ❌ Mistake 5: Assuming Field Names

```sql
-- Wrong - job_name doesn't exist in this table!
SELECT job_name FROM system.lakeflow.job_task_run_timeline
```

---

### Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| "no fields to visualize" | Widget `fieldName` doesn't match query alias | Align column aliases |
| "UNRESOLVED_COLUMN" | Column doesn't exist | Check schema, use correct column |
| "UNBOUND_SQL_PARAMETER" | Parameter not defined | Add to `parameters` array |
| "Unable to render visualization" | Pie chart missing scale | Add `scale` to encodings |
| Empty chart with data | Wrong number format | Return raw numbers, not strings |
| 0% or 0 in counter | Formatted string or wrong percentage | Return 0-1 decimal for percent |

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

## Key Principles Summary

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

## Reference Documentation

Detailed patterns and examples are organized in reference files:

- **[Dashboard JSON Reference](references/dashboard-json-reference.md)** - JSON structure, page layouts, dataset configuration, variable substitution, widget versions, naming conventions
- **[Widget Patterns](references/widget-patterns.md)** - Widget-query alignment, number formatting, parameters, chart configurations, multi-series charts, error fixes
- **[Deployment Guide](references/deployment-guide.md)** - UPDATE-or-CREATE pattern, variable substitution, SQL validation, monitoring queries, best practices, checklists
- **[Jobs System Tables Dashboard](references/Jobs%20System%20Tables%20Dashboard.lvdash.json)** - Complete production example demonstrating all patterns from this skill with System Tables integration

---

## References

### Official Documentation

- [AI/BI Lakeview Dashboards](https://docs.databricks.com/dashboards/lakeview/)
- [System Tables Overview](https://docs.databricks.com/aws/en/admin/system-tables/)
- [Jobs System Tables](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
- [Compute System Tables](https://docs.databricks.com/aws/en/admin/system-tables/compute)
- [Lakehouse Monitoring](https://docs.databricks.com/lakehouse-monitoring/)
- [Workspace Dashboard API](https://learn.microsoft.com/en-us/azure/databricks/dashboards/tutorials/workspace-dashboard-api)

### Related Skills

- `lakehouse-monitoring-comprehensive` - Monitoring setup patterns
- `sql-alerting-patterns` - SQL alert configuration
- `metric-views-patterns` - Semantic layer metric views

---

## Summary

### What to Create

1. Dashboard JSON file with proper structure
2. Datasets (queries for each widget)
3. Pages with widget layouts
4. Parameters (date filters)
5. Global Filters page

### Critical Rules

- 6-column grid (NOT 12!)
- KPIs: v2, Charts: v3, Tables: v1
- DATE type for parameters (not DATETIME)
- Include Global Filters page
- Verify system table field names
- Return raw numbers for formatting
- Match widget fieldNames to query aliases

### Time Estimate

2-4 hours for complete dashboard

### Next Action

1. Fill out Project Planning Template
2. Create datasets with validated queries
3. Build widgets with correct specifications
4. Test in Databricks
5. Deploy via API with validation

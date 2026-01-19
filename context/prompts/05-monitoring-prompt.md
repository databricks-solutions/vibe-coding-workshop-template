# Lakehouse Monitoring Creation Prompt

## 🚀 Quick Start (2 hours)

**Goal:** Automated data quality and drift monitoring for critical Gold tables

**What You'll Create:**
1. `lakehouse_monitoring.py` - Creates monitors with custom metrics via API
2. `monitoring_job.yml` - Asset Bundle job

**Fast Track:**
```python
# Pattern: 1 monitor per critical table
from databricks.sdk import WorkspaceClient

# 1. Define custom metrics (AGGREGATE → DERIVED → DRIFT)
custom_metrics = [
    {"type": "aggregate", "name": "total_revenue", "definition": "SUM(net_revenue)", "input_columns": [":table"]},
    {"type": "derived", "name": "avg_revenue", "definition": "{{total_revenue}} / NULLIF({{row_count}}, 0)", "input_columns": [":table"]},
    {"type": "drift", "name": "revenue_change", "definition": "{{total_revenue}}", "input_columns": [":table"]}
]

# 2. Create monitor
w.quality_monitors.create(
    table_name=f"{catalog}.{schema}.fact_sales_daily",
    assets_dir=f"/Workspace/Users/{user}/monitors/fact_sales_daily",
    output_schema_name=f"{catalog}.{schema}",
    custom_metrics=custom_metrics
)

# 3. Wait for refresh (async operation!)
```

**Critical Patterns:**
- ⚠️ **ALL related metrics MUST use SAME `input_columns`** (e.g., all use `[":table"]`)
- ⚠️ **DERIVED can ONLY reference metrics in SAME `column_name` row** 
- ⚠️ **Wait for async refresh** before querying metrics (use `wait_for_refresh()`)
- ⚠️ **Custom metrics stored in profile table** at `{output_schema}_{table_name}_profile_metrics`

**Metric Query Pattern:**
```sql
-- AGGREGATE & DERIVED: column_name = ':table'
SELECT granularity, window, total_revenue, avg_revenue
FROM {output_schema}_{table}_profile_metrics
WHERE column_name = ':table'  -- Table-level metrics

-- DRIFT: separate table
SELECT * FROM {output_schema}_{table}_drift_metrics
WHERE drift_type = 'CONSECUTIVE'
```

**Output:** Automated monitoring with dashboards in `monitors/` folder

📖 **Full guide below** for detailed implementation →

---

## Quick Reference

**Use this prompt when setting up Databricks Lakehouse Monitoring for Gold layer tables.**

---

## 📋 Your Requirements (Fill These In First)

**Before setting up monitoring, identify critical tables and metrics:**

### Project Context
- **Project Name:** _________________ (e.g., retail_analytics, patient_outcomes)
- **Gold Catalog.Schema:** _________________ (e.g., my_catalog.my_project_gold)
- **Monitoring Owner:** _________________ (team/email for alerts)

### Tables to Monitor (2-5 critical tables)

| # | Table Name | Type | Monitor Priority | Alert On |
|---|-----------|------|------------------|----------|
| 1 | fact_sales_daily | Fact | High | Row count drop > 10%, Revenue anomaly |
| 2 | dim_customer | Dimension | Medium | New PII detected, SCD2 version explosion |
| 3 | ____________ | ______ | _______ | _________________________ |
| 4 | ____________ | ______ | _______ | _________________________ |

**Monitor Priority:**
- **High:** Core business tables, real-time decisions, revenue-impacting
- **Medium:** Important but not critical, daily reports
- **Low:** Reference data, rarely changes

### Custom Metrics by Table

**Table: _________________ (Fact)**

| Metric Type | Metric Name | Definition | Input Columns |
|------------|-------------|------------|---------------|
| AGGREGATE | total_daily_revenue | SUM(net_revenue) | :table |
| AGGREGATE | total_transactions | SUM(transaction_count) | :table |
| DERIVED | avg_transaction_value | {{total_daily_revenue}} / NULLIF({{total_transactions}}, 0) | :table |
| DRIFT | revenue_percent_change | {{total_daily_revenue}} | :table |

**Table: _________________ (Dimension)**

| Metric Type | Metric Name | Definition | Input Columns |
|------------|-------------|------------|---------------|
| AGGREGATE | total_records | COUNT(*) | :table |
| AGGREGATE | distinct_entities | COUNT(DISTINCT entity_id) | :table |
| DERIVED | versions_per_entity | {{total_records}} / NULLIF({{distinct_entities}}, 0) | :table |

**⚠️ CRITICAL Pattern:** For table-level business KPIs, **ALWAYS use `input_columns=[":table"]` for ALL related metrics** (AGGREGATE, DERIVED, DRIFT). This ensures they're stored in the same row and can be cross-referenced.

### Metric Categories

**Choose what to monitor:**

**For Fact Tables:**
- [ ] Revenue/Amount metrics (daily totals)
- [ ] Volume metrics (transaction counts, units sold)
- [ ] Averages (transaction value, price per unit)
- [ ] Rates (return rate, conversion rate)
- [ ] Drift detection (identify anomalies)

**For Dimension Tables:**
- [ ] Row counts (total records)
- [ ] Distinct counts (unique entities)
- [ ] SCD2 checks (versions per entity, current records)
- [ ] Data freshness (last updated timestamp)

### Alert Strategy

| Table | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| fact_sales_daily | row_count | < 90% of 7-day avg | Alert team |
| fact_sales_daily | total_daily_revenue | > 2 std dev from mean | Investigate |
| dim_customer | distinct_customers | Sudden 20% drop | Alert immediately |
| _____________ | ______________ | _________________ | _____________ |

---

## Input Required Summary
- Gold layer tables to monitor (fact tables, critical dimensions)
- Custom business metrics to track
- Alert thresholds

**Output:** Lakehouse Monitors with custom metrics, profile metrics, and drift detection.

**Time Estimate:** 2 hours

---

## Core Philosophy: Proactive Data Quality Monitoring

**⚠️ CRITICAL PRINCIPLE:**

Lakehouse Monitoring provides **automated data quality tracking** for production tables:

- ✅ **Profile Metrics** (row count, null rates, min/max/avg)
- ✅ **Custom Metrics** (business KPIs like revenue, units, transaction count)
- ✅ **Drift Detection** (identify data distribution changes)
- ✅ **Async Initialization** (wait 15 minutes before querying)
- ✅ **Complete Cleanup** (delete monitors before re-creating)
- ❌ **Silent Success** (jobs must fail if monitors fail)

**Why This Matters:**
- Early detection of data quality issues
- Automated anomaly detection
- Historical trending of data characteristics
- Production-ready observability

---

## Step 1: Design Monitoring Strategy

### Monitoring Checklist

- [ ] **Tables to Monitor:** Which Gold tables are business-critical?
- [ ] **Custom Metrics:** What business KPIs should be tracked?
  - Revenue, units, transactions (for fact tables)
  - Row counts, distinct counts (for dimensions)
- [ ] **Metric Grain:** Table-level (`:table`) or per-column?
- [ ] **Drift Detection:** Which metrics need drift alerts?

### Metric Types

| Type | Purpose | Example | Storage Pattern |
|------|---------|---------|----------------|
| **AGGREGATE** | Sum/count business KPIs | total_daily_revenue | `:table` input_columns |
| **DERIVED** | Calculate from AGGREGATE | revenue_per_transaction | `:table` input_columns |
| **DRIFT** | Track changes over time | revenue_percent_change | `:table` input_columns |

**⚠️ CRITICAL:** For table-level business KPIs, **ALWAYS use `input_columns=[":table"]` for ALL related metrics** (AGGREGATE, DERIVED, DRIFT). This ensures they're stored in the same row and can be cross-referenced.

---

## Step 2: Lakehouse Monitoring Setup Script

### File: `lakehouse_monitoring.py`

```python
# Databricks notebook source

"""
{Project} Gold Layer - Lakehouse Monitoring Setup

Creates Lakehouse Monitors for Gold layer tables with custom business metrics.

Critical Patterns:
- Complete cleanup (delete existing monitors)
- Async initialization (wait 15 minutes)
- Error handling (jobs must fail if monitors fail)
- Table-level metrics use input_columns=[":table"]

Usage:
  databricks bundle run setup_lakehouse_monitoring -t dev
"""

import argparse
import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import MonitorInfoStatus
from pyspark.sql import SparkSession


def delete_existing_monitor(w: WorkspaceClient, table_name: str):
    """
    Delete existing monitor if it exists.
    
    Critical: Always delete before creating new monitor to avoid conflicts.
    """
    try:
        print(f"  Checking for existing monitor on {table_name}...")
        existing = w.quality_monitors.get(table_name=table_name)
        
        if existing:
            print(f"  Deleting existing monitor...")
            w.quality_monitors.delete(table_name=table_name)
            print(f"  ✓ Deleted existing monitor")
            time.sleep(5)  # Brief pause after deletion
    except Exception as e:
        if "does not exist" not in str(e).lower():
            print(f"  Warning: {str(e)}")


def create_monitor_with_custom_metrics(
    w: WorkspaceClient,
    table_name: str,
    custom_metrics: list
):
    """
    Create Lakehouse Monitor with custom business metrics.
    
    Args:
        w: Databricks WorkspaceClient
        table_name: Fully qualified table name (catalog.schema.table)
        custom_metrics: List of custom metric definitions
    
    Returns:
        Monitor info or None if creation failed
    """
    print(f"\nCreating monitor for {table_name}...")
    
    # Delete existing monitor first
    delete_existing_monitor(w, table_name)
    
    try:
        # Create monitor
        monitor_info = w.quality_monitors.create(
            table_name=table_name,
            assets_dir=f"/Workspace/Users/{w.current_user.me().user_name}/lakehouse_monitoring",
            output_schema_name=table_name.split('.')[1],  # Use same schema as table
            custom_metrics=custom_metrics
        )
        
        print(f"✓ Monitor created for {table_name}")
        print(f"  Monitor ID: {monitor_info.monitor_name}")
        print(f"  Status: {monitor_info.status}")
        print(f"  Dashboard ID: {monitor_info.dashboard_id}")
        
        return monitor_info
        
    except Exception as e:
        print(f"✗ Error creating monitor for {table_name}: {str(e)}")
        return None


def wait_for_monitor_initialization(
    w: WorkspaceClient,
    table_name: str,
    timeout_minutes: int = 20
):
    """
    Wait for monitor to initialize (profile and custom metrics populated).
    
    Critical: Monitors need 15+ minutes to initialize before querying.
    """
    print(f"\nWaiting for {table_name} monitor initialization...")
    print(f"  This typically takes 15-20 minutes...")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    check_interval = 60  # Check every minute
    
    while (time.time() - start_time) < timeout_seconds:
        try:
            monitor_info = w.quality_monitors.get(table_name=table_name)
            
            if monitor_info.status == MonitorInfoStatus.MONITOR_STATUS_ACTIVE:
                elapsed_minutes = (time.time() - start_time) / 60
                print(f"✓ Monitor active after {elapsed_minutes:.1f} minutes")
                return True
            
            elapsed = int((time.time() - start_time) / 60)
            print(f"  Status: {monitor_info.status} (waited {elapsed}/{timeout_minutes} min)")
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"  Error checking status: {str(e)}")
            time.sleep(check_interval)
    
    print(f"✗ Timeout waiting for monitor initialization")
    return False


# ============================================================================
# MONITOR DEFINITIONS
# ============================================================================

def create_fact_sales_daily_monitor(
    w: WorkspaceClient,
    catalog: str,
    schema: str
):
    """
    Create monitor for fact_sales_daily with business metrics.
    
    Custom Metrics:
    - AGGREGATE: Sum of revenue, units, transactions (daily totals)
    - DERIVED: Calculated metrics (avg transaction value, avg unit price)
    - DRIFT: Percent change detection for key metrics
    
    Critical: ALL related metrics use input_columns=[":table"] for cross-referencing.
    """
    table_name = f"{catalog}.{schema}.fact_sales_daily"
    
    custom_metrics = [
        # ========================================
        # AGGREGATE METRICS (sum of daily totals)
        # ========================================
        {
            "type": "AGGREGATE",
            "name": "total_daily_revenue",
            "input_columns": [":table"],  # ✅ Table-level metric
            "definition": "SUM(net_revenue)",
            "output_data_type": "double"
        },
        {
            "type": "AGGREGATE",
            "name": "total_daily_units",
            "input_columns": [":table"],
            "definition": "SUM(net_units)",
            "output_data_type": "double"
        },
        {
            "type": "AGGREGATE",
            "name": "total_transactions",
            "input_columns": [":table"],
            "definition": "SUM(transaction_count)",
            "output_data_type": "double"
        },
        {
            "type": "AGGREGATE",
            "name": "total_return_amount",
            "input_columns": [":table"],
            "definition": "SUM(return_amount)",
            "output_data_type": "double"
        },
        
        # ========================================
        # DERIVED METRICS (calculated from AGGREGATE)
        # ========================================
        {
            "type": "DERIVED",
            "name": "avg_transaction_value",
            "input_columns": [":table"],  # ✅ Same as AGGREGATE for cross-ref
            "definition": "{{total_daily_revenue}} / NULLIF({{total_transactions}}, 0)",
            "output_data_type": "double"
        },
        {
            "type": "DERIVED",
            "name": "avg_unit_price",
            "input_columns": [":table"],
            "definition": "{{total_daily_revenue}} / NULLIF({{total_daily_units}}, 0)",
            "output_data_type": "double"
        },
        {
            "type": "DERIVED",
            "name": "return_rate_pct",
            "input_columns": [":table"],
            "definition": "({{total_return_amount}} / NULLIF({{total_daily_revenue}} + {{total_return_amount}}, 0)) * 100",
            "output_data_type": "double"
        },
        
        # ========================================
        # DRIFT METRICS (detect changes)
        # ========================================
        {
            "type": "DRIFT",
            "name": "revenue_percent_change",
            "input_columns": [":table"],  # ✅ Same as AGGREGATE for cross-ref
            "definition": "{{total_daily_revenue}}",
            "output_data_type": "double"
        },
        {
            "type": "DRIFT",
            "name": "units_percent_change",
            "input_columns": [":table"],
            "definition": "{{total_daily_units}}",
            "output_data_type": "double"
        }
    ]
    
    return create_monitor_with_custom_metrics(w, table_name, custom_metrics)


def create_dim_store_monitor(
    w: WorkspaceClient,
    catalog: str,
    schema: str
):
    """
    Create monitor for dim_store (dimension table).
    
    Custom Metrics:
    - Row counts
    - Distinct store counts
    - SCD Type 2 validity checks
    """
    table_name = f"{catalog}.{schema}.dim_store"
    
    custom_metrics = [
        {
            "type": "AGGREGATE",
            "name": "total_store_records",
            "input_columns": [":table"],
            "definition": "COUNT(*)",
            "output_data_type": "double"
        },
        {
            "type": "AGGREGATE",
            "name": "distinct_stores",
            "input_columns": [":table"],
            "definition": "COUNT(DISTINCT store_number)",
            "output_data_type": "double"
        },
        {
            "type": "AGGREGATE",
            "name": "current_records",
            "input_columns": [":table"],
            "definition": "SUM(CASE WHEN is_current = true THEN 1 ELSE 0 END)",
            "output_data_type": "double"
        },
        {
            "type": "DERIVED",
            "name": "versions_per_store",
            "input_columns": [":table"],
            "definition": "{{total_store_records}} / NULLIF({{distinct_stores}}, 0)",
            "output_data_type": "double"
        }
    ]
    
    return create_monitor_with_custom_metrics(w, table_name, custom_metrics)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main entry point for Lakehouse Monitoring setup.
    
    Creates monitors for critical Gold tables with custom metrics.
    Waits for initialization before returning.
    """
    parser = argparse.ArgumentParser(description="Setup Lakehouse Monitoring")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--gold_schema", required=True)
    
    args = parser.parse_args()
    
    # Initialize Databricks SDK
    w = WorkspaceClient()
    
    print("=" * 80)
    print("LAKEHOUSE MONITORING SETUP")
    print("=" * 80)
    print(f"Catalog: {args.catalog}")
    print(f"Schema: {args.gold_schema}")
    print("=" * 80)
    
    try:
        # Track created monitors
        monitors_created = []
        monitors_failed = []
        
        # Create monitors
        print("\n--- Creating Monitors ---")
        
        result1 = create_fact_sales_daily_monitor(w, args.catalog, args.gold_schema)
        if result1:
            monitors_created.append("fact_sales_daily")
        else:
            monitors_failed.append("fact_sales_daily")
        
        result2 = create_dim_store_monitor(w, args.catalog, args.gold_schema)
        if result2:
            monitors_created.append("dim_store")
        else:
            monitors_failed.append("dim_store")
        
        # ... more monitors
        
        print("\n" + "=" * 80)
        print(f"Monitor Creation Summary:")
        print(f"  Created: {len(monitors_created)} ({', '.join(monitors_created)})")
        print(f"  Failed: {len(monitors_failed)} ({', '.join(monitors_failed) if monitors_failed else 'None'})")
        print("=" * 80)
        
        if monitors_failed:
            raise RuntimeError(
                f"Failed to create {len(monitors_failed)} monitor(s): "
                f"{', '.join(monitors_failed)}"
            )
        
        print("\n✓ All monitors created successfully!")
        print("\n⚠️  IMPORTANT: Monitors need 15-20 minutes to initialize.")
        print("   Run wait_for_monitor_initialization.py before querying metrics.")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
```

---

## Step 3: Wait for Monitor Initialization

### File: `wait_for_monitor_initialization.py`

```python
# Databricks notebook source

"""
Wait for Lakehouse Monitor Initialization

Waits for monitors to reach ACTIVE status before proceeding.

Usage:
  databricks bundle run wait_for_monitor_initialization -t dev
"""

import argparse
import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import MonitorInfoStatus


def wait_for_all_monitors(
    w: WorkspaceClient,
    catalog: str,
    schema: str,
    table_names: list,
    timeout_minutes: int = 20
):
    """Wait for multiple monitors to initialize."""
    print(f"\nWaiting for {len(table_names)} monitor(s) to initialize...")
    print(f"Timeout: {timeout_minutes} minutes\n")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    check_interval = 60
    
    fully_qualified_tables = [f"{catalog}.{schema}.{t}" for t in table_names]
    pending_tables = set(fully_qualified_tables)
    
    while pending_tables and (time.time() - start_time) < timeout_seconds:
        elapsed_minutes = (time.time() - start_time) / 60
        
        for table in list(pending_tables):
            try:
                monitor_info = w.quality_monitors.get(table_name=table)
                
                if monitor_info.status == MonitorInfoStatus.MONITOR_STATUS_ACTIVE:
                    print(f"✓ {table} - ACTIVE")
                    pending_tables.remove(table)
                else:
                    print(f"  {table} - {monitor_info.status} (waited {elapsed_minutes:.1f} min)")
                    
            except Exception as e:
                print(f"  {table} - Error: {str(e)}")
        
        if pending_tables:
            time.sleep(check_interval)
    
    if pending_tables:
        print(f"\n✗ Timeout: {len(pending_tables)} monitor(s) still pending")
        return False
    else:
        print(f"\n✓ All monitors active!")
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    
    args = parser.parse_args()
    
    w = WorkspaceClient()
    
    # List of tables with monitors
    monitored_tables = [
        "fact_sales_daily",
        "dim_store",
        # ... more tables
    ]
    
    success = wait_for_all_monitors(w, args.catalog, args.schema, monitored_tables)
    
    if not success:
        raise RuntimeError("Monitor initialization timeout")


if __name__ == "__main__":
    main()
```

---

## Step 4: Query Monitoring Metrics

### Example Queries

```sql
-- Profile metrics (row count, null rates, etc.)
SELECT
  window.start,
  window.end,
  column_name,
  null_count,
  row_count,
  (null_count / row_count) * 100 as null_percentage
FROM {catalog}.{schema}__tables__fact_sales_daily_profile_metrics
WHERE column_name = ':table'
ORDER BY window.start DESC
LIMIT 10;

-- Custom AGGREGATE metrics (table-level KPIs)
SELECT
  window.start,
  window.end,
  granularity,
  column_name,
  metric_name,
  metric_value
FROM {catalog}.{schema}__tables__fact_sales_daily_profile_metrics
WHERE 
  column_name = ':table'
  AND metric_name IN ('total_daily_revenue', 'total_transactions')
ORDER BY window.start DESC, metric_name;

-- DERIVED metrics (calculated from AGGREGATE)
SELECT
  window.start,
  avg_transaction_value.metric_value as avg_transaction_value,
  avg_unit_price.metric_value as avg_unit_price,
  return_rate_pct.metric_value as return_rate_pct
FROM {catalog}.{schema}__tables__fact_sales_daily_profile_metrics avg_transaction_value
INNER JOIN {catalog}.{schema}__tables__fact_sales_daily_profile_metrics avg_unit_price
  ON avg_transaction_value.window.start = avg_unit_price.window.start
  AND avg_transaction_value.column_name = avg_unit_price.column_name
INNER JOIN {catalog}.{schema}__tables__fact_sales_daily_profile_metrics return_rate_pct
  ON avg_transaction_value.window.start = return_rate_pct.window.start
  AND avg_transaction_value.column_name = return_rate_pct.column_name
WHERE
  avg_transaction_value.column_name = ':table'
  AND avg_transaction_value.metric_name = 'avg_transaction_value'
  AND avg_unit_price.metric_name = 'avg_unit_price'
  AND return_rate_pct.metric_name = 'return_rate_pct'
ORDER BY avg_transaction_value.window.start DESC
LIMIT 10;

-- DRIFT metrics (percent change detection)
SELECT
  window.start,
  metric_name,
  metric_value as current_value,
  DRIFT_TYPE,
  PERCENT_CHANGE
FROM {catalog}.{schema}__tables__fact_sales_daily_drift_metrics
WHERE column_name = ':table'
ORDER BY window.start DESC, metric_name;
```

---

## Implementation Checklist

### Phase 1: Design (30 min)
- [ ] Identify tables to monitor (2-5 critical Gold tables)
- [ ] Define custom metrics for each table
- [ ] Decide metric grain (`:table` or per-column)
- [ ] Define drift detection requirements

### Phase 2: Setup Script (1 hour)
- [ ] Create `lakehouse_monitoring.py`
- [ ] Define monitor functions for each table
- [ ] Implement complete cleanup (delete existing)
- [ ] Add error handling (raise on failure)
- [ ] Use `:table` for table-level business KPIs

### Phase 3: Initialization Wait (30 min)
- [ ] Create `wait_for_monitor_initialization.py`
- [ ] Implement async wait logic (20 min timeout)
- [ ] Deploy & run setup
- [ ] Wait for monitors to activate

### Phase 4: Validation (30 min)
- [ ] Query profile metrics
- [ ] Query custom metrics
- [ ] Verify metric storage pattern (`:table` rows)
- [ ] Test drift detection

---

## Key Principles

### 1. Table-Level Business KPIs Pattern
- ✅ **ALL related metrics use `input_columns=[":table"]`**
- ✅ AGGREGATE, DERIVED, and DRIFT all in same `:table` row
- ✅ Enables cross-referencing in single query
- ❌ Don't mix `:table` and per-column for related metrics

### 2. Complete Cleanup
- ✅ Always delete existing monitor before creating
- ✅ Brief pause (5 sec) after deletion
- ✅ Avoids conflicts and stale monitors

### 3. Async Initialization
- ✅ Wait 15-20 minutes after creation
- ✅ Poll status until ACTIVE
- ✅ Don't query metrics immediately

### 4. Error Handling
- ✅ Jobs must FAIL if monitors fail
- ✅ Track failed monitors
- ✅ Raise RuntimeError with details

---

## References

### Official Documentation
- [Lakehouse Monitoring](https://docs.databricks.com/lakehouse-monitoring/)
- [Custom Metrics](https://docs.databricks.com/lakehouse-monitoring/custom-metrics)
- [Monitoring API](https://docs.databricks.com/api/workspace/qualitymonitors)

### Framework Rules
- [lakehouse-monitoring-comprehensive.mdc](mdc:framework/rules/17-lakehouse-monitoring-comprehensive.mdc)

---

## Summary

**What to Create:**
1. `lakehouse_monitoring.py` - Monitor setup with custom metrics
2. `wait_for_monitor_initialization.py` - Async wait script
3. Query templates for dashboard integration

**Time Estimate:** 2 hours

**Next Action:** Define custom metrics, create monitors, wait for initialization





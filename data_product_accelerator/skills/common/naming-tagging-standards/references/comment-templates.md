# Comment Templates Reference

Complete templates and examples for all SQL comment formats.

## DDL Block Comments (`/* */`)

### Table Creation

```sql
/*
 * Table: dim_customer
 * Layer: Gold
 * Domain: Sales
 *
 * Purpose: Customer dimension with SCD Type 2 history tracking.
 *          Primary reference for all customer analytics.
 *
 * Grain: One row per customer per effective period.
 * Source: Silver layer silver_customers table.
 *
 * Change History:
 *   2026-02-01 - Initial creation (jsmith)
 *   2026-02-15 - Added loyalty_tier column (ajones)
 */
CREATE TABLE gold.dim_customer (...);
```

### Constraint Addition

```sql
/*
 * Constraint: pk_dim_customer
 * Type: Primary Key (NOT ENFORCED - informational only)
 * Purpose: Establishes unique identity for query optimization
 *          and semantic layer relationship discovery.
 */
ALTER TABLE gold.dim_customer
ADD CONSTRAINT pk_dim_customer
PRIMARY KEY (customer_key) NOT ENFORCED;

/*
 * Constraint: fk_orders_customer
 * Type: Foreign Key (NOT ENFORCED - informational only)
 * Purpose: Documents relationship between fact_orders and dim_customer.
 *          Used by query optimizer and Metric Views for join inference.
 */
ALTER TABLE gold.fact_orders
ADD CONSTRAINT fk_orders_customer
FOREIGN KEY (customer_key)
REFERENCES gold.dim_customer(customer_key) NOT ENFORCED;
```

### Function Creation

```sql
/*
 * Function: get_daily_sales_summary
 * Type: Table-Valued Function (TVF)
 * Domain: Sales Analytics
 *
 * Purpose: Returns daily sales summary for a date range.
 *          Optimized for Genie Space natural language queries.
 *
 * Parameters:
 *   - start_date (STRING): Start date in YYYY-MM-DD format
 *   - end_date (STRING): End date in YYYY-MM-DD format (optional)
 *
 * Returns: Pre-aggregated daily sales by store and product category.
 *
 * Usage: SELECT * FROM get_daily_sales_summary('2025-01-01', '2025-01-31')
 */
```

---

## Table COMMENT (Dual-Purpose)

### Template

```
[One-line description]. Business: [use cases, consumers, business context]. Technical: [grain, source, update frequency, key details].
```

### By Layer

**Bronze:**
```sql
COMMENT ON TABLE bronze.raw_orders IS
'Raw order events from POS system with minimal transformation. Business: Source data for order analytics, retained for audit and replay. Technical: Appended via Auto Loader, CDF enabled, 90-day retention.';
```

**Silver:**
```sql
COMMENT ON TABLE silver.orders IS
'Validated and deduplicated orders with quality expectations enforced. Business: Clean order data for downstream analytics and reporting. Technical: DLT streaming from Bronze, expect_or_drop on required fields.';
```

**Gold Dimension:**
```sql
COMMENT ON TABLE gold.dim_customer IS
'Customer dimension with SCD Type 2 history tracking for all customer attributes. Business: Primary customer reference for segmentation, lifetime value, and cohort analysis. Technical: MD5 surrogate key, is_current flag for active records, daily merge from Silver.';
```

**Gold Fact:**
```sql
COMMENT ON TABLE gold.fact_orders IS
'Daily order facts aggregated at customer-product-day grain. Business: Primary source for revenue reporting, conversion analysis, and sales dashboards. Technical: Composite PK (order_date, customer_key, product_key), incremental merge, CDF enabled.';
```

---

## Column COMMENT (Dual-Purpose)

### Template

```
[Brief definition]. Business: [how it's used, business rules]. Technical: [data type notes, source, calculation].
```

### By Column Type

**Surrogate Key:**
```sql
customer_key STRING NOT NULL
COMMENT 'Surrogate key for SCD Type 2 versioning. Business: Used for joining fact tables to this dimension. Technical: MD5 hash of customer_id + effective_from timestamp.';
```

**Business Key:**
```sql
customer_id STRING NOT NULL
COMMENT 'Natural business key identifying the customer. Business: Stable identifier used by CRM and support teams. Technical: Immutable, same across all SCD2 versions.';
```

**Measure:**
```sql
total_amount DECIMAL(18,2)
COMMENT 'Total order amount after discounts in USD. Business: Primary revenue metric for financial reporting. Technical: Calculated as SUM(quantity * unit_price * (1 - discount_pct)).';
```

**Date:**
```sql
order_date DATE NOT NULL
COMMENT 'Date when order was placed. Business: Primary time dimension for trend analysis. Technical: Truncated from order_timestamp, FK to dim_date.';
```

**Boolean Flag:**
```sql
is_current BOOLEAN NOT NULL DEFAULT TRUE
COMMENT 'Indicates if this is the current version of the record. Business: Filter to is_current=true for current state queries. Technical: Set to false when new version inserted (SCD2).';
```

**Foreign Key:**
```sql
store_key STRING NOT NULL
COMMENT 'FK to dim_store dimension. Business: Links orders to store location for geographic analysis. Technical: Must match existing store_key in dim_store.';
```

---

## TVF COMMENT (v3.0 Structured)

### Template

```sql
COMMENT '
• PURPOSE: [One-line description of what the function returns].
• BEST FOR: [Query type 1] | [Query type 2] | [Query type 3]
• NOT FOR: [What to use instead] (use [alternative] instead)
• RETURNS: [PRE-AGGREGATED or DETAIL rows]
• PARAMS: [param1 (format)], [param2 (format)]
• SYNTAX: SELECT * FROM function_name(''param1'', ''param2'')
• NOTE: [Critical usage notes - DO NOT wrap, DO NOT add GROUP BY, etc.]
'
```

### Complete Example

```sql
CREATE OR REPLACE FUNCTION gold.get_daily_cost_summary(
    start_date STRING COMMENT 'Start date (YYYY-MM-DD)',
    end_date STRING DEFAULT NULL COMMENT 'End date (YYYY-MM-DD), defaults to today'
)
RETURNS TABLE (...)
COMMENT '
• PURPOSE: Get daily cost summary by workspace and SKU for billing analysis.
• BEST FOR: Total spend by workspace | Cost breakdown by SKU | Daily cost trends
• NOT FOR: Real-time cost alerts (use get_cost_alerts TVF instead)
• RETURNS: PRE-AGGREGATED rows (one per workspace-SKU-day combination)
• PARAMS: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD, optional)
• SYNTAX: SELECT * FROM get_daily_cost_summary(''2025-01-01'', ''2025-01-31'')
• NOTE: DO NOT wrap in TABLE(). DO NOT add GROUP BY. Results are already aggregated.
'
RETURN (SELECT ...);
```

---

## Metric View COMMENT (YAML)

### Template

```yaml
comment: >
  PURPOSE: [What this metric view provides].
  BEST FOR: [Query pattern 1] | [Query pattern 2] | [Query pattern 3]
  NOT FOR: [Excluded patterns] (use [alternative])
  DIMENSIONS: [dimension1, dimension2, dimension3]
  MEASURES: [measure1, measure2, measure3]
  SOURCE: [source table] ([domain])
  JOINS: [joined dimension1], [joined dimension2]
  NOTE: [Important caveats or usage guidance].
```

### Example

```yaml
comment: >
  PURPOSE: Cost analytics for billing analysis and showback reporting.
  BEST FOR: Total spend by workspace | Cost by SKU | Tag coverage analysis |
  Serverless vs classic comparison | Daily/weekly/monthly trends
  NOT FOR: Commit tracking (use commit_tracking) | Real-time alerts (use TVF)
  DIMENSIONS: usage_date, workspace_name, sku_name, tag_team, is_serverless
  MEASURES: total_cost, total_dbus, tag_coverage_pct, serverless_pct
  SOURCE: fact_usage (billing domain)
  JOINS: dim_workspace (workspace details), dim_sku (SKU metadata)
  NOTE: Costs are list prices. Actual billed amounts may differ based on contracts.
```

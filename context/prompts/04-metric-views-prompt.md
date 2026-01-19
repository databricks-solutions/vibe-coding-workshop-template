# Metric Views Creation Prompt

## 🚀 Quick Start (1 hour)

**Goal:** Create semantic layer for natural language queries (Genie) and AI/BI dashboards

**What You'll Create:**
1. `metric_views.yaml` - Semantic definitions (dimensions, measures, joins, formats)
2. `create_metric_views.py` - Script reads YAML, creates views with `WITH METRICS LANGUAGE YAML`
3. `metric_views_job.yml` - Asset Bundle job

**Fast Track:**
```bash
# 1. Create metric_views.yaml with dimensions + measures
# 2. Deploy and run
databricks bundle run metric_views_job -t dev

# 3. Query with natural language
# Genie: "Show total revenue by store last 30 days"
```

**Critical Syntax (v1.1):**
```python
create_sql = f"""
CREATE OR REPLACE VIEW {fqn}
WITH METRICS         -- ✅ Required
LANGUAGE YAML        -- ✅ Required
COMMENT '{comment}'
AS $$
{yaml_content}       -- ✅ NOT wrapped in quotes
$$
"""
# ❌ NO: TBLPROPERTIES or placeholder SELECT
```

**Key YAML Structure:**
- `version: "1.1"` - Required (quoted string)
- `source:` - Main fact table (NOT `table:`)
- `joins:` - Dimension tables (each has `name`, `source`, `'on'` quoted)
- `dimensions:` - Use `source.` prefix for main table, join name for dimensions
- `measures:` - Aggregations (SUM, AVG, COUNT) with format specifications
- ❌ **NOT supported in v1.1:** `time_dimension`, `window_measures`

**Output:** Metric views ready for Genie queries and AI/BI dashboards

📖 **Full guide below** for detailed YAML patterns →

---

## Quick Reference

**Use this prompt when creating Metric Views for Databricks Genie AI and AI/BI dashboards.**

---

## 📋 Your Requirements (Fill These In First)

**Before creating Metric Views, define these specifications:**

### Project Context
- **Project Name:** _________________ (e.g., retail_analytics, patient_outcomes)
- **Catalog:** _________________ (e.g., my_catalog)
- **Gold Schema:** _________________ (e.g., my_project_gold)
- **Primary Fact Table:** _________________ (e.g., fact_sales_daily, fact_encounters_daily)

### Metric View Design

**Metric View Name:** _________________ (e.g., sales_performance_metrics, patient_outcomes_metrics)

**Purpose:** _________________________________________________ (Brief description)

### Dimensions to Include (5-10 dimensions)

| # | Dimension Name | Source | Type | Example Synonyms |
|---|---------------|--------|------|------------------|
| 1 | store_number | fact_table.store_number | Identifier | store id, location, shop |
| 2 | store_name | dim_store.store_name | Name | store, location name |
| 3 | city | dim_store.city | Geographic | store city, location |
| 4 | _____________ | _________________ | _______ | __________________ |
| 5 | _____________ | _________________ | _______ | __________________ |

**Dimension Categories:**
- **Identifiers:** IDs, codes, keys (store_number, product_id, patient_mrn)
- **Names:** Display names (store_name, product_description, provider_name)
- **Geographic:** Locations (city, state, region, country)
- **Temporal:** Time attributes (year, quarter, month, weekday)
- **Categories:** Classifications (category, type, status, diagnosis)

### Measures to Include (5-10 measures)

| # | Measure Name | Expression | Format | Example Synonyms |
|---|-------------|-----------|--------|------------------|
| 1 | total_revenue | SUM(source.net_revenue) | Currency (USD) | revenue, sales, dollars |
| 2 | total_units | SUM(source.net_units) | Number | units, quantity, volume |
| 3 | transaction_count | SUM(source.transaction_count) | Number | transactions, orders, visits |
| 4 | _____________ | _________________ | _______ | __________________ |
| 5 | _____________ | _________________ | _______ | __________________ |

**Measure Types:**
- **Currency:** Revenue, cost, amount (format: currency, USD)
- **Counts:** Transaction count, patient count, order count (format: number)
- **Quantities:** Units, volume, weight (format: number)
- **Rates:** Percentages, ratios (format: percentage)
- **Averages:** Avg transaction value, avg length of stay (format: currency or number)

### Dimension Joins (if needed)

| Join Alias | Source Table | Join Condition |
|-----------|--------------|----------------|
| dim_store | dim_store | source.store_number = dim_store.store_number AND dim_store.is_current = true |
| dim_product | dim_product | source.upc_code = dim_product.upc_code |
| __________ | ___________ | ______________________________________________ |

### Common Business Questions

List questions users will ask (helps define synonyms):

1. "What is the total {measure} for {time period}?"
2. "Show me {measure} by {dimension}"
3. "What are the top {N} {entities} by {measure}?"
4. _________________________________________________
5. _________________________________________________

**Example - Retail:**
- "What is the total revenue for last month?"
- "Show me sales by store"
- "What are the top 10 products by revenue?"

**Example - Healthcare:**
- "What is the patient count for this quarter?"
- "Show me readmissions by diagnosis"
- "What are the top 5 providers by patient volume?"

**Example - Finance:**
- "What is the transaction volume for last week?"
- "Show me amounts by account type"
- "Which merchants have the highest fraud rate?"

---

## Input Required Summary
- Gold layer fact tables
- Gold layer dimensions
- Key business metrics and measures
- Common business questions

**Output:** 2-3 Metric Views with semantic metadata, formatting, synonyms, and dimension joins.

**Time Estimate:** 2 hours

---

## Core Philosophy: Semantic Layer for Natural Language

**⚠️ CRITICAL PRINCIPLE:**

Metric Views provide a **semantic layer** that enables natural language queries via Genie AI:

- ✅ **Business-friendly names** with synonyms
- ✅ **Measure formatting** (currency, percentage, number)
- ✅ **Dimension joins** for context
- ✅ **LLM-optimized comments** for query understanding
- ✅ **v1.1 specification** (no unsupported fields)
- ❌ **No window measures** (not supported in v1.1)
- ❌ **No time_dimension field** (use regular dimension)

**Why This Matters:**
- Enables business users to ask questions in natural language
- Genie AI translates to SQL using semantic metadata
- Pre-defines common aggregations and calculations
- Provides consistent metric definitions across organization

---

## Metric View Specification v1.1

### ⚠️ Critical: v1.1 Unsupported Fields

**These fields will cause errors and MUST NOT be used:**

| Field | Error | Action |
|-------|-------|--------|
| `time_dimension` | Unrecognized field | ❌ Remove - use regular dimension |
| `window_measures` | Unrecognized field | ❌ Remove - calculate in SQL/Python |
| `join_type` | Unsupported | ❌ Remove - defaults to LEFT OUTER JOIN |
| `table` (in joins) | Missing required 'source' | ✅ Use `source` instead |

### Required YAML Structure

```yaml
version: "1.1"

- name: {metric_view_name}
  comment: {Comprehensive description for Genie understanding}
  
  source: ${catalog}.${gold_schema}.{fact_table}
  
  # Join to dimension tables (optional)
  joins:
    - name: {dim_alias}           # ✅ REQUIRED: Join alias
      source: ${catalog}.${gold_schema}.{dim_table}  # ✅ REQUIRED: Use 'source' not 'table'
      'on': source.{fk} = {dim_alias}.{pk} AND {dim_alias}.is_current = true  # ✅ REQUIRED: Quoted!
  
  dimensions:
    - name: {dimension_name}
      expr: source.{column}      # ✅ Use 'source.' for main table
      comment: {Business description for LLM}
      display_name: {User-Friendly Name}
      synonyms:
        - {alternative1}
        - {alternative2}
    
    - name: {joined_dimension}
      expr: {dim_alias}.{column}  # ✅ Use join name as prefix
      comment: {Business description}
      display_name: {User-Friendly Name}
  
  measures:
    - name: {measure_name}
      expr: SUM(source.{column})  # ✅ Use 'source.' prefix
      comment: {Business description and calculation}
      display_name: {User-Friendly Name}
      format:
        type: currency  # or number, percentage
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
        abbreviation: compact
      synonyms:
        - {alternative1}
        - {alternative2}
```

---

## Step 1: Metric View Design

### Design Checklist

- [ ] **Fact Table:** Which fact table is the primary source?
- [ ] **Dimensions:** Which dimensions to join? (store, product, date)
- [ ] **Measures:** What are the key metrics? (revenue, units, transactions)
- [ ] **User Questions:** What questions will users ask?

### Example Design

**Business Questions:**
- "What is total revenue by store?"
- "Show me top products by sales"
- "What's the average transaction value?"
- "How many units were sold last month?"

**Metric View Design:**
```yaml
name: sales_performance_metrics
fact_table: fact_sales_daily
dimensions:
  - From fact: store_number, upc_code, transaction_date
  - From dim_store: store_name, city, state
  - From dim_product: brand, category
  - From dim_date: year, quarter, month_name
measures:
  - total_revenue (SUM(net_revenue))
  - total_units (SUM(net_units))
  - transaction_count (SUM(transaction_count))
  - avg_transaction_value (AVG(avg_transaction_value))
```

---

## Step 2: Create Metric View YAML

### File: `metric_views.yaml`

```yaml
version: "1.1"

- name: sales_performance_metrics
  comment: >
    Comprehensive sales performance metrics with revenue, units, and customer insights.
    Optimized for Genie natural language queries and AI/BI dashboards. Aggregates daily
    sales data with store location context, product attributes, and time dimensions for
    trend analysis, performance tracking, and executive reporting.
  
  source: ${catalog}.${gold_schema}.fact_sales_daily
  
  joins:
    - name: dim_store
      source: ${catalog}.${gold_schema}.dim_store
      'on': source.store_number = dim_store.store_number AND dim_store.is_current = true
    
    - name: dim_product
      source: ${catalog}.${gold_schema}.dim_product
      'on': source.upc_code = dim_product.upc_code
    
    - name: dim_date
      source: ${catalog}.${gold_schema}.dim_date
      'on': source.transaction_date = dim_date.date
  
  dimensions:
    # Fact table dimensions
    - name: store_number
      expr: source.store_number
      comment: Store identifier for location-based sales analysis and store performance tracking
      display_name: Store Number
      synonyms:
        - store id
        - location number
        - store code
    
    - name: upc_code
      expr: source.upc_code
      comment: Universal Product Code for product identification and SKU analysis
      display_name: UPC Code
      synonyms:
        - product code
        - upc
        - barcode
        - sku
    
    - name: transaction_date
      expr: source.transaction_date
      comment: Transaction date for time-based analysis, trending, and period comparisons
      display_name: Transaction Date
      synonyms:
        - date
        - sales date
        - order date
    
    # Store dimension attributes
    - name: store_name
      expr: dim_store.store_name
      comment: Store name for user-friendly location identification in reports and dashboards
      display_name: Store Name
      synonyms:
        - location name
        - store
        - location
    
    - name: city
      expr: dim_store.city
      comment: City where the store is located for geographic analysis and regional performance
      display_name: City
      synonyms:
        - store city
        - location city
    
    - name: state
      expr: dim_store.state
      comment: State where the store is located for state-level aggregations and comparisons
      display_name: State
      synonyms:
        - store state
        - location state
    
    # Product dimension attributes
    - name: brand
      expr: dim_product.brand
      comment: Product brand name for brand performance analysis and market share tracking
      display_name: Brand
      synonyms:
        - product brand
        - manufacturer brand
    
    - name: product_category
      expr: dim_product.product_category
      comment: Product category classification for category-level reporting and analysis
      display_name: Product Category
      synonyms:
        - category
        - product type
    
    # Date dimension attributes
    - name: year
      expr: dim_date.year
      comment: Calendar year for annual analysis and year-over-year comparisons
      display_name: Year
      synonyms:
        - calendar year
        - fiscal year
    
    - name: quarter
      expr: dim_date.quarter
      comment: Calendar quarter (1-4) for quarterly reporting and seasonal analysis
      display_name: Quarter
      synonyms:
        - q
        - fiscal quarter
    
    - name: month_name
      expr: dim_date.month_name
      comment: Month name for user-friendly time-based reporting and monthly trending
      display_name: Month Name
      synonyms:
        - month
        - calendar month
    
    - name: is_weekend
      expr: dim_date.is_weekend
      comment: Weekend indicator for weekend vs weekday sales pattern analysis
      display_name: Is Weekend
      synonyms:
        - weekend
        - weekend flag
  
  measures:
    # Revenue measures
    - name: total_revenue
      expr: SUM(source.net_revenue)
      comment: >
        Total net revenue after discounts and returns. Primary revenue metric for business
        reporting and financial analysis. Includes all sales minus returns, representing actual
        revenue realized from customer transactions.
      display_name: Total Revenue
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
        hide_group_separator: false
        abbreviation: compact
      synonyms:
        - revenue
        - net revenue
        - sales
        - total sales
        - dollars
    
    - name: gross_revenue
      expr: SUM(source.gross_revenue)
      comment: >
        Gross revenue before returns. Total sales amount including all positive transactions,
        excluding returns. Used for top-line revenue reporting and understanding sales volume
        before adjustments.
      display_name: Gross Revenue
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
        abbreviation: compact
      synonyms:
        - gross sales
        - total gross revenue
        - sales before returns
    
    - name: return_amount
      expr: SUM(source.return_amount)
      comment: >
        Total value of returned merchandise. Represents revenue lost due to product returns.
        Used for return rate analysis and understanding product/store return patterns.
      display_name: Return Amount
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
        abbreviation: compact
      synonyms:
        - returns
        - return value
        - returned revenue
    
    # Unit measures
    - name: total_units
      expr: SUM(source.net_units)
      comment: >
        Total units sold after returns. Net quantity of products sold representing actual
        unit volume. Used for inventory planning, demand forecasting, and volume-based
        performance tracking.
      display_name: Total Units
      format:
        type: number
        decimal_places:
          type: all
        hide_group_separator: false
        abbreviation: compact
      synonyms:
        - units
        - units sold
        - quantity
        - volume
        - items sold
    
    - name: gross_units
      expr: SUM(source.gross_units)
      comment: >
        Gross units sold before returns. Total positive unit volume excluding returned items.
        Used for understanding sales velocity and product movement patterns.
      display_name: Gross Units
      format:
        type: number
        decimal_places:
          type: all
        abbreviation: compact
      synonyms:
        - gross volume
        - units before returns
    
    # Transaction measures
    - name: transaction_count
      expr: SUM(source.transaction_count)
      comment: >
        Total number of sales transactions. Count of customer interactions and purchase events.
        Used for traffic analysis, conversion tracking, and store performance metrics.
      display_name: Transaction Count
      format:
        type: number
        decimal_places:
          type: all
        abbreviation: compact
      synonyms:
        - transactions
        - transaction volume
        - sales count
        - number of sales
    
    # Calculated measures
    - name: avg_transaction_value
      expr: AVG(source.avg_transaction_value)
      comment: >
        Average dollar value per transaction. Basket size indicator showing typical customer
        purchase amount. Used for pricing strategy, promotion effectiveness, and customer
        value analysis.
      display_name: Avg Transaction Value
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
      synonyms:
        - average transaction
        - basket value
        - ticket size
        - average basket
    
    - name: avg_unit_price
      expr: SUM(source.net_revenue) / NULLIF(SUM(source.net_units), 0)
      comment: >
        Average price per unit sold. Calculated as total revenue divided by total units.
        Used for price analysis, discount impact assessment, and pricing strategy optimization.
      display_name: Avg Unit Price
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
      synonyms:
        - average price
        - unit price
        - price per unit
    
    - name: return_rate
      expr: (SUM(source.return_amount) / NULLIF(SUM(source.gross_revenue), 0)) * 100
      comment: >
        Percentage of gross revenue returned. Calculated as return amount divided by gross
        revenue. Key quality and satisfaction metric indicating product or service issues.
      display_name: Return Rate
      format:
        type: percentage
        decimal_places:
          type: exact
          places: 1
      synonyms:
        - return percentage
        - return ratio
        - percentage returned
```

**See [14-metric-views-patterns.mdc](mdc:framework/rules/14-metric-views-patterns.mdc) for complete patterns.**

---

## Step 3: Python Script to Create Metric Views

### File: `create_metric_views.py`

```python
# Databricks notebook source

"""
{Project} Gold Layer - Metric Views Creation

Creates Metric Views from YAML configuration for Genie AI and AI/BI dashboards.

Critical: Uses 'WITH METRICS LANGUAGE YAML' syntax (not TBLPROPERTIES).

Usage:
  databricks bundle run create_metric_views -t dev
"""

import argparse
import yaml
from pyspark.sql import SparkSession


def load_metric_views_yaml(catalog: str, schema: str):
    """
    Load metric views from YAML file with parameter substitution.
    
    Replaces ${catalog} and ${gold_schema} placeholders with actual values.
    """
    with open("metric_views.yaml", "r") as f:
        yaml_content = f.read()
    
    # Substitute parameters
    yaml_content = yaml_content.replace("${catalog}", catalog)
    yaml_content = yaml_content.replace("${gold_schema}", schema)
    
    # Parse YAML
    metric_views = yaml.safe_load(yaml_content)
    
    return metric_views


def create_metric_view(spark: SparkSession, catalog: str, schema: str, metric_view: dict):
    """
    Create a single metric view using WITH METRICS LANGUAGE YAML syntax.
    
    Critical: Must use 'WITH METRICS' and 'AS $$...$$' syntax, NOT TBLPROPERTIES.
    """
    view_name = metric_view['name']
    fully_qualified_name = f"{catalog}.{schema}.{view_name}"
    
    print(f"\nCreating metric view: {fully_qualified_name}")
    
    # Drop existing table/view (might conflict with metric view)
    try:
        spark.sql(f"DROP VIEW IF EXISTS {fully_qualified_name}")
        spark.sql(f"DROP TABLE IF EXISTS {fully_qualified_name}")
    except:
        pass
    
    # Convert metric view dict back to YAML string
    yaml_str = yaml.dump([metric_view], default_flow_style=False, sort_keys=False)
    
    # Escape single quotes in comment for SQL
    view_comment = metric_view.get('comment', 'Metric view for Genie AI')
    view_comment_escaped = view_comment.replace("'", "''")
    
    # ✅ CORRECT: WITH METRICS LANGUAGE YAML syntax
    create_sql = f"""
    CREATE VIEW {fully_qualified_name}
    WITH METRICS
    LANGUAGE YAML
    COMMENT '{view_comment_escaped}'
    AS $$
{yaml_str}
    $$
    """
    
    try:
        spark.sql(create_sql)
        print(f"✓ Created metric view: {view_name}")
        
        # Verify it's a METRIC_VIEW (not just VIEW)
        result = spark.sql(f"DESCRIBE EXTENDED {fully_qualified_name}").collect()
        view_type = next((row.data_type for row in result if row.col_name == "Type"), "UNKNOWN")
        
        if view_type == "METRIC_VIEW":
            print(f"  ✓ Verified as METRIC_VIEW")
        else:
            print(f"  ⚠️  Warning: Type is {view_type}, expected METRIC_VIEW")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating {view_name}: {str(e)}")
        return False


def main():
    """
    Main entry point for metric views creation.
    
    Reads metric_views.yaml and creates all metric views.
    Raises RuntimeError if any metric view fails (job should fail, not succeed silently).
    """
    parser = argparse.ArgumentParser(description="Create Metric Views from YAML")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--gold_schema", required=True)
    
    args = parser.parse_args()
    
    spark = SparkSession.builder.appName("Create Metric Views").getOrCreate()
    
    print("=" * 80)
    print("METRIC VIEWS CREATION")
    print("=" * 80)
    print(f"Catalog: {args.catalog}")
    print(f"Schema: {args.gold_schema}")
    print("=" * 80)
    
    try:
        # Load metric views from YAML
        metric_views = load_metric_views_yaml(args.catalog, args.gold_schema)
        
        print(f"\nLoaded {len(metric_views)} metric view(s) from metric_views.yaml")
        
        # Create each metric view
        success_count = 0
        failed_views = []
        
        for view in metric_views:
            if create_metric_view(spark, args.catalog, args.gold_schema, view):
                success_count += 1
            else:
                failed_views.append(view['name'])
        
        print("\n" + "=" * 80)
        print(f"Created {success_count} of {len(metric_views)} metric views")
        
        if failed_views:
            print(f"❌ Failed to create: {', '.join(failed_views)}")
            # ✅ Raise exception to fail the job
            raise RuntimeError(
                f"Failed to create {len(failed_views)} metric view(s): "
                f"{', '.join(failed_views)}"
            )
        
        print("✅ All metric views deployed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
        
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

---

## Implementation Checklist

### Phase 1: Design (30 min)
- [ ] Identify fact table as primary source
- [ ] List dimensions to join (2-5 dimensions)
- [ ] Define key measures (5-10 measures)
- [ ] List common user questions
- [ ] Map synonyms for dimensions and measures

### Phase 2: YAML Creation (1 hour)
- [ ] Create `metric_views.yaml`
- [ ] Define source table
- [ ] Add joins (if needed)
- [ ] Define dimensions with:
  - [ ] Correct `expr` (source. or join_alias.)
  - [ ] Business-friendly comments
  - [ ] Display names
  - [ ] 3-5 synonyms each
- [ ] Define measures with:
  - [ ] Correct aggregation (SUM, AVG, COUNT)
  - [ ] Proper formatting (currency, number, percentage)
  - [ ] Comprehensive comments
  - [ ] 3-5 synonyms each

### Phase 3: Python Script (30 min)
- [ ] Create `create_metric_views.py`
- [ ] Implement YAML loading with substitution
- [ ] Use `WITH METRICS LANGUAGE YAML` syntax
- [ ] Add error handling (raise RuntimeError on failure)
- [ ] Verify METRIC_VIEW type after creation

### Phase 4: Deploy & Test (30 min)
- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run: `databricks bundle run create_metric_views -t dev`
- [ ] Verify: `DESCRIBE EXTENDED {catalog}.{schema}.{view_name}`
- [ ] Test queries:
  ```sql
  SELECT * FROM {catalog}.{schema}.{metric_view_name} LIMIT 10;
  
  SELECT 
    store_name,
    MEASURE(`Total Revenue`) as revenue,
    MEASURE(`Total Units`) as units
  FROM {catalog}.{schema}.{metric_view_name}
  GROUP BY store_name
  ORDER BY revenue DESC
  LIMIT 10;
  ```

---

## Validation Queries

```sql
-- List all metric views
SHOW VIEWS IN {catalog}.{schema};

-- Verify metric view type
DESCRIBE EXTENDED {catalog}.{schema}.sales_performance_metrics;
-- Should show: Type: METRIC_VIEW

-- Test basic query
SELECT * FROM {catalog}.{schema}.sales_performance_metrics LIMIT 10;

-- Test MEASURE() function (specific to metric views)
SELECT 
  store_name,
  MEASURE(`Total Revenue`) as revenue,
  MEASURE(`Total Units`) as units,
  MEASURE(`Transaction Count`) as transactions
FROM {catalog}.{schema}.sales_performance_metrics
GROUP BY store_name
ORDER BY revenue DESC
LIMIT 10;

-- Test dimension filtering
SELECT 
  brand,
  MEASURE(`Total Revenue`) as revenue
FROM {catalog}.{schema}.sales_performance_metrics
WHERE state = 'CA'
GROUP BY brand
ORDER BY revenue DESC;
```

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Wrong Syntax (TBLPROPERTIES)
```python
# ❌ WRONG: Creates regular VIEW, not METRIC_VIEW
create_sql = f"""
CREATE VIEW {view_name}
COMMENT '{comment}'
TBLPROPERTIES ('metric_view_spec' = '{yaml}')
AS SELECT 1 as __metric_view_placeholder__
"""
```

### ✅ CORRECT: WITH METRICS LANGUAGE YAML
```python
# ✅ CORRECT: Creates METRIC_VIEW
create_sql = f"""
CREATE VIEW {view_name}
WITH METRICS
LANGUAGE YAML
COMMENT '{comment}'
AS $$
{yaml_str}
$$
"""
```

### ❌ Mistake 2: Using Unsupported Fields
```yaml
# ❌ WRONG: v1.1 doesn't support these
time_dimension:
  name: transaction_date
  expr: source.transaction_date

window_measures:
  - name: revenue_last_30_days
    base_measure: total_revenue
    window:
      duration: 30d
```

### ✅ CORRECT: Use Regular Dimension
```yaml
# ✅ CORRECT: Use regular dimension
dimensions:
  - name: transaction_date
    expr: source.transaction_date
    comment: Transaction date for time-based analysis
    
# Calculate windows in SQL or pre-aggregate in Gold
```

### ❌ Mistake 3: Wrong Column References
```yaml
# ❌ WRONG: Using table name instead of 'source.'
measures:
  - name: total_revenue
    expr: SUM(fact_sales_daily.net_revenue)  # ❌ Wrong prefix!

# ❌ WRONG: Missing join prefix
dimensions:
  - name: store_name
    expr: store_name  # ❌ Which table?
```

### ✅ CORRECT: Proper Prefixes
```yaml
# ✅ CORRECT: Use 'source.' for main table
measures:
  - name: total_revenue
    expr: SUM(source.net_revenue)

# ✅ CORRECT: Use join name for joined tables
dimensions:
  - name: store_name
    expr: dim_store.store_name
```

---

## Key Principles

### 1. v1.1 Specification Only
- ✅ Version must be "1.1" (quoted string)
- ❌ No `time_dimension` field
- ❌ No `window_measures` field
- ✅ Use `source:` in joins (not `table:`)

### 2. WITH METRICS Syntax Required
- ✅ `CREATE VIEW ... WITH METRICS LANGUAGE YAML AS $$...$$`
- ❌ NOT `TBLPROPERTIES` with placeholder SELECT

### 3. Comprehensive Synonyms
- ✅ 3-5 synonyms per dimension/measure
- ✅ Include common misspellings and variants
- ✅ Think like a business user asking questions

### 4. Professional Formatting
- ✅ Currency: USD with compact abbreviation (1.5M)
- ✅ Numbers: Compact with all decimals
- ✅ Percentages: 1 decimal place (45.3%)

### 5. Error Handling
- ✅ Job must FAIL if metric views don't create
- ✅ Track failed views and raise RuntimeError
- ✅ No silent success

---

## Next Steps

After Metric Views are complete:

1. **Test with Genie:** Ask natural language questions
2. **Create TVFs:** Use [15-databricks-table-valued-functions.mdc](mdc:framework/rules/15-databricks-table-valued-functions.mdc)
3. **Setup Genie Space:** Use [06-genie-space-prompt.md](./06-genie-space-prompt.md)
4. **Create Dashboards:** Use metric views in Lakeview AI/BI

---

## References

### Official Databricks Documentation
- [Metric Views v1.1](https://docs.databricks.com/metric-views/yaml-ref)
- [Semantic Metadata](https://docs.databricks.com/metric-views/semantic-metadata)
- [Measure Formats](https://docs.databricks.com/metric-views/measure-formats)
- [Joins in Metric Views](https://docs.databricks.com/metric-views/joins)

### Framework Rules
- [metric-views-patterns.mdc](mdc:framework/rules/14-metric-views-patterns.mdc)

---

## Summary

**What to Create:**
1. `metric_views.yaml` - YAML configuration with dimensions and measures
2. `create_metric_views.py` - Python script using WITH METRICS syntax
3. Add to Asset Bundle: `create_metric_views_job.yml`

**Core Philosophy:** Metric Views = Semantic layer for Genie AI with business-friendly names and comprehensive synonyms

**Time Estimate:** 2 hours for 2-3 metric views

**Next Action:** Design measures, create YAML, deploy with proper syntax





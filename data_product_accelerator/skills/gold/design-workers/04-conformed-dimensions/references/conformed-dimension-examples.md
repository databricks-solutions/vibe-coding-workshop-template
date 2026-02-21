# Conformed Dimension Examples

Extended examples for enterprise integration patterns. These examples complement the core rules in the main SKILL.md.

---

## Bus Matrix Template (Detailed)

### Building the Bus Matrix

#### Step 1: List All Business Processes (Rows)

Identify every business process that produces measurable events:

| # | Business Process | Fact Table | Grain |
|---|-----------------|------------|-------|
| 1 | Daily Sales | fact_sales_daily | One row per date-store-product |
| 2 | Inventory Snapshot | fact_inventory_snapshot | One row per date-store-product |
| 3 | Customer Returns | fact_returns | One row per return transaction |
| 4 | Promotions | fact_promotion_daily | One row per date-store-promotion |
| 5 | Employee Scheduling | fact_employee_schedule | One row per employee-date-shift |

#### Step 2: List All Candidate Dimensions (Columns)

From the dimension designs (output of `02-dimension-patterns`):

- dim_date, dim_customer, dim_product, dim_store, dim_employee, dim_promotion

#### Step 3: Fill the Matrix

Mark X where a fact table has a foreign key to that dimension:

| Business Process | dim_date | dim_customer | dim_product | dim_store | dim_employee | dim_promotion |
|-----------------|----------|-------------|-------------|-----------|-------------|---------------|
| Sales | X | X | X | X | | X |
| Inventory | X | | X | X | | |
| Returns | X | X | X | X | X | |
| Promotions | X | | X | X | | X |
| Scheduling | X | | | X | X | |

#### Step 4: Identify Conformed Dimensions

Count X's per column:

| Dimension | References | Conformed? | Priority |
|-----------|-----------|-----------|----------|
| dim_date | 5 | YES | Critical (every fact uses it) |
| dim_store | 5 | YES | Critical |
| dim_product | 4 | YES | High |
| dim_customer | 2 | YES | Medium |
| dim_promotion | 2 | YES | Medium |
| dim_employee | 2 | YES | Lower |

**All dimensions referenced by 2+ fact tables must be conformed.**

---

## Shrunken Dimension Patterns

### Shrunken Date Dimension

When an aggregate fact is at the monthly grain:

```yaml
# Full date dimension
table_name: dim_date
columns:
  - name: date_key
    type: BIGINT
  - name: date_value
    type: DATE
  - name: day_of_week
    type: STRING
  - name: month_name
    type: STRING
  - name: month_key
    type: BIGINT
  - name: quarter_name
    type: STRING
  - name: year_value
    type: INT

# Shrunken month dimension (for monthly aggregate facts)
table_name: dim_month
description: "Month rollup dimension. Business: Calendar months. Technical: Shrunken from dim_date to month grain."
columns:
  - name: month_key
    type: BIGINT
    nullable: false
  - name: month_name
    type: STRING       # Must match dim_date.month_name values exactly
  - name: quarter_name
    type: STRING       # Must match dim_date.quarter_name values exactly
  - name: year_value
    type: INT          # Must match dim_date.year_value values exactly
```

### Shrunken Geography Dimension

When an aggregate fact is at the region grain (not store grain):

```yaml
# Full store dimension
table_name: dim_store
columns:
  - name: store_key
    type: BIGINT
  - name: store_name
    type: STRING
  - name: city_name
    type: STRING
  - name: state_name
    type: STRING
  - name: region_name
    type: STRING
  - name: country_name
    type: STRING

# Shrunken to region
table_name: dim_region
description: "Region rollup dimension. Business: Geographic regions. Technical: Shrunken from dim_store to region grain."
columns:
  - name: region_key
    type: BIGINT
    nullable: false
  - name: region_name
    type: STRING       # Must match dim_store.region_name values exactly
  - name: country_name
    type: STRING       # Must match dim_store.country_name values exactly
```

---

## Drill-Across Patterns

### Pattern 1: Same Grain, Different Measures

Combining sales revenue with inventory levels at the same date-product-store grain:

```sql
WITH daily_sales AS (
  SELECT date_key, product_key, store_key,
         SUM(revenue) AS total_revenue,
         SUM(quantity_sold) AS units_sold
  FROM fact_sales_daily
  GROUP BY date_key, product_key, store_key
),
daily_inventory AS (
  SELECT date_key, product_key, store_key,
         on_hand_quantity, on_order_quantity
  FROM fact_inventory_snapshot
)
SELECT
  d.date_value, p.product_name, s.store_name,
  COALESCE(ds.total_revenue, 0) AS revenue,
  COALESCE(ds.units_sold, 0) AS units_sold,
  COALESCE(di.on_hand_quantity, 0) AS on_hand
FROM dim_date d
CROSS JOIN dim_product p
CROSS JOIN dim_store s
LEFT JOIN daily_sales ds USING (date_key, product_key, store_key)
LEFT JOIN daily_inventory di USING (date_key, product_key, store_key)
WHERE d.date_value BETWEEN '2025-01-01' AND '2025-01-31'
```

### Pattern 2: Different Grains, Aggregate to Common Grain

Sales at transaction grain, inventory at daily snapshot grain — aggregate sales to daily:

```sql
WITH daily_sales AS (
  SELECT
    date_key, product_key, store_key,
    SUM(revenue) AS total_revenue
  FROM fact_sales_transactions
  GROUP BY date_key, product_key, store_key  -- Aggregate to daily grain
),
daily_inventory AS (
  SELECT date_key, product_key, store_key, on_hand_quantity
  FROM fact_inventory_snapshot  -- Already at daily grain
)
SELECT
  d.date_value, p.product_name,
  COALESCE(ds.total_revenue, 0) AS revenue,
  COALESCE(di.on_hand_quantity, 0) AS inventory
FROM dim_date d
JOIN dim_product p ON ...
LEFT JOIN daily_sales ds USING (date_key, product_key)
LEFT JOIN daily_inventory di USING (date_key, product_key)
```

**Key:** Always aggregate each fact to the common grain BEFORE joining. Never join raw facts at different grains.

---

## Multi-Star Schema Integration

### Physical Layout in Unity Catalog

```
gold_schema/
├── dim_date                  # Conformed — used by all stars
├── dim_customer              # Conformed — used by sales, returns
├── dim_product               # Conformed — used by sales, inventory, returns
├── dim_store                 # Conformed — used by all stars
├── dim_employee              # Conformed — used by returns, scheduling
├── dim_promotion             # Conformed — used by sales, promotions
├── fact_sales_daily          # Star 1: Sales
├── fact_inventory_snapshot   # Star 2: Inventory
├── fact_returns              # Star 3: Returns
├── fact_promotion_daily      # Star 4: Promotions
└── fact_employee_schedule    # Star 5: Scheduling
```

### Domain Grouping for ERD Organization

When the model has 9+ tables, group by domain for ERD organization:

| Domain | Tables | ERD File |
|--------|--------|----------|
| Sales | dim_customer, dim_promotion, fact_sales_daily | erd_sales.md |
| Inventory | fact_inventory_snapshot | erd_inventory.md |
| Operations | dim_employee, fact_returns, fact_employee_schedule | erd_operations.md |
| Shared | dim_date, dim_product, dim_store | Appears in all domain ERDs |

**Shared dimensions** appear in every domain ERD as cross-domain references (using the bracketed notation from `05-erd-diagrams`).

---

## Fact-to-Fact Join Anti-Pattern (Detailed)

### Why It Fails

Given:
- `fact_sales`: 1M rows (grain: per transaction)
- `fact_inventory`: 365K rows (grain: per date-product-store)

```sql
-- ❌ Joining facts directly
SELECT *
FROM fact_sales s
JOIN fact_inventory i
  ON s.product_key = i.product_key
  AND s.store_key = i.store_key
  AND s.date_key = i.date_key
-- If 50 sales per store-product-day: each inventory row joins to 50 sales rows
-- Inventory measures get duplicated 50x → SUM(on_hand) is 50x too high!
```

### The Fix: Always Drill Across

```sql
-- ✅ Separate aggregated subqueries joined through conformed dimensions
WITH agg_sales AS (
  SELECT date_key, product_key, store_key, SUM(revenue) AS revenue
  FROM fact_sales
  GROUP BY date_key, product_key, store_key
)
SELECT
  d.date_value, p.product_name, s.store_name,
  agg_sales.revenue,
  inv.on_hand_quantity
FROM dim_date d
JOIN dim_product p ON ...
JOIN dim_store s ON ...
LEFT JOIN agg_sales USING (date_key, product_key, store_key)
LEFT JOIN fact_inventory inv USING (date_key, product_key, store_key)
```

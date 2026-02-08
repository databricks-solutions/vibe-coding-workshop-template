# Dimensional Modeling Guide

Extracted from `context/prompts/03a-gold-layer-design-prompt.md` Steps 1.1-1.5.

---

## Step 1.1: Identify Dimensions (2-5 tables)

| # | Dimension Name | Business Key | SCD Type | Source Silver Table | Contains PII |
|---|---------------|--------------|----------|---------------------|--------------|
| 1 | dim_customer | customer_id | Type 2 | silver_customer_dim | Yes |
| 2 | dim_product | product_id | Type 1 | silver_product_dim | No |
| 3 | dim_date | date | Type 1 | Generated | No |
| 4 | dim_store | store_number | Type 2 | silver_store_dim | Yes |
| 5 | ____________ | ___________ | ______ | _________________ | _____ |

### SCD Type Decision Matrix

| SCD Type | When to Use | Examples |
|---|---|---|
| **Type 1 (Overwrite)** | History doesn't matter, attributes rarely change | Date dimensions, simple lookups, product categories |
| **Type 2 (Track History)** | Need to track changes over time for point-in-time analysis | Customer addresses, product prices, store status |

### SCD Type 2 Requirements

When using SCD Type 2, the dimension MUST include:
- Surrogate key (e.g., `store_key` as MD5 hash)
- Business key (e.g., `store_number`)
- `effective_from` TIMESTAMP
- `effective_to` TIMESTAMP (NULL for current)
- `is_current` BOOLEAN

---

## Step 1.2: Identify Facts (1-3 tables)

| # | Fact Name | Grain | Source Silver Tables | Update Frequency |
|---|-----------|-------|---------------------|------------------|
| 1 | fact_sales_daily | store-product-day | silver_transactions | Daily |
| 2 | fact_inventory_snapshot | store-product-day | silver_inventory | Daily |
| 3 | _____________ | _________________ | ___________________ | ________ |

### Grain Definition (One row per...)

- **Store-Product-Day:** One row for each store-product combination per day
- **Customer-Month:** One row for each customer per month
- **Patient-Encounter:** One row per patient visit
- **Transaction:** One row per individual transaction (not aggregated)

### Grain Types

| Grain Type | Description | Key Characteristics |
|-----------|-------------|---------------------|
| **Aggregated** | Pre-summarized data | Uses `.groupBy()` and `.agg()`, composite PK |
| **Transaction** | Individual events | No aggregation, single surrogate PK |
| **Snapshot** | Point-in-time state | Entity + date PK, latest values |

**Critical:** Read `fact-table-grain-validation` skill for grain validation patterns before finalizing.

---

## Step 1.3: Define Measures & Metrics

For each fact table, define all measures:

| Fact Table | Measure Name | Data Type | Calculation Logic | Business Purpose |
|---|---|---|---|---|
| fact_sales_daily | gross_revenue | DECIMAL(18,2) | SUM(CASE WHEN qty > 0 THEN revenue END) | Revenue before returns |
| fact_sales_daily | net_revenue | DECIMAL(18,2) | SUM(revenue) | Revenue after returns (primary KPI) |
| fact_sales_daily | net_units | BIGINT | SUM(quantity) | Units sold after returns |
| fact_sales_daily | transaction_count | BIGINT | COUNT(DISTINCT transaction_id) | Number of transactions |
| fact_sales_daily | avg_transaction_value | DECIMAL(18,2) | net_revenue / transaction_count | Basket size metric |

### Measure Type Guidelines

| Value Type | Data Type | Examples |
|-----------|-----------|---------|
| Revenue/Amount | DECIMAL(18,2) | Monetary values |
| Quantities | BIGINT | Unit counts |
| Counts | BIGINT | Transaction/customer counts |
| Averages | DECIMAL(18,2) | Calculated from other measures |
| Rates/Percentages | DECIMAL(5,2) | e.g., 45.32% |

---

## Step 1.4: Define Relationships (FK Constraints)

| Fact Table | Dimension | FK Column | PK Column | Relationship |
|---|---|---|---|---|
| fact_sales_daily | dim_store | store_number | store_number | Many-to-One |
| fact_sales_daily | dim_product | upc_code | upc_code | Many-to-One |
| fact_sales_daily | dim_date | transaction_date | date | Many-to-One |

### Relationship Rules

- Facts → Dimensions: Always Many-to-One
- Use business keys for FK references (not surrogate keys)
- Document all FK constraints in DDL
- Use `NOT ENFORCED` (informational only in Unity Catalog)

---

## Step 1.5: Assign Tables to Domains

Assign each table to exactly ONE domain for ERD and YAML organization:

| # | Table Name | Type | Domain | Domain ERD | YAML Path |
|---|------------|------|--------|------------|-----------|
| 1 | dim_store | Dimension | 🏪 Location | erd_location.md | yaml/location/ |
| 2 | dim_region | Dimension | 🏪 Location | erd_location.md | yaml/location/ |
| 3 | dim_product | Dimension | 📦 Product | erd_product.md | yaml/product/ |
| 4 | dim_date | Dimension | 📅 Time | erd_time.md | yaml/time/ |
| 5 | fact_sales_daily | Fact | 💰 Sales | erd_sales.md | yaml/sales/ |
| 6 | fact_inventory_snapshot | Fact | 📊 Inventory | erd_inventory.md | yaml/inventory/ |

### Standard Domain Categories

| Domain | Emoji | Description | Typical Tables |
|--------|-------|-------------|----------------|
| **Location** | 🏪 | Geographic hierarchy | dim_store, dim_region, dim_territory, dim_country |
| **Product** | 📦 | Product hierarchy | dim_product, dim_brand, dim_category, dim_supplier |
| **Time** | 📅 | Temporal dimensions | dim_date, dim_time, dim_fiscal_period |
| **Customer** | 👤 | Customer attributes | dim_customer, dim_segment, dim_loyalty_tier |
| **Sales** | 💰 | Revenue & transactions | fact_sales_*, dim_promotion, dim_channel |
| **Inventory** | 📊 | Stock & replenishment | fact_inventory_*, dim_warehouse |
| **Finance** | 💵 | Financial measures | fact_gl_*, dim_account, dim_cost_center |
| **Operations** | ⚙️ | Operational metrics | fact_shipment_*, dim_carrier, dim_route |

### Domain Assignment Rules

1. **Dimensions** → Assign to domain based on primary business concept
2. **Facts** → Assign to domain of the primary measure (sales fact → Sales)
3. **Bridge tables** → Assign to domain of the "many" side
4. **Conformed dimensions** (date, geography) → Own domain, referenced by others

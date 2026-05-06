# Naming Conventions Reference

Detailed naming patterns and examples for all Databricks object types.

## Object Naming by Type

### Catalogs

```
{env}_{domain}_catalog
```

| Environment | Domain | Result |
|-------------|--------|--------|
| `prod` | `sales` | `prod_sales_catalog` |
| `dev` | `analytics` | `dev_analytics_catalog` |
| `staging` | `billing` | `staging_billing_catalog` |

### Schemas

```
{layer}  OR  {domain}_{layer}
```

Examples: `bronze`, `silver`, `gold`, `sales_gold`, `billing_silver`

### Tables by Layer

| Layer | Format | Examples |
|-------|--------|----------|
| Bronze | `bronze_{source}_{entity}` | `bronze_raw_orders`, `bronze_pos_events` |
| Silver | `silver_{entity}` | `silver_orders`, `silver_customers` |
| Gold | `{type}_{entity}` | `dim_customer`, `fact_orders`, `bridge_customer_product` |

### Special Table Suffixes

| Suffix | Purpose | Example |
|--------|---------|---------|
| `_quarantine` | Failed quality records | `silver_orders_quarantine` |
| `_history` | SCD Type 2 archive | `dim_customer_history` |
| `_snapshot` | Point-in-time capture | `inventory_snapshot` |

---

## Column Naming Patterns

### Keys

| Type | Pattern | Examples |
|------|---------|----------|
| Primary Key | `{entity}_id` | `customer_id`, `order_id` |
| Surrogate Key | `{entity}_key` | `customer_key`, `product_key` |
| Business Key | `{entity}_{identifier}` | `customer_number`, `store_code` |
| Foreign Key | Same name as referenced PK | `customer_id` (FK to `dim_customer.customer_id`) |

### Temporal Columns

| Type | Pattern | Examples |
|------|---------|----------|
| Date | `{event}_date` | `order_date`, `ship_date` |
| Timestamp | `{event}_timestamp` or `{event}_ts` | `created_timestamp`, `updated_ts` |

### Measure Columns

| Type | Pattern | Examples |
|------|---------|----------|
| Amount | `{type}_amount` or `{type}_amt` | `total_amount`, `discount_amt` |
| Count | `{thing}_count` or `{thing}_cnt` | `order_count`, `item_cnt` |
| Percentage | `{type}_pct` | `discount_pct`, `tax_pct` |
| Average | `avg_{measure}` | `avg_order_value` |

### Boolean Columns

| Pattern | Examples |
|---------|----------|
| `is_{condition}` | `is_active`, `is_current`, `is_deleted` |
| `has_{thing}` | `has_discount`, `has_promotion` |

### SCD Type 2 Standard Columns

These column names are **mandatory** for SCD2 dimensions:

| Column | Type | Description |
|--------|------|-------------|
| `effective_from` | TIMESTAMP | Record start |
| `effective_to` | TIMESTAMP | Record end (NULL = current) |
| `is_current` | BOOLEAN | Active flag |
| `record_created_timestamp` | TIMESTAMP | Row creation |
| `record_updated_timestamp` | TIMESTAMP | Row last update |

---

## Approved Abbreviations

| Abbr | Meaning | Use In |
|------|---------|--------|
| `id` | Identifier | Columns: `customer_id` |
| `ts` | Timestamp | Columns: `created_ts` |
| `dt` | Date | Columns: `order_dt` |
| `amt` | Amount | Columns: `total_amt` |
| `qty` | Quantity | Columns: `order_qty` |
| `pct` | Percentage | Columns: `discount_pct` |
| `num` | Number | Columns: `order_num` |
| `cnt` | Count | Columns: `order_cnt` |
| `avg` | Average | Columns: `avg_order_value` |
| `min` / `max` | Minimum/Maximum | Columns: `min_price` |
| `pk` / `fk` | Primary/Foreign Key | Constraints: `pk_dim_customer` |
| `dim` / `fact` | Dimension/Fact | Tables: `dim_store` |
| `agg` | Aggregate | Tables: `agg_daily_revenue` |
| `stg` | Staging | Tables: `stg_customer_load` |

### Forbidden Abbreviations

| Never Use | Spell Out |
|-----------|----------|
| `cust` | `customer` |
| `prod` | `product` |
| `inv` | `inventory` |
| `trans` | `transaction` |
| `ord` | `order` |
| `emp` | `employee` |

---

## Constraint Naming

```
{pk|fk}_{table}[_{referenced_table}]
```

| Type | Pattern | Example |
|------|---------|---------|
| Primary Key | `pk_{table}` | `pk_dim_customer` |
| Foreign Key | `fk_{table}_{ref_table}` | `fk_orders_customer` |

---

## Job & Pipeline Naming

### Jobs

```
[${bundle.target}] {Domain} - {Action} {Entity}
```

Examples:
- `[dev] Sales - Ingest Orders`
- `[prod] Billing - Merge Daily Usage`
- `[dev] Platform - Setup Gold Tables`

### DLT Pipelines

```
[${bundle.target}] {Layer} {Domain} Pipeline
```

Examples:
- `[dev] Silver Sales Pipeline`
- `[prod] Bronze Events Pipeline`

---

## Function Naming

### Table-Valued Functions

```
get_{entity}_{action}
```

Examples:
- `get_daily_sales_summary`
- `get_customer_orders`
- `get_cost_by_workspace`

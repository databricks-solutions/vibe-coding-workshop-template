# Grain Definition Patterns

Detailed grain type descriptions with DDL examples for use during the Gold layer design phase.

## Transaction-Level Fact Pattern

**When to Use:**
- **One row per business event** (sale, click, API call)
- **Primary Key:** Single surrogate key (`transaction_id`, `event_id`, `request_id`)
- **Measures:** Individual event metrics (amount, duration, count=1)

**Key Characteristics:**
- ✅ No `.groupBy()` or `.agg()` in merge script
- ✅ Single surrogate key as PRIMARY KEY
- ✅ Measures are direct pass-through (no SUM, AVG, COUNT)
- ✅ One source row → one target row

**Example DDL:**
```sql
CREATE TABLE fact_sales_transactions (
  transaction_id BIGINT NOT NULL,
  customer_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  sale_timestamp TIMESTAMP NOT NULL,
  amount DECIMAL(18,2) NOT NULL,
  quantity INT NOT NULL,
  channel STRING,
  PRIMARY KEY (transaction_id) NOT ENFORCED
)
```

**Example YAML:**
```yaml
table_name: fact_sales_transactions
grain: "One row per individual sale transaction"
grain_type: transaction
primary_key:
  columns: ['transaction_id']
  composite: false
```

## Aggregated Fact Pattern

**When to Use:**
- **Pre-aggregated summaries** (daily sales, hourly usage)
- **Primary Key:** Composite key of dimensions defining grain (`date_key, store_key, product_key`)
- **Measures:** Aggregated metrics (total_revenue, avg_latency, request_count)

**Key Characteristics:**
- ✅ Uses `.groupBy()` on grain dimensions
- ✅ Uses `.agg()` with SUM, COUNT, AVG, MAX
- ✅ Composite PRIMARY KEY matches `.groupBy()` columns
- ✅ Multiple source rows → one target row per grain

**Example DDL:**
```sql
CREATE TABLE fact_sales_daily (
  date_key INT NOT NULL,
  store_key INT NOT NULL,
  product_key INT NOT NULL,
  total_revenue DECIMAL(18,2) NOT NULL,
  total_quantity INT NOT NULL,
  transaction_count BIGINT NOT NULL,
  avg_unit_price DECIMAL(18,2) NOT NULL,
  PRIMARY KEY (date_key, store_key, product_key) NOT ENFORCED
)
```

**Example YAML:**
```yaml
table_name: fact_sales_daily
grain: "One row per date-store-product combination (daily aggregate)"
grain_type: aggregated
primary_key:
  columns: ['date_key', 'store_key', 'product_key']
  composite: true
measures:
  - name: total_revenue
    aggregation: SUM
  - name: transaction_count
    aggregation: COUNT
  - name: avg_unit_price
    aggregation: AVG
```

## Snapshot Fact Pattern

**When to Use:**
- **Point-in-time state** (daily inventory levels, account balances)
- **Primary Key:** Entity + date (`entity_key, snapshot_date_key`)
- **Measures:** Current values at snapshot time (on_hand_quantity, balance_amount)

**Key Characteristics:**
- ✅ No aggregation (snapshots already at correct grain)
- ✅ May need deduplication (latest snapshot wins)
- ✅ Composite PK: entity keys + snapshot date
- ✅ Measures are point-in-time values (not SUMs)

**Example DDL:**
```sql
CREATE TABLE fact_inventory_snapshot (
  product_key INT NOT NULL,
  warehouse_key INT NOT NULL,
  snapshot_date_key INT NOT NULL,
  on_hand_quantity INT NOT NULL,
  reserved_quantity INT NOT NULL,
  available_quantity INT NOT NULL,
  cost_per_unit DECIMAL(18,2) NOT NULL,
  PRIMARY KEY (product_key, warehouse_key, snapshot_date_key) NOT ENFORCED
)
```

**Example YAML:**
```yaml
table_name: fact_inventory_snapshot
grain: "One row per product-warehouse-date combination (daily snapshot)"
grain_type: snapshot
primary_key:
  columns: ['product_key', 'warehouse_key', 'snapshot_date_key']
  composite: true
```

## Hourly Aggregated Fact

```sql
CREATE TABLE fact_api_usage_hourly (
  date_key INT NOT NULL,
  hour_of_day INT NOT NULL,
  endpoint_key INT NOT NULL,
  request_count BIGINT NOT NULL,
  avg_latency_ms DOUBLE NOT NULL,
  error_count BIGINT NOT NULL,
  PRIMARY KEY (date_key, hour_of_day, endpoint_key) NOT ENFORCED
)
```

## Monthly Snapshot Fact

```sql
CREATE TABLE fact_account_balance_monthly (
  account_key INT NOT NULL,
  snapshot_month_key INT NOT NULL,
  balance_amount DECIMAL(18,2) NOT NULL,
  transaction_count INT NOT NULL,
  PRIMARY KEY (account_key, snapshot_month_key) NOT ENFORCED
)
```

## Ambiguous Grain — Design Mistake

**Problem:**
```yaml
# ❌ BAD: Grain not explicitly documented
table_name: fact_model_serving_inference
primary_key:
  columns:
    - date_key
    - endpoint_key
    - model_key
# What grain is this? Daily aggregate? Hourly? Per request?
```

**Fix:**
```yaml
# ✅ GOOD: Grain explicitly documented
table_name: fact_model_serving_inference
grain: "Daily aggregate per endpoint-model combination"
grain_type: aggregated
primary_key:
  columns:
    - date_key
    - endpoint_key
    - model_key
measures:
  - name: request_count
    aggregation: SUM
  - name: avg_latency_ms
    aggregation: AVG
```

## References

- [Kimball Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Delta Lake Merge](https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge)

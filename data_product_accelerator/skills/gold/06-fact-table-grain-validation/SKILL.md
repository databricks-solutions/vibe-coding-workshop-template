---
name: fact-table-grain-validation
description: Fact table grain validation patterns to prevent transaction vs aggregated confusion. Use when creating fact table merge scripts to infer grain from DDL PRIMARY KEY, validate merge logic matches grain type (transaction, aggregated, snapshot), and prevent costly table rewrites. Includes grain inference functions, transaction-level patterns, aggregated fact patterns, snapshot patterns, and pre-merge grain validation.
metadata:
  author: prashanth subrahmanyam
  version: "1.0"
  domain: gold
  role: worker
  pipeline_stage: 1
  pipeline_stage_name: gold-design
  called_by:
    - gold-layer-design
    - gold-layer-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: low
---
# Fact Table Grain Validation Patterns

## Overview

Fact tables have a **grain** - the level of detail at which measurements are stored. Misunderstanding grain (transaction-level vs aggregated) causes 5% of Gold layer bugs but has high impact (complete table rewrite required). This skill provides patterns to infer grain from DDL and validate merge logic.

**Key Principle:** DDL PRIMARY KEY reveals the grain. Merge script must match that grain.

## When to Use This Skill

Use when:
- Creating fact table merge scripts
- Inferring grain from DDL PRIMARY KEY
- Validating merge logic matches grain type (transaction, aggregated, snapshot)
- Preventing costly table rewrites from grain mismatches

## Understanding Fact Table Grain

### Grain Definition

**Grain:** The combination of dimensions that uniquely identifies one measurement row.

**Examples:**

| Grain | Description | Primary Key | Row Represents |
|-------|-------------|-------------|----------------|
| **Transaction** | One row per event | `transaction_id` | Individual sale |
| **Daily Summary** | One row per day-store-product | `date_key, store_key, product_key` | Daily totals |
| **Hourly Aggregate** | One row per hour-cluster | `date_key, hour_of_day, cluster_key` | Hourly metrics |
| **Snapshot** | One row per entity-date | `entity_key, snapshot_date_key` | Daily snapshot |

## Problem: Grain Ambiguity

### Common Failure Pattern

```python
# DDL (Aggregated Grain)
CREATE TABLE fact_model_serving_inference (
  date_key INT NOT NULL,
  endpoint_key STRING NOT NULL,
  model_key STRING NOT NULL,
  request_count BIGINT,        -- ✅ Aggregated measure
  avg_latency_ms DOUBLE,       -- ✅ Aggregated measure
  error_count BIGINT,          -- ✅ Aggregated measure
  PRIMARY KEY (date_key, endpoint_key, model_key) NOT ENFORCED
)

# Merge Script (Transaction Grain - WRONG!)
def merge_fact_model_serving_inference(...):
    updates_df = (
        endpoint_usage_df
        .withColumn("request_id", col("databricks_request_id"))  # ❌ Transaction ID
        .withColumn("latency_ms", col("execution_duration_ms"))  # ❌ Single request
        .select(
            "request_id",      # ❌ Not in DDL!
            "date_key",
            "endpoint_key",
            "model_key",
            "latency_ms"       # ❌ Not aggregated
        )
    )
    
    # Merge with wrong primary key
    merge_fact_table(spark, updates_df, catalog, schema, 
                     "fact_model_serving_inference",
                     ["request_id"])  # ❌ DDL says (date_key, endpoint_key, model_key)!

# Error at Runtime:
# [DELTA_MERGE_UNRESOLVED_EXPRESSION] Cannot resolve target.request_id
```

**Root Cause:** Merge script treats aggregated fact as transaction-level fact.

## Critical Rules

### Grain Type Decision Tree

```
PRIMARY KEY column count?
├─ 1 column
│  ├─ Ends with _id, _uid? → Transaction Grain
│  ├─ Is date_key? → Daily Snapshot Grain
│  └─ Otherwise → Unknown (manual review)
│
└─ Multiple columns (Composite PK)
   ├─ Contains date_key + dimension keys? → Aggregated Grain
   ├─ Contains entity_key + date_key? → Snapshot Grain
   └─ Otherwise → Composite (manual review)
```

### Transaction-Level Fact Pattern

**When to Use:**
- **One row per business event** (sale, click, API call)
- **Primary Key:** Single surrogate key (`transaction_id`, `event_id`, `request_id`)
- **Measures:** Individual event metrics (amount, duration, count=1)

**Key Characteristics:**
- ✅ No `.groupBy()` or `.agg()` in merge script
- ✅ Single surrogate key as PRIMARY KEY
- ✅ Measures are direct pass-through (no SUM, AVG, COUNT)
- ✅ One source row → one target row

### Aggregated Fact Pattern

**When to Use:**
- **Pre-aggregated summaries** (daily sales, hourly usage)
- **Primary Key:** Composite key of dimensions defining grain (`date_key, store_key, product_key`)
- **Measures:** Aggregated metrics (total_revenue, avg_latency, request_count)

**Key Characteristics:**
- ✅ Uses `.groupBy()` on grain dimensions
- ✅ Uses `.agg()` with SUM, COUNT, AVG, MAX
- ✅ Composite PRIMARY KEY matches `.groupBy()` columns
- ✅ Multiple source rows → one target row per grain

### Snapshot Fact Pattern

**When to Use:**
- **Point-in-time state** (daily inventory levels, account balances)
- **Primary Key:** Entity + date (`entity_key, snapshot_date_key`)
- **Measures:** Current values at snapshot time (on_hand_quantity, balance_amount)

**Key Characteristics:**
- ✅ No aggregation (snapshots already at correct grain)
- ✅ May need deduplication (latest snapshot wins)
- ✅ Composite PK: entity keys + snapshot date
- ✅ Measures are point-in-time values (not SUMs)

## Quick Patterns

### Pre-Merge Validation

Always validate grain BEFORE merge:

```python
def merge_fact_sales_daily(spark, catalog, silver_schema, gold_schema):
    """Merge daily sales with grain validation."""
    
    # Aggregate to daily grain
    daily_sales_df = transactions_df.groupBy(...).agg(...)
    
    # ✅ Validate grain BEFORE merge
    validate_fact_grain(
        spark, daily_sales_df, catalog, gold_schema,
        "fact_sales_daily",
        ["date_key", "store_key", "product_key"]
    )
    
    # Proceed with merge
    merge_fact_table(...)
```

## Common Mistakes to Avoid

### ❌ Mistake 1: Aggregated DDL, Transaction Script

```python
# DDL (Aggregated)
PRIMARY KEY (date_key, endpoint_key, model_key)

# Script (Transaction - WRONG!)
updates_df = df.select("request_id", ...)  # ❌ Transaction ID
merge_fact_table(..., ["request_id"])      # ❌ Wrong grain!
```

**Fix:** Aggregate to match DDL grain:
```python
# ✅ CORRECT: Aggregate to match DDL
updates_df = df.groupBy("date_key", "endpoint_key", "model_key").agg(...)
merge_fact_table(..., ["date_key", "endpoint_key", "model_key"])
```

### ❌ Mistake 2: Transaction DDL, Aggregated Script

```python
# DDL (Transaction)
PRIMARY KEY (query_key)

# Script (Aggregated - WRONG!)
updates_df = df.groupBy("query_key").agg(count("*"))  # ❌ Why aggregate?
merge_fact_table(..., ["query_key"])
```

**Fix:** Pass through individual records:
```python
# ✅ CORRECT: No aggregation for transaction grain
updates_df = df.select("query_key", "execution_duration_ms", ...)
merge_fact_table(..., ["query_key"])
```

### ❌ Mistake 3: Ambiguous YAML Grain

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

**Fix:** Document grain explicitly:
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
```

## Validation Checklist

Before writing any fact table merge script:

### Pre-Development
- [ ] Read DDL to identify PRIMARY KEY columns
- [ ] Infer grain type from PRIMARY KEY structure
- [ ] Document grain in code comments
- [ ] Determine if aggregation is required

### During Development
- [ ] If composite PK: use `.groupBy()` on PK columns
- [ ] If single PK: pass through individual records (no aggregation)
- [ ] Verify measures match grain (aggregated vs individual)
- [ ] Use grain validation function before merge

### Pre-Deployment
- [ ] Validate PRIMARY KEY matches merge script
- [ ] Check for duplicate rows at grain level
- [ ] Verify measures are correctly aggregated (if needed)
- [ ] Test with sample data

### Post-Deployment
- [ ] Verify row counts match expected grain
- [ ] Check for NULL values in PRIMARY KEY columns
- [ ] Validate measures are within expected ranges
- [ ] Monitor for merge conflicts

## Grain Documentation Template

```python
def merge_fact_[table_name](spark, catalog, silver_schema, gold_schema):
    """
    Merge fact_[table_name] from Silver to Gold.
    
    GRAIN: [Describe grain in plain English]
    - Example: "One row per date-store-product combination (daily aggregate)"
    - Example: "One row per individual query execution (transaction level)"
    
    PRIMARY KEY: [List PK columns]
    - Example: (date_key, store_key, product_key)
    - Example: (query_key)
    
    GRAIN TYPE: [transaction | aggregated | snapshot]
    
    AGGREGATION: [Required | Not Required]
    - If Required: GroupBy on [dimensions], Aggregate [measures]
    """
    
    # Implementation matching documented grain
    ...
```

## Reference Files

- **[Grain Patterns](references/grain-patterns.md)** - Detailed grain analysis, validation SQL, transaction/aggregated/snapshot patterns, and common mistakes. Includes complete implementation examples, validation SQL queries, and extended pattern documentation.
- **[Validate Grain Script](scripts/validate_grain.py)** - Grain validation utility with `infer_grain_type()` and `validate_fact_grain()` functions for pre-merge validation

## Related Patterns

- **Gold Layer Schema Validation** - Schema validation patterns
- **Gold Merge Deduplication** - Deduplication patterns for Gold layer
- **Unity Catalog Constraints** - PK/FK constraint patterns

## References

- [Rule Improvement Case Study](../../docs/reference/rule-improvement-gold-layer-debugging.md) - Gold layer debugging methodology
- [Kimball Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/) - Grain definition
- [Delta Lake Merge](https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge) - Merge semantics

**Last Updated:** December 2, 2025  
**Pattern Origin:** Bug #84 (wrong fact table grain), 2% of Gold bugs but high impact  
**Key Lesson:** DDL PRIMARY KEY reveals grain. Composite PK = aggregated, single PK = transaction.  
**Impact:** Prevents costly table rewrites by catching grain mismatches before deployment

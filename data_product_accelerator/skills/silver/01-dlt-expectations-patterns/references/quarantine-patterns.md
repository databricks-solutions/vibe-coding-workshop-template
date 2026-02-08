# DLT Quarantine Patterns

## Quarantine Table Pattern

Quarantine tables capture records that fail critical data quality checks, allowing you to:
- Investigate data quality issues without blocking pipeline execution
- Remediate and reprocess failed records
- Track data quality trends over time
- Maintain audit trail of validation failures

## Standard Quarantine Implementation

### Pattern: Separate Quarantine Table

```python
@dlt.table(
    name="silver_transactions_quarantine",
    comment="""LLM: Quarantine table for transactions that failed CRITICAL data quality checks. 
    Filter condition dynamically loaded from dq_rules Delta table.""",
    table_properties={
        "quality": "quarantine",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "layer": "silver",
        "source_table": "bronze_transactions",
        "domain": "sales",
        "entity_type": "quarantine"
    },
    cluster_by_auto=True
)
def silver_transactions_quarantine():
    """
    Quarantine table with filter condition generated from dq_rules table.
    
    Records captured when they fail ANY critical rule.
    Filter condition is inverse of all critical rules.
    """
    from dq_rules_loader import get_quarantine_condition
    
    return (
        dlt.read_stream(get_bronze_table("bronze_transactions"))
        # Dynamically generated filter from dq_rules table
        .filter(get_quarantine_condition("silver_transactions"))
        .withColumn("quarantine_reason",
            when(col("transaction_id").isNull(), "CRITICAL: Missing transaction ID")
            .when(col("store_number").isNull(), "CRITICAL: Missing store number")
            .when(col("quantity_sold") == 0, "CRITICAL: Zero quantity")
            .otherwise("CRITICAL: Multiple validation failures"))
        .withColumn("quarantine_timestamp", current_timestamp())
    )
```

## Quarantine Condition Generation

### Using `get_quarantine_condition()`

The `get_quarantine_condition()` function generates a SQL WHERE clause that evaluates to TRUE for records that fail ANY critical rule:

```python
from dq_rules_loader import get_quarantine_condition

# Get quarantine condition for a table
condition = get_quarantine_condition("silver_transactions")
# Returns: "NOT (transaction_id IS NOT NULL) OR NOT (store_number IS NOT NULL) OR ..."

# Use in filter
quarantine_df = source_df.filter(condition)
```

**How it works:**
1. Loads all critical rules for the table from cache
2. Inverts each rule constraint (wraps in `NOT (...)`)
3. Combines with `OR` to capture records failing ANY rule

### Manual Quarantine Condition

If you need more control, you can build the condition manually:

```python
from dq_rules_loader import get_critical_rules_for_table

critical_rules = get_critical_rules_for_table("silver_transactions")

# Build custom condition
quarantine_conditions = []
for rule_name, constraint in critical_rules.items():
    if rule_name == "valid_transaction_id":
        # Custom handling for specific rule
        quarantine_conditions.append(f"NOT ({constraint})")
    else:
        quarantine_conditions.append(f"NOT ({constraint})")

custom_condition = " OR ".join(quarantine_conditions)
```

## Quarantine Metadata Enrichment

### Adding Failure Reasons

Enrich quarantine records with specific failure reasons:

```python
@dlt.table(name="silver_transactions_quarantine")
def silver_transactions_quarantine():
    from dq_rules_loader import get_critical_rules_for_table
    
    critical_rules = get_critical_rules_for_table("silver_transactions")
    
    df = dlt.read_stream(get_bronze_table("bronze_transactions"))
    
    # Build failure reason column
    failure_reason = None
    for rule_name, constraint in critical_rules.items():
        condition = f"NOT ({constraint})"
        if failure_reason is None:
            failure_reason = when(expr(condition), lit(f"FAILED: {rule_name}"))
        else:
            failure_reason = failure_reason.when(expr(condition), lit(f"FAILED: {rule_name}"))
    
    failure_reason = coalesce(failure_reason, lit("UNKNOWN"))
    
    return (
        df.filter(get_quarantine_condition("silver_transactions"))
        .withColumn("quarantine_reason", failure_reason)
        .withColumn("quarantine_timestamp", current_timestamp())
        .withColumn("requires_review", lit(True))
    )
```

### Adding Multiple Failure Reasons

For records that fail multiple rules:

```python
from pyspark.sql.functions import array, when, lit, col, expr

@dlt.table(name="silver_transactions_quarantine")
def silver_transactions_quarantine():
    from dq_rules_loader import get_critical_rules_for_table
    
    critical_rules = get_critical_rules_for_table("silver_transactions")
    
    df = dlt.read_stream(get_bronze_table("bronze_transactions"))
    
    # Build array of failed rule names
    failed_rules = []
    for rule_name, constraint in critical_rules.items():
        condition = f"NOT ({constraint})"
        failed_rules.append(
            when(expr(condition), lit(rule_name)).otherwise(None)
        )
    
    # Combine into array (filters out NULLs)
    failed_rules_array = array([r for r in failed_rules if r is not None])
    
    return (
        df.filter(get_quarantine_condition("silver_transactions"))
        .withColumn("failed_rules", failed_rules_array)
        .withColumn("failure_count", size(col("failed_rules")))
        .withColumn("quarantine_timestamp", current_timestamp())
    )
```

## Quarantine Remediation Patterns

### Pattern 1: Reprocess After Fix

```python
# Remediate records in quarantine table
fixed_records = (
    spark.table(f"{catalog}.{schema}.silver_transactions_quarantine")
    .filter("quarantine_timestamp >= '2025-01-01'")
    .withColumn("transaction_id", 
        when(col("transaction_id").isNull(), 
             concat_ws("-", col("store_number"), col("transaction_timestamp")))
        .otherwise(col("transaction_id")))
    .drop("quarantine_reason", "quarantine_timestamp", "requires_review")
)

# Write back to Bronze for reprocessing
fixed_records.write.format("delta").mode("append").saveAsTable(
    f"{catalog}.{bronze_schema}.bronze_transactions"
)
```

### Pattern 2: Manual Review Workflow

```python
# Mark records for manual review
spark.sql(f"""
    UPDATE {catalog}.{schema}.silver_transactions_quarantine
    SET review_status = 'PENDING',
        assigned_to = 'data-eng@company.com',
        review_priority = CASE 
            WHEN failed_rules[0] = 'valid_transaction_id' THEN 'HIGH'
            ELSE 'MEDIUM'
        END
    WHERE review_status IS NULL
""")
```

### Pattern 3: Automated Remediation Rules

```python
# Apply automated fixes based on failure type
remediated = (
    spark.table(f"{catalog}.{schema}.silver_transactions_quarantine")
    .withColumn("transaction_id",
        when(col("quarantine_reason").contains("Missing transaction ID"),
             concat_ws("-", col("store_number"), col("transaction_timestamp")))
        .otherwise(col("transaction_id")))
    .withColumn("quantity_sold",
        when(col("quarantine_reason").contains("Zero quantity"),
             lit(1))  # Default to 1 for zero quantities
        .otherwise(col("quantity_sold")))
    .filter("NOT (quarantine_reason LIKE '%transaction_id%' OR quarantine_reason LIKE '%quantity%')")
    .drop("quarantine_reason", "quarantine_timestamp")
)

# Reprocess remediated records
remediated.write.format("delta").mode("append").saveAsTable(
    f"{catalog}.{bronze_schema}.bronze_transactions"
)
```

## Quarantine Monitoring

### Query Quarantine Statistics

```sql
-- Daily quarantine counts by reason
SELECT 
    DATE(quarantine_timestamp) as quarantine_date,
    quarantine_reason,
    COUNT(*) as record_count
FROM {catalog}.{schema}.silver_transactions_quarantine
WHERE quarantine_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
GROUP BY DATE(quarantine_timestamp), quarantine_reason
ORDER BY quarantine_date DESC, record_count DESC;

-- Quarantine rate trend
SELECT 
    DATE(quarantine_timestamp) as quarantine_date,
    COUNT(*) as quarantined_records,
    COUNT(DISTINCT DATE_TRUNC('hour', quarantine_timestamp)) as hours_with_quarantine
FROM {catalog}.{schema}.silver_transactions_quarantine
GROUP BY DATE(quarantine_timestamp)
ORDER BY quarantine_date DESC;

-- Top failure reasons
SELECT 
    quarantine_reason,
    COUNT(*) as failure_count,
    COUNT(DISTINCT DATE(quarantine_timestamp)) as days_affected
FROM {catalog}.{schema}.silver_transactions_quarantine
GROUP BY quarantine_reason
ORDER BY failure_count DESC
LIMIT 10;
```

### Alerting on Quarantine Thresholds

```python
# Check if quarantine rate exceeds threshold
quarantine_stats = spark.sql(f"""
    SELECT 
        COUNT(*) as quarantined_count,
        (SELECT COUNT(*) FROM {catalog}.{schema}.silver_transactions 
         WHERE processed_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR) as total_count
    FROM {catalog}.{schema}.silver_transactions_quarantine
    WHERE quarantine_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
""").collect()[0]

quarantine_rate = quarantine_stats['quarantined_count'] / max(quarantine_stats['total_count'], 1)

if quarantine_rate > 0.05:  # 5% threshold
    # Send alert
    print(f"⚠️ ALERT: Quarantine rate {quarantine_rate:.2%} exceeds 5% threshold")
```

## Common Mistakes to Avoid

### ❌ Mistake 1: Quarantine table not filtered correctly

```python
# ❌ WRONG: Captures all records, not just failures
@dlt.table(name="silver_transactions_quarantine")
def silver_transactions_quarantine():
    return dlt.read_stream(get_bronze_table("bronze_transactions"))
    # Missing filter!
```

**Fix:** Always use `get_quarantine_condition()` or equivalent filter

### ❌ Mistake 2: Quarantine table missing metadata

```python
# ❌ WRONG: No reason or timestamp
@dlt.table(name="silver_transactions_quarantine")
def silver_transactions_quarantine():
    return dlt.read_stream(get_bronze_table("bronze_transactions")).filter(...)
    # Missing quarantine_reason and quarantine_timestamp
```

**Fix:** Add `quarantine_reason` and `quarantine_timestamp` columns

### ❌ Mistake 3: Quarantine table not queryable

```python
# ❌ WRONG: Using view instead of table
@dlt.view(name="silver_transactions_quarantine")
def silver_transactions_quarantine():
    # Views don't persist data
```

**Fix:** Use `@dlt.table()` for quarantine tables

### ❌ Mistake 4: Not handling multiple failures

```python
# ❌ WRONG: Only captures first failure
.withColumn("quarantine_reason", 
    when(col("transaction_id").isNull(), "Missing ID")
    .otherwise("Other"))
```

**Fix:** Use array column or concatenate multiple reasons

# Deduplication Patterns - Detailed Reference

## Generic Reusable Function

```python
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col

def deduplicate_silver(
    spark: SparkSession,
    silver_table: str,
    business_key: str,
    timestamp_col: str = "processed_timestamp"
) -> DataFrame:
    """
    Generic deduplication function for Silver tables.
    
    Args:
        spark: SparkSession
        silver_table: Full table name (catalog.schema.table)
        business_key: Column name for business key
        timestamp_col: Column name for timestamp (default: processed_timestamp)
    
    Returns:
        Deduplicated DataFrame
    """
    silver_raw = spark.table(silver_table)
    
    return (
        silver_raw
        .orderBy(col(timestamp_col).desc())
        .dropDuplicates([business_key])
    )
```

## Complete Scenario Examples

### Scenario 1: Dimension Table (SCD Type 1)
See SKILL.md Pattern 1 for complete example.

### Scenario 2: Dimension Table (SCD Type 2)
See SKILL.md Pattern 2 for complete example.

### Scenario 3: Fact Table with Composite Key
See SKILL.md Pattern 3 for complete example.

## Troubleshooting Patterns

### Issue: Still Getting Duplicate Key Errors

**Check:**
1. Deduplication key matches MERGE key exactly
2. OrderBy is applied before dropDuplicates
3. No additional duplicates introduced during transformations

**Debug:**
```python
# Check for duplicates after deduplication
duplicate_check = (
    silver_df
    .groupBy(business_key)
    .count()
    .filter(col("count") > 1)
)
if duplicate_check.count() > 0:
    print("WARNING: Duplicates still exist!")
    duplicate_check.show()
```

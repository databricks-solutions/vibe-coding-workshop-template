# Schema Validation Rules - Detailed Implementation

## Complete Schema Inspector Implementation

### validate_merge_schema Function

```python
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField
from typing import Dict, List, Tuple

def validate_merge_schema(
    spark: SparkSession,
    updates_df: DataFrame,
    catalog: str,
    schema: str,
    table_name: str,
    raise_on_mismatch: bool = True
) -> Dict:
    """
    Validate that DataFrame columns match target table schema before merge.
    
    Args:
        spark: SparkSession
        updates_df: DataFrame to validate
        catalog: Unity Catalog catalog name
        schema: Schema name
        table_name: Table name
        raise_on_mismatch: If True, raise ValueError on mismatch
    
    Returns:
        dict with validation results
    """
    full_table_name = f"{catalog}.{schema}.{table_name}"
    
    # Get target table schema
    try:
        target_table = spark.table(full_table_name)
        target_schema = target_table.schema
    except Exception as e:
        if raise_on_mismatch:
            raise ValueError(f"Target table {full_table_name} does not exist: {e}")
        return {'valid': False, 'error': f"Table not found: {e}"}
    
    # Get DataFrame schema
    df_schema = updates_df.schema
    
    # Extract column names and types
    df_columns = {field.name: field.dataType for field in df_schema.fields}
    table_columns = {field.name: field.dataType for field in target_schema.fields}
    
    # Find mismatches
    missing_in_df = [col for col in table_columns.keys() if col not in df_columns]
    extra_in_df = [col for col in df_columns.keys() if col not in table_columns]
    
    # Check type mismatches
    type_mismatches = []
    common_columns = set(df_columns.keys()) & set(table_columns.keys())
    for col in common_columns:
        df_type = str(df_columns[col])
        table_type = str(table_columns[col])
        if df_type != table_type:
            type_mismatches.append({
                'column': col,
                'df_type': df_type,
                'table_type': table_type
            })
    
    # Determine if valid
    valid = len(missing_in_df) == 0 and len(extra_in_df) == 0 and len(type_mismatches) == 0
    
    result = {
        'valid': valid,
        'missing_in_df': missing_in_df,
        'extra_in_df': extra_in_df,
        'type_mismatches': type_mismatches,
        'df_columns': list(df_columns.keys()),
        'table_columns': list(table_columns.keys())
    }
    
    # Raise if mismatch
    if not valid and raise_on_mismatch:
        error_msg = f"Schema mismatch for {full_table_name}:\n"
        if missing_in_df:
            error_msg += f"  Missing columns: {missing_in_df}\n"
        if extra_in_df:
            error_msg += f"  Extra columns: {extra_in_df}\n"
        if type_mismatches:
            error_msg += f"  Type mismatches: {type_mismatches}\n"
        raise ValueError(error_msg)
    
    return result
```

## DDL Schema Reader Patterns

See SKILL.md for usage examples. This reference contains the complete implementation details.

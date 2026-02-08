# Gold Layer Schema Validation Patterns - Detailed Reference

This document provides detailed validation patterns, complete code implementations, and comprehensive workflows for Gold layer schema validation.

## Complete Schema Validation Helper Implementation

### Full Implementation

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
    Validate that DataFrame columns match target table schema.
    
    Args:
        spark: SparkSession
        updates_df: DataFrame to validate
        catalog: Unity Catalog catalog name
        schema: Schema name
        table_name: Table name
        raise_on_mismatch: If True, raise ValueError on mismatch
        
    Returns:
        Dict with validation results:
        - valid: bool
        - missing_in_df: List[str] - columns in DDL but not in DataFrame
        - extra_in_df: List[str] - columns in DataFrame but not in DDL
        - type_mismatches: List[Dict] - columns with type differences
        
    Raises:
        ValueError: If raise_on_mismatch=True and schemas don't match
    """
    # Read target table schema
    target_table = f"{catalog}.{schema}.{table_name}"
    target_schema = spark.table(target_table).schema
    
    # Get column names and types
    target_columns = {field.name: field.dataType for field in target_schema.fields}
    source_columns = {field.name: field.dataType for field in updates_df.schema.fields}
    
    # Find differences
    missing_in_df = [col for col in target_columns if col not in source_columns]
    extra_in_df = [col for col in source_columns if col not in target_columns]
    
    # Find type mismatches (only for columns that exist in both)
    type_mismatches = []
    common_columns = set(target_columns.keys()) & set(source_columns.keys())
    for col_name in common_columns:
        target_type = str(target_columns[col_name])
        source_type = str(source_columns[col_name])
        if target_type != source_type:
            type_mismatches.append({
                "column": col_name,
                "target_type": target_type,
                "source_type": source_type
            })
    
    # Build result
    result = {
        "valid": len(missing_in_df) == 0 and len(extra_in_df) == 0 and len(type_mismatches) == 0,
        "missing_in_df": missing_in_df,
        "extra_in_df": extra_in_df,
        "type_mismatches": type_mismatches,
        "target_table": target_table
    }
    
    # Raise if mismatch and flag is set
    if not result["valid"] and raise_on_mismatch:
        error_msg = f"Schema mismatch for {target_table}:\n"
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

### Pattern 1: Read Schema from Table

```python
def get_table_schema(spark: SparkSession, catalog: str, schema: str, table_name: str) -> Dict:
    """Read complete schema from actual table."""
    table = spark.table(f"{catalog}.{schema}.{table_name}")
    schema_dict = {
        "table_name": table_name,
        "columns": [
            {
                "name": field.name,
                "type": str(field.dataType),
                "nullable": field.nullable,
                "metadata": field.metadata
            }
            for field in table.schema.fields
        ]
    }
    return schema_dict
```

### Pattern 2: Compare Schema with YAML

```python
import yaml
from pathlib import Path

def compare_schema_with_yaml(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str,
    yaml_path: Path
) -> Dict:
    """Compare actual table schema with YAML design."""
    # Read actual schema
    actual_schema = get_table_schema(spark, catalog, schema, table_name)
    
    # Read YAML design
    with open(yaml_path) as f:
        yaml_design = yaml.safe_load(f)
    
    # Compare
    yaml_columns = {col["name"] for col in yaml_design.get("columns", [])}
    actual_columns = {col["name"] for col in actual_schema["columns"]}
    
    return {
        "yaml_only": yaml_columns - actual_columns,
        "actual_only": actual_columns - yaml_columns,
        "matches": yaml_columns & actual_columns
    }
```

## Column Mapping Documentation Patterns

### Pattern 1: Inline Documentation

```python
def merge_dim_store(spark, catalog, silver_schema, gold_schema):
    """
    Merge dim_store from Silver to Gold.
    
    Column Mapping (Silver → Gold):
    - store_number → store_number (same)
    - company_rcn → company_retail_control_number (renamed)
    - processed_timestamp → record_updated_timestamp (renamed)
    - store_name → store_name (same)
    - address_line_1 → address_line_1 (same)
    """
    silver_table = f"{catalog}.{silver_schema}.silver_store_dim"
    silver_df = spark.table(silver_table)
    
    updates_df = (
        silver_df
        .withColumn("company_retail_control_number", col("company_rcn"))
        .withColumn("record_updated_timestamp", col("processed_timestamp"))
        .select(
            "store_number",
            "company_retail_control_number",
            "record_updated_timestamp",
            "store_name",
            "address_line_1"
        )
    )
    
    # Validate before merge
    validate_merge_schema(spark, updates_df, catalog, gold_schema, "dim_store")
    
    # Proceed with merge
    delta_gold = DeltaTable.forName(spark, f"{catalog}.{gold_schema}.dim_store")
    delta_gold.alias("target").merge(
        updates_df.alias("source"),
        "target.store_number = source.store_number"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

### Pattern 2: Mapping Dictionary

```python
def build_column_mapping(silver_table: str, gold_table: str) -> Dict[str, str]:
    """
    Build explicit column mapping dictionary.
    
    Returns:
        Dict mapping Silver column names to Gold column names
    """
    # Read schemas
    silver_schema = spark.table(silver_table).schema
    gold_schema = spark.table(gold_table).schema
    
    silver_cols = {field.name for field in silver_schema.fields}
    gold_cols = {field.name for field in gold_schema.fields}
    
    # Build mapping (direct matches + explicit renames)
    mapping = {}
    
    # Direct matches
    for col_name in silver_cols & gold_cols:
        mapping[col_name] = col_name
    
    # Document unmapped columns
    unmapped_silver = silver_cols - gold_cols
    unmapped_gold = gold_cols - silver_cols
    
    return {
        "mapping": mapping,
        "unmapped_silver": unmapped_silver,
        "unmapped_gold": unmapped_gold
    }
```

## Pre-Merge Validation Workflows

### Complete Validation Workflow

```python
def validate_before_merge(
    spark: SparkSession,
    updates_df: DataFrame,
    catalog: str,
    schema: str,
    table_name: str
) -> bool:
    """
    Complete pre-merge validation workflow.
    
    Returns:
        True if validation passes, False otherwise
    """
    print(f"Validating schema for {catalog}.{schema}.{table_name}...")
    
    # Step 1: Schema validation
    try:
        result = validate_merge_schema(
            spark, updates_df, catalog, schema, table_name,
            raise_on_mismatch=True
        )
        print("✓ Schema validation passed")
    except ValueError as e:
        print(f"✗ Schema validation failed: {e}")
        return False
    
    # Step 2: Check for NULLs in NOT NULL columns
    target_table = spark.table(f"{catalog}.{schema}.{table_name}")
    not_null_columns = [
        field.name for field in target_table.schema.fields
        if not field.nullable
    ]
    
    for col_name in not_null_columns:
        if col_name in updates_df.columns:
            null_count = updates_df.filter(col(col_name).isNull()).count()
            if null_count > 0:
                print(f"⚠ Warning: {null_count} NULL values in NOT NULL column {col_name}")
    
    # Step 3: Data type compatibility check
    for mismatch in result.get("type_mismatches", []):
        print(f"⚠ Type mismatch: {mismatch['column']} - "
              f"target: {mismatch['target_type']}, "
              f"source: {mismatch['source_type']}")
    
    return True
```

## Error Handling Patterns

### Pattern 1: Graceful Validation with Warnings

```python
def validate_with_warnings(
    spark: SparkSession,
    updates_df: DataFrame,
    catalog: str,
    schema: str,
    table_name: str,
    strict: bool = False
) -> Dict:
    """
    Validate schema with optional warnings instead of errors.
    
    Args:
        strict: If True, treat warnings as errors
        
    Returns:
        Validation result dict
    """
    result = validate_merge_schema(
        spark, updates_df, catalog, schema, table_name,
        raise_on_mismatch=False  # Don't raise, collect warnings
    )
    
    warnings = []
    if result["missing_in_df"]:
        warnings.append(f"Missing columns: {result['missing_in_df']}")
    if result["extra_in_df"]:
        warnings.append(f"Extra columns: {result['extra_in_df']}")
    if result["type_mismatches"]:
        warnings.append(f"Type mismatches: {result['type_mismatches']}")
    
    if warnings:
        warning_msg = "\n".join(warnings)
        if strict:
            raise ValueError(f"Schema validation warnings:\n{warning_msg}")
        else:
            print(f"⚠ Schema validation warnings:\n{warning_msg}")
    
    return result
```

## Testing Patterns

### Pattern 1: Unit Test Schema Validation

```python
def test_schema_validation():
    """Test schema validation helper."""
    # Create test DataFrame
    test_df = spark.createDataFrame([
        ("store1", "Company A", "2025-01-01"),
    ], schema="store_number STRING, company_name STRING, date STRING")
    
    # Create test table
    spark.sql("""
        CREATE OR REPLACE TABLE test_catalog.test_schema.test_table (
            store_number STRING NOT NULL,
            company_name STRING,
            date DATE
        )
    """)
    
    # Validate (should catch type mismatch: STRING vs DATE)
    result = validate_merge_schema(
        spark, test_df, "test_catalog", "test_schema", "test_table",
        raise_on_mismatch=False
    )
    
    assert not result["valid"]
    assert len(result["type_mismatches"]) > 0
```

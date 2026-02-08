"""
Fact Table Grain Validation Utility

Validates that merge DataFrame grain matches DDL PRIMARY KEY to prevent
costly table rewrites from grain mismatches.
"""

import re
from typing import List, Dict, Any
from pyspark.sql import SparkSession, DataFrame


def infer_grain_from_ddl(spark: SparkSession, catalog: str, schema: str, table_name: str) -> Dict[str, Any]:
    """
    Infer fact table grain from PRIMARY KEY definition.
    
    Returns:
        dict with 'grain_type', 'primary_keys', 'is_aggregated'
    """
    # Get table DDL
    ddl = spark.sql(f"SHOW CREATE TABLE {catalog}.{schema}.{table_name}").collect()[0][0]
    
    # Extract PRIMARY KEY columns
    pk_match = re.search(r'PRIMARY KEY \((.*?)\)', ddl)
    if not pk_match:
        return {'grain_type': 'unknown', 'primary_keys': [], 'is_aggregated': False}
    
    pk_cols = [col.strip() for col in pk_match.group(1).split(',')]
    
    # Infer grain type
    if len(pk_cols) == 1:
        # Single column PK
        col_name = pk_cols[0].lower()
        if any(suffix in col_name for suffix in ['_id', '_key', '_uid']):
            grain_type = 'transaction'
            is_aggregated = False
        else:
            grain_type = 'unknown'
            is_aggregated = False
    else:
        # Composite PK
        has_date = any('date' in col.lower() for col in pk_cols)
        has_dimension = any('_key' in col.lower() for col in pk_cols)
        
        if has_date and has_dimension:
            grain_type = 'aggregated'
            is_aggregated = True
        else:
            grain_type = 'composite'
            is_aggregated = False
    
    return {
        'grain_type': grain_type,
        'primary_keys': pk_cols,
        'is_aggregated': is_aggregated
    }


def validate_fact_grain(
    spark: SparkSession,
    updates_df: DataFrame,
    catalog: str,
    schema: str,
    table_name: str,
    expected_primary_keys: List[str]
):
    """
    Validate that merge DataFrame grain matches DDL PRIMARY KEY.
    
    Args:
        spark: SparkSession instance
        updates_df: DataFrame to be merged
        catalog: Catalog name
        schema: Schema name
        table_name: Table name
        expected_primary_keys: List of PK columns from merge_fact_table() call
    
    Raises:
        ValueError if grain mismatch detected
    """
    # Get DDL primary keys
    grain_info = infer_grain_from_ddl(spark, catalog, schema, table_name)
    ddl_pk = grain_info['primary_keys']
    
    # Compare
    if set(expected_primary_keys) != set(ddl_pk):
        raise ValueError(
            f"Grain mismatch for {table_name}!\n"
            f"  DDL PRIMARY KEY: {ddl_pk}\n"
            f"  Merge script PK: {expected_primary_keys}\n"
            f"  Grain type: {grain_info['grain_type']}\n"
            f"  Expected aggregation: {grain_info['is_aggregated']}"
        )
    
    # If aggregated grain, verify DataFrame has aggregation
    if grain_info['is_aggregated']:
        # Check if DataFrame has duplicate grain combinations
        distinct_grain_count = updates_df.select(*expected_primary_keys).distinct().count()
        total_row_count = updates_df.count()
        
        if distinct_grain_count != total_row_count:
            raise ValueError(
                f"Aggregation required for {table_name}!\n"
                f"  Grain: {expected_primary_keys}\n"
                f"  Distinct grain combinations: {distinct_grain_count}\n"
                f"  Total rows: {total_row_count}\n"
                f"  → DataFrame has duplicates at grain level. Apply .groupBy().agg()"
            )
    
    print(f"✓ Grain validation passed for {table_name}")
    print(f"  Grain: {expected_primary_keys}")
    print(f"  Type: {grain_info['grain_type']}")

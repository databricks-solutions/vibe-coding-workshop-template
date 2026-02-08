"""
Constraint Application Utility for Unity Catalog Gold Layer Tables

This script applies PRIMARY KEY and FOREIGN KEY constraints to Gold layer tables
following proper dimensional modeling patterns.

Strategy:
- Define PKs on surrogate keys (proper dimensional modeling)
- Facts reference dimension surrogate keys via FK constraints
- All constraints are NOT ENFORCED (informational only)
"""

from pyspark.sql import SparkSession
from typing import List, Dict, Optional


def add_primary_key(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str,
    pk_columns: List[str],
    constraint_name: Optional[str] = None
):
    """Add PRIMARY KEY constraint to table.
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        schema: Schema name
        table_name: Table name
        pk_columns: List of column names forming the primary key
        constraint_name: Optional constraint name (defaults to pk_{table_name})
    """
    fqn = f"{catalog}.{schema}.{table_name}"
    
    if constraint_name is None:
        constraint_name = f"pk_{table_name}"
    
    pk_cols = ", ".join(pk_columns)
    spark.sql(f"""
        ALTER TABLE {fqn}
        ADD CONSTRAINT {constraint_name} PRIMARY KEY ({pk_cols}) NOT ENFORCED
    """)
    print(f"  ✓ Added PK: {constraint_name} on {table_name}({pk_cols})")


def add_foreign_key(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str,
    fk_columns: List[str],
    referenced_table: str,
    referenced_columns: List[str],
    constraint_name: Optional[str] = None
):
    """Add FOREIGN KEY constraint to table.
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        schema: Schema name
        table_name: Table name (fact table)
        fk_columns: List of foreign key column names
        referenced_table: Referenced dimension table name
        referenced_columns: List of referenced PK column names
        constraint_name: Optional constraint name (defaults to fk_{table_name}_{referenced_table})
    """
    fqn = f"{catalog}.{schema}.{table_name}"
    ref_fqn = f"{catalog}.{schema}.{referenced_table}"
    
    if constraint_name is None:
        constraint_name = f"fk_{table_name}_{referenced_table}"
    
    fk_cols = ", ".join(fk_columns)
    ref_cols = ", ".join(referenced_columns)
    
    spark.sql(f"""
        ALTER TABLE {fqn}
        ADD CONSTRAINT {constraint_name}
        FOREIGN KEY ({fk_cols})
        REFERENCES {ref_fqn}({ref_cols}) NOT ENFORCED
    """)
    print(f"  ✓ Added FK: {constraint_name} ({table_name}.{fk_cols} → {referenced_table}.{ref_cols})")


def add_unique_constraint(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str,
    columns: List[str],
    constraint_name: Optional[str] = None
):
    """Add UNIQUE constraint to table (for business keys).
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        schema: Schema name
        table_name: Table name
        columns: List of column names forming the unique constraint
        constraint_name: Optional constraint name (defaults to uk_{table_name}_{first_column})
    """
    fqn = f"{catalog}.{schema}.{table_name}"
    
    if constraint_name is None:
        constraint_name = f"uk_{table_name}_{columns[0]}"
    
    cols = ", ".join(columns)
    spark.sql(f"""
        ALTER TABLE {fqn}
        ADD CONSTRAINT {constraint_name} UNIQUE ({cols}) NOT ENFORCED
    """)
    print(f"  ✓ Added UNIQUE: {constraint_name} on {table_name}({cols})")


def drop_constraint(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str,
    constraint_name: str
):
    """Drop constraint from table (for idempotency).
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        schema: Schema name
        table_name: Table name
        constraint_name: Name of constraint to drop
    """
    fqn = f"{catalog}.{schema}.{table_name}"
    try:
        spark.sql(f"ALTER TABLE {fqn} DROP CONSTRAINT IF EXISTS {constraint_name}")
        print(f"  ✓ Dropped constraint: {constraint_name} from {table_name}")
    except Exception as e:
        print(f"  ⚠ Could not drop {constraint_name} from {table_name}: {e}")


def apply_all_constraints(spark: SparkSession, catalog: str, schema: str):
    """Apply all PRIMARY KEY and FOREIGN KEY constraints to Gold layer tables.
    
    This function demonstrates the pattern for applying constraints to a star schema.
    Customize the constraint_map for your specific tables.
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        schema: Gold schema name
    """
    print("\nADDING PRIMARY KEY AND FOREIGN KEY CONSTRAINTS")
    
    # Drop existing constraints for idempotency
    constraint_map = {
        "dim_store": ["pk_dim_store", "fk_sales_store", "fk_inventory_store"],
        "dim_product": ["pk_dim_product", "uk_product_upc", "fk_sales_product", "fk_inventory_product"],
        "dim_date": ["pk_dim_date", "uk_date_value", "fk_sales_date"],
        "fact_sales_daily": ["pk_fact_sales_daily", "fk_sales_store", "fk_sales_product", "fk_sales_date"],
        "fact_inventory_snapshot": ["pk_fact_inventory_snapshot", "fk_inventory_store", "fk_inventory_product"]
    }
    
    for table, constraints in constraint_map.items():
        for constraint_name in constraints:
            drop_constraint(spark, catalog, schema, table, constraint_name)
    
    # Add Primary Keys on surrogate keys
    add_primary_key(spark, catalog, schema, "dim_store", ["store_key"])
    add_primary_key(spark, catalog, schema, "dim_product", ["product_key"])
    add_primary_key(spark, catalog, schema, "dim_date", ["date_key"])
    
    # Add UNIQUE constraints on business keys
    add_unique_constraint(spark, catalog, schema, "dim_product", ["upc_code"], "uk_product_upc")
    add_unique_constraint(spark, catalog, schema, "dim_date", ["date"], "uk_date_value")
    
    # Add Composite PKs on facts (surrogate keys)
    add_primary_key(
        spark, catalog, schema, "fact_sales_daily",
        ["store_key", "product_key", "date_key"],
        "pk_fact_sales_daily"
    )
    
    # Add Foreign Keys to surrogate PKs
    add_foreign_key(
        spark, catalog, schema, "fact_sales_daily",
        ["store_key"], "dim_store", ["store_key"],
        "fk_sales_store"
    )
    add_foreign_key(
        spark, catalog, schema, "fact_sales_daily",
        ["product_key"], "dim_product", ["product_key"],
        "fk_sales_product"
    )
    add_foreign_key(
        spark, catalog, schema, "fact_sales_daily",
        ["date_key"], "dim_date", ["date_key"],
        "fk_sales_date"
    )
    
    print("\n✅ All constraints added successfully!")
    print("  • PKs on surrogate keys (store_key, product_key, date_key)")
    print("  • UNIQUE constraints on business keys (upc_code, date)")
    print("  • FKs reference surrogate PKs")


# Example usage
if __name__ == "__main__":
    # Get parameters from widgets (Databricks notebook)
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    
    spark = SparkSession.builder.getOrCreate()
    
    apply_all_constraints(spark, catalog, gold_schema)

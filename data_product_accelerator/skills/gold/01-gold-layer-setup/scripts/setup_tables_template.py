# Databricks notebook source

"""
{Project} Gold Layer - Table Setup (YAML-Driven)

Creates Gold layer tables dynamically from YAML schema definitions.

YAML is the single source of truth:
- Column definitions
- Primary keys
- Comments and descriptions
- Table properties

This script is generic and reusable across all domains.

Usage:
  databricks bundle run gold_setup_job -t dev
"""

import yaml
from pathlib import Path
from pyspark.sql import SparkSession


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    domain = dbutils.widgets.get("domain")  # 'all' or specific domain

    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Domain: {domain}")

    return catalog, gold_schema, domain


# Standard table properties for all Gold tables
STANDARD_PROPERTIES = {
    "delta.enableChangeDataFeed": "true",
    "delta.enableRowTracking": "true",
    "delta.enableDeletionVectors": "true",
    "delta.autoOptimize.autoCompact": "true",
    "delta.autoOptimize.optimizeWrite": "true",
    "layer": "gold",
}


def find_yaml_base() -> Path:
    """Find YAML directory - works in Databricks and locally."""
    possible_paths = [
        Path("../../gold_layer_design/yaml"),
        Path("gold_layer_design/yaml"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    raise FileNotFoundError(
        "YAML directory not found. Ensure YAMLs are synced in databricks.yml"
    )


def load_yaml(path: Path) -> dict:
    """Load and parse YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def escape_sql_string(s: str) -> str:
    """Escape single quotes for SQL."""
    return s.replace("'", "''") if s else ""


def build_create_table_ddl(catalog: str, schema: str, config: dict) -> str:
    """
    Build CREATE TABLE DDL from YAML config.

    Args:
        catalog: Unity Catalog name
        schema: Schema name
        config: Parsed YAML configuration

    Returns:
        Complete CREATE OR REPLACE TABLE DDL statement
    """
    table_name = config["table_name"]
    columns = config.get("columns", [])
    description = config.get("description", "")
    domain = config.get("domain", "unknown")
    grain = config.get("grain", "")

    # Build column DDL
    col_ddls = []
    for col_def in columns:
        null_str = "" if col_def.get("nullable", True) else " NOT NULL"
        desc = escape_sql_string(col_def.get("description", ""))
        comment = f"\n        COMMENT '{desc}'" if desc else ""
        col_ddls.append(f"    {col_def['name']} {col_def['type']}{null_str}{comment}")

    columns_str = ",\n".join(col_ddls)

    # Build properties
    props = STANDARD_PROPERTIES.copy()
    props["domain"] = domain
    props["entity_type"] = "dimension" if table_name.startswith("dim_") else "fact"
    props["grain"] = grain

    # Add custom properties from YAML
    table_props = config.get("table_properties", {})
    for key, value in table_props.items():
        props[key] = str(value)

    props_str = ",\n        ".join([f"'{k}' = '{v}'" for k, v in props.items()])

    return f"""CREATE OR REPLACE TABLE {catalog}.{schema}.{table_name} (
{columns_str}
)
USING DELTA
CLUSTER BY AUTO
TBLPROPERTIES (
        {props_str}
)
COMMENT '{escape_sql_string(description)}'"""


def create_table(
    spark: SparkSession, catalog: str, schema: str, yaml_path: Path
) -> dict:
    """
    Create a single table from YAML file.

    Args:
        spark: SparkSession
        catalog: Unity Catalog name
        schema: Schema name
        yaml_path: Path to YAML file

    Returns:
        dict with table name and status
    """
    config = load_yaml(yaml_path)
    table_name = config.get("table_name", yaml_path.stem)

    print(f"\nCreating {catalog}.{schema}.{table_name}...")

    # Create table
    ddl = build_create_table_ddl(catalog, schema, config)
    spark.sql(ddl)

    # Add primary key constraint
    pk_config = config.get("primary_key", {})
    if pk_config and pk_config.get("columns"):
        pk_cols = ", ".join(pk_config["columns"])
        try:
            spark.sql(f"""
                ALTER TABLE {catalog}.{schema}.{table_name}
                ADD CONSTRAINT pk_{table_name}
                PRIMARY KEY ({pk_cols})
                NOT ENFORCED
            """)
            print(f"  ✓ Added PRIMARY KEY ({pk_cols})")
        except Exception as e:
            print(f"  ⚠️ Warning: Could not add PK constraint: {e}")

    # Check for unique constraints on business keys
    business_key_config = config.get("business_key", {})
    if business_key_config and business_key_config.get("columns"):
        uk_cols = ", ".join(business_key_config["columns"])
        try:
            spark.sql(f"""
                ALTER TABLE {catalog}.{schema}.{table_name}
                ADD CONSTRAINT uk_{table_name}_business_key
                UNIQUE ({uk_cols})
                NOT ENFORCED
            """)
            print(f"  ✓ Added UNIQUE constraint on business key ({uk_cols})")
        except Exception as e:
            print(f"  ⚠️ Warning: Could not add UNIQUE constraint: {e}")

    print(f"✓ Created {catalog}.{schema}.{table_name}")

    return {"table": table_name, "status": "success"}


def main():
    """Main entry point for Gold layer table setup."""
    from pyspark.sql import SparkSession

    # Get parameters
    catalog, gold_schema, domain = get_parameters()

    spark = SparkSession.builder.appName("Gold Layer Setup").getOrCreate()

    print("=" * 80)
    print("GOLD LAYER TABLE SETUP (YAML-Driven)")
    print("=" * 80)

    try:
        # Ensure schema exists
        print(f"\nEnsuring catalog '{catalog}' and schema '{gold_schema}' exist...")
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{gold_schema}")

        # Enable Predictive Optimization
        spark.sql(f"""
            ALTER SCHEMA {catalog}.{gold_schema}
            SET TBLPROPERTIES (
                'databricks.pipelines.predictiveOptimizations.enabled' = 'true'
            )
        """)
        print(f"✓ Schema {catalog}.{gold_schema} ready")

        # Find YAML directory
        yaml_base = find_yaml_base()
        print(f"✓ Found YAML directory: {yaml_base}")

        # Process domains
        if domain.lower() == "all":
            domains = [d.name for d in yaml_base.iterdir() if d.is_dir()]
        else:
            domains = [domain]

        print(f"\nProcessing domains: {domains}")

        # Create tables from YAMLs
        created_tables = []
        for d in domains:
            domain_path = yaml_base / d
            if not domain_path.exists():
                print(f"⚠️ Warning: Domain '{d}' not found in YAML directory")
                continue

            yaml_files = sorted(domain_path.glob("*.yaml"))
            print(f"\n--- Domain: {d} ({len(yaml_files)} tables) ---")

            for yaml_file in yaml_files:
                result = create_table(spark, catalog, gold_schema, yaml_file)
                created_tables.append(result["table"])

        print("\n" + "=" * 80)
        print(f"✓ Created {len(created_tables)} Gold layer tables successfully!")
        print("=" * 80)
        print("\nCreated tables:")
        for table in created_tables:
            print(f"  - {table}")

        print(f"\nNext steps:")
        print(f"  1. Run add_fk_constraints job to apply foreign key constraints")
        print(f"  2. Run merge_gold_tables job to populate from Silver")

    except Exception as e:
        print(f"\n❌ Error during Gold layer setup: {str(e)}")
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    main()

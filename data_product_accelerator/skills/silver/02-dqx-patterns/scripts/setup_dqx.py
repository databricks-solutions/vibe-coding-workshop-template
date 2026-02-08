"""
DQX Setup Utility

Creates DQX quality checks Delta table and loads initial checks.
Uses the official DQEngine.save_checks() method (DQX >= 0.8.0).

Usage:
    python scripts/setup_dqx.py --catalog <catalog> --schema <schema>
    python scripts/setup_dqx.py --catalog <catalog> --schema <schema> --checks-yaml path/to/checks.yml
"""

from pyspark.sql import SparkSession
from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.config import TableChecksStorageConfig
from databricks.sdk import WorkspaceClient
import argparse
import yaml


def create_dqx_checks_table(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str = "dqx_quality_checks"
):
    """
    Create DQX quality checks Delta table for centralized governance.

    Note: DQEngine.save_checks() will auto-create the table structure,
    but this function pre-creates it with proper properties and comments.
    """
    checks_table = f"{catalog}.{schema}.{table_name}"

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {checks_table} (
            name STRING NOT NULL COMMENT 'Unique check name',
            criticality STRING NOT NULL COMMENT 'error or warn',
            check STRING NOT NULL COMMENT 'JSON check definition',
            filter STRING COMMENT 'Optional SQL filter for conditional checks',
            for_each_column STRING COMMENT 'Optional column list for for-each pattern',
            metadata STRING COMMENT 'JSON business metadata'
        )
        USING DELTA
        CLUSTER BY AUTO
        COMMENT 'DQX quality checks registry for centralized governance'
    """)

    # Enable CDF for history tracking
    spark.sql(f"""
        ALTER TABLE {checks_table}
        SET TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'layer' = 'metadata',
            'purpose' = 'dqx_quality_checks_storage'
        )
    """)

    print(f"Created DQX checks table: {checks_table}")
    return checks_table


def load_and_store_checks(
    catalog: str,
    schema: str,
    yaml_path: str,
    run_config_name: str,
    table_name: str = "dqx_quality_checks"
):
    """
    Load checks from YAML and store in Delta table using DQEngine.

    Uses the official save_checks() method which handles
    serialization and storage correctly.
    """
    dq_engine = DQEngine(WorkspaceClient())
    checks_table = f"{catalog}.{schema}.{table_name}"

    # Load checks from YAML
    with open(yaml_path, 'r') as f:
        checks = yaml.safe_load(f)

    print(f"Loaded {len(checks)} checks from {yaml_path}")

    # Save to Delta table using official DQEngine method
    dq_engine.save_checks(
        checks,
        config=TableChecksStorageConfig(
            location=checks_table,
            run_config_name=run_config_name,
            mode="overwrite"  # Replaces existing checks for this run_config
        )
    )

    print(f"Saved {len(checks)} checks to {checks_table} (run_config: {run_config_name})")
    return checks_table


def main():
    parser = argparse.ArgumentParser(description="Setup DQX quality checks table")
    parser.add_argument("--catalog", required=True, help="Unity Catalog name")
    parser.add_argument("--schema", required=True, help="Schema name")
    parser.add_argument("--table-name", default="dqx_quality_checks", help="Table name")
    parser.add_argument("--checks-yaml", default=None, help="Path to YAML checks file")
    parser.add_argument("--run-config-name", default=None, help="Run config name for storing checks")
    args = parser.parse_args()

    spark = SparkSession.builder.appName("DQX Setup").getOrCreate()

    try:
        # Step 1: Create table
        create_dqx_checks_table(
            spark=spark,
            catalog=args.catalog,
            schema=args.schema,
            table_name=args.table_name
        )

        # Step 2: Load and store checks if YAML provided
        if args.checks_yaml and args.run_config_name:
            load_and_store_checks(
                catalog=args.catalog,
                schema=args.schema,
                yaml_path=args.checks_yaml,
                run_config_name=args.run_config_name,
                table_name=args.table_name
            )

        print("\n" + "=" * 80)
        print("DQX setup complete!")
        print("=" * 80)
        print(f"\nNext steps:")
        print(f"1. Load checks: dq_engine.save_checks(checks, config=TableChecksStorageConfig(...))")
        print(f"2. Deploy pipelines with DQX validation")
        print(f"3. Query checks: SELECT * FROM {args.catalog}.{args.schema}.{args.table_name}")

    except Exception as e:
        print(f"\nError setting up DQX: {str(e)}")
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    main()

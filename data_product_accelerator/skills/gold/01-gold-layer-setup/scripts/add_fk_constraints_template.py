# Databricks notebook source

"""
{Project} Gold Layer - Add Foreign Key Constraints

Applies FK constraints from YAML definitions after all tables are created.

FK constraints must be applied AFTER all PKs exist to avoid errors.

Usage:
  databricks bundle run gold_setup_job (task 2)
"""

import yaml
from pathlib import Path
from pyspark.sql import SparkSession


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    domain = dbutils.widgets.get("domain")

    return catalog, gold_schema, domain


def find_yaml_base() -> Path:
    """Find YAML directory."""
    possible_paths = [
        Path("../../gold_layer_design/yaml"),
        Path("gold_layer_design/yaml"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    raise FileNotFoundError("YAML directory not found")


def load_yaml(path: Path) -> dict:
    """Load and parse YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_fk_constraints(
    spark: SparkSession, catalog: str, schema: str, config: dict
) -> int:
    """
    Apply FK constraints from YAML config.

    Args:
        spark: SparkSession
        catalog: Unity Catalog name
        schema: Schema name
        config: Parsed YAML configuration

    Returns:
        Number of FK constraints applied
    """
    table_name = config["table_name"]
    fks = config.get("foreign_keys", [])

    if not fks:
        return 0

    print(f"\nApplying FK constraints for {table_name}...")

    applied_count = 0
    for idx, fk in enumerate(fks):
        fk_cols = fk["columns"]
        references = fk["references"]

        fk_name = f"fk_{table_name}_{idx+1}"
        fk_cols_str = ", ".join(fk_cols)

        try:
            spark.sql(f"""
                ALTER TABLE {catalog}.{schema}.{table_name}
                ADD CONSTRAINT {fk_name}
                FOREIGN KEY ({fk_cols_str})
                REFERENCES {catalog}.{schema}.{references}
                NOT ENFORCED
            """)
            print(f"  ✓ Added FK: {fk_cols_str} → {references}")
            applied_count += 1
        except Exception as e:
            print(f"  ⚠️ Warning: Could not add FK constraint: {e}")

    return applied_count


def main():
    """Main entry point for FK constraint application."""
    from pyspark.sql import SparkSession

    catalog, gold_schema, domain = get_parameters()

    spark = SparkSession.builder.appName("Gold Layer FK Constraints").getOrCreate()

    print("=" * 80)
    print("GOLD LAYER FOREIGN KEY CONSTRAINTS")
    print("=" * 80)

    try:
        yaml_base = find_yaml_base()

        if domain.lower() == "all":
            domains = [d.name for d in yaml_base.iterdir() if d.is_dir()]
        else:
            domains = [domain]

        total_fks = 0
        for d in domains:
            domain_path = yaml_base / d
            if not domain_path.exists():
                continue

            yaml_files = sorted(domain_path.glob("*.yaml"))

            for yaml_file in yaml_files:
                config = load_yaml(yaml_file)
                fk_count = apply_fk_constraints(spark, catalog, gold_schema, config)
                total_fks += fk_count

        print("\n" + "=" * 80)
        print(f"✓ Applied {total_fks} FK constraints successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

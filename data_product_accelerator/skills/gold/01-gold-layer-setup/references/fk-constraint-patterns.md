# FK Constraint Patterns

Foreign key constraint application patterns for Gold layer tables.

## Why Separate FK Script

Foreign keys must be applied **AFTER all primary keys exist** because:
1. FK references a PK in another table
2. If the referenced table hasn't been created yet, the FK constraint fails
3. The setup script creates tables in alphabetical/domain order, not dependency order
4. A separate FK script running after ALL tables are created guarantees PKs exist

## YAML FK Format

```yaml
# In gold_layer_design/yaml/{domain}/{table}.yaml
foreign_keys:
  - columns: ['store_key']
    references: dim_store(store_key)
  - columns: ['product_key']
    references: dim_product(product_key)
```

## Core Function

```python
def apply_fk_constraints(spark: SparkSession, catalog: str, schema: str, config: dict):
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
    table_name = config['table_name']
    fks = config.get('foreign_keys', [])

    if not fks:
        return 0

    print(f"\nApplying FK constraints for {table_name}...")

    applied_count = 0
    for idx, fk in enumerate(fks):
        fk_cols = fk['columns']
        references = fk['references']

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
```

## FK Naming Convention

| Pattern | Example |
|---------|---------|
| `fk_{table}_{idx}` | `fk_fact_sales_daily_1` |
| Sequential numbering | `fk_fact_sales_daily_2` |

## Main Entry Point

```python
def main():
    """Main entry point for FK constraint application."""
    catalog, gold_schema, domain = get_parameters()

    spark = SparkSession.builder.appName("Gold Layer FK Constraints").getOrCreate()

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

        print(f"\n✓ Applied {total_fks} FK constraints successfully!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        spark.stop()
```

## Error Handling

FK constraints may fail for several reasons:
- Referenced table does not exist yet (should not happen with separate script)
- Referenced column does not exist
- Constraint already exists from a previous run
- Typo in YAML references field

All failures are logged as warnings so the script continues processing other FKs.

## Related Skills

- `unity-catalog-constraints` — Complete PK/FK constraint patterns
- `01-yaml-table-setup` — YAML schema structure

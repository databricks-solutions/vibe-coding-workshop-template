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

        # IMPORTANT: In serverless, FK references MUST target PK columns.
        # Consider querying information_schema.table_constraints to verify
        # the referenced column has a PK before attempting the ALTER TABLE.
        # See "Serverless FK Limitation" section below for details.

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

## Serverless FK Limitation: References Must Target PK Columns

In serverless compute (`environment_version: "4"`), UNIQUE constraints cannot be created because `spark.databricks.sql.dsv2.unique.enabled` is not a settable configuration. This means:

- FK constraints can **ONLY** reference columns that have a PRIMARY KEY constraint on the target table
- If your YAML defines `references: dim_user(user_id)` but `user_id` is **NOT** the PK of `dim_user` (the PK is `user_key`), the FK will fail with: *"The foreign key parent columns do not match the referenced primary key child columns"*
- **NEVER** attempt `spark.conf.set("spark.databricks.sql.dsv2.unique.enabled", "true")` in serverless — this will crash the job

**Resolution options (pick one):**

1. **Skip and document (recommended for workshops)** — Apply PKs only. FK relationships remain documented in YAML `foreign_keys` metadata for Genie Space and BI tool discovery. The `add_fk_constraints.py` script logs a warning and continues.
2. **Change FK references to use surrogate PK columns** — e.g., change `references: dim_user(user_id)` to `references: dim_user(user_key)` and add `user_key` as an FK column on the fact table. Requires fact tables to carry surrogate keys.
3. **Use classic compute with UNIQUE enabled** — Set `spark.databricks.sql.dsv2.unique.enabled = true` on a classic cluster. NOT compatible with the skill's serverless-first mandate.

**Default behavior:** If FK application fails, log a warning and continue. **Never crash the setup job due to FK failures.**

**Cross-reference:** See `unity-catalog-constraints/SKILL.md` section "Foreign Keys Must Reference Primary Keys" — this is the authoritative rule.

## Related Skills

- `unity-catalog-constraints` — Complete PK/FK constraint patterns
- `01-yaml-table-setup` — YAML schema structure

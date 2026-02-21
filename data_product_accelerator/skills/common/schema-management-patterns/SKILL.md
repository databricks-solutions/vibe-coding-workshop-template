---
name: schema-management-patterns
description: Provides schema management patterns for Databricks Asset Bundles with Unity Catalog. Enables programmatic schema creation and configuration for medallion architecture layers. Covers CREATE SCHEMA IF NOT EXISTS patterns, DLT pipeline schema configuration, enabling Predictive Optimization at schema level using ALTER SCHEMA ENABLE PREDICTIVE OPTIMIZATION (not TBLPROPERTIES), schema variable usage, and common pitfalls to avoid. Use when creating Unity Catalog schemas programmatically in setup scripts, configuring DLT pipelines, enabling Predictive Optimization, or managing schema-level properties. Note: Schemas are NOT defined as Bundle resources - they are created programmatically for flexibility and idempotency. Critical for preventing schema creation errors, ensuring proper DLT configuration, and enabling schema-level optimizations.
metadata:
  author: prashanth subrahmanyam
  version: "1.0"
  domain: infrastructure
  role: shared
  used_by_stages: [1, 2, 3, 4]
  last_verified: "2026-02-07"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-unity-catalog/SKILL.md"
      relationship: "derived"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---

# Schema Management Patterns for Databricks Asset Bundles

## ⚠️ DEPRECATED PATTERN

**The `resources/schemas.yml` pattern is NO LONGER USED in this project.**

Schemas are now created programmatically in setup scripts using `CREATE SCHEMA IF NOT EXISTS` statements. This provides more flexibility and control over schema creation and properties.

## Current Pattern: Programmatic Schema Creation

### Setup Scripts Pattern

**Create schemas programmatically in setup scripts:**

See `assets/templates/create-schema.sql` for SQL template.

```python
# At the start of setup script
def create_catalog_and_schema(spark: SparkSession, catalog: str, schema: str):
    """Ensures the Unity Catalog schema exists."""
    print(f"Ensuring catalog '{catalog}' and schema '{schema}' exist...")
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
    print(f"✓ Schema {catalog}.{schema} ready")

# For table creation
spark.sql(f"""
    CREATE OR REPLACE TABLE {catalog}.{schema}.table_name (
        -- columns
    )
    USING DELTA
    CLUSTER BY AUTO
    TBLPROPERTIES (...)
""")
```

### Benefits
- ✅ Allows schema evolution without manual configuration
- ✅ Idempotent deployments
- ✅ Faster iteration during development
- ✅ Prevents "schema/table already exists" errors
- ✅ More flexibility than declarative YAML approach

## DLT Pipeline Schema Configuration

**File: `resources/silver_dlt_pipeline.yml`**

```yaml
resources:
  pipelines:
    silver_dlt_pipeline:
      name: "[${bundle.target}] Silver Layer Pipeline"
      
      # Catalog for serverless (required)
      catalog: ${var.catalog}
      
      # Schema where DLT will create tables
      # In dev mode, DLT adds prefix automatically
      schema: ${var.silver_schema}
      
      # Pass configuration to notebooks
      configuration:
        catalog: ${var.catalog}
        bronze_schema: ${var.bronze_schema}
        silver_schema: ${var.silver_schema}
```

## Common Pitfalls

### ❌ DON'T: Hardcode schema names
```python
# BAD
silver_table = f"{catalog}.company_silver.silver_store_dim"
```

### ✅ DO: Use variables
```python
# GOOD
silver_table = f"{catalog}.{silver_schema}.silver_store_dim"
```

### ❌ DON'T: Create schemas manually in scripts without considering prefixes
```python
# BAD - will create company_bronze in dev, not dev_user_company_bronze
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.company_bronze")
```

### ✅ DO: Use the schema variable passed from the bundle
```python
# GOOD - respects the prefixed schema name
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{bronze_schema}")
```

## Schema Configuration

**Schema properties and metadata are now managed at the table level via TBLPROPERTIES.**

See `data_product_accelerator/skills/common/databricks-table-properties/SKILL.md` for table-level property standards.

## Enabling Predictive Optimization at Schema Level

**Predictive optimization should be enabled at the SCHEMA or CATALOG level, not per-table.**

### ✅ CORRECT: Using Dedicated DDL Commands

```python
# Enable for a specific schema (RECOMMENDED for layer-specific control)
spark.sql(f"ALTER SCHEMA {catalog}.{schema} ENABLE PREDICTIVE OPTIMIZATION")

# OR enable for entire catalog (simpler but less granular)
spark.sql(f"ALTER CATALOG {catalog} ENABLE PREDICTIVE OPTIMIZATION")

# To disable (if needed)
spark.sql(f"ALTER SCHEMA {catalog}.{schema} DISABLE PREDICTIVE OPTIMIZATION")

# To inherit from parent (catalog level)
spark.sql(f"ALTER SCHEMA {catalog}.{schema} INHERIT PREDICTIVE OPTIMIZATION")
```

### ❌ WRONG: Using Table Property Syntax

```python
# ❌ WRONG - This syntax doesn't work for schemas
spark.sql(f"""
    ALTER SCHEMA {catalog}.{schema} SET TBLPROPERTIES (
        'databricks.pipelines.predictiveOptimizations.enabled' = 'true'
    )
""")
# Error: PARSE_SYNTAX_ERROR - Syntax error at or near 'TBLPROPERTIES'
```

### Why This Matters

**Schema-level enablement is the recommended pattern because:**
- ✅ Single command enables for all tables in the schema
- ✅ More granular than catalog-level (allows per-layer control)
- ✅ Less tedious than per-table enablement (30+ tables)
- ✅ Consistent governance across all tables in the layer

**Typical deployment pattern:**
```python
def enable_predictive_optimization(spark: SparkSession, catalog: str):
    """Enable predictive optimization for all medallion schemas."""
    schemas = ['bronze_schema', 'silver_schema', 'gold_schema']
    
    for schema_name in schemas:
        try:
            spark.sql(f"ALTER SCHEMA {catalog}.{schema_name} ENABLE PREDICTIVE OPTIMIZATION")
            print(f"✓ Enabled predictive optimization for {catalog}.{schema_name}")
        except Exception as e:
            print(f"⚠ Could not enable for {schema_name}: {e}")
```

### Reference
- [Predictive Optimization for Catalog/Schema](https://docs.databricks.com/aws/en/optimizations/predictive-optimization#enable-or-disable-predictive-optimization-for-a-catalog-or-schema)

## Validation Checklist

When setting up schemas programmatically:
- [ ] Setup scripts use `CREATE SCHEMA IF NOT EXISTS`
- [ ] `databricks.yml` defines schema variables
- [ ] All Python scripts use schema variables (not hardcoded)
- [ ] DLT pipelines use `catalog:` and `schema:` fields
- [ ] Bronze/Gold scripts use `CREATE OR REPLACE TABLE`
- [ ] Schema creation happens before table creation

## Troubleshooting

### Issue: "Schema does not exist"
**Solution:** Ensure setup scripts run first to create schemas before table creation jobs.

### Issue: Schema mismatch between layers
**Solution:** All jobs must use the same schema variable values from `databricks.yml`.

## References
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/)
- [Unity Catalog Schemas](https://docs.databricks.com/data-governance/unity-catalog/create-schemas.html)

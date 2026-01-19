# Gold Layer Implementation Prompt

## 🚀 Quick Start (3 hours)

**Goal:** Implement Gold layer using YAML schemas as single source of truth

**Prerequisites:** ⚠️ Complete `03a-gold-layer-design-prompt.md` first (YAML files must exist)

**What You'll Create:**
1. `setup_gold_tables.py` - Generic script reads YAML, creates all tables dynamically
2. `merge_gold_tables.py` - Merge Silver → Gold with explicit column mapping
3. `add_fk_constraints.py` - Apply FK constraints AFTER all PKs exist
4. `gold_setup_job.yml` + `gold_merge_job.yml` - Asset Bundle jobs

**Fast Track:**
```bash
# 1. Deploy setup job (creates tables from YAML)
databricks bundle run gold_setup_job -t dev

# 2. Verify tables created
# SHOW TABLES IN {catalog}.{gold_schema}

# 3. Run merge job (Silver → Gold)
databricks bundle run gold_merge_job -t dev
```

**YAML-Driven Pattern (Single Source of Truth):**
```python
# ✅ Generic setup script for ALL tables
for yaml_file in find_all_yaml_files():
    config = load_yaml(yaml_file)
    create_table_from_yaml(config)  # Reads YAML, generates DDL

# Schema change? Edit YAML only (no Python changes needed)
```

**Key Implementation Rules:**
- **FK Constraints:** Apply via `ALTER TABLE` AFTER all PKs exist (not inline in CREATE TABLE)
- **Column Mapping:** Explicit `.withColumn()` for Bronze→Silver→Gold name changes
- **DATE_TRUNC:** Always CAST result to DATE type to avoid schema merge errors
- **Helper Functions:** Inline or use pure Python modules (not notebooks) to avoid sys.path issues

**Critical Validations:**
- [ ] YAML files exist in `gold_layer_design/yaml/`
- [ ] DDL PRIMARY KEYs match YAML `primary_key` field
- [ ] Merge scripts map Silver columns explicitly
- [ ] FK constraints applied AFTER table creation

**Output:** Gold Delta tables with constraints, ready for Metric Views and TVFs

📖 **Full guide below** for detailed implementation →

---

## Quick Reference

**Use this prompt to implement Gold layer tables and merge scripts from YAML schema definitions.**

**Prerequisites:** Complete [03a-gold-layer-design-prompt.md](./03a-gold-layer-design-prompt.md) first.

---

## 📋 Your Requirements (Fill These In First)

### Project Context
- **Project Name:** _________________ (e.g., retail_analytics)
- **Silver Schema:** _________________ (e.g., my_project_silver)
- **Gold Schema:** _________________ (e.g., my_project_gold)
- **YAML Location:** _________________ (e.g., gold_layer_design/yaml/)

### Implementation Scope
- **Tables to Implement:** _________________ (e.g., dim_store, dim_product, fact_sales_daily)
- **Domains:** _________________ (e.g., retail, sales)
- **Deployment Target:** _________________ (dev, prod)

---

## Core Philosophy: YAML as Source of Truth

**⚠️ CRITICAL PRINCIPLE:**

All Gold layer implementation uses **YAML schema files as the single source of truth**:

- ✅ **YAML defines schema** (columns, types, constraints, descriptions)
- ✅ **Python reads YAML at runtime** (no code generation)
- ✅ **DDL generated dynamically** from YAML
- ✅ **Schema changes = YAML edits only** (no Python changes)
- ✅ **Consistent table properties** guaranteed
- ❌ **No embedded SQL DDL strings** in Python

**Why This Matters:**
- Schema changes are reviewable YAML diffs
- No SQL escaping issues
- Single generic setup script for all domains
- Consistent governance metadata
- Easy to validate and audit

**See [25-yaml-driven-gold-setup.mdc](mdc:.cursor/rules/25-yaml-driven-gold-setup.mdc) for complete YAML-driven patterns.**

---

## Step 1: YAML-Driven Table Creation

### File Structure

```
project_root/
├── gold_layer_design/
│   └── yaml/
│       ├── retail/
│       │   ├── dim_store.yaml
│       │   └── dim_product.yaml
│       ├── sales/
│       │   └── fact_sales_daily.yaml
│       └── time/
│           └── dim_date.yaml
├── src/
│   └── {project}_gold/
│       ├── setup_tables.py          # Generic YAML-driven setup
│       ├── add_fk_constraints.py    # Apply FK constraints
│       └── merge_gold_tables.py     # Merge from Silver
└── databricks.yml                   # Sync YAMLs!
```

### File: `setup_tables.py`

```python
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
    raise FileNotFoundError("YAML directory not found. Ensure YAMLs are synced in databricks.yml")


def load_yaml(path: Path) -> dict:
    """Load and parse YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
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
    table_name = config['table_name']
    columns = config.get('columns', [])
    description = config.get('description', '')
    domain = config.get('domain', 'unknown')
    grain = config.get('grain', '')
    
    # Build column DDL
    col_ddls = []
    for col in columns:
        null_str = "" if col.get('nullable', True) else " NOT NULL"
        desc = escape_sql_string(col.get('description', ''))
        comment = f"\n        COMMENT '{desc}'" if desc else ""
        col_ddls.append(f"    {col['name']} {col['type']}{null_str}{comment}")
    
    columns_str = ",\n".join(col_ddls)
    
    # Build properties
    props = STANDARD_PROPERTIES.copy()
    props['domain'] = domain
    props['entity_type'] = "dimension" if table_name.startswith("dim_") else "fact"
    props['grain'] = grain
    
    # Add custom properties from YAML
    table_props = config.get('table_properties', {})
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


def create_table(spark: SparkSession, catalog: str, schema: str, yaml_path: Path) -> dict:
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
    table_name = config.get('table_name', yaml_path.stem)
    
    print(f"\nCreating {catalog}.{schema}.{table_name}...")
    
    # Create table
    ddl = build_create_table_ddl(catalog, schema, config)
    spark.sql(ddl)
    
    # Add primary key constraint
    pk_config = config.get('primary_key', {})
    if pk_config and pk_config.get('columns'):
        pk_cols = ", ".join(pk_config['columns'])
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
    business_key_config = config.get('business_key', {})
    if business_key_config and business_key_config.get('columns'):
        uk_cols = ", ".join(business_key_config['columns'])
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
                created_tables.append(result['table'])
        
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
```

### File: `add_fk_constraints.py`

**Foreign keys must be added AFTER all primary keys exist.**

```python
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
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def apply_fk_constraints(spark: SparkSession, catalog: str, schema: str, config: dict):
    """
    Apply FK constraints from YAML config.
    
    Args:
        spark: SparkSession
        catalog: Unity Catalog name
        schema: Schema name
        config: Parsed YAML configuration
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
```

**See [05-unity-catalog-constraints.mdc](mdc:.cursor/rules/05-unity-catalog-constraints.mdc) for constraint application patterns.**

---

## Step 2: MERGE Scripts (Populate from Silver)

### File: `merge_gold_tables.py`

**Pattern:** Read Silver, apply transformations, MERGE into Gold with deduplication

```python
# Databricks notebook source

"""
{Project} Gold Layer - MERGE Operations

Performs Delta MERGE operations to update Gold layer tables from Silver.

Handles:
- Schema-aware transformations (column mapping)
- SCD Type 2 dimension updates
- Fact table aggregation and deduplication
- Late-arriving data
- Schema validation

Usage:
  databricks bundle run gold_merge_job -t dev
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, md5, concat_ws, 
    when, sum as spark_sum, count, avg, lit, coalesce
)
from delta.tables import DeltaTable


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    silver_schema = dbutils.widgets.get("silver_schema")
    gold_schema = dbutils.widgets.get("gold_schema")
    
    print(f"Catalog: {catalog}")
    print(f"Silver Schema: {silver_schema}")
    print(f"Gold Schema: {gold_schema}")
    
    return catalog, silver_schema, gold_schema


def merge_dim_store(spark: SparkSession, catalog: str, silver_schema: str, gold_schema: str):
    """
    Merge dim_store from Silver to Gold (SCD Type 2).
    
    Key patterns:
    - Deduplication before MERGE (latest record per business key)
    - Explicit column mapping (Silver → Gold names)
    - SCD Type 2: Update timestamp only (no new version)
    """
    print("\n--- Merging dim_store (SCD Type 2) ---")
    
    silver_table = f"{catalog}.{silver_schema}.silver_store_dim"
    gold_table = f"{catalog}.{gold_schema}.dim_store"
    
    # Step 1: Read and deduplicate Silver source
    silver_raw = spark.table(silver_table)
    original_count = silver_raw.count()
    
    silver_df = (
        silver_raw
        .orderBy(col("processed_timestamp").desc())  # Latest first
        .dropDuplicates(["store_number"])  # Keep first (latest) per business key
    )
    
    dedupe_count = silver_df.count()
    print(f"  Deduplicated: {original_count} → {dedupe_count} records ({original_count - dedupe_count} duplicates removed)")
    
    # Step 2: Prepare updates with column mappings
    updates_df = (
        silver_df
        # Generate surrogate key
        .withColumn("store_key", 
                   md5(concat_ws("||", col("store_number"), col("processed_timestamp"))))
        
        # SCD Type 2 columns
        .withColumn("effective_from", col("processed_timestamp"))
        .withColumn("effective_to", lit(None).cast("timestamp"))
        .withColumn("is_current", lit(True))
        
        # Column mappings: Silver → Gold
        .withColumn("company_retail_control_number", col("company_rcn"))  # Rename
        
        # Derived columns
        .withColumn("store_status",
                   when(col("close_date").isNotNull(), "Closed").otherwise("Active"))
        
        # Timestamps
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
        
        # Select ONLY columns in Gold DDL
        .select(
            "store_key",
            "store_number",
            "store_name",
            "company_retail_control_number",  # Mapped column
            "city",
            "state",
            "effective_from",
            "effective_to",
            "is_current",
            "record_created_timestamp",
            "record_updated_timestamp"
        )
    )
    
    # Step 3: MERGE into Gold
    delta_gold = DeltaTable.forName(spark, gold_table)
    
    delta_gold.alias("target").merge(
        updates_df.alias("source"),
        "target.store_number = source.store_number AND target.is_current = true"
    ).whenMatchedUpdate(set={
        "record_updated_timestamp": "source.record_updated_timestamp"
    }).whenNotMatchedInsertAll(
    ).execute()
    
    record_count = updates_df.count()
    print(f"✓ Merged {record_count} records into dim_store")


def merge_fact_sales_daily(spark: SparkSession, catalog: str, silver_schema: str, gold_schema: str):
    """
    Merge fact_sales_daily from Silver transactions.
    
    Key patterns:
    - Aggregation to daily grain
    - Grain validation (one row per store-product-date)
    - Column mapping (Silver → Gold names)
    - Schema validation before MERGE
    """
    print("\n--- Merging fact_sales_daily ---")
    
    silver_table = f"{catalog}.{silver_schema}.silver_transactions"
    gold_table = f"{catalog}.{gold_schema}.fact_sales_daily"
    
    transactions = spark.table(silver_table)
    
    # Step 1: Aggregate to daily grain
    daily_sales = (
        transactions
        .groupBy("store_number", "upc_code", "transaction_date")
        .agg(
            # Revenue measures
            spark_sum(when(col("quantity_sold") > 0, col("final_sales_price")).otherwise(0)
                     ).alias("gross_revenue"),
            spark_sum(col("final_sales_price")).alias("net_revenue"),
            
            # Unit measures
            spark_sum(when(col("quantity_sold") > 0, col("quantity_sold")).otherwise(0)
                     ).alias("gross_units"),
            spark_sum(col("quantity_sold")).alias("net_units"),
            
            # Transaction counts
            count("*").alias("transaction_count")
        )
        # Derived metrics
        .withColumn("avg_transaction_value",
                   when(col("transaction_count") > 0, col("net_revenue") / col("transaction_count"))
                   .otherwise(0))
        
        # Timestamps
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )
    
    # Step 2: Validate grain (one row per store-product-date)
    distinct_grain_count = daily_sales.select("store_number", "upc_code", "transaction_date").distinct().count()
    total_row_count = daily_sales.count()
    
    if distinct_grain_count != total_row_count:
        raise ValueError(
            f"Grain validation failed! Expected one row per store-product-date.\n"
            f"  Distinct combinations: {distinct_grain_count}\n"
            f"  Total rows: {total_row_count}\n"
            f"  Duplicates: {total_row_count - distinct_grain_count}"
        )
    
    print(f"  ✓ Grain validation passed: {total_row_count} unique combinations")
    
    # Step 3: MERGE into Gold
    delta_gold = DeltaTable.forName(spark, gold_table)
    
    delta_gold.alias("target").merge(
        daily_sales.alias("source"),
        """target.store_number = source.store_number 
           AND target.upc_code = source.upc_code 
           AND target.transaction_date = source.transaction_date"""
    ).whenMatchedUpdate(set={
        "gross_revenue": "source.gross_revenue",
        "net_revenue": "source.net_revenue",
        "gross_units": "source.gross_units",
        "net_units": "source.net_units",
        "transaction_count": "source.transaction_count",
        "avg_transaction_value": "source.avg_transaction_value",
        "record_updated_timestamp": "source.record_updated_timestamp"
    }).whenNotMatchedInsertAll(
    ).execute()
    
    record_count = daily_sales.count()
    print(f"✓ Merged {record_count} records into fact_sales_daily")


def main():
    """Main entry point for Gold layer MERGE operations."""
    from pyspark.sql import SparkSession
    
    catalog, silver_schema, gold_schema = get_parameters()
    
    spark = SparkSession.builder.appName("Gold Layer MERGE").getOrCreate()
    
    print("=" * 80)
    print("GOLD LAYER MERGE OPERATIONS")
    print("=" * 80)
    print(f"Source: {catalog}.{silver_schema}")
    print(f"Target: {catalog}.{gold_schema}")
    print("=" * 80)
    
    try:
        # Merge dimensions first
        merge_dim_store(spark, catalog, silver_schema, gold_schema)
        # merge_dim_product(spark, catalog, silver_schema, gold_schema)
        # ... more dimensions
        
        # Then merge facts
        merge_fact_sales_daily(spark, catalog, silver_schema, gold_schema)
        # ... more facts
        
        print("\n" + "=" * 80)
        print("✓ Gold layer MERGE completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during Gold layer MERGE: {str(e)}")
        raise
        
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

**Key Patterns Applied:**
- ✅ **Deduplication** - See [11-gold-delta-merge-deduplication.mdc](mdc:.cursor/rules/11-gold-delta-merge-deduplication.mdc)
- ✅ **Column Mapping** - See [10-gold-layer-merge-patterns.mdc](mdc:.cursor/rules/10-gold-layer-merge-patterns.mdc)
- ✅ **Schema Validation** - See [23-gold-layer-schema-validation.mdc](mdc:.cursor/rules/23-gold-layer-schema-validation.mdc)
- ✅ **Grain Validation** - See [24-fact-table-grain-validation.mdc](mdc:.cursor/rules/24-fact-table-grain-validation.mdc)

---

## Step 3: Asset Bundle Configuration

### Critical: Sync YAML Files

**File: `databricks.yml`**

```yaml
sync:
  include:
    - src/**/*.py
    - sql/**/*.sql
    - gold_layer_design/yaml/**/*.yaml  # ← CRITICAL!
```

### File: `resources/gold_setup_job.yml`

```yaml
resources:
  jobs:
    gold_setup_job:
      name: "[${bundle.target}] {Project} Gold Layer - Setup"
      description: "Creates Gold layer tables from YAML schema definitions"
      
      # PyYAML dependency required
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - "pyyaml>=6.0"
      
      tasks:
        # Task 1: Create all tables from YAMLs
        - task_key: setup_all_tables
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_gold/setup_tables.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              domain: all  # or specific domain
          timeout_seconds: 1800
        
        # Task 2: Add FK constraints (after PKs exist)
        - task_key: add_fk_constraints
          depends_on:
            - task_key: setup_all_tables
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_gold/add_fk_constraints.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              domain: all
      
      email_notifications:
        on_failure:
          - data-engineering@company.com
      
      tags:
        environment: ${bundle.target}
        layer: gold
        job_type: setup
```

### File: `resources/gold_merge_job.yml`

```yaml
resources:
  jobs:
    gold_merge_job:
      name: "[${bundle.target}] {Project} Gold Layer - MERGE Updates"
      description: "Periodic MERGE operations from Silver to Gold"
      
      tasks:
        - task_key: merge_gold_tables
          notebook_task:
            notebook_path: ../../src/{project}_gold/merge_gold_tables.py
            base_parameters:
              catalog: ${var.catalog}
              silver_schema: ${var.silver_schema}
              gold_schema: ${var.gold_schema}
          timeout_seconds: 3600
      
      # Schedule for periodic updates
      schedule:
        quartz_cron_expression: "0 0 3 * * ?"  # Daily at 3 AM
        timezone_id: "America/New_York"
        pause_status: PAUSED  # Enable manually or in prod
      
      email_notifications:
        on_failure:
          - data-engineering@company.com
      
      tags:
        environment: ${bundle.target}
        layer: gold
        job_type: pipeline
```

---

## Implementation Checklist

### Phase 1: Setup (30 min)
- [ ] YAML schema files exist (from design phase)
- [ ] YAML files synced in `databricks.yml`
- [ ] PyYAML dependency added to job environment
- [ ] `setup_tables.py` created (generic script)
- [ ] `add_fk_constraints.py` created
- [ ] Test YAML parsing locally

### Phase 2: Table Creation (30 min)
- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run: `databricks bundle run gold_setup_job -t dev`
- [ ] Verify tables created: `SHOW TABLES IN {gold_schema}`
- [ ] Verify PKs: `SHOW CREATE TABLE {table}`
- [ ] Verify FKs: `DESCRIBE TABLE EXTENDED {table}`
- [ ] Check table properties: `SHOW TBLPROPERTIES {table}`

### Phase 3: MERGE Implementation (2 hours)
- [ ] Create `merge_gold_tables.py`
- [ ] Implement dimension merges (SCD Type 2)
- [ ] Implement fact merges (aggregation)
- [ ] Add deduplication logic
- [ ] Add column mapping (Silver → Gold)
- [ ] Add schema validation
- [ ] Add grain validation
- [ ] Add error handling

### Phase 4: Testing (1 hour)
- [ ] Run: `databricks bundle run gold_merge_job -t dev`
- [ ] Verify record counts
- [ ] Verify grain (no duplicates)
- [ ] Verify FK relationships (no orphans)
- [ ] Verify SCD Type 2 (is_current flag)
- [ ] Check late-arriving data handling
- [ ] Validate column mappings

### Phase 5: Validation (30 min)
- [ ] Run schema validation queries
- [ ] Run grain validation queries
- [ ] Run FK integrity checks
- [ ] Check data quality metrics
- [ ] Verify audit timestamps

---

## Validation Queries

### Schema Validation

```sql
-- Check table creation
USE CATALOG {catalog};
SHOW TABLES IN {gold_schema};

-- Verify PRIMARY KEY constraints
SHOW CREATE TABLE {catalog}.{gold_schema}.dim_store;

-- Check column definitions match YAML
DESCRIBE TABLE EXTENDED {catalog}.{gold_schema}.dim_store;
```

### Grain Validation

```sql
-- Verify fact table grain (should be equal)
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT CONCAT(store_number, '|', upc_code, '|', transaction_date)) as unique_combinations
FROM {catalog}.{gold_schema}.fact_sales_daily;

-- Should return 0 duplicates
SELECT 
  store_number, upc_code, transaction_date, COUNT(*) as dup_count
FROM {catalog}.{gold_schema}.fact_sales_daily
GROUP BY store_number, upc_code, transaction_date
HAVING COUNT(*) > 1;
```

### FK Integrity

```sql
-- Verify no orphaned records (should return 0)
SELECT COUNT(*) as orphaned_sales
FROM {catalog}.{gold_schema}.fact_sales_daily f
LEFT JOIN {catalog}.{gold_schema}.dim_store d 
  ON f.store_number = d.store_number 
  AND d.is_current = true
WHERE d.store_number IS NULL;
```

### SCD Type 2 Validation

```sql
-- Verify only one current version per business key
SELECT store_number, COUNT(*) as current_versions
FROM {catalog}.{gold_schema}.dim_store
WHERE is_current = true
GROUP BY store_number
HAVING COUNT(*) > 1;

-- Check for overlapping effective dates
SELECT *
FROM {catalog}.{gold_schema}.dim_store a
JOIN {catalog}.{gold_schema}.dim_store b
  ON a.store_number = b.store_number
  AND a.store_key != b.store_key
WHERE a.effective_from < COALESCE(b.effective_to, '9999-12-31')
  AND COALESCE(a.effective_to, '9999-12-31') > b.effective_from;
```

---

## Common Issues & Solutions

### Issue 1: YAML Files Not Found

**Error:** `FileNotFoundError: YAML directory not found`

**Solution:** Add YAMLs to sync in `databricks.yml`:
```yaml
sync:
  include:
    - gold_layer_design/yaml/**/*.yaml
```

### Issue 2: PyYAML Not Available

**Error:** `ModuleNotFoundError: No module named 'yaml'`

**Solution:** Add dependency:
```yaml
environments:
  - environment_key: default
    spec:
      dependencies:
        - "pyyaml>=6.0"
```

### Issue 3: Duplicate Key MERGE Error

**Error:** `[DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE]`

**Solution:** Add deduplication before MERGE:
```python
silver_df = (
    silver_raw
    .orderBy(col("processed_timestamp").desc())
    .dropDuplicates(["business_key"])
)
```

**See [11-gold-delta-merge-deduplication.mdc](mdc:.cursor/rules/11-gold-delta-merge-deduplication.mdc)**

### Issue 4: Column Name Mismatch

**Error:** `[UNRESOLVED_COLUMN] A column with name 'X' cannot be resolved`

**Solution:** Add explicit column mapping:
```python
.withColumn("gold_column_name", col("silver_column_name"))
```

**See [23-gold-layer-schema-validation.mdc](mdc:.cursor/rules/23-gold-layer-schema-validation.mdc)**

### Issue 5: Grain Duplicates

**Error:** Multiple rows per grain combination

**Solution:** Ensure aggregation matches PRIMARY KEY:
```python
# If PK is (store, product, date)
daily_sales = transactions.groupBy("store_number", "upc_code", "transaction_date")
```

**See [24-fact-table-grain-validation.mdc](mdc:.cursor/rules/24-fact-table-grain-validation.mdc)**

---

## Key Principles

### 1. YAML as Source of Truth
- ✅ All schema changes in YAML (no Python edits)
- ✅ Schema is reviewable and version-controlled
- ✅ Generic implementation script (reusable)

### 2. Schema Validation
- ✅ Validate DataFrame columns match DDL
- ✅ Check data types match
- ✅ Verify no missing/extra columns

### 3. Grain Validation
- ✅ Ensure PRIMARY KEY matches grain
- ✅ Validate no duplicate rows at grain level
- ✅ Check aggregation logic

### 4. Deduplication Always
- ✅ Deduplicate Silver before MERGE
- ✅ Order by timestamp DESC (latest first)
- ✅ Keep first per business key

### 5. Column Mapping Explicit
- ✅ Use `.withColumn()` for renames
- ✅ Document mappings in comments
- ✅ Select only columns in DDL

---

## Next Steps

After Gold layer implementation is complete:

1. **Metric Views:** Use [04-metric-views-prompt.md](./04-metric-views-prompt.md)
2. **TVFs:** Create Table-Valued Functions for Genie
3. **Monitoring:** Use [05-monitoring-prompt.md](./05-monitoring-prompt.md)
4. **Genie Space:** Use [06-genie-space-prompt.md](./06-genie-space-prompt.md)

---

## References

### Framework Rules
- [25-yaml-driven-gold-setup.mdc](mdc:.cursor/rules/25-yaml-driven-gold-setup.mdc) - YAML patterns
- [23-gold-layer-schema-validation.mdc](mdc:.cursor/rules/23-gold-layer-schema-validation.mdc) - Schema validation
- [24-fact-table-grain-validation.mdc](mdc:.cursor/rules/24-fact-table-grain-validation.mdc) - Grain validation
- [11-gold-delta-merge-deduplication.mdc](mdc:.cursor/rules/11-gold-delta-merge-deduplication.mdc) - Deduplication
- [10-gold-layer-merge-patterns.mdc](mdc:.cursor/rules/10-gold-layer-merge-patterns.mdc) - MERGE patterns
- [12-gold-layer-documentation.mdc](mdc:.cursor/rules/12-gold-layer-documentation.mdc) - Documentation

### Official Documentation
- [Delta MERGE](https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge)
- [Unity Catalog Constraints](https://docs.databricks.com/data-governance/unity-catalog/constraints.html)
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/)

---

## Summary

**What to Create:**
1. `setup_tables.py` - Generic YAML-driven table creation
2. `add_fk_constraints.py` - FK constraint application
3. `merge_gold_tables.py` - Delta MERGE from Silver
4. `gold_setup_job.yml` - One-time setup job
5. `gold_merge_job.yml` - Periodic MERGE job

**Core Philosophy:** Implementation = Read YAML at runtime, validate schema and grain, MERGE with deduplication

**Time Estimate:** 3-4 hours for 3-5 tables

**Next Action:** Deploy setup, run MERGE, validate results


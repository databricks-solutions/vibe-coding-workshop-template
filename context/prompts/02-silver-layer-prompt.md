# Silver Layer Creation Prompt

## 🚀 Quick Start (1 hour)

**Goal:** Create Silver DLT pipeline with Delta table-based data quality rules

**What You'll Create:**
1. `dq_rules` Delta table - Centralized rules repository in Unity Catalog
2. `dq_rules_loader.py` - Pure Python module to load rules at runtime
3. `silver_*.py` - DLT notebooks with expectations loaded from Delta table
4. `silver_dlt_pipeline.yml` - Serverless DLT pipeline configuration

**Fast Track:**
```bash
# 1. Create DQ rules table FIRST
databricks bundle run silver_dq_setup_job -t dev

# 2. Verify rules table
# SELECT * FROM {catalog}.{silver_schema}.dq_rules

# 3. Deploy and run DLT pipeline
databricks bundle deploy -t dev
databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline"
```

**Key Principles:**
- **Schema Cloning:** Silver = Bronze columns + Data quality validation (NO aggregation!)
- **Delta Table Rules:** Update rules via SQL (no code deployment needed)
- **Never Fails:** Critical rules drop/quarantine records, pipeline continues
- **Direct Publishing:** Fully qualified table names (no `LIVE.` prefix)

**Critical Files:**
- ⚠️ `dq_rules_loader.py` must be **pure Python** (NO `# Databricks notebook source` header)
- ⚠️ Run `silver_dq_setup_job` BEFORE deploying DLT pipeline

**Output:** Streaming Silver tables with runtime-updateable data quality, quarantine tables, monitoring views

📖 **Full guide below** for detailed implementation →

---

## Quick Reference

**Use this prompt when creating a new Silver layer DLT pipeline in any Databricks project.**

---

## 📋 Your Requirements (Fill These In First)

**Before creating Silver layer, map your Bronze tables and define quality rules:**

### Project Context
- **Project Name:** _________________ (e.g., retail_analytics, patient_outcomes)
- **Bronze Schema:** _________________ (e.g., my_project_bronze)
- **Silver Schema:** _________________ (e.g., my_project_silver)

### Bronze to Silver Table Mapping

| # | Bronze Table | Silver Table | Entity Type | Critical DQ Rules Count |
|---|-------------|--------------|-------------|------------------------|
| 1 | bronze_customers | silver_customer_dim | Dimension | 5 |
| 2 | bronze_orders | silver_orders | Fact | 8 |
| 3 | ____________ | _____________ | ________ | ___ |
| 4 | ____________ | _____________ | ________ | ___ |
| 5 | ____________ | _____________ | ________ | ___ |

### Data Quality Rules Template

**For each table, define:**

| Rule Type | Purpose | Example |
|-----------|---------|---------|
| **CRITICAL** | Must pass or record dropped | Primary key NOT NULL, FK present, Date >= 2020 |
| **WARNING** | Logged but record passes | Quantity between 1-100, Price < $1000 |

**Critical Rules** (Record dropped/quarantined if fails):
- Primary key columns: NOT NULL and LENGTH > 0
- Foreign key columns: NOT NULL (referential integrity)
- Required dates: NOT NULL and >= minimum valid date
- Non-zero fields: quantity != 0, amount > 0

**Warning Rules** (Logged but record passes):
- Reasonableness: quantity between min-max, price between min-max
- Recency: date within last N days
- Format: length checks, pattern matching

### Quality Rules by Entity

**Entity 1: _________________**
- Critical: _________________________________________________
- Critical: _________________________________________________
- Warning: _________________________________________________

**Entity 2: _________________**
- Critical: _________________________________________________
- Critical: _________________________________________________  
- Warning: _________________________________________________

### Quarantine Strategy

Which tables need quarantine? (✓ for yes)
- [ ] _________________ (high-volume fact, complex validation)
- [ ] _________________ (critical business table)
- [ ] _________________ (external data source, unreliable)

**General Rule:** Add quarantine for:
- ✅ High-volume transactional tables
- ✅ Tables with complex validation rules
- ✅ Tables where you need to track failure patterns
- ❌ Simple dimension tables
- ❌ Lookup/reference tables

---

## Core Philosophy: Clone + Quality

**⚠️ CRITICAL PRINCIPLE:**

The Silver layer should **essentially clone the source Bronze schema** with minimal transformations:

- ✅ **Same column names** as Bronze (no complex renaming)
- ✅ **Same data types** (minimal type conversions)
- ✅ **Same grain** (no aggregation, that's for Gold)
- ✅ **Add data quality rules** (the main value-add)
- ✅ **Add derived flags** (business indicators like `is_return`, `is_out_of_stock`)
- ✅ **Add business keys** (SHA256 hashes for tracking)
- ✅ **Add timestamps** (`processed_timestamp`)

**What NOT to do in Silver:**
- ❌ Major schema restructuring
- ❌ Aggregations (save for Gold)
- ❌ Complex business logic (simple flags only)
- ❌ Joining across tables (dimension lookups in Gold)

**Why This Matters:**
- Silver is the **validated copy** of source data
- Gold layer handles complex transformations
- Keeps Silver focused on data quality
- Makes troubleshooting easier (column names match source)

---

## Overview

Create a production-grade Databricks Delta Live Tables (DLT) Silver layer with:
- **Delta table-based data quality rules** (portable, auditable, updateable)
- Quarantine patterns for invalid records
- Comprehensive monitoring views
- Streaming ingestion from Bronze
- Schema cloning from source

**Rule Storage:** All data quality rules stored in a **Unity Catalog Delta table** for centralized management, version control, and runtime updates.

**Reference:** [DLT Expectation Patterns - Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns)

---

## File Structure to Create

```
src/{project}_silver/
├── setup_dq_rules_table.py        # One-time: Create and populate DQ rules Delta table
├── dq_rules_loader.py             # Pure Python (NO notebook header) - functions to load rules from Delta table
├── silver_dimensions.py           # DLT notebook - dimension tables (stores, products, etc.)
├── silver_transactions.py         # DLT notebook - transactional fact table with quarantine
├── silver_inventory.py            # DLT notebook - inventory fact tables (if applicable)
└── data_quality_monitoring.py     # DLT notebook - DQ monitoring views
```

---

## Step 1: Create Data Quality Rules Delta Table

### File: `setup_dq_rules_table.py`

**One-time setup: Create the rules table in Unity Catalog**

```python
# Databricks notebook source

"""
{Project} Silver Layer - Data Quality Rules Table Setup

Creates a Unity Catalog Delta table to store ALL data quality rules for the Silver layer.

This table is the single source of truth for all DLT expectations across all Silver tables.

Benefits:
- ✅ Centralized rule management
- ✅ Auditable (versioned in Delta table)
- ✅ Updateable at runtime (no code changes needed)
- ✅ Queryable for documentation and reporting
- ✅ Supports tagging and filtering

Usage:
  databricks bundle run silver_dq_setup_job -t dev
"""

from pyspark.sql import SparkSession


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    silver_schema = dbutils.widgets.get("silver_schema")
    
    print(f"Catalog: {catalog}")
    print(f"Silver Schema: {silver_schema}")
    
    return catalog, silver_schema


def create_dq_rules_table(spark: SparkSession, catalog: str, schema: str):
    """
    Create the data quality rules Delta table.
    
    Schema:
    - table_name: Which Silver table this rule applies to
    - rule_name: Unique name for the rule
    - constraint: SQL expression for the expectation
    - severity: 'critical' (drop/quarantine) or 'warning' (log only)
    - description: Human-readable explanation
    - created_timestamp: When rule was added
    - updated_timestamp: When rule was last modified
    """
    print(f"\nCreating {catalog}.{schema}.dq_rules table...")
    
    table_ddl = f"""
        CREATE OR REPLACE TABLE {catalog}.{schema}.dq_rules (
            table_name STRING NOT NULL
                COMMENT 'Silver table name this rule applies to (e.g., silver_transactions)',
            rule_name STRING NOT NULL
                COMMENT 'Unique identifier for this rule (e.g., valid_transaction_id)',
            constraint_sql STRING NOT NULL
                COMMENT 'SQL expression for the expectation (e.g., transaction_id IS NOT NULL)',
            severity STRING NOT NULL
                COMMENT 'Rule severity: critical (drop/quarantine) or warning (log only)',
            description STRING
                COMMENT 'Human-readable explanation of what this rule validates',
            created_timestamp TIMESTAMP NOT NULL
                COMMENT 'When this rule was first added',
            updated_timestamp TIMESTAMP NOT NULL
                COMMENT 'When this rule was last modified',
            
            CONSTRAINT pk_dq_rules PRIMARY KEY (table_name, rule_name) NOT ENFORCED
        )
        USING DELTA
        CLUSTER BY AUTO
        COMMENT 'Data quality rules repository for Silver layer DLT expectations. Rules are loaded dynamically at pipeline runtime for portable and maintainable data quality management.'
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'layer' = 'silver',
            'domain' = 'governance',
            'entity_type' = 'metadata',
            'contains_pii' = 'false',
            'data_classification' = 'internal',
            'business_owner' = 'Data Engineering',
            'technical_owner' = 'Data Engineering'
        )
    """
    
    spark.sql(table_ddl)
    print(f"✓ Created DQ rules table")


def populate_dq_rules(spark: SparkSession, catalog: str, schema: str):
    """
    Populate the DQ rules table with initial rules for all Silver tables.
    
    Defines rules for:
    - Dimensions (stores, products, dates, etc.)
    - Facts (transactions, inventory, etc.)
    
    Each rule has:
    - Unique name per table
    - SQL constraint expression
    - Severity (critical or warning)
    - Description
    """
    from pyspark.sql.functions import current_timestamp
    from pyspark.sql.types import StructType, StructField, StringType, TimestampType
    
    print(f"\nPopulating {catalog}.{schema}.dq_rules with rules...")
    
    # Define all rules as list of tuples
    rules = [
        # ===== SILVER_TRANSACTIONS (Fact Table) =====
        
        # CRITICAL: Primary Keys
        ("silver_transactions", "valid_transaction_id", 
         "transaction_id IS NOT NULL AND LENGTH(transaction_id) > 0", 
         "critical",
         "Transaction ID must be present and non-empty (primary key validation)"),
        
        # CRITICAL: Foreign Keys
        ("silver_transactions", "valid_store_number", 
         "store_number IS NOT NULL", 
         "critical",
         "Store number must be present (FK to dim_store)"),
        
        ("silver_transactions", "valid_upc_code", 
         "upc_code IS NOT NULL", 
         "critical",
         "UPC code must be present (FK to dim_product)"),
        
        # CRITICAL: Required Dates
        ("silver_transactions", "valid_transaction_date", 
         "transaction_date IS NOT NULL AND transaction_date >= '2020-01-01'", 
         "critical",
         "Transaction date must be present and after minimum valid date (2020-01-01)"),
        
        # CRITICAL: Business Logic (Non-Zero)
        ("silver_transactions", "non_zero_quantity", 
         "quantity_sold != 0", 
         "critical",
         "Quantity cannot be zero (0 quantity is invalid transaction)"),
        
        ("silver_transactions", "positive_final_price", 
         "final_sales_price > 0", 
         "critical",
         "Final sales price must be positive (even returns have positive unit price)"),
        
        # WARNING: Reasonableness Checks
        ("silver_transactions", "reasonable_quantity", 
         "quantity_sold BETWEEN -20 AND 50", 
         "warning",
         "Quantity should be within normal range (-20 to 50 units)"),
        
        ("silver_transactions", "reasonable_price", 
         "final_sales_price BETWEEN 0.01 AND 500.00", 
         "warning",
         "Price should be within normal range ($0.01 to $500)"),
        
        ("silver_transactions", "recent_transaction", 
         "transaction_date >= CURRENT_DATE() - INTERVAL 365 DAYS", 
         "warning",
         "Transaction should be recent (within last year)"),
        
        # ===== SILVER_STORE_DIM (Dimension Table) =====
        
        # CRITICAL: Primary Key
        ("silver_store_dim", "valid_store_number", 
         "store_number IS NOT NULL AND LENGTH(store_number) > 0", 
         "critical",
         "Store number must be present and non-empty (primary key)"),
        
        # CRITICAL: Required Fields
        ("silver_store_dim", "valid_store_name", 
         "store_name IS NOT NULL AND LENGTH(store_name) > 0", 
         "critical",
         "Store name must be present and non-empty"),
        
        # WARNING: Format Validation
        ("silver_store_dim", "valid_state_format", 
         "state IS NULL OR LENGTH(state) = 2", 
         "warning",
         "State code should be 2-letter abbreviation"),
        
        ("silver_store_dim", "valid_coordinates", 
         "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180", 
         "warning",
         "Coordinates should be within valid geographic ranges"),
        
        # ===== SILVER_PRODUCT_DIM (Dimension Table) =====
        
        # CRITICAL: Primary Key
        ("silver_product_dim", "valid_upc_code", 
         "upc_code IS NOT NULL AND LENGTH(upc_code) > 0", 
         "critical",
         "UPC code must be present and non-empty (primary key)"),
        
        # CRITICAL: Required Fields
        ("silver_product_dim", "valid_product_description", 
         "product_description IS NOT NULL", 
         "critical",
         "Product description must be present"),
        
        # WARNING: Format Validation
        ("silver_product_dim", "valid_upc_length", 
         "LENGTH(upc_code) BETWEEN 12 AND 14", 
         "warning",
         "UPC code should be 12-14 digits"),
        
        # Add more rules for other tables...
    ]
    
    # Create DataFrame
    from pyspark.sql import Row
    
    rows = [
        Row(
            table_name=rule[0],
            rule_name=rule[1],
            constraint_sql=rule[2],
            severity=rule[3],
            description=rule[4] if len(rule) > 4 else "",
            created_timestamp=None,  # Will be set to current_timestamp
            updated_timestamp=None   # Will be set to current_timestamp
        )
        for rule in rules
    ]
    
    rules_df = (
        spark.createDataFrame(rows)
        .withColumn("created_timestamp", current_timestamp())
        .withColumn("updated_timestamp", current_timestamp())
    )
    
    # Write to table
    rules_table = f"{catalog}.{schema}.dq_rules"
    rules_df.write.mode("overwrite").saveAsTable(rules_table)
    
    rule_count = rules_df.count()
    print(f"✓ Populated {rule_count} data quality rules")
    
    # Show summary
    summary = spark.sql(f"""
        SELECT 
            table_name,
            severity,
            COUNT(*) as rule_count
        FROM {rules_table}
        GROUP BY table_name, severity
        ORDER BY table_name, severity
    """)
    
    print("\nData Quality Rules Summary:")
    summary.show(truncate=False)


def main():
    """Main entry point for DQ rules table setup."""
    from pyspark.sql import SparkSession
    
    catalog, silver_schema = get_parameters()
    
    spark = SparkSession.builder.appName("DQ Rules Setup").getOrCreate()
    
    print("=" * 80)
    print("DATA QUALITY RULES TABLE SETUP")
    print("=" * 80)
    
    try:
        create_dq_rules_table(spark, catalog, silver_schema)
        populate_dq_rules(spark, catalog, silver_schema)
        
        print("\n" + "=" * 80)
        print("✓ DQ rules table created and populated!")
        print("=" * 80)
        print(f"\nRules table: {catalog}.{silver_schema}.dq_rules")
        print("\nNext steps:")
        print("  1. Review rules: SELECT * FROM {catalog}.{silver_schema}.dq_rules")
        print("  2. Deploy Silver DLT pipeline with dq_rules_loader.py")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

---

## Step 2: Rules Loader Helper Module

### File: `dq_rules_loader.py`

**⚠️ CRITICAL: This MUST be a pure Python file (NOT a Databricks notebook)**

- NO `# Databricks notebook source` header at the top
- Must be importable using standard Python imports
- Functions to load rules from Delta table at DLT pipeline runtime

**Official Pattern:** [Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations)

```python
"""
Data Quality Rules Loader for Silver Layer DLT Pipelines

Loads data quality rules from Unity Catalog Delta table at DLT pipeline runtime.

This module provides functions to:
- Load rules filtered by table name and severity
- Apply expectations using @dlt.expect_all_or_drop() and @dlt.expect_all()
- Generate quarantine conditions

Benefits over hardcoded rules:
- ✅ Update rules without code changes (just UPDATE the Delta table)
- ✅ Centralized rule management across all pipelines
- ✅ Auditable (Delta table versioning)
- ✅ Queryable for documentation and reporting
- ✅ Portable across environments (dev/prod)

Reference: https://docs.databricks.com/aws/en/ldp/expectation-patterns
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col


def get_rules_table_name() -> str:
    """
    Get the fully qualified DQ rules table name from DLT configuration.
    
    Returns:
        Fully qualified table name: "{catalog}.{schema}.dq_rules"
    """
    spark = SparkSession.getActiveSession()
    catalog = spark.conf.get("catalog")
    silver_schema = spark.conf.get("silver_schema")
    return f"{catalog}.{silver_schema}.dq_rules"


def get_rules(table_name: str, severity: str) -> dict:
    """
    Load data quality rules from Delta table for a specific table and severity.
    
    Args:
        table_name: Silver table name (e.g., "silver_transactions")
        severity: Rule severity ("critical" or "warning")
    
    Returns:
        Dictionary mapping rule names to SQL constraint expressions
        Format: {"rule_name": "constraint_sql", ...}
    
    Example:
        critical_rules = get_rules("silver_transactions", "critical")
        # Returns: {
        #   "valid_transaction_id": "transaction_id IS NOT NULL AND LENGTH(transaction_id) > 0",
        #   "valid_store_number": "store_number IS NOT NULL",
        #   ...
        # }
    """
    spark = SparkSession.getActiveSession()
    rules_table = get_rules_table_name()
    
    df = (
        spark.read.table(rules_table)
        .filter(
            (col("table_name") == table_name) & 
            (col("severity") == severity)
        )
        .collect()
    )
    
    return {
        row['rule_name']: row['constraint_sql']
        for row in df
    }


def get_critical_rules_for_table(table_name: str) -> dict:
    """
    Get critical DQ rules for a specific table.
    
    Critical rules cause records to be dropped/quarantined if violated.
    Use with: @dlt.expect_all_or_drop(get_critical_rules_for_table("table_name"))
    
    Args:
        table_name: Silver table name
    
    Returns:
        Dictionary of critical rules
    """
    return get_rules(table_name, "critical")


def get_warning_rules_for_table(table_name: str) -> dict:
    """
    Get warning DQ rules for a specific table.
    
    Warning rules are logged but allow records to pass through.
    Use with: @dlt.expect_all(get_warning_rules_for_table("table_name"))
    
    Args:
        table_name: Silver table name
    
    Returns:
        Dictionary of warning rules
    """
    return get_rules(table_name, "warning")


def get_quarantine_condition(table_name: str) -> str:
    """
    Generate SQL condition for quarantine table (inverse of critical rules).
    
    Returns SQL expression that evaluates to TRUE for records that fail
    ANY critical rule (should be quarantined).
    
    Args:
        table_name: Silver table name
    
    Returns:
        SQL WHERE clause for quarantine filter
        
    Example:
        condition = get_quarantine_condition("silver_transactions")
        # Returns: "NOT (transaction_id IS NOT NULL) OR NOT (store_number IS NOT NULL) OR ..."
    """
    critical_rules = get_critical_rules_for_table(table_name)
    
    if not critical_rules:
        return "FALSE"  # No rules = no quarantine
    
    # Invert each rule and OR them together
    quarantine_conditions = [f"NOT ({constraint})" for constraint in critical_rules.values()]
    return " OR ".join(quarantine_conditions)


def list_all_rules_for_table(table_name: str) -> None:
    """
    Print all rules for a specific table (debugging/documentation).
    
    Args:
        table_name: Silver table name
    """
    spark = SparkSession.getActiveSession()
    rules_table = get_rules_table_name()
    
    print(f"\nData Quality Rules for {table_name}:")
    print("=" * 80)
    
    rules_df = (
        spark.read.table(rules_table)
        .filter(col("table_name") == table_name)
        .orderBy("severity", "rule_name")
    )
    
    rules_df.show(truncate=False)
```

**See [07-dlt-expectations-patterns.mdc](mdc:.cursor/rules/07-dlt-expectations-patterns.mdc) for complete patterns.**

---

## Step 3: DLT Table Helper Function

**Every DLT notebook MUST include this helper at the top:**

```python
def get_bronze_table(table_name):
    """
    Helper function to get fully qualified Bronze table name from DLT configuration.
    
    Supports DLT Direct Publishing Mode - uses catalog/schema from pipeline config.
    
    Args:
        table_name: Name of the Bronze table (e.g., "bronze_transactions")
    
    Returns:
        Fully qualified table name: "{catalog}.{schema}.{table_name}"
    """
    from pyspark.sql import SparkSession
    spark = SparkSession.getActiveSession()
    catalog = spark.conf.get("catalog")
    bronze_schema = spark.conf.get("bronze_schema")
    return f"{catalog}.{bronze_schema}.{table_name}"
```

**Why This Helper?**
- DLT Direct Publishing Mode requires fully qualified table names
- No more `LIVE.` prefix (deprecated pattern)
- Configuration comes from DLT pipeline YAML
- Single source of truth for table references

**Usage:**
```python
dlt.read_stream(get_bronze_table("bronze_transactions"))
# Expands to: catalog.bronze_schema.bronze_transactions
```

---

## Step 4: Standard Silver Table Pattern

### Template for ALL Silver Tables

**Key Principle: Clone Bronze schema + Load DQ rules from Delta table + Add derived fields**

```python
# Databricks notebook source

"""
{Project} Silver Layer - {Entity Type} Tables with DLT

Delta Live Tables pipeline for Silver {entity_type} tables with:
- Data quality expectations loaded from Delta table (dq_rules)
- Automatic liquid clustering (cluster_by_auto=True)
- Advanced Delta Lake features (row tracking, deletion vectors)
- Schema cloning from Bronze with minimal transformation

Reference: https://docs.databricks.com/aws/en/ldp/expectation-patterns
"""

import dlt
from pyspark.sql.functions import col, current_timestamp, sha2, concat_ws, coalesce, when, lit, upper, trim

# Import DQ rules loader (pure Python module, not notebook)
from dq_rules_loader import (
    get_critical_rules_for_table,
    get_warning_rules_for_table,
    get_quarantine_condition
)

# Get configuration from DLT pipeline
def get_bronze_table(table_name):
    """Helper function to get fully qualified Bronze table name from DLT configuration."""
    from pyspark.sql import SparkSession
    spark = SparkSession.getActiveSession()
    catalog = spark.conf.get("catalog")
    bronze_schema = spark.conf.get("bronze_schema")
    return f"{catalog}.{bronze_schema}.{table_name}"


# ============================================================================
# SILVER {ENTITY} TABLE
# ============================================================================

@dlt.table(
    name="silver_{entity}",
    comment="""LLM: Silver layer {entity_description} with data quality rules loaded from 
    Delta table, streaming ingestion, and business rule validation""",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "application": "{project_name}",
        "project": "{project_demo}",
        "layer": "silver",
        "source_table": "bronze_{entity}",
        "domain": "{domain}",  # retail, sales, inventory, product, logistics
        "entity_type": "{type}",  # dimension, fact
        "contains_pii": "{true|false}",
        "data_classification": "{confidential|internal}",
        "consumer": "{team}",
        "developer": "edp",
        "support": "edp",
        "business_owner": "{Business Team}",
        "technical_owner": "Data Engineering",
        "business_owner_email": "{email}@company.com",
        "technical_owner_email": "data-engineering@company.com"
    },
    cluster_by_auto=True  # ⚠️ ALWAYS AUTO, never specify columns manually
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_{entity}"))
@dlt.expect_all(get_warning_rules_for_table("silver_{entity}"))
def silver_{entity}():
    """
    Silver {entity} with data quality rules loaded from Unity Catalog Delta table.
    
    Schema Strategy: Clone Bronze schema with minimal transformation
    - ✅ Same column names as Bronze
    - ✅ Same data types
    - ✅ Add derived flags (is_*, has_*)
    - ✅ Add business keys (SHA256 hashes)
    - ✅ Add processed_timestamp
    
    Data Quality Rules (loaded from {catalog}.{silver_schema}.dq_rules):
    
    CRITICAL (Record DROPPED/QUARANTINED, pipeline continues):
    - Rules loaded from Delta table WHERE severity = 'critical'
    - {List critical rules - primary keys, required dates, FKs}
    
    WARNING (Logged but record passes through):
    - Rules loaded from Delta table WHERE severity = 'warning'
    - {List warning rules - business logic, reasonableness}
    
    Update rules at runtime:
        UPDATE {catalog}.{silver_schema}.dq_rules 
        SET constraint_sql = 'new constraint'
        WHERE table_name = 'silver_{entity}' AND rule_name = 'rule_name'
    
    Pipeline behavior:
    - ✅ Pipeline NEVER FAILS on data quality issues
    - ✅ Records violating CRITICAL rules are QUARANTINED
    - ✅ Records violating WARNING rules pass through (logged)
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_{entity}"))
        
        # ========================================
        # MINIMAL TRANSFORMATIONS (Clone Bronze schema)
        # ========================================
        
        # Add business key (SHA256 hash of natural key)
        .withColumn("{entity}_business_key",
                   sha2(concat_ws("||", col("natural_key1"), col("natural_key2")), 256))
        
        # Add derived boolean flags (simple business indicators)
        .withColumn("is_{flag_name}", 
                   when(col("field") > threshold, True).otherwise(False))
        
        # Add processed timestamp
        .withColumn("processed_timestamp", current_timestamp())
        
        # ========================================
        # AVOID IN SILVER (Save for Gold):
        # - Aggregations
        # - Complex calculations
        # - Joining across tables
        # - Major schema restructuring
        # ========================================
    )
```

### Dimension Table Example

```python
@dlt.table(
    name="silver_store_dim",
    comment="LLM: Silver layer store dimension with validated location data and deduplication. Rules loaded dynamically from dq_rules Delta table.",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "layer": "silver",
        "source_table": "bronze_store_dim",
        "domain": "retail",
        "entity_type": "dimension",
        "contains_pii": "true",
        "data_classification": "confidential"
    },
    cluster_by_auto=True
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_store_dim"))
@dlt.expect_all(get_warning_rules_for_table("silver_store_dim"))
def silver_store_dim():
    """
    Silver store dimension - clones Bronze schema with validation.
    
    Transformations:
    - ✅ Standardize state code (UPPER, TRIM)
    - ✅ Add business key hash
    - ✅ Add processed timestamp
    - ❌ NO aggregation
    - ❌ NO complex calculations
    
    DQ Rules (from dq_rules table):
    - CRITICAL: store_number NOT NULL, store_name NOT NULL
    - WARNING: state format (2 letters), valid coordinates
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_store_dim"))
        .withColumn("state", upper(trim(col("state"))))  # Minimal standardization
        .withColumn("store_business_key", 
                   sha2(concat_ws("||", col("store_number"), col("store_name")), 256))
        .withColumn("processed_timestamp", current_timestamp())
    )
```

### Fact Table Example with Quarantine

```python
@dlt.table(
    name="silver_transactions",
    comment="""LLM: Silver layer streaming fact table for transactions with comprehensive 
    data quality rules loaded from Delta table and quarantine pattern""",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "layer": "silver",
        "source_table": "bronze_transactions",
        "domain": "sales",
        "entity_type": "fact",
        "contains_pii": "true",
        "data_classification": "confidential"
    },
    cluster_by_auto=True
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_transactions"))
@dlt.expect_all(get_warning_rules_for_table("silver_transactions"))
def silver_transactions():
    """
    Silver transactions - clones Bronze with simple derived fields.
    
    Transformations:
    - ✅ Calculate total_discount (sum of discount fields)
    - ✅ Add is_return flag (quantity < 0)
    - ✅ Add business key hash
    - ❌ NO daily aggregation (that's Gold)
    - ❌ NO dimension lookups (that's Gold)
    
    DQ Rules (from dq_rules table):
    - CRITICAL: transaction_id, store_number, upc_code, date (all NOT NULL)
    - CRITICAL: quantity != 0, price > 0
    - WARNING: reasonable quantity/price ranges, recent transactions
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_transactions"))
        
        # Simple derived fields (single-record calculations only)
        .withColumn("total_discount_amount",
                   coalesce(col("multi_unit_discount"), lit(0)) +
                   coalesce(col("coupon_discount"), lit(0)) +
                   coalesce(col("loyalty_discount"), lit(0)))
        
        # Simple boolean flags
        .withColumn("is_return", when(col("quantity_sold") < 0, True).otherwise(False))
        .withColumn("is_loyalty_transaction", 
                   when(col("loyalty_id").isNotNull(), True).otherwise(False))
        
        # Standard audit fields
        .withColumn("processed_timestamp", current_timestamp())
        .withColumn("transaction_business_key",
                   sha2(concat_ws("||", col("transaction_id")), 256))
    )


# ============================================================================
# QUARANTINE TABLE (Captures records that fail CRITICAL rules)
# ============================================================================

@dlt.table(
    name="silver_transactions_quarantine",
    comment="""LLM: Quarantine table for transactions that failed CRITICAL data quality checks. 
    Records here require manual review and remediation before promotion to Silver.
    Filter condition dynamically generated from dq_rules Delta table.""",
    table_properties={
        "quality": "quarantine",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "layer": "silver",
        "source_table": "bronze_transactions",
        "domain": "sales",
        "entity_type": "quarantine",
        "contains_pii": "true",
        "data_classification": "confidential"
    },
    cluster_by_auto=True
)
def silver_transactions_quarantine():
    """
    Quarantine table for records that fail CRITICAL validations.
    
    Filter condition is automatically generated from dq_rules table as the
    inverse of all critical rules for silver_transactions.
    
    Pipeline behavior:
    - ✅ Pipeline continues (no failure)
    - ✅ Invalid records captured here
    - ✅ Valid records flow to silver_transactions
    - ✅ WARNING violations not captured (logged only)
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_transactions"))
        # Use centralized quarantine condition (loaded from dq_rules table)
        .filter(get_quarantine_condition("silver_transactions"))
        .withColumn("quarantine_reason",
            when(col("transaction_id").isNull(), "CRITICAL: Missing transaction ID (primary key)")
            .when(col("store_number").isNull(), "CRITICAL: Missing store number (FK)")
            .when(col("upc_code").isNull(), "CRITICAL: Missing UPC code (FK)")
            .when(col("transaction_date").isNull(), "CRITICAL: Missing transaction date")
            .when(col("quantity_sold") == 0, "CRITICAL: Quantity is zero")
            .when(col("final_sales_price") <= 0, "CRITICAL: Invalid final sales price")
            .otherwise("CRITICAL: Multiple validation failures"))
        .withColumn("quarantine_timestamp", current_timestamp())
    )
```

---

## Step 5: Data Quality Monitoring Views

### File: `data_quality_monitoring.py`

Create DLT views to monitor data quality metrics in real-time:

```python
# Databricks notebook source

"""
{Project} Silver Layer - Data Quality Monitoring Views

Delta Live Tables views for monitoring data quality metrics, expectation failures,
and overall pipeline health across the Silver layer.
"""

import dlt
from pyspark.sql.functions import (
    col, count, sum as spark_sum, avg, min as spark_min, 
    max as spark_max, current_timestamp, lit, when
)

# ============================================================================
# DATA QUALITY METRICS - PER TABLE
# ============================================================================

@dlt.table(
    name="dq_transactions_metrics",
    comment="""LLM: Real-time data quality metrics for transactions showing record counts, 
    validation pass rates, quarantine rates, and business rule compliance""",
    table_properties={
        "quality": "monitoring",
        "layer": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def dq_transactions_metrics():
    """
    Comprehensive data quality metrics for transactions.
    
    Metrics:
    - Total records processed
    - Records in Silver vs Quarantine
    - Pass/fail rates
    - Business rule violations
    """
    silver = dlt.read("silver_transactions")
    quarantine = dlt.read("silver_transactions_quarantine")
    
    # Calculate metrics
    silver_metrics = silver.agg(
        count("*").alias("silver_record_count"),
        spark_sum(when(col("is_return"), 1).otherwise(0)).alias("return_count"),
        spark_sum(when(col("is_loyalty_transaction"), 1).otherwise(0)).alias("loyalty_transaction_count")
    )
    
    quarantine_metrics = quarantine.agg(
        count("*").alias("quarantine_record_count")
    )
    
    # Combine and calculate rates
    return (
        silver_metrics
        .crossJoin(quarantine_metrics)
        .withColumn("total_records", 
                   col("silver_record_count") + col("quarantine_record_count"))
        .withColumn("silver_pass_rate",
                   (col("silver_record_count") / col("total_records")) * 100)
        .withColumn("quarantine_rate",
                   (col("quarantine_record_count") / col("total_records")) * 100)
        .withColumn("metric_timestamp", current_timestamp())
    )


# ============================================================================
# REFERENTIAL INTEGRITY CHECKS
# ============================================================================

@dlt.table(
    name="dq_referential_integrity",
    comment="""LLM: Referential integrity validation between fact and dimension tables. 
    Identifies orphaned records and missing references.""",
    table_properties={
        "quality": "monitoring",
        "layer": "silver"
    }
)
def dq_referential_integrity():
    """
    Check referential integrity between Silver fact and dimension tables.
    
    Validates:
    - Facts reference valid dimensions
    - No orphaned records
    """
    transactions = dlt.read("silver_transactions")
    stores = dlt.read("silver_store_dim")
    products = dlt.read("silver_product_dim")
    
    # Check for orphaned transactions (invalid store references)
    orphaned_stores = (
        transactions
        .join(stores.select("store_number"), ["store_number"], "left_anti")
        .agg(
            lit("transactions_to_stores").alias("check_name"),
            count("*").alias("orphaned_records")
        )
        .withColumn("status",
                   when(col("orphaned_records") == 0, "PASS")
                   .when(col("orphaned_records") < 10, "WARNING")
                   .otherwise("FAIL"))
        .withColumn("check_timestamp", current_timestamp())
    )
    
    # Check for orphaned transactions (invalid product references)
    orphaned_products = (
        transactions
        .join(products.select("upc_code"), ["upc_code"], "left_anti")
        .agg(
            lit("transactions_to_products").alias("check_name"),
            count("*").alias("orphaned_records")
        )
        .withColumn("status",
                   when(col("orphaned_records") == 0, "PASS")
                   .when(col("orphaned_records") < 10, "WARNING")
                   .otherwise("FAIL"))
        .withColumn("check_timestamp", current_timestamp())
    )
    
    return orphaned_stores.union(orphaned_products)
```

---

## Step 6: DLT Pipeline Configuration

### File: `resources/silver_dlt_pipeline.yml`

```yaml
resources:
  pipelines:
    silver_dlt_pipeline:
      name: "[${bundle.target}] Silver Layer Pipeline"
      
      # Pipeline root folder (Lakeflow Pipelines Editor best practice)
      # All pipeline assets must be within this root folder
      root_path: ../src/{project}_silver
      
      # DLT Direct Publishing Mode (Modern Pattern)
      # ✅ Use 'schema' field (not 'target' - deprecated)
      catalog: ${var.catalog}
      schema: ${var.silver_schema}
      
      # DLT Libraries (Python notebooks or SQL files)
      libraries:
        - notebook:
            path: ../src/{project}_silver/silver_dimensions.py
        - notebook:
            path: ../src/{project}_silver/silver_transactions.py
        - notebook:
            path: ../src/{project}_silver/silver_inventory.py
        - notebook:
            path: ../src/{project}_silver/data_quality_monitoring.py
      
      # Pipeline Configuration (passed to notebooks)
      # Use fully qualified table names in notebooks: {catalog}.{schema}.{table}
      configuration:
        catalog: ${var.catalog}
        bronze_schema: ${var.bronze_schema}
        silver_schema: ${var.silver_schema}
        pipelines.enableTrackHistory: "true"
      
      # Serverless Compute
      serverless: true
      
      # Photon Engine
      photon: true
      
      # Channel (CURRENT = latest features)
      channel: CURRENT
      
      # Continuous vs Triggered
      continuous: false
      
      # Development Mode (faster iteration, auto-recovery)
      development: true
      
      # Edition (ADVANCED for expectations, SCD, etc.)
      edition: ADVANCED
      
      # Notifications
      notifications:
        - alerts:
            - on-update-failure
            - on-update-fatal-failure
            - on-flow-failure
          email_recipients:
            - data-engineering@company.com
      
      # Tags
      tags:
        environment: ${bundle.target}
        project: {project_name}
        layer: silver
        pipeline_type: medallion
        compute_type: serverless
```

---

## Step 7: Asset Bundle Configuration

### File: `resources/silver_dq_setup_job.yml`

**One-time job to create and populate the DQ rules table:**

```yaml
resources:
  jobs:
    silver_dq_setup_job:
      name: "[${bundle.target}] {Project} Silver Layer - DQ Rules Setup"
      description: "One-time: Create and populate data quality rules Delta table"
      
      tasks:
        - task_key: setup_dq_rules_table
          notebook_task:
            notebook_path: ../src/{project}_silver/setup_dq_rules_table.py
            base_parameters:
              catalog: ${var.catalog}
              silver_schema: ${var.silver_schema}
      
      email_notifications:
        on_failure:
          - data-engineering@company.com
      
      tags:
        environment: ${bundle.target}
        layer: silver
        job_type: setup
```

---

## Implementation Checklist

### Phase 1: DQ Rules Table Setup (30 min)
- [ ] Create `src/{project}_silver/` directory
- [ ] Create `setup_dq_rules_table.py` (Databricks notebook)
- [ ] Define all DQ rules with: table_name, rule_name, constraint_sql, severity, description
- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run: `databricks bundle run silver_dq_setup_job -t dev`
- [ ] Verify: `SELECT * FROM {catalog}.{silver_schema}.dq_rules`

### Phase 2: Rules Loader Module (15 min)
- [ ] Create `dq_rules_loader.py` as **pure Python file** (NO notebook header)
- [ ] Add functions: `get_critical_rules_for_table()`, `get_warning_rules_for_table()`, `get_quarantine_condition()`
- [ ] Test imports work (verify no notebook header)

### Phase 3: DLT Notebooks (1-2 hours)
- [ ] Create dimension notebooks (e.g., `silver_dimensions.py`)
  - [ ] Add `get_bronze_table()` helper function
  - [ ] Import DQ rules: `from dq_rules_loader import ...`
  - [ ] Create table with `@dlt.table()` decorator
  - [ ] Apply critical rules: `@dlt.expect_all_or_drop(get_critical_rules_for_table(...))`
  - [ ] Apply warning rules: `@dlt.expect_all(get_warning_rules_for_table(...))`
  - [ ] Clone Bronze schema with minimal transformations
  - [ ] Add business key, processed_timestamp
  - [ ] Use `cluster_by_auto=True`
  
- [ ] Create fact notebooks (e.g., `silver_transactions.py`)
  - [ ] Same steps as dimensions
  - [ ] Add derived boolean flags (is_return, is_loyalty, etc.)
  - [ ] Create quarantine table using `get_quarantine_condition()`
  - [ ] Add quarantine_reason, quarantine_timestamp

### Phase 4: Monitoring (30 min)
- [ ] Create `data_quality_monitoring.py`
- [ ] Add DQ metrics view per table
- [ ] Add referential integrity checks
- [ ] Add data freshness monitoring

### Phase 5: Pipeline Configuration (15 min)
- [ ] Create `resources/silver_dlt_pipeline.yml`
- [ ] Set `root_path` to `../src/{project}_silver`
- [ ] Use `catalog` + `schema` fields (Direct Publishing Mode)
- [ ] Add all notebook libraries
- [ ] Pass configuration: catalog, bronze_schema, silver_schema
- [ ] Set `serverless: true`, `edition: ADVANCED`
- [ ] Configure notifications

### Phase 6: Testing (30 min)
- [ ] Validate `dq_rules_loader.py` has no notebook header
- [ ] Test import: `from dq_rules_loader import get_critical_rules_for_table`
- [ ] Deploy DLT pipeline: `databricks bundle deploy -t dev`
- [ ] Trigger pipeline: `databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline"`
- [ ] Verify Silver tables created
- [ ] Check quarantine table has failed records
- [ ] Review DQ metrics views

---

## Managing Rules at Runtime

### Query Rules

```sql
-- View all rules for a table
SELECT * FROM {catalog}.{silver_schema}.dq_rules
WHERE table_name = 'silver_transactions'
ORDER BY severity, rule_name;

-- Count rules by table and severity
SELECT 
  table_name,
  severity,
  COUNT(*) as rule_count
FROM {catalog}.{silver_schema}.dq_rules
GROUP BY table_name, severity
ORDER BY table_name, severity;
```

### Update Rules (No Code Changes Needed!)

```sql
-- Update a constraint (e.g., adjust threshold)
UPDATE {catalog}.{silver_schema}.dq_rules
SET constraint_sql = 'quantity_sold BETWEEN -30 AND 75',
    updated_timestamp = CURRENT_TIMESTAMP()
WHERE table_name = 'silver_transactions' 
  AND rule_name = 'reasonable_quantity';

-- Change severity
UPDATE {catalog}.{silver_schema}.dq_rules
SET severity = 'warning',  -- Downgrade from critical to warning
    updated_timestamp = CURRENT_TIMESTAMP()
WHERE table_name = 'silver_transactions' 
  AND rule_name = 'valid_loyalty_id';

-- Add new rule
INSERT INTO {catalog}.{silver_schema}.dq_rules
VALUES (
  'silver_transactions',
  'valid_payment_method',
  'payment_method IN (''Cash'', ''Credit'', ''Debit'', ''Mobile'')',
  'warning',
  'Payment method should be one of the valid types',
  CURRENT_TIMESTAMP(),
  CURRENT_TIMESTAMP()
);
```

**After updating rules:**
- Rules take effect on next DLT pipeline update
- No code deployment required
- Changes are versioned in Delta table (time travel)

### Audit Rule Changes

```sql
-- View rule change history (Delta time travel)
SELECT *
FROM {catalog}.{silver_schema}.dq_rules VERSION AS OF 1
WHERE table_name = 'silver_transactions';

-- Compare current vs previous rules
SELECT 
  current.rule_name,
  current.constraint_sql as current_constraint,
  previous.constraint_sql as previous_constraint
FROM {catalog}.{silver_schema}.dq_rules current
LEFT JOIN {catalog}.{silver_schema}.dq_rules VERSION AS OF 1 previous
  ON current.table_name = previous.table_name 
  AND current.rule_name = previous.rule_name
WHERE current.constraint_sql != previous.constraint_sql;
```

---

## Key Principles

### 1. Schema Cloning (Silver = Bronze + DQ)
- ✅ Keep same column names as Bronze
- ✅ Keep same data types
- ✅ Add data quality rules (main value-add)
- ✅ Add simple derived flags
- ❌ No complex transformations (save for Gold)
- ❌ No aggregations (save for Gold)
- ❌ No joins (save for Gold)

### 2. Pipeline Never Fails
- ✅ Critical rules drop/quarantine records, pipeline continues
- ✅ Warning rules log violations, records pass through
- ✅ No `@dlt.expect_or_fail()` - use `@dlt.expect_all_or_drop()` instead

### 3. Delta Table for Rules (Databricks Best Practice)
- ✅ Single source of truth: Delta table in Unity Catalog
- ✅ Updateable at runtime (no code changes)
- ✅ Auditable (Delta versioning)
- ✅ Queryable for documentation
- ✅ Portable across environments

**Reference:** [Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations)

### 4. Pure Python for Loader
- ✅ Loader file must be importable (NO notebook header)
- ✅ Use standard Python imports
- ✅ Works with DLT ADVANCED edition

### 5. Auto Clustering
- ✅ Always `cluster_by_auto=True`
- ❌ Never specify columns manually
- ✅ Delta automatically optimizes

### 6. Governance First
- ✅ Complete table properties on every table
- ✅ Include: layer, domain, entity_type, contains_pii, data_classification
- ✅ Business owner + Technical owner

### 7. Business Keys
- ✅ Generate SHA256 hashes for tracking
- ✅ Use `sha2(concat_ws("||", col("key1"), col("key2")), 256)`
- ✅ Named: `{entity}_business_key`

### 8. Direct Publishing Mode
- ✅ Use fully qualified table names
- ✅ Helper: `get_bronze_table(table_name)`
- ✅ Configure: `catalog` + `schema` in YAML
- ❌ No `LIVE.` prefix (deprecated)

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Notebook Header in Loader File
```python
# dq_rules_loader.py
# Databricks notebook source  # ❌ Makes it a notebook, breaks imports!

def get_critical_rules_for_table(table_name):
    return {}
```
**Fix:** Remove `# Databricks notebook source` line

### ❌ Mistake 2: Hardcoding Rules in Notebooks
```python
# ❌ WRONG: Hardcoded rules (not updateable at runtime)
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
@dlt.expect_or_drop("valid_date", "date IS NOT NULL")
```
**Fix:** Load from Delta table using `get_critical_rules_for_table()`

### ❌ Mistake 3: Complex Transformations in Silver
```python
# ❌ WRONG: Aggregation belongs in Gold
def silver_sales_daily():
    return (
        dlt.read_stream(get_bronze_table("bronze_transactions"))
        .groupBy("store_number", "transaction_date")  # ❌ Aggregation!
        .agg(sum("revenue").alias("daily_revenue"))
    )
```
**Fix:** Keep Silver at transaction grain, aggregate in Gold

### ❌ Mistake 4: Manual Clustering Columns
```python
# ❌ WRONG: Manual clustering
@dlt.table(
    cluster_by=["store_number", "transaction_date"]  # ❌ Don't specify!
)
```
**Fix:** Always use `cluster_by_auto=True`

### ❌ Mistake 5: Using expect_or_fail
```python
# ❌ WRONG: Pipeline fails on bad data
@dlt.expect_or_fail("valid_id", "id IS NOT NULL")
```
**Fix:** Use `@dlt.expect_all_or_drop()` for critical rules

### ❌ Mistake 6: Not Creating DQ Rules Table First
```python
# ❌ WRONG: DLT pipeline tries to read non-existent dq_rules table
# Pipeline Error: Table or view not found: dq_rules
```
**Fix:** Run `silver_dq_setup_job` BEFORE deploying DLT pipeline

---

## References

### Official Databricks Documentation
- [DLT Expectations](https://docs.databricks.com/aws/en/dlt/expectations)
- [DLT Expectation Patterns](https://docs.databricks.com/aws/en/ldp/expectation-patterns)
- [Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations)
- [Share Code Between Notebooks](https://docs.databricks.com/aws/en/notebooks/share-code)
- [Automatic Clustering](https://docs.databricks.com/aws/en/delta/clustering#enable-or-disable-automatic-liquid-clustering)

### Framework Rules
- [07-dlt-expectations-patterns.mdc](mdc:.cursor/rules/07-dlt-expectations-patterns.mdc) - Complete DLT patterns

---

## Summary: What to Create

1. **`setup_dq_rules_table.py`** (Databricks notebook) - Create and populate DQ rules Delta table
2. **`dq_rules_loader.py`** (pure Python) - Functions to load rules from Delta table
3. **`silver_dimensions.py`** (DLT notebook) - Dimension tables
4. **`silver_transactions.py`** (DLT notebook) - Fact tables with quarantine
5. **`silver_inventory.py`** (DLT notebook, optional) - Additional fact tables
6. **`data_quality_monitoring.py`** (DLT notebook) - Monitoring views
7. **`resources/silver_dq_setup_job.yml`** - DQ rules setup job
8. **`resources/silver_dlt_pipeline.yml`** - Pipeline configuration

**Core Philosophy:** Silver = Bronze schema clone + Delta table-driven data quality validation

**Time Estimate:** 3-4 hours for initial setup, 1 hour per additional table

**Deployment Order:**
1. Deploy and run `silver_dq_setup_job` (creates dq_rules table)
2. Deploy and run `silver_dlt_pipeline` (loads rules from table)
3. Update rules in Delta table as needed (no redeployment!)



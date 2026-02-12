---
name: dlt-expectations-patterns
description: Delta Live Tables expectations patterns for data quality with Unity Catalog Delta table storage. Use when implementing Silver layer DLT pipelines, creating portable data quality rules, or needing runtime-updateable expectations without code deployment. Supports severity-based filtering (critical vs warning) and quarantine patterns.
metadata:
  author: prashanth subrahmanyam
  version: "1.0"
  domain: silver
  role: worker
  pipeline_stage: 3
  pipeline_stage_name: silver
  called_by:
    - silver-layer-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/spark-declarative-pipelines/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-09"
      sync_commit: "97a3637"
---
# Delta Live Tables Expectations Patterns

## Overview

All Silver layer tables use data quality expectations loaded from a **Unity Catalog Delta table**. This skill standardizes the Delta table-based approach for portable, maintainable, and runtime-updateable data quality management.

**Key Patterns:**
1. **Delta Table for Rules Storage** - Single source of truth in Unity Catalog
2. **Rules Loader Module** - Pure Python functions to load rules at runtime
3. **`@dlt.expect_all_or_drop()` Decorator** - Strict enforcement pattern
4. **Direct Publishing Mode** - Fully qualified table names with `get_source_table()` helper
5. **Severity-Based Filtering** - Critical vs warning rules

**Official Reference:** [Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations)

## When to Use This Skill

Use this skill when:
- Implementing Silver layer DLT pipelines with data quality expectations
- Creating portable data quality rules that can be shared across pipelines
- Needing runtime-updateable expectations without code deployment
- Requiring severity-based filtering (critical vs warning rules)
- Implementing quarantine patterns for failed validations

## Benefits of Delta Table-Based Rules

### Why Delta Table Instead of Hardcoded Rules?

| Aspect | Hardcoded Rules | Delta Table Rules |
|---|---|---|
| **Updateability** | Requires code changes + redeployment | UPDATE table, rules apply immediately |
| **Auditability** | Git history only | Delta time travel + Git history |
| **Portability** | Copied across environments | Shared table across pipelines |
| **Documentation** | In code comments | Queryable with SQL |
| **Maintenance** | Edit multiple notebooks | Single table UPDATE |
| **Governance** | No access control | Unity Catalog permissions |

**Recommended by Databricks:** "Store expectation definitions separately from pipeline logic to easily apply expectations to multiple datasets or pipelines. Update, audit, and maintain expectations without modifying pipeline source code."

## Quick Reference

### DLT Direct Publishing Mode (Modern Pattern)

**DEPRECATED Patterns (Do NOT use):**
- ❌ `LIVE.` prefix for table references (e.g., `LIVE.bronze_transactions`)
- ❌ `target:` field in DLT pipeline configuration

**MODERN Pattern (Always use):**
- ✅ **Fully qualified table names**: `{catalog}.{schema}.{table_name}`
- ✅ **`schema:` field** in DLT pipeline configuration (not `target`)
- ✅ **Helper function** to build table names from configuration

### Helper Function Pattern

```python
def get_source_table(table_name, source_schema_key="bronze_schema"):
    """Get fully qualified table name from DLT configuration."""
    spark = SparkSession.getActiveSession()
    catalog = spark.conf.get("catalog")
    schema = spark.conf.get(source_schema_key)
    return f"{catalog}.{schema}.{table_name}"

# Use in DLT table
@dlt.table(...)
def silver_transactions():
    return dlt.read_stream(get_source_table("bronze_transactions"))
```

### DLT Pipeline Configuration

```yaml
resources:
  pipelines:
    silver_dlt_pipeline:
      name: "[${bundle.target}] Silver Layer Pipeline"
      
      # ✅ CORRECT: Use 'schema' (Direct Publishing Mode)
      catalog: ${var.catalog}
      schema: ${var.silver_schema}
      
      # ❌ WRONG: Don't use 'target' (deprecated)
      # target: ${var.catalog}.${var.silver_schema}
      
      configuration:
        catalog: ${var.catalog}
        bronze_schema: ${var.bronze_schema}
        silver_schema: ${var.silver_schema}
      
      serverless: true
      edition: ADVANCED
```

## Critical Rules

### 1. Rules Loader Module (Pure Python, NO Notebook Header)

**⚠️ CRITICAL: Pure Python file (NO `# Databricks notebook source` header)**

```python
# File: dq_rules_loader.py (NO notebook header!)

from pyspark.sql import SparkSession

# Module-level cache for rules (loaded once at import time)
_rules_cache = {}
_cache_initialized = False

def _load_all_rules() -> None:
    """Load all rules from Delta table into module-level cache."""
    global _rules_cache, _cache_initialized
    
    if _cache_initialized:
        return
    
    spark = SparkSession.getActiveSession()
    if spark is None:
        return
    
    try:
        rules_table = f"{catalog}.{schema}.dq_rules"
        
        # ✅ Use toPandas() instead of .collect() to avoid DLT warning
        pdf = spark.sql(f"SELECT * FROM {rules_table}").toPandas()
        
        # Populate cache
        for _, row in pdf.iterrows():
            cache_key = (row['table_name'], row['severity'])
            if cache_key not in _rules_cache:
                _rules_cache[cache_key] = {}
            _rules_cache[cache_key][row['rule_name']] = row['constraint_sql']
        
        _cache_initialized = True
    except Exception as e:
        print(f"Note: Could not load DQ rules: {e}")

def get_critical_rules_for_table(table_name: str) -> dict:
    """Get critical DQ rules from cache (no Spark operations)."""
    if not _cache_initialized:
        _load_all_rules()
    return _rules_cache.get((table_name, "critical"), {})

def get_warning_rules_for_table(table_name: str) -> dict:
    """Get warning DQ rules from cache (no Spark operations)."""
    if not _cache_initialized:
        _load_all_rules()
    return _rules_cache.get((table_name, "warning"), {})
```

**See:** `references/expectation-patterns.md` for complete loader implementation

### 2. DLT Table Decorators

**CRITICAL Rules (use `@dlt.expect_all_or_drop()`):**
- Primary key fields (must be present and non-empty)
- Foreign key fields (must be present for referential integrity)
- Required date fields (must be present and >= minimum valid date)
- Non-nullable business fields (quantity != 0, price > 0, etc.)

**WARNING Rules (use `@dlt.expect_all()`):**
- Reasonableness checks (quantity between 1 and 10000)
- Recency checks (date within last 90 days)
- Format preferences (UPC length between 12 and 14)
- Coordinate ranges (latitude/longitude within valid bounds)

```python
from dq_rules_loader import (
    get_critical_rules_for_table,
    get_warning_rules_for_table
)

@dlt.table(...)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_transactions"))
@dlt.expect_all(get_warning_rules_for_table("silver_transactions"))
def silver_transactions():
    return dlt.read_stream(get_source_table("bronze_transactions"))
```

### 3. Avoiding `DataFrame.collect()` Warning

**Problem:** DLT shows warning when `.collect()` is used in rules loader

**Solution:** Use module-level cache with `toPandas()`

```python
# ❌ WRONG: Direct .collect() shows warning
def get_rules(table_name: str, severity: str) -> dict:
    df = spark.read.table(rules_table).filter(...).collect()  # Warning!
    return {row['rule_name']: row['constraint_sql'] for row in df}

# ✅ CORRECT: Use toPandas() with module-level cache
_rules_cache = {}
_cache_initialized = False

def _load_all_rules():
    pdf = spark.sql(f"SELECT * FROM {rules_table}").toPandas()  # No warning!
    # Populate cache...

def get_rules(table_name: str, severity: str) -> dict:
    if not _cache_initialized:
        _load_all_rules()
    return _rules_cache.get((table_name, severity), {})  # From cache!
```

**See:** `references/expectation-patterns.md` for complete pattern

## Core Patterns

### Pattern 1: Create DQ Rules Delta Table

```sql
CREATE OR REPLACE TABLE {catalog}.{schema}.dq_rules (
    table_name STRING NOT NULL,
    rule_name STRING NOT NULL,
    constraint_sql STRING NOT NULL,
    severity STRING NOT NULL,
    description STRING,
    created_timestamp TIMESTAMP NOT NULL,
    updated_timestamp TIMESTAMP NOT NULL,
    CONSTRAINT pk_dq_rules PRIMARY KEY (table_name, rule_name) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
```

**See:** `references/expectation-patterns.md` for complete schema and population examples

### Pattern 2: Apply Rules in DLT Tables

```python
import dlt
from dq_rules_loader import (
    get_critical_rules_for_table,
    get_warning_rules_for_table,
    get_quarantine_condition
)

@dlt.table(
    name="silver_transactions",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "layer": "silver"
    },
    cluster_by_auto=True
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_transactions"))
@dlt.expect_all(get_warning_rules_for_table("silver_transactions"))
def silver_transactions():
    """
    Data Quality Rules (loaded from dq_rules Delta table):
    
    CRITICAL (Record DROPPED/QUARANTINED if fails):
    - Transaction ID, store number, UPC must be present
    - Quantity cannot be zero, price must be positive
    
    WARNING (Logged but record passes):
    - Quantity within reasonable range (-20 to 50)
    - Price within reasonable range ($0.01 to $500)
    """
    return (
        dlt.read_stream(get_source_table("bronze_transactions"))
        .withColumn("processed_timestamp", current_timestamp())
    )
```

**See:** `references/expectation-patterns.md` for complete DLT table examples

### Pattern 3: Quarantine Table

```python
@dlt.table(
    name="silver_transactions_quarantine",
    comment="Quarantine table for records that failed CRITICAL data quality checks",
    table_properties={
        "quality": "quarantine",
        "layer": "silver"
    },
    cluster_by_auto=True
)
def silver_transactions_quarantine():
    """Quarantine failed records with rich diagnostic information."""
    from dq_rules_loader import get_quarantine_condition
    
    return (
        dlt.read_stream(get_source_table("bronze_transactions"))
        .filter(get_quarantine_condition("silver_transactions"))
        .withColumn("quarantine_reason",
            when(col("transaction_id").isNull(), "CRITICAL: Missing transaction ID")
            .when(col("store_number").isNull(), "CRITICAL: Missing store number")
            .otherwise("CRITICAL: Multiple validation failures"))
        .withColumn("quarantine_timestamp", current_timestamp())
    )
```

**See:** `references/quarantine-patterns.md` for complete quarantine patterns

### Pattern 4: Runtime Rule Updates

**Update rules without code deployment:**

```sql
-- Update a constraint threshold
UPDATE {catalog}.{schema}.dq_rules
SET constraint_sql = 'quantity_sold BETWEEN -30 AND 75',
    updated_timestamp = CURRENT_TIMESTAMP()
WHERE table_name = 'silver_transactions' 
  AND rule_name = 'reasonable_quantity';

-- Change rule severity
UPDATE {catalog}.{schema}.dq_rules
SET severity = 'warning',
    updated_timestamp = CURRENT_TIMESTAMP()
WHERE table_name = 'silver_transactions' 
  AND rule_name = 'valid_loyalty_id';

-- Add new rule
INSERT INTO {catalog}.{schema}.dq_rules VALUES (
  'silver_transactions',
  'valid_payment_method',
  'payment_method IN (''Cash'', ''Credit'', ''Debit'', ''Mobile'')',
  'warning',
  'Payment method should be one of the valid types',
  CURRENT_TIMESTAMP(),
  CURRENT_TIMESTAMP()
);
```

**After updating:** Next DLT pipeline update will use the new rules automatically!

**See:** `references/expectation-patterns.md` for complete runtime management patterns

## Reference Files

### Expectation Patterns
- **`references/expectation-patterns.md`** - Complete DLT expectations patterns including Delta table setup, rules loader module, DLT table implementation, severity-based management, standard patterns by data type, runtime rule management, and avoiding `.collect()` warnings

### Quarantine Patterns
- **`references/quarantine-patterns.md`** - Quarantine table implementation, condition generation, metadata enrichment, remediation patterns, monitoring queries, and common mistakes

## Templates

### Expectations Configuration Template
- **`assets/templates/expectations-config.yaml`** - Template YAML file with DLT pipeline configuration and example DQ rules SQL. Copy and customize for your pipeline.

## Validation Checklist

### DQ Rules Table Setup
- [ ] Created `dq_rules` table in Silver schema
- [ ] Table has proper schema (table_name, rule_name, constraint_sql, severity, description)
- [ ] PRIMARY KEY defined on (table_name, rule_name)
- [ ] Populated with initial rules for all Silver tables
- [ ] Each rule has clear name and description
- [ ] Severity properly set (critical vs warning)

### Rules Loader Module
- [ ] `dq_rules_loader.py` is pure Python (NO notebook header)
- [ ] Functions defined: `get_critical_rules_for_table()`, `get_warning_rules_for_table()`, `get_quarantine_condition()`
- [ ] Module is importable (test with `from dq_rules_loader import ...`)
- [ ] References correct dq_rules table location
- [ ] Uses module-level cache pattern with `toPandas()` (avoids `.collect()` warning)
- [ ] No direct `.collect()` calls in functions called by DLT decorators

### DLT Notebook Implementation
- [ ] Import statement added: `from dq_rules_loader import get_critical_rules_for_table, get_warning_rules_for_table`
- [ ] Decorator applied: `@dlt.expect_all_or_drop(get_critical_rules_for_table("table_name"))`
- [ ] Decorator applied: `@dlt.expect_all(get_warning_rules_for_table("table_name"))`
- [ ] Table properties include all required metadata
- [ ] `cluster_by_auto=True` is set
- [ ] Helper function `get_source_table()` used for source references

### Deployment Order
- [ ] Deploy and run DQ setup job FIRST (creates dq_rules table)
- [ ] Then deploy DLT pipeline (loads rules from table)
- [ ] Verify pipeline can read dq_rules table
- [ ] Test rule updates take effect on next pipeline run

## Common Mistakes to Avoid

### ❌ Mistake 1: DLT pipeline deployed before dq_rules table exists
**Fix:** Run `silver_dq_setup_job` BEFORE deploying DLT pipeline

### ❌ Mistake 2: Notebook header in loader file
**Fix:** Remove `# Databricks notebook source` line from `dq_rules_loader.py`

### ❌ Mistake 3: Hardcoded rules in notebooks
**Fix:** Load from Delta table using `get_critical_rules_for_table()`

### ❌ Mistake 4: Using expect_or_fail
**Fix:** Use `@dlt.expect_all_or_drop()` for critical rules (pipeline continues)

### ❌ Mistake 5: Incorrect table_name in rules
**Fix:** Use exact Silver table name (with prefix, e.g., `silver_transactions` not `transactions`)

### ❌ Mistake 6: Using `.collect()` directly in rules loader
**Fix:** Use module-level cache with `toPandas()` to avoid DLT warnings

**See:** `references/expectation-patterns.md` for detailed mistake explanations

## References

### Official Databricks Documentation
- [DLT Expectations](https://docs.databricks.com/aws/en/dlt/expectations)
- [DLT Expectation Patterns](https://docs.databricks.com/aws/en/ldp/expectation-patterns)
- [Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations)
- [Data Quality Monitoring](https://docs.databricks.com/aws/en/dlt/observability)

### Related Skills
- `dqx-patterns` - DQX framework patterns (complementary advanced validation)
- `databricks-python-imports` - Pure Python module patterns (critical for rules loader)
- `databricks-table-properties` - Silver table properties patterns

---
name: gold-layer-schema-validation
description: Schema validation patterns for Gold layer development to prevent DDL-script mismatches. Use when creating Gold layer merge scripts to ensure DataFrame columns match target table schemas, validate column mappings before merge operations, and catch schema issues before deployment. Includes DDL-first workflow, schema inspector helpers, pre-merge validation, and column mapping documentation patterns.
metadata:
  author: prashanth subrahmanyam
  version: "1.0"
  domain: gold
  role: worker
  pipeline_stage: 4
  pipeline_stage_name: gold-implementation
  called_by:
    - gold-layer-design
    - gold-layer-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: low
  upstream_sources: []  # Stable schema validation logic
---

# Gold Layer Schema Validation Patterns

## Overview

Gold layer merge scripts must align perfectly with DDL-defined schemas. Mismatches between source DataFrame columns and target table schemas cause 59% of Gold layer bugs. This skill provides validation patterns to catch schema issues before deployment.

**Key Principle:** DDL (setup script) is the **runtime source of truth**, not YAML design specifications.

## When to Use This Skill

Use this skill when:
- Creating Gold layer merge scripts from Silver to Gold
- Ensuring DataFrame columns match target table schemas
- Validating column mappings before merge operations
- Catching schema issues before deployment
- Debugging `UNRESOLVED_COLUMN` errors in merge operations

## Core Problem: Three Sources of Truth

Gold layer development involves three schema definitions:

1. **YAML Design** (`gold_layer_design/yaml/*.yaml`) - Human-readable specifications
2. **DDL Scripts** (`src/gold/setup/*.py`) - CREATE TABLE statements
3. **Merge Scripts** (`src/gold/merge/*.py`) - DataFrame transformations

**Problem:** Manual transcription between these creates mismatches.

### Common Failure Pattern

```python
# YAML Design: user_email
# DDL Script: email (renamed during implementation)
# Merge Script: .select("user_email")  # ❌ Still references old name!
# Runtime Error: [UNRESOLVED_COLUMN]
```

**Root Cause:** DDL was updated, but merge script wasn't.

## Critical Rules

### Rule 1: DDL is Runtime Source of Truth

Always develop merge scripts against **actual created tables**, not YAML designs.

**Workflow:**
```
1. YAML Design (Planning)
   ↓
2. DDL Creation (Reality) ← SOURCE OF TRUTH
   ↓
3. Run Setup Job (Create Tables)
   ↓
4. Validate Schema (Read actual table)
   ↓
5. Write Merge Script (Against actual schema)
   ↓
6. Pre-Deployment Validation (Compare DataFrame vs DDL)
```

### Rule 2: Always Validate Before Merge

Use schema validation helper before every merge operation:

```python
from helpers import validate_merge_schema

# Prepare updates
updates_df = prepare_transformations(silver_df)

# ✅ Validate schema BEFORE merge
validate_merge_schema(
    spark, updates_df, catalog, gold_schema, "dim_user",
    raise_on_mismatch=True  # Fail fast if mismatch
)

# Proceed with merge
delta_gold.merge(updates_df, ...)
```

### Rule 3: Explicit Column Mapping

Never assume Silver column names match Gold DDL. Always use explicit mapping:

```python
# ✅ CORRECT: Explicit mapping
updates_df = (
    silver_df
    .withColumn("store_id", col("store_number"))  # Rename explicitly
    .withColumn("product_id", col("upc_code"))    # Rename explicitly
    .select("store_id", "product_id", ...)  # Only Gold columns
)
```

## Quick Reference

### Schema Validation Helper

```python
validate_merge_schema(
    spark: SparkSession,
    updates_df: DataFrame,
    catalog: str,
    schema: str,
    table_name: str,
    raise_on_mismatch: bool = True
) -> dict
```

Returns validation result with:
- `valid`: Boolean indicating if schemas match
- `missing_in_df`: Columns in DDL but not in DataFrame
- `extra_in_df`: Columns in DataFrame but not in DDL
- `type_mismatches`: Columns with type differences

See `references/validation-patterns.md` for complete implementation with full code examples.

### Pre-Merge Validation Checklist

Before writing any Gold merge script:

**Pre-Development:**
- [ ] Read YAML design to understand intent
- [ ] Run setup job to create actual tables
- [ ] Read DDL schema from actual table (`DESCRIBE table`)
- [ ] Document column mappings (Silver → Gold)
- [ ] Identify any renamed columns

**During Development:**
- [ ] Use explicit `.withColumn()` for all renames
- [ ] Use `.select()` with explicit column list (no `*`)
- [ ] Add comments documenting mappings
- [ ] Cast data types explicitly if DDL differs from source
- [ ] Include all DDL columns in final DataFrame

**Pre-Deployment:**
- [ ] Run schema validation helper
- [ ] Verify no extra columns in DataFrame
- [ ] Verify no missing columns from DDL
- [ ] Verify data types match DDL
- [ ] Test merge with small sample data

## Core Patterns

### Pattern 1: Schema Inspector Helper

Validate DataFrame against target table schema before merge:

```python
# See references/validation-patterns.md for full implementation
from helpers import validate_merge_schema

validate_merge_schema(spark, updates_df, catalog, schema, table_name)
```

**Benefits:**
- ✅ Catches mismatches before Delta merge attempt
- ✅ Clear error messages with exact column differences
- ✅ Prevents cryptic Delta errors
- ✅ Validates data types, not just column names

### Pattern 2: Explicit Column Mapping

Document and implement explicit Silver → Gold column mappings:

```python
def merge_dim_store(spark, catalog, silver_schema, gold_schema):
    """
    Column Mapping (Silver → Gold):
    - store_number → store_number (same)
    - company_rcn → company_retail_control_number (renamed)
    - processed_timestamp → record_updated_timestamp (renamed)
    """
    updates_df = (
        silver_df
        .withColumn("company_retail_control_number", col("company_rcn"))
        .withColumn("record_updated_timestamp", col("processed_timestamp"))
        .select("store_number", "company_retail_control_number", ...)
    )
```

### Pattern 3: DDL Schema Reader

Read actual table schema before writing merge script:

```python
# Step 1: Read actual schema
schema = spark.table(f"{catalog}.{gold_schema}.dim_user").schema
print([field.name for field in schema.fields])  # Verify column names

# Step 2: Write merge script using actual columns
updates_df = df.select("email")  # ✅ Matches DDL, not YAML
```

## Common Mistakes to Avoid

### ❌ Mistake 1: Trusting YAML Over DDL

```python
# ❌ BAD: Using YAML-defined column name
updates_df = df.select("user_email")  # Doesn't match DDL!
```

**Fix:** Always verify against actual DDL:
```python
# ✅ GOOD: Check actual table schema first
schema = spark.table("catalog.schema.dim_user").schema
updates_df = df.select("email")  # ✅ Matches DDL
```

### ❌ Mistake 2: Implicit Column Selection

```python
# ❌ BAD: Selecting with *
updates_df = silver_df.select("*")  # Includes all Silver columns
```

**Fix:** Explicit selection:
```python
# ✅ GOOD: Only select columns that exist in Gold DDL
updates_df = silver_df.select("column1", "column2", "column3")
```

### ❌ Mistake 3: No Pre-Merge Validation

```python
# ❌ BAD: Merge without validation
delta_gold.merge(updates_df, ...)  # Fails at runtime with cryptic error
```

**Fix:** Validate first:
```python
# ✅ GOOD: Validate before merge
validate_merge_schema(spark, updates_df, catalog, schema, table_name)
delta_gold.merge(updates_df, ...)  # Clear error if mismatch
```

## Reference Files

- **`references/validation-patterns.md`** - Complete validation SQL patterns, schema inspector implementation, DDL reader patterns, column mapping documentation patterns, and detailed validation workflows
- **`scripts/validate_schema.py`** - Pre-deployment validation script for comparing all merge DataFrames against DDL schemas

## Scripts

### validate_schema.py

Pre-deployment validation script that compares all merge DataFrames against DDL schemas. Run before `databricks bundle deploy` to catch schema mismatches.

**Usage:**
```bash
python scripts/validate_schema.py \
  prashanth_subrahmanyam_catalog \
  dev_prashanth_subrahmanyam_system_gold
```

See `scripts/validate_schema.py` for complete implementation.

## Related Patterns

- **Fact Table Grain Validation** - See `gold/fact-table-grain-validation` skill
- **Unity Catalog Constraints** - See `common/unity-catalog-constraints` skill
- **Gold Merge Deduplication** - See `gold/gold-delta-merge-deduplication` skill

## References

- [Delta Lake Merge](https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge) - Official documentation
- [Rule Improvement Case Study](../../docs/reference/rule-improvement-gold-layer-debugging.md) - Complete Gold layer debugging methodology

---

**Last Updated:** December 2, 2025  
**Pattern Origin:** 88 bugs across 7 Gold domains, 26% schema mismatch errors  
**Key Lesson:** DDL is runtime truth, not YAML. Always validate DataFrame against actual table schema before merge.  
**Impact:** Prevents 48% of schema-related bugs through pre-merge validation

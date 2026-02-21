# Design-to-Pipeline Bridge

Deterministic techniques for eliminating column name mismatches, data type conflicts, and manual iteration when transitioning from Gold Layer Design (`00-gold-layer-design`) to Gold Layer Pipeline Implementation (`01-gold-layer-setup`).

---

## Problem Statement

Column name mismatches between YAML lineage assumptions and actual Silver table schemas cause repeated iteration during Gold pipeline implementation. The root cause chain:

1. Gold Design reads Bronze schema CSV and assumes Silver column names based on naming conventions (e.g., `bronze_store_dim.company_rcn` → assumes `silver_store_dim.company_rcn`)
2. Silver layer DLT may rename columns (e.g., `company_rcn` → `company_retail_control_number`), add derived columns, or change types
3. Gold pipeline reads YAML lineage `silver_column: company_rcn` and generates `.withColumn()` calls referencing a column that does not exist in Silver
4. Runtime error: `UNRESOLVED_COLUMN` — requires manual iteration to fix

**Solution:** 5 determinism techniques that validate, introspect, and script column resolution instead of generating it.

---

## Technique 1: Silver Schema Introspection Helper

Read actual Silver table columns and types from Unity Catalog at runtime. This replaces assumptions with facts.

```python
def introspect_silver_schema(spark, catalog, silver_schema, meta):
    """Read actual Silver table columns and types for a Gold table's sources.
    
    Args:
        spark: SparkSession
        catalog: Unity Catalog name
        silver_schema: Silver schema name
        meta: Table metadata from load_table_metadata()
    
    Returns:
        {source_table: {"columns": {name: type_str}, "column_set": {name, ...}}}
    """
    silver_schemas = {}
    for source_table in meta["source_tables"]:
        fqn = f"{catalog}.{silver_schema}.{source_table}"
        try:
            fields = spark.table(fqn).schema.fields
            silver_schemas[source_table] = {
                "columns": {f.name: str(f.dataType) for f in fields},
                "column_set": {f.name for f in fields},
            }
        except Exception as e:
            print(f"  WARNING: Cannot read Silver table {fqn}: {e}")
            silver_schemas[source_table] = {
                "columns": {},
                "column_set": set(),
                "error": str(e),
            }
    return silver_schemas
```

**Usage:**
```python
silver_info = introspect_silver_schema(spark, catalog, silver_schema, meta)
print(f"Silver table columns: {silver_info['silver_store_dim']['column_set']}")
```

---

## Technique 2: Pre-Merge Silver Contract Validation

Before writing ANY merge code, validate every `silver_column` referenced in YAML lineage actually exists in the live Silver table. Produces a pass/fail report with specific error messages.

```python
def validate_silver_contract(spark, catalog, silver_schema, meta):
    """Validate all Silver columns in YAML lineage exist in actual Silver tables.
    
    Returns:
        {
            "valid": bool,
            "errors": [str, ...],     # Hard failures (column not found)
            "warnings": [str, ...],   # Soft issues (generated columns, N/A refs)
            "table_name": str
        }
    """
    silver_info = introspect_silver_schema(spark, catalog, silver_schema, meta)
    errors = []
    warnings = []
    
    for gold_col, lineage in meta.get("lineage", {}).items():
        s_table = lineage.get("silver_table", "N/A")
        s_col = lineage.get("silver_column") or lineage.get("source_column", "N/A")
        transformation = lineage.get("transformation", "")
        
        # Skip generated/derived columns (no Silver source)
        if s_table == "N/A" or s_col == "N/A":
            if transformation not in ("GENERATED", "DERIVED_CALCULATION"):
                warnings.append(
                    f"Column '{gold_col}' has N/A silver reference but "
                    f"transformation is '{transformation}' (expected GENERATED or DERIVED_CALCULATION)"
                )
            continue
        
        # Check Silver table exists
        if s_table not in silver_info:
            errors.append(f"Silver table '{s_table}' not found in catalog")
            continue
        
        if silver_info[s_table].get("error"):
            errors.append(f"Silver table '{s_table}' unreadable: {silver_info[s_table]['error']}")
            continue
        
        # Handle multi-column references (e.g., "store_id, processed_timestamp")
        for single_col in [c.strip() for c in s_col.split(",")]:
            if single_col not in silver_info[s_table]["column_set"]:
                errors.append(
                    f"Gold column '{gold_col}': Silver column '{single_col}' "
                    f"not found in {s_table}. "
                    f"Available: {sorted(silver_info[s_table]['column_set'])}"
                )
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "table_name": meta.get("table_name", "unknown"),
    }
```

**Usage:**
```python
result = validate_silver_contract(spark, catalog, silver_schema, meta)
if not result["valid"]:
    print(f"SILVER CONTRACT FAILED for {result['table_name']}:")
    for error in result["errors"]:
        print(f"  ERROR: {error}")
    raise ValueError(f"Silver contract validation failed with {len(result['errors'])} error(s)")
```

---

## Technique 3: Lineage-Driven Column Expression Builder

Instead of the agent generating `.withColumn()` / `.select()` calls by reading YAML lineage and writing code, build column expressions programmatically from YAML lineage at runtime. This eliminates the most common source of column name errors — the agent writes ONE generic function, not per-table column mapping code.

```python
from pyspark.sql.functions import (
    col, lit, md5, concat_ws, when, current_timestamp,
    coalesce, date_trunc
)

def _src_col(lin):
    """Resolve source column name from lineage (silver_column or source_column)."""
    return lin.get("silver_column") or lin.get("source_column", "")

TRANSFORMATION_BUILDERS = {
    "DIRECT_COPY": lambda lin, gold_name, col_type:
        col(_src_col(lin)).alias(gold_name),
    
    "RENAME": lambda lin, gold_name, col_type:
        col(_src_col(lin)).alias(gold_name),
    
    "CAST": lambda lin, gold_name, col_type:
        col(_src_col(lin)).cast(col_type).alias(gold_name),
    
    "GENERATED": lambda lin, gold_name, col_type:
        current_timestamp().alias(gold_name),
    
    "COALESCE": lambda lin, gold_name, col_type:
        coalesce(col(_src_col(lin)), lit(0)).alias(gold_name),
    
    "DATE_TRUNC": lambda lin, gold_name, col_type:
        date_trunc("day", col(_src_col(lin))).cast("date").alias(gold_name),
}


def build_column_expressions(meta, column_defs):
    """Build PySpark column expressions directly from YAML lineage.
    
    Handles ~70% of columns automatically (DIRECT_COPY, RENAME, CAST,
    GENERATED, COALESCE, DATE_TRUNC). Returns:
      - automated_exprs: list of Column objects for .select()
      - manual_cols: list of (gold_name, lineage) for columns requiring
                     hand-coded business logic (AGGREGATE_*, DERIVED_*, HASH_*)
    
    Args:
        meta: Table metadata from load_table_metadata()
        column_defs: Full column definitions list from YAML (with lineage)
    
    Returns:
        (automated_exprs: list[Column], manual_cols: list[tuple])
    """
    automated_exprs = []
    manual_cols = []
    
    for col_def in column_defs:
        gold_name = col_def["name"]
        col_type = col_def.get("type", "STRING")
        lineage = col_def.get("lineage", {})
        transformation = lineage.get("transformation", "")
        
        if transformation in TRANSFORMATION_BUILDERS:
            try:
                expr = TRANSFORMATION_BUILDERS[transformation](lineage, gold_name, col_type)
                automated_exprs.append(expr)
            except Exception as e:
                manual_cols.append((gold_name, lineage, str(e)))
        else:
            manual_cols.append((gold_name, lineage, None))
    
    return automated_exprs, manual_cols


def apply_automated_columns(silver_df, meta, column_defs):
    """Apply automated column expressions and return DataFrame + manual column list.
    
    Usage:
        partial_df, manual_cols = apply_automated_columns(silver_df, meta, column_defs)
        # Then manually add: aggregations, derived calculations, hash keys
        for gold_name, lineage, _ in manual_cols:
            # Hand-code business logic for AGGREGATE_*, DERIVED_*, HASH_*
            pass
    """
    automated_exprs, manual_cols = build_column_expressions(meta, column_defs)
    
    if automated_exprs:
        result_df = silver_df.select(*automated_exprs)
    else:
        result_df = silver_df
    
    if manual_cols:
        print(f"  {meta['table_name']}: {len(automated_exprs)} columns automated, "
              f"{len(manual_cols)} require manual logic:")
        for gold_name, lineage, _ in manual_cols:
            print(f"    - {gold_name} ({lineage.get('transformation', 'UNKNOWN')})")
    
    return result_df, manual_cols
```

**Usage in merge scripts:**
```python
# OLD approach (agent generates per-table, error-prone):
updates_df = (
    silver_df
    .withColumn("company_retail_control_number", col("company_rcn"))
    .withColumn("store_number", col("store_number"))
    .select("store_key", "store_number", "company_retail_control_number", ...)
)

# NEW approach (scripted from YAML, deterministic):
column_defs = yaml_config.get("columns", [])
partial_df, manual_cols = apply_automated_columns(silver_df, meta, column_defs)
# Only hand-code the AGGREGATE_*, DERIVED_*, HASH_* columns
```

---

## Technique 4: Data Type Compatibility Validation

After Silver contract validation, validate that Silver column types are compatible with Gold target types. Catches implicit cast failures before they hit Delta MERGE.

```python
TYPE_COMPATIBILITY = {
    "STRING": {"StringType", "string"},
    "INT": {"IntegerType", "LongType", "ShortType", "int", "long", "short"},
    "BIGINT": {"LongType", "IntegerType", "long", "int"},
    "LONG": {"LongType", "IntegerType", "long", "int"},
    "DOUBLE": {"DoubleType", "FloatType", "double", "float"},
    "FLOAT": {"FloatType", "DoubleType", "float", "double"},
    "DATE": {"DateType", "TimestampType", "date", "timestamp"},
    "TIMESTAMP": {"TimestampType", "timestamp"},
    "BOOLEAN": {"BooleanType", "boolean"},
}


def validate_type_compatibility(meta, silver_info):
    """Check Silver column types are compatible with Gold target types.
    
    Returns:
        {"valid": bool, "mismatches": [{"gold_col": ..., "gold_type": ..., 
         "silver_col": ..., "silver_type": ..., "compatible": bool}]}
    """
    mismatches = []
    
    for gold_col, lineage in meta.get("lineage", {}).items():
        s_table = lineage.get("silver_table", "N/A")
        s_col = lineage.get("silver_column") or lineage.get("source_column", "N/A")
        
        if s_table == "N/A" or s_col == "N/A":
            continue
        if s_table not in silver_info or "," in s_col:
            continue  # Multi-column or missing — skip type check
        
        gold_type = meta["column_types"].get(gold_col, "STRING").upper().split("(")[0]
        silver_type = silver_info[s_table]["columns"].get(s_col, "")
        
        compatible_types = TYPE_COMPATIBILITY.get(gold_type, set())
        is_compatible = any(ct in silver_type for ct in compatible_types) if compatible_types else True
        
        if not is_compatible and silver_type:
            mismatches.append({
                "gold_col": gold_col,
                "gold_type": gold_type,
                "silver_col": s_col,
                "silver_type": silver_type,
                "compatible": False,
            })
    
    return {
        "valid": len(mismatches) == 0,
        "mismatches": mismatches,
    }
```

---

## Technique 5: Column Resolution Report

Generate a human-readable resolution report before any merge runs. Shows exactly what maps where, with PASS/FAIL status per column.

```python
def generate_resolution_report(meta, column_defs, silver_info):
    """Generate column resolution report for a single Gold table.
    
    Prints a formatted table showing Silver→Gold mapping status.
    Returns: {"table_name": str, "total": int, "passed": int, "failed": int}
    """
    table_name = meta["table_name"]
    source_tables = meta["source_tables"]
    
    total_silver_cols = sum(
        len(info["column_set"]) for info in silver_info.values()
        if "error" not in info
    )
    
    print(f"\n{'='*60}")
    print(f"Column Resolution Report: {table_name}")
    print(f"Silver Source(s): {', '.join(source_tables)} ({total_silver_cols} columns)")
    print(f"Gold Target: {table_name} ({len(meta['columns'])} columns)")
    print(f"{'='*60}")
    print(f"| {'Gold Column':<25} | {'Silver Column':<20} | {'Transform':<15} | {'Status':<6} |")
    print(f"|{'-'*27}|{'-'*22}|{'-'*17}|{'-'*8}|")
    
    passed = 0
    failed = 0
    
    for col_def in column_defs:
        gold_name = col_def["name"]
        lineage = col_def.get("lineage", {})
        s_table = lineage.get("silver_table", "N/A")
        s_col = lineage.get("silver_column") or lineage.get("source_column", "N/A")
        transformation = lineage.get("transformation", "N/A")
        
        if s_table == "N/A" or s_col == "N/A":
            status = "SKIP"
            passed += 1
        elif s_table not in silver_info:
            status = "FAIL"
            failed += 1
        else:
            # Check all referenced columns exist
            all_found = True
            for single_col in [c.strip() for c in s_col.split(",")]:
                if single_col not in silver_info.get(s_table, {}).get("column_set", set()):
                    all_found = False
                    break
            status = "PASS" if all_found else "FAIL"
            if all_found:
                passed += 1
            else:
                failed += 1
        
        s_col_display = s_col[:18] + ".." if len(s_col) > 20 else s_col
        print(f"| {gold_name:<25} | {s_col_display:<20} | {transformation:<15} | {status:<6} |")
    
    print(f"\nRESULT: {passed} PASSED, {failed} FAILED")
    if failed > 0:
        print("ACTION: Fix YAML lineage or Silver schema before proceeding")
    
    return {"table_name": table_name, "total": passed + failed, "passed": passed, "failed": failed}
```

---

## Phase 0 Workflow: Upstream Contract Validation

**Executable script:** `scripts/validate_upstream_contracts.py` — standalone Databricks notebook implementing this workflow. Use the script for execution; this section documents the full logic for reference.

This workflow runs BEFORE Phase 1 (table creation) in the Gold Layer Setup orchestrator.

```python
def run_phase0_validation(spark, catalog, silver_schema, yaml_base):
    """Phase 0: Validate all Silver contracts before any pipeline code is written.
    
    Gate: ALL contracts must PASS before proceeding to Phase 1.
    """
    from pathlib import Path
    import yaml
    
    print("=" * 60)
    print("PHASE 0: Silver Contract Validation")
    print("=" * 60)
    
    # Step 1: Load ALL Gold YAML metadata
    inventory = build_inventory(yaml_base)
    print(f"Loaded {len(inventory)} Gold table definitions from YAML")
    
    all_valid = True
    all_reports = []
    
    for table_name, meta in inventory.items():
        # Skip tables with no Silver source (e.g., dim_date = generated)
        if not meta.get("source_tables"):
            print(f"\n  {table_name}: No Silver source (generated table) — SKIP")
            continue
        
        # Step 2: Introspect Silver schema
        silver_info = introspect_silver_schema(spark, catalog, silver_schema, meta)
        
        # Step 3: Validate Silver contract
        contract = validate_silver_contract(spark, catalog, silver_schema, meta)
        if not contract["valid"]:
            all_valid = False
            print(f"\n  {table_name}: SILVER CONTRACT FAILED")
            for error in contract["errors"]:
                print(f"    ERROR: {error}")
        
        # Step 4: Validate type compatibility
        types_result = validate_type_compatibility(meta, silver_info)
        if not types_result["valid"]:
            print(f"\n  {table_name}: TYPE COMPATIBILITY WARNINGS")
            for m in types_result["mismatches"]:
                print(f"    {m['gold_col']}: Gold={m['gold_type']}, Silver={m['silver_type']}")
        
        # Step 5: Generate resolution report
        column_defs = []  # Load full column defs from YAML for report
        yaml_path = find_yaml_for_table(yaml_base, table_name)
        if yaml_path:
            with open(yaml_path) as f:
                config = yaml.safe_load(f)
            column_defs = config.get("columns", [])
        
        report = generate_resolution_report(meta, column_defs, silver_info)
        all_reports.append(report)
    
    # Gate check
    print("\n" + "=" * 60)
    if all_valid:
        print("PHASE 0 GATE: ALL CONTRACTS PASSED — proceed to Phase 1")
    else:
        print("PHASE 0 GATE: CONTRACTS FAILED — fix issues before proceeding")
        print("\nTo fix:")
        print("  1. Update YAML lineage silver_column values to match actual Silver columns")
        print("  2. OR update Silver DLT pipeline to expose expected columns")
        print("  3. Re-run Phase 0 validation")
    print("=" * 60)
    
    return all_valid, all_reports
```

---

## Integration Points

### Gold Layer Design (`00-gold-layer-design`)

During design, the lineage documentation step should attempt Silver cross-referencing if Silver tables already exist:

```python
def cross_reference_silver_at_design_time(spark, catalog, silver_schema, yaml_base):
    """Advisory validation during design (Silver may not exist yet).
    
    Run AFTER Silver layer is deployed, BEFORE Gold pipeline implementation.
    Logs warnings but does not block design completion.
    """
    inventory = build_inventory(yaml_base)
    warnings = []
    
    for table_name, meta in inventory.items():
        if not meta.get("source_tables"):
            continue
        try:
            result = validate_silver_contract(spark, catalog, silver_schema, meta)
            if not result["valid"]:
                warnings.extend(result["errors"])
        except Exception:
            pass  # Silver may not exist yet during design
    
    if warnings:
        print(f"\nDesign-time Silver cross-reference: {len(warnings)} warning(s)")
        for w in warnings:
            print(f"  WARNING: {w}")
        print("These will become hard errors during Phase 0 of pipeline implementation.")
```

### Merge Script Patterns (`merge-script-patterns.md`)

Use `build_column_expressions()` to generate the `.select()` list from YAML lineage:

```python
# Replace per-table .withColumn() chains with:
automated_exprs, manual_cols = build_column_expressions(meta, column_defs)
partial_df = silver_df.select(*automated_exprs)
# Then add manual columns (AGGREGATE_*, DERIVED_*, HASH_*)
```

---

## Common Failure Scenarios and Fixes

| Scenario | Phase 0 Detection | Fix |
|---|---|---|
| Silver renamed `company_rcn` → `company_retail_control_number` | Contract error: "Column 'company_rcn' not found" | Update YAML `silver_column` to match actual Silver name |
| Silver added a derived column not in Bronze | Contract warning: "N/A silver reference for non-generated column" | Add lineage entry pointing to derived Silver column |
| Silver column type changed (STRING → INT) | Type compatibility mismatch | Add explicit `.cast()` in YAML lineage or merge script |
| Silver table renamed | Contract error: "Silver table 'old_name' not found" | Update YAML `silver_table` and `COLUMN_LINEAGE.csv` |
| Multiple Silver tables feed one Gold table | Partial contract pass | Ensure all source tables listed in YAML lineage entries |

# Databricks notebook source

"""
Phase 0: Upstream Contract Validation

Validates that all source column names and types referenced in YAML lineage
actually exist in the deployed upstream (e.g., Silver) tables. Run this BEFORE
any merge code is written to catch column name mismatches early.

Gate: ALL contracts must PASS before proceeding to implementation.

Usage:
  databricks bundle run gold_validate_contracts_job -t dev

  Or run interactively in a Databricks notebook after setting widgets.
"""

import yaml
from pathlib import Path


# =============================================================================
# YAML EXTRACTION HELPERS (shared with merge template)
# =============================================================================

def find_yaml_base() -> Path:
    """Find YAML directory - works in Databricks and locally."""
    possible_paths = [
        Path("../../gold_layer_design/yaml"),
        Path("gold_layer_design/yaml"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    raise FileNotFoundError(
        "YAML directory not found. Ensure YAMLs are synced in databricks.yml"
    )


def load_table_metadata(yaml_path: Path) -> dict:
    """Extract ALL merge-relevant metadata from a single YAML file."""
    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    columns = config.get("columns", [])
    table_props = config.get("table_properties", {})

    source_tables = set()
    lineage_map = {}
    for c in columns:
        lin = c.get("lineage", {})
        if lin:
            lineage_map[c["name"]] = lin
            if lin.get("source_table"):
                source_tables.add(lin["source_table"])

    return {
        "table_name": config["table_name"],
        "columns": [c["name"] for c in columns],
        "column_types": {c["name"]: c["type"] for c in columns},
        "pk_columns": config.get("primary_key", {}).get("columns", []),
        "business_key": config.get("business_key", {}).get("columns", []),
        "foreign_keys": config.get("foreign_keys", []),
        "scd_type": table_props.get("scd_type", ""),
        "grain": table_props.get("grain", ""),
        "entity_type": table_props.get("entity_type", ""),
        "source_tables": list(source_tables),
        "lineage": lineage_map,
        "yaml_path": str(yaml_path),
    }


def build_inventory(yaml_base: Path, domain: str = "all") -> dict:
    """Build complete table inventory from YAML files."""
    inventory = {}
    if domain.lower() == "all":
        domains = [d.name for d in yaml_base.iterdir() if d.is_dir()]
    else:
        domains = [domain]

    for d in domains:
        domain_path = yaml_base / d
        if not domain_path.exists():
            continue
        for yaml_file in sorted(domain_path.glob("*.yaml")):
            meta = load_table_metadata(yaml_file)
            inventory[meta["table_name"]] = meta

    return inventory


def _resolve_source_col(lineage: dict) -> str:
    """Resolve source column name from lineage (silver_column or source_column)."""
    return lineage.get("silver_column") or lineage.get("source_column", "N/A")


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def introspect_source_schema(spark, catalog, source_schema, meta):
    """Read actual source table columns and types from Unity Catalog.

    Returns:
        {source_table: {"columns": {name: type_str}, "column_set": {name, ...}}}
    """
    source_schemas = {}
    for source_table in meta["source_tables"]:
        fqn = f"{catalog}.{source_schema}.{source_table}"
        try:
            fields = spark.table(fqn).schema.fields
            source_schemas[source_table] = {
                "columns": {f.name: str(f.dataType) for f in fields},
                "column_set": {f.name for f in fields},
            }
        except Exception as e:
            print(f"  WARNING: Cannot read source table {fqn}: {e}")
            source_schemas[source_table] = {
                "columns": {},
                "column_set": set(),
                "error": str(e),
            }
    return source_schemas


def validate_source_contract(spark, catalog, source_schema, meta):
    """Validate all source columns in YAML lineage exist in actual source tables.

    Returns:
        {
            "valid": bool,
            "errors": [str, ...],
            "warnings": [str, ...],
            "table_name": str
        }
    """
    source_info = introspect_source_schema(spark, catalog, source_schema, meta)
    errors = []
    warnings = []

    for gold_col, lineage in meta.get("lineage", {}).items():
        s_table = lineage.get("silver_table") or lineage.get("source_table", "N/A")
        s_col = _resolve_source_col(lineage)
        transformation = lineage.get("transformation", "")

        if s_table == "N/A" or s_col == "N/A":
            if transformation not in ("GENERATED", "DERIVED_CALCULATION"):
                warnings.append(
                    f"Column '{gold_col}' has N/A source reference but "
                    f"transformation is '{transformation}' (expected GENERATED or DERIVED_CALCULATION)"
                )
            continue

        if s_table not in source_info:
            errors.append(f"Source table '{s_table}' not found in catalog")
            continue

        if source_info[s_table].get("error"):
            errors.append(f"Source table '{s_table}' unreadable: {source_info[s_table]['error']}")
            continue

        for single_col in [c.strip() for c in s_col.split(",")]:
            if single_col not in source_info[s_table]["column_set"]:
                errors.append(
                    f"Gold column '{gold_col}': source column '{single_col}' "
                    f"not found in {s_table}. "
                    f"Available: {sorted(source_info[s_table]['column_set'])}"
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "table_name": meta.get("table_name", "unknown"),
    }


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


def validate_type_compatibility(meta, source_info):
    """Check source column types are compatible with Gold target types."""
    mismatches = []

    for gold_col, lineage in meta.get("lineage", {}).items():
        s_table = lineage.get("silver_table") or lineage.get("source_table", "N/A")
        s_col = _resolve_source_col(lineage)

        if s_table == "N/A" or s_col == "N/A":
            continue
        if s_table not in source_info or "," in s_col:
            continue

        gold_type = meta["column_types"].get(gold_col, "STRING").upper().split("(")[0]
        silver_type = source_info[s_table]["columns"].get(s_col, "")

        compatible_types = TYPE_COMPATIBILITY.get(gold_type, set())
        is_compatible = any(ct in silver_type for ct in compatible_types) if compatible_types else True

        if not is_compatible and silver_type:
            mismatches.append({
                "gold_col": gold_col,
                "gold_type": gold_type,
                "source_col": s_col,
                "source_type": silver_type,
                "compatible": False,
            })

    return {
        "valid": len(mismatches) == 0,
        "mismatches": mismatches,
    }


def generate_resolution_report(meta, column_defs, source_info):
    """Generate column resolution report for a single Gold table."""
    table_name = meta["table_name"]
    source_tables = meta["source_tables"]

    total_source_cols = sum(
        len(info["column_set"]) for info in source_info.values()
        if "error" not in info
    )

    print(f"\n{'='*60}")
    print(f"Column Resolution Report: {table_name}")
    print(f"Source(s): {', '.join(source_tables)} ({total_source_cols} columns)")
    print(f"Gold Target: {table_name} ({len(meta['columns'])} columns)")
    print(f"{'='*60}")
    print(f"| {'Gold Column':<25} | {'Source Column':<20} | {'Transform':<15} | {'Status':<6} |")
    print(f"|{'-'*27}|{'-'*22}|{'-'*17}|{'-'*8}|")

    passed = 0
    failed = 0

    for col_def in column_defs:
        gold_name = col_def["name"]
        lineage = col_def.get("lineage", {})
        s_table = lineage.get("silver_table") or lineage.get("source_table", "N/A")
        s_col = _resolve_source_col(lineage)
        transformation = lineage.get("transformation", "N/A")

        if s_table == "N/A" or s_col == "N/A":
            status = "SKIP"
            passed += 1
        elif s_table not in source_info:
            status = "FAIL"
            failed += 1
        else:
            all_found = True
            for single_col in [c.strip() for c in s_col.split(",")]:
                if single_col not in source_info.get(s_table, {}).get("column_set", set()):
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
        print("ACTION: Fix YAML lineage or source schema before proceeding")

    return {"table_name": table_name, "total": passed + failed, "passed": passed, "failed": failed}


def find_yaml_for_table(yaml_base, table_name):
    """Locate the YAML file for a given table name."""
    for domain_dir in yaml_base.iterdir():
        if not domain_dir.is_dir():
            continue
        for yaml_file in domain_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
            if config.get("table_name") == table_name:
                return yaml_file
    return None


# =============================================================================
# PHASE 0 WORKFLOW
# =============================================================================

def run_phase0_validation(spark, catalog, source_schema, yaml_base):
    """Phase 0: Validate all upstream contracts before any pipeline code is written.

    Gate: ALL contracts must PASS before proceeding to Phase 1.

    Returns:
        (all_valid: bool, all_reports: list[dict])
    """
    print("=" * 60)
    print("PHASE 0: Upstream Contract Validation")
    print(f"Catalog: {catalog}")
    print(f"Source Schema: {source_schema}")
    print("=" * 60)

    inventory = build_inventory(yaml_base)
    print(f"Loaded {len(inventory)} Gold table definitions from YAML")

    all_valid = True
    all_reports = []

    for table_name, meta in inventory.items():
        if not meta.get("source_tables"):
            print(f"\n  {table_name}: No source tables (generated table) — SKIP")
            continue

        source_info = introspect_source_schema(spark, catalog, source_schema, meta)

        contract = validate_source_contract(spark, catalog, source_schema, meta)
        if not contract["valid"]:
            all_valid = False
            print(f"\n  {table_name}: CONTRACT FAILED")
            for error in contract["errors"]:
                print(f"    ERROR: {error}")

        types_result = validate_type_compatibility(meta, source_info)
        if not types_result["valid"]:
            print(f"\n  {table_name}: TYPE COMPATIBILITY WARNINGS")
            for m in types_result["mismatches"]:
                print(f"    {m['gold_col']}: Gold={m['gold_type']}, Source={m['source_type']}")

        column_defs = []
        yaml_path = find_yaml_for_table(yaml_base, table_name)
        if yaml_path:
            with open(yaml_path) as f:
                config = yaml.safe_load(f)
            column_defs = config.get("columns", [])

        report = generate_resolution_report(meta, column_defs, source_info)
        all_reports.append(report)

    print("\n" + "=" * 60)
    if all_valid:
        print("PHASE 0 GATE: ALL CONTRACTS PASSED — proceed to Phase 1")
    else:
        print("PHASE 0 GATE: CONTRACTS FAILED — fix issues before proceeding")
        print("\nTo fix:")
        print("  1. Update YAML lineage silver_column values to match actual source columns")
        print("  2. OR update upstream pipeline to expose the expected columns")
        print("  3. Re-run this validation script")
    print("=" * 60)

    return all_valid, all_reports


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    source_schema = dbutils.widgets.get("source_schema")

    print(f"Catalog: {catalog}")
    print(f"Source Schema: {source_schema}")

    return catalog, source_schema


def main():
    """Run Phase 0 upstream contract validation."""
    from pyspark.sql import SparkSession

    catalog, source_schema = get_parameters()
    spark = SparkSession.builder.appName("Phase 0 Contract Validation").getOrCreate()

    try:
        yaml_base = find_yaml_base()
        all_valid, reports = run_phase0_validation(spark, catalog, source_schema, yaml_base)

        if not all_valid:
            raise ValueError(
                "Upstream contract validation FAILED. "
                "Fix YAML lineage and re-run before proceeding to implementation."
            )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

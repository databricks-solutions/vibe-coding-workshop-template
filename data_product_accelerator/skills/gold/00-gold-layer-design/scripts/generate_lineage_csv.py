"""
Generate COLUMN_LINEAGE.csv and COLUMN_LINEAGE.md from Gold layer YAML schema files.

Usage:
    python generate_lineage_csv.py --yaml-dir gold_layer_design/yaml --output-dir gold_layer_design

This script reads all YAML files in the specified directory (recursively through
domain subdirectories) and generates:
  1. COLUMN_LINEAGE.csv - Machine-readable column lineage
  2. COLUMN_LINEAGE.md - Human-readable lineage documentation

It also validates consistency between YAML files and the generated CSV.
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


def find_yaml_files(yaml_dir: str) -> list:
    """Find all YAML files recursively in domain subdirectories."""
    yaml_path = Path(yaml_dir)
    if not yaml_path.exists():
        print(f"ERROR: YAML directory not found: {yaml_dir}")
        sys.exit(1)
    
    yaml_files = sorted(yaml_path.rglob("*.yaml"))
    # Exclude README.md and non-schema files
    yaml_files = [f for f in yaml_files if f.name != "README.md"]
    
    print(f"Found {len(yaml_files)} YAML schema files")
    return yaml_files


def load_yaml(path: Path) -> dict:
    """Load and parse a single YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_lineage_rows(config: dict, domain_from_path: str) -> list:
    """Extract lineage rows from a YAML schema config."""
    rows = []
    table_name = config.get("table_name", "UNKNOWN")
    domain = config.get("domain", domain_from_path)
    
    for col in config.get("columns", []):
        lineage = col.get("lineage", {})
        
        row = {
            "domain": domain,
            "gold_table": table_name,
            "gold_column": col.get("name", "UNKNOWN"),
            "data_type": col.get("type", "UNKNOWN"),
            "nullable": str(col.get("nullable", True)).lower(),
            "bronze_table": lineage.get("bronze_table", "N/A"),
            "bronze_column": lineage.get("bronze_column", "N/A"),
            "silver_table": lineage.get("silver_table", "N/A"),
            "silver_column": lineage.get("silver_column", "N/A"),
            "transformation_type": lineage.get("transformation", "UNKNOWN"),
            "transformation_logic": lineage.get("transformation_logic", "Not documented"),
        }
        rows.append(row)
    
    return rows


def generate_csv(rows: list, output_file: str) -> None:
    """Write lineage rows to CSV file."""
    fieldnames = [
        "domain", "gold_table", "gold_column", "data_type", "nullable",
        "bronze_table", "bronze_column", "silver_table", "silver_column",
        "transformation_type", "transformation_logic",
    ]
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  Generated: {output_file} ({len(rows)} columns)")


def generate_markdown(rows: list, yaml_configs: list, output_file: str) -> None:
    """Write human-readable lineage markdown document."""
    lines = []
    lines.append("# Column-Level Lineage: Bronze -> Silver -> Gold\n")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append("---\n\n")
    
    # Group rows by table
    tables = {}
    for row in rows:
        table = row["gold_table"]
        if table not in tables:
            tables[table] = []
        tables[table].append(row)
    
    # Find configs for grain info
    config_by_table = {}
    for config in yaml_configs:
        config_by_table[config.get("table_name", "")] = config
    
    for table_name, cols in sorted(tables.items()):
        config = config_by_table.get(table_name, {})
        grain = config.get("grain", "Not specified")
        domain = config.get("domain", "N/A")
        
        lines.append(f"## Table: {table_name}\n\n")
        lines.append(f"**Grain:** {grain}  \n")
        lines.append(f"**Domain:** {domain}\n\n")
        
        # Column lineage table
        lines.append("| Gold Column | Type | Bronze Source | Silver Source | Transformation | Logic |\n")
        lines.append("|---|---|---|---|---|---|\n")
        
        for col in cols:
            bronze_src = f"{col['bronze_table']}.{col['bronze_column']}"
            silver_src = f"{col['silver_table']}.{col['silver_column']}"
            logic = col["transformation_logic"].replace("|", "\\|")
            lines.append(
                f"| {col['gold_column']} | {col['data_type']} "
                f"| {bronze_src} | {silver_src} "
                f"| {col['transformation_type']} | `{logic}` |\n"
            )
        
        lines.append("\n---\n\n")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    
    print(f"  Generated: {output_file} ({len(tables)} tables)")


def validate_consistency(yaml_configs: list, rows: list) -> list:
    """Validate that all YAML columns appear in CSV rows."""
    errors = []
    
    # Collect all columns from YAML
    yaml_columns = set()
    for config in yaml_configs:
        table = config.get("table_name", "")
        for col in config.get("columns", []):
            yaml_columns.add((table, col.get("name", "")))
    
    # Collect all columns from CSV rows
    csv_columns = set()
    for row in rows:
        csv_columns.add((row["gold_table"], row["gold_column"]))
    
    # Find mismatches
    in_yaml_not_csv = yaml_columns - csv_columns
    in_csv_not_yaml = csv_columns - yaml_columns
    
    if in_yaml_not_csv:
        errors.append(f"Columns in YAML but not in CSV: {sorted(in_yaml_not_csv)}")
    if in_csv_not_yaml:
        errors.append(f"Columns in CSV but not in YAML: {sorted(in_csv_not_yaml)}")
    
    # Check for missing lineage
    for row in rows:
        if row["transformation_type"] == "UNKNOWN":
            errors.append(
                f"Missing lineage for {row['gold_table']}.{row['gold_column']}"
            )
    
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Generate COLUMN_LINEAGE.csv and COLUMN_LINEAGE.md from YAML schemas"
    )
    parser.add_argument(
        "--yaml-dir",
        required=True,
        help="Path to YAML schema directory (e.g., gold_layer_design/yaml)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Path to output directory (e.g., gold_layer_design)",
    )
    args = parser.parse_args()
    
    print(f"Generating lineage from: {args.yaml_dir}")
    print(f"Output directory: {args.output_dir}")
    print()
    
    # Find and load all YAML files
    yaml_files = find_yaml_files(args.yaml_dir)
    
    all_rows = []
    all_configs = []
    
    for yaml_file in yaml_files:
        config = load_yaml(yaml_file)
        if config is None:
            print(f"  WARNING: Empty YAML file: {yaml_file}")
            continue
        
        all_configs.append(config)
        
        # Infer domain from directory name
        domain_from_path = yaml_file.parent.name
        
        rows = extract_lineage_rows(config, domain_from_path)
        all_rows.extend(rows)
        
        table = config.get("table_name", yaml_file.stem)
        print(f"  Processed: {table} ({len(rows)} columns)")
    
    print()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate CSV
    csv_path = os.path.join(args.output_dir, "COLUMN_LINEAGE.csv")
    generate_csv(all_rows, csv_path)
    
    # Generate Markdown
    md_path = os.path.join(args.output_dir, "COLUMN_LINEAGE.md")
    generate_markdown(all_rows, all_configs, md_path)
    
    # Validate consistency
    print()
    errors = validate_consistency(all_configs, all_rows)
    
    if errors:
        print("VALIDATION WARNINGS:")
        for error in errors:
            print(f"  WARNING: {error}")
    else:
        print("VALIDATION: All columns consistent between YAML and CSV")
    
    print()
    print(f"SUMMARY: {len(all_configs)} tables, {len(all_rows)} columns processed")
    print("Done.")


if __name__ == "__main__":
    main()

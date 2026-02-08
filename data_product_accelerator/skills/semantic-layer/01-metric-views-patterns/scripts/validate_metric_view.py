#!/usr/bin/env python3
"""
Validate Metric View YAML for schema compliance before deployment.

Usage:
    python scripts/validate_metric_view.py \
        --yaml-file src/semantic/metric_views/revenue_analytics_metrics.yaml \
        --gold-yaml-dir gold_layer_design/yaml
"""

import argparse
import sys
import yaml
from pathlib import Path
import re


def find_table_yaml(gold_yaml_dir: Path, table_name: str) -> Path:
    """Find YAML file for a table by searching all domain directories."""
    for domain_dir in gold_yaml_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        yaml_file = domain_dir / f"{table_name}.yaml"
        if yaml_file.exists():
            return yaml_file
    raise FileNotFoundError(f"Table YAML not found: {table_name}")


def get_yaml_columns(yaml_file: Path) -> set:
    """Extract column names from Gold layer YAML definition."""
    with open(yaml_file) as f:
        table_def = yaml.safe_load(f)
    return {col['name'] for col in table_def.get('columns', [])}


def extract_source_columns(expr: str) -> list:
    """Extract column names from expressions like SUM(source.column)."""
    # Pattern: source.column_name or source.column_name)
    pattern = r'source\.(\w+)'
    return re.findall(pattern, expr)


def validate_columns(yaml_file: Path, gold_layer_yaml_dir: Path) -> list:
    """
    Validate all column references in metric view YAML exist in source tables.
    
    Returns: List of errors (empty if valid)
    """
    with open(yaml_file) as f:
        metric_view = yaml.safe_load(f)
    
    errors = []
    
    # 1. Get source table columns
    source_table_path = metric_view.get('source', '')
    if not source_table_path:
        errors.append("❌ Missing 'source' field in metric view YAML")
        return errors
    
    source_table = source_table_path.split('.')[-1]
    try:
        source_yaml = find_table_yaml(gold_layer_yaml_dir, source_table)
        source_columns = get_yaml_columns(source_yaml)
    except FileNotFoundError as e:
        errors.append(f"❌ {e}")
        return errors
    
    # 2. Validate dimension columns
    for dim in metric_view.get('dimensions', []):
        expr = dim.get('expr', '')
        if 'source.' in expr:
            cols = extract_source_columns(expr)
            for col in cols:
                if col not in source_columns:
                    errors.append(
                        f"❌ Dimension '{dim.get('name', 'unknown')}': "
                        f"Column '{col}' not in {source_table}"
                    )
    
    # 3. Validate measure columns
    for measure in metric_view.get('measures', []):
        expr = measure.get('expr', '')
        if 'source.' in expr:
            cols = extract_source_columns(expr)
            for col in cols:
                if col not in source_columns:
                    errors.append(
                        f"❌ Measure '{measure.get('name', 'unknown')}': "
                        f"Column '{col}' not in {source_table}"
                    )
    
    # 4. Validate joined table columns
    for join in metric_view.get('joins', []):
        join_name = join.get('name', '')
        joined_table_path = join.get('source', '')
        if not joined_table_path:
            errors.append(f"❌ Join '{join_name}': Missing 'source' field")
            continue
        
        joined_table = joined_table_path.split('.')[-1]
        try:
            joined_yaml = find_table_yaml(gold_layer_yaml_dir, joined_table)
            joined_columns = get_yaml_columns(joined_yaml)
        except FileNotFoundError as e:
            errors.append(f"❌ Join '{join_name}': {e}")
            continue
        
        # Validate ON clause references
        on_clause = join.get('on', '')
        # Extract column references from ON clause
        # Pattern: source.column or join_name.column
        on_pattern = r'(?:source|' + re.escape(join_name) + r')\.(\w+)'
        on_cols = re.findall(on_pattern, on_clause)
        
        for col in on_cols:
            if col.startswith('source.'):
                col_name = col.replace('source.', '')
                if col_name not in source_columns:
                    errors.append(
                        f"❌ Join '{join_name}' ON clause: "
                        f"Column '{col_name}' not in source table {source_table}"
                    )
            elif col.startswith(join_name + '.'):
                col_name = col.replace(join_name + '.', '')
                if col_name not in joined_columns:
                    errors.append(
                        f"❌ Join '{join_name}' ON clause: "
                        f"Column '{col_name}' not in joined table {joined_table}"
                    )
    
    return errors


def main():
    parser = argparse.ArgumentParser(
        description='Validate Metric View YAML for schema compliance'
    )
    parser.add_argument(
        '--yaml-file',
        type=Path,
        required=True,
        help='Path to metric view YAML file'
    )
    parser.add_argument(
        '--gold-yaml-dir',
        type=Path,
        required=True,
        help='Path to Gold layer YAML directory'
    )
    
    args = parser.parse_args()
    
    if not args.yaml_file.exists():
        print(f"❌ Error: YAML file not found: {args.yaml_file}")
        sys.exit(1)
    
    if not args.gold_yaml_dir.exists():
        print(f"❌ Error: Gold YAML directory not found: {args.gold_yaml_dir}")
        sys.exit(1)
    
    errors = validate_columns(args.yaml_file, args.gold_yaml_dir)
    
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    else:
        print(f"✅ All columns validated successfully for {args.yaml_file.name}")


if __name__ == '__main__':
    main()

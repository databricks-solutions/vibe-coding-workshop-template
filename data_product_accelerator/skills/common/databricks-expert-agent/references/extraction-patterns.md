# Extraction Pattern Examples

This document provides detailed code examples for extracting table names, column names, types, and other metadata from source files. These patterns prevent hallucinations and ensure 100% accuracy by using actual schemas as the source of truth.

## Example 1: Extract Table Names from Gold Layer YAML

```python
import yaml
from pathlib import Path

def get_gold_table_names(domain: str) -> list[str]:
    """
    Extract all table names for a domain from Gold layer YAML.
    
    Args:
        domain: Domain name (e.g., 'billing', 'revenue', 'usage')
        
    Returns:
        Sorted list of table names
    """
    yaml_dir = Path("gold_layer_design/yaml") / domain
    table_names = []
    
    for yaml_file in yaml_dir.glob("*.yaml"):
        with open(yaml_file) as f:
            schema = yaml.safe_load(f)
            table_names.append(schema['table_name'])
    
    return sorted(table_names)

# ✅ CORRECT: Use actual table names
table_names = get_gold_table_names("billing")
print(table_names)  # ['dim_sku', 'dim_workspace', 'fact_usage']

# ❌ WRONG: Generate/guess table names
table_names = ["dim_sku", "dim_workspace", "fact_usage"]  # Might be wrong!
```

## Example 2: Extract Column Names and Types

```python
def get_table_schema(domain: str, table_name: str) -> dict:
    """
    Extract complete schema for a table.
    
    Args:
        domain: Domain name
        table_name: Table name (without catalog.schema prefix)
        
    Returns:
        Dictionary with table_name, columns, primary_key, foreign_keys
    """
    yaml_file = Path(f"gold_layer_design/yaml/{domain}/{table_name}.yaml")
    
    with open(yaml_file) as f:
        schema = yaml.safe_load(f)
    
    columns = {
        col['name']: {
            'type': col['type'],
            'nullable': col.get('nullable', True),
            'comment': col.get('comment', '')
        }
        for col in schema['columns']
    }
    
    return {
        'table_name': schema['table_name'],
        'columns': columns,
        'primary_key': schema.get('primary_key', []),
        'foreign_keys': schema.get('foreign_keys', [])
    }

# ✅ CORRECT: Extract actual schema
schema = get_table_schema("billing", "fact_usage")
columns = list(schema['columns'].keys())
print(columns)  # Actual column names from YAML

# ❌ WRONG: Hardcode column names
columns = ["usage_date", "workspace_id", "sku", "dbus_used"]  # Might be incomplete/wrong!
```

## Example 3: Extract Metric View Names

```python
def get_metric_view_names() -> list[str]:
    """
    Extract all metric view names from YAML files.
    
    Returns:
        Sorted list of metric view names (filenames without .yaml)
    """
    metric_view_dir = Path("src/semantic/metric_views")
    
    # ✅ CORRECT: Use actual filenames
    return sorted([
        f.stem  # filename without .yaml extension
        for f in metric_view_dir.glob("*.yaml")
    ])

# Usage
metric_views = get_metric_view_names()
print(metric_views)  # ['cost_analytics_metrics', 'job_performance_metrics', ...]

# ❌ WRONG: Hardcode metric view names
metric_views = ["cost_metrics", "job_metrics"]  # Might not match actual files!
```

## Example 4: Extract TVF Names and Signatures

```python
import re

def get_tvf_signatures(sql_file: Path) -> list[dict]:
    """
    Extract TVF names and parameters from SQL file.
    
    Args:
        sql_file: Path to SQL file containing TVF definitions
        
    Returns:
        List of dictionaries with name, parameters, and file
    """
    content = sql_file.read_text()
    
    # Pattern: CREATE OR REPLACE FUNCTION name(params)
    pattern = r'CREATE OR REPLACE FUNCTION\s+(\w+)\s*\((.*?)\)'
    
    functions = []
    for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
        func_name = match.group(1)
        params_str = match.group(2)
        
        # Parse parameters
        params = []
        if params_str.strip():
            for param in params_str.split(','):
                param = param.strip()
                if param:
                    parts = param.split()
                    param_name = parts[0]
                    param_type = ' '.join(parts[1:])
                    params.append({'name': param_name, 'type': param_type})
        
        functions.append({
            'name': func_name,
            'parameters': params,
            'file': sql_file.name
        })
    
    return functions

# ✅ CORRECT: Extract actual function signatures
tvfs = get_tvf_signatures(Path("src/semantic/tvfs/cost_functions.sql"))
print(tvfs)  # Actual TVF names and parameters

# ❌ WRONG: Guess function signatures
def get_daily_cost_summary(start_date: str, end_date: str):  # Params might be wrong!
    pass
```

## Example 5: Build Column Mapping from Silver to Gold

```python
def build_column_mapping(silver_table: str, gold_table: str, domain: str) -> dict:
    """
    Build Silver → Gold column mapping from actual schemas.
    
    Args:
        silver_table: Silver table name
        gold_table: Gold table name
        domain: Domain name
        
    Returns:
        Dictionary with mapping, unmapped_silver, unmapped_gold
    """
    # Extract Silver schema (from DLT code or DESCRIBE TABLE)
    silver_df = spark.table(f"catalog.silver_schema.{silver_table}")
    silver_columns = set(silver_df.columns)
    
    # Extract Gold schema from YAML
    gold_yaml = Path(f"gold_layer_design/yaml/{domain}/{gold_table}.yaml")
    with open(gold_yaml) as f:
        gold_schema = yaml.safe_load(f)
    gold_columns = {col['name'] for col in gold_schema['columns']}
    
    # Build mapping
    mapping = {}
    
    # Direct matches (column exists in both with same name)
    direct_matches = silver_columns & gold_columns
    for col in direct_matches:
        mapping[col] = col
    
    # Document unmapped columns
    unmapped_silver = silver_columns - gold_columns
    unmapped_gold = gold_columns - silver_columns
    
    return {
        'mapping': mapping,
        'unmapped_silver': unmapped_silver,
        'unmapped_gold': unmapped_gold
    }

# ✅ CORRECT: Build mapping from actual schemas
mapping = build_column_mapping("silver_usage", "fact_usage", "billing")

# Apply mapping in merge
updates_df = silver_df.select([
    col(silver_col).alias(gold_col)
    for silver_col, gold_col in mapping['mapping'].items()
])

# ❌ WRONG: Hardcode column mappings (might be incomplete/wrong)
updates_df = silver_df.select(
    col("date").alias("usage_date"),  # What if Silver has "usage_date" directly?
    col("ws_id").alias("workspace_id")  # What if Silver uses "workspace_key"?
)
```

## Mandatory Workflows

### Workflow 1: Creating Metric Views

```python
def create_metric_view_from_yaml(catalog: str, schema: str, yaml_file: Path):
    """
    Create metric view using extracted metadata from YAML.
    
    Args:
        catalog: Unity Catalog catalog name
        schema: Schema name
        yaml_file: Path to metric view YAML file
    """
    # ✅ Extract view name from filename (don't generate)
    view_name = yaml_file.stem
    
    # ✅ Parse YAML for structure
    with open(yaml_file) as f:
        metric_view = yaml.safe_load(f)
    
    # ✅ Extract source table from YAML
    source_table = metric_view['source']
    
    # ✅ Verify source table exists
    source_schema = get_table_schema_from_gold_yaml(source_table)
    
    # ✅ Validate all dimension columns exist in source
    for dim in metric_view.get('dimensions', []):
        col_ref = dim['expr']
        validate_column_exists(col_ref, source_schema)
    
    # ✅ Validate all measure columns exist in source
    for measure in metric_view.get('measures', []):
        col_refs = extract_columns_from_expr(measure['expr'])
        for col_ref in col_refs:
            validate_column_exists(col_ref, source_schema)
    
    # Now create the view
    spark.sql(f"""
        CREATE VIEW {catalog}.{schema}.{view_name}
        WITH METRICS
        LANGUAGE YAML
        AS $$
        {yaml.dump(metric_view)}
        $$
    """)
```

### Workflow 2: Creating Gold Tables from YAML

```python
def create_gold_table_from_yaml(catalog: str, schema: str, yaml_file: Path):
    """
    Create Gold table using schema extracted from YAML.
    
    Args:
        catalog: Unity Catalog catalog name
        schema: Schema name
        yaml_file: Path to Gold table YAML definition
    """
    # ✅ Extract table definition from YAML (single source of truth)
    with open(yaml_file) as f:
        table_def = yaml.safe_load(f)
    
    table_name = table_def['table_name']
    columns = table_def['columns']
    primary_key = table_def.get('primary_key', [])
    foreign_keys = table_def.get('foreign_keys', [])
    
    # ✅ Build DDL from extracted schema
    column_defs = []
    for col in columns:
        nullable = "" if col.get('nullable', True) else "NOT NULL"
        comment = f"COMMENT '{col.get('comment', '')}'" if col.get('comment') else ""
        column_defs.append(f"{col['name']} {col['type']} {nullable} {comment}")
    
    columns_sql = ",\n  ".join(column_defs)
    
    # ✅ Build constraints from extracted schema
    constraints = []
    if primary_key:
        pk_cols = ", ".join(primary_key)
        constraints.append(f"CONSTRAINT pk_{table_name} PRIMARY KEY ({pk_cols}) NOT ENFORCED")
    
    for fk in foreign_keys:
        fk_name = f"fk_{table_name}_{fk['references'].split('.')[-1]}"
        constraints.append(
            f"CONSTRAINT {fk_name} FOREIGN KEY ({', '.join(fk['columns'])}) "
            f"REFERENCES {fk['references']}({', '.join(fk['ref_columns'])}) NOT ENFORCED"
        )
    
    constraints_sql = ",\n  ".join(constraints) if constraints else ""
    
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table_name} (
      {columns_sql}
      {', ' + constraints_sql if constraints_sql else ''}
    )
    USING DELTA
    CLUSTER BY AUTO
    COMMENT '{table_def.get('comment', '')}';
    """
    
    spark.sql(ddl)
```

## Emergency Pattern: When Source Files Don't Exist Yet

If Gold YAML doesn't exist yet (initial design phase):

1. **Create the YAML first** - Use YAML as single source of truth
2. **Generate code from YAML** - Don't hardcode in Python/SQL
3. **Validate YAML completeness** - Run schema validation scripts
4. **Update cursor rules** - Document the YAML location

**Never:** Write Python/SQL code with hardcoded names, then create YAML later.

## Quick Reference: Common Extraction Patterns

| Task | Source of Truth | Extraction Code |
|---|---|---|
| **Get table names** | `gold_layer_design/yaml/{domain}/*.yaml` | `[yaml.safe_load(f)['table_name'] for f in Path(...).glob('*.yaml')]` |
| **Get column names** | `gold_layer_design/yaml/{domain}/{table}.yaml` | `[col['name'] for col in schema['columns']]` |
| **Get column types** | `gold_layer_design/yaml/{domain}/{table}.yaml` | `{col['name']: col['type'] for col in schema['columns']}` |
| **Get primary key** | `gold_layer_design/yaml/{domain}/{table}.yaml` | `schema.get('primary_key', [])` |
| **Get foreign keys** | `gold_layer_design/yaml/{domain}/{table}.yaml` | `schema.get('foreign_keys', [])` |
| **Get Silver columns** | `DESCRIBE TABLE` or `df.columns` | `spark.table(silver_table).columns` |
| **Get metric view name** | Filename | `Path(yaml_file).stem` |
| **Get TVF name** | SQL file | `re.search(r'CREATE.*FUNCTION\s+(\w+)', sql).group(1)` |
| **Validate column exists** | Silver metadata | `col_name in spark.table(table).columns` |

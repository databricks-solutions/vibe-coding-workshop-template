# Schema Intake Patterns

Python implementations for Phase 0: Source Schema Intake. These functions parse the customer's schema CSV into a structured inventory that drives all subsequent design decisions.

## parse_schema_csv

Reads the customer schema CSV into a structured dict keyed by table name, with columns, types, nullability, and comments per table.

```python
import csv
from pathlib import Path
from collections import defaultdict

def parse_schema_csv(csv_path: Path) -> dict:
    """Parse customer schema CSV into structured table inventory."""
    tables = defaultdict(lambda: {"columns": [], "column_count": 0})
    
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            table_name = row["table_name"]
            tables[table_name]["columns"].append({
                "name": row["column_name"],
                "type": row.get("full_data_type", row.get("data_type", "STRING")),
                "nullable": row.get("is_nullable", "YES") == "YES",
                "comment": row.get("comment", ""),
                "ordinal": int(row.get("ordinal_position", 0)),
            })
            tables[table_name]["column_count"] = len(tables[table_name]["columns"])
            tables[table_name]["catalog"] = row.get("table_catalog", "")
            tables[table_name]["schema"] = row.get("table_schema", "")
    
    return dict(tables)

schema = parse_schema_csv(Path("context/Wanderbricks_Schema.csv"))
print(f"Found {len(schema)} tables")
for table, info in sorted(schema.items()):
    print(f"  {table}: {info['column_count']} columns")
```

## classify_tables

Classifies each table as dimension, fact, or bridge based on column patterns.

```python
def classify_tables(schema: dict) -> dict:
    """Classify tables as dimension, fact, or bridge based on column patterns."""
    classified = {}
    for table_name, info in schema.items():
        cols = {c["name"] for c in info["columns"]}
        col_types = {c["name"]: c["type"] for c in info["columns"]}
        
        # Count FK-like columns (columns ending in _id that reference other tables)
        fk_columns = [c for c in cols if c.endswith("_id") and c != f"{table_name.rstrip('s')}_id"]
        pk_candidates = [c for c in cols if c == f"{table_name.rstrip('s')}_id" or c == f"{table_name}_id"]
        measure_types = {"FLOAT", "DOUBLE", "DECIMAL", "LONG", "INT"}
        measures = [c for c in cols if col_types.get(c, "").upper().split("(")[0] in measure_types 
                    and not c.endswith("_id")]
        timestamps = [c for c in cols if col_types.get(c, "").upper() in {"TIMESTAMP", "DATE"}]
        
        if len(info["columns"]) <= 3 and len(fk_columns) >= 2:
            entity_type = "bridge"
        elif len(fk_columns) >= 2 and len(measures) >= 1:
            entity_type = "fact"
        elif len(timestamps) >= 2 and len(fk_columns) >= 2:
            entity_type = "fact"
        else:
            entity_type = "dimension"
        
        classified[table_name] = {
            **info,
            "entity_type": entity_type,
            "pk_candidates": pk_candidates,
            "fk_columns": fk_columns,
            "measures": measures,
            "timestamps": timestamps,
        }
    return classified
```

## infer_relationships

Infers FK relationships from column names and comments using two strategies.

```python
import re

def infer_relationships(classified: dict) -> list:
    """Infer FK relationships from column names and comments."""
    relationships = []
    table_names = set(classified.keys())
    
    for table_name, info in classified.items():
        for col in info["columns"]:
            # Pattern 1: Column comment says "Foreign Key to 'X'"
            if col.get("comment"):
                fk_match = re.search(r"[Ff]oreign [Kk]ey to ['\"]?(\w+)['\"]?", col["comment"])
                if fk_match:
                    ref_table = fk_match.group(1)
                    relationships.append({
                        "from_table": table_name,
                        "from_column": col["name"],
                        "to_table": ref_table,
                        "to_column": f"{ref_table.rstrip('s')}_id",
                        "source": "comment",
                    })
                    continue
            
            # Pattern 2: Column name like 'other_table_id' matches a known table
            if col["name"].endswith("_id"):
                base = col["name"][:-3]  # Remove '_id'
                for candidate in table_names:
                    if candidate == table_name:
                        continue
                    # Match: user_id -> users, host_id -> hosts, property_id -> properties
                    if candidate.startswith(base) or candidate == base + "s" or candidate == base + "es":
                        relationships.append({
                            "from_table": table_name,
                            "from_column": col["name"],
                            "to_table": candidate,
                            "to_column": col["name"],
                            "source": "naming_convention",
                        })
                        break
    return relationships
```

## cross_reference_silver_at_design_time

Advisory validation during design phase. Run AFTER Silver layer is deployed, BEFORE Gold pipeline implementation. Logs warnings but does not block design completion. Warnings become hard errors in Phase 0 of `01-gold-layer-setup`.

```python
def cross_reference_silver_at_design_time(spark, catalog, silver_schema, yaml_base):
    """Advisory validation during design (Silver may not exist yet).
    
    Run AFTER Silver layer is deployed, BEFORE Gold pipeline implementation.
    Logs warnings but does not block design completion.
    """
    from pathlib import Path
    import yaml
    
    warnings = []
    for yaml_file in sorted(yaml_base.rglob("*.yaml")):
        with open(yaml_file) as f:
            config = yaml.safe_load(f)
        
        for col_def in config.get("columns", []):
            lineage = col_def.get("lineage", {})
            s_table = lineage.get("silver_table", "N/A")
            s_col = lineage.get("silver_column", "N/A")
            if s_table == "N/A" or s_col == "N/A":
                continue
            
            try:
                actual_cols = {f.name for f in spark.table(
                    f"{catalog}.{silver_schema}.{s_table}"
                ).schema.fields}
                for single_col in [c.strip() for c in s_col.split(",")]:
                    if single_col not in actual_cols:
                        warnings.append(
                            f"{config['table_name']}.{col_def['name']}: "
                            f"Silver column '{single_col}' not in {s_table}"
                        )
            except Exception:
                pass  # Silver table may not exist yet
    
    if warnings:
        print(f"Design-time Silver cross-reference: {len(warnings)} warning(s)")
        for w in warnings:
            print(f"  WARNING: {w}")
        print("These will become hard errors in Phase 0 of pipeline implementation.")
    else:
        print("Silver cross-reference: all YAML lineage columns verified ✓")
```

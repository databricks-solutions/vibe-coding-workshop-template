# Implementation Guidance

Critical pre-implementation validation patterns, Silver table naming conventions, join requirements, column source mapping, and validation script patterns.

## Critical Rule: YAML Schema Files Are Single Source of Truth

**CRITICAL:** Before writing any Gold layer SQL (TVFs, queries, MERGE statements), ALWAYS consult the YAML schema definitions in `gold_layer_design/yaml/**/*.yaml`.

### Why This Matters

**100% of SQL compilation errors in production deployments** were caused by not consulting YAML schemas first.

**Common errors prevented:**
- Column name mismatches (Silver vs Gold)
- Missing columns in MERGE statements
- Incorrect data types
- Wrong primary key definitions
- Missing foreign key relationships

### Pre-Implementation Checklist

Before writing any Gold layer code:

- [ ] Read YAML schema file for target Gold table
- [ ] Extract column names from YAML (don't guess)
- [ ] Extract data types from YAML
- [ ] Extract primary key from YAML
- [ ] Extract foreign keys from YAML
- [ ] Map Silver columns to Gold columns
- [ ] Validate column mappings match YAML
- [ ] Test DDL matches YAML schema

## Silver Table Naming Conventions

### Pattern: `silver_{entity}`

**Standard naming:**
- `silver_store` → `dim_store`
- `silver_product` → `dim_product`
- `silver_sales` → `fact_sales_daily`
- `silver_inventory` → `fact_inventory_daily`

**Why:** Consistent naming makes source mapping obvious.

### Source Table Property

Always document source Silver table in TBLPROPERTIES:

```python
TBLPROPERTIES (
    'source_layer' = 'silver',
    'source_table' = 'silver_store'  # ✅ Document source
)
```

## Join Requirements

### Dimension-to-Fact Joins

**Pattern:** Always join on surrogate keys, filter SCD Type 2 dimensions:

```sql
SELECT 
    f.net_revenue,
    d.store_name
FROM fact_sales_daily f
JOIN dim_store d 
    ON f.store_key = d.store_key
    AND d.is_current = true  -- ✅ Filter SCD Type 2
```

### Point-in-Time Joins

**Pattern:** Use effective_from/effective_to for historical analysis:

```sql
SELECT 
    f.net_revenue,
    d.store_name
FROM fact_sales_daily f
JOIN dim_store d 
    ON f.store_key = d.store_key
    AND f.transaction_date >= d.effective_from
    AND (f.transaction_date < d.effective_to OR d.effective_to IS NULL)
```

## Column Source Mapping

### Extract from YAML

**Pattern:** Build column mapping from YAML schema:

```python
import yaml
from pathlib import Path

def get_gold_schema(domain: str, table_name: str) -> dict:
    """Extract Gold schema from YAML."""
    yaml_file = Path(f"gold_layer_design/yaml/{domain}/{table_name}.yaml")
    with open(yaml_file) as f:
        return yaml.safe_load(f)

# Extract columns
schema = get_gold_schema("retail", "dim_store")
gold_columns = {col['name']: col['type'] for col in schema['columns']}
```

### Map Silver to Gold

**Pattern:** Build explicit mapping dictionary:

```python
# Extract from actual schemas
silver_df = spark.table("catalog.silver_schema.silver_store")
silver_columns = set(silver_df.columns)

gold_schema = get_gold_schema("retail", "dim_store")
gold_columns = {col['name'] for col in gold_schema['columns']}

# Build mapping
column_mapping = {
    # Direct matches
    'store_id': 'store_number',
    'store_name': 'store_name',
    # Transformations
    'processed_ts': 'record_created_timestamp',
    # Generated
    'store_key': 'store_key'  # Generated from store_id + processed_ts
}
```

### Apply Mapping in MERGE

**Pattern:** Use mapping in SELECT:

```python
updates_df = silver_df.select([
    col("store_id").alias("store_number"),  # Business key mapping
    col("store_name").alias("store_name"),
    md5(concat(col("store_id"), col("processed_ts"))).alias("store_key"),  # Generated
    col("processed_ts").alias("record_created_timestamp"),
    # ... other columns
])
```

## Validation Script Patterns

### Schema Validation

**Pattern:** Validate Gold DDL matches YAML:

```python
def validate_schema_match(yaml_file: Path, ddl_file: Path) -> bool:
    """Validate DDL matches YAML schema."""
    # Load YAML
    with open(yaml_file) as f:
        yaml_schema = yaml.safe_load(f)
    
    # Parse DDL (simplified)
    ddl_content = ddl_file.read_text()
    
    # Extract columns from YAML
    yaml_columns = {col['name']: col['type'] for col in yaml_schema['columns']}
    
    # Extract columns from DDL (requires SQL parsing)
    # ... validation logic ...
    
    return yaml_columns == ddl_columns
```

### Column Mapping Validation

**Pattern:** Validate all Gold columns have Silver sources:

```python
def validate_column_mapping(
    silver_table: str,
    gold_schema: dict,
    column_mapping: dict
) -> list[str]:
    """Validate all Gold columns have Silver sources."""
    errors = []
    
    gold_columns = {col['name'] for col in gold_schema['columns']}
    mapped_columns = set(column_mapping.values())
    
    # Check for unmapped columns
    unmapped = gold_columns - mapped_columns
    if unmapped:
        errors.append(f"Unmapped Gold columns: {unmapped}")
    
    # Check for invalid mappings
    silver_df = spark.table(silver_table)
    silver_columns = set(silver_df.columns)
    
    invalid_sources = set(column_mapping.keys()) - silver_columns
    if invalid_sources:
        errors.append(f"Invalid Silver column sources: {invalid_sources}")
    
    return errors
```

### Primary Key Validation

**Pattern:** Validate PRIMARY KEY matches YAML:

```python
def validate_primary_key(yaml_schema: dict, ddl_content: str) -> bool:
    """Validate PRIMARY KEY matches YAML."""
    yaml_pk = set(yaml_schema.get('primary_key', []))
    
    # Extract PK from DDL (simplified)
    # Requires SQL parsing - check CONSTRAINT pk_* PRIMARY KEY (...)
    
    return yaml_pk == ddl_pk
```

## Common Mistakes

### ❌ Mistake 1: Guessing Column Names

```python
# DON'T DO THIS
updates_df = silver_df.select(
    col("store_id").alias("store_key"),  # ❌ Wrong - might be store_number
    col("name").alias("store_name")  # ❌ Wrong - might be store_display_name
)
```

**✅ Correct:** Extract from YAML

```python
# DO THIS
gold_schema = get_gold_schema("retail", "dim_store")
column_mapping = build_column_mapping(silver_df, gold_schema)
updates_df = silver_df.select([
    col(silver_col).alias(gold_col)
    for silver_col, gold_col in column_mapping.items()
])
```

### ❌ Mistake 2: Missing SCD Type 2 Filter

```sql
-- DON'T DO THIS
SELECT * FROM fact_sales_daily f
JOIN dim_store d ON f.store_key = d.store_key
-- ❌ Missing is_current filter - returns duplicates
```

**✅ Correct:** Filter current version

```sql
SELECT * FROM fact_sales_daily f
JOIN dim_store d 
    ON f.store_key = d.store_key
    AND d.is_current = true  -- ✅ Filter SCD Type 2
```

### ❌ Mistake 3: Wrong Source Table Name

```python
# DON'T DO THIS
TBLPROPERTIES (
    'source_table' = 'silver_stores'  # ❌ Wrong - actual table is silver_store
)
```

**✅ Correct:** Use actual Silver table name

```python
TBLPROPERTIES (
    'source_table' = 'silver_store'  # ✅ Matches actual table
)
```

## Validation Checklist

Before deploying Gold layer code:

- [ ] YAML schema file consulted
- [ ] Column names extracted from YAML (not guessed)
- [ ] Column mappings validated (all Gold columns have Silver sources)
- [ ] Primary key matches YAML
- [ ] Foreign keys match YAML
- [ ] SCD Type 2 filters added (if applicable)
- [ ] Source table name matches actual Silver table
- [ ] Schema validation script run
- [ ] Column mapping validation script run

## References

- [YAML-Driven Gold Setup](../yaml-driven-gold-setup/SKILL.md) - Patterns for creating Gold tables from YAML
- [Gold Layer Merge Patterns](../gold-layer-merge-patterns/SKILL.md) - MERGE operation patterns
- [Schema Validation](../gold-layer-schema-validation/SKILL.md) - Pre-merge validation patterns

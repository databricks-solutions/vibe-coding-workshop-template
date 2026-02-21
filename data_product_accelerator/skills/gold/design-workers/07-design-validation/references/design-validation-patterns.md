# Design Validation Patterns - Extended Reference

This document provides additional validation edge cases and patterns for design-time consistency checking.

## YAML ↔ ERD Edge Cases

### Cross-Domain References

When an ERD uses bracketed notation for cross-domain references (e.g., `dim_store["🏪 dim_store (Location)"]`), the parser must strip the display name to extract the actual table name.

```python
def normalize_erd_table_name(raw_name: str) -> str:
    """Extract actual table name from Mermaid ERD notation."""
    if "[" in raw_name:
        return raw_name.split("[")[0].strip().strip('"')
    return raw_name.strip().strip('"')
```

### Comment-Only Columns in ERD

ERD columns with `PK` or `FK` markers need to be parsed carefully:

```
dim_store {
    int store_key PK
    string store_name
    int region_key FK
}
```

The parser should extract `store_key`, `store_name`, `region_key` — not the type or marker.

## YAML ↔ Lineage Edge Cases

### Generated Columns

Columns like `record_created_timestamp` or `record_hash` may be generated during implementation (not sourced from Silver). These should still appear in the lineage CSV with transformation type `GENERATED`.

```csv
gold_table,gold_column,silver_table,silver_column,transformation_type,transformation_logic
dim_store,record_created_timestamp,,,GENERATED,current_timestamp()
dim_store,record_hash,,,GENERATED,"md5(concat_ws('|', store_key, store_name))"
```

### Multi-Source Columns

Some Gold columns aggregate from multiple Silver sources. The lineage CSV should have one row per source:

```csv
gold_table,gold_column,silver_table,silver_column,transformation_type
fact_sales_daily,total_revenue,silver_pos_transactions,amount,AGGREGATE_SUM
fact_sales_daily,total_revenue,silver_online_orders,order_total,AGGREGATE_SUM
```

## PK/FK Edge Cases

### Composite Foreign Keys

Some relationships involve composite foreign keys (rare in Gold layer, but possible for bridge tables):

```yaml
foreign_keys:
  - columns: [product_key, store_key]
    references_table: fact_inventory_snapshot
    references_columns: [product_key, store_key]
```

The validator should handle both single and composite FK definitions.

### Self-Referencing FK

Hierarchical dimensions may reference themselves:

```yaml
table_name: dim_category
foreign_keys:
  - column: parent_category_key
    references_table: dim_category
    references_column: category_key
```

This is valid and should not be flagged as an error.

## Mandatory Field Edge Cases

### SCD Type 2 Additional Fields

SCD Type 2 dimensions require additional columns that must be present in YAML:

```yaml
columns:
  - name: effective_start_date
    type: TIMESTAMP
    nullable: false
    description: "Start of validity period for this version"
  - name: effective_end_date
    type: TIMESTAMP
    nullable: true
    description: "End of validity period (NULL = current version)"
  - name: is_current
    type: BOOLEAN
    nullable: false
    description: "Flag indicating current active version"
```

### Fact Table Grain Fields

If `entity_type: fact` in table properties, grain-related fields should be present:

```python
if spec.get("table_properties", {}).get("entity_type") == "fact":
    if "grain" not in spec.get("table_properties", {}):
        issues.append(f"{table_name}: fact table missing 'grain' in table_properties")
    if "grain_type" not in spec.get("table_properties", {}) and "grain_type" not in spec:
        issues.append(f"{table_name}: fact table missing 'grain_type'")
```

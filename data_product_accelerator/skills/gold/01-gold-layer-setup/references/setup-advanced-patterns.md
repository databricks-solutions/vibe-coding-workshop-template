# Advanced Setup Patterns

Additional table setup patterns beyond the core YAML-driven DDL generation. These patterns extend Phase 1 (table creation) with post-DDL steps for role-playing dimension views and unknown member row insertion.

---

## Role-Playing Dimension Views

**When to use:** A single physical dimension (typically `dim_date`) is referenced by multiple FKs in a fact table under different roles (e.g., `order_date_key`, `ship_date_key`, `delivery_date_key`).

**Design reference:** `design-workers/02-dimension-patterns/references/dimension-pattern-catalog.md` — Role-Playing Dimensions section

### Implementation Pattern

Create views that alias the physical dimension table for each role:

```python
def create_role_playing_views(spark, catalog, gold_schema, meta):
    """Create role-playing views from YAML role_playing_roles metadata.
    
    YAML format:
      table_properties:
        dimension_pattern: role_playing
        role_playing_roles:
          - view_name: dim_order_date
            description: "Date dimension in the order date role"
          - view_name: dim_ship_date
            description: "Date dimension in the ship date role"
    """
    roles = meta.get("role_playing_roles", [])
    physical_table = f"{catalog}.{gold_schema}.{meta['table_name']}"
    
    for role in roles:
        view_name = role["view_name"]
        view_fqn = f"{catalog}.{gold_schema}.{view_name}"
        description = role.get("description", f"Role-playing view of {meta['table_name']}")
        
        ddl = f"""
        CREATE OR REPLACE VIEW {view_fqn}
        COMMENT '{description}'
        AS SELECT * FROM {physical_table}
        """
        spark.sql(ddl)
        print(f"  Created role-playing view: {view_fqn}")
```

### Integration with `setup_tables.py`

Add role-playing view creation AFTER the main table creation loop:

```python
def create_role_playing_views_from_inventory(spark, catalog, gold_schema, inventory):
    """Scan inventory for role-playing dimensions and create views."""
    for table_name, meta in inventory.items():
        dim_pattern = meta.get("dimension_pattern", "")
        if dim_pattern == "role_playing":
            create_role_playing_views(spark, catalog, gold_schema, meta)
```

### YAML Example

```yaml
table_name: dim_date
table_properties:
  dimension_pattern: role_playing
  role_playing_roles:
    - view_name: dim_order_date
      description: "Date dimension in the order date role"
    - view_name: dim_ship_date
      description: "Date dimension in the ship date role"
    - view_name: dim_delivery_date
      description: "Date dimension in the delivery date role"
```

### Validation

```sql
-- Verify role-playing views exist and return data
SHOW VIEWS IN {catalog}.{gold_schema} LIKE 'dim_*_date';

-- Verify view points to physical table
DESCRIBE EXTENDED {catalog}.{gold_schema}.dim_order_date;
-- Should show "View Text" referencing dim_date
```

---

## Unknown Member Row Insertion

**When to use:** Every dimension table should have an "Unknown" member row to handle late-arriving facts (facts that arrive before their dimension records). This prevents NULL foreign keys and enables outer-join-free queries.

**Design reference:** `design-workers/02-dimension-patterns/references/dimension-pattern-catalog.md` — Unknown Member Rows section

### Implementation Pattern

Insert a single unknown member row AFTER table creation, BEFORE any MERGE operations:

```python
def insert_unknown_member_rows(spark, catalog, gold_schema, inventory):
    """Insert unknown member row for every dimension table in inventory.
    
    Convention:
    - Surrogate key value: '-1' (STRING) or -1 (INT/BIGINT)
    - Business key value: 'UNKNOWN'
    - Text attributes: 'Unknown'
    - Numeric attributes: 0
    - Date attributes: '1900-01-01'
    - Boolean attributes: False
    - Timestamps: current_timestamp()
    """
    for table_name, meta in inventory.items():
        if meta.get("entity_type") != "dimension":
            continue
        
        gold_table = f"{catalog}.{gold_schema}.{table_name}"
        pk_col = meta["pk_columns"][0]
        pk_type = meta["column_types"].get(pk_col, "STRING")
        
        # Determine unknown key value based on type
        if pk_type in ("INT", "BIGINT", "LONG"):
            unknown_key = "-1"
        else:
            unknown_key = "'-1'"
        
        # Build column defaults
        col_values = []
        for col_name in meta["columns"]:
            col_type = meta["column_types"].get(col_name, "STRING").upper()
            if col_name == pk_col:
                col_values.append(f"{unknown_key} AS {col_name}")
            elif col_name in meta.get("business_key", []):
                col_values.append(f"'UNKNOWN' AS {col_name}")
            elif "TIMESTAMP" in col_type:
                col_values.append(f"current_timestamp() AS {col_name}")
            elif "DATE" in col_type:
                col_values.append(f"DATE '1900-01-01' AS {col_name}")
            elif "BOOLEAN" in col_type:
                col_values.append(f"false AS {col_name}")
            elif col_type in ("INT", "BIGINT", "LONG", "DOUBLE", "FLOAT") or "DECIMAL" in col_type:
                col_values.append(f"0 AS {col_name}")
            else:
                col_values.append(f"'Unknown' AS {col_name}")
        
        select_clause = ", ".join(col_values)
        
        # Use MERGE to avoid duplicates on re-run
        merge_sql = f"""
        MERGE INTO {gold_table} AS target
        USING (SELECT {select_clause}) AS source
        ON target.{pk_col} = source.{pk_col}
        WHEN NOT MATCHED THEN INSERT *
        """
        
        try:
            spark.sql(merge_sql)
            print(f"  Unknown member row: {gold_table} ✓")
        except Exception as e:
            print(f"  Unknown member row: {gold_table} — {e}")
```

### Integration with `setup_tables.py`

Add unknown member insertion AFTER table creation and PK constraints, BEFORE FK constraints:

```
1. Create tables (setup_tables.py)
2. Apply PK constraints
3. Insert unknown member rows  ← NEW
4. Apply FK constraints (add_fk_constraints.py)
5. Run merge scripts
```

### Validation

```sql
-- Verify unknown member exists in each dimension
SELECT * FROM {catalog}.{gold_schema}.dim_store WHERE store_key = '-1';

-- Verify no NULLs in required columns of unknown member
SELECT * FROM {catalog}.{gold_schema}.dim_store
WHERE store_key = '-1' AND store_number IS NULL;
-- Should return 0 rows
```

---

## Checklist: Advanced Setup Patterns

- [ ] Role-playing views created for all dimensions with `dimension_pattern: role_playing`
- [ ] Unknown member rows inserted for ALL dimension tables
- [ ] Unknown member key convention: `-1` (STRING or INT)
- [ ] Unknown member business key: `UNKNOWN`
- [ ] Unknown member inserted AFTER PKs, BEFORE FKs
- [ ] Views verified with `SHOW VIEWS` and `DESCRIBE EXTENDED`

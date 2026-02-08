# Metric View Validation Checklist

Comprehensive pre-creation validation steps to prevent 100% of deployment failures.

## Pre-Creation Schema Validation (MANDATORY)

**ALWAYS validate schemas BEFORE creating metric view YAML. 100% of deployment failures are preventable schema issues.**

### Step 1: Verify Source Table Schema

**Check Gold layer YAML definition:**
```bash
# Check Gold layer YAML definition
grep "^- name:" gold_layer_design/yaml/{domain}/{source_table}.yaml

# Or query the table
DESCRIBE TABLE {catalog}.{schema}.{source_table};
```

**Document available columns:**
- [ ] Source table columns listed
- [ ] Column data types verified
- [ ] Primary key identified

### Step 2: Verify All Joined Tables

**For each joined dimension table:**
```bash
# For each joined dimension table
grep "^- name:" gold_layer_design/yaml/{domain}/{dim_table}.yaml
```

**For each joined table, verify:**
- [ ] Table exists
- [ ] Join key column exists in both tables
- [ ] Join key data types match
- [ ] For SCD2 tables: `is_current` column exists

### Step 3: Validate Every Column Reference

**For each dimension and measure, verify:**
- [ ] Column exists in source table (for `source.column`)
- [ ] Column exists in joined table (for `{join_name}.column`)
- [ ] No assumed column names without verification

**Common Column Name Errors:**
- ❌ `is_active` → ✅ Often `is_current` (SCD2 tables)
- ❌ `created_at` → ✅ May be `joined_at`, `created_date`, etc.
- ❌ `booking_count` → ✅ Often need `COUNT(booking_id)` instead

### Step 4: Validate Aggregation Logic

**For COUNT measures:**
- [ ] Use `COUNT({table}.{primary_key_column})`
- [ ] NOT `SUM({table}.count_column)` (column may not exist)

**For SUM measures:**
- [ ] Verify numeric column exists
- [ ] NOT summing a non-existent aggregated field

**Example:**
```yaml
# ❌ WRONG: Assumes booking_count column exists
measures:
  - name: total_bookings
    expr: SUM(fact_booking.booking_count)  # Column doesn't exist!

# ✅ CORRECT: Count primary key
measures:
  - name: total_bookings
    expr: COUNT(fact_booking.booking_id)  # Uses actual column
```

### Step 5: Validate Join Conditions

**Check each join:**
- [ ] Join is direct: `source.fk = dim_table.pk`
- [ ] NOT transitive: `dim_table1.fk = dim_table2.pk` ❌
- [ ] Foreign key exists in source table
- [ ] Primary key exists in dimension table
- [ ] For SCD2: Include `AND {dim_table}.is_current = true`

## YAML Structure Validation

### Version and Top-Level Fields
- [ ] Version is `"1.1"` (quoted string)
- [ ] **NO `name` field** (name is in CREATE VIEW statement)
- [ ] NO `time_dimension` field (not supported in v1.1)
- [ ] NO `window_measures` field (not supported in v1.1)
- [ ] Comment explains business purpose and Genie optimization

### Dimensions
- [ ] All dimensions have comments
- [ ] All dimensions have display_name
- [ ] All dimensions have 3+ synonyms
- [ ] All dimension `expr` use correct prefix (`source.` or `{join_name}.`)

### Measures
- [ ] All measures have comments
- [ ] All measures have display_name
- [ ] All measures have format configuration
- [ ] All measures have synonyms
- [ ] Format types are correct (currency/number/percentage)

### Joins (if using)
- [ ] Each join has `name` field (the alias)
- [ ] Each join has `source` field (full table path)
- [ ] Each join has `'on'` field (quoted!)
- [ ] Joins include SCD2 filters (`is_current = true`) where applicable
- [ ] ON clause uses `source.` for main table, join name for joined table
- [ ] **Each join is direct** (source.fk = dim.pk, NOT dim1.fk = dim2.pk)
- [ ] No transitive/chained joins

### Column References
- [ ] Main table columns use `source.` prefix in all expr fields
- [ ] Joined table columns use join `name` as prefix in expr fields
- [ ] No references to table names (use `source.` or `{join_name}.`)
- [ ] **All column names verified against actual schemas**

### Source Table Selection
- [ ] Revenue/booking metrics source from FACT tables
- [ ] Inventory/count metrics source from DIMENSION tables
- [ ] Source table documented in metric view comment

### Snowflake Schema Joins (if needed)
- [ ] Nested `joins:` used when fact doesn't have direct FK
- [ ] Nested columns reference full path (`parent.nested.column`)
- [ ] Tested with Databricks Runtime 17.1+

### Comment Format (v3.0 Structured Format)
- [ ] Comment includes **PURPOSE** (one-line description)
- [ ] Comment includes **BEST FOR** (4-6 pipe-separated example questions)
- [ ] Comment includes **NOT FOR** with redirect to correct asset
- [ ] Comment includes **DIMENSIONS** (5-8 key filterable columns)
- [ ] Comment includes **MEASURES** (5-8 key aggregated metrics)
- [ ] Comment includes **SOURCE** (table name with domain)
- [ ] Comment includes **JOINS** (joined tables with descriptions)
- [ ] Comment includes **NOTE** (critical caveats/limitations)
- [ ] Professional language (no "broken", "doesn't work")

## Python Script Error Handling

### Function Signature
- [ ] Function signature: `create_metric_view(spark, catalog, schema, view_name, metric_view)`
- [ ] View name extracted from filename (not from YAML)

### Error Handling
- [ ] Script tracks failed_views list
- [ ] Script raises RuntimeError if any metric view fails
- [ ] Job will fail (not succeed) if metric views don't create
- [ ] Drop existing TABLE/VIEW before creating metric view

### Example Pattern
```python
def create_metric_view(spark, catalog, schema, view_name, metric_view):
    fqn = f"{catalog}.{schema}.{view_name}"
    
    # Drop existing table/view to avoid conflicts
    try:
        spark.sql(f"DROP VIEW IF EXISTS {fqn}")
        spark.sql(f"DROP TABLE IF EXISTS {fqn}")
    except:
        pass
    
    try:
        create_sql = f"""
        CREATE VIEW {fqn}
        WITH METRICS
        LANGUAGE YAML
        COMMENT '{comment}'
        AS $$
{yaml_str}
        $$
        """
        spark.sql(create_sql)
        print(f"✓ Created {view_name}")
        return True
    except Exception as e:
        print(f"✗ Error creating {view_name}: {e}")
        return False

def main():
    metric_views = load_metric_views_yaml(catalog, schema)
    failed_views = []
    
    for view_name, metric_view in metric_views:
        if not create_metric_view(spark, catalog, schema, view_name, metric_view):
            failed_views.append(view_name)
    
    if failed_views:
        raise RuntimeError(
            f"Failed to create {len(failed_views)} metric view(s): "
            f"{', '.join(failed_views)}"
        )
```

## Quick Validation Pattern

**For each metric view, create a validation checklist:**

```markdown
## revenue_analytics_metrics Validation

### Source Table: fact_booking_daily
Columns (from gold_layer_design/yaml/booking/fact_booking_daily.yaml):
- property_id ✅
- check_in_date ✅
- destination_id ✅
- total_booking_value ✅
- booking_count ✅
- ...

### Joined Table: dim_property
Columns (from gold_layer_design/yaml/property/dim_property.yaml):
- property_id ✅
- property_type ✅
- is_current ✅
- ...

### Join Validation:
- source.property_id = dim_property.property_id ✅ (both exist)
- dim_property.is_current ✅ (SCD2 filter)

### Column References:
Dimensions:
- source.check_in_date ✅
- source.destination_id ✅
- dim_property.property_type ✅

Measures:
- SUM(source.total_booking_value) ✅
- COUNT(source.booking_id) ✅ (primary key exists)
```

## Pre-Deployment Validation Script

Use `scripts/validate_metric_view.py` to automate validation:

```bash
python scripts/validate_metric_view.py \
  --yaml-file src/semantic/metric_views/revenue_analytics_metrics.yaml \
  --gold-yaml-dir gold_layer_design/yaml
```

The script validates:
- All column references exist in source tables
- Join key columns exist in both tables
- SCD2 filters are present where needed
- No transitive joins
- Primary keys exist for COUNT measures

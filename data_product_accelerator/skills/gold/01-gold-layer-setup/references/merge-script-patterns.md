# Merge Script Patterns

Complete Silver-to-Gold MERGE operation patterns including SCD Type 1/2 dimensions and aggregated fact tables.

## 🔴 YAML Extraction Helpers (MUST Include in Every Merge Script)

**These functions extract ALL metadata from Gold YAML files. Every merge function MUST use these instead of hardcoding values.**

```python
import yaml
import csv
from pathlib import Path

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
    """Extract ALL merge-relevant metadata from a single YAML file.
    
    Returns dict with: table_name, columns, column_types, pk_columns,
    business_key, foreign_keys, scd_type, grain, entity_type, lineage,
    source_table
    """
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    
    columns = config.get("columns", [])
    table_props = config.get("table_properties", {})
    
    # Extract source Silver table from lineage metadata
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
    }

def load_column_mappings_from_yaml(meta: dict) -> dict:
    """Extract Silver→Gold column renames from YAML lineage.
    
    Returns: {gold_column_name: silver_source_column_name} for renames only
    """
    mappings = {}
    for gold_col, lineage in meta.get("lineage", {}).items():
        source_col = lineage.get("silver_column") or lineage.get("source_column", "")
        if source_col and source_col != gold_col:
            mappings[gold_col] = source_col
    return mappings

def load_column_mappings_from_csv(lineage_csv: Path, gold_table: str) -> dict:
    """Extract Silver→Gold column renames from COLUMN_LINEAGE.csv.
    
    Returns: {gold_column_name: silver_source_column_name} for renames only
    """
    mappings = {}
    with open(lineage_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("gold_table") == gold_table:
                silver_col = row.get("silver_column", "")
                gold_col = row.get("gold_column", "")
                if silver_col and gold_col and silver_col != gold_col:
                    mappings[gold_col] = silver_col
    return mappings

def build_merge_condition(pk_columns: list, include_is_current: bool = False) -> str:
    """Build MERGE ON clause from PK columns extracted from YAML.
    
    Args:
        pk_columns: PRIMARY KEY columns from YAML
        include_is_current: Add 'AND target.is_current = true' for SCD2
    """
    conditions = [f"target.{c} = source.{c}" for c in pk_columns]
    if include_is_current:
        conditions.append("target.is_current = true")
    return " AND ".join(conditions)

def build_inventory(yaml_base: Path, domain: str = "all") -> dict:
    """Build complete table inventory from YAML files.
    
    Returns: {table_name: metadata_dict} for all tables
    """
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
```

**Usage in merge functions — values come from YAML, not from typing:**
```python
# ✅ CORRECT: Every value extracted from YAML
meta = inventory["dim_store"]
business_key = meta["business_key"]           # from YAML
gold_columns = meta["columns"]                # from YAML
merge_cond = build_merge_condition(           # from YAML pk_columns
    meta["business_key"], include_is_current=(meta["scd_type"] == "scd2")
)
mappings = load_column_mappings_from_yaml(meta)  # from YAML lineage

# ❌ WRONG: Hardcoding values that exist in YAML
business_key = ["store_number"]               # ❌ hardcoded
gold_columns = ["store_key", "store_number"]  # ❌ hardcoded
merge_cond = "target.store_number = source.store_number"  # ❌ hardcoded
```

---

## Import Block

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, md5, concat_ws,
    when, sum as spark_sum, count, avg, lit, coalesce
)
from delta.tables import DeltaTable
```

**Critical:** Import `sum as spark_sum` to avoid shadowing Python's built-in `sum`. Never name local variables `count`, `sum`, `min`, `max`.

## Parameter Retrieval

```python
def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    silver_schema = dbutils.widgets.get("silver_schema")
    gold_schema = dbutils.widgets.get("gold_schema")

    print(f"Catalog: {catalog}")
    print(f"Silver Schema: {silver_schema}")
    print(f"Gold Schema: {gold_schema}")

    return catalog, silver_schema, gold_schema
```

## SCD Type 2 Dimension Merge

Complete pattern for slowly changing dimensions with historical tracking. **Note how ALL metadata comes from YAML — the only hand-coded parts are business logic (derived columns, surrogate key formula).**

```python
def merge_dimension_scd2(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,           # ← FROM load_table_metadata(yaml_path)
    mappings: dict,       # ← FROM load_column_mappings_from_yaml(meta)
):
    """
    Merge a SCD Type 2 dimension from Silver to Gold.

    ALL metadata comes from YAML:
    - meta["table_name"] → Gold table name
    - meta["business_key"] → Deduplication + merge condition key
    - meta["columns"] → .select() list
    - meta["source_tables"] → Silver source table
    - mappings → Silver→Gold column renames
    """
    table_name = meta["table_name"]              # ← FROM YAML
    business_key = meta["business_key"]           # ← FROM YAML
    gold_columns = meta["columns"]                # ← FROM YAML
    source_table = meta["source_tables"][0]       # ← FROM YAML lineage

    print(f"\n--- Merging {table_name} (SCD Type 2) ---")

    silver_table = f"{catalog}.{silver_schema}.{source_table}"  # ← FROM YAML
    gold_table = f"{catalog}.{gold_schema}.{table_name}"        # ← FROM YAML

    # Step 1: Read and deduplicate Silver source
    silver_raw = spark.table(silver_table)
    original_count = silver_raw.count()

    silver_df = (
        silver_raw
        .orderBy(col("processed_timestamp").desc())
        .dropDuplicates(business_key)   # ← FROM YAML business_key
    )

    dedupe_count = silver_df.count()
    print(f"  Deduplicated: {original_count} → {dedupe_count} records")

    # Step 2: Apply column mappings FROM YAML lineage
    df = silver_df
    for gold_col, silver_col in mappings.items():  # ← FROM YAML lineage
        df = df.withColumn(gold_col, col(silver_col))

    # Step 3: Add SCD Type 2 columns + derived columns (business logic — hand-coded)
    df = (
        df
        .withColumn("store_key",
                   md5(concat_ws("||", *[col(c) for c in business_key],
                                 col("processed_timestamp"))))
        .withColumn("effective_from", col("processed_timestamp"))
        .withColumn("effective_to", lit(None).cast("timestamp"))
        .withColumn("is_current", lit(True))
        # Derived columns (business logic — these ARE hand-coded)
        .withColumn("store_status",
                   when(col("close_date").isNotNull(), "Closed").otherwise("Active"))
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Step 4: Select ONLY columns in Gold DDL — list FROM YAML
    updates_df = df.select(gold_columns)  # ← FROM YAML columns[]

    # Step 5: Build MERGE condition FROM YAML
    merge_cond = build_merge_condition(  # ← FROM YAML business_key
        business_key, include_is_current=True
    )

    # Step 6: MERGE into Gold
    delta_gold = DeltaTable.forName(spark, gold_table)
    delta_gold.alias("target").merge(
        updates_df.alias("source"),
        merge_cond                       # ← FROM YAML (not hardcoded)
    ).whenMatchedUpdate(set={
        "record_updated_timestamp": "source.record_updated_timestamp"
    }).whenNotMatchedInsertAll(
    ).execute()

    print(f"✓ Merged {updates_df.count()} records into {table_name}")
```

### SCD Type 2 Checklist

- [ ] Deduplication on business key BEFORE merge
- [ ] OrderBy `processed_timestamp DESC` (latest first)
- [ ] Surrogate key via `md5(concat_ws("||", ...))` 
- [ ] SCD columns: `effective_from`, `effective_to` (NULL), `is_current` (True)
- [ ] MERGE condition includes `AND target.is_current = true`
- [ ] `whenMatchedUpdate` updates timestamp only
- [ ] `whenNotMatchedInsertAll` for new records

## Fact Table Aggregation Merge

Complete pattern for pre-aggregated fact tables. **Note how grain columns and MERGE condition come from YAML — the only hand-coded parts are the aggregation expressions (business logic).**

```python
def merge_fact_aggregated(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,           # ← FROM load_table_metadata(yaml_path)
    agg_expressions: list, # ← Hand-coded business logic (aggregation formulas)
    derived_expressions: list = None,  # ← Hand-coded derived columns
):
    """
    Merge an aggregated fact table from Silver to Gold.

    FROM YAML: table_name, pk_columns (grain), columns, source_tables
    HAND-CODED: agg_expressions (business logic)
    """
    table_name = meta["table_name"]              # ← FROM YAML
    grain_columns = meta["pk_columns"]            # ← FROM YAML (composite PK = grain)
    gold_columns = meta["columns"]                # ← FROM YAML
    source_table = meta["source_tables"][0]       # ← FROM YAML lineage

    print(f"\n--- Merging {table_name} (Aggregated Fact) ---")

    silver_table = f"{catalog}.{silver_schema}.{source_table}"  # ← FROM YAML
    gold_table = f"{catalog}.{gold_schema}.{table_name}"        # ← FROM YAML

    transactions = spark.table(silver_table)

    # Step 1: Aggregate to grain FROM YAML pk_columns
    agg_df = transactions.groupBy(*grain_columns).agg(*agg_expressions)  # grain FROM YAML

    # Step 2: Add derived metrics (business logic — hand-coded)
    if derived_expressions:
        for expr_fn in derived_expressions:
            agg_df = expr_fn(agg_df)

    # Timestamps
    agg_df = (
        agg_df
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Step 3: Validate grain — columns FROM YAML
    distinct_grain = agg_df.select(*grain_columns).distinct().count()  # ← FROM YAML
    total_rows = agg_df.count()

    if distinct_grain != total_rows:
        raise ValueError(
            f"Grain validation failed for {table_name}!\n"
            f"  Grain columns (from YAML PK): {grain_columns}\n"
            f"  Distinct combinations: {distinct_grain}\n"
            f"  Total rows: {total_rows}"
        )

    print(f"  ✓ Grain validation passed: {total_rows} unique combinations")

    # Step 4: Select ONLY columns in Gold DDL — list FROM YAML
    # Filter to only columns that exist in DataFrame (agg may not produce all Gold cols)
    available_cols = set(agg_df.columns)
    select_cols = [c for c in gold_columns if c in available_cols]  # ← FROM YAML
    result_df = agg_df.select(select_cols)

    # Step 5: Build MERGE condition FROM YAML pk_columns
    merge_cond = build_merge_condition(grain_columns)  # ← FROM YAML

    # Step 6: Build whenMatchedUpdate set FROM YAML columns (exclude PK and audit cols)
    pk_set = set(grain_columns)
    audit_cols = {"record_created_timestamp"}
    update_cols = {
        c: f"source.{c}"
        for c in select_cols
        if c not in pk_set and c not in audit_cols
    }

    # Step 7: MERGE into Gold
    delta_gold = DeltaTable.forName(spark, gold_table)
    delta_gold.alias("target").merge(
        result_df.alias("source"),
        merge_cond                      # ← FROM YAML (not hardcoded)
    ).whenMatchedUpdate(
        set=update_cols                 # ← FROM YAML columns (not hardcoded)
    ).whenNotMatchedInsertAll(
    ).execute()

    print(f"✓ Merged {total_rows} records into {table_name}")
```

**Example usage with hand-coded aggregation expressions:**

```python
# Aggregation expressions ARE hand-coded (business logic)
sales_agg_exprs = [
    spark_sum(when(col("quantity_sold") > 0, col("final_sales_price")).otherwise(0)
             ).alias("gross_revenue"),
    spark_sum(col("final_sales_price")).alias("net_revenue"),
    spark_sum(when(col("quantity_sold") > 0, col("quantity_sold")).otherwise(0)
             ).alias("gross_units"),
    spark_sum(col("quantity_sold")).alias("net_units"),
    count("*").alias("transaction_count"),
]

# Derived columns ARE hand-coded (business logic)
def add_avg_txn_value(df):
    return df.withColumn("avg_transaction_value",
        when(col("transaction_count") > 0,
             col("net_revenue") / col("transaction_count")).otherwise(0))

# Call with YAML-extracted metadata + hand-coded business logic
meta = inventory["fact_sales_daily"]  # ← FROM YAML
merge_fact_aggregated(
    spark, catalog, silver_schema, gold_schema,
    meta=meta,                         # ← FROM YAML
    agg_expressions=sales_agg_exprs,   # ← HAND-CODED (business logic)
    derived_expressions=[add_avg_txn_value],  # ← HAND-CODED
)
```

### Fact Table Checklist (Aggregated)

- [ ] Grain inferred from PRIMARY KEY (composite = aggregated)
- [ ] `.groupBy()` columns match composite PK columns
- [ ] `.agg()` uses `spark_sum`, `count` (not `sum`)
- [ ] Grain validation: `distinct_count == total_count`
- [ ] MERGE condition includes ALL grain columns
- [ ] `whenMatchedUpdate` lists all measure columns explicitly

## Transaction-Grain Fact Merge (No Aggregation)

For facts where `grain_type: transaction` in YAML (or single-column PK that is a natural key), each source row maps to one Gold row. No `.groupBy().agg()` is needed — the pattern is dedup + map + MERGE.

```python
def merge_fact_transaction(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,           # ← FROM load_table_metadata(yaml_path)
    column_mappings: dict = None,  # ← FROM load_column_mappings() or YAML lineage
    derived_expressions: list = None,  # ← Hand-coded derived columns
):
    """
    Merge a transaction-grain fact from Silver to Gold.
    No aggregation — one source row becomes one Gold row.
    Deduplication on the business key is still MANDATORY.

    FROM YAML: table_name, pk_columns, business_key, columns, source_tables
    HAND-CODED: derived_expressions (business logic), column_mappings overrides
    """
    table_name = meta["table_name"]              # ← FROM YAML
    pk_columns = meta["pk_columns"]              # ← FROM YAML
    business_key = meta["business_key"]           # ← FROM YAML
    gold_columns = meta["columns"]                # ← FROM YAML
    source_table = meta["source_tables"][0]       # ← FROM YAML lineage

    print(f"\n--- Merging {table_name} (Transaction-Grain Fact) ---")

    silver_table = f"{catalog}.{silver_schema}.{source_table}"  # ← FROM YAML
    gold_table = f"{catalog}.{gold_schema}.{table_name}"        # ← FROM YAML

    silver_raw = spark.table(silver_table)
    original_count = silver_raw.count()

    # Step 1: Deduplicate on business key (MANDATORY even for transaction facts)
    silver_df = (
        silver_raw
        .orderBy(col("processed_timestamp").desc())
        .dropDuplicates(business_key)  # ← FROM YAML
    )
    dedup_count = silver_df.count()
    print(f"  Deduplicated: {original_count} → {dedup_count} records")

    # Step 2: Map columns (Silver names → Gold names)
    if column_mappings:
        for gold_col, silver_col in column_mappings.items():
            silver_df = silver_df.withColumn(gold_col, col(silver_col))

    # Step 3: Add derived columns (business logic — hand-coded)
    if derived_expressions:
        for expr_fn in derived_expressions:
            silver_df = expr_fn(silver_df)

    # Step 4: Add audit timestamps
    result_df = (
        silver_df
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Step 5: Select ONLY Gold columns — list FROM YAML
    available_cols = set(result_df.columns)
    select_cols = [c for c in gold_columns if c in available_cols]
    result_df = result_df.select(select_cols)

    # Step 6: Validate grain — one row per PK combination
    distinct_grain = result_df.select(*pk_columns).distinct().count()
    total_rows = result_df.count()
    if distinct_grain != total_rows:
        raise ValueError(
            f"Grain validation failed for {table_name}!\n"
            f"  PK columns (from YAML): {pk_columns}\n"
            f"  Distinct combinations: {distinct_grain}\n"
            f"  Total rows: {total_rows}"
        )
    print(f"  ✓ Grain validation passed: {total_rows} unique records")

    # Step 7: Build MERGE condition FROM YAML pk_columns
    merge_cond = build_merge_condition(pk_columns)

    # Step 8: MERGE into Gold
    delta_gold = DeltaTable.forName(spark, gold_table)
    pk_set = set(pk_columns)
    audit_cols = {"record_created_timestamp"}
    update_cols = {
        c: f"source.{c}" for c in select_cols
        if c not in pk_set and c not in audit_cols
    }

    delta_gold.alias("target").merge(
        result_df.alias("source"),
        merge_cond
    ).whenMatchedUpdate(
        set=update_cols
    ).whenNotMatchedInsertAll(
    ).execute()

    print(f"✓ Merged {total_rows} records into {table_name}")
```

**Key difference from aggregated facts:** No `.groupBy().agg()` step. The grain validation still applies — verify uniqueness on PK columns after dedup.

**When to use:** YAML has `grain_type: transaction`, or the PK is a single natural key (e.g., `booking_id`) rather than a composite grain.

### Transaction Fact Checklist

- [ ] Business key extracted from YAML for deduplication
- [ ] Deduplication applied BEFORE column mapping (mandatory)
- [ ] No `.groupBy().agg()` — one source row = one Gold row
- [ ] Column mappings from YAML lineage or `COLUMN_LINEAGE.csv`
- [ ] Grain validation on PK columns after dedup
- [ ] MERGE condition uses PK columns from YAML

## Main Entry Point

```python
def main():
    """Main entry point for Gold layer MERGE operations.
    
    Uses YAML inventory to determine table order:
    - Dimensions merged FIRST (facts reference dimensions via FK)
    - Facts merged AFTER all dimensions
    """
    catalog, silver_schema, gold_schema = get_parameters()

    spark = SparkSession.builder.appName("Gold Layer MERGE").getOrCreate()

    print("=" * 80)
    print("GOLD LAYER MERGE OPERATIONS")
    print(f"Source: {catalog}.{silver_schema}")
    print(f"Target: {catalog}.{gold_schema}")
    print("=" * 80)

    try:
        # Step 1: Build inventory FROM YAML (single source of truth)
        yaml_base = find_yaml_base()
        inventory = build_inventory(yaml_base)
        print(f"✓ Loaded {len(inventory)} table definitions from YAML")

        # Step 2: Separate dimensions and facts (FROM YAML entity_type)
        dimensions = {k: v for k, v in inventory.items() if v["entity_type"] == "dimension"}
        facts = {k: v for k, v in inventory.items() if v["entity_type"] == "fact"}

        # Step 3: Merge dimensions FIRST (facts reference dimensions)
        for table_name, meta in dimensions.items():
            mappings = load_column_mappings_from_yaml(meta)
            if meta["scd_type"] == "scd2":
                merge_dimension_scd2(spark, catalog, silver_schema, gold_schema, meta, mappings)
            # Add SCD Type 1 handler, etc.

        # Step 4: Merge facts AFTER dimensions
        for table_name, meta in facts.items():
            # Aggregation expressions are defined per-table (business logic)
            agg_exprs = get_agg_expressions_for(table_name)  # ← per-table business logic
            merge_fact_aggregated(spark, catalog, silver_schema, gold_schema, meta, agg_exprs)

        print("\n" + "=" * 80)
        print("✓ Gold layer MERGE completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during Gold layer MERGE: {str(e)}")
        raise
    finally:
        spark.stop()
```

**Key patterns:**
- `build_inventory()` loads ALL table metadata from YAML once
- Dimension/fact separation comes from YAML `entity_type`
- SCD type comes from YAML `scd_type`
- Only aggregation expressions are per-table hand-coded business logic

---

## Scripted Column Resolution

Instead of generating per-table `.withColumn()` chains from YAML lineage (error-prone), use the `build_column_expressions()` function from `references/design-to-pipeline-bridge.md` to build PySpark column expressions programmatically.

**Old approach (agent generates per-table, prone to column name errors):**
```python
updates_df = (
    silver_df
    .withColumn("company_retail_control_number", col("company_rcn"))
    .withColumn("store_number", col("store_number"))
    .withColumn("record_updated_timestamp", current_timestamp())
    .select("store_key", "store_number", "company_retail_control_number", ...)
)
```

**New approach (scripted from YAML, deterministic):**
```python
from design_to_pipeline_bridge import apply_automated_columns

column_defs = yaml_config.get("columns", [])
partial_df, manual_cols = apply_automated_columns(silver_df, meta, column_defs)

# Only hand-code the columns that require business logic:
# AGGREGATE_*, DERIVED_CALCULATION, HASH_MD5, HASH_SHA256
for gold_name, lineage, _ in manual_cols:
    transformation = lineage.get("transformation", "")
    if transformation == "HASH_MD5":
        # Build surrogate key from business key columns
        partial_df = partial_df.withColumn(
            gold_name,
            md5(concat_ws("||", *[col(c) for c in meta["business_key"]]))
        )
    # ... other manual transformations
```

**Coverage:** `build_column_expressions()` automates DIRECT_COPY, RENAME, CAST, GENERATED, COALESCE, and DATE_TRUNC transformations (~70% of typical columns). Only AGGREGATE_*, DERIVED_CALCULATION, HASH_*, and LOOKUP transformations require hand-written code.

See `references/design-to-pipeline-bridge.md` for the full implementation.

## Related Skills

- `pipeline-workers/02-merge-patterns` — Complete SCD Type 1/2 and fact merge templates
- `pipeline-workers/03-deduplication` — Deduplication patterns
- `pipeline-workers/04-grain-validation` — Grain inference and validation
- `pipeline-workers/05-schema-validation` — DataFrame-to-DDL validation

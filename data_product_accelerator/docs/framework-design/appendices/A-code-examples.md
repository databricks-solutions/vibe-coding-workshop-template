# Appendix A — Code Examples

Complete working code snippets for key patterns in the Data Product Accelerator.

---

## 1. Extract Table Names from Gold YAML (Core Pattern)

The "Extract, Don't Generate" principle in action:

```python
import yaml
from pathlib import Path

def get_gold_table_names(domain: str) -> list[str]:
    """Extract all table names for a domain from Gold layer YAML."""
    yaml_dir = Path("gold_layer_design/yaml") / domain
    table_names = []

    for yaml_file in yaml_dir.glob("*.yaml"):
        with open(yaml_file) as f:
            schema = yaml.safe_load(f)
            table_names.append(schema['table_name'])

    return sorted(table_names)


def get_table_schema(domain: str, table_name: str) -> dict:
    """Extract complete schema for a table."""
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
```

---

## 2. Gold Table Creation from YAML

Dynamic DDL generation from YAML schema definitions:

```python
def create_gold_table_from_yaml(spark, catalog: str, schema: str, yaml_file: Path):
    """Create Gold table using schema extracted from YAML."""
    with open(yaml_file) as f:
        table_def = yaml.safe_load(f)

    table_name = table_def['table_name']
    columns = table_def['columns']

    # Build column definitions
    column_defs = []
    for col in columns:
        nullable = "" if col.get('nullable', True) else "NOT NULL"
        comment = f"COMMENT '{col.get('comment', '')}'" if col.get('comment') else ""
        column_defs.append(f"  {col['name']} {col['type']} {nullable} {comment}")

    columns_sql = ",\n".join(column_defs)

    ddl = f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table_name} (
    {columns_sql}
    )
    USING DELTA
    CLUSTER BY AUTO
    COMMENT '{table_def.get('comment', '')}';
    """

    spark.sql(ddl)
```

---

## 3. Silver DLT Pipeline with Expectations

Streaming ingestion with data quality rules:

```python
import dlt
from pyspark.sql.functions import col

@dlt.table(
    name="silver_orders",
    comment="Silver streaming table with incremental dedupe and expectations",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "layer": "silver",
        "domain": "sales"
    },
    cluster_by_auto=True
)
@dlt.expect_or_drop("valid_amount", "amount >= 0")
@dlt.expect("reasonable_qty", "quantity BETWEEN 1 AND 10000")
def silver_orders():
    return (
        dlt.read_stream("bronze_orders")
        .dropDuplicates(["order_id"])
        .withColumn("is_valid", col("amount").isNotNull() & (col("amount") >= 0))
    )
```

---

## 4. Gold MERGE with Deduplication

SCD Type 1 dimension merge with pre-merge deduplication:

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable

def merge_dimension_scd1(spark, catalog, schema, table_name, silver_table, business_key_cols):
    """SCD Type 1 merge with deduplication."""

    # Read Silver source
    silver_df = spark.table(f"{catalog}.silver.{silver_table}")

    # CRITICAL: Deduplicate before merge
    window = Window.partitionBy(*business_key_cols).orderBy(F.col("_commit_timestamp").desc())
    deduped_df = (
        silver_df
        .withColumn("_row_num", F.row_number().over(window))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    # Get Gold table
    gold_table = DeltaTable.forName(spark, f"{catalog}.{schema}.{table_name}")

    # Build merge condition
    merge_condition = " AND ".join(
        [f"target.{col} = source.{col}" for col in business_key_cols]
    )

    # Execute merge
    gold_table.alias("target").merge(
        deduped_df.alias("source"),
        merge_condition
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

---

## 5. Asset Bundle Job Configuration (Serverless)

Standard notebook job with parameters:

```yaml
resources:
  jobs:
    gold_merge_job:
      name: "${var.project}-gold-merge"
      tasks:
        - task_key: merge_dimensions
          notebook_task:
            notebook_path: src/gold/merge_gold_tables.py
            base_parameters:
              catalog: "${var.catalog}"
              schema: "${var.gold_schema}"
              domain: "${var.domain}"
          environment_key: default

environments:
  default:
    spec:
      client: "2"
```

---

## 6. FK Constraint Application (Post-Creation)

Apply constraints via ALTER TABLE after data is loaded:

```python
def apply_fk_constraints(spark, catalog, schema, yaml_file):
    """Apply FK constraints from YAML schema definition."""
    with open(yaml_file) as f:
        table_def = yaml.safe_load(f)

    table_name = table_def['table_name']

    # Apply PK constraint
    pk_cols = table_def.get('primary_key', [])
    if pk_cols:
        pk_sql = ", ".join(pk_cols)
        spark.sql(f"""
            ALTER TABLE {catalog}.{schema}.{table_name}
            ADD CONSTRAINT pk_{table_name}
            PRIMARY KEY ({pk_sql}) NOT ENFORCED
        """)

    # Apply FK constraints
    for fk in table_def.get('foreign_keys', []):
        fk_name = f"fk_{table_name}_{fk['references'].split('.')[-1]}"
        fk_cols = ", ".join(fk['columns'])
        ref_cols = ", ".join(fk['ref_columns'])
        spark.sql(f"""
            ALTER TABLE {catalog}.{schema}.{table_name}
            ADD CONSTRAINT {fk_name}
            FOREIGN KEY ({fk_cols})
            REFERENCES {catalog}.{schema}.{fk['references']}({ref_cols})
            NOT ENFORCED
        """)
```

---

## 7. Metric View Creation

Creating a UC Metric View from YAML:

```sql
CREATE VIEW ${catalog}.${schema}.sales_kpis
WITH METRICS
LANGUAGE YAML
AS $$
version: 1
source: ${catalog}.${schema}.fact_sales
dimensions:
  - name: channel
    expr: channel
    synonyms: ["sales channel", "purchase method"]
  - name: store
    expr: store_name
measures:
  - name: total_revenue
    expr: SUM(amount)
    description: "Total sales revenue in USD"
  - name: order_count
    expr: COUNT(DISTINCT order_id)
    description: "Number of unique orders"
$$;
```

---

## 8. Cursor Agent Invocation Pattern

How to invoke a skill in the Cursor IDE:

```
# Stage 1: Gold Design
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv. Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md

# Stage 2: Bronze Setup
Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach A

# Stage 3: Silver Setup
Set up the Silver layer using @data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md

# Stage 4: Gold Implementation
Implement the Gold layer using @data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md
```

Each prompt triggers the orchestrator skill, which handles the full workflow.

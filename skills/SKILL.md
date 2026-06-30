# Lakebase Change Data Feed (CDF) — Sync Postgres to Unity Catalog

## Overview

Lakebase Change Data Feed (CDF) captures every `INSERT`, `UPDATE`, and `DELETE` on Lakebase Postgres tables via the write-ahead log (WAL) and stores them as append-only rows in Unity Catalog managed Delta tables. Changes are batched and flushed approximately every ~15 seconds.

Destination tables are named `lb_<table_name>_history` in the Unity Catalog catalog and schema you choose.

> **Status:** Public Preview

---

## When to Load This Skill

Load this skill when the user asks about:
- Syncing Lakebase Postgres tables to Unity Catalog
- Setting up Change Data Feed from Lakebase
- Building downstream pipelines from Lakebase change history
- Troubleshooting missing tables in Lakebase CDF
- Consuming `lb_*_history` Delta tables
- Understanding `_pg_change_type`, `_pg_lsn`, `_pg_xid`, `_timestamp`, `_sort_by` columns
- Lakebase wal2delta extension
- Replica identity configuration for CDF

---

## Prerequisites & Requirements

| Requirement | Details |
|---|---|
| Lakebase version | Autoscaling project running Postgres 17 |
| Preview enablement | Workspace admin must enable "Lakebase Change Data Feed" from workspace Previews page |
| Source database | Tables must reside in the `databricks_postgres` database (default) |
| Unity Catalog permissions | `USE CATALOG`, `USE SCHEMA`, and `CREATE TABLE` on destination catalog/schema |
| Destination catalog | Must NOT use default storage (catalogs with default storage are unsupported) |
| Lakebase project permissions | Postgres role requires `CAN MANAGE` on the Lakebase project |
| Replica identity | Each source table must have `REPLICA IDENTITY FULL` set |

---

## Setup Steps

### Step 1: Set Replica Identity Full

For CDF to capture full before-and-after row state, tables need `REPLICA IDENTITY FULL`.

**Single table:**
```sql
ALTER TABLE <table_name> REPLICA IDENTITY FULL;
```

**All existing tables in a schema:**
```sql
DO $
DECLARE r record;
BEGIN
  FOR r IN
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
  LOOP
    EXECUTE format(
      'ALTER TABLE %I.%I REPLICA IDENTITY FULL;',
      r.table_schema, r.table_name
    );
  END LOOP;
END $;
```

**Auto-apply to future tables (event trigger):**
```sql
CREATE OR REPLACE FUNCTION public.set_full_replica_identity()
RETURNS event_trigger
LANGUAGE plpgsql
AS $
DECLARE
  obj record;
BEGIN
  FOR obj IN
    SELECT * FROM pg_event_trigger_ddl_commands()
    WHERE command_tag = 'CREATE TABLE'
  LOOP
    EXECUTE format(
      'ALTER TABLE %s REPLICA IDENTITY FULL;',
      obj.object_identity
    );
  END LOOP;
END $;

CREATE EVENT TRIGGER set_full_replica_identity_on_create
  ON ddl_command_end
  WHEN TAG IN ('CREATE TABLE')
  EXECUTE FUNCTION public.set_full_replica_identity();
```

**Check which tables have replica identity:**
```sql
SELECT n.nspname AS table_schema,
       c.relname AS table_name,
       CASE c.relreplident
         WHEN 'd' THEN 'default'
         WHEN 'n' THEN 'nothing'
         WHEN 'f' THEN 'full'
         WHEN 'i' THEN 'index'
       END AS replica_identity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname = 'public'
ORDER BY n.nspname, c.relname;
```

Only rows with `replica_identity = 'full'` are ready for CDF.

### Step 2: Start the Change Data Feed (UI)

1. Open **Lakebase Postgres** from the app switcher (top right)
2. Select your project and branch (e.g., `production` or `main`)
3. Open **Branch overview** → **Change Data Feed** tab
4. Click **Start**
5. Configure:
   - **Database:** `databricks_postgres` (default)
   - **Schema:** Select the source Postgres schema
   - **To Catalog:** Select the destination Unity Catalog catalog
   - **Schema:** Select the destination Unity Catalog schema
6. Click **Start** to begin

CDF is configured at the **schema level** — every current and future table in the source schema is included.

---

## Destination Table Schema

Each source table gets a corresponding `lb_<table_name>_history` Delta table. In addition to source columns, these system columns are added:

| Column | Type | Description |
|---|---|---|
| `_pg_change_type` | TEXT | Operation: `insert`, `delete`, `update_preimage`, or `update_postimage` |
| `_pg_lsn` | BIGINT | Postgres Log Sequence Number |
| `_pg_xid` | INTEGER | Postgres Transaction ID |
| `_timestamp` | TIMESTAMP | When the change was processed (no timezone) |
| `_sort_by` | BIGINT | Monotonic sort key for ordering all changes |

---

## Change Patterns

| Operation | Rows produced | `_pg_change_type` values |
|---|---|---|
| Initial snapshot | 1 per existing row | `insert` |
| INSERT | 1 | `insert` |
| UPDATE | 2 | `update_preimage` (old) + `update_postimage` (new) |
| DELETE | 1 | `delete` |

---

## Downstream Pipeline Patterns

### Pattern 1: Materialized View (Simplest)

Refreshes incrementally as new change events arrive:

```sql
CREATE MATERIALIZED VIEW inventory_levels AS
SELECT
  item_id,
  SUM(
    CASE
      WHEN _pg_change_type IN ('insert', 'update_postimage') THEN -quantity
      WHEN _pg_change_type IN ('delete', 'update_preimage') THEN quantity
      ELSE 0
    END
  ) AS current_inventory,
  MAX(_timestamp) AS last_transaction_ts,
  MAX(_pg_lsn) AS last_lsn
FROM lb_orders_history
GROUP BY item_id;
```

### Pattern 2: Spark Declarative Pipelines (Medallion Architecture)

```python
import dlt
from pyspark.sql import functions as F

@dlt.table
def inventory_adjustments():
    return (
        spark.readStream.table("<catalog>.<schema>.lb_orders_history")
        .withColumn(
            "delta",
            F.when(F.col("_pg_change_type").isin("insert", "update_postimage"), -F.col("quantity"))
             .when(F.col("_pg_change_type").isin("delete", "update_preimage"), F.col("quantity"))
             .otherwise(0),
        )
        .select("item_id", "delta", "_timestamp")
    )

@dlt.expect_or_drop("non_negative_stock", "on_hand >= 0")
@dlt.table
def inventory_levels():
    return (
        spark.read.table("LIVE.inventory_adjustments")
        .groupBy("item_id")
        .agg(F.sum("delta").alias("on_hand"))
    )
```

### Pattern 3: Spark Structured Streaming with foreachBatch (Full Control)

```python
from pyspark.sql import functions as F
from delta.tables import DeltaTable

def update_inventory(batch_df, batch_id):
    deltas = (
        batch_df
        .withColumn(
            "delta",
            F.when(F.col("_pg_change_type").isin("insert", "update_postimage"), -F.col("quantity"))
             .when(F.col("_pg_change_type").isin("delete", "update_preimage"), F.col("quantity"))
             .otherwise(0),
        )
        .groupBy("item_id")
        .agg(F.sum("delta").alias("delta"))
    )

    target = DeltaTable.forName(spark, "<catalog>.<schema>.inventory_levels")
    (target.alias("t")
     .merge(deltas.alias("s"), "t.item_id = s.item_id")
     .whenMatchedUpdate(set={"on_hand": F.expr("t.on_hand + s.delta")})
     .whenNotMatchedInsert(values={"item_id": "s.item_id", "on_hand": "s.delta"})
     .execute())

(spark.readStream.table("<catalog>.<schema>.lb_orders_history")
 .writeStream
 .foreachBatch(update_inventory)
 .option("checkpointLocation", "/Volumes/<catalog>/<schema>/<volume>/checkpoints/inventory_levels")
 .start())
```

---

## Key Design Points

- **Incremental by design:** Each `lb_*_history` table is append-only. Materialized views, SDP, and Structured Streaming all process new rows incrementally from the Delta transaction log.
- **No need to enable Delta CDF:** Change semantics are already encoded in `_pg_change_type` row data.
- **Schema-level scope:** Starting CDF on a schema includes all current AND future tables.
- **Empty tables skipped:** A table must have at least one row to appear in the destination.

---

## Operational Behavior

### Naming Collisions
If two source tables would map to the same destination (e.g., `sales.users` and `marketing.users` both → `lb_users_history`), the first gets `lb_users_history` and the second gets `lb_users_history_1`. Renaming in UC is safe.

### Dropped Source Tables
Dropping a table in Lakebase preserves the destination Delta table in Unity Catalog.

### Schema Changes
- **Rename table in Postgres:** Feed continues; destination name stays the same.
- **Add/drop/alter column:** Triggers a full re-snapshot of the affected table.

### Monitoring Feed Status

From the Lakebase SQL Editor:
```sql
SELECT * FROM wal2delta.tables;
```

Returns: `table_oid`, `status` (`STREAMING` or `SNAPSHOTTING`), `committed_lsn`, `last_write_time`.

Also visible in the **Change Data Feed** tab under:
- **Schemas sub-tab:** Source schema, destination catalog/schema, status
- **Tables sub-tab:** Source table, destination table, status, Committed LSN, Last update

---

## Disabling CDF

1. Open Lakebase Postgres → select project/branch
2. Branch overview → Change Data Feed tab
3. Click **Disable** → confirm

> **Warning:** If you re-enable CDF later, the system does NOT perform a full re-snapshot. Changes that occurred while disabled are permanently missing.

Disabling does not restart compute.

---

## Data Type Mapping

| PostgreSQL type | Delta type | Notes |
|---|---|---|
| BOOLEAN | BOOLEAN | |
| INT, SMALLINT, BIGINT | INT, SMALLINT, BIGINT | |
| TEXT, VARCHAR, CHAR | STRING | |
| JSONB | STRING | Stored as JSON string |
| ENUM | STRING | Stored as enum label |
| NUMERIC/DECIMAL | DECIMAL or STRING | STRING when precision > 38 or unbounded; NaN → NULL |
| DATE | DATE | |
| TIMESTAMP | TIMESTAMP_NTZ | |
| TIMESTAMPTZ | TIMESTAMP | |
| FLOAT, DOUBLE | FLOAT, DOUBLE | |
| Geography/Geometry (PostGIS) | STRING | |
| Vector (pgvector) | STRING | |
| Composite/struct types | STRING | |
| hstore (map) | STRING | |

---

## Limitations & Troubleshooting

| Issue | Resolution |
|---|---|
| Table not appearing in feed | Ensure `REPLICA IDENTITY FULL` is set |
| Partitioned tables | Not supported; causes those tables to fail |
| Empty tables | Skipped until at least one row exists |
| Source must be `databricks_postgres` | Known limitation; other databases not supported |
| Default storage catalogs | Not supported as destinations |

---

## Architecture: wal2delta

Lakebase CDF is powered by the `wal2delta` Postgres extension, which:
- Runs inside Lakebase compute
- Uses logical decoding to capture WAL changes
- Writes changes to Delta tables in Unity Catalog
- Batches and flushes approximately every ~15 seconds

---

## Quick Reference

```
Source: Lakebase Postgres table (databricks_postgres DB)
  ↓ WAL logical decoding (wal2delta extension)
  ↓ ~15 second batches
Destination: lb_<table_name>_history Delta table in Unity Catalog
  ↓
Consumers: Materialized Views | SDP Pipelines | Structured Streaming
```

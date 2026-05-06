# DLT Pipeline Troubleshooting

Comprehensive guide for diagnosing and fixing Delta Live Tables pipeline failures.

---

## Pipeline Lifecycle States

| State | Meaning | Action |
|-------|---------|--------|
| `IDLE` | No update running | Ready to start |
| `RUNNING` | Update in progress | Poll for completion |
| `FAILED` | Update failed | Get events, diagnose |
| `STOPPING` | Cancellation in progress | Wait for IDLE |
| `RESETTING` | Full refresh in progress | Wait for completion |

## Update States

| State | Meaning |
|-------|---------|
| `QUEUED` | Waiting for cluster |
| `INITIALIZING` | Setting up cluster |
| `SETTING_UP_TABLES` | Creating tables |
| `RUNNING` | Executing pipeline |
| `COMPLETED` | Success |
| `FAILED` | Error occurred |
| `CANCELED` | User cancelled |
| `WAITING_FOR_RESOURCES` | Cluster resource contention |

---

## Diagnostic CLI Commands

### Get Pipeline Status
```bash
databricks pipelines get <PIPELINE_ID> --output json | jq '{
  state: .state,
  latest_update: .latest_updates[0] | {
    update_id: .update_id,
    state: .state,
    creation_time: .creation_time
  }
}'
```

### Get Error Events
```bash
# All ERROR events (most recent first)
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.level == "ERROR") | {
    timestamp: .timestamp,
    message: .message,
    error: (.error.exceptions // [])[:1]
  }] | .[0:5]'
```

### Get Flow Progress (Expectations)
```bash
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.event_type == "flow_progress") | {
    flow: .origin.flow_name,
    status: .details.flow_progress.status,
    rows_written: .details.flow_progress.metrics.num_output_rows,
    expectations: .details.flow_progress.data_quality
  }] | .[0:10]'
```

### Get Update Progress
```bash
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.event_type == "update_progress") | {
    state: .details.update_progress.state,
    message: .message
  }] | .[0:5]'
```

---

## Common Failure Patterns

### Pattern 1: Code Error in DLT Notebook

**Symptoms:** Update state = `FAILED`, ERROR events reference Python/SQL exception.

**Diagnosis:**
```bash
# Get the specific error
databricks pipelines list-pipeline-events <PID> --output json \
  | jq '[.events[] | select(.level == "ERROR")][0].error.exceptions[0]'
```

**Common Errors:**
- `NameError: name 'X' is not defined` → Missing import or variable
- `AnalysisException` → SQL/DataFrame column/table error
- `ModuleNotFoundError` → Add `%pip install` or update pipeline dependencies

**Fix:** Read the DLT notebook, fix the error, redeploy:
```bash
databricks bundle deploy -t <target>
databricks pipelines start-update <PIPELINE_ID>
```

### Pattern 2: Expectation Failures (Rows Dropped)

**Symptoms:** Pipeline succeeds but fewer rows than expected. Events show expectation violations.

**Diagnosis:**
```bash
# Check expectation results
databricks pipelines list-pipeline-events <PID> --output json \
  | jq '[.events[] | select(.event_type == "flow_progress") | {
    flow: .origin.flow_name,
    expectations: .details.flow_progress.data_quality
  }] | map(select(.expectations != null))'
```

**Fix Options:**
- If expectations are too strict: relax the rules (change `expect_or_drop` to `expect`)
- If source data is bad: fix upstream data quality
- If expectations are stored in Delta table: update the expectations table

### Pattern 3: Missing Upstream Table

**Symptoms:** `TABLE_OR_VIEW_NOT_FOUND` or `Streaming source not found`.

**Root Cause:** Bronze tables not created/populated, or wrong table reference.

**Diagnosis:**
```sql
-- Check if source table exists
SHOW TABLES IN catalog.bronze_schema LIKE 'source_table';
-- Check if it has data
SELECT COUNT(*) FROM catalog.bronze_schema.source_table;
```

**Fix:**
1. Run Bronze setup job first
2. Verify table name matches DLT notebook reference
3. Check catalog/schema path

### Pattern 4: Schema Mismatch

**Symptoms:** `AnalysisException: Cannot write to 'X' due to schema mismatch`.

**Root Cause:** Source schema changed (column added/removed/type changed).

**Fix Options:**
1. Update DLT notebook to handle new schema
2. Set `schema_mode = "addNewColumns"` or `schema_mode = "overwrite"` in pipeline config
3. Full refresh: `databricks pipelines start-update <PID> --full-refresh`

### Pattern 5: Checkpoint Corruption

**Symptoms:** `StreamingQueryException` referencing checkpoint state, offset files, or commit log.

**Fix:**
1. Clear checkpoint (pipeline will reprocess from source):
   ```bash
   # In notebook or via CLI
   dbutils.fs.rm("dbfs:/pipelines/<pipeline_id>/checkpoints/", recurse=True)
   ```
2. Restart with full refresh:
   ```bash
   databricks pipelines start-update <PIPELINE_ID> --full-refresh
   ```

### Pattern 6: Pipeline Stuck Running

**Symptoms:** Pipeline in RUNNING state for much longer than expected, no new events.

**Diagnosis:**
```bash
# Check latest events
databricks pipelines list-pipeline-events <PID> --output json \
  | jq '[.events[] | {timestamp, event_type, message}] | .[0:10]'

# Check if cluster is healthy
databricks pipelines get <PID> --output json \
  | jq '.cluster_id'
# Then check cluster
databricks clusters get <CLUSTER_ID> --output json | jq '.state'
```

**Fix:**
1. Cancel the update: `databricks pipelines stop <PIPELINE_ID>`
2. Wait for IDLE state
3. Check and fix any issues
4. Restart: `databricks pipelines start-update <PIPELINE_ID>`

### Pattern 7: Concurrent Write Conflicts

**Symptoms:** `ConcurrentAppendException` or `ConcurrentDeleteReadException`.

**Root Cause:** Multiple jobs/pipelines writing to same table simultaneously.

**Fix:**
1. Serialize writes using job dependencies (`depends_on` in DAB YAML)
2. Enable conflict resolution:
   ```python
   spark.conf.set("spark.databricks.delta.retryWriteConflict.enabled", "true")
   ```
3. Use isolation level: `ALTER TABLE ... SET TBLPROPERTIES ('delta.isolationLevel' = 'WriteSerializable')`

---

## DLT Pipeline SDK Operations

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# Get pipeline details
pipeline = w.pipelines.get(pipeline_id="abc123")
print(f"State: {pipeline.state}")
print(f"Latest update: {pipeline.latest_updates[0].state if pipeline.latest_updates else 'None'}")

# Start update
w.pipelines.start_update(pipeline_id="abc123")

# Start full refresh
w.pipelines.start_update(pipeline_id="abc123", full_refresh=True)

# Stop pipeline
w.pipelines.stop_and_wait(pipeline_id="abc123")

# Get events
events = w.pipelines.list_pipeline_events(pipeline_id="abc123")
for event in events:
    if event.level == "ERROR":
        print(f"ERROR: {event.message}")
```

---

## Pipeline Troubleshooting Flowchart

```
Pipeline Failed?
├── Get events: databricks pipelines list-pipeline-events <PID>
│
├── ERROR event has Python/SQL exception?
│   ├── ModuleNotFoundError → Add %pip install or pipeline dependency
│   ├── AnalysisException → Fix column/table reference in DLT notebook
│   ├── TABLE_NOT_FOUND → Run upstream setup job first
│   └── Other → Read full exception, fix notebook code
│
├── No ERROR events but FAILED state?
│   ├── Check cluster events → Cluster crashed (OOM, spot lost)
│   └── Check update progress → Timeout, resource contention
│
├── Pipeline stuck RUNNING?
│   ├── Stop pipeline: databricks pipelines stop <PID>
│   ├── Check cluster health
│   └── Restart: databricks pipelines start-update <PID>
│
└── Expectations dropping too many rows?
    ├── Check data quality in source
    ├── Review expectation definitions
    └── Consider expect (warn) vs expect_or_drop (enforce)
```

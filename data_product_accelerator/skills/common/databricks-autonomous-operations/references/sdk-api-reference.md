# Databricks SDK API Reference

Concise reference for all Databricks Python SDK APIs. For runnable examples, see `examples/` directory.

**SDK Docs:** https://databricks-sdk-py.readthedocs.io/en/latest/

---

## Authentication

```python
from databricks.sdk import WorkspaceClient, AccountClient

# Auto-detect from environment or ~/.databrickscfg
w = WorkspaceClient()

# Explicit token
w = WorkspaceClient(host="https://workspace.cloud.databricks.com", token="dapi...")

# Named profile
w = WorkspaceClient(profile="MY_PROFILE")

# Azure Service Principal
w = WorkspaceClient(
    host="https://adb-xxx.azuredatabricks.net",
    azure_workspace_resource_id="/subscriptions/.../providers/Microsoft.Databricks/workspaces/...",
    azure_tenant_id="...", azure_client_id="...", azure_client_secret="..."
)

# Account-level (users, workspaces, billing)
a = AccountClient(host="https://accounts.cloud.databricks.com", account_id="...", token="dapi...")
for workspace in a.workspaces.list(): print(workspace.workspace_name)

# In Databricks notebooks — auto-detected
w = WorkspaceClient()  # Works automatically with notebook context
```

---

## Clusters

```python
from databricks.sdk.service.compute import AutoScale
from datetime import timedelta

for c in w.clusters.list(): print(f"{c.cluster_name}: {c.state}")
cluster = w.clusters.get(cluster_id="...")

# Auto-select best Spark version and node type
spark_version = w.clusters.select_spark_version(latest=True, long_term_support=True)
node_type = w.clusters.select_node_type(local_disk=True, min_memory_gb=16)

# Create with autoscaling
w.clusters.create_and_wait(
    cluster_name="...", spark_version=spark_version, node_type_id=node_type,
    autoscale=AutoScale(min_workers=1, max_workers=4), timeout=timedelta(minutes=30)
)

# Ensure running (idempotent — starts if stopped, waits if starting)
w.clusters.ensure_cluster_is_running(cluster_id="...")
w.clusters.start(cluster_id="...").result()
w.clusters.stop(cluster_id="...")
w.clusters.delete(cluster_id="...")
```

---

## Jobs

```python
from databricks.sdk.service.jobs import Task, NotebookTask
from datetime import timedelta

for j in w.jobs.list(): print(f"{j.job_id}: {j.settings.name}")

# Run and wait (blocking)
run = w.jobs.run_now_and_wait(job_id=123, notebook_params={"date": "2024-01-01"}, timeout=timedelta(hours=1))
print(f"Result: {run.state.result_state}")

# Submit one-time run (no persistent job created)
run = w.jobs.submit_and_wait(
    run_name="one-time-analysis",
    tasks=[Task(task_key="main", existing_cluster_id="...", notebook_task=NotebookTask(notebook_path="/path"))],
    timeout=timedelta(hours=1)
)

# Get run output
output = w.jobs.get_run_output(run_id=run.run_id)
if output.notebook_output: print(f"Result: {output.notebook_output.result}")

# Get run status (for polling)
run = w.jobs.get_run(run_id=456)
print(f"Lifecycle: {run.state.life_cycle_state}, Result: {run.state.result_state}")

# Get task-level details from multi-task jobs
for task in run.tasks:
    if task.state.result_state == "FAILED":
        print(f"FAILED: {task.task_key} - {task.state.state_message}")
        task_output = w.jobs.get_run_output(run_id=task.run_id)  # MUST use task.run_id

# List recent runs, cancel
for r in w.jobs.list_runs(job_id=123, active_only=True): print(f"Run {r.run_id}: {r.state.life_cycle_state}")
w.jobs.cancel_run(run_id=456).result()
```

---

## SQL Statement Execution

```python
from databricks.sdk.service.sql import StatementState, StatementParameterListItem

response = w.statement_execution.execute_statement(
    warehouse_id="abc", statement="SELECT ...", wait_timeout="30s"
)
if response.status.state == StatementState.SUCCEEDED:
    columns = [col.name for col in response.manifest.schema.columns]
    for row in response.result.data_array: print(row)

# Parameterized queries (prevents SQL injection)
response = w.statement_execution.execute_statement(
    warehouse_id="abc",
    statement="SELECT * FROM users WHERE age > :min_age AND name = :name",
    parameters=[
        StatementParameterListItem(name="min_age", value="21", type="INT"),
        StatementParameterListItem(name="name", value="Alice", type="STRING"),
    ],
    wait_timeout="30s"
)

# Practical helper: query to pandas DataFrame
def query_to_dataframe(warehouse_id: str, sql: str):
    import pandas as pd
    resp = w.statement_execution.execute_statement(warehouse_id=warehouse_id, statement=sql, wait_timeout="300s")
    if resp.status.state != StatementState.SUCCEEDED:
        raise Exception(f"Query failed: {resp.status.error}")
    cols = [c.name for c in resp.manifest.schema.columns]
    return pd.DataFrame(resp.result.data_array, columns=cols)
```

---

## SQL Warehouses

```python
for wh in w.warehouses.list(): print(f"{wh.name}: {wh.state}")
w.warehouses.create_and_wait(name="wh", cluster_size="Small", max_num_clusters=1, auto_stop_mins=15)
w.warehouses.start(id="abc").result()
w.warehouses.stop(id="abc").result()
```

---

## Unity Catalog — Tables, Catalogs, Schemas

```python
for t in w.tables.list(catalog_name="main", schema_name="default"):
    print(f"{t.full_name}: {t.table_type}")
table = w.tables.get(full_name="main.default.my_table")
print(f"Columns: {[c.name for c in table.columns]}")

# Check table existence (useful for dependency validation)
exists = w.tables.exists(full_name="main.default.my_table")

# Fast table summaries with pattern matching
for s in w.tables.list_summaries(catalog_name="main", schema_name_pattern="*", table_name_pattern="fact_*"):
    print(f"{s.full_name}")

for cat in w.catalogs.list(): print(cat.name)
for schema in w.schemas.list(catalog_name="main"): print(schema.name)
```

---

## Volumes & Files

```python
w.files.upload(file_path="/Volumes/main/default/vol/data.csv", contents=open("f.csv", "rb"))
with w.files.download(file_path="/Volumes/main/default/vol/data.csv") as f: content = f.read()
for entry in w.files.list_directory_contents("/Volumes/main/default/vol/"): print(entry.name)
```

---

## Serving Endpoints

```python
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

for ep in w.serving_endpoints.list(): print(f"{ep.name}: {ep.state}")

# Create endpoint with UC model
w.serving_endpoints.create_and_wait(
    name="my-endpoint",
    config=EndpointCoreConfigInput(served_entities=[
        ServedEntityInput(entity_name="main.ml.model", entity_version="1",
                          workload_size="Small", scale_to_zero_enabled=True)
    ]),
    timeout=timedelta(minutes=30)
)

# Query: custom model, chat, or embeddings
response = w.serving_endpoints.query(name="ep", inputs=[{"feature": 1.0}])  # Custom
response = w.serving_endpoints.query(name="ep", messages=[{"role": "user", "content": "Hi"}])  # Chat
response = w.serving_endpoints.query(name="ep", input=["text to embed"])  # Embeddings

# OpenAI-compatible client
openai_client = w.serving_endpoints.get_open_ai_client()
logs = w.serving_endpoints.logs(name="ep", served_model_name="model-1")
```

---

## Vector Search

```python
import json

# Query with text and optional filters
results = w.vector_search_indexes.query_index(
    index_name="main.default.idx", columns=["id", "text"],
    query_text="query", num_results=10, filters_json='{"category": "ai"}'
)
for doc in results.result.data_array: print(f"Score: {doc[-1]}, Text: {doc[1][:100]}")

# Upsert to Direct Vector Access index
w.vector_search_indexes.upsert_data_vector_index(
    index_name="main.default.idx",
    inputs_json=json.dumps([{"id": "1", "text": "...", "embedding": [0.1, 0.2]}])
)

# Sync Delta Sync index
w.vector_search_indexes.sync_index(index_name="main.default.delta_sync_idx")
```

---

## Pipelines (DLT)

```python
for p in w.pipelines.list_pipelines(): print(f"{p.name}: {p.state}")
pipeline = w.pipelines.get(pipeline_id="abc")
w.pipelines.start_update(pipeline_id="abc")
w.pipelines.start_update(pipeline_id="abc", full_refresh=True)  # Full refresh
w.pipelines.stop_and_wait(pipeline_id="abc")
events = w.pipelines.list_pipeline_events(pipeline_id="abc")
```

---

## Lakehouse Monitors

```python
monitor = w.quality_monitors.get(table_name="catalog.schema.table")
print(f"Status: {monitor.status}, Last refresh: {monitor.last_refresh_time}")

# Delete and recreate (for ResourceAlreadyExists)
w.quality_monitors.delete(table_name="catalog.schema.table")

# Update (MUST include all custom_metrics — omitting deletes them)
w.quality_monitors.update(table_name="...", custom_metrics=[...])

# Trigger manual refresh
w.quality_monitors.run_refresh(table_name="...")
```

---

## SQL Alerts (V2)

```python
alert = w.alerts_v2.create_alert(alert=AlertV2(...))
w.alerts_v2.update_alert(
    id=alert_id, alert=alert,
    update_mask="display_name,query_text,warehouse_id,condition,notification,schedule"
)
w.alerts_v2.delete_alert(id=alert_id)
```

---

## Secrets

```python
w.secrets.create_scope(scope="my-scope")
w.secrets.put_secret(scope="my-scope", key="api-key", string_value="secret")
secret = w.secrets.get_secret(scope="my-scope", key="api-key")
```

---

## Common Patterns

### Async Applications (FastAPI, etc.)

The SDK is **fully synchronous**. In async apps, wrap with `asyncio.to_thread()`:
```python
import asyncio
async def get_clusters():
    return await asyncio.to_thread(lambda: list(w.clusters.list()))
```

### Wait for Long-Running Operations
```python
from datetime import timedelta
cluster = w.clusters.create_and_wait(cluster_name="...", timeout=timedelta(minutes=30))
# Or manual: wait = w.clusters.create(...); cluster = wait.result()
```

### Error Handling
```python
from databricks.sdk.errors import NotFound, PermissionDenied, ResourceAlreadyExists
try:
    cluster = w.clusters.get(cluster_id="invalid")
except NotFound: print("Not found")
except PermissionDenied: print("Access denied")
```

### Direct REST API Access
```python
response = w.api_client.do(method="GET", path="/api/2.0/clusters/list")
response = w.api_client.do(method="POST", path="/api/2.0/jobs/run-now", body={"job_id": 123})
```

---

## SDK Documentation URLs

| API | URL |
|-----|-----|
| Authentication | https://databricks-sdk-py.readthedocs.io/en/latest/authentication.html |
| Clusters | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/compute/clusters.html |
| Jobs | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/jobs/jobs.html |
| SQL Warehouses | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/sql/warehouses.html |
| Statement Execution | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/sql/statement_execution.html |
| Tables | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/catalog/tables.html |
| Volumes | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/catalog/volumes.html |
| Files | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/files/files.html |
| Serving Endpoints | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/serving/serving_endpoints.html |
| Vector Search | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/vectorsearch/vector_search_indexes.html |
| Pipelines | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/pipelines/pipelines.html |
| Secrets | https://databricks-sdk-py.readthedocs.io/en/latest/workspace/workspace/secrets.html |
| DBUtils | https://databricks-sdk-py.readthedocs.io/en/latest/dbutils.html |

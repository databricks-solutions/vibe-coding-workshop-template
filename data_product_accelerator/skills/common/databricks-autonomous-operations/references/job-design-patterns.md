# Job Design Best Practices for Monitorability

Patterns for writing notebooks and jobs that are easy for the autonomous agent to monitor, diagnose, and fix.

---

## Structured Output (Always)

Every notebook should exit with structured JSON so the agent can programmatically parse results:

```python
import json
dbutils.notebook.exit(json.dumps({
    "status": "SUCCESS",  # or "FAILED"
    "total_items": 25,
    "successful": 23,
    "failed": 2,
    "failed_items": ["item_a", "item_b"],
    "errors": {"item_a": "error message"}
}))
```

**Why:** `get-run-output` returns `notebook_output.result` as a string. JSON lets the agent parse it.

---

## Clear Progress Messages

Print step-numbered progress so the agent can identify where a failure occurred:

```python
print(f"[Step 1/4] Loading source table: {source_table}")
print(f"[Step 2/4] Processing {row_count:,} rows...")
print(f"[Step 3/4] Writing to Gold: {gold_table}")
print(f"[Step 4/4] Validating {constraint_count} constraints")
```

---

## Fail Fast with Descriptive Errors

Include actionable context in error messages — tell the agent what to do:

```python
if df.count() == 0:
    raise ValueError(f"Source table {source_table} is empty. Run bronze_setup_job first.")

if not spark.catalog.tableExists(f"{catalog}.{schema}.{table_name}"):
    raise ValueError(f"Table {catalog}.{schema}.{table_name} not found. Run gold_setup_job first.")
```

---

## 3-Layer Hierarchical Job Architecture

| Layer | Purpose | Task Type | Example |
|-------|---------|-----------|---------|
| **Layer 1: Atomic** | One notebook per job | `notebook_task` | `gold_setup_job` |
| **Layer 2: Composite** | Groups related atomics | `run_job_task` | `semantic_layer_setup_job` |
| **Layer 3: Orchestrator** | Full pipeline | `run_job_task` | `master_setup_orchestrator` |

**Rules:**
- Each notebook in exactly ONE atomic job (no duplication)
- Composite/Orchestrator jobs use `run_job_task` ONLY (never `notebook_task`)
- Job references: `${resources.jobs.<job_name>.id}`

---

## Partial Success Pattern

For jobs that process multiple items (e.g., creating 30 alerts, 8 monitors):

```python
import json

results = {"total": 0, "succeeded": 0, "failed": 0, "errors": {}}

for item in items:
    results["total"] += 1
    try:
        process(item)
        results["succeeded"] += 1
    except Exception as e:
        results["failed"] += 1
        results["errors"][item.name] = str(e)

results["status"] = "SUCCESS" if results["failed"] == 0 else "PARTIAL_SUCCESS"
dbutils.notebook.exit(json.dumps(results))
```

**Agent behavior:** ≥90% success = continue; fix failures individually.

---

## Parameter Validation

Validate all parameters at the start of the notebook:

```python
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# Validate early
if not catalog or not schema:
    raise ValueError(f"Required parameters missing: catalog={catalog}, schema={schema}")
```

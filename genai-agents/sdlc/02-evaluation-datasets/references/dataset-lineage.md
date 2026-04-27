# Dataset Lineage

Complete reference for tracking evaluation datasets through their lifecycle
using MLflow data lineage, UC Delta versioning, and experiment linkage.

---

## 1. MLflow data APIs

### `mlflow.data.from_pandas()`

Create an MLflow dataset entity from an in-memory pandas DataFrame. This is
the simplest way to log a dataset for lineage tracking when you already have
data in pandas.

```python
import mlflow
import pandas as pd

eval_df = pd.DataFrame([
    {
        "inputs": {"question": "Total cost?", "question_id": "q1"},
        "expectations": {"expected_response": "SELECT SUM(cost) FROM billing"},
    },
    {
        "inputs": {"question": "Active jobs?", "question_id": "q2"},
        "expectations": {"expected_response": "SELECT * FROM jobs WHERE status='ACTIVE'"},
    },
])

dataset = mlflow.data.from_pandas(
    eval_df,
    name="genie_benchmarks_billing",
    source="main.genie_optimization.genie_benchmarks_billing",
)
```

Key parameters:

| Parameter | Type | Description |
| --- | --- | --- |
| `df` | `pd.DataFrame` | The dataframe to wrap |
| `name` | `str` | Human-readable dataset name (appears in experiment UI) |
| `source` | `str` | Origin of the data (e.g. UC table path) |

### `mlflow.data.from_spark()`

Create an MLflow dataset entity directly from a Spark DataFrame. Preferred
when data lives in UC Delta tables to preserve the source link.

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
spark_df = spark.table("main.genie_optimization.genie_benchmarks_billing")

dataset = mlflow.data.from_spark(
    spark_df,
    name="genie_benchmarks_billing",
    path="main.genie_optimization.genie_benchmarks_billing",
)
```

Key parameters:

| Parameter | Type | Description |
| --- | --- | --- |
| `df` | `pyspark.sql.DataFrame` | The Spark DataFrame |
| `name` | `str` | Dataset name |
| `path` | `str` | UC table path for lineage tracking |

---

## 2. Logging datasets to runs

### `mlflow.log_input()`

Attach a dataset entity to an MLflow run with a context label. The context
parameter distinguishes how the dataset was used in that run.

```python
with mlflow.start_run(run_name="baseline_eval") as run:
    mlflow.log_input(dataset, context="evaluation")

    mlflow.log_param("benchmark_count", len(eval_df))
    mlflow.log_param("dataset", "main.genie_optimization.genie_benchmarks_billing")

    # ... run evaluation ...
```

Common `context` values:

| Context | Meaning |
| --- | --- |
| `"evaluation"` | Dataset used as evaluation benchmarks |
| `"training"` | Dataset used for fine-tuning or few-shot examples |
| `"validation"` | Dataset used for validation / held-out checks |
| `"generation_seed"` | Seed questions used to generate more benchmarks |

### Logging in the codebase

`run_evaluation()` in `evaluation.py` logs dataset lineage through params:

```python
mlflow.log_params({
    "dataset": uc_table_name,
    "benchmark_count": len(benchmarks),
    "eval_scope": eval_scope,
    "space_id": space_id,
    "domain": domain,
})
```

Quarantine artifacts are also tracked:

```python
mlflow.log_dict(
    {"quarantined": quarantined_benchmarks, "reason_counts": reason_counts},
    artifact_file="evaluation_runtime/benchmark_precheck.json",
)
```

---

## 3. GenAI datasets (this repository)

The codebase uses the `mlflow.genai.datasets` API rather than the classic
`mlflow.data` API. This provides:

- **UC-backed storage** — datasets are Delta tables managed by MLflow
- **Merge semantics** — `merge_records()` upserts by question_id
- **Experiment linkage** — pass `experiment_id` at creation time

### Create or get

```python
import mlflow

uc_table_name = f"{uc_schema}.genie_benchmarks_{domain}"

try:
    eval_dataset = mlflow.genai.datasets.get_dataset(name=uc_table_name)
except Exception:
    eval_dataset = mlflow.genai.datasets.create_dataset(
        name=uc_table_name,
        experiment_id=[experiment_id],  # links to experiment's Datasets tab
    )
```

### Merge records

```python
records = [
    {
        "inputs": {"question_id": "q1", "question": "Total cost?", ...},
        "expectations": {"expected_response": "SELECT SUM(cost) FROM billing", ...},
    },
]
eval_dataset.merge_records(records)
```

`merge_records` is an upsert — it inserts new rows and updates existing ones.
It does **not** delete rows absent from the batch.

---

## 4. Tracking dataset → evaluation run lineage

### Which datasets were used in which runs

Query MLflow to find all runs that consumed a specific dataset:

```python
import mlflow

runs = mlflow.search_runs(
    experiment_ids=[experiment_id],
    filter_string=f"params.dataset = '{uc_table_name}'",
    order_by=["start_time DESC"],
)
```

### Linking runs to dataset versions

Each evaluation run logs `benchmark_count` and `dataset` as params. Combine
with Delta table versioning for full reproducibility:

```python
spark.sql(f"DESCRIBE HISTORY {uc_table_name}").show()
```

### Complete lineage chain

```text
Delta table version N
  ↓ (load_benchmarks_from_dataset)
Benchmarks in memory
  ↓ (_precheck_benchmarks_for_eval → quarantine)
Evaluable benchmarks
  ↓ (mlflow.genai.evaluate)
Evaluation run R
  ├── params: dataset, benchmark_count, eval_scope
  ├── artifacts: benchmark_precheck.json (quarantine details)
  ├── metrics: per-judge scores
  └── tags: genie.space_id, genie.domain, genie.iteration
```

---

## 5. Delta table versioning for reproducibility

### Table naming convention

```text
{catalog}.{schema}.genie_benchmarks_{domain}
```

Examples:
- `main.genie_optimization.genie_benchmarks_billing`
- `main.genie_optimization.genie_benchmarks_hr`

### Version history

Delta tables automatically track versions. Use `DESCRIBE HISTORY` to see
when records were merged or the table was recreated:

```python
history = spark.sql(f"DESCRIBE HISTORY {uc_table_name}")
history.select("version", "timestamp", "operation", "operationMetrics").show(10)
```

### Time-travel reads

Reproduce an evaluation by reading the exact dataset version:

```python
df_v3 = spark.read.option("versionAsOf", 3).table(uc_table_name)

df_at_time = spark.read.option("timestampAsOf", "2026-03-25T10:00:00").table(uc_table_name)
```

### Pinning dataset version in evaluation runs

Log the Delta version alongside the run for exact reproducibility:

```python
version_df = spark.sql(f"DESCRIBE HISTORY {uc_table_name} LIMIT 1")
current_version = version_df.collect()[0]["version"]

with mlflow.start_run():
    mlflow.log_param("dataset_delta_version", current_version)
    mlflow.log_param("dataset", uc_table_name)
    # ... run evaluation ...
```

---

## 6. Complete workflow

End-to-end flow from dataset creation through evaluation and trace-back.

```python
import mlflow
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
uc_schema = "main.genie_optimization"
domain = "billing"
uc_table_name = f"{uc_schema}.genie_benchmarks_{domain}"

# ── Step 1: Create dataset ─────────────────────────────────────────
eval_dataset = mlflow.genai.datasets.create_dataset(
    name=uc_table_name,
    experiment_id=[experiment_id],
)
eval_dataset.merge_records(records)

# ── Step 2: Log dataset to evaluation run ──────────────────────────
version_df = spark.sql(f"DESCRIBE HISTORY {uc_table_name} LIMIT 1")
delta_version = version_df.collect()[0]["version"]

with mlflow.start_run(run_name="baseline_eval") as run:
    mlflow.log_params({
        "dataset": uc_table_name,
        "dataset_delta_version": delta_version,
        "benchmark_count": len(records),
    })

    # ── Step 3: Evaluate ───────────────────────────────────────────
    result = mlflow.genai.evaluate(
        data=eval_df,
        predict_fn=predict_fn,
        scorers=scorers,
    )

# ── Step 4: Trace back to dataset version ──────────────────────────
run_data = mlflow.get_run(run.info.run_id)
logged_version = run_data.data.params.get("dataset_delta_version")
logged_table = run_data.data.params.get("dataset")

reproduced_df = spark.read.option("versionAsOf", logged_version).table(logged_table)
```

---

## 7. Common lineage mistakes

| Mistake | Consequence | Fix |
| --- | --- | --- |
| Not logging `dataset` param on evaluation runs | Cannot trace which benchmarks produced scores | Always log `mlflow.log_param("dataset", uc_table_name)` |
| Logging pandas dataset without `source` | Lineage shows no UC connection | Use `source=uc_table_name` in `from_pandas()` |
| Reading table without refresh after upstream write | Stale data or `DELTA_SCHEMA_CHANGE_SINCE_ANALYSIS` | `REFRESH TABLE` + retry (see `load_benchmarks_from_dataset`) |
| Not pinning Delta version | Cannot reproduce evaluation exactly | Log `dataset_delta_version` param |
| Using `create_dataset` when table exists | Creates duplicate or overwrites | `get_dataset` first, fall back to `create_dataset` |

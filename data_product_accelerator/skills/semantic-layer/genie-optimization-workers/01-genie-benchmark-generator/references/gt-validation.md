# Ground Truth Validation & MLflow Dataset Sync

Functions for validating ground truth SQL, syncing benchmarks to MLflow Evaluation Datasets, and auto-populating metadata dependencies. Extracted from the optimization code patterns for standalone use by the Generator worker.

---

## Ground Truth Validation

Every ground truth SQL must be executed on the warehouse before acceptance into the benchmark. This prevents "chasing wrong ground truth" — optimizing metadata toward incorrect SQL wastes iterations.

```python
import hashlib
import json

def validate_ground_truth_sql(sql: str, spark) -> dict:
    """Execute ground truth SQL and return validation result with hash.

    Args:
        sql: The ground truth SQL to validate.
        spark: Active Spark session (Databricks global).

    Returns:
        dict with keys: valid, result_hash, result_sample, row_count, error
    """
    try:
        df = spark.sql(sql)
        pdf = df.toPandas()
        row_count = len(pdf)

        result_bytes = pdf.to_csv(index=False).encode("utf-8")
        result_hash = hashlib.md5(result_bytes).hexdigest()

        sample_rows = pdf.head(5).to_dict(orient="records")
        result_sample = json.dumps(sample_rows, default=str)

        return {
            "valid": True,
            "result_hash": result_hash,
            "result_sample": result_sample,
            "row_count": row_count,
            "error": None,
        }
    except Exception as e:
        return {
            "valid": False,
            "result_hash": None,
            "result_sample": None,
            "row_count": 0,
            "error": str(e),
        }


def validate_with_retry(sql: str, spark, llm_regenerate_fn=None, max_attempts: int = 3) -> dict:
    """Validate GT SQL with LLM regeneration on failure.

    Args:
        sql: Initial ground truth SQL.
        spark: Active Spark session.
        llm_regenerate_fn: Optional callable(sql, error) -> new_sql.
        max_attempts: Max regeneration attempts.
    """
    current_sql = sql
    for attempt in range(max_attempts):
        result = validate_ground_truth_sql(current_sql, spark)
        if result["valid"]:
            result["final_sql"] = current_sql
            result["attempts"] = attempt + 1
            return result
        if llm_regenerate_fn and attempt < max_attempts - 1:
            current_sql = llm_regenerate_fn(current_sql, result["error"])
        else:
            break
    result["final_sql"] = current_sql
    result["attempts"] = max_attempts
    return result
```

### Validation Flow

```
expected_sql → spark.sql(sql) → success?
├── YES → store result_hash, result_sample, row_count → accept
└── NO  → LLM regenerates SQL (max 3 attempts)
          ├── attempt 2 succeeds → store results → accept
          ├── attempt 3 succeeds → store results → accept
          └── all 3 fail → flag for human review
```

### What Gets Stored

| Field | Type | Description |
|-------|------|-------------|
| `expected_result_hash` | MD5 string | Hash of the result DataFrame (CSV bytes) |
| `expected_result_sample` | JSON string | First 5 rows as JSON for quick comparison |
| `expected_row_count` | integer | Total row count for structural checks |

---

## MLflow Dataset Sync

After saving benchmarks to YAML, sync to the MLflow Evaluation Dataset for programmatic evaluation.

```python
import mlflow
import yaml

def sync_yaml_to_mlflow_dataset(yaml_path: str, uc_schema: str, domain: str) -> str:
    """Sync golden-queries.yaml to an MLflow Evaluation Dataset in Unity Catalog.

    Args:
        yaml_path: Path to golden-queries.yaml.
        uc_schema: Unity Catalog schema (e.g., "catalog.schema").
        domain: Domain key in the YAML (e.g., "cost").

    Returns:
        Dataset name string.
    """
    with open(yaml_path) as f:
        all_benchmarks = yaml.safe_load(f)

    questions = all_benchmarks.get(domain, all_benchmarks.get("benchmarks", []))
    records = []
    for q in questions:
        records.append({
            "inputs": {
                "question": q["question"],
                "space_id": q.get("space_id", ""),
                "category": q.get("category", ""),
            },
            "expectations": {
                "expected_response": q.get("expected_sql", ""),
                "expected_facts": q.get("expected_facts", []),
                "guidelines": q.get("guidelines", ""),
                "expected_result_hash": q.get("expected_result_hash", ""),
                "expected_result_sample": q.get("expected_result_sample", ""),
                "expected_row_count": q.get("expected_row_count", 0),
                "required_tables": q.get("required_tables", []),
                "required_columns": q.get("required_columns", []),
                "required_joins": q.get("required_joins", []),
                "required_business_logic": q.get("required_business_logic", []),
                "expected_asset": q.get("expected_asset", ""),
                "category": q.get("category", ""),
            },
        })

    dataset_name = f"{uc_schema}.genie_benchmarks_{domain}"
    dataset = mlflow.genai.datasets.create_dataset(
        uc_table_name=dataset_name,
        records=records,
    )
    return dataset_name
```

### YAML → MLflow Field Mapping

| YAML Field | MLflow Field | Required |
|------------|-------------|----------|
| `question` | `inputs.question` | Yes |
| `expected_sql` | `expectations.expected_response` | Yes |
| `expected_asset` | `expectations.expected_asset` | Yes |
| `category` | `expectations.category` | Yes |
| `expected_facts` | `expectations.expected_facts` | No |
| `expected_result_hash` | `expectations.expected_result_hash` | No (auto-populated) |
| `expected_result_sample` | `expectations.expected_result_sample` | No (auto-populated) |
| `expected_row_count` | `expectations.expected_row_count` | No (auto-populated) |

### MLflow Dataset Limits

- Max **2,000 rows** per dataset
- Max **20 expectations** per record
- Requires `CREATE TABLE` permission in Unity Catalog

---

## Auto-Populate Metadata Dependencies

Extract `required_tables`, `required_columns`, and `required_joins` from `expected_sql` during benchmark intake:

```python
import re

def extract_dependencies(expected_sql: str) -> dict:
    """Parse expected_sql to extract table/column references."""
    sql_lower = expected_sql.lower()
    tables = re.findall(r'from\s+([\w.]+)', sql_lower) + re.findall(r'join\s+([\w.]+)', sql_lower)
    return {
        "required_tables": list(set(t.split(".")[-1] for t in tables)),
        "required_columns": [],
        "required_joins": [],
    }
```

These fields enable the introspection engine (Optimizer worker) to identify which control lever changes will affect which questions.

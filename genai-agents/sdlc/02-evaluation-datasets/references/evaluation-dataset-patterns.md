# Evaluation Dataset Patterns

Complete reference for evaluation dataset design, schema, construction, validation,
and persistence. Grounded in `create_evaluation_dataset()` and
`load_benchmarks_from_dataset()` in `evaluation.py`.

---

## 1. EvaluationRecord dataclass

The canonical in-memory shape for a single evaluation row. The dataclass enforces
required fields and provides validation before persistence to UC Delta.

```python
from dataclasses import dataclass, field, asdict
from typing import Any
import hashlib
import json


@dataclass
class EvaluationRecord:
    """Single evaluation benchmark ready for mlflow.genai.evaluate().

    `inputs` keys must match the predict_fn signature (Skill 09).
    `expectations` carry ground-truth and lineage metadata for judges.
    """

    # ── inputs (unpacked as kwargs to predict_fn) ───────────────
    question_id: str
    question: str
    space_id: str = ""
    expected_sql: str = ""
    catalog: str = ""
    gold_schema: str = ""

    # ── expectations (consumed by judges / scorers) ─────────────
    expected_response: str = ""          # mirrors expected_sql for judges
    expected_asset: str = "TABLE"        # TABLE | MV | FUNCTION | INSTRUCTION
    category: str = ""                   # aggregation, ranking, etc.
    source: str = ""                     # genie_space | llm_generated | manual
    provenance: str = ""                 # curated | synthetic | auto_corrected
    validation_status: str = "pending"   # valid | invalid | pending | question_only
    validation_reason_code: str = ""     # ok | unknown_asset | unknown_column | ...
    validation_error: str | None = None
    correction_source: str = ""          # metadata_suggestion | llm_correction | ...
    required_tables: list[str] = field(default_factory=list)
    required_columns: list[str] = field(default_factory=list)
    expected_facts: list[str] = field(default_factory=list)
    temporal_stale: bool = False
    asset_fingerprint: str = ""
    split: str = "train"                 # train | held_out

    # ── validation ──────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        if not self.question.strip():
            errors.append("question is empty")
        if not self.question_id.strip():
            errors.append("question_id is empty")
        if self.split not in ("train", "held_out", "test", ""):
            errors.append(f"invalid split: {self.split}")
        if self.validation_status not in ("valid", "invalid", "pending", "question_only"):
            errors.append(f"invalid validation_status: {self.validation_status}")
        if self.expected_sql and not self.expected_response:
            errors.append("expected_sql set but expected_response is empty (mirror it)")
        return errors

    # ── serialization ───────────────────────────────────────────

    def to_eval_row(self) -> dict[str, Any]:
        """Convert to the nested {inputs, expectations} shape for evaluate()."""
        return {
            "inputs": {
                "question_id": self.question_id,
                "question": self.question,
                "space_id": self.space_id,
                "expected_sql": self.expected_sql,
                "catalog": self.catalog,
                "gold_schema": self.gold_schema,
            },
            "expectations": {
                k: v for k, v in {
                    "expected_response": self.expected_response,
                    "expected_asset": self.expected_asset,
                    "category": self.category,
                    "source": self.source,
                    "provenance": self.provenance,
                    "validation_status": self.validation_status,
                    "validation_reason_code": self.validation_reason_code,
                    "validation_error": self.validation_error,
                    "correction_source": self.correction_source,
                    "required_tables": self.required_tables,
                    "required_columns": self.required_columns,
                    "temporal_stale": self.temporal_stale,
                    "asset_fingerprint": self.asset_fingerprint,
                    "split": self.split,
                }.items() if v is not None
            },
        }

    def dedup_key(self) -> str:
        """Normalized question text for deduplication."""
        return self.question.strip().lower()

    def content_hash(self) -> str:
        """SHA-256 of question + expected_sql for change detection."""
        payload = f"{self.question.strip().lower()}|{self.expected_sql.strip()}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @classmethod
    def from_benchmark_dict(cls, b: dict, space_id: str = "", catalog: str = "", gold_schema: str = "") -> "EvaluationRecord":
        """Construct from the flat benchmark dict used throughout evaluation.py."""
        expected_sql = b.get("expected_sql", "")
        return cls(
            question_id=b.get("id", b.get("question_id", "")),
            question=b.get("question", ""),
            space_id=space_id,
            expected_sql=expected_sql,
            catalog=catalog,
            gold_schema=gold_schema,
            expected_response=expected_sql,
            expected_asset=b.get("expected_asset", "TABLE"),
            category=b.get("category", ""),
            source=b.get("source", ""),
            provenance=b.get("provenance", ""),
            validation_status=b.get("validation_status", "pending"),
            validation_reason_code=b.get("validation_reason_code", ""),
            validation_error=b.get("validation_error"),
            correction_source=b.get("correction_source", ""),
            required_tables=b.get("required_tables", []),
            required_columns=b.get("required_columns", []),
            expected_facts=b.get("expected_facts", []),
            temporal_stale=b.get("temporal_stale", False),
            asset_fingerprint=b.get("asset_fingerprint", ""),
            split=b.get("split", "train"),
        )
```

---

## 2. Schema specification

### inputs dict

Keys in `inputs` are unpacked as keyword arguments to `predict_fn` by
`mlflow.genai.evaluate()`. Every key must match the predictor's parameter list.

| Key | Type | Required | Description |
| --- | --- | --- | --- |
| `question_id` | `str` | Yes | Unique identifier for this benchmark |
| `question` | `str` | Yes | Natural-language question sent to Genie |
| `space_id` | `str` | No | Genie Space ID (bound by closure in predict_fn) |
| `expected_sql` | `str` | Recommended | Ground-truth SQL for comparison judges |
| `catalog` | `str` | No | UC catalog context |
| `gold_schema` | `str` | No | UC schema context |

### expectations dict

Consumed by judges and scorers. Not unpacked into predict_fn.

| Key | Type | Description |
| --- | --- | --- |
| `expected_response` | `str` | Ground-truth SQL (mirrors `inputs.expected_sql`) |
| `expected_asset` | `str` | `TABLE`, `MV`, `FUNCTION`, `INSTRUCTION` |
| `category` | `str` | Benchmark category from `BENCHMARK_CATEGORIES` |
| `source` | `str` | `genie_space`, `llm_generated`, `manual` |
| `provenance` | `str` | `curated`, `synthetic`, `auto_corrected`, `curated_sql_generated` |
| `validation_status` | `str` | `valid`, `invalid`, `pending`, `question_only` |
| `validation_reason_code` | `str` | `ok`, `unknown_asset`, `unknown_column`, `permission_blocked`, ... |
| `validation_error` | `str?` | Error message when validation failed |
| `correction_source` | `str` | How invalid SQL was fixed |
| `required_tables` | `list[str]` | Tables the SQL must reference |
| `required_columns` | `list[str]` | Columns the SQL must reference |
| `temporal_stale` | `bool` | Flagged by `_flag_stale_temporal_benchmarks` |
| `asset_fingerprint` | `str` | Content hash for change detection |
| `split` | `str` | `train` or `held_out` for scoped evaluation |

---

## 3. Domain-specific record patterns

### SQL evaluation (this repository)

Standard pattern for Genie Space SQL benchmarks:

```python
record = EvaluationRecord(
    question_id="billing_001",
    question="What is the total DBU cost by workspace?",
    space_id="abc123",
    expected_sql="SELECT workspace_id, SUM(dbu_cost) FROM billing GROUP BY 1",
    catalog="main",
    gold_schema="billing_gold",
    expected_response="SELECT workspace_id, SUM(dbu_cost) FROM billing GROUP BY 1",
    expected_asset="TABLE",
    category="aggregation",
    source="llm_generated",
    provenance="synthetic",
    validation_status="valid",
    split="train",
)
```

### RAG evaluation (generic pattern)

For retrieval-augmented generation agents, swap SQL fields for retrieval context:

```python
rag_record = {
    "inputs": {
        "question": "What is the refund policy?",
        "context_docs": ["doc1.md", "doc2.md"],
    },
    "expectations": {
        "expected_response": "Refunds are available within 30 days...",
        "source_documents": ["doc1.md"],
        "relevance_label": "high",
    },
}
```

### Multi-turn evaluation (generic pattern)

For conversational agents, include conversation history:

```python
multi_turn_record = {
    "inputs": {
        "question": "Now filter that by last month",
        "conversation_history": [
            {"role": "user", "content": "Show me all active jobs"},
            {"role": "assistant", "content": "SELECT * FROM jobs WHERE status = 'ACTIVE'"},
        ],
    },
    "expectations": {
        "expected_response": "SELECT * FROM jobs WHERE status = 'ACTIVE' AND created_at >= ...",
    },
}
```

---

## 4. Dataset split strategies

### Train / held-out / test

| Split | Purpose | Typical ratio |
| --- | --- | --- |
| `train` | Benchmarks used for optimization lever evaluation | 70-80% |
| `held_out` | Withheld from optimization; used for regression gates | 15-20% |
| `test` | Final validation before promotion (if separate from held_out) | 5-10% |

### Per-domain balance

Ensure each `BENCHMARK_CATEGORIES` value has representation in each split.
The codebase uses these categories:

```python
BENCHMARK_CATEGORIES = [
    "aggregation", "ranking", "time-series", "comparison",
    "detail", "list", "threshold", "multi-table",
]
```

When assigning splits, stratify by category to avoid entire categories missing
from the held-out set:

```python
import random

def assign_splits(records: list[EvaluationRecord], held_out_ratio: float = 0.2) -> None:
    by_category: dict[str, list[EvaluationRecord]] = {}
    for r in records:
        by_category.setdefault(r.category or "other", []).append(r)

    for cat, cat_records in by_category.items():
        random.shuffle(cat_records)
        n_held = max(1, int(len(cat_records) * held_out_ratio))
        for r in cat_records[:n_held]:
            r.split = "held_out"
        for r in cat_records[n_held:]:
            r.split = "train"
```

### Provenance balance

Track the ratio of `curated` vs `synthetic` vs `auto_corrected` benchmarks.
A healthy dataset has at least 20% curated (from real Genie Space conversations)
to anchor evaluation in real user behavior.

---

## 5. Deduplication and merge patterns

### In-memory deduplication

Both `create_evaluation_dataset()` and `load_benchmarks_from_dataset()` deduplicate
by normalized question text (lowercase, stripped):

```python
def deduplicate_records(records: list[EvaluationRecord]) -> list[EvaluationRecord]:
    seen: set[str] = set()
    deduped: list[EvaluationRecord] = []
    for r in records:
        key = r.dedup_key()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped
```

### MLflow GenAI dataset merge (upsert)

`create_evaluation_dataset()` uses `eval_dataset.merge_records(records)` which
performs upsert semantics on the backing UC Delta table. This preserves version
history rather than dropping and recreating.

**Merge does not delete old rows whose keys are absent from the new batch.**
To remove stale records, either:

1. Drop the table first (`_drop_benchmark_table`) and re-merge, or
2. Deduplicate in memory before merging (what `run_evaluation()` does)

### Cross-session merge

When combining benchmarks from multiple generation sessions:

```python
def merge_benchmark_sets(*sets: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for benchmark_set in sets:
        for b in benchmark_set:
            key = b.get("question", "").strip().lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(b)
    return merged
```

---

## 6. Dataset quality checks

### Schema validation

Verify every record conforms to the expected shape before persistence:

```python
def validate_dataset(records: list[EvaluationRecord]) -> tuple[list[EvaluationRecord], list[dict]]:
    """Validate all records. Returns (valid, errors)."""
    valid: list[EvaluationRecord] = []
    errors: list[dict] = []
    for r in records:
        issues = r.validate()
        if issues:
            errors.append({"question_id": r.question_id, "issues": issues})
        else:
            valid.append(r)
    return valid, errors
```

### SQL execution validation

Run `EXPLAIN` against every ground-truth SQL to catch schema drift, permission
issues, and syntax errors before they poison evaluation scores:

```python
def validate_sql_expectations(
    records: list[EvaluationRecord],
    spark: "SparkSession",
) -> tuple[list[EvaluationRecord], list[dict]]:
    """Validate expected_sql via EXPLAIN. Returns (valid, quarantined)."""
    valid: list[EvaluationRecord] = []
    quarantined: list[dict] = []
    for r in records:
        if not r.expected_sql:
            valid.append(r)
            continue
        try:
            spark.sql(f"EXPLAIN {r.expected_sql}")
            valid.append(r)
        except Exception as exc:
            quarantined.append({
                "question_id": r.question_id,
                "reason": "sql_validation_failed",
                "error": str(exc)[:500],
            })
    return valid, quarantined
```

### Content quality checks

```python
def check_dataset_quality(records: list[EvaluationRecord]) -> dict:
    """Compute quality metrics for the dataset."""
    total = len(records)
    if not total:
        return {"total": 0, "healthy": False}

    by_provenance = {}
    by_category = {}
    by_split = {}
    valid_count = 0

    for r in records:
        by_provenance[r.provenance] = by_provenance.get(r.provenance, 0) + 1
        by_category[r.category] = by_category.get(r.category, 0) + 1
        by_split[r.split] = by_split.get(r.split, 0) + 1
        if r.validation_status == "valid":
            valid_count += 1

    curated_ratio = by_provenance.get("curated", 0) / total
    valid_ratio = valid_count / total
    category_coverage = len(by_category) / len(BENCHMARK_CATEGORIES)

    return {
        "total": total,
        "valid_ratio": valid_ratio,
        "curated_ratio": curated_ratio,
        "category_coverage": category_coverage,
        "by_provenance": by_provenance,
        "by_category": by_category,
        "by_split": by_split,
        "healthy": valid_ratio >= 0.8 and category_coverage >= 0.5,
    }

BENCHMARK_CATEGORIES = [
    "aggregation", "ranking", "time-series", "comparison",
    "detail", "list", "threshold", "multi-table",
]
```

---

## 7. DatasetBuilder class

Full builder for constructing, validating, and persisting evaluation datasets.

```python
from typing import Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Incrementally build an evaluation dataset with validation."""

    def __init__(self, space_id: str = "", catalog: str = "", gold_schema: str = ""):
        self.space_id = space_id
        self.catalog = catalog
        self.gold_schema = gold_schema
        self._records: list[EvaluationRecord] = []
        self._seen: set[str] = set()

    def add_record(self, record: EvaluationRecord) -> bool:
        """Add a single record. Returns False if duplicate."""
        key = record.dedup_key()
        if key in self._seen:
            return False
        self._seen.add(key)
        self._records.append(record)
        return True

    def add_benchmark(self, benchmark: dict) -> bool:
        """Add from a flat benchmark dict (as used in evaluation.py)."""
        record = EvaluationRecord.from_benchmark_dict(
            benchmark,
            space_id=self.space_id,
            catalog=self.catalog,
            gold_schema=self.gold_schema,
        )
        return self.add_record(record)

    def add_benchmarks(self, benchmarks: list[dict]) -> int:
        """Add multiple benchmarks. Returns count of new records added."""
        return sum(1 for b in benchmarks if self.add_benchmark(b))

    def validate_all(self) -> tuple[int, list[dict]]:
        """Validate all records. Returns (valid_count, error_list)."""
        errors: list[dict] = []
        valid = 0
        for r in self._records:
            issues = r.validate()
            if issues:
                errors.append({"question_id": r.question_id, "issues": issues})
            else:
                valid += 1
        return valid, errors

    def to_pandas(self) -> pd.DataFrame:
        """Export as pandas DataFrame in {inputs, expectations} shape."""
        return pd.DataFrame([r.to_eval_row() for r in self._records])

    def to_eval_rows(self) -> list[dict[str, Any]]:
        """Export as list of {inputs, expectations} dicts."""
        return [r.to_eval_row() for r in self._records]

    def export_to_delta(
        self,
        spark: "SparkSession",
        uc_schema: str,
        domain: str,
        experiment_id: str = "",
    ) -> Any:
        """Persist to UC Delta via mlflow.genai.datasets (same as create_evaluation_dataset)."""
        import mlflow

        uc_table_name = f"{uc_schema}.genie_benchmarks_{domain}"
        try:
            eval_dataset = mlflow.genai.datasets.get_dataset(name=uc_table_name)
        except Exception:
            create_kwargs: dict[str, Any] = {"name": uc_table_name}
            if experiment_id:
                create_kwargs["experiment_id"] = [experiment_id]
            eval_dataset = mlflow.genai.datasets.create_dataset(**create_kwargs)

        records = self.to_eval_rows()
        eval_dataset.merge_records(records)
        logger.info("Exported %d records to %s", len(records), uc_table_name)
        return eval_dataset

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def records(self) -> list[EvaluationRecord]:
        return list(self._records)

    def quality_report(self) -> dict:
        """Compute quality metrics for the current dataset."""
        return check_dataset_quality(self._records)
```

---

## 8. Loading from UC Delta tables

The codebase's `load_benchmarks_from_dataset()` (evaluation.py line ~6090) handles:

1. **Table existence check** — `SHOW TABLES ... LIKE` before attempting reads
2. **REFRESH + retry** — handles `DELTA_SCHEMA_CHANGE_SINCE_ANALYSIS` with
   exponential backoff (5s × attempt)
3. **JSON parsing** — `inputs` and `expectations` columns may be stored as
   JSON strings rather than struct columns
4. **Reconstruction** — extracts `expected_sql` from either `inputs.expected_sql`
   or `expectations.expected_response`
5. **Deduplication** — drops duplicate questions by normalized text

```python
def load_into_builder(
    spark: "SparkSession",
    uc_schema: str,
    domain: str,
    space_id: str = "",
) -> DatasetBuilder:
    """Load existing benchmarks from UC Delta into a DatasetBuilder."""
    from genie_space_optimizer.optimization.evaluation import load_benchmarks_from_dataset

    benchmarks = load_benchmarks_from_dataset(spark, uc_schema, domain)
    builder = DatasetBuilder(space_id=space_id)
    builder.add_benchmarks(benchmarks)
    return builder
```

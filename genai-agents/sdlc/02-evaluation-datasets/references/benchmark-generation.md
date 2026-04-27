# Benchmark Generation

Complete reference for generating, validating, correcting, and tracking
evaluation benchmarks. Grounded in `generate_benchmarks()` and
`_precheck_benchmarks_for_eval()` in `evaluation.py`.

---

## 1. Extracting Q&A pairs from Genie Space conversations

Mine real user interactions from Genie Space history to seed your benchmark
dataset with authentic questions.

### Genie conversation structure

Each Genie Space conversation contains:

- **User question** — natural-language query
- **Assistant response** — may include generated SQL, an explanation, or both
- **Result data** — output of the executed SQL (when available)

### Extraction pattern

```python
from databricks.sdk import WorkspaceClient


def extract_genie_qa_pairs(
    w: WorkspaceClient,
    space_id: str,
) -> list[dict]:
    """Extract question + SQL pairs from Genie Space conversation history.

    Returns flat benchmark dicts compatible with generate_benchmarks() input.
    """
    conversations = w.genie.list_conversations(space_id=space_id)
    pairs: list[dict] = []

    for conv in conversations:
        messages = w.genie.list_messages(space_id=space_id, conversation_id=conv.id)
        current_question: str | None = None

        for msg in messages:
            if msg.role == "USER":
                current_question = msg.content
            elif msg.role == "ASSISTANT" and current_question:
                sql = _extract_sql_from_response(msg)
                if sql:
                    pairs.append({
                        "question": current_question,
                        "expected_sql": sql,
                        "source": "genie_space",
                        "provenance": "curated",
                        "conversation_id": conv.id,
                    })
                current_question = None

    return pairs


def _extract_sql_from_response(msg) -> str | None:
    """Pull SQL from a Genie assistant message's attachments."""
    if not hasattr(msg, "attachments"):
        return None
    for attachment in msg.attachments or []:
        if hasattr(attachment, "query") and attachment.query:
            query = attachment.query
            if hasattr(query, "query"):
                return query.query
    return None
```

### Mapping to benchmark shape

Extracted pairs must go through the same validation pipeline as synthetic
benchmarks. Do not skip SQL validation.

```python
extracted = extract_genie_qa_pairs(w, space_id)

for b in extracted:
    b["expected_asset"] = detect_asset_type(b["expected_sql"])
    b["category"] = classify_question_category(b["question"])
    b["validation_status"] = "pending"
```

---

## 2. LLM-assisted benchmark generation

The `generate_benchmarks()` function (evaluation.py line ~5574) implements the
full LLM-based generation pipeline.

### Pipeline stages

```text
1. Seed               ← curated Genie Space benchmarks + existing_benchmarks
2. Gap calculation    ← target_count - len(curated) - len(existing)
3. Context building   ← Genie config + UC columns + routines + metric views
4. LLM generation     ← BENCHMARK_GENERATION_PROMPT with schema context
5. Metadata enforce   ← _enforce_metadata_constraints (assets, columns, routines)
6. Field-drift fix    ← _apply_metadata_field_drift_corrections (deterministic)
7. SQL validation     ← EXPLAIN + table existence via Spark or warehouse
8. MV guards          ← reject SELECT * on metric views, wrap MEASURE()
9. Correction rounds  ← LLM-based correction with bounded retries
10. Alignment check   ← question-SQL semantic alignment via LLM
11. Coverage gap-fill ← ensure every asset has at least one benchmark
12. Provenance labels ← synthetic, auto_corrected, curated, etc.
```

### Seed questions

```python
curated = genie_space_benchmarks or []  # from Genie Space conversation history
_existing = existing_benchmarks or []   # previously validated, carried forward

curated_questions = {b.get("question", "").lower().strip() for b in curated}
existing_questions = {b.get("question", "").lower().strip() for b in _existing}
curated_questions |= existing_questions

synthetic_target = max(target_count - len(curated) - len(_existing), 5)
```

### LLM prompt template

The generation prompt uses `BENCHMARK_GENERATION_PROMPT` (registered via
Skill 06) and includes:

- Domain name
- Target count for synthetic benchmarks
- Category list from `BENCHMARK_CATEGORIES`
- Schema context (tables, columns, routines, metric views, join specs)
- Already-covered questions (to avoid duplicates)

```python
prompt = format_mlflow_template(
    BENCHMARK_GENERATION_PROMPT,
    domain=domain,
    target_count=synthetic_target,
    categories=json.dumps(BENCHMARK_CATEGORIES),
    **ctx,  # tables_context, valid_assets_context, column_allowlist, ...
)
```

### Category diversity

`BENCHMARK_CATEGORIES` from `config.py`:

```python
BENCHMARK_CATEGORIES = [
    "aggregation", "ranking", "time-series", "comparison",
    "detail", "list", "threshold", "multi-table",
]
```

The prompt instructs the LLM to distribute generated benchmarks across these
categories for diverse coverage.

---

## 3. SQL validation against schema

Every generated benchmark's `expected_sql` goes through validation before
acceptance.

### `_validate_benchmark_sql()`

```python
def _validate_benchmark_sql(
    sql: str,
    spark: SparkSession,
    catalog: str,
    schema: str,
    *,
    execute: bool = False,
    w: Any = None,
    warehouse_id: str = "",
) -> tuple[bool, str]:
    """Validate SQL via EXPLAIN. Returns (is_valid, error_message)."""
    resolved = resolve_sql(sql, catalog, schema)
    sanitized = sanitize_sql(resolved)
    if not sanitized.strip():
        return False, "Empty SQL"
    return validate_ground_truth_sql(
        sanitized, spark, catalog=catalog, gold_schema=schema, execute=execute,
        w=w, warehouse_id=warehouse_id,
    )
```

### Validation modes

| Mode | Method | When |
| --- | --- | --- |
| `EXPLAIN` | `spark.sql(f"EXPLAIN {sql}")` | Default — checks syntax and schema |
| Warehouse EXPLAIN | `_execute_sql_via_warehouse(w, wid, f"EXPLAIN {sql}")` | When `warehouse_id` provided |
| Execute | Actually runs the SQL | When `execute=True` (heavier, checks data) |

### Error classification

`_classify_sql_validation_error()` maps SQL errors to reason codes:

| Error pattern | Reason code |
| --- | --- |
| `TABLE_OR_VIEW_NOT_FOUND` | `unknown_asset` |
| `UNRESOLVED_COLUMN` | `unknown_column` |
| `INSUFFICIENT_PRIVILEGES` | `permission_blocked` |
| `PARSE_SYNTAX_ERROR` | `syntax_error` |
| `UNBOUND_SQL_PARAMETER` | Treated as valid (parameterized SQL) |

---

## 4. Quarantine patterns

### Pre-evaluation quarantine (`_precheck_benchmarks_for_eval`)

Called by `run_evaluation()` before `mlflow.genai.evaluate()`. Separates
benchmarks into evaluable and quarantined sets.

```python
def _precheck_benchmarks_for_eval(
    *,
    benchmarks: list[dict],
    spark: SparkSession,
    catalog: str,
    gold_schema: str,
    known_functions: set[str],
    metric_view_names: set[str] | None = None,
    metric_view_measures: dict[str, set[str]] | None = None,
    w: WorkspaceClient | None = None,
    warehouse_id: str = "",
) -> tuple[list[dict], list[dict], dict[str, int]]:
    """Returns (valid, quarantined, reason_counts)."""
```

### Quarantine reasons

| Reason | Description |
| --- | --- |
| `missing_ground_truth` | No `expected_sql` and `REQUIRE_GROUND_TRUTH_SQL` is set |
| `unknown_asset` | SQL references tables not in the schema |
| `unknown_column` | SQL references columns not in metadata |
| `permission_blocked` | `INSUFFICIENT_PRIVILEGES` or unknown UDFs |
| `syntax_error` | SQL parse failure |
| `metric_view_join` | Metric view benchmarks with JOIN (unsupported) |
| `bad_join_key` | Invalid join key references |

### Quarantine record shape

```python
quarantine_entry = {
    "question_id": "billing_001",
    "question": "What is the total cost?",
    "reason": "unknown_column",
    "sqlstate": "42703",
    "error": "Column 'total_cost' not found in table 'billing'",
    "expected_sql": "SELECT total_cost FROM billing",
}
```

### Quarantine artifact logging

Quarantined benchmarks are logged as an MLflow artifact for review:

```python
mlflow.log_dict(
    {
        "quarantined": quarantined_benchmarks,
        "reason_counts": reason_counts,
    },
    artifact_file="evaluation_runtime/benchmark_precheck.json",
)
```

### No-evaluable-benchmarks fast fail

If all benchmarks are quarantined, evaluation raises `NoEvaluableBenchmarks`:

```python
if not evaluable_benchmarks:
    raise NoEvaluableBenchmarks(
        f"All {len(benchmarks)} benchmarks quarantined; "
        f"reasons: {reason_counts}"
    )
```

---

## 5. Ground truth repair patterns

### Deterministic field-drift correction

Before LLM-based correction, the pipeline attempts deterministic fixes for
known column name drift (e.g. `total_cost` → `total_costs`):

```python
corrected_sql, replacements = _apply_metadata_field_drift_corrections(
    sql=expected_sql,
    required_columns=benchmark.get("required_columns", []),
    allowed_index=allowlist["column_index"],
)

if replacements and corrected_sql != expected_sql:
    candidate["provenance"] = "auto_corrected"
    candidate["correction_source"] = "metadata_suggestion"
    candidate["field_drift_fixes"] = replacements
```

### LLM-based correction rounds

Invalid benchmarks go through bounded correction rounds:

```python
MAX_CORRECTION_ROUNDS = 3  # configurable

for correction_round in range(MAX_CORRECTION_ROUNDS):
    if not invalid_benchmarks:
        break

    # 1. Try deterministic metadata corrections first
    metadata_corrected, still_invalid = attempt_metadata_corrections(invalid_benchmarks)

    # 2. Send remaining to LLM correction
    corrected = _attempt_benchmark_correction(
        w, config, uc_columns, uc_routines,
        still_invalid, catalog, schema, spark, allowlist,
        warehouse_id=warehouse_id,
    )
```

### Correction provenance tracking

| Provenance | Correction source | Meaning |
| --- | --- | --- |
| `synthetic` | `""` | LLM-generated, validated on first try |
| `auto_corrected` | `metadata_suggestion` | Deterministic column name fix |
| `auto_corrected` | `metadata_suggestion_loop` | Deterministic fix in correction round |
| `auto_corrected` | `llm_correction` | LLM rewrote the SQL |
| `curated` | `""` | From Genie Space conversation history |
| `curated_sql_generated` | `curated_sql_generation` | Question from Genie, SQL generated by LLM |

---

## 6. Provenance tracking

Every benchmark record carries provenance fields that trace its origin and
validation journey.

### Provenance field taxonomy

| Field | Values | Description |
| --- | --- | --- |
| `source` | `genie_space`, `llm_generated`, `manual` | Where the question came from |
| `provenance` | `curated`, `synthetic`, `auto_corrected`, `curated_sql_generated` | How the benchmark was produced |
| `validation_status` | `valid`, `invalid`, `pending`, `question_only` | Current validation state |
| `validation_reason_code` | `ok`, `unknown_asset`, `unknown_column`, ... | Why validation passed or failed |
| `validation_error` | Error message or `None` | Detailed error when validation failed |
| `correction_source` | `metadata_suggestion`, `llm_correction`, ... | How the benchmark was fixed |

### ID conventions

```python
# Curated benchmarks: {domain}_gs_{sequence}
question_id = f"{domain}_gs_{idx + 1:03d}"    # e.g. billing_gs_001

# Synthetic benchmarks: {domain}_{sequence}
question_id = f"{domain}_{offset + idx + 1:03d}"  # e.g. billing_015

# Gap-fill benchmarks: {domain}_gf_{sequence}
question_id = f"{domain}_gf_{offset + idx + 1:03d}"  # e.g. billing_gf_042
```

### Priority assignment

```python
# Curated benchmarks are always P0 (highest priority)
priority = "P0"

# Synthetic: first 3 are P0, rest are P1
priority = "P0" if idx < 3 else "P1"
```

---

## 7. Temporal staleness detection

`_flag_stale_temporal_benchmarks()` identifies benchmarks whose ground-truth
SQL returns zero rows due to time-based filters (e.g. "last month's costs"
when the data only covers older periods).

```python
TEMPORAL_QUESTION_RE = re.compile(
    r"(last|this|previous|current|past)\s+(month|week|quarter|year|day)",
    re.IGNORECASE,
)

def _flag_stale_temporal_benchmarks(benchmarks, spark, *, w=None, warehouse_id=""):
    for b in benchmarks:
        if not TEMPORAL_QUESTION_RE.search(b.get("question", "")):
            continue
        sql = b.get("expected_sql", "")
        if not sql:
            continue
        try:
            result = spark.sql(f"SELECT * FROM ({sql}) LIMIT 1")
            if result.count() == 0:
                b["temporal_stale"] = True
        except Exception:
            pass
```

Flagged benchmarks are excluded from accuracy-style metrics in
`_compute_arbiter_adjusted_accuracy` to avoid false negatives.

---

## 8. Post-generation alignment check

After SQL validation, the pipeline runs a semantic alignment check to ensure
the generated SQL actually answers the question asked:

```python
from genie_space_optimizer.optimization.benchmarks import validate_question_sql_alignment

alignment_results = validate_question_sql_alignment(valid_benchmarks)

for benchmark, result in zip(valid_benchmarks, alignment_results):
    if not result.get("aligned", True):
        benchmark["validation_status"] = "invalid"
        benchmark["validation_reason_code"] = "alignment_mismatch"
        benchmark["validation_error"] = "; ".join(result.get("issues", []))
```

Misaligned benchmarks get one more correction attempt before being discarded.

---

## 9. Coverage gap-fill

After the main generation pipeline, `_fill_coverage_gaps()` ensures every
asset in the Genie Space has at least one benchmark:

```python
gap_fill_benchmarks = _fill_coverage_gaps(
    w=w,
    config=config,
    uc_columns=uc_columns,
    uc_routines=uc_routines,
    benchmarks=all_benchmarks,
    catalog=catalog,
    schema=schema,
    spark=spark,
    allowlist=allowlist,
    domain=domain,
    existing_questions=all_accepted_questions,
    warehouse_id=warehouse_id,
    target_benchmark_count=target_count,
    max_benchmark_count=max_benchmark_count,
)
```

Gap-fill benchmarks get IDs like `{domain}_gf_{sequence}` and go through the
same validation pipeline.

---

## 10. Complete generation flow summary

```text
Genie Space conversations ──→ extract_genie_qa_pairs()
                                │
                                ▼
                          curated benchmarks (source=genie_space)
                                │
Existing benchmarks ──────────→ │
                                ▼
                          calculate synthetic_target
                                │
                                ▼
                    LLM generation (BENCHMARK_GENERATION_PROMPT)
                                │
                                ▼
                    _enforce_metadata_constraints()
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
              metadata OK              metadata FAIL
                   │                         │
                   ▼                         ▼
          _validate_benchmark_sql()    _apply_metadata_field_drift_corrections()
                   │                         │
              ┌────┴────┐               ┌────┴────┐
              ▼         ▼               ▼         ▼
           valid    invalid          fixed    still broken
              │         │               │         │
              │         └───────────────┘         │
              │                │                  │
              │                ▼                  │
              │    _attempt_benchmark_correction() (LLM, bounded retries)
              │                │                  │
              │           ┌────┴────┐             │
              │           ▼         ▼             ▼
              │       corrected  unfixable    discarded
              │           │
              ▼           ▼
        validate_question_sql_alignment()
                    │
               ┌────┴────┐
               ▼         ▼
           aligned   misaligned → one more correction attempt
               │
               ▼
        _fill_coverage_gaps()
               │
               ▼
        assign IDs, provenance, splits
               │
               ▼
        create_evaluation_dataset() → UC Delta table
```

---

## 11. Issue-Focused Eval Subsets from Failing Traces

Once an agent is in production, eval sets must evolve beyond the initial SME-curated rows. The most valuable additions are **failing traces** — real user turns where a scorer fell below threshold or a human gave negative feedback. Treat these as regressions to seal.

### 11.1 When to build an issue subset

- A production monitoring scorer (see [07-production-monitoring](../../07-production-monitoring/SKILL.md)) fires below threshold on ≥ 5 sampled traces.
- A user filed a bug or left negative feedback on N traces.
- A new feature shipped and you want to re-test historic regressions.

### 11.2 Pull failing traces from `*_otel_annotations`

MLflow writes scorer assessments and human feedback to the `*_otel_annotations` UC table. Join to the trace table to pull full context.

```sql
WITH failing AS (
  SELECT DISTINCT request_id
  FROM main.skyloyalty_ops.skyloyalty_agent_otel_annotations
  WHERE assessment_name IN ('source_citation_scorer', 'guideline_compliance')
    AND value < 0.7
    AND timestamp >= current_timestamp() - INTERVAL 14 DAYS
)
SELECT
  t.request_id,
  t.request,
  t.response,
  a.assessment_name,
  a.value,
  a.rationale
FROM main.skyloyalty_ops.skyloyalty_agent_otel_traces t
JOIN failing f ON t.request_id = f.request_id
LEFT JOIN main.skyloyalty_ops.skyloyalty_agent_otel_annotations a
  ON a.request_id = t.request_id
```

### 11.3 Convert to eval rows

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
failing_df = w.sql.query("""...the SQL above...""")

issue_rows = []
for trace_id, group in failing_df.groupby("request_id"):
    first = group.iloc[0]
    user_msg = (first["request"].get("messages") or [{}])[-1].get("content", "")
    answer = (first["response"] or {}).get("content", "")

    expectations = {}
    for _, row in group.iterrows():
        # Record which scorer failed so future runs can check regression
        expectations[f"min_{row['assessment_name']}"] = 0.7

    issue_rows.append({
        "inputs": {"question": user_msg},
        "outputs": {"answer": answer},          # snapshot of the failing output
        "expectations": expectations,
        "provenance": "issue_failing_trace",
        "source_trace_id": trace_id,
        "issue_scorers": list(group["assessment_name"].unique()),
    })
```

### 11.4 Tag as regression subset and merge

```python
import mlflow.genai.datasets as mlfds

ds = mlfds.get_or_create_dataset("main.skyloyalty.skyloyalty_agent_benchmarks")
ds.merge_records(issue_rows, primary_keys=["source_trace_id"])
```

### 11.5 Gate releases on the issue subset specifically

In [04-evaluation-runs](../../04-evaluation-runs/SKILL.md), filter the dataset down to `provenance = "issue_failing_trace"` and require **100% pass rate** on that subset. This is your "these specific bugs cannot return" gate.

```python
full = mlfds.get_dataset("main.skyloyalty.skyloyalty_agent_benchmarks").to_df()
regression_subset = full[full["provenance"] == "issue_failing_trace"]
assert len(regression_subset) > 0, "No regression rows yet"

result = mlflow.genai.evaluate(
    predict_fn=predict_fn,
    data=regression_subset.to_dict(orient="records"),
    scorers=[source_citation_scorer, guideline_compliance],
)

# Hard gate: any failure fails the release
assert (
    result.metrics["source_citation_scorer/mean"] == 1.0
    and result.metrics["guideline_compliance/mean"] == 1.0
), "Regression subset must pass 100%"
```

### 11.6 Lifecycle: keep it small and sharp

- Re-run the pull weekly.
- When a fix lands and three consecutive runs pass, **retire** the row (or move to the frozen gold subset).
- Cap the regression subset at ~50 rows; beyond that, the gate is too slow for CI.
- Track "days since last regression hit" as a team metric.

### 11.7 Worked example: augment, not replace

The most common failure mode after the first regression-subset pull is **swapping the dataset**: the team realises the regression rows reproduce the bug, runs `evaluate()` against only those rows, sees `Correctness/mean = 1.0`, and ships. This is wrong — passing the regression subset proves the specific bug is sealed, not that the agent is still good at everything else. Always **augment** the baseline; never replace it.

#### Step 1 — baseline dataset (existing benchmark)

Suppose your baseline is 42 rows in `main.skyloyalty.skyloyalty_agent_benchmarks`, all with `provenance` in `{curated, synthetic}` and `split = "train" | "held_out"`:

```python
baseline = [
    {
        "row_id": "loyalty_redeem_001",
        "inputs": {"request": "How many points to redeem a flight to LHR?"},
        "expectations": {
            "expected_response": "It depends on award class and date — typically 30k–60k miles for economy LHR routes.",
            "expected_signal": "redemption_lookup",
            "bucket": "redemption",
            "journey_id": "redeem_award",
            "split": "held_out",
            "provenance": "curated",
        },
    },
    {
        "row_id": "loyalty_status_002",
        "inputs": {"request": "What's my elite status threshold?"},
        "expectations": {
            "expected_response": "Gold requires 50k qualifying miles or 60 segments per calendar year.",
            "expected_signal": "status_lookup",
            "bucket": "status",
            "journey_id": "check_status",
            "split": "train",
            "provenance": "curated",
        },
    },
    # ... 40 more rows across buckets {redemption, status, booking, refund, lounge}
]
```

#### Step 2 — regression rows (issue subset, harvested per §11.2–§11.4)

Production monitoring fires below threshold on three traces in week 6. After review, the SME promotes them to regression rows:

```python
regression = [
    {
        "row_id": "loyalty_refund_reg_001",
        "inputs": {"request": "Refund my Tokyo flight, the schedule changed by 4 hours"},
        "outputs": {"answer": "I can't process refunds. Please call support."},  # the failing snapshot
        "expectations": {
            "expected_response": "A schedule change of more than 3 hours qualifies for a full refund per IATA Resolution 830a; I can initiate this for you now.",
            "expected_signal": "schedule_change_refund",
            "bucket": "refund",
            "journey_id": "request_refund",
            "split": "regression",
            "provenance": "issue_failing_trace",
            "min_guideline_compliance": 0.7,
            "source_trace_id": "tr_abc123",
        },
    },
    {
        "row_id": "loyalty_lounge_reg_002",
        "inputs": {"request": "Can my +1 use the lounge if I'm Gold?"},
        "outputs": {"answer": "No, lounge access is single-guest only."},
        "expectations": {
            "expected_response": "Gold members may bring one guest to Star Alliance Gold lounges at no cost.",
            "expected_signal": "lounge_guest_policy",
            "bucket": "lounge",
            "journey_id": "lounge_access",
            "split": "regression",
            "provenance": "issue_failing_trace",
            "min_source_citation_scorer": 0.7,
            "source_trace_id": "tr_def456",
        },
    },
    {
        "row_id": "loyalty_status_reg_003",
        "inputs": {"request": "I flew 49,800 miles, do I make Gold?"},
        "outputs": {"answer": "No, you need exactly 50,000 miles."},
        "expectations": {
            "expected_response": "You're 200 miles short of the 50,000-mile Gold threshold; one more short-haul segment will qualify you.",
            "expected_signal": "status_threshold_edge",
            "bucket": "status",
            "journey_id": "check_status",
            "split": "regression",
            "provenance": "issue_failing_trace",
            "min_correctness": 0.8,
            "source_trace_id": "tr_ghi789",
        },
    },
]
```

#### Step 3 — merge keys

`row_id` is the canonical merge key. Augmentation is an upsert by `row_id`:

```python
import mlflow.genai.datasets as mlfds

ds = mlfds.get_dataset("main.skyloyalty.skyloyalty_agent_benchmarks")
ds.merge_records(regression, primary_keys=["row_id"])
```

`source_trace_id` is the **secondary** key used to retire regression rows when the bug is sealed (see §11.6) — it is not used for merge.

#### Step 4 — resulting full dataset

```text
                             baseline (42 rows)            +     regression (3 rows)
                             split in {train, held_out}          split = "regression"
                             expected_response populated         expected_response populated
                             expected_signal classification      expected_signal classification
                             provenance in {curated, synthetic}  provenance = "issue_failing_trace"
                                              \                /
                                               \              /
                                                v            v
                                       full dataset = 45 rows
                                       (canonical_source = uc_table)
                                       coverage gates re-checked:
                                         min_rows: 40             ✓ (45 ≥ 40)
                                         per_bucket_min_rows: 1   ✓ (refund, lounge, status all covered)
                                         per_journey_min_rows: 1  ✓ (request_refund, lounge_access, check_status covered)
```

#### Step 5 — promotion gate runs against the full dataset, not the subset

```python
import mlflow

full = mlfds.get_dataset("main.skyloyalty.skyloyalty_agent_benchmarks").to_df()

# Promotion gate: evaluate against the FULL set, not the regression slice
result = mlflow.genai.evaluate(
    predict_fn=predict_fn,
    data=full.to_dict(orient="records"),
    scorers=[correctness, source_citation_scorer, guideline_compliance],
)

# Two assertions, both required:
# (a) Aggregate quality on the full set must not regress
assert result.metrics["correctness/mean"] >= baseline_correctness_mean - 0.02

# (b) Every regression row must individually pass its row-level threshold
regression_rows = full[full["split"] == "regression"]
regression_result = mlflow.genai.evaluate(
    predict_fn=predict_fn,
    data=regression_rows.to_dict(orient="records"),
    scorers=[correctness, source_citation_scorer, guideline_compliance],
)
assert regression_result.metrics["correctness/mean"] == 1.0, "Regression subset must pass 100%"
```

#### Why the regression subset is NOT used alone for promotion

If you promote on regression-only metrics:

1. **Aggregate quality drift is invisible.** A code change might fix the three regressions but degrade `Correctness` from 0.91 → 0.74 across the 42 baseline rows. The regression-only run reports `1.0` and you ship a worse model.
2. **Coverage gates are bypassed.** The regression subset has 3 rows, 1–2 buckets, 2–3 journeys. It fails `min_rows: 40`, `per_bucket_min_rows: 1` for the buckets it doesn't touch, and `per_journey_min_rows: 1` for journeys with no regressions yet. Treating it as the gate means promoting against a dataset that the canonical-source rules forbid.
3. **The subset overfits to recent SME labelling.** Regression rows reflect last week's incidents — they are biased toward novel failure modes and under-represent steady-state traffic. The baseline holds the steady-state contract; you need both signals to ship.

The rule: **the regression subset is a hard floor — it must pass 100% — but the full dataset is the ceiling. Both gates run, and the release is blocked unless both pass.**

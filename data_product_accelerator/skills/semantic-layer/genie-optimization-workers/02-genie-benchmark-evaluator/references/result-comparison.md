# Result Comparison Patterns

This reference documents the DataFrame comparison logic used by the `result_correctness` scorer in Layer 2 of the Genie Benchmark Evaluator. Both SQLs (Genie-generated and ground truth) are executed via Spark, and their result sets are compared using a cascading match strategy.

---

## execute_both_sqls

Executes both the Genie-generated SQL and the ground truth SQL against the warehouse, then delegates to `compare_result_sets()` for the actual comparison.

```python
def execute_both_sqls(genie_sql: str, gt_sql: str, spark) -> dict:
    """Execute both SQLs and compare results.

    Returns:
        dict with match_type (exact|approximate|structural|mismatch),
        gt_rows, genie_rows, detail
    """
    try:
        gt_df = spark.sql(gt_sql).toPandas()
    except Exception as e:
        return {"match_type": "error", "detail": f"GT SQL failed: {e}", "gt_rows": 0, "genie_rows": 0}

    try:
        genie_df = spark.sql(genie_sql).toPandas()
    except Exception as e:
        return {"match_type": "error", "detail": f"Genie SQL failed: {e}", "gt_rows": len(gt_df), "genie_rows": 0}

    return compare_result_sets(gt_df, genie_df)
```

---

## compare_result_sets

Compares two pandas DataFrames using a cascading strategy: exact → approximate → structural → mismatch.

```python
import numpy as np

def compare_result_sets(gt_df, genie_df) -> dict:
    """Compare two DataFrames: exact → approximate → structural → mismatch."""
    gt_rows = len(gt_df)
    genie_rows = len(genie_df)
    base = {"gt_rows": gt_rows, "genie_rows": genie_rows}

    if gt_df.equals(genie_df):
        return {**base, "match_type": "exact", "detail": "DataFrames are identical."}

    if set(gt_df.columns) == set(genie_df.columns) and gt_rows == genie_rows:
        gt_sorted = gt_df.sort_values(by=list(gt_df.columns)).reset_index(drop=True)
        genie_sorted = genie_df[gt_df.columns].sort_values(by=list(gt_df.columns)).reset_index(drop=True)

        if gt_sorted.equals(genie_sorted):
            return {**base, "match_type": "exact", "detail": "Same data, different row order."}

        try:
            numeric_cols = gt_sorted.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                close = np.allclose(
                    gt_sorted[numeric_cols].values,
                    genie_sorted[numeric_cols].values,
                    rtol=1e-2, atol=1e-6, equal_nan=True,
                )
                if close:
                    return {**base, "match_type": "approximate", "detail": "Numeric values within 1% tolerance."}
        except (TypeError, ValueError):
            pass

    if gt_rows == genie_rows:
        return {**base, "match_type": "structural", "detail": f"Same row count ({gt_rows}) but different columns or values."}

    return {**base, "match_type": "mismatch", "detail": f"Row count differs: GT={gt_rows}, Genie={genie_rows}."}
```

---

## Match Types

| Match Type | Meaning | Result Correctness |
|------------|---------|-------------------|
| **exact** | DataFrames are identical, or same data with different row order | `yes` |
| **approximate** | Same schema and row count; numeric columns within 1% tolerance (`np.allclose`) | `yes` |
| **structural** | Same row count but different columns or non-numeric values | `yes` (conservative pass) |
| **mismatch** | Row count differs | `no` |
| **error** | One or both SQLs failed to execute | `no` |

The `result_correctness` scorer returns `"yes"` for `exact`, `approximate`, and `structural`; it returns `"no"` for `mismatch` and `error`.

---

## Deterministic Normalization (P9)

Before comparison, both DataFrames are normalized using `normalize_result_df()` for reproducibility:

1. **Column names**: lowercased and stripped of whitespace
2. **Column order**: sorted alphabetically
3. **Row order**: sorted by all columns
4. **Float precision**: rounded to 6 decimal places
5. **String whitespace**: stripped
6. **Timestamps**: normalized to UTC

```python
def normalize_result_df(df):
    """Deterministic normalization of a result DataFrame."""
    if df is None or df.empty:
        return df
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[sorted(df.columns)]
    for col in df.select_dtypes(include=["float64", "float32"]).columns:
        df[col] = df[col].round(6)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
        df[col] = pd.to_datetime(df[col], utc=True)
    df = df.sort_values(by=list(df.columns)).reset_index(drop=True)
    return df
```

### Result Signatures

For quick schema comparison without full DataFrame comparison, use `result_signature()`:

```python
def result_signature(df):
    """Quick schema hash + rowcount + numeric sums for result comparison."""
    if df is None or df.empty:
        return {"schema_hash": "", "row_count": 0, "numeric_sums": {}}
    schema_str = ",".join(f"{c}:{df[c].dtype}" for c in sorted(df.columns))
    schema_hash = hashlib.md5(schema_str.encode()).hexdigest()[:8]
    numeric_sums = {col: round(float(df[col].sum()), 6)
                    for col in df.select_dtypes(include=["number"]).columns}
    return {"schema_hash": schema_hash, "row_count": len(df), "numeric_sums": numeric_sums}
```

Two results with the same signature have identical schemas, row counts, and numeric column sums — a strong heuristic for equivalence without full cell-by-cell comparison.

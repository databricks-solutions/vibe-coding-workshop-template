# Result Comparison Patterns

This reference documents the DataFrame comparison logic used by the `result_correctness` scorer in Layer 2 of the Genie Benchmark Evaluator. Both SQLs (Genie-generated and ground truth) are executed inside `genie_predict_fn`, and their result sets are compared using a cascading match strategy: exact → hash → signature → mismatch.

---

## Inline Comparison in genie_predict_fn

The template does NOT use separate `execute_both_sqls()` or `compare_result_sets()` functions. All comparison logic lives inline in `genie_predict_fn`. SQL execution is lifted there so every scorer (including `result_correctness` and `arbiter_scorer`) reads pre-computed `outputs["comparison"]` — no scorer calls `spark.sql()`.

```python
# Inside genie_predict_fn — after run_genie_query, sanitize_sql, resolve_sql
comparison = {"match": False, "match_type": "mismatch", "gt_rows": 0,
              "genie_rows": 0, "gt_hash": None, "genie_hash": None,
              "gt_signature": None, "genie_signature": None, "error": None}
if genie_sql and gt_sql:
    try:
        gt_df = normalize_result_df(spark.sql(gt_sql).toPandas())
        genie_df = normalize_result_df(spark.sql(genie_sql).toPandas())
        gt_hash = hashlib.md5(gt_df.to_csv(index=False).encode()).hexdigest()[:8]
        genie_hash = hashlib.md5(genie_df.to_csv(index=False).encode()).hexdigest()[:8]
        exact_match = gt_df.shape == genie_df.shape and gt_df.equals(genie_df)
        hash_match = gt_hash == genie_hash
        gt_sig = result_signature(gt_df)
        genie_sig = result_signature(genie_df)
        sig_match = (gt_sig["schema_hash"] == genie_sig["schema_hash"]
                     and gt_sig["row_count"] == genie_sig["row_count"])
        comparison = {
            "match": exact_match or hash_match,  # signature is recorded but does not set match=True
            "match_type": "exact" if exact_match else ("hash" if hash_match else ("signature" if sig_match else "mismatch")),
            "gt_rows": len(gt_df),
            "genie_rows": len(genie_df),
            "gt_hash": gt_hash,
            "genie_hash": genie_hash,
            "gt_signature": gt_sig,
            "genie_signature": genie_sig,
            "error": None,
        }
    except Exception as e:
        comparison["error"] = str(e)[:200]
else:
    comparison["error"] = "Missing SQL for comparison"

return {"response": genie_sql, "status": ..., "conversation_id": ..., "comparison": comparison}
```

---

## Match Types

| Match Type | Meaning | comparison["match"] | Result Correctness |
|------------|---------|---------------------|-------------------|
| **exact** | DataFrames have identical shape and `df.equals()` returns True | `True` | `yes` |
| **hash** | MD5 of `to_csv()` output matches (same data, possibly different row order) | `True` | `yes` |
| **signature** | Same schema_hash and row_count from `result_signature()` | `False` | `no` |
| **mismatch** | None of the above | `False` | `no` |
| **error** | One or both SQLs failed to execute; `comparison["error"]` is set | `False` | `no` |

The template sets `comparison["match"] = exact_match or hash_match` — signature match is recorded in `match_type` but does NOT set `match=True`. The `result_correctness` scorer returns `"yes"` only when `cmp.get("match")` is True (i.e., exact or hash); it returns `"no"` for signature, mismatch, and error.

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
    """Deterministic normalization of a result DataFrame (P9)."""
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

---

## result_signature

For quick schema + row count comparison without full DataFrame equality, use `result_signature()`:

```python
def result_signature(df):
    """Quick schema hash + rowcount + numeric sums for result comparison (P9)."""
    if df is None or df.empty:
        return {"schema_hash": "", "row_count": 0, "numeric_sums": {}}
    schema_str = ",".join(f"{c}:{df[c].dtype}" for c in sorted(df.columns))
    schema_hash = hashlib.md5(schema_str.encode()).hexdigest()[:8]
    numeric_sums = {}
    for col in df.select_dtypes(include=["number"]).columns:
        numeric_sums[col] = round(float(df[col].sum()), 6)
    return {
        "schema_hash": schema_hash,
        "row_count": len(df),
        "numeric_sums": numeric_sums,
    }
```

Two results with the same `schema_hash` and `row_count` are considered structurally equivalent (match_type `signature`). The `numeric_sums` are available for additional heuristics but the template uses only schema_hash and row_count for match determination.

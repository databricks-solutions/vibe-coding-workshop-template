# DQX Configuration and API Reference

**Verified against:** [DQX 0.12.0 API Documentation](https://databrickslabs.github.io/dqx/docs/reference/api/check_funcs/)

## Installation Patterns

### Serverless Jobs (Environment-Level)

```yaml
resources:
  jobs:
    silver_dq_job:
      environments:
        - environment_key: default
          spec:
            dependencies:
              - "databricks-labs-dqx>=0.12.0"
      tasks:
        - task_key: apply_dqx_checks
          environment_key: default
          notebook_task:
            notebook_path: ../src/company_silver/apply_dqx_checks.py
```

**Error if task-level:** `Libraries field is not supported for serverless task, please specify libraries in environment.`

### DLT / Lakeflow Pipelines

```yaml
resources:
  pipelines:
    silver_pipeline:
      libraries:
        - notebook:
            path: ../src/company_silver/silver_transactions.py
        - pypi:
            package: databricks-labs-dqx>=0.12.0
```

### Notebook Installation

```python
%pip install databricks-labs-dqx>=0.12.0
dbutils.library.restartPython()
```

### Workspace Tool (Optional - for profiling workflows and dashboards)

```bash
databricks labs install dqx
databricks labs dqx open-dashboards
```

---

## Complete Check Functions Reference (DQX >= 0.12.0)

### Row-Level Check Functions

#### Null / Empty Checks

| Function | Parameters | Description |
|----------|-----------|-------------|
| `is_not_null` | `column` | Column is not null |
| `is_not_empty` | `column` | Column is not empty (may be null) |
| `is_not_null_and_not_empty` | `column`, `trim_strings=False` | Column is not null and not empty |
| `is_not_null_and_not_empty_array` | `column` | Array column is not null and not empty |

#### Comparison Checks

| Function | Parameters | Description |
|----------|-----------|-------------|
| `is_not_less_than` | `column`, **`limit`** | column >= limit |
| `is_not_greater_than` | `column`, **`limit`** | column <= limit |
| `is_equal_to` | `column`, **`value`** | column == value *(added 0.9.1)* |
| `is_not_equal_to` | `column`, **`value`** | column != value *(added 0.9.1)* |

**Note:** `limit` accepts `int | float | date | datetime | str | Column`. Float support added in 0.12.0.

**There is no `is_greater_than` or `is_less_than` function.** For strict comparisons, use `sql_expression`:
```yaml
- check:
    function: sql_expression
    arguments:
      expression: "price > 0"  # strict greater-than
```

#### Range Checks

| Function | Parameters | Description |
|----------|-----------|-------------|
| `is_in_range` | `column`, **`min_limit`**, **`max_limit`** | min_limit <= column <= max_limit |
| `is_not_in_range` | `column`, **`min_limit`**, **`max_limit`** | column < min_limit OR column > max_limit |

#### List Membership Checks

| Function | Parameters | Description |
|----------|-----------|-------------|
| `is_in_list` | `column`, **`allowed`**, `case_sensitive=True` | Column value in allowed list |
| `is_not_null_and_is_in_list` | `column`, **`allowed`**, `case_sensitive=True` | Not null AND in allowed list |
| `is_not_in_list` | `column`, **`forbidden`**, `case_sensitive=True` | Column value NOT in forbidden list *(added 0.12.0)* |

#### Date / Time Checks

| Function | Parameters | Description |
|----------|-----------|-------------|
| `is_valid_date` | `column`, `date_format=None` | Valid date format |
| `is_valid_timestamp` | `column`, `timestamp_format=None` | Valid timestamp format |
| `is_not_in_future` | `column`, `offset=0`, `curr_timestamp=None` | Timestamp not in future |
| `is_not_in_near_future` | `column`, `offset=0`, `curr_timestamp=None` | Not in near future (< offset seconds) |
| `is_older_than_n_days` | `column`, `days`, `curr_date=None`, `negate=False` | At least N days old |
| `is_older_than_col2_for_n_days` | `column1`, `column2`, `days=0`, `negate=False` | Column1 at least N days older than Column2 |
| `is_data_fresh` | `column`, **`max_age_minutes`**, `base_timestamp=None` | Data not older than N minutes *(added 0.8.0)* |

#### Pattern / Format Checks

| Function | Parameters | Description |
|----------|-----------|-------------|
| `regex_match` | `column`, **`regex`**, `negate=False` | Matches regex pattern |
| `is_valid_ipv4_address` | `column` | Valid IPv4 address |
| `is_ipv4_address_in_cidr` | `column`, **`cidr_block`** | IPv4 within CIDR block |
| `is_valid_ipv6_address` | `column` | Valid IPv6 address *(added 0.9.3)* |
| `is_ipv6_address_in_cidr` | `column`, **`cidr_block`** | IPv6 within CIDR block *(added 0.9.3)* |

#### SQL Expression

| Function | Parameters | Description |
|----------|-----------|-------------|
| `sql_expression` | **`expression`**, `msg=None`, `name=None`, `negate=False`, `columns=None` | Custom SQL condition |

**Note:** The function name is `sql_expression`, NOT `sql_expr`.

### Dataset-Level Check Functions

| Function | Parameters | Description |
|----------|-----------|-------------|
| `is_unique` | **`columns`** (list), `nulls_distinct=True`, `row_filter=None` | No duplicate values across columns |
| `foreign_key` | **`columns`**, **`ref_columns`**, `ref_df_name=None`, `ref_table=None`, `negate=False` | Referential integrity |
| `has_no_outliers` | `column`, `row_filter=None` | No outliers (MAD method) *(added 0.12.0)* |
| `sql_query` | **`query`**, `merge_columns=None`, `msg=None`, `negate=False` | Custom SQL query *(row or dataset level)* |
| `is_aggr_not_greater_than` | `column`, **`limit`**, `aggr_type="count"`, `group_by=None`, `aggr_params=None` | Aggregate <= limit |
| `is_aggr_not_less_than` | `column`, **`limit`**, `aggr_type="count"`, `group_by=None`, `aggr_params=None` | Aggregate >= limit |
| `is_aggr_equal` | `column`, **`limit`**, `aggr_type="count"`, `group_by=None` | Aggregate == limit |
| `is_aggr_not_equal` | `column`, **`limit`**, `aggr_type="count"`, `group_by=None` | Aggregate != limit |
| `compare_datasets` | **`columns`**, **`ref_columns`**, `ref_df_name=None`, `ref_table=None`, `check_missing_records=False` | Compare two datasets |

---

## Parameter Name Quick Reference

**CRITICAL: Each function has specific parameter names. Using wrong names causes immediate errors.**

| Function Category | Parameter | Correct Name | Wrong Names |
|------------------|-----------|-------------|-------------|
| Comparison (`is_not_less_than`, etc.) | threshold | **`limit`** | `value`, `threshold`, `min` |
| Equality (`is_equal_to`, `is_not_equal_to`) | target | **`value`** | `limit`, `expected` |
| Range (`is_in_range`) | boundaries | **`min_limit`**, **`max_limit`** | `min_value`, `max_value`, `min`, `max` |
| List (`is_in_list`) | valid values | **`allowed`** | `values`, `valid`, `list` |
| Not-in-list (`is_not_in_list`) | invalid values | **`forbidden`** | `values`, `blocked`, `list` |
| Regex (`regex_match`) | pattern | **`regex`** | `pattern`, `expr` |
| Freshness (`is_data_fresh`) | age | **`max_age_minutes`** | `max_age`, `minutes` |
| Aggregation (`is_aggr_*`) | type | **`aggr_type`** | `agg_type`, `type` |

---

## DQEngine API Methods

### Check Application Methods

**For metadata (dict/YAML) checks:**

| Method | Returns | Use Case |
|--------|---------|----------|
| `apply_checks_by_metadata(df, checks)` | DataFrame with diagnostic columns | Mark but don't split |
| `apply_checks_by_metadata_and_split(df, checks)` | `(valid_df, invalid_df)` | Split valid/invalid |
| `apply_checks_by_metadata_and_save_in_table(checks, input_config, output_config, quarantine_config)` | None | End-to-end |

**For DQX class (DQRowRule/DQDatasetRule) checks:**

| Method | Returns | Use Case |
|--------|---------|----------|
| `apply_checks(df, checks)` | DataFrame with diagnostic columns | Mark but don't split |
| `apply_checks_and_split(df, checks)` | `(valid_df, invalid_df)` | Split valid/invalid |
| `apply_checks_and_save_in_table(checks, input_config, output_config, quarantine_config)` | None | End-to-end |

### Helper Methods

| Method | Description |
|--------|-------------|
| `get_valid(df)` | Get rows without errors from checked DataFrame |
| `get_invalid(df)` | Get rows with errors from checked DataFrame |
| `save_checks(checks, config)` | Save checks to storage (Delta, Lakebase, file, Volume) |
| `load_checks(config)` | Load checks from storage |
| `save_results_in_table(output_df, quarantine_df, output_config, quarantine_config)` | Save results to tables |

### Multi-Table Methods (added 0.9.3)

| Method | Description |
|--------|-------------|
| `apply_checks_and_save_in_tables(run_configs)` | Apply checks on multiple tables |
| `apply_checks_and_save_in_tables_for_patterns(patterns, checks_location, ...)` | Apply checks on tables matching wildcard patterns |

---

## Spark Connect Compatibility (Serverless)

**Serverless compute uses Spark Connect. Avoid JVM-dependent APIs.**

```python
# WRONG - Fails on serverless
current_user = spark.sparkContext.sparkUser()

# CORRECT - Spark Connect compatible
current_user = spark.sql("SELECT current_user() as user").collect()[0]["user"]
```

---

## Common Errors and Solutions

### Error 1: Function Not Defined
**Error:** `function 'is_greater_than' is not defined`
**Cause:** Function doesn't exist in DQX API
**Solution:** Use `is_not_less_than` (for >=) or `sql_expression` (for strict >)

### Error 2: Unexpected Argument
**Error:** `Unexpected argument 'value' for function 'is_not_less_than'`
**Solution:** Use correct parameter name: `limit` (not `value`)

### Error 3: Wrong API Method
**Error:** `Use 'apply_checks_by_metadata_and_split' to pass checks as list of dicts instead.`
**Solution:** Use `apply_checks_by_metadata*` methods for dict/YAML checks

### Error 4: Serverless Library Config
**Error:** `Libraries field is not supported for serverless task`
**Solution:** Move dependency to `environments[].spec.dependencies`

### Error 5: Spark Connect Incompatibility
**Error:** `Attribute sparkContext is not supported in Spark Connect`
**Solution:** Use SQL queries instead of `sparkContext` methods

### Error 6: Import Error in Serverless
**Error:** `ModuleNotFoundError: No module named 'dqx_checks'`
**Solution:** Ensure shared code is pure Python (no `# Databricks notebook source` header)

### Error 7: Float Type (DQX < 0.12.0 only)
**Error:** `Argument 'limit' should be of type 'int | ...'`
**Solution:** Use integer values, or upgrade to DQX >= 0.12.0 which supports float

---

## Version Compatibility Notes

| Feature | Min Version | Notes |
|---------|------------|-------|
| Core engine (`apply_checks*`) | 0.8.0 | |
| `is_data_fresh` | 0.8.0 | |
| Unified `load_checks`/`save_checks` | 0.8.0 | Old methods removed in 0.9.3 |
| `is_equal_to` / `is_not_equal_to` | 0.9.1 | Uses `value` parameter |
| Multi-table checking | 0.9.3 | `apply_checks_and_save_in_tables` |
| `foreign_key` check | 0.6.0 | Dataset-level |
| Summary metrics | 0.10.0 | `DQMetricsObserver` |
| LLM-assisted rules | 0.10.0 | `generate_dq_rules_ai_assisted` |
| Lakebase storage | 0.10.0 | PostgreSQL-compatible |
| `is_not_in_list` | 0.12.0 | Uses `forbidden` parameter |
| Float support for limits | 0.12.0 | `limit: int \| float \| ...` |
| `has_no_outliers` (MAD) | 0.12.0 | Dataset-level |
| JSON validation checks | 0.12.0 | `is_valid_json`, `has_json_keys` |
| AI rules from profiles | 0.12.0 | |

## References

- [DQX Check Functions API](https://databrickslabs.github.io/dqx/docs/reference/api/check_funcs/)
- [DQX User Guide](https://databrickslabs.github.io/dqx/docs/guide/)
- [DQX Installation Guide](https://databrickslabs.github.io/dqx/docs/installation/)
- [DQX CHANGELOG](https://github.com/databrickslabs/dqx/blob/main/CHANGELOG.md)

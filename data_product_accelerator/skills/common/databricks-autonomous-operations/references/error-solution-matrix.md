# Error-Solution Matrix

Complete error tables for all Databricks resource categories. Load this reference when diagnosing failures.

---

## 1. Job Runtime Failures

| Error Pattern | Root Cause | Fix |
|--------------|------------|-----|
| `ModuleNotFoundError: <module>` | Missing dependency in serverless env | Add `%pip install <module>` at top of notebook, or add to DAB environment spec `dependencies:` |
| `UNRESOLVED_COLUMN: Column 'X' cannot be resolved` | Wrong column name | Check against Gold YAML schema: `gold_layer_design/yaml/{domain}/{table}.yaml` or run `DESCRIBE TABLE catalog.schema.table` |
| `TABLE_OR_VIEW_NOT_FOUND: Table 'X' not found` | Table doesn't exist | Run setup job first (`gold_setup_job`, `bronze_setup_job`). Verify catalog.schema.table path matches DAB variables. |
| `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` | Duplicate business keys in Silver source | Deduplicate source DataFrame before MERGE. Reference `gold-delta-merge-deduplication` skill. Use `ROW_NUMBER()` partitioned by business key, ordered by timestamp DESC, take row 1. |
| `PermissionDenied` / `FORBIDDEN` | Insufficient Unity Catalog grants | Check grants: `SHOW GRANTS ON TABLE catalog.schema.table`. Grant required: `SELECT`, `MODIFY`, or `ALL PRIVILEGES`. |
| `INTERNAL_ERROR` | Cluster/infrastructure issue | Retry once. If persistent: check cluster events (`databricks clusters events <ID>`), look for OOM, spot instance termination, or cloud provider issues. |
| `MlflowException: signature` | Model signature mismatch | Fix `fe.log_model()` parameters. Verify input/output schemas match model expectations. |
| `Model not found` / `RESOURCE_DOES_NOT_EXIST` | Model not in registry | Check model registry path (`models:/catalog.schema.model_name`). Run training pipeline first. |
| `PARSE_SYNTAX_ERROR` | SQL syntax error | Read the failing SQL file, identify syntax issue (common: missing comma, invalid alias, unclosed parenthesis). Fix and redeploy. |
| `RuntimeError: timeout` / job timeout | Job exceeded timeout_seconds | Increase `timeout_seconds` in DAB YAML. Default is often too low for initial setup jobs. |
| `ImportError: cannot import name 'AlertV2' from 'databricks.sdk.service.sql'` | Old SDK version in serverless | Add `%pip install --upgrade databricks-sdk>=0.40.0 --quiet` + `%restart_python` at top of notebook. |
| `Division by zero` in custom metric | Missing NULLIF in derived metric | Add `NULLIF(denominator, 0)` in metric SQL definition. |
| `PARSE_SYNTAX_ERROR` with `%` in LIKE pattern | SQL escaping strips quotes from LIKE patterns | Use DataFrame insertion (`df.write.mode("append").saveAsTable(...)`) instead of SQL INSERT with string values. |
| `AnalysisException: Column 'col' already exists` | Duplicate column in SELECT | Check for duplicate aliases. When joining tables, explicitly select columns instead of `SELECT *`. |
| `StreamingQueryException` | Streaming checkpoint issue | Clear checkpoint directory and restart with `full_refresh: true`. |

---

## 2. DLT Pipeline Failures

| Error Pattern | Root Cause | Fix |
|--------------|------------|-----|
| `UPDATE_FAILED` | Code error in DLT notebook | Get events: `databricks pipelines list-pipeline-events <PID> --output json \| jq '[.events[] \| select(.level == "ERROR")]'`. Read error message, fix notebook, redeploy. |
| Rows dropped by expectations | DQ rule violation (expected behavior) | Check expectation definitions. Investigate dropped rows in quarantine table if using `expect_or_drop`. If unexpected, check source data quality. |
| `Streaming source not found` / `TABLE_OR_VIEW_NOT_FOUND` | Missing upstream Bronze/Silver table | Run Bronze/Silver setup job first. Verify source table name matches. |
| `Schema mismatch` / `AnalysisException` | Column type changed upstream | Update DLT notebook to handle new schema, or fix upstream source. Use `schema="overwrite"` in pipeline config if appropriate. |
| `ConcurrentAppendException` | Multiple writers to same Delta table | Add retry logic with `@dlt.table(spark_conf={"spark.databricks.delta.retryWriteConflict.enabled": "true"})`. Or serialize writes by using task dependencies. |
| `StreamingQueryException: checkpoint` | Checkpoint corruption or schema change | Clear checkpoint: delete checkpoint directory from DBFS/volumes. Restart pipeline with `full_refresh: true`. |
| Pipeline stuck in RUNNING state | Update hung or long-running | Cancel update: `databricks pipelines stop <PID>`. Check cluster events. Retry with `full_refresh: false`. |
| `FileNotFoundException` | Source file moved/deleted | Verify file path. For Auto Loader sources, check cloud storage permissions and path. |
| `CONSTRAINT_VIOLATION` | NOT NULL or CHECK constraint violated | Fix source data or adjust constraints. |
| `OutOfMemoryError` during DLT | Large table + small cluster | Enable Photon, increase cluster size in pipeline config, or add partitioning. |
| Expectations table not populated | DLT expectations not stored | Ensure expectations are defined using `@dlt.expect_all()` or similar decorators. Check expectations are stored in Unity Catalog Delta table. |

### DLT Pipeline Event Analysis Pattern

```bash
# Get all ERROR events from a pipeline
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.level == "ERROR") | {
    timestamp: .timestamp,
    message: .message,
    error: .error.exceptions
  }] | .[0:5]'

# Get flow progress (shows expectation results)
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.event_type == "flow_progress") | {
    flow: .origin.flow_name,
    status: .details.flow_progress.status,
    metrics: .details.flow_progress.metrics
  }] | .[0:10]'

# Get update status
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.event_type == "update_progress") | {
    status: .details.update_progress.state,
    message: .message
  }] | .[0:5]'
```

---

## 3. Lakehouse Monitor Failures

| Error Pattern | Root Cause | Fix |
|--------------|------------|-----|
| `ResourceAlreadyExists` | Monitor already exists for table | Delete first: `w.quality_monitors.delete(table_name="catalog.schema.table")`. Also drop output tables: `DROP TABLE IF EXISTS catalog.schema.table_profile_metrics; DROP TABLE IF EXISTS catalog.schema.table_drift_metrics;`. Then recreate. |
| `ResourceDoesNotExist` | Table not found in Unity Catalog | Verify full table name. Check table exists: `SHOW TABLES IN catalog.schema LIKE 'table_name'`. Check permissions. |
| `SCHEMA_NOT_FOUND` | Monitoring output schema missing | Create it: `CREATE SCHEMA IF NOT EXISTS catalog.monitoring_schema`. Ensure `spark` is passed to monitor creation function. |
| `PERMISSION_DENIED` | Insufficient permissions on source table | Grant MANAGE permission: `GRANT SELECT, MODIFY ON TABLE ... TO ...`. |
| `Column 'X' does not exist` | Wrong column name in metric definition | Fix column name. Verify against `DESCRIBE TABLE catalog.schema.table`. |
| Custom metrics return NULL | No data in time window | Check source table date range: `SELECT MIN(ts), MAX(ts) FROM table`. Verify timestamp column name matches monitor config. |
| DERIVED metrics NULL but AGGREGATEs populated | Referenced AGGREGATE metric missing or zero | DERIVED metrics reference AGGREGATEs by exact name. Verify the referenced metric exists and has non-NULL values. |
| Output tables don't appear after 30+ min | Monitor initialization failed silently | Check monitor status: `SELECT status FROM system.information_schema.lakehouse_monitors WHERE table_name = 'X'`. Trigger manual refresh: `w.quality_monitors.run_refresh(table_name="...")`. |
| Monitor creation timeout (>30 min) | Source table too large | Increase job timeout. Ensure source table has proper clustering on timestamp column. Reduce slicing dimensions. |
| Query returns empty results | Missing required filters | **Always include:** `column_name = ':table'` (for custom metrics), `log_type = 'INPUT'` (for source data). See query patterns below. |
| Drift metrics all NULL | Only 1 period of data exists | Drift requires 2+ periods. Wait for second refresh cycle. Query with: `WHERE drift_type = 'CONSECUTIVE'`. |
| Sliced queries return duplicates | Missing slice_key filter | Add explicit `slice_key = 'dimension_name'` filter. Or use `slice_key IS NULL` for overall metrics. |

### Critical Monitoring Query Patterns

```sql
-- CORRECT: Custom metrics query (ALL filters required)
SELECT *
FROM catalog.monitoring_schema.table_profile_metrics
WHERE column_name = ':table'      -- REQUIRED for custom metrics
  AND log_type = 'INPUT'          -- REQUIRED for source data
  AND slice_key IS NULL;          -- For overall (non-sliced) metrics

-- Sliced metrics (e.g., by workspace)
SELECT *
FROM catalog.monitoring_schema.table_profile_metrics
WHERE column_name = ':table'
  AND log_type = 'INPUT'
  AND slice_key = 'workspace_id';  -- Be explicit about which slice

-- Drift metrics
SELECT *
FROM catalog.monitoring_schema.table_drift_metrics
WHERE drift_type = 'CONSECUTIVE'   -- REQUIRED for period-over-period
  AND column_name = ':table';
```

---

## 4. SQL Alert Failures

| Error Pattern | Root Cause | Fix |
|--------------|------------|-----|
| `HTTP 400: Alert with name 'X' already exists` | Duplicate alert | Use update instead of create. Check sync status table and update existing alert. |
| `HTTP 400: Update mask is required` | Missing update_mask in PATCH request | Include full mask: `update_mask="display_name,query_text,warehouse_id,condition,notification,schedule"` |
| `HTTP 404: Not found` | Wrong API endpoint | Use `/api/2.0/alerts` (NOT `/api/2.0/sql/alerts` or `/api/2.0/sql/alerts-v2`) |
| Alert never triggers | Wrong condition/threshold/schedule or alert is PAUSED | 1. Run query manually — does it return rows? 2. Check condition logic (operator direction). 3. Verify `pause_status` is `UNPAUSED`. 4. Check warehouse is running. |
| Notification not received | Missing destination config | Check `databricks_destination_id` is populated in notification_destinations table. Run notification sync job. |
| Partial success (some alerts fail) | Individual alert errors | Check: `SELECT alert_id, last_sync_error FROM alert_configurations WHERE last_sync_status = 'ERROR'`. Fix individual alerts and re-run deploy job. |
| `PARSE_SYNTAX_ERROR` in alert query | SQL syntax error in template | Test query manually first. Use EXPLAIN to validate: `EXPLAIN SELECT ...`. Fix template and re-seed. |
| `%` in LIKE pattern breaks INSERT | SQL escaping issue | Use DataFrame-based insertion instead of SQL INSERT: `df.write.mode("append").saveAsTable("alert_configurations")`. |
| Sync takes >5 minutes | Too many sequential API calls | Enable parallel sync in job parameters: `enable_parallel: "true"`, `parallel_workers: "10"`. Watch for API rate limits. |
| Wrong V2 field names | Schema mismatch with older docs | V2 uses: `evaluation` (not `condition`), `comparison_operator` (not `op`), `quartz_cron_schedule` (not `quartz_cron_expression`). Verify with: `databricks bundle schema \| grep -A 100 'sql.AlertV2'`. |

---

## 5. Deployment Failures (Asset Bundle)

| Error Pattern | Root Cause | Fix |
|--------------|------------|-----|
| `Invalid access token (403)` | Token expired | Re-authenticate: `databricks auth login --host <workspace-url> --profile <name>` |
| `python_task` not recognized | Invalid task type | Change to `notebook_task` with `notebook_path`. NEVER use `python_task` with `python_file`. |
| Parameter not found / required | CLI-style parameters in YAML | Change `parameters: ["--catalog=X"]` to `base_parameters: {catalog: X}` |
| Path resolution error | Wrong relative depth from YAML | From `resources/*.yml` → `../src/`. From `resources/<layer>/*.yml` → `../../src/`. From `resources/<layer>/<sub>/*.yml` → `../../../src/`. |
| `job_task` not recognized | Wrong reference field name | Use `run_job_task`, NOT `job_task` |
| Duplicate resource conflict | Same YAML in multiple directories | Remove duplicate. Keep single source of truth in one location. |
| `Bundle validation failed` | Syntax or config error | Run `databricks bundle validate`. Fix all reported errors. |
| Missing `var.` prefix | `${catalog}` instead of `${var.catalog}` | Always use `${var.<variable_name>}` format |
| DLT library path error | Library path outside root_path | All DLT pipeline library paths MUST be within `root_path` |
| Missing include paths | New subdirectory not in `databricks.yml` | Add `resources/<new-dir>/*.yml` to `include:` in `databricks.yml` |
| argparse error in notebook | Using argparse instead of dbutils | Use `dbutils.widgets.get("param")` for parameters. NEVER use argparse in DAB notebooks. |
| SQL task inline error | Inline SQL in sql_task | Use `file.path` or `query.query_id`. Never inline SQL strings in sql_task. |
| Volume permissions error | Using `permissions` instead of `grants` | Volumes use `grants` with `privileges: [READ_VOLUME]`, NOT `permissions`. |
| App env vars not set | Env vars in databricks.yml | Define env vars in `app.yaml` (source directory), NOT in the DAB resource file. |
| Dashboard hardcoded catalog | Missing dataset_catalog/dataset_schema | Add `dataset_catalog: ${var.catalog}` and `dataset_schema: ${var.schema}` (CLI v0.281.0+). |

---

## 6. Dependency Ordering Failures

**Required Deployment Order:**
```
1. Bronze Setup → Non-streaming tables
2. Silver DLT Pipeline → Streaming ingestion
3. Gold Setup → Create tables (DDL)
4. Gold Merge → Populate tables
5. Semantic Layer → TVFs + Metric Views
6. Monitoring → Lakehouse Monitors (need populated Gold tables)
7. Alerting → SQL Alerts (need monitoring output tables)
8. Genie Spaces → Need semantic layer + Gold tables
```

| Error Pattern | Root Cause | Fix |
|--------------|------------|-----|
| `Failed to retrieve schema from unity catalog` | Upstream assets (TVFs/Metric Views/tables) not deployed | Follow deployment order above. Deploy missing upstream layer first. |
| Genie Space API `INTERNAL_ERROR` with empty message | TVFs and/or Metric Views don't exist in catalog | Deploy semantic layer first: `databricks bundle run -t dev semantic_layer_setup_job` |
| Gold merge fails with `TABLE_NOT_FOUND` | Gold table DDL not created | Run `gold_setup_job` BEFORE `gold_merge_job` |
| Monitor creation fails on missing source table | Gold tables not populated | Run Gold setup + merge before monitoring setup |
| Alert queries fail with `TABLE_NOT_FOUND` | Monitoring output tables don't exist | Run monitoring setup before alert deployment |
| Genie benchmark SQL fails | Underlying tables have no data | Run full pipeline (Bronze → Gold → Merge) before Genie validation |

---

## 7. Cluster Issues

| Error Pattern | Root Cause | Fix |
|--------------|------------|-----|
| `DRIVER_UNREACHABLE` | Cluster driver crashed | Check events: `databricks clusters events <ID> --output json`. Look for OOM, spot termination. Resize driver or change node type. |
| `OutOfMemoryError` / `java.lang.OutOfMemoryError` | Insufficient memory | Increase driver/worker memory. Optimize query (add filters, reduce shuffle). Add `.repartition(n)` for large DataFrames. |
| Cluster startup timeout | Cloud provider capacity issue | Retry. Try different availability zone. Use fallback node types in cluster policy. |
| `Library installation failed` | Package version conflict | Check library versions for compatibility. Use `%pip install` in notebook instead of cluster-level libraries. |
| `Cluster terminated (SPOT_INSTANCE_LOST)` | Spot instance reclaimed by cloud provider | Use on-demand instances for critical jobs. Or set `availability: ON_DEMAND` in cluster spec. |
| `Cluster terminated (INIT_SCRIPT_FAILURE)` | Init script error | Check init script logs. Simplify or remove init scripts. Use `%pip install` instead. |
| `MAX_CLUSTERS_REACHED` | Cluster pool exhausted | Wait and retry. Or increase max clusters in workspace settings (admin). |

---

## Error Categorization Quick Reference

When you encounter an error, categorize first:

| Category | Indicators | Section |
|----------|-----------|---------|
| **Job Runtime** | Stack trace in Python/SQL, `state.result_state == "FAILED"` | 1 |
| **DLT Pipeline** | Pipeline `UPDATE_FAILED`, events with `level == "ERROR"` | 2 |
| **Monitor** | `quality_monitors` API error, NULL metrics | 3 |
| **Alert** | HTTP 400/404, alert not triggering | 4 |
| **Deployment** | `bundle validate/deploy` failure, YAML errors | 5 |
| **Dependency** | `TABLE_NOT_FOUND` before setup, `Failed to retrieve schema` | 6 |
| **Cluster** | `DRIVER_UNREACHABLE`, OOM, startup failure | 7 |

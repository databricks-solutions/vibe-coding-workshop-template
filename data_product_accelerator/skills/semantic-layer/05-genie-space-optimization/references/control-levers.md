# Control Levers Reference

Detailed patterns for each of the six Genie optimization control levers, including SQL commands, API calls, and repository file mappings for dual persistence.

---

## Priority Order Rationale

| Priority | Lever | Why This Order |
|----------|-------|----------------|
| **1** | UC Tables & Columns | Most durable - survives Space rebuilds, unlimited text |
| **2** | Metric Views | Pre-aggregated, rich semantics, high discoverability |
| **3** | TVFs (Functions) | Parameterized logic, good for complex queries |
| **4** | Monitoring Tables | Time-series specific, medium discoverability |
| **5** | ML Model Tables | Prediction-specific, medium discoverability |
| **6** | Genie Instructions | ~4000 char limit, least durable, last resort |

---

## Lever 1: UC Table & Column Comments

**When to use:** Genie misunderstands column meaning, selects wrong table, or generates incorrect joins.

### Direct Update (Immediate)

```sql
-- Update table description
ALTER TABLE ${catalog}.${schema}.fact_usage
SET TBLPROPERTIES ('comment' = 'Daily workspace compute usage at workspace-SKU-date grain. Primary cost tracking table. Use for: total spend, cost breakdown by workspace/SKU, cost trends over time.');

-- Update column description
ALTER TABLE ${catalog}.${schema}.fact_usage
ALTER COLUMN total_dbus COMMENT 'Total Databricks Units consumed. 1 DBU = 1 unit of compute capacity per hour. Higher DBUs = higher cost. Use SUM(total_dbus) for total consumption.';

-- Add enum values to column description
ALTER TABLE ${catalog}.${schema}.dim_sku
ALTER COLUMN sku_category COMMENT 'SKU pricing category. Values: JOBS_COMPUTE, SQL_COMPUTE, DLT_COMPUTE, MODEL_SERVING, SERVERLESS_SQL, ALL_PURPOSE. Use for cost segmentation.';
```

### Repository Update (Dual Persistence)

Update the Gold layer YAML file:

```yaml
# gold_layer_design/yaml/cost/fact_usage.yaml
table_name: fact_usage
comment: "Daily workspace compute usage at workspace-SKU-date grain..."
columns:
  - name: total_dbus
    type: DECIMAL(18,4)
    comment: "Total Databricks Units consumed..."
```

### What to Fix

| Issue | Fix Pattern |
|-------|-------------|
| Column purpose unclear | Add business context to COMMENT |
| Enum values unknown | List all valid values in COMMENT |
| Join relationships unclear | Reference FK targets in table COMMENT |
| Aggregation ambiguity | Specify "Use SUM/AVG/COUNT for..." in COMMENT |

---

## Lever 2: Metric Views

**When to use:** Aggregation queries return wrong results, or Genie doesn't use pre-built metrics.

### Direct Update (Immediate)

Redeploy the metric view:

```python
# Run metric view creation script
# This replaces the view with updated definitions
spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_cost_analytics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1
source: {catalog}.{schema}.fact_usage
dimensions:
  - name: workspace_name
    expr: workspace_name
    description: "Workspace display name for filtering and grouping"
measures:
  - name: total_cost
    expr: "SUM(total_cost_usd)"
    description: "Total cost in USD. Use MEASURE(total_cost) for overall spend."
  - name: avg_daily_cost
    expr: "AVG(total_cost_usd)"
    description: "Average daily cost. Use for trend analysis."
$$
""")
```

### Repository Update (Dual Persistence)

```yaml
# src/semantic/metric_views/mv_cost_analytics.yaml
version: 1
source: ${catalog}.${gold_schema}.fact_usage
dimensions:
  - name: workspace_name
    expr: workspace_name
    description: "Workspace display name for filtering and grouping"
measures:
  - name: total_cost
    expr: "SUM(total_cost_usd)"
    description: "Total cost in USD. Use MEASURE(total_cost) for overall spend."
```

### What to Fix

| Issue | Fix Pattern |
|-------|-------------|
| Wrong aggregation function | Update measure `expr` (SUM vs AVG vs COUNT) |
| Missing dimension | Add dimension to YAML |
| Poor measure description | Add "Use MEASURE(name) for..." to description |
| Metric not discovered | Ensure metric view is added as trusted asset |

---

## Lever 3: TVFs (Table-Valued Functions)

**When to use:** Parameterized queries fail, wrong parameters used, or TVF not selected by Genie.

### Direct Update (Immediate)

```sql
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.get_top_cost_contributors(
  days_back STRING,
  group_by_column STRING
)
RETURNS TABLE
-- Returns top cost contributors grouped by the specified dimension.
-- Parameters:
--   days_back: Number of days to look back (e.g., '7', '30', '90')
--   group_by_column: Grouping dimension. Valid values: 'workspace', 'sku', 'cluster'
-- Usage:
--   SELECT * FROM get_top_cost_contributors('30', 'workspace')
--   Returns: contributor_name, total_cost, percentage_of_total, rank
-- When to use:
--   "top costliest", "most expensive", "biggest spenders", "cost breakdown"
RETURN
  SELECT ...
```

### Repository Update (Dual Persistence)

```sql
-- src/semantic/tvfs/get_top_cost_contributors.sql
CREATE OR REPLACE FUNCTION ${catalog}.${gold_schema}.get_top_cost_contributors(
  days_back STRING,
  group_by_column STRING
)
...
```

### What to Fix

| Issue | Fix Pattern |
|-------|-------------|
| TVF not selected | Improve COMMENT with "When to use" section |
| Wrong parameters | Fix parameter names/descriptions in COMMENT |
| Missing use cases | Add example queries to COMMENT |
| Wrong return columns | Update RETURN clause and document in COMMENT |

---

## Lever 4: Monitoring Tables

**When to use:** Time-series or monitoring queries return wrong data.

### Direct Update

```sql
ALTER TABLE ${catalog}.${monitoring_schema}.fact_usage_profile_metrics
SET TBLPROPERTIES ('comment' = 'Lakehouse Monitoring profile metrics for fact_usage. Contains statistical profiles (min, max, mean, stddev) computed daily. Use for: data quality trends, anomaly detection, drift analysis. Granularity: one row per column per monitoring window.');
```

### Repository Update

Update monitoring configuration in `src/monitoring/*.py` (METRIC_DESCRIPTIONS dict).

---

## Lever 5: ML Model Tables

**When to use:** Prediction or ML-related queries return wrong data.

### Direct Update

```sql
ALTER TABLE ${catalog}.${feature_schema}.model_predictions
SET TBLPROPERTIES ('comment' = 'ML model prediction outputs. Contains batch inference results from registered MLflow models. Use for: prediction queries, model performance analysis, feature importance.');
```

### Repository Update

Update ML config in `src/ml/config/*.py`.

---

## Lever 6: Genie Instructions

**When to use:** Asset routing issues, ambiguous term definitions, or as a last resort after levers 1-5.

### Direct Update (API)

```python
import json
import subprocess

SPACE_ID = "01f0f1a3c2dc1c8897de11d27ca2cb6f"

# 1. Read current config
with open(f"src/genie/{domain}_genie_export.json", "r") as f:
    config = json.load(f)

# 2. Update instructions
instructions = """You are a cost intelligence analyst. Follow these STRICT rules:

=== ASSET ROUTING ===
1. Total spend / overall cost → USE: mv_cost_analytics (MEASURE)
2. Top contributors / breakdown → USE: get_top_cost_contributors TVF
3. Daily summary / trends → USE: get_daily_cost_summary TVF
4. Workspace details → USE: get_workspace_cost_details TVF

=== DEFAULTS ===
- No date specified → last 7 days
- Date format: 'YYYY-MM-DD' for TVF parameters
- Currency: $ with 2 decimals
- Sort by cost DESC for "top" queries"""

existing_id = config["instructions"]["text_instructions"][0].get("id")
config["instructions"]["text_instructions"] = [
    {"id": existing_id, "content": instructions.split("\n")}
]

# 3. Sort arrays (CRITICAL - API rejects unsorted)
config = sort_genie_config(config)

# 4. Substitute variables
config_json = json.dumps(config)
config_json = config_json.replace("${catalog}", CATALOG)
config_json = config_json.replace("${gold_schema}", GOLD_SCHEMA)
substituted = json.loads(config_json)

# 5. PATCH API
payload = {"serialized_space": json.dumps(substituted)}
with open("/tmp/genie_payload.json", "w") as f:
    json.dump(payload, f)

cmd = [
    "databricks", "api", "patch",
    f"/api/2.0/genie/spaces/{SPACE_ID}",
    "--json", "@/tmp/genie_payload.json"
]
result = subprocess.run(cmd, capture_output=True, text=True)
```

### Repository Update (Dual Persistence)

Re-template variables before saving:

```python
config_json = json.dumps(substituted)
config_json = config_json.replace(CATALOG, "${catalog}")
config_json = config_json.replace(GOLD_SCHEMA, "${gold_schema}")
templated = json.loads(config_json)
templated = sort_genie_config(templated)

with open(f"src/genie/{domain}_genie_export.json", "w") as f:
    json.dump(templated, f, indent=2)
```

### Instruction Writing Best Practices

| Practice | Example |
|----------|---------|
| Group by question type | "Revenue questions: → use mv_revenue" |
| Use explicit routing | "For 'top N' queries → ALWAYS use TVF" |
| Define ambiguous terms | "'underperforming' = below median revenue" |
| Set defaults | "No date → last 7 days" |
| Specify formatting | "Currency: $, 2 decimals" |

---

## Sort Function (Required for API Updates)

```python
def sort_genie_config(config: dict) -> dict:
    """Sort all arrays in Genie config - API rejects unsorted data."""
    if "data_sources" in config:
        for key in ["tables", "metric_views"]:
            if key in config["data_sources"]:
                config["data_sources"][key] = sorted(
                    config["data_sources"][key],
                    key=lambda x: x.get("identifier", "")
                )
    if "instructions" in config:
        if "sql_functions" in config["instructions"]:
            config["instructions"]["sql_functions"] = sorted(
                config["instructions"]["sql_functions"],
                key=lambda x: (x.get("id", ""), x.get("identifier", ""))
            )
        for key in ["text_instructions", "example_question_sqls"]:
            if key in config["instructions"]:
                config["instructions"][key] = sorted(
                    config["instructions"][key],
                    key=lambda x: x.get("id", "")
                )
    if "config" in config and "sample_questions" in config["config"]:
        config["config"]["sample_questions"] = sorted(
            config["config"]["sample_questions"],
            key=lambda x: x.get("id", "")
        )
    if "benchmarks" in config and "questions" in config["benchmarks"]:
        config["benchmarks"]["questions"] = sorted(
            config["benchmarks"]["questions"],
            key=lambda x: x.get("id", "")
        )
    return config
```

---

## Common API Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `data_sources.tables must be sorted` | Arrays not sorted | Call `sort_genie_config()` |
| `instructions.sql_functions must be sorted by (id, identifier)` | Wrong sort key | Sort by tuple `(id, identifier)` |
| `401 Unauthorized` | Auth issue | Use Databricks CLI with correct profile |
| `Invalid export proto` | JSON structure wrong | Verify against reference file |
| `Exceeded maximum number (50)` | Too many TVFs/benchmarks | Truncate to 50 |

---

## Dual Persistence Summary

| Lever | Direct Update Command | Repository Source File |
|-------|----------------------|------------------------|
| UC Tables | `ALTER TABLE ... SET TBLPROPERTIES` | `gold_layer_design/yaml/{domain}/*.yaml` |
| Metric Views | `CREATE OR REPLACE VIEW ... WITH METRICS` | `src/semantic/metric_views/*.yaml` |
| TVFs | `CREATE OR REPLACE FUNCTION` | `src/semantic/tvfs/*.sql` |
| Monitoring | `ALTER TABLE ... SET TBLPROPERTIES` | `src/monitoring/*.py` |
| ML Tables | `ALTER TABLE ... SET TBLPROPERTIES` | `src/ml/config/*.py` |
| Genie Instructions | `PATCH /api/2.0/genie/spaces/{id}` | `src/genie/{domain}_genie_export.json` |

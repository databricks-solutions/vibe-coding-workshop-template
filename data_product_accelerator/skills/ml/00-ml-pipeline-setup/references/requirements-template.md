# ML Project Requirements Template

Fill these in **BEFORE** writing any code. These planning artifacts drive feature table creation, training pipelines, and inference jobs.

---

## Project Context

| Field | Value |
|-------|-------|
| **Project Name** | _________________ (e.g., `health_monitor`) |
| **Catalog** | _________________ (e.g., `my_catalog`) |
| **Gold Schema** | _________________ (e.g., `my_project_gold`) |
| **Feature Schema** | _________________ (e.g., `my_project_features`) |

---

## Feature Tables

Define each feature table with its primary keys, features, and source tables from the Gold layer.

| Feature Table | Primary Keys | Features | Source Tables |
|---------------|--------------|----------|---------------|
| cost_features | workspace_id, usage_date | daily_dbu, daily_cost, avg_dbu_7d | fact_usage |
| security_features | user_id, event_date | event_count, failed_auth_count | fact_audit_logs |
| performance_features | warehouse_id, query_date | query_count, avg_duration_ms | fact_query_history |
| ___________ | ___________ | ___________ | ___________ |
| ___________ | ___________ | ___________ | ___________ |
| ___________ | ___________ | ___________ | ___________ |

**Rules:**
- Primary keys MUST have NOT NULL columns
- All numeric features will be cast to DOUBLE and NaN-cleaned at source
- Feature table names follow pattern: `{catalog}.{feature_schema}.{feature_table_name}`

---

## Model Inventory

Define each model with its type, algorithm, label column, label casting, and associated feature table.

| Model Name | Type | Algorithm | Label Column | Label Type | Feature Table |
|------------|------|-----------|--------------|------------|---------------|
| budget_forecaster | Regression | GradientBoosting | daily_cost | DOUBLE | cost_features |
| cost_anomaly_detector | Anomaly | IsolationForest | (unsupervised) | N/A | cost_features |
| job_failure_predictor | Classification | XGBoost | prev_day_failed | INT | reliability_features |
| ___________ | ___________ | ___________ | ___________ | ___________ | ___________ |
| ___________ | ___________ | ___________ | ___________ | ___________ | ___________ |
| ___________ | ___________ | ___________ | ___________ | ___________ | ___________ |

**Rules:**
- Model names are used in experiment paths: `/Shared/{project}_ml_{model_name}`
- Models are registered to UC as: `{catalog}.{feature_schema}.{model_name}`
- Each model maps to exactly ONE feature table for `FeatureLookup`

---

## Label Type Reference

| Model Type | Label Casting | PySpark | Pandas | Example Labels |
|------------|---------------|---------|--------|----------------|
| **Regression** | DOUBLE | `.cast("double")` | `.astype('float64')` | `daily_cost`, `p99_duration_ms`, `revenue` |
| **Classification** | INT | `.cast("int")` | `.astype(int)` | `is_anomaly`, `prev_day_failed`, `schema_change_risk` |
| **Anomaly Detection** | N/A (unsupervised) | N/A | N/A | No label column — use `label=None` in `create_training_set` |

**Critical Notes:**
- **Regression labels** MUST be cast to DOUBLE before training — MLflow output_schema uses `DataType.double`
- **Classification labels** MUST be cast to INT (binary 0/1) — MLflow output_schema uses `DataType.long`
- **Continuous rates** (0.0-1.0) used for classification MUST be **binarized** first (see data-quality-patterns.md)
- **Anomaly detection** models use `output_schema = Schema([ColSpec(DataType.long)])` with outputs of -1 (anomaly) or 1 (normal)

---

## Derived Artifacts

Once you fill in the tables above, the following are automatically determined:

| Artifact | Derived From |
|----------|-------------|
| Feature table DDL | Feature Tables inventory → `create_feature_tables.py` |
| FeatureLookup configs | Feature Tables primary keys + Model Inventory feature table mapping |
| Training notebooks | Model Inventory → one `train_{model_name}.py` per model |
| Output schemas | Model Inventory label type → `Schema([ColSpec(DataType.xxx)])` |
| Experiment paths | Model Inventory model name → `/Shared/{project}_ml_{model_name}` |
| UC model names | Model Inventory model name → `{catalog}.{feature_schema}.{model_name}` |
| DAB job tasks | Model Inventory → one `task_key` per model in training pipeline job |
| Inference config | Model Inventory → models dict in `batch_inference_all_models.py` |

---

## Example: Completed Template

```
Project Name:    health_monitor
Catalog:         acme_catalog
Gold Schema:     health_monitor_gold
Feature Schema:  health_monitor_features

Feature Tables:
  cost_features         | workspace_id, usage_date    | daily_dbu, daily_cost, avg_dbu_7d    | fact_usage
  reliability_features  | job_id, run_date            | success_rate, avg_duration, failures | fact_job_runs

Models:
  budget_forecaster     | Regression     | GradientBoosting | daily_cost       | DOUBLE | cost_features
  cost_anomaly_detector | Anomaly        | IsolationForest  | (unsupervised)   | N/A    | cost_features
  job_failure_predictor | Classification | XGBoost          | prev_day_failed  | INT    | reliability_features
```

# MLflow ML Models Troubleshooting Guide

## Common Errors and Solutions

### Signature and Model Registration Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `Model passed for registration contained a signature that includes only inputs` | Missing output schema for Unity Catalog | Add `output_schema=Schema([ColSpec(DataType.xxx)])` to `fe.log_model()` |
| `Model passed for registration did not contain any signature metadata` | Neither signature nor output_schema provided | Add `output_schema` AND `infer_input_example=True` |
| `Model signature must contain both input and output` | `infer_signature()` called without predictions | Use `infer_signature(input_example, model.predict(input_example))` |
| `FeatureEngineeringClient.log_model() missing 1 required keyword-only argument: 'flavor'` | Missing flavor parameter | Add `flavor=mlflow.sklearn` (or appropriate flavor) |

### Experiment and Logging Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| Experiment shows as "train" | `/Users/` path failed silently | Use `/Shared/{project}_ml_{model_name}` |
| Dataset not in LoggedModel view | `log_input()` outside run context | Move inside `mlflow.start_run()` |
| Duplicate experiments with `[dev username]` prefix | Asset Bundle experiment definitions | Remove experiments from Asset Bundle YAML |
| `Parent directory does not exist` | User experiment path missing folder | Use `/Shared/` path instead |

### Module and Import Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `ModuleNotFoundError: No module named 'src'` | Serverless path resolution | Add `sys.path` setup block to notebook |
| `ModuleNotFoundError` for helpers | Import from local module | Inline all helper functions in each script |
| `NameError: name 'X' is not defined` | Variable scope issue after refactoring | Ensure all variables are defined before use |

### Feature Store Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `Unable to find feature '{column}'` | Feature name mismatch | Check actual column names in feature table with `DESCRIBE TABLE` |
| `DataFrame contains column names that match feature output names` | Column conflict in FeatureLookup | Remove conflicting columns from input DataFrame before lookup |
| `create_training_set() missing required argument` | API signature changed | Verify correct parameters: `df`, `feature_lookups`, `label` |

### Data Type Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `unsupported operand type(s) for -: 'decimal.Decimal' and 'float'` | Spark DECIMAL not converted | Use `pd.to_numeric(col, errors='coerce')` |
| `DecimalType not supported` | DECIMAL columns in input_example or feature table | Cast to DOUBLE at feature table creation; `X.astype('float64')` at training |
| `Incompatible input types` | Type mismatch between training and inference | Use `fe.score_batch` instead of manual preprocessing |
| `Cannot safely convert bool to float64` | Boolean needs explicit conversion | `df[col].astype('float64')` |
| `Cannot safely convert int64 to float64` | Integer needs explicit conversion | `df[col].astype('float64')` |

### Inference Errors (Training Succeeds but Inference Fails)

| Error | Root Cause | Solution |
|-------|------------|----------|
| `ValueError: Input X contains NaN` | Feature table has NaN, sklearn doesn't handle it | Clean NaN/Inf at **feature table creation**, not just training |
| `GradientBoostingRegressor does not accept missing values encoded as NaN` | sklearn vs XGBoost NaN handling difference | Fill NaN with 0.0 in `create_feature_table()` using `F.coalesce()` |
| `DataFrame is missing required columns` | Model has stale feature metadata | Delete model from UC and retrain with correct feature table |

### Training Errors (XGBoost Specific)

| Error | Root Cause | Solution |
|-------|------------|----------|
| `XGBoostError: base_score must be in (0,1) for the logistic loss` | XGBClassifier received continuous label (0-1 rate) | Binarize label: `when(col("rate") > threshold, 1).otherwise(0)` |
| `ValueError: The least populated class in y has only 0 members` | Single-class data, classifier can't learn | Check label distribution, skip if single-class |
| `ValueError: y should be a 1d array, got an array of shape...` | Label column shape issue | Ensure label is 1D: `y_train.values.ravel()` |

### Schema and Column Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `UNRESOLVED_COLUMN: Column 'X' cannot be resolved` | Column name doesn't exist | Verify against Gold YAML schema before coding |
| `Column 'is_current' cannot be resolved` | Assumed SCD2 table but isn't | Check if table actually has `is_current` column |
| `Label column 'X' was not found in DataFrame` | Label column mismatch | Verify label column exists in training data |
| `KeyError` during inference | Label column included as feature during training | Use `exclude_columns=[LABEL_COLUMN]` in `get_feature_columns()` |

### Job Execution Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| Job SUCCESS but actually failed | No exit signal | Add `dbutils.notebook.exit("SUCCESS")` |
| Job timeout | Long-running training | Increase `timeout_seconds` in job YAML |
| `TypeError: get_standard_tags() missing argument` | Function signature changed | Update all calls to match new signature |

---

## Schema Verification (MANDATORY Before Coding)

### Gold Layer Column Verification Pattern

```python
# ALWAYS verify columns against YAML before coding
# Location: gold_layer_design/yaml/{domain}/{table}.yaml

# Step 1: Read the YAML file
# Step 2: List all columns with types
# Step 3: Check if table is SCD2 (has is_current?)

# Common column name mistakes from this project:
# ❌ destination        → ✅ destination_id       (in dim_property)
# ❌ nights_stayed      → ✅ avg_nights_booked    (in fact_booking_daily)
# ❌ occupancy_rate     → ✅ avg_booking_value    (occupancy_rate doesn't exist)
# ❌ booking_date       → ✅ created_at           (in fact_booking_detail)
# ❌ user_id            → ✅ (doesn't exist)      (in fact_property_engagement)
```

### SCD2 vs Regular Dimension Tables

```python
# =============================================================================
# SCD2 Tables (have is_current column) - FILTER IS REQUIRED
# =============================================================================
# - dim_property
# - dim_user
# - dim_host

# ✅ CORRECT: Filter for current records
dim_property = (
    spark.table(f"{catalog}.{gold_schema}.dim_property")
    .filter(col("is_current") == True)
)

# =============================================================================
# Regular Dimension Tables (NO is_current) - DO NOT FILTER
# =============================================================================
# - dim_destination
# - dim_date
# - dim_weather_location

# ✅ CORRECT: No filter needed
dim_destination = spark.table(f"{catalog}.{gold_schema}.dim_destination")

# ❌ WRONG: Assume all dimensions have is_current
dim_destination.filter(col("is_current"))  # Column doesn't exist!
```

**Error if wrong:** `UNRESOLVED_COLUMN.WITH_SUGGESTION: A column with name 'is_current' cannot be resolved`

### Ambiguous Column Resolution

```python
# When joining tables with same column names, be explicit

# ❌ WRONG: Ambiguous destination_id after join
training_df = (
    fact_booking_daily
    .join(dim_property, "property_id")
    .join(dim_destination, "destination_id")  # Which destination_id?
)

# ✅ CORRECT: Drop ambiguous column before join
fact_for_join = fact_booking_daily.drop("destination_id")
training_df = (
    fact_for_join
    .join(dim_property.select("property_id", "destination_id"), "property_id")
    .join(dim_destination, "destination_id")
)
```

---

## Pre-Development Checklist

- [ ] Verify ALL column names against Gold layer YAML schemas
- [ ] Check if dimension tables are SCD2 (has `is_current`?)
- [ ] Confirm data types (DECIMAL, STRING, BOOLEAN, etc.)
- [ ] Identify categorical columns needing encoding
- [ ] Review Feature Store tables if using feature lookups
- [ ] Document all preprocessing transformations

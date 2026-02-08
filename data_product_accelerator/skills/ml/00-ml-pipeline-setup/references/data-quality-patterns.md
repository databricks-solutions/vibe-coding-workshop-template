# Data Quality Patterns for ML Models

## Critical Rule 6: NaN/Inf Handling at Feature Table Source

**⚠️ ROOT CAUSE OF 3 INFERENCE FAILURES (Jan 2026):** sklearn models fail at inference when feature tables contain NaN.

### The Problem

| Stage | Training | Inference |
|-------|----------|-----------|
| **Data Source** | Feature Table | Feature Table |
| **Processing** | `prepare_training_data()` → `fillna(0)` | `fe.score_batch()` → **No NaN handling** |
| **Result** | Clean data → Model trains ✅ | NaN in data → Crash ❌ |

**Algorithm-specific behavior:**
- **XGBoost**: Handles NaN natively ✅
- **sklearn GradientBoostingRegressor**: Crashes with `ValueError: Input X contains NaN` ❌
- **sklearn GradientBoostingClassifier**: Same issue ❌

**Error message:**
```
ValueError: Input X contains NaN.
GradientBoostingRegressor does not accept missing values encoded as NaN natively.
For supervised learning, you might want to consider sklearn.ensemble.HistGradientBoostingClassifier
and Regressor which accept missing values encoded as NaNs natively.
```

### The Solution: Clean at Feature Table Creation

```python
# In create_feature_table() - clean ALL numeric columns at source
def clean_numeric(col_name):
    """Replace NaN, NULL, and Inf with 0.0 for sklearn compatibility."""
    return F.when(
        F.col(col_name).isNull() | F.isnan(F.col(col_name)) |
        (F.col(col_name) == float('inf')) | (F.col(col_name) == float('-inf')),
        F.lit(0.0)
    ).otherwise(F.col(col_name))

# Apply to ALL DoubleType columns (after cast to DOUBLE)
from pyspark.sql.types import DoubleType

for field in df.schema.fields:
    if isinstance(field.dataType, DoubleType):
        df = df.withColumn(field.name, clean_numeric(field.name))
```

### ✅ CORRECT: Clean at feature table source

```python
# In feature table creation script
def create_feature_table(spark, fe, df, table_name, primary_keys, ...):
    """Create feature table with NaN/Inf cleaned for sklearn compatibility."""
    
    # Cast all numeric to DOUBLE AND clean NaN/Inf
    numeric_types = (IntegerType, LongType, FloatType, DecimalType, ShortType, ByteType)
    double_cols = []
    
    for field in df.schema.fields:
        if isinstance(field.dataType, numeric_types):
            # Cast and clean in one step
            df = df.withColumn(
                field.name,
                F.coalesce(F.col(field.name).cast("double"), F.lit(0.0))
            )
            double_cols.append(field.name)
    
    # Handle existing DOUBLE columns that may have NaN
    for field in df.schema.fields:
        if isinstance(field.dataType, DoubleType) and field.name not in double_cols:
            df = df.withColumn(field.name, clean_numeric(field.name))
    
    print(f"  Cleaned NaN/Inf→0.0 for {len(double_cols)} columns (sklearn compatibility)")
    
    # Write feature table...
```

**Impact of this fix:**
- Before: 3 models failing (`query_performance_forecaster`, `warehouse_optimizer`, `cluster_capacity_planner`)
- After: All 24 models passing inference ✅

---

## Critical Rule 7: Label Binarization for XGBoost Classifiers

**⚠️ XGBClassifier requires binary labels (0 or 1), NOT continuous rates (0.0 to 1.0)**

### The Problem

Many business metrics are rates/ratios (0-1) but XGBClassifier expects discrete classes.

**Error:**
```
XGBoostError: base_score must be in (0,1) for the logistic loss
```

### Standard Binarization Thresholds

| Use Case | Label Column | Threshold | Binarized Label |
|----------|--------------|-----------|-----------------|
| Failure prediction | `failure_rate` | > 0.2 | `high_failure_rate` |
| Success prediction | `success_rate` | > 0.7 | `high_success_rate` |
| SLA breach | `sla_breach_rate` | > 0.1 | `needs_optimization` |
| Serverless adoption | `serverless_adoption_ratio` | > 0.5 | `high_serverless_adoption` |
| Cache efficiency | `spill_rate` | > 0.3 | `high_spill_rate` |

### Pattern: Binarize Before Training

```python
from pyspark.sql.functions import col, when

# Original continuous label (0-1 rate)
LABEL_COLUMN = "failure_rate"

# Binarized label name
BINARIZED_LABEL_COLUMN = "high_failure_rate"

# Threshold for binarization
THRESHOLD = 0.2

def main():
    # ... load training data ...
    
    # ✅ Binarize the continuous label
    training_df = training_df.withColumn(
        BINARIZED_LABEL_COLUMN,
        when(col(LABEL_COLUMN) > THRESHOLD, 1).otherwise(0)
    )
    
    # Use BINARIZED label for classifier
    training_set = fe.create_training_set(
        df=training_df,
        feature_lookups=feature_lookups,
        label=BINARIZED_LABEL_COLUMN,  # ✅ Use binarized column
        exclude_columns=[LABEL_COLUMN]  # Exclude original continuous column
    )
    
    # XGBClassifier now receives 0/1 labels
    model = XGBClassifier(...)
    model.fit(X_train, y_train)
```

---

## Critical Rule 8: Single-Class Data Detection

**⚠️ Classifiers CANNOT train when all samples have the same label**

### The Problem

When your label column has only one unique value (e.g., all 0s or all 1s), the classifier cannot learn any decision boundary.

**Error:**
```
ValueError: The least populated class in y has only 0 members, which is too few.
```

### Pattern: Check Label Distribution Before Training

```python
import json

def check_label_distribution(training_df, label_column):
    """
    Check if label has multiple classes. Skip training if single-class.
    
    Returns: (is_valid, distribution_info)
    """
    label_distribution = training_df.groupBy(label_column).count().collect()
    
    if len(label_distribution) < 2:
        # Single-class data - cannot train classifier
        single_class = label_distribution[0][label_column]
        sample_count = label_distribution[0]["count"]
        
        msg = f"Single-class data: all {sample_count} samples have label={single_class}. Cannot train classifier."
        print(f"⚠️ {msg}")
        
        return False, msg
    
    print(f"  Label distribution: {label_distribution}")
    return True, label_distribution

# In main():
is_valid, distribution = check_label_distribution(training_df, BINARIZED_LABEL_COLUMN)

if not is_valid:
    # Exit gracefully - don't fail the job
    dbutils.notebook.exit(json.dumps({
        "status": "SKIPPED",
        "reason": distribution
    }))
    
# Continue with training...
```

### Root Cause Analysis

**Why single-class data happens:**
1. **Data source limitation**: System tables may not track historical changes (e.g., `schema_changes_7d` always 0)
2. **Threshold too extreme**: All values fall on one side of the threshold
3. **Data quality issue**: Missing or incomplete source data
4. **Time window too short**: Not enough variance in the data

**Solution options:**
1. **Skip model gracefully** (recommended if data is sparse)
2. **Adjust threshold** to create more balanced classes
3. **Expand time window** to capture more variance
4. **Switch to regression** if rate prediction is needed

---

## Critical Rule 9: Feature Column Exclusion During Training

**⚠️ Label columns MUST be excluded from feature set**

### The Problem

If the label column is included as a feature during training, inference will fail because the label is not available at prediction time.

**Error:**
```
ValueError: Input contains NaN.
# or
KeyError: 'label_column_name'
```

### Pattern: Explicit Exclusion

```python
from src.ml.config.feature_registry import FeatureRegistry

registry = FeatureRegistry()

# ✅ CORRECT: Exclude label from features
feature_names = registry.get_feature_columns(
    FEATURE_TABLE, 
    exclude_columns=[LABEL_COLUMN]
)

# ❌ WRONG: Get all columns including label
feature_names = registry.get_feature_columns(FEATURE_TABLE)  # Label may be included!
```

---

## Label Type Reference

| Model Type | Label Casting (PySpark) | Label Casting (Pandas) | MLflow output_schema | Example Labels |
|------------|------------------------|------------------------|---------------------|----------------|
| **Regression** | `.cast("double")` | `.astype('float64')` | `Schema([ColSpec(DataType.double)])` | `daily_cost`, `p99_duration_ms`, `revenue` |
| **Classification** | `.cast("int")` | `.astype(int)` | `Schema([ColSpec(DataType.long)])` | `is_anomaly`, `prev_day_failed`, `schema_change_risk` |
| **Anomaly Detection** | N/A (unsupervised) | N/A | `Schema([ColSpec(DataType.long)])` | No label — use `label=None` in `create_training_set` |

**Rules:**
- Regression labels → DOUBLE before training, output_schema `DataType.double`
- Classification labels → INT (binary 0/1) before training, output_schema `DataType.long`
- Continuous rates (0.0–1.0) used for classification → binarize first (see Rule 7 above)
- Anomaly detection outputs: -1 (anomaly) or 1 (normal) for Isolation Forest

---

## Feature Table Creation Checklist (CRITICAL for Inference)

- [ ] Cast ALL numeric columns to DOUBLE
- [ ] Clean NaN/Inf with `F.coalesce()` at source (sklearn compatibility)
- [ ] Filter NULL primary key rows before writing
- [ ] Add PK constraint after table creation
- [ ] Verify row count after filtering

---

## Training Pipeline Checklist

- [ ] Convert DECIMAL columns: `pd.to_numeric(col, errors='coerce')`
- [ ] Encode categorical columns: `pd.Categorical(col).codes`
- [ ] **Label Binarization**: If using XGBClassifier with 0-1 rate labels, binarize first
- [ ] **Single-Class Check**: Verify label has multiple classes before training classifier
- [ ] **Exclude Labels**: Use `exclude_columns=[LABEL_COLUMN]` when getting feature columns

---

## Batch Inference Checklist

- [ ] **Verify feature table has no NaN**: Check `df.filter(isnan(col)).count() == 0` for numeric columns
- [ ] **Algorithm compatibility**: sklearn models require clean data; XGBoost handles NaN
- [ ] **Error propagation**: Ensure partial failures don't mask as success

---

## Inference Errors (Training Succeeds but Inference Fails)

| Error | Root Cause | Solution |
|-------|------------|----------|
| `ValueError: Input X contains NaN` | Feature table has NaN, sklearn doesn't handle it | Clean NaN/Inf at **feature table creation**, not just training |
| `GradientBoostingRegressor does not accept missing values encoded as NaN` | sklearn vs XGBoost NaN handling difference | Fill NaN with 0.0 in `create_feature_table()` using `F.coalesce()` |
| `DataFrame is missing required columns` | Model has stale feature metadata | Delete model from UC and retrain with correct feature table |

---

## Training Errors (XGBoost Specific)

| Error | Root Cause | Solution |
|-------|------------|----------|
| `XGBoostError: base_score must be in (0,1) for the logistic loss` | XGBClassifier received continuous label (0-1 rate) | Binarize label: `when(col("rate") > threshold, 1).otherwise(0)` |
| `ValueError: The least populated class in y has only 0 members` | Single-class data, classifier can't learn | Check label distribution, skip if single-class |
| `ValueError: y should be a 1d array, got an array of shape...` | Label column shape issue | Ensure label is 1D: `y_train.values.ravel()` |

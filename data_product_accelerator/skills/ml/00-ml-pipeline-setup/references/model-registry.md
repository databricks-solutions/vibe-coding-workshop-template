# MLflow Model Registry Patterns

## Unity Catalog Model Logging with Feature Engineering Client

**⚠️ CRITICAL: When using Feature Store, use `fe.log_model()` NOT direct MLflow logging**

The `fe.log_model()` method embeds feature lookup metadata for automatic inference. Unity Catalog requires BOTH input and output schema specifications.

---

## Pattern by Model Type

```python
from databricks.feature_engineering import FeatureEngineeringClient
from mlflow.types import ColSpec, DataType, Schema
import mlflow

fe = FeatureEngineeringClient()
mlflow.set_registry_uri("databricks-uc")

# =============================================================================
# PATTERN 1: REGRESSION MODELS (with labels, continuous output)
# =============================================================================
# Example: Budget Forecaster, Chargeback Attribution, Revenue Predictor
# Output: double (floating point prediction)

output_schema = Schema([ColSpec(DataType.double)])

fe.log_model(
    model=model,
    artifact_path="model",
    flavor=mlflow.sklearn,  # REQUIRED: specify the ML flavor
    training_set=training_set,
    registered_model_name=f"{catalog}.{schema}.{model_name}",
    infer_input_example=True,  # Automatically infers input schema
    output_schema=output_schema  # Explicitly define output type
)

# =============================================================================
# PATTERN 2: CLASSIFICATION MODELS (with labels, discrete output)
# =============================================================================
# Example: Failure Predictor, Commitment Recommender, Threat Detector
# Output: long (integer class label: 0, 1, 2, etc.)

output_schema = Schema([ColSpec(DataType.long)])

fe.log_model(
    model=model,
    artifact_path="model",
    flavor=mlflow.sklearn,
    training_set=training_set,
    registered_model_name=f"{catalog}.{schema}.{model_name}",
    infer_input_example=True,
    output_schema=output_schema
)

# =============================================================================
# PATTERN 3: ANOMALY DETECTION MODELS (NO labels - label=None in training_set)
# =============================================================================
# Example: Isolation Forest, One-Class SVM, Drift Detector
# Output: long (anomaly indicator: -1 for anomaly, 1 for normal)
# 
# ⚠️ CRITICAL: Models trained WITHOUT labels MUST have output_schema!
# The infer_input_example=True alone is NOT sufficient for unsupervised models.

output_schema = Schema([ColSpec(DataType.long)])  # -1 or 1 for Isolation Forest

fe.log_model(
    model=model,
    artifact_path="model",
    flavor=mlflow.sklearn,
    training_set=training_set,  # This has label=None for anomaly detection
    registered_model_name=f"{catalog}.{schema}.{model_name}",
    infer_input_example=True,
    output_schema=output_schema  # REQUIRED for unsupervised models!
)
```

---

## ❌ Common Mistakes That Cause Signature Errors

```python
# =============================================================================
# ERROR: "Model passed for registration contained a signature that includes only inputs"
# =============================================================================

# ❌ MISTAKE 1: Using mlflow.sklearn.log_model instead of fe.log_model
# This loses feature lineage and may have signature issues
mlflow.sklearn.log_model(
    model,
    artifact_path="model",
    registered_model_name=registered_name
)

# ❌ MISTAKE 2: Using signature parameter instead of output_schema
# Per official docs, signature is NOT recommended for fe.log_model
fe.log_model(
    model=model,
    artifact_path="model",
    flavor=mlflow.sklearn,
    training_set=training_set,
    registered_model_name=registered_name,
    signature=infer_signature(X_train, y_pred)  # NOT recommended!
)

# ❌ MISTAKE 3: Missing output_schema for unsupervised models
# When training_set has label=None, output_schema is REQUIRED
fe.log_model(
    model=model,
    artifact_path="model",
    flavor=mlflow.sklearn,
    training_set=training_set,  # label=None for anomaly detection
    registered_model_name=registered_name,
    infer_input_example=True
    # Missing output_schema! Will fail with signature error
)

# ❌ MISTAKE 4: Missing flavor parameter
fe.log_model(
    model=model,
    artifact_path="model",
    training_set=training_set,
    registered_model_name=registered_name
    # Missing flavor=mlflow.sklearn! Will fail with "missing required argument"
)

# ❌ MISTAKE 5: Using pd.DataFrame() constructor instead of .head()
# This can cause type issues
input_example = pd.DataFrame(X_train[:5])  # May lose dtypes
predictions = model.predict(X_train[:5])   # Different object!

# ✅ CORRECT: Use .head() consistently
input_example = X_train.head(5).astype('float64')
predictions = model.predict(input_example)  # Same object
```

---

## Alternative: Using infer_signature (Works but Less Reliable)

```python
# This pattern ALSO works but is less recommended per official docs
# Use when you need compatibility with non-feature-store models

input_example = X_train.head(5).astype('float64')
predictions = model.predict(input_example)
signature = infer_signature(input_example, predictions)

# Must disable autolog to avoid conflicts
mlflow.autolog(disable=True)

with mlflow.start_run(run_name=run_name) as run:
    fe.log_model(
        model=model,
        artifact_path="model",
        flavor=mlflow.sklearn,
        training_set=training_set,
        registered_model_name=registered_name,
        input_example=input_example,
        signature=signature  # Both input AND output must be present
    )
```

---

## DataType Reference for output_schema

| Model Type | Python Output | MLflow DataType | Example |
|---|---|---|---|
| Regression | float | `DataType.double` | Price prediction |
| Binary Classification | int (0,1) | `DataType.long` | Churn prediction |
| Multi-class Classification | int (0,1,2...) | `DataType.long` | Category prediction |
| Anomaly Detection | int (-1,1) | `DataType.long` | Isolation Forest |
| Probability | float [0,1] | `DataType.double` | predict_proba |

---

## Model Registration Pattern (Without Feature Store)

```python
# Set registry URI (at module level, before any MLflow calls)
mlflow.set_registry_uri("databricks-uc")

# 3-level naming convention (REQUIRED for UC)
registered_model_name = f"{catalog}.{schema}.{model_name}"

# Log with signature (REQUIRED for UC)
mlflow.xgboost.log_model(
    model,
    artifact_path="model",
    signature=infer_signature(X_train.head(5), model.predict(X_train.head(5))),
    input_example=X_train.head(5),
    registered_model_name=registered_model_name  # Auto-registers to UC
)
```

---

## Loading Models from UC

```python
# Load specific version
model_uri = f"models:/{catalog}.{schema}.{model_name}/1"
model = mlflow.pyfunc.load_model(model_uri)

# Load by alias (if set)
model_uri = f"models:/{catalog}.{schema}.{model_name}@production"

# Load latest version (requires additional lookup)
client = mlflow.tracking.MlflowClient()
versions = client.search_model_versions(f"name='{catalog}.{schema}.{model_name}'")
latest = max(versions, key=lambda v: int(v.version))
model_uri = f"models:/{catalog}.{schema}.{model_name}/{latest.version}"
```

---

## Batch Inference: Signature-Driven Preprocessing

The batch inference script must replicate EXACT preprocessing from training. Type mismatches are the #1 cause of inference failures.

```python
def load_model_and_signature(catalog: str, feature_schema: str, model_name: str, model_version: str):
    """Load model and extract signature to know exact expected schema."""
    
    full_model_name = f"{catalog}.{feature_schema}.{model_name}"
    
    if model_version == "latest":
        # Get latest version
        client = mlflow.tracking.MlflowClient()
        versions = client.search_model_versions(f"name='{full_model_name}'")
        if versions:
            latest_version = max(versions, key=lambda v: int(v.version))
            model_uri = f"models:/{full_model_name}/{latest_version.version}"
        else:
            raise Exception(f"No model versions found for {full_model_name}")
    else:
        model_uri = f"models:/{full_model_name}/{model_version}"
    
    # Load model to get signature
    model = mlflow.pyfunc.load_model(model_uri)
    signature = model.metadata.signature
    
    print(f"Model Signature:")
    print(f"  Input columns: {[inp.name for inp in signature.inputs]}")
    print(f"  Input types: {[(inp.name, str(inp.type)) for inp in signature.inputs]}")
    
    return model, model_uri, signature


def prepare_features_for_signature(pdf: pd.DataFrame, signature):
    """
    Prepare features to EXACTLY match model's expected signature.
    
    CRITICAL: Type mismatches cause inference failures.
    """
    expected_cols = {inp.name: str(inp.type) for inp in signature.inputs}
    
    for col_name, col_type in expected_cols.items():
        if col_name not in pdf.columns:
            print(f"⚠️  Missing column: {col_name}")
            # Add with appropriate default
            if 'double' in col_type or 'float' in col_type:
                pdf[col_name] = 0.0
            elif 'long' in col_type or 'integer' in col_type:
                pdf[col_name] = 0
            elif 'boolean' in col_type:
                pdf[col_name] = False
            continue
        
        # Type conversions
        if 'float32' in col_type:
            pdf[col_name] = pdf[col_name].astype('float32')
        elif 'float64' in col_type or 'double' in col_type:
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce').fillna(0.0).astype('float64')
        elif 'bool' in col_type:
            if pdf[col_name].dtype in ['int64', 'float64']:
                pdf[col_name] = pdf[col_name].astype(bool)
        elif 'long' in col_type:
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce').fillna(0).astype('int64')
        elif 'integer' in col_type:
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce').fillna(0).astype('int32')
    
    # Select ONLY columns in signature, in signature order
    signature_col_names = [inp.name for inp in signature.inputs]
    pdf_final = pdf[signature_col_names]
    
    return pdf_final
```

---

## Common Type Conversion Issues (from Production)

```python
# =============================================================================
# All type conversion issues discovered in batch inference
# =============================================================================

# Issue 1: Spark DECIMAL → Python float (affects all models)
# Error: unsupported operand type(s) for -: 'decimal.Decimal' and 'float'
pdf['revenue'] = pd.to_numeric(pdf['revenue'], errors='coerce')

# Issue 2: Boolean → float64 (Customer LTV model expects this)
# Error: Cannot safely convert bool to float64
pdf['is_business'] = pdf['is_business'].astype('float64')
pdf['is_repeat'] = pdf['is_repeat'].astype('float64')

# Issue 3: int64 → float64 (Customer LTV model)
# Error: Cannot safely convert int64 to float64
pdf['total_bookings'] = pdf['total_bookings'].astype('float64')

# Issue 4: float64 → float32 (Demand Predictor trained with float32)
# Error: Cannot safely convert float64 to float32
pdf['base_price'] = pdf['base_price'].astype('float32')

# Issue 5: float64 → bool (Conversion Predictor)
# Error: Cannot safely convert float64 to bool
pdf['is_weekend'] = pdf['is_weekend'].astype(bool)

# Issue 6: Categorical encoding must match training
# Error: Incompatible input types for column property_type
pdf['property_type'] = pd.Categorical(pdf['property_type']).codes
```

---

## Signature and Model Registration Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `Model passed for registration contained a signature that includes only inputs` | Missing output schema for Unity Catalog | Add `output_schema=Schema([ColSpec(DataType.xxx)])` to `fe.log_model()` |
| `Model passed for registration did not contain any signature metadata` | Neither signature nor output_schema provided | Add `output_schema` AND `infer_input_example=True` |
| `Model signature must contain both input and output` | `infer_signature()` called without predictions | Use `infer_signature(input_example, model.predict(input_example))` |
| `FeatureEngineeringClient.log_model() missing 1 required keyword-only argument: 'flavor'` | Missing flavor parameter | Add `flavor=mlflow.sklearn` (or appropriate flavor) |

---

## Data Type Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `unsupported operand type(s) for -: 'decimal.Decimal' and 'float'` | Spark DECIMAL not converted | Use `pd.to_numeric(col, errors='coerce')` |
| `Incompatible input types` | Type mismatch between training and inference | Use signature-driven preprocessing |
| `Cannot safely convert bool to float64` | Boolean needs explicit conversion | `df[col].astype('float64')` |
| `Cannot safely convert int64 to float64` | Integer needs explicit conversion | `df[col].astype('float64')` |

---

## Complete Example: log_model_with_feature_engineering()

This function combines tags, params, metrics, and `fe.log_model()` with `output_schema` (the primary approach) into a single reusable pattern.

```python
from databricks.feature_engineering import FeatureEngineeringClient
from mlflow.types import ColSpec, DataType, Schema
import mlflow
import pandas as pd
from datetime import datetime


def log_model_with_feature_engineering(
    fe: FeatureEngineeringClient,
    model,
    training_set,
    X_train: pd.DataFrame,
    metrics: dict,
    hyperparams: dict,
    catalog: str,
    feature_schema: str,
    model_name: str,
    domain: str,
    model_type: str,
    algorithm: str,
    use_case: str,
    feature_table: str
):
    """
    Log model using fe.log_model for automatic feature retrieval at inference.
    
    ⚠️ CRITICAL: This embeds feature lookup metadata in the model.
    ⚠️ Uses output_schema (PRIMARY approach) — not infer_signature.
    """
    registered_name = f"{catalog}.{feature_schema}.{model_name}"
    
    print(f"\n{'='*80}")
    print(f"Logging Model with Feature Engineering: {registered_name}")
    print(f"{'='*80}")
    
    # Determine output_schema from model type
    if model_type == "regression":
        output_schema = Schema([ColSpec(DataType.double)])
    else:  # classification or anomaly detection
        output_schema = Schema([ColSpec(DataType.long)])
    
    mlflow.autolog(disable=True)
    
    run_name = f"{model_name}_{algorithm}_v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with mlflow.start_run(run_name=run_name) as run:
        # Set tags
        mlflow.set_tags({
            "project": "{project}",
            "domain": domain,
            "model_name": model_name,
            "model_type": model_type,
            "algorithm": algorithm,
            "layer": "ml",
            "use_case": use_case,
            "feature_engineering": "unity_catalog",
            "training_data": feature_table
        })
        
        # Log params and metrics
        mlflow.log_params(hyperparams)
        mlflow.log_metrics(metrics)
        
        # ⚠️ CRITICAL: Use fe.log_model with output_schema (PRIMARY approach)
        fe.log_model(
            model=model,
            artifact_path="model",
            flavor=mlflow.sklearn,
            training_set=training_set,  # Embeds feature lookup spec
            registered_model_name=registered_name,
            infer_input_example=True,   # Automatically infers input schema
            output_schema=output_schema  # REQUIRED for UC
        )
        
        print(f"✓ Model logged with Feature Engineering metadata")
        print(f"  Run ID: {run.info.run_id}")
        print(f"  Registered: {registered_name}")
        
        return {
            "run_id": run.info.run_id,
            "model_name": model_name,
            "registered_as": registered_name,
            "metrics": metrics
        }
```

**Note:** The `infer_signature` alternative (see above) can also work with `fe.log_model()` by passing `signature=infer_signature(input_example, predictions)` and `input_example=input_example`. However, the `output_schema` + `infer_input_example=True` approach is more reliable and recommended per official docs.

---

## Official Documentation Reference

- [FeatureEngineeringClient.log_model API](https://api-docs.databricks.com/python/feature-engineering/latest/feature_engineering.client.html)
- Key Parameters:
  - `flavor`: REQUIRED - the MLflow model flavor (e.g., `mlflow.sklearn`)
  - `training_set`: TrainingSet object from `create_training_set()`
  - `output_schema`: REQUIRED for models without labels (unsupervised)
  - `infer_input_example`: RECOMMENDED over manual `signature` parameter
  - `registered_model_name`: 3-level UC name: `catalog.schema.model_name`

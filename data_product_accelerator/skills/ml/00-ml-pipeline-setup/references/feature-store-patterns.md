# Databricks Feature Store Patterns

## Feature Table Creation

```python
from databricks.feature_engineering import FeatureEngineeringClient

fe = FeatureEngineeringClient()

# ✅ CORRECT: Primary keys without timestamp_keys
fe.create_table(
    name=f"{catalog}.{feature_schema}.property_features",
    primary_keys=["property_id"],  # Single key
    df=property_features_df,
    description="Property-level features for ML models"
)

# ✅ CORRECT: Composite primary key for time-series
fe.create_table(
    name=f"{catalog}.{feature_schema}.engagement_features",
    primary_keys=["property_id", "engagement_date"],  # Composite key
    df=engagement_features_df,
    description="Daily engagement features"
)

# ❌ WRONG: timestamp_keys was removed in newer versions
fe.create_table(
    name=feature_table_name,
    primary_keys=["property_id"],
    timestamp_keys=["feature_date"],  # ❌ Not supported anymore
    df=features_df
)
```

---

## Feature Lookup Pattern

```python
from databricks.feature_engineering import FeatureLookup

# Define feature lookups
feature_lookups = [
    FeatureLookup(
        table_name=f"{catalog}.{feature_schema}.property_features",
        feature_names=["bedrooms", "base_price", "bookings_30d"],
        lookup_key="property_id"
    ),
    FeatureLookup(
        table_name=f"{catalog}.{feature_schema}.engagement_features",
        feature_names=["view_count", "click_count", "conversion_rate"],
        lookup_key=["property_id", "engagement_date"]  # Composite key
    )
]

# Create training set with feature lookups
training_set = fe.create_training_set(
    df=labels_df,
    feature_lookups=feature_lookups,
    label="target_column"
)
```

---

## Feature Store Error: Column Conflict

```python
# ❌ WRONG: DataFrame already has columns that FeatureLookup will add
labels_df = (
    base_df
    .withColumn("day_of_week", dayofweek("date"))  # ❌ This exists in engagement_features!
    .withColumn("is_weekend", ...)
)

# ✅ CORRECT: Let Feature Store provide the columns
labels_df = base_df.select("property_id", "engagement_date", "target")
# day_of_week, is_weekend will come from engagement_features via FeatureLookup
```

**Error:** `DataFrame contains column names that match feature output names`

---

## Feature Registry Pattern

```python
class FeatureRegistry:
    """Registry of feature tables and their schemas."""
    
    def get_feature_columns(self, table_name: str, exclude_columns: list = None) -> list:
        """Get feature columns, optionally excluding specific columns."""
        
        config = self.tables.get(table_name)
        if not config:
            raise ValueError(f"Unknown feature table: {table_name}")
        
        columns = config["columns"]
        
        # Always exclude primary keys
        pk_cols = config.get("primary_keys", [])
        
        # Add user-specified exclusions
        exclude = set(pk_cols)
        if exclude_columns:
            exclude.update(exclude_columns)
        
        return [c for c in columns if c not in exclude]

# Usage
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

## Feature Store Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `Unable to find feature '{column}'` | Feature name mismatch | Check actual column names in feature table with `DESCRIBE TABLE` |
| `DataFrame contains column names that match feature output names` | Column conflict in FeatureLookup | Remove conflicting columns from input DataFrame before lookup |
| `create_training_set() missing required argument` | API signature changed | Verify correct parameters: `df`, `feature_lookups`, `label` |

# Model Promotion Patterns

Alias management and promotion logic for GenAI agents with threshold-based decisions.

## Alias Management

```python
import mlflow

# Standard aliases
ALIAS_CHAMPION = "champion"  # Best performing model
ALIAS_PRODUCTION = "production"  # Production model
ALIAS_STAGING = "staging"  # Staging model

def set_model_alias(
    model_name: str,
    alias: str,
    version: int
):
    """
    Set alias for a model version.
    
    Args:
        model_name: Registered model name
        alias: Alias name (champion, production, staging)
        version: Model version number
    """
    mlflow.set_registered_model_alias(
        name=model_name,
        alias=alias,
        version=version
    )
```

## Promotion Logic

```python
def promote_model_to_production(
    model_name: str,
    model_version: int,
    evaluation_results: dict,
    thresholds: dict
) -> bool:
    """
    Promote model to production if thresholds met.
    
    Args:
        model_name: Registered model name
        model_version: Model version to promote
        evaluation_results: Evaluation metrics
        thresholds: Required thresholds for promotion
    
    Returns:
        True if promoted, False otherwise
    """
    # Check thresholds
    if not check_thresholds(evaluation_results, thresholds):
        print(f"Model version {model_version} does not meet promotion thresholds")
        return False
    
    # Promote to production
    mlflow.set_registered_model_alias(
        name=model_name,
        alias="production",
        version=model_version
    )
    
    print(f"Promoted model version {model_version} to production")
    return True
```

## Threshold-Based Decision

```python
def check_thresholds(results: dict, thresholds: dict) -> bool:
    """
    Check if evaluation results meet all thresholds.
    
    Args:
        results: Evaluation results dict
        thresholds: Required thresholds
    
    Returns:
        True if all thresholds met, False otherwise
    """
    for metric_name, threshold in thresholds.items():
        metric_value = get_metric_value(results, metric_name)
        
        if metric_value is None:
            print(f"Warning: Metric {metric_name} not found")
            continue
        
        if metric_value < threshold:
            print(f"Threshold failed: {metric_name} = {metric_value:.3f} < {threshold:.3f}")
            return False
    
    return True


def get_metric_value(results: dict, metric_name: str) -> float:
    """
    Get metric value with alias support.
    """
    # Try direct match
    if metric_name in results:
        return results[metric_name]
    
    # Try aliases
    aliases = {
        "relevance/mean": ["relevance_to_query/mean"],
        "safety/mean": ["safety/mean"],
        "guidelines/mean": ["guidelines/mean"],
    }
    
    if metric_name in aliases:
        for alias in aliases[metric_name]:
            if alias in results:
                return results[alias]
    
    return None
```

## Champion Model Pattern

```python
def promote_to_champion(
    model_name: str,
    model_version: int,
    evaluation_results: dict
):
    """
    Promote model to champion alias if it outperforms current champion.
    
    Args:
        model_name: Registered model name
        model_version: Model version to evaluate
        evaluation_results: Evaluation metrics
    """
    # Get current champion
    try:
        champion_version = mlflow.get_model_version_by_alias(
            model_name, "champion"
        )
        champion_results = get_champion_evaluation_results(champion_version)
        
        # Compare metrics
        if compare_models(evaluation_results, champion_results):
            # New model is better - promote to champion
            mlflow.set_registered_model_alias(
                name=model_name,
                alias="champion",
                version=model_version
            )
            print(f"Promoted model version {model_version} to champion")
        else:
            print(f"Model version {model_version} does not outperform champion")
    except Exception:
        # No champion exists - promote first model
        mlflow.set_registered_model_alias(
            name=model_name,
            alias="champion",
            version=model_version
        )
        print(f"Promoted model version {model_version} to champion (first champion)")


def compare_models(new_results: dict, champion_results: dict) -> bool:
    """
    Compare two models - return True if new model is better.
    
    Compares key metrics: relevance, safety, guidelines.
    """
    metrics_to_compare = ["relevance/mean", "safety/mean", "guidelines/mean"]
    
    new_wins = 0
    champion_wins = 0
    
    for metric in metrics_to_compare:
        new_value = get_metric_value(new_results, metric)
        champion_value = get_metric_value(champion_results, metric)
        
        if new_value is None or champion_value is None:
            continue
        
        if new_value > champion_value:
            new_wins += 1
        elif champion_value > new_value:
            champion_wins += 1
    
    # New model wins if it outperforms in majority of metrics
    return new_wins > champion_wins
```

## Complete Promotion Workflow

```python
def evaluate_and_promote(
    model_name: str,
    model_version: int,
    eval_dataset,
    thresholds: dict
):
    """
    Complete workflow: evaluate model, then promote if thresholds met.
    
    Args:
        model_name: Registered model name
        model_version: Model version to evaluate
        eval_dataset: Evaluation dataset
        thresholds: Required thresholds
    """
    # Step 1: Run evaluation
    model_uri = f"models:/{model_name}/{model_version}"
    evaluation_results = mlflow.genai.evaluate(
        model=model_uri,
        data=eval_dataset,
        model_type="databricks-agent",
        evaluators=evaluators
    )
    
    # Step 2: Check thresholds
    if not check_thresholds(evaluation_results, thresholds):
        raise PromotionThresholdError(
            f"Model version {model_version} does not meet promotion thresholds"
        )
    
    # Step 3: Promote to production
    promote_model_to_production(
        model_name=model_name,
        model_version=model_version,
        evaluation_results=evaluation_results,
        thresholds=thresholds
    )
    
    # Step 4: Consider champion promotion
    promote_to_champion(
        model_name=model_name,
        model_version=model_version,
        evaluation_results=evaluation_results
    )


class PromotionThresholdError(Exception):
    """Raised when model doesn't meet promotion thresholds."""
    pass
```

## Usage Example

```python
# Promotion thresholds
THRESHOLDS = {
    "relevance/mean": 0.7,
    "safety/mean": 0.9,
    "guidelines/mean": 0.6,
    "cost_accuracy/mean": 0.8,
}

# Evaluate and promote
try:
    evaluate_and_promote(
        model_name="health_monitor_agent",
        model_version=2,
        eval_dataset=eval_df,
        thresholds=THRESHOLDS
    )
    print("Model promoted successfully")
except PromotionThresholdError as e:
    print(f"Promotion failed: {str(e)}")
```

## Alias Querying

```python
def get_production_model(model_name: str) -> mlflow.entities.model_registry.ModelVersion:
    """Get current production model version."""
    return mlflow.get_model_version_by_alias(model_name, "production")


def get_champion_model(model_name: str) -> mlflow.entities.model_registry.ModelVersion:
    """Get current champion model version."""
    return mlflow.get_model_version_by_alias(model_name, "champion")
```

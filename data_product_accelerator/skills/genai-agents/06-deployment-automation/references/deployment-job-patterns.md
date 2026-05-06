# Deployment Job Patterns

Complete deployment job flow with MODEL_VERSION_CREATED trigger, evaluation-then-promote logic, and error handling.

## Complete Deployment Job Flow

```python
"""
Deployment job notebook: evaluate_and_deploy_agent.py

Runs automatically when new model version is created.
"""
import mlflow
from mlflow.data import from_spark
from pyspark.sql import DataFrame
from datetime import datetime
import sys

# Configuration
MODEL_NAME = "health_monitor_agent"
EXPERIMENT_EVALUATION = "/Shared/health_monitor_agent/evaluation"
EXPERIMENT_DEPLOYMENT = "/Shared/health_monitor_agent/deployment"

# Evaluation thresholds
THRESHOLDS = {
    "relevance/mean": 0.7,
    "safety/mean": 0.9,
    "guidelines/mean": 0.6,
    "cost_accuracy/mean": 0.8,
}

def evaluate_and_deploy():
    """
    Main deployment workflow: evaluate model, then deploy if thresholds met.
    """
    # Step 1: Get latest model version from trigger
    model_version = get_model_version_from_trigger()
    model_uri = f"models:/{MODEL_NAME}/{model_version.version}"
    
    print(f"Evaluating model version {model_version.version}")
    
    # Step 2: Load evaluation dataset
    eval_dataset = load_evaluation_dataset_with_lineage()
    
    # Step 3: Run evaluation
    evaluation_results = run_evaluation(
        model_uri=model_uri,
        eval_dataset=eval_dataset,
        model_version=model_version.version
    )
    
    # Step 4: Check thresholds
    if not check_thresholds(evaluation_results, THRESHOLDS):
        raise DeploymentThresholdError(
            f"Model version {model_version.version} did not meet deployment thresholds"
        )
    
    # Step 5: Promote to production
    promote_model_to_production(model_version)
    
    # Step 6: Deploy to Model Serving (optional)
    deploy_to_model_serving(model_version)
    
    print(f"Successfully deployed model version {model_version.version}")


def get_model_version_from_trigger() -> mlflow.entities.model_registry.ModelVersion:
    """
    Get model version from deployment job trigger.
    
    In Asset Bundle jobs with MODEL_VERSION_CREATED trigger,
    model version is available via widget or environment variable.
    """
    try:
        # Try widget parameter (set by Asset Bundle)
        model_version = dbutils.widgets.get("model_version")
        if model_version:
            return mlflow.get_model_version(MODEL_NAME, model_version)
    except:
        pass
    
    # Fallback: Get latest version
    latest_version = mlflow.search_model_versions(
        f"name='{MODEL_NAME}'",
        order_by=["version_number DESC"],
        max_results=1
    )[0]
    
    return latest_version


def run_evaluation(
    model_uri: str,
    eval_dataset: DataFrame,
    model_version: str
) -> dict:
    """
    Run evaluation and log results with dataset lineage.
    """
    from mlflow.genai import evaluate
    from mlflow.data import from_spark
    
    run_name = f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    mlflow.set_experiment(EXPERIMENT_EVALUATION)
    
    with mlflow.start_run(run_name=run_name):
        # Link evaluation dataset
        mlflow.log_input(
            from_spark(eval_dataset),
            context="evaluation"
        )
        
        # Run evaluation
        results = evaluate(
            model=model_uri,
            data=eval_dataset,
            model_type="databricks-agent",
            evaluators=evaluators,
            evaluator_config=evaluator_config
        )
        
        # Log model version
        mlflow.set_tag("model_version", model_version)
        mlflow.set_tag("deployment_candidate", "true")
        
        return results


def check_thresholds(results: dict, thresholds: dict) -> bool:
    """
    Check if evaluation results meet deployment thresholds.
    
    Returns:
        True if all thresholds met, False otherwise
    """
    for metric_name, threshold in thresholds.items():
        # Handle metric aliases (e.g., relevance/mean vs relevance_to_query/mean)
        metric_value = get_metric_value(results, metric_name)
        
        if metric_value is None:
            print(f"Warning: Metric {metric_name} not found in results")
            continue
        
        if metric_value < threshold:
            print(f"Threshold check failed: {metric_name} = {metric_value:.3f} < {threshold:.3f}")
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


def promote_model_to_production(model_version: mlflow.entities.model_registry.ModelVersion):
    """
    Promote model to production alias.
    """
    # Set production alias
    mlflow.set_registered_model_alias(
        name=MODEL_NAME,
        alias="production",
        version=model_version.version
    )
    
    # Log deployment run
    run_name = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    mlflow.set_experiment(EXPERIMENT_DEPLOYMENT)
    
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("model_version", model_version.version)
        mlflow.set_tag("deployment_status", "success")
        mlflow.log_param("promoted_to", "production")


def deploy_to_model_serving(model_version: mlflow.entities.model_registry.ModelVersion):
    """
    Deploy model to Model Serving endpoint (optional).
    """
    from databricks.agents import deploy
    
    endpoint_name = f"{MODEL_NAME}_endpoint"
    
    try:
        deploy(
            model_uri=f"models:/{MODEL_NAME}@production",
            endpoint_name=endpoint_name,
            environment="production"
        )
        print(f"Deployed to Model Serving endpoint: {endpoint_name}")
    except Exception as e:
        print(f"Warning: Model Serving deployment failed: {str(e)}")
        # Don't fail deployment job if Model Serving fails


class DeploymentThresholdError(Exception):
    """Raised when model doesn't meet deployment thresholds."""
    pass


# Main execution
if __name__ == "__main__":
    try:
        evaluate_and_deploy()
    except DeploymentThresholdError as e:
        print(f"Deployment failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)
```

## Trigger Configuration

```yaml
# databricks.yml (Asset Bundle configuration)
resources:
  jobs:
    deploy_agent_job:
      name: deploy-agent (serverless)
      environments:
        - default
      tasks:
        - task_key: evaluate_and_deploy
          environment_key: default
          notebook_task:
            notebook_path: notebooks/deployment/evaluate_and_deploy_agent
            base_parameters:
              model_name: "health_monitor_agent"
      trigger:
        type: MODEL_VERSION_CREATED
        model_name: "health_monitor_agent"
        stages: ["None"]  # Trigger on new versions (before staging/production)
```

## Error Handling

```python
def handle_deployment_error(error: Exception, model_version: str):
    """
    Handle deployment errors with proper logging.
    """
    run_name = f"deploy_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    mlflow.set_experiment(EXPERIMENT_DEPLOYMENT)
    
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("model_version", model_version)
        mlflow.set_tag("deployment_status", "failed")
        mlflow.log_param("error_type", type(error).__name__)
        mlflow.log_param("error_message", str(error))
```

## Usage Example

```python
# Deployment job runs automatically when:
# 1. New model version created via mlflow.register_model()
# 2. Asset Bundle detects MODEL_VERSION_CREATED event
# 3. Job executes evaluate_and_deploy() workflow

# Manual trigger (for testing)
if __name__ == "__main__":
    evaluate_and_deploy()
```

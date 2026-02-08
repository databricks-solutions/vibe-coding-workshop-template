# Experiment Organization Patterns

Three-experiment structure for GenAI agent development: development, evaluation, and deployment tracking.

## Three Experiments Structure

```python
# Experiment paths
EXPERIMENT_DEVELOPMENT = "/Shared/health_monitor_agent/development"
EXPERIMENT_EVALUATION = "/Shared/health_monitor_agent/evaluation"
EXPERIMENT_DEPLOYMENT = "/Shared/health_monitor_agent/deployment"
```

| Experiment | Purpose | Run Types | Naming Convention |
|---|---|---|---|
| **EXPERIMENT_DEVELOPMENT** | Agent development and testing | Development runs, testing, debugging | `dev_YYYYMMDD_HHMMSS` |
| **EXPERIMENT_EVALUATION** | Pre-deployment evaluation | Evaluation runs, threshold checks | `eval_pre_deploy_YYYYMMDD_HHMMSS` |
| **EXPERIMENT_DEPLOYMENT** | Production deployment tracking | Deployment runs, promotion logs | `deploy_YYYYMMDD_HHMMSS` |

## Experiment Creation

```python
import mlflow

def create_experiments():
    """Create three experiments for agent development."""
    experiments = [
        "/Shared/health_monitor_agent/development",
        "/Shared/health_monitor_agent/evaluation",
        "/Shared/health_monitor_agent/deployment"
    ]
    
    for exp_path in experiments:
        try:
            mlflow.create_experiment(exp_path)
            print(f"Created experiment: {exp_path}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"Experiment already exists: {exp_path}")
            else:
                raise
```

## Run Naming Conventions

### Development Runs

```python
from datetime import datetime

def create_development_run():
    """Create development run with standard naming."""
    mlflow.set_experiment("/Shared/health_monitor_agent/development")
    
    run_name = f"dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("run_type", "development")
        mlflow.set_tag("agent_name", "health_monitor_agent")
        # ... development code
```

### Evaluation Runs

```python
def create_evaluation_run():
    """Create evaluation run with standard naming."""
    mlflow.set_experiment("/Shared/health_monitor_agent/evaluation")
    
    run_name = f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("run_type", "evaluation")
        mlflow.set_tag("agent_name", "health_monitor_agent")
        mlflow.set_tag("deployment_candidate", "true")
        # ... evaluation code
```

### Deployment Runs

```python
def create_deployment_run(model_version: str):
    """Create deployment run with standard naming."""
    mlflow.set_experiment("/Shared/health_monitor_agent/deployment")
    
    run_name = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("run_type", "deployment")
        mlflow.set_tag("agent_name", "health_monitor_agent")
        mlflow.set_tag("model_version", model_version)
        mlflow.set_tag("deployment_status", "success")
        # ... deployment code
```

## Standard Tags

```python
STANDARD_TAGS = {
    "agent_name": "health_monitor_agent",
    "run_type": "development|evaluation|deployment",
    "environment": "dev|staging|production",
    "version": "1.0.0",
}

def apply_standard_tags(run_type: str, **additional_tags):
    """
    Apply standard tags to current run.
    
    Args:
        run_type: "development", "evaluation", or "deployment"
        **additional_tags: Additional tags to apply
    """
    tags = {
        **STANDARD_TAGS,
        "run_type": run_type,
        **additional_tags
    }
    
    for key, value in tags.items():
        mlflow.set_tag(key, value)
```

## Querying Runs by Experiment

```python
def get_latest_evaluation_run() -> mlflow.entities.Run:
    """Get latest evaluation run."""
    runs = mlflow.search_runs(
        experiment_ids=[mlflow.get_experiment_by_name(
            "/Shared/health_monitor_agent/evaluation"
        ).experiment_id],
        filter_string="tags.run_type = 'evaluation'",
        order_by=["start_time DESC"],
        max_results=1
    )
    
    if runs.empty:
        return None
    
    return runs.iloc[0]


def get_deployment_runs_for_version(model_version: str) -> list:
    """Get all deployment runs for a model version."""
    runs = mlflow.search_runs(
        experiment_ids=[mlflow.get_experiment_by_name(
            "/Shared/health_monitor_agent/deployment"
        ).experiment_id],
        filter_string=f"tags.model_version = '{model_version}'",
        order_by=["start_time DESC"]
    )
    
    return runs
```

## Experiment Organization Best Practices

### 1. Use `/Shared/` Prefix

```python
# ✅ CORRECT: Shared experiments
EXPERIMENT_DEVELOPMENT = "/Shared/health_monitor_agent/development"

# ❌ WRONG: User-specific experiments
EXPERIMENT_DEVELOPMENT = "/Users/john.doe@databricks.com/health_monitor_agent/development"
```

**Why:** Shared experiments enable team collaboration and CI/CD access.

### 2. Consistent Naming

```python
# ✅ CORRECT: Consistent naming
run_name = f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ❌ WRONG: Inconsistent naming
run_name = f"evaluation-{datetime.now().isoformat()}"  # Different format
```

**Why:** Consistent naming enables programmatic querying.

### 3. Tag Everything

```python
# ✅ CORRECT: Comprehensive tagging
mlflow.set_tag("run_type", "evaluation")
mlflow.set_tag("agent_name", "health_monitor_agent")
mlflow.set_tag("model_version", "1")
mlflow.set_tag("deployment_candidate", "true")

# ❌ WRONG: Minimal tagging
mlflow.set_tag("type", "eval")  # Too generic
```

**Why:** Tags enable filtering and querying across experiments.

## Complete Workflow Example

```python
import mlflow
from datetime import datetime

# Configuration
EXPERIMENT_DEVELOPMENT = "/Shared/health_monitor_agent/development"
EXPERIMENT_EVALUATION = "/Shared/health_monitor_agent/evaluation"
EXPERIMENT_DEPLOYMENT = "/Shared/health_monitor_agent/deployment"

# Step 1: Development
mlflow.set_experiment(EXPERIMENT_DEVELOPMENT)
with mlflow.start_run(run_name=f"dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
    mlflow.set_tag("run_type", "development")
    # ... development code

# Step 2: Evaluation
mlflow.set_experiment(EXPERIMENT_EVALUATION)
with mlflow.start_run(run_name=f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
    mlflow.set_tag("run_type", "evaluation")
    mlflow.set_tag("deployment_candidate", "true")
    # ... evaluation code

# Step 3: Deployment
mlflow.set_experiment(EXPERIMENT_DEPLOYMENT)
with mlflow.start_run(run_name=f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
    mlflow.set_tag("run_type", "deployment")
    mlflow.set_tag("model_version", "1")
    mlflow.set_tag("deployment_status", "success")
    # ... deployment code
```

## Validation Checklist

- [ ] Three experiments created (dev, eval, deploy)
- [ ] Experiments use `/Shared/` prefix
- [ ] Run naming conventions followed
- [ ] Standard tags applied to all runs
- [ ] Run types clearly distinguished
- [ ] Model versions tracked in deployment runs

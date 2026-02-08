---
name: deployment-automation
description: >
  Automated deployment workflows for GenAI agents - MLflow deployment job trigger,
  dataset linking, evaluation-then-promote, experiment organization. Use when setting
  up CI/CD for GenAI agents, automating model deployment, linking evaluation datasets,
  or implementing evaluation-then-promote workflows. Triggers on "deploy", "deployment job",
  "model version", "promote", "CI/CD", "mlflow.log_input".
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
---

# Deployment Automation Patterns

Production-grade patterns for automating GenAI agent deployment with MLflow job triggers, dataset lineage, evaluation-then-promote workflows, and proper experiment organization.

## When to Use

- Setting up CI/CD pipelines for GenAI agents
- Automating model deployment with evaluation gates
- Linking evaluation datasets for traceability
- Implementing evaluation-then-promote workflows
- Organizing MLflow experiments for agent development
- Troubleshooting deployment job failures

---

## Deployment Job Trigger (MODEL_VERSION_CREATED)

Deployment jobs automatically trigger when a new model version is created, enabling CI/CD workflows.

```python
# Asset Bundle configuration
resources:
  jobs:
    deploy_agent_job:
      name: deploy-agent (serverless)
      trigger:
        type: MODEL_VERSION_CREATED
        model_name: "health_monitor_agent"
        stages: ["None"]  # Trigger on new versions
      tasks:
        - task_key: evaluate_and_deploy
          # ... evaluation and deployment logic
```

**For complete deployment job patterns, see:** `references/deployment-job-patterns.md`

---

## Dataset Linking Overview (mlflow.log_input)

**CRITICAL: Always link evaluation datasets using `mlflow.log_input()` for traceability.**

```python
import mlflow
from mlflow.data import from_spark

# Load evaluation dataset
eval_df = spark.table("gold.evaluation.agent_eval_dataset")

# Link dataset to run
with mlflow.start_run():
    mlflow.log_input(
        from_spark(eval_df),
        context="evaluation"
    )
    
    # Run evaluation
    results = mlflow.genai.evaluate(...)
```

**Why this matters:**
- Enables dataset lineage tracking
- Links evaluation results to specific dataset versions
- Required for production audit trails
- Enables dataset impact analysis

**For complete dataset lineage patterns, see:** `references/dataset-lineage.md`

---

## Three Experiments (dev, eval, deploy)

Organize agent development across three experiments for clear separation of concerns.

| Experiment | Purpose | Run Naming |
|---|---|---|
| **EXPERIMENT_DEVELOPMENT** | Agent development and testing | `dev_YYYYMMDD_HHMMSS` |
| **EXPERIMENT_EVALUATION** | Pre-deployment evaluation | `eval_pre_deploy_YYYYMMDD_HHMMSS` |
| **EXPERIMENT_DEPLOYMENT** | Production deployment tracking | `deploy_YYYYMMDD_HHMMSS` |

```python
EXPERIMENT_DEVELOPMENT = "/Shared/health_monitor_agent/development"
EXPERIMENT_EVALUATION = "/Shared/health_monitor_agent/evaluation"
EXPERIMENT_DEPLOYMENT = "/Shared/health_monitor_agent/deployment"
```

**For complete experiment organization patterns, see:** `references/experiment-organization.md`

---

## Run Naming Conventions

**ALWAYS use consistent run naming** for programmatic querying and CI/CD integration.

```python
from datetime import datetime

# Development runs
run_name = f"dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Evaluation runs
run_name = f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Deployment runs
run_name = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
```

**Why this matters:**
- Enables automated threshold checking
- CI/CD pipelines can query latest results
- Clear audit trail for deployments

---

## Promotion Workflow Overview

Evaluation-then-promote pattern ensures only high-quality models reach production.

```python
def evaluate_and_promote(model_uri: str, eval_dataset: DataFrame):
    """
    Evaluate model, then promote if thresholds met.
    """
    # Step 1: Run evaluation
    results = mlflow.genai.evaluate(
        model=model_uri,
        data=eval_dataset,
        evaluators=evaluators
    )
    
    # Step 2: Check thresholds
    if check_thresholds(results):
        # Step 3: Promote to production
        mlflow.set_registered_model_alias(
            name="health_monitor_agent",
            alias="production",
            version=model_version
        )
    else:
        raise DeploymentThresholdError("Evaluation thresholds not met")
```

**For complete promotion patterns, see:** `references/model-promotion.md`

---

## Validation Checklist

Before deploying automated deployment workflows:

### Deployment Job Configuration
- [ ] Job configured with `MODEL_VERSION_CREATED` trigger
- [ ] Model name matches registered model name
- [ ] Stages configured correctly (typically `["None"]`)
- [ ] Job runs in serverless environment

### Dataset Lineage
- [ ] ✅ **`mlflow.log_input()` used for evaluation datasets**
- [ ] ✅ **`from_spark()` used for Spark DataFrames**
- [ ] ✅ **Context set to "evaluation"**
- [ ] Evaluation dataset stored in Unity Catalog

### Experiment Organization
- [ ] Three experiments created (dev, eval, deploy)
- [ ] Run naming conventions followed
- [ ] Standard tags applied to runs
- [ ] Experiment paths use `/Shared/` prefix

### Promotion Workflow
- [ ] Threshold checking implemented
- [ ] Alias management configured (champion, production, staging)
- [ ] Error handling for threshold failures
- [ ] Deployment logging implemented

---

## Reference Files

- **`references/deployment-job-patterns.md`** - Complete deployment job flow and trigger configuration
- **`references/dataset-lineage.md`** - `mlflow.log_input()` patterns and dataset tracking
- **`references/experiment-organization.md`** - Three-experiment structure and run naming
- **`references/model-promotion.md`** - Alias management and promotion logic
- **`assets/templates/deployment-job.yml`** - Asset Bundle YAML template for deployment jobs

---

## References

### Official Documentation
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [MLflow Dataset Tracking](https://mlflow.org/docs/latest/data/index.html)
- [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/index.html)
- [Model Serving Deployment](https://docs.databricks.com/en/machine-learning/model-serving/index.html)

### Related Skills
- `mlflow-genai-evaluation` - Agent evaluation patterns
- `responses-agent-patterns` - ResponsesAgent implementation
- `databricks-asset-bundles` - Asset Bundle configuration patterns

---

## Version History

| Date | Changes |
|---|---|
| Feb 6, 2026 | Initial version: Deployment automation with dataset lineage |

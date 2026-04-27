# ModelConfig Patterns

Complete reference for using `mlflow.models.ModelConfig` to externalize
configuration from agent code. Enables the same logged model to target
different environments (dev, staging, prod) without code changes.

---

## 1. Why ModelConfig

Hardcoded values inside an agent class create deployment friction:

| Problem | Example |
|---------|---------|
| Environment coupling | `endpoint = "dev-llm-endpoint"` baked into the model |
| Secret leakage | Warehouse IDs, catalog names in source code |
| Re-logging required | Any config change requires a new `log_model()` call |

ModelConfig solves this by loading values from a YAML file at serving time.

---

## 2. YAML Configuration

### Basic config file (`config.yml`)

```yaml
model_serving_endpoint: "databricks-claude-sonnet-4-6"
warehouse_id: "abc123def456"
catalog: "main"
schema: "genie_optimization"
max_retries: 3
temperature: 0
```

### Loading in agent code

```python
import mlflow


config = mlflow.models.ModelConfig(development_config="config.yml")

endpoint = config.get("model_serving_endpoint")
warehouse_id = config.get("warehouse_id")
catalog = config.get("catalog")
schema = config.get("schema")
max_retries = config.get("max_retries")
```

The `development_config` parameter specifies which file to read during local
development and notebook execution. When the model is deployed to Model
Serving, the config is resolved from the logged artifact.

---

## 3. Dict-Based Configuration

For simple cases or testing, pass a dict directly:

```python
config = mlflow.models.ModelConfig(
    development_config={
        "model_serving_endpoint": "test-endpoint",
        "warehouse_id": "test-warehouse",
    }
)
```

This is useful for unit tests where no YAML file is available.

---

## 4. Override at Log Time

When you `log_model()`, pass the config path so the YAML is bundled with
the model artifact:

```python
import mlflow

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        python_model=MyAgent(),
        artifact_path="agent",
        model_config="config.yml",
    )
```

To override specific values at log time without editing the YAML:

```python
import mlflow

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        python_model=MyAgent(),
        artifact_path="agent",
        model_config="config-prod.yml",  # production config
    )
```

### Multiple config files for environments

```text
configs/
├── config-dev.yml        # development defaults
├── config-staging.yml    # staging overrides
└── config-prod.yml       # production values
```

At log time, select the appropriate file:

```python
import os

env = os.getenv("DEPLOY_ENV", "dev")
config_path = f"configs/config-{env}.yml"

mlflow.pyfunc.log_model(
    python_model=MyAgent(),
    artifact_path="agent",
    model_config=config_path,
)
```

---

## 5. Environment-Specific Configs

### Development (`config-dev.yml`)

```yaml
model_serving_endpoint: "databricks-claude-sonnet-4-6"
warehouse_id: "dev-warehouse-001"
catalog: "dev_catalog"
schema: "genie_optimization"
max_retries: 1
temperature: 0.7
enable_tracing: true
log_level: "DEBUG"
```

### Staging (`config-staging.yml`)

```yaml
model_serving_endpoint: "databricks-claude-sonnet-4-6"
warehouse_id: "staging-warehouse-001"
catalog: "staging_catalog"
schema: "genie_optimization"
max_retries: 3
temperature: 0
enable_tracing: true
log_level: "INFO"
```

### Production (`config-prod.yml`)

```yaml
model_serving_endpoint: "databricks-claude-opus-4-6"
warehouse_id: "prod-warehouse-001"
catalog: "prod_catalog"
schema: "genie_optimization"
max_retries: 5
temperature: 0
enable_tracing: false
log_level: "WARNING"
```

---

## 6. Config Loading in Agent Code

### In `load_context()` (recommended)

```python
class MyAgent(PythonModel):
    def load_context(self, context):
        config = mlflow.models.ModelConfig(development_config="config.yml")
        self.endpoint = config.get("model_serving_endpoint")
        self.catalog = config.get("catalog")
        self.schema = config.get("schema")

    def predict(self, context, model_input, params=None):
        # Use self.endpoint, self.catalog, etc.
        ...
```

### At module level (for non-class agents)

```python
import mlflow

config = mlflow.models.ModelConfig(development_config="config.yml")
ENDPOINT = config.get("model_serving_endpoint")
CATALOG = config.get("catalog")

def predict(model_input):
    # Use ENDPOINT, CATALOG
    ...
```

Module-level loading works because ModelConfig reads the YAML once and caches
the result. The file is resolved relative to the model artifact directory on
Model Serving.

---

## 7. DO / DON'T Pairs

### Hardcoded values

```python
# DON'T — environment-specific values baked into code
class BadAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        w = WorkspaceClient()
        return w.serving_endpoints.query(
            name="my-prod-endpoint",  # Hardcoded
            messages=model_input["input"],
        )
```

```python
# DO — externalize via ModelConfig
class GoodAgent(PythonModel):
    def load_context(self, context):
        config = mlflow.models.ModelConfig(development_config="config.yml")
        self.endpoint = config.get("model_serving_endpoint")

    def predict(self, context, model_input, params=None):
        w = WorkspaceClient()
        return w.serving_endpoints.query(
            name=self.endpoint,
            messages=model_input["input"],
        )
```

### Missing config key handling

```python
# DON'T — crashes with KeyError if key is absent
endpoint = config.get("nonexistent_key")
w.serving_endpoints.query(name=endpoint, ...)  # endpoint is None → 400 error
```

```python
# DO — validate required keys at load time
def load_context(self, context):
    config = mlflow.models.ModelConfig(development_config="config.yml")
    self.endpoint = config.get("model_serving_endpoint")
    if not self.endpoint:
        raise ValueError("model_serving_endpoint is required in config.yml")
```

### Config at log time

```python
# DON'T — forget to pass model_config; YAML not bundled with artifact
mlflow.pyfunc.log_model(python_model=agent, artifact_path="agent")
```

```python
# DO — always pass model_config so the YAML travels with the model
mlflow.pyfunc.log_model(
    python_model=agent,
    artifact_path="agent",
    model_config="config.yml",
)
```

---

## 8. Complete Example with Multiple Configs

```python
"""Agent with environment-aware ModelConfig loading."""

import os
import mlflow
from mlflow.pyfunc import PythonModel


class EnvironmentAwareAgent(PythonModel):

    def load_context(self, context):
        config = mlflow.models.ModelConfig(development_config="config.yml")
        self.endpoint = config.get("model_serving_endpoint")
        self.catalog = config.get("catalog")
        self.schema = config.get("schema")
        self.max_retries = int(config.get("max_retries") or 3)
        self.temperature = float(config.get("temperature") or 0)

    def predict(self, context, model_input, params=None):
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        messages = model_input.get("input", [])
        response = w.serving_endpoints.query(
            name=self.endpoint,
            messages=messages,
            temperature=self.temperature,
            max_tokens=4096,
        )
        return {"output": response.choices[0].message.content}


# --- Logging for different environments ---

def log_agent(env: str = "dev"):
    config_path = f"configs/config-{env}.yml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")

    with mlflow.start_run(run_name=f"agent-{env}"):
        mlflow.pyfunc.log_model(
            python_model=EnvironmentAwareAgent(),
            artifact_path="agent",
            model_config=config_path,
            input_example={
                "input": [{"role": "user", "content": "Hello"}],
            },
        )
```

---

## 9. Relationship to Bundle Variables

ModelConfig is for **runtime agent configuration** (what the model reads at
serving time). Bundle variables in `databricks.yml` are for **deployment-time
infrastructure** (endpoint names, permissions, resource IDs).

| Concern | Mechanism |
|---------|-----------|
| Which LLM endpoint to call | ModelConfig YAML |
| Which catalog/schema for state tables | ModelConfig YAML |
| Which warehouse to provision | `databricks.yml` variables |
| Which permissions to grant | `deploy.sh` / bundle resources |

They complement each other: bundle variables configure the infrastructure,
ModelConfig configures the agent's behavior within that infrastructure.

---

## Related Skills

- **Skill 00 — MLflow GenAI Foundation:** Dependency setup and autolog
- **Skill 02 — ResponsesAgent Patterns:** How agents use ModelConfig
- **Skill 10 — UC Model Management:** Logging models with config for promotion

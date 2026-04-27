# Deployment by Track

Track-specific deployment guidance for GenAI agents on Databricks. The **primary
path** for this SDLC remains Databricks Apps (see the parent `SKILL.md`).

---

## Track A: Databricks Apps

Use the primary workflow in `SKILL.md`:

- `uv run preflight`
- `databricks bundle validate` / `databricks bundle deploy`
- Chat UI verification and programmatic access via `OpenAI` against the app base URL

For advanced patterns (Lakebase, SP lifecycle, logs), see
[`apps-deployment-patterns.md`](apps-deployment-patterns.md).

---

## Track B: Supervisor API

The Supervisor API is a managed service — there is no separate “deploy app”
step in the same sense as Apps. Your agent is already runnable when you call
`client.responses.create()`.

**CI/CD implications**

- The **evaluate → promote** pipeline still applies (quality gates before
  promoting configuration).
- Instead of `databricks bundle deploy`, automation typically runs evaluation
  and updates **`config.yml`** (or equivalent) with new model / tool
  configuration.
- **Version-control** `config.yml` so configuration changes are auditable and
  reversible.

---

## Track C: Model Serving

Typical flow:

1. Register the model in Unity Catalog (SDLC Step 5).
2. Create or update a **serving endpoint** (Python SDK or bundle resource).
3. Wait until the endpoint is in **READY** state.
4. Run **evaluate → promote → deploy** with **endpoint updates** substituting
   for app deploys where your org’s pipeline is endpoint-centric.

### Bundle resource definition

Use [`databricks-yml-serving-template.yaml`](../assets/templates/databricks-yml-serving-template.yaml) for a complete Track C bundle.
The key resource block:

```yaml
resources:
  experiments:
    agent_experiment:
      name: /Users/${workspace.current_user.userName}/${var.app_name}

  model_serving_endpoints:
    agent_endpoint:
      name: ${var.app_name}-endpoint
      config:
        served_entities:
          - entity_name: "${var.catalog}.${var.schema}.${var.app_name}"
            entity_version: "1"
            workload_size: "Small"
            scale_to_zero_enabled: true
        auto_capture_config:
          catalog_name: ${var.catalog}
          schema_name: ${var.schema}
          table_name_prefix: "${var.app_name}_inference"
          enabled: true
      permissions:
        - group_name: "users"
          level: "CAN_QUERY"
```

Deploy with:

```bash
databricks bundle validate
databricks bundle deploy --target dev --var warehouse_id=abc123
```

### SDK example (alternative to bundle)

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
w.serving_endpoints.create(
    name="my-agent-endpoint",
    config={
        "served_entities": [{
            "entity_name": "main.my_schema.my_agent",
            "entity_version": "1",
            "workload_size": "Small",
            "scale_to_zero_enabled": True,
        }],
        "auto_capture_config": {
            "catalog_name": "main",
            "schema_name": "my_schema",
            "table_name_prefix": "my_agent_inference",
            "enabled": True,
        },
    },
)
```

For full patterns (resources, `ModelConfig`, stateless agents), see
[`model-serving-patterns.md`](model-serving-patterns.md) and
[`stateless-serving.md`](stateless-serving.md).

---

## Model Serving as a reference alternative (not the primary course path)

Use a **stateless serving endpoint** when you need high-throughput API access
**without** the Apps chat UI or custom FastAPI middleware. This is **not** the
default path for the GenAI Agents SDLC course (Apps remain the default).

### When to use Model Serving instead of Apps

| Scenario | Use Apps | Use Model Serving |
|----------|----------|-------------------|
| Interactive chat UI needed | Yes | No |
| Custom server logic (FastAPI, middleware) | Yes | No |
| Stateless, high-throughput API | No | Yes |
| Automatic auth passthrough for logged resources | Limited | Yes (via logged resources) |
| GPU serving for custom models | No | Yes |

### Quick reference: log with resources and deploy

```python
# Log with resources for Model Serving
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
)

mlflow.pyfunc.log_model(
    python_model="/path/to/agent.py",
    resources=[
        DatabricksServingEndpoint(endpoint_name="my-llm"),
        DatabricksVectorSearchIndex(index_name="prod.docs.index"),
    ],
)

# Deploy to serving endpoint
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
w.serving_endpoints.create(
    name="my-agent-endpoint",
    config={
        "served_entities": [{
            "entity_name": "main.genie_optimization.my_agent",
            "entity_version": "1",
            "workload_size": "Small",
        }]
    },
)
```

### Further reading

- In-repo: [`model-serving-patterns.md`](model-serving-patterns.md)
- Databricks: [Model Serving](https://docs.databricks.com/aws/en/machine-learning/model-serving/)

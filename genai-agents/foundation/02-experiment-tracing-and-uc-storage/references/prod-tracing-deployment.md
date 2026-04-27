# Production tracing deployment — canonical reference

> **Companion to** [`../SKILL.md`](../SKILL.md) (Foundation Step 2) and
> [`../../02b-typescript-tracing/SKILL.md`](../../02b-typescript-tracing/SKILL.md) (Foundation Step 2b).
>
> **Source:** [Trace agents deployed on Databricks](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/prod-tracing).

This is the canonical checklist for getting traces from a **deployed**
agent into MLflow. It applies in three different deployment shapes:

1. **Agent Framework** (`mlflow.models.set_model(...)` + `agents.deploy(...)`).
2. **Custom CPU serving** (`pyfunc` / `pyfunc.ChatModel` / `ResponsesAgent`
   logged + `mlflow.deployments` model serving endpoint, **without** Agent
   Framework auto-tracing).
3. **Databricks Apps** (`@mlflow.genai.agent_server.invoke` /
   `@stream`, AppKit-integrated apps, custom Node/Python servers).

Pick the section that matches your stack. The env-var matrix and SP
permissions are the same idea but the hooks differ.

---

## 1. Agent Framework path

When you deploy with `databricks.agents.deploy(...)`, MLflow traces are
**auto-wired** to the experiment that owned the model run.

```python
import mlflow
from databricks import agents

mlflow.set_experiment("/Shared/my-agent/eval")  # NOT a Git-folder experiment

with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        python_model=my_agent,
        artifact_path="agent",
        input_example=example,
    )

agents.deploy(
    model_name=registered_name,
    model_version=model_info.version,
)
```

What auto-traces:

- Every request to the deployed endpoint produces a trace in the
  experiment used at log/deploy time.
- Token counts, latency, and `gen_ai.*` attributes flow if you used
  `mlflow.openai.autolog()` (or another autolog integration) at
  log time. See [`autolog-integrations.md`](autolog-integrations.md).

### Git-folder caveat (critical)

If your experiment lives **inside a Databricks Git folder**, traces from
the deployed endpoint may not flow back to the experiment. Always:

1. Create the experiment in a **non-Git** path (e.g. `/Shared/...` or `/Users/<you>/...`).
2. `mlflow.set_experiment("/Shared/...")` to that non-Git path **before**
   `agents.deploy(...)`.

If you ignore this, traces silently land in the workspace default
location (or get dropped) and the Agent Framework dashboards in the
Experiment UI stay empty.

This is the single most common production-tracing failure mode for
Agent Framework deploys.

---

## 2. Custom CPU serving path (Model Serving without Agent Framework)

When you deploy a `pyfunc` to Model Serving directly (not via
`agents.deploy`), tracing does **not** auto-wire. Set these env vars on
the serving endpoint:

| Env var | Purpose |
|---|---|
| `ENABLE_MLFLOW_TRACING` | `true` — turns on the tracing exporter inside the model serving runtime. |
| `MLFLOW_EXPERIMENT_ID` | Numeric id of the target experiment (not the path). |
| `APP_ENVIRONMENT` | `production` / `staging` / `development`. Application code reads this and overrides `mlflow.source.type` via `mlflow.update_current_trace(metadata=...)`. See [F2c § Track environments and versions](../../02c-trace-context-and-environments/SKILL.md#track-environments-and-versions). |
| `DATABRICKS_HOST` | Workspace URL (only required for PAT mode; SP/OAuth modes auto-detect). |
| `DATABRICKS_TOKEN` | PAT for the calling identity (PAT mode). |
| `DATABRICKS_CLIENT_ID` | Service principal client id (OAuth mode). |
| `DATABRICKS_CLIENT_SECRET` | Service principal secret (OAuth mode). |

Pick **one** authentication mode:

- **PAT mode:** `DATABRICKS_HOST` + `DATABRICKS_TOKEN`.
- **OAuth mode (recommended for prod):** `DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET`.

In `databricks.yml` (Asset Bundles):

```yaml
resources:
  model_serving_endpoints:
    my_agent:
      name: my-agent-endpoint
      config:
        served_models:
          - model_name: ${var.catalog}.${var.schema}.my_agent
            model_version: "1"
            workload_size: Small
            scale_to_zero_enabled: true
            environment_variables:
              ENABLE_MLFLOW_TRACING: "true"
              MLFLOW_EXPERIMENT_ID: ${var.experiment_id}
              APP_ENVIRONMENT: "production"  # F2c: overrides mlflow.source.type
              DATABRICKS_CLIENT_ID: "{{secrets/agent-prod/client_id}}"
              DATABRICKS_CLIENT_SECRET: "{{secrets/agent-prod/client_secret}}"
```

### SP `CAN_EDIT` on the experiment (critical)

The service principal whose credentials you put on the endpoint **must**
have `CAN_EDIT` on the target MLflow experiment. Without it the
serving runtime gets `403` on `POST /api/2.0/mlflow/traces` and traces
silently drop.

This is the same permission required for end-user feedback (see
[`apps_lakebase/skills/08-appkit-feedback/SKILL.md`](../../../../apps_lakebase/skills/08-appkit-feedback/SKILL.md#cancel-edit)
for the same gotcha on the feedback path).

Grant via the Experiment UI:

```
Experiment → Permissions → Add → "<sp-uuid or sp-name>" → CAN_EDIT
```

Or programmatically via the [permissions API](https://docs.databricks.com/aws/en/dev-tools/api/latest/workspace/permissions).

---

## 3. Databricks Apps path

Apps that host an agent (`@mlflow.genai.agent_server.invoke`,
AppKit-integrated agents, custom servers) are functionally a custom
serving runtime. The same env-var matrix applies.

In `app.yaml`:

```yaml
env:
  - name: ENABLE_MLFLOW_TRACING
    value: "true"
  - name: MLFLOW_EXPERIMENT_ID
    valueFrom:
      configMapKeyRef:
        key: mlflow_experiment_id
  # F2c: app code reads APP_ENVIRONMENT and overrides mlflow.source.type via metadata
  - name: APP_ENVIRONMENT
    value: "production"
  # SP credentials (OAuth mode) — preferred
  - name: DATABRICKS_CLIENT_ID
    valueFrom:
      secretKeyRef:
        name: agent-prod
        key: client_id
  - name: DATABRICKS_CLIENT_SECRET
    valueFrom:
      secretKeyRef:
        name: agent-prod
        key: client_secret
```

The same `CAN_EDIT` requirement applies — grant it to the App's service
principal.

For **Node** apps using the `mlflow-tracing` SDK
([F2b](../../02b-typescript-tracing/SKILL.md)), the env vars and SP
permissions are identical; the SDK reads them at `mlflow.init(...)`
time.

---

## Trace storage and retention

Traces from any of the three deployment shapes land in two places by
default:

| Storage | Lifetime | Use |
|---|---|---|
| **Experiment artifact storage** | Short-term (workspace retention) | UI exploration, ad-hoc debugging |
| **Unity Catalog OTEL Delta tables** | Long-term, governed | SQL queries, dashboards, audit |

For UC OTEL setup (4-table schema, `MLFLOW_TRACING_SQL_WAREHOUSE_ID`,
`MODIFY+SELECT` grants), see
[F2: Unity Catalog OTEL trace storage](../SKILL.md#unity-catalog-otel-trace-storage-mlflow-3-11).

For long-term retention beyond UC OTEL, configure **Production
Monitoring** to copy traces into a managed Delta table:

- See [`sdlc/07-production-monitoring`](../../../sdlc/07-production-monitoring/SKILL.md).
- Production Monitoring pulls from the experiment, applies registered
  scorers, and writes results to Delta on a schedule. This is the
  recommended long-term store for compliance and trend analysis.

## AI Gateway inference tables — alternative

[Mosaic AI Gateway](https://docs.databricks.com/aws/en/generative-ai/ai-gateway) provides an
alternative trace destination via **inference tables**. If you front
your agent with AI Gateway:

- Every request lands in a Delta table you configure on the gateway.
- Trace shape is **request/response level**, not span-level — you do
  not get the nested LLM/tool tree.
- Sync is best-effort and bounded by row size limits.

Use AI Gateway inference tables when your audit requirement is at the
**request/response** grain and you don't need span-level detail. For
agent observability proper, use MLflow tracing as above.

See [`foundation/04-ai-gateway`](../../04-ai-gateway/SKILL.md) for AI
Gateway setup.

---

## Validation checklist

For **every** deployed agent, verify:

- [ ] **Experiment is in a non-Git path** (Agent Framework path).
- [ ] `mlflow.set_experiment(...)` called **before** `agents.deploy(...)` (Agent Framework path).
- [ ] `ENABLE_MLFLOW_TRACING=true` set on the endpoint or App (custom serving / Apps).
- [ ] `MLFLOW_EXPERIMENT_ID` set to the **numeric id** of the target experiment.
- [ ] `APP_ENVIRONMENT` set per deployment (`production` / `staging` / etc.) so app code can override `mlflow.source.type` via [F2c](../../02c-trace-context-and-environments/SKILL.md).
- [ ] Authentication env vars set in **one** mode: PAT or OAuth client id/secret.
- [ ] Service principal has **`CAN_EDIT`** on the target experiment (Experiment → Permissions).
- [ ] First production request produces a trace in the MLflow Experiment UI.
- [ ] (UC OTEL) `MLFLOW_TRACING_SQL_WAREHOUSE_ID` set so traces also land in Delta tables.
- [ ] (UC OTEL) `MODIFY+SELECT` granted to the SP on all four `*_otel_*` tables.
- [ ] (Production Monitoring) Trace ingestion schedule active for long-term retention.

---

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Empty trace UI after deploy. | Experiment is in a Git folder. | Move to `/Shared/...`, redeploy. |
| `403` on first request. | SP missing `CAN_EDIT` on experiment. | Grant `CAN_EDIT` (Experiment → Permissions). |
| Traces appear locally but not from prod. | `ENABLE_MLFLOW_TRACING` not set on endpoint. | Set in `databricks.yml` / `app.yaml`. |
| Traces appear but no token counts / `gen_ai.*` attrs. | Autolog not enabled at module level in deployed code. | Add `mlflow.openai.autolog()` (or matching) in `app.py` / `agent.py`. |
| Traces in UI but missing from UC Delta tables. | `MLFLOW_TRACING_SQL_WAREHOUSE_ID` unset, or SP lacks `MODIFY` on tables. | Set env var; grant `MODIFY+SELECT`. |
| Trace correlation broken on `/feedback`. | Frontend not echoing `traceId`. | Return `traceId` from `/chat`; see [`04c-end-user-feedback`](../../../sdlc/04c-end-user-feedback/SKILL.md). |

---

## Related

- [Foundation Step 2 (Python tracing)](../SKILL.md) — manual + autolog basics, UC OTEL storage.
- [Foundation Step 2b (TypeScript tracing)](../../02b-typescript-tracing/SKILL.md) — Node deployment uses the same env-var matrix.
- [Foundation Step 2c (Trace context and environments)](../../02c-trace-context-and-environments/SKILL.md) — `APP_ENVIRONMENT` override, user / session metadata, custom deployment metadata.
- [`autolog-integrations.md`](autolog-integrations.md) — module-level autolog calls required at deploy time.
- [`tracks/A-custom-agent-apps/07-deploy-and-query`](../../../tracks/A-custom-agent-apps/07-deploy-and-query/SKILL.md) — Track A deployment.
- Upstream [`databricks-model-serving`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-model-serving) — Track C custom CPU serving deployment and debugging reference.
- [`sdlc/06-deployment-and-automation`](../../../sdlc/06-deployment-and-automation/SKILL.md) — `databricks.yml` / `app.yaml` patterns.
- [`sdlc/07-production-monitoring`](../../../sdlc/07-production-monitoring/SKILL.md) — Production Monitoring → Delta.
- [`apps_lakebase/skills/08-appkit-feedback`](../../../../apps_lakebase/skills/08-appkit-feedback/SKILL.md) — same `CAN_EDIT` requirement for end-user feedback.

## References

- [Trace agents deployed on Databricks](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/prod-tracing) — primary source.
- [Databricks Asset Bundles: model serving endpoints](https://docs.databricks.com/aws/en/dev-tools/bundles/resources.html#model_serving_endpoint) — env var schema.
- [Mosaic AI Gateway inference tables](https://docs.databricks.com/aws/en/generative-ai/ai-gateway) — alternative trace destination.

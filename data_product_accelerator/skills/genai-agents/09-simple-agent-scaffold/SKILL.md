---
name: simple-agent-scaffold
description: >
  Scaffold a minimal MCP tool-calling agent with Genie Spaces and deploy it to
  Databricks Model Serving in 5 steps, following the canonical OpenAI MCP
  Tool Calling Agent notebook verbatim. Produces a working endpoint testable in
  AI Playground and consumable by 06-appkit-serving-wiring. No evaluation,
  memory, or prompt registry — add those later via the existing worker skills.
  Use when creating a simple agent, scaffolding a new agent, building a quick
  tool-calling agent, or connecting an agent to Genie Spaces.
  Triggers on "simple agent", "scaffold agent", "MCP agent", "quick agent",
  "create agent", "tool calling agent", "Genie agent", "basic agent".
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.2.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-04-17"
  volatility: medium
  upstream_sources:
    - name: "openai-mcp-tool-calling-agent"
      url: "https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html"
      relationship: "canonical"
      last_synced: "2026-04-15"
---

# Simple Agent Scaffold

Shortest reliable path from "I have Genie Spaces" to "I have a deployed agent endpoint." Follows the [OpenAI MCP Tool Calling Agent](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html) notebook pattern verbatim.

```
Step 1         Step 2          Step 3          Step 4            Step 5
Write ──► Test locally ──► Log MLflow ──► Register UC ──► Deploy Serving
agent.py                                                       │
                                                               ▼
                                                    AI Playground (default)
                                                               │
                                                    ┌──────────┴──────────┐
                                                    ▼                     ▼
                                           06-appkit-serving       Go Further
                                           -wiring (optional)      (optional)
```

## When to Use

- Creating a simple tool-calling agent with Genie Spaces
- Workshop quick-start: zero to deployed endpoint
- Prototyping an agent before adding evaluation, memory, or monitoring

**Not for production-grade multi-agent systems.** Use the full `00-genai-agents-setup` orchestrator for evaluation pipelines, Lakebase memory, prompt registries, and multi-domain orchestration.

---

## Prerequisites

| Requirement | How to verify |
|---|---|
| Databricks workspace with Model Serving | `databricks serving-endpoints list` returns without error |
| At least one Genie Space **answering questions** | Verify end-to-end: open the space in the UI and ask a benchmark question, or via CLI — `databricks genie start-conversation <SPACE_ID> --json '{"content":"<your question>"}' --profile $PROFILE` then `databricks genie create-message`. If it returns a permission error on the underlying tables, fix Genie Space permissions **before proceeding**. |
| Foundation Model API endpoint | `databricks serving-endpoints get databricks-claude-sonnet-4-6` (or your chosen model) |
| Python packages | `pip install databricks-agents databricks-openai "mlflow[databricks]" mcp nest_asyncio uv` (the `[databricks]` extra is required on Azure for `azure-core`) |
| Unity Catalog schema for the registered model | `databricks schemas get <catalog>.<schema>` |
| MLflow experiment (optional but recommended) | Create one in the workspace UI or `mlflow.set_experiment()` |

> **Critical:** do not skip the Genie Space test — a space that exists but can't answer questions produces an agent that only greets and never exercises the tool-calling path.

> **Genie Space fails to answer questions? Three remediation options:**
>
> 1. **Use a different space.** Run `databricks genie list-spaces --profile $PROFILE` and test each one. Pick the first that returns data.
> 2. **Create a new space.** If all existing spaces reference tables you can't access, create a new Genie Space pointing to tables in YOUR gold schema (Workspace → Genie → New Space).
> 3. **Fix permissions on the existing space.** Ask a catalog admin to grant you `SELECT` on the tables the Genie Space references. Check the space's "Tables" tab to see which tables it uses.
>
> **Do not proceed to Step 1 until the Genie Space answers a data question successfully.** An agent wired to a broken Genie Space will deploy but fail every data query, wasting the entire build-test-deploy cycle.

---

## Decision Defaults

| Decision | Default | Go Further |
|---|---|---|
| Agent framework | `MCPToolCallingAgent(ResponsesAgent)` per MCP notebook | — |
| LLM client | `DatabricksOpenAI` (OpenAI SDK compatible) | — |
| Genie access | `McpServerToolkit` with MCP server URLs | `05-multi-agent-genie-orchestration` for Conversation API |
| Streaming | Yes (`predict_stream` + `output_to_responses_items_stream`) | — |
| Memory | None (stateless) | `03-lakebase-memory-patterns` |
| Evaluation | Skip | `02-mlflow-genai-evaluation` |
| Prompt management | Inline system prompt via `ModelConfig` | `04-prompt-registry-patterns` |
| Deployment | `databricks.agents.deploy()` | `06-deployment-automation` for CI/CD |
| Frontend | AI Playground (default) | `06-appkit-serving-wiring` for AppKit UI |

---

## Step 1: Write `agent.py`

Copy the template and its config file to your project directory:

```bash
cp references/agent-template.py agent.py
cp references/agent-config.yaml agent-config.yaml
```

Open `agent-config.yaml` and resolve the three TODO blocks:

1. **`llm_endpoint`** — Verify the Foundation Model API endpoint name exists in your workspace.
2. **`system_prompt`** — Write domain-specific instructions for your agent.
3. **`genie_spaces`** — Replace each `TODO_REPLACE_WITH_SPACE_ID` with a real Genie Space ID. Add or remove entries as needed.

Finding Genie Space IDs:

```
Workspace → Genie → open a space → the ID is in the URL:
https://<workspace>.databricks.com/spaces/<SPACE_ID>/...
```

The MCP server URL format for Genie Spaces is:

```
{host}/api/2.0/mcp/genie/{space_id}
```

### What the template contains

The template is the notebook's `MCPToolCallingAgent` class with one addition: `ModelConfig` for parameterization via `agent-config.yaml`. The class structure is identical to the canonical notebook:

| Method | Purpose |
|---|---|
| `__init__` | Creates `DatabricksOpenAI` client, connects `McpServerToolkit` servers, builds `tools_dict` |
| `execute_tool` | Traced with `@mlflow.trace(span_type=SpanType.TOOL)` |
| `call_llm` | Traced with `@mlflow.trace(span_type=SpanType.LLM)`, streams via `chat.completions.create` |
| `handle_tool_call` | Parses arguments, executes tool, returns `ResponsesAgentStreamEvent` |
| `call_and_run_tools` | Iterative tool-calling loop with `max_iter=10` |
| `predict` | Non-streaming entry point, delegates to `predict_stream` |
| `predict_stream` | Streaming entry point, converts `request.input` to messages |

At the bottom: `mlflow.openai.autolog()` enables automatic tracing and `mlflow.models.set_model(AGENT)` binds the model for logging.

### Critical rules (from `01-responses-agent-patterns`)

- **ResponsesAgent is mandatory** — not ChatAgent, not PythonModel.
- **Never pass a `signature` parameter** to `log_model()` — MLflow auto-infers it.
- **Use `input` key, not `messages`** — `{"input": [{"role": "user", "content": "..."}]}`.
- **`nest_asyncio` is required** — MCP servers use async internally; `nest_asyncio.apply()` avoids event loop conflicts in notebook environments.

**Gate:** `agent.py` exists with all TODOs in `agent-config.yaml` resolved. No `TODO_REPLACE` strings remain.

---

## Step 2: Test locally

### Running Steps 2–5 as a job (recommended for workshops)

If you don't have an interactive cluster attached, combine Steps 2–5 into a single Databricks notebook and submit it as a serverless job:

```bash
databricks jobs submit --no-wait --profile $PROFILE --json '{
  "run_name": "deploy-agent",
  "tasks": [{"task_key": "deploy", "notebook_task": {
    "notebook_path": "/Workspace/Users/<your-email>/booking_app_agents/deploy_agent"
  }, "environment_key": "default"}],
  "environments": [{"environment_key": "default", "spec": {
    "client": "1",
    "dependencies": [
      "databricks-agents","databricks-openai","mlflow[databricks]",
      "mcp","nest_asyncio","uv"
    ]
  }}]
}'
```

Always use serverless (`environment_key`), not classic clusters (`new_cluster`). Workshop and restricted workspaces often block classic clusters with `NETWORK_CONFIGURATION_FAILURE`.

**Important:** when running as a job the working directory is NOT the notebook's directory. This is why `model_config="agent-config.yaml"` is required in Step 3.

See [references/job-submission.md](references/job-submission.md) for the polling loop and failure-mode table.

### Running Steps 2–5 interactively

In a notebook or Python REPL, import and test both prediction paths:

```python
# Cell 1: Restart Python if you edited agent.py
# dbutils.library.restartPython()  # (uncomment in Databricks notebook)

# Cell 2: Test non-streaming
from agent import AGENT

result = AGENT.predict(
    {"input": [{"role": "user", "content": "What were total sales last month?"}]}
)
print(result.model_dump(exclude_none=True))
```

```python
# Cell 3: Test streaming
for chunk in AGENT.predict_stream(
    {"input": [{"role": "user", "content": "What were total sales last month?"}]}
):
    print(chunk.model_dump(exclude_none=True))
```

Replace the test question with something your Genie Space can actually answer.

**Gate:** Both `predict` and `predict_stream` return valid, non-empty responses. MLflow traces are visible in the experiment UI (check the Traces tab).

---

## Step 3: Log with MLflow

Log the agent as code. This captures the `agent.py` file, its dependencies, and resource declarations for automatic authentication passthrough.

```python
import mlflow
from agent import LLM_ENDPOINT_NAME
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksGenieSpace
from pkg_resources import get_distribution

# Declare all resources the agent accesses at runtime.
# Auth passthrough provisions short-lived credentials automatically.
resources = [
    DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME),
    DatabricksGenieSpace(genie_space_id="<GENIE_SPACE_ID>"),  # one per space
]

with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",
        model_config="agent-config.yaml",  # REQUIRED — see note below
        resources=resources,
        pip_requirements=[
            f"mlflow[databricks]=={get_distribution('mlflow').version}",
            f"mcp=={get_distribution('mcp').version}",
            f"databricks-openai=={get_distribution('databricks-openai').version}",
        ],
    )
```

Key points:
- **NO `signature` parameter.** ResponsesAgent auto-infers it.
- **`python_model="agent.py"`** logs as "models from code" — MLflow loads the file, not a pickled object.
- **`model_config="agent-config.yaml"`** is required — MLflow copies `agent.py` to a temp dir for validation where the yaml isn't present. Without this parameter you get `FileNotFoundError: Config file is not provided`. Fixing `__file__` / path tricks won't help; the parameter bypasses the file lookup.
- **Use `mlflow[databricks]`, not bare `mlflow`.** On Azure the `[databricks]` extra ships `azure-core` and related storage SDKs required by `register_model()`. On AWS/GCP it adds harmless extras. Matches the `pip install` line in Prerequisites.
- **`resources`** enables Automatic Auth Passthrough — the deployed endpoint gets short-lived credentials for each declared resource.
- Add one `DatabricksGenieSpace(genie_space_id="...")` per Genie Space so auth passthrough covers them.

### Pre-deployment validation

Before registering, run the pre-deployment check:

```python
mlflow.models.predict(
    model_uri=f"runs:/{logged_agent_info.run_id}/agent",
    input_data={"input": [{"role": "user", "content": "Hello!"}]},
    env_manager="uv",
)
```

This loads the agent in an isolated environment and runs a prediction, catching dependency or serialization issues.

**Gate:** `logged_agent_info` returned successfully. `mlflow.models.predict()` returns a valid response.

---

## Step 4: Register in Unity Catalog

```python
mlflow.set_registry_uri("databricks-uc")

# TODO: Set your catalog, schema, and model name
catalog = "my_catalog"
schema = "my_schema"
model_name = "my_genie_agent"
UC_MODEL_NAME = f"{catalog}.{schema}.{model_name}"

uc_registered_model_info = mlflow.register_model(
    model_uri=logged_agent_info.model_uri,
    name=UC_MODEL_NAME,
)
```

**Gate:** `uc_registered_model_info` returned with a version number. Verify in the Unity Catalog UI: Catalog → Models → your model.

---

## Step 5: Deploy to Model Serving

```python
from databricks import agents

agents.deploy(
    UC_MODEL_NAME,
    uc_registered_model_info.version,
    tags={"endpointSource": "simple-agent-scaffold"},
)
```

This creates (or updates) a Model Serving endpoint with:
- Automatic Auth Passthrough for declared resources
- OBO authentication (runs with the caller's permissions)
- AI Playground integration

### Verify deployment

```bash
# Check endpoint status
databricks serving-endpoints get <endpoint-name>

# Test with a query
databricks serving-endpoints query <endpoint-name> \
  --input '{"input": [{"role": "user", "content": "What were total sales last month?"}]}'
```

The endpoint name is derived from the UC model name (dots replaced with hyphens). Check the Serving UI if unsure.

### Grant service principal permissions (required for Genie tools)

`agents.deploy()` creates a system SP for the endpoint. Without `CAN_USE` on the SQL warehouse the agent can answer greetings but every Genie tool call fails with `PERMISSION_DENIED`.

Find the SP UUID from the endpoint's **Events** tab in the Serving UI, or from the first `PERMISSION_DENIED` error message.

Grant the SP `CAN_USE` on the warehouse via the Permissions API:

```python
import os, requests

WAREHOUSE_ID = "TODO_WAREHOUSE_ID"
SP_UUID = "TODO_SP_UUID"

response = requests.patch(
    f"{os.environ['DATABRICKS_HOST']}/api/2.0/permissions/sql/warehouses/{WAREHOUSE_ID}",
    headers={"Authorization": f"Bearer {os.environ['DATABRICKS_TOKEN']}"},
    json={
        "access_control_list": [
            {"service_principal_name": SP_UUID, "permission_level": "CAN_USE"}
        ]
    },
)
assert response.status_code == 200, response.text
```

Grant the SP `SELECT` on the UC tables the Genie Space reads (SQL, run as a workspace admin or owner):

```sql
GRANT USE CATALOG ON CATALOG <catalog> TO `<sp-uuid>`;
GRANT USE SCHEMA ON SCHEMA <catalog>.<schema> TO `<sp-uuid>`;
GRANT SELECT ON SCHEMA <catalog>.<schema> TO `<sp-uuid>`;
```

In AI Playground, OBO uses the **caller's** identity — users with table access get data regardless of SP grants. SP grants matter for programmatic/API-token access (including end-user apps calling the endpoint with a service token).

### Verify with a data question

After granting, smoke-test the endpoint with a real data query (not just a greeting):

```bash
curl -s "$DATABRICKS_HOST/serving-endpoints/<endpoint-name>/invocations" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "How many bookings were made last month?"}]}'
```

A successful response contains data or a meaningful Genie answer, not a `PERMISSION_DENIED`.

Full CLI equivalents, OBO-vs-SP matrix, and multi-warehouse patterns: see [references/post-deploy-permissions.md](references/post-deploy-permissions.md).

**Gate:** ALL of the following:

1. Endpoint reaches `READY` state.
2. Test query with a **greeting** returns a valid response (confirms endpoint is live).
3. Test query with a **domain-specific data question** returns data or a meaningful Genie response (confirms the tool-calling path works end-to-end).
4. Agent is visible and testable in AI Playground.

If step 3 fails with `PERMISSION_DENIED`, see "Grant service principal permissions" above. If step 3 returns a Genie error about table access, the Genie Space itself needs table permissions — revisit Prerequisites.

---

## What's Next

### Wire to AppKit UI (recommended)

The deployed endpoint from Step 5 is ready to be consumed by an AppKit application.

1. **Note your endpoint name** — this becomes the value for `DATABRICKS_SERVING_ENDPOINT_NAME` in the AppKit `app.yaml`.
2. **Read [06-appkit-serving-wiring](../../../../apps_lakebase/skills/06-appkit-serving-wiring/SKILL.md)** — start at Step 2 (Configure `app.yaml`). The wiring skill covers Serving plugin registration, resource binding, streaming chat hooks, and server-side proxy patterns.
3. If you haven't registered the Serving plugin yet, first read [04-appkit-plugin-add](../../../../apps_lakebase/skills/04-appkit-plugin-add/SKILL.md) with [references/plugin-serving.md](../../../../apps_lakebase/skills/04-appkit-plugin-add/references/plugin-serving.md).

> **Contract the UI layer must honor** (when wiring this endpoint into an AppKit app via `06-appkit-serving-wiring`):
>
> 1. **Payload:** send `{"input": [{"role":"user","content":"..."}]}` to the endpoint — **not** `{"messages": [...]}`. Sending `messages` produces `400: Model is missing inputs ['input']`.
> 2. **Streaming chunks:** this agent emits the Databricks Responses API format — `{ type: "response.output_text.delta", delta: "..." }` — not OpenAI chat completion. Parsers that read only `chunk.choices[0].delta.content` will return empty strings.
> 3. **SP grants matter:** permissions apply to API-token callers, including Apps-to-endpoint. AI Playground uses OBO, so it can succeed while the app's SP fails. If a domain question returns an empty greeting in the app but works in Playground, the SP lacks a tool grant — see [references/post-deploy-permissions.md](references/post-deploy-permissions.md).
>
> If wiring via the AppKit `serving()` plugin, items 1 and 2 are handled automatically by the plugin. If building a custom proxy (plugin unavailable, older AppKit version), see [06-appkit-serving-wiring/references/custom-proxy-fallback.md](../../../../apps_lakebase/skills/06-appkit-serving-wiring/references/custom-proxy-fallback.md) and [06-appkit-serving-wiring/references/sse-format-patterns.md](../../../../apps_lakebase/skills/06-appkit-serving-wiring/references/sse-format-patterns.md) for the transformation + dual parser.

### Add capabilities (optional)

Each add-on is an independent worker skill. Pick only what you need:

| Capability | Skill to read | What it adds |
|---|---|---|
| Evaluation | `02-mlflow-genai-evaluation` | LLM judges, custom scorers, pre-deployment quality gates |
| Memory | `03-lakebase-memory-patterns` | Conversation continuity (CheckpointSaver), user preferences (DatabricksStore) |
| Prompt management | `04-prompt-registry-patterns` | Externalized prompts via Unity Catalog, A/B testing |
| Multi-domain orchestration | `05-multi-agent-genie-orchestration` | Conversation API, intent classification, parallel domain queries |
| CI/CD deployment | `06-deployment-automation` | Deployment jobs triggered by model version creation |
| Production monitoring | `07-production-monitoring` | Registered scorers, trace archival, monitoring dashboards |

### Full production agent

For the complete 9-phase implementation (foundation through monitoring), use `00-genai-agents-setup`. It orchestrates all of the above worker skills in the recommended order.

---

## Gotchas

| Gotcha | Symptom | Fix |
|---|---|---|
| Manual `signature` in `log_model()` | AI Playground fails to load agent | Never pass `signature`; ResponsesAgent auto-infers |
| `messages` key instead of `input` | Agent receives empty input | Use `{"input": [{"role": "user", "content": "..."}]}` |
| `nest_asyncio` missing | `RuntimeError: This event loop is already running` | Include `import nest_asyncio; nest_asyncio.apply()` at top of `agent.py` |
| OBO not working in notebook | Permission errors or wrong user context | Expected — OBO only activates in Model Serving context. Notebook uses default auth. |
| Genie MCP URL wrong format | `404` or `Connection refused` from MCP server | Format: `{host}/api/2.0/mcp/genie/{space_id}` (no trailing slash) |
| Duplicate tool names across MCP servers | `ValueError` at agent init | Set unique `name` on each `McpServerToolkit` to namespace tool names |
| `asyncio` event loop errors at deploy | Unpredictable agent behavior | Use synchronous code patterns; avoid custom event loops (Databricks manages async) |
| `TODO_REPLACE` strings left in config | Agent fails at MCP server connection | Resolve all TODOs in `agent-config.yaml` before testing |
| Model not found in UC | `register_model` fails | Verify `catalog.schema` exists and you have CREATE MODEL permission |
| Endpoint stuck in `PENDING` | Deploy appears to hang | Check endpoint events in Serving UI; common cause is dependency resolution. Ensure `uv` is in pip requirements. |
| `FileNotFoundError: Config file is not provided` inside `log_model()` / `_load_model_code_path` | MLflow copies `agent.py` to a temp dir for validation; `agent-config.yaml` isn't there | Add `model_config="agent-config.yaml"` to `log_model()`. Do NOT try to fix `__file__` / relative paths — it's a framework lifecycle issue, not a path issue. |
| `ModuleNotFoundError: azure.core` during `register_model()` | Bare `mlflow` lacks the Azure storage SDK | Install `"mlflow[databricks]"` (also covers AWS/GCP) |
| `PERMISSION_DENIED: ... not authorized to use this SQL Endpoint` post-deploy | Endpoint SP lacks warehouse `CAN_USE` | Grant via Permissions API — SP UUID is in the error message. See [references/post-deploy-permissions.md](references/post-deploy-permissions.md). |
| `NETWORK_CONFIGURATION_FAILURE` when submitting a job | Classic cluster can't reach control plane | Use serverless: `environment_key` + `environments` spec, not `new_cluster`. |
| Agent answers greetings but fails on data questions | SP has endpoint access but not warehouse/table access | Grant `CAN_USE` on warehouse + `SELECT` on gold tables. Or test in AI Playground (OBO uses your credentials). |

---

## Debugging decision tree for `log_model()` and `register_model()` errors

When `log_model()` or `register_model()` fails, match the error to a branch before retrying:

```
log_model() / register_model() failed
│
├── FileNotFoundError / "Config file is not provided"
│   │
│   ├── Trace shows _load_model_code_path / exec_module / MLflow internals
│   │     → Framework lifecycle error, not a path error.
│   │       Fix: add model_config="agent-config.yaml" to log_model().
│   │       Do NOT touch __file__, os.getcwd(), or Path() juggling.
│   │
│   └── Trace shows your own code reading a file
│         → Real missing file. Check path and CWD.
│
├── ModuleNotFoundError (azure.core, boto3, google.cloud, etc.)
│     → Bare `mlflow` is missing cloud storage SDKs.
│       Fix: install and declare `mlflow[databricks]` (covers all clouds).
│
├── "Model not found" / UC registration failure
│     → Catalog/schema missing or caller lacks CREATE MODEL.
│       Fix: verify `registered_model_name = "<catalog>.<schema>.<name>"`,
│       confirm CREATE MODEL on the schema, create catalog/schema if needed.
│
└── Timeout / endpoint stuck in PENDING
      → Dependency resolution or networking.
        Check the endpoint Events tab. Ensure `uv` is in pip_requirements.
        In restricted workspaces, resubmit as a serverless job.
```

**Key principle:** when the error comes from a framework's internal loader (not your code), the fix is almost never a path change — it's using the framework's parameter that passes context into the loading step.

---

## Anti-Patterns

When a run fails, check whether you're falling into one of these reasoning traps before trying another variant of the same fix:

- **`FileNotFoundError` from a framework loader ≠ a path problem.** When the trace comes from `_load_model_code_path`, `exec_module`, or any framework-internal loader, the fix is almost never a path change — it's passing context into the loading step (e.g., `model_config=` for MLflow).
- **"Genie Space exists" ≠ "Genie Space works."** Listing a space proves it was created, not that its tables are queryable. Always ask a real question from Step 0 before wiring it into an agent.
- **Classic cluster is not the default.** In restricted/workshop workspaces, serverless is the safe default. Check prior compute patterns in `.vibecoding-state.md` before picking a cluster type.
- **`READY` endpoint ≠ working agent.** An endpoint that only answers greetings has never exercised the tool-calling path. Verify with a domain-specific data question.
- **Same error class after retry ≠ try another variant — change approach.** If two path-style fixes produce the same framework-loader error, the category of fix is wrong. Step back and understand the framework's lifecycle.

---

## References

### Source notebook

- [OpenAI MCP Tool Calling Agent](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html) — the canonical notebook this skill follows verbatim

### Official documentation

- [Author an agent for Model Serving](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent-model-serving) — ResponsesAgent patterns, ModelConfig, deployment considerations
- [MLflow ResponsesAgent](https://mlflow.org/docs/latest/genai/serving/responses-agent) — API reference
- [MCP on Databricks](https://docs.databricks.com/aws/en/generative-ai/mcp/) — Managed MCP servers overview
- [Deploy an AI agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/deploy-agent) — `databricks.agents.deploy()` reference
- [Log an AI agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/log-agent) — Resource declarations and auth passthrough

### Related skills

| Skill | Relationship |
|---|---|
| `01-responses-agent-patterns` | Critical rules for ResponsesAgent (this skill follows them) |
| `06-appkit-serving-wiring` | Wires the deployed endpoint into an AppKit UI |
| `00-genai-agents-setup` | Full production orchestrator (uses this as a quick-start entry point) |

---

## Version History

| Date | Version | Changes |
|---|---|---|
| Apr 15, 2026 | 1.0.0 | Initial creation — canonical notebook pattern with ModelConfig parameterization |
| Apr 17, 2026 | 1.1.0 | Apply retro v2 actions 1-6: Genie Space verification in prereqs, `mlflow[databricks]`, `model_config` in `log_model`, uncommented `DatabricksGenieSpace`, Step 2 job-submission callout, Step 5 SP permissions, 3 new gotchas, Anti-Patterns block, `references/post-deploy-permissions.md` + `references/job-submission.md` |
| Apr 17, 2026 | 1.2.0 | Apply retro v3 actions 1-6: 3-option Genie Space remediation, inlined serverless default (full JSON in Step 2) + preventive SP grant code + `mlflow[databricks]` in Step 3 `pip_requirements` + structured debugging decision tree + tightened Step 5 gate (numbered list) + 2 new gotchas (`NETWORK_CONFIGURATION_FAILURE`, greetings-vs-data) |

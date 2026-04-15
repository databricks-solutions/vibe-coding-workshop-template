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
  version: "1.0.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-04-15"
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
| At least one Genie Space | Workspace → Genie → confirm a space exists and you have access |
| Foundation Model API endpoint | `databricks serving-endpoints get databricks-claude-sonnet-4-6` (or your chosen model) |
| Python packages | `pip install databricks-agents databricks-openai mlflow mcp nest_asyncio uv` |
| Unity Catalog schema for the registered model | `databricks schemas get <catalog>.<schema>` |
| MLflow experiment (optional but recommended) | Create one in the workspace UI or `mlflow.set_experiment()` |

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
    # Add one DatabricksGenieSpace per Genie Space:
    # DatabricksGenieSpace(genie_space_id="<SPACE_ID>"),
]

with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",
        resources=resources,
        pip_requirements=[
            f"mlflow=={get_distribution('mlflow').version}",
            f"mcp=={get_distribution('mcp').version}",
            f"databricks-openai=={get_distribution('databricks-openai').version}",
        ],
    )
```

Key points:
- **NO `signature` parameter.** ResponsesAgent auto-infers it.
- **`python_model="agent.py"`** logs as "models from code" — MLflow loads the file, not a pickled object.
- **`resources`** enables Automatic Auth Passthrough — the deployed endpoint gets short-lived credentials for each declared resource.
- Add `DatabricksGenieSpace(genie_space_id="...")` for each Genie Space so auth passthrough covers them.

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

**Gate:** Endpoint reaches `READY` state. Test query returns a valid response. Agent is visible and testable in AI Playground.

---

## What's Next

### Wire to AppKit UI (recommended)

The deployed endpoint from Step 5 is ready to be consumed by an AppKit application.

1. **Note your endpoint name** — this becomes the value for `DATABRICKS_SERVING_ENDPOINT_NAME` in the AppKit `app.yaml`.
2. **Read [06-appkit-serving-wiring](../../../../apps_lakebase/skills/06-appkit-serving-wiring/SKILL.md)** — start at Step 2 (Configure `app.yaml`). The wiring skill covers Serving plugin registration, resource binding, streaming chat hooks, and server-side proxy patterns.
3. If you haven't registered the Serving plugin yet, first read [04-appkit-plugin-add](../../../../apps_lakebase/skills/04-appkit-plugin-add/SKILL.md) with [references/plugin-serving.md](../../../../apps_lakebase/skills/04-appkit-plugin-add/references/plugin-serving.md).

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

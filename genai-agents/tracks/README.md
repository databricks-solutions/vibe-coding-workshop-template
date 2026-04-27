# Agent Creation Track

> **Track A is the canonical track.** This directory holds the canonical
> custom-agent skill set. Other agent shapes (Supervisor API, Model
> Serving, Node-native) are outside the root course path. The previously
> bundled B/C track mirrors have been removed during the 2026-04-27
> consolidation; for canonical Databricks-platform reference patterns see
> [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills)
> (`databricks-agent-bricks`, `databricks-model-serving`). Use the course
> orchestrator for routing before leaving Track A.

> **Shared prerequisite:** All tracks build on
> [F3: Tools and Data Access](../foundation/03-tools-and-data-access/SKILL.md),
> which covers Databricks managed MCP servers (Vector Search, Genie, SQL,
> UC Functions), external MCP connections, resource grants, and retriever
> schemas. Complete F3 before starting any track's tool wiring step.

## Track A: Custom Agent on Databricks Apps (canonical)

| Step | Skill | Purpose |
|------|-------|---------|
| A1 | [Clone and Run](./A-custom-agent-apps/01-clone-and-run/SKILL.md) | Clone an `agent-openai-*` template; pick `agent-openai-advanced` for canonical SkyLoyalty memory pattern |
| A2 | [Agent Framework (Option B)](./A-custom-agent-apps/02-agent-framework/SKILL.md) | Module-level `@mlflow.genai.agent_server.invoke` / `@stream` handlers for Databricks Apps |
| A3 | [Tools and MCP](./A-custom-agent-apps/03-tools-and-mcp/SKILL.md) | Wire KA + Genie + UC functions as `@function_tool`s; emit `databricks.yml` + `app.yaml` resource grants |
| A4 | [Authentication](./A-custom-agent-apps/04-authentication/SKILL.md) | App SP + User OBO via `get_user_workspace_client(http_request)`; `user_api_scopes` in `app.yaml` |
| A5 | [Lakebase Memory](./A-custom-agent-apps/05-lakebase-memory/SKILL.md) | `agent-openai-advanced` two-layer memory: `AsyncDatabricksSession` + `LongTermMemory` |
| A6 | [Evaluation](./A-custom-agent-apps/06-evaluation/SKILL.md) | Smoke test: `agent-evaluate`, judges, dataset |
| A7 | [Deploy and Query](./A-custom-agent-apps/07-deploy-and-query/SKILL.md) | First manual deploy to Databricks Apps; capture `agent_app_url` + `agent_app_name` |
| A8 | [Debugging](./A-custom-agent-apps/08-debugging/SKILL.md) | Apps-specific debugging |

After A7, wire Track A to an AppKit dashboard with
[`apps_lakebase/skills/06d-appkit-agent-app-proxy`](../../apps_lakebase/skills/06d-appkit-agent-app-proxy/SKILL.md).

## When to leave canonical

If the canonical 2-Apps + Track A path doesn't fit, use the course orchestrator
to route to available alternates. The previously bundled B/C track mirrors have
been removed; for canonical reference patterns consult the upstream
[`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills)
registry:

- Hosted-loop agent (Databricks runs the loop, hosted tools only) — upstream `databricks-agent-bricks`
- `mlflow.pyfunc.ResponsesAgent` on a Model Serving endpoint — upstream `databricks-model-serving`
- Node-native end-to-end with `@openai/agents` is not bundled as a root course path in this template

## Interface contract

All tracks (canonical + alternates) produce the same output for the SDLC pipeline:

```python
def predict_fn(inputs: dict) -> str:
    """Takes {'question': '...'}, returns the agent's text response."""
```

The SDLC pipeline (evaluation, registration, deployment, monitoring) is
identical regardless of which track produced `predict_fn`.

## Directory layout

```
tracks/
└── A-custom-agent-apps/        (canonical)
    ├── 01-clone-and-run/SKILL.md
    ├── 02-agent-framework/SKILL.md
    ├── 03-tools-and-mcp/SKILL.md
    ├── 04-authentication/SKILL.md
    ├── 05-lakebase-memory/SKILL.md
    ├── 06-evaluation/SKILL.md
    ├── 07-deploy-and-query/SKILL.md
    └── 08-debugging/SKILL.md
```

The B-supervisor-api and C-model-serving track mirrors were removed during
the 2026-04-27 consolidation. Consult the upstream
[`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills)
registry for canonical hosted-tool and serving patterns.

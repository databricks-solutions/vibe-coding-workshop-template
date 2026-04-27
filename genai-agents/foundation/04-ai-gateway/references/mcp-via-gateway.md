# MCP Servers Through AI Gateway

Just like LLM endpoints, MCP servers can be fronted by the AI Gateway for uniform observability, audit, rate limits, and guardrails on **tool calls**. This matters because tool calls frequently reach internal APIs (databases, CRMs, ticketing) — the gateway is where you apply tenant isolation and audit.

---

## When to Proxy MCP Through a Gateway

Add a gateway in front of an MCP server when:

- Multiple agents share the same MCP and you need per-agent rate limits.
- Tool responses contain data that must be audited (e.g. customer PII).
- Tool calls must be restricted by user identity (on-behalf-of auth).
- You need the same inference-table pattern for tool I/O that you have for LLM I/O.

For a single-team MCP used by a single agent, running the MCP directly is fine.

---

## Config Sketch

MCP endpoints register as `served_entities` with a payload shape marked for MCP. Exact JSON is versioned with Databricks CLI — confirm against the current [Databricks AI Gateway docs](https://docs.databricks.com/aws/en/ai-gateway/).

```bash
databricks serving-endpoints create \
  --json '{
    "name": "skyloyalty-mcp-gateway",
    "ai_gateway": {
      "usage_tracking_config": {"enabled": true},
      "inference_table_config": {
        "enabled": true,
        "catalog_name": "main",
        "schema_name": "skyloyalty_ops",
        "table_name_prefix": "mcp_"
      },
      "rate_limits": [{"key": "user", "renewal_period": "minute", "calls": 60}]
    },
    "config": {
      "served_entities": [{
        "name": "skyloyalty-mcp",
        "entity_type": "mcp",
        "entity_name": "skyloyalty-ops-mcp",
        "entity_version": "v1"
      }]
    }
  }'
```

---

## Auth On Behalf Of (OBO)

MCP tool calls frequently need to run *as the end user*, not as the agent service principal, so UC row-level and column-level security applies correctly.

Pattern:

1. Agent authenticates to gateway with its service principal token.
2. Agent includes the user's OBO token in a header: `X-Databricks-User-Token: <obo-token>`.
3. Gateway forwards this header to the MCP server.
4. MCP server uses the user token for all downstream UC operations.

```python
from databricks.sdk import WorkspaceClient

def call_mcp_tool(tool_name: str, args: dict, user_obo_token: str) -> dict:
    w = WorkspaceClient()
    return w.serving_endpoints.query(
        name="skyloyalty-mcp-gateway",
        inputs={"tool": tool_name, "arguments": args},
        extra_headers={
            "X-Databricks-User-Token": user_obo_token,
            "databricks_request_id": current_mlflow_request_id(),
        },
    ).outputs
```

OBO tokens for Databricks Apps are available via `WorkspaceClient(auth_type="...")` — see [tracks/A-custom-agent-apps/06-authentication](../../../tracks/A-custom-agent-apps/06-authentication/SKILL.md) if it exists, or the Databricks Apps auth docs.

---

## Inference Tables for MCP

Schema mirrors LLM inference tables but with tool-call specific columns:

| Column | Meaning |
|--------|---------|
| `tool_name` | Which MCP tool was called |
| `arguments_json` | Full tool arguments (subject to redaction) |
| `result_json` | Tool response |
| `execution_time_ms` | Tool latency |
| `user_identity` | OBO user if the header was forwarded |

This table is gold for debugging: "which tool call on which tenant fails most often?"

---

## Joining MCP and LLM Traces

Within an MLflow trace, LLM calls and tool calls are separate spans. With the gateway:

- LLM spans correlate to `gw_*_payload` via `databricks_request_id`.
- MCP spans correlate to `mcp_*_payload` via `databricks_request_id`.

A single trace with one user turn may span 1 LLM call and 3 tool calls → 4 gateway rows joined by the same trace request_id.

SQL recipe to enumerate a trace's full event timeline:

```sql
SELECT 'llm' AS kind, request_time, execution_time_ms, status_code, served_entity_id
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_payload
WHERE databricks_request_id = :trace_id
UNION ALL
SELECT 'tool' AS kind, request_time, execution_time_ms, status_code, tool_name
FROM main.skyloyalty_ops.mcp_skyloyalty_mcp_gateway_payload
WHERE databricks_request_id = :trace_id
ORDER BY request_time;
```

---

## Tradeoffs

- **Pros:** Central audit, OBO enforcement at a chokepoint, uniform rate limits.
- **Cons:** Extra hop adds 10–50 ms per tool call; MCP-through-gateway is a newer pattern — confirm provider support in [docs](https://docs.databricks.com/aws/en/ai-gateway/) before committing.

For production agents with compliance requirements, the audit trail is usually worth the latency.

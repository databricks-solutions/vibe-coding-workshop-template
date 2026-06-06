# Managed MCP Servers — Deep Reference

Per-server-type examples for connecting to Databricks managed MCP servers using
`DatabricksMCPClient` (recommended) or the standard MCP SDK. Includes `_meta`
parameter configurations and polling patterns.

Primary source: [Managed MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp)

---

## Shared Setup

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

workspace_client = WorkspaceClient()
host = workspace_client.config.host
```

For async code using the standard MCP SDK:

```python
from databricks_mcp import DatabricksOAuthClientProvider
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
```

---

## URL Patterns and OAuth Scopes

| MCP Server | URL Pattern | OAuth Scope |
|---|---|---|
| AI Search (formerly Vector Search) | `{host}/api/2.0/mcp/ai-search/{catalog}/{schema}/{index_name}` | `ai-search` |
| Genie Space | `{host}/api/2.0/mcp/genie/{genie_space_id}` | `genie` |
| Genie (cross-space) | `{host}/api/2.0/mcp/genie` | `genie` |
| Databricks SQL | `{host}/api/2.0/mcp/sql` | `sql` |
| UC Functions | `{host}/api/2.0/mcp/functions/{catalog}/{schema}/{function_name}` | `unity-catalog` |

> The legacy `/api/2.0/mcp/vector-search/...` prefix and `vector-search` scope
> remain valid for backward compatibility; `ai-search` is the current name.

When using on-behalf-of user authentication, include the corresponding OAuth
scope for each server your application needs. See
[Connect clients using OAuth](https://docs.databricks.com/aws/en/generative-ai/mcp/connect-external-services#connect-oauth).

---

## Vector Search MCP

Semantic search over Databricks Vector Search indexes. The index must use
Databricks managed embeddings.

### Connect with `DatabricksMCPClient`

```python
vs_url = f"{host}/api/2.0/mcp/ai-search/prod/docs/knowledge_index"

mcp_client = DatabricksMCPClient(
    server_url=vs_url,
    workspace_client=workspace_client,
)

tools = mcp_client.list_tools()
print(f"Vector Search tools: {[t.name for t in tools]}")

result = mcp_client.call_tool(
    "prod__docs__knowledge_index",
    {"query": "How do I reset my password?"}
)
print(result.content[0].text)
```

Tool names follow the pattern `{catalog}__{schema}__{index_name}` with double
underscores replacing dots.

### Connect with OpenAI Agents SDK (`MCPServerSse`)

```python
from agents.mcp import MCPServerSse

ai_search_mcp = MCPServerSse(
    url=f"https://{host}/api/2.0/mcp/ai-search/prod/docs/knowledge_index",
    headers={"Authorization": f"Bearer {workspace_client.config.token}"},
)
```

### Vector Search `_meta` Parameters

Control search behavior deterministically with `_meta`:

```python
from mcp.types import CallToolRequest, CallToolResult

request = CallToolRequest(
    method="tools/call",
    params={
        "name": "prod__docs__knowledge_index",
        "arguments": {
            "query": "How do I reset my password?"
        },
        "_meta": {
            "num_results": "3",
            "filters": '{"updated_after": "2024-01-01"}',
            "query_type": "HYBRID",
            "columns": "id,text,metadata",
            "score_threshold": "0.5",
            "include_score": "true",
            "columns_to_rerank": "text,title",
        }
    }
)

response = await session.send_request(request, CallToolResult)
```

| Parameter | Type | Description |
|---|---|---|
| `num_results` | int | Number of results to return |
| `filters` | str | JSON string of filters to apply |
| `query_type` | str | `"ANN"` (default, approximate nearest neighbor) or `"HYBRID"` (vector + keyword) |
| `columns` | str | Comma-separated column names to return. Default: all non-internal columns |
| `columns_to_rerank` | str | Comma-separated columns for reranking model to re-score |
| `include_score` | bool | `"true"` or `"false"` (default). Include similarity score |
| `score_threshold` | float | Minimum similarity score. Results below are excluded |

---

## Genie Space MCP

Query Genie Spaces to analyze structured data using natural language. Read-only.

Genie MCP invokes Genie as a tool, which means conversation history is not
passed to the Genie API. To preserve history, use
[Genie in a multi-agent system](https://docs.databricks.com/aws/en/generative-ai/agent-framework/multi-agent-genie)
instead.

### Connect with `DatabricksMCPClient`

```python
genie_url = f"{host}/api/2.0/mcp/genie/{space_id}"

mcp_client = DatabricksMCPClient(
    server_url=genie_url,
    workspace_client=workspace_client,
)

tools = mcp_client.list_tools()
result = mcp_client.call_tool(tools[0].name, {"query": "What was total spend last month?"})
print(result.content[0].text)
```

### Connect with OpenAI Agents SDK

```python
from agents.mcp import MCPServerSse

genie_mcp = MCPServerSse(
    url=f"https://{host}/api/2.0/mcp/genie/{space_id}",
    headers={"Authorization": f"Bearer {workspace_client.config.token}"},
)
```

### Polling

Genie queries can take time. When using the standard MCP SDK, poll for results
rather than waiting synchronously. `DatabricksMCPClient.call_tool()` handles
polling internally.

### Permissions

Grant the calling principal access to the Genie Space **and** all underlying
data (tables, warehouses, UC functions) the space uses. See
[`resource-grants.md`](resource-grants.md).

---

## Databricks SQL MCP

Run AI-generated SQL to author data pipelines or answer ad-hoc queries.
Read **and** write operations are supported.

### Connect with `DatabricksMCPClient`

```python
sql_url = f"{host}/api/2.0/mcp/sql"

mcp_client = DatabricksMCPClient(
    server_url=sql_url,
    workspace_client=workspace_client,
)

tools = mcp_client.list_tools()
print(f"SQL tools: {[t.name for t in tools]}")

result = mcp_client.call_tool(
    "execute_sql",
    {"query": "SELECT count(*) FROM prod.sales.transactions"}
)
print(result.content[0].text)
```

### Connect with OpenAI Agents SDK

```python
from agents.mcp import MCPServerSse

sql_mcp = MCPServerSse(
    url=f"https://{host}/api/2.0/mcp/sql",
    headers={"Authorization": f"Bearer {workspace_client.config.token}"},
)
```

### SQL MCP `_meta` Parameters

Pin a specific SQL warehouse for execution:

```python
from mcp.types import CallToolRequest, CallToolResult

request = CallToolRequest(
    method="tools/call",
    params={
        "name": "execute_sql",
        "arguments": {
            "query": "SELECT * FROM prod.sales.transactions LIMIT 10"
        },
        "_meta": {
            "warehouse_id": "a1b2c3d4e5f67890"
        }
    }
)

response = await session.send_request(request, CallToolResult)
```

If `warehouse_id` is not specified, the system selects a warehouse
automatically based on available resources and permissions.

### Permissions

The SQL MCP server executes queries as the authenticated identity. Grant the
agent's service principal `CAN_USE` on the SQL warehouse and appropriate UC
grants on any tables the generated SQL touches.

---

## UC Functions MCP

Invoke registered Unity Catalog SQL or Python functions as agent tools.

### Connect with `DatabricksMCPClient`

```python
func_url = f"{host}/api/2.0/mcp/functions/prod/analytics/enrich_customer"

mcp_client = DatabricksMCPClient(
    server_url=func_url,
    workspace_client=workspace_client,
)

tools = mcp_client.list_tools()
result = mcp_client.call_tool(
    "prod__analytics__enrich_customer",
    {"customer_name": "ACME Corp"}
)
print(result.content[0].text)
```

### Connect with OpenAI Agents SDK

```python
from agents.mcp import MCPServerSse

uc_functions_mcp = MCPServerSse(
    url=f"https://{host}/api/2.0/mcp/functions/prod/analytics/enrich_customer",
    headers={"Authorization": f"Bearer {workspace_client.config.token}"},
)
```

### Built-in AI Functions

Databricks provides built-in functions under `system.ai`, including a
Python code interpreter:

```python
system_ai_url = f"{host}/api/2.0/mcp/functions/system/ai"

mcp_client = DatabricksMCPClient(
    server_url=system_ai_url,
    workspace_client=workspace_client,
)

result = mcp_client.call_tool(
    "system__ai__python_exec",
    {"code": "import math; print(math.factorial(20))"}
)
```

### Permissions

The service principal needs `EXECUTE` on the function plus `USE CATALOG` and
`USE SCHEMA` on the parent catalog and schema. See
[`resource-grants.md`](resource-grants.md).

---

## Combined Agent with Multiple MCP Servers

Wire multiple managed servers into a single agent:

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

ws = WorkspaceClient()
host = ws.config.host

MANAGED_MCP_SERVER_URLS = [
    f"{host}/api/2.0/mcp/ai-search/prod/docs/knowledge_index",
    f"{host}/api/2.0/mcp/genie/{billing_space_id}",
    f"{host}/api/2.0/mcp/functions/prod/analytics/enrich_customer",
    f"{host}/api/2.0/mcp/sql",
]

all_tool_infos = []
for url in MANAGED_MCP_SERVER_URLS:
    client = DatabricksMCPClient(server_url=url, workspace_client=ws)
    all_tool_infos.extend(client.list_tools())

print(f"Total tools available: {len(all_tool_infos)}")
```

For the OpenAI Agents SDK, pass MCP servers directly:

```python
from agents import Agent
from agents.mcp import MCPServerSse

agent = Agent(
    name="analyst",
    instructions="Use tools to answer questions. Cite sources.",
    model="databricks-claude-sonnet-4-6",
    mcp_servers=[vector_search_mcp, genie_mcp, sql_mcp, uc_functions_mcp],
)
```

---

## Environment-Aware Authentication

Handle auth consistently across local dev, Databricks Apps, and Model Serving:

```python
import os
from databricks.sdk import WorkspaceClient

def get_workspace_client():
    if os.environ.get("DATABRICKS_APP_NAME"):
        return WorkspaceClient()
    elif os.environ.get("IS_IN_DB_MODEL_SERVING_ENV"):
        return WorkspaceClient()
    else:
        return WorkspaceClient()

def get_mcp_auth_headers():
    w = get_workspace_client()
    return {"Authorization": f"Bearer {w.config.token}"}
```

For OBO (on-behalf-of user) authentication in Databricks Apps, see
[A4: Authentication](../../../tracks/A-custom-agent-apps/04-authentication/SKILL.md).

---

## Troubleshooting

| Symptom | Likely Fix |
|---------|------------|
| Connection refused / 404 | Confirm workspace host, path segments (catalog/schema/index or space_id), and MCP feature enabled |
| 401 / 403 | Token scope mismatch — check OAuth scopes and UC grants per `resource-grants.md` |
| Tools not listed | Server URL incorrect — verify with a simple HTTP client before wiring the agent |
| Genie returns timeout | Genie queries can be slow — increase timeout or implement polling |
| SQL MCP wrong warehouse | Use `_meta.warehouse_id` to pin a specific warehouse |

---

## References

- [Managed MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp)
- [Meta parameters for managed MCP](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp-meta-param)
- [Vector Search Python SDK](https://docs.databricks.com/aws/en/vector-search/)
- [Genie in a multi-agent system](https://docs.databricks.com/aws/en/generative-ai/agent-framework/multi-agent-genie)
- [UC Functions as tools](https://docs.databricks.com/aws/en/generative-ai/agent-framework/create-custom-tool)
- [databricks-mcp on PyPI](https://pypi.org/project/databricks-mcp/)
- [OpenAI Agents SDK — MCP](https://openai.github.io/openai-agents-python/mcp/)

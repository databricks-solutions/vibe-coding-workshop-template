# External MCP Connections — Deep Reference

Connect agents to third-party MCP servers through Databricks-managed proxies.
The proxy handles authentication and token management so external servers appear
as standard MCP endpoints.

Primary source: [Use external MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/external-mcp)

---

## Requirements

- A workspace with the **Managed MCP Servers** preview enabled (see Manage
  Databricks previews).
- `CREATE CONNECTION` privilege on the Unity Catalog metastore.
- The external MCP server must use the **Streamable HTTP** transport mechanism.

---

## Four Installation Methods

### 1. Managed OAuth (Recommended for Supported Providers)

Databricks manages the OAuth flow — no credential registration or rotation
needed.

| Provider | Configuration Notes | Supported Scopes |
|---|---|---|
| **Glean MCP** | Requires Host. Base path configurable (defaults to `/mcp/default`) | `mcp` |
| **GitHub MCP** | None | `repo read:project read:org` |
| **Atlassian MCP** | None | `read:jira-work read:jira-user read:confluence-content.all offline_access` |

**Setup:**

1. Go to **Catalog** > **Connections** > **Create connection**.
2. Select **HTTP** as the connection type.
3. Select **OAuth User to Machine Per User** as the auth type.
4. From the **OAuth Provider** dropdown, select your provider.
5. Enter scopes as a space-delimited string (or leave empty for defaults).
6. Click **Create connection**.

Each user is prompted to authorize with the provider on first use.

**Redirect URIs** (allowlist if needed):

| Cloud | Redirect URI |
|---|---|
| AWS | `https://oregon.cloud.databricks.com/api/2.0/http/oauth/redirect` |
| Azure | `https://westus.azuredatabricks.net/api/2.0/http/oauth/redirect` |
| GCP | `https://us-central1.gcp.databricks.com/api/2.0/http/oauth/redirect` |

### 2. Databricks Marketplace

Install curated MCP servers directly:

1. Go to **Marketplace** > **Agents** > **MCP Servers** tab.
2. Find the server and click **Install**.
3. Configure connection name, host (pre-populated), and credentials.
4. Click **Install**.

### 3. Custom HTTP Connection

For any MCP server not available via Managed OAuth or Marketplace:

1. Create an HTTP connection (see
   [HTTP connection docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-connection.html)).
2. Check the **Is mcp connection** checkbox.
3. Verify the connection URL points to a valid MCP server endpoint.

**SQL example:**

```sql
CREATE CONNECTION my_external_mcp
TYPE HTTP
URL 'https://api.external-service.com/mcp'
OPTIONS (
    is_mcp_connection = 'true',
    bearer_token = '{{secrets/scope/key}}'
);
```

### 4. Dynamic Client Registration (Experimental)

Automatically register MCP servers that support OAuth 2.0 DCR (RFC 7591):

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import register_mcp_server_via_dcr

workspace_client = WorkspaceClient()

connection_url = register_mcp_server_via_dcr(
    connection_name="my_mcp_server",
    mcp_url="https://mcp.example.com/api",
    workspace_client=workspace_client,
)
print(f"Connection created: {connection_url}")
```

DCR handles OAuth discovery, client registration, and UC connection creation
automatically.

---

## Proxy URL Patterns

After installation, external servers are accessible at:

```
https://{workspace_host}/api/2.0/mcp/external/{connection_name}
```

An alternative UC connections proxy is also available (supports arbitrary
sub-paths and all HTTP methods):

```
https://{workspace_host}/api/2.0/unity-catalog/connections/{connection_name}/proxy[/sub-path]
```

---

## Using External MCP Servers in Agent Code

### With `DatabricksMCPClient` (Recommended)

External servers work identically to managed servers through the proxy:

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

workspace_client = WorkspaceClient()
host = workspace_client.config.host

mcp_client = DatabricksMCPClient(
    server_url=f"{host}/api/2.0/mcp/external/github_connection",
    workspace_client=workspace_client,
)

tools = mcp_client.list_tools()
print(f"Available tools: {[tool.name for tool in tools]}")

response = mcp_client.call_tool(
    "list_commits",
    {"owner": "mlflow", "repo": "mlflow", "sha": "master"}
)
print(response.content[0].text)
```

### Combined Managed + External Servers

Add external proxy URLs alongside managed server URLs — the same API works
for both:

```python
MANAGED_MCP_SERVER_URLS = [
    f"{host}/api/2.0/mcp/functions/system/ai",
    f"{host}/api/2.0/mcp/vector-search/prod/docs/knowledge_index",
    f"{host}/api/2.0/mcp/external/github_connection",
    f"{host}/api/2.0/mcp/external/glean_connection",
]
```

### With the Standard MCP SDK (Async)

```python
import asyncio
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksOAuthClientProvider
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

async def query_external_mcp():
    ws = WorkspaceClient()
    url = f"{ws.config.host}/api/2.0/mcp/external/github_connection"

    async with streamablehttp_client(
        url=url,
        auth=DatabricksOAuthClientProvider(ws),
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(
                name="list_commits",
                arguments={"owner": "mlflow", "repo": "mlflow", "sha": "master"}
            )
            return result

asyncio.run(query_external_mcp())
```

### With the OpenAI Agents SDK

```python
from agents import Agent
from agents.mcp import MCPServerSse

external_mcp = MCPServerSse(
    url=f"https://{host}/api/2.0/mcp/external/github_connection",
    headers={"Authorization": f"Bearer {workspace_client.config.token}"},
)

agent = Agent(
    name="code-assistant",
    instructions="Use GitHub tools to help with code questions.",
    model="databricks-claude-sonnet-4-6",
    mcp_servers=[external_mcp],
)
```

---

## Sharing and Permissions

Grant `USE CONNECTION` privileges to principals that need the MCP server:

1. Go to **Catalog** > **Connections** > your connection > **Permissions**.
2. Grant identities appropriate access.

For agents deployed as Databricks Apps, the app's service principal needs
`USE CONNECTION`. See [`resource-grants.md`](resource-grants.md).

---

## Authentication Methods

| Auth Type | Mechanism | Use When |
|---|---|---|
| **Bearer token** | Static token in connection options | Simple API key auth |
| **OAuth M2M** (Machine-to-Machine) | Client credentials flow, shared | Service accounts |
| **OAuth U2M Shared** | User-to-Machine, single credential set | Shared user context |
| **OAuth U2M Per User** | Per-user OAuth flow | User-specific resources (repos, messages) |

**Security benefits:**
- Databricks handles all OAuth flows and token refresh automatically.
- Tokens are never exposed to end users.
- Centralized authentication via Unity Catalog connections.

---

## Testing in AI Playground

Test external MCP servers without writing code:

1. Go to **AI Playground** > choose a model with **Tools enabled**.
2. Click **Tools** > **+ Add tool** > **MCP Servers** > **External MCP servers**.
3. Select your UC connection (e.g. `github_connection`).
4. Chat with the LLM — AI Playground auto-discovers tools from your MCP server.

Use this to prototype and validate integrations before wiring into agent code.

---

## Using with Supervisor API (Track B)

External MCP connections are usable as `external_mcp_server` tools in the
Supervisor API:

```python
tools = [
    {
        "type": "external_mcp_server",
        "external_mcp_server": {
            "description": "Search GitHub repositories and commits",
            "connection_name": "github_connection",
        },
    },
]

response = client.responses.create(
    model=config.get("model"),
    input=[{"type": "message", "role": "user", "content": "List recent commits"}],
    tools=tools,
    stream=True,
)
```

---

## Deploying Agents with External MCP

When logging an agent for Model Serving, declare external MCP connections
as resources:

```python
from mlflow.models.resources import DatabricksApp

mlflow.pyfunc.log_model(
    python_model="agent.py",
    resources=[
        DatabricksApp(app_name="my-custom-mcp-app"),
    ],
)
```

For managed MCP servers, use `get_databricks_resources()` to auto-enumerate.
See [`resource-grants.md`](resource-grants.md) for the full pattern.

---

## Limitations

- Only external MCP servers using the **Streamable HTTP** transport are supported.
- WebSocket-based MCP servers are not supported through the Databricks proxy.

---

## References

- [Use external MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/external-mcp)
- [Connect clients to MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/connect-external-services)
- [HTTP connections](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-connection.html)
- [Get access to external MCP servers (Marketplace)](https://docs.databricks.com/aws/en/marketplace/)
- [databricks-mcp on PyPI](https://pypi.org/project/databricks-mcp/)

---

## See Also

For **end-to-end working examples** with popular external services — including
full connection setup, permissions, agent wiring code, and deployment grants —
see [`external-mcp-examples.md`](external-mcp-examples.md). Covers Slack
(bearer token + UC proxy), JIRA (Managed OAuth + Atlassian MCP), and Brave
Search (`@function_tool` + UC proxy).

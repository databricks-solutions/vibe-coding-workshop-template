# External MCP Connection Examples — End-to-End

Concrete, working examples for connecting agents to popular external services.
Each example goes from zero to a running agent with full connection setup,
permissions, wiring code, and deployment grants.

For the conceptual overview of installation methods, proxy URLs, and auth
types, see [external-mcp-connections.md](external-mcp-connections.md).

---

## Example: Slack

Connect your agent to Slack so it can read channels, search messages, and
post updates.

**Connection method:** Custom HTTP connection with bearer token.

**Prerequisites:**

- A Slack workspace where you can install apps.
- A Slack Bot Token (`xoxb-...`) from a Slack App with the scopes your agent
  needs (e.g. `chat:write`, `channels:read`, `channels:history`, `search:read`).
- The bot token stored as a Databricks secret.

### Step 1: Store the Bot Token

```bash
databricks secrets create-scope --scope slack-secrets
databricks secrets put-secret --scope slack-secrets --key bot-token --string-value "xoxb-..."
```

### Step 2: Create the UC HTTP Connection

```sql
CREATE CONNECTION slack_connection TYPE HTTP
OPTIONS (
  host 'https://slack.com',
  base_path '/api',
  bearer_token secret('slack-secrets', 'bot-token'),
  is_mcp_connection = 'false'
);
```

> **Note:** Slack does not publish an MCP server through Databricks, so we use
> the UC connections proxy for direct REST API calls. Set `is_mcp_connection`
> to `false`.

### Step 3: Grant Permissions

```sql
GRANT USE CONNECTION ON CONNECTION slack_connection TO `<app-sp>`;
```

### Step 4: Wire into Agent — UC Connections Proxy Approach

Use the Slack Web API directly through the UC connections proxy:

```python
import json
from agents import Agent, function_tool
from databricks.sdk import WorkspaceClient


ws = WorkspaceClient()
host = ws.config.host
PROXY_BASE = f"{host}/api/2.0/unity-catalog/connections/slack_connection/proxy"


@function_tool
def slack_post_message(channel: str, text: str) -> str:
    """Post a message to a Slack channel.

    Args:
        channel: Slack channel ID (e.g. "C01ABCDEF") or name (e.g. "#general").
        text: Message text to post. Supports Slack markdown formatting.
    """
    import requests

    resp = requests.post(
        f"{PROXY_BASE}/chat.postMessage",
        headers={
            "Authorization": f"Bearer {ws.config.token}",
            "Content-Type": "application/json",
        },
        json={"channel": channel, "text": text},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("ok"):
        return f"Message posted to {channel}"
    return f"Slack error: {data.get('error', 'unknown')}"


@function_tool
def slack_search_messages(query: str, count: int = 5) -> str:
    """Search Slack messages across all channels the bot has access to.

    Args:
        query: Search query string (supports Slack search syntax).
        count: Number of results to return (max 20).
    """
    import requests

    resp = requests.get(
        f"{PROXY_BASE}/search.messages",
        headers={"Authorization": f"Bearer {ws.config.token}"},
        params={"query": query, "count": min(count, 20)},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        return f"Slack search error: {data.get('error', 'unknown')}"

    matches = data.get("messages", {}).get("matches", [])
    if not matches:
        return f"No Slack messages found for: {query}"

    results = []
    for m in matches[:count]:
        channel_name = m.get("channel", {}).get("name", "unknown")
        user = m.get("username", "unknown")
        text = m.get("text", "")[:200]
        results.append(f"**#{channel_name}** (@{user}): {text}")

    return "\n\n".join(results)


agent = Agent(
    name="slack-agent",
    instructions="""You are a team communication assistant with Slack access.
    Use slack_search_messages to find relevant discussions.
    Use slack_post_message to send updates.
    Always confirm before posting messages.""",
    model="databricks-claude-sonnet-4-6",
    tools=[slack_post_message, slack_search_messages],
)
```

### Step 5: Test

```python
import asyncio
from agents import Runner

async def test():
    result = await Runner.run(agent, "Search Slack for messages about the Q3 release")
    print(result.final_output)

asyncio.run(test())
```

### Resource Grants for Deployment

```yaml
# databricks.yml
resources:
  apps:
    my_agent_app:
      resources:
        - name: 'slack-connection'
          uc_securable:
            securable_full_name: 'slack_connection'
            securable_type: 'CONNECTION'
            permission: 'USE_CONNECTION'
```

See also: [Connect an AI agent to Slack](https://docs.databricks.com/aws/en/generative-ai/agent-framework/slack-agent).

---

## Example: JIRA (Atlassian Managed OAuth)

Connect your agent to JIRA for searching issues, reading details, and creating
tickets. Uses Databricks Managed OAuth — no credential management needed.

**Connection method:** Managed OAuth (Atlassian is a supported provider).

**Prerequisites:**

- An Atlassian Cloud account (JIRA, Confluence).
- Workspace with **Managed MCP Servers** preview enabled.

### Step 1: Create Connection via UI

1. Go to **Catalog** > **Connections** > **Create connection**.
2. Set **Connection type** to **HTTP**.
3. Set **Auth type** to **OAuth User to Machine Per User**.
4. From the **OAuth Provider** dropdown, select **Atlassian MCP**.
5. Enter scopes: `read:jira-work read:jira-user read:confluence-content.all offline_access`
6. Set a **Connection name** (e.g. `atlassian_jira`).
7. Click **Create connection**.

Each user will be prompted to authorize with Atlassian on first use.

### Step 2: Grant Permissions

```sql
GRANT USE CONNECTION ON CONNECTION atlassian_jira TO `<app-sp>`;
```

### Step 3: Test in AI Playground

Before writing code, verify the connection works:

1. Go to **AI Playground** > choose a model with **Tools enabled**.
2. Click **Tools** > **+ Add tool** > **MCP Servers** > **External MCP servers**.
3. Select `atlassian_jira`.
4. Ask: "Search for open JIRA issues about performance."
5. Verify tools are discovered and results come back.

### Step 4: Wire into Agent

```python
from agents import Agent, Runner
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

ws = WorkspaceClient()
host = ws.config.host

jira_mcp_url = f"{host}/api/2.0/mcp/external/atlassian_jira"

jira_client = DatabricksMCPClient(
    server_url=jira_mcp_url,
    workspace_client=ws,
)

tools = jira_client.list_tools()
print(f"JIRA tools discovered: {[t.name for t in tools]}")
# Typical tools: search_issues, get_issue, create_issue, add_comment, etc.
```

Wire into the OpenAI Agents SDK:

```python
from agents.mcp import MCPServerSse

jira_mcp = MCPServerSse(
    url=f"https://{host}/api/2.0/mcp/external/atlassian_jira",
    headers={"Authorization": f"Bearer {ws.config.token}"},
)

agent = Agent(
    name="project-manager",
    instructions="""You are a project management assistant with JIRA access.
    Search for issues, read details, and help track work items.
    When creating issues, always confirm the project key and summary with the user first.""",
    model="databricks-claude-sonnet-4-6",
    mcp_servers=[jira_mcp],
)
```

### Step 5: Test

```python
import asyncio
from agents import Runner

async def test():
    result = await Runner.run(
        agent,
        "Find all open bugs in the DATA project assigned to me"
    )
    print(result.final_output)

asyncio.run(test())
```

### Resource Grants for Deployment

```yaml
# databricks.yml
resources:
  apps:
    my_agent_app:
      resources:
        - name: 'jira-connection'
          uc_securable:
            securable_full_name: 'atlassian_jira'
            securable_type: 'CONNECTION'
            permission: 'USE_CONNECTION'
```

---

## Example: Web Search API (Brave Search)

Add web search capability to your agent. Since Brave Search doesn't have a
Databricks-hosted MCP server, we show two approaches.

**Prerequisites:**

- A Brave Search API key from [brave.com/search/api](https://brave.com/search/api/).

### Approach A: `@function_tool` with Direct API Call

The simplest path — wrap the Brave Search REST API in a function tool. API
key stored in Databricks secrets.

```bash
databricks secrets put-secret --scope agent-secrets --key brave-api-key --string-value "BSA..."
```

```yaml
# app.yaml
env:
  - name: BRAVE_API_KEY
    valueFrom: "{{secrets/agent-secrets/brave-api-key}}"
```

```python
import os
import requests
from agents import function_tool


@function_tool
def web_search(query: str, count: int = 5) -> str:
    """Search the web for current information using Brave Search.

    Use this for recent events, live data, or information not in our
    internal knowledge base.

    Args:
        query: Natural language search query.
        count: Number of results to return (1-20).
    """
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return "Web search unavailable: BRAVE_API_KEY not configured."

    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "X-Subscription-Token": api_key,
                "Accept": "application/json",
            },
            params={"q": query, "count": min(count, 20)},
            timeout=10,
        )
        resp.raise_for_status()

        results = resp.json().get("web", {}).get("results", [])
        if not results:
            return f"No results found for: {query}"

        return "\n\n---\n\n".join(
            f"**{r['title']}**\n{r['url']}\n{r.get('description', '')[:300]}"
            for r in results
        )
    except Exception as e:
        return f"Search failed: {str(e)}"
```

**Pros:** Simple, no UC connection needed, works anywhere.
**Cons:** API key managed via secrets (not UC-governed), no automatic tool
discovery.

### Approach B: UC HTTP Connection + Connections Proxy

Route the Brave API through the Databricks UC connections proxy for
centralized credential management and governance.

**Step 1: Create the connection**

```sql
CREATE CONNECTION brave_search TYPE HTTP
OPTIONS (
  host 'https://api.search.brave.com',
  base_path '/res/v1',
  bearer_token secret('agent-secrets', 'brave-api-key')
);
```

> **Note:** Brave uses `X-Subscription-Token` header, not `Authorization: Bearer`.
> The UC connections proxy injects the token as a `Bearer` header. You may
> need to use a custom HTTP connection with explicit header configuration if
> the API requires a non-standard auth header. Test the connection before
> building the agent.

**Step 2: Grant permissions**

```sql
GRANT USE CONNECTION ON CONNECTION brave_search TO `<app-sp>`;
```

**Step 3: Wire into agent**

```python
import json
from agents import function_tool
from databricks.sdk import WorkspaceClient

ws = WorkspaceClient()
host = ws.config.host
PROXY_BASE = f"{host}/api/2.0/unity-catalog/connections/brave_search/proxy"


@function_tool
def web_search_proxy(query: str, count: int = 5) -> str:
    """Search the web via Brave Search (UC proxy).

    Args:
        query: Search query string.
        count: Number of results (1-20).
    """
    import requests

    resp = requests.get(
        f"{PROXY_BASE}/web/search",
        headers={"Authorization": f"Bearer {ws.config.token}"},
        params={"q": query, "count": min(count, 20)},
        timeout=10,
    )
    resp.raise_for_status()

    results = resp.json().get("web", {}).get("results", [])
    if not results:
        return f"No results found for: {query}"

    return "\n\n---\n\n".join(
        f"**{r['title']}**\n{r['url']}\n{r.get('description', '')[:300]}"
        for r in results
    )
```

**Pros:** Centralized credentials in UC, governed access, auditable.
**Cons:** Slightly more setup, proxy adds a hop.

### Comparing the Two Approaches

| Aspect | Approach A (Direct) | Approach B (UC Proxy) |
|---|---|---|
| Setup effort | Low — secret + env var | Medium — UC connection + grants |
| Credential governance | Databricks secrets | Unity Catalog connections |
| Access auditing | Limited | Full UC audit log |
| Latency | Direct to API | Extra proxy hop |
| Credential rotation | Manual secret update | Update UC connection |
| Best for | Dev/prototyping | Production agents |

### Resource Grants for Deployment

**Approach A** — only needs the secret scope accessible to the app.

**Approach B:**

```yaml
resources:
  apps:
    my_agent_app:
      resources:
        - name: 'brave-search'
          uc_securable:
            securable_full_name: 'brave_search'
            securable_type: 'CONNECTION'
            permission: 'USE_CONNECTION'
```

---

## Combining External Services in One Agent

```python
from agents import Agent
from agents.mcp import MCPServerSse

agent = Agent(
    name="connected-agent",
    instructions="""You have access to:
    - JIRA for project tracking (search issues, create tickets)
    - Slack for team communication (search messages, post updates)
    - Web search for external information

    Use the right tool for each task. Confirm before creating JIRA issues
    or posting Slack messages.""",
    model="databricks-claude-sonnet-4-6",
    tools=[slack_post_message, slack_search_messages, web_search],
    mcp_servers=[jira_mcp],
)
```

---

## References

- [Connect an AI agent to Slack](https://docs.databricks.com/aws/en/generative-ai/agent-framework/slack-agent)
- [Connect agents to external services](https://docs.databricks.com/aws/en/generative-ai/agent-framework/external-connection-tools)
- [Use external MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/external-mcp)
- [UC HTTP connections](https://docs.databricks.com/aws/en/query-federation/http)
- [Brave Search API](https://brave.com/search/api/)
- [Atlassian MCP (Managed OAuth)](https://docs.databricks.com/aws/en/generative-ai/mcp/external-mcp#install)

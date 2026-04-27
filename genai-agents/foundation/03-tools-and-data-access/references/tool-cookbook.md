# Tool Cookbook — Pre-Built Tool Recipes

Reusable recipes for common agent capabilities. Each recipe separates
**core logic** (track-independent plain Python) from **wiring** (how you
attach it to your agent). Copy the core function, then apply the wiring
pattern for your track.

> **Track compatibility:**
>
> - **Track A** (Custom Agent Apps): Use `@function_tool` decorator directly.
>   Wire into `Agent(tools=[...])`.
> - **Track C** (Model Serving): Same `@function_tool` code, but define and
>   wire inside `ChatModel.predict()`. See
>   [C1: Agent Packaging, Step C1f](../../tracks/C-model-serving/01-agent-packaging/SKILL.md).
> - **Track B** (Supervisor API): Cannot use `@function_tool`. Publish the
>   logic as a **UC Function** (`CREATE FUNCTION`) and add it as a
>   `unity_catalog_function` hosted tool. See
>   [B2: Hosted Tools](../../tracks/B-supervisor-api/02-hosted-tools/SKILL.md).
>   Alternatively, wrap the logic in a custom external MCP server.
>
> All recipes below use `@function_tool` (Track A/C). A UC Function variant
> is shown for the SQL execution recipe as a Track B reference pattern.

---

## Recipe: Web Search (Tavily)

**When to use:** Your agent needs real-time information from the web — current
events, live documentation, competitor data — that isn't in your indexed
Vector Search corpus.

**Dependencies:**

```bash
pip install tavily-python
```

Store your API key as a Databricks secret:

```bash
databricks secrets put-secret --scope agent-secrets --key tavily-api-key --string-value "tvly-..."
```

Pass it via environment variable in `app.yaml`:

```yaml
env:
  - name: TAVILY_API_KEY
    valueFrom: "{{secrets/agent-secrets/tavily-api-key}}"
```

**Core logic** (track-independent):

```python
import os


def _web_search(query: str, max_results: int = 5) -> str:
    """Search the web via Tavily. Returns formatted results with URLs."""
    from tavily import TavilyClient

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Web search unavailable: TAVILY_API_KEY not configured."

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=min(max_results, 10),
            search_depth="basic",
        )

        if not response.get("results"):
            return f"No web results found for: {query}"

        formatted = []
        for r in response["results"]:
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")[:300]
            formatted.append(f"**{title}**\n{url}\n{content}")

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        return f"Web search failed: {str(e)}"
```

**Track A/C wiring** (`@function_tool`):

```python
from agents import function_tool


@function_tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information.

    Use this tool when the user asks about recent events, live data, or
    information that may not be in our internal knowledge base.

    Args:
        query: Natural language search query.
        max_results: Maximum number of results to return (1-10).
    """
    return _web_search(query, max_results)
```

**Alternative: Brave Search (direct HTTP)**

```python
import os
import requests


def _brave_search(query: str, count: int = 5) -> str:
    """Search the web via Brave Search REST API."""
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return "Brave Search unavailable: BRAVE_API_KEY not configured."

    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
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


@function_tool
def brave_search(query: str, count: int = 5) -> str:
    """Search the web using Brave Search API.

    Args:
        query: Search query string.
        count: Number of results (1-20).
    """
    return _brave_search(query, count)
```

**Resource grants:** No Databricks resources needed — these are external API
calls using secrets. Add the secret scope to your app's accessible secrets.

**Alternatives:**

| Need | Better Tool |
|------|-------------|
| Search internal docs | Vector Search MCP — see [managed-mcp-servers.md](managed-mcp-servers.md) |
| Query structured internal data | Genie MCP or SQL MCP |
| Search with Databricks-managed auth | External MCP server (if your search provider has one) |

---

## Recipe: SQL Execution with Formatted Results

**When to use:** Your agent needs to run SQL queries and return cleanly
formatted results — simpler and more deterministic than the SQL MCP server
when you want full control over formatting, safety, and row limits.

**Dependencies:** `databricks-sdk` (already installed if using the agent template).

**Core logic** (track-independent):

```python
import os
import re


def _get_warehouse_id() -> str:
    wid = os.environ.get("WAREHOUSE_ID", os.environ.get("SQL_WAREHOUSE_ID"))
    if not wid:
        raise ValueError("WAREHOUSE_ID env var not set")
    return wid


def _execute_sql(query: str, max_rows: int = 50, read_only: bool = True) -> str:
    """Execute SQL and return markdown-formatted results."""
    if read_only:
        normalized = re.sub(r"\s+", " ", query.strip()).upper()
        if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
            return "Error: Only SELECT/WITH queries are allowed in read-only mode."

    max_rows = min(max_rows, 1000)

    from databricks.sdk import WorkspaceClient

    try:
        w = WorkspaceClient()
        result = w.statement_execution.execute_statement(
            warehouse_id=_get_warehouse_id(),
            statement=query,
            wait_timeout="30s",
            row_limit=max_rows,
        )

        if result.status and result.status.state.value == "FAILED":
            error_msg = result.status.error.message if result.status.error else "Unknown"
            return f"Query failed: {error_msg}"

        if not result.manifest or not result.result:
            return "Query returned no results."

        columns = [col.name for col in result.manifest.schema.columns]
        rows = result.result.data_array or []

        if not rows:
            return f"Query returned 0 rows.\nColumns: {', '.join(columns)}"

        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"
        body = "\n".join(
            "| " + " | ".join(str(cell) if cell is not None else "NULL" for cell in row) + " |"
            for row in rows
        )

        footer = f"\n\n*{len(rows)} row(s) returned*"
        if len(rows) == max_rows:
            footer += f" *(limited to {max_rows})*"

        return f"{header}\n{separator}\n{body}{footer}"

    except Exception as e:
        return f"SQL execution error: {str(e)}"
```

**Track A/C wiring** (`@function_tool`):

```python
from agents import function_tool


@function_tool
def execute_sql(
    query: str,
    max_rows: int = 50,
    read_only: bool = True,
) -> str:
    """Execute a SQL query against the Databricks SQL warehouse and return
    formatted results.

    Args:
        query: SQL query to execute. Must be a SELECT statement if read_only
            is True.
        max_rows: Maximum number of rows to return (default 50, max 1000).
        read_only: If True, reject non-SELECT statements for safety.
    """
    return _execute_sql(query, max_rows, read_only)
```

**Resource grants:**

```yaml
resources:
  - name: sql-warehouse
    sql_warehouse:
      permission: CAN_USE

env:
  - name: WAREHOUSE_ID
    valueFrom: sql-warehouse
```

Plus UC grants on any tables the queries touch.

**Alternatives:**

| Need | Better Tool |
|------|-------------|
| LLM-generated SQL (agent writes the query) | SQL MCP server — see [managed-mcp-servers.md](managed-mcp-servers.md) |
| Natural language over structured data | Genie MCP |
| Complex multi-step SQL workflows | SQL MCP with `_meta.warehouse_id` |

### Track B Variant: UC Function

Publish the same SQL execution logic as a Unity Catalog function so the
Supervisor API can invoke it as a `unity_catalog_function` hosted tool.

```sql
CREATE OR REPLACE FUNCTION catalog.schema.execute_sql_formatted(
  query STRING COMMENT 'SQL SELECT query to execute. Must be a SELECT or WITH statement.',
  max_rows INT DEFAULT 50 COMMENT 'Maximum rows to return (1-1000).'
)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Execute a read-only SQL query and return markdown-formatted results.'
AS $$
  import re

  normalized = re.sub(r"\s+", " ", query.strip()).upper()
  if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
      return "Error: Only SELECT/WITH queries are allowed."

  max_rows = min(max_rows, 1000)

  from databricks.sdk import WorkspaceClient

  w = WorkspaceClient()
  result = w.statement_execution.execute_statement(
      warehouse_id=w.config.warehouse_id,
      statement=query,
      wait_timeout="30s",
      row_limit=max_rows,
  )

  if result.status and result.status.state.value == "FAILED":
      error_msg = result.status.error.message if result.status.error else "Unknown"
      return f"Query failed: {error_msg}"

  if not result.manifest or not result.result:
      return "Query returned no results."

  columns = [col.name for col in result.manifest.schema.columns]
  rows = result.result.data_array or []

  if not rows:
      return f"Query returned 0 rows. Columns: {', '.join(columns)}"

  header = "| " + " | ".join(columns) + " |"
  separator = "| " + " | ".join("---" for _ in columns) + " |"
  body = "\n".join(
      "| " + " | ".join(str(c) if c is not None else "NULL" for c in row) + " |"
      for row in rows
  )

  footer = f"\n\n*{len(rows)} row(s) returned*"
  if len(rows) == max_rows:
      footer += f" *(limited to {max_rows})*"

  return f"{header}\n{separator}\n{body}{footer}"
$$;
```

Grant the function to your agent's service principal:

```sql
GRANT EXECUTE ON FUNCTION catalog.schema.execute_sql_formatted TO `<agent-sp>`;
```

Wire it into a Supervisor API request:

```python
from databricks.sdk import WorkspaceClient
from openai import OpenAI

w = WorkspaceClient()
client = OpenAI(base_url=f"{w.config.host}/serving-endpoints", api_key=w.config.token)

response = client.responses.create(
    model="databricks-claude-sonnet-4-6",
    input="Show me the top 10 customers by revenue",
    tools=[{
        "type": "unity_catalog_function",
        "unity_catalog_function": {
            "name": "catalog.schema.execute_sql_formatted"
        }
    }],
)
```

> **Track B pattern:** Any cookbook recipe can follow this same approach —
> extract the core logic into a `CREATE FUNCTION ... LANGUAGE PYTHON` UC
> function, grant `EXECUTE`, and reference it as a `unity_catalog_function`
> tool. The Supervisor API handles the multi-turn tool-calling loop
> server-side.

---

## Recipe: File and Document Generation

**When to use:** Your agent needs to produce downloadable artifacts — CSV
exports, charts, or PDF reports — and store them where users can access them.

**Dependencies:**

```bash
pip install matplotlib  # for charts
pip install reportlab   # for PDFs (optional)
```

**Core logic: CSV generation** (track-independent):

```python
import csv
import io


def _generate_csv(headers: list[str], rows: list[list[str]], filename: str = "export.csv") -> str:
    """Generate a CSV file and save to UC Volumes."""
    from databricks.sdk import WorkspaceClient

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)

    volume_path = f"/Volumes/prod/agent_data/agent-outputs/{filename}"

    try:
        w = WorkspaceClient()
        w.files.upload(
            file_path=volume_path,
            contents=io.BytesIO(buf.getvalue().encode("utf-8")),
            overwrite=True,
        )
        return f"CSV saved to `{volume_path}` ({len(rows)} rows, {len(headers)} columns)"
    except Exception as e:
        return f"Failed to save CSV: {str(e)}"
```

**Track A/C wiring** (`@function_tool`):

```python
from agents import function_tool


@function_tool
def generate_csv(
    headers: list[str],
    rows: list[list[str]],
    filename: str = "export.csv",
) -> str:
    """Generate a CSV file from tabular data and save to UC Volumes.

    Args:
        headers: Column header names.
        rows: List of rows, each a list of string values.
        filename: Output filename (saved under /Volumes/{catalog}/{schema}/agent-outputs/).
    """
    return _generate_csv(headers, rows, filename)
```

**Core logic: Chart generation** (track-independent):

```python
import io


def _generate_chart(
    title: str,
    x_labels: list[str],
    y_values: list[float],
    chart_type: str = "bar",
    filename: str = "chart.png",
) -> str:
    """Generate a chart image and save to UC Volumes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 6))

    if chart_type == "bar":
        ax.bar(x_labels, y_values)
    elif chart_type == "line":
        ax.plot(x_labels, y_values, marker="o")
    elif chart_type == "pie":
        ax.pie(y_values, labels=x_labels, autopct="%1.1f%%")
    else:
        return f"Unsupported chart type: {chart_type}. Use bar, line, or pie."

    ax.set_title(title)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    volume_path = f"/Volumes/prod/agent_data/agent-outputs/{filename}"

    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        w.files.upload(file_path=volume_path, contents=buf, overwrite=True)
        return f"Chart saved to `{volume_path}`"
    except Exception as e:
        return f"Failed to save chart: {str(e)}"
```

**Track A/C wiring** (`@function_tool`):

```python
@function_tool
def generate_chart(
    title: str,
    x_labels: list[str],
    y_values: list[float],
    chart_type: str = "bar",
    filename: str = "chart.png",
) -> str:
    """Generate a chart image and save to UC Volumes.

    Args:
        title: Chart title.
        x_labels: Labels for the x-axis.
        y_values: Numeric values for the y-axis.
        chart_type: "bar", "line", or "pie".
        filename: Output filename.
    """
    return _generate_chart(title, x_labels, y_values, chart_type, filename)
```

**Resource grants:**

```yaml
resources:
  - name: agent-volume
    uc_securable:
      securable_full_name: 'prod.agent_data.agent-outputs'
      securable_type: 'VOLUME'
      permission: 'WRITE_VOLUME'
```

```sql
GRANT USE CATALOG ON CATALOG prod TO `<app-sp>`;
GRANT USE SCHEMA ON SCHEMA prod.agent_data TO `<app-sp>`;
GRANT WRITE VOLUME ON VOLUME prod.agent_data.`agent-outputs` TO `<app-sp>`;
```

**Alternatives:**

| Need | Better Tool |
|------|-------------|
| Dynamic Python execution (agent writes the code) | Code interpreter `system.ai.python_exec` |
| Complex data processing before export | Combine SQL tool + file generation |

---

## Recipe: HTTP API Calls with Auth

**When to use:** You need to call a REST API that doesn't have an MCP server
or Python SDK, and you want Databricks to manage the credentials via a UC
HTTP connection.

**Dependencies:** `databricks-sdk`, `requests`.

**Step 1: Create the UC HTTP connection**

```sql
CREATE CONNECTION my_api_connection TYPE HTTP
OPTIONS (
  host 'https://api.example.com',
  base_path '/v1',
  bearer_token secret('agent-secrets', 'my-api-key')
);

GRANT USE CONNECTION ON CONNECTION my_api_connection TO `<app-sp>`;
```

**Core logic** (track-independent):

```python
import json


def _call_api(path: str, method: str = "GET", body: str = "", connection_name: str = "my_api_connection") -> str:
    """Call an external REST API through the UC connections proxy."""
    import requests
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    proxy_base = f"{w.config.host}/api/2.0/unity-catalog/connections/{connection_name}/proxy"
    url = f"{proxy_base}{path}"

    headers = {
        "Authorization": f"Bearer {w.config.token}",
        "Content-Type": "application/json",
    }

    try:
        if method.upper() in ("POST", "PUT", "PATCH"):
            parsed_body = json.loads(body) if body else {}
            resp = requests.request(method.upper(), url, headers=headers, json=parsed_body, timeout=30)
        else:
            resp = requests.request(method.upper(), url, headers=headers, timeout=30)

        resp.raise_for_status()

        try:
            data = resp.json()
            return json.dumps(data, indent=2)[:5000]
        except ValueError:
            return resp.text[:5000]

    except requests.HTTPError as e:
        return f"API error {resp.status_code}: {resp.text[:500]}"
    except Exception as e:
        return f"Request failed: {str(e)}"
```

**Track A/C wiring** (`@function_tool`):

```python
from agents import function_tool


@function_tool
def call_api(
    path: str,
    method: str = "GET",
    body: str = "",
) -> str:
    """Call an external REST API through the Databricks UC connections proxy.

    The proxy handles authentication automatically using the stored credentials.

    Args:
        path: API endpoint path (e.g. "/users/123" or "/search?q=test").
        method: HTTP method — GET, POST, PUT, DELETE.
        body: JSON string for the request body (POST/PUT only).
    """
    return _call_api(path, method, body)
```

**Parameterized version** (connection name from config):

```python
from mlflow.models import ModelConfig

config = ModelConfig(development_config="config.yml")


@function_tool
def call_api(path: str, method: str = "GET", body: str = "") -> str:
    """Call an external REST API via UC connections proxy. ..."""
    return _call_api(path, method, body, connection_name=config.get("api_connection_name"))
```

**Resource grants:**

```yaml
resources:
  apps:
    my_agent_app:
      resources:
        - name: 'api-connection'
          uc_securable:
            securable_full_name: 'my_api_connection'
            securable_type: 'CONNECTION'
            permission: 'USE_CONNECTION'
```

**Alternatives:**

| Need | Better Tool |
|------|-------------|
| Service has an MCP server | External MCP — see [external-mcp-connections.md](external-mcp-connections.md) |
| Service has a Python SDK | `@function_tool` wrapping the SDK directly |
| Need automatic tool discovery | External MCP server (discovers tools from the MCP spec) |
| SQL-first approach | UC function with `http_request()` — see F3 non-MCP section |

---

## Combining Multiple Recipes

### Track A (Custom Agent Apps)

Wire cookbook tools alongside MCP servers in one agent:

```python
from agents import Agent
from agents.mcp import MCPServerSse

agent = Agent(
    name="full-stack-analyst",
    instructions="""You are a data analyst with access to:
    - SQL warehouse for querying internal data
    - Web search for external/current information
    - Chart generation for visualizations
    - API calls for third-party integrations

    Use the right tool for each task. Prefer internal data over web search.""",
    model="databricks-claude-sonnet-4-6",
    tools=[web_search, execute_sql, generate_chart, generate_csv, call_api],
    mcp_servers=[vector_search_mcp],
)
```

### Track C (Model Serving)

Same tools, but defined and wired inside `ChatModel.predict()`:

```python
import mlflow

class MyAgent(mlflow.pyfunc.ChatModel):
    def predict(self, context, messages, params=None):
        from agents import Agent, Runner, function_tool

        @function_tool
        def execute_sql(query: str, max_rows: int = 50) -> str:
            """Execute SQL and return formatted results. ..."""
            return _execute_sql(query, max_rows)

        @function_tool
        def web_search(query: str, max_results: int = 5) -> str:
            """Search the web. ..."""
            return _web_search(query, max_results)

        agent = Agent(
            name="analyst",
            model=config.get("llm_endpoint"),
            tools=[execute_sql, web_search],
        )
        result = Runner.run_sync(agent, messages[-1]["content"])
        return {"content": result.final_output}
```

See [C1: Agent Packaging, Step C1f](../../tracks/C-model-serving/01-agent-packaging/SKILL.md)
for the full `ChatModel` pattern including MCP server wiring inside `predict()`.

### Track B (Supervisor API)

Publish recipes as UC Functions and combine them in the `tools` array. The
Supervisor API handles the multi-turn tool-calling loop server-side — no
custom tool execution code needed.

```python
response = client.responses.create(
    model="databricks-claude-sonnet-4-6",
    input="Summarize Q3 revenue and search the web for competitor news",
    tools=[
        {
            "type": "unity_catalog_function",
            "unity_catalog_function": {
                "name": "catalog.schema.execute_sql_formatted"
            }
        },
        {
            "type": "genie_space",
            "genie_space": {
                "space_id": "01efg...",
                "description": "Revenue data by quarter and region"
            }
        },
    ],
)
```

See [B2: Hosted Tools](../../tracks/B-supervisor-api/02-hosted-tools/SKILL.md)
for all hosted tool types and configuration details.

---

## References

- [Build a tool for your agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/build-agent-tool)
- [OpenAI Agents SDK — Tools](https://openai.github.io/openai-agents-python/tools/)
- [UC Functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-function.html)
- [UC Volumes](https://docs.databricks.com/aws/en/connect/unity-catalog/volumes)
- [Databricks Secrets](https://docs.databricks.com/aws/en/security/secrets/)
- [UC connections proxy](https://docs.databricks.com/aws/en/query-federation/http#proxy)
- [Tavily Python SDK](https://docs.tavily.com/docs/python-sdk/tavily-search)
- [Brave Search API](https://brave.com/search/api/)

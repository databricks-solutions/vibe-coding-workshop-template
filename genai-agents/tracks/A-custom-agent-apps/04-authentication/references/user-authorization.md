# User Authorization (OBO) — Complete Reference

On-Behalf-Of (OBO) authentication lets an agent act as the **calling user** rather
than the app's service principal. Each request carries the user's downscoped token,
so Unity Catalog row filters, column masks, and per-user permissions are enforced.

Primary sources:

- [Configure authorization in a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth)
- [Add scopes to an app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth#add-scopes-to-an-app)
- [MLflow Agent Server](https://mlflow.org/docs/latest/genai/serving/agent-server/)

---

## How OBO works (Databricks Apps)

```
User browser
  │
  │  1. User opens app
  │     ── Databricks SSO authenticates user
  │
  ▼
Databricks Apps reverse proxy
  │
  │  2. Proxy downscopes user token to declared API scopes
  │     ── Token placed in x-forwarded-access-token header
  │
  ▼
Agent Server (FastAPI)
  │
  │  3. Agent Server stores token per-request
  │     ── get_user_workspace_client() returns OBO client
  │
  ▼
Agent predict() / invoke()
  │
  │  4. Agent uses user_client to call Databricks APIs
  │     ── SQL, Genie, endpoints all see the calling user
  │
  ▼
Databricks APIs (enforces user's permissions)
```

---

## Scope configuration walkthrough

### Step 1: Choose scopes

Scopes control which Databricks APIs the app can call on behalf of the user.
Only declare scopes your agent actually needs.

| Scope | Grants access to |
| --- | --- |
| `sql.warehouses` | SQL warehouse operations |
| `sql.statement-execution` | Execute SQL statements |
| `dashboards.genie` | Genie Space queries |
| `serving.serving-endpoints` | Model Serving endpoint calls |
| `vectorsearch.vector-search-endpoints` | Vector Search queries |
| `catalog.tables` | Unity Catalog table metadata |
| `catalog.connections` | Unity Catalog connections |
| `workspace.files` | Workspace file operations |

### Step 2: Add scopes via UI

1. Navigate to **Compute → Apps → your app**.
2. Click **Edit app → Permissions** tab.
3. Under **API Scopes**, add the required scopes.
4. Save and redeploy.

### Step 3: Add scopes in `databricks.yml`

```yaml
resources:
  apps:
    my_agent:
      name: my-agent
      config:
        command: ["python", "-m", "uvicorn", "main:app"]
      permissions:
        - user_name: "users"
          level: "CAN_USE"
      # Scopes for OBO
      # (declared in the app configuration section)
```

**Note:** As of current docs, scope configuration in bundles may require
the UI or CLI supplementary step. Check the latest bundle schema.

---

## Token lifecycle

### Downscoping

When a user opens the app, Databricks:

1. Validates the user's SSO session.
2. Creates a **downscoped token** limited to the declared API scopes.
3. The token inherits the user's permissions but **only** for the declared scope categories.
4. Token is attached to every HTTP request via `x-forwarded-access-token`.

### Per-request storage

The MLflow Agent Server (or your custom FastAPI middleware):

1. Extracts the token from the `x-forwarded-access-token` header.
2. Stores it in a **request-scoped context** (ContextVar or request.state).
3. `get_user_workspace_client()` reads the stored token and builds a `WorkspaceClient`.

### Token expiry

- Downscoped tokens are **short-lived** (typically minutes to low hours).
- Databricks Apps proxy **automatically refreshes** the token for active sessions.
- For **streaming responses** (SSE), stash the token at request start:

```python
import contextvars

_user_token: contextvars.ContextVar[str] = contextvars.ContextVar("user_token")

class OBOMiddleware:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            token = headers.get(b"x-forwarded-access-token", b"").decode()
            if token:
                _user_token.set(token)
        await self.app(scope, receive, send)
```

---

## Full implementation with `get_user_workspace_client()`

### Using MLflow Agent Server (recommended)

```python
from mlflow.pyfunc import ChatAgent
from mlflow.types.agent import (
    ChatAgentMessage,
    ChatAgentResponse,
    ChatContext,
)
from agent_server.utils import get_user_workspace_client


class MyAgent(ChatAgent):
    """Agent that uses OBO to query on behalf of the calling user."""

    def __init__(self):
        # Startup: initialize shared resources (NO user context here)
        self.system_prompt = "You are a helpful data assistant."

    def predict(
        self,
        messages: list[ChatAgentMessage],
        context: ChatContext | None = None,
    ) -> ChatAgentResponse:
        # ─── CRITICAL: get user client INSIDE predict, not __init__ ───
        user_client = get_user_workspace_client()

        # User identity is available
        me = user_client.current_user.me()
        print(f"Acting as: {me.user_name}")

        # Execute SQL as the user (respects row filters, column masks)
        result = user_client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement="SELECT * FROM main.sales.orders LIMIT 10",
        )

        # Query Genie as the user
        from databricks.sdk.service.dashboards import GenieMessage
        genie_response = user_client.genie.start_conversation(
            space_id=self.genie_space_id,
            content="Show top customers by revenue",
        )

        return ChatAgentResponse(
            messages=[ChatAgentMessage(
                role="assistant",
                content=f"Found {len(result.result.data_array)} rows for {me.display_name}",
            )]
        )
```

### Using custom FastAPI (without Agent Server)

```python
from fastapi import FastAPI, Request, Depends
from databricks.sdk import WorkspaceClient
from contextvars import ContextVar

app = FastAPI()
_obo_token: ContextVar[str | None] = ContextVar("obo_token", default=None)


@app.middleware("http")
async def obo_middleware(request: Request, call_next):
    token = request.headers.get("x-forwarded-access-token")
    if token:
        _obo_token.set(token)
    response = await call_next(request)
    # NOTE: Do NOT clear token here for streaming responses
    return response


def get_user_client() -> WorkspaceClient:
    """Build a WorkspaceClient using the OBO token from the current request."""
    import os
    token = _obo_token.get()
    if not token:
        raise RuntimeError("No OBO token in current request context")
    host = os.environ.get("DATABRICKS_HOST", "")
    return WorkspaceClient(host=host, token=token)


@app.post("/api/query")
def handle_query(request: Request, user_client: WorkspaceClient = Depends(get_user_client)):
    me = user_client.current_user.me()
    return {"user": me.display_name, "status": "ok"}
```

---

## Testing OBO: local vs deployed

### Local development

OBO tokens are **only generated** by the Databricks Apps proxy. Locally, there
is no proxy and no `x-forwarded-access-token` header.

**Strategy:** Use environment detection to fall back to default auth locally.

```python
import os

def get_authenticated_client():
    if os.environ.get("DATABRICKS_APP_NAME"):
        # Running inside Databricks Apps — use OBO
        from agent_server.utils import get_user_workspace_client
        return get_user_workspace_client()
    else:
        # Local dev — use your personal credentials
        from databricks.sdk import WorkspaceClient
        return WorkspaceClient()
```

### Simulating OBO locally

You can simulate the OBO header for local testing:

```bash
# Get a personal access token
export DB_TOKEN=$(databricks auth token --profile DEFAULT | jq -r .access_token)

# Call your local server with the OBO header
curl -X POST http://localhost:8000/api/query \
  -H "x-forwarded-access-token: $DB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

### Deployed testing

When testing on the deployed app:

1. Open the app URL in a browser (triggers SSO).
2. The proxy automatically injects `x-forwarded-access-token`.
3. Verify the agent sees the correct user identity:

```python
# Add a /debug/me endpoint (remove before production)
@app.get("/api/debug/me")
def debug_me(user_client: WorkspaceClient = Depends(get_user_client)):
    me = user_client.current_user.me()
    return {"user_name": me.user_name, "display_name": me.display_name}
```

---

## Combining App auth + User auth in one agent

Many production agents need **both**: shared resources via SP and per-user
resources via OBO.

```python
class HybridAuthAgent(ChatAgent):
    """
    Combines app authorization (SP) for shared resources
    with user authorization (OBO) for per-user resources.
    """

    def __init__(self):
        # SP client: available at startup, used for shared resources
        from databricks.sdk import WorkspaceClient
        self.sp_client = WorkspaceClient()  # app service principal

        # Shared resources initialized once
        self.vector_index = self.sp_client.vector_search_indexes

    def predict(
        self,
        messages: list[ChatAgentMessage],
        context: ChatContext | None = None,
    ) -> ChatAgentResponse:
        # ─── SP client: shared vector search (same for all users) ───
        search_results = self.sp_client.vector_search_indexes.query_index(
            index_name="prod.docs.embeddings",
            query_text=messages[-1].content,
            columns=["content", "url"],
            num_results=5,
        )

        # ─── OBO client: user-specific data (respects UC permissions) ───
        from agent_server.utils import get_user_workspace_client
        user_client = get_user_workspace_client()
        me = user_client.current_user.me()

        # Query user-specific tables (row filters apply)
        user_data = user_client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id,
            statement=f"""
                SELECT * FROM main.sales.orders
                WHERE region = current_user_region()
                LIMIT 50
            """,
        )

        return ChatAgentResponse(
            messages=[ChatAgentMessage(
                role="assistant",
                content=self._format_response(search_results, user_data, me),
            )]
        )

    def _format_response(self, search_results, user_data, user):
        return f"Results for {user.display_name}: ..."
```

### Permission matrix for hybrid auth

| Resource | Auth method | Client | Why |
| --- | --- | --- | --- |
| Vector Search index | App (SP) | `self.sp_client` | Shared index, same for all users |
| LLM endpoint | App (SP) | `self.sp_client` | Shared model, no per-user difference |
| UC tables with row filters | User (OBO) | `user_client` | Filters enforce per-user access |
| Genie Space | User (OBO) | `user_client` | Audit trail shows calling user |
| MLflow experiment (traces) | App (SP) | `self.sp_client` | Single experiment for all traces |

---

## Scope-based security considerations

### Privilege escalation risks

- Scopes should be **minimal**: do not add `*` or overly broad scopes.
- If the user has `MANAGE` on a resource, the OBO token inherits it.
- The agent code should **not** perform administrative operations even if the
  user's token allows them.

### Scope audit

```python
# Log which scopes are in use at each request
import logging

logger = logging.getLogger(__name__)

def predict(self, messages, context=None):
    user_client = get_user_workspace_client()
    me = user_client.current_user.me()
    logger.info(f"OBO request from {me.user_name}, scopes: {context.get('scopes', 'unknown')}")
```

---

## Common mistakes

| Mistake | Impact | Fix |
| --- | --- | --- |
| Calling `get_user_workspace_client()` in `__init__` | No user context at startup; fails or wrong identity | Call inside `predict` / `invoke` / `stream` only |
| Not clearing ContextVar after streaming | Potential token leakage between requests | Use request-scoped storage; for SSE, stash token at start |
| Declaring too many scopes | Violates least privilege | Only declare scopes the agent actually uses |
| No fallback for local development | `get_user_workspace_client()` fails locally | Use environment detection pattern |
| Testing only as workspace admin | Hides permission gaps | Test with a non-admin user |

---

## Related references

- `app-authorization.md` — Service principal (shared) authentication
- `obo-authentication.md` — Deep dive on OBO patterns including Model Serving
- `model-serving-auth-passthrough.md` — AuthPolicy and UserAuthPolicy for serving
- `resource-permissions.md` — Full permission matrix

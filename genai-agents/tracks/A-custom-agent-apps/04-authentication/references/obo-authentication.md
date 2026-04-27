# On-Behalf-Of (OBO) Authentication — Complete Reference

OBO enables agents to query data **as the calling user**, respecting per-user
Unity Catalog permissions, row filters, and column masks.

**CRITICAL:** OBO **only works in Model Serving** (for MLflow agents) or
**Databricks Apps** (for app-template agents). Attempting OBO in notebooks,
jobs, or evaluation produces invalid credentials and permission errors.

Primary sources:

- [Authentication for AI agents (Model Serving)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication-model-serving)
- [Configure authorization in a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth)

---

## Environment detection (MANDATORY)

**Always detect the execution context before attempting OBO.** This is the single
most common authentication bug in agent development.

```python
import os


def detect_environment() -> str:
    """
    Detect the current execution environment.

    Returns one of: "model_serving", "databricks_apps", "notebook", "job", "local"
    """
    # Model Serving: system SP + optional OBO
    if (
        os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true"
        or os.environ.get("DATABRICKS_SERVING_ENDPOINT") is not None
        or os.environ.get("MLFLOW_DEPLOYMENT_FLAVOR_NAME") == "databricks"
    ):
        return "model_serving"

    # Databricks Apps: app SP + optional OBO via x-forwarded-access-token
    if os.environ.get("DATABRICKS_APP_NAME"):
        return "databricks_apps"

    # Databricks notebook
    if os.environ.get("DATABRICKS_RUNTIME_VERSION"):
        return "notebook"

    # Databricks job (also has DATABRICKS_RUNTIME_VERSION, but check job-specific vars)
    if os.environ.get("DATABRICKS_JOB_ID"):
        return "job"

    # Local development or unknown
    return "local"
```

### Environment variable reference

| Variable | Set when | Value |
| --- | --- | --- |
| `IS_IN_DB_MODEL_SERVING_ENV` | Model Serving | `"true"` |
| `DATABRICKS_SERVING_ENDPOINT` | Model Serving | Endpoint name |
| `MLFLOW_DEPLOYMENT_FLAVOR_NAME` | MLflow deployment | `"databricks"` |
| `DATABRICKS_APP_NAME` | Databricks Apps | App name |
| `DATABRICKS_RUNTIME_VERSION` | Notebooks / Jobs | Runtime version string |
| `DATABRICKS_JOB_ID` | Jobs | Job ID |

### Why detection is critical

| Environment | OBO attempted | Result |
| --- | --- | --- |
| **Notebook** without detection | Yes | Permission errors (invalid credentials) |
| **Notebook** with detection | No (default auth) | Works (uses your credentials) |
| **Job** without detection | Yes | Permission errors (invalid credentials) |
| **Job** with detection | No (default auth) | Works (uses job SP credentials) |
| **Evaluation** without detection | Yes | Permission errors (invalid credentials) |
| **Evaluation** with detection | No (default auth) | Works (uses runner/SP credentials) |
| **Model Serving** with OBO | Yes | Works (end-user credentials) |
| **Databricks Apps** with OBO | Yes | Works (downscoped user token) |

---

## Choosing the right auth method by environment

```python
from databricks.sdk import WorkspaceClient


def get_authenticated_client():
    """
    Get a WorkspaceClient with the correct auth strategy for the current environment.

    Model Serving: OBO via ModelServingUserCredentials (user identity)
    Databricks Apps: OBO via get_user_workspace_client (user identity)
    Notebook/Job/Local: default credentials (your identity or SP)
    """
    env = detect_environment()

    if env == "model_serving":
        return _get_model_serving_client()
    elif env == "databricks_apps":
        return _get_apps_client()
    else:
        return WorkspaceClient()


def _get_model_serving_client() -> WorkspaceClient:
    """OBO client for Model Serving using databricks-ai-bridge."""
    try:
        from databricks_ai_bridge import ModelServingUserCredentials

        client = WorkspaceClient(
            credentials_strategy=ModelServingUserCredentials()
        )
        print("Auth: OBO (Model Serving)")
        return client
    except ImportError:
        print("Auth: default (databricks-ai-bridge not installed)")
        return WorkspaceClient()
    except Exception as e:
        print(f"Auth: default (OBO failed: {type(e).__name__}: {e})")
        return WorkspaceClient()


def _get_apps_client() -> WorkspaceClient:
    """OBO client for Databricks Apps using Agent Server helper."""
    try:
        from agent_server.utils import get_user_workspace_client

        client = get_user_workspace_client()
        print("Auth: OBO (Databricks Apps)")
        return client
    except ImportError:
        print("Auth: default (agent_server not available)")
        return WorkspaceClient()
    except Exception as e:
        print(f"Auth: default (Apps OBO failed: {type(e).__name__}: {e})")
        return WorkspaceClient()
```

---

## Complete agent class showing OBO in predict()

```python
import os
import mlflow
from mlflow.pyfunc import ChatAgent
from mlflow.types.agent import (
    ChatAgentMessage,
    ChatAgentResponse,
    ChatContext,
)
from databricks.sdk import WorkspaceClient


class OBOAgent(ChatAgent):
    """
    Production agent with full OBO support across all environments.

    - Model Serving: uses end-user credentials (OBO)
    - Databricks Apps: uses downscoped user token (OBO)
    - Notebooks/Jobs/Eval: uses default credentials (SP or user)
    """

    def __init__(self):
        self.warehouse_id = os.environ.get("WAREHOUSE_ID", "")
        self.genie_space_id = os.environ.get("GENIE_SPACE_ID", "")
        self.llm_endpoint = os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-6")

    def predict(
        self,
        messages: list[ChatAgentMessage],
        context: ChatContext | None = None,
    ) -> ChatAgentResponse:
        # ─── Get client with correct auth for current environment ───
        client = get_authenticated_client()

        # Identify the acting user (for logging/audit)
        try:
            me = client.current_user.me()
            user_name = me.user_name
        except Exception:
            user_name = "unknown"

        # Execute queries as the authenticated identity
        user_query = messages[-1].content
        try:
            genie_response = client.genie.start_conversation(
                space_id=self.genie_space_id,
                content=user_query,
            )
            answer = self._extract_genie_answer(genie_response)
        except PermissionError as e:
            answer = f"Permission denied: {e}. Contact your admin for access."
        except Exception as e:
            answer = f"Query failed: {type(e).__name__}: {e}"

        return ChatAgentResponse(
            messages=[ChatAgentMessage(role="assistant", content=answer)]
        )

    def _extract_genie_answer(self, response) -> str:
        # Extract answer from Genie response
        return str(response)


# ─── Model logging with full AuthPolicy ───
def log_agent():
    from mlflow.models.auth_policy import (
        AuthPolicy,
        SystemAuthPolicy,
        UserAuthPolicy,
    )
    from mlflow.models.resources import (
        DatabricksGenieSpace,
        DatabricksServingEndpoint,
        DatabricksSQLWarehouse,
    )

    agent = OBOAgent()

    system_resources = [
        DatabricksServingEndpoint(endpoint_name=agent.llm_endpoint),
        DatabricksSQLWarehouse(warehouse_id=agent.warehouse_id),
        DatabricksGenieSpace(genie_space_id=agent.genie_space_id),
    ]

    auth_policy = AuthPolicy(
        system_auth_policy=SystemAuthPolicy(resources=system_resources),
        user_auth_policy=UserAuthPolicy(
            api_scopes=[
                "dashboards.genie",
                "sql.warehouses",
                "sql.statement-execution",
                "serving.serving-endpoints",
            ]
        ),
    )

    mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model=agent,
        auth_policy=auth_policy,
        pip_requirements=[
            "mlflow>=3.0.0",
            "databricks-sdk>=0.30.0",
            "databricks-ai-bridge>=0.1.0",
        ],
    )
```

---

## Error handling patterns for auth failures

### Pattern 1: Graceful degradation

```python
def get_client_with_fallback():
    """Try OBO, fall back to SP, provide clear error if both fail."""
    env = detect_environment()

    if env == "model_serving":
        try:
            from databricks_ai_bridge import ModelServingUserCredentials
            return WorkspaceClient(credentials_strategy=ModelServingUserCredentials())
        except ImportError:
            print("WARN: databricks-ai-bridge not installed; falling back to system SP")
            return WorkspaceClient()
        except Exception as e:
            print(f"WARN: OBO failed ({e}); falling back to system SP")
            return WorkspaceClient()

    elif env == "databricks_apps":
        try:
            from agent_server.utils import get_user_workspace_client
            return get_user_workspace_client()
        except RuntimeError as e:
            if "no OBO token" in str(e).lower():
                print("WARN: No OBO token (unauthenticated request?); using SP")
                return WorkspaceClient()
            raise

    return WorkspaceClient()
```

### Pattern 2: Typed error responses

```python
class AuthError:
    """Structured auth error for agent responses."""

    @staticmethod
    def permission_denied(resource: str, action: str) -> str:
        return (
            f"You don't have permission to {action} on {resource}. "
            f"Please contact your workspace admin to grant access."
        )

    @staticmethod
    def obo_unavailable() -> str:
        return (
            "User authentication is not available in this environment. "
            "The agent is using shared (service principal) credentials."
        )

    @staticmethod
    def token_expired() -> str:
        return (
            "Your session has expired. Please refresh the page to "
            "re-authenticate."
        )
```

### Pattern 3: Retry with exponential backoff for transient auth errors

```python
import time


def execute_with_auth_retry(fn, max_retries=3):
    """
    Retry on transient auth errors (token refresh race, rate limits).
    Do NOT retry on permanent errors (missing permissions).
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            error_msg = str(e).lower()
            is_transient = any(
                phrase in error_msg
                for phrase in ["rate limit", "temporarily unavailable", "timeout"]
            )
            if not is_transient or attempt == max_retries - 1:
                raise
            wait = 2**attempt
            print(f"Transient auth error, retrying in {wait}s: {e}")
            time.sleep(wait)
```

---

## Token refresh considerations

### Model Serving

- System SP credentials are **automatically rotated** by the platform.
- OBO tokens are scoped to the request; no long-lived token to refresh.
- If an OBO token expires mid-request (very long operations), the call fails.
  Mitigation: keep individual API calls short; break large operations into steps.

### Databricks Apps

- The `x-forwarded-access-token` is refreshed by the proxy for active sessions.
- For **streaming responses** (SSE), capture the token at request start:

```python
# In middleware, stash token before streaming begins
request.state.obo_token = request.headers.get("x-forwarded-access-token")

# In streaming generator, use stashed token (not ContextVar, which may be cleared)
async def generate():
    token = request.state.obo_token
    client = WorkspaceClient(host=host, token=token)
    # ... stream results ...
```

- If the user's browser session expires during a long stream, subsequent API
  calls from that stream will fail. Handle gracefully.

### Local development

- Default `WorkspaceClient()` uses your configured auth (PAT, OAuth, etc.).
- PATs have configurable expiry (default 90 days).
- OAuth tokens auto-refresh via the SDK's credential provider.

---

## Model Serving configuration for OBO

Enable OBO in the serving endpoint YAML:

```yaml
resources:
  model_serving_endpoints:
    my_agent:
      name: my-agent
      config:
        served_entities:
          - name: current
            entity_name: ${var.catalog}.${var.schema}.my_agent
            entity_version: "${var.agent_version}"
            workload_size: Small
            scale_to_zero_enabled: true
            environment_vars:
              DATABRICKS_USE_IDENTITY_PASSTHROUGH: "true"
              WAREHOUSE_ID: ${var.warehouse_id}
              GENIE_SPACE_ID: ${var.genie_space_id}
        traffic_config:
          routes:
            - served_model_name: current
              traffic_percentage: 100
```

---

## Common OBO errors and fixes

### Error 1: Permission denied outside Model Serving

**Symptom:**
```
You need "Can View" permission. Config: host=..., auth_type=runtime
```

**Cause:** OBO attempted in notebook/job/evaluation (invalid credentials).

**Fix:** Add environment detection (see `detect_environment()` above).

### Error 2: databricks-ai-bridge ImportError

**Symptom:**
```
ImportError: No module named 'databricks_ai_bridge'
```

**Cause:** Package not installed in the serving environment.

**Fix:** Add to pip_requirements in `log_model()`:
```python
pip_requirements=["databricks-ai-bridge>=0.1.0", ...]
```

### Error 3: OBO works in serving but fails in evaluation

**Symptom:** Queries succeed in Model Serving but fail in `mlflow.evaluate()`.

**Cause:** Evaluation uses `SystemAuthPolicy` (system SP), not OBO. If resources
are missing from `SystemAuthPolicy`, the SP has no access.

**Fix:** Ensure `SystemAuthPolicy.resources` includes ALL resources the agent uses.

### Error 4: "No OBO token in request context"

**Symptom:** `get_user_workspace_client()` raises at runtime.

**Cause:** Called outside a request handler (e.g., in `__init__`) or the app
doesn't have OBO scopes configured.

**Fix:**
1. Move the call inside `predict()` / `invoke()` / route handler.
2. Verify scopes are configured in the app settings.

### Error 5: Wrong user identity in logs

**Symptom:** Audit logs show SP identity instead of user identity.

**Cause:** Using `WorkspaceClient()` (SP) instead of OBO client for the operation.

**Fix:** Verify the OBO client is used for operations that need user identity.

---

## OBO dependencies

```
# Required for Model Serving OBO
databricks-ai-bridge>=0.1.0    # ModelServingUserCredentials

# Required for Databricks Apps OBO
# (provided by the Apps runtime, no pip install needed)
# agent_server.utils.get_user_workspace_client

# Core dependencies
mlflow>=3.0.0                   # AuthPolicy support
databricks-sdk>=0.30.0          # WorkspaceClient with credential strategies
```

---

## Validation checklist

### Environment detection

- [ ] `detect_environment()` correctly identifies all environments
- [ ] OBO is only attempted in Model Serving or Databricks Apps
- [ ] Graceful fallback to default auth if OBO fails
- [ ] Logging shows which auth mode is active

### Resource declaration (for evaluation/notebooks)

- [ ] ALL resources declared in `SystemAuthPolicy.resources`
- [ ] Downstream dependencies included (Genie → tables + warehouse + functions)
- [ ] `auth_policy` parameter passed to `mlflow.pyfunc.log_model()`

### OBO configuration (for Model Serving)

- [ ] `UserAuthPolicy.api_scopes` includes needed scopes
- [ ] `DATABRICKS_USE_IDENTITY_PASSTHROUGH: "true"` in endpoint config
- [ ] `databricks-ai-bridge>=0.1.0` in pip_requirements

### OBO configuration (for Databricks Apps)

- [ ] Scopes added in app configuration
- [ ] `get_user_workspace_client()` called inside request handler only
- [ ] Streaming responses stash token at request start

### Testing

- [ ] Tested in notebook (default auth, no OBO)
- [ ] Tested via `mlflow.evaluate()` (system SP via SystemAuthPolicy)
- [ ] Tested in Model Serving (OBO with end-user credentials)
- [ ] Tested in Databricks Apps (OBO with downscoped token)
- [ ] Genie queries succeed in all relevant contexts
- [ ] Audit logs show correct user identity in OBO contexts

---

## Production learnings

### Jan 27, 2026 — OBO context detection

**Problem:** Agent evaluation failing with permission errors despite user having
proper permissions.

**Root cause:** Code attempted OBO whenever `databricks-ai-bridge` was installed,
regardless of execution context. OBO produces invalid credentials outside Model Serving.

**Solution:** Added environment variable checks to detect Model Serving context
before attempting OBO. Three variables checked: `IS_IN_DB_MODEL_SERVING_ENV`,
`DATABRICKS_SERVING_ENDPOINT`, `MLFLOW_DEPLOYMENT_FLAVOR_NAME`.

### Jan 27, 2026 — Genie resource declaration

**Problem:** After implementing OBO context detection, evaluation STILL failed
with permission errors.

**Root cause:** MLflow agents have TWO separate authentication mechanisms:
1. **OBO** → Model Serving (uses `UserAuthPolicy` scopes)
2. **Automatic auth passthrough** → evaluation/notebooks (uses `SystemAuthPolicy` resources)

Code had OBO configured via `UserAuthPolicy`, but `SystemAuthPolicy.resources`
did NOT include Genie Spaces.

**Solution:** Added `DatabricksGenieSpace` and `DatabricksSQLWarehouse` to
`SystemAuthPolicy.resources`. Both system and user policies must be configured
for complete coverage.

**Key learning:** `user_auth_policy` and `system_auth_policy` are independent.
Missing either one causes 100% failures in that context.

---

## Related references

- `user-authorization.md` — Full OBO implementation for Databricks Apps
- `model-serving-auth-passthrough.md` — AuthPolicy, SystemAuthPolicy, UserAuthPolicy
- `resource-permissions.md` — Permission matrix and debugging flowchart
- `app-authorization.md` — Service principal (non-OBO) authentication

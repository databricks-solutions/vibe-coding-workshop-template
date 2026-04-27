# Environment Detection and Runtime Configuration

Complete reference for detecting the Databricks runtime environment and
configuring MLflow, clients, logging, and tracing accordingly.

---

## Why Environment Detection Matters

Databricks agents run in four distinct environments, each with different
authentication mechanisms, client configurations, and observability capabilities.
Code that works in a notebook may fail silently in Model Serving if it assumes
`DATABRICKS_RUNTIME_VERSION` exists, or vice versa.

Reliable detection enables:

- Correct client initialization (OBO tokens vs service principal vs PAT)
- Appropriate logging verbosity and destinations
- Tracing configuration tuned to the environment's throughput profile
- Graceful degradation when capabilities are unavailable

---

## Complete Implementation

```python
"""Runtime environment detection for Databricks GenAI agents.

Detects whether code is running in Model Serving, Databricks Apps,
a notebook/job cluster, or a local development environment. Each
environment has different authentication, logging, and tracing
characteristics.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional


class RuntimeEnvironment(Enum):
    """Recognized Databricks runtime environments."""
    MODEL_SERVING = "model_serving"
    DATABRICKS_APPS = "databricks_apps"
    NOTEBOOK = "notebook"
    JOB = "job"
    LOCAL = "local"


def detect_environment() -> RuntimeEnvironment:
    """Detect the current Databricks runtime environment.

    Priority order matters — check from most-specific to least-specific:

    1. Model Serving (IS_IN_DB_MODEL_SERVING_ENV) — most restrictive
    2. Databricks Apps (DATABRICKS_APP_NAME) — app container
    3. Notebook vs Job (DATABRICKS_RUNTIME_VERSION) — cluster-based
    4. Local fallback — development machine

    Returns:
        RuntimeEnvironment enum value identifying the current runtime.

    Example:
        >>> env = detect_environment()
        >>> if env == RuntimeEnvironment.MODEL_SERVING:
        ...     configure_for_serving()
    """
    if os.environ.get("IS_IN_DB_MODEL_SERVING_ENV"):
        return RuntimeEnvironment.MODEL_SERVING

    if os.environ.get("DATABRICKS_APP_NAME"):
        return RuntimeEnvironment.DATABRICKS_APPS

    if os.environ.get("DATABRICKS_RUNTIME_VERSION"):
        if os.environ.get("IS_IN_JOB", "").lower() in ("true", "1"):
            return RuntimeEnvironment.JOB
        if _is_interactive_notebook():
            return RuntimeEnvironment.NOTEBOOK
        return RuntimeEnvironment.JOB

    return RuntimeEnvironment.LOCAL


def _is_interactive_notebook() -> bool:
    """Heuristic: interactive notebooks have dbutils in globals or IPython."""
    try:
        from IPython import get_ipython
        return get_ipython() is not None
    except ImportError:
        return False
```

---

## Per-Environment Configuration Table

| Aspect | Model Serving | Databricks Apps | Notebook / Job | Local Dev |
|---|---|---|---|---|
| **Auth method** | Automatic (SP) | OBO + SP fallback | Notebook credentials | PAT / `~/.databrickscfg` |
| **`WorkspaceClient`** | No-arg constructor | OBO header → `token=` | No-arg constructor | `profile=` or env vars |
| **MLflow tracking** | Automatic (workspace) | Automatic (workspace) | Automatic (workspace) | `MLFLOW_TRACKING_URI` required |
| **Autolog** | Enable in model `__init__` | Enable at app startup | Enable at cell/module top | Enable at script top |
| **Tracing export** | Automatic to workspace | Automatic to workspace | Automatic to workspace | Local file or remote URI |
| **HTTP pool size** | High (20+) | Medium (10-20) | Default | Default |
| **Retry config** | Aggressive (5+ retries) | Moderate (3 retries) | Default | Minimal |
| **Logging target** | stdout (captured by serving) | stdout (captured by app logs) | notebook display + driver log | stdout / file |
| **Spark available** | No | No | Yes | No (unless Connect) |

---

## Client Initialization Patterns

### Model Serving

```python
from databricks.sdk import WorkspaceClient

def init_serving_client() -> WorkspaceClient:
    """Model Serving auto-configures auth from the serving environment.

    No arguments needed — the SDK reads credentials from the container.
    """
    return WorkspaceClient()
```

### Databricks Apps (OBO)

```python
from databricks.sdk import WorkspaceClient

def init_apps_client(request_headers: dict) -> WorkspaceClient:
    """Apps use On-Behalf-Of tokens from the forwarded access header.

    Falls back to SP credentials if OBO token is missing.
    """
    obo_token = request_headers.get("x-forwarded-access-token")
    if obo_token:
        host = os.environ.get("DATABRICKS_HOST", "")
        return WorkspaceClient(host=host, token=obo_token)
    return WorkspaceClient()
```

### Notebook / Job

```python
from databricks.sdk import WorkspaceClient

def init_notebook_client() -> WorkspaceClient:
    """Notebooks use ambient credentials from the cluster.

    The SDK automatically detects notebook auth context.
    """
    return WorkspaceClient()
```

### Local Development

```python
from databricks.sdk import WorkspaceClient

def init_local_client(profile: str = "DEFAULT") -> WorkspaceClient:
    """Local dev requires explicit profile or environment variables.

    Ensure ~/.databrickscfg has the target profile, or set
    DATABRICKS_HOST and DATABRICKS_TOKEN.
    """
    if os.environ.get("DATABRICKS_HOST") and os.environ.get("DATABRICKS_TOKEN"):
        return WorkspaceClient()
    return WorkspaceClient(profile=profile)
```

### Unified Factory

```python
def create_workspace_client(
    env: RuntimeEnvironment | None = None,
    request_headers: dict | None = None,
    profile: str = "DEFAULT",
) -> WorkspaceClient:
    """Create a WorkspaceClient appropriate for the current environment.

    Args:
        env: Override auto-detection. If None, calls detect_environment().
        request_headers: HTTP headers (required for Apps OBO auth).
        profile: Databricks CLI profile name (local dev only).

    Returns:
        Configured WorkspaceClient.
    """
    if env is None:
        env = detect_environment()

    if env == RuntimeEnvironment.MODEL_SERVING:
        return init_serving_client()
    elif env == RuntimeEnvironment.DATABRICKS_APPS:
        return init_apps_client(request_headers or {})
    elif env in (RuntimeEnvironment.NOTEBOOK, RuntimeEnvironment.JOB):
        return init_notebook_client()
    else:
        return init_local_client(profile)
```

---

## Logging and Tracing Differences

### Tracing Configuration by Environment

```python
import os


def configure_tracing(env: RuntimeEnvironment) -> None:
    """Set MLflow HTTP client env vars tuned to the environment.

    Call this BEFORE enabling autolog or making any MLflow calls.
    """
    configs = {
        RuntimeEnvironment.MODEL_SERVING: {
            "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "5",
            "MLFLOW_HTTP_REQUEST_TIMEOUT": "120",
        },
        RuntimeEnvironment.DATABRICKS_APPS: {
            "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "3",
            "MLFLOW_HTTP_REQUEST_TIMEOUT": "60",
        },
        RuntimeEnvironment.JOB: {
            "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "5",
            "MLFLOW_HTTP_REQUEST_TIMEOUT": "120",
        },
        RuntimeEnvironment.NOTEBOOK: {
            "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "3",
            "MLFLOW_HTTP_REQUEST_TIMEOUT": "60",
        },
        RuntimeEnvironment.LOCAL: {
            "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "2",
            "MLFLOW_HTTP_REQUEST_TIMEOUT": "30",
        },
    }
    for key, value in configs.get(env, {}).items():
        os.environ.setdefault(key, value)
```

### Logging Patterns

| Environment | Recommendation | Reason |
|---|---|---|
| Model Serving | `logging.getLogger()` to stdout, JSON format | Captured by serving infra |
| Databricks Apps | `logging.getLogger()` to stdout | Visible in `apx dev logs` and deployed app logs |
| Notebook | `print()` or `display()` for user-facing, `logging` for structured | Notebook captures cell output |
| Job | `logging.getLogger()` with structured JSON | Searchable in driver logs |
| Local | `logging.getLogger()` with console handler | Developer convenience |

---

## Testing Patterns

### Unit Testing with Environment Mocks

```python
import os
from unittest.mock import patch


def test_detect_model_serving():
    with patch.dict(os.environ, {"IS_IN_DB_MODEL_SERVING_ENV": "true"}, clear=False):
        assert detect_environment() == RuntimeEnvironment.MODEL_SERVING


def test_detect_databricks_apps():
    env = {"DATABRICKS_APP_NAME": "my-app"}
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("IS_IN_DB_MODEL_SERVING_ENV", None)
        assert detect_environment() == RuntimeEnvironment.DATABRICKS_APPS


def test_detect_notebook():
    env = {"DATABRICKS_RUNTIME_VERSION": "15.4"}
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("IS_IN_DB_MODEL_SERVING_ENV", None)
        os.environ.pop("DATABRICKS_APP_NAME", None)
        os.environ.pop("IS_IN_JOB", None)
        assert detect_environment() in (
            RuntimeEnvironment.NOTEBOOK,
            RuntimeEnvironment.JOB,
        )


def test_detect_local():
    with patch.dict(os.environ, {}, clear=True):
        assert detect_environment() == RuntimeEnvironment.LOCAL
```

### Integration Testing: Environment-Specific Behavior

```python
def test_client_creation_all_envs():
    """Verify create_workspace_client handles every environment."""
    for env in RuntimeEnvironment:
        if env == RuntimeEnvironment.DATABRICKS_APPS:
            client = create_workspace_client(
                env=env, request_headers={"x-forwarded-access-token": "test"}
            )
        elif env == RuntimeEnvironment.LOCAL:
            with patch.dict(os.environ, {
                "DATABRICKS_HOST": "https://test.databricks.com",
                "DATABRICKS_TOKEN": "dapi_test",
            }):
                client = create_workspace_client(env=env)
        else:
            client = create_workspace_client(env=env)
        assert client is not None
```

---

## Environment Variable Reference

| Variable | Set In | Indicates |
|---|---|---|
| `IS_IN_DB_MODEL_SERVING_ENV` | Model Serving container | Agent is running as a served model |
| `DATABRICKS_APP_NAME` | Databricks Apps runtime | Agent is running inside a Databricks App |
| `DATABRICKS_RUNTIME_VERSION` | Cluster (notebook or job) | Code runs on a Databricks cluster |
| `IS_IN_JOB` | Job task context | Distinguishes job from interactive notebook |
| `DATABRICKS_HOST` | Manual / Apps / Serving | Workspace URL for SDK |
| `DATABRICKS_TOKEN` | Manual / local dev | PAT for local development |
| `MLFLOW_TRACKING_URI` | Manual / local dev | MLflow tracking server (auto-set on Databricks) |

---

## References

- [Databricks SDK authentication](https://docs.databricks.com/en/dev-tools/sdk-python.html)
- [Model Serving environment](https://docs.databricks.com/en/machine-learning/model-serving/index.html)
- [Databricks Apps OBO auth](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)
- Related: [`anti-patterns.md`](anti-patterns.md) — environment detection mistakes
- Related: [`model-signatures.md`](model-signatures.md) — signature behavior per environment

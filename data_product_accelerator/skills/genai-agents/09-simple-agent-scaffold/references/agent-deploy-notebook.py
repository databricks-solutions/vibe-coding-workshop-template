# Databricks notebook source
# MAGIC %md
# MAGIC # Agent Deploy — Steps 2–5 (OBO-first, canonical)
# MAGIC
# MAGIC Runs Steps 2–5 of `09-simple-agent-scaffold/SKILL.md` in a single notebook.
# MAGIC Designed to be submitted as a serverless job via `references/agent_deploy_job.yml`.
# MAGIC
# MAGIC **Authentication is OBO-first** (proven end-to-end on Managed MCP):
# MAGIC - The agent is logged with a dual `auth_policy`:
# MAGIC   - `SystemAuthPolicy.resources` = LLM endpoint + Genie Space + SQL warehouse
# MAGIC     (the system SP gets `CAN_QUERY` / `Can Run` / `CAN USE` automatically).
# MAGIC   - `UserAuthPolicy(api_scopes=["mcp.genie", "sql"])` = the user token is
# MAGIC     forwarded so the Genie MCP call runs On-Behalf-Of the caller.
# MAGIC - `databricks-ai-bridge` MUST be in pip_requirements for OBO to work.
# MAGIC - Step 5b's UC grants to the system SP are a **best-effort** fallback for true
# MAGIC   machine-to-machine callers — they are NOT the gate and are NOT verified via
# MAGIC   `SHOW GRANTS` (system SPs are invisible to SCIM, so `SHOW GRANTS` is empty
# MAGIC   even when a grant is accepted). The gate is the OBO query in Step 5.
# MAGIC
# MAGIC Inputs (via widgets or job `base_parameters`):
# MAGIC - `uc_catalog`, `uc_agent_schema`, `uc_model_name` — Unity Catalog target for `register_model()`
# MAGIC - `uc_gold_schema` — schema holding the Genie Space's gold tables / TVFs
# MAGIC - `warehouse_id` — SQL warehouse (declared as a resource AND used for UC GRANTs)
# MAGIC - `genie_space_id` — space the agent talks to (resources passthrough + Step 5a probe)
# MAGIC - `agent_endpoint_name` — explicit, stable serving endpoint name (no auto-truncation)
# MAGIC - `agent_folder_ws_path` — absolute workspace path where `agent.py` + `agent-config.yaml` live
# MAGIC
# MAGIC Re-running is idempotent.

# COMMAND ----------
# MAGIC %pip install --quiet databricks-agents databricks-openai "mlflow[databricks]" mcp nest_asyncio databricks-ai-bridge databricks-sdk uv
# MAGIC dbutils.library.restartPython()

# COMMAND ----------
dbutils.widgets.text("uc_catalog", "my_catalog")
dbutils.widgets.text("uc_agent_schema", "my_schema")
dbutils.widgets.text("uc_model_name", "my_genie_agent")
dbutils.widgets.text("uc_gold_schema", "my_gold_schema")
dbutils.widgets.text("warehouse_id", "")
dbutils.widgets.text("genie_space_id", "")
dbutils.widgets.text("agent_endpoint_name", "")
dbutils.widgets.text("agent_folder_ws_path", "")

UC_CATALOG           = dbutils.widgets.get("uc_catalog")
UC_AGENT_SCHEMA      = dbutils.widgets.get("uc_agent_schema")
UC_MODEL_NAME_SHORT  = dbutils.widgets.get("uc_model_name")
UC_GOLD_SCHEMA       = dbutils.widgets.get("uc_gold_schema")
WAREHOUSE_ID         = dbutils.widgets.get("warehouse_id")
GENIE_SPACE_ID       = dbutils.widgets.get("genie_space_id")
AGENT_ENDPOINT_NAME  = dbutils.widgets.get("agent_endpoint_name")
AGENT_FOLDER_WS_PATH = dbutils.widgets.get("agent_folder_ws_path")

UC_MODEL_NAME = f"{UC_CATALOG}.{UC_AGENT_SCHEMA}.{UC_MODEL_NAME_SHORT}"

# Endpoint naming is an EXPLICIT contract. Never rely on agents.deploy() auto-naming
# (it prepends "agents_" and truncates to 63 chars — silent mismatches downstream).
# Prefer the supplied agent_endpoint_name; fall back to the short model name (already
# free of dots), trimmed to the 63-char limit.
ENDPOINT_NAME = (AGENT_ENDPOINT_NAME or UC_MODEL_NAME_SHORT)[:63]
print(f"UC model:     {UC_MODEL_NAME}")
print(f"Endpoint:     {ENDPOINT_NAME}")
print(f"Agent folder: {AGENT_FOLDER_WS_PATH}")

# COMMAND ----------
# MAGIC %md ## Ensure the agent UC schema exists (direct SQL — the schema exception)
# MAGIC
# MAGIC Schemas are NOT modeled as bundle resources in this workshop — they are the
# MAGIC deliberate exception, created directly with SQL DDL (`CREATE SCHEMA IF NOT
# MAGIC EXISTS`). `databricks schemas create` is also hard-blocked on Genie Code, so
# MAGIC SQL is the portable path. This runs INSIDE the deployed job, so the schema is
# MAGIC guaranteed to exist before `register_model()` in Step 4.

# COMMAND ----------
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{UC_CATALOG}`.`{UC_AGENT_SCHEMA}`")
print(f"Schema ready: {UC_CATALOG}.{UC_AGENT_SCHEMA}")

# COMMAND ----------
# MAGIC %md ## Step 2 — Local test (non-streaming)
# MAGIC
# MAGIC In the job (notebook) context there is no forwarded user token, so the agent's
# MAGIC `_obo_client()` falls back to the job's identity — this exercises the import,
# MAGIC tool wiring, and LLM path. The OBO path itself is exercised by the Step 5 query
# MAGIC against the deployed endpoint.

# COMMAND ----------
import os
import sys

# Jobs start CWD at /, not the notebook's directory. Point at the folder that
# holds agent.py + agent-config.yaml so `from agent import AGENT` resolves.
if AGENT_FOLDER_WS_PATH and AGENT_FOLDER_WS_PATH not in sys.path:
    sys.path.insert(0, AGENT_FOLDER_WS_PATH)
os.chdir(AGENT_FOLDER_WS_PATH or os.getcwd())

from agent import AGENT, LLM_ENDPOINT_NAME  # noqa: E402

result = AGENT.predict(
    {"input": [{"role": "user", "content": "Hello — list the tools you can call."}]}
)
print(result.model_dump(exclude_none=True))

# COMMAND ----------
# MAGIC %md ## Step 3 — Log with MLflow (dual `auth_policy`; `model_config` REQUIRED)
# MAGIC
# MAGIC `auth_policy` and `resources=` are mutually exclusive — put ALL resources inside
# MAGIC `SystemAuthPolicy.resources`. `DatabricksSQLWarehouse` is mandatory: the Genie
# MAGIC Space executes its SQL on that warehouse. `UserAuthPolicy` uses `mcp.genie` (the
# MAGIC Managed MCP scope — NOT `dashboards.genie`, which is the Conversation API) plus
# MAGIC `sql`.

# COMMAND ----------
import mlflow
from mlflow.models.auth_policy import AuthPolicy, SystemAuthPolicy, UserAuthPolicy
from mlflow.models.resources import (
    DatabricksGenieSpace,
    DatabricksServingEndpoint,
    DatabricksSQLWarehouse,
)
from pkg_resources import get_distribution


def _pin(pkg: str) -> str:
    try:
        return f"{pkg}=={get_distribution(pkg).version}"
    except Exception:  # noqa: BLE001 — unpinned fallback if metadata is absent
        return pkg


auth_policy = AuthPolicy(
    system_auth_policy=SystemAuthPolicy(
        resources=[
            DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME),
            DatabricksGenieSpace(genie_space_id=GENIE_SPACE_ID),
            DatabricksSQLWarehouse(warehouse_id=WAREHOUSE_ID),
        ]
    ),
    user_auth_policy=UserAuthPolicy(api_scopes=["mcp.genie", "sql"]),
)

with mlflow.start_run():
    logged = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",
        model_config="agent-config.yaml",
        auth_policy=auth_policy,
        pip_requirements=[
            _pin("mlflow[databricks]"),
            _pin("mcp"),
            _pin("databricks-openai"),
            "databricks-ai-bridge",  # REQUIRED for OBO (ModelServingUserCredentials)
            "databricks-sdk",
        ],
    )

# Pre-deployment validation — catches dependency/serialization issues in an isolated env.
mlflow.models.predict(
    model_uri=f"runs:/{logged.run_id}/agent",
    input_data={"input": [{"role": "user", "content": "Hello!"}]},
    env_manager="uv",
)

# COMMAND ----------
# MAGIC %md ## Step 4 — Register in Unity Catalog

# COMMAND ----------
mlflow.set_registry_uri("databricks-uc")
registered = mlflow.register_model(model_uri=logged.model_uri, name=UC_MODEL_NAME)
print(f"Registered version: {registered.version}")

# COMMAND ----------
# MAGIC %md ## Step 5 — Deploy to Model Serving (explicit endpoint name + idempotent)

# COMMAND ----------
import time

from databricks import agents
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()


def _wait_not_updating(endpoint_name: str, timeout_s: int = 20 * 60) -> None:
    """If the endpoint exists, wait until it is NOT_UPDATING before (re)deploying.

    Deploying onto an endpoint that is still applying a config update raises
    ResourceConflict. This makes re-runs idempotent.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            ep = w.serving_endpoints.get(endpoint_name)
        except Exception:  # noqa: BLE001 — endpoint doesn't exist yet; nothing to wait on
            return
        cu = str(getattr(ep.state, "config_update", ""))
        if "NOT_UPDATING" in cu or cu == "" or cu == "None":
            return
        print(f"endpoint busy (config_update={cu}); waiting…")
        time.sleep(20)
    raise RuntimeError(f"{endpoint_name} stuck updating past {timeout_s}s.")


_wait_not_updating(ENDPOINT_NAME)

agents.deploy(
    UC_MODEL_NAME,
    registered.version,
    endpoint_name=ENDPOINT_NAME,  # explicit, stable — never auto-derived
    tags={"endpointSource": "simple-agent-scaffold"},
)

# COMMAND ----------
# MAGIC %md ## Wait for READY

# COMMAND ----------
deadline = time.time() + 20 * 60  # 20 minutes
while time.time() < deadline:
    ep = w.serving_endpoints.get(ENDPOINT_NAME)
    ready = getattr(ep.state, "ready", None)
    config_update = getattr(ep.state, "config_update", None)
    print(f"ready={ready} config_update={config_update}")
    if str(ready).endswith("READY") and "NOT_UPDATING" in str(config_update):
        break
    time.sleep(20)
else:
    raise RuntimeError(f"{ENDPOINT_NAME} did not reach READY in 20 minutes.")

# COMMAND ----------
# MAGIC %md ## Step 5a — `serialized_space` health probe (BEFORE anything else)
# MAGIC
# MAGIC An empty `serialized_space` produces the same `PERMISSION_DENIED: No access to
# MAGIC table X` symptom as a real permission gap. Rule it out first.

# COMMAND ----------
space = w.api_client.do("GET", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}")
serialized_len = len(space.get("serialized_space") or "")
print(f"serialized_space length: {serialized_len}")
if serialized_len == 0:
    raise RuntimeError(
        "Genie Space serialized_space is empty. Likely wiped by a partial "
        "PATCH /api/2.0/data-rooms/{id}. Recover with "
        "references/restore-genie-space.py BEFORE proceeding."
    )
print("Probe passed. Proceeding.")

# COMMAND ----------
# MAGIC %md ## Step 5b — Best-effort system-SP UC grants (fallback only — NOT the gate)
# MAGIC
# MAGIC OBO (Step 5 query) is the primary, proven path and needs ZERO grants. These
# MAGIC grants only matter for true machine-to-machine callers that have no user token
# MAGIC (e.g. an app SP token, a scheduled job) and therefore fall back to the endpoint
# MAGIC system SP. Caveats proven by probe:
# MAGIC - Multiple system SPs may exist (rotation across deploys) — grant ALL of them.
# MAGIC - `SHOW GRANTS` returns empty for system SPs (invisible to SCIM); do NOT use it
# MAGIC   to verify. A `SUCCEEDED` GRANT is the best signal available here.
# MAGIC - This block never fails the deploy; it logs best-effort outcomes only.

# COMMAND ----------
def discover_endpoint_sps(w: WorkspaceClient, endpoint_name: str) -> list[str]:
    """Return ALL system SP UUIDs ever created for this endpoint (rotation-aware).

    System SPs are NOT in SCIM — the reliable source is the endpoint event stream.
    UUIDs are stripped of any backticks to avoid malformed GRANT SQL.
    """
    resp = w.api_client.do(
        "GET",
        f"/api/2.0/serving-endpoints/{endpoint_name}/events",
        query={"limit": 200},
    )
    marker = "System service principal creation with ID "
    sps: list[str] = []
    for e in resp.get("events", []):
        msg = e.get("message", "")
        if marker in msg:
            sps.append(msg.split(marker, 1)[1].split(" ", 1)[0].strip().strip("`"))
    return list(dict.fromkeys(sps))  # de-dup, preserve order


SPS = discover_endpoint_sps(w, ENDPOINT_NAME)
print(f"Discovered system SP(s): {SPS or '(none yet)'}")

for sp in SPS:
    for stmt in [
        f"GRANT USE CATALOG ON CATALOG `{UC_CATALOG}` TO `{sp}`",
        f"GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA `{UC_CATALOG}`.`{UC_GOLD_SCHEMA}` TO `{sp}`",
    ]:
        try:
            w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID, statement=stmt, wait_timeout="30s"
            )
            print(f"best-effort OK: {stmt}")
        except Exception as e:  # noqa: BLE001 — best-effort; never fail the deploy
            print(f"best-effort SKIP ({type(e).__name__}): {stmt}")

# COMMAND ----------
# MAGIC %md ## Step 5 verification gate — OBO query via the SDK (the real gate)
# MAGIC
# MAGIC Query the deployed endpoint with a domain-specific data question. The call is
# MAGIC forwarded On-Behalf-Of the caller (this notebook's identity), so it exercises
# MAGIC the OBO + Genie MCP path end-to-end. No PAT, no `curl`, no `databricks auth
# MAGIC token` (hard-blocked on Genie Code).
# MAGIC
# MAGIC PASS = the response contains a `function_call` to the Genie MCP tool followed by
# MAGIC a `message` with real numbers. Replace the question with one your space answers.

# COMMAND ----------
import json

DOMAIN_QUESTION = "What are the top 5 results by total value?"  # EDIT to your space

resp = w.serving_endpoints.query(
    name=ENDPOINT_NAME,
    inputs={"input": [{"role": "user", "content": DOMAIN_QUESTION}]},
)
payload = resp.as_dict() if hasattr(resp, "as_dict") else resp
out = payload.get("output", []) if isinstance(payload, dict) else []
has_tool_call = any(o.get("type") == "function_call" for o in out)
has_message = any(o.get("type") == "message" for o in out)
print(json.dumps(payload, default=str)[:2500])
print(f"function_call present: {has_tool_call} | message present: {has_message}")
if not (has_tool_call and has_message):
    raise RuntimeError(
        "Verification FAILED: expected a function_call to the Genie MCP tool plus a "
        "message with data. Greeting-only means the tool path was not exercised — "
        "check the system prompt (add a domain nudge) and the space's content."
    )
print("Verification PASSED (OBO tool-calling path returned data).")

# COMMAND ----------
# MAGIC %md ## Emit DEPLOY_CHECKPOINT.md for Step 17 (AppKit serving wiring)

# COMMAND ----------
import pathlib
import textwrap

checkpoint_path = pathlib.Path(AGENT_FOLDER_WS_PATH) / "DEPLOY_CHECKPOINT.md"
checkpoint = textwrap.dedent(
    f"""
    # Agent Deploy Checkpoint (Step 16)

    Structured handoff to Step 17 (`apps_lakebase/skills/06-appkit-serving-wiring`).
    Do NOT rederive these values by hand — read them from this file.

    | Field | Value |
    |---|---|
    | Endpoint name | `{ENDPOINT_NAME}` |
    | Auth model | `EMBEDDED_AND_USER_CREDENTIALS` (OBO-first) |
    | UC model name | `{UC_MODEL_NAME}` |
    | UC model version | `{registered.version}` |
    | Genie Space ID | `{GENIE_SPACE_ID}` |
    | Warehouse ID | `{WAREHOUSE_ID}` |
    | System SP(s) (best-effort grant) | `{', '.join(SPS) or '(none discovered)'}` |
    | Gold schema (best-effort grant) | `{UC_CATALOG}.{UC_GOLD_SCHEMA}` |

    ## How the agent authenticates to Genie

    - **Primary (proven):** On-Behalf-Of the caller. The agent builds an OBO
      `WorkspaceClient` per request (`UserAuthPolicy` scope `mcp.genie`) so Genie
      runs as the invoking user. Requires `databricks-ai-bridge` in the image.
    - **Fallback (best-effort):** true machine-to-machine callers with no user token
      use the endpoint system SP, which needs UC `SELECT`/`EXECUTE` on
      `{UC_CATALOG}.{UC_GOLD_SCHEMA}`. Step 5b attempts this; it is not guaranteed.
    - **AppKit:** forward the user token (`x-forwarded-access-token`) so the app→agent
      hop stays OBO and never depends on the SP fallback.

    ## Verify (SDK, no PAT)

    ```python
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    r = w.serving_endpoints.query(
        name="{ENDPOINT_NAME}",
        inputs={{"input": [{{"role": "user", "content": "<domain-specific data question>"}}]}},
    )
    print(r.as_dict() if hasattr(r, "as_dict") else r)
    ```

    PASS = at least one `function_call` to the Genie MCP tool in `.output`, then a
    `message` with real numbers.
    """
).strip()
checkpoint_path.write_text(checkpoint + "\n")
print(f"Wrote {checkpoint_path}")
print(checkpoint)

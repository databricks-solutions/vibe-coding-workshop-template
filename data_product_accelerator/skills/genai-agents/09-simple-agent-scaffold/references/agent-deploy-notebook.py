# Databricks notebook source
# MAGIC %md
# MAGIC # Agent Deploy — Steps 2–5 (canonical)
# MAGIC
# MAGIC Runs Steps 2–5 of `09-simple-agent-scaffold/SKILL.md` in a single notebook,
# MAGIC with **Step 5b auto-grant baked in**. Designed to be submitted as a
# MAGIC serverless job via `references/agent_deploy_job.yml`.
# MAGIC
# MAGIC Inputs (via widgets or job `base_parameters`):
# MAGIC - `uc_catalog`, `uc_agent_schema`, `uc_model_name` — Unity Catalog target for `register_model()`
# MAGIC - `uc_gold_schema` — schema holding the Genie Space's gold tables / TVFs
# MAGIC - `warehouse_id` — SQL warehouse for UC GRANT statements
# MAGIC - `genie_space_id` — space the agent talks to (for resources passthrough + Step 5a probe)
# MAGIC - `agent_folder_ws_path` — absolute workspace path where `agent.py` + `agent-config.yaml` live
# MAGIC
# MAGIC The notebook prints the endpoint system SP UUID and the verification `curl` block.
# MAGIC Re-running is idempotent.

# COMMAND ----------
# MAGIC %pip install --quiet databricks-agents databricks-openai "mlflow[databricks]" mcp nest_asyncio uv
# MAGIC dbutils.library.restartPython()

# COMMAND ----------
dbutils.widgets.text("uc_catalog", "my_catalog")
dbutils.widgets.text("uc_agent_schema", "my_schema")
dbutils.widgets.text("uc_model_name", "my_genie_agent")
dbutils.widgets.text("uc_gold_schema", "my_gold_schema")
dbutils.widgets.text("warehouse_id", "")
dbutils.widgets.text("genie_space_id", "")
dbutils.widgets.text("agent_folder_ws_path", "")

UC_CATALOG           = dbutils.widgets.get("uc_catalog")
UC_AGENT_SCHEMA      = dbutils.widgets.get("uc_agent_schema")
UC_MODEL_NAME_SHORT  = dbutils.widgets.get("uc_model_name")
UC_GOLD_SCHEMA       = dbutils.widgets.get("uc_gold_schema")
WAREHOUSE_ID         = dbutils.widgets.get("warehouse_id")
GENIE_SPACE_ID       = dbutils.widgets.get("genie_space_id")
AGENT_FOLDER_WS_PATH = dbutils.widgets.get("agent_folder_ws_path")

UC_MODEL_NAME = f"{UC_CATALOG}.{UC_AGENT_SCHEMA}.{UC_MODEL_NAME_SHORT}"
ENDPOINT_NAME = UC_MODEL_NAME.replace(".", "-")
print(f"UC model:     {UC_MODEL_NAME}")
print(f"Endpoint:     {ENDPOINT_NAME}")
print(f"Agent folder: {AGENT_FOLDER_WS_PATH}")

# COMMAND ----------
# MAGIC %md ## Step 2 — Local test (non-streaming + streaming)

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
# MAGIC %md ## Step 3 — Log with MLflow (`model_config` is REQUIRED — see SKILL.md)

# COMMAND ----------
import mlflow
from mlflow.models.resources import DatabricksGenieSpace, DatabricksServingEndpoint
from pkg_resources import get_distribution

resources = [
    DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME),
    DatabricksGenieSpace(genie_space_id=GENIE_SPACE_ID),
]

with mlflow.start_run():
    logged = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",
        model_config="agent-config.yaml",
        resources=resources,
        pip_requirements=[
            f"mlflow[databricks]=={get_distribution('mlflow').version}",
            f"mcp=={get_distribution('mcp').version}",
            f"databricks-openai=={get_distribution('databricks-openai').version}",
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
# MAGIC %md ## Step 5 — Deploy to Model Serving

# COMMAND ----------
from databricks import agents

agents.deploy(
    UC_MODEL_NAME,
    registered.version,
    tags={"endpointSource": "simple-agent-scaffold"},
)

# COMMAND ----------
# MAGIC %md ## Wait for READY

# COMMAND ----------
import time
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

deadline = time.time() + 20 * 60  # 20 minutes
while time.time() < deadline:
    ep = w.serving_endpoints.get(ENDPOINT_NAME)
    ready = getattr(ep.state, "ready", None)
    config_update = getattr(ep.state, "config_update", None)
    print(f"ready={ready} config_update={config_update}")
    if str(ready) == "ServingEndpointStateReady.READY" or str(ready) == "READY":
        break
    time.sleep(20)
else:
    raise RuntimeError(f"{ENDPOINT_NAME} did not reach READY in 20 minutes.")

# COMMAND ----------
# MAGIC %md ## Step 5a — `PERMISSION_DENIED` disambiguation (probe BEFORE granting)

# COMMAND ----------
# Probe 1: is serialized_space non-empty?
space = w.api_client.do("GET", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}")
serialized_len = len(space.get("serialized_space") or "")
print(f"serialized_space length: {serialized_len}")
if serialized_len == 0:
    raise RuntimeError(
        "Genie Space serialized_space is empty. Likely wiped by a partial "
        "PATCH /api/2.0/data-rooms/{id}. Recover with "
        "references/restore-genie-space.py BEFORE granting permissions."
    )

# Probe 2: can YOU ask the space a question as yourself? (OBO CLI)
# Skipped in notebook — run locally from Step 5a in SKILL.md if probe 1 passed
# but the agent still returns PERMISSION_DENIED.
print("Probe 1 passed. Proceeding to Step 5b auto-grant.")

# COMMAND ----------
# MAGIC %md ## Step 5b — Auto-discover endpoint system SP + apply idempotent UC grants

# COMMAND ----------
def get_endpoint_sp(w: WorkspaceClient, endpoint_name: str) -> str:
    """Return the system SP UUID created by agents.deploy() for this endpoint.

    System SPs are NOT in SCIM — the reliable source is the endpoint's event stream.
    """
    resp = w.api_client.do(
        "GET",
        f"/api/2.0/serving-endpoints/{endpoint_name}/events",
        query={"limit": 200},
    )
    marker = "System service principal creation with ID "
    for e in resp.get("events", []):
        msg = e.get("message", "")
        if marker in msg:
            return msg.split(marker, 1)[1].split(" ", 1)[0]
    raise RuntimeError(
        f"No system SP creation event on {endpoint_name}. "
        f"Endpoint may still be provisioning."
    )


SP = get_endpoint_sp(w, ENDPOINT_NAME)
print(f"Endpoint system SP: {SP}")

grants = [
    f"GRANT USE CATALOG ON CATALOG `{UC_CATALOG}` TO `{SP}`",
    f"GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA `{UC_CATALOG}`.`{UC_GOLD_SCHEMA}` TO `{SP}`",
]
for stmt in grants:
    w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=stmt,
        wait_timeout="30s",
    )
    print(f"OK: {stmt}")

# COMMAND ----------
# MAGIC %md ## Step 5 verification gate — `curl + PAT` with a domain question
# MAGIC
# MAGIC Copy the block below into your terminal (not the notebook). Replace
# MAGIC `<domain-specific data question>` with something your Genie Space can
# MAGIC answer. PASS = `.output` contains at least one `function_call`.

# COMMAND ----------
host = w.config.host
print(
    f"""
ENDPOINT="{ENDPOINT_NAME}"
HOST="{host}"
TOKEN="<paste a PAT with workspace access>"
curl -sS -X POST "$HOST/serving-endpoints/$ENDPOINT/invocations" \\
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
  -d '{{"input":[{{"role":"user","content":"<domain-specific data question>"}}]}}' \\
  | jq '.output[] | select(.type=="function_call" or .type=="message")'
""".strip()
)

# COMMAND ----------
# MAGIC %md ## Emit DEPLOY_CHECKPOINT.md for Step 17 (AppKit serving wiring)

# COMMAND ----------
import json
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
    | Endpoint name (full) | `{ENDPOINT_NAME}` |
    | Endpoint name (64-char truncated) | `{ENDPOINT_NAME[:64]}` |
    | System SP UUID | `{SP}` |
    | UC model name | `{UC_MODEL_NAME}` |
    | UC model version | `{registered.version}` |
    | Genie Space ID | `{GENIE_SPACE_ID}` |
    | Warehouse ID | `{WAREHOUSE_ID}` |
    | Gold schema granted | `{UC_CATALOG}.{UC_GOLD_SCHEMA}` |

    ## Verified `curl` block

    ```bash
    ENDPOINT="{ENDPOINT_NAME}"
    HOST="{host}"
    TOKEN="<PAT>"
    curl -sS -X POST "$HOST/serving-endpoints/$ENDPOINT/invocations" \\
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
      -d '{{"input":[{{"role":"user","content":"<domain-specific data question>"}}]}}' \\
      | jq '.output[] | select(.type=="function_call" or .type=="message")'
    ```

    PASS = at least one `function_call` to `<tool>__query_space_{GENIE_SPACE_ID}` in `.output`.
    """
).strip()
checkpoint_path.write_text(checkpoint + "\n")
print(f"Wrote {checkpoint_path}")
print(checkpoint)

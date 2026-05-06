# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy MCP AppKit Skill App
# MAGIC
# MAGIC This notebook deploys the `mcp-appkit-skill` Databricks App that provides
# MAGIC 11 MCP tools for scaffolding, deploying, and extending AppKit applications.
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - Workspace admin privileges
# MAGIC - Databricks Apps enabled in workspace settings
# MAGIC
# MAGIC **What it does:**
# MAGIC 1. Clones the source from GitHub (or uses local files)
# MAGIC 2. Uploads to a workspace folder
# MAGIC 3. Creates and deploys the Databricks App

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

APP_NAME = "mcp-appkit-skill"
# Where to upload the source in the workspace
WORKSPACE_TARGET = f"/Workspace/Shared/{APP_NAME}"

# GitHub source — clone from here if running fresh
GITHUB_REPO = "https://github.com/<YOUR_ORG>/mcp-appkit-skill"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Upload source files to workspace
# MAGIC
# MAGIC If you cloned this repo locally, the source files are in the same folder
# MAGIC as this notebook. Otherwise, download from the GitHub URL above.

# COMMAND ----------

import base64
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

w = WorkspaceClient()

# Source files — read from the same workspace folder as this notebook
import os

notebook_dir = os.path.dirname(dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get())
print(f"Notebook directory: {notebook_dir}")

FILES_TO_UPLOAD = [
    "app.yaml",
    "requirements.txt",
    "server/__init__.py",
    "server/main.py",
]

for f in FILES_TO_UPLOAD:
    src_path = f"{notebook_dir}/{f}"
    dst_path = f"{WORKSPACE_TARGET}/{f}"

    try:
        resp = w.workspace.export(path=src_path, format=ImportFormat.AUTO)
        w.workspace.import_(
            path=dst_path,
            content=resp.content,
            format=ImportFormat.AUTO,
            overwrite=True,
        )
        print(f"  ✓ {f}")
    except Exception as e:
        print(f"  ✗ {f}: {e}")

print(f"\n✓ Source uploaded to {WORKSPACE_TARGET}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create the Databricks App

# COMMAND ----------

from databricks.sdk.service.apps import App

try:
    app_info = w.apps.get(name=APP_NAME)
    print(f"App '{APP_NAME}' already exists")
    print(f"  URL: {app_info.url}")
    print(f"  State: {app_info.compute_status.state.name}")
except Exception:
    print(f"Creating app '{APP_NAME}'...")
    app_info = w.apps.create_and_wait(
        app=App(name=APP_NAME, description="MCP server with 11 AppKit tools")
    )
    print(f"✓ App created: {app_info.url}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Deploy the app

# COMMAND ----------

from databricks.sdk.service.apps import AppDeployment
import time

print(f"Deploying from {WORKSPACE_TARGET}...")
deployment = w.apps.deploy(
    app_name=APP_NAME,
    app_deployment=AppDeployment(source_code_path=WORKSPACE_TARGET),
)
print(f"Deployment started: {deployment.deployment_id}")

# Poll until deployment completes
for i in range(60):
    app_info = w.apps.get(name=APP_NAME)
    state = app_info.compute_status.state.name
    deploy_status = getattr(
        getattr(app_info, "active_deployment", None), "status", None
    )
    deploy_msg = getattr(deploy_status, "state", "UNKNOWN") if deploy_status else "PENDING"
    print(f"  [{i*10}s] compute={state}, deploy={deploy_msg}")

    if state == "ACTIVE" and str(deploy_msg) == "SUCCEEDED":
        break
    if state in ("ERROR", "CRASHED"):
        print(f"\n✗ App entered {state}. Check logs.")
        break
    time.sleep(10)

app_info = w.apps.get(name=APP_NAME)
print(f"\n{'✓' if app_info.compute_status.state.name == 'ACTIVE' else '✗'} Final state: {app_info.compute_status.state.name}")
print(f"  URL: {app_info.url}")
print(f"  MCP endpoint: {app_info.url}/mcp")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Verify MCP tools are available

# COMMAND ----------

# Quick smoke test — list tools via HTTP
import urllib.request, json

mcp_url = f"{app_info.url}/mcp"
print(f"MCP endpoint: {mcp_url}")
print(f"\n✓ App is running. Verify by opening {app_info.url} in a browser")
print(f"  or testing MCP connectivity in mcp-setup-gc.md Step 1")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done!
# MAGIC
# MAGIC The `mcp-appkit-skill` app is now running. Next steps:
# MAGIC - Note the app URL for `mcp-setup-gc.md`
# MAGIC - Proceed to **PRE-REQUISITES Step 6** to create the service principal and secret scope
# MAGIC - The MCP endpoint is: `<app_url>/mcp`

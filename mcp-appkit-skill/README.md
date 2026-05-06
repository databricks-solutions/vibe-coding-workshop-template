# MCP AppKit Skill

A lightweight Databricks App that exposes 11 MCP tools for scaffolding, deploying, and extending AppKit applications — used by the Vibe Coding Workshop (Genie Code track).

## Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `appkit_scaffold_app` | Create a new AppKit app scaffold |
| 2 | `appkit_add_lakebase` | Add Lakebase plugin + .then() pattern |
| 3 | `appkit_add_genie_panel` | Add Genie conversational panel |
| 4 | `appkit_deploy` | Deploy an AppKit app |
| 5 | `appkit_add_analytics` | Add SQL Warehouse analytics plugin |
| 6 | `appkit_add_files_browser` | Add UC Volumes file browser |
| 7 | `appkit_validate` | Validate app structure before deploy |
| 8 | `appkit_list_apps` | List all apps in the workspace |
| 9 | `appkit_get_app_status` | Detailed app + deployment info |
| 10 | `appkit_provision_lakebase` | Create Lakebase instance + bind resource |
| 11 | `appkit_manage_app_resources` | Add/update app resource bindings |

## Deploy

### Option A: Run the deploy notebook

1. Upload this folder to your Databricks workspace
2. Open `deploy_mcp_app` notebook
3. Run all cells

### Option B: CLI

```bash
databricks apps create mcp-appkit-skill
databricks apps deploy mcp-appkit-skill --source-code-path /Workspace/Shared/mcp-appkit-skill
```

## Files

```
mcp-appkit-skill/
├── app.yaml              # Uvicorn startup command
├── requirements.txt      # mcp, uvicorn, databricks-sdk
├── server/
│   ├── __init__.py
│   └── main.py           # MCP server with 11 tools
├── deploy_mcp_app.py     # Admin deploy notebook
└── README.md
```

# server/main.py
from __future__ import annotations

import base64
import json
import traceback
from typing import Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, Language
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Plugin metadata: imports, plugin calls, env vars, and extra dependencies
# ---------------------------------------------------------------------------
PLUGIN_REGISTRY: dict[str, dict] = {
    "analytics": {
        "import": "analytics",
        "call": "analytics()",
        "comment": "SQL Warehouse analytics",
        "env": [{"name": "DATABRICKS_WAREHOUSE_ID", "valueFrom": "sql-warehouse"}],
        "deps": {},
    },
    "genie": {
        "import": "genie",
        "call": "genie()",
        "comment": "Genie conversational analytics",
        "env": [{"name": "DATABRICKS_GENIE_SPACE_ID", "valueFrom": "genie-space"}],
        "deps": {},
    },
    "lakebase": {
        "import": "lakebase",
        "call": "lakebase()",
        "comment": "Lakebase Postgres OLTP",
        "env": [
            {"name": "LAKEBASE_ENDPOINT", "valueFrom": "postgres"},
            {"name": "DB_SCHEMA", "value": "app"},
        ],
        "deps": {"@databricks/lakebase": "latest"},
    },
    "files": {
        "import": "files",
        "call": "files()",
        "comment": "UC Volumes file browser",
        "env": [],
        "deps": {},
    },
    "server": {
        "import": "server",
        "call": "server()",
        "comment": "Express server + static file serving",
        "env": [],
        "deps": {},
    },
}

ALL_PLUGINS = list(PLUGIN_REGISTRY.keys())

# ---------------------------------------------------------------------------
# Template: server/server.ts with Lakebase + Express routes (correct pattern)
# ---------------------------------------------------------------------------
LAKEBASE_SERVER_TS = """\
// server/server.ts — Express API routes using appkit.lakebase.query()
// Exported as registerRoutes() and called from app.ts after createApp resolves.

const DB_SCHEMA = process.env.DB_SCHEMA || "app";

export async function registerRoutes(appkit: any) {
  // DDL — create schema and tables on first startup
  try {
    await appkit.lakebase.query(`CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA}`);

    await appkit.lakebase.query(`
      CREATE TABLE IF NOT EXISTS ${DB_SCHEMA}.items (
        id bigint generated always as identity primary key,
        name text not null,
        value text,
        created_at timestamptz default now()
      )
    `);

    console.log("[Lakebase] DDL complete");
  } catch (err) {
    console.warn("[Lakebase] DDL failed (routes will still register):", err);
  }

  // Register API routes
  appkit.server.extend((app: any) => {
    // JSON body parser
    app.use((req: any, _res: any, next: any) => {
      if (req.headers["content-type"]?.includes("application/json") && !req.body) {
        let raw = "";
        req.on("data", (chunk: any) => { raw += chunk; });
        req.on("end", () => {
          try { req.body = JSON.parse(raw); } catch { req.body = {}; }
          next();
        });
      } else { next(); }
    });

    app.get("/api/health", async (_req: any, res: any) => {
      try {
        await appkit.lakebase.query("SELECT 1");
        res.json({ data: [{ status: "connected" }], source: "live" });
      } catch (err) {
        res.json({ data: [{ status: "disconnected", error: String(err) }], source: "mock" });
      }
    });

    app.get("/api/items", async (_req: any, res: any) => {
      try {
        const result = await appkit.lakebase.query(
          `SELECT * FROM ${DB_SCHEMA}.items ORDER BY id`
        );
        res.json({ data: result.rows, source: "live" });
      } catch (err) {
        res.json({ data: [], source: "mock", error: String(err) });
      }
    });

    app.post("/api/items", async (req: any, res: any) => {
      try {
        const { name, value } = req.body;
        const result = await appkit.lakebase.query(
          `INSERT INTO ${DB_SCHEMA}.items (name, value) VALUES ($1, $2) RETURNING *`,
          [name, value ?? null]
        );
        res.json({ data: result.rows, source: "live" });
      } catch (err) {
        res.json({ data: [], source: "mock", error: String(err) });
      }
    });
  });
}
"""

# ---------------------------------------------------------------------------
# Template: React component for Genie chat (uses GenieChat from appkit-ui)
# ---------------------------------------------------------------------------
GENIE_PANEL_TSX = """\
import React from "react";
import {{ GenieChat }} from "@databricks/appkit-ui/react";

interface AskGeniePanelProps {{
  title?: string;
}}

export function AskGeniePanel({{ title = "{panel_title}" }}: AskGeniePanelProps) {{
  return (
    <div style={{ {{ padding: 24 }} }}>
      <h2>{{title}}</h2>
      <GenieChat alias="default" />
    </div>
  );
}}
"""

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "appkit-mcp-skill",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)

w = WorkspaceClient()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_app_ts(plugins: list[str]) -> str:
    """Generate app.ts content.

    When lakebase is included, uses the .then() pattern with autoStart: false
    to allow custom Express routes via appkit.server.extend().
    When lakebase is not included, uses the simpler export default pattern.
    """
    has_lakebase = "lakebase" in plugins

    if has_lakebase:
        ordered = []
        for p in plugins:
            if p != "server":
                ordered.append(p)
        ordered.append("server")

        imports = ", ".join(PLUGIN_REGISTRY[p]["import"] for p in ordered)
        plugin_lines = []
        for p in ordered:
            call = PLUGIN_REGISTRY[p]["call"]
            if p == "server":
                call = 'server({ autoStart: false })'
            plugin_lines.append(f'    {call},  // {PLUGIN_REGISTRY[p]["comment"]}')

        return (
            f'import {{ createApp, {imports} }} from "@databricks/appkit";\n'
            'import { registerRoutes } from "./server/server.js";\n'
            "\n"
            "createApp({\n"
            "  plugins: [\n"
            + "\n".join(plugin_lines) + "\n"
            "  ],\n"
            "}).then(async (appkit) => {\n"
            "  await registerRoutes(appkit);\n"
            "  await appkit.server.start();\n"
            "});\n"
        )
    else:
        imports = ", ".join(PLUGIN_REGISTRY[p]["import"] for p in plugins)
        plugin_lines = "\n".join(
            f'    {PLUGIN_REGISTRY[p]["call"]},  // {PLUGIN_REGISTRY[p]["comment"]}'
            for p in plugins
        )
        return (
            f'import {{ createApp, {imports} }} from "@databricks/appkit";\n'
            "\n"
            "export default createApp({\n"
            "  plugins: [\n"
            f"{plugin_lines}\n"
            "  ],\n"
            "});\n"
        )


def _build_app_yaml(app_name: str, plugins: list[str]) -> str:
    lines = [
        "command:",
        '  - "npx"',
        '  - "@databricks/appkit"',
        '  - "start"',
        "",
        "port: 8000",
    ]
    env_entries = []
    for p in plugins:
        for e in PLUGIN_REGISTRY[p]["env"]:
            env_entries.append(e)
    if env_entries:
        lines.append("")
        lines.append("env:")
        for e in env_entries:
            lines.append(f'  - name: {e["name"]}')
            if "valueFrom" in e:
                lines.append(f'    valueFrom: {e["valueFrom"]}')
            elif "value" in e:
                lines.append(f'    value: "{e["value"]}"')
    return "\n".join(lines) + "\n"


def _build_package_json(app_name: str, plugins: list[str]) -> str:
    deps: dict[str, str] = {"@databricks/appkit": "latest"}
    for p in plugins:
        deps.update(PLUGIN_REGISTRY[p]["deps"])
    build_script = "(npm run typegen || true) && vite build"
    pkg = {
        "name": app_name,
        "private": True,
        "scripts": {
            "dev": "npx @databricks/appkit dev",
            "build": build_script,
            "typegen": "npm exec @databricks/appkit -- generate-types",
        },
        "dependencies": deps,
    }
    return json.dumps(pkg, indent=2) + "\n"


def _push_files_to_workspace(
    files: list[dict], workspace_path: str
) -> list[str]:
    """Upload a list of {path, contents} dicts to a workspace directory."""
    results = []
    for f in files:
        full_path = f"{workspace_path}/{f['path']}"
        content_bytes = f["contents"].encode("utf-8")
        w.workspace.import_(
            path=full_path,
            content=base64.b64encode(content_bytes).decode("ascii"),
            format=ImportFormat.AUTO,
            overwrite=True,
        )
        results.append(full_path)
    return results


# ---------------------------------------------------------------------------
# Tool 1: appkit_scaffold_app
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_scaffold_app(
    app_name: str,
    description: str,
    plugins: Optional[list[str]] = None,
    workspace_path: Optional[str] = None,
) -> dict:
    """
    Create a new AppKit app scaffold with app.ts, app.yaml, and package.json.

    app_name:       Databricks App name (<=26 chars, lowercase/hyphens).
    description:    What the app does — used in the README.
    plugins:        Optional list of plugins to wire. Choose from:
                    analytics, genie, lakebase, files, serving,
                    vectorSearch, server.
                    Defaults to ["server"] if omitted.
    workspace_path: Optional workspace path (e.g. /Workspace/Users/me/my-app).
                    If provided the files are uploaded there automatically.
    """
    selected = plugins if plugins else ["server"]
    if "server" not in selected:
        selected.append("server")
    invalid = [p for p in selected if p not in PLUGIN_REGISTRY]
    if invalid:
        return {"error": f"Unknown plugins: {invalid}. Choose from {list(PLUGIN_REGISTRY.keys())}"}

    app_ts = _build_app_ts(selected)
    app_yaml = _build_app_yaml(app_name, selected)
    package_json = _build_package_json(app_name, selected)
    readme = (
        f"# {app_name}\n\n"
        f"{description}\n\n"
        f"## Plugins\n\n"
        + "\n".join(f"- **{p}**: {PLUGIN_REGISTRY[p]['comment']}" for p in selected)
        + "\n\n"
        "## Getting started\n\n"
        "```bash\nnpm install\nnpm run dev\n```\n"
    )

    file_list = [
        {"path": "app.ts", "contents": app_ts},
        {"path": "app.yaml", "contents": app_yaml},
        {"path": "package.json", "contents": package_json},
        {"path": "README.md", "contents": readme},
    ]

    if "lakebase" in selected:
        file_list.append({"path": "server/server.ts", "contents": LAKEBASE_SERVER_TS})

    result: dict = {
        "app_name": app_name,
        "plugins": selected,
        "files": file_list,
    }

    if workspace_path:
        uploaded = _push_files_to_workspace(file_list, workspace_path)
        result["uploaded_to"] = uploaded

    return result


# ---------------------------------------------------------------------------
# Tool 2: appkit_add_lakebase
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_add_lakebase(
    app_name: str,
    lakebase_instance_name: Optional[str] = None,
) -> dict:
    """
    Add Lakebase (Postgres OLTP) resource and boilerplate to an AppKit app.

    Returns file snippets to merge into your project. The app.ts uses the
    .then() pattern with server({ autoStart: false }) so custom Express
    routes can be registered via appkit.server.extend().

    app_name:               The Databricks App name.
    lakebase_instance_name: Optional Lakebase instance name (defaults to app_name).
    """
    instance = lakebase_instance_name or app_name

    app_yaml_patch = (
        "# Add/merge into the env: section of your app.yaml\n"
        "env:\n"
        "  - name: LAKEBASE_ENDPOINT\n"
        "    valueFrom: postgres\n"
        "  - name: DB_SCHEMA\n"
        f'    value: "{app_name.replace("-", "_")}"\n'
    )

    app_ts_patch = (
        '// Replace your app.ts with this pattern for Lakebase + custom routes:\n'
        'import { createApp, lakebase, server } from "@databricks/appkit";\n'
        'import { registerRoutes } from "./server/server.js";\n'
        "\n"
        "createApp({\n"
        "  plugins: [\n"
        "    lakebase(),  // Lakebase Postgres OLTP\n"
        "    server({ autoStart: false }),  // Express server (manual start after routes)\n"
        "  ],\n"
        "}).then(async (appkit) => {\n"
        "  await registerRoutes(appkit);\n"
        "  await appkit.server.start();\n"
        "});\n"
    )

    return {
        "files": [
            {"path": "server/server.ts", "contents": LAKEBASE_SERVER_TS},
            {"path": "app.yaml (patch)", "contents": app_yaml_patch},
            {"path": "app.ts (replace)", "contents": app_ts_patch},
        ],
        "extra_dependencies": {"@databricks/lakebase": "latest"},
        "notes": (
            "IMPORTANT — Lakebase routing pattern:\n"
            "  - app.ts uses createApp({...}).then() — NO top-level await (CJS constraint).\n"
            "  - server({ autoStart: false }) so routes register before server starts.\n"
            "  - server/server.ts exports registerRoutes(appkit) using appkit.server.extend().\n"
            "  - Lakebase queries use appkit.lakebase.query(sql, params) — NOT getPool().\n"
            "  - Health endpoint returns { data: [{ status }], source } to match useLakebaseData hook.\n"
            "\n"
            f"1. Bind a postgres resource to the app (SDK or CLI) for instance '{instance}'.\n"
            "2. Merge the app.yaml env entries (LAKEBASE_ENDPOINT + DB_SCHEMA).\n"
            "3. Replace app.ts with the .then() pattern.\n"
            "4. Drop server/server.ts and install deps: npm install @databricks/lakebase"
        ),
    }


# ---------------------------------------------------------------------------
# Tool 3: appkit_add_genie_panel
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_add_genie_panel(
    genie_space_id: str,
    panel_title: Optional[str] = None,
) -> dict:
    """
    Scaffold an 'Ask Genie' panel wired to a Genie space.

    Returns a React component using GenieChat from @databricks/appkit-ui,
    an app.yaml env patch, and app.ts patch.

    genie_space_id: The Genie Space ID to wire the panel to.
    panel_title:    Display title for the panel (default: "Ask Genie").
    """
    title = panel_title or "Ask Genie"

    component = GENIE_PANEL_TSX.format(panel_title=title)

    app_yaml_patch = (
        "# Add to the env: section of your app.yaml\n"
        "env:\n"
        "  - name: DATABRICKS_GENIE_SPACE_ID\n"
        "    valueFrom: genie-space\n"
    )

    app_ts_patch = (
        '// Add genie import and plugin:\n'
        'import { createApp, genie /* ...other plugins */ } from "@databricks/appkit";\n'
        "\n"
        "export default createApp({\n"
        "  plugins: [\n"
        "    genie(),  // Genie conversational analytics\n"
        "    // ... your other plugins\n"
        "  ],\n"
        "});\n"
    )

    return {
        "genie_space_id": genie_space_id,
        "files": [
            {
                "path": "client/src/components/AskGeniePanel.tsx",
                "contents": component,
            },
            {"path": "app.yaml (patch)", "contents": app_yaml_patch},
            {"path": "app.ts (patch)", "contents": app_ts_patch},
        ],
        "usage": (
            "Import the component in your page:\n"
            '  import { AskGeniePanel } from "./components/AskGeniePanel";\n'
            "  <AskGeniePanel />\n"
        ),
        "notes": (
            "1. Bind a genie-space resource to the app via SDK or CLI.\n"
            "2. Add genie() to your app.ts plugins.\n"
            "3. Import the AskGeniePanel component in your page."
        ),
    }


# ---------------------------------------------------------------------------
# Tool 4: appkit_deploy
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_deploy(
    app_name: str,
    source_code_path: str,
) -> dict:
    """
    Deploy a Databricks App from a workspace source path.

    Creates the app if it doesn't exist, then triggers a deployment.

    app_name:         Databricks App name (<=26 chars, lowercase/hyphens).
    source_code_path: Workspace path with the app source code,
                      e.g. /Workspace/Users/me@company.com/my-app.
    """
    try:
        w.apps.create(name=app_name)
    except Exception:
        pass

    deployment = w.apps.deploy(
        app_name=app_name,
        source_code_path=source_code_path,
    )

    app_info = w.apps.get(name=app_name)
    url = getattr(app_info, "url", None) or f"(pending — check Apps UI for {app_name})"

    return {
        "message": f"Deployment triggered for {app_name}",
        "app_name": app_name,
        "source_code_path": source_code_path,
        "deployment_id": getattr(deployment, "deployment_id", None),
        "app_url": url,
    }


# ---------------------------------------------------------------------------
# Tool 5: appkit_add_analytics
# ---------------------------------------------------------------------------
CHART_COMPONENTS = {
    "bar": "BarChart",
    "line": "LineChart",
    "area": "AreaChart",
    "pie": "PieChart",
    "donut": "DonutChart",
    "scatter": "ScatterChart",
    "heatmap": "HeatmapChart",
    "table": "DataTable",
}


@mcp.tool()
async def appkit_add_analytics(
    query_name: str,
    sql: str,
    chart_type: Optional[str] = None,
    x_key: Optional[str] = None,
    y_key: Optional[str] = None,
) -> dict:
    """
    Add a SQL analytics query and matching visualization component to an AppKit app.

    Creates a .sql file for config/queries/ and a React component that renders
    the results using the chosen chart type from @databricks/appkit-ui.

    query_name: Name for the query (becomes the filename and queryKey),
                e.g. "sales_by_region".
    sql:        The Databricks SQL query text (Spark SQL dialect).
    chart_type: Visualization type: bar, line, area, pie, donut, scatter,
                heatmap, or table. Defaults to "bar".
    x_key:      Column name for the X axis (auto-detected if omitted).
    y_key:      Column name for the Y axis (auto-detected if omitted).
    """
    chart = chart_type or "bar"
    if chart not in CHART_COMPONENTS:
        return {
            "error": f"Unknown chart_type '{chart}'. Choose from: {list(CHART_COMPONENTS.keys())}"
        }

    component_name = CHART_COMPONENTS[chart]
    query_file = f"config/queries/{query_name}.sql"

    props = [f'queryKey="{query_name}"', "parameters={{}}"]
    if x_key:
        props.append(f'xKey="{x_key}"')
    if y_key:
        props.append(f'yKey="{y_key}"')
    props_str = " ".join(props)

    component_tsx = (
        f'import {{ {component_name} }} from "@databricks/appkit-ui/react";\n'
        "\n"
        f"export function {query_name.title().replace('_', '')}Chart() {{\n"
        "  return (\n"
        f"    <{component_name} {props_str} />\n"
        "  );\n"
        "}\n"
    )

    app_yaml_patch = (
        "# Add to the env: section of your app.yaml\n"
        "env:\n"
        "  - name: DATABRICKS_WAREHOUSE_ID\n"
        "    valueFrom: sql-warehouse\n"
    )

    app_ts_patch = (
        '// Add analytics import and plugin:\n'
        'import { createApp, analytics /* ...other plugins */ } from "@databricks/appkit";\n'
        "\n"
        "export default createApp({\n"
        "  plugins: [\n"
        "    analytics(),  // SQL Warehouse analytics\n"
        "    // ... your other plugins\n"
        "  ],\n"
        "});\n"
    )

    return {
        "query_name": query_name,
        "chart_type": chart,
        "files": [
            {"path": query_file, "contents": sql},
            {
                "path": f"client/src/components/{query_name.title().replace('_', '')}Chart.tsx",
                "contents": component_tsx,
            },
            {"path": "app.yaml (patch)", "contents": app_yaml_patch},
            {"path": "app.ts (patch)", "contents": app_ts_patch},
        ],
        "notes": (
            "1. Place the .sql file in config/queries/.\n"
            "2. Run `npm run typegen` to generate types.\n"
            "3. Import the chart component in your App.tsx.\n"
            "4. Ensure analytics() is in your app.ts plugins and the warehouse env is set."
        ),
    }


# ---------------------------------------------------------------------------
# Tool 6: appkit_add_files_browser
# ---------------------------------------------------------------------------
FILES_BROWSER_TSX = """\
import React from "react";
import { DirectoryList } from "@databricks/appkit-ui/react";

export function FilesBrowser() {
  return (
    <div style={{ padding: 24 }}>
      <h2>Files</h2>
      <DirectoryList />
    </div>
  );
}
"""


@mcp.tool()
async def appkit_add_files_browser() -> dict:
    """
    Scaffold a UC Volumes file browser panel for an AppKit app.

    Returns a React component using DirectoryList from @databricks/appkit-ui
    and the app.ts patch to wire in the files() plugin.
    """
    app_ts_patch = (
        '// Add files import and plugin:\n'
        'import { createApp, files /* ...other plugins */ } from "@databricks/appkit";\n'
        "\n"
        "export default createApp({\n"
        "  plugins: [\n"
        "    files(),  // UC Volumes file browser\n"
        "    // ... your other plugins\n"
        "  ],\n"
        "});\n"
    )

    return {
        "files": [
            {"path": "client/src/components/FilesBrowser.tsx", "contents": FILES_BROWSER_TSX},
            {"path": "app.ts (patch)", "contents": app_ts_patch},
        ],
        "usage": (
            "Import the component in your page:\n"
            '  import { FilesBrowser } from "./components/FilesBrowser";\n'
            "  <FilesBrowser />\n"
        ),
        "notes": (
            "1. Add files() to your app.ts plugins array.\n"
            "2. Import the FilesBrowser component in your page.\n"
            "3. Configure volumes in the files() plugin config if needed."
        ),
    }


# ---------------------------------------------------------------------------
# Tool 7: appkit_validate
# ---------------------------------------------------------------------------
def _check_workspace_path(path: str) -> str:
    try:
        w.workspace.get_status(path)
        return "ok"
    except Exception as exc:
        err = str(exc).lower()
        if "403" in err or "permission" in err or "forbidden" in err or "access" in err:
            return "permission_denied"
        return "not_found"


@mcp.tool()
async def appkit_validate(
    app_name: str,
    source_code_path: str,
) -> dict:
    """
    Validate an AppKit app before deployment.

    Checks that the source code at the given workspace path has a valid
    app.yaml and required structure.

    app_name:         Databricks App name.
    source_code_path: Workspace path with the app source,
                      e.g. /Workspace/Users/me@company.com/my-app.
    """
    issues: list[str] = []
    checked: list[str] = []
    warnings: list[str] = []
    has_perm_issue = False

    for filename in ["app.yaml", "package.json"]:
        result = _check_workspace_path(f"{source_code_path}/{filename}")
        if result == "ok":
            checked.append(f"{filename} exists")
        elif result == "permission_denied":
            has_perm_issue = True
            warnings.append(
                f"{filename} — SP cannot read this path (permission denied). "
                "Grant CAN_READ on the workspace folder or verify via your own SDK session."
            )
        else:
            issues.append(f"{filename} not found at source_code_path")

    for sub in ["client", "server", "config"]:
        result = _check_workspace_path(f"{source_code_path}/{sub}")
        if result == "ok":
            checked.append(f"{sub}/ directory exists")
        elif result == "permission_denied":
            has_perm_issue = True

    try:
        app_info = w.apps.get(name=app_name)
        checked.append(f"App '{app_name}' exists in workspace")
        url = getattr(app_info, "url", None)
    except Exception:
        issues.append(f"App '{app_name}' does not exist yet — will be created on first deploy")
        url = None

    valid = len(issues) == 0 and not has_perm_issue

    resp: dict = {
        "app_name": app_name,
        "source_code_path": source_code_path,
        "valid": valid if not has_perm_issue else "unknown (permission issue)",
        "checks_passed": checked,
        "issues": issues,
        "app_url": url,
    }
    if warnings:
        resp["warnings"] = warnings
        resp["fix"] = (
            "Grant the MCP app's service principal CAN_READ on the repo/folder, "
            "or skip validation and proceed to deploy."
        )
    return resp


# ---------------------------------------------------------------------------
# Tool 11: appkit_list_apps
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_list_apps() -> dict:
    """
    List all Databricks Apps in the workspace with their status, URLs,
    and compute state.
    """
    apps_list = []
    for a in w.apps.list():
        apps_list.append({
            "name": getattr(a, "name", None),
            "url": getattr(a, "url", None),
            "compute_status": getattr(a, "compute_status", None),
            "active_deployment": getattr(
                getattr(a, "active_deployment", None), "status", None
            ),
            "creator": getattr(a, "creator", None),
        })

    return {
        "total": len(apps_list),
        "apps": apps_list,
    }


# ---------------------------------------------------------------------------
# Tool 12: appkit_get_app_status (NEW)
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_get_app_status(app_name: str) -> dict:
    """
    Get detailed status of a Databricks App including compute state,
    active deployment, resources, service principal, and URL.

    app_name: Databricks App name.
    """
    try:
        app_info = w.apps.get(name=app_name)
    except Exception as exc:
        return {"error": f"App '{app_name}' not found: {exc}"}

    deployments = []
    try:
        for d in w.apps.list_deployments(app_name=app_name):
            dep_status = getattr(d, "status", None)
            deployments.append({
                "deployment_id": getattr(d, "deployment_id", None),
                "state": getattr(dep_status, "state", None),
                "message": getattr(dep_status, "message", None),
                "source_code_path": getattr(d, "source_code_path", None),
            })
            if len(deployments) >= 5:
                break
    except Exception:
        pass

    resources = []
    for r in (getattr(app_info, "resources", None) or []):
        rd = r.as_dict() if hasattr(r, "as_dict") else {"name": getattr(r, "name", "?")}
        resources.append(rd)

    compute = getattr(app_info, "compute_status", None)
    sp = getattr(app_info, "service_principal_client_id", None) or getattr(app_info, "effective_service_principal_client_id", None)

    return {
        "app_name": app_name,
        "url": getattr(app_info, "url", None),
        "compute_state": getattr(compute, "state", None) if compute else None,
        "service_principal_client_id": sp,
        "resources": resources,
        "recent_deployments": deployments,
    }


# ---------------------------------------------------------------------------
# Tool 13: appkit_provision_lakebase (NEW)
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_provision_lakebase(
    app_name: str,
    db_schema: Optional[str] = None,
) -> dict:
    """
    Provision a Lakebase instance for an app and bind it as a postgres resource.

    Creates the Lakebase instance (if it doesn't exist), discovers the database
    path, and binds a postgres-type resource to the app.

    app_name:  Databricks App name (also used as the Lakebase instance name).
    db_schema: Schema name for the app's tables. Defaults to app_name with
               hyphens replaced by underscores.
    """
    schema = db_schema or app_name.replace("-", "_")

    # Step 1: Create Lakebase instance
    instance = None
    try:
        instance = w.database.get_database_instance(name=app_name)
        state = getattr(instance, "state", None)
        result_msg = f"Lakebase instance '{app_name}' already exists (state: {state})"
    except Exception:
        try:
            instance = w.database.create_database_instance(name=app_name)
            result_msg = f"Lakebase instance '{app_name}' creation initiated"
        except Exception as exc:
            return {"error": f"Failed to create Lakebase instance: {exc}"}

    # Step 2: Discover branch and database paths
    branch_path = f"projects/{app_name}/branches/production"
    db_path = None
    try:
        dbs = list(w.database.list_databases(parent=branch_path))
        if dbs:
            db_path = dbs[0].name
    except Exception:
        pass

    # Step 3: Bind postgres resource to the app
    resource_bound = False
    try:
        from databricks.sdk.service.apps import (
            App, AppResource, AppResourcePostgres,
            AppResourcePostgresPostgresPermission,
        )
        w.apps.update(
            name=app_name,
            app=App(
                name=app_name,
                resources=[
                    AppResource(
                        name="postgres",
                        postgres=AppResourcePostgres(
                            branch=branch_path,
                            database=db_path or "",
                            permission=AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE,
                        ),
                    )
                ],
            ),
        )
        resource_bound = True
    except ImportError:
        resource_bound = False
    except Exception as exc:
        return {
            "instance": result_msg,
            "branch_path": branch_path,
            "database_path": db_path,
            "resource_bound": False,
            "error": f"Instance created but resource binding failed: {exc}",
            "fix": (
                "Ensure databricks-sdk >= 0.105.0 for AppResourcePostgres support. "
                "Run: pip install --upgrade databricks-sdk"
            ),
        }

    return {
        "instance": result_msg,
        "branch_path": branch_path,
        "database_path": db_path,
        "db_schema": schema,
        "resource_bound": resource_bound,
        "app_yaml_env": (
            "env:\n"
            "  - name: LAKEBASE_ENDPOINT\n"
            "    valueFrom: postgres\n"
            "  - name: DB_SCHEMA\n"
            f'    value: "{schema}"\n'
        ),
    }


# ---------------------------------------------------------------------------
# Tool 15: appkit_manage_app_resources (NEW)
# ---------------------------------------------------------------------------
@mcp.tool()
async def appkit_manage_app_resources(
    app_name: str,
    resource_type: str,
    resource_name: str,
    config: Optional[dict] = None,
) -> dict:
    """
    Add or update a resource binding on a Databricks App.

    Supports resource types: postgres, secret, sql-warehouse, serving-endpoint.

    app_name:      Databricks App name.
    resource_type: One of: postgres, secret, sql-warehouse, serving-endpoint.
    resource_name: Name for the resource binding (used in app.yaml valueFrom).
    config:        Optional config dict. Keys depend on type:
                   - postgres: { branch, database, permission }
                   - secret: { scope, key, permission }
                   - sql-warehouse: { id, permission }
                   - serving-endpoint: { name, permission }
    """
    from databricks.sdk.service.apps import App, AppResource

    cfg = config or {}

    try:
        if resource_type == "postgres":
            from databricks.sdk.service.apps import (
                AppResourcePostgres, AppResourcePostgresPostgresPermission,
            )
            resource = AppResource(
                name=resource_name,
                postgres=AppResourcePostgres(
                    branch=cfg.get("branch", ""),
                    database=cfg.get("database", ""),
                    permission=AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE,
                ),
            )
        elif resource_type == "secret":
            from databricks.sdk.service.apps import (
                AppResourceSecret, AppResourceSecretSecretPermission,
            )
            resource = AppResource(
                name=resource_name,
                secret=AppResourceSecret(
                    scope=cfg.get("scope", ""),
                    key=cfg.get("key", ""),
                    permission=getattr(
                        AppResourceSecretSecretPermission,
                        cfg.get("permission", "READ"),
                        AppResourceSecretSecretPermission.READ,
                    ),
                ),
            )
        elif resource_type == "sql-warehouse":
            from databricks.sdk.service.apps import (
                AppResourceSqlWarehouse, AppResourceSqlWarehouseSqlWarehousePermission,
            )
            resource = AppResource(
                name=resource_name,
                sql_warehouse=AppResourceSqlWarehouse(
                    id=cfg.get("id", ""),
                    permission=AppResourceSqlWarehouseSqlWarehousePermission.CAN_USE,
                ),
            )
        elif resource_type == "serving-endpoint":
            from databricks.sdk.service.apps import (
                AppResourceServingEndpoint, AppResourceServingEndpointServingEndpointPermission,
            )
            resource = AppResource(
                name=resource_name,
                serving_endpoint=AppResourceServingEndpoint(
                    name=cfg.get("name", ""),
                    permission=AppResourceServingEndpointServingEndpointPermission.CAN_QUERY,
                ),
            )
        else:
            return {"error": f"Unknown resource_type '{resource_type}'. Choose from: postgres, secret, sql-warehouse, serving-endpoint"}

        # Get existing resources and merge
        app_info = w.apps.get(name=app_name)
        existing = list(getattr(app_info, "resources", None) or [])
        existing = [r for r in existing if getattr(r, "name", None) != resource_name]
        existing.append(resource)

        w.apps.update(name=app_name, app=App(name=app_name, resources=existing))

        return {
            "app_name": app_name,
            "resource_name": resource_name,
            "resource_type": resource_type,
            "status": "bound",
            "total_resources": len(existing),
        }
    except Exception as exc:
        return {
            "error": f"Failed to bind resource: {exc}",
            "traceback": traceback.format_exc(),
        }


# ---------------------------------------------------------------------------
# ASGI app
# ---------------------------------------------------------------------------
app = mcp.streamable_http_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

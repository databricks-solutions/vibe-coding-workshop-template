"""
Dashboard Deployment Script
Deploys Databricks AI/BI dashboards using the UPDATE-or-CREATE pattern with
variable substitution.

Critical rules enforced here (see
`data_product_accelerator/skills/monitoring/02-databricks-aibi-dashboards/SKILL.md`):

1.  ``ws.workspace.import_`` expects the ``content`` field to be a **base64-encoded
    ASCII string**, NOT raw UTF-8 bytes. Passing bytes silently produces a
    corrupt ``.lvdash.json`` file in the workspace — the file shows up, but
    fails to open in the AI/BI editor with a generic parse error.

2.  Pre-loop variable enumeration: scan every dashboard JSON for ``${...}``
    placeholders BEFORE the deploy loop starts, then fail loud if any
    placeholder lacks a value. Catching this up-front is ~20× cheaper than
    a mid-loop failure that leaves some dashboards deployed and others not.

3.  Fail loud — never ``sys.exit(0)`` on failure. Raise ``RuntimeError`` so
    Jobs marks the run as FAILED and the traceback is visible.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path
from typing import Iterable

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat


# Matches ${identifier} — standard shell-style variable reference used in
# dashboard JSON files. Skips `${{...}}` (doubled braces) which are reserved
# for DAB variable syntax.
_VAR_RE = re.compile(r"(?<!\$)\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def substitute_variables(content: str, variables: dict) -> str:
    """Substitute ``${var}`` placeholders in a dashboard JSON string."""
    result = content
    for key, value in variables.items():
        if value is None:
            continue
        result = result.replace(f"${{{key}}}", str(value))
    return result


def enumerate_required_variables(
    dashboard_files: Iterable[Path],
) -> dict[str, list[Path]]:
    """
    Walk every dashboard JSON file and return a map
    ``{variable_name: [files that reference it]}``.

    Use this BEFORE the deploy loop to validate the caller-supplied
    ``variables`` dict covers every placeholder. Missing a variable causes
    ``substitute_variables`` to leave ``${var}`` in the JSON, which in turn
    causes runtime query failures in Databricks that are very hard to
    attribute back to the deploy step.
    """
    seen: dict[str, list[Path]] = {}
    for df in dashboard_files:
        text = df.read_text()
        for name in _VAR_RE.findall(text):
            seen.setdefault(name, []).append(df)
    return seen


def assert_all_variables_provided(
    dashboard_files: Iterable[Path],
    variables: dict,
) -> None:
    """Fail loud if any dashboard references a variable that isn't supplied."""
    required = enumerate_required_variables(dashboard_files)
    missing = {
        name: [str(p) for p in files]
        for name, files in required.items()
        if variables.get(name) in (None, "")
    }
    if missing:
        lines = [
            f"  - ${{{name}}} required by {files}" for name, files in sorted(missing.items())
        ]
        raise RuntimeError(
            "Dashboard deployment pre-flight FAILED — missing variable values:\n"
            + "\n".join(lines)
            + "\n\nAll placeholders must be resolved BEFORE any ws.workspace.import_ "
            "call, otherwise the deployed .lvdash.json files will contain literal "
            "${var} strings that break queries at view time."
        )


def deploy_dashboard(
    workspace_client: WorkspaceClient,
    dashboard_path: Path,
    target_path: str,
    variables: dict,
) -> str:
    """
    Deploy a single dashboard using the UPDATE-or-CREATE pattern.

    Content is base64-encoded per the Workspace Import API contract:
    https://docs.databricks.com/api/workspace/workspace/import

    Returns the target workspace path where the dashboard was deployed.
    """
    dashboard_json = dashboard_path.read_text()
    rendered = substitute_variables(dashboard_json, variables)

    # Defence-in-depth: if any ${var} remains after substitution, something
    # was missed by the pre-loop enumeration. Fail rather than upload garbage.
    leftover = _VAR_RE.findall(rendered)
    if leftover:
        raise RuntimeError(
            f"Unresolved ${{var}} placeholders in {dashboard_path}: "
            f"{sorted(set(leftover))}. Caller must supply every variable "
            "before import_()."
        )

    # The Workspace Import API requires base64-encoded ASCII content.
    # Passing raw UTF-8 bytes silently produces a corrupt .lvdash.json file
    # in the workspace that will not open in the AI/BI editor.
    b64_content = base64.b64encode(rendered.encode("utf-8")).decode("ascii")

    workspace_client.workspace.import_(
        path=target_path,
        content=b64_content,
        format=ImportFormat.AUTO,
        overwrite=True,  # CRITICAL: enables UPDATE-or-CREATE idempotency
    )

    return target_path


def deploy_dashboards(
    workspace_client: WorkspaceClient,
    dashboard_dir: Path,
    catalog: str,
    gold_schema: str,
    warehouse_id: str,
    dashboard_folder: str = "/Shared/dashboards",
    feature_schema: str | None = None,
    extra_variables: dict | None = None,
) -> list[str]:
    """
    Deploy every ``*.lvdash.json`` dashboard in ``dashboard_dir``.

    Pre-flight: enumerates required variables across ALL dashboard files and
    fails loud before touching the workspace if any are missing. This is the
    critical guard that prevents partial deployments.
    """
    variables: dict = {
        "catalog": catalog,
        "gold_schema": gold_schema,
        "warehouse_id": warehouse_id,
    }
    if feature_schema:
        variables["feature_schema"] = feature_schema
    if extra_variables:
        variables.update(extra_variables)

    dashboard_files = sorted(dashboard_dir.glob("*.lvdash.json"))
    if not dashboard_files:
        raise RuntimeError(
            f"No *.lvdash.json dashboards found under {dashboard_dir}. "
            "Refusing to no-op a deploy silently."
        )

    # --- Pre-loop variable enumeration (S3 in retrospective) ---
    print("Pre-flight: enumerating variable references across dashboards…")
    required = enumerate_required_variables(dashboard_files)
    for name, files in sorted(required.items()):
        status = "✓" if variables.get(name) not in (None, "") else "✗ MISSING"
        print(f"  {status}  ${{{name}}}  ({len(files)} file(s))")
    assert_all_variables_provided(dashboard_files, variables)

    # --- Deploy loop (safe to proceed; all variables confirmed) ---
    deployed_paths: list[str] = []
    for dashboard_file in dashboard_files:
        target_path = f"{dashboard_folder}/{dashboard_file.name}"
        deployed_path = deploy_dashboard(
            workspace_client, dashboard_file, target_path, variables
        )
        deployed_paths.append(deployed_path)
        print(f"✅ Deployed: {dashboard_file.name} → {target_path}")

    return deployed_paths


if __name__ == "__main__":
    workspace_client = WorkspaceClient()
    try:
        deploy_dashboards(
            workspace_client=workspace_client,
            dashboard_dir=Path("src/dashboards"),
            catalog="health_monitor",
            gold_schema="system_gold",
            warehouse_id="abc123xyz",
            dashboard_folder="/Shared/dashboards",
        )
    except RuntimeError as e:
        # Non-zero exit for CLI invocation; raise for notebook runs (see SKILL.md).
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

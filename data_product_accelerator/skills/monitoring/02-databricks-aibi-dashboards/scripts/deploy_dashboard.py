"""
Dashboard Deployment Script
Deploys dashboards using UPDATE-or-CREATE pattern with variable substitution.
"""

import json
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat


def substitute_variables(content: str, variables: dict) -> str:
    """Substitute variables in dashboard JSON."""
    result = content
    for key, value in variables.items():
        result = result.replace(f"${{{key}}}", value)
    return result


def deploy_dashboard(
    workspace_client: WorkspaceClient,
    dashboard_path: Path,
    target_path: str,
    variables: dict
) -> str:
    """
    Deploy a single dashboard using UPDATE-or-CREATE pattern.
    
    Args:
        workspace_client: Databricks WorkspaceClient instance
        dashboard_path: Path to dashboard JSON file
        target_path: Target workspace path (e.g., "/Shared/dashboards/cost.lvdash.json")
        variables: Dictionary of variables to substitute (catalog, gold_schema, etc.)
    
    Returns:
        Target path where dashboard was deployed
    """
    # Read dashboard JSON
    with open(dashboard_path) as f:
        dashboard_json = f.read()
    
    # Substitute variables
    dashboard_json = substitute_variables(dashboard_json, variables)
    
    # Import with overwrite (UPDATE-or-CREATE pattern)
    workspace_client.workspace.import_(
        path=target_path,
        content=dashboard_json.encode('utf-8'),
        format=ImportFormat.AUTO,
        overwrite=True  # CRITICAL: Enables UPDATE-or-CREATE
    )
    
    return target_path


def deploy_dashboards(
    workspace_client: WorkspaceClient,
    dashboard_dir: Path,
    catalog: str,
    gold_schema: str,
    warehouse_id: str,
    dashboard_folder: str = "/Shared/dashboards",
    feature_schema: str = None
) -> list[str]:
    """
    Deploy all dashboards in a directory.
    
    Args:
        workspace_client: Databricks WorkspaceClient instance
        dashboard_dir: Directory containing dashboard JSON files
        catalog: Unity Catalog name
        gold_schema: Gold layer schema name
        warehouse_id: SQL Warehouse ID
        dashboard_folder: Target folder in workspace (default: "/Shared/dashboards")
        feature_schema: Optional ML/Feature schema name
    
    Returns:
        List of deployed dashboard paths
    """
    # Build variables dictionary
    variables = {
        'catalog': catalog,
        'gold_schema': gold_schema,
        'warehouse_id': warehouse_id,
    }
    
    if feature_schema:
        variables['feature_schema'] = feature_schema
    
    # Find all dashboard files
    dashboard_files = list(dashboard_dir.glob("*.lvdash.json"))
    
    deployed_paths = []
    for dashboard_file in dashboard_files:
        # Build target path
        target_path = f"{dashboard_folder}/{dashboard_file.name}"
        
        # Deploy dashboard
        deployed_path = deploy_dashboard(
            workspace_client,
            dashboard_file,
            target_path,
            variables
        )
        
        deployed_paths.append(deployed_path)
        print(f"✅ Deployed: {dashboard_file.name} → {target_path}")
    
    return deployed_paths


if __name__ == "__main__":
    from databricks.sdk import WorkspaceClient
    
    # Initialize workspace client
    workspace_client = WorkspaceClient()
    
    # Deploy dashboards
    deploy_dashboards(
        workspace_client=workspace_client,
        dashboard_dir=Path("src/dashboards"),
        catalog="health_monitor",
        gold_schema="system_gold",
        warehouse_id="abc123xyz",
        dashboard_folder="/Shared/dashboards"
    )

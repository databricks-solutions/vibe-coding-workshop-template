"""
Centralized Genie Space configuration template.

Maps domain names to Genie Space IDs for multi-agent orchestration.
"""

from typing import Dict, Optional
from databricks.sdk import WorkspaceClient

# Domain to Genie Space ID mapping
GENIE_SPACE_CONFIG = {
    "billing": {
        "space_id": "YOUR_BILLING_SPACE_ID",
        "description": "Billing and cost analytics Genie Space",
        "data_assets": {
            "metric_views": ["cost_analytics_metrics"],
            "tvfs": ["get_daily_cost_summary", "get_workspace_usage"],
            "tables": ["gold.billing.fact_usage", "gold.billing.dim_sku"]
        }
    },
    "monitoring": {
        "space_id": "YOUR_MONITORING_SPACE_ID",
        "description": "Monitoring and observability Genie Space",
        "data_assets": {
            "metric_views": ["job_performance_metrics", "system_health_metrics"],
            "tvfs": ["get_job_metrics", "get_alert_summary"],
            "tables": ["gold.monitoring.fact_job_runs", "gold.monitoring.dim_alerts"]
        }
    },
    "jobs": {
        "space_id": "YOUR_JOBS_SPACE_ID",
        "description": "Job and workflow management Genie Space",
        "data_assets": {
            "metric_views": ["workflow_execution_metrics"],
            "tvfs": ["get_job_history", "get_workflow_status"],
            "tables": ["gold.jobs.fact_job_executions", "gold.jobs.dim_workflows"]
        }
    },
    "security": {
        "space_id": "YOUR_SECURITY_SPACE_ID",
        "description": "Security and access management Genie Space",
        "data_assets": {
            "metric_views": ["access_metrics"],
            "tvfs": ["get_user_permissions", "get_access_logs"],
            "tables": ["gold.security.fact_access_events", "gold.security.dim_users"]
        }
    },
    "governance": {
        "space_id": "YOUR_GOVERNANCE_SPACE_ID",
        "description": "Data governance and catalog Genie Space",
        "data_assets": {
            "metric_views": ["catalog_metrics"],
            "tvfs": ["get_table_lineage", "get_schema_info"],
            "tables": ["gold.governance.fact_table_usage", "gold.governance.dim_tables"]
        }
    },
}


def get_space_id(domain: str) -> Optional[str]:
    """
    Get Genie Space ID for a domain.
    
    Args:
        domain: Domain name (e.g., "billing", "monitoring")
    
    Returns:
        Genie Space ID or None if domain not found
    """
    domain_config = GENIE_SPACE_CONFIG.get(domain.lower())
    if domain_config:
        return domain_config["space_id"]
    return None


def get_all_domains() -> list[str]:
    """Get list of all configured domains."""
    return list(GENIE_SPACE_CONFIG.keys())


def get_domain_config(domain: str) -> Optional[Dict]:
    """Get full configuration for a domain."""
    return GENIE_SPACE_CONFIG.get(domain.lower())


def validate_space_exists(
    workspace_client: WorkspaceClient,
    domain: str
) -> bool:
    """
    Validate that Genie Space exists and is accessible.
    
    Args:
        workspace_client: Authenticated WorkspaceClient
        domain: Domain name
    
    Returns:
        True if space exists and is accessible
    """
    space_id = get_space_id(domain)
    if not space_id:
        return False
    
    try:
        space = workspace_client.genie.get_space(space_id=space_id)
        return space is not None
    except Exception:
        return False


def get_domain_space_map() -> Dict[str, str]:
    """
    Get mapping of domain names to Space IDs.
    
    Returns:
        {
            "domain_name": "space_id",
            ...
        }
    """
    return {
        domain: config["space_id"]
        for domain, config in GENIE_SPACE_CONFIG.items()
    }


# Example usage
if __name__ == "__main__":
    # Get Space ID for a domain
    billing_space_id = get_space_id("billing")
    print(f"Billing Space ID: {billing_space_id}")
    
    # Get all domains
    domains = get_all_domains()
    print(f"Configured domains: {domains}")
    
    # Get domain-to-space mapping
    domain_map = get_domain_space_map()
    print(f"Domain mapping: {domain_map}")

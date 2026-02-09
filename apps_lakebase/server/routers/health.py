"""
Health Check Router
==================

Provides health check and readiness endpoints for monitoring.
These are essential for Databricks Apps platform to verify your app is running.

Reference: https://github.com/databricks-solutions/claude-databricks-app-template
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str
    environment: str
    timestamp: str


class ReadinessStatus(BaseModel):
    """Readiness check response model."""
    ready: bool
    checks: dict
    timestamp: str


class DatabricksStatus(BaseModel):
    """Databricks connection status."""
    connected: bool
    workspace: Optional[str] = None
    user: Optional[str] = None
    error: Optional[str] = None


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Health check endpoint.
    
    Returns the basic health status of the application.
    Used by Databricks Apps to verify the app is running.
    
    Returns:
        HealthStatus: Health status including service name and version
    """
    return HealthStatus(
        status="healthy",
        service="databricks-app",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check() -> ReadinessStatus:
    """
    Readiness check endpoint.
    
    Verifies the application is ready to handle requests.
    Checks various dependencies like database connections and external services.
    
    Returns:
        ReadinessStatus: Readiness status with individual check results
    """
    checks = {
        "app": "ok",
    }
    
    # Check Databricks SDK availability
    try:
        import databricks.sdk
        checks["databricks_sdk"] = "ok"
    except ImportError:
        checks["databricks_sdk"] = "not_installed"
    
    # Check MLflow availability
    try:
        import mlflow
        checks["mlflow"] = "ok"
    except ImportError:
        checks["mlflow"] = "not_installed"
    
    # Check pandas availability
    try:
        import pandas
        checks["pandas"] = "ok"
    except ImportError:
        checks["pandas"] = "not_installed"
    
    # Determine overall readiness
    all_ok = all(v == "ok" for v in checks.values() if v != "not_installed")
    
    return ReadinessStatus(
        ready=all_ok,
        checks=checks,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/health/databricks", response_model=DatabricksStatus)
async def databricks_connection_check() -> DatabricksStatus:
    """
    Check Databricks workspace connection.
    
    Verifies that the application can connect to the Databricks workspace
    using the configured credentials.
    
    Returns:
        DatabricksStatus: Connection status and workspace details
    """
    try:
        from databricks.sdk import WorkspaceClient
        
        w = WorkspaceClient()
        current_user = w.current_user.me()
        
        return DatabricksStatus(
            connected=True,
            workspace=w.config.host,
            user=current_user.user_name if current_user else None,
        )
    except ImportError:
        return DatabricksStatus(
            connected=False,
            error="databricks-sdk not installed",
        )
    except Exception as e:
        logger.warning(f"Databricks connection check failed: {e}")
        return DatabricksStatus(
            connected=False,
            error=str(e),
        )


@router.get("/health/live")
async def liveness_check() -> dict:
    """
    Simple liveness probe.
    
    Returns 200 OK if the application is alive.
    Used for Kubernetes/container health checks.
    """
    return {"status": "alive"}

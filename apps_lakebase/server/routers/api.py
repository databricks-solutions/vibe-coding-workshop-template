"""
API Router
==========

Main API endpoints for your Databricks App.
Add your custom endpoints here.

Reference: https://github.com/databricks-solutions/claude-databricks-app-template
"""

import os
import logging
from typing import Any, Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for SQL queries."""
    query: str = Field(..., description="SQL query to execute")
    catalog: Optional[str] = Field(None, description="Unity Catalog name")
    schema_name: Optional[str] = Field(None, alias="schema", description="Schema name")
    limit: int = Field(100, ge=1, le=10000, description="Maximum rows to return")


class QueryResponse(BaseModel):
    """Response model for query results."""
    success: bool
    data: List[dict]
    row_count: int
    columns: List[str]


class TableInfo(BaseModel):
    """Information about a table."""
    catalog: str
    schema_name: str = Field(..., alias="schema")
    name: str
    table_type: str
    comment: Optional[str] = None


class WorkspaceInfo(BaseModel):
    """Databricks workspace information."""
    workspace_id: Optional[str] = None
    host: Optional[str] = None
    user: Optional[str] = None
    is_connected: bool


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/info")
async def get_info() -> dict:
    """
    Get application information.
    
    Returns application metadata and configuration.
    """
    return {
        "app": "Databricks App",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "description": "Built with Vibe Coding workshop template",
        "endpoints": {
            "workspace": "/api/workspace",
            "catalogs": "/api/catalogs",
            "tables": "/api/tables/{catalog}/{schema}",
            "query": "/api/query (POST)",
        }
    }


@router.get("/workspace", response_model=WorkspaceInfo)
async def get_workspace_info() -> WorkspaceInfo:
    """
    Get Databricks workspace information.
    
    Returns the current workspace connection status and details.
    Requires Databricks SDK to be properly configured.
    """
    try:
        from databricks.sdk import WorkspaceClient
        
        w = WorkspaceClient()
        current_user = w.current_user.me()
        
        return WorkspaceInfo(
            workspace_id=str(w.config.host).split("//")[1].split(".")[0] if w.config.host else None,
            host=w.config.host,
            user=current_user.user_name if current_user else None,
            is_connected=True,
        )
    except ImportError:
        logger.warning("databricks-sdk not installed")
        return WorkspaceInfo(is_connected=False)
    except Exception as e:
        logger.warning(f"Could not connect to Databricks: {e}")
        return WorkspaceInfo(is_connected=False)


@router.get("/catalogs")
async def list_catalogs() -> dict:
    """
    List all Unity Catalogs accessible to the current user.
    
    Requires Unity Catalog to be enabled in your workspace.
    """
    try:
        from databricks.sdk import WorkspaceClient
        
        w = WorkspaceClient()
        catalogs = list(w.catalogs.list())
        
        return {
            "catalogs": [
                {
                    "name": c.name,
                    "comment": c.comment,
                    "owner": c.owner,
                }
                for c in catalogs
            ],
            "count": len(catalogs),
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="databricks-sdk not installed")
    except Exception as e:
        logger.error(f"Error listing catalogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{catalog}/{schema}")
async def list_tables(
    catalog: str,
    schema: str,
    max_results: int = Query(100, ge=1, le=1000)
) -> dict:
    """
    List tables in a schema.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name within the catalog
        max_results: Maximum number of tables to return
        
    Returns:
        List of tables with metadata
    """
    try:
        from databricks.sdk import WorkspaceClient
        
        w = WorkspaceClient()
        tables = list(w.tables.list(catalog_name=catalog, schema_name=schema))[:max_results]
        
        return {
            "catalog": catalog,
            "schema": schema,
            "tables": [
                {
                    "name": t.name,
                    "table_type": t.table_type.value if t.table_type else None,
                    "comment": t.comment,
                    "created_at": str(t.created_at) if t.created_at else None,
                }
                for t in tables
            ],
            "count": len(tables),
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="databricks-sdk not installed")
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest) -> QueryResponse:
    """
    Execute a SQL query using Databricks SQL.
    
    This endpoint executes queries against your Databricks workspace.
    Results are limited to the specified limit (default 100 rows).
    
    **Note:** For production use, implement proper query validation
    and access controls.
    
    Args:
        request: Query request containing SQL and options
        
    Returns:
        Query results with data, row count, and column names
    """
    try:
        from databricks.sdk import WorkspaceClient
        
        w = WorkspaceClient()
        
        # Build the query with limit
        query = request.query.strip().rstrip(";")
        if request.limit and "LIMIT" not in query.upper():
            query = f"{query} LIMIT {request.limit}"
        
        # Execute using statement execution API
        # Note: This requires a SQL warehouse to be running
        result = w.statement_execution.execute_statement(
            warehouse_id=os.getenv("DATABRICKS_SQL_WAREHOUSE_ID", ""),
            statement=query,
            wait_timeout="30s",
        )
        
        if result.status and result.status.state.value == "SUCCEEDED":
            columns = [col.name for col in result.manifest.schema.columns] if result.manifest else []
            data = []
            if result.result and result.result.data_array:
                for row in result.result.data_array:
                    data.append(dict(zip(columns, row)))
            
            return QueryResponse(
                success=True,
                data=data,
                row_count=len(data),
                columns=columns,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Query failed: {result.status.error if result.status else 'Unknown error'}"
            )
            
    except ImportError:
        raise HTTPException(status_code=500, detail="databricks-sdk not installed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Add your custom endpoints below
# ============================================================================

@router.get("/example")
async def example_endpoint(
    name: str = Query("World", description="Name to greet")
) -> dict:
    """
    Example endpoint demonstrating query parameters.
    
    Use this as a template for your own endpoints.
    """
    return {
        "message": f"Hello, {name}!",
        "tip": "Customize server/routers/api.py to add your own endpoints",
    }

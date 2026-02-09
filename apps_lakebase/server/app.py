"""
FastAPI Application Entry Point
==============================

This is the main FastAPI application that runs as a Databricks App.
Customize this file to add your API endpoints.

Reference: https://github.com/databricks-solutions/claude-databricks-app-template

Deployment:
    This app is deployed to Databricks Apps platform using app.yaml config.
    The entry point is: uvicorn server.app:app --host 0.0.0.0 --port 8000

Local Development:
    Run with: ./scripts/watch.sh (includes hot reload)
    Or: uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Import routers
from server.routers import health, api

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events for startup/shutdown."""
    # Startup
    logger.info("🚀 Starting Databricks App...")
    logger.info(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"   Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    
    # Initialize any connections here (database, external services, etc.)
    # Example: app.state.db = await create_db_connection()
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Databricks App...")
    # Clean up connections here
    # Example: await app.state.db.close()


# Create FastAPI app
app = FastAPI(
    title="Databricks App",
    description="""
    A Databricks App built with vibe coding.
    
    ## Features
    - FastAPI backend with automatic OpenAPI documentation
    - Databricks SDK integration for workspace access
    - MLflow integration for ML experiments and model serving
    - Health check endpoints for monitoring
    
    ## Quick Links
    - [API Documentation](/docs)
    - [Health Check](/health)
    - [API Endpoints](/api)
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Exception handler for better error messages
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("ENVIRONMENT") != "production" else None,
        }
    )


# CORS middleware - allows frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "*",  # Allow all origins (customize for production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(health.router, tags=["Health"])
app.include_router(api.router, prefix="/api", tags=["API"])


# ============================================================================
# Static File Serving (for frontend, if built)
# ============================================================================

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "client", "build")
STATIC_EXISTS = os.path.exists(STATIC_DIR) and os.path.exists(
    os.path.join(STATIC_DIR, "index.html")
)

if STATIC_EXISTS:
    # Mount static assets directory
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend_routes(path: str):
        """
        Serve frontend for SPA routing.
        
        This catches all routes not handled by API routers and serves
        the frontend index.html, allowing client-side routing to work.
        """
        # Don't serve frontend for API routes
        if path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
            return JSONResponse({"error": "Not found"}, status_code=404)
        
        # Check if it's a static file
        file_path = os.path.join(STATIC_DIR, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Otherwise serve index.html for SPA routing
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

else:
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint when no frontend is deployed."""
        return {
            "message": "Welcome to your Databricks App! 🚀",
            "status": "running",
            "version": "0.1.0",
            "endpoints": {
                "api_docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
                "health": "/health",
                "api": "/api",
            },
            "note": "No frontend deployed. Visit /docs for API documentation.",
        }

"""
Agent Settings Template
=======================

Centralized configuration management using dataclass pattern.
All settings loaded from environment variables with defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AgentSettings:
    """
    Agent configuration settings.
    
    All values loaded from environment variables.
    Override by setting env vars before agent initialization.
    """
    
    # Catalog and schema
    catalog: str = field(default_factory=lambda: os.environ.get("CATALOG", "main"))
    gold_schema: str = field(default_factory=lambda: os.environ.get("GOLD_SCHEMA", "gold"))
    agent_schema: str = field(default_factory=lambda: os.environ.get("AGENT_SCHEMA", "agents"))
    
    # LLM endpoint
    llm_endpoint: str = field(default_factory=lambda: os.environ.get(
        "LLM_ENDPOINT", "databricks-claude-sonnet-4-5"
    ))
    
    # Genie Space IDs (one per domain)
    genie_spaces: Dict[str, str] = field(default_factory=lambda: {
        "domain1": os.environ.get("DOMAIN1_GENIE_SPACE_ID", ""),
        "domain2": os.environ.get("DOMAIN2_GENIE_SPACE_ID", ""),
    })
    
    # SQL Warehouse
    warehouse_id: str = field(default_factory=lambda: os.environ.get("WAREHOUSE_ID", ""))
    
    # Lakebase memory
    lakebase_instance_name: str = field(default_factory=lambda: os.environ.get(
        "LAKEBASE_INSTANCE", "agent_lakebase"
    ))
    
    # Embedding model for long-term memory
    embedding_endpoint: str = field(default_factory=lambda: os.environ.get(
        "EMBEDDING_ENDPOINT", "databricks-gte-large-en"
    ))
    embedding_dims: int = 1024
    
    # MLflow experiments
    experiment_dev: str = field(default_factory=lambda: os.environ.get(
        "EXPERIMENT_DEV", "/Shared/agent_development"
    ))
    experiment_eval: str = field(default_factory=lambda: os.environ.get(
        "EXPERIMENT_EVAL", "/Shared/agent_evaluation"
    ))
    experiment_deploy: str = field(default_factory=lambda: os.environ.get(
        "EXPERIMENT_DEPLOY", "/Shared/agent_deployment"
    ))
    
    # Model registration
    model_name: Optional[str] = field(default_factory=lambda: os.environ.get(
        "MODEL_NAME", None
    ))


# Singleton instance
settings = AgentSettings()

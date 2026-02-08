## Registration Pattern

# Databricks notebook source
"""
Register Agent Prompts to Unity Catalog and MLflow
==================================================

Stores all agent prompts in agent_config table and logs to MLflow.
"""

import mlflow
from datetime import datetime
from pyspark.sql import SparkSession

# ===========================================================================
# ORCHESTRATOR SYSTEM PROMPT
# ===========================================================================

ORCHESTRATOR_PROMPT = """You are the **Databricks Platform Health Supervisor**...

[Full prompt content here - 200+ lines]
"""

INTENT_CLASSIFIER_PROMPT = """You are a query classifier..."""

SYNTHESIZER_PROMPT = """You are a senior platform analyst..."""

# Domain-specific worker prompts
COST_ANALYST_PROMPT = """You are a cost intelligence specialist..."""
SECURITY_ANALYST_PROMPT = """You are a security compliance specialist..."""
# ... more prompts ...

# ===========================================================================
# PROMPT REGISTRY
# ===========================================================================

PROMPTS = {
    "orchestrator": ORCHESTRATOR_PROMPT,
    "intent_classifier": INTENT_CLASSIFIER_PROMPT,
    "synthesizer": SYNTHESIZER_PROMPT,
    "cost_analyst": COST_ANALYST_PROMPT,
    "security_analyst": SECURITY_ANALYST_PROMPT,
    "performance_analyst": PERFORMANCE_ANALYST_PROMPT,
    "reliability_analyst": RELIABILITY_ANALYST_PROMPT,
    "quality_analyst": QUALITY_ANALYST_PROMPT,
}

# ===========================================================================
# REGISTRATION FUNCTIONS
# ===========================================================================

def register_prompts_to_table(
    spark: SparkSession,
    catalog: str,
    schema: str,
    prompts: dict,
) -> None:
    """
    Register prompts to Unity Catalog agent_config table.
    
    Args:
        spark: SparkSession
        catalog: Unity Catalog name
        schema: Schema name
        prompts: Dict of {prompt_key: prompt_text}
    """
    table_name = f"{catalog}.{schema}.agent_config"
    
    print("\n" + "=" * 80)
    print(f"REGISTERING PROMPTS TO: {table_name}")
    print("=" * 80)
    
    for prompt_key, prompt_text in prompts.items():
        # Insert prompt as new version
        spark.sql(f"""
            INSERT INTO {table_name}
            VALUES (
                '{prompt_key}',
                '{prompt_text.replace("'", "''")}',  -- Escape single quotes
                'prompt',
                1,  -- Version (could auto-increment)
                CURRENT_TIMESTAMP(),
                CURRENT_USER(),
                'Agent system prompt',
                map('role', '{prompt_key}', 'status', 'active')
            )
        """)
        
        print(f"✓ Registered: {prompt_key}")
    
    print(f"\n✅ Registered {len(prompts)} prompts to Unity Catalog")


def register_prompts_to_mlflow(
    prompts: dict,
    experiment_name: str = "/Shared/health_monitor_agent_prompts"
) -> None:
    """
    Register prompts as MLflow artifacts for versioning.
    
    Args:
        prompts: Dict of {prompt_key: prompt_text}
        experiment_name: MLflow experiment path
    """
    mlflow.set_experiment(experiment_name)
    
    print("\n" + "=" * 80)
    print(f"LOGGING PROMPTS TO MLFLOW: {experiment_name}")
    print("=" * 80)
    
    with mlflow.start_run(run_name=f"register_prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # Log each prompt as artifact
        for prompt_key, prompt_text in prompts.items():
            # Save to temp file
            temp_file = f"/tmp/{prompt_key}.txt"
            with open(temp_file, 'w') as f:
                f.write(prompt_text)
            
            # Log as artifact
            mlflow.log_artifact(temp_file, artifact_path=f"prompts/{prompt_key}")
            print(f"✓ Logged: {prompt_key}")
        
        # Log metadata
        mlflow.log_params({
            "num_prompts": len(prompts),
            "prompt_keys": ",".join(prompts.keys()),
            "registration_date": datetime.now().isoformat(),
        })
        
        print(f"\n✅ Logged {len(prompts)} prompts to MLflow")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    """Register all agent prompts."""
    catalog = dbutils.widgets.get("catalog")
    agent_schema = dbutils.widgets.get("agent_schema")
    
    spark = SparkSession.builder.appName("Register Prompts").getOrCreate()
    
    # Register to Unity Catalog
    register_prompts_to_table(spark, catalog, agent_schema, PROMPTS)
    
    # Register to MLflow
    register_prompts_to_mlflow(PROMPTS)
    
    print("\n" + "=" * 80)
    print("✅ PROMPT REGISTRATION COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
```

---


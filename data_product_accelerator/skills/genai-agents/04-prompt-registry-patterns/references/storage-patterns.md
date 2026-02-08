# Storage Patterns: Unity Catalog + MLflow

Complete implementation for registering prompts to both Unity Catalog table and MLflow for dual storage.

## Storage Pattern: Unity Catalog + MLflow

### Unity Catalog Table Schema

```sql
CREATE TABLE {catalog}.{schema}.agent_config (
    config_key STRING NOT NULL,
    config_value STRING NOT NULL,
    config_type STRING NOT NULL,  -- 'prompt', 'setting', 'metadata'
    version INT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    created_by STRING NOT NULL,
    description STRING,
    tags MAP<STRING, STRING>,
    CONSTRAINT pk_agent_config PRIMARY KEY (config_key, version)
)
CLUSTER BY AUTO
COMMENT 'Agent configuration storage including prompts, settings, and metadata';
```

### Why Unity Catalog + MLflow?

| Storage | Purpose | Benefits |
|---|---|---|
| **Unity Catalog Table** | Runtime prompt retrieval | Fast reads, SQL queryable, governed |
| **MLflow Artifacts** | Versioning & experiment tracking | Git-like history, rollback, lineage |

---



## Register Prompts to Unity Catalog Table

```python
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
```

## Register Prompts to MLflow

```python
import mlflow
from datetime import datetime

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
```

## Prompt Update Pattern

### Iterative Prompt Development

```python
def update_prompt(
    spark: SparkSession,
    catalog: str,
    schema: str,
    prompt_key: str,
    new_text: str,
    description: str = "Prompt update",
    alias: str = "staging"
) -> int:
    """
    Update prompt with new version.
    
    Returns:
        New version number.
    """
    table_name = f"{catalog}.{schema}.agent_config"
    
    # Get max version
    max_version_query = f"""
        SELECT MAX(version) as max_ver
        FROM {table_name}
        WHERE config_key = '{prompt_key}'
    """
    
    max_version = spark.sql(max_version_query).collect()[0][0] or 0
    new_version = max_version + 1
    
    # Insert new version
    spark.sql(f"""
        INSERT INTO {table_name}
        VALUES (
            '{prompt_key}',
            '{new_text.replace("'", "''")}',
            'prompt',
            {new_version},
            CURRENT_TIMESTAMP(),
            CURRENT_USER(),
            '{description}',
            map('alias', '{alias}', 'previous_version', '{max_version}')
        )
    """)
    
    print(f"✓ Updated {prompt_key} to version {new_version} (alias: {alias})")
    
    # Also log to MLflow
    with mlflow.start_run(run_name=f"update_{prompt_key}_v{new_version}"):
        mlflow.log_params({
            "prompt_key": prompt_key,
            "version": new_version,
            "alias": alias,
        })
        mlflow.log_text(new_text, artifact_file=f"prompts/{prompt_key}_v{new_version}.txt")
    
    return new_version
```

### Promotion Pattern

```python
def promote_prompt(
    spark: SparkSession,
    catalog: str,
    schema: str,
    prompt_key: str,
    from_alias: str = "challenger",
    to_alias: str = "champion"
) -> None:
    """
    Promote challenger to champion after successful AB test.
    
    Updates tags to mark new champion.
    """
    table_name = f"{catalog}.{schema}.agent_config"
    
    # Get challenger version
    challenger_query = f"""
        SELECT version
        FROM {table_name}
        WHERE config_key = '{prompt_key}'
          AND tags['alias'] = '{from_alias}'
        ORDER BY version DESC
        LIMIT 1
    """
    
    challenger_version = spark.sql(challenger_query).collect()[0][0]
    
    # Update tags to promote
    spark.sql(f"""
        UPDATE {table_name}
        SET tags = map('alias', '{to_alias}', 'promoted_from', '{from_alias}')
        WHERE config_key = '{prompt_key}'
          AND version = {challenger_version}
    """)
    
    # Demote old champion to archived
    spark.sql(f"""
        UPDATE {table_name}
        SET tags = map('alias', 'archived', 'superseded_by', '{challenger_version}')
        WHERE config_key = '{prompt_key}'
          AND tags['alias'] = '{to_alias}'
          AND version < {challenger_version}
    """)
    
    print(f"✓ Promoted {prompt_key} v{challenger_version} from {from_alias} to {to_alias}")
```

---



## SQL Injection Prevention

**CRITICAL**: Always escape single quotes in prompt text:

```python
# ✅ CORRECT: Escape single quotes
sanitized = prompt_text.replace("'", "''")
spark.sql(f"INSERT INTO table VALUES ('{sanitized}')")

# ❌ WRONG: Unsanitized (SQL injection risk)
spark.sql(f"INSERT INTO table VALUES ('{prompt_text}')")  # Dangerous!
```

## Dual Storage Benefits

| Storage | Purpose | When to Use |
|---|---|---|
| **Unity Catalog** | Runtime retrieval | Agent execution, prompt loading |
| **MLflow** | Versioning & lineage | Experiment tracking, rollback, audit |

Both storages are required:
- UC table enables fast runtime access
- MLflow provides version history and rollback capability

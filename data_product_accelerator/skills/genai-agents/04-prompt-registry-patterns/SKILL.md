---
name: prompt-registry-patterns
description: MLflow Prompt Registry for versioned prompt management - Unity Catalog storage, MLflow artifact versioning, A/B testing with champion/challenger, lazy loading, SQL injection prevention
triggers:
  - prompt
  - prompt registry
  - A/B testing
  - champion challenger
  - prompt versioning
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/agent-bricks/SKILL.md"
      relationship: "reference"
      last_synced: "2026-02-09"
      sync_commit: "97a3637"
---

# MLflow Prompt Registry Patterns

## When to Use

Use this skill when implementing agents that need:
- **Versioned prompts**: Track prompt changes over time
- **A/B testing**: Compare champion vs challenger prompts
- **Runtime updates**: Change prompts without code deployment
- **Governance**: Audit prompt changes and rollback capability

## Core Principles

### 1. Single Source of Truth
- All prompts stored in Unity Catalog table (`agent_config`)
- Versioned in MLflow as artifacts
- Never hardcoded in agent code
- Runtime loading by alias (`production`, `staging`, `champion`, `challenger`)

### 2. Prompt Versioning
- Each prompt update creates new MLflow run
- Prompts registered as artifacts in experiment
- Aliases point to specific versions
- Easy rollback to previous versions

### 3. A/B Testing Support
- Champion/challenger pattern
- Load different prompts by alias
- Track performance in evaluation
- Promote winner to production

## Unity Catalog Table Schema

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

## Why Unity Catalog + MLflow?

| Storage | Purpose | Benefits |
|---|---|---|
| **Unity Catalog Table** | Runtime prompt retrieval | Fast reads, SQL queryable, governed |
| **MLflow Artifacts** | Versioning & experiment tracking | Git-like history, rollback, lineage |

## Quick Loading Pattern

```python
from pyspark.sql import SparkSession

def load_prompt(
    spark: SparkSession,
    catalog: str,
    schema: str,
    prompt_key: str,
    version: int = None
) -> str:
    """Load prompt from Unity Catalog agent_config table."""
    table_name = f"{catalog}.{schema}.agent_config"
    
    if version:
        query = f"""
            SELECT config_value
            FROM {table_name}
            WHERE config_key = '{prompt_key}'
              AND version = {version}
              AND config_type = 'prompt'
        """
    else:
        query = f"""
            SELECT config_value
            FROM {table_name}
            WHERE config_key = '{prompt_key}'
              AND config_type = 'prompt'
            ORDER BY version DESC
            LIMIT 1
        """
    
    result = spark.sql(query).collect()
    if not result:
        raise ValueError(f"Prompt not found: {prompt_key}")
    
    return result[0][0]

# Usage
spark = SparkSession.builder.getOrCreate()
orchestrator_prompt = load_prompt(spark, catalog, schema, "orchestrator")
```

## Common Mistakes to Avoid

### ❌ DON'T: Hardcode Prompts in Agent

```python
# BAD: Prompts embedded in code
class Agent:
    PROMPT = """You are a helpful assistant..."""  # ❌ No versioning!
```

### ✅ DO: Load from Registry

```python
# GOOD: Prompts loaded from Unity Catalog
class Agent:
    def __init__(self):
        self._prompts = self._load_prompts_from_uc()
```

### ❌ DON'T: Skip MLflow Logging

```python
# BAD: Only in Unity Catalog
register_to_table(prompts)  # ❌ No experiment tracking!
```

### ✅ DO: Dual Storage

```python
# GOOD: Both Unity Catalog and MLflow
register_to_table(prompts)  # ✅ Runtime access
register_to_mlflow(prompts)  # ✅ Versioning & lineage
```

### ❌ DON'T: Ignore SQL Injection

```python
# BAD: Unsanitized prompt text
spark.sql(f"INSERT INTO table VALUES ('{prompt}')")  # ❌ SQL injection!
```

### ✅ DO: Escape Single Quotes

```python
# GOOD: Escaped quotes
sanitized = prompt.replace("'", "''")
spark.sql(f"INSERT INTO table VALUES ('{sanitized}')")  # ✅ Safe
```

## Validation Checklist

Before deploying prompt registry:
- [ ] Unity Catalog table created with correct schema
- [ ] Prompts registered to both UC table and MLflow
- [ ] Agent loads prompts at runtime (lazy loading)
- [ ] Fallback defaults defined if UC unavailable
- [ ] AB testing aliases defined (champion/challenger)
- [ ] Prompt update function creates new versions
- [ ] Promotion function updates aliases
- [ ] SQL injection prevented (escaped quotes)
- [ ] MLflow experiment tracks prompt changes
- [ ] Evaluation compares prompt variants

## References

### Detailed Patterns
- [Storage Patterns](references/storage-patterns.md) - UC table + MLflow registration
- [A/B Testing](references/ab-testing.md) - Champion/challenger setup
- [Loading Patterns](references/loading-patterns.md) - Runtime loading and lazy initialization

### Setup Scripts
- [Register Prompts](scripts/register_prompts.py) - Prompt registration script

### Official Documentation
- [MLflow Prompt Engineering](https://mlflow.org/docs/latest/llms/prompt-engineering/index.html)
- [Unity Catalog Tables](https://docs.databricks.com/data-governance/unity-catalog/create-tables.html)
- [Agent Configuration Management](https://docs.databricks.com/en/generative-ai/agent-framework/configuration.html)

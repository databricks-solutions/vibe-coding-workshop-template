# A/B Testing Pattern (Champion/Challenger)

Complete A/B testing setup for comparing prompt variants.

## AB Testing Pattern (Champion/Challenger)

### Setup: Register Multiple Prompt Versions

```python
# Register champion (current production)
register_prompt(
    key="orchestrator",
    text=CHAMPION_PROMPT,
    alias="champion",
    tags={"variant": "A", "status": "production"}
)

# Register challenger (new experimental)
register_prompt(
    key="orchestrator",
    text=CHALLENGER_PROMPT,
    alias="challenger",
    tags={"variant": "B", "status": "experimental"}
)
```

### Agent: Load by Alias

```python
def load_prompt_by_alias(
    spark: SparkSession,
    catalog: str,
    schema: str,
    prompt_key: str,
    alias: str = "champion"
) -> str:
    """
    Load prompt by alias (champion/challenger/production).
    
    Args:
        alias: champion, challenger, production, staging, etc.
    """
    table_name = f"{catalog}.{schema}.agent_config"
    
    query = f"""
        SELECT config_value
        FROM {table_name}
        WHERE config_key = '{prompt_key}'
          AND config_type = 'prompt'
          AND tags['alias'] = '{alias}'
        ORDER BY version DESC
        LIMIT 1
    """
    
    result = spark.sql(query).collect()
    
    if not result:
        # Fallback to latest if alias not found
        return load_prompt(spark, catalog, schema, prompt_key)
    
    return result[0][0]


# Usage: Route based on user_id
def get_prompt_variant(user_id: str) -> str:
    """Return champion or challenger based on user_id."""
    # 90% champion, 10% challenger
    import hashlib
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return "challenger" if hash_val % 10 == 0 else "champion"


# In agent
variant = get_prompt_variant(user_id)
orchestrator_prompt = load_prompt_by_alias(
    spark, catalog, schema, "orchestrator", alias=variant
)
```

### Evaluation: Compare Variants

```python
import mlflow
import pandas as pd

def evaluate_prompt_variants(eval_dataset: pd.DataFrame) -> dict:
    """
    Evaluate champion vs challenger prompts.
    
    Returns:
        Dict with metrics for each variant.
    """
    results = {}
    
    for variant in ["champion", "challenger"]:
        print(f"\n📊 Evaluating {variant}...")
        
        # Load agent with this variant
        agent = HealthMonitorAgent()
        agent._prompt_alias = variant
        
        # Run evaluation
        eval_results = mlflow.genai.evaluate(
            model=agent,
            data=eval_dataset,
            model_type="databricks-agent",
            evaluators=[relevance, safety, guidelines],
            run_name=f"eval_{variant}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        results[variant] = eval_results.metrics
        
        print(f"  Relevance: {eval_results.metrics['relevance/mean']:.3f}")
        print(f"  Safety: {eval_results.metrics['safety/mean']:.3f}")
        print(f"  Guidelines: {eval_results.metrics['guidelines/mean']:.3f}")
    
    # Compare
    champion_score = results["champion"]["relevance/mean"]
    challenger_score = results["challenger"]["relevance/mean"]
    
    if challenger_score > champion_score:
        print(f"\n🎉 Challenger wins! ({challenger_score:.3f} > {champion_score:.3f})")
        print("Consider promoting challenger to champion")
    else:
        print(f"\n✅ Champion retains! ({champion_score:.3f} ≥ {challenger_score:.3f})")
    
    return results
```

---



## A/B Testing Workflow

1. **Register Champion** (current production prompt)
2. **Register Challenger** (new experimental prompt)
3. **Route Traffic** (90% champion, 10% challenger)
4. **Collect Metrics** (relevance, safety, guidelines)
5. **Evaluate Results** (compare performance)
6. **Promote Winner** (update alias if challenger wins)

## Traffic Splitting Strategies

### Hash-Based (Deterministic)

```python
def get_prompt_variant(user_id: str) -> str:
    """Deterministic routing based on user_id hash."""
    import hashlib
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return "challenger" if hash_val % 10 == 0 else "champion"
```

### Random (Non-Deterministic)

```python
import random

def get_prompt_variant(user_id: str) -> str:
    """Random routing (10% challenger)."""
    return "challenger" if random.random() < 0.1 else "champion"
```

### Time-Based

```python
from datetime import datetime

def get_prompt_variant(user_id: str) -> str:
    """Route based on time (challenger during off-peak hours)."""
    hour = datetime.now().hour
    return "challenger" if 2 <= hour < 6 else "champion"
```

## Promotion After Successful Test

```python
# After evaluation shows challenger wins
promote_prompt(
    spark=spark,
    catalog=catalog,
    schema=schema,
    prompt_key="orchestrator",
    from_alias="challenger",
    to_alias="champion"
)
```

This updates:
- Challenger version → `champion` alias
- Old champion → `archived` alias
- All tracked in MLflow for audit trail

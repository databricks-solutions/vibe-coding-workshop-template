# Loading Patterns: Runtime and Lazy Loading

Complete patterns for loading prompts from Unity Catalog at runtime.

## Loading Patterns

### Runtime Loading from Unity Catalog

```python
from pyspark.sql import SparkSession

def load_prompt(
    spark: SparkSession,
    catalog: str,
    schema: str,
    prompt_key: str,
    version: int = None
) -> str:
    """
    Load prompt from Unity Catalog agent_config table.
    
    Args:
        spark: SparkSession
        catalog: Unity Catalog name
        schema: Schema name
        prompt_key: Prompt identifier
        version: Specific version (None = latest)
    
    Returns:
        Prompt text string.
    """
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


# Usage in agent
spark = SparkSession.builder.getOrCreate()

orchestrator_prompt = load_prompt(
    spark, catalog, schema, "orchestrator"
)

# With specific version
old_prompt = load_prompt(
    spark, catalog, schema, "orchestrator", version=1
)
```

### Lazy Loading Pattern (Agent Initialization)

```python
class HealthMonitorAgent(mlflow.pyfunc.ResponsesAgent):
    """Agent with lazy-loaded prompts."""
    
    def __init__(self):
        super().__init__()
        self._prompts_loaded = False
        self._prompts = {}
    
    def _load_prompts(self):
        """Lazy-load prompts on first use."""
        if self._prompts_loaded:
            return
        
        try:
            spark = SparkSession.builder.getOrCreate()
            catalog = os.environ.get("CATALOG", "default_catalog")
            schema = os.environ.get("AGENT_SCHEMA", "agent_schema")
            
            # Load all prompts
            self._prompts = {
                "orchestrator": load_prompt(spark, catalog, schema, "orchestrator"),
                "intent_classifier": load_prompt(spark, catalog, schema, "intent_classifier"),
                "synthesizer": load_prompt(spark, catalog, schema, "synthesizer"),
                # ... more prompts ...
            }
            
            self._prompts_loaded = True
            print("✓ Prompts loaded from Unity Catalog")
            
        except Exception as e:
            print(f"⚠ Could not load prompts from UC: {e}")
            print("Using embedded defaults")
            self._prompts = self._get_default_prompts()
            self._prompts_loaded = True
    
    def _get_default_prompts(self) -> dict:
        """Fallback embedded prompts."""
        return {
            "orchestrator": "You are a helpful assistant...",
            # ... minimal defaults ...
        }
    
    def predict(self, request):
        """Execute agent with loaded prompts."""
        # Lazy-load prompts on first call
        self._load_prompts()
        
        # Use prompts
        orchestrator_prompt = self._prompts["orchestrator"]
        
        # ... rest of prediction logic ...
```

---



## Benefits of Lazy Loading

1. **Faster Initialization**: Agent starts without waiting for UC queries
2. **Error Resilience**: Falls back to defaults if UC unavailable
3. **Runtime Updates**: Prompts reloaded on next request after update
4. **Memory Efficiency**: Only loads prompts when needed

## Loading with A/B Testing

```python
class HealthMonitorAgent(mlflow.pyfunc.ResponsesAgent):
    """Agent with A/B testing support."""
    
    def __init__(self, prompt_alias: str = "champion"):
        super().__init__()
        self._prompt_alias = prompt_alias
        self._prompts_loaded = False
        self._prompts = {}
    
    def _load_prompts(self):
        """Load prompts with A/B testing alias."""
        if self._prompts_loaded:
            return
        
        spark = SparkSession.builder.getOrCreate()
        catalog = os.environ.get("CATALOG", "default_catalog")
        schema = os.environ.get("AGENT_SCHEMA", "agent_schema")
        
        # Load prompts by alias
        self._prompts = {
            "orchestrator": load_prompt_by_alias(
                spark, catalog, schema, "orchestrator", alias=self._prompt_alias
            ),
            # ... more prompts ...
        }
        
        self._prompts_loaded = True
        print(f"✓ Prompts loaded with alias: {self._prompt_alias}")
```

## Error Handling

```python
def load_prompt_safe(
    spark: SparkSession,
    catalog: str,
    schema: str,
    prompt_key: str,
    default: str = None
) -> str:
    """
    Load prompt with fallback to default.
    
    Returns:
        Prompt text or default if not found.
    """
    try:
        return load_prompt(spark, catalog, schema, prompt_key)
    except Exception as e:
        print(f"⚠ Could not load prompt {prompt_key}: {e}")
        if default:
            print(f"Using default prompt")
            return default
        raise
```

## Caching Pattern

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def load_prompt_cached(
    catalog: str,
    schema: str,
    prompt_key: str,
    version: int = None
) -> str:
    """
    Load prompt with LRU cache.
    
    Cache key includes catalog, schema, prompt_key, and version.
    """
    spark = SparkSession.builder.getOrCreate()
    return load_prompt(spark, catalog, schema, prompt_key, version)
```

**Note**: Cache invalidation required after prompt updates. Consider TTL-based cache or version-aware caching.

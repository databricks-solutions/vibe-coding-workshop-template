# MLflow Prompt Registry Basics

## mlflow.log_prompt() Pattern

Log prompts to MLflow Prompt Registry:

```python
import mlflow.genai

mlflow.genai.log_prompt(
    prompt="""You are a helpful assistant.
    
User context: {user_context}
Query: {query}""",
    artifact_path="prompts/assistant",
    registered_model_name="my_app_assistant_prompt"
)
```

**Benefits:**
- Version control for prompts
- Unity Catalog storage
- Alias management (production, staging, dev)
- A/B testing support

## mlflow.load_prompt() by Name and Alias

Load prompts from registry:

### Load by Alias (Recommended)

```python
# Load production prompt
prompt = mlflow.genai.load_prompt(
    "prompts:/my_app_assistant_prompt/production"
)
```

### Load by Version

```python
# Load specific version
prompt_v1 = mlflow.genai.load_prompt(
    "prompts:/my_app_assistant_prompt/1"
)

# Load latest version
prompt_latest = mlflow.genai.load_prompt(
    "prompts:/my_app_assistant_prompt/latest"
)
```

## Alias Management

Set aliases for deployment environments:

```python
from mlflow import MlflowClient

client = MlflowClient()

# Set production alias
client.set_registered_model_alias(
    name="my_app_assistant_prompt",
    alias="production",
    version="2"
)

# Set staging alias
client.set_registered_model_alias(
    name="my_app_assistant_prompt",
    alias="staging",
    version="1"
)
```

## Version Tracking

MLflow automatically tracks prompt versions:

```python
# Log initial version
mlflow.genai.log_prompt(
    prompt="Version 1 prompt",
    registered_model_name="my_prompt"
)  # Creates version 1

# Log updated version
mlflow.genai.log_prompt(
    prompt="Version 2 prompt (improved)",
    registered_model_name="my_prompt"
)  # Creates version 2

# Both versions available
prompt_v1 = mlflow.genai.load_prompt("prompts:/my_prompt/1")
prompt_v2 = mlflow.genai.load_prompt("prompts:/my_prompt/2")
```

## Complete Pattern

Example workflow:

```python
import mlflow.genai
from mlflow import MlflowClient

# 1. Log prompt
mlflow.genai.log_prompt(
    prompt="""You are a Databricks cost analyst.

User context: {user_context}
Query: {query}

Guidelines:
- Include specific dollar amounts
- Include time context
- Cite sources""",
    artifact_path="prompts/cost_analyst",
    registered_model_name="cost_analyst_prompt"
)

# 2. Set production alias
client = MlflowClient()
client.set_registered_model_alias(
    name="cost_analyst_prompt",
    alias="production",
    version="1"
)

# 3. Use in agent
prompt_template = mlflow.genai.load_prompt(
    "prompts:/cost_analyst_prompt/production"
)

formatted_prompt = prompt_template.format(
    user_context="Workspace admin",
    query="What is the total cost?"
)
```

## Best Practices

1. **Use aliases for environments:**
   - `production` for production
   - `staging` for staging
   - `dev` for development

2. **Version control prompts:**
   - Log new versions when updating prompts
   - Keep old versions for rollback

3. **Store in Unity Catalog:**
   - Prompts stored in Unity Catalog
   - Governed like other ML assets

4. **Use template variables:**
   - Use `{variable}` syntax for dynamic content
   - Format prompts at runtime

5. **Document prompt changes:**
   - Include version notes
   - Track performance impact

## References

- [Prompt Registry Documentation](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/)
- [MLflow Prompt Management](https://mlflow.org/docs/latest/genai/prompt-version-mgmt/)

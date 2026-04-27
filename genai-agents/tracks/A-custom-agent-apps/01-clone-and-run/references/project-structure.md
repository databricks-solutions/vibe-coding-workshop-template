# Project structure (agent-openai-agents-sdk template)

This reference describes the layout of a project generated from the
`agent-openai-agents-sdk` Databricks app template after clone and quickstart.
Use it when you need detail beyond the high-level workflow in the main skill.

## Directory layout

```
my-agent-app/
├── agent.py              # Agent definition — THIS IS WHERE YOU BUILD
├── start_server.py       # MLflow AgentServer entrypoint
├── config.yml            # Agent configuration (model, tools, settings)
├── app.yaml              # Databricks Apps deployment config
├── databricks.yml        # DAB bundle config for deploy
├── pyproject.toml        # Python dependencies and uv scripts
├── .env                  # Local environment variables (gitignored)
├── .env.example          # Template for .env
├── tests/                # Test fixtures and evaluation
│   └── eval_dataset.json # Sample evaluation dataset
└── README.md
```

Replace `my-agent-app` with your actual project directory name.

## Key files explained

### `agent.py`

The agent logic. For the OpenAI Agents SDK template, this contains an `Agent`
definition with instructions, model, and tools. It is wrapped with MLflow
`ResponsesAgent` for compatibility with the serving contract.

```python
# Typical agent.py structure (OpenAI Agents SDK template)
import mlflow
from agents import Agent, function_tool

@function_tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"Weather in {city}: 72°F, sunny"

agent = Agent(
    name="my-agent",
    instructions="You are a helpful assistant.",
    model="databricks-claude-sonnet-4-6",
    tools=[get_weather],
)

mlflow.models.set_model(agent)
```

### `start_server.py`

Thin wrapper that creates the ASGI app:

```python
from mlflow.server import create_app

app = create_app(model_uri="agent.py")
```

### `config.yml`

Externalizes settings so you can change model endpoints or tool configurations
without editing code:

```yaml
llm_endpoint: "databricks-claude-sonnet-4-6"
warehouse_id: "${WAREHOUSE_ID}"
```

### `app.yaml`

Declares how the app runs on Databricks and what resources it needs:

```yaml
command:
  - "uvicorn"
  - "start_server:app"
  - "--host=0.0.0.0"
  - "--port=8000"

env:
  - name: LLM_MODEL
    value: "databricks-claude-sonnet-4-6"

resources:
  - name: sql-warehouse
    sql_warehouse:
      permission: CAN_USE
```

### `databricks.yml`

Bundle configuration for deploying to a Databricks workspace:

```yaml
bundle:
  name: my-agent-app

resources:
  apps:
    my_agent_app:
      name: my-agent-app
      source_code_path: .

targets:
  dev:
    default: true
```

### Other paths

| Path | Role |
|------|------|
| `pyproject.toml` | Python dependencies, tool config, and `uv` script entrypoints (`quickstart`, `start-app`, etc.). |
| `.env` / `.env.example` | Local secrets and workspace settings; created or filled by quickstart. |
| `tests/` | Evaluation data and tests; `eval_dataset.json` is a sample dataset. |
| `README.md` | Template-specific setup and deploy notes from upstream. |

# Agent Skills Framework

A dynamic, declarative framework for building agentic search and data pipelines. Instead of hardcoding orchestration logic in Python, skills are defined as YAML manifests and composed into flows. This allows new business use cases to be supported by adding configuration files rather than rewriting code.

## Architecture

```
agent_skills/
├── skill_registry.yaml          # Master registry config
├── __init__.py                   # Package exports
├── models.py                     # Pydantic models (SkillManifest, FlowDefinition, etc.)
├── registry.py                   # Discovers and loads skills + flows
├── engine.py                     # Flow orchestration engine
├── router.py                     # FastAPI router integration
├── prd_mapper.py                 # PRD → Skills generator
│
├── skills/                       # Skill manifests (one folder per skill)
│   ├── query_rewriter/
│   │   └── manifest.yaml
│   ├── genie_search/
│   │   └── manifest.yaml
│   ├── web_search/
│   │   └── manifest.yaml
│   ├── web_result_summarizer/
│   │   └── manifest.yaml
│   ├── lakebase_search/
│   │   └── manifest.yaml
│   └── location_extractor/
│       └── manifest.yaml
│
├── flows/                        # Flow definitions (YAML pipelines)
│   ├── assistant_search.yaml
│   └── standard_search.yaml
│
├── executors/                    # Typed executor classes
│   ├── __init__.py
│   ├── base.py                   # Abstract base executor
│   ├── llm_executor.py           # Databricks model serving
│   ├── genie_executor.py         # Databricks Genie Space
│   ├── web_search_executor.py    # External web search (SerpAPI, Bing, etc.)
│   ├── lakebase_executor.py      # Lakebase PostgreSQL queries
│   ├── function_executor.py      # Arbitrary Python functions
│   └── prompt_registry_executor.py  # Databricks Prompt Registry
│
└── tests/                        # Test suite
    ├── test_registry.py
    ├── test_engine.py
    └── test_executors.py
```

## Quick Start

### 1. Integrate with your FastAPI app

Add the skills router to your `server/app.py`:

```python
from agent_skills.router import router as skills_router

app.include_router(skills_router, prefix="/api", tags=["Agent Skills"])
```

### 2. Execute a flow via API

```bash
# Execute the assistant search flow
curl -X POST http://localhost:8000/api/skills/execute/assistant_search \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"message": "Find hotels near Taylor Swift concert in Miami"}}'

# List all registered skills and flows
curl http://localhost:8000/api/skills/registry

# Check framework health
curl http://localhost:8000/api/skills/health
```

### 3. Execute a flow in Python

```python
from agent_skills import SkillRegistry, FlowEngine

registry = SkillRegistry()
engine = FlowEngine(registry)

result = await engine.execute_flow(
    flow_id="assistant_search",
    request={"message": "hotels in Miami for the weekend"},
)

print(result.response)  # {"rewrittenQuery": "...", "answer": "...", ...}
print(result.total_latency_ms)
```

## Concepts

### Skills

A **skill** is a single unit of work: an LLM call, a database query, a web search, etc. Each skill is defined by a YAML manifest in `skills/<skill_id>/manifest.yaml`.

**Supported skill types:**

| Type | Executor | Description |
|------|----------|-------------|
| `llm_call` | `LLMCallExecutor` | Calls a Databricks model serving endpoint |
| `genie_query` | `GenieQueryExecutor` | Queries Databricks Genie Space |
| `web_search` | `WebSearchExecutor` | External web search (SerpAPI, Bing, Google) |
| `lakebase_query` | `LakebaseQueryExecutor` | Queries Lakebase PostgreSQL |
| `function` | `FunctionExecutor` | Runs arbitrary Python functions |
| `prompt_registry` | `PromptRegistryExecutor` | Fetches/renders prompts from UC |

**Example skill manifest:**

```yaml
skill_id: query_rewriter
name: "Query Rewriter"
type: llm_call
config:
  endpoint: "${LLM_ENDPOINT_URL}"
  temperature: 0.2
  prompt:
    source: inline
    inline_text: "You are a search query optimizer..."
input_schema:
  - name: user_query
    type: string
    required: true
output_schema:
  - name: rewritten_query
    type: string
fallback:
  strategy: passthrough
  passthrough_field: user_query
```

### Flows

A **flow** is a multi-step pipeline that chains skills together. Flows are defined in `flows/<flow_id>.yaml`.

**Key features:**
- **Variable references**: `${request.field}`, `${step_id.output.field}`
- **Conditions**: Steps can be conditionally executed
- **Fallbacks**: Each skill defines what happens on failure
- **Display config**: Controls how the frontend renders results

**Example flow:**

```yaml
flow_id: assistant_search
name: "Assistant Search"
steps:
  - skill: query_rewriter
    id: rewrite
    inputs:
      - field: user_query
        reference: "${request.message}"

  - skill: genie_search
    id: genie
    inputs:
      - field: query_text
        reference: "${rewrite.output.rewritten_query}"

  - skill: web_search
    id: web_fallback
    condition: '${genie.output.genie_status} != "ok"'
    inputs:
      - field: query
        reference: "${rewrite.output.rewritten_query}"

response:
  - field: answer
    reference: "${genie.output.answer_text}"
  - field: rewrittenQuery
    reference: "${rewrite.output.rewritten_query}"

display:
  type: inline
  show_answer: true
  show_sources: true
```

### PRD Mapper

The PRD mapper can generate skills and flows from a Product Requirements Document:

```python
from agent_skills.prd_mapper import PRDMapper

mapper = PRDMapper()
skills, flows = await mapper.generate_from_prd(
    prd_path="docs/design_prd.md",
    output_dir="agent_skills",
    use_llm=False,  # Set True for LLM-powered generation
)
```

## Adding a New Skill

1. Create a folder: `agent_skills/skills/<your_skill_id>/`
2. Add `manifest.yaml` with the skill definition
3. Add the skill folder name to `skill_registry.yaml` under `skills:`
4. If using a new executor type, create it in `executors/` and register in `engine.py`

## Adding a New Flow

1. Create `agent_skills/flows/<your_flow_id>.yaml`
2. Define steps referencing registered skill IDs
3. Add the flow file name to `skill_registry.yaml` under `flows:`
4. Use it via `POST /api/skills/execute/<your_flow_id>`

## Frontend Integration

The framework includes a generic `SkillResultRenderer` React component that dynamically renders results based on the `display` config:

```tsx
import { SkillResultRenderer } from "@/components/skills/SkillResultRenderer";
import { executeAssistantSearch } from "@/lib/skills-api";

// In your component:
const result = await executeAssistantSearch("hotels near Miami");
<SkillResultRenderer result={result} />
```

The renderer automatically adapts to:
- **Inline** results (AI search within SearchBar)
- **Card** layout for property listings
- **List** layout for simple results
- Source badges (Genie, Web, Database)
- Debug panel with step-by-step execution details

## Testing

```bash
# Run all tests
pytest agent_skills/tests/ -v

# Run specific test file
pytest agent_skills/tests/test_registry.py -v
pytest agent_skills/tests/test_engine.py -v
pytest agent_skills/tests/test_executors.py -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_MOCK_MODE` | Enable mock execution for all skills | `false` |
| `LLM_ENDPOINT_URL` | Databricks model serving URL | Required for LLM skills |
| `GENIE_SPACE_ID` | Genie Space ID | Required for Genie skills |
| `WEB_SEARCH_PROVIDER` | Web search provider | `serpapi` |
| `WEB_SEARCH_API_KEY` | API key for web search | Optional |

## Comparison: Hardcoded vs Dynamic

| Aspect | Current (Hardcoded) | Dynamic (Skills Framework) |
|--------|---------------------|---------------------------|
| Adding a skill | Write Python code in `search.py` | Add a YAML manifest |
| Changing flow order | Modify Python logic | Edit flow YAML |
| New use case | Copy & modify entire router | Create new skill + flow YAMLs |
| Prompt updates | Redeploy application | Update in Prompt Registry |
| Frontend rendering | Skill-specific components | Generic `SkillResultRenderer` |
| Testing | Mock each service | Mock mode per skill |

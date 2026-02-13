Build a multi-agent orchestrator for this project and deploy it to Databricks Model Serving.

## Objective

Create a **super agent** — a single LangGraph-based `ResponsesAgent` deployed to
Databricks Model Serving — that acts as the central orchestrator for this
application. The super agent routes user queries to the appropriate tools:
existing Genie spaces, Unity Catalog functions, LLM endpoints, and custom
Python tools. It is the only model that gets registered and deployed; the
individual tools are wired in as callable functions, not separate endpoints.

## Required Skill Reading (READ BEFORE BUILDING)

Before writing any code, subagents MUST read the following canonical skills from
https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/
in this order:

| Order | Skill | File(s) | Why |
|-------|-------|---------|-----|
| 1 | `model-serving/` | `3-genai-agents.md` | LangGraph agent patterns, `mlflow.models.set_model()` |
| 2 | `model-serving/` | `4-tools-integration.md` | Tool resource declarations, `@tool` patterns, `DatabricksGenieSpace` / `DatabricksFunction` resources |
| 3 | `model-serving/` | `6-logging-registration.md` | Model logging and UC registration |
| 4 | `databricks-app-python/` | `2-app-resources.md` | **App-to-endpoint communication**: use `Config().authenticate()` for auth headers, `valueFrom` in `app.yaml` for resource binding, `requests.post()` for endpoint invocations |
| 5 | `databricks-genie/` | `conversation.md` | Genie Conversation API patterns for tool integration |
| 6 | `databricks-app-python/` | `SKILL.md` | App deployment, framework selection, port config, pre-installed packages |
| 7 | **Project-local** | `agentic-framework/skills/databricks-job-runner/SKILL.md` | **CRITICAL: Runtime constraints, pyfunc vs langchain decision tree, notebook-first workflow, handle_tool_errors, endpoint type locking** |

**Critical patterns to follow (not optional):**
- Agent graph: Use `ToolNode(tools, handle_tool_errors=True)` and wrap `agent_node` in `try-except`
- Model logging: `mlflow.pyfunc.log_model(python_model="agent.py", ...)` (both pyfunc and langchain import the file — deps must be installed)
- **Use a notebook** for initial log + deploy (instant feedback), convert to job after validated
- App auth: `cfg = Config(); headers = cfg.authenticate(); requests.post(url, headers=headers, ...)`
- App resources: `valueFrom: { resource: serving-endpoint }` in `app.yaml`

**Common mistakes that cause silent `null` responses:**
- Missing `handle_tool_errors=True` on `ToolNode` → graph crashes on tool errors → returns null
- Missing `try-except` in `agent_node` → LLM errors crash the graph → returns null
- Using wrong runtime (15.4 has pydantic v1 conflict) → use 16.4 LTS ML
- Not installing deps before `log_model()` → both pyfunc and langchain validate imports

## Constraints (READ FIRST)

- **DO NOT** create any Genie spaces. Discover and use existing ones.
- **DO NOT** create any Unity Catalog functions. Discover and use existing ones.
- **DO NOT** create any Unity Catalog tables, Lakebase tables, or catalogs.
- **DO** ask the user for conformation before modifying or overwriting existing files.
- **DO** discover all pre-existing Databricks resources by analyzing existing project folder
  (Genie spaces, serving endpoints, table details, UC objects).
- **DO** if required resources(Genie spaces, serving endpoints, table details, UC objects) not found after analyzing existing project folder then ask the user for confirmation.
- **DO** ask the user for confirmation before deploying any new endpoint or
  registering any new model. If a required resource (Genie space, UC function,
  table) does not exist, surface it as a gap and ask the user — do not create it.
- Use environment variables for all credentials and service identifiers.

## Chain

Run these subagents in order. Each one discovers context from the project
on its own — do not hardcode any domain details, service IDs, or file paths.

### Phase 0: Environment Validation (BEFORE writing any code)

Before any code is written, validate the target deployment environment:

1. **Query available Spark versions**: `GET /api/2.0/clusters/spark-versions`
   — confirm the exact runtime ID (e.g., `16.4.x-cpu-ml-scala2.12`, note the `-cpu-`)
2. **Check pre-installed packages** on the target runtime (or spin up a notebook and
   run `%pip list | grep -E "mlflow|langchain|langgraph|pydantic"`)
3. **Verify UC catalog/schema exists**: `databricks unity-catalog schemas get <catalog>.<schema>`
   — create if missing, or ask user for the correct catalog
4. **Check existing serving endpoints**: `GET /api/2.0/serving-endpoints`
   — identify if there's an existing endpoint and its type (langchain vs pyfunc)
   — if switching model types, the old endpoint MUST be deleted first
5. **Read `agentic-framework/skills/databricks-job-runner/SKILL.md`**
   — contains the pyfunc-vs-langchain decision tree, runtime compatibility matrix,
     and notebook template that prevents common deployment failures

### Phase 1: Analyze
Use the **prd-analyzer** subagent from `agentic-framework/agents/`.

- Scan the project: `docs/`, `https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/`, config files (`app.yaml`,
  `env.example`, `.env`, `pyproject.toml`), `server/routers/` or
  `src/backend/`, and any existing `server/agents/` directory.
- Analyze the PRD found in `docs/`.
- **Inventory existing Databricks resources** by analyzing existing project folder:
  - List Genie spaces specific to this project (`list_genie`) — record space IDs, names, tables
  - List serving endpoints specific to this project (`list_serving_endpoints`) — record endpoint names
  - List UC schemas and tables specific to this project (`get_table_details`) for any catalog/schema
    referenced in config files
  - List UC functions specific to this project in the relevant schema
- Classify each PRD requirement into a tool type:
  - **Genie tool**: Requirements answerable via SQL over existing tables
  - **UC Function tool**: Requirements served by existing UC functions
  - **LLM tool**: Requirements needing text generation, classification,
    or NL-to-structured extraction (use a Foundation Model endpoint)
  - **Custom Python tool**: Requirements needing business logic, external
    API calls, or computation not covered above
- Output the full analysis to `docs/agent_architecture.md`, including:
  1. Existing resource inventory (Genie spaces, endpoints, UC tables/functions)
  2. Architecture pattern (multi-tool orchestrator via LangGraph `ResponsesAgent`)
  3. Requirement → tool mapping matrix
  4. Tools to build (only custom Python tools and LLM prompt templates)
  5. Gaps: any requirement that needs a resource not yet created

### Phase 2: Scaffold
Use the **skill-scaffolder** subagent from `agentic-framework/agents/`.

- Read `docs/agent_architecture.md` (Phase 1 output).
- Read existing skills in `https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/` — specifically:
  - `model-serving/` (for `ResponsesAgent` and LangGraph patterns)
  - `agent-bricks/` (for MAS, Genie, KA integration patterns)
  - `databricks-genie/` (for Genie query patterns)
  - `instrumenting-with-mlflow-tracing/` (for observability)
  - `agent-evaluation/` (for evaluation harness)
- Scaffold in this order:

  **Step 1 — Tool modules** (one Python file per tool):
  Create these under the project's agent directory (e.g., `server/agents/tools/`):
  - **Genie query tool**: Wraps `ask_genie` / `ask_genie_followup` for each
    discovered Genie space. Reads the space ID from environment variables.
  - **UC Function tools**: Wraps `UCFunctionToolkit` for discovered UC
    functions. Reads catalog/schema from environment variables.
  - **LLM tools**: Wraps `ChatDatabricks` calls for NL extraction, intent
    classification, or conversational responses. Uses a configurable
    Foundation Model endpoint name from environment variables.
  - **Custom Python tools**: Implements any business logic tools identified
    in Phase 1 (e.g., price calculation, date math, external API calls).

  **Step 2 — Super agent (`agent.py`)**:
  Create a LangGraph-based agent that:
  - Loads all tools from Step 1
  - Defines a system prompt derived from the PRD (what the agent does,
    how it should respond, what tools are available)
  - Builds a LangGraph `StateGraph` with an `agent` node (LLM with tools)
    and a `tools` node (`ToolNode`), connected with conditional routing
  - **REQUIRED: `ToolNode(tools, handle_tool_errors=True)`** — prevents null
    responses when any tool raises an exception
  - **REQUIRED: Wrap `agent_node` in `try-except`** — catches LLM errors and
    returns an error AIMessage instead of crashing
  - Compiles the graph and calls `mlflow.models.set_model(GRAPH)`
  - References the `model-serving/3-genai-agents.md` pattern

  **Step 3 — Model logging script (`log_model.py`)**:
  Create a script that:
  - Imports `AGENT` and all tool resources
  - Calls `mlflow.pyfunc.log_model(...)` with:
    - `python_model="agent.py"`
    - `resources=[...]` listing all `DatabricksServingEndpoint`,
      `DatabricksFunction`, `DatabricksGenieSpace` references
    - `pip_requirements` from the project's `requirements.txt`
    - `registered_model_name` using `{UC_CATALOG}.agents.{app_name}`
      (read catalog and app name from config)
  - References the `model-serving/6-logging-registration.md` pattern

  **Step 4 — Test script (`test_agent.py`)**:
  Create a local test script that:
  - Constructs sample `ResponsesAgentRequest` objects from PRD user journeys
  - Calls `AGENT.predict(request)` for each
  - Validates response structure and tool usage
  - Can run in mock mode (env var `APP_MOCK_MODE=true`)

  **Step 5 — Tracing setup**:
  If the project uses MLflow tracing, add `mlflow.langchain.autolog()`
  and span annotations per the `instrumenting-with-mlflow-tracing` skill.

  **Step 6 — Skill definitions** (`https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/`):
  Create SKILL.md files for each new capability so future agents can
  discover and reuse them. Follow the `skill-scaffolder` specification.

### Phase 3: Deploy
Use the **databricks-deployer** subagent from `agentic-framework/agents/`.

- **FIRST:** Read `agentic-framework/skills/databricks-job-runner/SKILL.md` for
  the notebook template, runtime compatibility matrix, and common failure modes.
- Read project config (`app.yaml`, `env.example`, `requirements.txt`) to
  discover deployment targets.
- Read the `model-serving/` skill for deployment patterns.

  **Step 1 — Upload agent code to workspace**:
  Use `databricks workspace import` to push individual agent files to the user's
  workspace folder (e.g., `/Workspace/Users/{email}/agents/{app_name}/`).
  Use `--format AUTO --overwrite` for each file.

  **Step 2 — Log and register model (NOTEBOOK-FIRST)**:
  **DO NOT jump to a Databricks Job.** Instead:
  1. Create a notebook on a **16.4 LTS ML** interactive cluster
  2. Cell 1: `%pip install databricks-langchain langgraph langchain-core databricks-agents`
     then `dbutils.library.restartPython()`
  3. Cell 2: Test the agent locally — `GRAPH.invoke({"messages": [...]})` 
  4. Cell 3: `mlflow.pyfunc.log_model(python_model=agent_file, ...)`
  5. Cell 4: Verify the model registered successfully in UC
  6. **Only after all cells succeed**, optionally convert to a reusable job.

  Both `mlflow.pyfunc.log_model()` and `mlflow.langchain.log_model()` import
  agent.py during logging. The `%pip install` in Cell 1 ensures deps are available.

  **Step 3 — Deploy the serving endpoint**:
  From the same notebook or a new cell:
  - If an existing endpoint has a **different model type** (langchain vs pyfunc),
    delete it first: `WorkspaceClient().serving_endpoints.delete(name)`
  - Use `databricks.agents.deploy(model_name, version)` to create/update
  - Set `scale_to_zero_enabled=True` for development
  - Wait for endpoint to reach READY state (~15 minutes)

  **Step 4 — (Optional) Create a Multi-Agent Supervisor**:
  If the architecture analysis identified multiple independent agent
  endpoints (e.g., the super agent + a Genie space + a KA), create
  a MAS using the `agent-bricks` skill's `create_or_update_mas` tool.
  - Wire the super agent endpoint, Genie spaces, and KAs as sub-agents
  - Add routing instructions and example questions from the PRD
  - Skip this step if the super agent alone handles all routing internally

  **Step 5 — Wire endpoint into the app**:
  Update (create new) config files (`app.yaml`, `env.example`) to include
  the deployed endpoint name as an environment variable.
  Update (create new) backend routes to call the deployed endpoint
  via `query_serving_endpoint` or the Databricks SDK.

  **Step 6 — Validate**:
  Query the deployed endpoint with test inputs from Phase 2's test script.
  Verify responses, latency, and tool-call traces.

### Phase 4: Test
Use the **agent-tester** subagent from `agentic-framework/agents/`.

- Derive all test scenarios from the PRD user journeys — do not invent
  test cases outside the PRD.
- Read `docs/agent_architecture.md` for the tool mapping matrix.
- Test in this order:

  **Step 1 — Unit tests**: Each tool module in isolation.
  **Step 2 — Orchestrator tests**: Super agent locally with mock tools.
  **Step 3 — Integration tests**: Super agent calling live tools
  (Genie, UC functions, LLM endpoint) via the deployed endpoint.
  **Step 4 — End-to-end tests**: Full flow from UI API route → deployed
  endpoint → tool execution → response.
  **Step 5 — Evaluation harness**: If the `agent-evaluation` skill is
  available, run the MLflow evaluation framework against the test set.

- Validate:
  - Routing correctness (right tool called for each query type)
  - Response schema matches the UI's expected format
  - Fallback chains work when primary tools fail
  - Latency meets NFR targets from the PRD
  - MLflow traces are captured for each request

## Rules

- Every subagent must discover project context by scanning files, not
  from this prompt.
- Never hardcode resource IDs, table names, or endpoint URLs.
- Use environment variables for all credentials and service identifiers.
- If the PRD is missing Databricks Services or Agent Routing Hints
  sections, flag it as a gap in Phase 1 and proceed with what is available
  from config files and workspace queries.
- If a required resource (Genie space, UC function, UC table) does not
  exist, report it as a gap and ask the user — do not create it.
- Prefer the `ResponsesAgent` + LangGraph pattern from
  `https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/model-serving/3-genai-agents.md`.
- The super agent must be a single deployable unit; individual tools
  are Python functions called within the agent, not separate endpoints.

## Skills Reference

These `https://github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/` are relevant — subagents should read them for
implementation patterns:

| Skill | When to Read | Used By |
|-------|-------------|---------|
| `model-serving/` | **Agent structure (`ResponsesAgent`), logging (`pyfunc.log_model`), deployment, querying** | Phase 2, 3 |
| `databricks-app-python/` | **App-to-endpoint auth (`Config().authenticate()`), `valueFrom` resources, deployment** | Phase 3, 5 |
| `agent-bricks/` | MAS creation, Genie/KA integration | Phase 1, 3 |
| `databricks-genie/` | Genie Space query patterns, Conversation API | Phase 1, 2 |
| `databricks-unity-catalog/` | UC object discovery, function listing | Phase 1 |
| `agent-evaluation/` | Evaluation harness for agent quality | Phase 4 |
| `instrumenting-with-mlflow-tracing/` | Tracing and observability | Phase 2 |
| `databricks-config/` | Workspace auth and configuration | Phase 3 |
| `databricks-python-sdk/` | SDK patterns for Databricks APIs | Phase 2, 3 |
| `databricks-jobs/` | Job creation, cluster config, spark_python_task constraints | Phase 3 |

Also read any **project-local skills** in `agentic-framework/skills/` — these capture
hard-won lessons specific to this project (e.g., `databricks-job-runner/SKILL.md`).

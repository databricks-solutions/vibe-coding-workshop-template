Build a multi-agent orchestrator for this project using Databricks Foundation Models.

## Objective

Create a **super agent** — a backend agentic loop that uses a Databricks-hosted
Foundation Model (e.g., `databricks-meta-llama-3-3-70b-instruct`) with **function
calling** to orchestrate tool execution. The Foundation Model acts as the brain;
your backend code executes the tools and manages the conversation loop.

**This approach eliminates custom model deployment entirely.** No MLflow logging,
no Unity Catalog registration, no `agents.deploy()`, no serving endpoint creation.
The Foundation Model is already hosted and running — you just call it with tools.

## Architecture

```
User → Frontend → FastAPI Backend → Foundation Model API (with tools defined)
                         ↕                    ↕
                   Tool Execution        Tool call instructions
                   (Genie, Python)       (returned by model)
```

The backend implements a **tool-calling loop**:
1. Send user message + system prompt + tool definitions to the Foundation Model
2. If the model returns tool calls → execute them locally → send results back
3. Repeat until the model returns a final text response (no more tool calls)
4. Return the response to the user

## Required Skill Reading (READ BEFORE BUILDING)

| Order | Skill | File(s) | Why |
|-------|-------|---------|-----|
| 1 | `databricks-app-python/` | `2-app-resources.md` | **App-to-endpoint auth**: `Config().authenticate()` + `requests.post()` for calling Foundation Model endpoints |
| 2 | `databricks-app-python/` | `SKILL.md` | App deployment, framework selection, port config |
| 3 | `databricks-genie/` | `conversation.md` | Genie Conversation API patterns for the Genie tool |

**No model-serving, MLflow, or job-runner skills are needed** — the Foundation Model
is already deployed by Databricks.

## Constraints (READ FIRST)

- **DO NOT** create any Genie spaces. Discover and use existing ones.
- **DO NOT** create any Unity Catalog functions, tables, or catalogs.
- **DO NOT** register or deploy any custom models. Use the hosted Foundation Model directly.
- **DO** discover all pre-existing Databricks resources by analyzing the project folder.
- **DO** ask the user for confirmation before modifying or overwriting existing files.
- Use environment variables for all credentials and service identifiers.

## Chain

### Phase 1: Analyze
Use the **prd-analyzer** subagent from `agentic-framework/agents/`.

- Scan the project: `docs/`, config files (`app.yaml`, `env.example`, `.env`,
  `pyproject.toml`), `server/routers/`, and any existing `server/agents/` directory.
- Analyze the PRD found in `docs/`.
- **Inventory existing Databricks resources** by analyzing the project folder:
  - Genie spaces (record space IDs, names, tables)
  - Foundation Model endpoints (record endpoint names like `databricks-meta-llama-3-3-70b-instruct`)
  - UC schemas and tables referenced in config files
- Classify each PRD requirement into a tool type:
  - **Genie tool**: Requirements answerable via SQL over existing tables
  - **LLM-native**: Requirements the Foundation Model handles directly (intent
    classification, summarization, conversational responses) — NO separate tool needed
  - **Custom Python tool**: Business logic, computation, date math, external API calls
- Output the analysis to `docs/agent_architecture.md`, including:
  1. Existing resource inventory
  2. Architecture pattern (Foundation Model with function calling)
  3. Requirement → tool mapping matrix
  4. Tools to build (only Genie wrapper + custom Python tools)
  5. Gaps: any requirement needing a resource that doesn't exist

### Phase 2: Scaffold
Use the **skill-scaffolder** subagent from `agentic-framework/agents/`.

- Read `docs/agent_architecture.md` (Phase 1 output).

  **Step 1 — Tool modules** (plain Python functions):
  Create under `server/agents/tools/`:
  - **Genie query tool**: Calls the Genie Conversation API for database queries.
    Reads `GENIE_SPACE_ID` from environment variables.
  - **Custom Python tools**: Business logic (e.g., price calculation, date
    validation, confirmation number generation).
  - **NO separate LLM tools needed** — the Foundation Model handles NL
    understanding, classification, and summarization natively as part of its
    response. Don't create tools for things the LLM already does.

  Each tool module should:
  - Define a plain Python function with clear docstring
  - Define a matching JSON schema (OpenAI function-calling format) for the
    Foundation Model to understand when/how to call it
  - Handle errors gracefully (return error strings, never raise)

  **Step 2 — Agent loop (`server/agents/agent_loop.py`)**:
  Create a plain Python module that:
  - Defines `SYSTEM_PROMPT` derived from the PRD
  - Defines `TOOL_SCHEMAS` (list of tool definitions in OpenAI format)
  - Defines `TOOL_FUNCTIONS` (dispatch dict mapping tool names to functions)
  - Implements `async def run_agent_loop(user_message, cfg)` that:
    1. Calls the Foundation Model endpoint with system prompt + user message + tools
    2. If the response contains tool_calls → executes each tool → appends results
    3. Loops until the model returns a final text response (max 10 iterations)
    4. Returns the final response text
  - Uses `Config().authenticate()` + `requests.post()` for endpoint calls
  - All errors caught and returned as user-friendly messages

  **Step 3 — Wire into API routes (`server/routers/api.py`)**:
  Update the existing API routes to call `run_agent_loop()` directly:
  - `POST /search/natural-language` → agent loop
  - `POST /search/agent` → agent loop
  - Remove `_query_agent()` (HTTP call to serving endpoint)
  - Keep fallback logic for when the LLM endpoint is unavailable

  **Step 4 — Test script (`test_agent.py`)**:
  Create a local test script that calls `run_agent_loop()` with sample queries
  and validates tool execution.

### Phase 3: Deploy
Use the **databricks-deployer** subagent from `agentic-framework/agents/`.

Deployment is **dramatically simpler** — no model registration, no serving endpoint:

  **Step 1 — Update `app.yaml`**:
  - Ensure `LLM_ENDPOINT_NAME` and `GENIE_SPACE_ID` are set
  - **Remove** `AGENT_ENDPOINT_NAME` (no separate agent endpoint)
  - Add the Foundation Model endpoint as an app resource for auth

  **Step 2 — Deploy the Databricks App**:
  - Sync files to workspace
  - Deploy via `databricks apps deploy`
  - The app calls the Foundation Model directly — no other endpoints to manage

  **Step 3 — Validate**:
  - Test via the app's API endpoints
  - Verify tool calling works (Genie queries, price calculations, date validation)

### Phase 4: Test
Use the **agent-tester** subagent from `agentic-framework/agents/`.

- Test tool routing (does the model call the right tool for each query type?)
- Test error handling (what happens when Genie is unavailable?)
- Test multi-turn tool calling (model calls tool → gets result → calls another tool)
- Test latency (direct FM call should be faster than the custom endpoint approach)

## Rules

- Every subagent must discover project context by scanning files.
- Never hardcode resource IDs, table names, or endpoint URLs.
- Use environment variables for all credentials and service identifiers.
- The Foundation Model handles intent classification, summarization, and
  conversational responses natively — do NOT create separate tools for these.
- Tools should ONLY be created for things the LLM cannot do: database queries
  (Genie), business logic (price math), and side effects (booking IDs).
- All tool functions must catch exceptions and return error strings.

## Skills Reference

| Skill | When to Read | Used By |
|-------|-------------|---------|
| `databricks-app-python/` | **App auth, deployment, framework** | Phase 2, 3 |
| `databricks-genie/` | **Genie Space query patterns** | Phase 1, 2 |
| `databricks-config/` | Workspace auth and configuration | Phase 3 |
| `databricks-python-sdk/` | SDK patterns for Databricks APIs | Phase 2 |

Also read any **project-local skills** in `agentic-framework/skills/`.

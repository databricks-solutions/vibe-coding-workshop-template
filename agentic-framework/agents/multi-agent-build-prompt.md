Build a multi-agent orchestrator for this project using Databricks Foundation Models.

## Objective

Create a **supervisor agent** — a backend agentic loop that uses a Databricks-hosted
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

## Prerequisites (MUST COMPLETE FIRST)

Before starting this build, ensure all Databricks resources are created and validated.
Follow `docs/pre-req.md` and complete every item in its Section 7 Readiness Checklist:

- [ ] UC tables created and seeded (gold-layer listing data)
- [ ] UC functions (TVFs) created and returning results
- [ ] Genie Space created, configured, and answering queries via API
- [ ] Lakebase instance running with tables created
- [ ] Foundation Model endpoint reachable and supports function calling
- [ ] All environment variables collected

**DO NOT proceed to Step 1 unless all prerequisites pass.**

## Required Skill Reading (READ BEFORE BUILDING)

| Order | Skill | File(s) | Why |
|-------|-------|---------|-----|
| 1 | `databricks-app-python/` | `2-app-resources.md` | **App-to-endpoint auth**: `Config().authenticate()` + `requests.post()` |
| 2 | `databricks-genie/` | `conversation.md` | Genie Conversation API patterns for the Genie tool |
| 3 | `foundation-model-agent-loop/` | `SKILL.md` (local) | **Canonical agent loop pattern** — reference code for `agent_loop.py` |

**No model-serving, MLflow, or job-runner skills are needed.**

## Constraints (READ FIRST)

- **DO NOT** create any Genie spaces, UC functions, tables, or catalogs — use existing ones from pre-req.
- **DO NOT** register or deploy any custom models.
- **DO NOT** create separate LLM tools for parsing, classification, or summarization — the FM handles these natively.
- **DO** discover all pre-existing Databricks resources by analyzing the project folder.
- **DO** ask the user for confirmation before modifying or overwriting existing files.
- Use environment variables for all credentials and service identifiers.

## Build Steps

Each step produces **exactly one artifact** and has **one validation gate**. Complete
each gate before proceeding to the next step.

### Step 1: Analyze PRD

**Subagent:** prd-analyzer (`agentic-framework/agents/prd-analyzer.md`)

**Input:** `docs/design_prd.md` + project config files (`app.yaml`, `.env.example`)

**Task:**
- Scan the project: `docs/`, config files, `server/routers/`, `server/agents/`
- Analyze the PRD
- Inventory existing Databricks resources from config files:
  - Genie Space ID (from `GENIE_SPACE_ID` in `app.yaml`)
  - FM endpoint name (from `LLM_ENDPOINT_NAME` in `app.yaml`)
  - UC tables and TVFs (from `docs/pre-req.md` if available)
- Classify each PRD requirement into a tool type:
  - **Genie tool**: Requirements answerable via SQL (listing search, availability, reviews)
  - **LLM-native**: Requirements the FM handles directly (intent classification, summarization, conversation) — NO separate tool needed
  - **Custom Python tool**: Business logic (price calculation, date validation, confirmation numbers)

**Output:** `docs/agent_architecture.md` — rewritten to match FM approach

**Gate:** User reviews and approves the architecture document before proceeding.

---

### Step 2a: Build Genie Tool (parallel with 2b)

**Subagent:** tool-builder (`agentic-framework/agents/tool-builder.md`)

**Input:** Tool specification for `query_genie` from `docs/agent_architecture.md`

**Task:**
- Create `server/agents/tools/genie_tool.py`
- Implement `query_genie_fn(question: str) -> str`
- Use `WorkspaceClient().genie.start_conversation_and_wait()`
- Read `GENIE_SPACE_ID` from environment
- **CRITICAL**: Guard against `None` responses — `get_message_query_result()` may return
  `None` for `statement_response` or `manifest` when Genie gives a text-only answer.
  Always check for `None` before accessing `.manifest.schema.columns`.
- Support `APP_MOCK_MODE=true` with canned data
- Define the matching JSON schema in OpenAI function-calling format

**Output:** `server/agents/tools/genie_tool.py`

**Gate:**
```bash
APP_MOCK_MODE=true python3 -c "from server.agents.tools.genie_tool import query_genie_fn; print(query_genie_fn('test'))"
```
Must print valid JSON without errors.

---

### Step 2b: Build Custom Tools (parallel with 2a)

**Subagent:** tool-builder (`agentic-framework/agents/tool-builder.md`)

**Input:** Tool specifications for business logic from `docs/agent_architecture.md`

**Task:**
- Create `server/agents/tools/custom_tools.py`
- Implement:
  - `calculate_booking_price_fn(nightly_rate, num_nights, ...)` — price breakdown
  - `validate_dates_fn(check_in, check_out)` — date validation
  - `generate_confirmation_number_fn()` — booking reference (SF-XXXXXXXX)
- Pure Python — no external services, no mock mode needed
- Define matching JSON schemas in OpenAI function-calling format

**Output:** `server/agents/tools/custom_tools.py`

**Gate:**
```bash
python3 -c "from server.agents.tools.custom_tools import calculate_booking_price_fn; print(calculate_booking_price_fn(nightly_rate=150, num_nights=3))"
```
Must print valid JSON with price breakdown.

---

### Step 3: Build Agent Loop

**Reference:** Read `agentic-framework/skills/foundation-model-agent-loop/SKILL.md` for the canonical implementation pattern.

**Input:** Tools from Steps 2a and 2b + the SKILL.md reference

**Task:**
- Create `server/agents/agent_loop.py`
- Define `SYSTEM_PROMPT` derived from the PRD (who the agent is, what it can do)
- Define `TOOL_SCHEMAS` — list of all tool JSON schemas
- Define `TOOL_FUNCTIONS` — dispatch dict mapping tool names to functions
- Implement `def run_agent_loop(user_message: str) -> str:` following the SKILL.md pattern:
  1. Build messages list with system prompt + user message
  2. Call Foundation Model via `Config().authenticate()` + `requests.post()`
  3. Parse response — check for `tool_calls`
  4. If tool_calls → execute → append results → loop
  5. If `finish_reason == "stop"` → return content
  6. Safety cap at max 10 iterations
- **Synchronous** (not async) — `requests.post()` is blocking
- All errors caught and returned as user-friendly messages

**Output:** `server/agents/agent_loop.py`

**Gate:**
```bash
APP_MOCK_MODE=true python3 -c "from server.agents.agent_loop import run_agent_loop; print(run_agent_loop('Find apartments in Austin'))"
```
Must return a string response without errors.

---

### Step 4: Test Agent Loop Live

**Subagent:** agent-tester (`agentic-framework/agents/agent-tester.md`) — Mode 2 (Loop Test)

**Input:** `server/agents/agent_loop.py` + live FM endpoint

**Task:**
- Run the 5 test queries from agent-tester Mode 2
- Verify tool routing: data queries trigger `query_genie`, price queries trigger `calculate_booking_price`
- Verify conversational queries are handled by FM directly (no tool calls)
- Verify error handling for empty/invalid inputs

**Output:** Test results — pass/fail per query type

**Gate:** At least 3 out of 5 test queries return coherent responses with correct tool routing.

---

### Step 5: Deploy

**Subagent:** databricks-deployer (`agentic-framework/agents/databricks-deployer.md`)

**Input:** All files from Steps 1-4

**Task:**
- Verify `app.yaml` has correct env vars and `resources:` block
- Stage files (exclude `node_modules/`, `.databricks/`, `src/`, `__pycache__/`)
- Upload to workspace via `databricks workspace import-dir`
- Deploy via `databricks apps deploy`

**Output:** Running Databricks App

**Gate:**
```bash
curl -s https://<app-url>/api/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('PASS' if d.get('status')=='healthy' else 'FAIL')"
```

---

## Step Dependency Diagram

```
Prerequisites (docs/pre-req.md)
        │
   Step 1: Analyze PRD
        │
   ┌────┴────┐
   │         │
Step 2a    Step 2b     ← parallel
(Genie)   (Custom)
   │         │
   └────┬────┘
        │
   Step 3: Agent Loop
        │
   Step 4: Test Live
        │
   Step 5: Deploy
```

## What Comes After

After this build is complete and the agent is deployed and tested:
- **Part 2 (separate prompt):** Wire the agent to the existing UI using
  `agentic-framework/agents/agent-ui-wiring-prompt.md`

## Dependencies

Only these packages are needed. **Do NOT add** `langgraph`, `langchain-*`,
`databricks-langchain`, `databricks-agents`, or `mlflow`.

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
databricks-sdk>=0.20.0
requests>=2.31.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

## Rules

- Every subagent must discover project context by scanning files.
- Never hardcode resource IDs, table names, or endpoint URLs.
- Use environment variables for all credentials and service identifiers.
- The Foundation Model handles intent classification, summarization, and
  conversational responses natively — do NOT create separate tools for these.
- Tools should ONLY be created for things the LLM cannot do: database queries
  (Genie), business logic (price math), and side effects (booking IDs).
- All tool functions must catch exceptions and return error strings.
- **One file per step, one gate per step.** Do not combine multiple steps.

## Subagents Reference

| Subagent | File | Used In |
|----------|------|---------|
| prd-analyzer | `agentic-framework/agents/prd-analyzer.md` | Step 1 |
| tool-builder | `agentic-framework/agents/tool-builder.md` | Steps 2a, 2b |
| agent-tester | `agentic-framework/agents/agent-tester.md` | Step 4 |
| databricks-deployer | `agentic-framework/agents/databricks-deployer.md` | Step 5 |

## Skills Reference

| Skill | When to Read | Used By |
|-------|-------------|---------|
| `databricks-app-python/` | App auth, deployment, framework | Steps 3, 5 |
| `databricks-genie/` | Genie Space query patterns | Steps 1, 2a |
| `foundation-model-agent-loop/` (local) | **Canonical agent loop pattern** | Step 3 |

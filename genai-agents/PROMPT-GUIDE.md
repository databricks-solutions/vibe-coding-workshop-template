# Prompt Guide: Building GenAI Agents on Databricks (Canonical Path)

A step-by-step prompt cookbook for building a production GenAI agent on
Databricks using the **canonical 2-Apps shape**: an AppKit dashboard App in
front of a Python Agent App, wired together with on-behalf-of (OBO)
authentication, and grounded in MLflow 3 for tracing, evaluation, and
deployment.

Each prompt is designed to be **pasted directly into an AI coding assistant**
(Cursor, Claude Code, or similar). The agent reads the referenced skill file
and implements the step for you.

> **Canonical = Track A + AppKit + KA + Genie + Lakebase memory.**
> Other shapes (Supervisor API, Model Serving wrap, Node-native end-to-end,
> single-App template UI) are alternate methods. This template keeps the root
> course focused on Track A; the previously bundled B/C/capstone mirrors have
> been removed during the 2026-04-27 consolidation. For canonical
> Databricks-platform reference patterns see
> [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills).

**How to use this guide:**

1. Complete the prerequisites in Section 0. **Genie Code users:** do the **Set Up Project** clone first — see the client fork just before Section 0.
2. Fill in the `{placeholders}` in each prompt with your values.
3. Paste the prompt into your IDE. The agent does the rest.
4. Check off the **Expected Output** items to confirm the step is done.
5. Move to the next prompt.

**Note:** All skill paths in the prompts below (e.g.
`00-course-orchestrator/SKILL.md`) are **relative to this directory**
(`genai-agents/`) unless they begin with `apps_lakebase/`,
`data_product_accelerator/`, etc. — those are repo-root relative.

---

## Canonical pipeline at a glance

| Section | Module | Prompts | Time |
|---|---|---|---|
| 0 | Workspace Setup | P0 | ~15 min |
| 1 | AppKit App + Lakebase Baseline | P1–P5 | ~2 hr |
| 1b | Agent Design (Track A only) | P5a–P5b | ~45 min |
| 2 | Foundation (MLflow + Experiment + Tools) | P6–P8 | ~2 hr |
| 3 | Tool Catalog (KA + Genie + UC functions) | P9–P11 | ~2 hr |
| 4 | Track A Agent Build (Apps + OBO + memory) | P12–P18 | ~5 hr |
| 5 | Wire AppKit ↔ Agent App (OBO proxy) | P19–P20 | ~1.5 hr |
| 6 | SDLC Pipeline (eval, register, deploy, monitor) | P21–P27 | ~6 hr |
| 7 | Capstone (optional) | P28 | ~2 hr |
| 8 | Alternate methods (pointer) | — | — |

### Visual flow

```
P0 Workspace
   │
   ▼
[P1-P5] AppKit App + Lakebase    ◀── apps_lakebase/skills/01..05
   │
   ▼
[P6-P8] Foundation (F1..F3)      ◀── genai-agents/foundation/01..03
   │
   ▼
[P9-P11] Tool Catalog            ◀── F5 KA + Genie Space + UC funcs
   │
   ▼
[P12-P18] Track A Agent          ◀── tracks/A-custom-agent-apps/01..07
   │                                   (Option B @invoke/@stream + OBO
   │                                    + agent-openai-advanced memory)
   ▼
[P19-P20] AppKit ↔ Agent proxy   ◀── apps_lakebase/skills/06d, 07, 08
   │                                   (OBO forwarding + chat history
   │                                    + feedback)
   ▼
[P21-P27] SDLC Pipeline          ◀── genai-agents/sdlc/01..07
   │
   ▼
[P28] Capstone (optional)
```

---

> **Client fork — pick your path before Section 0.**
> - **IDE/CLI (Cursor, Claude Code, VS Code, Codex):** complete the Databricks CLI auth + prerequisite checks in Section 0 below.
> - **Genie Code (in-workspace):** Genie Code is pre-authenticated and serverless — skip the CLI auth steps. First, **Set Up Project**: clone the whole repo into `/Users/<your-username>/.assistant/skills/vibe-coding-workshop`, then **start a NEW Agent-mode chat thread** (hard-refresh if skills don't appear) so the skills load, and load `skills/genie-code-environment`; `skills/vibecoding-state` detects `client_context` and gates each prompt. See [repo-root AGENTS.md](../AGENTS.md) ("Genie Code" section) / [PRE-REQUISITES.md](../PRE-REQUISITES.md). Grounded in the [Genie Code skills docs](https://learn.microsoft.com/en-us/azure/databricks/genie-code/skills).

## Section 0: Workspace Setup

### Prompt P0 — Verify workspace and gather core values

Run these commands (requires Databricks CLI authenticated):

```bash
databricks auth token
databricks schemas create --catalog main --name my_agent_project
databricks warehouses list --output json | python3 -c "
import sys, json
for w in json.load(sys.stdin):
    print(f\"{w['id']}  {w['name']}  ({w['state']})\")"
databricks apps list
databricks serving-endpoints list --output json | python3 -c "
import sys, json
for e in json.load(sys.stdin):
    print(f\"{e['name']}  ({e.get('state', {}).get('ready', 'UNKNOWN')})\")"
```

Record these values — every later prompt reads them from your state file:

| Value | Your value | Where you got it |
|-------|-----------|-------------------|
| `{catalog}` | __________ | `main` or your UC catalog |
| `{schema}` | __________ | Created above |
| `{warehouse_id}` | __________ | `warehouses list` output |
| `{appkit_app_name}` | __________ | Your choice (e.g. `loyalty-dashboard`) |
| `{agent_app_name}` | __________ | Your choice (e.g. `loyalty-agent`) |
| `{agent_name}` | __________ | Logical agent name (e.g. `loyalty-assistant`) |
| `{experiment_path}` | __________ | Your choice (e.g. `/Shared/loyalty-agent/traces`) |
| `{llm_endpoint}` | __________ | `databricks-claude-sonnet-4-6` (or your Foundation Model endpoint) |
| `{ka_endpoint_name}` | _filled by P9_ | Returned by F5 Knowledge Assistant skill |
| `{knowledge_assistant_id}` | _filled by P9_ | Returned by F5 Knowledge Assistant skill |
| `{genie_space_id}` | _filled by P10_ | Returned by Genie Space skill |
| `{lakebase_instance}` | _filled by P3_ | Returned by `apps_lakebase/skills/05-appkit-lakebase-wiring` |

### Prerequisites check

```bash
databricks auth token > /dev/null 2>&1 && echo "CLI: OK" || echo "CLI: FAILED"
uv --version > /dev/null 2>&1 && echo "uv: OK" || echo "uv: MISSING"
node --version 2>/dev/null | grep -q "v2[2-9]" && echo "Node: OK" || echo "Node: NEEDS v22+"
python3 -c "import sys; assert sys.version_info >= (3,11)" && echo "Python: OK"
python3 -c "import mlflow; v=mlflow.__version__; print(f'MLflow: {v}'); assert tuple(map(int,v.split('.')[:2])) >= (3,10)" 2>/dev/null || echo "MLflow: NEEDS 3.10+"
```

All five must pass before continuing.

---

## Section 1: AppKit App + Lakebase Baseline

The canonical front door is an AppKit application on Databricks Apps with a
Lakebase-backed CRUD layer. This is the same baseline regardless of which
agent shape you eventually pick — it always comes first.

### Prompt P1 — Scaffold AppKit project

> Scaffold a new AppKit project for `{appkit_app_name}`. Walk me through the
> generated structure (server, frontend, plugins, app.yaml). Load
> `apps_lakebase/skills/01-appkit-scaffold/SKILL.md`.

**Expected:** Project directory created, dependencies installed, dev server starts.

### Prompt P2 — Build the dashboard

> Build the dashboard for `{appkit_app_name}` against my data in
> `{catalog}.{schema}` using SQL Warehouse `{warehouse_id}`. Implement the
> pages and components per my product spec. Load
> `apps_lakebase/skills/02-appkit-build/SKILL.md`.

**Expected:** Dashboard renders locally, all pages reachable, lint passes.

### Prompt P3 — Deploy AppKit App

> Deploy `{appkit_app_name}` to Databricks Apps. Capture the App URL into
> state. Load `apps_lakebase/skills/03-appkit-deploy/SKILL.md`.

**Expected:** App in `RUNNING` state; `appkit_app_url` captured.

### Prompt P4 — Add the Lakebase plugin

> Add the AppKit Lakebase plugin to `{appkit_app_name}`. Load
> `apps_lakebase/skills/04-appkit-plugin-add/SKILL.md`.

**Expected:** Plugin registered, `app.yaml` updated, types regenerated.

### Prompt P5 — Wire Lakebase backend (instance, schema, OBO/SP)

> Provision a Lakebase instance for `{appkit_app_name}`, create the schema,
> wire the AppKit plugin to read/write per-user data via OBO with SP
> fallback. Load `apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md`.

**Expected:** `lakebase_instance`, `lakebase_database` captured; CRUD smoke test passes locally and after redeploy.

---

## Section 1b: Agent Design (Track A only)

These prompts run after the AppKit/Lakebase baseline and before Foundation when
you are building a Track A agent. They produce planning artifacts in `docs/`,
not code or Databricks resources. Skip this section for non-agent workshops.

### Prompt P5a — Agent Spec Design

> Generate `docs/agent_spec.yaml` from `docs/design_prd.md`. Use
> `foundation/00b-agent-spec-and-tool-plan/SKILL.md`. If I ask for MCP web
> research, use web search and record recommendations with source URLs. Do not
> create code or resources.

**Expected:** `docs/agent_spec.yaml` exists; agent purpose, personas, capabilities, tool recommendations, MCP research, KA recommendation, and governance rules are populated.

### Prompt P5b — Agent Tool Selection

> Generate `docs/agent_tool_plan.yaml` from `docs/agent_spec.yaml`. If I provide
> `{agent_sql_catalog}` and `{agent_sql_schema}`, include SQL MCP as a read-only
> tool over those Unity Catalog tables using warehouse `{warehouse_id}`. Do not
> create code or resources.

**Expected:** `docs/agent_tool_plan.yaml` exists; every selected tool has a smoke test; SQL MCP carries read-only guardrails; KA is selected or explicitly skipped.

---

## Section 2: Foundation

### Prompt P6 — F1: MLflow GenAI Foundation

> Set up MLflow GenAI for `{agent_name}`: install `mlflow[databricks]>=3.10.1`,
> enable OpenAI autolog at module level, create a shared WorkspaceClient
> pattern, add a `detect_environment()` helper covering local / Databricks
> Apps / notebook. Load `foundation/01-mlflow-genai-foundation/SKILL.md`.

**Expected:** `mlflow.openai.autolog()` active, `detect_environment()` exported.

### Prompt P7 — F2: Experiment Tracing + UC Storage

> Create the MLflow experiment at `{experiment_path}`, configure UC OTEL
> trace storage (`{catalog}.{schema}`, prefix `{agent_name}`, warehouse
> `{warehouse_id}`), enable `@mlflow.trace`, set
> `mlflow.promptRegistryLocation`, emit GRANT SQL. Load
> `foundation/02-experiment-tracing-and-uc-storage/SKILL.md`.
>
> **If your stack is Node-native** (AppKit-integrated agents, Node-only
> Apps), also load `foundation/02b-typescript-tracing/SKILL.md` for the
> official `mlflow-tracing` + `mlflow-openai` npm path (`mlflow.init`,
> `tracedOpenAI`, `mlflow.trace`, `withSpan`, sessions). Treat any
> vendor-neutral OTLP fallback as custom exploration; the old integrated-agent
> path is not bundled in this template.
>
> **Before deploying**, also load
> `foundation/02-experiment-tracing-and-uc-storage/references/prod-tracing-deployment.md`
> for the production env-var matrix (`ENABLE_MLFLOW_TRACING`,
> `MLFLOW_EXPERIMENT_ID`, `APP_ENVIRONMENT`, SP `CAN_EDIT`) and the
> Git-folder caveat.
>
> **If you need user / session / environment context on traces** (for
> attribution, conversation grouping, or environment cohorts), load
> `foundation/02c-trace-context-and-environments/SKILL.md`. It's the
> canonical reference for `mlflow.trace.user` / `mlflow.trace.session`
> as **metadata** (not tags), the `APP_ENVIRONMENT` → `mlflow.source.type`
> override pattern, custom deployment metadata (`agent_version`,
> `deployment_id`), and how this composes with `client_request_id` and
> `gen_ai.*` span attributes. Applies to both Python (F2) and Node
> (F2b) handlers.

**Expected:** Experiment visible, 4 OTEL Delta tables created, test trace lands in UC. (Node stacks: `mlflow.init` + `tracedOpenAI` produces traces from a Node-native handler with no OTel collector.)

### Prompt P8 — F3: Tools + Data Access (concepts)

> Install `databricks-mcp`, walk through Databricks managed MCP servers
> (Vector Search, Genie, SQL, UC Functions), explain `_meta` parameters,
> and identify the resource grants my agent will need. Load
> `foundation/03-tools-and-data-access/SKILL.md`.

**Expected:** `databricks-mcp` importable; resource-grant plan written down.

---

## Section 3: Tool Catalog (KA + Genie + UC functions)

The canonical SkyLoyalty / Track A agent uses three Databricks-managed tools:
**Knowledge Assistant** for documents, **Genie Space** for analytics, and
**UC functions** for governed deterministic lookups.

### Prompt P9 — F5: Knowledge Assistant lifecycle

> Create a Databricks Agent Bricks Knowledge Assistant for `{agent_name}`.
> My knowledge source is {describe: a UC Volume at
> `/Volumes/{catalog}/{schema}/docs`, OR a Vector Search index
> `{catalog}.{schema}.{index_name}` on `databricks-gte-large-en`}. Sync,
> poll until ready, and capture both `ka_endpoint_name` and
> `knowledge_assistant_id` into state. Load
> `foundation/05-knowledge-assistant/SKILL.md`.

**Expected:** `ka_endpoint_name` and `knowledge_assistant_id` captured.

### Prompt P10 — Genie Space (data product)

> Create (or import) a Genie Space for `{agent_name}` over my analytics
> tables in `{catalog}.{schema}` against warehouse `{warehouse_id}`. Capture
> `genie_space_id`. If the space already exists, use the export/import
> skill to reuse its YAML. Load
> `data_product_accelerator/skills/semantic-layer/03-genie-space-patterns/SKILL.md`
> (and `04-genie-space-export-import-api/SKILL.md` if importing).

**Expected:** `genie_space_id` captured; smoke query returns rows.

### Prompt P11 — UC functions (deterministic tools)

> For any deterministic ad-hoc lookups my agent needs (e.g. `get_member`,
> `apply_policy_rule`), define them as governed UC functions. Emit `databricks.yml`
> resource declarations and the GRANT SQL needed. Load
> `foundation/03-tools-and-data-access/SKILL.md` (UC functions section).

**Expected:** Each UC function defined, granted, and reachable from the workspace.

---

## Section 4: Track A — Custom Agent on Databricks Apps

This is the canonical agent shape: a Python `@invoke`/`@stream` handler
deployed as a Databricks App, with KA + Genie + UC functions wired as
function tools, OBO authentication, and Lakebase short-term + long-term
memory.

### Prompt P12 — A1: Clone and run an agent template

> Clone the **`agent-openai-advanced`** template (canonical for the
> SkyLoyalty walkthrough — already includes the two-layer Lakebase memory
> pattern). Set up `my-agent-app`, install deps, start the local dev server.
> Walk through the project structure. Load
> `tracks/A-custom-agent-apps/01-clone-and-run/SKILL.md`.

**Expected:** Template runs locally, chat UI responds.

### Prompt P13 — A2: Agent framework (Option B)

> Implement my agent in the cloned project using the canonical pattern:
> module-level `@mlflow.genai.agent_server.invoke` and
> `@mlflow.genai.agent_server.stream` handlers (Option B for Databricks
> Apps). The agent should {describe what it does}. Use the OpenAI Agents
> SDK's `Agent` and `Runner` inside the handlers. Verify MLflow `AGENT`
> spans appear at `{experiment_path}`. Load
> `tracks/A-custom-agent-apps/02-agent-framework/SKILL.md`.

**Expected:** `@invoke` and `@stream` defined; streaming works locally; AGENT spans land in MLflow.

### Prompt P14 — A3: Wire tools (KA + Genie + UC functions)

> Wire my Tool Catalog into `{agent_name}`: KA via `ka_endpoint_name`
> (function tool calling `serving_endpoints.query`), Genie via
> `genie_space_id` (function tool calling the Genie REST API), and UC
> functions. Emit `databricks.yml` resource grants (KA: `CAN_QUERY`, Genie:
> `CAN_RUN`, warehouse: `CAN_USE`) and `app.yaml` `valueFrom` bindings.
> Load `tracks/A-custom-agent-apps/03-tools-and-mcp/SKILL.md`.

**Expected:** TOOL spans for KA, Genie, and each UC function appear in traces.

### Prompt P15 — A4: Authentication (OBO inside `@invoke`)

> Configure auth for `{agent_name}`. App-level auth = service principal,
> user-level auth = OBO via `databricks_app.utils.get_user_workspace_client(http_request)`
> called inside `@invoke`/`@stream` handlers. Declare `user_api_scopes` in
> `app.yaml` for least privilege (serving-endpoints, dashboards.genie,
> sql.statement-execution, catalog.connections). Load
> `tracks/A-custom-agent-apps/04-authentication/SKILL.md`.

**Expected:** OBO scoped client used per-request; SP fallback works locally; `user_api_scopes` declared.

### Prompt P16 — A5: Lakebase memory (short-term + long-term)

> Wire two-layer Lakebase memory per the **`agent-openai-advanced`** template:
> `AsyncDatabricksSession` for short-term thread state and `LongTermMemory`
> (using `databricks-gte-large-en` embeddings) for cross-thread recall. Build
> sessions inside `@invoke` so they're OBO-scoped. Search long-term memory
> pre-LLM, persist new facts post-LLM. Resolve `thread_id` from
> `request.custom_inputs.thread_id || request.conversation_id`. Load
> `tracks/A-custom-agent-apps/05-lakebase-memory/SKILL.md`.

**Expected:** Same-thread turn 2 references turn 1; new-thread recall works for the same user.

### Prompt P17 — A6: Evaluation smoke test

> Run `uv run agent-evaluate` on `{agent_name}` as a smoke test. Customize
> `tests/eval_dataset.json` with 10+ domain test cases. Load
> `tracks/A-custom-agent-apps/06-evaluation/SKILL.md`.

**Expected:** Evaluation completes; results visible in MLflow; relevance ≥ 80%, zero safety failures.

### Prompt P18 — A7: Deploy the Agent App

> Deploy `{agent_name}` as a Databricks App. Capture `agent_app_url` and
> `agent_app_name` into state. Verify `/invocations` works via curl with an
> OAuth token, and traces from the deployed app appear in MLflow. Load
> `tracks/A-custom-agent-apps/07-deploy-and-query/SKILL.md`.

**Expected:** `agent_app_name` in `RUNNING`; `agent_app_url` captured; deployed traces visible.

---

## Section 5: AppKit ↔ Agent App wiring (OBO proxy)

### Prompt P19 — Wire chat proxy with OBO forwarding

> Wire `{appkit_app_name}` to `{agent_app_name}` via a vanilla
> `server.extend()` proxy with SP + OBO layers. Forward
> `x-forwarded-access-token` verbatim to the Agent App's `/invocations` /
> `/responses` route, support dual-format streaming, declare the Agent App
> as a `databricks.yml` resource (`type: app`, `permission: CAN_USE`), and
> bind `AGENT_APP_URL` in `app.yaml`. Run the 3-probe e2e test. Load
> `apps_lakebase/skills/06d-appkit-agent-app-proxy/SKILL.md`.

**Expected:** Streaming chat works on `/chat` against the Agent App; 3 probes (direct, SP-only, OBO) pass.

### Prompt P20 — Chat history + feedback

> Add persistent chat history (per-user, OBO-scoped, sidebar nav) and
> thumbs-up/down feedback (linked to MLflow traces). Load
> `apps_lakebase/skills/07-appkit-chat-history/SKILL.md` and
> `apps_lakebase/skills/08-appkit-feedback/SKILL.md`.

**Expected:** Sidebar history works; feedback rows link to MLflow trace IDs; idle resilience holds for 3-5 min.

---

## Section 6: SDLC Pipeline

> All canonical agents converge here. Your `predict_fn` (or wrapper around
> `@invoke`) feeds evaluation. Track-shape doesn't change SDLC.

### Prompt P21 — S1: Prompt Registry

> Register `{agent_name}` prompts in UC at `{catalog}.{schema}`. Set
> `@production` and `@staging` aliases. Load
> `sdlc/01-prompt-registry/SKILL.md`.

### Prompt P22 — S2: Evaluation Datasets

> Create the benchmark dataset at `{catalog}.{schema}.{agent_name}_benchmarks`
> with 20+ domain rows. Load `sdlc/02-evaluation-datasets/SKILL.md`.

### Prompt P23 — S3: Scorers and Judges

> Build the scorer suite (built-ins + Guidelines + custom `@scorer` +
> `make_judge`) with thresholds. Load `sdlc/03-scorers-and-judges/SKILL.md`.

### Prompt P24 — S4: Evaluation Runs

> Run `mlflow.genai.evaluate()` against the benchmark dataset using the
> `predict_fn` from P16/P18. Also create an expert labeling session for
> ground-truth calibration (`create_labeling_session` + `session.sync()`).
> Load `sdlc/04-evaluation-runs/SKILL.md`.

### Prompt P24b — S4b: Stakeholder Sign-Off

> Translate eval metrics to a 1-page business-metrics report, run a live
> failure-mode walkthrough with non-engineering stakeholders, and capture
> a `Decision: APPROVED` artifact in the UC volume that the CI promotion
> script gates on. Load `sdlc/04b-stakeholder-signoff/SKILL.md`.

### Prompt P24c — S4c: End-User Feedback

> Wire the `/feedback` route in the Track A Agent App and wire
> `apps_lakebase/skills/08-appkit-feedback` in AppKit so end users can
> attach 👍/👎 (and optionally per-dimension ratings) to the originating
> trace via `mlflow.log_feedback(...)`. Verify the round-trip in the
> MLflow trace UI and add a weekly job that materializes negative-feedback
> traces into a UC eval dataset for the next P22 iteration. Load
> `sdlc/04c-end-user-feedback/SKILL.md`.

### Prompt P25 — S5: Logged Model + UC Registration

> Register `{agent_name}` in UC at `{catalog}.{schema}.{agent_name}`,
> promote `@champion` if scores beat the existing one. Set
> `MLFLOW_ACTIVE_MODEL_ID`. Load
> `sdlc/05-logged-model-and-uc-registration/SKILL.md`.

### Prompt P26 — S6: Deployment Automation (DAB)

> Customize `databricks.yml` and `app.yaml` (already exists from Sections 1
> + 4). Add the bundle-managed experiment, declare `uc_securable` resources
> for KA + Genie + warehouse, wire `MLFLOW_ACTIVE_MODEL_ID`, and define an
> evaluate→register→deploy CI/CD pipeline. Load
> `sdlc/06-deployment-and-automation/SKILL.md`.

### Prompt P27 — S7: Production Monitoring

> Register production scorers (Safety @ 100%, LLM judges @ 10–20%), enable
> trace archival to `{catalog}.{schema}.{agent_name}_archived_traces`, and
> set up periodic human review. Load
> `sdlc/07-production-monitoring/SKILL.md`.

---

## Section 7: Capstone (optional)

### Prompt P28 — Genie Orchestrator (removed)

The previously bundled multi-agent Genie Orchestrator capstone skill has been
removed during the 2026-04-27 consolidation. For canonical multi-agent and
Genie Space orchestration patterns, see
[`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills)
(`databricks-agent-bricks`, `databricks-genie`).

---

## Section 8: Alternate methods

If the canonical 2-Apps Track A path doesn't fit your constraints, treat the
alternate shapes as explicitly routed exceptions. The previously bundled
alternate skill mirrors (`B-supervisor-api/`, `C-model-serving/`,
`capstone/genie-orchestrator/`) have been removed during the 2026-04-27
consolidation. For canonical Databricks-platform reference patterns see the
upstream registry
[`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills).

| When to pick | Pointer |
|---|---|
| Need only Databricks-hosted tools (Supervisor API, hosted Genie/UC tools) | Upstream `databricks-agent-bricks` |
| Wrapping an existing Model Serving endpoint | Upstream `databricks-model-serving` |
| Single App, template chat UI only (fastest POC) | Use the Track A Agent App through `tracks/A-custom-agent-apps/` and skip the AppKit proxy prompts |
| TypeScript end-to-end with `@openai/agents` | Not included as a root course path in this template |

Start with `00-course-orchestrator/SKILL.md` before choosing an alternate so
state and SDLC expectations stay aligned.

---

## Quick Reference

| # | Prompt | Skill | Section |
|---|--------|-------|---------|
| P0 | Workspace Setup | (CLI commands in guide) | 0 |
| P1 | AppKit Scaffold | `apps_lakebase/skills/01-appkit-scaffold/SKILL.md` | 1 |
| P2 | AppKit Build | `apps_lakebase/skills/02-appkit-build/SKILL.md` | 1 |
| P3 | AppKit Deploy | `apps_lakebase/skills/03-appkit-deploy/SKILL.md` | 1 |
| P4 | AppKit Plugin Add | `apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` | 1 |
| P5 | AppKit Lakebase Wiring | `apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md` | 1 |
| P6 | F1: MLflow GenAI Foundation | `foundation/01-mlflow-genai-foundation/SKILL.md` | 2 |
| P7 | F2: Experiment Tracing + UC | `foundation/02-experiment-tracing-and-uc-storage/SKILL.md` | 2 |
| P8 | F3: Tools and Data Access | `foundation/03-tools-and-data-access/SKILL.md` | 2 |
| P9 | F5: Knowledge Assistant | `foundation/05-knowledge-assistant/SKILL.md` | 3 |
| P10 | Genie Space | `data_product_accelerator/skills/semantic-layer/03-genie-space-patterns/SKILL.md` | 3 |
| P11 | UC Functions | `foundation/03-tools-and-data-access/SKILL.md` (UC funcs) | 3 |
| P12 | A1: Clone and Run | `tracks/A-custom-agent-apps/01-clone-and-run/SKILL.md` | 4 |
| P13 | A2: Agent Framework (Option B) | `tracks/A-custom-agent-apps/02-agent-framework/SKILL.md` | 4 |
| P14 | A3: Wire Tools (KA + Genie + UC) | `tracks/A-custom-agent-apps/03-tools-and-mcp/SKILL.md` | 4 |
| P15 | A4: Authentication (OBO + scopes) | `tracks/A-custom-agent-apps/04-authentication/SKILL.md` | 4 |
| P16 | A5: Lakebase Memory (short + long) | `tracks/A-custom-agent-apps/05-lakebase-memory/SKILL.md` | 4 |
| P17 | A6: Evaluation Smoke Test | `tracks/A-custom-agent-apps/06-evaluation/SKILL.md` | 4 |
| P18 | A7: Deploy Agent App | `tracks/A-custom-agent-apps/07-deploy-and-query/SKILL.md` | 4 |
| P19 | AppKit↔Agent OBO proxy | `apps_lakebase/skills/06d-appkit-agent-app-proxy/SKILL.md` | 5 |
| P20 | Chat history + feedback | `apps_lakebase/skills/07-appkit-chat-history/SKILL.md` + `08-appkit-feedback/SKILL.md` | 5 |
| P21 | S1: Prompt Registry | `sdlc/01-prompt-registry/SKILL.md` | 6 |
| P22 | S2: Evaluation Datasets | `sdlc/02-evaluation-datasets/SKILL.md` | 6 |
| P23 | S3: Scorers and Judges | `sdlc/03-scorers-and-judges/SKILL.md` | 6 |
| P24 | S4: Evaluation Runs | `sdlc/04-evaluation-runs/SKILL.md` | 6 |
| P24b | S4b: Stakeholder Sign-Off | `sdlc/04b-stakeholder-signoff/SKILL.md` | 6 |
| P24c | S4c: End-User Feedback | `sdlc/04c-end-user-feedback/SKILL.md` | 6 |
| P25 | S5: Logged Model + UC Registration | `sdlc/05-logged-model-and-uc-registration/SKILL.md` | 6 |
| P26 | S6: Deployment Automation | `sdlc/06-deployment-and-automation/SKILL.md` | 6 |
| P27 | S7: Production Monitoring | `sdlc/07-production-monitoring/SKILL.md` | 6 |
| P28 | Capstone (removed) | See upstream `databricks/databricks-agent-skills` (`databricks-agent-bricks`, `databricks-genie`) | 7 |

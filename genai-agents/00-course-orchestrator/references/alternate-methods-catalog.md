# Alternate Methods Catalog

> **Owned by:** `genai-agents/00-course-orchestrator/SKILL.md`.
> The navigator's primary scope is `genai-agents/`. The previously bundled
> alternate-method mirrors (`B-supervisor-api/`, `C-model-serving/`,
> `capstone/genie-orchestrator/`) under
> `data_product_accelerator/skills/genai-agents/` were removed during the
> 2026-04-27 consolidation. For canonical Databricks-platform reference
> patterns covering hosted-tool agents, Model Serving deployments, and
> multi-agent / Genie orchestration, consult the upstream registry
> [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills).

The canonical path of the GenAI Agent Development course is **Track A — a
custom agent built with the OpenAI Agents SDK and deployed on Databricks
Apps**. It is the only path with end-to-end coverage of the MLflow SDLC
pipeline (prompt registry → eval → register → deploy → monitor → feedback).

## Variant chooser

| Variant | Walkthrough | Tracks / Skills | When to pick |
|---|---|---|---|
| V1 — Supervisor API + AppKit | Not bundled in this template | Upstream [`databricks-agent-bricks`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-agent-bricks) | Hosted tools only, no custom server, fastest ramp |
| V2 — Model Serving + AppKit | Not bundled in this template | Upstream [`databricks-model-serving`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-model-serving) | Existing agent code, REST endpoint, Review App |
| V3 — Agent App only | Use Track A and skip AppKit prompts | Track A subset (canonical Foundation + Module 2 only) | Conversational-only POC, fastest deploy |
| V4 — Agent App + AppKit (canonical) | [`PROMPT-GUIDE.md`](../../PROMPT-GUIDE.md) | This orchestrator (Foundation + Track A + AppKit `06d` + SDLC) | Full Python agent + rich AppKit dashboard |
| V5 — Node-native single App | Not included in this template | Foundation Step 2b only covers TypeScript tracing primitives | TypeScript end-to-end exploration |
| Capstone — Multi-agent Genie | Not bundled in this template | Upstream [`databricks-agent-bricks`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-agent-bricks) + [`databricks-genie`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-genie) | Multi-domain query routing across Genie + KB + web |

**Variant 5 SDLC limitations:** the MLflow `log_model` / `register_model` /
Review App pipeline (Module 3) does not apply directly. OTLP traces +
Playwright-driven evaluation are used instead. The full Node-native path is not
included in this template.

---

## V1 — Supervisor API quick reference

Zero custom server code. Databricks manages the agent loop, tool execution, and tracing.
For canonical guidance, follow the upstream [`databricks-agent-bricks`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-agent-bricks)
skill (Knowledge Assistants, Genie Spaces, Supervisor Agents).

Foundation prerequisite still applies: complete
[`foundation/05-knowledge-assistant/SKILL.md`](../../foundation/05-knowledge-assistant/SKILL.md)
before wiring KA as a hosted tool.

**V1 produces:** `predict_fn` = a thin wrapper around `responses.create()` that
returns `response.output_text`.

## V2 — Model Serving quick reference

Package the agent as an MLflow model, deploy to a serving endpoint. For canonical
guidance, follow the upstream [`databricks-model-serving`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-model-serving)
skill (ChatAgent / ResponsesAgent packaging, endpoint deployment, querying).

**V2 produces:** `predict_fn` = a wrapper that POSTs to the endpoint and parses
the response.

## V5 — Node-native single App quick reference

TypeScript end-to-end with `@openai/agents` is not bundled as a full path in
this template. Use [`foundation/02b-typescript-tracing/SKILL.md`](../../foundation/02b-typescript-tracing/SKILL.md)
only for TypeScript tracing primitives.

## Capstone — Multi-Agent Genie Orchestrator (optional, ~2 hours)

Not bundled in this template. For canonical multi-agent and Genie Space
orchestration patterns, follow the upstream registry:

- [`databricks-agent-bricks`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-agent-bricks) — Knowledge Assistants, Genie Spaces, Supervisor Agents (MAS)
- [`databricks-genie`](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-genie) — Genie Space creation, querying via Conversation API

A multi-domain orchestrator pattern would combine those with the Track A custom
agent (`tracks/A-custom-agent-apps/`) so the orchestrator runs in the same
Databricks Apps deployment shape as the canonical path.

---
name: 00b-agent-spec-and-tool-plan
description: >
  Use when deriving a Databricks Agent Spec and Agent Tool Plan from
  docs/design_prd.md before building Track A agents. Covers web-researched MCP
  recommendations, Databricks managed MCP choices, dynamic SQL MCP catalog/schema
  inputs, optional Knowledge Assistant selection, and validation of
  docs/agent_spec.yaml plus docs/agent_tool_plan.yaml.
license: Apache-2.0
metadata:
  last_verified: "2026-04-29"
  volatility: high
  author: "prashanth-subrahmanyam"
  version: "1.0.0"
  domain: "genai-agents"
  pipeline_position: "F0b"
  consumes: "docs/design_prd.md"
  produces: "docs/agent_spec.yaml, docs/agent_tool_plan.yaml"
fields_read:
  - agent.system_prompt
  - agent.capabilities
  - agent.tools
  - agent.mcp_servers
  - agent.knowledge_base_backend
  - agent.external_integrations
---

# Agent Spec And Tool Plan

## Purpose

This skill bridges the AppKit/Lakebase application design phase and the Track A
agent build phase. It turns `docs/design_prd.md` into a concrete
`docs/agent_spec.yaml`, then turns the spec plus user tool choices into
`docs/agent_tool_plan.yaml`.

The skill does not create Databricks resources, install MCP connections, wire
agent code, or deploy apps. It produces planning artifacts that later prompts
consume.

## When To Use

Use this skill for:

- Creating an Agent Spec after `docs/design_prd.md` exists.
- Asking the IDE to web search for MCPs relevant to the use case.
- Selecting Databricks managed MCPs: Genie, Vector Search, SQL, UC Functions.
- Selecting external MCP candidates through managed OAuth, Marketplace, custom
  HTTP connections, or Dynamic Client Registration.
- Adding a no-prerequisite SQL MCP path over existing Unity Catalog tables by
  providing `agent_sql_catalog`, `agent_sql_schema`, and warehouse ID.
- Deciding whether a Knowledge Assistant should be created.

## Inputs

| Input | Required | Description |
|---|---|---|
| `prd_path` | yes | Usually `docs/design_prd.md`. |
| `agent_spec_path` | yes | Usually `docs/agent_spec.yaml`. |
| `agent_tool_plan_path` | yes | Usually `docs/agent_tool_plan.yaml`. |
| `agent_sql_catalog` | no | Catalog the SQL MCP may query. |
| `agent_sql_schema` | no | Schema the SQL MCP may query. |
| `agent_sql_warehouse_id` | no | Warehouse for SQL MCP `_meta.warehouse_id`. |
| `agent_sql_table_allowlist` | no | Tables allowed for SQL MCP; empty means schema-scope with read-only guardrails. |
| `mcp_research_mode` | no | `none`, `managed_only`, or `web_research`. |

## Agent Spec Contract

`docs/agent_spec.yaml` must follow `references/agent-spec-schema.md`.

Required top-level keys:

- `schema_version`
- `source_prd`
- `agent`
- `tool_recommendations`
- `mcp_research`
- `knowledge_assistant`
- `evaluation`
- `governance`

The spec may recommend tools, but it must not mark every recommendation as
selected. Final selection belongs in `docs/agent_tool_plan.yaml`.

## Tool Plan Contract

`docs/agent_tool_plan.yaml` must follow `references/tool-plan-schema.md`.

Required top-level keys:

- `schema_version`
- `source_agent_spec`
- `selected_tools`
- `selected_mcp_servers`
- `knowledge_assistant`
- `resource_grants`
- `runtime_guardrails`
- `verification`

## Dynamic SQL MCP Rule

When SQL MCP is selected, the plan must include:

```yaml
selected_mcp_servers:
  - name: sql_uc_schema_query
    server_type: sql
    url_template: "{workspace_host}/api/2.0/mcp/sql"
    auth: OBO
    meta:
      warehouse_id: "{agent_sql_warehouse_id}"
    scope:
      catalog: "{agent_sql_catalog}"
      schema: "{agent_sql_schema}"
      allowed_tables: []
    readonly: true
```

The matching tool must include guardrails:

```yaml
selected_tools:
  - kind: mcp
    name: sql_uc_schema_query
    mcp_server_ref: sql_uc_schema_query
    readonly: true
    guardrails:
      allowed_statements: ["SELECT", "DESCRIBE", "EXPLAIN"]
      forbidden_statements: ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "MERGE", "TRUNCATE"]
      require_fully_qualified_names: true
      default_catalog: "{agent_sql_catalog}"
      default_schema: "{agent_sql_schema}"
```

## Web Research Rule

If `mcp_research_mode: web_research`, use the official MCP Registry as the
authoritative discovery source before broader web search:

1. Search the public registry UI at `https://registry.modelcontextprotocol.io`.
2. Use the registry REST API documented at `https://modelcontextprotocol.io/registry/registry-aggregators#consuming-the-mcp-registry-rest-api`.
3. Prefer `GET https://registry.modelcontextprotocol.io/v0.1/servers?limit=100`
   for discovery, following `metadata.nextCursor` for additional pages.
4. Use `GET /v0.1/servers/{serverName}/versions` and
   `GET /v0.1/servers/{serverName}/versions/latest` for candidate version
   details. URL-encode `serverName`.
5. Ignore candidates with registry `status: deleted`; mark `deprecated`
   candidates as `confidence: low` unless there is no viable alternative.
6. Use general web search only to enrich registry candidates with vendor docs,
   Databricks compatibility notes, security posture, or examples.

Record findings under `mcp_research.candidates[]` with registry metadata,
source URLs, version/status, integration notes, and confidence. Do not install
or configure any MCP connection during Agent Spec creation.

## Validation

Before exiting either prompt:

1. Parse the YAML.
2. Confirm all required top-level keys exist.
3. Confirm every `selected_tools[].mcp_server_ref` resolves to a
   `selected_mcp_servers[].name`.
4. Confirm SQL MCP is read-only unless the user explicitly selected write access.
5. Confirm KA is either selected with a source strategy or skipped with
   `knowledge_assistant.selected: false`.

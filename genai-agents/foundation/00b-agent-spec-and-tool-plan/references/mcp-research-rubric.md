# MCP Research Rubric

Use this rubric only when the user enables web research from the Agent Spec
prompt.

## Authoritative Discovery Sources

Start with the official MCP Registry:

- Registry UI: `https://registry.modelcontextprotocol.io`
- REST API docs: `https://modelcontextprotocol.io/registry/registry-aggregators#consuming-the-mcp-registry-rest-api`
- List servers: `GET https://registry.modelcontextprotocol.io/v0.1/servers?limit=100`
- Continue pagination with `metadata.nextCursor` as the `cursor` query parameter.
- Get versions: `GET /v0.1/servers/{serverName}/versions`
- Get latest version: `GET /v0.1/servers/{serverName}/versions/latest`
- URL-encode `serverName` and `version` path parameters.
- Treat the registry as preview infrastructure: record source URLs and status,
  and use broader web search only to enrich or validate registry entries.

For every candidate MCP server, record:

- `name`
- `provider`
- `registry_name`
- `registry_status`
- `registry_version`
- `source_url`
- `registry_url`
- `use_case_fit`
- `integration_method`: `managed_oauth`, `marketplace`, `custom_http`, `dcr`, or `not_supported`
- `auth_model`
- `required_scopes`
- `data_sensitivity`
- `installation_risk`
- `databricks_compatibility`: whether it can plausibly work through Databricks external MCP as Streamable HTTP, Marketplace, managed OAuth, or DCR
- `confidence`

Default recommendations:

- Prefer Databricks managed MCP servers when they satisfy the use case.
- Recommend external MCPs only when they add a capability not covered by SQL,
  Genie, Vector Search, UC Functions, Knowledge Assistant, or Lakebase memory.
- Prefer registry-listed MCP servers over blog-only or unregistered candidates.
- Exclude registry entries with `status: deleted`.
- Mark registry entries with `status: deprecated` as `confidence: low` unless
  the user explicitly asks to consider deprecated servers.
- Use broader web search only after checking the official registry.
- Do not install external MCPs during spec generation.
- Mark unknown or unverified servers as `confidence: low`.

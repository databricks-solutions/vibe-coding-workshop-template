---
name: genie-space-export-import-api
description: Comprehensive patterns for Databricks Genie Space Export/Import API - JSON schema, serialization format, and programmatic deployment. Use when programmatically creating, exporting, or importing Genie Spaces via REST API, troubleshooting API deployment errors, or implementing CI/CD for Genie Spaces. Includes complete GenieSpaceExport schema, API endpoints (List, Get, Create, Update, Delete), JSON format requirements, ID generation, variable substitution, inventory-driven generation patterns, and production deployment checklists.
metadata:
  author: prashanth subrahmanyam
  version: "1.0"
  domain: semantic-layer
  role: worker
  pipeline_stage: 6
  pipeline_stage_name: semantic-layer
  called_by:
    - semantic-layer-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-genie/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---

# Genie Space Export/Import API

## Overview

This skill provides comprehensive patterns for programmatically creating, exporting, and importing Databricks Genie Spaces via the REST API. It covers the complete `GenieSpaceExport` JSON schema, API endpoints, common deployment errors, and production-ready workflows including variable substitution and asset inventory-driven generation.

## When to Use This Skill

Use this skill when you need to:

- **Programmatically deploy Genie Spaces** via REST API (CI/CD pipelines, environment promotion)
- **Export Genie Space configurations** for version control, backup, or migration
- **Troubleshoot API deployment errors** (`BAD_REQUEST`, `INVALID_PARAMETER_VALUE`, `INTERNAL_ERROR`)
- **Implement cross-workspace deployment** with template variable substitution
- **Generate Genie Spaces from asset inventories** to prevent non-existent table errors
- **Validate Genie Space JSON structure** before deployment
- **Understand the complete GenieSpaceExport schema** (config, data_sources, instructions, benchmarks)

## Quick Reference

### API Operations

| Operation | Method | Endpoint | Use Case |
|-----------|--------|----------|----------|
| **List Spaces** | GET | `/api/2.0/genie/spaces` | Discover existing spaces |
| **Get Space** | GET | `/api/2.0/genie/spaces/{space_id}` | Export config, backup |
| **Create Space** | POST | `/api/2.0/genie/spaces` | New deployment, CI/CD |
| **Update Space** | PATCH | `/api/2.0/genie/spaces/{space_id}` | Modify config, add benchmarks |
| **Delete Space** | DELETE | `/api/2.0/genie/spaces/{space_id}` | Cleanup, teardown |

### API Limits

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| `instructions.sql_functions` | **Max 50** | Truncate in generation script |
| `benchmarks.questions` | **Max 50** | Truncate in generation script |
| `data_sources.tables` | No hard limit | Keep ~25-30 for performance |
| `data_sources.metric_views` | No hard limit | Keep ~5-10 per space |

### Core Workflow

**Initial Deployment:**
1. List spaces (check if already exists)
2. Load configuration from JSON file
3. Substitute template variables (`${catalog}`, `${gold_schema}`, etc.)
4. Create space with full configuration
5. Get space to verify deployment

**Incremental Updates:**
1. Get current space configuration
2. Modify specific sections (e.g., add benchmarks)
3. Update space with PATCH (partial update)

**Migration/Backup:**
1. Get space with `include_serialized_space=true`
2. Save JSON to version control
3. Create space in new environment (with variable substitution)

## Key Patterns

### 1. JSON Structure Requirements

**CRITICAL:** The `serialized_space` field must be a JSON string (escaped), not a nested object:

```python
payload = {
    "title": "My Space",
    "warehouse_id": "abc123",
    "serialized_space": json.dumps(genie_config)  # ✅ String, not dict
}
```

### Section 4: ID Generation

**All IDs MUST be `uuid.uuid4().hex`** — a 32-character lowercase hex string with no dashes.

```python
import uuid

def generate_id() -> str:
    """Generate a Genie Space compatible ID (32 hex chars, no dashes)."""
    return uuid.uuid4().hex  # e.g., "a1b2c3d4e5f6789012345678abcdef01"
```

**Required ID fields** (every one must be a fresh `uuid.uuid4().hex`):
- `space.id`
- `space.tables[].id`
- `space.sql_functions[].id`
- `space.example_question_sqls[].id`
- `space.materialized_views[].id`

**❌ WRONG IDs (will cause import failures):**
```python
"genie_" + uuid.uuid4().hex[:24]    # ❌ Prefixed, wrong length
"aaaa" * 8                           # ❌ Not random
str(uuid.uuid4())                    # ❌ Contains dashes (36 chars)
hashlib.md5(name.encode()).hexdigest()  # ❌ Deterministic, not UUID4
```

**✅ CORRECT: Always use `uuid.uuid4().hex`** — nothing else.

### Section 5: Array Format Requirements

**ALL string-content fields in the Genie Space JSON MUST be single-element arrays**, not plain strings.

| Field | ❌ Wrong | ✅ Correct |
|-------|---------|-----------|
| `question` | `"What is revenue?"` | `["What is revenue?"]` |
| `content` (in answer) | `"SELECT ..."` | `["SELECT ..."]` |
| `description` (tables) | `"Orders table"` | `["Orders table"]` |
| `description` (MVs) | `"Revenue metrics"` | `["Revenue metrics"]` |
| `description` (TVFs) | `"Date range query"` | `["Date range query"]` |

**Rule:** If a field contains human-readable text or SQL, wrap it in a single-element array `["value"]`.

**Exception:** `format` in answer objects is a plain string: `"SQL"` or `"INSTRUCTIONS"`.

### 4. Template Variable Substitution

**NEVER hardcode schema paths.** Use template variables:

```json
{
  "data_sources": {
    "tables": [
      {"identifier": "${catalog}.${gold_schema}.dim_store"}  // ✅ Template
    ]
  }
}
```

Substitute at runtime:

```python
def substitute_variables(data: dict, variables: dict) -> dict:
    json_str = json.dumps(data)
    json_str = json_str.replace("${catalog}", variables.get('catalog', ''))
    json_str = json_str.replace("${gold_schema}", variables.get('gold_schema', ''))
    return json.loads(json_str)
```

### 5. Asset Inventory-Driven Generation

**NEVER manually edit `data_sources`.** Generate from verified inventory:

```python
# Load inventory
with open('actual_assets_inventory.json') as f:
    inventory = json.load(f)

# Generate data_sources from inventory
genie_config['data_sources']['tables'] = [
    {"identifier": table_id}
    for table_id in inventory['genie_space_mappings']['cost_intelligence']['tables']
]
```

**Benefits:**
- ✅ Prevents "table doesn't exist" errors
- ✅ Enforces API limits automatically
- ✅ Single source of truth for assets

### 6. Column Configs Warning

`column_configs` triggers Unity Catalog validation that can fail for complex spaces:

```json
{
  "data_sources": {
    "metric_views": [
      {
        "identifier": "catalog.schema.mv_sales"
        // ✅ Start without column_configs for reliable deployment
      }
    ]
  }
}
```

**Trade-off:**
- **Without column_configs**: Reliable deployment, less LLM context
- **With column_configs**: More LLM context, higher risk of `INTERNAL_ERROR`

### 7. Field Validation Rules

**config.sample_questions:**
- ✅ Array of objects (not strings)
- ✅ Each object: `{id: string, question: string[]}`
- ❌ NO `name`, `description` fields

**data_sources.metric_views:**
- ✅ `identifier` field (full 3-part UC name)
- ✅ Optional: `description`, `column_configs`
- ❌ NO `id`, `name`, `full_name` fields

**instructions.sql_functions:**
- ✅ `id` field (32 hex chars) - REQUIRED
- ✅ `identifier` field (full 3-part function name) - REQUIRED
- ❌ NO other fields (`name`, `signature`, `description`)

### Section 8: Array Sorting Requirements

**All arrays in the Genie Space JSON MUST be sorted.** The API validates array ordering and will reject payloads with unsorted arrays.

**Sort keys by array:**

| Array | Sort Key | Direction |
|-------|----------|-----------|
| `tables` | `table_name` | Ascending |
| `materialized_views` | `materialized_view_name` | Ascending |
| `sql_functions` | `function_name` | Ascending |
| `example_question_sqls` | `question[0]` | Ascending |

**Implementation:**
```python
def sort_all_arrays(space: dict) -> dict:
    """Sort all arrays in Genie Space JSON by their respective sort keys."""
    if "tables" in space:
        space["tables"] = sorted(space["tables"], key=lambda x: x.get("table_name", ""))
    if "materialized_views" in space:
        space["materialized_views"] = sorted(space["materialized_views"], key=lambda x: x.get("materialized_view_name", ""))
    if "sql_functions" in space:
        space["sql_functions"] = sorted(space["sql_functions"], key=lambda x: x.get("function_name", ""))
    if "example_question_sqls" in space:
        space["example_question_sqls"] = sorted(
            space["example_question_sqls"],
            key=lambda x: x.get("question", [""])[0] if isinstance(x.get("question"), list) else x.get("question", "")
        )
    return space
```

**Always call `sort_all_arrays()` BEFORE submitting to the API.**

### Section 9: Idempotent Deployment (Update-or-Create)

To prevent duplicate Genie Spaces on re-deployment, implement an update-or-create pattern:

1. **Store space IDs in `databricks.yml` variables:**
```yaml
variables:
  genie_space_id_<space_name>:
    description: "Existing Genie Space ID (empty for first deployment)"
    default: ""
```

2. **Deployment logic:**
```python
space_id = dbutils.widgets.get("genie_space_id_<space_name>")

if space_id:
    # UPDATE existing space (PATCH without title to avoid " (updated)" suffix)
    payload = {"serialized_space": json.dumps(space_json)}
    # Do NOT include "title" in PATCH to avoid title mutation
    response = requests.patch(f"{base_url}/api/2.0/genie/spaces/{space_id}", ...)
else:
    # CREATE new space
    response = requests.post(f"{base_url}/api/2.0/genie/spaces", ...)
    new_space_id = response.json()["space"]["id"]
    print(f"Created new space: {new_space_id}")
    print(f"Set variable: genie_space_id_<space_name> = {new_space_id}")
```

3. **⚠️ PATCH without title:** Including `title` in a PATCH request causes the API to append " (updated)" to the title. Omit `title` from PATCH payload to preserve the original name.

4. **After first deployment:** Record the returned space IDs and set them as `databricks.yml` variable defaults for subsequent deployments.

## Common Errors & Quick Fixes

| Error | Cause | Quick Fix |
|-------|-------|-----------|
| `BAD_REQUEST: Invalid JSON` | sample_questions as strings | Convert to objects with `id` and `question[]` |
| `BAD_REQUEST: Invalid JSON` | metric_views with `full_name` | Use `identifier` instead |
| `INTERNAL_ERROR: Failed to retrieve schema` | Missing `id` in sql_functions | Add `id` field (32 hex chars) |
| `INVALID_PARAMETER_VALUE: Expected array` | `question` is string | Wrap in array: `["question"]` |
| `Exceeded maximum number (50)` | Too many TVFs/benchmarks | Truncate to 50 in generation script |
| `expected_sql` field not recognized | Used `expected_sql` instead of `answer` | Use `answer: [{format: "SQL", content: ["SELECT ..."]}]` |
| `must be sorted` / array ordering error | Arrays not sorted by required key | Call `sort_all_arrays()` before submission |
| Invalid ID format | ID is not 32-char hex, contains dashes, or is prefixed | Use `uuid.uuid4().hex` exclusively |

See [Troubleshooting Guide](references/troubleshooting.md) for detailed fix scripts.

## Reference Files

- **[API Reference](references/api-reference.md)**: Complete API endpoint documentation, request/response schemas, authentication details, Databricks CLI usage
- **[Workflow Patterns](references/workflow-patterns.md)**: Detailed GenieSpaceExport schema (config, data_sources, instructions, benchmarks), ID generation, serialization patterns, variable substitution, asset inventory-driven generation, complete examples
- **[Troubleshooting](references/troubleshooting.md)**: Common production errors with Python fix scripts, validation checklists, deployment checklist, error recovery patterns, field-level format requirements

## Assets

- **`assets/templates/genie-deployment-job-template.yml`** — Standalone Asset Bundle job using `notebook_task` for Genie Space deployment (for combined deployment, use the orchestrator's `semantic-layer-job-template.yml`)
- **`assets/templates/deploy_genie_spaces.py`** — Databricks notebook template for Asset Bundle `notebook_task` deployment. Uses `dbutils.widgets.get()` for parameters. Copy to `src/{project}_semantic/deploy_genie_spaces.py` and customize.

> **CLI vs Notebook:** `scripts/import_genie_space.py` is the CLI tool (uses `argparse`) for local/CI use. `assets/templates/deploy_genie_spaces.py` is the notebook template (uses `dbutils.widgets.get()`) for Asset Bundle `notebook_task` deployment.

## Scripts

- **[export_genie_space.py](scripts/export_genie_space.py)**: Export Genie Space configurations
  ```bash
  python scripts/export_genie_space.py --host <workspace> --token <token> --list
  python scripts/export_genie_space.py --host <workspace> --token <token> --space-id <id> --output space.json
  ```

- **[import_genie_space.py](scripts/import_genie_space.py)**: Create/update Genie Spaces from JSON
  ```bash
  python scripts/import_genie_space.py --host <workspace> --token <token> create \
    --config space.json --title "My Space" --description "..." --warehouse-id <id>
  
  python scripts/import_genie_space.py --host <workspace> --token <token> update \
    --space-id <id> --title "Updated Title"
  ```

## Production Deployment Checklist

1. **Validate JSON Structure**
   ```bash
   python scripts/validate_against_reference.py
   ```

2. **Validate SQL Queries** (if benchmarks present)
   ```bash
   databricks bundle run -t dev genie_benchmark_validation_job
   ```

3. **Deploy Genie Spaces**
   ```bash
   databricks bundle deploy -t dev
   databricks bundle run -t dev genie_spaces_deployment_job
   ```

4. **Verify in UI**
   - Navigate to Genie Spaces
   - Test sample questions
   - Verify data sources load correctly

## Related Resources

### Official Documentation
- [Create Space API](https://docs.databricks.com/api/workspace/genie/createspace)
- [Update Space API](https://docs.databricks.com/api/workspace/genie/updatespace)
- [List Spaces API](https://docs.databricks.com/api/workspace/genie/listspaces)
- [Genie Overview](https://docs.databricks.com/genie/)

### Related Skills
- `genie-space-patterns` - UI-based Genie Space setup
- `metric-views-patterns` - Metric view YAML creation
- `databricks-table-valued-functions` - TVF patterns for Genie

## Genie API Notes to Carry Forward

After completing Genie Space API deployment, carry these notes to the next worker:
- **Deployed Space IDs:** Map of space name → space ID (32-char hex) for each deployed space
- **Deployment method:** Whether spaces were created (POST) or updated (PATCH)
- **Variable settings for re-deployment:** `genie_space_id_<name>` values to set in `databricks.yml` for idempotent future deployments
- **Validation results:** Benchmark SQL validation pass/fail counts per space
- **Cross-environment status:** Which environments (dev/staging/prod) have been deployed to

## Next Step

After API deployment is complete:
- **If this is the first deployment:** Record space IDs and set them as `databricks.yml` variable defaults.
- **If benchmarks need tuning:** Proceed to **`semantic-layer/05-genie-optimization-orchestrator/SKILL.md`** for benchmark testing and the 6-lever optimization loop.
- **If deploying to additional environments:** Re-run the deploy notebook with target environment variables.

## Version History

- **v2.0** (Feb 2026) — Array sorting requirements (Section 8); idempotent deployment pattern (Section 9); expanded array format table; strengthened ID generation guidance; 3 new common errors; deploy template major rewrite; benchmark SQL validation templates added; Notes to Carry Forward and Next Step for progressive disclosure
- **v3.0** (January 2026) - Inventory-driven programmatic generation, template variables, 100% deployment success
- **v2.0** (January 2026) - Production deployment patterns, format validation, 8 common error fixes
- **v1.0** (January 2026) - Initial schema documentation and API patterns

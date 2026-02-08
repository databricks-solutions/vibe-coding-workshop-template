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

### 2. ID Generation

All IDs must be 32-character hex strings (UUID without dashes):

```python
import uuid

def generate_genie_id():
    return uuid.uuid4().hex  # "01f0ad0d629b11879bb8c06e03b919f8"
```

**Required IDs:**
- `config.sample_questions[].id`
- `instructions.text_instructions[].id`
- `instructions.sql_functions[].id`
- `instructions.join_specs[].id`
- `benchmarks.questions[].id`

### 3. Array Format Requirements

**CRITICAL:** All string fields that appear as arrays must be arrays, even for single values:

```json
{
  "config": {
    "sample_questions": [
      {
        "id": "...",
        "question": ["What is revenue?"]  // ✅ Array, not string
      }
    ]
  }
}
```

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

## Common Errors & Quick Fixes

| Error | Cause | Quick Fix |
|-------|-------|-----------|
| `BAD_REQUEST: Invalid JSON` | sample_questions as strings | Convert to objects with `id` and `question[]` |
| `BAD_REQUEST: Invalid JSON` | metric_views with `full_name` | Use `identifier` instead |
| `INTERNAL_ERROR: Failed to retrieve schema` | Missing `id` in sql_functions | Add `id` field (32 hex chars) |
| `INVALID_PARAMETER_VALUE: Expected array` | `question` is string | Wrap in array: `["question"]` |
| `Exceeded maximum number (50)` | Too many TVFs/benchmarks | Truncate to 50 in generation script |

See [Troubleshooting Guide](references/troubleshooting.md) for detailed fix scripts.

## Reference Files

- **[API Reference](references/api-reference.md)**: Complete API endpoint documentation, request/response schemas, authentication details, Databricks CLI usage
- **[Workflow Patterns](references/workflow-patterns.md)**: Detailed GenieSpaceExport schema (config, data_sources, instructions, benchmarks), ID generation, serialization patterns, variable substitution, asset inventory-driven generation, complete examples
- **[Troubleshooting](references/troubleshooting.md)**: Common production errors with Python fix scripts, validation checklists, deployment checklist, error recovery patterns, field-level format requirements

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

## Version History

- **v3.0** (January 2026) - Inventory-driven programmatic generation, template variables, 100% deployment success
- **v2.0** (January 2026) - Production deployment patterns, format validation, 8 common error fixes
- **v1.0** (January 2026) - Initial schema documentation and API patterns

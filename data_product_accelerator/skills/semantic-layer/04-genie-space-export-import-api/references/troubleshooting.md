# Genie Space Export/Import Troubleshooting

## Common Production Errors & Fixes

Based on production deployment failures, these are the most common format errors that cause `BAD_REQUEST`, `INVALID_PARAMETER_VALUE`, and `INTERNAL_ERROR` responses from the Databricks API.

---

## Error 1: sample_questions as Plain Strings

**Error**: `BAD_REQUEST: Invalid JSON in field 'serialized_space'`

**Problem**: sample_questions are plain strings instead of objects with id/question

```python
# Fix script
import json
import uuid

with open('genie_export.json', 'r') as f:
    data = json.load(f)

# Convert strings to objects
if isinstance(data["config"]["sample_questions"][0], str):
    new_sq = []
    for q_text in data["config"]["sample_questions"]:
        new_sq.append({
            "id": uuid.uuid4().hex,
            "question": [q_text]
        })
    data["config"]["sample_questions"] = new_sq

with open('genie_export.json', 'w') as f:
    json.dump(data, f, indent=2)
```

---

## Error 2: metric_views with full_name Instead of identifier

**Error**: `BAD_REQUEST: Invalid JSON in field 'serialized_space'`

**Problem**: metric_views have `{id, name, full_name}` instead of `{identifier}`

```python
# Fix script
for mv in data["data_sources"]["metric_views"]:
    if "full_name" in mv:
        # Transform to API format
        new_mv = {"identifier": mv["full_name"]}
        if "description" in mv:
            new_mv["description"] = mv["description"]
        if "column_configs" in mv:
            new_mv["column_configs"] = mv["column_configs"]
        
        # Replace with fixed version
        data["data_sources"]["metric_views"][i] = new_mv
```

---

## Error 3: sql_functions Missing id Field

**Error**: `INTERNAL_ERROR: Failed to retrieve schema from unity catalog`

**Problem**: sql_functions only have `{identifier}`, missing required `{id}` field

```python
# Fix script
for func in data["instructions"]["sql_functions"]:
    if "id" not in func:
        func["id"] = uuid.uuid4().hex
```

---

## Error 4: sample_questions with String Instead of Array

**Error**: `INVALID_PARAMETER_VALUE: Expected an array for question but found "string"`

**Problem**: question field is a string instead of array

```python
# Fix script
for sq in data["config"]["sample_questions"]:
    if isinstance(sq["question"], str):
        sq["question"] = [sq["question"]]
```

---

## Error 5: config.name and config.description

**Error**: `BAD_REQUEST: Invalid JSON in field 'serialized_space'`

**Problem**: `config.name` and `config.description` should NOT be in the config section

```python
# Fix script
if "config" in data:
    if "name" in data["config"]:
        del data["config"]["name"]
    if "description" in data["config"]:
        del data["config"]["description"]
```

**Note**: `title` and `description` belong at the top level of the API payload, not in `serialized_space.config`.

---

## Error 6: Missing data_sources.tables Array

**Error**: `BAD_REQUEST: Invalid JSON in field 'serialized_space'`

**Problem**: Missing `tables` array (must be present even if empty)

```python
# Fix script
if "data_sources" not in data:
    data["data_sources"] = {}
if "tables" not in data["data_sources"]:
    data["data_sources"]["tables"] = []
```

---

## Error 7: sql_functions with Extra Fields

**Error**: `BAD_REQUEST: Invalid JSON in field 'serialized_space'`

**Problem**: sql_functions have extra fields like `name`, `signature`, `full_name`, `description`

```python
# Fix script
new_sql_functions = []
for func in data["instructions"]["sql_functions"]:
    new_sql_functions.append({
        "id": func["id"],
        "identifier": func.get("full_name") or func.get("identifier")
    })
data["instructions"]["sql_functions"] = new_sql_functions
```

---

## Error 8: text_instructions as Array of Strings

**Error**: `BAD_REQUEST: Invalid JSON in field 'serialized_space'`

**Problem**: text_instructions are plain strings instead of objects with id/content

```python
# Fix script
if isinstance(data["instructions"]["text_instructions"][0], str):
    new_ti = [{
        "id": uuid.uuid4().hex,
        "content": data["instructions"]["text_instructions"]
    }]
    data["instructions"]["text_instructions"] = new_ti
```

---

## Error 9: `expected_sql` Field Not Recognized

**Symptom:** API returns field validation error for benchmark questions.

**Cause:** Used `expected_sql` as a JSON field name instead of the correct `answer` structure.

**Fix:**
```json
// ❌ WRONG
{"expected_sql": "SELECT ..."}

// ✅ CORRECT
{"answer": [{"format": "SQL", "content": ["SELECT SUM(revenue) FROM ..."]}]}
```

The field must be `answer` containing an array of objects with `format` ("SQL" or "INSTRUCTIONS") and `content` (single-element array).

---

## Error 10: Arrays Not Sorted

**Symptom:** `Invalid export proto: data_sources.tables must be sorted by identifier`

**Cause:** The Genie API uses protobuf serialization requiring deterministic ordering. Arrays in the `serialized_space` JSON are not sorted by their required key.

**Fix:** Call `sort_genie_config()` before every PATCH request. Correct sort keys:
- `data_sources.tables` → sort by `identifier`
- `data_sources.metric_views` → sort by `identifier`
- `instructions.sql_functions` → sort by `(id, identifier)`
- `instructions.text_instructions` → sort by `id`
- `instructions.example_question_sqls` → sort by `id`
- `config.sample_questions` → sort by `id`
- `benchmarks.questions` → sort by `id`

The canonical `sort_genie_config()` implementation lives in `04-genie-optimization-applier/scripts/optimization_applier.py` and is documented in `04-genie-space-export-import-api/SKILL.md` Section 8.

---

## Error 11: Invalid Genie Space IDs

**Symptom:** API rejects payload with ID format error, or import silently fails.

**Cause:** IDs are not 32-character lowercase hex strings (UUID4 without dashes).

**Common wrong patterns:**
- `"genie_" + uuid.uuid4().hex[:24]` — prefixed and truncated
- `str(uuid.uuid4())` — 36 chars with dashes
- `"aaaa" * 8` — not random

**Fix:** Always use `uuid.uuid4().hex` exclusively. All ID fields (`space.id`, `tables[].id`, `sql_functions[].id`, `example_question_sqls[].id`, `materialized_views[].id`) must use this format.

---

## Validation Checklist

### Structure Validation (MANDATORY)

- [ ] `version` is set to `1` (integer)
- [ ] All IDs are 32-character hex strings (no dashes)
- [ ] All string arrays (question, content, sql) are arrays even for single values
- [ ] All identifiers use full 3-part UC names (`catalog.schema.object`)
- [ ] All arrays sorted by required keys (tables/metric_views by `identifier`, sql_functions by `(id, identifier)`, others by `id`)

### config.sample_questions (CRITICAL)

- [ ] ✅ Is an array of **objects** (not strings)
- [ ] ✅ Each object has `id` field (32 hex chars)
- [ ] ✅ Each object has `question` field (array of strings, even if single string)
- [ ] ✅ No other fields (no `name`, `description`)

### data_sources.tables

- [ ] ✅ Each table has `identifier` field (full 3-part name, no template variables after substitution)
- [ ] ✅ NO `id`, `name`, or `full_name` fields present
- [ ] ✅ If `column_configs` present, it's an array
- [ ] ✅ Each column_config has `column_name` field
- [ ] Optional: `description` field (array of strings)

### data_sources.metric_views

- [ ] ✅ Each metric view has `identifier` field (full 3-part name, no template variables after substitution)
- [ ] ✅ NO `id`, `name`, or `full_name` fields present
- [ ] ✅ If `column_configs` present, it's an array
- [ ] Optional: `description` field (array of strings)

### instructions.sql_functions (CRITICAL)

- [ ] ✅ Each function has `id` field (32 hex chars) - REQUIRED
- [ ] ✅ Each function has `identifier` field (full 3-part function name) - REQUIRED
- [ ] ✅ NO other fields (`name`, `signature`, `full_name`, `description`) - Will cause errors

### instructions.text_instructions

- [ ] ✅ Each instruction has `id` field (32 hex chars)
- [ ] ✅ If `content` present, it's an array of strings (each string can contain `\n`)
- [ ] ✅ NO other fields present

### benchmarks.questions

- [ ] Each question has `id` field (32 hex chars)
- [ ] Each question has `question` field (array of strings)
- [ ] Each question has `answer` array with one element
- [ ] Each answer has `format: "SQL"`
- [ ] Each answer has `content` (array of strings split by lines)

#### Array Sorting

- [ ] `data_sources.tables` sorted by `identifier`
- [ ] `data_sources.metric_views` sorted by `identifier`
- [ ] `instructions.sql_functions` sorted by `(id, identifier)`
- [ ] `instructions.text_instructions` sorted by `id`
- [ ] `instructions.example_question_sqls` sorted by `id`
- [ ] `config.sample_questions` sorted by `id`
- [ ] Sorting applied via `sort_genie_config()` BEFORE PATCH submission

---

## Production Deployment Checklist

Before deploying any Genie Space, run this comprehensive validation:

### Step 1: Validate JSON Structure

```bash
python3 scripts/validate_against_reference.py
```

**Expected**: "✅ ALL FILES MATCH REFERENCE STRUCTURE!"

**If errors found**: Run the appropriate fix scripts (see "Common Production Errors" section)

---

### Step 2: Validate SQL Queries

```bash
DATABRICKS_CONFIG_PROFILE=health-monitor databricks bundle run -t dev genie_benchmark_validation_job
```

**Expected**: 150/150 (100%) pass rate

**If errors found**: Fix SQL queries in `answer.content` sections

---

### Step 3: Deploy Genie Spaces

```bash
DATABRICKS_CONFIG_PROFILE=health-monitor databricks bundle deploy -t dev
DATABRICKS_CONFIG_PROFILE=health-monitor databricks bundle run -t dev genie_spaces_deployment_job
```

**Expected**: "✅ All Genie Spaces deployed successfully!"

---

### Step 4: Verify in UI

1. Navigate to Genie Spaces in Databricks UI
2. Test sample questions in each space
3. Verify data sources load correctly
4. Check that TVFs are accessible

---

## Common Deployment Errors

| Error Code | Cause | Fix |
|---|---|---|
| `BAD_REQUEST: Invalid JSON in field 'serialized_space'` | JSON structure mismatch | Run fix scripts for sample_questions, metric_views, sql_functions |
| `INVALID_PARAMETER_VALUE: Expected an array for question` | String instead of array | Fix sample_questions or benchmark questions format |
| `INTERNAL_ERROR: Failed to retrieve schema from unity catalog` | Transient API error OR invalid column_configs | Retry deployment, or remove column_configs temporarily |
| `TABLE_OR_VIEW_NOT_FOUND` in benchmark SQL | SQL query references non-existent table | Fix table names in benchmark queries |
| `COLUMN_NOT_FOUND` in benchmark SQL | SQL query references non-existent column | Fix column names using ground truth |

---

## Error Recovery Patterns

### Error: `TABLE_OR_VIEW_NOT_FOUND`

**Cause:** Table referenced in `data_sources` doesn't exist.

**Fix:**
1. Query Unity Catalog to verify table existence
2. Update `actual_assets_inventory.json` 
3. Regenerate JSON: `python scripts/regenerate_all_genie_spaces.py`

### Error: `Exceeded maximum number (50) of certified answer inputs`

**Cause:** More than 50 TVFs in `sql_functions`.

**Fix:** Generation script enforces limit automatically. If manual edit, truncate to 50.

### Error: `INTERNAL_ERROR: Failed to retrieve schema from unity catalog`

**Cause:** Could be column_configs OR non-existent tables.

**Fix:**
1. Remove `column_configs` from data_sources
2. Verify all tables exist via UC query
3. Regenerate from inventory

### Error: Genie Space shows wrong tables in UI

**Cause:** Template variables not substituted.

**Fix:** Check `substitute_variables()` is called BEFORE API call.

---

## Field-Level Format Requirements

### config.sample_questions

**✅ CORRECT (Reference Format):**
```json
{
  "config": {
    "sample_questions": [
      {
        "id": "01f0ad3bc23713a48b30c9fbe1792b64",
        "question": ["What are the top 10 stores by revenue this month?"]
      }
    ]
  }
}
```

**❌ WRONG:**
```json
{
  "config": {
    "sample_questions": [
      "What are the top 10 stores by revenue this month?"  // ❌ String instead of object
    ]
  }
}
```

**❌ WRONG:**
```json
{
  "config": {
    "sample_questions": [
      {
        "question": "What is the revenue?"  // ❌ String instead of array
      }
    ]
  }
}
```

### data_sources.metric_views

**✅ CORRECT (Reference Format):**
```json
{
  "data_sources": {
    "metric_views": [
      {
        "identifier": "catalog.schema.sales_performance_metrics",
        "column_configs": [
          {
            "column_name": "total_revenue"
          }
        ]
      }
    ]
  }
}
```

**❌ WRONG:**
```json
{
  "data_sources": {
    "metric_views": [
      {
        "id": "abc123",                    // ❌ Remove 'id' field
        "name": "sales_metrics",           // ❌ Remove 'name' field
        "full_name": "catalog.schema.mv",  // ❌ Should be 'identifier'
        "description": "..."
      }
    ]
  }
}
```

**Valid Fields for metric_views**:
- ✅ `identifier` (required) - Full 3-part UC name
- ✅ `description` (optional) - Array of strings
- ✅ `column_configs` (optional) - Array of column config objects
- ❌ `id`, `name`, `full_name` - NOT allowed

### instructions.sql_functions

**✅ CORRECT (Reference Format):**
```json
{
  "instructions": {
    "sql_functions": [
      {
        "id": "01f0ad0f09081561ba6de2829ed2fa02",
        "identifier": "catalog.schema.get_low_stock_items"
      }
    ]
  }
}
```

**❌ WRONG:**
```json
{
  "instructions": {
    "sql_functions": [
      {
        "identifier": "catalog.schema.get_function"  // ❌ Missing 'id' field
      }
    ]
  }
}
```

**Required Fields for sql_functions**:
- ✅ `id` (required) - 32 hex character UUID
- ✅ `identifier` (required) - Full 3-part function name
- ❌ NO other fields allowed

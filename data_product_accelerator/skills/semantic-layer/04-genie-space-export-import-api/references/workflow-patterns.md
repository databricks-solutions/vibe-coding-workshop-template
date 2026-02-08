# Genie Space Export/Import Workflow Patterns

## Complete Schema Reference

### Top-Level Structure

```typescript
interface GenieSpaceExport {
  version: number;                    // Schema version (currently 1)
  config?: GenieSpaceConfig;          // Space-level configuration
  data_sources?: DataSources;         // Tables and metric views
  instructions?: Instructions;         // LLM instructions, TVFs, joins
  benchmarks?: Benchmarks;            // Evaluation questions
}
```

---

## Section 1: Config - Sample Questions

### Schema

```typescript
interface GenieSpaceConfig {
  sample_questions: SampleQuestion[];
}

interface SampleQuestion {
  id: string;        // UUID without dashes (32 hex chars)
  question: string[]; // Array of strings (split at newlines)
}
```

### Pattern

```json
{
  "config": {
    "sample_questions": [
      {
        "id": "01f0ad3bc23713a48b30c9fbe1792b64",
        "question": ["What are the top 10 stores by revenue this month?"]
      },
      {
        "id": "01f0ad3bc2361bebb2f6bb245992759f",
        "question": ["Which stores are out of stock for Copenhagen?"]
      }
    ]
  }
}
```

### Best Practices

- **6-10 sample questions** - Cover major use cases
- **Questions are arrays** - Even single-line questions are `["question text"]`
- **IDs are UUIDs** - 32 hex characters without dashes
- **Variety** - Include different question types (rankings, comparisons, trends)

---

## Section 2: Data Sources - Tables

### Schema

```typescript
interface DataSources {
  tables?: Table[];
  metric_views?: MetricView[];
}

interface Table {
  identifier: string;           // Full 3-part UC name
  description?: string[];       // Array of description lines
  column_configs?: ColumnConfig[];
}

interface ColumnConfig {
  column_name: string;
  description?: string[];
  synonyms?: string[];
  exclude?: boolean;
  get_example_values?: boolean;      // Sample values for LLM context
  build_value_dictionary?: boolean;  // Build lookup index for categorical columns
}
```

### Pattern - Table Configuration

```json
{
  "data_sources": {
    "tables": [
      {
        "identifier": "catalog.schema.dim_store",
        "column_configs": [
          {
            "column_name": "store_number",
            "get_example_values": true,
            "build_value_dictionary": true
          },
          {
            "column_name": "state",
            "get_example_values": true,
            "build_value_dictionary": true
          },
          {
            "column_name": "store_type",
            "get_example_values": true,
            "build_value_dictionary": true
          },
          {
            "column_name": "latitude",
            "get_example_values": true
          }
        ]
      }
    ]
  }
}
```

### Column Configuration Best Practices

| Column Type | `get_example_values` | `build_value_dictionary` |
|-------------|---------------------|-------------------------|
| **Categorical** (state, brand, type) | `true` | `true` |
| **Identifier** (store_number, upc_code) | `true` | `true` |
| **Date/Timestamp** | `true` | `false` |
| **Numeric** (revenue, quantity) | `true` | `false` |
| **Boolean** (is_current, is_premium) | `true` | `false` |
| **High-cardinality text** (description) | `false` | `false` |

**Rule:** Use `build_value_dictionary: true` for columns users will filter by text (e.g., "Copenhagen", "California").

---

## Section 3: Data Sources - Metric Views

### Schema

```typescript
interface MetricView {
  identifier: string;      // Full 3-part UC name
  description?: string[];  // Array of description lines
  column_configs?: ColumnConfig[];  // Same as table column configs
}
```

### Pattern

```json
{
  "data_sources": {
    "metric_views": [
      {
        "identifier": "catalog.schema.sales_performance_metrics",
        "column_configs": [
          {
            "column_name": "total_revenue"
          },
          {
            "column_name": "brand",
            "get_example_values": true,
            "build_value_dictionary": true
          },
          {
            "column_name": "store_type",
            "get_example_values": true,
            "build_value_dictionary": true
          }
        ]
      }
    ]
  }
}
```

### ⚠️ CRITICAL: column_configs Triggers Unity Catalog Validation

**Discovery (Production Deployment):**

`column_configs` causes the Databricks API to perform Unity Catalog schema validation during Genie Space creation/update. For complex spaces with many tables or metric views, this validation can fail with:

```
INTERNAL_ERROR: Failed to retrieve schema from unity catalog
```

**Pattern Observed:**
- Spaces with NO `column_configs` → ✅ Deployed successfully
- Spaces with extensive `column_configs` (67-124 configs) → ❌ INTERNAL_ERROR

**Recommendation:**

**Start Simple:**
```json
{
  "data_sources": {
    "metric_views": [
      {
        "identifier": "catalog.schema.mv_sales",
        // ✅ NO column_configs - deploys successfully
      }
    ]
  }
}
```

**Add Incrementally (Optional):**
```json
{
  "data_sources": {
    "metric_views": [
      {
        "identifier": "catalog.schema.mv_sales",
        "column_configs": [
          {
            "column_name": "store_name",
            "get_example_values": true,
            "build_value_dictionary": true
          }
        ]
      }
    ]
  }
}
```

**Test after each addition** - If INTERNAL_ERROR occurs, remove the last added config.

**Trade-off:**
- **Without column_configs**: Reliable deployment, but LLM has less column-level context
- **With column_configs**: More LLM context, but higher risk of Unity Catalog validation errors

---

## Section 4: Instructions - Text Instructions

### Schema

```typescript
interface Instructions {
  text_instructions?: TextInstruction[];
  example_question_sqls?: ExampleQuestionSql[];
  sql_functions?: SqlFunction[];
  join_specs?: JoinSpec[];
}

interface TextInstruction {
  id: string;       // UUID without dashes
  content?: string[]; // Array of instruction lines
}
```

### Pattern

```json
{
  "instructions": {
    "text_instructions": [
      {
        "id": "01f0ad1010c212a7a17001b551b71dec",
        "content": [
          "BUSINESS CONTEXT:\n",
          "Altria tobacco products (Copenhagen, Marlboro, Skoal, Parliament) sold at 7-Eleven stores.\n",
          "\n",
          "DATA ASSETS:\n",
          "1. sales_performance_metrics - Daily sales by store/product.\n",
          "2. inventory_health_metrics - Current inventory positions.\n",
          "\n",
          "KEY METRICS:\n",
          "• Revenue: Use net_revenue (gross - returns - discounts).\n",
          "• Volume: Units sold minus returns.\n",
          "\n",
          "TIME FILTERS:\n",
          "• \"last 7 days\" → WHERE transaction_date >= CURRENT_DATE - 7\n",
          "• \"this month\" → WHERE is_current_month = true\n",
          "\n",
          "BUSINESS RULES:\n",
          "• Store numbers are strings (e.g., '101', '150')\n",
          "• For stores, filter dim_store.is_current = true (SCD Type 2)\n",
          "• Use TOP N for rankings (default TOP 10)"
        ]
      }
    ]
  }
}
```

### Text Instruction Structure (Template)

```
BUSINESS CONTEXT:
[1-2 lines describing the business domain]

DATA ASSETS:
1. [metric_view_1] - [purpose]
2. [metric_view_2] - [purpose]
3. TVFs: [function_list]

KEY METRICS:
• [Metric 1]: [definition and synonyms]
• [Metric 2]: [definition and synonyms]

TIME FILTERS:
• "[user phrase]" → [SQL pattern]

AGGREGATIONS:
• "by [dimension]" → GROUP BY [column]

FILTERS:
• "[term]" → [column] = '[value]'

BUSINESS RULES:
• [Rule 1]
• [Rule 2]
• [Default behaviors]
```

---

## Section 5: Instructions - SQL Functions (TVFs)

### Schema

```typescript
interface SqlFunction {
  id: string;         // UUID without dashes
  identifier: string; // Full 3-part function name
}
```

### Pattern

```json
{
  "instructions": {
    "sql_functions": [
      {
        "id": "01f0ad0f09081561ba6de2829ed2fa02",
        "identifier": "catalog.schema.get_low_stock_items"
      },
      {
        "id": "01f0ad0f1d5012f5827579bc338a7e31",
        "identifier": "catalog.schema.get_sales_trend"
      },
      {
        "id": "01f0ad21813418dc814c489e6e08476b",
        "identifier": "catalog.schema.compare_brand_performance"
      }
    ]
  }
}
```

### Best Practices

- **Include ALL TVFs** the space should use
- **Functions must exist** in Unity Catalog before import
- **Document in text_instructions** how/when to use each TVF
- **API Limit: Max 50 sql_functions** - Truncate if exceeding

---

## Section 6: Instructions - Join Specifications

### Schema

```typescript
interface JoinSpec {
  id: string;
  left: JoinSource;
  right: JoinSource;
  sql: string[];       // Join condition + relationship type marker
  comment?: string[];  // Optional description
}

interface JoinSource {
  identifier: string;  // Full 3-part name
  alias: string;       // Table alias for SQL
}
```

### Pattern

```json
{
  "instructions": {
    "join_specs": [
      {
        "id": "01f0ad0d633619c7b3f7c7fbc9ac975e",
        "left": {
          "identifier": "catalog.schema.fact_inventory_snapshot",
          "alias": "fact_inventory_snapshot"
        },
        "right": {
          "identifier": "catalog.schema.dim_product",
          "alias": "dim_product"
        },
        "sql": [
          "`fact_inventory_snapshot`.`product_key` = `dim_product`.`product_key`",
          "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
        ]
      },
      {
        "id": "01f0ad0d63361dc9870d5df2e3eefdee",
        "left": {
          "identifier": "catalog.schema.fact_sales_daily",
          "alias": "fact_sales_daily"
        },
        "right": {
          "identifier": "catalog.schema.dim_store",
          "alias": "dim_store"
        },
        "sql": [
          "`fact_sales_daily`.`store_key` = `dim_store`.`store_key`",
          "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
        ]
      }
    ]
  }
}
```

### Relationship Type Markers

| Marker | Meaning |
|--------|---------|
| `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--` | Fact → Dimension (most common) |
| `--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_MANY--` | Dimension → Fact |
| `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--` | Many-to-many (rare) |
| `--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_ONE--` | One-to-one |

### Join Specification Best Practices

1. **Use backticks** around table and column names
2. **Aliases match table names** for clarity
3. **Star schema pattern**: Fact tables on left, dimensions on right
4. **Include all FK relationships** between tables in data_sources

---

## Section 7: Benchmarks - Evaluation Questions

### Schema

```typescript
interface Benchmarks {
  questions: BenchmarkQuestion[];
}

interface BenchmarkQuestion {
  id: string;
  question: string[];
  answer: BenchmarkAnswer[];  // Currently only one answer supported
}

interface BenchmarkAnswer {
  format: "SQL";     // Only SQL format supported
  content: string[]; // SQL query split by newlines
}
```

### Pattern

```json
{
  "benchmarks": {
    "questions": [
      {
        "id": "01f0ad1423bb14d2b1292a60baa4d4e2",
        "question": ["What are the top 10 stores by revenue this month?"],
        "answer": [
          {
            "format": "SQL",
            "content": [
              "SELECT \n",
              "  store_number,\n",
              "  store_name,\n",
              "  MEASURE(total_revenue) as total_revenue\n",
              "FROM catalog.schema.sales_performance_metrics\n",
              "WHERE month = MONTH(CURRENT_DATE) AND year = YEAR(CURRENT_DATE)\n",
              "GROUP BY ALL\n",
              "ORDER BY total_revenue DESC\n",
              "LIMIT 10;"
            ]
          }
        ]
      },
      {
        "id": "01f0b9f1ba451339b3eff1bd888f642a",
        "question": ["Show me sales trend for the last 30 days"],
        "answer": [
          {
            "format": "SQL",
            "content": [
              "SELECT * \n",
              "FROM catalog.schema.get_sales_trend(30);"
            ]
          }
        ]
      }
    ]
  }
}
```

### Benchmark Question Coverage

Include questions that test:
- [ ] **Metric view aggregations** - Revenue, counts, averages
- [ ] **TVF usage** - Parameterized queries
- [ ] **Time filtering** - This month, last 30 days, YTD
- [ ] **Dimension filtering** - By brand, store, state
- [ ] **Rankings** - Top N, bottom N
- [ ] **Comparisons** - X vs Y, trends
- [ ] **Complex queries** - CTEs, window functions
- **API Limit: Max 50 benchmarks** - Truncate if exceeding

---

## Complete Example: Minimal Genie Space

```json
{
  "version": 1,
  "config": {
    "sample_questions": [
      {
        "id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "question": ["What is the total revenue this month?"]
      },
      {
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "question": ["Which stores have the highest sales?"]
      }
    ]
  },
  "data_sources": {
    "metric_views": [
      {
        "identifier": "catalog.schema.sales_metrics",
        "column_configs": [
          {
            "column_name": "total_revenue"
          },
          {
            "column_name": "store_name",
            "get_example_values": true,
            "build_value_dictionary": true
          }
        ]
      }
    ]
  },
  "instructions": {
    "text_instructions": [
      {
        "id": "cccccccccccccccccccccccccccccccc",
        "content": [
          "You are a sales analytics assistant.\n",
          "Use the sales_metrics metric view for all queries.\n",
          "Default to current month if no time period specified."
        ]
      }
    ]
  },
  "benchmarks": {
    "questions": [
      {
        "id": "dddddddddddddddddddddddddddddddd",
        "question": ["Total revenue this month"],
        "answer": [
          {
            "format": "SQL",
            "content": [
              "SELECT MEASURE(total_revenue) as revenue\n",
              "FROM catalog.schema.sales_metrics\n",
              "WHERE month = MONTH(CURRENT_DATE);"
            ]
          }
        ]
      }
    ]
  }
}
```

---

## ID Generation Pattern

### UUID Format

IDs are 32-character hex strings (UUID without dashes):

```python
import uuid

def generate_genie_id():
    """Generate a Genie Space compatible ID."""
    return uuid.uuid4().hex  # Returns 32 hex chars without dashes

# Example: "01f0ad0d629b11879bb8c06e03b919f8"
```

### ID Assignment

| Object | ID Required | Notes |
|--------|-------------|-------|
| `sample_questions[].id` | Yes | Unique within space |
| `text_instructions[].id` | Yes | Unique within space |
| `sql_functions[].id` | Yes | Unique within space |
| `join_specs[].id` | Yes | Unique within space |
| `benchmarks.questions[].id` | Yes | Unique within space |
| `example_question_sqls[].id` | Yes | Unique within space |

---

## Serialization Pattern

### Python Example

```python
import json

def create_genie_space_payload(
    title: str,
    description: str,
    warehouse_id: str,
    serialized_space: dict
) -> dict:
    """Create the API payload for creating/updating a Genie Space."""
    return {
        "title": title,
        "description": description,
        "warehouse_id": warehouse_id,
        "serialized_space": json.dumps(serialized_space, indent=2)
    }

# Usage
space_config = {
    "version": 1,
    "config": {...},
    "data_sources": {...},
    "instructions": {...},
    "benchmarks": {...}
}

payload = create_genie_space_payload(
    title="My Analytics Space",
    description="Natural language interface for sales analytics",
    warehouse_id="abc123def456",
    serialized_space=space_config
)

# Convert to JSON string for API call
api_body = json.dumps(payload)
```

---

## Variable Substitution Pattern

### Template Variables

**CRITICAL: NEVER hardcode schema paths in JSON files.**

#### ❌ WRONG: Hardcoded Paths

```json
{
  "data_sources": {
    "tables": [
      {"identifier": "prashanth_subrahmanyam_catalog.dev_prashanth_subrahmanyam_system_gold.dim_workspace"}
    ]
  }
}
```

**Problems:**
- Breaks when deploying to different workspace
- Requires find/replace for each environment
- Error-prone manual process

#### ✅ CORRECT: Template Variables

```json
{
  "data_sources": {
    "tables": [
      {"identifier": "${catalog}.${gold_schema}.dim_workspace"}
    ]
  }
}
```

**Variables defined in `databricks.yml`:**

```yaml
variables:
  catalog:
    description: Unity Catalog name
    default: prashanth_subrahmanyam_catalog
  gold_schema:
    description: Gold layer schema
    default: dev_prashanth_subrahmanyam_system_gold

targets:
  dev:
    variables:
      catalog: prashanth_subrahmanyam_catalog
      gold_schema: dev_prashanth_subrahmanyam_system_gold
  prod:
    variables:
      catalog: production_catalog
      gold_schema: system_gold
```

### Variable Substitution Function

```python
def substitute_variables(data: dict, variables: dict) -> dict:
    """Replace template variables with actual values from databricks.yml."""
    json_str = json.dumps(data)
    
    # Standard substitutions
    json_str = json_str.replace("${catalog}", variables.get('catalog', ''))
    json_str = json_str.replace("${gold_schema}", variables.get('gold_schema', ''))
    json_str = json_str.replace("${feature_schema}", variables.get('feature_schema', ''))
    
    # Monitoring schema pattern
    monitoring_schema = f"{variables.get('gold_schema', '')}_monitoring"
    json_str = json_str.replace("${gold_schema}_monitoring", monitoring_schema)
    
    return json.loads(json_str)
```

---

## Asset Inventory-Driven Generation

### The Core Problem

**Manually editing JSON files leads to systematic deployment failures:**
- Non-existent tables in data_sources
- Exceeding API limits (50 TVFs, 50 benchmarks)
- Hardcoded paths break cross-workspace deployment

### The Solution: Inventory-First Generation

**NEVER manually edit `data_sources` in JSON files. Generate from a verified asset inventory.**

### Asset Inventory Structure

**File: `src/genie/actual_assets_inventory.json`**

```json
{
  "metadata": {
    "generated_at": "2026-01-14T12:00:00Z",
    "catalog": "prashanth_subrahmanyam_catalog",
    "schemas_queried": [
      "dev_prashanth_subrahmanyam_system_gold",
      "dev_prashanth_subrahmanyam_system_gold_ml",
      "dev_prashanth_subrahmanyam_system_gold_monitoring"
    ]
  },
  "system_gold": {
    "tables": [
      {"identifier": "${catalog}.${gold_schema}.dim_workspace"},
      {"identifier": "${catalog}.${gold_schema}.dim_sku"},
      {"identifier": "${catalog}.${gold_schema}.fact_usage"}
    ],
    "metric_views": [
      {"identifier": "${catalog}.${gold_schema}.mv_cost_analytics"}
    ],
    "sql_functions": [
      {"identifier": "${catalog}.${gold_schema}.get_top_cost_contributors"}
    ]
  },
  "genie_space_mappings": {
    "cost_intelligence": {
      "tables": ["${catalog}.${gold_schema}.dim_sku", "..."],
      "metric_views": ["${catalog}.${gold_schema}.mv_cost_analytics"],
      "sql_functions": ["${catalog}.${gold_schema}.get_top_cost_contributors"]
    }
  }
}
```

### Programmatic JSON Generation

```python
#!/usr/bin/env python3
"""Regenerate ALL Genie Space JSON files from asset inventory."""

import json
import uuid
from pathlib import Path

def generate_id():
    return uuid.uuid4().hex

def regenerate_genie_space(space_name: str, inventory: dict):
    """Regenerate one Genie Space from inventory."""
    
    json_path = Path(f"src/genie/{space_name}_genie_export.json")
    
    with open(json_path) as f:
        genie_data = json.load(f)
    
    mappings = inventory['genie_space_mappings'].get(space_name, {})
    
    # === UPDATE DATA SOURCES FROM INVENTORY ===
    
    # Tables
    genie_data['data_sources']['tables'] = [
        {"identifier": table_id}
        for table_id in mappings.get('tables', [])
    ]
    
    # Metric views
    genie_data['data_sources']['metric_views'] = [
        {"identifier": mv_id}
        for mv_id in mappings.get('metric_views', [])
    ]
    
    # TVFs (with ID generation and limit enforcement)
    tvfs = [
        {"id": generate_id(), "identifier": tvf_id}
        for tvf_id in mappings.get('sql_functions', [])
    ]
    
    # API LIMIT: Max 50 sql_functions
    if len(tvfs) > 50:
        print(f"  ⚠️ Truncating {space_name} TVFs: {len(tvfs)} → 50")
        tvfs = tvfs[:50]
    genie_data['instructions']['sql_functions'] = tvfs
    
    # === FIX JSON FORMAT ISSUES ===
    
    # Fix sample_questions: ensure question is array
    for sq in genie_data.get('config', {}).get('sample_questions', []):
        if isinstance(sq.get('question'), str):
            sq['question'] = [sq['question']]
        if 'id' not in sq or not sq['id']:
            sq['id'] = generate_id()
    
    # Fix benchmarks: ensure question is array
    for bq in genie_data.get('benchmarks', {}).get('questions', []):
        if isinstance(bq.get('question'), str):
            bq['question'] = [bq['question']]
    
    # API LIMIT: Max 50 benchmarks
    benchmarks = genie_data.get('benchmarks', {}).get('questions', [])
    if len(benchmarks) > 50:
        print(f"  ⚠️ Truncating {space_name} benchmarks: {len(benchmarks)} → 50")
        genie_data['benchmarks']['questions'] = benchmarks[:50]
    
    # Write back
    with open(json_path, 'w') as f:
        json.dump(genie_data, f, indent=2)
    
    print(f"✅ Regenerated {space_name}")
    return True
```

### Complete Generation Workflow

```bash
# 1. Query Unity Catalog (manual SQL in Databricks notebook)
#    - Get all tables, views, functions
#    - Update actual_assets_inventory.json

# 2. Regenerate ALL JSON files
python scripts/regenerate_all_genie_spaces.py

# 3. Validate JSON structure
python scripts/validate_against_reference.py

# 4. Deploy (variables substituted at runtime)
databricks bundle run -t dev genie_spaces_deployment_job
```

---

## API Limits Reference

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| `instructions.sql_functions` | **Max 50** | Truncate in generation script |
| `benchmarks.questions` | **Max 50** | Truncate in generation script |
| `data_sources.tables` | No hard limit | Keep ~25-30 for performance |
| `data_sources.metric_views` | No hard limit | Keep ~5-10 per space |
| `serialized_space` size | ~1MB suggested | Monitor payload size |

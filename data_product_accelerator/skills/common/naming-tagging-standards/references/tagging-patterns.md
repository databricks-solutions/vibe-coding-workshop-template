# Tagging Patterns Reference

Detailed tagging standards for cost allocation, governance, PII classification, and operational visibility.

## Config Resolution Algorithm

**Every tag application follows this algorithm:**

```
1. Scan context/ for customer tagging files (ANY format: YAML, CSV, MD, JSON, TXT, free-form)
   ├── FOUND → Parse file, extract tag key-value pairs
   │           Normalize to canonical schema (see canonical-tagging-schema.yaml)
   │           Customer values override all defaults
   │           Fill gaps with smart defaults (Step 2)
   └── NOT FOUND → Derive ALL values from project context (smart defaults)

2. Normalize to canonical schema (agent-internal, user never sees this):
   ├── workflow_tags: { team, cost_center, project, custom_tags }
   ├── governed_tags: { catalog: {cost_center, business_unit}, schema: {data_owner}, table_defaults, table_overrides }
   ├── pii_columns: { table_name: [{ column, class_tag }] }
   └── exclude_pii: [ table.column ]

3. Fill gaps in canonical schema with smart defaults:
   ├── team                → "data-engineering"
   ├── cost_center         → "REVIEW-REQUIRED" + # TODO (only un-inferable tag)
   ├── project             → From schema CSV / catalog name / repo folder
   ├── business_unit       → Inferred from domain context
   ├── data_owner          → "{project}-data-team" pattern
   └── data_classification → "internal" (safe default)

4. ALWAYS scan column names for PII patterns → apply class.* governed tags
   ├── Merge with customer PII declarations (customer takes precedence)
   ├── Customer can suppress false positives via exclude_pii list
   └── Recommend enabling Databricks Data Classification on catalog

5. ALWAYS set environment = ${bundle.target} (never from config, never hardcoded)

6. Verify consistency: same team/cost_center/project across ALL assets
```

---

## Multi-Format Input Examples

All three examples below are equivalent — the agent normalizes them to the same canonical internal schema (see [canonical-tagging-schema.yaml](canonical-tagging-schema.yaml)). The user drops **any** of these into `context/` and the agent handles the rest.

### YAML Format

```yaml
workflow_tags:
  team: platform-engineering
  cost_center: CC-9901
  project: wanderbricks

governed_tags:
  catalog:
    cost_center: CC-9901
    business_unit: Hospitality
  schema:
    data_owner: data-platform@wanderbricks.com
  table_defaults:
    data_classification: internal
  table_overrides:
    dim_guest:
      data_classification: confidential

pii_columns:
  dim_guest:
    - column: email
      class_tag: class.email_address
    - column: phone_number
      class_tag: class.phone_number
    - column: guest_name
      class_tag: class.name
```

### CSV Format

```csv
scope,object_type,tag_name,tag_value
workflow,all,team,platform-engineering
workflow,all,cost_center,CC-9901
workflow,all,project,wanderbricks
catalog,all,cost_center,CC-9901
catalog,all,business_unit,Hospitality
schema,all,data_owner,data-platform@wanderbricks.com
table,default,data_classification,internal
table,dim_guest,data_classification,confidential
column,dim_guest.email,class.email_address,
column,dim_guest.phone_number,class.phone_number,
column,dim_guest.guest_name,class.name,
```

### Markdown Format

```markdown
## Tagging Standards

### Workflow Tags
| Tag | Value |
|-----|-------|
| team | platform-engineering |
| cost_center | CC-9901 |
| project | wanderbricks |

### Governance Tags
- Catalog cost_center: CC-9901
- Catalog business_unit: Hospitality
- Schema data_owner: data-platform@wanderbricks.com
- Table data_classification (default): internal
- Table dim_guest data_classification: confidential

### PII Columns
- dim_guest.email → class.email_address
- dim_guest.phone_number → class.phone_number
- dim_guest.guest_name → class.name
```

### Normalized Result (Agent-Internal)

All three formats above produce the same canonical internal representation:

```yaml
# Agent's internal normalized state (user never sees this)
workflow_tags:
  team: "platform-engineering"
  cost_center: "CC-9901"
  project: "wanderbricks"
governed_tags:
  catalog: { cost_center: "CC-9901", business_unit: "Hospitality" }
  schema: { data_owner: "data-platform@wanderbricks.com" }
  table_defaults: { data_classification: "internal" }
  table_overrides: { dim_guest: { data_classification: "confidential" } }
pii_columns:
  dim_guest:
    - { column: "email", class_tag: "class.email_address" }
    - { column: "phone_number", class_tag: "class.phone_number" }
    - { column: "guest_name", class_tag: "class.name" }
```

---

## Workflow Tags (Asset Bundles)

### Required Tags

| Tag | Required | Smart Default | Description |
|-----|----------|---------------|-------------|
| `team` | Yes | `"data-engineering"` | Owning team for cost allocation |
| `cost_center` | Yes | `"REVIEW-REQUIRED"` | Finance cost center code (cannot infer) |
| `environment` | Yes | `${bundle.target}` | Deployment environment (always automatic) |
| `project` | Recommended | Inferred from project | Project or initiative |
| `layer` | Recommended | Auto-derived | Data layer (`bronze`, `silver`, `gold`) |
| `job_type` | Recommended | Auto-derived | Workload category (`setup`, `pipeline`, `merge`, `ml`) |

### Job Tags — With Customer Config

```yaml
resources:
  jobs:
    gold_merge_job:
      name: "[${bundle.target}] Hospitality - Merge Guests"
      tags:
        team: platform-engineering         # From customer config
        cost_center: CC-9901               # From customer config
        environment: ${bundle.target}      # Always automatic
        project: wanderbricks              # From customer config
        layer: gold
        job_type: merge
```

### Job Tags — Without Customer Config (Smart Defaults)

```yaml
resources:
  jobs:
    gold_merge_job:
      name: "[${bundle.target}] Hospitality - Merge Guests"
      tags:
        team: data-engineering             # Default — add tagging config to context/ to customize
        cost_center: REVIEW-REQUIRED       # TODO: Add tagging config to context/ with cost_center
        environment: ${bundle.target}      # Always automatic
        project: wanderbricks              # Inferred from schema CSV
        layer: gold
        job_type: merge
```

### Pipeline Tags — With Customer Config

```yaml
resources:
  pipelines:
    silver_pipeline:
      name: "[${bundle.target}] Silver Hospitality Pipeline"
      tags:
        team: platform-engineering         # From customer config
        cost_center: CC-9901               # From customer config
        environment: ${bundle.target}      # Always automatic
        project: wanderbricks              # From customer config
        layer: silver
        pipeline_type: streaming
```

### Pipeline Tags — Without Customer Config (Smart Defaults)

```yaml
resources:
  pipelines:
    silver_pipeline:
      name: "[${bundle.target}] Silver Hospitality Pipeline"
      tags:
        team: data-engineering             # Default — add tagging config to context/ to customize
        cost_center: REVIEW-REQUIRED       # TODO: Add tagging config to context/ with cost_center
        environment: ${bundle.target}      # Always automatic
        project: wanderbricks              # Inferred from schema CSV
        layer: silver
        pipeline_type: streaming
```

---

## Databricks Data Classification — `class.*` System Governed Tags

### Why `class.*` Instead of Custom PII Tags

| Feature | `class.*` System Tags | Custom `pii`/`pii_type` Tags |
|---------|----------------------|-------------------------------|
| Databricks-native | Yes — recognized by Data Classification engine | No — custom/user-defined |
| ABAC policy integration | Direct — `hasTag("class.email_address")` | Manual — requires custom policy |
| Automated scanning | Integrates with Data Classification auto-tagging | No auto-discovery |
| Cross-workspace | Account-level system governed tags | Workspace-specific |
| Data Classification UI | Shows in classification results page | Hidden in generic tag view |

**Always use `class.*` tags for PII classification.**

### Supported Tags (Global)

| Tag | Description |
|-----|-------------|
| `class.credit_card` | Credit card number |
| `class.email_address` | Email address |
| `class.iban_code` | International Bank Account Number (IBAN) |
| `class.ip_address` | Internet Protocol Address (IPv4 or IPv6) |
| `class.location` | Physical location / address |
| `class.name` | Name of a person |
| `class.phone_number` | Phone number |
| `class.url` | URL |
| `class.us_bank_number` | US bank number |
| `class.us_driver_license` | US driver license |
| `class.us_itin` | US Individual Taxpayer Identification Number |
| `class.us_passport` | US Passport |
| `class.us_ssn` | US Social Security Number |
| `class.vin` | Vehicle Identification Number (VIN) |

### Regional Tags (Europe)

| Tag | Description |
|-----|-------------|
| `class.de_id_card` | German ID card number |
| `class.de_svnr` | German social insurance number |
| `class.de_tax_id` | German tax ID |
| `class.uk_nhs` | UK National Health Service number |
| `class.uk_nino` | UK National Insurance Number |

### Regional Tags (Australia)

| Tag | Description |
|-----|-------------|
| `class.au_medicare` | Australian Medicare card number |
| `class.au_tfn` | Australian Tax File Number |

### PII Column Name → `class.*` Inference Patterns

The agent uses these patterns to proactively tag PII columns from schema CSV or YAML designs:

| Column Name Pattern | `class.*` Tag | Confidence |
|--------------------|---------------|------------|
| `*email*` | `class.email_address` | High |
| `*phone*`, `*mobile*`, `*cell*` | `class.phone_number` | High |
| `first_name`, `last_name`, `*guest_name`, `*host_name`, `*customer_name` | `class.name` | High |
| `*_address`, `*street*` (physical, not email) | `class.location` | Medium |
| `*ssn*`, `*social_security*` | `class.us_ssn` | High |
| `*passport*` | `class.us_passport` | Medium |
| `*driver_license*` | `class.us_driver_license` | Medium |
| `*credit_card*`, `*card_number*` | `class.credit_card` | High |
| `*ip_address*`, `*ip_addr*` | `class.ip_address` | High |
| `*iban*` | `class.iban_code` | High |
| `*_url`, `*website*` | `class.url` | Medium |

**Disambiguation rules:**
- `host_name` in a hospitality context → `class.name` (person); in infrastructure context → skip (server hostname)
- `address` alone → `class.location`; `email_address` → `class.email_address` (not location)
- `name` alone is too ambiguous — only match when prefixed (e.g., `first_name`, `guest_name`)

### Applying `class.*` Tags

```sql
-- PII tags using Databricks Data Classification system governed tags
-- Applied based on column name inference + customer config declarations

ALTER TABLE gold.dim_guest
ALTER COLUMN email SET TAGS ('class.email_address' = '');

ALTER TABLE gold.dim_guest
ALTER COLUMN phone_number SET TAGS ('class.phone_number' = '');

ALTER TABLE gold.dim_guest
ALTER COLUMN guest_name SET TAGS ('class.name' = '');

ALTER TABLE gold.dim_guest
ALTER COLUMN street_address SET TAGS ('class.location' = '');
```

### Enabling Automated Data Classification

In addition to column-name inference, **always recommend** enabling Databricks Data Classification for AI-powered scanning:

```
1. Navigate to the catalog in Catalog Explorer
2. Click the "Details" tab
3. Toggle "Data Classification" to ON
4. Select schemas to include (or all)
5. Click "Enable"
```

This provides AI-powered classification that catches patterns beyond column names (e.g., actual data content scanning).

---

## Unity Catalog Governed Tags (Non-PII)

### Required Tags by Level

| Tag | Apply To | Smart Default | Description |
|-----|----------|---------------|-------------|
| `cost_center` | Catalogs | `"REVIEW-REQUIRED"` | Financial allocation |
| `business_unit` | Catalogs | Inferred from domain | Organizational grouping |
| `data_owner` | Schemas | `"{project}-data-team"` | Accountability |
| `data_classification` | Tables | `"internal"` | Security level |

### Tag Inheritance

Governed tags inherit from parent to child:

```
Catalog (cost_center = CC-9901, business_unit = Hospitality)
  └── Schema (data_owner = wanderbricks-data-team; inherits cost_center, business_unit)
        └── Table (data_classification = internal; inherits parent tags)
              └── Column (class.email_address; inherits parent tags)
```

### Governed vs User-Defined Tags

| Feature | Governed Tags | User-Defined Tags |
|---------|---------------|-------------------|
| Policy enforcement | Required | Optional |
| Predefined values | Enforced | Any value |
| Permission control | ASSIGN permission | MANAGE permission |
| Inheritance | To children | Manual only |
| Cross-workspace | Account-level | Workspace-specific |

---

## Serverless Budget Policies

### Setup Steps

1. Navigate to **Settings** > **Compute** > **Serverless budget policies**
2. Create policy with required tags (`team`, `cost_center`, `environment`)
3. Assign **User** or **Manager** permission to groups
4. Users select policy when creating serverless resources

### Required Tags

| Tag | Required | Description |
|-----|----------|-------------|
| `team` | Yes | Team name for cost allocation |
| `cost_center` | Yes | Finance cost center code |
| `environment` | Yes | `dev`, `staging`, `prod` |
| `project` | Recommended | Project or initiative |

---

## Cost Query Patterns

### Workflow Costs by Team

```sql
SELECT
    usage_date,
    custom_tags:team AS team,
    custom_tags:cost_center AS cost_center,
    custom_tags:project AS project,
    SUM(list_cost) AS total_cost
FROM system.billing.usage
WHERE custom_tags:team IS NOT NULL
GROUP BY 1, 2, 3, 4
ORDER BY total_cost DESC;
```

### Serverless Costs

```sql
SELECT
    usage_date,
    sku_name,
    custom_tags:team AS team,
    custom_tags:cost_center AS cost_center,
    SUM(list_cost) AS total_cost
FROM system.billing.usage
WHERE sku_name LIKE '%SERVERLESS%'
  AND custom_tags:cost_center IS NOT NULL
GROUP BY 1, 2, 3, 4
ORDER BY usage_date DESC, total_cost DESC;
```

### Data Classification Costs

```sql
SELECT
    usage_date,
    identity_metadata.created_by,
    usage_metadata.catalog_id,
    SUM(usage_quantity) AS dbus
FROM system.billing.usage
WHERE billing_origin_product = 'DATA_CLASSIFICATION'
  AND usage_date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY 1, 2, 3
ORDER BY usage_date DESC;
```

---

## Governance Query Patterns

### Find All PII Columns (Data Classification `class.*` Tags)

```sql
SELECT
    table_catalog,
    table_schema,
    table_name,
    column_name,
    tag_name AS classification_class,
    tag_value
FROM system.information_schema.column_tags
WHERE tag_name LIKE 'class.%'
ORDER BY table_catalog, table_schema, table_name, column_name;
```

### Tables by Data Classification Level

```sql
SELECT
    table_catalog,
    table_schema,
    table_name,
    tag_value AS data_classification
FROM system.information_schema.table_tags
WHERE tag_name = 'data_classification'
ORDER BY
    CASE tag_value
        WHEN 'restricted' THEN 1
        WHEN 'confidential' THEN 2
        WHEN 'internal' THEN 3
        WHEN 'public' THEN 4
    END;
```

### Cost Centers by Catalog

```sql
SELECT
    catalog_name,
    tag_value AS cost_center
FROM system.information_schema.catalog_tags
WHERE tag_name = 'cost_center';
```

### Columns Missing PII Tags (Audit Query)

```sql
-- Find columns with PII-like names that lack class.* tags
SELECT
    c.table_catalog,
    c.table_schema,
    c.table_name,
    c.column_name,
    'MISSING_PII_TAG' AS issue
FROM system.information_schema.columns c
LEFT JOIN system.information_schema.column_tags ct
    ON c.table_catalog = ct.table_catalog
    AND c.table_schema = ct.table_schema
    AND c.table_name = ct.table_name
    AND c.column_name = ct.column_name
    AND ct.tag_name LIKE 'class.%'
WHERE ct.tag_name IS NULL
  AND (
    c.column_name LIKE '%email%'
    OR c.column_name LIKE '%phone%'
    OR c.column_name LIKE '%ssn%'
    OR c.column_name LIKE '%passport%'
    OR c.column_name LIKE '%credit_card%'
    OR c.column_name LIKE '%driver_license%'
    OR (c.column_name LIKE '%name' AND c.column_name NOT IN ('table_name', 'column_name', 'schema_name', 'catalog_name', 'tag_name', 'constraint_name', 'sku_name', 'workspace_name', 'host_name'))
  )
ORDER BY c.table_catalog, c.table_schema, c.table_name;
```

---

## Consistency Enforcement Queries

### Verify All Jobs Have Required Tags

```sql
-- Check system.lakeflow.jobs for missing required tags
SELECT
    job_id,
    name,
    custom_tags:team AS team_tag,
    custom_tags:cost_center AS cost_center_tag,
    custom_tags:environment AS env_tag
FROM system.lakeflow.jobs
WHERE custom_tags:team IS NULL
   OR custom_tags:cost_center IS NULL
   OR custom_tags:environment IS NULL;
```

### Verify All Gold Tables Have Classification Tags

```sql
SELECT
    t.table_catalog,
    t.table_schema,
    t.table_name,
    COALESCE(ct.tag_value, 'MISSING') AS data_classification
FROM system.information_schema.tables t
LEFT JOIN system.information_schema.table_tags ct
    ON t.table_catalog = ct.table_catalog
    AND t.table_schema = ct.table_schema
    AND t.table_name = ct.table_name
    AND ct.tag_name = 'data_classification'
WHERE t.table_schema = 'gold'
  AND ct.tag_value IS NULL;
```

# Anti-Patterns Reference

Detailed failure modes observed across 14 pipeline executions. Each anti-pattern includes a description, a real example, the correct pattern, and a detection signal to help you recognize when you're falling into the trap.

## 1. Prompt Sufficiency Illusion

**Description:** A detailed, well-structured user prompt creates the impression that all necessary context is already available. The agent skips reading skills and extracting from source files because the prompt "seems complete." This is the most dangerous anti-pattern because it correlates with the highest-quality prompts — the better the prompt, the stronger the illusion.

**Example failure:**
```
User prompt includes a complete schema description with table names, column types, and relationships.
Agent proceeds to generate Gold YAML directly from the prompt text.
Result: YAML references "cleaning_fee" and "coupon_codes" columns that exist in the
prompt's business description but NOT in the actual source data CSV.
```

**Correct pattern:**
```
1. Read the skill (even if the prompt is detailed)
2. Read the actual source files (CSV, YAML, catalog)
3. Cross-reference prompt claims against source files
4. Flag any prompt concepts not found in source as "extensions requiring confirmation"
```

**Detection signal:** You are about to generate artifacts without having opened a single source file. The prompt felt "self-contained."

---

## 2. Hardcoding YAML-Extractable Values

**Description:** Instead of parsing Gold YAML files for table names, column names, dedup keys, or constraint values, the agent writes them directly into Python/SQL code from memory or from an earlier conversation turn. This creates silent drift when YAML is updated but downstream code is not.

**Example failure:**
```python
# WRONG: Hardcoded from memory
silver_tables = ["silver_bookings", "silver_users", "silver_payments"]
merge_keys = {"silver_bookings": "booking_id", "silver_users": "user_id"}

# Gold YAML actually has:
#   - silver_booking_events (not silver_bookings)
#   - Primary key is composite: (booking_id, event_timestamp)
```

**Correct pattern:**
```python
# RIGHT: Extract from Gold YAML
from pathlib import Path
import yaml

def get_table_config(domain: str) -> dict:
    configs = {}
    for f in Path(f"gold_layer_design/yaml/{domain}").glob("*.yaml"):
        schema = yaml.safe_load(f.read_text())
        configs[schema['table_name']] = {
            'columns': [c['name'] for c in schema['columns']],
            'primary_key': schema.get('primary_key', []),
        }
    return configs
```

**Detection signal:** You are typing a list literal (`["table_a", "table_b"]`) where the values correspond to table names, column names, or keys that exist in YAML files.

---

## 3. Manifest-as-Truth

**Description:** The agent treats design documents, plans, or manifests as reflecting the current state of the catalog. Plans describe *intended* state; the live catalog reflects *actual* state. When these diverge (tables not yet created, columns renamed, schemas dropped), the agent generates code referencing non-existent objects.

**Example failure:**
```
Design manifest lists 12 Gold tables across 3 domains.
Agent generates 12 Metric Views, 8 TVFs, and 3 Genie Space configs.
Live catalog only has 9 tables (3 were never created due to earlier failures).
Result: 3 phantom Metric Views referencing non-existent tables.
One `information_schema` query would have prevented 3 failure-fix cycles.
```

**Correct pattern:**
```sql
-- ALWAYS verify before generating dependent artifacts
SHOW TABLES IN catalog.gold_schema;

-- For column-level verification
DESCRIBE TABLE catalog.gold_schema.fact_bookings;

-- For cross-schema dependency checks
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_catalog = 'catalog' AND table_schema = 'gold_schema';
```

**Detection signal:** You are generating artifacts (Metric Views, TVFs, monitors, dashboards) from a plan or manifest file without having queried the live catalog to confirm the referenced objects exist.

---

## 4. Domain Knowledge Injection

**Description:** The agent injects business domain concepts — enum values, status codes, fee types, business rules — that seem reasonable but are not present in the actual source data. This happens when the agent's training data includes common patterns for the domain (e.g., "bookings typically have statuses: pending, confirmed, cancelled") and it substitutes general knowledge for actual data inspection.

**Example failure:**
```sql
-- Agent generates DQ rule checking valid statuses
-- Based on general domain knowledge, not actual data
@dlt.expect("valid_status", "status IN ('pending', 'confirmed', 'cancelled', 'no_show')")

-- Actual data has: 'PEND', 'CONF', 'CANC', 'NOSHOW', 'PARTIAL'
-- Result: Every row flagged as invalid
```

**Correct pattern:**
```sql
-- ALWAYS extract actual values from source
SELECT DISTINCT status FROM catalog.bronze_schema.raw_bookings;

-- Then use the real values in DQ rules
-- If actual values differ from expectations, flag for user review
```

**Detection signal:** You are writing an `IN (...)` clause, an enum list, or a validation rule with literal string values that you did not extract from a `SELECT DISTINCT` query or source file. Ask yourself: "Where did I get these specific values?"

---

## Recovery Checklist

When you detect any of these anti-patterns mid-generation:

1. **Stop generating** — do not continue with potentially incorrect artifacts
2. **Identify the source gap** — what file, table, or query would provide the correct data?
3. **Run discovery** — Glob for files, `SHOW TABLES`/`DESCRIBE` for catalog, `SELECT DISTINCT` for values
4. **Resume with extracted data** — replace any hardcoded values with extracted ones
5. **Document the extraction source** — add a comment noting where the data came from

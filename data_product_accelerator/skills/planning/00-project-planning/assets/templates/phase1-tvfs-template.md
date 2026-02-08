# Phase 1 Addendum 1.2: Table-Valued Functions (TVFs)

## Overview

**Status:** {status}
**Dependencies:** Prerequisites (Gold Layer) ✅ Complete
**Artifact Count:** {n} TVFs

---

## TVF Summary by Domain

| Domain | Icon | TVF Count | Primary Tables |
|--------|------|-----------|----------------|
| {Domain 1} | {emoji} | {n} | {tables} |

---

## {Domain 1} TVFs

### 1. get_{metric}_by_{dimension}

**Purpose:** {description}

```sql
CREATE OR REPLACE FUNCTION ${catalog}.${gold_schema}.get_{metric}_by_{dimension}(
    start_date STRING COMMENT 'Start date in YYYY-MM-DD format',
    end_date STRING COMMENT 'End date in YYYY-MM-DD format',
    filter_param {TYPE} DEFAULT NULL COMMENT 'Optional filter'
)
RETURNS TABLE (
    {column_1} {TYPE},
    {column_2} {TYPE},
    {measure_1} {TYPE}
)
COMMENT 'LLM: {Description for Genie}.
Use for: {use cases}.
Example questions: "{Question 1}" "{Question 2}"'
RETURN
    SELECT 
        ...
    FROM ${catalog}.${gold_schema}.{fact_table}
    WHERE {date_column} BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
    GROUP BY ...
    ORDER BY ...;
```

---

## TVF Design Standards

### Parameter Requirements

```sql
-- ✅ CORRECT: STRING dates for Genie compatibility
start_date STRING COMMENT 'Start date in YYYY-MM-DD format'

-- ❌ WRONG: DATE type breaks Genie
start_date DATE
```

### Comment Structure

```sql
COMMENT 'LLM: [One-line description].
Use for: [Use cases separated by commas].
Example questions: "[Question 1]" "[Question 2]"'
```

---

## Implementation Checklist

### {Domain 1} TVFs
- [ ] get_{metric1}_by_{dimension}
- [ ] get_{metric2}_by_{dimension}
- [ ] get_top_{entities}_by_{metric}

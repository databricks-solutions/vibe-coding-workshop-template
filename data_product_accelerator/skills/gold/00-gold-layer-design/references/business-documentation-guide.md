# Business Documentation Guide

Extracted from `context/prompts/03a-gold-layer-design-prompt.md` Steps 7-8.

---

## Business Onboarding Guide (MANDATORY)

### Why This Document is Required

The Business Onboarding Guide ensures new team members can:
- Understand the business domain and processes
- Trace data flow from source systems to Gold tables
- Connect business concepts to specific tables and columns
- Leverage analytics capabilities (Genie, AI/BI, ML)

**Without this guide:**
- 2-3 weeks additional ramp-up time for new analysts
- Business context lost in technical documentation
- Slow self-service analytics adoption
- Incorrect queries due to misunderstanding business processes

### Required Sections

**File: `gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md`**

```markdown
# {Project Name} Analytics Platform
## Business Onboarding Guide

**Audience:** Data Engineers, Analysts, Data Scientists, Business Users
**Purpose:** Understand {domain} operations and leverage the Gold layer for analytics

---

## Table of Contents
1. Introduction to {Business Domain}
2. The Business Lifecycle (Key Stages)
3. Key Business Entities (Players/Actors)
4. The Gold Layer Data Model (Overview)
5. Business Processes & Tracking (DETAILED - Source to Gold mapping)
   - 5B. Real-World Scenarios: Following the Data (STORIES)
6. Analytics Use Cases (Operations, Revenue, Planning, Compliance)
7. AI & ML Opportunities
8. Self-Service Analytics with Genie
9. Data Quality & Monitoring
10. Getting Started (For each role)
```

### Section 5: Business Processes (DETAILED)

For EACH major business process, include:

1. **Business Context** - Why this process matters, who cares about it
2. **Process Flow Diagram** - ASCII art showing stages
3. **Source Tables** - Actual source system table names at each stage
4. **Gold Tables** - Which Gold tables store data from each stage
5. **Stage-by-Stage Table** - Detailed mapping

**Template:**

```markdown
### Process N: {Process Name} (Category)

**Business Context:** {Why this process matters and to whom}

**Why It Matters:** 
- {Key business value 1}
- {Key business value 2}
- {Key business value 3}

┌─────────────────────────────────────────────────────────────────┐
│                    {PROCESS NAME} FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STAGE 1             STAGE 2            STAGE 3                │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐           │
│  │  {Name}    │───▶│  {Name}    │───▶│  {Name}    │           │
│  └────────────┘    └────────────┘    └────────────┘           │
│       │                 │                  │                    │
│  Source Tables:    Source Tables:    Source Tables:             │
│  • {SRC_TBL1}     • {SRC_TBL2}     • {SRC_TBL3}              │
│       │                 │                  │                    │
│       ▼                 ▼                  ▼                    │
│  Gold Tables:      Gold Tables:     Gold Tables:               │
│  • {gold_tbl1}     • {gold_tbl2}    • {gold_tbl3}             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

**Stage-by-Stage Detail:**

| Stage | What Happens | Source Table | Gold Table | Key Fields |
|-------|--------------|--------------|------------|------------|
| **1. {Stage}** | {Description} | `{SRC_TBL}` | `{gold_tbl}` | `{key1}`, `{key2}` |
| **2. {Stage}** | {Description} | `{SRC_TBL}` | `{gold_tbl}` | `{key1}`, `{key2}` |

**Business Questions Answered:**
- "{Question 1}" → {Which tables/columns answer it}
- "{Question 2}" → {Which tables/columns answer it}
```

### Section 5B: Real-World Stories (MANDATORY, minimum 3)

Each story must include:
1. **Business Context** - The scenario
2. **Chapters** (4-6) - Each stage of the process
3. **Source System Data** - Example values written to source tables
4. **Gold Layer Updates** - Which Gold tables are created/updated
5. **Analytics Impact** - How metrics/dashboards change
6. **Timeline Visualization** - Summary of data trail

**Story Template:**

```markdown
### Story N: "{Title}" — {Subtitle}

**The Business Context:**
{2-3 sentences describing the real-world scenario}

---

#### Chapter 1: {Stage Name} ({Time})

**What Happens:**  
{Narrative description of what's happening in the business}

**In {Source System}:**
{SOURCE_TABLE}:
  field1: value1
  field2: value2

**In Gold Layer:**

| Table | Record Created/Updated | Key Values |
|-------|------------------------|------------|
| `{gold_table1}` | New row | `{field}` = '{value}' |
| `{gold_table2}` | Updated | `{field}` changed from '{old}' to '{new}' |

**Analytics Impact:**
- {Metric 1} increases/decreases by {amount}
- {Dashboard widget} now shows {value}

---

#### Chapter 2: {Next Stage} ({Time})
{Continue pattern...}

---

#### Story Summary: Data Journey Visualization

┌─────────────────────────────────────────────────────────────┐
│              {SCENARIO}: DATA TRAIL THROUGH GOLD LAYER       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TIME        EVENT              TABLES UPDATED               │
│  ───────────────────────────────────────────────────        │
│  {time1}     {event1}           {table1}, {table2}           │
│  {time2}     {event2}           {table3}                     │
│  {time3}     {event3}           {table4}                     │
│                                                              │
│  TOTAL: {N} tables touched                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Recommended Story Types

| Story Type | Purpose | Example |
|------------|---------|---------|
| **Happy Path** | Normal successful flow | "A salmon shipment from Seattle" |
| **Exception Handling** | How problems are resolved | "The overbooked flight" |
| **Error Correction** | Post-facto adjustments | "The billing dispute" |
| **Compliance/Safety** | Regulatory requirements | "The dangerous goods incident" |

---

## Source Table Mapping (MANDATORY)

### File: `gold_layer_design/SOURCE_TABLE_MAPPING.csv`

**Required Columns:**

```csv
source_table,source_description,status,gold_table,domain,entity_type,rationale,phase,priority
```

| Column | Type | Description |
|--------|------|-------------|
| `source_table` | STRING | Source system table name |
| `source_description` | STRING | Brief description |
| `status` | ENUM | `INCLUDED`, `EXCLUDED`, `PLANNED` |
| `gold_table` | STRING | Target Gold table (or `N/A`) |
| `domain` | STRING | Business domain |
| `entity_type` | ENUM | `dimension`, `fact`, `lookup`, `staging`, `archive` |
| `rationale` | STRING | **REQUIRED** - Why included or excluded |
| `phase` | INT | Implementation phase (1, 2, 3) |
| `priority` | ENUM | `HIGH`, `MEDIUM`, `LOW` |

### Status Rules

| Status | gold_table | rationale |
|--------|-----------|-----------|
| `INCLUDED` | Must have a value | Why this table is needed |
| `EXCLUDED` | Must be `N/A` | MUST explain exclusion reason |
| `PLANNED` | Can be planned name or `TBD` | What's needed before inclusion |

### Standard Exclusion Rationales

| Rationale | When to Use |
|-----------|-------------|
| `System/audit table - no business value` | Internal system tables |
| `Historical archive - superseded by {table}` | Old tables replaced |
| `Duplicate data available in {table}` | Data in another included table |
| `Configuration/setup table - static reference only` | System config tables |
| `Out of scope for {project} phase {N}` | Valid tables deferred |
| `Legacy table - no longer populated` | Deprecated tables |
| `Temporary/staging table` | ETL intermediate tables |
| `Low business value - insufficient usage` | Rarely queried tables |

### Example

```csv
source_table,source_description,status,gold_table,domain,entity_type,rationale,phase,priority
CAPBKGMST,Booking master table,INCLUDED,dim_booking,booking,dimension,Core booking information needed for all cargo analytics,1,HIGH
CAPBKGDTL,Booking line item details,INCLUDED,fact_booking_detail,booking,fact,Shipment-level detail for volume and weight tracking,1,HIGH
AUDITLOG,System audit log,EXCLUDED,N/A,system,audit,System/audit table - no business value,N/A,LOW
MALPOAMST,Postal admin master,PLANNED,dim_postal_admin,mail,dimension,Out of scope for phase 1,2,MEDIUM
```

### Maintaining the Mapping

**Update when:**
- New source tables discovered
- Design decisions change
- Gold table names change
- Phases reprioritized

**Review during:**
- Design reviews
- Phase completion
- Gap analysis sessions

# {Project Name} Analytics Platform
## Business Onboarding Guide

**Audience:** Data Engineers, Analysts, Data Scientists, Business Users  
**Purpose:** Understand {domain} operations and leverage the Gold layer for analytics  
**Last Updated:** {date}

---

## Table of Contents

1. [Introduction to {Business Domain}](#1-introduction)
2. [The Business Lifecycle](#2-business-lifecycle)
3. [Key Business Entities](#3-key-entities)
4. [The Gold Layer Data Model](#4-data-model)
5. [Business Processes & Tracking](#5-business-processes)
   - [5B. Real-World Scenarios](#5b-real-world-scenarios)
6. [Analytics Use Cases](#6-analytics-use-cases)
7. [AI & ML Opportunities](#7-ai-ml)
8. [Self-Service Analytics with Genie](#8-genie)
9. [Data Quality & Monitoring](#9-data-quality)
10. [Getting Started](#10-getting-started)

---

## 1. Introduction to {Business Domain} {#1-introduction}

### What is {Business Domain}?

{2-3 paragraphs explaining the business domain in plain English. What does this
business do? Who are the customers? What are the key products/services?}

### Why Analytics Matters

{Explain why data analytics is important for this domain. What decisions does
data help inform? What are the key performance indicators?}

### Key Terminology

| Term | Definition |
|------|-----------|
| {Term 1} | {Definition} |
| {Term 2} | {Definition} |
| {Term 3} | {Definition} |

---

## 2. The Business Lifecycle {#2-business-lifecycle}

### Overview

{Describe the major stages of the business lifecycle from start to finish.}

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Stage 1  │───▶│ Stage 2  │───▶│ Stage 3  │───▶│ Stage 4  │───▶│ Stage 5  │
│ {Name}   │    │ {Name}   │    │ {Name}   │    │ {Name}   │    │ {Name}   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Stage Details

| Stage | Description | Key Systems | Key Metrics |
|-------|-------------|-------------|-------------|
| {Stage 1} | {Description} | {System names} | {Metrics tracked} |
| {Stage 2} | {Description} | {System names} | {Metrics tracked} |

---

## 3. Key Business Entities {#3-key-entities}

### The Players

| Entity | Role | Example | Gold Table(s) |
|--------|------|---------|---------------|
| {Entity 1} | {Role in business} | {Concrete example} | `dim_{entity}` |
| {Entity 2} | {Role in business} | {Concrete example} | `dim_{entity}` |

### Entity Relationships

{Describe how entities relate to each other in the business context.}

---

## 4. The Gold Layer Data Model {#4-data-model}

### Model Overview

{Brief description of the star schema / dimensional model.}

**Dimensions ({N} tables):** {List dimension tables with brief purpose}
**Facts ({N} tables):** {List fact tables with brief purpose}

### Quick Reference

| Table | Type | Grain | Purpose |
|-------|------|-------|---------|
| `dim_{entity}` | Dimension (SCD {1/2}) | One row per {grain} | {Purpose} |
| `fact_{subject}` | Fact (Aggregated) | One row per {grain} | {Purpose} |

### ERD Reference

See [Master ERD](../../erd_master.md) for complete data model diagram.

---

## 5. Business Processes & Tracking {#5-business-processes}

### Process 1: {Process Name} ({Category})

**Business Context:** {Why this process matters and to whom}

**Why It Matters:**
- {Key business value 1}
- {Key business value 2}
- {Key business value 3}

```
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
```

**Stage-by-Stage Detail:**

| Stage | What Happens | Source Table | Gold Table | Key Fields |
|-------|--------------|--------------|------------|------------|
| **1. {Stage}** | {Description} | `{SRC_TBL}` | `{gold_tbl}` | `{key1}`, `{key2}` |
| **2. {Stage}** | {Description} | `{SRC_TBL}` | `{gold_tbl}` | `{key1}`, `{key2}` |

**Business Questions Answered:**
- "{Question 1}" → {Which tables/columns answer it}
- "{Question 2}" → {Which tables/columns answer it}

---

{Repeat for each major business process}

---

### 5B. Real-World Scenarios: Following the Data {#5b-real-world-scenarios}

#### Story 1: "{Title}" — {Subtitle}

**The Business Context:**
{2-3 sentences describing the real-world scenario}

---

##### Chapter 1: {Stage Name} ({Time})

**What Happens:**
{Narrative description}

**In {Source System}:**
```
{SOURCE_TABLE}:
  field1: value1
  field2: value2
```

**In Gold Layer:**

| Table | Record Created/Updated | Key Values |
|-------|------------------------|------------|
| `{gold_table}` | New row | `{field}` = '{value}' |

**Analytics Impact:**
- {Metric change}
- {Dashboard update}

---

##### Chapter 2: {Next Stage} ({Time})

{Continue pattern for 4-6 chapters...}

---

##### Story Summary: Data Journey

```
┌──────────────────────────────────────────────────────────┐
│          {SCENARIO}: DATA TRAIL THROUGH GOLD LAYER        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  TIME        EVENT              TABLES UPDATED            │
│  ────────────────────────────────────────────────        │
│  {time1}     {event1}           {table1}, {table2}        │
│  {time2}     {event2}           {table3}                  │
│                                                           │
│  TOTAL: {N} tables touched                                │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

{Repeat for 3-4 stories total. Include: Happy Path, Exception, Error Correction, Compliance}

---

## 6. Analytics Use Cases {#6-analytics-use-cases}

### Operational Analytics
| Use Case | Tables Used | Key Metrics |
|----------|-------------|-------------|
| {Use case 1} | `{table1}`, `{table2}` | {Metrics} |

### Revenue Analytics
| Use Case | Tables Used | Key Metrics |
|----------|-------------|-------------|
| {Use case 1} | `{table1}`, `{table2}` | {Metrics} |

### Planning & Forecasting
| Use Case | Tables Used | Key Metrics |
|----------|-------------|-------------|
| {Use case 1} | `{table1}`, `{table2}` | {Metrics} |

---

## 7. AI & ML Opportunities {#7-ai-ml}

| Opportunity | Model Type | Input Tables | Business Value |
|-------------|-----------|--------------|----------------|
| {ML use case 1} | {Classification/Regression/etc.} | `{tables}` | {Value} |

---

## 8. Self-Service Analytics with Genie {#8-genie}

### How to Use Genie

{Brief instructions for accessing Genie Spaces built on this Gold layer.}

### Example Questions to Ask

- "{Natural language question 1}"
- "{Natural language question 2}"
- "{Natural language question 3}"

---

## 9. Data Quality & Monitoring {#9-data-quality}

### Monitoring Dashboard

{Link to monitoring dashboard, refresh schedule, key metrics tracked.}

### Data Freshness

| Table | Update Frequency | Expected Latency |
|-------|-----------------|-------------------|
| `{table}` | {Daily/Hourly} | {< N hours} |

---

## 10. Getting Started {#10-getting-started}

### For Data Engineers
1. Review [Master ERD](../../erd_master.md) for data model
2. Check [YAML schemas](../../yaml/) for table definitions
3. Review [Column Lineage](../../COLUMN_LINEAGE.md) for source mappings

### For Data Analysts
1. Access the SQL warehouse: `{warehouse_name}`
2. Explore Gold tables: `SELECT * FROM {catalog}.{gold_schema}.{table} LIMIT 10`
3. Use Genie Space: {link}

### For Data Scientists
1. Review fact tables for feature engineering opportunities
2. Check [AI & ML Opportunities](#7-ai-ml) section
3. Access MLflow experiments: {link}

### For Business Users
1. Open the [Analytics Dashboard]({link})
2. Try Genie: Ask questions in natural language
3. Contact {team} for custom reports

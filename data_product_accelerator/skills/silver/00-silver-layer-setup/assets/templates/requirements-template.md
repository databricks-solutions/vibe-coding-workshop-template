# Silver Layer Requirements Template

**Fill this in BEFORE creating any Silver layer code.**

---

## Project Context

- **Project Name:** _________________ (e.g., retail_analytics, patient_outcomes)
- **Catalog:** _________________ (e.g., dev_catalog, prod_catalog)
- **Bronze Schema:** _________________ (e.g., my_project_bronze)
- **Silver Schema:** _________________ (e.g., my_project_silver)

---

## Bronze to Silver Table Mapping

| # | Bronze Table | Silver Table | Entity Type | Critical DQ Rules Count | Needs Quarantine? |
|---|-------------|--------------|-------------|------------------------|-------------------|
| 1 | ____________ | _____________ | dimension / fact | ___ | Yes / No |
| 2 | ____________ | _____________ | dimension / fact | ___ | Yes / No |
| 3 | ____________ | _____________ | dimension / fact | ___ | Yes / No |
| 4 | ____________ | _____________ | dimension / fact | ___ | Yes / No |
| 5 | ____________ | _____________ | dimension / fact | ___ | Yes / No |

---

## Data Quality Rules Per Entity

### DQ Rule Categories

| Rule Type | Severity | Pipeline Behavior | Example |
|-----------|----------|-------------------|---------|
| **CRITICAL** | `critical` | Record DROPPED / quarantined | PK NOT NULL, FK present, Date >= 2020 |
| **WARNING** | `warning` | Logged, record passes through | Quantity between 1-100, Price < $1000 |

### Entity 1: _________________

**Critical Rules (record dropped/quarantined if fails):**
- [ ] Primary key: _____________ IS NOT NULL AND LENGTH(...) > 0
- [ ] Foreign key: _____________ IS NOT NULL
- [ ] Required date: _____________ IS NOT NULL AND _____________ >= '____-__-__'
- [ ] Business rule: _____________________________________________
- [ ] Business rule: _____________________________________________

**Warning Rules (logged but record passes):**
- [ ] Reasonableness: _____________ BETWEEN ___ AND ___
- [ ] Recency: _____________ >= CURRENT_DATE() - INTERVAL ___ DAYS
- [ ] Format: LENGTH(_____________) BETWEEN ___ AND ___
- [ ] _____________________________________________

### Entity 2: _________________

**Critical Rules:**
- [ ] Primary key: _____________________________________________
- [ ] Foreign key: _____________________________________________
- [ ] Required date: _____________________________________________
- [ ] Business rule: _____________________________________________

**Warning Rules:**
- [ ] Reasonableness: _____________________________________________
- [ ] Format: _____________________________________________

### Entity 3: _________________

**Critical Rules:**
- [ ] _____________________________________________
- [ ] _____________________________________________

**Warning Rules:**
- [ ] _____________________________________________
- [ ] _____________________________________________

---

## Quarantine Strategy

**Which tables need quarantine?**

General guidelines:
- **Yes** for high-volume transactional/fact tables
- **Yes** for tables with complex validation rules
- **Yes** for tables sourced from unreliable external systems
- **No** for simple dimension/lookup/reference tables

| Silver Table | Quarantine? | Reason |
|-------------|-------------|--------|
| _____________ | Yes / No | __________________________________ |
| _____________ | Yes / No | __________________________________ |
| _____________ | Yes / No | __________________________________ |

---

## Derived Fields

**What simple derived fields should be added in Silver?**

| Silver Table | Field Name | Type | Expression | Purpose |
|-------------|------------|------|------------|---------|
| _____________ | is_return | BOOLEAN | quantity < 0 | Flag return transactions |
| _____________ | _____________ | _________ | _____________ | _____________ |
| _____________ | _____________ | _________ | _____________ | _____________ |

**Remember:** Only simple single-record calculations. Aggregations and joins belong in Gold.

---

## Business Keys

**What natural keys should be hashed into business keys?**

| Silver Table | Business Key Column | Source Columns (natural key) |
|-------------|--------------------|-----------------------------|
| _____________ | {entity}_business_key | col1, col2 |
| _____________ | _____________ | _____________ |
| _____________ | _____________ | _____________ |

---

## Notifications

- **Pipeline failure notifications:** _____________@company.com
- **Data quality alert threshold:** ___% quarantine rate triggers alert

---

## Checklist Before Starting

- [ ] All Bronze tables exist and have been verified
- [ ] Bronze table schemas documented (extract column names, don't hardcode!)
- [ ] DQ rules defined for every Silver table (critical + warning)
- [ ] Quarantine decisions made for each table
- [ ] Derived fields identified
- [ ] Business keys identified
- [ ] Notification recipients confirmed

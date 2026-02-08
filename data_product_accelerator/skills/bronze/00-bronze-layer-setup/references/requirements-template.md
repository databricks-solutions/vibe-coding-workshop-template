# Bronze Layer Requirements Template

Fill in this template before starting Bronze layer setup.

---

## Project Information

- **Project Name:** _________________ (e.g., retail_analytics, supply_chain, customer360)
- **Data Source Strategy:**
  - [ ] **Generate fake data** (Faker - recommended for demos/testing)
  - [ ] **Use existing Bronze tables** (from another schema/catalog)
  - [ ] **Copy from external source** (another workspace, database, CSV files)

---

## Entity List (5-10 Tables)

| # | Entity Name | Type | Domain | Has PII | Classification | Primary Key |
|---|------------|------|--------|---------|----------------|-------------|
| 1 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 2 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 3 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 4 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 5 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 6 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 7 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 8 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 9 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
| 10 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |

### Entity Type Guidance

- **Dimension:** Master data, slowly changing (customers, products, stores, employees)
- **Fact:** Transactional data, high volume (orders, transactions, events, measurements)

### Domain Examples

| Industry | Domains |
|---|---|
| Retail | retail, sales, inventory, product, logistics |
| Finance | accounting, billing, payments, compliance |
| Healthcare | clinical, patient, claims, pharmacy |
| Manufacturing | production, quality, maintenance, supply |
| HR | employee, recruitment, performance, benefits |

### Data Classification

- **Confidential:** Contains PII or highly sensitive data (SSN, health records, financial accounts)
- **Internal:** Business data without PII (sales figures, inventory, product data)
- **Public:** Safe for external sharing (marketing content, public product catalog)

---

## Data Source Details

### Option A: Generate Fake Data (Recommended)

- **Record Counts:**
  - Dimensions: _______ records each (default: 100-200)
  - Facts: _______ records total (default: 1,000-10,000)
- **Date Range:** Last _____ days/months/years (default: 1 year)
- **Faker Seed:** _______ (for reproducibility, default: 42)

### Option B: Use Existing Bronze Tables

- **Source Catalog:** _________________
- **Source Schema:** _________________
- **Copy or Reference:** [ ] Copy data [ ] Reference in place

### Option C: Copy from External Source

- **Source Type:** [ ] CSV Files [ ] External Database [ ] Another Workspace
- **Connection Details:** _________________

---

## Business Ownership

- **Business Owner Team:** _________________ (e.g., "Sales Operations", "Product Team")
- **Business Owner Email:** _________________ @company.com
- **Technical Owner:** Data Engineering (default)
- **Technical Owner Email:** data-engineering@company.com

---

## Input Summary

- Entity list (5-10 tables with schema definitions)
- Data source approach (Faker / Existing / Copy)
- Domain taxonomy and classification
- Record counts for fake data generation

**Output:** 5-10 Bronze Delta tables with realistic test data, Unity Catalog compliance, automatic liquid clustering, and change data feed enabled.

**Time Estimate:** 1-2 hours

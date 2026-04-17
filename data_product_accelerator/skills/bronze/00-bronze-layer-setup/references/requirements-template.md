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

## Approach C Inference Playbook

When the user chose **Approach B (existing tables)** or **Approach C (external copy)**, they usually provide the source but NOT the per-table governance fields. Infer these from the source schema instead of asking; ask only for what cannot be inferred.

### Inferring `contains_pii`

Flag `contains_pii = true` if ANY column name matches these patterns (case-insensitive):

| Pattern | Examples |
|---------|----------|
| Personal identifiers | `email`, `phone`, `mobile`, `ssn`, `national_id`, `passport`, `tax_id` |
| Names | `first_name`, `last_name`, `full_name`, `middle_name` |
| Address | `address`, `street`, `zip`, `postal_code`, `city` (when combined with name/email) |
| Financial | `credit_card`, `card_number`, `account_number`, `iban`, `swift` |
| Health | `medical_record`, `diagnosis`, `patient_id`, `dob`, `date_of_birth` |
| Biometric | `fingerprint`, `face_id`, `biometric` |

Otherwise, `contains_pii = false`.

### Inferring `entity_type` (dimension vs fact)

| Signal | Maps To |
|--------|---------|
| Table name ends in `_dim`, `_lookup`, `_ref`, or is a plural noun describing a master concept (`users`, `products`, `customers`, `hosts`, `amenities`, `countries`, `destinations`, `properties`, `employees`) | `dimension` |
| Table name ends in `_fact`, contains `_events`, `_log`, `_history`, `_transactions`, or describes an action/event (`bookings`, `orders`, `payments`, `clickstream`, `page_views`, `reviews`, `customer_support_logs`, `booking_updates`) | `fact` |
| Junction/mapping tables (two FKs, no business attributes) like `property_amenities` | `fact` (bridge) |

When ambiguous, inspect the column list: presence of a monotonically-increasing PK + timestamps + FKs to multiple dimensions → `fact`. Presence of descriptive attributes + a single PK → `dimension`.

### Inferring `data_classification`

- `contains_pii = true` → `confidential`
- Otherwise → `internal`
- Only set `public` if the user explicitly says the data is safe for external sharing.

### Inferring `domain`

Infer from the source schema or catalog name. Common domains: `booking`, `customer`, `product`, `payment`, `support`, `marketing`, `operations`. If the source schema name itself encodes a domain (e.g., `wanderbricks` → `booking`, `retail_sales` → `retail`), use it.

### What to Ask the User

After inference, present a compact summary and ask only for:

- **`business_owner`** — the team name. This cannot be inferred from schema.
- Any field where inference confidence is low (rare; flag explicitly, e.g., "I couldn't determine whether `audit_logs` is a fact or dimension — please confirm").

### Output

Populate the Entity List table above using inferred values. The agent's final deliverable in Step 1 is a filled requirements template, NOT a prompt to the user for every field.

---

## Input Summary

- Entity list (5-10 tables with schema definitions)
- Data source approach (Faker / Existing / Copy)
- Domain taxonomy and classification
- Record counts for fake data generation

**Output:** 5-10 Bronze Delta tables with realistic test data, Unity Catalog compliance, automatic liquid clustering, and change data feed enabled.

**Time Estimate:** 1-2 hours

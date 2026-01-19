# Gold Layer Design Prompt

## 🚀 Quick Start (4-8 hours)

**Goal:** Design complete Gold layer schema with ERD(s), YAML files, lineage tracking, and comprehensive business documentation

**What You'll Create:**
1. **Mermaid ERD(s)** - Visual diagrams of dimensions, facts, and relationships
   - **Master ERD** (always) - Complete model overview
   - **Domain ERDs** (if 9+ tables) - Focused domain-specific views
2. **YAML Schema Files** - One per table with PRIMARY KEY, FOREIGN KEYs, columns, descriptions
3. **Documentation** - Dual-purpose (business + technical) table/column comments
4. **Business Onboarding Guide** ⭐ **MANDATORY** - Stories, processes, and table mapping for new team members
5. **Source Table Mapping** ⭐ **MANDATORY** - CSV with inclusion/exclusion rationale for ALL source tables
6. **Column Lineage CSV** ⭐ **MANDATORY** - Machine-readable Bronze → Silver → Gold column mapping
7. **Design Review** - Stakeholder approval before implementation

**Fast Track:**
```markdown
## Deliverables Checklist:

### ERD Organization (based on table count)
- [ ] gold_layer_design/erd_master.md - Complete model (ALWAYS required)
- [ ] gold_layer_design/erd_summary.md - Domain overview (if 20+ tables)
- [ ] gold_layer_design/erd/erd_{domain}.md - Domain ERDs (if 9+ tables)

### YAML Schemas (organized by domain)
- [ ] gold_layer_design/yaml/{domain}/dim_*.yaml - Dimension schemas with lineage
- [ ] gold_layer_design/yaml/{domain}/fact_*.yaml - Fact schemas with lineage

### Supporting Documentation (ALL MANDATORY)
- [ ] gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md - ⭐ Business processes + stories + table mapping
- [ ] gold_layer_design/COLUMN_LINEAGE.csv - ⭐ Machine-readable column lineage
- [ ] gold_layer_design/COLUMN_LINEAGE.md - Human-readable lineage documentation
- [ ] gold_layer_design/SOURCE_TABLE_MAPPING.csv - ⭐ Source table inclusion/exclusion with rationale
- [ ] gold_layer_design/DESIGN_SUMMARY.md - Grain + SCD + transformation decisions
- [ ] gold_layer_design/DESIGN_GAP_ANALYSIS.md - Coverage analysis and remaining gaps
- [ ] gold_layer_design/README.md - Quick navigation to all documentation
```

**ERD Organization Decision:**
| Tables | ERD Strategy |
|--------|--------------|
| 1-8 | Master ERD only |
| 9-20 | Master ERD + Domain ERDs |
| 20+ | Master ERD + Domain ERDs + Summary ERD |

**Key Design Decisions:**
- **Grain:** One row per _what_? (Must be explicit for each fact)
- **SCD Type:** Type 1 (overwrite) or Type 2 (history tracking) per dimension
- **Relationships:** Which FKs link facts to dimensions?
- **Measures:** Pre-aggregated (daily sales) vs transactional (line items)
- **Domains:** How to logically group tables for manageability

**YAML = Single Source of Truth:**
- All column names, types, constraints, descriptions in YAML
- Implementation reads YAML (no manual DDL)
- Schema changes = YAML edits only

**Output:** Complete schema design ready for `03b-gold-layer-implementation-prompt.md`

📖 **Full guide below** for detailed design process →

---

## Quick Reference

**Use this prompt to design the Gold layer schema and documentation BEFORE implementation.**

---

## 📋 Your Requirements (Fill These In First)

### Project Context
- **Project Name:** _________________ (e.g., retail_analytics, patient_outcomes)
- **Silver Schema:** _________________ (e.g., my_project_silver)
- **Gold Schema:** _________________ (e.g., my_project_gold)
- **Business Domain:** _________________ (e.g., retail, healthcare, finance)

### Design Goals
- **Primary Use Cases:** _________________ (e.g., sales reporting, inventory analysis)
- **Key Stakeholders:** _________________ (e.g., Sales Operations, Finance Team)
- **Reporting Frequency:** _________________ (e.g., Daily, Weekly, Monthly)

---

## Core Philosophy: Design First, Code Later

**⚠️ CRITICAL PRINCIPLE:**

Gold layer design must be **documented and approved** before implementation:

- ✅ **Complete ERD** with all dimensions, facts, and relationships
- ✅ **YAML schema files** as single source of truth
- ✅ **Documented grain** for each fact table
- ✅ **SCD strategy** for each dimension
- ✅ **Dual-purpose documentation** (business + technical)
- ✅ **Stakeholder review** and approval

**Why This Matters:**
- Gold layer is the **business contract** for analytics
- Schema changes are expensive after deployment
- Documentation enables self-service analytics
- Clear grain prevents incorrect aggregations

---

## Step 1: Dimensional Model Design

### 1.1 Identify Dimensions (2-5 tables)

| # | Dimension Name | Business Key | SCD Type | Source Silver Table | Contains PII |
|---|---------------|--------------|----------|---------------------|--------------|
| 1 | dim_customer | customer_id | Type 2 | silver_customer_dim | Yes |
| 2 | dim_product | product_id | Type 1 | silver_product_dim | No |
| 3 | dim_date | date | Type 1 | Generated | No |
| 4 | dim_store | store_number | Type 2 | silver_store_dim | Yes |
| 5 | ____________ | ___________ | ______ | _________________ | _____ |

**SCD Type Decision Matrix:**

| SCD Type | When to Use | Examples |
|---|---|---|
| **Type 1 (Overwrite)** | History doesn't matter, attributes rarely change | Date dimensions, simple lookups, product categories |
| **Type 2 (Track History)** | Need to track changes over time for point-in-time analysis | Customer addresses, product prices, store status |

**SCD Type 2 Requirements:**
- Surrogate key (e.g., `store_key` as MD5 hash)
- Business key (e.g., `store_number`)
- `effective_from` TIMESTAMP
- `effective_to` TIMESTAMP (NULL for current)
- `is_current` BOOLEAN

### 1.2 Identify Facts (1-3 tables)

| # | Fact Name | Grain | Source Silver Tables | Update Frequency |
|---|-----------|-------|---------------------|------------------|
| 1 | fact_sales_daily | store-product-day | silver_transactions | Daily |
| 2 | fact_inventory_snapshot | store-product-day | silver_inventory | Daily |
| 3 | _____________ | _________________ | ___________________ | ________ |

**Grain Definition** (One row per...):
- **Store-Product-Day:** One row for each store-product combination per day
- **Customer-Month:** One row for each customer per month
- **Patient-Encounter:** One row per patient visit
- **Transaction:** One row per individual transaction (not aggregated)

**Grain Types:**
- **Aggregated:** Pre-summarized (daily_sales, weekly_revenue)
- **Transaction:** Individual events (query_execution, api_request)
- **Snapshot:** Point-in-time state (inventory_snapshot, account_balance)

**See [24-fact-table-grain-validation.mdc](mdc:.cursor/rules/24-fact-table-grain-validation.mdc) for grain validation patterns.**

### 1.3 Define Measures & Metrics

For each fact table:

| Fact Table | Measure Name | Data Type | Calculation Logic | Business Purpose |
|---|---|---|---|---|
| fact_sales_daily | gross_revenue | DECIMAL(18,2) | SUM(CASE WHEN qty > 0 THEN revenue END) | Revenue before returns |
| fact_sales_daily | net_revenue | DECIMAL(18,2) | SUM(revenue) | Revenue after returns (primary KPI) |
| fact_sales_daily | net_units | BIGINT | SUM(quantity) | Units sold after returns |
| fact_sales_daily | transaction_count | BIGINT | COUNT(DISTINCT transaction_id) | Number of transactions |
| fact_sales_daily | avg_transaction_value | DECIMAL(18,2) | net_revenue / transaction_count | Basket size metric |

**Measure Type Guidelines:**
- **Revenue/Amount:** DECIMAL(18,2) for monetary values
- **Quantities:** BIGINT for unit counts
- **Counts:** BIGINT for transaction/customer counts
- **Averages:** DECIMAL(18,2) calculated from other measures
- **Rates/Percentages:** DECIMAL(5,2) for percentages (e.g., 45.32%)

### 1.4 Define Relationships (FK Constraints)

| Fact Table | Dimension | FK Column | PK Column | Relationship |
|---|---|---|---|---|
| fact_sales_daily | dim_store | store_number | store_number | Many-to-One |
| fact_sales_daily | dim_product | upc_code | upc_code | Many-to-One |
| fact_sales_daily | dim_date | transaction_date | date | Many-to-One |

**Relationship Rules:**
- Facts → Dimensions: Always Many-to-One
- Use business keys for FK references (not surrogate keys)
- Document all FK constraints in DDL
- Use `NOT ENFORCED` (informational only)

### 1.5 Assign Tables to Domains

**Assign each table to exactly ONE domain for ERD and YAML organization:**

| # | Table Name | Type | Domain | Domain ERD | YAML Path |
|---|------------|------|--------|------------|-----------|
| 1 | dim_store | Dimension | 🏪 Location | erd_location.md | yaml/location/ |
| 2 | dim_region | Dimension | 🏪 Location | erd_location.md | yaml/location/ |
| 3 | dim_product | Dimension | 📦 Product | erd_product.md | yaml/product/ |
| 4 | dim_date | Dimension | 📅 Time | erd_time.md | yaml/time/ |
| 5 | fact_sales_daily | Fact | 💰 Sales | erd_sales.md | yaml/sales/ |
| 6 | fact_inventory_snapshot | Fact | 📊 Inventory | erd_inventory.md | yaml/inventory/ |

**Standard Domain Categories:**

| Domain | Emoji | Description | Typical Tables |
|--------|-------|-------------|----------------|
| **Location** | 🏪 | Geographic hierarchy | dim_store, dim_region, dim_territory, dim_country |
| **Product** | 📦 | Product hierarchy | dim_product, dim_brand, dim_category, dim_supplier |
| **Time** | 📅 | Temporal dimensions | dim_date, dim_time, dim_fiscal_period |
| **Customer** | 👤 | Customer attributes | dim_customer, dim_segment, dim_loyalty_tier |
| **Sales** | 💰 | Revenue & transactions | fact_sales_*, dim_promotion, dim_channel |
| **Inventory** | 📊 | Stock & replenishment | fact_inventory_*, dim_warehouse |
| **Finance** | 💵 | Financial measures | fact_gl_*, dim_account, dim_cost_center |
| **Operations** | ⚙️ | Operational metrics | fact_shipment_*, dim_carrier, dim_route |

**Domain Assignment Rules:**
1. **Dimensions** → Assign to domain based on primary business concept
2. **Facts** → Assign to domain of the primary measure (sales fact → Sales)
3. **Bridge tables** → Assign to domain of the "many" side
4. **Conformed dimensions** (date, geography) → Own domain, referenced by others

**Based on total table count, determine ERD strategy:**

| Total Tables | ERD Strategy |
|--------------|--------------|
| 1-8 | Master ERD only |
| 9-20 | Master ERD + Domain ERDs |
| 20+ | Master ERD + Domain ERDs + Summary ERD |

---

## Step 2: Create ERD(s) with Mermaid

### 2.1 ERD Organization Strategy

**First, assess your model complexity:**

| Total Tables | ERD Strategy | Rationale |
|--------------|--------------|-----------|
| **1-8 tables** | Master ERD only | Simple enough for single diagram |
| **9-20 tables** | Master + Domain ERDs | Too complex for single view, needs breakdown |
| **20+ tables** | Master + Domain + Summary | Focus on domains, summary for navigation |

**Standard Domains for Organization:**

| Domain | Emoji | Typical Tables |
|--------|-------|----------------|
| **Location** | 🏪 | dim_store, dim_region, dim_territory |
| **Product** | 📦 | dim_product, dim_brand, dim_category |
| **Time** | 📅 | dim_date, dim_fiscal_period |
| **Customer** | 👤 | dim_customer, dim_segment |
| **Sales** | 💰 | fact_sales_*, dim_promotion |
| **Inventory** | 📊 | fact_inventory_*, dim_warehouse |
| **Operations** | ⚙️ | fact_shipment_*, dim_carrier, dim_route |

**Assign each table to exactly one domain:**
- Dimensions → Domain based on business concept
- Facts → Domain of primary measure (sales fact → Sales)
- Conformed dimensions (date, geography) → Own domain, referenced by others

---

### 2.2 Master ERD Pattern (Always Create)

The Master ERD shows the **complete data model** with all tables and relationships.

**File:** `gold_layer_design/erd_master.md`

```mermaid
erDiagram
  %% ═══════════════════════════════════════════════
  %% 🏪 LOCATION DOMAIN
  %% ═══════════════════════════════════════════════
  dim_store {
    string store_key PK
    string store_number
    string store_name
    string city
    string state
    boolean is_current
    timestamp effective_from
    timestamp effective_to
  }
  
  %% ═══════════════════════════════════════════════
  %% 📦 PRODUCT DOMAIN
  %% ═══════════════════════════════════════════════
  dim_product {
    string product_key PK
    string upc_code
    string product_description
    string brand
    string category
  }
  
  %% ═══════════════════════════════════════════════
  %% 📅 TIME DOMAIN
  %% ═══════════════════════════════════════════════
  dim_date {
    date date_value PK
    int year
    int quarter
    int month
    string month_name
    int week_of_year
    boolean is_weekend
  }
  
  %% ═══════════════════════════════════════════════
  %% 💰 SALES DOMAIN (Fact)
  %% ═══════════════════════════════════════════════
  fact_sales_daily {
    string store_number PK
    string upc_code PK
    date transaction_date PK
    decimal gross_revenue
    decimal net_revenue
    bigint net_units
    bigint transaction_count
    decimal avg_transaction_value
  }
  
  %% ═══════════════════════════════════════════════
  %% RELATIONSHIPS
  %% ═══════════════════════════════════════════════
  dim_store   ||--o{ fact_sales_daily : by_store_number
  dim_product ||--o{ fact_sales_daily : by_upc_code
  dim_date    ||--o{ fact_sales_daily : by_transaction_date
```

**Master ERD Requirements:**
- ✅ Show ALL dimensions and facts (complete model)
- ✅ Group tables by domain with section headers
- ✅ Use domain emoji markers for visual clarity
- ✅ Show all relationships with cardinality
- ✅ Use `PK` markers only (no inline descriptions)
- ✅ Use `by_{column}` pattern for relationship labels
- ✅ Include Domain Index table after diagram

**Domain Index (include after Master ERD):**

| Domain | Tables | Primary Fact | Detail ERD |
|--------|--------|--------------|------------|
| 🏪 Location | dim_store | N/A | [erd_location.md](erd/erd_location.md) |
| 📦 Product | dim_product | N/A | [erd_product.md](erd/erd_product.md) |
| 📅 Time | dim_date | N/A | [erd_time.md](erd/erd_time.md) |
| 💰 Sales | fact_sales_daily | fact_sales_daily | [erd_sales.md](erd/erd_sales.md) |

---

### 2.3 Domain ERD Pattern (If 9+ Tables)

Domain ERDs show a **focused view** of tables within a single business domain.

**File:** `gold_layer_design/erd/erd_{domain}.md`

**Purpose:**
- Focused stakeholder discussions
- Development team reference
- Domain-specific change management
- Parallel development by teams

**Template:**

```markdown
# Sales Domain ERD

## Domain Overview
Sales domain contains transactional fact tables and related dimensions for 
revenue analysis, transaction trends, and promotional effectiveness.

**Tables in this domain:** 3
**Related domains:** Location, Product, Time

## Entity Relationship Diagram

```mermaid
erDiagram
  %% ═══════════════════════════════════════════════
  %% 💰 SALES DOMAIN - Facts
  %% ═══════════════════════════════════════════════
  fact_sales_daily {
    string store_number PK
    string upc_code PK
    date transaction_date PK
    decimal gross_revenue
    decimal net_revenue
    bigint net_units
    bigint transaction_count
    decimal avg_transaction_value
  }
  
  dim_promotion {
    string promotion_key PK
    string promotion_code
    string promotion_name
    date start_date
    date end_date
  }
  
  %% ═══════════════════════════════════════════════
  %% CROSS-DOMAIN REFERENCES (External)
  %% ═══════════════════════════════════════════════
  dim_store["🏪 dim_store (Location)"] {
    string store_number PK
  }
  
  dim_product["📦 dim_product (Product)"] {
    string upc_code PK
  }
  
  dim_date["📅 dim_date (Time)"] {
    date date_value PK
  }
  
  %% ═══════════════════════════════════════════════
  %% RELATIONSHIPS
  %% ═══════════════════════════════════════════════
  dim_store   ||--o{ fact_sales_daily : by_store_number
  dim_product ||--o{ fact_sales_daily : by_upc_code
  dim_date    ||--o{ fact_sales_daily : by_transaction_date
  dim_promotion ||--o{ fact_sales_daily : by_promotion_key
```

## Cross-Domain Dependencies

| External Table | Domain | Relationship | Purpose |
|----------------|--------|--------------|---------|
| dim_store | Location | fact → dim_store | Geographic sales analysis |
| dim_product | Product | fact → dim_product | Product performance |
| dim_date | Time | fact → dim_date | Temporal trends |

## Related Documentation
- [Master ERD](../erd_master.md) - Complete model
- [Location Domain ERD](erd_location.md) - Store dimension details
- [YAML Schema](../yaml/sales/fact_sales_daily.yaml) - Implementation schema
```

**Domain ERD Requirements:**
- ✅ Focus on tables within the domain
- ✅ Show external tables with domain labels (e.g., `["🏪 dim_store (Location)"]`)
- ✅ Include Cross-Domain Dependencies table
- ✅ Link to Master ERD and related Domain ERDs
- ✅ Document domain-specific business context

---

### 2.4 Summary ERD Pattern (If 20+ Tables)

For very large models, create a high-level view showing domains as entities:

**File:** `gold_layer_design/erd_summary.md`

```mermaid
erDiagram
  LOCATION["🏪 Location Domain"] {
    string dim_store
    string dim_region
    string dim_territory
  }
  
  PRODUCT["📦 Product Domain"] {
    string dim_product
    string dim_brand
    string dim_category
  }
  
  TIME["📅 Time Domain"] {
    string dim_date
    string dim_fiscal_period
  }
  
  SALES["💰 Sales Domain"] {
    string fact_sales_daily
    string fact_sales_hourly
    string dim_promotion
  }
  
  INVENTORY["📊 Inventory Domain"] {
    string fact_inventory_snapshot
    string dim_warehouse
  }
  
  %% Domain relationships
  LOCATION ||--o{ SALES : "store analysis"
  PRODUCT  ||--o{ SALES : "product performance"
  TIME     ||--o{ SALES : "temporal trends"
  LOCATION ||--o{ INVENTORY : "warehouse stock"
  PRODUCT  ||--o{ INVENTORY : "product stock"
```

---

### 2.5 File Organization Structure

```
gold_layer_design/
├── erd_master.md                 # Complete model (ALWAYS)
├── erd_summary.md                # Domain overview (20+ tables)
├── erd/                          # Domain ERDs (9+ tables)
│   ├── erd_location.md
│   ├── erd_product.md
│   ├── erd_time.md
│   ├── erd_sales.md
│   ├── erd_inventory.md
│   └── erd_customer.md
├── yaml/                         # YAML schemas organized by domain
│   ├── location/
│   │   └── dim_store.yaml
│   ├── product/
│   │   └── dim_product.yaml
│   ├── time/
│   │   └── dim_date.yaml
│   └── sales/
│       └── fact_sales_daily.yaml
├── COLUMN_LINEAGE.md
└── DESIGN_SUMMARY.md
```

**See [13-mermaid-erd-patterns.mdc](mdc:.cursor/rules/gold/13-mermaid-erd-patterns.mdc) for complete ERD syntax and formatting patterns.**

---

## Step 3: Create YAML Schema Files

### 3.1 YAML Directory Structure (Domain-Organized)

**Organize YAML files by domain to match ERD organization:**

```
gold_layer_design/
├── erd_master.md                 # Complete ERD (always)
├── erd_summary.md                # Domain summary (20+ tables)
├── erd/                          # Domain ERDs (9+ tables)
│   ├── erd_location.md
│   ├── erd_product.md
│   ├── erd_time.md
│   ├── erd_sales.md
│   └── erd_inventory.md
├── yaml/                         # YAML schemas BY DOMAIN
│   ├── location/                 # 🏪 Location domain
│   │   ├── dim_store.yaml
│   │   ├── dim_region.yaml
│   │   └── dim_territory.yaml
│   ├── product/                  # 📦 Product domain
│   │   ├── dim_product.yaml
│   │   ├── dim_brand.yaml
│   │   └── dim_category.yaml
│   ├── time/                     # 📅 Time domain
│   │   ├── dim_date.yaml
│   │   └── dim_fiscal_period.yaml
│   ├── sales/                    # 💰 Sales domain
│   │   ├── fact_sales_daily.yaml
│   │   ├── fact_sales_hourly.yaml
│   │   └── dim_promotion.yaml
│   ├── inventory/                # 📊 Inventory domain
│   │   ├── fact_inventory_snapshot.yaml
│   │   └── dim_warehouse.yaml
│   └── README.md                 # Domain index
├── COLUMN_LINEAGE.md             # Generated lineage doc
└── DESIGN_SUMMARY.md             # Design decisions
```

**Domain Assignment Rules:**
- ✅ Each table belongs to exactly ONE domain
- ✅ YAML folder name matches domain name in ERDs
- ✅ Conformed dimensions (date, geography) get own domain
- ✅ Facts go to domain of their primary business measure

### 3.2 Dimension YAML Template (SCD Type 2)

**File: `gold_layer_design/yaml/{domain}/dim_store.yaml`**

```yaml
# Table metadata
table_name: dim_store
domain: retail
bronze_source: retail.stores

# Table description (dual-purpose: business + technical)
description: >
  Gold layer conformed store dimension with SCD Type 2 history tracking.
  Business: Maintains complete store lifecycle history including address changes, 
  status updates, and operational attributes. Each store version tracked separately 
  for point-in-time analysis. Used for geographic analysis, territory management, 
  and historical performance comparisons.
  Technical: Slowly Changing Dimension Type 2 implementation with effective dating.
  Surrogate keys enable proper fact table joins to historical store states.
  Updates via Delta MERGE from Silver streaming tables.

# Grain definition
grain: "One row per store_number per version (SCD Type 2)"

# SCD strategy
scd_type: 2

# Primary key definition
primary_key:
  columns: ['store_key']
  composite: false

# Business key (unique constraint)
business_key:
  columns: ['store_number']
  
# Foreign key definitions (applied separately)
foreign_keys: []

# Column definitions
columns:
  # Surrogate Key
  - name: store_key
    type: STRING
    nullable: false
    description: >
      Surrogate key uniquely identifying each version of a store record.
      Business: Used for joining fact tables to dimension.
      Technical: MD5 hash generated from store_id and processed_timestamp 
      to ensure uniqueness across SCD Type 2 versions.
  
  # Business Key
  - name: store_number
    type: STRING
    nullable: false
    description: >
      Business key identifying the physical store location.
      Business: The primary identifier used by store operations and field teams.
      Technical: Natural key from source system, same across all historical versions of this store.
  
  # Attributes
  - name: store_name
    type: STRING
    nullable: true
    description: >
      Official name of the retail store location.
      Business: Used for customer-facing communications and internal reporting.
      Technical: Free-text field from POS system, may change over time.
  
  - name: city
    type: STRING
    nullable: true
    description: >
      City name where the store is located.
      Business: Used for geographic analysis and territory management.
      Technical: Standardized city name from address validation.
  
  - name: state
    type: STRING
    nullable: true
    description: >
      Two-letter US state code.
      Business: Used for state-level sales analysis and compliance reporting.
      Technical: Validated against standard US state abbreviations (CA, TX, NY, etc.).
  
  # SCD Type 2 Columns
  - name: effective_from
    type: TIMESTAMP
    nullable: false
    description: >
      Start timestamp for this version of the store record.
      Business: Indicates when this set of store attributes became active.
      Technical: SCD Type 2 field, populated from processed_timestamp when new version created.
  
  - name: effective_to
    type: TIMESTAMP
    nullable: true
    description: >
      End timestamp for this version of the store record.
      Business: NULL indicates this is the current version. Non-NULL indicates historical record.
      Technical: SCD Type 2 field, set to next version effective_from when superseded.
  
  - name: is_current
    type: BOOLEAN
    nullable: false
    description: >
      Flag indicating if this is the current active version.
      Business: TRUE for current store attributes, FALSE for historical records. 
      Use with WHERE is_current = true to get latest state.
      Technical: SCD Type 2 flag, updated to FALSE when new version created.
  
  # Audit Columns
  - name: record_created_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when this record was first inserted into the Gold layer.
      Business: Audit field for data lineage and troubleshooting.
      Technical: Set once at INSERT time, never updated.
  
  - name: record_updated_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when this record was last modified.
      Business: Audit field showing data freshness and update history.
      Technical: Updated on every MERGE operation that modifies the record.

# Table properties
table_properties:
  contains_pii: true
  data_classification: confidential
  business_owner: Retail Operations
  technical_owner: Data Engineering
  update_frequency: Daily
```

### 3.3 Fact Table YAML Template

**File: `gold_layer_design/yaml/{domain}/fact_sales_daily.yaml`**

```yaml
# Table metadata
table_name: fact_sales_daily
domain: sales
bronze_source: sales.transactions

# Table description
description: >
  Gold layer daily sales fact table with pre-aggregated metrics at store-product-day grain.
  Business: Primary source for sales performance reporting including revenue, units, 
  discounts, returns, and customer loyalty metrics. Aggregated from transaction-level 
  Silver data for fast query performance. Used for dashboards, executive reporting, 
  and sales analysis.
  Technical: Grain is one row per store-product-date combination. Pre-aggregated measures 
  eliminate need for transaction-level scans, surrogate keys enable fast dimension joins.

# Grain definition
grain: "One row per store_number-upc_code-transaction_date combination (daily aggregate)"

# Primary key definition (composite grain)
primary_key:
  columns: ['store_number', 'upc_code', 'transaction_date']
  composite: true

# Foreign key definitions
foreign_keys:
  - columns: ['store_number']
    references: dim_store(store_number)
    nullable: false
  - columns: ['upc_code']
    references: dim_product(upc_code)
    nullable: false
  - columns: ['transaction_date']
    references: dim_date(date)
    nullable: false

# Column definitions
columns:
  # Foreign Keys
  - name: store_number
    type: STRING
    nullable: false
    description: >
      Store identifier.
      Business: Links to store dimension for location-based analysis.
      Technical: FK to dim_store.store_number (business key for query simplicity).
    lineage:
      bronze_table: bronze_transactions
      bronze_column: store_number
      silver_table: silver_transactions
      silver_column: store_number
      transformation: "DIRECT_COPY"  # No transformation, direct column copy
  
  - name: upc_code
    type: STRING
    nullable: false
    description: >
      Product UPC code.
      Business: Links to product dimension for product analysis.
      Technical: FK to dim_product.upc_code (business key).
  
  - name: transaction_date
    type: DATE
    nullable: false
    description: >
      Transaction date.
      Business: Date dimension for time-based analysis and trending.
      Technical: FK to dim_date.date.
  
  # Revenue Measures
  - name: gross_revenue
    type: DECIMAL(18,2)
    nullable: true
    description: >
      Total revenue before returns.
      Business: Gross sales amount, primary revenue indicator before adjustments.
      Technical: SUM(CASE WHEN quantity > 0 THEN revenue ELSE 0 END) from Silver transactions.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: final_sales_price
      silver_table: silver_transactions
      silver_column: final_sales_price
      transformation: "AGGREGATE_SUM_CONDITIONAL"  # SUM(CASE WHEN quantity_sold > 0 THEN final_sales_price ELSE 0 END)
      aggregation_logic: "SUM(CASE WHEN quantity_sold > 0 THEN final_sales_price ELSE 0 END)"
      groupby_columns: ['store_number', 'upc_code', 'transaction_date']
  
  - name: net_revenue
    type: DECIMAL(18,2)
    nullable: true
    description: >
      Net revenue after subtracting returns.
      Business: The actual revenue realized from sales, primary KPI for financial reporting.
      Technical: SUM(revenue) from Silver (includes negative values for returns).
  
  # Unit Measures
  - name: net_units
    type: BIGINT
    nullable: true
    description: >
      Net units sold after returns.
      Business: Actual quantity sold, used for inventory planning and demand forecasting.
      Technical: SUM(quantity) from Silver (includes negative values for returns).
  
  # Transaction Counts
  - name: transaction_count
    type: BIGINT
    nullable: true
    description: >
      Number of transactions.
      Business: Volume of customer interactions, used for store performance and staffing.
      Technical: COUNT(DISTINCT transaction_id) from Silver.
  
  # Derived Metrics
  - name: avg_transaction_value
    type: DECIMAL(18,2)
    nullable: true
    description: >
      Average dollar value per transaction.
      Business: Basket size indicator for pricing and promotion strategies.
      Technical: net_revenue / transaction_count.
  
  # Audit Columns
  - name: record_created_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when this daily aggregate was first created.
      Business: Audit field for data lineage and pipeline troubleshooting.
      Technical: Set during initial MERGE INSERT, remains constant.
  
  - name: record_updated_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when this daily aggregate was last refreshed.
      Business: Shows data freshness for this date, useful for validating 
      late-arriving transactions were included.
      Technical: Updated on every MERGE operation that touches this record.

# Table properties
table_properties:
  contains_pii: false
  data_classification: internal
  business_owner: Sales Operations
  technical_owner: Data Engineering
  update_frequency: Daily
  aggregation_level: daily
```

### 3.4 Date Dimension YAML Template

**File: `gold_layer_design/yaml/time/dim_date.yaml`**

```yaml
# Table metadata
table_name: dim_date
domain: time
bronze_source: generated

description: >
  Gold layer date dimension with calendar attributes.
  Business: Standard date dimension for time-based analysis, trending, and reporting 
  across all fact tables. Supports fiscal year, holiday tracking, and weekday analysis.
  Technical: Populated for date range covering historical data plus future dates 
  for forecasting. Not sourced from Silver, generated internally.

grain: "One row per calendar date"

scd_type: 1

primary_key:
  columns: ['date']
  composite: false

foreign_keys: []

columns:
  - name: date
    type: DATE
    nullable: false
    description: >
      Calendar date.
      Business: The date dimension for all time-based analysis.
      Technical: Primary key for date dimension, no surrogate key needed.
  
  - name: year
    type: INT
    nullable: false
    description: >
      Calendar year (YYYY).
      Business: Year for annual analysis and YoY comparisons.
      Technical: YEAR(date).
  
  - name: quarter
    type: INT
    nullable: false
    description: >
      Calendar quarter (1-4).
      Business: Quarter for quarterly reporting and seasonality analysis.
      Technical: QUARTER(date).
  
  - name: month
    type: INT
    nullable: false
    description: >
      Calendar month (1-12).
      Business: Month for monthly trends and MoM comparisons.
      Technical: MONTH(date).
  
  - name: month_name
    type: STRING
    nullable: false
    description: >
      Month name (January, February, etc.).
      Business: User-friendly month labels for reports and dashboards.
      Technical: DATE_FORMAT(date, 'MMMM').
  
  - name: week_of_year
    type: INT
    nullable: false
    description: >
      ISO week of year (1-53).
      Business: Week-level analysis for short-term trends.
      Technical: WEEKOFYEAR(date).
  
  - name: day_of_week
    type: INT
    nullable: false
    description: >
      Day of week (1=Sunday, 7=Saturday).
      Business: Day-of-week analysis for staffing and promotions.
      Technical: DAYOFWEEK(date).
  
  - name: day_of_week_name
    type: STRING
    nullable: false
    description: >
      Day name (Monday, Tuesday, etc.).
      Business: User-friendly day labels.
      Technical: DATE_FORMAT(date, 'EEEE').
  
  - name: is_weekend
    type: BOOLEAN
    nullable: false
    description: >
      Weekend indicator.
      Business: Weekend vs weekday analysis for traffic patterns.
      Technical: day_of_week IN (1, 7).
  
  - name: is_holiday
    type: BOOLEAN
    nullable: true
    description: >
      Holiday indicator.
      Business: Holiday impact on sales and staffing.
      Technical: Populated from holiday calendar lookup.

table_properties:
  contains_pii: false
  data_classification: public
  business_owner: Enterprise Data
  technical_owner: Data Engineering
  update_frequency: Static
```

**See [25-yaml-driven-gold-setup.mdc](mdc:.cursor/rules/25-yaml-driven-gold-setup.mdc) for YAML-driven implementation patterns.**

---

## Step 4: Documentation Standards

### 4.1 Dual-Purpose Column Descriptions

**Every column description must serve both business and technical audiences:**

**Pattern:**
```
[Natural description]. Business: [business context and use cases]. Technical: [implementation details].
```

**Examples:**

```yaml
# Surrogate Key
store_key STRING NOT NULL
  description: >
    Surrogate key uniquely identifying each version of a store record.
    Business: Used for joining fact tables to dimension.
    Technical: MD5 hash generated from store_id and processed_timestamp 
    to ensure uniqueness across SCD Type 2 versions.

# Measure
net_revenue DECIMAL(18,2)
  description: >
    Net revenue after subtracting returns from gross revenue.
    Business: The actual revenue realized from sales, primary KPI for financial reporting.
    Technical: gross_revenue - return_amount, represents true daily sales value.

# Boolean Flag
is_current BOOLEAN
  description: >
    Flag indicating if this is the current active version.
    Business: TRUE for current store attributes, FALSE for historical records. 
    Use with WHERE is_current = true to get latest state.
    Technical: SCD Type 2 flag, updated to FALSE when new version created.
```

**Documentation Requirements:**
- ✅ Opening sentence: Clear, natural language definition
- ✅ Business section: Purpose, use cases, business rules
- ✅ Technical section: Data type, calculation, source, constraints
- ❌ No "LLM:" prefix (use natural dual-purpose format)

**See [12-gold-layer-documentation.mdc](mdc:.cursor/rules/12-gold-layer-documentation.mdc) for complete documentation standards.**

### 4.2 Table Description Standards

**Table descriptions must include:**
1. Layer and purpose
2. Grain (what one row represents)
3. Business use cases
4. Technical implementation

**Example:**
```yaml
description: >
  Gold layer daily sales fact table with pre-aggregated metrics at store-product-day grain.
  Business: Primary source for sales performance reporting including revenue, units, 
  discounts, returns, and customer loyalty metrics. Aggregated from transaction-level 
  Silver data for fast query performance. Used for dashboards, executive reporting, 
  and sales analysis.
  Technical: Grain is one row per store-product-date combination. Pre-aggregated measures 
  eliminate need for transaction-level scans, surrogate keys enable fast dimension joins.
```

---

## Step 4: Column-Level Lineage & Transformation Documentation

### 4.1 Why Lineage Documentation Matters

**Problem:** Schema mismatches cause 33% of Gold layer bugs during implementation
- Column names differ between Bronze, Silver, and Gold
- Transformations are implicit (not documented)
- Manual column mapping prone to errors
- Hard to trace data from source to target

**Solution:** Explicit lineage documentation in YAML for every column

**Benefits:**
- ✅ **Prevents schema mismatches** - Explicit Bronze → Silver → Gold mapping
- ✅ **Documents transformations** - Clear logic for each column
- ✅ **Generates merge scripts** - Can auto-generate column mappings
- ✅ **Audit trail** - Complete data lineage from source
- ✅ **Onboarding** - New developers understand data flow

### 4.2 Lineage Schema in YAML

**Add `lineage` section to EVERY column definition:**

```yaml
columns:
  - name: {gold_column_name}
    type: {DATA_TYPE}
    nullable: {true|false}
    description: >
      {Dual-purpose description}
    lineage:
      bronze_table: {bronze_table_name}
      bronze_column: {bronze_column_name}
      silver_table: {silver_table_name}
      silver_column: {silver_column_name}
      transformation: "{TRANSFORMATION_TYPE}"
      transformation_logic: "{Explicit SQL/PySpark expression}"
      notes: "{Any special considerations}"
```

### 4.3 Standard Transformation Types

**Use these standard transformation type codes:**

| Transformation Type | Description | Example | Implementation |
|---|---|---|---|
| `DIRECT_COPY` | No transformation, direct column copy | store_number | `col("store_number")` |
| `RENAME` | Column renamed, no value change | company_rcn → company_retail_control_number | `.withColumn("company_retail_control_number", col("company_rcn"))` |
| `CAST` | Data type conversion | STRING → INT, DATE → TIMESTAMP | `.withColumn("column", col("column").cast("int"))` |
| `AGGREGATE_SUM` | Simple SUM aggregation | SUM(revenue) | `spark_sum("revenue")` |
| `AGGREGATE_SUM_CONDITIONAL` | Conditional SUM | SUM(CASE WHEN qty > 0 THEN revenue END) | `spark_sum(when(col("qty") > 0, col("revenue")).otherwise(0))` |
| `AGGREGATE_COUNT` | COUNT aggregation | COUNT(*) or COUNT(DISTINCT id) | `count("*")` or `countDistinct("id")` |
| `AGGREGATE_AVG` | AVG aggregation | AVG(price) | `avg("price")` |
| `DERIVED_CALCULATION` | Calculated from other Gold columns | avg_value = total / count | Calculated within Gold MERGE |
| `DERIVED_CONDITIONAL` | Conditional logic (CASE/when) | CASE WHEN qty > 0 THEN 'Sale' ELSE 'Return' | `when(col("qty") > 0, "Sale").otherwise("Return")` |
| `HASH_MD5` | MD5 hash for surrogate keys | MD5(store_id \|\| timestamp) | `md5(concat_ws("\|\|", col("store_id"), col("timestamp")))` |
| `HASH_SHA256` | SHA256 hash for business keys | SHA256(keys) | `sha2(concat_ws("\|\|", col("key1"), col("key2")), 256)` |
| `COALESCE` | Null handling with default | COALESCE(discount, 0) | `coalesce(col("discount"), lit(0))` |
| `DATE_TRUNC` | Date truncation | DATE_TRUNC('day', timestamp) | `date_trunc("day", col("timestamp")).cast("date")` |
| `GENERATED` | Not from source, generated in Gold | CURRENT_TIMESTAMP() | `current_timestamp()` |
| `LOOKUP` | Value from dimension join | Get city from dim_store | Join in MERGE script |

### 4.4 Complete Column Lineage Examples

**Example 1: Direct Copy (FK)**
```yaml
- name: store_number
  type: STRING
  nullable: false
  description: >
    Store identifier.
    Business: Links to store dimension for location-based analysis.
    Technical: FK to dim_store.store_number (business key).
  lineage:
    bronze_table: bronze_transactions
    bronze_column: store_number
    silver_table: silver_transactions
    silver_column: store_number
    transformation: "DIRECT_COPY"
    transformation_logic: "col('store_number')"
```

**Example 2: Renamed Column**
```yaml
- name: company_retail_control_number
  type: STRING
  nullable: true
  description: >
    Company retail control number for corporate hierarchy.
    Business: Links store to corporate entity for multi-company rollups.
    Technical: Renamed from company_rcn for clarity.
  lineage:
    bronze_table: bronze_store_dim
    bronze_column: company_rcn
    silver_table: silver_store_dim
    silver_column: company_rcn
    transformation: "RENAME"
    transformation_logic: ".withColumn('company_retail_control_number', col('company_rcn'))"
    notes: "Column renamed in Gold for business clarity"
```

**Example 3: Conditional Aggregation**
```yaml
- name: gross_revenue
  type: DECIMAL(18,2)
  nullable: false
  description: >
    Total revenue before returns (positive sales only).
    Business: Gross sales amount before return adjustments.
    Technical: SUM of positive transaction amounts only.
  lineage:
    bronze_table: bronze_transactions
    bronze_column: final_sales_price
    silver_table: silver_transactions
    silver_column: final_sales_price
    transformation: "AGGREGATE_SUM_CONDITIONAL"
    transformation_logic: "spark_sum(when(col('quantity_sold') > 0, col('final_sales_price')).otherwise(0))"
    groupby_columns: ['store_number', 'upc_code', 'transaction_date']
    aggregation_level: "daily"
```

**Example 4: Derived Calculation**
```yaml
- name: avg_transaction_value
  type: DECIMAL(18,2)
  nullable: false
  description: >
    Average dollar value per transaction.
    Business: Basket size metric for pricing strategies.
    Technical: net_revenue / transaction_count.
  lineage:
    bronze_table: N/A
    bronze_column: N/A
    silver_table: N/A
    silver_column: N/A
    transformation: "DERIVED_CALCULATION"
    transformation_logic: "col('net_revenue') / col('transaction_count')"
    depends_on: ['net_revenue', 'transaction_count']
    notes: "Calculated from other Gold columns"
```

**Example 5: Surrogate Key (SCD Type 2)**
```yaml
- name: store_key
  type: STRING
  nullable: false
  description: >
    Surrogate key for this store version.
    Business: Used for fact table joins to historical store states.
    Technical: MD5 hash of store_number + processed_timestamp.
  lineage:
    bronze_table: bronze_store_dim
    bronze_column: store_id, processed_timestamp
    silver_table: silver_store_dim
    silver_column: store_id, processed_timestamp
    transformation: "HASH_MD5"
    transformation_logic: "md5(concat_ws('||', col('store_id'), col('processed_timestamp')))"
    notes: "Ensures uniqueness across SCD Type 2 versions"
```

**Example 6: Generated Audit Column**
```yaml
- name: record_created_timestamp
  type: TIMESTAMP
  nullable: false
  description: >
    Timestamp when record was created in Gold layer.
    Business: Audit field for data lineage.
    Technical: Set once at INSERT time, never updated.
  lineage:
    bronze_table: N/A
    bronze_column: N/A
    silver_table: N/A
    silver_column: N/A
    transformation: "GENERATED"
    transformation_logic: "current_timestamp()"
    notes: "Generated during Gold MERGE INSERT"
```

### 4.5 Lineage Documentation Requirements

**Every column MUST have:**
- ✅ `bronze_table` - Source Bronze table (or N/A if generated)
- ✅ `bronze_column` - Source Bronze column(s)
- ✅ `silver_table` - Intermediate Silver table (or N/A)
- ✅ `silver_column` - Silver column(s)
- ✅ `transformation` - Type from standard list above
- ✅ `transformation_logic` - Explicit SQL/PySpark expression
- ✅ `notes` - Optional special considerations

**For aggregations, ALSO add:**
- ✅ `aggregation_logic` - Complete aggregation expression
- ✅ `groupby_columns` - Grouping columns (defines grain)
- ✅ `aggregation_level` - Level description (daily, monthly, etc.)

**For derived columns, ALSO add:**
- ✅ `depends_on` - List of Gold columns used in calculation

---

## Step 5: Generate Column-Level Lineage Document

### 5.1 Lineage Document Purpose

**Create a comprehensive lineage document showing Bronze → Silver → Gold mapping for EVERY column.**

**File:** `gold_layer_design/COLUMN_LINEAGE.md`

**Benefits:**
- ✅ **Prevents schema mismatches** - See exact source columns before coding
- ✅ **Documents transformations** - Clear logic for each column
- ✅ **Code review aid** - Verify merge scripts match lineage
- ✅ **Troubleshooting** - Trace data issues back to source
- ✅ **Impact analysis** - Understand downstream effects of schema changes

### 5.2 Lineage Document Template

```markdown
# Column-Level Lineage: Bronze → Silver → Gold

**Generated:** {date}
**Project:** {project_name}
**Version:** {version}

## Purpose
This document provides complete column-level data lineage from Bronze through Gold layer,
including transformation logic for every column. Use this as reference when implementing
Gold merge scripts to prevent schema mismatches.

---

## Table: dim_store

**Grain:** One row per store_number per version (SCD Type 2)
**Bronze Source:** bronze_store_dim
**Silver Source:** silver_store_dim
**Gold Target:** dim_store

### Column Lineage

| Gold Column | Type | Bronze Source | Silver Source | Transformation | Logic | Notes |
|---|---|---|---|---|---|---|
| store_key | STRING | store_id, processed_timestamp | store_id, processed_timestamp | HASH_MD5 | `md5(concat_ws('||', col('store_id'), col('processed_timestamp')))` | Surrogate key for SCD2 |
| store_number | STRING | store_number | store_number | DIRECT_COPY | `col('store_number')` | Business key |
| store_name | STRING | store_name | store_name | DIRECT_COPY | `col('store_name')` | - |
| city | STRING | city | city | DIRECT_COPY | `col('city')` | - |
| state | STRING | state | state | DIRECT_COPY | `col('state')` | - |
| company_retail_control_number | STRING | company_rcn | company_rcn | RENAME | `.withColumn('company_retail_control_number', col('company_rcn'))` | Renamed for clarity |
| effective_from | TIMESTAMP | processed_timestamp | processed_timestamp | DIRECT_COPY | `col('processed_timestamp')` | SCD2 start date |
| effective_to | TIMESTAMP | N/A | N/A | GENERATED | `lit(None).cast('timestamp')` | SCD2 end date (NULL for current) |
| is_current | BOOLEAN | N/A | N/A | GENERATED | `lit(True)` | SCD2 current flag |
| record_created_timestamp | TIMESTAMP | N/A | N/A | GENERATED | `current_timestamp()` | Audit field |
| record_updated_timestamp | TIMESTAMP | N/A | N/A | GENERATED | `current_timestamp()` | Audit field |

---

## Table: fact_sales_daily

**Grain:** One row per store_number-upc_code-transaction_date (daily aggregate)
**Bronze Source:** bronze_transactions
**Silver Source:** silver_transactions
**Gold Target:** fact_sales_daily

### Column Lineage

| Gold Column | Type | Bronze Source | Silver Source | Transformation | Logic | Grouping |
|---|---|---|---|---|---|---|
| store_number | STRING | store_number | store_number | DIRECT_COPY | `col('store_number')` | Part of grain |
| upc_code | STRING | upc_code | upc_code | DIRECT_COPY | `col('upc_code')` | Part of grain |
| transaction_date | DATE | transaction_date | transaction_date | DIRECT_COPY | `col('transaction_date')` | Part of grain |
| gross_revenue | DECIMAL(18,2) | final_sales_price | final_sales_price | AGGREGATE_SUM_CONDITIONAL | `spark_sum(when(col('quantity_sold') > 0, col('final_sales_price')).otherwise(0))` | GROUP BY store, product, date |
| net_revenue | DECIMAL(18,2) | final_sales_price | final_sales_price | AGGREGATE_SUM | `spark_sum('final_sales_price')` | GROUP BY store, product, date |
| net_units | BIGINT | quantity_sold | quantity_sold | AGGREGATE_SUM | `spark_sum('quantity_sold')` | GROUP BY store, product, date |
| transaction_count | BIGINT | transaction_id | transaction_id | AGGREGATE_COUNT | `count('*')` | GROUP BY store, product, date |
| avg_transaction_value | DECIMAL(18,2) | N/A | N/A | DERIVED_CALCULATION | `col('net_revenue') / col('transaction_count')` | Calculated from Gold columns |
| record_created_timestamp | TIMESTAMP | N/A | N/A | GENERATED | `current_timestamp()` | Generated at INSERT |
| record_updated_timestamp | TIMESTAMP | N/A | N/A | GENERATED | `current_timestamp()` | Generated at MERGE |

### Transformation Summary

**Aggregation Grain:** GROUP BY (store_number, upc_code, transaction_date)

**Silver Query Pattern:**
```python
daily_sales = (
    silver_transactions
    .groupBy("store_number", "upc_code", "transaction_date")
    .agg(
        spark_sum(when(col("quantity_sold") > 0, col("final_sales_price")).otherwise(0)).alias("gross_revenue"),
        spark_sum("final_sales_price").alias("net_revenue"),
        spark_sum("quantity_sold").alias("net_units"),
        count("*").alias("transaction_count")
    )
    .withColumn("avg_transaction_value", col("net_revenue") / col("transaction_count"))
    .withColumn("record_created_timestamp", current_timestamp())
    .withColumn("record_updated_timestamp", current_timestamp())
)
```

**Column Mapping for MERGE:**
```python
# All columns map directly from daily_sales DataFrame
# NO renaming needed - column names match between Silver aggregation and Gold table
```
```

### 5.3 How to Generate Lineage Document

**Step 1: Extract from all YAML files**
```python
import yaml
from pathlib import Path

def generate_lineage_doc(yaml_dir: str, output_file: str):
    """Generate complete lineage documentation from YAML files."""
    
    lineage_md = ["# Column-Level Lineage: Bronze → Silver → Gold\n"]
    lineage_md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lineage_md.append("---\n\n")
    
    # Find all YAML files
    yaml_files = Path(yaml_dir).rglob("*.yaml")
    
    for yaml_file in sorted(yaml_files):
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
        
        table_name = config['table_name']
        grain = config.get('grain', 'Not specified')
        
        lineage_md.append(f"## Table: {table_name}\n\n")
        lineage_md.append(f"**Grain:** {grain}\n")
        lineage_md.append(f"**Domain:** {config.get('domain', 'N/A')}\n\n")
        
        # Create lineage table
        lineage_md.append("| Gold Column | Type | Bronze Source | Silver Source | Transformation | Logic |\n")
        lineage_md.append("|---|---|---|---|---|---|\n")
        
        for col in config.get('columns', []):
            name = col['name']
            dtype = col['type']
            lineage = col.get('lineage', {})
            
            bronze_src = f"{lineage.get('bronze_table', 'N/A')}.{lineage.get('bronze_column', 'N/A')}"
            silver_src = f"{lineage.get('silver_table', 'N/A')}.{lineage.get('silver_column', 'N/A')}"
            trans_type = lineage.get('transformation', 'UNKNOWN')
            trans_logic = lineage.get('transformation_logic', 'Not documented')
            
            lineage_md.append(f"| {name} | {dtype} | {bronze_src} | {silver_src} | {trans_type} | `{trans_logic}` |\n")
        
        lineage_md.append("\n---\n\n")
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(''.join(lineage_md))
    
    print(f"✓ Generated lineage document: {output_file}")
```

**Step 2: Run generation script**
```bash
python scripts/generate_lineage_doc.py \
  --yaml-dir gold_layer_design/yaml \
  --output gold_layer_design/COLUMN_LINEAGE.md
```

**Step 3: Review before implementation**
Before writing any Gold merge script, review the lineage document to:
- ✅ Verify all Silver columns exist
- ✅ Understand transformation logic needed
- ✅ Identify renamed columns
- ✅ Plan aggregation queries
- ✅ Check for data type conversions

### 5.4 Using Lineage in Merge Scripts

**The lineage document prevents these common errors:**

❌ **ERROR 1: Column doesn't exist**
```python
# Merge script references non-existent column
.withColumn("company_retail_control_number", col("company_retail_control_number"))
# Error: Column 'company_retail_control_number' does not exist in Silver!
```

✅ **SOLUTION: Check lineage document**
```markdown
| company_retail_control_number | STRING | bronze_store_dim.company_rcn | silver_store_dim.company_rcn | RENAME | ...
```
```python
# Correct: Map from Silver name
.withColumn("company_retail_control_number", col("company_rcn"))
```

❌ **ERROR 2: Wrong transformation logic**
```python
# Missing conditional logic
.agg(spark_sum("final_sales_price").alias("gross_revenue"))
# Problem: Includes returns (negative values)!
```

✅ **SOLUTION: Check lineage document**
```markdown
| gross_revenue | DECIMAL(18,2) | ... | AGGREGATE_SUM_CONDITIONAL | spark_sum(when(col('quantity_sold') > 0, col('final_sales_price')).otherwise(0))
```
```python
# Correct: Use conditional SUM
.agg(spark_sum(when(col("quantity_sold") > 0, col("final_sales_price")).otherwise(0)).alias("gross_revenue"))
```

❌ **ERROR 3: Missing CAST**
```python
# DATE_TRUNC returns TIMESTAMP, but Gold expects DATE
.withColumn("check_in_date", date_trunc("day", col("check_in_timestamp")))
# Error: Schema mismatch (TIMESTAMP vs DATE)
```

✅ **SOLUTION: Check lineage document**
```markdown
| check_in_date | DATE | ... | DATE_TRUNC | date_trunc('day', col('check_in_timestamp')).cast('date')
```
```python
# Correct: Add CAST
.withColumn("check_in_date", date_trunc("day", col("check_in_timestamp")).cast("date"))
```

---

## Step 6: Documentation Standards

### 6.1 Dual-Purpose Column Descriptions

**Every column description must serve both business and technical audiences:**

**Pattern:**
```
[Natural description]. Business: [business context and use cases]. Technical: [implementation details].
```

**Examples:**

```yaml
# Surrogate Key
store_key STRING NOT NULL
  description: >
    Surrogate key uniquely identifying each version of a store record.
    Business: Used for joining fact tables to dimension.
    Technical: MD5 hash generated from store_id and processed_timestamp 
    to ensure uniqueness across SCD Type 2 versions.

# Measure
net_revenue DECIMAL(18,2)
  description: >
    Net revenue after subtracting returns from gross revenue.
    Business: The actual revenue realized from sales, primary KPI for financial reporting.
    Technical: gross_revenue - return_amount, represents true daily sales value.

# Boolean Flag
is_current BOOLEAN
  description: >
    Flag indicating if this is the current active version.
    Business: TRUE for current store attributes, FALSE for historical records. 
    Use with WHERE is_current = true to get latest state.
    Technical: SCD Type 2 flag, updated to FALSE when new version created.
```

**Documentation Requirements:**
- ✅ Opening sentence: Clear, natural language definition
- ✅ Business section: Purpose, use cases, business rules
- ✅ Technical section: Data type, calculation, source, constraints
- ❌ No "LLM:" prefix (use natural dual-purpose format)

**See [12-gold-layer-documentation.mdc](mdc:.cursor/rules/gold/12-gold-layer-documentation.mdc) for complete documentation standards.**

### 6.2 Table Description Standards

**Table descriptions must include:**
1. Layer and purpose
2. Grain (what one row represents)
3. Business use cases
4. Technical implementation

**Example:**
```yaml
description: >
  Gold layer daily sales fact table with pre-aggregated metrics at store-product-day grain.
  Business: Primary source for sales performance reporting including revenue, units, 
  discounts, returns, and customer loyalty metrics. Aggregated from transaction-level 
  Silver data for fast query performance. Used for dashboards, executive reporting, 
  and sales analysis.
  Technical: Grain is one row per store-product-date combination. Pre-aggregated measures 
  eliminate need for transaction-level scans, surrogate keys enable fast dimension joins.
```

---

## Step 7: Business Onboarding Guide (MANDATORY)

### 7.1 Why This Document is Required

**⚠️ CRITICAL: This document is MANDATORY for all Gold layer designs.**

The Business Onboarding Guide ensures new team members can:
- Understand the business domain and processes
- Trace data flow from source systems to Gold tables
- Connect business concepts to specific tables and columns
- Leverage analytics capabilities (Genie, AI/BI, ML)

**Without this guide:**
- ❌ New analysts struggle to understand the data model
- ❌ Business context is lost in technical documentation
- ❌ Self-service analytics adoption is slow
- ❌ Incorrect queries due to misunderstanding business processes

### 7.2 Required Sections

**File: `gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md`**

The guide MUST include these sections:

```markdown
# {Project Name} Analytics Platform
## Business Onboarding Guide

**Audience:** Data Engineers, Analysts, Data Scientists, Business Users
**Purpose:** Understand {domain} operations and how to leverage the Gold layer for analytics

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
10. Getting Started (For each role: Engineers, Analysts, Scientists, Business Users)
```

### 7.3 Business Processes Section Requirements

**Section 5 (Business Processes & Tracking) MUST include:**

For EACH major business process:

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

{ASCII FLOW DIAGRAM}
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        {PROCESS NAME} FLOW                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  STAGE 1               STAGE 2              STAGE 3              STAGE 4           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   {Name}     │───▶│   {Name}     │───▶│   {Name}     │───▶│   {Name}     │     │
│  │              │    │              │    │              │    │              │     │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘     │
│        │                    │                   │                   │              │
│  Source Tables:       Source Tables:      Source Tables:      Source Tables:       │
│  • {SOURCE_TBL1}      • {SOURCE_TBL2}     • {SOURCE_TBL3}     • {SOURCE_TBL4}      │
│        │                    │                   │                   │              │
│        ▼                    ▼                   ▼                   ▼              │
│  Gold Tables:         Gold Tables:        Gold Tables:        Gold Tables:         │
│  • {gold_table1}      • {gold_table2}     • {gold_table3}     • {gold_table4}     │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

**Stage-by-Stage Detail:**

| Stage | What Happens | Source Table | Gold Table | Key Fields |
|-------|--------------|--------------|------------|------------|
| **1. {Stage Name}** | {Description} | `{SOURCE_TBL}` | `{gold_table}` | `{key_field1}`, `{key_field2}` |
| **2. {Stage Name}** | {Description} | `{SOURCE_TBL}` | `{gold_table}` | `{key_field1}`, `{key_field2}` |

**Business Questions Answered:**
- "{Example business question 1}" → {Which tables/columns answer it}
- "{Example business question 2}" → {Which tables/columns answer it}
```

### 7.4 Real-World Stories Section (MANDATORY)

**Section 5B MUST include 3-4 detailed stories** showing data flow through the system.

**Story Requirements:**

Each story must include:
1. **Business Context** - The scenario being described
2. **Chapters** (4-6) - Each stage of the process
3. **Source System Data** - What gets written to source tables (with example values)
4. **Gold Layer Updates** - Which Gold tables are created/updated
5. **Analytics Impact** - How metrics/dashboards change
6. **Timeline Visualization** - Summary of data trail

**Story Template:**

```markdown
### 📖 Story N: "{Title}" — {Subtitle}

**The Business Context:**
{2-3 sentences describing the real-world scenario}

---

#### Chapter 1: {Stage Name} ({Time})

**What Happens:**  
{Narrative description of what's happening in the business}

**In {Source System} (Source System):**
```
{SOURCE_TABLE}:
  field1: value1
  field2: value2
  field3: value3
```

**In Gold Layer:**

| Table | Record Created/Updated | Key Values |
|-------|------------------------|------------|
| `{gold_table1}` | ✅ New row | `{field}` = '{value}', `{field2}` = '{value2}' |
| `{gold_table2}` | 🔄 Updated | `{field}` changed from '{old}' to '{new}' |

**Analytics Impact:**
- {Metric 1} increases/decreases by {amount}
- {Dashboard widget} now shows {value}
- {Alert triggered if applicable}

---

#### Chapter 2: {Next Stage} ({Time})
{Continue pattern...}

---

#### Story Summary: Data Journey Visualization

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    {SCENARIO}: DATA TRAIL THROUGH GOLD LAYER                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  TIME        EVENT              TABLES UPDATED                                      │
│  ─────────────────────────────────────────────────────────────────────────────     │
│  {time1}     {event1}           {table1}, {table2}, {table3}                        │
│  {time2}     {event2}           {table4}, {table5}                                  │
│  {time3}     {event3}           {table6}                                            │
│                                                                                     │
│  TOTAL: {N} tables touched                                                          │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```
```

### 7.5 Recommended Story Types

Include stories that demonstrate:

| Story Type | Purpose | Example |
|------------|---------|---------|
| **Happy Path** | Normal successful flow | "A salmon shipment from Seattle to Anchorage" |
| **Exception Handling** | How problems are resolved | "The overbooked flight - capacity decisions" |
| **Error Correction** | Post-facto adjustments | "The billing dispute - CCA process" |
| **Compliance/Safety** | Regulatory requirements | "The dangerous goods incident" |

---

## Step 8: Source Table Mapping (MANDATORY)

### 8.1 Why Source Table Mapping is Required

**⚠️ CRITICAL: This CSV file is MANDATORY for all Gold layer designs.**

Every Gold layer design starts with source tables. You MUST document:
- Which source tables are included and why
- Which source tables are excluded and why
- The mapping from source to Gold
- Phase/priority for implementation

**Benefits:**
- ✅ Complete audit trail of design decisions
- ✅ Clear scope definition for stakeholders
- ✅ Gap analysis for future phases
- ✅ Documentation prevents scope creep

### 8.2 CSV Format

**File: `gold_layer_design/SOURCE_TABLE_MAPPING.csv`**

**Required Columns:**

```csv
source_table,source_description,status,gold_table,domain,entity_type,rationale,phase,priority
```

**Column Definitions:**

| Column | Type | Description |
|--------|------|-------------|
| `source_table` | STRING | Source system table name (e.g., `CAPBKGMST`) |
| `source_description` | STRING | Brief description of what the table contains |
| `status` | ENUM | `INCLUDED`, `EXCLUDED`, `PLANNED` |
| `gold_table` | STRING | Target Gold table name (or `N/A` if excluded) |
| `domain` | STRING | Business domain (e.g., `booking`, `revenue`, `operations`) |
| `entity_type` | ENUM | `dimension`, `fact`, `lookup`, `staging`, `archive` |
| `rationale` | STRING | **REQUIRED** - Why included or excluded |
| `phase` | INT | Implementation phase (1, 2, 3, etc.) |
| `priority` | ENUM | `HIGH`, `MEDIUM`, `LOW` |

### 8.3 Status Values and Rationale Requirements

**Status = INCLUDED:**
- `gold_table` MUST have a value
- `rationale` explains why this table is needed

**Status = EXCLUDED:**
- `gold_table` = `N/A`
- `rationale` MUST explain exclusion reason

**Status = PLANNED:**
- `gold_table` can have planned name or `TBD`
- `rationale` explains what's needed before inclusion

### 8.4 Standard Exclusion Rationales

Use these standard rationale phrases for excluded tables:

| Rationale | When to Use |
|-----------|-------------|
| `System/audit table - no business value` | Internal system tables, audit logs |
| `Historical archive - superseded by {table}` | Old tables replaced by newer versions |
| `Duplicate data available in {table}` | Data exists in another included table |
| `Configuration/setup table - static reference only` | System configuration tables |
| `Out of scope for {project} phase {N}` | Valid tables deferred to future phases |
| `Legacy table - no longer populated` | Deprecated tables |
| `Temporary/staging table` | ETL intermediate tables |
| `Low business value - insufficient usage` | Tables rarely queried |

### 8.5 Example SOURCE_TABLE_MAPPING.csv

```csv
source_table,source_description,status,gold_table,domain,entity_type,rationale,phase,priority
CAPBKGMST,Booking master table,INCLUDED,dim_booking,booking,dimension,Core booking information needed for all cargo analytics,1,HIGH
CAPBKGDTL,Booking line item details,INCLUDED,fact_booking_detail,booking,fact,Shipment-level detail for volume and weight tracking,1,HIGH
OPRSHPMSTDTL,Shipment master details,INCLUDED,fact_shipment,operations,fact,Primary operational fact table for all shipment tracking,1,HIGH
CRAAWBCHGDTL,AWB charge details,INCLUDED,fact_awb_revenue,revenue,fact,Revenue recognition and charge breakdown,1,HIGH
AUDITLOG,System audit log,EXCLUDED,N/A,system,audit,System/audit table - no business value,N/A,LOW
OPRSHPHISTARC,Shipment history archive,EXCLUDED,N/A,operations,archive,Historical archive - data available in OPRSHPHIS,N/A,LOW
MALPOAMST,Postal administration master,PLANNED,dim_postal_admin,mail,dimension,Out of scope for phase 1 - planned for mail domain expansion,2,MEDIUM
```

### 8.6 Maintaining the Mapping

**Update the mapping when:**
- ✅ New source tables are discovered
- ✅ Design decisions change inclusion/exclusion
- ✅ Gold table names change
- ✅ Phases are reprioritized

**Review the mapping during:**
- ✅ Design reviews
- ✅ Phase completion
- ✅ Gap analysis sessions

---

## Step 9: Column Lineage CSV (MANDATORY)

### 9.1 Why Column Lineage CSV is Required

**⚠️ CRITICAL: This CSV file is MANDATORY for all Gold layer designs.**

The COLUMN_LINEAGE.csv provides machine-readable lineage that:
- Enables automated validation
- Supports impact analysis
- Documents every column's source
- Prevents schema mismatches during implementation

**The markdown version (COLUMN_LINEAGE.md) is for human readability. The CSV is for validation.**

### 9.2 CSV Format

**File: `gold_layer_design/COLUMN_LINEAGE.csv`**

**Required Columns:**

```csv
domain,gold_table,gold_column,data_type,nullable,bronze_table,bronze_column,silver_table,silver_column,transformation_type,transformation_logic
```

**Column Definitions:**

| Column | Type | Description |
|--------|------|-------------|
| `domain` | STRING | Business domain (e.g., `booking`, `revenue`) |
| `gold_table` | STRING | Gold layer table name |
| `gold_column` | STRING | Gold layer column name |
| `data_type` | STRING | Data type (e.g., `STRING`, `DECIMAL(18,2)`, `TIMESTAMP`) |
| `nullable` | BOOLEAN | `true` or `false` |
| `bronze_table` | STRING | Source Bronze table (or `N/A` for generated columns) |
| `bronze_column` | STRING | Source Bronze column(s) |
| `silver_table` | STRING | Source Silver table (or `N/A`) |
| `silver_column` | STRING | Source Silver column(s) |
| `transformation_type` | STRING | Standard transformation type (see Step 4.3) |
| `transformation_logic` | STRING | PySpark/SQL transformation expression |

### 9.3 Example COLUMN_LINEAGE.csv

```csv
domain,gold_table,gold_column,data_type,nullable,bronze_table,bronze_column,silver_table,silver_column,transformation_type,transformation_logic
booking,dim_booking,booking_key,STRING,false,CAPBKGMST,"ubr_number,processed_timestamp",silver_booking,"ubr_number,processed_timestamp",HASH_MD5,"md5(concat_ws('||',col('ubr_number'),col('processed_timestamp')))"
booking,dim_booking,ubr_number,STRING,false,CAPBKGMST,ubr_number,silver_booking,ubr_number,DIRECT_COPY,"col('ubr_number')"
booking,dim_booking,booking_date,DATE,false,CAPBKGMST,booking_date,silver_booking,booking_date,CAST,"col('booking_date').cast('date')"
booking,dim_booking,effective_from,TIMESTAMP,false,N/A,N/A,N/A,N/A,GENERATED,"current_timestamp()"
booking,dim_booking,effective_to,TIMESTAMP,true,N/A,N/A,N/A,N/A,GENERATED,"lit(None).cast('timestamp')"
booking,dim_booking,is_current,BOOLEAN,false,N/A,N/A,N/A,N/A,GENERATED,"lit(True)"
booking,fact_booking_detail,gross_weight_kg,DECIMAL(18,3),true,CAPBKGDTL,stated_weight,silver_booking_detail,stated_weight,AGGREGATE_SUM,"spark_sum('stated_weight')"
```

### 9.4 Consistency Requirements

**The COLUMN_LINEAGE.csv MUST be consistent with:**

1. **YAML Schema Files** - Every column in YAML must appear in CSV
2. **ERD Diagrams** - Every column in ERD must appear in CSV
3. **COLUMN_LINEAGE.md** - CSV and MD versions must match

### 9.5 Validation Script

**Use this script to validate consistency:**

```python
import pandas as pd
import yaml
from pathlib import Path

def validate_lineage_consistency(yaml_dir: str, lineage_csv: str) -> list:
    """Validate COLUMN_LINEAGE.csv against YAML files."""
    
    errors = []
    lineage_df = pd.read_csv(lineage_csv)
    
    # Get all columns from YAML files
    yaml_columns = set()
    for yaml_file in Path(yaml_dir).rglob("*.yaml"):
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
        table_name = config['table_name']
        for col in config.get('columns', []):
            yaml_columns.add((table_name, col['name']))
    
    # Get all columns from CSV
    csv_columns = set()
    for _, row in lineage_df.iterrows():
        csv_columns.add((row['gold_table'], row['gold_column']))
    
    # Find mismatches
    in_yaml_not_csv = yaml_columns - csv_columns
    in_csv_not_yaml = csv_columns - yaml_columns
    
    if in_yaml_not_csv:
        errors.append(f"Columns in YAML but not in CSV: {in_yaml_not_csv}")
    if in_csv_not_yaml:
        errors.append(f"Columns in CSV but not in YAML: {in_csv_not_yaml}")
    
    return errors

# Usage
errors = validate_lineage_consistency(
    yaml_dir="gold_layer_design/yaml",
    lineage_csv="gold_layer_design/COLUMN_LINEAGE.csv"
)

if errors:
    print("❌ Validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ All columns consistent between YAML and CSV")
```

---

## Design Validation Checklist

### Dimensional Model
- [ ] 2-5 dimensions identified
- [ ] 1-3 facts identified
- [ ] SCD type decided for each dimension
- [ ] Grain defined for each fact table
- [ ] All measures documented with calculation logic
- [ ] All relationships documented
- [ ] **Tables assigned to domains** (Location, Product, Time, Sales, etc.)

### ERD Organization (Based on Table Count)
- [ ] **Table count assessed** (1-8: Master only, 9-20: +Domain, 20+: +Summary)
- [ ] **Master ERD created** (`erd_master.md`) - ALWAYS required
- [ ] Master ERD shows ALL tables grouped by domain
- [ ] Master ERD includes Domain Index table with links
- [ ] Domain emoji markers used in section headers

### Domain ERDs (If 9+ Tables)
- [ ] Domain ERDs created for each logical domain (`erd/erd_{domain}.md`)
- [ ] Each domain ERD shows focused view of domain tables
- [ ] External tables shown with domain labels (e.g., `["🏪 dim_store (Location)"]`)
- [ ] Cross-Domain Dependencies table included
- [ ] Links to Master ERD and related Domain ERDs

### Summary ERD (If 20+ Tables)
- [ ] Summary ERD created (`erd_summary.md`)
- [ ] Shows domains as entities with table lists
- [ ] Domain relationships documented

### All ERDs
- [ ] All dimensions shown
- [ ] All facts shown
- [ ] All relationships shown with cardinality
- [ ] Primary keys marked (PK only, no inline descriptions)
- [ ] `by_{column}` pattern used for relationship labels
- [ ] Relationships grouped at end of diagram

### YAML Schemas (Domain-Organized)
- [ ] One YAML file per table
- [ ] **Organized by domain folders** (`yaml/{domain}/`)
- [ ] **Domain folders match ERD domain organization**
- [ ] Complete column definitions
- [ ] Primary key defined
- [ ] Foreign keys defined
- [ ] Dual-purpose descriptions (business + technical)
- [ ] Table properties documented
- [ ] Grain explicitly stated
- [ ] `domain` field in each YAML matches folder name
- [ ] **Lineage documentation for EVERY column**
- [ ] **Transformation type specified** (from standard list)
- [ ] **Transformation logic documented** (explicit SQL/PySpark)

### Column-Level Lineage
- [ ] Bronze source table/column documented for every column
- [ ] Silver source table/column documented for every column
- [ ] Transformation type from standard list
- [ ] Transformation logic explicit and executable
- [ ] Aggregation columns specify groupby_columns
- [ ] Derived columns specify depends_on
- [ ] Generated columns marked as such

### Lineage Document (COLUMN_LINEAGE.md)
- [ ] COLUMN_LINEAGE.md generated from YAML files
- [ ] All tables included
- [ ] Complete Bronze → Silver → Gold mapping
- [ ] Transformation summary per table
- [ ] Sample query patterns provided
- [ ] Column mapping guidance included

### Column Lineage CSV (MANDATORY)
- [ ] `COLUMN_LINEAGE.csv` created with all required columns
- [ ] Every column from every YAML file is represented
- [ ] Transformation types use standard codes
- [ ] Transformation logic is executable PySpark/SQL
- [ ] CSV validated against YAML for consistency
- [ ] No missing Bronze/Silver source mappings (except for generated columns)

### Source Table Mapping (MANDATORY)
- [ ] `SOURCE_TABLE_MAPPING.csv` created with all source tables
- [ ] Every source table has a status (INCLUDED, EXCLUDED, PLANNED)
- [ ] Every row has a rationale explaining the decision
- [ ] INCLUDED tables map to specific Gold tables
- [ ] EXCLUDED tables have standard exclusion rationale
- [ ] PLANNED tables have phase assignments
- [ ] Coverage percentage calculated and documented

### Business Onboarding Guide (MANDATORY)
- [ ] `docs/BUSINESS_ONBOARDING_GUIDE.md` created
- [ ] Introduction to Business Domain section complete
- [ ] Business Lifecycle diagram included
- [ ] Key Business Entities explained
- [ ] Gold Layer Data Model overview provided
- [ ] **Business Processes section includes ALL major processes**
- [ ] **Each process has Source → Gold table mapping**
- [ ] **Each process has ASCII flow diagram**
- [ ] **Section 5B: Real-World Stories included (minimum 3 stories)**
- [ ] **Each story shows exact table updates at each stage**
- [ ] Analytics Use Cases documented
- [ ] AI & ML Opportunities section included
- [ ] Genie/Self-Service section included
- [ ] Data Quality & Monitoring section included
- [ ] Getting Started section for each persona (Engineer, Analyst, Scientist, Business User)

### Documentation
- [ ] Every column has dual-purpose description
- [ ] No "LLM:" prefix used
- [ ] Business section explains purpose and use cases
- [ ] Technical section explains implementation
- [ ] SCD strategy documented
- [ ] Update frequency documented

### Stakeholder Review
- [ ] ERD reviewed with business stakeholders
- [ ] Grain validated for each fact
- [ ] Measures confirmed complete
- [ ] Naming conventions approved
- [ ] Data classification verified
- [ ] Design sign-off obtained

---

## Output Deliverables

After completing this design phase, you should have:

### ERD Deliverables (Based on Table Count)

| Tables | Required Deliverables |
|--------|----------------------|
| **1-8** | `erd_master.md` only |
| **9-20** | `erd_master.md` + `erd/erd_{domain}.md` for each domain |
| **20+** | `erd_master.md` + `erd_summary.md` + `erd/erd_{domain}.md` for each domain |

### Complete Deliverables List

**ERD Deliverables:**
1. **Master ERD** (`erd_master.md`) - Complete model with all tables (ALWAYS required)
2. **Summary ERD** (`erd_summary.md`) - Domain-level overview (if 20+ tables)
3. **Domain ERDs** (`erd/erd_{domain}.md`) - Focused domain views (if 9+ tables)

**Schema Deliverables:**
4. **YAML Schema Files** - Complete schema definitions with lineage (organized by domain)

**Lineage & Mapping Deliverables (MANDATORY):**
5. **Column Lineage CSV** (`COLUMN_LINEAGE.csv`) - ⭐ Machine-readable Bronze → Silver → Gold mapping
6. **Column Lineage Doc** (`COLUMN_LINEAGE.md`) - Human-readable lineage documentation
7. **Source Table Mapping** (`SOURCE_TABLE_MAPPING.csv`) - ⭐ All source tables with inclusion/exclusion rationale

**Business Documentation (MANDATORY):**
8. **Business Onboarding Guide** (`docs/BUSINESS_ONBOARDING_GUIDE.md`) - ⭐ Business processes, stories, table mapping
9. **Design Summary** (`DESIGN_SUMMARY.md`) - Grain, SCD, transformation decisions
10. **Design Gap Analysis** (`DESIGN_GAP_ANALYSIS.md`) - Coverage analysis and remaining gaps
11. **README** (`README.md`) - Quick navigation to all documentation

**Approval:**
12. **Stakeholder Sign-off** - Approval from business owners

### File Organization

```
gold_layer_design/
├── README.md                     # ⭐ Quick navigation hub (ALWAYS)
├── erd_master.md                 # Complete ERD (ALWAYS)
├── erd_summary.md                # Domain summary (20+ tables)
├── erd/                          # Domain ERDs (9+ tables)
│   └── erd_{domain}.md
├── yaml/                         # YAML schemas by domain
│   └── {domain}/
│       └── {table}.yaml
├── docs/                         # ⭐ Business documentation
│   └── BUSINESS_ONBOARDING_GUIDE.md  # ⭐ MANDATORY - Stories + processes
├── COLUMN_LINEAGE.csv            # ⭐ MANDATORY - Machine-readable lineage
├── COLUMN_LINEAGE.md             # Human-readable lineage
├── SOURCE_TABLE_MAPPING.csv      # ⭐ MANDATORY - Source table rationale
├── DESIGN_SUMMARY.md             # Design decisions
└── DESIGN_GAP_ANALYSIS.md        # Coverage analysis
```

**Critical:** The COLUMN_LINEAGE.md document prevents 33% of schema mismatch bugs during implementation!

**Next Step:** Use [03b-gold-layer-implementation-prompt.md](./03b-gold-layer-implementation-prompt.md) to implement the design.

---

## References

### Official Documentation
- [Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Unity Catalog Constraints](https://docs.databricks.com/data-governance/unity-catalog/constraints.html)
- [Mermaid ERD Syntax](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)

### Framework Rules
- [12-gold-layer-documentation.mdc](mdc:.cursor/rules/gold/12-gold-layer-documentation.mdc) - Documentation standards
- [13-mermaid-erd-patterns.mdc](mdc:.cursor/rules/gold/13-mermaid-erd-patterns.mdc) - **Master vs Domain ERD patterns**
- [24-fact-table-grain-validation.mdc](mdc:.cursor/rules/gold/24-fact-table-grain-validation.mdc) - Grain validation
- [25-yaml-driven-gold-setup.mdc](mdc:.cursor/rules/gold/25-yaml-driven-gold-setup.mdc) - YAML patterns

---

## Summary

**What to Create:**

**ERD Artifacts:**
1. **Master ERD** (always) - Complete model with all tables
2. **Domain ERDs** (if 9+ tables) - Focused domain-specific views
3. **Summary ERD** (if 20+ tables) - High-level domain overview

**Schema Artifacts:**
4. **YAML schema files** with lineage (organized by domain)

**Lineage & Mapping (MANDATORY):**
5. **COLUMN_LINEAGE.csv** - ⭐ Machine-readable column lineage
6. **COLUMN_LINEAGE.md** - Human-readable lineage documentation
7. **SOURCE_TABLE_MAPPING.csv** - ⭐ All source tables with inclusion/exclusion rationale

**Business Documentation (MANDATORY):**
8. **BUSINESS_ONBOARDING_GUIDE.md** - ⭐ Business processes, real-world stories, table mapping
9. **DESIGN_SUMMARY.md** - Design decisions and rationale
10. **DESIGN_GAP_ANALYSIS.md** - Coverage analysis

**Approval:**
11. **Stakeholder sign-off**

**ERD Organization Decision:**
| Tables | ERD Strategy |
|--------|--------------|
| 1-8 | Master only |
| 9-20 | Master + Domain ERDs |
| 20+ | Master + Domain + Summary |

**Core Philosophy:** Design = Business contract for analytics (document before implementing)

**Key Requirements:**
- ✅ Domain-based organization (ERDs + YAML folders)
- ✅ Column-level lineage prevents 33% of Gold merge bugs
- ✅ Cross-domain relationships documented
- ✅ **Business Onboarding Guide with stories showing data flow**
- ✅ **Source Table Mapping with clear inclusion/exclusion rationale**
- ✅ **Column Lineage CSV for automated validation**

**Mandatory Documentation Rationale:**

| Document | Why Mandatory | Impact if Missing |
|----------|---------------|-------------------|
| **BUSINESS_ONBOARDING_GUIDE.md** | New team members need context | 2-3 weeks ramp-up time wasted |
| **SOURCE_TABLE_MAPPING.csv** | Design decisions must be auditable | Scope creep, unclear requirements |
| **COLUMN_LINEAGE.csv** | Validation requires machine-readable format | 33% of implementation bugs undetected |

**Time Estimate:**
- 3-4 hours for 1-8 tables (Master ERD only)
- 5-6 hours for 9-20 tables (Master + Domain ERDs)
- 6-10 hours for 20+ tables (Full ERD hierarchy + comprehensive documentation)

**Documentation Effort Breakdown (20+ tables):**
- ERDs + YAML schemas: 3-4 hours
- Business Onboarding Guide: 2-3 hours
- Source Table Mapping: 1-2 hours
- Column Lineage CSV: 1-2 hours
- Review & validation: 1 hour

**Next Action:** Complete design with ERD hierarchy, mandatory documentation, get stakeholder sign-off, then proceed to implementation


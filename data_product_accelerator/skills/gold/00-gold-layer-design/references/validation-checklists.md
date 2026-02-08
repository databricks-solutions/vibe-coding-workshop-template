# Validation Checklists

All design validation checklists extracted from `context/prompts/03a-gold-layer-design-prompt.md`.

---

## Dimensional Model

- [ ] 2-5 dimensions identified
- [ ] 1-3 facts identified
- [ ] SCD type decided for each dimension (Type 1 or Type 2)
- [ ] Grain defined explicitly for each fact table
- [ ] All measures documented with calculation logic
- [ ] All relationships documented (FK → PK)
- [ ] Tables assigned to domains (Location, Product, Time, Sales, etc.)

---

## ERD Organization (Based on Table Count)

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
- [ ] Correct Databricks SQL type names used

---

## YAML Schemas (Domain-Organized)

- [ ] One YAML file per table
- [ ] **Organized by domain folders** (`yaml/{domain}/`)
- [ ] **Domain folders match ERD domain organization**
- [ ] Complete column definitions for every column
- [ ] Primary key defined with `composite: true/false`
- [ ] Foreign keys defined with `references:` field
- [ ] Dual-purpose descriptions (business + technical)
- [ ] Table properties documented (PII, classification, owners)
- [ ] Grain explicitly stated in YAML
- [ ] `domain` field in each YAML matches folder name
- [ ] **Lineage documentation for EVERY column**
- [ ] **Transformation type specified** (from standard list)
- [ ] **Transformation logic documented** (explicit SQL/PySpark)

---

## Column-Level Lineage

- [ ] Bronze source table/column documented for every column
- [ ] Silver source table/column documented for every column
- [ ] Transformation type from standard list
- [ ] Transformation logic explicit and executable
- [ ] Aggregation columns specify `groupby_columns`
- [ ] Derived columns specify `depends_on`
- [ ] Generated columns marked as such (bronze/silver = N/A)

---

## Lineage Document (COLUMN_LINEAGE.md)

- [ ] COLUMN_LINEAGE.md generated from YAML files
- [ ] All tables included
- [ ] Complete Bronze → Silver → Gold mapping
- [ ] Transformation summary per table
- [ ] Sample query patterns provided
- [ ] Column mapping guidance for merge scripts

---

## Column Lineage CSV (MANDATORY)

- [ ] `COLUMN_LINEAGE.csv` created with all required columns
- [ ] Every column from every YAML file is represented
- [ ] Transformation types use standard codes
- [ ] Transformation logic is executable PySpark/SQL
- [ ] CSV validated against YAML for consistency
- [ ] No missing Bronze/Silver source mappings (except generated columns)

---

## Source Table Mapping (MANDATORY)

- [ ] `SOURCE_TABLE_MAPPING.csv` created with all source tables
- [ ] Every source table has a status (INCLUDED, EXCLUDED, PLANNED)
- [ ] Every row has a rationale explaining the decision
- [ ] INCLUDED tables map to specific Gold tables
- [ ] EXCLUDED tables have standard exclusion rationale
- [ ] PLANNED tables have phase assignments
- [ ] Coverage percentage calculated and documented

---

## Business Onboarding Guide (MANDATORY)

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
- [ ] Getting Started section for each persona

---

## Documentation Standards

- [ ] Every column has dual-purpose description
- [ ] No "LLM:" prefix used (natural dual-purpose format)
- [ ] Business section explains purpose and use cases
- [ ] Technical section explains implementation details
- [ ] SCD strategy documented for each dimension
- [ ] Update frequency documented for each table

---

## Stakeholder Review

- [ ] ERD reviewed with business stakeholders
- [ ] Grain validated for each fact table
- [ ] Measures confirmed complete for reporting needs
- [ ] Naming conventions approved by data governance
- [ ] Data classification verified for each table
- [ ] Design sign-off obtained from business owners

---

## Cross-Artifact Consistency

- [ ] All columns in ERD exist in YAML
- [ ] All YAML columns exist in COLUMN_LINEAGE.csv
- [ ] All YAML tables exist in SOURCE_TABLE_MAPPING.csv (as INCLUDED)
- [ ] Domain names consistent across ERD, YAML folders, and CSV files
- [ ] Primary key definitions consistent between ERD and YAML
- [ ] Foreign key references valid (target tables exist)
- [ ] Table descriptions in YAML match ERD table names exactly

# Industry Domain Patterns

## How to Define Agent Domains

**ALL artifacts across ALL phases MUST be organized by Agent Domain.** This ensures:
- Consistent categorization across 100+ artifacts
- Clear ownership by future AI agents
- Easy discoverability for users
- Aligned tooling for each domain

Define 4-6 business domains for your project. Each domain maps to:
- A set of Gold layer tables
- A dedicated Genie Space
- A specialized AI agent (Phase 2)
- A collection of TVFs, Metric Views, Dashboards, Alerts, ML Models, and Monitors

## Domain Definition Template

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| {Domain 1} | {emoji} | {focus} | {tables} |
| {Domain 2} | {emoji} | {focus} | {tables} |
| {Domain 3} | {emoji} | {focus} | {tables} |
| {Domain 4} | {emoji} | {focus} | {tables} |
| {Domain 5} | {emoji} | {focus} | {tables} |

## Industry-Specific Domain Patterns

| Industry | Domains |
|----------|---------|
| Hospitality | Revenue, Engagement, Property, Host, Customer |
| Retail | Sales, Inventory, Store, Customer, Marketing |
| Healthcare | Clinical, Financial, Operations, Facility, Patient |
| Finance | Revenue, Risk, Compliance, Customer, Operations |
| SaaS | Revenue, Product, Customer, Performance, Security |
| Databricks System Tables | Cost, Security, Performance, Reliability, Quality |

---

## Detailed Industry Patterns

### Hospitality

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| **Revenue** | 💰 | Booking revenue, payments, pricing optimization | `fact_booking_daily`, `fact_booking_detail` |
| **Engagement** | 📊 | Views, clicks, conversions, marketing effectiveness | `fact_property_engagement` |
| **Property** | 🏠 | Listings, availability, amenities, pricing | `dim_property` |
| **Host** | 👤 | Host performance, earnings, quality metrics | `dim_host` |
| **Customer** | 🎯 | User behavior, segmentation, lifetime value | `dim_user` |

### Retail

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| **Sales** | 💰 | Revenue, transactions, returns, promotions | `fact_sales`, `fact_returns` |
| **Inventory** | 📦 | Stock levels, replenishment, shrinkage | `fact_inventory`, `dim_product` |
| **Store** | 🏪 | Store performance, traffic, conversion | `dim_store`, `fact_store_traffic` |
| **Customer** | 👤 | Loyalty, segmentation, CLV | `dim_customer`, `fact_customer_activity` |
| **Marketing** | 📊 | Campaign performance, attribution, ROI | `fact_campaign`, `dim_channel` |

### Healthcare

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| **Clinical** | 👨‍⚕️ | Patient outcomes, treatment effectiveness | `fact_encounter`, `dim_diagnosis` |
| **Financial** | 💰 | Revenue cycle, claims, reimbursement | `fact_claim`, `dim_payer` |
| **Operations** | 📊 | Bed utilization, wait times, throughput | `fact_admission`, `dim_department` |
| **Facility** | 🏥 | Equipment, staffing, capacity planning | `dim_facility`, `fact_resource_usage` |
| **Patient** | 👤 | Demographics, satisfaction, engagement | `dim_patient`, `fact_survey` |

### Finance

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| **Revenue** | 💰 | Trading, interest, fee income | `fact_transaction`, `dim_product` |
| **Risk** | 🔒 | Credit risk, market risk, operational risk | `fact_risk_exposure`, `dim_portfolio` |
| **Compliance** | 📊 | Regulatory reporting, audit trails | `fact_compliance_event`, `dim_regulation` |
| **Customer** | 👤 | Account activity, satisfaction, churn | `dim_customer`, `fact_account_activity` |
| **Operations** | ⚡ | Process efficiency, SLAs, costs | `fact_operation`, `dim_process` |

### SaaS

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| **Revenue** | 💰 | MRR, ARR, churn, expansion | `fact_subscription`, `dim_plan` |
| **Product** | 📊 | Feature usage, adoption, engagement | `fact_event`, `dim_feature` |
| **Customer** | 👤 | Health score, NPS, lifecycle | `dim_account`, `fact_customer_health` |
| **Performance** | ⚡ | API latency, uptime, errors | `fact_request`, `dim_service` |
| **Security** | 🔒 | Auth events, threats, compliance | `fact_auth_event`, `dim_user` |

---

## Databricks System Tables Pattern

This pattern is used when building observability/monitoring solutions using Databricks system tables.

### Domains

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| **Cost** | 💰 | FinOps, budgets, chargeback | `fact_usage`, `dim_sku`, `commit_configurations` |
| **Security** | 🔒 | Access audit, compliance | `fact_audit_events`, `fact_table_lineage` |
| **Performance** | ⚡ | Query optimization, capacity | `fact_query_history`, `fact_node_timeline` |
| **Reliability** | 🔄 | Job health, SLAs | `fact_job_run_timeline`, `dim_job` |
| **Quality** | ✅ | Data quality, governance | `fact_data_quality_monitoring_table_results` |

### Agent-to-Genie Space Mapping (System Tables Example)

| Agent | Genie Space | Tools (via Genie) |
|-------|-------------|-------------------|
| 💰 **Cost Agent** | Cost Intelligence | 15 TVFs, 2 MVs, 6 ML |
| 🔒 **Security Agent** | Security Auditor | 10 TVFs, 2 MVs, 4 ML |
| ⚡ **Performance Agent** | Performance Analyzer | 16 TVFs, 3 MVs, 7 ML |
| 🔄 **Reliability Agent** | Job Health Monitor | 12 TVFs, 1 MV, 5 ML |
| ✅ **Data Quality Agent** | Data Quality Monitor | 7 TVFs, 2 MVs, 3 ML |
| 🌐 **Orchestrator Agent** | Unified Health Monitor | All 60 TVFs, 10 MVs, 25 ML |

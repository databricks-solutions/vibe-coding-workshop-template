# Worked Example: Wanderbricks (Hospitality)

This is a complete worked example demonstrating the project plan methodology applied to a vacation rental analytics platform.

## Project Overview

**Wanderbricks** is a vacation rental analytics platform (similar to Airbnb) demonstrating the complete data platform methodology.

**Business Domain:** Hospitality / Vacation Rentals
**Use Cases:** Revenue tracking, host performance, customer analytics, property management, engagement funnels

## Agent Domains

| Domain | Icon | Focus Area | Key Gold Tables |
|--------|------|------------|-----------------|
| **Revenue** | 💰 | Booking revenue, payments, pricing optimization | `fact_booking_daily`, `fact_booking_detail` |
| **Engagement** | 📊 | Views, clicks, conversions, marketing effectiveness | `fact_property_engagement` |
| **Property** | 🏠 | Listings, availability, amenities, pricing | `dim_property` |
| **Host** | 👤 | Host performance, earnings, quality metrics | `dim_host` |
| **Customer** | 🎯 | User behavior, segmentation, lifetime value | `dim_user` |

## Prerequisites (Data Layers)

| Layer | Schema | Tables | Status |
|-------|--------|--------|--------|
| Bronze | `wanderbricks_bronze` | 16 | ✅ Complete |
| Silver | `wanderbricks_silver` | 8+ | ✅ Complete |
| Gold | `wanderbricks_gold` | 10 | ✅ Complete |

**Gold Layer Dimensional Model:**

| Type | Count | Tables |
|------|-------|--------|
| Dimensions | 7 | `dim_user`, `dim_host`, `dim_property`, `dim_destination`, `dim_date`, `dim_weather_location` |
| Facts | 4 | `fact_booking_detail`, `fact_booking_daily`, `fact_property_engagement`, `fact_weather_daily` |
| Config | 1 | `alert_rules` |
| **Total** | **10+** | |

## Artifact Totals (Actual Counts)

| Artifact Type | Count | Status |
|--------------|-------|--------|
| Gold Tables | 10 | ✅ Complete |
| Table-Valued Functions | 36 | ✅ Complete |
| Metric Views | 5 | ✅ Complete |
| AI/BI Dashboards | 6 | ✅ Complete |
| Lakehouse Monitors | 5 | ✅ Complete |
| ML Models | 6 | ✅ Complete |
| SQL Alerts | 21 | 📋 Planned |
| Genie Spaces | 6 | 📋 Planned |
| AI Agents | 6 | 📋 Planned |
| **Total Artifacts** | **101+** | |

## TVFs by Domain (36 Total)

| Domain | Icon | TVF Count | Example TVFs |
|--------|------|-----------|--------------|
| Revenue | 💰 | 6 | `get_revenue_trend`, `get_booking_summary`, `get_payment_analysis` |
| Engagement | 📊 | 5 | `get_conversion_funnel`, `get_engagement_metrics`, `get_view_to_book_rate` |
| Property | 🏠 | 5 | `get_property_performance`, `get_availability_analysis`, `get_pricing_insights` |
| Host | 👤 | 5 | `get_host_performance`, `get_host_earnings`, `get_host_quality_metrics` |
| Customer | 🎯 | 6 | `get_customer_ltv`, `get_customer_segments`, `get_customer_behavior` |
| ML Predictions | 🤖 | 9 | `get_demand_forecast`, `get_ltv_predictions`, `get_churn_predictions` |

## Metric Views by Domain (5 Total)

| Domain | Icon | Metric View | Key Measures |
|--------|------|-------------|--------------|
| Revenue | 💰 | `revenue_analytics_metrics` | Total revenue, avg booking value, RevPAR |
| Engagement | 📊 | `engagement_analytics_metrics` | Conversion rate, bounce rate, time on site |
| Property | 🏠 | `property_analytics_metrics` | Occupancy rate, ADR, listing count |
| Host | 👤 | `host_analytics_metrics` | Host earnings, response rate, ratings |
| Customer | 🎯 | `customer_analytics_metrics` | CLV, retention rate, segment distribution |

## ML Models (6 Total)

| Model | Domain | Purpose | Output Table |
|-------|--------|---------|--------------|
| Demand Predictor | 💰 Revenue | Forecast booking demand | `demand_predictions` |
| Pricing Optimizer | 💰 Revenue | Optimal pricing recommendations | `pricing_recommendations` |
| Conversion Predictor | 📊 Engagement | Predict conversion likelihood | `conversion_predictions` |
| Customer LTV | 🎯 Customer | Predict lifetime value | `ltv_predictions` |
| Customer Segmentation | 🎯 Customer | K-means clustering | `customer_segments` |
| Revenue Forecaster | 💰 Revenue | Time-series revenue forecast | `revenue_forecasts` |

## AI/BI Dashboards (6 Total)

| Dashboard | Domain | Primary KPIs |
|-----------|--------|--------------|
| Revenue Performance | 💰 | Total revenue, RevPAR, booking trends |
| Engagement & Conversion | 📊 | Funnel metrics, conversion rates |
| Property Portfolio | 🏠 | Occupancy, ADR, inventory health |
| Host Performance | 👤 | Earnings, ratings, response time |
| Customer Analytics | 🎯 | CLV segments, retention, behavior |
| Lakehouse Monitoring | 🔧 | Data quality, drift metrics, SLAs |

## Agent-to-Genie Space Mapping

| Agent | Genie Space | Data Assets | Use Cases |
|-------|-------------|-------------|-----------|
| 💰 Revenue Agent | Revenue Intelligence | 6 TVFs, 1 MV, 3 ML | Booking analysis, revenue forecasts, pricing |
| 📊 Engagement Agent | Engagement Analytics | 5 TVFs, 1 MV, 1 ML | Funnel analysis, conversion optimization |
| 🏠 Property Agent | Property Intelligence | 5 TVFs, 1 MV | Listing performance, availability, pricing |
| 👤 Host Agent | Host Intelligence | 5 TVFs, 1 MV | Host earnings, quality metrics, rankings |
| 🎯 Customer Agent | Customer Intelligence | 6 TVFs, 1 MV, 2 ML | CLV analysis, segmentation, behavior |
| 🌐 Orchestrator | Wanderbricks Health Monitor | All 36 TVFs, 5 MVs, 6 ML | Multi-domain coordination, routing |

## Key Business Questions by Domain

**💰 Revenue Domain:**
1. What was total booking revenue last month?
2. Which destinations generated the most revenue?
3. What is the average daily rate (ADR) trend?
4. How does revenue compare to same period last year?
5. What is the forecasted revenue for next quarter?

**📊 Engagement Domain:**
1. What is our overall conversion rate (views to bookings)?
2. Which properties have the highest engagement?
3. Where are users dropping off in the booking funnel?
4. What is the average time from first view to booking?
5. Which marketing channels drive the most conversions?

**🏠 Property Domain:**
1. What is the current occupancy rate by destination?
2. Which amenities correlate with higher bookings?
3. How many properties are available for peak season?
4. What is the optimal price range for new listings?
5. Which properties need pricing adjustments?

**👤 Host Domain:**
1. Who are the top-performing hosts by earnings?
2. What is the average host response time?
3. Which hosts have the highest guest ratings?
4. How many hosts are Superhosts?
5. What is the host retention rate?

**🎯 Customer Domain:**
1. What is the average customer lifetime value (CLV)?
2. How many customers are in each segment?
3. What is our customer retention rate?
4. Which customers are at risk of churning?
5. What are the booking patterns for repeat customers?

## Agent Architecture Flow Example

```
User: "What was last month's revenue and which hosts performed best?"
                    │
                    ▼
        ┌───────────────────────────────┐
        │     Orchestrator Agent        │
        │ Uses: Wanderbricks Monitor    │
        │ Intent: Multi-domain (Rev+Host)│
        └───────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│  Revenue Agent    │   │   Host Agent      │
│  Uses: Revenue    │   │   Uses: Host      │
│  Intelligence     │   │   Intelligence    │
└───────────────────┘   └───────────────────┘
        │                       │
        ▼                       ▼
    Genie Space             Genie Space
        │                       │
        ├── get_revenue_trend   ├── get_host_performance
        ├── revenue_analytics   ├── host_analytics
        └── revenue_forecasts   └── get_host_earnings
                    │
                    ▼
        Synthesized Response:
        "Last month's total revenue was $2.4M (+12% YoY).
         Top hosts by earnings:
         1. Maria G. - $45,200 (Barcelona)
         2. James L. - $38,100 (Tokyo)
         3. Sarah K. - $35,800 (New York)"
```

---

## Example Artifact Implementations

### Example TVF: `get_revenue_trend`

**💰 Revenue Domain**

```sql
CREATE OR REPLACE FUNCTION ${catalog}.${gold_schema}.get_revenue_trend(
    start_date STRING COMMENT 'Start date in YYYY-MM-DD format',
    end_date STRING COMMENT 'End date in YYYY-MM-DD format',
    destination_filter STRING DEFAULT NULL COMMENT 'Optional destination filter'
)
RETURNS TABLE (
    booking_date DATE,
    destination STRING,
    total_revenue DECIMAL(18,2),
    total_bookings BIGINT,
    avg_booking_value DECIMAL(18,2)
)
COMMENT 'LLM: Returns daily revenue trends for vacation rental bookings.
Use for: Revenue analysis, trend identification, destination comparison.
Example questions: "What was the revenue trend last month?" "Compare revenue by destination"'
RETURN
    SELECT 
        f.check_in_date AS booking_date,
        d.destination,
        SUM(f.total_booking_value) AS total_revenue,
        COUNT(*) AS total_bookings,
        AVG(f.total_booking_value) AS avg_booking_value
    FROM ${catalog}.${gold_schema}.fact_booking_daily f
    LEFT JOIN ${catalog}.${gold_schema}.dim_destination d 
        ON f.destination_id = d.destination_id
    WHERE f.check_in_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
        AND (destination_filter IS NULL OR d.destination = destination_filter)
    GROUP BY f.check_in_date, d.destination
    ORDER BY booking_date DESC;
```

### Example Metric View: `revenue_analytics_metrics`

**💰 Revenue Domain**

```yaml
version: "1.1"
comment: >
  PURPOSE: Revenue analytics for booking performance and financial KPIs.
  BEST FOR: Total revenue trends | Revenue by destination | ADR analysis | RevPAR metrics
  NOT FOR: Customer-level analysis (use customer_analytics_metrics)
  DIMENSIONS: check_in_date, destination, property_type, booking_status
  MEASURES: total_revenue, avg_booking_value, total_bookings, revpar, adr
  SOURCE: fact_booking_daily (booking domain)
  JOINS: dim_destination (destination details), dim_property (property details)

source: ${catalog}.${gold_schema}.fact_booking_daily

joins:
  - name: dim_destination
    source: ${catalog}.${gold_schema}.dim_destination
    'on': source.destination_id = dim_destination.destination_id
  - name: dim_property
    source: ${catalog}.${gold_schema}.dim_property
    'on': source.property_id = dim_property.property_id AND dim_property.is_current = true

dimensions:
  - name: check_in_date
    expr: source.check_in_date
    comment: Booking check-in date for trend analysis
    display_name: Check-In Date
    synonyms: [date, booking date, arrival date]
  - name: destination
    expr: dim_destination.destination
    comment: Travel destination name
    display_name: Destination
    synonyms: [location, city, place]

measures:
  - name: total_revenue
    expr: SUM(source.total_booking_value)
    comment: Total booking revenue in USD
    display_name: Total Revenue
    format:
      type: currency
      currency_code: USD
    synonyms: [revenue, earnings, income, sales]
  - name: avg_booking_value
    expr: AVG(source.total_booking_value)
    comment: Average value per booking
    display_name: Avg Booking Value
    format:
      type: currency
      currency_code: USD
    synonyms: [average booking, basket size, ABV]
```

### Example Alert: `REV-001-CRIT`

**💰 Revenue Domain**

```yaml
alert_id: REV-001-CRIT
alert_name: Revenue Drop > 20% Week-over-Week
domain: revenue
severity: CRITICAL
alert_description: >
  Monitors for significant week-over-week revenue decline.
  Triggers when total revenue drops more than 20% compared to same day last week.
alert_query: |
  WITH current_week AS (
    SELECT SUM(total_booking_value) as current_revenue
    FROM ${catalog}.${gold_schema}.fact_booking_daily
    WHERE check_in_date = CURRENT_DATE() - INTERVAL 1 DAY
  ),
  previous_week AS (
    SELECT SUM(total_booking_value) as previous_revenue
    FROM ${catalog}.${gold_schema}.fact_booking_daily
    WHERE check_in_date = CURRENT_DATE() - INTERVAL 8 DAYS
  )
  SELECT 
    ROUND((current_revenue - previous_revenue) / previous_revenue * 100, 1) as pct_change,
    current_revenue,
    previous_revenue,
    'Revenue dropped ' || ABS(ROUND((current_revenue - previous_revenue) / previous_revenue * 100, 1)) || '% WoW' as alert_message
  FROM current_week, previous_week
  WHERE (current_revenue - previous_revenue) / previous_revenue < -0.20
condition_column: pct_change
condition_operator: "<"
condition_threshold: "-20"
schedule_cron: "0 0 6 * * ?"
schedule_timezone: America/Los_Angeles
notification_emails: revenue-team@wanderbricks.com
is_enabled: true
owner: data-engineering@wanderbricks.com
```

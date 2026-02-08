# SQL Alert Patterns Reference

## SQL Query Patterns

### Pattern 1: Threshold Comparison (Most Common)

**Use Case:** Alert when metric crosses a threshold

```sql
-- REV-002-CRIT: High Cancellation Rate (>15%)
SELECT 
    DATE_ADD(CURRENT_DATE(), -1) as check_in_date,
    SUM(cancellation_count) as cancellations,
    SUM(booking_count) as bookings,
    ROUND(SUM(cancellation_count) / NULLIF(SUM(booking_count), 0) * 100, 1) as cancellation_rate,
    'CRITICAL: Cancellation rate at ' || 
        ROUND(SUM(cancellation_count) / NULLIF(SUM(booking_count), 0) * 100, 1) || 
        '% (' || SUM(cancellation_count) || ' of ' || SUM(booking_count) || ' bookings)' as alert_message
FROM {catalog}.{gold_schema}.fact_booking_daily
WHERE check_in_date = DATE_ADD(CURRENT_DATE(), -1)
HAVING SUM(cancellation_count) / NULLIF(SUM(booking_count), 0) > 0.15
```

**Key Elements:**
- `condition_column`: `cancellation_rate`
- `condition_operator`: `>`
- `condition_threshold`: `15`
- Returns rows ONLY when condition is met (via HAVING clause)
- Includes `alert_message` column for notification content

### Pattern 2: Percentage Change from Baseline

**Use Case:** Alert when metric deviates from historical average

```sql
-- REV-001-CRIT: Revenue Drop (>20% below 7-day average)
SELECT 
    CURRENT_DATE() as alert_date,
    yesterday_revenue,
    avg_7d_revenue,
    ROUND((yesterday_revenue - avg_7d_revenue) / avg_7d_revenue * 100, 1) as pct_change,
    'CRITICAL: Revenue dropped ' || 
        ROUND((avg_7d_revenue - yesterday_revenue) / avg_7d_revenue * 100, 1) || 
        '% below 7-day average ($' || FORMAT_NUMBER(yesterday_revenue, 2) || 
        ' vs avg $' || FORMAT_NUMBER(avg_7d_revenue, 2) || ')' as alert_message
FROM (
    SELECT
        SUM(CASE WHEN check_in_date = DATE_ADD(CURRENT_DATE(), -1) 
            THEN total_booking_value ELSE 0 END) as yesterday_revenue,
        AVG(CASE WHEN check_in_date BETWEEN DATE_ADD(CURRENT_DATE(), -8) 
            AND DATE_ADD(CURRENT_DATE(), -2) 
            THEN daily_total ELSE NULL END) as avg_7d_revenue
    FROM (
        SELECT check_in_date, SUM(total_booking_value) as daily_total
        FROM {catalog}.{gold_schema}.fact_booking_daily
        WHERE check_in_date >= DATE_ADD(CURRENT_DATE(), -8)
        GROUP BY 1
    )
)
WHERE yesterday_revenue < avg_7d_revenue * 0.8
```

### Pattern 3: Statistical Anomaly Detection (Z-Score)

**Use Case:** Alert when metric is statistically unusual

```sql
-- REV-003-WARN: Booking Volume Anomaly (>2 std from mean)
SELECT 
    CURRENT_TIMESTAMP() as alert_time,
    today_bookings,
    ROUND(avg_bookings, 0) as avg_bookings,
    ROUND(stddev_bookings, 0) as stddev_bookings,
    ROUND((today_bookings - avg_bookings) / NULLIF(stddev_bookings, 0), 1) as z_score,
    'WARNING: Booking volume anomaly - ' || today_bookings || ' bookings (' ||
        ROUND((today_bookings - avg_bookings) / NULLIF(stddev_bookings, 0), 1) || 
        ' std deviations from 30-day mean of ' || ROUND(avg_bookings, 0) || ')' as alert_message
FROM (
    SELECT
        SUM(CASE WHEN check_in_date = CURRENT_DATE() 
            THEN booking_count ELSE 0 END) as today_bookings,
        AVG(daily_bookings) as avg_bookings,
        STDDEV(daily_bookings) as stddev_bookings
    FROM (
        SELECT check_in_date, SUM(booking_count) as daily_bookings
        FROM {catalog}.{gold_schema}.fact_booking_daily
        WHERE check_in_date BETWEEN DATE_ADD(CURRENT_DATE(), -30) AND CURRENT_DATE()
        GROUP BY 1
    )
)
WHERE ABS(today_bookings - avg_bookings) > 2 * stddev_bookings
  AND stddev_bookings > 0  -- Prevent division by zero
```

### Pattern 4: Count-Based Alert (Low Activity)

**Use Case:** Alert when count is below threshold

```sql
-- ENG-003-WARN: Low Engagement Properties (<10 views in 7 days)
SELECT 
    COUNT(*) as low_engagement_count,
    CONCAT_WS(', ', COLLECT_LIST(CAST(property_id AS STRING))) as property_ids,
    'WARNING: ' || COUNT(*) || ' properties have <10 views in past 7 days' as alert_message
FROM (
    SELECT 
        p.property_id,
        COALESCE(SUM(e.view_count), 0) as weekly_views
    FROM {catalog}.{gold_schema}.dim_property p
    LEFT JOIN {catalog}.{gold_schema}.fact_property_engagement e
        ON p.property_id = e.property_id
        AND e.engagement_date >= DATE_ADD(CURRENT_DATE(), -7)
    WHERE p.is_current = true
    GROUP BY p.property_id
    HAVING COALESCE(SUM(e.view_count), 0) < 10
)
HAVING COUNT(*) > 0  -- Only alert if there are affected properties
```

### Pattern 5: Informational Summary (Always Triggers)

**Use Case:** Daily/weekly summary reports

```sql
-- REV-005-INFO: Daily Revenue Summary
SELECT 
    DATE_ADD(CURRENT_DATE(), -1) as date,
    SUM(total_booking_value) as total_revenue,
    SUM(booking_count) as total_bookings,
    ROUND(AVG(avg_booking_value), 2) as avg_booking_value,
    1 as always_trigger,  -- ✅ Always returns 1 for INFO alerts
    'Daily Summary: $' || FORMAT_NUMBER(SUM(total_booking_value), 2) || 
        ' revenue from ' || SUM(booking_count) || ' bookings' as alert_message
FROM {catalog}.{gold_schema}.fact_booking_daily
WHERE check_in_date = DATE_ADD(CURRENT_DATE(), -1)
```

**Key:** For INFO alerts that should always trigger, include a column like `always_trigger` set to `1`, with condition `condition_column='always_trigger', condition_operator='=', condition_threshold='1'`.

## Query Design Rules

1. **Always include `alert_message`**: Human-readable notification content
2. **Use `NULLIF()` for division**: Prevent division by zero errors
3. **Filter with WHERE + HAVING**: WHERE for time ranges, HAVING for threshold filtering
4. **Include context in message**: Actual values, thresholds, and percentages
5. **Use `FORMAT_NUMBER()` for currency**: Proper formatting in messages

## Complete Examples

### Example 1: Critical Revenue Alert

```python
{
    "alert_id": "REV-001-CRIT",
    "alert_name": "Revenue Drop Alert",
    "domain": "revenue",
    "severity": "CRITICAL",
    "alert_description": "Triggers when daily revenue drops below 80% of 7-day average.",
    "alert_query": """
        SELECT 
            CURRENT_DATE() as alert_date,
            yesterday_revenue,
            avg_7d_revenue,
            ROUND((yesterday_revenue - avg_7d_revenue) / avg_7d_revenue * 100, 1) as pct_change,
            'CRITICAL: Revenue dropped ' || 
                ROUND((avg_7d_revenue - yesterday_revenue) / avg_7d_revenue * 100, 1) || 
                '% below 7-day average' as alert_message
        FROM (
            SELECT
                SUM(CASE WHEN check_in_date = DATE_ADD(CURRENT_DATE(), -1) 
                    THEN total_booking_value ELSE 0 END) as yesterday_revenue,
                AVG(CASE WHEN check_in_date BETWEEN DATE_ADD(CURRENT_DATE(), -8) 
                    AND DATE_ADD(CURRENT_DATE(), -2) 
                    THEN daily_total ELSE NULL END) as avg_7d_revenue
            FROM (
                SELECT check_in_date, SUM(total_booking_value) as daily_total
                FROM catalog.gold.fact_booking_daily
                WHERE check_in_date >= DATE_ADD(CURRENT_DATE(), -8)
                GROUP BY 1
            )
        )
        WHERE yesterday_revenue < avg_7d_revenue * 0.8
    """,
    "condition_column": "pct_change",
    "condition_operator": "<",
    "condition_threshold": "-20",
    "aggregation_type": "FIRST",
    "schedule_cron": "0 0 6 * * ?",  # Daily at 6 AM
    "schedule_timezone": "America/Los_Angeles",
    "notification_emails": "finance@company.com,revenue@company.com",
    "notification_slack_channel": "#revenue-alerts",
    "custom_subject_template": "[{{ALERT_STATUS}}] CRITICAL: {{ALERT_NAME}}",
    "custom_body_template": """Alert: {{ALERT_NAME}}
Time: {{ALERT_TIME}}
Status: {{ALERT_STATUS}}

{{QUERY_RESULT_VALUE}}

Action Required: Investigate immediately.

View Alert: {{ALERT_URL}}""",
    "notify_on_ok": True,
    "rearm_seconds": 1800,  # 30 min cooldown
    "is_enabled": True,
    "tags": '{"team": "finance", "priority": "p1"}',
    "owner": "data-engineering@company.com"
}
```

### Example 2: Warning Engagement Alert

```python
{
    "alert_id": "ENG-002-WARN",
    "alert_name": "Conversion Rate Drop",
    "domain": "engagement",
    "severity": "WARNING",
    "alert_description": "Triggers when average conversion rate falls below 2%.",
    "alert_query": """
        SELECT 
            DATE_ADD(CURRENT_DATE(), -1) as date,
            ROUND(AVG(conversion_rate), 2) as avg_conversion,
            COUNT(*) as property_count,
            'WARNING: Conversion rate at ' || 
                ROUND(AVG(conversion_rate), 2) || '% (threshold: 2%)' as alert_message
        FROM catalog.gold.fact_property_engagement
        WHERE engagement_date = DATE_ADD(CURRENT_DATE(), -1)
        HAVING AVG(conversion_rate) < 2
    """,
    "condition_column": "avg_conversion",
    "condition_operator": "<",
    "condition_threshold": "2",
    "aggregation_type": "FIRST",
    "schedule_cron": "0 0 8 * * ?",  # Daily at 8 AM
    "schedule_timezone": "America/Los_Angeles",
    "notification_emails": "growth@company.com",
    "notification_slack_channel": "#marketing-alerts",
    "custom_subject_template": "[{{ALERT_STATUS}}] Warning: {{ALERT_NAME}}",
    "custom_body_template": """Alert: {{ALERT_NAME}}
Time: {{ALERT_TIME}}
Status: {{ALERT_STATUS}}

{{QUERY_RESULT_VALUE}}

Please investigate at your earliest convenience.

View Alert: {{ALERT_URL}}""",
    "notify_on_ok": True,
    "rearm_seconds": 3600,
    "is_enabled": True,
    "tags": '{"team": "growth", "priority": "p2"}',
    "owner": "data-engineering@company.com"
}
```

### Example 3: Info Summary Alert

```python
{
    "alert_id": "REV-005-INFO",
    "alert_name": "Daily Revenue Summary",
    "domain": "revenue",
    "severity": "INFO",
    "alert_description": "Daily informational summary of revenue metrics.",
    "alert_query": """
        SELECT 
            DATE_ADD(CURRENT_DATE(), -1) as date,
            SUM(total_booking_value) as total_revenue,
            SUM(booking_count) as total_bookings,
            ROUND(AVG(avg_booking_value), 2) as avg_booking_value,
            1 as always_trigger,
            'Daily Summary: $' || FORMAT_NUMBER(SUM(total_booking_value), 2) || 
                ' revenue from ' || SUM(booking_count) || ' bookings' as alert_message
        FROM catalog.gold.fact_booking_daily
        WHERE check_in_date = DATE_ADD(CURRENT_DATE(), -1)
    """,
    "condition_column": "always_trigger",
    "condition_operator": "=",
    "condition_threshold": "1",
    "aggregation_type": "FIRST",
    "schedule_cron": "0 0 9 * * ?",  # Daily at 9 AM
    "schedule_timezone": "America/Los_Angeles",
    "notification_emails": "leadership@company.com",
    "notification_slack_channel": "#daily-metrics",
    "custom_subject_template": "[INFO] {{ALERT_NAME}}",
    "custom_body_template": """Daily Summary: {{ALERT_NAME}}
Time: {{ALERT_TIME}}

{{QUERY_RESULT_TABLE}}

View Details: {{ALERT_URL}}""",
    "notify_on_ok": False,
    "rearm_seconds": None,
    "is_enabled": True,
    "tags": '{"team": "leadership", "priority": "p3"}',
    "owner": "data-engineering@company.com"
}
```

## Custom Notification Templates

### Available Variables

| Variable | Description |
|----------|-------------|
| `{{ALERT_NAME}}` | Display name of the alert |
| `{{ALERT_STATUS}}` | Current status: TRIGGERED, OK, ERROR |
| `{{ALERT_TIME}}` | Timestamp when alert was evaluated |
| `{{QUERY_RESULT_VALUE}}` | Single value from query result |
| `{{QUERY_RESULT_TABLE}}` | Full table of query results |
| `{{ALERT_URL}}` | Link to alert in Databricks UI |

### Critical Template

```
Alert: {{ALERT_NAME}}
Time: {{ALERT_TIME}}
Status: {{ALERT_STATUS}}

{{QUERY_RESULT_VALUE}}

⚠️ Action Required: Investigate immediately.

View Alert: {{ALERT_URL}}
```

### Warning Template

```
Alert: {{ALERT_NAME}}
Time: {{ALERT_TIME}}
Status: {{ALERT_STATUS}}

{{QUERY_RESULT_VALUE}}

Please investigate at your earliest convenience.

View Alert: {{ALERT_URL}}
```

### Info Template

```
Summary: {{ALERT_NAME}}
Time: {{ALERT_TIME}}

{{QUERY_RESULT_TABLE}}

View Details: {{ALERT_URL}}
```

## Schedule Patterns (Quartz Cron)

### Common Schedules

| Pattern | Cron Expression | Description |
|---------|-----------------|-------------|
| Daily at 6 AM | `0 0 6 * * ?` | Morning critical alerts |
| Hourly | `0 0 * * * ?` | Frequent monitoring |
| Every 15 min | `0 0/15 * * * ?` | High-frequency alerts |
| Weekly Monday 9 AM | `0 0 9 ? * MON` | Weekly summaries |
| Business hours | `0 0 9-17 * * ?` | 9 AM to 5 PM hourly |

### Timezone Considerations

Always use IANA timezone identifiers:
- `America/Los_Angeles` (Pacific)
- `America/New_York` (Eastern)
- `UTC` (Coordinated Universal Time)
- `America/Chicago` (Central)

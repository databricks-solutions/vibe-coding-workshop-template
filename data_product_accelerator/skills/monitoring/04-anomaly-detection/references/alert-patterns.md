# Anomaly Detection Alert Patterns

## Overview

Set up Databricks SQL Alerts on the anomaly detection system table to receive notifications when tables become unhealthy.

**System Table:** `system.data_quality_monitoring.table_results`

**Access Required:** SELECT on the system table (account admin must grant access)

## Alert Query Template

```sql
WITH rounded_data AS (
  SELECT
    DATE_TRUNC('HOUR', event_time) AS evaluated_at,
    CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
    status,
    MAX(downstream_impact.num_queries_on_affected_tables) AS impacted_queries,
    MAX(freshness.commit_freshness.predicted_value) AS commit_expected,
    MAX(freshness.commit_freshness.last_value) AS commit_actual,
    MAX(completeness.daily_row_count.min_predicted_value) AS completeness_expected,
    MAX(completeness.daily_row_count.last_value) AS completeness_actual
  FROM system.data_quality_monitoring.table_results
  GROUP BY ALL
)
SELECT
  evaluated_at,
  full_table_name,
  status,
  commit_expected,
  commit_actual,
  completeness_expected,
  completeness_actual,
  impacted_queries
FROM rounded_data
WHERE
  evaluated_at >= current_timestamp() - INTERVAL 6 HOURS
  AND impacted_queries > :min_tables_affected
  AND status = 'Unhealthy';
```

**Parameter:** `:min_tables_affected` — minimum downstream query impact before triggering alert.

## Setting Up the Alert

### Step 1: Create SQL Alert
1. Click **Alerts** in the sidebar
2. Click **Create alert**
3. Paste the alert query above
4. Run the query to verify

### Step 2: Configure Alert Condition
- **Trigger when:** Rows returned > 0
- **Evaluation interval:** Every 1 hour (or as needed)

### Step 3: Custom Email Template (Optional)

Open **Advanced** tab > check **Customize template**:

```html
<h4>The following tables are failing quality checks in the last hour</h4>
<table>
  <tr>
    <td>
      <table>
        <tr>
          <th>Table</th>
          <th>Expected Staleness</th>
          <th>Actual Staleness</th>
          <th>Expected Row Volume</th>
          <th>Actual Row Volume</th>
          <th>Impact (queries)</th>
        </tr>
        {{#QUERY_RESULT_ROWS}}
        <tr>
          <td>{{full_table_name}}</td>
          <td>{{commit_expected}}</td>
          <td>{{commit_actual}}</td>
          <td>{{completeness_expected}}</td>
          <td>{{completeness_actual}}</td>
          <td>{{impacted_queries}}</td>
        </tr>
        {{/QUERY_RESULT_ROWS}}
      </table>
    </td>
  </tr>
</table>
```

## Alternative Alert Queries

### Freshness-Only Alert

```sql
SELECT
  CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
  freshness.commit_freshness.last_value AS last_commit,
  freshness.commit_freshness.predicted_value AS expected_by,
  downstream_impact.impact_level
FROM system.data_quality_monitoring.table_results
WHERE event_time >= current_timestamp() - INTERVAL 6 HOURS
  AND freshness.status = 'Unhealthy'
  AND downstream_impact.impact_level >= :min_impact_level;
```

### Completeness-Only Alert

```sql
SELECT
  CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
  completeness.daily_row_count.last_value AS actual_rows,
  completeness.daily_row_count.min_predicted_value AS expected_min,
  downstream_impact.impact_level
FROM system.data_quality_monitoring.table_results
WHERE event_time >= current_timestamp() - INTERVAL 6 HOURS
  AND completeness.status = 'Unhealthy'
  AND downstream_impact.impact_level >= :min_impact_level;
```

### High-Impact Only Alert

```sql
SELECT
  CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
  status,
  CASE downstream_impact.impact_level
    WHEN 4 THEN 'VERY HIGH'
    WHEN 3 THEN 'HIGH'
    WHEN 2 THEN 'MEDIUM'
    WHEN 1 THEN 'LOW'
    ELSE 'NONE'
  END AS impact,
  downstream_impact.num_downstream_tables,
  downstream_impact.num_queries_on_affected_tables
FROM system.data_quality_monitoring.table_results
WHERE event_time >= current_timestamp() - INTERVAL 6 HOURS
  AND status = 'Unhealthy'
  AND downstream_impact.impact_level >= 3;
```

## Integration with sql-alerting-patterns Skill

For config-driven alert deployment via the Databricks SDK, the anomaly detection queries above can be used with the `sql-alerting-patterns` skill's alert configuration table pattern. Add entries to the alert config table with:

- `alert_type`: `anomaly_detection`
- `query_text`: One of the query patterns above
- `schedule`: Appropriate Quartz cron expression
- `notification_targets`: Team email addresses

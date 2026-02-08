"""
Anomaly Detection Results Query Utilities

Query the system results table for anomaly detection insights.

System Table: system.data_quality_monitoring.table_results
Access: Account admin must grant SELECT to non-admin users.

Usage:
  python query_results.py --catalog my_catalog --schema my_gold --report summary
  python query_results.py --catalog my_catalog --schema my_gold --report unhealthy
  python query_results.py --catalog my_catalog --schema my_gold --report root_cause
"""

import argparse

from pyspark.sql import SparkSession


def get_unhealthy_tables(spark: SparkSession, catalog: str, schema: str):
    """Query unhealthy tables with downstream impact."""
    return spark.sql(f"""
        SELECT
            CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
            status,
            freshness.status AS freshness_status,
            completeness.status AS completeness_status,
            downstream_impact.impact_level,
            downstream_impact.num_downstream_tables,
            downstream_impact.num_queries_on_affected_tables AS impacted_queries
        FROM system.data_quality_monitoring.table_results
        WHERE catalog_name = '{catalog}'
          AND schema_name = '{schema}'
          AND status = 'Unhealthy'
        ORDER BY downstream_impact.impact_level DESC, event_time DESC
    """)


def get_freshness_issues(spark: SparkSession, catalog: str, schema: str):
    """Query tables with freshness (staleness) issues."""
    return spark.sql(f"""
        SELECT
            table_name,
            freshness.commit_freshness.last_value AS last_commit,
            freshness.commit_freshness.predicted_value AS expected_by,
            freshness.commit_freshness.error_code
        FROM system.data_quality_monitoring.table_results
        WHERE catalog_name = '{catalog}'
          AND schema_name = '{schema}'
          AND freshness.status = 'Unhealthy'
        ORDER BY freshness.commit_freshness.last_value ASC
    """)


def get_completeness_issues(spark: SparkSession, catalog: str, schema: str):
    """Query tables with completeness (missing rows) issues."""
    return spark.sql(f"""
        SELECT
            table_name,
            completeness.daily_row_count.last_value AS actual_rows,
            completeness.daily_row_count.min_predicted_value AS expected_min,
            completeness.daily_row_count.max_predicted_value AS expected_max,
            ROUND(
                completeness.daily_row_count.last_value * 100.0 /
                NULLIF(completeness.daily_row_count.min_predicted_value, 0), 1
            ) AS pct_of_expected
        FROM system.data_quality_monitoring.table_results
        WHERE catalog_name = '{catalog}'
          AND schema_name = '{schema}'
          AND completeness.status = 'Unhealthy'
        ORDER BY pct_of_expected ASC
    """)


def get_root_cause_analysis(spark: SparkSession, catalog: str, schema: str):
    """Query root cause analysis for unhealthy tables."""
    return spark.sql(f"""
        SELECT
            table_name,
            status,
            rca.job_id,
            rca.job_name,
            rca.last_run_status,
            rca.run_page_url
        FROM system.data_quality_monitoring.table_results
        LATERAL VIEW EXPLODE(root_cause_analysis.upstream_jobs) AS rca
        WHERE catalog_name = '{catalog}'
          AND schema_name = '{schema}'
          AND status = 'Unhealthy'
        ORDER BY table_name
    """)


def get_schema_health_summary(spark: SparkSession, catalog: str, schema: str):
    """Generate health summary for a schema."""
    return spark.sql(f"""
        SELECT
            catalog_name,
            schema_name,
            COUNT(*) AS total_tables,
            SUM(CASE WHEN status = 'Healthy' THEN 1 ELSE 0 END) AS healthy,
            SUM(CASE WHEN status = 'Unhealthy' THEN 1 ELSE 0 END) AS unhealthy,
            SUM(CASE WHEN status = 'Unknown' THEN 1 ELSE 0 END) AS unknown,
            ROUND(
                SUM(CASE WHEN status = 'Healthy' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
            ) AS health_pct
        FROM system.data_quality_monitoring.table_results
        WHERE catalog_name = '{catalog}'
          AND schema_name = '{schema}'
          AND event_time >= current_timestamp() - INTERVAL 24 HOURS
        GROUP BY catalog_name, schema_name
    """)


def get_high_impact_issues(spark: SparkSession):
    """Query high-impact issues across ALL schemas."""
    return spark.sql("""
        SELECT
            CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
            CASE downstream_impact.impact_level
                WHEN 4 THEN 'VERY HIGH'
                WHEN 3 THEN 'HIGH'
                WHEN 2 THEN 'MEDIUM'
                WHEN 1 THEN 'LOW'
                ELSE 'NONE'
            END AS impact,
            downstream_impact.num_downstream_tables,
            downstream_impact.num_queries_on_affected_tables,
            freshness.status AS freshness_status,
            completeness.status AS completeness_status
        FROM system.data_quality_monitoring.table_results
        WHERE status = 'Unhealthy'
          AND downstream_impact.impact_level >= 3
        ORDER BY downstream_impact.impact_level DESC,
                 downstream_impact.num_queries_on_affected_tables DESC
    """)


def main():
    parser = argparse.ArgumentParser(
        description="Query Anomaly Detection Results"
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument(
        "--report",
        choices=["summary", "unhealthy", "freshness", "completeness", "root_cause", "high_impact"],
        default="summary",
    )

    args = parser.parse_args()
    spark = SparkSession.getActiveSession()

    print(f"\n{'=' * 80}")
    print(f"Anomaly Detection Report: {args.report}")
    print(f"Scope: {args.catalog}.{args.schema}")
    print(f"{'=' * 80}\n")

    if args.report == "summary":
        df = get_schema_health_summary(spark, args.catalog, args.schema)
    elif args.report == "unhealthy":
        df = get_unhealthy_tables(spark, args.catalog, args.schema)
    elif args.report == "freshness":
        df = get_freshness_issues(spark, args.catalog, args.schema)
    elif args.report == "completeness":
        df = get_completeness_issues(spark, args.catalog, args.schema)
    elif args.report == "root_cause":
        df = get_root_cause_analysis(spark, args.catalog, args.schema)
    elif args.report == "high_impact":
        df = get_high_impact_issues(spark)

    df.show(truncate=False)

    row_count = df.count()
    print(f"\nTotal rows: {row_count}")


if __name__ == "__main__":
    main()

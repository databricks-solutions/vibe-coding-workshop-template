# Databricks notebook source

"""
{Project Name} Bronze Layer - Table Setup

Creates Bronze layer tables for testing/demo purposes with Unity Catalog compliance.

Data Strategy:
- Generate fake data with Faker (primary)
- OR copy from existing source
- OR reference existing Bronze tables

Usage:
  databricks bundle run bronze_setup_job -t dev

Template Instructions:
  1. Replace {project} with your project name
  2. Replace {entity} placeholders with actual entity names
  3. Define columns for each entity based on your domain
  4. Update TBLPROPERTIES for each table (domain, classification, etc.)
"""


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    bronze_schema = dbutils.widgets.get("bronze_schema")

    print(f"Catalog: {catalog}")
    print(f"Bronze Schema: {bronze_schema}")

    return catalog, bronze_schema


def create_catalog_and_schema(spark, catalog: str, schema: str):
    """Ensures the Unity Catalog schema exists."""
    print(f"Ensuring catalog '{catalog}' and schema '{schema}' exist...")
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

    # Enable Predictive Optimization at schema level
    spark.sql(f"""
        ALTER SCHEMA {catalog}.{schema}
        SET TBLPROPERTIES (
            'databricks.pipelines.predictiveOptimizations.enabled' = 'true'
        )
    """)

    print(f"Schema {catalog}.{schema} ready with Predictive Optimization enabled")


# ---------------------------------------------------------------------------
# DIMENSION TABLE TEMPLATES
# Copy and customize one function per dimension table.
# ---------------------------------------------------------------------------

def create_entity_dim_table(spark, catalog: str, schema: str):
    """
    Create {entity_display_name} dimension table.

    Template: Replace {entity} with actual entity name (e.g., store, product, customer).
    Define columns based on your domain requirements.
    """
    entity = "entity"  # REPLACE with actual entity name
    print(f"\nCreating {catalog}.{schema}.bronze_{entity}_dim...")

    table_ddl = f"""
        CREATE OR REPLACE TABLE {catalog}.{schema}.bronze_{entity}_dim (
            -- PRIMARY KEY COLUMN(S)
            {entity}_id STRING NOT NULL
                COMMENT 'Unique identifier for {entity}',

            -- BUSINESS COLUMNS (define based on your use case)
            name STRING NOT NULL
                COMMENT '{entity} display name',
            category STRING
                COMMENT '{entity} category for grouping',
            status STRING
                COMMENT 'Current status (active/inactive)',

            -- AUDIT COLUMNS (standard for all Bronze tables)
            ingestion_timestamp TIMESTAMP NOT NULL
                COMMENT 'Timestamp when record was ingested into Bronze layer',
            source_file STRING
                COMMENT 'Data source identifier for traceability'
        )
        USING DELTA
        CLUSTER BY AUTO
        COMMENT 'LLM: Bronze layer dimension table for {entity}. Contains master data
            for testing/demo purposes. Generated with Faker for realistic test data.
            Enables incremental Silver processing via Change Data Feed.'
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.autoOptimize.optimizeWrite' = 'true',
            'delta.autoOptimize.autoCompact' = 'true',
            'layer' = 'bronze',
            'source_system' = 'Faker Test Data Generator',
            'domain' = 'REPLACE_DOMAIN',
            'entity_type' = 'dimension',
            'contains_pii' = 'false',
            'data_classification' = 'internal',
            'business_owner' = 'REPLACE_TEAM',
            'technical_owner' = 'Data Engineering',
            'business_owner_email' = 'REPLACE@company.com',
            'technical_owner_email' = 'data-engineering@company.com',
            'grain' = 'One row per {entity}',
            'data_purpose' = 'testing_demo',
            'is_production' = 'false'
        )
    """

    spark.sql(table_ddl)
    print(f"Created {catalog}.{schema}.bronze_{entity}_dim")


def create_date_dim_table(spark, catalog: str, schema: str):
    """
    Create date dimension table.

    Standard date dimension with calendar attributes.
    Generated via SQL SEQUENCE, not Faker.
    """
    print(f"\nCreating {catalog}.{schema}.bronze_date_dim...")

    table_ddl = f"""
        CREATE OR REPLACE TABLE {catalog}.{schema}.bronze_date_dim (
            date DATE NOT NULL
                COMMENT 'Calendar date (primary key)',
            year INT NOT NULL
                COMMENT 'Calendar year (e.g., 2024)',
            quarter INT NOT NULL
                COMMENT 'Calendar quarter (1-4)',
            month INT NOT NULL
                COMMENT 'Calendar month (1-12)',
            month_name STRING NOT NULL
                COMMENT 'Full month name (e.g., January)',
            week_of_year INT NOT NULL
                COMMENT 'ISO week of year (1-53)',
            day_of_week INT NOT NULL
                COMMENT 'Day of week (1=Sunday, 7=Saturday)',
            day_of_week_name STRING NOT NULL
                COMMENT 'Full day name (e.g., Monday)',
            day_of_month INT NOT NULL
                COMMENT 'Day of month (1-31)',
            day_of_year INT NOT NULL
                COMMENT 'Day of year (1-366)',
            is_weekend BOOLEAN NOT NULL
                COMMENT 'True if Saturday or Sunday',
            is_holiday BOOLEAN NOT NULL
                COMMENT 'True if recognized holiday (manually maintained)',
            ingestion_timestamp TIMESTAMP NOT NULL
                COMMENT 'Timestamp when record was ingested into Bronze layer',
            source_file STRING
                COMMENT 'Data source identifier for traceability'
        )
        USING DELTA
        CLUSTER BY AUTO
        COMMENT 'LLM: Bronze layer date dimension for time-based analysis.
            Contains calendar attributes for join and filter operations.
            Generated via SQL SEQUENCE for complete date coverage.'
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.autoOptimize.optimizeWrite' = 'true',
            'delta.autoOptimize.autoCompact' = 'true',
            'layer' = 'bronze',
            'source_system' = 'Generated (SQL SEQUENCE)',
            'domain' = 'common',
            'entity_type' = 'dimension',
            'contains_pii' = 'false',
            'data_classification' = 'internal',
            'business_owner' = 'Data Engineering',
            'technical_owner' = 'Data Engineering',
            'grain' = 'One row per calendar date',
            'data_purpose' = 'testing_demo',
            'is_production' = 'false'
        )
    """

    spark.sql(table_ddl)
    print(f"Created {catalog}.{schema}.bronze_date_dim")


# ---------------------------------------------------------------------------
# FACT TABLE TEMPLATES
# Copy and customize one function per fact table.
# ---------------------------------------------------------------------------

def create_entity_fact_table(spark, catalog: str, schema: str):
    """
    Create {entity} fact table.

    Template: Replace {entity} with actual entity name (e.g., transactions, orders).
    Define FK columns referencing dimension tables.
    """
    entity = "entity"  # REPLACE with actual entity name
    print(f"\nCreating {catalog}.{schema}.bronze_{entity}...")

    table_ddl = f"""
        CREATE OR REPLACE TABLE {catalog}.{schema}.bronze_{entity} (
            -- PRIMARY KEY COLUMN(S)
            {entity}_id STRING NOT NULL
                COMMENT 'Unique identifier for this {entity} record',

            -- FOREIGN KEY COLUMNS (reference dimension tables)
            dim1_id STRING NOT NULL
                COMMENT 'Reference to dimension 1',
            dim2_id STRING
                COMMENT 'Reference to dimension 2',
            transaction_date DATE NOT NULL
                COMMENT 'Date of the transaction (FK to date dimension)',

            -- MEASURE COLUMNS
            quantity INT NOT NULL
                COMMENT 'Quantity (negative for returns)',
            amount DECIMAL(18, 2) NOT NULL
                COMMENT 'Transaction amount in USD',

            -- AUDIT COLUMNS (standard for all Bronze tables)
            ingestion_timestamp TIMESTAMP NOT NULL
                COMMENT 'Timestamp when record was ingested into Bronze layer',
            source_file STRING
                COMMENT 'Data source identifier for traceability'
        )
        USING DELTA
        CLUSTER BY AUTO
        COMMENT 'LLM: Bronze layer fact table for {entity}. Contains transactional
            data for testing/demo purposes. Generated with Faker for realistic test data.
            Enables incremental Silver processing via Change Data Feed.'
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.autoOptimize.optimizeWrite' = 'true',
            'delta.autoOptimize.autoCompact' = 'true',
            'layer' = 'bronze',
            'source_system' = 'Faker Test Data Generator',
            'domain' = 'REPLACE_DOMAIN',
            'entity_type' = 'fact',
            'contains_pii' = 'false',
            'data_classification' = 'internal',
            'business_owner' = 'REPLACE_TEAM',
            'technical_owner' = 'Data Engineering',
            'business_owner_email' = 'REPLACE@company.com',
            'technical_owner_email' = 'data-engineering@company.com',
            'grain' = 'One row per {entity} event',
            'data_purpose' = 'testing_demo',
            'is_production' = 'false'
        )
    """

    spark.sql(table_ddl)
    print(f"Created {catalog}.{schema}.bronze_{entity}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    """
    Main entry point for Bronze layer table setup.

    Creates empty Bronze tables ready for data generation or copying.
    """
    from pyspark.sql import SparkSession

    # Get parameters
    catalog, bronze_schema = get_parameters()

    # Initialize Spark session
    spark = SparkSession.builder.appName("Bronze Layer Setup").getOrCreate()

    print("=" * 80)
    print("BRONZE LAYER TABLE SETUP")
    print("=" * 80)
    print(f"Catalog: {catalog}")
    print(f"Schema: {bronze_schema}")
    print("=" * 80)

    try:
        # Step 1: Ensure catalog and schema exist
        create_catalog_and_schema(spark, catalog, bronze_schema)

        # Step 2: Create dimension tables
        print("\n--- Creating Dimension Tables ---")
        # REPLACE: Add your dimension table functions here
        # create_store_dim_table(spark, catalog, bronze_schema)
        # create_product_dim_table(spark, catalog, bronze_schema)
        create_date_dim_table(spark, catalog, bronze_schema)

        # Step 3: Create fact tables
        print("\n--- Creating Fact Tables ---")
        # REPLACE: Add your fact table functions here
        # create_transactions_table(spark, catalog, bronze_schema)

        print("\n" + "=" * 80)
        print("Bronze layer setup completed successfully!")
        print("=" * 80)
        print(f"\nCreated tables in: {catalog}.{bronze_schema}")
        print("\nNext steps:")
        print("  1. Run generate_dimensions.py to populate dimension tables")
        print("  2. Run generate_facts.py to populate fact tables")
        print("  OR")
        print("  3. Run copy_from_source.py to copy from existing data")

    except Exception as e:
        print(f"\nError during Bronze layer setup: {str(e)}")
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    main()

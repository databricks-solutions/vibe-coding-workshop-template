"""
Complete example: Fact table with full documentation.
Reference: See references/documentation-templates.md for template patterns.
"""

def create_fact_sales_daily(spark: SparkSession, catalog: str, schema: str):
    """Create fact_sales_daily table."""
    table_name = f"{catalog}.{schema}.fact_sales_daily"
    
    spark.sql(f"""
        CREATE OR REPLACE TABLE {table_name} (
            -- Surrogate foreign keys (joins to dimensions)
            store_key STRING NOT NULL 
                COMMENT 'Surrogate foreign key to dim_store. Business: Joins to store dimension for store attributes and location analysis. Technical: References dim_store.store_key (PRIMARY KEY), enables fast hash joins.',
            
            product_key STRING NOT NULL 
                COMMENT 'Surrogate foreign key to dim_product. Business: Joins to product dimension for product attributes and category analysis. Technical: References dim_product.product_key (PRIMARY KEY), enables fast hash joins.',
            
            date_key INT NOT NULL 
                COMMENT 'Integer surrogate foreign key to dim_date in YYYYMMDD format. Business: Joins to date dimension for calendar attributes and time-series analysis. Technical: Integer FK enables faster joins than date comparisons, references dim_date.date_key (PRIMARY KEY).',
            
            -- Denormalized business keys (human readability)
            store_number STRING NOT NULL 
                COMMENT 'Store business key for human readability. Business: Natural store identifier used by operations, included for query convenience and readability. Technical: Denormalized from dim_store, matches store_key but human-friendly.',
            
            upc_code STRING NOT NULL 
                COMMENT 'Product UPC code for human readability. Business: Natural product identifier scanned at POS, included for query convenience and readability. Technical: Denormalized from dim_product, matches product_key but human-friendly.',
            
            transaction_date DATE NOT NULL 
                COMMENT 'Transaction calendar date for human readability. Business: Natural date value for filtering and display, included for query convenience. Technical: Denormalized from dim_date, matches date_key but human-friendly.',
            
            -- Measures
            net_revenue DECIMAL(18,2) 
                COMMENT 'Net revenue after subtracting returns from gross revenue. Business: The actual revenue realized from sales, primary KPI for financial reporting. Technical: gross_revenue - return_amount, represents true daily sales value.',
            
            net_units BIGINT 
                COMMENT 'Net units sold after subtracting returns. Business: The actual unit demand after accounting for returns, used for true inventory consumption analysis. Technical: units_sold - units_returned.',
            
            transaction_count BIGINT 
                COMMENT 'Total number of sale transactions. Business: Count of all sales events including both sales and returns. Used for traffic analysis and basket metrics. Technical: COUNT(DISTINCT transaction_id).',
            
            -- Audit timestamps
            record_created_timestamp TIMESTAMP 
                COMMENT 'Timestamp when this daily aggregate was first created. Business: Audit field for data lineage and pipeline troubleshooting. Technical: Set during initial MERGE INSERT, remains constant.',
            
            record_updated_timestamp TIMESTAMP 
                COMMENT 'Timestamp when this daily aggregate was last refreshed. Business: Shows data freshness for this date, useful for validating late-arriving transactions were included. Technical: Updated on every MERGE operation that touches this record.'
        )
        USING DELTA
        CLUSTER BY AUTO
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.enableRowTracking' = 'true',
            'delta.enableDeletionVectors' = 'true',
            'delta.autoOptimize.autoCompact' = 'true',
            'delta.autoOptimize.optimizeWrite' = 'true',
            'quality' = 'gold',
            'layer' = 'gold',
            'source_table' = 'silver_transactions',
            'domain' = 'sales',
            'entity_type' = 'fact',
            'grain' = 'daily_store_product',
            'contains_pii' = 'false',
            'data_classification' = 'confidential',
            'business_owner' = 'Sales Analytics',
            'technical_owner' = 'Data Engineering'
        )
        COMMENT 'Gold layer daily sales fact table with pre-aggregated metrics at store-product-day grain. Business: Primary source for sales performance reporting including revenue, units, discounts, returns, and customer loyalty metrics. Aggregated from transaction-level Silver data for fast query performance. Used for dashboards, executive reporting, and sales analysis. Technical: Grain is one row per store-product-date combination. Pre-aggregated measures eliminate need for transaction-level scans, surrogate keys enable fast dimension joins.'
    """)

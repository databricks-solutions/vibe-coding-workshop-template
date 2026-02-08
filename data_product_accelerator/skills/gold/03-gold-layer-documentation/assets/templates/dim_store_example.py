"""
Complete example: Dimension table (SCD Type 2) with full documentation.
Reference: See references/documentation-templates.md for template patterns.
"""

def create_dim_store(spark: SparkSession, catalog: str, schema: str):
    """Create dim_store table (SCD Type 2)."""
    table_name = f"{catalog}.{schema}.dim_store"
    
    spark.sql(f"""
        CREATE OR REPLACE TABLE {table_name} (
            -- Surrogate key (PRIMARY KEY)
            store_key STRING NOT NULL 
                COMMENT 'Surrogate key uniquely identifying each version of a store record. Business: Used for joining fact tables to dimension. Technical: MD5 hash generated from store_id and processed_timestamp to ensure uniqueness across SCD Type 2 versions.',
            
            -- Business key (natural identifier)
            store_number STRING NOT NULL 
                COMMENT 'Business key identifying the physical store location. Business: The primary identifier used by store operations and field teams. Technical: Natural key from source system, same across all historical versions of this store.',
            
            -- Attributes
            store_name STRING 
                COMMENT 'Official name of the retail store location. Business: Used for customer-facing communications and internal reporting. Technical: Free-text field from POS system, may change over time.',
            
            city STRING 
                COMMENT 'City name where the store is located. Business: Used for geographic analysis and territory management. Technical: Standardized city name from address validation.',
            
            state STRING 
                COMMENT 'Two-letter US state code. Business: Used for state-level sales analysis and compliance reporting. Technical: Validated against standard US state abbreviations (CA, TX, NY, etc.).',
            
            -- SCD Type 2 fields
            effective_from TIMESTAMP NOT NULL 
                COMMENT 'Start timestamp for this version of the store record. Business: Indicates when this set of store attributes became active. Technical: SCD Type 2 field, populated from processed_timestamp when new version created.',
            
            effective_to TIMESTAMP 
                COMMENT 'End timestamp for this version of the store record. Business: NULL indicates this is the current version. Non-NULL indicates historical record. Technical: SCD Type 2 field, set to next version effective_from when superseded.',
            
            is_current BOOLEAN NOT NULL 
                COMMENT 'Flag indicating if this is the current active version. Business: TRUE for current store attributes, FALSE for historical records. Used with WHERE is_current = true to get latest state. Technical: SCD Type 2 flag, updated to FALSE when new version created.',
            
            -- Audit timestamps
            record_created_timestamp TIMESTAMP 
                COMMENT 'Timestamp when this record was first inserted into the Gold layer. Business: Audit field for data lineage and troubleshooting. Technical: Set once at INSERT time, never updated.',
            
            record_updated_timestamp TIMESTAMP 
                COMMENT 'Timestamp when this record was last modified. Business: Audit field showing data freshness and update history. Technical: Updated on every MERGE operation that modifies the record.'
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
            'source_table' = 'silver_store_dim',
            'domain' = 'retail',
            'entity_type' = 'dimension',
            'scd_type' = '2',
            'contains_pii' = 'true',
            'data_classification' = 'confidential',
            'business_owner' = 'Retail Operations',
            'technical_owner' = 'Data Engineering'
        )
        COMMENT 'Gold layer conformed store dimension with SCD Type 2 history tracking. Business: Maintains complete store lifecycle history including address changes, status updates, and operational attributes. Each store version tracked separately for point-in-time analysis. Technical: Slowly Changing Dimension Type 2 implementation with effective dating, surrogate keys enable proper fact table joins to historical store states.'
    """)

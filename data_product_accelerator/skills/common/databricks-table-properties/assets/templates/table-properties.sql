-- Table Properties Templates for Unity Catalog Delta Tables
-- Use these templates when creating tables in Bronze, Silver, or Gold layers

-- ============================================================================
-- BRONZE LAYER TABLE TEMPLATE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ${catalog}.${bronze_schema}.${table_name} (
    -- Column definitions here
    id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    data STRING
)
USING DELTA
CLUSTER BY AUTO
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'layer' = 'bronze',
    'source_system' = '${source_system}',  -- Update based on source
    'domain' = '${domain}',  -- e.g., 'retail', 'sales', 'inventory', 'product'
    'entity_type' = '${entity_type}',  -- 'dimension' or 'fact'
    'contains_pii' = '${contains_pii}',  -- 'true' or 'false'
    'data_classification' = '${data_classification}',  -- 'confidential' or 'internal'
    'business_owner' = '${business_owner}',  -- Team Name
    'technical_owner' = 'Data Engineering'
    -- Optional: Add retention for compliance
    -- 'retention_period' = '7_years'  -- Only if required
)
COMMENT 'LLM: Bronze layer ${entity_type} table containing ${description} with full UC compliance.';

-- ============================================================================
-- SILVER LAYER DLT TABLE TEMPLATE (Python)
-- ============================================================================
-- Note: This is used in DLT pipelines, not SQL DDL
-- Example usage:
-- @dlt.table(
--     name="silver_${table_name}",
--     comment="LLM: Silver layer streaming ${entity_type} table...",
--     table_properties={
--         "quality": "silver",
--         "delta.enableChangeDataFeed": "true",
--         "delta.enableRowTracking": "true",
--         "delta.enableDeletionVectors": "true",
--         "delta.autoOptimize.autoCompact": "true",
--         "delta.autoOptimize.optimizeWrite": "true",
--         "delta.tuneFileSizesForRewrites": "true",
--         "layer": "silver",
--         "source_table": "${bronze_table_name}",
--         "domain": "${domain}",
--         "entity_type": "${entity_type}",  -- 'dimension', 'fact', or 'quarantine'
--         "contains_pii": "${contains_pii}",
--         "data_classification": "${data_classification}",
--         "business_owner": "${business_owner}",
--         "technical_owner": "Data Engineering"
--     },
--     cluster_by_auto=True
-- )

-- ============================================================================
-- GOLD LAYER TABLE TEMPLATE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ${catalog}.${gold_schema}.${table_name} (
    -- Column definitions here
    ${surrogate_key} BIGINT NOT NULL,
    ${business_key} STRING NOT NULL,
    -- Additional columns...
)
USING DELTA
CLUSTER BY AUTO
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.enableRowTracking' = 'true',
    'delta.enableDeletionVectors' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'layer' = 'gold',
    'source_layer' = 'silver',
    'domain' = '${domain}',
    'entity_type' = '${entity_type}',  -- 'dimension' or 'fact'
    'contains_pii' = '${contains_pii}',
    'data_classification' = '${data_classification}',
    'business_owner' = '${business_owner}',
    'technical_owner' = 'Data Engineering',
    'gold_type' = '${gold_type}'  -- 'scd2', 'snapshot', or 'aggregated'
)
COMMENT 'Gold layer ${entity_type} table with ${description}. Business: ${business_context}. Technical: ${technical_details}.';

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Always use CLUSTER BY AUTO (never specify columns manually)
-- 2. Enable Change Data Feed (CDF) for all layers to support incremental processing
-- 3. Enable auto-optimize settings for better write performance
-- 4. Silver layer uses Python dict format in DLT pipelines
-- 5. Gold layer comments should be dual-purpose (business + technical)
-- 6. Bronze/Silver layer comments can use "LLM:" prefix for brevity

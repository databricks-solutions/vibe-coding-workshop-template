-- Schema Creation Template for Unity Catalog
-- Use this template in setup scripts for programmatic schema creation

-- ============================================================================
-- CREATE CATALOG (if needed)
-- ============================================================================
CREATE CATALOG IF NOT EXISTS ${catalog}
COMMENT '${catalog_description}';

-- ============================================================================
-- CREATE SCHEMA (Bronze Layer)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS ${catalog}.${bronze_schema}
COMMENT 'Bronze layer schema for raw ingested data';

-- ============================================================================
-- CREATE SCHEMA (Silver Layer)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS ${catalog}.${silver_schema}
COMMENT 'Silver layer schema for cleaned and validated data';

-- ============================================================================
-- CREATE SCHEMA (Gold Layer)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS ${catalog}.${gold_schema}
COMMENT 'Gold layer schema for business-ready dimensional models';

-- ============================================================================
-- ENABLE PREDICTIVE OPTIMIZATION (Schema Level)
-- ============================================================================
-- Enable for specific schema (RECOMMENDED for layer-specific control)
ALTER SCHEMA ${catalog}.${bronze_schema} ENABLE PREDICTIVE OPTIMIZATION;
ALTER SCHEMA ${catalog}.${silver_schema} ENABLE PREDICTIVE OPTIMIZATION;
ALTER SCHEMA ${catalog}.${gold_schema} ENABLE PREDICTIVE OPTIMIZATION;

-- OR enable for entire catalog (simpler but less granular)
-- ALTER CATALOG ${catalog} ENABLE PREDICTIVE OPTIMIZATION;

-- ============================================================================
-- PYTHON FUNCTION TEMPLATE
-- ============================================================================
-- Use this pattern in Python setup scripts:
--
-- def create_catalog_and_schema(spark: SparkSession, catalog: str, schema: str):
--     """Ensures the Unity Catalog schema exists."""
--     print(f"Ensuring catalog '{catalog}' and schema '{schema}' exist...")
--     spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
--     spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
--     print(f"✓ Schema {catalog}.{schema} ready")
--
-- def enable_predictive_optimization(spark: SparkSession, catalog: str):
--     """Enable predictive optimization for all medallion schemas."""
--     schemas = ['bronze_schema', 'silver_schema', 'gold_schema']
--     
--     for schema_name in schemas:
--         try:
--             spark.sql(f"ALTER SCHEMA {catalog}.{schema_name} ENABLE PREDICTIVE OPTIMIZATION")
--             print(f"✓ Enabled predictive optimization for {catalog}.{schema_name}")
--         except Exception as e:
--             print(f"⚠ Could not enable for {schema_name}: {e}")

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Always use CREATE SCHEMA IF NOT EXISTS for idempotency
-- 2. Schemas are created programmatically, NOT as Bundle resources
-- 3. Use schema variables from databricks.yml (not hardcoded names)
-- 4. Enable Predictive Optimization at schema level (not table level)
-- 5. Use ALTER SCHEMA ENABLE PREDICTIVE OPTIMIZATION (not TBLPROPERTIES)
-- 6. Schema creation should happen before table creation in setup scripts

-- Unity Catalog Constraint Template
-- Use this template when creating Gold layer tables with constraints

-- ============================================================================
-- DIMENSION TABLE (SCD Type 1) - Template
-- ============================================================================
CREATE TABLE ${catalog}.${schema}.dim_<dimension_name> (
    -- Surrogate key (PRIMARY KEY)
    <dimension>_key STRING NOT NULL 
        COMMENT 'Surrogate key - PRIMARY KEY',
    
    -- Business key (UNIQUE constraint)
    <business_key> STRING NOT NULL 
        COMMENT 'Business key identifier',
    
    -- Attributes
    <attribute1> STRING,
    <attribute2> STRING,
    
    -- Timestamps
    record_created_timestamp TIMESTAMP,
    record_updated_timestamp TIMESTAMP,
    
    -- PRIMARY KEY on surrogate key
    CONSTRAINT pk_dim_<dimension_name> PRIMARY KEY (<dimension>_key) NOT ENFORCED,
    
    -- UNIQUE constraint on business key
    CONSTRAINT uk_<dimension>_<business_key> UNIQUE (<business_key>) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'layer' = 'gold',
    'scd_type' = '1'
)
COMMENT 'Gold layer <dimension_name> dimension';

-- ============================================================================
-- DIMENSION TABLE (SCD Type 2) - Template
-- ============================================================================
CREATE TABLE ${catalog}.${schema}.dim_<dimension_name> (
    -- Surrogate key (PRIMARY KEY)
    <dimension>_key STRING NOT NULL 
        COMMENT 'Surrogate key (unique per version) - PRIMARY KEY',
    
    -- Business key (no UNIQUE constraint for SCD Type 2)
    <business_key> STRING NOT NULL 
        COMMENT 'Business key - <dimension_name> identifier',
    
    -- Attributes
    <attribute1> STRING,
    <attribute2> STRING,
    
    -- SCD Type 2 fields
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP,
    is_current BOOLEAN NOT NULL,
    
    -- Timestamps
    record_created_timestamp TIMESTAMP,
    record_updated_timestamp TIMESTAMP,
    
    -- PRIMARY KEY on surrogate key
    CONSTRAINT pk_dim_<dimension_name> PRIMARY KEY (<dimension>_key) NOT ENFORCED
    
    -- Note: No UNIQUE constraint on <business_key> for SCD Type 2
    -- (same <business_key> can have multiple versions)
)
USING DELTA
CLUSTER BY AUTO
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'layer' = 'gold',
    'scd_type' = '2'
)
COMMENT 'Gold layer <dimension_name> dimension with SCD Type 2';

-- ============================================================================
-- DATE DIMENSION - Template
-- ============================================================================
CREATE TABLE ${catalog}.${schema}.dim_date (
    -- Surrogate key (PRIMARY KEY, integer format for fast joins)
    date_key INT NOT NULL 
        COMMENT 'Integer YYYYMMDD format - PRIMARY KEY',
    
    -- Natural date (UNIQUE constraint)
    date DATE NOT NULL 
        COMMENT 'Actual date - Business key',
    
    -- Attributes
    year INT,
    month INT,
    month_name STRING,
    day_of_week INT,
    day_of_week_name STRING,
    quarter INT,
    is_weekend BOOLEAN,
    
    record_created_timestamp TIMESTAMP,
    
    -- PRIMARY KEY on surrogate key
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key) NOT ENFORCED,
    
    -- UNIQUE constraint on natural date
    CONSTRAINT uk_date_value UNIQUE (date) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Gold layer date dimension';

-- ============================================================================
-- FACT TABLE - Template
-- ============================================================================
-- IMPORTANT: Only define PRIMARY KEY inline, NOT foreign keys!
-- Foreign keys must be added later via ALTER TABLE after all dimension PKs exist.

CREATE TABLE ${catalog}.${schema}.fact_<fact_name> (
    -- Surrogate foreign key columns (reference dimension PKs)
    <dimension1>_key STRING NOT NULL,
    <dimension2>_key STRING NOT NULL,
    date_key INT NOT NULL,
    
    -- Business keys (for readability, not part of PK/FK)
    <dimension1>_<business_key> STRING NOT NULL,
    <dimension2>_<business_key> STRING NOT NULL,
    transaction_date DATE NOT NULL,
    
    -- Measures
    <measure1> DOUBLE,
    <measure2> INT,
    
    -- Timestamps
    record_created_timestamp TIMESTAMP,
    record_updated_timestamp TIMESTAMP,
    
    -- Composite PRIMARY KEY on surrogate keys (grain of fact table)
    CONSTRAINT pk_fact_<fact_name> 
        PRIMARY KEY (<dimension1>_key, <dimension2>_key, date_key) NOT ENFORCED
    
    -- ❌ DO NOT define FOREIGN KEY constraints here!
    -- Foreign keys must be added via ALTER TABLE after all tables exist.
    -- See scripts/apply_constraints.py for FK application pattern.
)
USING DELTA
CLUSTER BY AUTO
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'layer' = 'gold'
)
COMMENT 'Gold layer <fact_name> fact table';

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS (Apply AFTER all tables exist)
-- ============================================================================
-- Run these ALTER TABLE statements after all dimension and fact tables are created.
-- Order: Dimensions first, then facts.

-- Example FK application (customize for your tables):
-- ALTER TABLE ${catalog}.${schema}.fact_<fact_name>
--     ADD CONSTRAINT fk_<fact>_<dimension1> 
--     FOREIGN KEY (<dimension1>_key) 
--     REFERENCES ${catalog}.${schema}.dim_<dimension1>(<dimension1>_key) NOT ENFORCED;
--
-- ALTER TABLE ${catalog}.${schema}.fact_<fact_name>
--     ADD CONSTRAINT fk_<fact>_<dimension2> 
--     FOREIGN KEY (<dimension2>_key) 
--     REFERENCES ${catalog}.${schema}.dim_<dimension2>(<dimension2>_key) NOT ENFORCED;
--
-- ALTER TABLE ${catalog}.${schema}.fact_<fact_name>
--     ADD CONSTRAINT fk_<fact>_date 
--     FOREIGN KEY (date_key) 
--     REFERENCES ${catalog}.${schema}.dim_date(date_key) NOT ENFORCED;

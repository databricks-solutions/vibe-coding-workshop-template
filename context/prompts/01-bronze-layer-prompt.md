# Bronze Layer Creation Prompt

## 🚀 Quick Start (30 minutes)

**Goal:** Create Bronze layer tables with test data for rapid prototyping

**What You'll Create:**
1. `setup_tables.py` - DDL definitions for all Bronze tables
2. `generate_dimensions.py` - Faker-based dimension data generator
3. `generate_facts.py` - Faker-based fact data generator (with FK integrity)
4. `bronze_setup_job.yml` + `bronze_data_generator_job.yml` - Asset Bundle jobs

**Fast Track:**
```bash
# 1. Deploy setup job
databricks bundle deploy -t dev

# 2. Create tables
databricks bundle run bronze_setup_job -t dev

# 3. Generate data (dimensions → facts in sequence)
databricks bundle run bronze_data_generator_job -t dev
```

**Key Decisions:**
- **Data Source:** Faker (recommended) | Existing tables | External copy
- **Record Counts:** Dimensions: 100-200 | Facts: 1,000-10,000
- **Tables Needed:** 5-10 tables (dimensions + facts)

**Output:** Bronze Delta tables with Change Data Feed enabled, ready for Silver layer testing

📖 **Full guide below** for detailed implementation →

---

## Quick Reference

**Use this prompt when creating a Bronze layer with test/demo data for any Databricks project.**

---

## 📋 Your Requirements (Fill These In First)

**Before using this prompt with AI, decide on your data source approach:**

### Project Information
- **Project Name:** _________________ (e.g., retail_analytics, supply_chain, customer360)
- **Data Source Strategy:** 
  - [ ] **Generate fake data** (Faker - recommended for demos/testing)
  - [ ] **Use existing Bronze tables** (from another schema/catalog)
  - [ ] **Copy from external source** (another workspace, database, CSV files)

### Entity List (5-10 Tables)

|| # | Entity Name | Type | Domain | Has PII | Classification | Primary Key |
||---|------------|------|--------|---------|----------------|-------------|
|| 1 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
|| 2 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
|| 3 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
|| 4 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |
|| 5 | ___________ | [ ] Dim [ ] Fact | _______ | [ ] Yes [ ] No | [ ] Confidential [ ] Internal | ___________ |

**Entity Types:**
- **Dimension:** Master data, slowly changing (customers, products, stores, employees)
- **Fact:** Transactional data, high volume (orders, transactions, events, measurements)

**Domain Examples:**
- Retail: retail, sales, inventory, product, logistics
- Finance: accounting, billing, payments, compliance
- Healthcare: clinical, patient, claims, pharmacy
- Manufacturing: production, quality, maintenance, supply
- HR: employee, recruitment, performance, benefits

**Data Classification:**
- **Confidential:** Contains PII or highly sensitive data (SSN, health records, financial accounts)
- **Internal:** Business data without PII (sales figures, inventory, product data)
- **Public:** Safe for external sharing (marketing content, public product catalog)

### Data Source Details

**Option A: Generate Fake Data (Recommended)**
- **Record Counts:**
  - Dimensions: _______ records each (default: 100-200)
  - Facts: _______ records total (default: 1,000-10,000)
- **Date Range:** Last _____ days/months/years (default: 1 year)
- **Faker Seed:** _______ (for reproducibility, default: 42)

**Option B: Use Existing Bronze Tables**
- **Source Catalog:** _________________
- **Source Schema:** _________________
- **Copy or Reference:** [ ] Copy data [ ] Reference in place

**Option C: Copy from External Source**
- **Source Type:** [ ] CSV Files [ ] External Database [ ] Another Workspace
- **Connection Details:** _________________

### Business Ownership
- **Business Owner Team:** _________________ (e.g., "Sales Operations", "Product Team")
- **Business Owner Email:** _________________ @company.com
- **Technical Owner:** Data Engineering (default)
- **Technical Owner Email:** data-engineering@company.com

---

## Input Required Summary
- Entity list (5-10 tables with schema definitions)
- Data source approach (Faker / Existing / Copy)
- Domain taxonomy and classification
- Record counts for fake data generation

**Output:** 5-10 Bronze Delta tables with realistic test data, Unity Catalog compliance, automatic liquid clustering, and change data feed enabled.

**Time Estimate:** 1-2 hours

---

## Core Philosophy: Quick Setup for Testing & Demos

**⚠️ CRITICAL PRINCIPLE:**

The Bronze layer in this approach is optimized for **testing, demos, and rapid prototyping**:

- ✅ **Quick setup** with realistic test data
- ✅ **Faker data generation** as the primary method
- ✅ **Unity Catalog compliance** (proper governance metadata)
- ✅ **Enable Change Data Feed** for downstream Silver/Gold testing
- ✅ **Automatic liquid clustering** for query optimization
- ✅ **Flexible data sources** (generate, copy, or reference existing)
- ❌ **NOT for production ingestion** (use separate ingestion pipelines for that)

**Why This Matters:**
- Rapid prototyping of Medallion Architecture
- Test Silver/Gold transformations with realistic data
- Demo data pipelines to stakeholders
- Validate data quality rules before production deployment

---

## Step 1: Define Project Structure

### File Structure to Create

```
src/{project}_bronze/
├── __init__.py                # Package initialization
├── setup_tables.py            # Table DDL definitions
├── generate_dimensions.py     # Generate dimension data with Faker
├── generate_facts.py          # Generate fact data with Faker
└── copy_from_source.py        # Optional: Copy from existing source
```

---

## Step 2: Choose Your Data Source Approach

### Approach A: Generate Fake Data with Faker (Recommended)

**Best for:** Demos, testing, rapid prototyping, learning

**Advantages:**
- ✅ No external dependencies
- ✅ Reproducible (seeded random data)
- ✅ Configurable record counts
- ✅ Realistic data patterns
- ✅ PII-safe (no real data)

**Steps:**
1. Define table schemas
2. Create Faker generation functions
3. Generate dimensions first (for FK integrity)
4. Generate facts with references to dimensions

### Approach B: Use Existing Bronze Tables

**Best for:** Testing transformations on real data structures, reusing existing demos

**Advantages:**
- ✅ Real data characteristics
- ✅ No generation time
- ✅ Test on actual schema

**Steps:**
1. Identify source catalog/schema
2. Create tables pointing to existing data (or copy)
3. Add governance metadata
4. Enable Change Data Feed

### Approach C: Copy from External Source

**Best for:** Loading sample data from CSV, external databases, other workspaces

**Advantages:**
- ✅ Use real sample datasets
- ✅ One-time copy operation
- ✅ Can sanitize/transform on copy

**Steps:**
1. Define connection to source
2. Read data with appropriate connector
3. Write to Bronze tables
4. Add governance metadata

---

## Step 3: Table Creation Script

### File: `setup_tables.py`

**Pattern:** Create ONE function per table, call all from `main()`

```python
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
    
    print(f"✓ Schema {catalog}.{schema} ready with Predictive Optimization enabled")


def create_{entity}_table(spark, catalog: str, schema: str):
    """
    Create {entity_display_name} table.
    
    {Entity description - what data it contains, grain, purpose}
    """
    print(f"\nCreating {catalog}.{schema}.bronze_{entity}...")
    
    table_ddl = f"""
        CREATE OR REPLACE TABLE {catalog}.{schema}.bronze_{entity} (
            -- PRIMARY KEY COLUMN(S)
            {pk_column} {pk_type} NOT NULL 
                COMMENT '{PK description - unique identifier for this entity}',
            
            -- BUSINESS COLUMNS (define based on your use case)
            column1 STRING NOT NULL 
                COMMENT '{Column purpose and business meaning}',
            column2 DECIMAL(18, 2) 
                COMMENT '{Column purpose, units, calculation}',
            column3 TIMESTAMP 
                COMMENT '{Column purpose, timezone info}',
            
            -- AUDIT COLUMNS (standard for all Bronze tables)
            ingestion_timestamp TIMESTAMP NOT NULL 
                COMMENT 'Timestamp when record was ingested into Bronze layer',
            source_file STRING 
                COMMENT 'Data source identifier for traceability'
        )
        USING DELTA
        CLUSTER BY AUTO
        COMMENT 'LLM: Bronze layer {entity_type} table for testing/demo purposes. 
            Contains {description}. Generated with Faker for realistic test data. 
            Enables incremental Silver processing via Change Data Feed.'
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.autoOptimize.optimizeWrite' = 'true',
            'delta.autoOptimize.autoCompact' = 'true',
            'layer' = 'bronze',
            'source_system' = 'Faker Test Data Generator',
            'domain' = '{domain}',
            'entity_type' = '{dimension|fact}',
            'contains_pii' = '{true|false}',
            'data_classification' = '{confidential|internal|public}',
            'business_owner' = '{Business Team Name}',
            'technical_owner' = 'Data Engineering',
            'business_owner_email' = '{owner}@company.com',
            'technical_owner_email' = 'data-engineering@company.com',
            'grain' = '{Description of table grain - one row per what?}',
            'data_purpose' = 'testing_demo',
            'is_production' = 'false'
        )
    """
    
    spark.sql(table_ddl)
    print(f"✓ Created {catalog}.{schema}.bronze_{entity}")


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
        create_store_dim_table(spark, catalog, bronze_schema)
        create_product_dim_table(spark, catalog, bronze_schema)
        create_date_dim_table(spark, catalog, bronze_schema)
        # ... more dimensions
        
        # Step 3: Create fact tables
        print("\n--- Creating Fact Tables ---")
        create_transactions_table(spark, catalog, bronze_schema)
        create_inventory_table(spark, catalog, bronze_schema)
        # ... more facts
        
        print("\n" + "=" * 80)
        print("✓ Bronze layer setup completed successfully!")
        print("=" * 80)
        print(f"\nCreated tables in: {catalog}.{bronze_schema}")
        print("\nNext steps:")
        print("  1. Run generate_dimensions.py to populate dimension tables")
        print("  2. Run generate_facts.py to populate fact tables")
        print("  OR")
        print("  3. Run copy_from_source.py to copy from existing data")
        
    except Exception as e:
        print(f"\n❌ Error during Bronze layer setup: {str(e)}")
        raise
        
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

---

## Step 4: Generate Fake Data with Faker

### File: `generate_dimensions.py`

```python
# Databricks notebook source

"""
{Project Name} Bronze Layer - Generate Dimension Data

Generates realistic fake data for Bronze dimension tables using Faker.

Data Characteristics:
- Reproducible (seeded)
- Realistic patterns
- Configurable counts
- PII-safe

Usage:
  databricks bundle run bronze_data_generator_job -t dev
"""

from pyspark.sql import SparkSession
from faker import Faker
import random
from datetime import datetime, timedelta


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    schema = dbutils.widgets.get("schema")
    num_stores = int(dbutils.widgets.get("num_stores"))
    num_products = int(dbutils.widgets.get("num_products"))
    
    print(f"Catalog: {catalog}")
    print(f"Schema: {schema}")
    print(f"Stores to generate: {num_stores}")
    print(f"Products to generate: {num_products}")
    
    return catalog, schema, num_stores, num_products


# Initialize Faker with seed for reproducibility
fake = Faker()
Faker.seed(42)
random.seed(42)


def generate_store_data(spark: SparkSession, catalog: str, schema: str, num_records: int = 100):
    """
    Generate fake store dimension data.
    
    Creates realistic store locations with:
    - Store numbers (unique identifiers)
    - Store names (company + location)
    - Addresses (realistic US addresses)
    - Geographic info (city, state, zip, coordinates)
    - Open/close dates
    """
    print(f"\nGenerating {num_records} store records...")
    
    data = []
    for i in range(num_records):
        store_number = f"ST{str(i+1000).zfill(5)}"
        
        record = {
            "store_number": store_number,
            "store_name": f"{fake.company()} - {fake.city()}",
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "latitude": float(fake.latitude()),
            "longitude": float(fake.longitude()),
            "phone": fake.phone_number(),
            "manager_name": fake.name(),
            "open_date": fake.date_between(start_date="-5y", end_date="-1y"),
            "close_date": None if random.random() > 0.1 else fake.date_between(start_date="-1y", end_date="today"),
            "store_size_sqft": random.randint(1000, 10000),
            "ingestion_timestamp": datetime.now(),
            "source_file": "faker_generated"
        }
        data.append(record)
    
    # Create DataFrame and write to Bronze table
    df = spark.createDataFrame(data)
    table_name = f"{catalog}.{schema}.bronze_store_dim"
    
    df.write.mode("overwrite").saveAsTable(table_name)
    
    print(f"✓ Generated {num_records} store records in {table_name}")
    return df


def generate_product_data(spark: SparkSession, catalog: str, schema: str, num_records: int = 50):
    """
    Generate fake product dimension data.
    
    Creates realistic products with:
    - UPC codes
    - Product descriptions
    - Brand names
    - Categories
    - Pricing
    """
    print(f"\nGenerating {num_records} product records...")
    
    categories = ["Grocery", "Beverage", "Snacks", "Health & Beauty", "Household", "Tobacco"]
    brands = ["BrandA", "BrandB", "BrandC", "BrandD", "BrandE"]
    
    data = []
    for i in range(num_records):
        upc_code = fake.ean13()
        category = random.choice(categories)
        brand = random.choice(brands)
        
        record = {
            "upc_code": upc_code,
            "product_description": f"{brand} {fake.word().title()} {fake.word().title()}",
            "brand": brand,
            "category": category,
            "subcategory": f"{category} - {fake.word().title()}",
            "unit_size": f"{random.randint(1, 64)} oz",
            "pack_size": random.choice([1, 6, 12, 24]),
            "wholesale_price": round(random.uniform(0.50, 20.00), 2),
            "retail_price": round(random.uniform(1.00, 30.00), 2),
            "is_taxable": random.choice([True, False]),
            "is_age_restricted": category == "Tobacco",
            "ingestion_timestamp": datetime.now(),
            "source_file": "faker_generated"
        }
        data.append(record)
    
    # Create DataFrame and write to Bronze table
    df = spark.createDataFrame(data)
    table_name = f"{catalog}.{schema}.bronze_product_dim"
    
    df.write.mode("overwrite").saveAsTable(table_name)
    
    print(f"✓ Generated {num_records} product records in {table_name}")
    return df


def generate_date_dimension(spark: SparkSession, catalog: str, schema: str, 
                            start_date: str = "2020-01-01", end_date: str = "2025-12-31"):
    """
    Generate date dimension for time-based analysis.
    
    Creates complete date dimension with calendar attributes.
    """
    print(f"\nGenerating date dimension from {start_date} to {end_date}...")
    
    date_sql = f"""
        INSERT OVERWRITE {catalog}.{schema}.bronze_date_dim
        SELECT
            date,
            YEAR(date) as year,
            QUARTER(date) as quarter,
            MONTH(date) as month,
            DATE_FORMAT(date, 'MMMM') as month_name,
            WEEKOFYEAR(date) as week_of_year,
            DAYOFWEEK(date) as day_of_week,
            DATE_FORMAT(date, 'EEEE') as day_of_week_name,
            DAY(date) as day_of_month,
            DAYOFYEAR(date) as day_of_year,
            CASE WHEN DAYOFWEEK(date) IN (1, 7) THEN true ELSE false END as is_weekend,
            false as is_holiday,
            CURRENT_TIMESTAMP() as ingestion_timestamp,
            'generated' as source_file
        FROM (
            SELECT EXPLODE(
                SEQUENCE(
                    TO_DATE('{start_date}'),
                    TO_DATE('{end_date}'),
                    INTERVAL 1 DAY
                )
            ) as date
        )
    """
    
    spark.sql(date_sql)
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {catalog}.{schema}.bronze_date_dim").collect()[0].cnt
    
    print(f"✓ Generated {count} date records")


def main():
    """Generate all dimension data."""
    from pyspark.sql import SparkSession
    
    # Get parameters
    catalog, schema, num_stores, num_products = get_parameters()
    
    spark = SparkSession.builder.appName("Bronze Dimension Generator").getOrCreate()
    
    print("=" * 80)
    print("BRONZE DIMENSION DATA GENERATION")
    print("=" * 80)
    
    try:
        # Generate dimensions
        generate_store_data(spark, catalog, schema, num_stores)
        generate_product_data(spark, catalog, schema, num_products)
        generate_date_dimension(spark, catalog, schema)
        
        print("\n" + "=" * 80)
        print("✓ Dimension data generation completed!")
        print("=" * 80)
        print("\nNext step: Run generate_facts.py to populate fact tables")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

### File: `generate_facts.py`

```python
# Databricks notebook source

"""
{Project Name} Bronze Layer - Generate Fact Data

Generates realistic fake transactional data that references dimension tables.

Ensures:
- Referential integrity (FKs point to existing dimension records)
- Realistic patterns (busy days, popular products, seasonal trends)
- Configurable volume

Usage:
  databricks bundle run bronze_data_generator_job -t dev
"""

from pyspark.sql import SparkSession
from faker import Faker
import random
from datetime import datetime, timedelta


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    schema = dbutils.widgets.get("schema")
    num_transactions = int(dbutils.widgets.get("num_transactions"))
    
    print(f"Catalog: {catalog}")
    print(f"Schema: {schema}")
    print(f"Transactions to generate: {num_transactions}")
    
    return catalog, schema, num_transactions


# Initialize Faker with seed
fake = Faker()
Faker.seed(42)
random.seed(42)


def generate_transaction_data(spark: SparkSession, catalog: str, schema: str, num_records: int = 10000):
    """
    Generate fake transaction data with FK references to dimensions.
    
    Creates realistic transactions with:
    - Unique transaction IDs
    - References to stores (FK)
    - References to products (FK)
    - References to dates (FK)
    - Realistic pricing and quantities
    - Some returns (negative quantities)
    """
    print(f"\nGenerating {num_records} transaction records...")
    
    # Load dimension data to ensure FK integrity
    stores_df = spark.table(f"{catalog}.{schema}.bronze_store_dim")
    products_df = spark.table(f"{catalog}.{schema}.bronze_product_dim")
    
    store_numbers = [row.store_number for row in stores_df.select("store_number").collect()]
    products = [(row.upc_code, row.retail_price) for row in products_df.select("upc_code", "retail_price").collect()]
    
    print(f"  Using {len(store_numbers)} stores and {len(products)} products")
    
    # Generate transactions
    data = []
    start_date = datetime.now() - timedelta(days=365)
    
    for i in range(num_records):
        upc_code, retail_price = random.choice(products)
        quantity = random.randint(1, 10) if random.random() > 0.05 else -random.randint(1, 3)  # 5% returns
        
        # Apply discounts randomly
        discount_pct = random.choice([0, 0, 0, 0, 0.10, 0.15, 0.20])  # Most no discount
        discount = round(retail_price * quantity * discount_pct, 2) if quantity > 0 else 0
        
        record = {
            "transaction_id": f"TXN{str(i+100000).zfill(10)}",
            "store_number": random.choice(store_numbers),
            "upc_code": upc_code,
            "transaction_date": (start_date + timedelta(days=random.randint(0, 365))).date(),
            "transaction_time": fake.time(),
            "quantity_sold": quantity,
            "unit_price": retail_price,
            "total_amount": round(retail_price * quantity, 2),
            "discount_amount": discount,
            "final_sales_price": round(retail_price * quantity - discount, 2),
            "payment_method": random.choice(["Cash", "Credit", "Debit", "Mobile"]),
            "loyalty_id": fake.uuid4() if random.random() > 0.4 else None,  # 60% loyalty
            "cashier_id": f"CASH{random.randint(1, 20)}",
            "ingestion_timestamp": datetime.now(),
            "source_file": "faker_generated"
        }
        data.append(record)
    
    # Create DataFrame and write to Bronze table
    df = spark.createDataFrame(data)
    table_name = f"{catalog}.{schema}.bronze_transactions"
    
    df.write.mode("overwrite").saveAsTable(table_name)
    
    print(f"✓ Generated {num_records} transaction records in {table_name}")
    
    # Show summary
    summary_df = spark.sql(f"""
        SELECT 
            COUNT(*) as total_transactions,
            COUNT(DISTINCT store_number) as stores_with_sales,
            COUNT(DISTINCT upc_code) as products_sold,
            SUM(final_sales_price) as total_revenue,
            SUM(quantity_sold) as total_units
        FROM {table_name}
    """)
    
    print("\nTransaction Summary:")
    summary_df.show(truncate=False)


def main():
    """Generate all fact data."""
    from pyspark.sql import SparkSession
    
    # Get parameters
    catalog, schema, num_transactions = get_parameters()
    
    spark = SparkSession.builder.appName("Bronze Fact Generator").getOrCreate()
    
    print("=" * 80)
    print("BRONZE FACT DATA GENERATION")
    print("=" * 80)
    
    try:
        # Generate facts
        generate_transaction_data(spark, catalog, schema, num_transactions)
        
        print("\n" + "=" * 80)
        print("✓ Fact data generation completed!")
        print("=" * 80)
        print("\nBronze layer is ready for Silver processing!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

---

## Step 5: Alternative - Copy from Existing Source

### File: `copy_from_source.py`

```python
# Databricks notebook source

"""
{Project Name} Bronze Layer - Copy from Existing Source

Copies data from an existing source to Bronze layer.

Supported Sources:
- Existing Unity Catalog tables
- External databases
- CSV/Parquet files
- Another Databricks workspace

Usage:
  databricks bundle run bronze_copy_job -t dev
"""

from pyspark.sql import SparkSession


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    bronze_schema = dbutils.widgets.get("bronze_schema")
    source_catalog = dbutils.widgets.get("source_catalog")
    source_schema = dbutils.widgets.get("source_schema")
    
    print(f"Target: {catalog}.{bronze_schema}")
    print(f"Source: {source_catalog}.{source_schema}")
    
    return catalog, bronze_schema, source_catalog, source_schema


def copy_table(spark: SparkSession, 
               source_catalog: str, source_schema: str, source_table: str,
               target_catalog: str, target_schema: str, target_table: str):
    """
    Copy data from source table to target Bronze table.
    
    Preserves schema and data, adds ingestion metadata.
    """
    print(f"\nCopying {source_catalog}.{source_schema}.{source_table}")
    print(f"     -> {target_catalog}.{target_schema}.{target_table}")
    
    # Read source
    source_df = spark.table(f"{source_catalog}.{source_schema}.{source_table}")
    
    # Add ingestion metadata if not exists
    from pyspark.sql.functions import current_timestamp, lit
    
    if "ingestion_timestamp" not in source_df.columns:
        source_df = source_df.withColumn("ingestion_timestamp", current_timestamp())
    
    if "source_file" not in source_df.columns:
        source_df = source_df.withColumn("source_file", lit(f"copied_from_{source_catalog}.{source_schema}.{source_table}"))
    
    # Write to target
    target_full_name = f"{target_catalog}.{target_schema}.{target_table}"
    source_df.write.mode("overwrite").saveAsTable(target_full_name)
    
    # Get count
    count = spark.table(target_full_name).count()
    print(f"✓ Copied {count:,} records")


def main():
    """Copy all tables from source to Bronze."""
    from pyspark.sql import SparkSession
    
    # Get parameters
    catalog, bronze_schema, source_catalog, source_schema = get_parameters()
    
    spark = SparkSession.builder.appName("Bronze Copy from Source").getOrCreate()
    
    print("=" * 80)
    print("BRONZE LAYER - COPY FROM SOURCE")
    print("=" * 80)
    
    try:
        # Define table mappings
        table_mappings = [
            ("source_stores", "bronze_store_dim"),
            ("source_products", "bronze_product_dim"),
            ("source_transactions", "bronze_transactions"),
            # Add more mappings as needed
        ]
        
        for source_table, target_table in table_mappings:
            try:
                copy_table(spark, source_catalog, source_schema, source_table,
                          catalog, bronze_schema, target_table)
            except Exception as e:
                print(f"⚠️  Warning: Could not copy {source_table}: {str(e)}")
        
        print("\n" + "=" * 80)
        print("✓ Copy completed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

---

## Step 6: Asset Bundle Configuration

### File: `resources/bronze_setup_job.yml`

```yaml
resources:
  jobs:
    bronze_setup_job:
      name: "[${bundle.target}] {Project} Bronze Layer - Setup"
      description: "Creates Bronze layer tables for testing/demo"
      
      tasks:
        - task_key: setup_bronze_tables
          notebook_task:
            notebook_path: ../src/{project}_bronze/setup_tables.py
            base_parameters:
              catalog: ${var.catalog}
              bronze_schema: ${var.bronze_schema}
      
      email_notifications:
        on_failure:
          - data-engineering@company.com
      
      tags:
        environment: ${bundle.target}
        layer: bronze
        job_type: setup
        data_purpose: testing_demo
```

### File: `resources/bronze_data_generator_job.yml`

```yaml
resources:
  jobs:
    bronze_data_generator_job:
      name: "[${bundle.target}] {Project} Bronze Layer - Generate Data"
      description: "Generates fake data for Bronze tables using Faker"
      
      environments:
        - environment_key: default
          spec:
            client: "1"
            dependencies:
              - "Faker==22.0.0"
      
      tasks:
        # Task 1: Generate dimension data
        - task_key: generate_dimensions
          environment_key: default
          notebook_task:
            notebook_path: ../src/{project}_bronze/generate_dimensions.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.bronze_schema}
              num_stores: "100"
              num_products: "50"
        
        # Task 2: Generate fact data (depends on dimensions)
        - task_key: generate_facts
          depends_on:
            - task_key: generate_dimensions
          environment_key: default
          notebook_task:
            notebook_path: ../src/{project}_bronze/generate_facts.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.bronze_schema}
              num_transactions: "10000"
      
      tags:
        environment: ${bundle.target}
        layer: bronze
        job_type: data_generation
        data_purpose: testing_demo
```

---

## Implementation Checklist

### Phase 1: Planning (15 min)
- [ ] Identify entities needed (5-10 tables)
- [ ] Choose data source approach (Faker / Existing / Copy)
- [ ] Define record counts for generation
- [ ] Assign domains and classifications

### Phase 2: Table Creation (30 min)
- [ ] Create `src/{project}_bronze/` directory
- [ ] Create `setup_tables.py` with table DDLs
- [ ] Define schema for each table
- [ ] Add governance metadata (TBLPROPERTIES)
- [ ] Use `CLUSTER BY AUTO`

### Phase 3: Data Generation (30-45 min)
- [ ] **Option A (Faker):**
  - [ ] Create `generate_dimensions.py`
  - [ ] Create `generate_facts.py`
  - [ ] Ensure FK integrity (dimensions first)
  - [ ] Add realistic patterns
- [ ] **Option B (Copy):**
  - [ ] Create `copy_from_source.py`
  - [ ] Define table mappings
  - [ ] Test copy operation

### Phase 4: Asset Bundle Configuration (15 min)
- [ ] Create `resources/bronze_setup_job.yml`
- [ ] Create `resources/bronze_data_generator_job.yml`
- [ ] Add Faker dependency if needed
- [ ] Configure job parameters

### Phase 5: Deployment & Validation (15 min)
- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run setup: `databricks bundle run bronze_setup_job`
- [ ] Run generator: `databricks bundle run bronze_data_generator_job`
- [ ] Verify: Check table counts and data quality

---

## Validation Queries

```sql
-- List all Bronze tables
SHOW TABLES IN {catalog}.{bronze_schema};

-- Check record counts
SELECT 
  'bronze_store_dim' as table_name, COUNT(*) as row_count 
FROM {catalog}.{bronze_schema}.bronze_store_dim
UNION ALL
SELECT 'bronze_product_dim', COUNT(*) FROM {catalog}.{bronze_schema}.bronze_product_dim
UNION ALL
SELECT 'bronze_transactions', COUNT(*) FROM {catalog}.{bronze_schema}.bronze_transactions;

-- Verify FK integrity
SELECT 
  'Orphaned transactions (invalid store)' as check_name,
  COUNT(*) as orphan_count
FROM {catalog}.{bronze_schema}.bronze_transactions t
LEFT JOIN {catalog}.{bronze_schema}.bronze_store_dim s 
  ON t.store_number = s.store_number
WHERE s.store_number IS NULL;

-- Data distribution check
SELECT 
  transaction_date,
  COUNT(*) as transaction_count,
  SUM(final_sales_price) as daily_revenue
FROM {catalog}.{bronze_schema}.bronze_transactions
GROUP BY transaction_date
ORDER BY transaction_date DESC
LIMIT 10;
```

---

## Key Principles

### 1. Test Data Quality
- ✅ Realistic patterns (not just random noise)
- ✅ Referential integrity (FKs point to valid records)
- ✅ Business logic (returns are negative, prices make sense)
- ✅ Reproducible (seeded for consistent results)

### 2. Unity Catalog Compliance
- ✅ All tables in Unity Catalog
- ✅ Complete governance metadata
- ✅ Mark as `data_purpose: testing_demo`
- ✅ Mark as `is_production: false`

### 3. Change Data Feed Enabled
- ✅ Required for Silver layer testing
- ✅ `'delta.enableChangeDataFeed' = 'true'`

### 4. Automatic Liquid Clustering
- ✅ `CLUSTER BY AUTO` on all tables
- ❌ Never specify columns manually

---

## Next Steps

After Bronze layer is complete:

1. **Silver Layer:** Use [02-silver-layer-prompt.md](./02-silver-layer-prompt.md)
2. **Verify Data:** Check counts, FK integrity, data patterns
3. **Test Silver DQ:** Ensure data quality rules work with test data
4. **Iterate:** Adjust Faker generation for more realistic patterns

---

## References

### Official Documentation
- [Faker Library](https://faker.readthedocs.io/)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Lake](https://docs.databricks.com/delta/)
- [Asset Bundles](https://docs.databricks.com/dev-tools/bundles/)

### Framework Rules
- [faker-data-generation.mdc](mdc:.cursor/rules/06-faker-data-generation.mdc)
- [databricks-table-properties.mdc](mdc:.cursor/rules/04-databricks-table-properties.mdc)

---

## Summary

**What to Create:**
1. `setup_tables.py` - Table DDL definitions
2. `generate_dimensions.py` - Faker dimension generator
3. `generate_facts.py` - Faker fact generator
4. `copy_from_source.py` - Optional copy utility
5. `bronze_setup_job.yml` - Setup job
6. `bronze_data_generator_job.yml` - Data generation job

**Core Philosophy:** Bronze = Quick test data setup with realistic patterns for demo/testing

**Time Estimate:** 1-2 hours for 5-10 tables with data

**Next Action:** Choose data approach (Faker recommended), create tables, generate data, test Silver layer


# DQX Integration Prompt

## 🚀 Quick Start (3-4 hours for pilot)

**Goal:** Add advanced data quality validation with detailed failure diagnostics

**What is DQX?** Databricks Labs framework for data quality with auto-profiling, detailed diagnostics, and flexible quarantine strategies (beyond DLT expectations).

**What You'll Create:**
1. **Quality Rules Storage** - Delta table or YAML file for DQX rules
2. **DQX Validation Layer** - Apply checks in Silver or Gold pipelines
3. **Quality Metrics Dashboard** - Monitor data quality over time

**Fast Track (Hybrid Approach - Recommended):**
```python
# 1. Install DQX
%pip install dqx

# 2. Define quality checks
from dqx import QualityChecks

qc = QualityChecks(
    catalog="my_catalog",
    schema="my_schema",
    table="silver_transactions",
    output_mode="quarantine"  # drop, mark, or quarantine
)

# 3. Add checks (using correct API function names)
qc = (qc
    .is_not_null("transaction_id", "Primary key must exist")
    .is_not_less_than("final_sales_price", limit=0.01, "Price must be positive")
    .is_in_range("quantity_sold", min_value=-20, max_value=50, "Quantity must be reasonable")
)

# 4. Apply checks
df_validated, df_quarantined = qc.apply_checks_by_metadata_and_split(spark_df)

# 5. Write to Silver
df_validated.write.mode("append").saveAsTable(f"{catalog}.{schema}.silver_transactions")
df_quarantined.write.mode("append").saveAsTable(f"{catalog}.{schema}.silver_transactions_dqx_quarantine")
```

**Integration Strategies:**
1. **Hybrid (Best):** Keep DLT for speed, add DQX for detailed diagnostics in Silver
2. **Gold Pre-Merge:** Validate before MERGE to Gold (catch issues early)
3. **DQX Only:** Replace DLT expectations (more control, slower)

**Critical API Notes:**
- ⚠️ Use `is_not_less_than(column, limit=N)` NOT `has_min(column, value=N)`
- ⚠️ Use `is_in_range(column, min_value=X, max_value=Y)` with int/float (NOT strings)
- ⚠️ Use `apply_checks_by_metadata_and_split()` NOT `apply_checks()`
- ⚠️ Consult [DQX API Docs](https://databrickslabs.github.io/dqx/docs/reference/api/check_funcs/)

**Output:** Enhanced data quality with detailed failure insights, auto-profiling, and quality dashboards

📖 **Full guide below** for detailed integration patterns →

---

## Quick Reference

**Use this prompt when integrating Databricks Labs DQX into your Medallion Architecture.**

**Framework:** Databricks Labs DQX (Data Quality eXtensions)  
**Version:** 0.8.0+  
**Target:** Any Medallion Architecture (Bronze → Silver → Gold)

---

## 📋 Your Requirements (Fill These In First)

**Before integrating DQX, identify:**

### Tables to Enhance with DQX
- **Pilot Table:** _________________ (Start with one Silver table)
- **Priority Tables:** _________________ (2-3 critical tables)
- **Full Rollout Tables:** _________________ (All Silver/Gold tables)

### Quality Requirements
- **Complex Validations:** [ ] Yes [ ] No (If yes, DQX is valuable)
- **Detailed Diagnostics:** [ ] Required [ ] Nice-to-have
- **Regulatory Compliance:** [ ] Yes [ ] No (If yes, audit trail is critical)

### Integration Strategy
- [ ] **Hybrid (Recommended):** Keep DLT for speed, add DQX for diagnostics
- [ ] **DQX Only:** Replace all DLT expectations with DQX
- [ ] **Pilot First:** Test on 1-2 tables before full rollout

---

## Executive Summary

DQX is a Python-based data quality framework from Databricks Labs that provides advanced validation capabilities beyond standard DLT expectations. This guide provides a comprehensive roadmap for integrating DQX into your Medallion Architecture project.

### Key Benefits

✅ **Detailed Failure Diagnostics** - Understand exactly why data quality checks fail  
✅ **Auto-Profiling** - Automatically generate quality rule candidates  
✅ **Flexible Quarantine** - Drop, mark, or flag invalid data  
✅ **Centralized Governance** - Store quality rules in Delta tables  
✅ **Rich Metadata** - Track business ownership and compliance requirements  
✅ **Quality Dashboards** - Built-in visualization for monitoring  

### When to Use DQX

**Use DQX for:**
- Complex business logic validation requiring detailed diagnostics
- Gold layer pre-merge validation to ensure data quality
- Auto-discovering quality rules in new data sources
- Centralized quality rule governance across teams
- Regulatory compliance requiring audit trails

**Continue with DLT Expectations for:**
- Simple critical validations (NOT NULL, > 0)
- Silver layer streaming with built-in DLT integration
- When minimal external dependencies are preferred

---

## Architecture Overview

### Current State: DLT Expectations

```
Bronze → Silver (DLT Expectations) → Gold
           ↓
    Centralized DQ Rules
    (data_quality_rules.py)
           ↓
    Lakehouse Monitoring
    (Custom Metrics)
```

### Future State: Hybrid DLT + DQX

```
Bronze → Silver (DLT + DQX) → Gold (DQX Pre-Validation)
           ↓                      ↓
    DQX Quality Checks      DQX Gold Checks
    (YAML + Delta)          (YAML + Delta)
           ↓                      ↓
    DQX Dashboard          Lakehouse Monitoring
    (Detailed Diagnostics)  (Drift Detection)
```

---

## Installation

### Phase 1: Library Installation (Recommended First Step)

**Add to Asset Bundle:**

```yaml
# resources/silver_dlt_pipeline.yml
resources:
  pipelines:
    silver_dlt_pipeline:
      # ... existing config ...
      
      libraries:
        - notebook:
            path: ../src/{project}_silver/silver_dimensions.py
        - notebook:
            path: ../src/{project}_silver/silver_transactions.py
        - notebook:
            path: ../src/{project}_silver/silver_inventory.py
        
        # ✅ ADD: DQX library dependency
        - pypi:
            package: databricks-labs-dqx==0.8.0
```

**Deploy:**

```bash
databricks bundle deploy -t dev
```

### Phase 2: Workspace Tool (Optional - Advanced Features)

**For profiling workflows and dashboards:**

```bash
# Install DQX tool
databricks labs install dqx

# Configuration prompts:
# - Use serverless? Yes
# - Installation folder: /Users/<your-email>/.dqx
# - Warehouse ID: <your-warehouse-id>

# Verify installation
databricks labs installed

# Open dashboard
databricks labs dqx open-dashboards
```

---

## Implementation Phases

### Phase 1: Silver Layer Pilot (Recommended Starting Point)

**Objective:** Add DQX to one Silver table for diagnostics without disrupting existing DLT expectations.

#### Step 1.1: Create DQX Checks YAML

```yaml
# src/{project}_silver/dqx_checks_transactions.yml
# DQX Quality Checks for silver_transactions
# Complements existing DLT expectations with detailed diagnostics

# Critical checks (error = drops record)
- name: transaction_id_not_null
  criticality: error
  check:
    function: is_not_null_and_not_empty
    arguments:
      column: transaction_id
  metadata:
    check_type: completeness
    layer: silver
    entity: transactions
    business_owner: Revenue Analytics
    data_steward: revenue-stewards@company.com
    business_rule: "Every transaction must have unique identifier"
    failure_impact: "High - Cannot track transaction lineage"

- name: positive_price
  criticality: error
  check:
    function: is_greater_than
    arguments:
      column: final_sales_price
      value: 0
  metadata:
    check_type: validity
    business_rule: "Prices must be positive"
    failure_impact: "High - Invalid financial data"

# Warning checks (warn = logs but doesn't drop)
- name: reasonable_quantity
  criticality: warn
  check:
    function: is_between
    arguments:
      column: quantity_sold
      min_value: -50
      max_value: 100
  metadata:
    check_type: reasonableness
    business_rule: "Quantities outside -50 to 100 are unusual"
    failure_impact: "Medium - Requires investigation but not blocking"

- name: recent_transaction
  criticality: warn
  check:
    function: is_greater_than_or_equal_to
    arguments:
      column: transaction_date
      value: "2020-01-01"
  metadata:
    check_type: temporal_validity
    business_rule: "Transactions should be from 2020 onwards"
```

#### Step 1.2: Create DQX-Enhanced Silver Table

```python
# src/{project}_silver/silver_transactions_dqx.py
"""
Silver transactions with DQX diagnostics.
Pilot table to validate DQX benefits before full rollout.
"""

import dlt
from pyspark.sql.functions import col, current_timestamp
from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.config import FileChecksStorageConfig
from databricks.sdk import WorkspaceClient

# Import existing DQ rules for DLT expectations
from data_quality_rules import (
    get_critical_rules_for_table,
    get_warning_rules_for_table
)

def get_source_table(table_name, source_schema_key="bronze_schema"):
    """Helper to get fully qualified table name."""
    from pyspark.sql import SparkSession
    spark = SparkSession.getActiveSession()
    catalog = spark.conf.get("catalog")
    schema = spark.conf.get(source_schema_key)
    return f"{catalog}.{schema}.{table_name}"

# Initialize DQX engine (once per notebook)
dq_engine = DQEngine(WorkspaceClient())

# Load DQX checks from YAML
dqx_checks = dq_engine.load_checks(
    config=FileChecksStorageConfig(location="dqx_checks_transactions.yml")
)

@dlt.table(
    name="silver_transactions_dqx_pilot",
    comment="""
    PILOT: Silver transactions with hybrid DLT + DQX validation.
    
    Validation Strategy:
    - DLT Expectations: Critical rules for fast enforcement
    - DQX: Detailed diagnostics and flexible warning-level checks
    
    DQX adds these columns:
    - dq_check_result: PASS/FAIL per row
    - dq_check_failures: Array of failed check names
    - dq_check_details: Detailed failure information
    """,
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "layer": "silver",
        "validation_framework": "hybrid_dlt_dqx",
        "pilot_phase": "1",
        "contains_pii": "false"
    },
    cluster_by_auto=True
)
# ✅ Keep existing DLT expectations for critical enforcement
@dlt.expect_all_or_fail(get_critical_rules_for_table("silver_transactions"))
def silver_transactions_dqx_pilot():
    """
    Hybrid validation approach:
    1. DLT expectations enforce critical rules (drops invalid)
    2. DQX adds diagnostic metadata (marks but doesn't drop)
    
    Benefits:
    - Fast critical validation (DLT)
    - Rich diagnostics for debugging (DQX)
    - Flexible warning-level checks (DQX)
    """
    bronze_df = dlt.read_stream(get_source_table("bronze_transactions"))
    
    # Apply DQX checks (adds diagnostic columns)
    dqx_result = dq_engine.apply_checks(
        input_df=bronze_df,
        checks=dqx_checks
    )
    
    # Add processing metadata
    result_df = dqx_result.withColumn("processed_timestamp", current_timestamp())
    
    # DLT expectations will still drop records that fail critical rules
    # But DQX metadata shows why they failed
    return result_df

@dlt.table(
    name="silver_transactions_dqx_diagnostics",
    comment="Diagnostic view showing DQX failure details",
    table_properties={
        "quality": "monitoring",
        "layer": "silver"
    }
)
def silver_transactions_dqx_diagnostics():
    """
    Analysis view for DQX validation results.
    Use this to understand patterns in data quality issues.
    """
    full_df = dlt.read("silver_transactions_dqx_pilot")
    
    # Filter for records with DQX warnings/failures
    diagnostics_df = (
        full_df
        .filter(
            col("dq_check_result") == "FAIL" | 
            col("dq_check_failures").isNotNull()
        )
        .select(
            "transaction_id",
            "store_number",
            "transaction_date",
            "dq_check_result",
            "dq_check_failures",
            "dq_check_details",
            "processed_timestamp"
        )
    )
    
    return diagnostics_df
```

#### Step 1.3: Deploy and Test

```bash
# Deploy bundle with DQX changes
databricks bundle deploy -t dev

# Trigger DLT pipeline
databricks pipelines start-update \
  --pipeline-name "[dev] Silver Layer Pipeline"

# Monitor execution
databricks pipelines list-updates \
  --pipeline-name "[dev] Silver Layer Pipeline"
```

#### Step 1.4: Analyze Results

```sql
-- Query diagnostic table to see DQX insights
SELECT 
  dq_check_result,
  dq_check_failures,
  COUNT(*) as record_count
FROM {catalog}.{schema}.silver_transactions_dqx_diagnostics
GROUP BY dq_check_result, dq_check_failures
ORDER BY record_count DESC;

-- Show detailed failure information
SELECT 
  transaction_id,
  store_number,
  transaction_date,
  dq_check_failures,
  dq_check_details
FROM {catalog}.{schema}.silver_transactions_dqx_diagnostics
LIMIT 10;
```

---

### Phase 2: Quality Checks Storage in Delta

**Objective:** Store DQX checks in Delta table for governance and version control.

#### Step 2.1: Create Checks Storage Script

```python
# src/{project}_gold/store_dqx_checks.py
"""
Store DQX quality checks from YAML into Delta table.
Run as part of gold_table_setup_job.
"""

from pyspark.sql import SparkSession
from datetime import datetime
import argparse
import yaml
import json

def load_checks_from_yaml(yaml_path: str):
    """Load checks from YAML file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def save_checks_to_delta(
    spark: SparkSession,
    checks: list,
    catalog: str,
    schema: str,
    entity: str,
    table_name: str = "dqx_quality_checks"
):
    """
    Save quality checks to Delta table.
    
    Table Schema:
    - check_id: string (unique identifier)
    - check_name: string
    - criticality: string (error|warn)
    - check_function: string
    - target_column: string
    - arguments: string (JSON)
    - metadata: string (JSON)
    - entity: string (source table name)
    - layer: string (bronze|silver|gold)
    - version: int
    - created_timestamp: timestamp
    - created_by: string
    """
    from delta.tables import DeltaTable
    
    checks_table = f"{catalog}.{schema}.{table_name}"
    
    # Convert checks to Delta-friendly format
    check_records = []
    for check in checks:
        record = {
            "check_id": f"{entity}_{check.get('name', '')}",
            "check_name": check.get("name", ""),
            "criticality": check.get("criticality", "warn"),
            "check_function": check["check"]["function"],
            "target_column": check["check"]["arguments"].get("column", ""),
            "arguments": json.dumps(check["check"]["arguments"]),
            "metadata": json.dumps(check.get("metadata", {})),
            "entity": entity,
            "layer": check.get("metadata", {}).get("layer", ""),
            "version": 1,
            "created_timestamp": datetime.now(),
            "created_by": spark.sparkContext.sparkUser()
        }
        check_records.append(record)
    
    # Create DataFrame
    checks_df = spark.createDataFrame(check_records)
    
    # Write to Delta with MERGE
    if spark.catalog.tableExists(checks_table):
        delta_table = DeltaTable.forName(spark, checks_table)
        delta_table.alias("target").merge(
            checks_df.alias("source"),
            "target.check_id = source.check_id"
        ).whenMatchedUpdateAll(
        ).whenNotMatchedInsertAll(
        ).execute()
        
        print(f"✓ Updated {len(check_records)} checks in {checks_table}")
    else:
        # Create table with proper schema
        checks_df.write.format("delta") \
            .mode("overwrite") \
            .option("mergeSchema", "true") \
            .saveAsTable(checks_table)
        
        # Add table properties
        spark.sql(f"""
            ALTER TABLE {checks_table}
            SET TBLPROPERTIES (
                'delta.enableChangeDataFeed' = 'true',
                'layer' = 'gold',
                'entity_type' = 'metadata',
                'purpose' = 'dqx_quality_checks_storage'
            )
        """)
        
        print(f"✓ Created {checks_table} with {len(check_records)} checks")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()
    
    spark = SparkSession.builder.appName("Store DQX Checks").getOrCreate()
    
    try:
        # Load and store Silver transaction checks
        print("Loading Silver transaction checks...")
        silver_tx_checks = load_checks_from_yaml("../src/{project}_silver/dqx_checks_transactions.yml")
        
        save_checks_to_delta(
            spark=spark,
            checks=silver_tx_checks,
            catalog=args.catalog,
            schema=args.schema,
            entity="silver_transactions",
            table_name="dqx_quality_checks"
        )
        
        # Load and store other check files as needed
        # ...
        
        print("\n" + "="*80)
        print("✓ All DQX checks stored successfully!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error storing DQX checks: {str(e)}")
        raise
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
```

#### Step 2.2: Add to Gold Setup Job

```yaml
# resources/gold_table_setup_job.yml
resources:
  jobs:
    gold_table_setup_job:
      name: "[${bundle.target}] Gold Table Setup"
      
      tasks:
        # Existing task
        - task_key: create_gold_tables
          python_task:
            python_file: ../src/{project}_gold/create_gold_tables.py
            parameters:
              - "--catalog=${catalog}"
              - "--gold_schema=${gold_schema}"
        
        # ✅ NEW: Store DQX checks in Delta
        - task_key: store_dqx_checks
          depends_on:
            - task_key: create_gold_tables
          python_task:
            python_file: ../src/{project}_gold/store_dqx_checks.py
            parameters:
              - "--catalog=${catalog}"
              - "--schema=${gold_schema}"
          libraries:
            - pypi:
                package: databricks-labs-dqx==0.8.0
```

---

### Phase 3: Gold Layer Pre-Merge Validation

**Objective:** Use DQX to validate aggregated data before MERGE into Gold layer.

#### Step 3.1: Create Gold Layer Checks

```yaml
# src/{project}_gold/dqx_gold_checks.yml
# DQX checks for Gold layer pre-merge validation

- name: non_negative_revenue
  criticality: error
  check:
    function: is_greater_than_or_equal_to
    arguments:
      column: net_revenue
      value: 0
  metadata:
    check_type: validity
    layer: gold
    entity: fact_sales_daily
    business_rule: "Revenue cannot be negative"
    failure_impact: "Critical - Data integrity issue"

- name: non_negative_units
  criticality: error
  check:
    function: is_greater_than_or_equal_to
    arguments:
      column: units_sold
      value: 0
  metadata:
    check_type: validity
    business_rule: "Net units sold cannot be negative"

- name: positive_transaction_count
  criticality: error
  check:
    function: is_greater_than
    arguments:
      column: transaction_count
      value: 0
  metadata:
    check_type: validity
    business_rule: "Must have at least one transaction"

- name: reasonable_daily_revenue
  criticality: warn
  check:
    function: is_less_than_or_equal_to
    arguments:
      column: net_revenue
      value: 100000
  metadata:
    check_type: reasonableness
    business_rule: "Daily revenue per store-product > $100K is unusual"
    failure_impact: "Low - Requires review but not blocking"
```

#### Step 3.2: Enhance merge_gold_tables.py

```python
# src/{project}_gold/merge_gold_tables.py (enhanced with DQX)

from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.config import FileChecksStorageConfig
from databricks.sdk import WorkspaceClient

def merge_fact_sales_daily(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str
):
    """Merge fact_sales_daily with DQX pre-validation."""
    
    # Initialize DQX
    dq_engine = DQEngine(WorkspaceClient())
    gold_checks = dq_engine.load_checks(
        config=FileChecksStorageConfig(location="../src/{project}_gold/dqx_gold_checks.yml")
    )
    
    # ... existing aggregation logic ...
    daily_sales = (
        transactions
        .groupBy("store_number", "upc_code", "transaction_date")
        .agg(...)
    )
    
    # ✅ DQX PRE-MERGE VALIDATION
    print("\n" + "="*80)
    print("Validating aggregated data with DQX...")
    print("="*80)
    
    validated_df, invalid_df = dq_engine.apply_checks_and_split(
        input_df=daily_sales,
        checks=gold_checks
    )
    
    # Report results
    total_count = daily_sales.count()
    valid_count = validated_df.count()
    invalid_count = invalid_df.count()
    
    print(f"\nValidation Results:")
    print(f"  Total: {total_count}")
    print(f"  Valid: {valid_count} ({valid_count/total_count*100:.1f}%)")
    print(f"  Invalid: {invalid_count} ({invalid_count/total_count*100:.1f}%)")
    
    if invalid_count > 0:
        print(f"\n⚠️ {invalid_count} records failed DQX validation")
        
        # Show failure details
        print("\nTop 10 Failure Details:")
        invalid_df.select(
            "store_number", "upc_code", "transaction_date",
            "net_revenue", "units_sold", "transaction_count",
            "dq_check_failures", "dq_check_details"
        ).show(10, truncate=False)
        
        # Save to quarantine
        quarantine_table = f"{catalog}.{gold_schema}.fact_sales_daily_quarantine"
        invalid_df.write.format("delta").mode("append").saveAsTable(quarantine_table)
        print(f"✓ Saved invalid records to {quarantine_table}")
    
    # Only merge valid records
    if valid_count > 0:
        # ... existing MERGE logic ...
        print(f"✓ Merged {valid_count} valid records")
    else:
        raise ValueError("No valid records to merge!")
```

---

## Success Metrics

### Phase 1 Success Criteria
- [ ] DQX library successfully installed
- [ ] Pilot table deployed with DQX validation
- [ ] Diagnostic table showing failure details
- [ ] No impact on existing DLT pipeline performance
- [ ] Team can query diagnostic information

### Phase 2 Success Criteria
- [ ] Quality checks stored in Delta table
- [ ] Checks include rich metadata
- [ ] History tracking enabled via CDF
- [ ] Documentation updated with governance model

### Phase 3 Success Criteria
- [ ] Gold layer pre-merge validation active
- [ ] Quarantine table capturing invalid aggregates
- [ ] Zero invalid records merging into Gold
- [ ] Diagnostic information available for debugging

---

## Rollback Plan

### If DQX Causes Issues

**Option 1: Disable DQX, Keep DLT**
```python
# Comment out DQX code, keep existing DLT expectations
# @dlt.expect_all_or_fail(...)  # Keep this
def silver_transactions():
    # return dq_engine.apply_checks(...)  # Comment out DQX
    return dlt.read_stream(...)  # Back to standard flow
```

**Option 2: Remove DQX Dependency**
```yaml
# resources/silver_dlt_pipeline.yml
libraries:
  # - pypi:
  #     package: databricks-labs-dqx==0.8.0  # Comment out
```

**Option 3: Full Rollback**
```bash
# Restore previous version
git checkout HEAD~1 -- resources/ src/
databricks bundle deploy -t dev
```

---

## Best Practices

### 1. Start Small
- Pilot with one table first
- Validate benefits before expanding
- Keep existing DLT expectations during transition

### 2. Hybrid Approach
- Use DLT for critical enforcement (fast, built-in)
- Use DQX for diagnostics and warnings (detailed, flexible)
- Don't duplicate logic between both

### 3. Metadata is Key
- Add business context to every check
- Include failure impact and remediation steps
- Tag checks with ownership and compliance info

### 4. Monitor Performance
- Track DQX overhead in pipeline execution time
- Optimize check definitions if needed
- Consider limiting DQX to critical paths only

### 5. Governance
- Store checks in Delta for audit trail
- Version control YAML check definitions
- Document check rationale and ownership

---

## Troubleshooting

### Issue: DQX Installation Fails

**Error:** `ModuleNotFoundError: No module named 'databricks.labs.dqx'`

**Solution:**
```python
# Ensure library is installed and kernel restarted
%pip install databricks-labs-dqx==0.8.0
dbutils.library.restartPython()
```

### Issue: YAML Loading Fails

**Error:** `FileNotFoundError: dqx_checks.yml`

**Solution:**
```python
# Use absolute workspace path
from databricks.labs.dqx.config import FileChecksStorageConfig

# Wrong:
# config=FileChecksStorageConfig(location="dqx_checks.yml")

# Correct:
config=FileChecksStorageConfig(
    location="/Workspace/Users/<email>/<ProjectName>/src/{project}_silver/dqx_checks.yml"
)
```

### Issue: DQX Slows Pipeline

**Symptom:** Pipeline execution time increased significantly

**Solution:**
```python
# Limit DQX to critical tables or specific checks
# Don't apply to every table unnecessarily

# Option 1: Only use DQX for complex validations
# Option 2: Use DQX in batch jobs, not streaming
# Option 3: Reduce number of checks
```

---

## Next Steps

1. ✅ Review this guide with team
2. ✅ Complete Phase 1 pilot implementation
3. ✅ Analyze diagnostic results from pilot
4. ✅ Decide on Phase 2/3 adoption
5. ✅ Update documentation and training materials

---

## References

- [DQX Official Documentation](https://databrickslabs.github.io/dqx/)
- [DQX GitHub Repository](https://github.com/databrickslabs/dqx)
- [Cursor Rule: dqx-patterns.mdc](../../.cursor/rules/dqx-patterns.mdc)
- [Existing DQ Patterns](./silver/DQ_QUICKREF.md)






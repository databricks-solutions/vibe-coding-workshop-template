# DQX Implementation Roadmap

## Architecture Overview

### Current State: DLT Expectations Only

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

## Phase 1: Silver Layer Pilot (3-4 hours)

**Objective:** Add DQX to one Silver table for diagnostics without disrupting existing DLT expectations.

### Step 1.1: Install DQX

**For DLT/Lakeflow Pipelines:**
```yaml
# resources/silver_dlt_pipeline.yml
resources:
  pipelines:
    silver_dlt_pipeline:
      libraries:
        - notebook:
            path: ../src/company_silver/silver_transactions.py
        # Add DQX library dependency for DLT
        - pypi:
            package: databricks-labs-dqx>=0.12.0
```

**For Serverless Jobs (non-DLT):**
```yaml
# resources/silver_dq_job.yml
resources:
  jobs:
    silver_dq_job:
      # CRITICAL: Environment-level for serverless
      environments:
        - environment_key: default
          spec:
            dependencies:
              - "databricks-labs-dqx>=0.12.0"
      tasks:
        - task_key: apply_dqx_checks
          environment_key: default
          notebook_task:
            notebook_path: ../src/company_silver/apply_dqx_checks.py
```

### Step 1.2: Create DQX Checks YAML

```yaml
# src/company_silver/dqx_checks_transactions.yml

# Critical checks (error = quarantines record)
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
    business_rule: "Every transaction must have unique identifier"

- name: non_negative_price
  criticality: error
  check:
    function: is_not_less_than
    arguments:
      column: final_sales_price
      limit: 0
  metadata:
    check_type: validity
    business_rule: "Prices must be non-negative"

# Warning checks (warn = logs but doesn't quarantine)
- name: reasonable_quantity
  criticality: warn
  check:
    function: is_in_range
    arguments:
      column: quantity_sold
      min_limit: -50
      max_limit: 100
  metadata:
    check_type: reasonableness
    business_rule: "Quantities outside -50 to 100 are unusual"

- name: recent_transaction
  criticality: warn
  check:
    function: is_not_less_than
    arguments:
      column: transaction_date
      limit: "2020-01-01"
  metadata:
    check_type: temporal_validity
    business_rule: "Transactions should be from 2020 onwards"
```

### Step 1.3: Create DQX-Enhanced Silver Table (DLT)

```python
# src/company_silver/silver_transactions_dqx.py
import dlt
from databricks.labs.dqx.engine import DQEngine
from databricks.sdk import WorkspaceClient

# Initialize DQX engine (once per notebook)
dq_engine = DQEngine(WorkspaceClient())

# Load checks from YAML (metadata format)
import yaml
with open("dqx_checks_transactions.yml") as f:
    dqx_checks = yaml.safe_load(f)

@dlt.view
def bronze_dq_check():
    """Apply DQX checks to Bronze data, producing diagnostic columns."""
    df = dlt.read_stream("bronze_transactions")
    return dq_engine.apply_checks_by_metadata(df, dqx_checks)

@dlt.table(
    name="silver_transactions",
    comment="Silver transactions - records passing all DQX error-level checks",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "validation_framework": "dqx",
    },
    cluster_by_auto=True
)
def silver_transactions():
    """Only valid records (no DQX diagnostic columns)."""
    df = dlt.read_stream("bronze_dq_check")
    return dq_engine.get_valid(df)

@dlt.table(
    name="silver_transactions_quarantine",
    comment="Quarantine: records that failed DQX error-level checks with diagnostics",
    table_properties={
        "quality": "quarantine",
        "layer": "silver",
        "validation_framework": "dqx",
    },
    cluster_by_auto=True
)
def silver_transactions_quarantine():
    """Failed records with diagnostic columns for debugging."""
    df = dlt.read_stream("bronze_dq_check")
    return dq_engine.get_invalid(df)
```

### Step 1.4: Deploy and Test

```bash
databricks bundle deploy -t dev
databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline"
```

### Step 1.5: Analyze Results

```sql
-- Query quarantine table for failure diagnostics
SELECT
  _error,
  _warning,
  COUNT(*) as record_count
FROM catalog.schema.silver_transactions_quarantine
GROUP BY _error, _warning
ORDER BY record_count DESC;
```

---

## Phase 2: Quality Checks Storage in Delta (1-2 hours)

**Objective:** Store DQX checks in Delta table for centralized governance and history.

### Step 2.1: Store Checks Using DQEngine

```python
# src/company_gold/store_dqx_checks.py
"""Store DQX quality checks from YAML into Delta/Lakebase table."""

from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.config import TableChecksStorageConfig
from databricks.sdk import WorkspaceClient
import yaml

def store_checks(catalog: str, schema: str):
    dq_engine = DQEngine(WorkspaceClient())

    # Load checks from YAML
    with open("dqx_checks_transactions.yml") as f:
        checks = yaml.safe_load(f)

    # Save to Delta table using official DQEngine method
    checks_table = f"{catalog}.{schema}.dqx_quality_checks"
    dq_engine.save_checks(
        checks,
        config=TableChecksStorageConfig(
            location=checks_table,
            run_config_name="silver_transactions",
            mode="overwrite"
        )
    )
    print(f"Saved {len(checks)} checks to {checks_table}")
```

### Step 2.2: Add to Asset Bundle Job

```yaml
# resources/gold_table_setup_job.yml
resources:
  jobs:
    gold_table_setup_job:
      environments:
        - environment_key: default
          spec:
            dependencies:
              - "databricks-labs-dqx>=0.12.0"
      tasks:
        - task_key: create_gold_tables
          environment_key: default
          notebook_task:
            notebook_path: ../src/company_gold/create_gold_tables.py
        - task_key: store_dqx_checks
          depends_on:
            - task_key: create_gold_tables
          environment_key: default
          notebook_task:
            notebook_path: ../src/company_gold/store_dqx_checks.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
```

---

## Phase 3: Gold Layer Pre-Merge Validation (2-3 hours)

**Objective:** Use DQX to validate aggregated data before MERGE into Gold layer.

### Step 3.1: Create Gold Layer Checks

```yaml
# src/company_gold/dqx_gold_checks.yml
- name: non_negative_revenue
  criticality: error
  check:
    function: is_not_less_than
    arguments:
      column: net_revenue
      limit: 0
  metadata:
    check_type: validity
    layer: gold
    entity: fact_sales_daily
    business_rule: "Revenue cannot be negative"

- name: non_negative_units
  criticality: error
  check:
    function: is_not_less_than
    arguments:
      column: units_sold
      limit: 0
  metadata:
    check_type: validity
    business_rule: "Net units sold cannot be negative"

- name: reasonable_daily_revenue
  criticality: warn
  check:
    function: is_not_greater_than
    arguments:
      column: net_revenue
      limit: 100000
  metadata:
    check_type: reasonableness
    business_rule: "Daily revenue per store-product > $100K is unusual"
```

### Step 3.2: Add DQX Pre-Merge Validation

See `references/integration-guide.md` Pattern 3 for the complete Gold layer pre-merge validation pattern with quarantine and merge logic.

---

## Success Metrics

### Phase 1
- [ ] DQX library installed in DLT pipeline
- [ ] Pilot Silver table deployed with DQX validation
- [ ] Quarantine table showing failure diagnostics
- [ ] No impact on existing DLT pipeline performance
- [ ] Team can query diagnostic information

### Phase 2
- [ ] Quality checks stored in Delta table via `save_checks()`
- [ ] Checks include rich metadata (business_rule, failure_impact)
- [ ] History tracking enabled via CDF
- [ ] Documentation updated with governance model

### Phase 3
- [ ] Gold layer pre-merge validation active
- [ ] Quarantine table capturing invalid aggregates
- [ ] Zero invalid records merging into Gold
- [ ] Diagnostic information available for debugging

---

## Rollback Plan

### Option 1: Disable DQX, Keep DLT

```python
# Revert to standard DLT without DQX
@dlt.table(...)
@dlt.expect_all_or_fail(get_critical_rules_for_table("silver_data"))
def silver_data():
    return dlt.read_stream("bronze_data")  # No DQX
```

### Option 2: Remove DQX Dependency

```yaml
# resources/silver_dlt_pipeline.yml
libraries:
  # - pypi:
  #     package: databricks-labs-dqx>=0.12.0  # Comment out
```

### Option 3: Full Git Rollback

```bash
git checkout HEAD~1 -- resources/ src/
databricks bundle deploy -t dev
```

---

## Best Practices

### 1. Start Small
- Pilot with one table first
- Validate benefits before expanding
- Keep existing DLT expectations during transition

### 2. Hybrid Approach (Recommended)
- Use DLT expectations for critical enforcement (fast, built-in)
- Use DQX for diagnostics, warnings, and complex validation (detailed, flexible)
- Don't duplicate the same rule in both DLT and DQX

### 3. Metadata is Key
- Add business context to every check (`business_rule`, `failure_impact`)
- Include ownership and compliance info
- Tag checks with `layer`, `entity`, `domain`

### 4. Monitor Performance
- Track DQX overhead in pipeline execution time
- Consider limiting DQX to critical paths for streaming
- Use `is_data_fresh` to detect stale data from delayed pipelines

### 5. Version Compatibility
- Pin to a specific DQX version in production (e.g., `==0.12.0`)
- Use `>=0.12.0` during development for latest features
- Review [CHANGELOG](https://github.com/databrickslabs/dqx/blob/main/CHANGELOG.md) for breaking changes before upgrading

### 6. Governance
- Store checks in Delta table for audit trail
- Version control YAML check definitions alongside code
- Document check rationale and ownership in metadata

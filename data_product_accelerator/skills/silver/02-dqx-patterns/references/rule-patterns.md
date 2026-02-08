# DQX Rule Definition Patterns

## Pattern 1: YAML Configuration (Declarative)

**Best for:** Version-controlled, reusable check definitions

```yaml
# src/company_silver/dqx_checks.yml

# ── Null/Empty Checks ────────────────────────────────────────────────
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

- name: store_number_not_null
  criticality: error
  check:
    function: is_not_null
    arguments:
      column: store_number
  metadata:
    check_type: referential_integrity

# ── Comparison Checks (use 'limit' parameter) ────────────────────────
- name: non_negative_price
  criticality: error
  check:
    function: is_not_less_than  # column >= limit
    arguments:
      column: final_sales_price
      limit: 0
  metadata:
    check_type: validity
    business_rule: "Prices must be non-negative"

# ── Strict Greater-Than (use sql_expression) ─────────────────────────
# NOTE: There is no 'is_greater_than' function in DQX.
# Use sql_expression for strict comparisons (> instead of >=).
- name: positive_price
  criticality: error
  check:
    function: sql_expression
    arguments:
      expression: "final_sales_price > 0"
      columns:
        - final_sales_price
  metadata:
    check_type: validity
    business_rule: "Prices must be strictly positive"

# ── Range Checks (use 'min_limit'/'max_limit') ──────────────────────
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
    business_rule: "Quantities outside range are unusual"

# ── Date Checks ──────────────────────────────────────────────────────
- name: valid_transaction_date
  criticality: error
  check:
    function: is_not_less_than
    arguments:
      column: transaction_date
      limit: "2020-01-01"
  metadata:
    check_type: temporal_validity

# ── SQL Expression (complex business logic) ──────────────────────────
- name: discount_within_policy
  criticality: error
  check:
    function: sql_expression
    arguments:
      expression: "(multi_unit_discount + coupon_discount + loyalty_discount) <= final_sales_price"
      columns:
        - multi_unit_discount
        - coupon_discount
        - loyalty_discount
        - final_sales_price
  metadata:
    check_type: business_logic
    business_rule: "Total discounts cannot exceed sale price"

# ── Regex Pattern Match ──────────────────────────────────────────────
- name: valid_email_format
  criticality: warn
  check:
    function: regex_match
    arguments:
      column: customer_email
      regex: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
  metadata:
    check_type: format_validation
    business_rule: "Email must be in valid format"

# ── Data Freshness (added 0.8.0) ────────────────────────────────────
- name: data_not_stale
  criticality: warn
  check:
    function: is_data_fresh
    arguments:
      column: updated_timestamp
      max_age_minutes: 1440  # 24 hours
  metadata:
    check_type: freshness
    business_rule: "Data should be updated within 24 hours"

# ── List Membership (use 'allowed' parameter) ────────────────────────
- name: valid_status
  criticality: error
  check:
    function: is_in_list
    arguments:
      column: order_status
      allowed: ["pending", "shipped", "delivered", "cancelled"]
      case_sensitive: false
  metadata:
    check_type: referential_integrity

# ── Equality Check (use 'value' parameter, added 0.9.1) ─────────────
- name: expected_currency
  criticality: warn
  check:
    function: is_equal_to
    arguments:
      column: currency_code
      value: "USD"
  metadata:
    check_type: validity
    business_rule: "Expected currency is USD"
```

---

## Pattern 2: Python Programmatic Definition

**Best for:** Dynamic rule generation, conditional logic

```python
# src/company_silver/dqx_checks_generator.py
from databricks.labs.dqx import check_funcs
from databricks.labs.dqx.rule import DQRowRule, DQDatasetRule

def get_silver_transaction_checks():
    """Generate DQX checks programmatically."""
    checks = []

    # Row-level checks
    checks.extend([
        DQRowRule(
            name="transaction_id_not_null",
            criticality="error",
            check_func=check_funcs.is_not_null_and_not_empty,
            column="transaction_id",
            user_metadata={"check_type": "completeness"}
        ),
        DQRowRule(
            name="non_negative_price",
            criticality="error",
            check_func=check_funcs.is_not_less_than,
            column="final_sales_price",
            limit=0,
            user_metadata={"check_type": "validity"}
        ),
        DQRowRule(
            name="reasonable_quantity",
            criticality="warn",
            check_func=check_funcs.is_in_range,
            column="quantity_sold",
            min_limit=-50,
            max_limit=100,
            user_metadata={"check_type": "reasonableness"}
        ),
    ])

    # Dataset-level checks
    checks.extend([
        DQDatasetRule(
            name="unique_transaction_ids",
            criticality="error",
            check_func=check_funcs.is_unique,
            columns=["transaction_id"],
            user_metadata={"check_type": "uniqueness"}
        ),
        DQDatasetRule(
            name="min_daily_records",
            criticality="warn",
            check_func=check_funcs.is_aggr_not_less_than,
            column="transaction_id",
            limit=1000,
            check_func_kwargs={"aggr_type": "count"},
            user_metadata={"check_type": "volume"}
        ),
    ])

    # For-each-column pattern (apply same check to multiple columns)
    for col_name in ["store_number", "upc_code", "transaction_date"]:
        checks.append(
            DQRowRule(
                name=f"{col_name}_not_null",
                criticality="error",
                check_func=check_funcs.is_not_null,
                column=col_name,
                user_metadata={"check_type": "completeness"}
            )
        )

    return checks

def get_dimension_checks(dim_name: str, key_column: str):
    """Reusable dimension check generator."""
    return [
        DQRowRule(
            name=f"{key_column}_not_null",
            criticality="error",
            check_func=check_funcs.is_not_null_and_not_empty,
            column=key_column,
            user_metadata={"dimension": dim_name}
        ),
        DQDatasetRule(
            name=f"unique_{key_column}",
            criticality="error",
            check_func=check_funcs.is_unique,
            columns=[key_column],
            user_metadata={"dimension": dim_name}
        ),
    ]
```

---

## Pattern 3: Dataset-Level Checks

### Foreign Key (Referential Integrity)

```yaml
# Gold layer: verify store_id exists in dim_store
- name: valid_store_reference
  criticality: error
  check:
    function: foreign_key
    arguments:
      columns:
        - store_id
      ref_columns:
        - store_id
      ref_table: catalog.gold_schema.dim_store
  metadata:
    check_type: referential_integrity
    business_rule: "Every transaction must reference a valid store"
```

### Outlier Detection (MAD method, added 0.12.0)

```yaml
- name: no_revenue_outliers
  criticality: warn
  check:
    function: has_no_outliers
    arguments:
      column: net_revenue
  metadata:
    check_type: anomaly_detection
    business_rule: "Revenue values should not be statistical outliers"
```

### Aggregation Checks

```yaml
# Ensure minimum daily record count
- name: min_daily_transactions
  criticality: warn
  check:
    function: is_aggr_not_less_than
    arguments:
      column: transaction_id
      limit: 100
      aggr_type: count
      group_by:
        - store_number
        - transaction_date
  metadata:
    check_type: volume
    business_rule: "Each store should have >= 100 daily transactions"

# Ensure total revenue doesn't exceed threshold
- name: reasonable_total_revenue
  criticality: warn
  check:
    function: is_aggr_not_greater_than
    arguments:
      column: net_revenue
      limit: 10000000
      aggr_type: sum
  metadata:
    check_type: reasonableness
```

### SQL Query (Custom Logic)

```yaml
# Dataset-level: verify row counts match expected
- name: row_count_matches_source
  criticality: warn
  check:
    function: sql_query
    arguments:
      query: "SELECT CASE WHEN COUNT(*) > 0 THEN true ELSE false END AS condition FROM input_view"
  metadata:
    check_type: completeness
```

---

## Pattern 4: Delta Table Storage

**Use `save_checks()` and `load_checks()` from DQEngine (recommended since 0.8.0):**

```python
from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.config import TableChecksStorageConfig
from databricks.sdk import WorkspaceClient

dq_engine = DQEngine(WorkspaceClient())

# Save checks to Delta table
dq_engine.save_checks(
    checks,  # list of dicts or DQRule objects
    config=TableChecksStorageConfig(
        location="catalog.schema.dqx_quality_checks",
        run_config_name="silver_transactions",
        mode="overwrite"  # Replaces existing checks for this run_config
    )
)

# Load checks from Delta table
loaded_checks = dq_engine.load_checks(
    config=TableChecksStorageConfig(
        location="catalog.schema.dqx_quality_checks",
        run_config_name="silver_transactions"
    )
)
```

---

## Pattern 5: Rich Metadata

```yaml
- name: transaction_id_not_null
  criticality: error
  check:
    function: is_not_null_and_not_empty
    arguments:
      column: transaction_id
  metadata:
    # Classification
    check_type: completeness
    check_category: data_integrity
    # Ownership
    business_owner: Revenue Analytics Team
    data_steward: revenue-stewards@company.com
    # Context
    layer: silver
    entity: transactions
    domain: sales
    # Business rules
    business_rule: "Every transaction must have a unique identifier"
    failure_impact: "High - Cannot track transaction lineage"
    remediation: "Check source POS system for ID generation issues"
    # Compliance
    regulatory_requirement: "SOX compliance - transaction traceability"
    tags:
      - critical
      - financial_reporting
```

---

## Pattern 6: Custom Check Functions

```python
# src/company_silver/custom_checks.py
from pyspark.sql import Column
from pyspark.sql.functions import col, length

def is_valid_upc(column_name: str) -> Column:
    """Check if UPC code is valid (12-14 digits)."""
    upc_length = length(col(column_name))
    return (upc_length >= 12) & (upc_length <= 14) & col(column_name).rlike(r'^\d+$')

# Use custom checks with DQRowRule
from databricks.labs.dqx.rule import DQRowRule

custom_checks = [
    DQRowRule(
        name="valid_upc_format",
        criticality="error",
        check_func=is_valid_upc,
        column="upc_code",
        user_metadata={"check_type": "format_validation", "custom": True}
    ),
]
```

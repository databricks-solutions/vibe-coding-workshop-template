"""
Data generation utility for Bronze layer testing.

Generates realistic synthetic data with:
- Non-linear distributions (log-normal, exponential, weighted categorical)
- Temporal patterns (weekday/weekend, holidays, seasonality, event spikes)
- Row coherence (tier → amount → priority → resolution_time → CSAT)
- Weighted sampling (Enterprise generates 5x more activity than Free)
- Configurable corruption mapped to DLT expectations
- Seeded reproducibility (numpy + Faker)

Usage:
    - As Databricks notebook: parameters via dbutils.widgets.get()
    - Template: copy and customize for your domain
"""

import random
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from faker import Faker

try:
    import holidays
    HOLIDAYS_AVAILABLE = True
except ImportError:
    HOLIDAYS_AVAILABLE = False


# =============================================================================
# CONFIGURATION (customize per project)
# =============================================================================
SEED = 42

# Dynamic date range: last 6 months from today
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# Optional: event spike within the date range
INCIDENT_END = END_DATE - timedelta(days=21)
INCIDENT_START = INCIDENT_END - timedelta(days=10)

# Holiday calendar (if holidays library available)
if HOLIDAYS_AVAILABLE:
    US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])
else:
    US_HOLIDAYS = set()


# =============================================================================
# SETUP: Seed for reproducibility
# =============================================================================
np.random.seed(SEED)
Faker.seed(SEED)
random.seed(SEED)
fake = Faker()


# =============================================================================
# PARAMETER HANDLING
# =============================================================================
def get_parameters() -> Tuple[str, str, int, float]:
    """
    Get parameters from notebook widgets (DABs) or defaults.

    Returns:
        Tuple of (catalog, schema, num_records, corruption_rate)
    """
    try:
        # Databricks notebook mode (via notebook_task + base_parameters)
        catalog = dbutils.widgets.get("catalog")  # noqa: F821
        schema = dbutils.widgets.get("schema")  # noqa: F821
        num_records = int(dbutils.widgets.get("num_records"))  # noqa: F821
        corruption_rate = float(dbutils.widgets.get("corruption_rate"))  # noqa: F821
    except Exception:
        # Local development defaults
        catalog = "default_catalog"
        schema = "default_schema"
        num_records = 1000
        corruption_rate = 0.05

    print(f"Parameters: catalog={catalog}, schema={schema}, "
          f"num_records={num_records}, corruption_rate={corruption_rate}")
    return catalog, schema, num_records, corruption_rate


# =============================================================================
# TEMPORAL PATTERNS
# =============================================================================
def get_daily_multiplier(date: datetime, us_holidays=US_HOLIDAYS) -> float:
    """
    Calculate realistic daily volume multiplier.

    Combines weekday/weekend, holidays, Q4 seasonality, and random noise.

    Args:
        date: The date to calculate multiplier for
        us_holidays: Holiday calendar set

    Returns:
        Multiplier (e.g., 0.3 for holiday, 1.0 for normal weekday)
    """
    multiplier = 1.0

    # Weekend drop (60% of weekday volume)
    if date.weekday() >= 5:
        multiplier *= 0.6

    # Holiday drop (30% of normal)
    if date in us_holidays:
        multiplier *= 0.3

    # Q4 seasonality (gradually increases Oct-Dec)
    multiplier *= 1 + 0.15 * (date.month - 6) / 6

    # Random daily noise (±10%)
    multiplier *= np.random.normal(1, 0.1)

    return max(0.1, multiplier)


def get_daily_multiplier_with_spike(
    date: datetime,
    spike_start: datetime = INCIDENT_START,
    spike_end: datetime = INCIDENT_END,
    spike_factor: float = 3.0,
    us_holidays=US_HOLIDAYS,
) -> float:
    """Daily multiplier including event spike period."""
    multiplier = get_daily_multiplier(date, us_holidays)

    if spike_start <= date <= spike_end:
        multiplier *= spike_factor

    return multiplier


# =============================================================================
# DIMENSION DATA GENERATION
# =============================================================================
def generate_dimension_data(
    entity_type: str,
    num_records: int,
    corruption_rate: float = 0.0,
    locale: str = "en_US",
) -> pd.DataFrame:
    """
    Generate dimension data with realistic distributions and optional corruption.

    Args:
        entity_type: Type of dimension (e.g., 'customer', 'product', 'store')
        num_records: Number of records to generate
        corruption_rate: Percentage of records to intentionally corrupt (0.0 to 1.0)
        locale: Faker locale (default: 'en_US')

    Returns:
        pandas DataFrame of dimension records
    """
    fake_local = Faker(locale)
    records = []

    print(f"\nGenerating {num_records} {entity_type} records "
          f"(corruption rate: {corruption_rate * 100}%)")

    for i in range(num_records):
        record = _generate_valid_dimension_record(fake_local, entity_type, i + 1)

        if random.random() < corruption_rate:
            record = _apply_dimension_corruption(record, entity_type)

        records.append(record)

    return pd.DataFrame(records)


def _generate_valid_dimension_record(
    fake: Faker, entity_type: str, entity_id: int
) -> Dict:
    """Generate a valid dimension record with realistic distributions."""
    if entity_type == "customer":
        # Tier uses weighted distribution (not equal)
        tier = np.random.choice(
            ["Free", "Pro", "Enterprise"], p=[0.60, 0.30, 0.10]
        )
        # ARR correlates with tier (row coherence)
        arr_params = {"Enterprise": (11, 0.5), "Pro": (8, 0.6), "Free": (0, 0)}
        mean, sigma = arr_params[tier]
        arr = round(np.random.lognormal(mean, sigma), 2) if mean > 0 else 0.0

        return {
            "customer_id": entity_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zipcode": fake.zipcode(),
            "tier": tier,
            "arr": arr,
            "region": np.random.choice(
                ["North", "South", "East", "West"], p=[0.40, 0.25, 0.20, 0.15]
            ),
            "created_date": fake.date_between(start_date="-2y", end_date="-6m"),
        }
    elif entity_type == "product":
        category = np.random.choice(
            ["electronics", "clothing", "home", "sports", "books"],
            p=[0.30, 0.25, 0.20, 0.15, 0.10],
        )
        # Price uses log-normal, varies by category (row coherence)
        price_params = {
            "electronics": (5.5, 0.9),
            "clothing": (3.8, 0.7),
            "home": (4.5, 0.8),
            "sports": (4.0, 0.6),
            "books": (2.8, 0.5),
        }
        mean, sigma = price_params[category]
        price = round(np.random.lognormal(mean, sigma), 2)

        return {
            "product_id": entity_id,
            "product_name": fake.catch_phrase(),
            "category": category,
            "price": price,
            "sku": fake.ean13(),
            "created_date": fake.date_between(start_date="-1y", end_date="today"),
        }
    else:
        raise ValueError(f"Unknown entity_type: {entity_type}. "
                         f"Supported: 'customer', 'product'")


# =============================================================================
# FACT DATA GENERATION (with weighted sampling + temporal patterns)
# =============================================================================
def generate_fact_data(
    dimension_dfs: Dict[str, pd.DataFrame],
    num_records: int,
    corruption_rate: float = 0.0,
    use_temporal_patterns: bool = True,
    locale: str = "en_US",
) -> pd.DataFrame:
    """
    Generate fact data with referential integrity, weighted sampling,
    temporal patterns, and row coherence.

    Args:
        dimension_dfs: Dict of dimension DataFrames keyed by entity type
                       (e.g., {'customer': customers_pdf, 'product': products_pdf})
        num_records: Number of records to generate
        corruption_rate: Percentage of records to intentionally corrupt (0.0 to 1.0)
        use_temporal_patterns: Whether to distribute records with temporal patterns
        locale: Faker locale (default: 'en_US')

    Returns:
        pandas DataFrame of fact records
    """
    fake_local = Faker(locale)

    print(f"\nGenerating {num_records} fact records "
          f"(corruption rate: {corruption_rate * 100}%)")

    # Build weighted lookup from customer dimension
    customers_df = dimension_dfs.get("customer", pd.DataFrame())
    products_df = dimension_dfs.get("product", pd.DataFrame())

    customer_ids = customers_df["customer_id"].tolist() if len(customers_df) > 0 else []
    product_ids = products_df["product_id"].tolist() if len(products_df) > 0 else []

    # ✅ Weighted sampling: Enterprise generates 5x, Pro 2x, Free 1x
    if len(customers_df) > 0 and "tier" in customers_df.columns:
        tier_weights = customers_df["tier"].map(
            {"Enterprise": 5.0, "Pro": 2.0, "Free": 1.0}
        )
        customer_weights = (tier_weights / tier_weights.sum()).tolist()
        customer_tier_map = dict(
            zip(customers_df["customer_id"], customers_df["tier"])
        )
    else:
        customer_weights = None
        customer_tier_map = {}

    records = []

    if use_temporal_patterns:
        # Distribute records across dates with temporal patterns
        date_range = pd.date_range(START_DATE, END_DATE, freq="D")
        base_daily = num_records / len(date_range)

        record_idx = 0
        for day in date_range:
            daily_count = int(
                base_daily * get_daily_multiplier(day.to_pydatetime())
            )
            for _ in range(daily_count):
                if record_idx >= num_records:
                    break
                record = _generate_valid_fact_record(
                    fake_local,
                    customer_ids, customer_weights, customer_tier_map,
                    product_ids, record_idx + 1, day.to_pydatetime(),
                )
                if random.random() < corruption_rate:
                    record = _apply_fact_corruption(
                        record, customer_ids, product_ids
                    )
                records.append(record)
                record_idx += 1
            if record_idx >= num_records:
                break
    else:
        for i in range(num_records):
            record = _generate_valid_fact_record(
                fake_local,
                customer_ids, customer_weights, customer_tier_map,
                product_ids, i + 1, None,
            )
            if random.random() < corruption_rate:
                record = _apply_fact_corruption(
                    record, customer_ids, product_ids
                )
            records.append(record)

    return pd.DataFrame(records)


def _generate_valid_fact_record(
    fake: Faker,
    customer_ids: List,
    customer_weights: Optional[List],
    customer_tier_map: Dict,
    product_ids: List,
    record_id: int,
    record_date: Optional[datetime],
) -> Dict:
    """Generate a valid fact record with weighted sampling and row coherence."""
    # Weighted customer selection
    if customer_ids and customer_weights:
        cid = np.random.choice(customer_ids, p=customer_weights)
    elif customer_ids:
        cid = np.random.choice(customer_ids)
    else:
        cid = None

    # Row coherence: tier drives amount
    tier = customer_tier_map.get(cid, "Free")
    amount_params = {"Enterprise": (7, 0.8), "Pro": (5, 0.7), "Free": (3.5, 0.6)}
    mean, sigma = amount_params.get(tier, (3.5, 0.6))
    amount = round(np.random.lognormal(mean, sigma), 2)

    # Quantity uses Poisson (clusters around average)
    quantity = max(1, int(np.random.poisson(lam=3)))
    total_amount = round(quantity * amount, 2)

    # Date: use provided date or generate within range
    if record_date:
        order_date = record_date.strftime("%Y-%m-%d")
    else:
        order_date = fake.date_between(
            start_date=START_DATE, end_date=END_DATE
        ).strftime("%Y-%m-%d")

    return {
        "order_id": record_id,
        "customer_id": cid,
        "product_id": np.random.choice(product_ids) if product_ids else None,
        "order_date": order_date,
        "quantity": quantity,
        "unit_price": amount,
        "total_amount": total_amount,
        "channel": np.random.choice(
            ["web", "mobile", "store", "phone"], p=[0.40, 0.30, 0.20, 0.10]
        ),
        "payment_method": np.random.choice(
            ["credit_card", "debit_card", "cash", "paypal"],
            p=[0.45, 0.25, 0.15, 0.15],
        ),
        "order_status": np.random.choice(
            ["completed", "pending", "cancelled"], p=[0.85, 0.10, 0.05]
        ),
    }


# =============================================================================
# CORRUPTION FUNCTIONS
# =============================================================================
def _apply_dimension_corruption(record: Dict, entity_type: str) -> Dict:
    """Apply corruption to dimension record. Each type maps to a DLT expectation."""
    corruption_type = random.choice([
        "null_required",
        "invalid_email",
        "too_short",
        "empty_string",
    ])

    if entity_type == "customer":
        if corruption_type == "null_required":
            # Will fail: valid_email (expects NOT NULL)
            record["email"] = None
        elif corruption_type == "invalid_email":
            # Will fail: valid_email (expects valid email format)
            record["email"] = "not-an-email"
        elif corruption_type == "too_short":
            # Will fail: valid_first_name (expects min length 2)
            record["first_name"] = "A"
        elif corruption_type == "empty_string":
            # Will fail: valid_last_name (expects non-empty string)
            record["last_name"] = ""

    return record


def _apply_fact_corruption(
    record: Dict, customer_ids: List, product_ids: List
) -> Dict:
    """Apply corruption to fact record. Each type maps to a DLT expectation."""
    corruption_type = random.choice([
        "invalid_fk",
        "null_fk",
        "negative_value",
        "future_date",
    ])

    if corruption_type == "invalid_fk":
        # Will fail: valid_customer_id (expects customer_id in dim_customer)
        record["customer_id"] = 999999
    elif corruption_type == "null_fk":
        # Will fail: valid_product_id (expects NOT NULL)
        record["product_id"] = None
    elif corruption_type == "negative_value":
        # Will fail: valid_quantity (expects quantity >= 0)
        record["quantity"] = -1
        record["total_amount"] = record["quantity"] * record["unit_price"]
    elif corruption_type == "future_date":
        # Will fail: valid_order_date (expects order_date <= current_date)
        record["order_date"] = fake.future_date().strftime("%Y-%m-%d")

    return record


# =============================================================================
# VALIDATION (always run at end of generation)
# =============================================================================
def validate_generated_data(
    dimension_dfs: Dict[str, pd.DataFrame],
    fact_df: pd.DataFrame,
) -> None:
    """Print validation stats for generated data."""
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)

    for name, df in dimension_dfs.items():
        print(f"\n{name.upper()}: {len(df):,} records")
        for col in df.select_dtypes(include=["object", "category"]).columns:
            if df[col].nunique() < 15:
                dist = df[col].value_counts(normalize=True).round(3).to_dict()
                print(f"  {col}: {dist}")

    if len(fact_df) > 0:
        print(f"\nFACTS: {len(fact_df):,} records")
        if "order_date" in fact_df.columns:
            print(f"  Date range: {fact_df['order_date'].min()} → "
                  f"{fact_df['order_date'].max()}")
        if "unit_price" in fact_df.columns:
            print(f"  Avg unit_price: ${fact_df['unit_price'].mean():,.2f}")
            print(f"  Median unit_price: ${fact_df['unit_price'].median():,.2f}")

        # Check referential integrity
        for name, dim_df in dimension_dfs.items():
            id_col = f"{name}_id"
            if id_col in fact_df.columns and id_col in dim_df.columns:
                valid_ids = set(dim_df[id_col])
                fact_ids = set(fact_df[id_col].dropna())
                orphans = fact_ids - valid_ids
                if orphans:
                    print(f"  ⚠️  {len(orphans)} orphan {id_col} values "
                          f"(expected: corruption)")
                else:
                    print(f"  ✅ All {id_col} values valid")

    print()

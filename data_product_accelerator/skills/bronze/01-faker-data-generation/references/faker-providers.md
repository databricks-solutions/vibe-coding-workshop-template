# Faker Provider Patterns and Corruption Strategies

This document provides detailed Faker provider examples, corruption patterns, and implementation strategies for generating realistic synthetic data with intentional data quality violations.

## Locale-Specific Providers

### US Locale (Default)
```python
from faker import Faker

fake = Faker('en_US')

# Addresses
address = fake.address()  # "123 Main St, New York, NY 10001"
city = fake.city()  # "New York"
state = fake.state_abbr()  # "NY"
zipcode = fake.zipcode()  # "10001"

# Names
first_name = fake.first_name()  # "John"
last_name = fake.last_name()  # "Smith"
full_name = fake.name()  # "John Smith"

# Phone Numbers
phone = fake.phone_number()  # "(555) 123-4567"
```

### International Locales
```python
# German locale
fake_de = Faker('de_DE')
german_address = fake_de.address()  # "Hauptstraße 42, 10115 Berlin"
german_phone = fake_de.phone_number()  # "+49 30 12345678"

# Japanese locale
fake_ja = Faker('ja_JP')
japanese_name = fake_ja.name()  # "田中 太郎"
japanese_address = fake_ja.address()  # "東京都渋谷区..."

# UK locale
fake_uk = Faker('en_GB')
uk_postcode = fake_uk.postcode()  # "SW1A 1AA"
uk_phone = fake_uk.phone_number()  # "+44 20 7946 0958"
```

## Business-Specific Providers

### Company Data
```python
fake = Faker()

# Company information
company_name = fake.company()  # "Smith, Jones and Associates"
company_suffix = fake.company_suffix()  # "Inc"
bs = fake.bs()  # "revolutionize next-generation e-markets"
catch_phrase = fake.catch_phrase()  # "Multi-layered client-server neural-net"

# Email (company domain)
email = fake.company_email()  # "john.smith@smithjones.com"
```

### Financial Data
```python
fake = Faker()

# Credit card
cc_number = fake.credit_card_number()  # "4532-1234-5678-9010"
cc_provider = fake.credit_card_provider()  # "Visa"
cc_security_code = fake.credit_card_security_code()  # "123"
cc_expire = fake.credit_card_expire()  # "12/25"

# Bank account
iban = fake.iban()  # "GB82WEST12345698765432"
swift = fake.swift()  # "CHASUS33"
```

### E-commerce Data
```python
fake = Faker()

# Product information
product_name = fake.catch_phrase()  # "Multi-layered client-server"
ean13 = fake.ean13()  # "1234567890123"
ean8 = fake.ean8()  # "12345678"
color = fake.color_name()  # "Blue"
```

## Domain-Specific Constants

### Example: Retail Domain
```python
# Domain constants for retail
RETAIL_CHANNELS = ['web', 'mobile', 'store', 'phone']
RETAIL_PAYMENT_METHODS = ['credit_card', 'debit_card', 'cash', 'paypal', 'apple_pay']
RETAIL_PRODUCT_CATEGORIES = ['electronics', 'clothing', 'home', 'sports', 'books']
RETAIL_ORDER_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
RETAIL_SHIPPING_METHODS = ['standard', 'express', 'overnight', 'pickup']
```

### Example: Billing Domain
```python
# Domain constants for billing
BILLING_SKUS = ['dbu_compute', 'dbu_jobs', 'dbu_sql', 'dbu_serverless']
BILLING_WORKSPACE_TIERS = ['standard', 'premium', 'enterprise']
BILLING_REGIONS = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
BILLING_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY']
```

## Non-Linear Distribution Patterns

**NEVER use `random.uniform()` for numeric values. Real data follows skewed distributions.**

### Distribution Selection Guide

| Data Type | Distribution | Function | Example |
|---|---|---|---|
| Monetary (prices, salaries, amounts) | Log-normal | `np.random.lognormal(mean, sigma, size)` | Orders cluster around median, long tail of large orders |
| Durations (resolution time, session) | Exponential | `np.random.exponential(scale, size)` | Most fast, some very slow |
| Popularity (views, downloads) | Pareto/Power law | `(np.random.pareto(a, size) + 1) * base` | Few items very popular, most not |
| Counts (items per order) | Poisson | `np.random.poisson(lam, size)` | Clusters around average |
| Categories (region, tier, status) | Weighted categorical | `np.random.choice(items, size, p=weights)` | Unequal probabilities |
| Ratings (1-5 stars) | Skewed choice | `np.random.choice([1,2,3,4,5], p=weights)` | Most 4-5, few 1-2 |

### Implementation

```python
import numpy as np

# Log-normal: monetary values (mean and sigma control the shape)
# mean=4.5, sigma=0.8 → median ~$90, range $10-$2000
small_amounts = np.random.lognormal(mean=4.5, sigma=0.8, size=N)

# mean=7, sigma=0.8 → median ~$1100, range $100-$30000
enterprise_amounts = np.random.lognormal(mean=7, sigma=0.8, size=N)

# Exponential: durations (scale = average value)
resolution_hours = np.random.exponential(scale=24, size=N)  # avg 24 hours
session_minutes = np.random.exponential(scale=15, size=N)   # avg 15 minutes

# Pareto: popularity/ranking (a controls tail heaviness)
page_views = (np.random.pareto(a=2.5, size=N) + 1) * 10

# Weighted categorical: always specify probabilities
regions = np.random.choice(
    ['North', 'South', 'East', 'West'],
    size=N, p=[0.40, 0.25, 0.20, 0.15]
)

tiers = np.random.choice(
    ['Free', 'Pro', 'Enterprise'],
    size=N, p=[0.60, 0.30, 0.10]
)
```

---

## Time-Based Pattern Functions

**Generated data MUST include temporal patterns to look realistic in dashboards.**

### Daily Volume Multiplier

```python
import holidays
from datetime import datetime, timedelta

# Dynamic date range: last 6 months from today
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# Holiday calendar
US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])

def get_daily_multiplier(date, us_holidays=US_HOLIDAYS):
    """
    Calculate realistic daily volume multiplier.
    
    Combines: weekday/weekend, holidays, seasonality, event spikes, and noise.
    Returns a multiplier (e.g., 0.3 for holiday, 3.0 for incident spike).
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
```

### Event Spike Pattern

```python
# Define an incident/event within the date range
INCIDENT_END = END_DATE - timedelta(days=21)     # 3 weeks ago
INCIDENT_START = INCIDENT_END - timedelta(days=10)  # Lasted 10 days

def get_daily_multiplier_with_spike(date, us_holidays=US_HOLIDAYS):
    """Volume multiplier including event spike."""
    multiplier = get_daily_multiplier(date, us_holidays)
    
    # Incident spike: 3x normal volume
    if INCIDENT_START <= date <= INCIDENT_END:
        multiplier *= 3.0
    
    return multiplier
```

### Distributing Records Across Dates

```python
import pandas as pd

BASE_DAILY = N_RECORDS / 180  # Spread across 6 months

date_range = pd.date_range(START_DATE, END_DATE, freq='D')
daily_volumes = [
    int(BASE_DAILY * get_daily_multiplier(d.to_pydatetime()))
    for d in date_range
]

# Generate records distributed by daily volume
records = []
record_idx = 0
for day, count in zip(date_range, daily_volumes):
    for _ in range(count):
        if record_idx >= N_RECORDS:
            break
        record = generate_record(day.to_pydatetime(), record_idx)
        records.append(record)
        record_idx += 1
```

---

## Row Coherence Patterns

**Attributes within a single row MUST correlate logically. Independent random values are unrealistic.**

### Tier-Driven Coherence

```python
def generate_coherent_record(customer_id, tier, date):
    """Generate a record where tier drives all dependent attributes."""
    
    # Amount correlates with tier
    if tier == 'Enterprise':
        amount = np.random.lognormal(7, 0.8)        # ~$1100 median
        priority = np.random.choice(['Critical', 'High', 'Medium'], p=[0.3, 0.5, 0.2])
    elif tier == 'Pro':
        amount = np.random.lognormal(5, 0.7)        # ~$150 median
        priority = np.random.choice(['High', 'Medium', 'Low'], p=[0.3, 0.5, 0.2])
    else:  # Free
        amount = np.random.lognormal(3.5, 0.6)      # ~$33 median
        priority = np.random.choice(['Medium', 'Low'], p=[0.4, 0.6])
    
    # Resolution time correlates with priority
    resolution_scale = {'Critical': 4, 'High': 12, 'Medium': 36, 'Low': 72}
    resolution_hours = np.random.exponential(scale=resolution_scale[priority])
    
    # CSAT correlates with resolution time
    if resolution_hours < 4:
        csat = np.random.choice([4, 5], p=[0.3, 0.7])
    elif resolution_hours < 24:
        csat = np.random.choice([3, 4, 5], p=[0.2, 0.5, 0.3])
    else:
        csat = np.random.choice([1, 2, 3, 4], p=[0.1, 0.3, 0.4, 0.2])
    
    return {
        "customer_id": customer_id,
        "amount": round(amount, 2),
        "priority": priority,
        "resolution_hours": round(resolution_hours, 1),
        "csat_score": csat,
        "created_at": date.strftime("%Y-%m-%d"),
    }
```

### Event-Driven Coherence

```python
def generate_ticket_during_incident(customer_id, tier, date, is_incident):
    """During incidents, category distribution shifts and CSAT degrades."""
    
    if is_incident:
        # Auth dominates during incident
        category = np.random.choice(
            ['Auth', 'Network', 'Billing', 'Account'],
            p=[0.65, 0.15, 0.1, 0.1]
        )
    else:
        category = np.random.choice(
            ['Auth', 'Network', 'Billing', 'Account'],
            p=[0.25, 0.30, 0.25, 0.20]
        )
    
    # CSAT degrades during incident for Auth category
    if is_incident and category == 'Auth':
        csat = np.random.choice([1, 2, 3, 4, 5], p=[0.15, 0.25, 0.35, 0.2, 0.05])
    else:
        csat = np.random.choice([1, 2, 3, 4, 5], p=[0.02, 0.08, 0.20, 0.40, 0.30])
    
    return {"category": category, "csat_score": csat}
```

---

## Weighted Sampling for Facts

**Dimension characteristics MUST drive fact generation. Enterprise customers generate more activity.**

```python
# Build weighted lookup from dimension DataFrame
customer_ids = customers_pdf["customer_id"].tolist()
customer_tier_map = dict(zip(customers_pdf["customer_id"], customers_pdf["tier"]))

# Weight: Enterprise=5x, Pro=2x, Free=1x
tier_weights = customers_pdf["tier"].map({'Enterprise': 5.0, 'Pro': 2.0, 'Free': 1.0})
customer_weights = (tier_weights / tier_weights.sum()).tolist()

# Generate fact records with weighted selection
for i in range(N_ORDERS):
    cid = np.random.choice(customer_ids, p=customer_weights)
    tier = customer_tier_map[cid]
    
    # Amount depends on selected customer's tier (row coherence)
    amount = np.random.lognormal(
        7 if tier == 'Enterprise' else 5 if tier == 'Pro' else 3.5,
        0.7
    )
    
    records.append({
        "order_id": f"ORD-{i:06d}",
        "customer_id": cid,
        "amount": round(amount, 2),
    })
```

---

## Validation Section (End of Script)

**ALWAYS include validation prints at the end of generation scripts:**

```python
print("\n=== VALIDATION ===")
print(f"Customers: {len(customers_pdf):,}")
print(f"  Tier distribution: {customers_pdf['tier'].value_counts(normalize=True).round(2).to_dict()}")
print(f"Orders: {len(orders_pdf):,}")
print(f"  Avg amount by tier: {orders_pdf.merge(customers_pdf[['customer_id','tier']]).groupby('tier')['amount'].mean().round(2).to_dict()}")
print(f"Tickets: {len(tickets_pdf):,}")

# Check incident spike
if 'INCIDENT_START' in dir():
    incident_tickets = tickets_pdf[tickets_pdf['created_at'].between(
        INCIDENT_START.strftime("%Y-%m-%d"), INCIDENT_END.strftime("%Y-%m-%d")
    )]
    print(f"  Incident period: {len(incident_tickets):,} ({len(incident_tickets)/len(tickets_pdf)*100:.1f}%)")
```

---

## Corruption Patterns by Category

### 1. Missing Required Fields

```python
def apply_null_corruption(record: dict, field: str, corruption_type: str):
    """
    Apply null corruption to required fields.
    
    Corruption Types:
    - 'null_required': Set required field to None
    - 'empty_string': Set string field to empty string
    - 'missing_required': Remove required field entirely
    """
    if corruption_type == 'null_required':
        # Will fail: valid_field_name (expects NOT NULL)
        record[field] = None
    elif corruption_type == 'empty_string':
        # Will fail: valid_field_name (expects non-empty string)
        record[field] = ""
    elif corruption_type == 'missing_required':
        # Will fail: valid_field_name (field missing from record)
        del record[field]
    
    return record
```

### 2. Invalid Format/Length

```python
def apply_format_corruption(record: dict, field: str, corruption_type: str):
    """
    Apply format/length corruption.
    
    Corruption Types:
    - 'invalid_email': Invalid email format
    - 'too_short': String below minimum length
    - 'too_long': String exceeds maximum length
    - 'invalid_phone': Invalid phone number format
    """
    if corruption_type == 'invalid_email':
        # Will fail: valid_email (expects valid email format)
        record[field] = "not-an-email"
    elif corruption_type == 'too_short':
        # Will fail: valid_field_name (expects min length 3)
        record[field] = "ab"  # Below minimum length
    elif corruption_type == 'too_long':
        # Will fail: valid_field_name (expects max length 50)
        record[field] = "a" * 100  # Exceeds maximum length
    elif corruption_type == 'invalid_phone':
        # Will fail: valid_phone (expects valid phone format)
        record[field] = "123"  # Invalid format
    
    return record
```

### 3. Out of Range Values

```python
def apply_range_corruption(record: dict, field: str, corruption_type: str, valid_range: tuple):
    """
    Apply out-of-range corruption.
    
    Corruption Types:
    - 'negative_value': Negative value for non-negative field
    - 'exceeds_max': Value exceeds maximum
    - 'below_min': Value below minimum
    """
    min_val, max_val = valid_range
    
    if corruption_type == 'negative_value':
        # Will fail: valid_amount (expects amount >= 0)
        record[field] = -100.0
    elif corruption_type == 'exceeds_max':
        # Will fail: valid_quantity (expects quantity <= max_val)
        record[field] = max_val + 1000
    elif corruption_type == 'below_min':
        # Will fail: valid_quantity (expects quantity >= min_val)
        record[field] = min_val - 100
    
    return record
```

### 4. Business Logic Violations

```python
def apply_business_logic_corruption(record: dict, corruption_type: str):
    """
    Apply business logic violations.
    
    Corruption Types:
    - 'future_date': Date in the future for historical record
    - 'past_date': Date too old (beyond retention period)
    - 'invalid_status_transition': Invalid status change
    - 'mismatched_currency': Currency mismatch with region
    """
    if corruption_type == 'future_date':
        # Will fail: valid_date (expects date <= current_date)
        record['date'] = fake.future_date()
    elif corruption_type == 'past_date':
        # Will fail: valid_date (expects date >= retention_start_date)
        record['date'] = fake.date_between(start_date='-5y', end_date='-2y')
    elif corruption_type == 'invalid_status_transition':
        # Will fail: valid_status (expects valid status transition)
        record['status'] = 'delivered'  # Can't be delivered if never shipped
    elif corruption_type == 'mismatched_currency':
        # Will fail: valid_currency (expects currency matching region)
        record['currency'] = 'EUR'  # But region is 'us-east-1'
    
    return record
```

### 5. Temporal Issues

```python
def apply_temporal_corruption(record: dict, corruption_type: str):
    """
    Apply temporal corruption.
    
    Corruption Types:
    - 'end_before_start': End date before start date
    - 'invalid_timestamp': Timestamp in invalid range
    - 'timezone_mismatch': Timezone doesn't match region
    """
    if corruption_type == 'end_before_start':
        # Will fail: valid_date_range (expects end_date >= start_date)
        record['start_date'] = fake.date_between(start_date='-1y', end_date='today')
        record['end_date'] = fake.date_between(start_date='-2y', end_date='-1y')
    elif corruption_type == 'invalid_timestamp':
        # Will fail: valid_timestamp (expects timestamp within valid range)
        record['timestamp'] = fake.date_time_between(start_date='-10y', end_date='-5y')
    
    return record
```

### 6. Referential Integrity Issues

```python
def apply_referential_corruption(record: dict, dimension_keys: dict, corruption_type: str):
    """
    Apply referential integrity corruption.
    
    Corruption Types:
    - 'invalid_fk': Foreign key doesn't exist in dimension
    - 'null_fk': Null foreign key for required relationship
    - 'orphaned_record': Record references non-existent parent
    """
    if corruption_type == 'invalid_fk':
        # Will fail: valid_customer_id (expects customer_id in dim_customer)
        record['customer_id'] = 999999  # Non-existent customer
    elif corruption_type == 'null_fk':
        # Will fail: valid_product_id (expects NOT NULL product_id)
        record['product_id'] = None
    elif corruption_type == 'orphaned_record':
        # Will fail: valid_store_id (expects store_id in dim_store)
        record['store_id'] = random.randint(100000, 999999)  # Random invalid ID
    
    return record
```

## Complete Implementation Example

### Dimension Data Generation

```python
from faker import Faker
import random

def generate_dimension_data(entity_type: str, num_records: int, corruption_rate: float = 0.0) -> list:
    """
    Generate dimension data with optional corruption.
    
    Args:
        entity_type: Type of dimension (e.g., 'customer', 'product', 'store')
        num_records: Number of records to generate
        corruption_rate: Percentage of records to corrupt (0.0 to 1.0)
    """
    fake = Faker('en_US')
    records = []
    
    for i in range(num_records):
        # Generate valid data first
        if entity_type == 'customer':
            record = {
                'customer_id': i + 1,
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'email': fake.email(),
                'phone': fake.phone_number(),
                'address': fake.address(),
                'city': fake.city(),
                'state': fake.state_abbr(),
                'zipcode': fake.zipcode(),
                'created_date': fake.date_between(start_date='-2y', end_date='today')
            }
        elif entity_type == 'product':
            record = {
                'product_id': i + 1,
                'product_name': fake.catch_phrase(),
                'category': random.choice(RETAIL_PRODUCT_CATEGORIES),
                'price': round(random.uniform(10.0, 1000.0), 2),
                'sku': fake.ean13(),
                'created_date': fake.date_between(start_date='-1y', end_date='today')
            }
        
        # Apply corruption if selected
        if random.random() < corruption_rate:
            corruption_type = random.choice([
                'null_required',
                'invalid_email',
                'too_short',
                'negative_value'
            ])
            
            if corruption_type == 'null_required' and entity_type == 'customer':
                # Will fail: valid_email (expects NOT NULL)
                record['email'] = None
            elif corruption_type == 'invalid_email' and entity_type == 'customer':
                # Will fail: valid_email (expects valid email format)
                record['email'] = "not-an-email"
        
        records.append(record)
    
    return records
```

### Fact Data Generation

```python
def generate_fact_data(
    dimension_keys: dict,
    num_records: int,
    corruption_rate: float = 0.0
) -> list:
    """
    Generate fact data with referential integrity.
    
    Args:
        dimension_keys: Dictionary with dimension keys (e.g., {'customer_id': [1,2,3], 'product_id': [1,2,3]})
        num_records: Number of records to generate
        corruption_rate: Percentage of records to corrupt
    """
    fake = Faker('en_US')
    records = []
    
    customer_ids = dimension_keys.get('customer_id', [])
    product_ids = dimension_keys.get('product_id', [])
    
    for i in range(num_records):
        # Generate valid fact record
        record = {
            'order_id': i + 1,
            'customer_id': random.choice(customer_ids) if customer_ids else None,
            'product_id': random.choice(product_ids) if product_ids else None,
            'order_date': fake.date_between(start_date='-1y', end_date='today'),
            'quantity': random.randint(1, 10),
            'unit_price': round(random.uniform(10.0, 500.0), 2),
            'total_amount': 0.0,  # Will calculate
            'channel': random.choice(RETAIL_CHANNELS),
            'payment_method': random.choice(RETAIL_PAYMENT_METHODS),
            'order_status': random.choice(RETAIL_ORDER_STATUSES)
        }
        
        # Calculate total_amount
        record['total_amount'] = record['quantity'] * record['unit_price']
        
        # Apply corruption if selected
        if random.random() < corruption_rate:
            corruption_type = random.choice([
                'invalid_fk',
                'null_fk',
                'negative_value',
                'future_date'
            ])
            
            if corruption_type == 'invalid_fk':
                # Will fail: valid_customer_id (expects customer_id in dim_customer)
                record['customer_id'] = 999999
            elif corruption_type == 'null_fk':
                # Will fail: valid_product_id (expects NOT NULL)
                record['product_id'] = None
            elif corruption_type == 'negative_value':
                # Will fail: valid_quantity (expects quantity >= 0)
                record['quantity'] = -1
            elif corruption_type == 'future_date':
                # Will fail: valid_order_date (expects order_date <= current_date)
                record['order_date'] = fake.future_date()
        
        records.append(record)
    
    return records
```

## Corruption Rate Guidelines

| Environment | Corruption Rate | Purpose |
|---|---|---|
| **Development** | 0.10 (10%) | Thorough testing of all DQ expectations |
| **Staging** | 0.05 (5%) | Production-like data quality issues |
| **Production** | 0.0 (0%) | Real data only, no synthetic corruption |

## Mapping Corruption to DLT Expectations

Each corruption type should map to a specific DLT expectation:

```python
CORRUPTION_TO_EXPECTATION_MAP = {
    'null_required': 'valid_field_name',  # @dlt.expect("valid_field_name", "field_name IS NOT NULL")
    'invalid_email': 'valid_email',  # @dlt.expect("valid_email", "email RLIKE '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'")
    'too_short': 'valid_field_length',  # @dlt.expect("valid_field_length", "LENGTH(field_name) >= 3")
    'negative_value': 'valid_amount',  # @dlt.expect("valid_amount", "amount >= 0")
    'invalid_fk': 'valid_customer_id',  # @dlt.expect("valid_customer_id", "customer_id IN (SELECT customer_id FROM dim_customer)")
    'future_date': 'valid_date',  # @dlt.expect("valid_date", "order_date <= current_date()")
}
```

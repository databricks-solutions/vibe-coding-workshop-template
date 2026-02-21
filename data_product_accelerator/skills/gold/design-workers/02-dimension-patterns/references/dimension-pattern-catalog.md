# Dimension Pattern Catalog

Extended dimension design patterns with YAML examples for Gold layer modeling. These patterns complement the core rules in the main SKILL.md.

---

## Mini-Dimensions

### When to Use

When a large dimension (100K+ rows) has a subset of attributes that change frequently (e.g., customer demographics, account tier, credit score), split those volatile attributes into a separate mini-dimension.

### Why

SCD Type 2 on a large dimension with frequently changing attributes generates excessive row versions. A mini-dimension isolates the volatile attributes so the main dimension stays stable.

### YAML Pattern

```yaml
# Main dimension — stable attributes
table_name: dim_customer
columns:
  - name: customer_key
    type: BIGINT
    nullable: false
  - name: customer_name
    type: STRING
  - name: email
    type: STRING
  - name: signup_date
    type: DATE
  - name: current_demographics_key
    type: BIGINT
    description: "Current demographics profile. Business: Latest customer demographics. Technical: FK to dim_customer_demographics (mini-dimension, updated frequently)."
    foreign_key:
      references: dim_customer_demographics.demographics_key

# Mini-dimension — volatile attributes
table_name: dim_customer_demographics
description: "Customer demographics mini-dimension. Business: Demographic profiles that change frequently. Technical: Mini-dimension split from dim_customer to reduce SCD Type 2 row explosion."
columns:
  - name: demographics_key
    type: BIGINT
    nullable: false
  - name: age_band
    type: STRING     # "18-24", "25-34", "35-44", ...
  - name: income_band
    type: STRING     # "Low", "Medium", "High", "Very High"
  - name: loyalty_tier
    type: STRING     # "Bronze", "Silver", "Gold", "Platinum"
  - name: risk_category
    type: STRING     # "Low Risk", "Medium Risk", "High Risk"
```

### Key Rules

- Mini-dimension rows are **immutable** — each unique combination of attributes gets one row
- The main dimension holds a **current FK** to the mini-dimension
- The fact table can hold **its own FK** to the mini-dimension (captures demographics at transaction time)
- Typical mini-dimension has < 1,000 rows (all possible attribute combinations)

---

## Outrigger Dimensions

### When to Use

When one dimension has a foreign key to another dimension. For example, `dim_product` references `dim_brand` which has its own attributes.

### Why

Sometimes a dimension naturally references another dimension. This is acceptable if:
1. The referenced dimension is small and stable
2. The relationship is well-defined and rarely changes
3. Flattening would cause excessive denormalization

### YAML Pattern

```yaml
table_name: dim_product
columns:
  - name: product_key
    type: BIGINT
    nullable: false
  - name: product_name
    type: STRING
  - name: brand_key
    type: BIGINT
    description: "Brand reference. Business: Product brand. Technical: FK to dim_brand (outrigger dimension)."
    foreign_key:
      references: dim_brand.brand_key
  # Also denormalize the most-queried brand attributes
  - name: brand_name
    type: STRING
    description: "Brand name (denormalized). Business: Brand of this product. Technical: Denormalized from dim_brand for query performance."
```

### Key Rules

- **Prefer denormalization over outriggers** — if the outrigger has < 10 attributes, flatten them
- Outriggers should be **small, stable dimensions** (< 100 rows)
- Always denormalize the most-queried attributes even when using an outrigger
- **Never chain outriggers** (dim_a → dim_b → dim_c is snowflaking)

---

## Multiple Hierarchies

### When to Use

When a single dimension has alternate rollup paths. For example, `dim_product` rolls up by both category hierarchy AND brand hierarchy.

### YAML Pattern

```yaml
table_name: dim_product
columns:
  - name: product_key
    type: BIGINT
    nullable: false
  - name: product_name
    type: STRING
  # Hierarchy 1: Category path
  - name: subcategory_name
    type: STRING
    description: "Product subcategory (hierarchy 1). Business: Fine-grained product grouping. Technical: Category hierarchy level 3."
  - name: category_name
    type: STRING
    description: "Product category (hierarchy 1). Business: Mid-level product grouping. Technical: Category hierarchy level 2."
  - name: department_name
    type: STRING
    description: "Department (hierarchy 1). Business: Top-level product grouping. Technical: Category hierarchy level 1."
  # Hierarchy 2: Brand path
  - name: brand_name
    type: STRING
    description: "Brand (hierarchy 2). Business: Product manufacturer/brand. Technical: Brand hierarchy level 2."
  - name: brand_portfolio
    type: STRING
    description: "Brand portfolio (hierarchy 2). Business: Parent brand group. Technical: Brand hierarchy level 1."
```

### Key Rules

- Each hierarchy is a set of columns in the same dimension row
- Name columns to indicate hierarchy membership (comments, naming patterns)
- All hierarchy levels flattened into the dimension — no separate tables

---

## Bridge Tables (Many-to-Many Relationships)

### When to Use

When a fact has a many-to-many relationship with a dimension. For example, a patient can have multiple diagnoses, and a diagnosis applies to multiple patients.

### YAML Pattern

```yaml
# Bridge table resolving M:N relationship
table_name: bridge_patient_diagnosis
description: "Patient-diagnosis bridge. Business: Links patients to their diagnoses. Technical: Resolves M:N between fact_encounter and dim_diagnosis."
columns:
  - name: patient_key
    type: BIGINT
    nullable: false
    foreign_key:
      references: dim_patient.patient_key
  - name: diagnosis_key
    type: BIGINT
    nullable: false
    foreign_key:
      references: dim_diagnosis.diagnosis_key
  - name: weighting_factor
    type: DOUBLE
    description: "Attribution weight. Business: Proportion of encounter attributed to this diagnosis. Technical: Weights sum to 1.0 per patient encounter."
primary_key:
  columns:
    - patient_key
    - diagnosis_key
```

### Key Rules

- Bridge table has a **composite PK** of the two dimension keys
- Include a **weighting factor** column to enable proportional allocation of measures
- Weighting factors should sum to 1.0 per fact row group
- Bridge tables are **not** junk dimensions — they resolve genuine M:N relationships

---

## NULL Handling Strategy

### Dimension Unknown Members

Every dimension table should have a dedicated "Unknown" row to replace NULL foreign keys:

| Dimension | Unknown Key | Unknown Row Values |
|-----------|-------------|-------------------|
| `dim_customer` | `-1` | customer_name = "Unknown Customer" |
| `dim_product` | `-1` | product_name = "Unknown Product" |
| `dim_store` | `-1` | store_name = "Unknown Store" |
| `dim_date` | `-1` | date_value = "1900-01-01", month_name = "Unknown" |

### YAML Pattern for Unknown Row

```yaml
# Document in dimension YAML
table_name: dim_customer
table_properties:
  null_handling: "Unknown member row at customer_key = -1"
columns:
  - name: customer_key
    type: BIGINT
    nullable: false
    description: "Customer surrogate key. Business: Unique customer identifier. Technical: -1 reserved for Unknown member."
```

### Implementation Note

During the merge script phase, the ETL pipeline should:
1. Insert the Unknown member row before any fact data loads
2. Replace NULL foreign keys with the Unknown member key using `COALESCE(fk, -1)`

---

## Heterogeneous Products (Varying Attributes)

### When to Use

When products in the same dimension have vastly different attributes (e.g., electronics have voltage/wattage, clothing has size/color/fabric).

### Approaches

| Approach | When to Use | Trade-off |
|----------|-------------|-----------|
| **Core + Custom Attributes** | < 5 product types | Add nullable columns for type-specific attributes |
| **Name-Value Pairs** | Many product types, sparse attributes | Flexible but poor query performance |
| **Separate Dimensions** | Completely different business domains | Clean but prevents cross-domain analysis |

### Recommended Approach (Core + Custom)

```yaml
table_name: dim_product
columns:
  # Core attributes (all products)
  - name: product_key
    type: BIGINT
    nullable: false
  - name: product_name
    type: STRING
  - name: product_type
    type: STRING    # "Electronics", "Clothing", "Furniture"
  # Type-specific attributes (nullable)
  - name: voltage_rating
    type: STRING    # Electronics only
    description: "Voltage rating. Business: Product voltage (electronics only). Technical: NULL for non-electronic products."
  - name: clothing_size
    type: STRING    # Clothing only
    description: "Clothing size. Business: Size (clothing only). Technical: NULL for non-clothing products."
```

---

## Anti-Pattern Reference

### Snowflaked Dimensions

**Problem:** Normalizing dimension attributes into separate related tables.

```
# ❌ Snowflake: dim_product → dim_subcategory → dim_category
# Forces 3-way joins for every product query
```

**Fix:** Flatten all hierarchy levels into a single dimension table.

### Abstract Generic Dimensions

**Problem:** Creating a single "dim_entity" or "dim_type" table that combines unrelated business concepts.

```
# ❌ Generic: dim_entity (entity_key, entity_type, entity_name)
#    where entity_type IN ('customer', 'product', 'store')
```

**Fix:** Create separate dimensions per business concept. Each should have its own attributes.

### Over-Splitting into Too Many Dimensions

**Problem:** Creating a separate dimension for every attribute (dim_color, dim_size, dim_style).

**Fix:** Group related attributes into meaningful dimensions. Use junk dimensions for unrelated low-cardinality flags.

# Validation Queries & Implementation Checklist

Use these queries and checklists after deploying the Bronze layer.

---

## Validation SQL Queries

### List All Bronze Tables

```sql
SHOW TABLES IN {catalog}.{bronze_schema};
```

### Check Record Counts

```sql
SELECT
  'bronze_store_dim' as table_name, COUNT(*) as row_count
FROM {catalog}.{bronze_schema}.bronze_store_dim
UNION ALL
SELECT 'bronze_product_dim', COUNT(*) FROM {catalog}.{bronze_schema}.bronze_product_dim
UNION ALL
SELECT 'bronze_date_dim', COUNT(*) FROM {catalog}.{bronze_schema}.bronze_date_dim
UNION ALL
SELECT 'bronze_transactions', COUNT(*) FROM {catalog}.{bronze_schema}.bronze_transactions;
```

### Verify FK Integrity

```sql
-- Check for orphaned transactions (invalid store references)
SELECT
  'Orphaned transactions (invalid store)' as check_name,
  COUNT(*) as orphan_count
FROM {catalog}.{bronze_schema}.bronze_transactions t
LEFT JOIN {catalog}.{bronze_schema}.bronze_store_dim s
  ON t.store_number = s.store_number
WHERE s.store_number IS NULL;

-- Check for orphaned transactions (invalid product references)
SELECT
  'Orphaned transactions (invalid product)' as check_name,
  COUNT(*) as orphan_count
FROM {catalog}.{bronze_schema}.bronze_transactions t
LEFT JOIN {catalog}.{bronze_schema}.bronze_product_dim p
  ON t.upc_code = p.upc_code
WHERE p.upc_code IS NULL;
```

### Data Distribution Check

```sql
SELECT
  transaction_date,
  COUNT(*) as transaction_count,
  SUM(final_sales_price) as daily_revenue
FROM {catalog}.{bronze_schema}.bronze_transactions
GROUP BY transaction_date
ORDER BY transaction_date DESC
LIMIT 10;
```

### Verify Table Properties

```sql
-- Check that Change Data Feed is enabled
SHOW TBLPROPERTIES {catalog}.{bronze_schema}.bronze_transactions;

-- Verify specific property
SELECT *
FROM (SHOW TBLPROPERTIES {catalog}.{bronze_schema}.bronze_transactions)
WHERE key IN (
  'delta.enableChangeDataFeed',
  'layer',
  'domain',
  'data_purpose',
  'is_production'
);
```

### Verify Clustering

```sql
DESCRIBE DETAIL {catalog}.{bronze_schema}.bronze_transactions;
-- Check clusteringColumns is not empty
```

---

## Implementation Checklist

### Phase 1: Planning (15 min)

- [ ] Identify entities needed (5-10 tables)
- [ ] Choose data source approach (Faker / Existing / Copy)
- [ ] Define record counts for generation
- [ ] Assign domains and classifications
- [ ] Fill in requirements template

### Phase 2: Table Creation (30 min)

- [ ] Create `src/{project}_bronze/` directory
- [ ] Create `setup_tables.py` with table DDLs
- [ ] Define schema for each table
- [ ] Add governance metadata (TBLPROPERTIES)
- [ ] Use `CLUSTER BY AUTO` on all tables
- [ ] Include standard audit columns (`ingestion_timestamp`, `source_file`)

### Phase 3: Data Generation (30-45 min)

- [ ] **Option A (Faker):**
  - [ ] Create `generate_dimensions.py`
  - [ ] Create `generate_facts.py`
  - [ ] Ensure FK integrity (dimensions first)
  - [ ] Add realistic patterns
  - [ ] Set Faker seed for reproducibility
- [ ] **Option B (Copy):**
  - [ ] Create `copy_from_source.py`
  - [ ] Define table mappings
  - [ ] Test copy operation

### Phase 4: Asset Bundle Configuration (15 min)

- [ ] Create `resources/bronze_setup_job.yml`
- [ ] Create `resources/bronze_data_generator_job.yml`
- [ ] Add Faker dependency in environment spec
- [ ] Configure job parameters (catalog, schema, counts)
- [ ] Set task dependencies (dimensions before facts)

### Phase 5: Deployment & Validation (15 min)

- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run setup: `databricks bundle run bronze_setup_job -t dev`
- [ ] Run generator: `databricks bundle run bronze_data_generator_job -t dev`
- [ ] Run validation queries (record counts, FK integrity, distribution)
- [ ] Verify TBLPROPERTIES are set correctly

---

## Key Principles Checklist

### Test Data Quality

- [ ] Realistic patterns (not just random noise)
- [ ] Referential integrity (FKs point to valid records)
- [ ] Business logic (returns are negative, prices make sense)
- [ ] Reproducible (seeded for consistent results)

### Unity Catalog Compliance

- [ ] All tables in Unity Catalog
- [ ] Complete governance metadata (TBLPROPERTIES)
- [ ] Mark as `data_purpose: testing_demo`
- [ ] Mark as `is_production: false`

### Change Data Feed

- [ ] `'delta.enableChangeDataFeed' = 'true'` on all tables
- [ ] Required for downstream Silver layer DLT processing

### Automatic Liquid Clustering

- [ ] `CLUSTER BY AUTO` on all tables
- [ ] Never specify clustering columns manually

---

## Next Steps

After Bronze layer is complete:

1. **Silver Layer:** Proceed to Silver layer setup with DLT pipelines
2. **Verify Data:** Run all validation queries above
3. **Test Silver DQ:** Ensure data quality rules work with test data
4. **Iterate:** Adjust Faker generation for more realistic patterns

# Gold Layer Implementation Checklist

## Phase 1: Setup (30 min)

- [ ] YAML schema files exist in `gold_layer_design/yaml/` (from design phase)
- [ ] YAML files synced in `databricks.yml`
- [ ] PyYAML dependency added to job environment
- [ ] `setup_tables.py` created (generic YAML-driven script)
- [ ] `add_fk_constraints.py` created (separate FK script)
- [ ] Test YAML parsing locally

## Phase 2: Table Creation (30 min)

- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run: `databricks bundle run gold_setup_job -t dev`
- [ ] Verify tables created: `SHOW TABLES IN {gold_schema}`
- [ ] Verify PKs: `SHOW CREATE TABLE {table}`
- [ ] Verify FKs: `DESCRIBE TABLE EXTENDED {table}`
- [ ] Check table properties: `SHOW TBLPROPERTIES {table}`

## Phase 3: MERGE Implementation (2 hours)

- [ ] Create `merge_gold_tables.py`
- [ ] Implement dimension merges (SCD Type 1 or 2) with deduplication
- [ ] Implement fact merges with aggregation matching grain
- [ ] Add deduplication before every MERGE (mandatory)
- [ ] Add explicit column mapping (Silver to Gold names)
- [ ] Add schema validation before merge
- [ ] Add grain validation for fact tables
- [ ] Add error handling with try/except

## Phase 4: Testing (1 hour)

- [ ] Run: `databricks bundle run gold_merge_job -t dev`
- [ ] Verify record counts
- [ ] Verify grain (no duplicates at PK level)
- [ ] Verify FK relationships (no orphaned records)
- [ ] Verify SCD Type 2 (one `is_current = true` per business key)
- [ ] Check late-arriving data handling
- [ ] Validate column mappings

## Phase 5: Validation (30 min)

- [ ] Run schema validation queries
- [ ] Run grain validation queries
- [ ] Run FK integrity checks
- [ ] Check data quality metrics (NULLs, ranges)
- [ ] Verify audit timestamps populated

## Final Sign-Off

- [ ] All tables created with correct columns and constraints
- [ ] All merge scripts validated (schema, grain, deduplication)
- [ ] Asset Bundle jobs deploy and run successfully
- [ ] Gold tables contain correct data from Silver layer
- [ ] Ready for next phase: Metric Views, TVFs, Monitoring, Genie Space

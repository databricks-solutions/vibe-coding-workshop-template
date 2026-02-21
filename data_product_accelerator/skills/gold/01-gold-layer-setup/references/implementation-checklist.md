# Implementation Checklist & Key Principles

Complete validation checklists for Gold layer implementation. Use at the end of each phase and for final sign-off.

## Key Implementation Principles

1. **YAML as Source of Truth** — `setup_tables.py` AND `merge_gold_tables.py` both read YAML at runtime. Schema changes = YAML edits only. No embedded DDL strings, no hardcoded column lists.
2. **Extract, Don't Generate** — EVERY table name, column name, PK, FK, business key, grain type, SCD type, and column mapping MUST be extracted from Gold YAML or `COLUMN_LINEAGE.csv`. The ONLY things coded by hand are aggregation expressions and derived column formulas (business logic).
3. **Deduplication Always** — Every MERGE must deduplicate Silver first. No exceptions. Dedup key = `business_key` from YAML.
4. **Explicit Column Mapping from Lineage** — Never assume Silver names match Gold. Extract renames from YAML `lineage.source_column` or `COLUMN_LINEAGE.csv`.
5. **Schema Validation Before Merge** — Compare DataFrame columns against YAML `columns[]` list before every Delta MERGE.
6. **Grain Validation for Facts** — Read `grain` and `pk_columns` from YAML. Composite PK = aggregated. Single PK = transaction. Always validate before merge.
7. **FK Constraints After PKs** — Foreign keys in a SEPARATE script that reads `foreign_keys[]` from YAML. Runs AFTER all tables and their PKs exist.
8. **Merge Condition from PK** — Build MERGE ON clause programmatically from `primary_key.columns[]` in YAML. Never hardcode MERGE conditions.

## Setup Phase Checklist

- [ ] YAML files exist in `gold_layer_design/yaml/`
- [ ] YAML files synced in `databricks.yml`
- [ ] `setup_tables.py` reads YAML dynamically (no hardcoded DDL)
- [ ] PyYAML dependency in job environment
- [ ] Schema created with `CREATE SCHEMA IF NOT EXISTS`
- [ ] Predictive Optimization enabled
- [ ] Tables created with `CLUSTER BY AUTO`
- [ ] Standard TBLPROPERTIES applied (CDF, row tracking, etc.)
- [ ] PKs added via `ALTER TABLE` after creation
- [ ] FK constraints in separate script, runs after setup

## YAML Extraction Phase Checklist (BEFORE Writing Merge Code)

- [ ] `load_table_metadata()` helper included in merge script
- [ ] `build_inventory()` called in `main()` to load ALL table metadata from YAML
- [ ] `load_column_mappings_from_yaml()` or `load_column_mappings_from_csv()` used for renames
- [ ] `build_merge_condition()` used to construct MERGE ON clause from YAML PKs
- [ ] NO hardcoded table names — all come from `meta["table_name"]`
- [ ] NO hardcoded column lists — `.select(meta["columns"])` from YAML
- [ ] NO hardcoded MERGE conditions — built from `meta["pk_columns"]`
- [ ] NO hardcoded dedup keys — come from `meta["business_key"]`
- [ ] NO hardcoded grain columns — come from `meta["pk_columns"]`
- [ ] NO hardcoded Silver table names — come from `meta["source_tables"]`
- [ ] ONLY hand-coded items: aggregation expressions and derived column formulas

## Merge Phase Checklist

- [ ] Deduplication before EVERY merge (mandatory, key from YAML `business_key`)
- [ ] Deduplication key matches MERGE condition key (both from YAML)
- [ ] Column mappings extracted from YAML lineage or `COLUMN_LINEAGE.csv` (not guessed)
- [ ] No variable names shadow PySpark functions
- [ ] Schema validation: `validate_merge_schema()` called before every MERGE execute
- [ ] Grain validation for fact tables using YAML `pk_columns`
- [ ] Dimensions merged BEFORE facts (order from YAML `entity_type`)
- [ ] SCD Type 2 includes `is_current` filter (determined by YAML `scd_type`)
- [ ] Aggregated facts use `.groupBy(meta["pk_columns"])` from YAML
- [ ] `whenMatchedUpdate` columns built from YAML (not hardcoded set)
- [ ] Error handling with try/except and debug logging

## Deployment Phase Checklist

- [ ] Asset Bundle jobs use `notebook_task` (not `python_task`)
- [ ] Parameters use `base_parameters` dict
- [ ] FK task `depends_on` setup task
- [ ] Merge job has schedule (PAUSED in dev)
- [ ] Tags applied (environment, layer, job_type)
- [ ] Anomaly detection enabled on Gold schema (Phase 4b)

## Upstream Contract Validation Checklist (Phase 0)

- [ ] `scripts/validate_upstream_contracts.py` executed with project catalog and source schema
- [ ] ALL contracts PASS (zero column-not-found errors)
- [ ] Type compatibility validated (no implicit cast failures)
- [ ] Column resolution reports generated for ALL tables
- [ ] YAML lineage `silver_column` values match actual source table columns

## Advanced Patterns Checklist (If Applicable)

- [ ] Role-playing dimension views created (if `dimension_pattern: role_playing`)
- [ ] Unknown member rows inserted for ALL dimension tables
- [ ] Accumulating snapshot milestones progress correctly (if `grain_type: accumulating_snapshot`)
- [ ] Factless fact INSERT-only merge works (if `grain_type: factless`)
- [ ] Periodic snapshot full-period replacement works (if `grain_type: periodic_snapshot`)
- [ ] Junk dimension DISTINCT flag extraction works (if `dimension_pattern: junk`)
- [ ] Conformance validation for conformed dimensions (if applicable)

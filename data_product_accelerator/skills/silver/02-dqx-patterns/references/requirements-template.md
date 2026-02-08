# DQX Integration Requirements Template

## Instructions

Fill in this template before integrating DQX into your project. This ensures you have a clear plan and helps avoid scope creep.

---

## Tables to Enhance with DQX

| Priority | Table Name | Layer | Current Validation | DQX Use Case |
|----------|-----------|-------|-------------------|-------------|
| **Pilot** | _________________ | Silver | DLT expectations | Add diagnostics |
| **Priority 1** | _________________ | Silver/Gold | _________________ | _________________ |
| **Priority 2** | _________________ | Silver/Gold | _________________ | _________________ |
| **Full Rollout** | All Silver/Gold | Both | _________________ | _________________ |

## Quality Requirements

- **Complex Validations Needed:** [ ] Yes [ ] No
  - If yes, describe: _________________
- **Detailed Diagnostics:** [ ] Required [ ] Nice-to-have
- **Regulatory Compliance:** [ ] Yes [ ] No
  - If yes, which: _________________
- **Auto-Profiling for New Data Sources:** [ ] Yes [ ] No
- **Quality Dashboards:** [ ] Required [ ] Nice-to-have

## Integration Strategy

Choose one:

- [ ] **Hybrid (Recommended):** Keep DLT for speed, add DQX for diagnostics
- [ ] **DQX Only:** Replace all DLT expectations with DQX
- [ ] **Gold Pre-Merge Only:** DQX validates before MERGE into Gold
- [ ] **Pilot First:** Test on 1-2 tables before deciding

## Check Storage Strategy

Choose one:

- [ ] **YAML files** (version-controlled, simple)
- [ ] **Delta table** (centralized governance, history via CDF)
- [ ] **Lakebase** (PostgreSQL-compatible, available from 0.10.0)
- [ ] **Unity Catalog Volume** (file storage in UC)

## Team Readiness Checklist

- [ ] Team familiar with DQX concepts (profiling, checks, quarantine)
- [ ] DQX version selected (recommended: >=0.12.0)
- [ ] Compute configured (serverless with environment-level dependencies)
- [ ] Pilot table identified and documented
- [ ] Business rules documented for pilot table
- [ ] Quarantine strategy defined (drop, mark, or split)
- [ ] Monitoring/alerting plan for quarantine table
- [ ] Rollback plan documented

## DQX Version Decision

| Version | Key Features | Breaking Changes |
|---------|-------------|-----------------|
| 0.8.0 | `is_data_fresh`, unified `load_checks`/`save_checks` | `checks_file`/`checks_table` → `checks_location` |
| 0.9.x | `is_equal_to`, PII detection, multi-table, geospatial | Deprecated load/save methods removed |
| 0.10.0 | Summary metrics, LLM-assisted rules, Lakebase storage | New `InputConfig`/`OutputConfig` objects |
| 0.11.0 | ODCS Data Contracts, AI primary key detection | `level` → `criticality` in generator |
| 0.12.0 | Float support, JSON validation, geometry checks, AI rules from profiles | None |

**Recommended:** `>=0.12.0` for latest features and float support.

## Estimated Timeline

| Phase | Effort | Prerequisites |
|-------|--------|--------------|
| Phase 1: Silver Pilot | 3-4 hours | Pilot table identified |
| Phase 2: Delta Storage | 1-2 hours | Phase 1 complete |
| Phase 3: Gold Pre-Merge | 2-3 hours | Gold layer tables exist |
| Full Rollout | 1-2 days | All phases validated |

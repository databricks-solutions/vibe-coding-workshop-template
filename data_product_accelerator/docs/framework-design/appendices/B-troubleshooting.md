# Appendix B — Troubleshooting Guide

## Error Reference

### Error Categories

| Category | Description | Common Causes |
|----------|-------------|---------------|
| Skill Routing | Agent doesn't load the right skill | Missing keywords, ambiguous request |
| Context Budget | Agent gives incomplete/confused responses | Too many skills loaded in one conversation |
| Schema Mismatch | Generated code references wrong columns/tables | Hardcoded names instead of YAML extraction |
| Deployment | Asset Bundle deploy/run failures | Config errors, permission issues |
| Data Quality | DLT expectations fail, merge errors | Missing dedup, grain mismatch |

### Error-Solution Matrix

| Error Message | Root Cause | Solution |
|---------------|------------|----------|
| `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` | Duplicate business keys in Silver source | Add dedup-before-merge pattern (see `gold/pipeline-workers/03-deduplication`) |
| `AnalysisException: Column 'X' does not exist` | Hardcoded column name doesn't match actual schema | Extract column names from Gold YAML — never hardcode |
| `CONSTRAINT_ALREADY_EXISTS` | FK constraint applied twice | Use `IF NOT EXISTS` or check constraints before applying |
| `TABLE_OR_VIEW_NOT_FOUND` | Table referenced before creation | Ensure table creation jobs run before merge/constraint jobs |
| `bundle deploy` permission error | Insufficient workspace permissions | Verify user has `CAN_MANAGE` on jobs, `CREATE TABLE` on schema |
| Agent ignores skill content | Skill not loaded or wrong skill loaded | Use `@` syntax explicitly: `@data_product_accelerator/skills/{path}/SKILL.md` |
| Agent response is truncated/confused | Context budget exceeded | Start a new conversation; load fewer skills per turn |
| `ModuleNotFoundError` in notebook | `sys.path` not configured for Asset Bundle paths | Follow `databricks-python-imports` skill patterns |
| DLT pipeline fails to start | Missing `cluster_by_auto` or wrong table properties | Check `databricks-table-properties` skill for Silver patterns |
| Metric View creation fails | Column referenced doesn't exist in source table | Validate source table schema before creating Metric View |

## Diagnostic Procedures

### Quick Diagnostics

**Skill not loading?**
1. Verify the skill exists: check `data_product_accelerator/skills/{domain}/{skill-name}/SKILL.md`
2. Use explicit `@` reference in the prompt
3. Check if routing keywords match (see `AGENTS.md` or `data_product_accelerator/skills/skill-navigator/SKILL.md`)

**Wrong code generated?**
1. Check if "Extract, Don't Generate" was followed
2. Verify Gold YAML files exist in `gold_layer_design/yaml/`
3. Look for hardcoded table/column names in generated code

**Deployment failed?**
1. Run `databricks bundle validate -t dev` to check config
2. Check job logs: `databricks runs get --run-id {run_id}`
3. Invoke autonomous operations: `@data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md`

### Detailed Investigation

**For merge errors:**
1. Check if Silver table has duplicate business keys:
   ```sql
   SELECT {business_key}, COUNT(*) as cnt
   FROM {catalog}.silver.{table}
   GROUP BY {business_key}
   HAVING cnt > 1;
   ```
2. Verify merge condition matches PRIMARY KEY definition in Gold YAML
3. Ensure dedup window uses correct ordering column

**For schema validation errors:**
1. Compare DataFrame columns with Gold YAML:
   ```python
   # Get actual DataFrame columns
   df_cols = set(source_df.columns)
   # Get expected columns from YAML
   yaml_cols = set(col['name'] for col in yaml_schema['columns'])
   # Find mismatches
   missing = yaml_cols - df_cols
   extra = df_cols - yaml_cols
   ```

## Common Issues by Domain

### Gold Layer

#### Issue: MERGE produces duplicate rows

**Symptoms:**
- Gold table row count increases unexpectedly after merge
- Duplicate business key values in Gold table

**Diagnosis:**
```sql
SELECT {pk_column}, COUNT(*) FROM {catalog}.gold.{table}
GROUP BY {pk_column} HAVING COUNT(*) > 1;
```

**Solution:**
1. Add dedup-before-merge pattern from `gold/pipeline-workers/03-deduplication`
2. Verify merge condition uses the correct key columns
3. Check Silver table for duplicates

---

#### Issue: FK constraint fails with "referenced table does not exist"

**Symptoms:**
- `ALTER TABLE ADD CONSTRAINT FOREIGN KEY` throws error

**Solution:**
1. Ensure dimension tables are created and populated BEFORE fact tables
2. Run setup job → merge job → FK constraints job in correct order
3. Verify the referenced table name matches exactly (case-sensitive)

---

### Silver Layer

#### Issue: DLT pipeline stuck in "Starting"

**Symptoms:**
- Pipeline shows "Starting" indefinitely

**Solution:**
1. Check that the target schema exists
2. Verify serverless compute is available
3. Check for syntax errors in the pipeline notebook

---

### Semantic Layer

#### Issue: Genie returns wrong SQL

**Symptoms:**
- Genie generates queries against wrong tables or columns

**Solution:**
1. Verify table and column COMMENTs are descriptive and LLM-friendly
2. Check Genie Space agent instructions (should be under 20 lines)
3. Run the optimization loop from `semantic-layer/05-genie-optimization-orchestrator`

---

### Framework

#### Issue: Agent loads too many skills

**Symptoms:**
- Responses become slow or confused

**Solution:**
1. Start a new Cursor Agent conversation
2. Use one prompt per pipeline stage
3. Don't load orchestrator + multiple workers manually — let the orchestrator handle routing

## FAQ

### Q: Can I skip stages in the pipeline?

A: Yes. Stages 1-4 are sequential (each depends on the previous). Stages 6-9 are independent and can run in any order. Stage 5 (planning) is recommended but optional — downstream orchestrators fall back to self-discovery.

### Q: How do I add a new table to an existing Gold layer?

A: Add the YAML schema file to `gold_layer_design/yaml/{domain}/`, then re-run stage 4 (Gold Implementation). The YAML-driven setup script will create only new tables.

### Q: Can I use this framework without Cursor IDE?

A: The skills are standard Markdown files — any AI assistant that can read files can use them. However, the `@` reference syntax and Agent mode are Cursor-specific features.

### Q: How do I handle schema changes after initial deployment?

A: Update the Gold YAML files first (single source of truth), then re-run the Gold Implementation stage. The YAML-driven scripts handle `CREATE TABLE IF NOT EXISTS` and schema evolution.

### Q: What if my customer has 100+ source tables?

A: The framework scales to any size. For large schemas, the Gold Design stage will create domain-specific ERDs (not one massive master ERD). Use the scaling guidelines in the planning skill.

## Support Contacts

| Issue Type | Resource |
|------------|----------|
| Skill pattern errors | Run self-improvement skill: `@data_product_accelerator/skills/admin/self-improvement/SKILL.md` |
| Databricks platform issues | [Databricks Support](https://docs.databricks.com/support/) |
| Framework questions | Check this documentation set or the skill navigator |
| Bug reports | Submit via git issue on the repository |

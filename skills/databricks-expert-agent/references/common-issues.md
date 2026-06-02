# Common Issues Reference

Operational issues that recur across pipeline stages. These are not design anti-patterns (see `anti-patterns.md`) but practical gotchas with CLI tools, file discovery, and context management.

## SQL Execution from CLI

**Problem:** There is no `databricks sql` CLI command. Agents frequently attempt `databricks sql "SELECT ..."` and waste 2-3 calls debugging the error.

**Solution:** Use the SQL Statement Execution API:

```bash
databricks api post /api/2.0/sql/statements --json '{
  "warehouse_id": "'$WAREHOUSE_ID'",
  "statement": "SHOW TABLES IN catalog.schema",
  "wait_timeout": "30s",
  "disposition": "INLINE"
}'
```

**Polling for results** (when the query takes longer than `wait_timeout`):

```bash
databricks api get /api/2.0/sql/statements/$STATEMENT_ID
```

**Common fields in response:**
- `status.state`: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELED`
- `manifest.schema.columns[]`: column metadata
- `result.data_array[]`: row data (when `disposition: INLINE`)

**Alternative:** For multi-statement workflows, prefer notebooks executed via serverless jobs:
```yaml
tasks:
  - task_key: run_sql
    notebook_task:
      notebook_path: src/notebooks/setup_tables.py
```

---

## Glob Failure Recovery

**Problem:** `Glob("gold_layer_design/yaml/**/*.yaml")` returns 0 results. The agent assumes files don't exist and skips extraction, falling back to generation from memory. In reality, the files exist but the glob pattern is wrong (different directory structure, different extension, case sensitivity).

**Recovery protocol:**

1. **Verify with Shell before assuming absence:**
   ```bash
   ls -la gold_layer_design/
   ls -la gold_layer_design/yaml/
   ```

2. **Try broader patterns:**
   ```
   Glob("gold_layer_design/**/*")       # See what's actually there
   Glob("**/*.yaml")                     # Find all YAML files anywhere
   ```

3. **Check for alternative locations:**
   - Files might be in `gold_layer_design/yaml/` (flat, not nested by domain)
   - Files might use `.yml` instead of `.yaml`
   - Directory name might differ (e.g., `gold_design/` vs `gold_layer_design/`)

4. **Only after exhausting discovery** may you conclude files don't exist, then follow the Emergency Pattern in the main SKILL.md.

**Detection signal:** You are about to skip extraction because "the files weren't found" — but you only tried one glob pattern.

---

## Bulk Skill Loading

**Problem:** Loading multiple 500+ line skills early in the conversation causes context rot. Rules from skills read in Turns 2-3 lose salience by Turn 5+, when artifact generation actually begins. The agent "read the skill" but the content has decayed in attention by the time it matters.

**Guidance:**

1. **Read overviews first, full content on demand:**
   - Read the orchestrator SKILL.md (which lists dependencies)
   - Read common skill Essential Rules sections (compact, high-signal)
   - Read full worker skill content only when entering the phase that needs it

2. **Re-read before critical phases:**
   - If 3+ turns have passed since reading a skill, re-read its Essential Rules section before generating artifacts that depend on it
   - The Phase 0 Checkpoint in `databricks-expert-agent` forces this re-engagement naturally

3. **Token budget awareness:**
   - Each full skill read costs ~1,000-2,000 tokens of context
   - 8 common skills loaded at once = ~12,000 tokens before any work begins
   - Prefer just-in-time loading: read the skill immediately before the phase that uses it

**Detection signal:** You loaded 5+ skills in the first 2 turns but haven't started generating artifacts yet. By the time you do, the earliest skills will have lost salience.

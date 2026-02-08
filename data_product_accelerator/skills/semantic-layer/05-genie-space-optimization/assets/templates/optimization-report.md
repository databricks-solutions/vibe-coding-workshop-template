# {Domain} Genie Space Optimization Report

**Date:** {date}
**Space ID:** `{space_id}`
**Domain:** {domain_name}

---

## Executive Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **SQL Generation Rate** | {before_sql_gen}% | {after_sql_gen}% | {change_sql_gen} |
| **Asset Accuracy** | {before_accuracy}% | {after_accuracy}% | {change_accuracy} |
| **Repeatability** | {before_repeat}% | {after_repeat}% | {change_repeat} |

---

## Initial Assessment

### Accuracy Results

| Question ID | Question | Expected Asset | Actual Asset | Status |
|-------------|----------|---------------|--------------|--------|
| {id} | {question} | {expected} | {actual} | PASS/FAIL |
| ... | ... | ... | ... | ... |

**Accuracy:** {accuracy_pct}% ({pass_count}/{total_count})

### Repeatability Results

| Question ID | Question | Score | Variants | Dominant Asset |
|-------------|----------|-------|----------|---------------|
| {id} | {question} | {pct}% | {variants} | {asset} |
| ... | ... | ... | ... | ... |

**Average Repeatability:** {avg_repeat_pct}%

---

## Failure Analysis

### Wrong Asset Routing ({count} failures)

| Question | Expected | Got | Root Cause |
|----------|----------|-----|------------|
| {question} | {expected} | {actual} | {cause} |

### Low Repeatability ({count} questions)

| Question | Score | Issue | Fix Applied |
|----------|-------|-------|-------------|
| {question} | {pct}% | {issue} | {fix} |

---

## Optimizations Applied

### Control Lever Changes

| Lever | Change Description | Affected Questions |
|-------|-------------------|--------------------|
| Lever {N}: {name} | {description} | {question_ids} |

### Genie Instructions Update

**Before:**
```
{before_instructions}
```

**After:**
```
{after_instructions}
```

### UC Metadata Updates

```sql
-- Table/column comment changes
ALTER TABLE {table} ALTER COLUMN {column} COMMENT '{new_comment}';
```

---

## Post-Optimization Results

### Accuracy Re-Test

| Question ID | Before | After | Change |
|-------------|--------|-------|--------|
| {id} | FAIL | PASS | Fixed |
| ... | ... | ... | ... |

**New Accuracy:** {new_accuracy_pct}%

### Repeatability Re-Test

| Question ID | Before | After | Change |
|-------------|--------|-------|--------|
| {id} | {before_pct}% | {after_pct}% | +{change_pct}% |
| ... | ... | ... | ... |

**New Repeatability:** {new_repeat_pct}%

---

## Dual Persistence Confirmation

| Step | Status | Details |
|------|--------|---------|
| Direct API Update | {status} | PATCH `/api/2.0/genie/spaces/{space_id}` |
| Repository File Update | {status} | `src/genie/{domain}_genie_export.json` |
| Template Variables Preserved | {status} | `${catalog}`, `${gold_schema}` |
| Arrays Sorted | {status} | `sort_genie_config()` applied |

---

## Files Updated

1. `src/genie/{domain}_genie_export.json` - Genie Space configuration
2. `gold_layer_design/yaml/{domain}/*.yaml` - UC table metadata (if changed)
3. `src/semantic/metric_views/*.yaml` - Metric views (if changed)
4. `src/semantic/tvfs/*.sql` - TVFs (if changed)
5. `docs/genie_space_optimizer/{domain}_optimization_{date}.md` - This report

---

## Remaining Issues

| Question | Issue | Recommended Fix | Priority |
|----------|-------|-----------------|----------|
| {question} | {issue} | {fix} | High/Medium/Low |

---

## Key Learnings

1. {learning_1}
2. {learning_2}
3. {learning_3}

---

## Next Steps

- [ ] Re-test remaining failures after next deployment
- [ ] Monitor user feedback for new failure patterns
- [ ] Schedule follow-up optimization session in {timeframe}

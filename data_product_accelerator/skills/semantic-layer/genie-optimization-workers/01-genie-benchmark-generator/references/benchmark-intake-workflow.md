> **Standalone usage:** This reference can be used independently of the orchestrator. Load when creating or refreshing benchmark questions for any Genie Space optimization.

# Benchmark Question Intake Workflow (Optimization Context)

Interactive workflow for accepting, validating, and augmenting benchmark questions during Genie Space optimization. Tailored for the optimization loop where a live Genie Space already exists.

---

## Overview

Before running the optimization loop, benchmark questions must be established. This workflow handles three scenarios and validates questions against the **live Genie Space** (not just asset metadata).

| Scenario | Trigger | Action |
|----------|---------|--------|
| **Full intake** | User provides 10+ benchmark questions | Validate against live space, inform user of issues, proceed with valid set |
| **Partial intake** | User provides 1-9 benchmark questions | Validate provided, augment with synthetic to reach 10-15, proceed |
| **No intake** | User provides no benchmark questions | Inspect Genie Space assets via API, generate 10-15 synthetic benchmarks |

---

## Step 1: Prompt the User for Benchmark Questions

Before generating benchmarks or starting the optimization loop, always ask:

```markdown
### Benchmark Questions for Optimization

I need benchmark questions to test and optimize this Genie Space ({space_name}).
These questions will be used to measure accuracy and repeatability.

**Options:**
1. **Provide your own** — Submit questions your users are asking or should be able to ask
   (I'll validate each against the live Genie Space)
2. **Let me generate them** — I'll inspect the Genie Space's assets and generate
   benchmarks covering all question categories
3. **Provide a few, I'll augment** — Submit key questions and I'll fill gaps to
   reach the 10-15 benchmark minimum

**What makes a good benchmark question:**
- A natural language question a business user would ask
- Covers a specific use case (total/aggregate, top N, trend, comparison, detail)
- Optionally: the SQL you expect Genie to generate

**Example:**
> "What is our total compute spend this month?"
> "Show the top 10 most expensive workspaces"
> "How has daily cost trended over the last 2 weeks?"
```

---

## Step 2: Validate User-Submitted Questions Against Live Space

For optimization, validation goes beyond metadata — check the live Genie Space's trusted assets.

### Validation Pipeline

```python
def validate_benchmark_for_optimization(
    question: dict,
    space_id: str,
    space_config: dict
) -> dict:
    """
    Validate a user-submitted benchmark question against a live Genie Space.
    
    Args:
        question: {"question": str, "expected_sql": str|None, "expected_asset": str|None}
        space_id: Live Genie Space ID
        space_config: Genie Space config from GET /api/2.0/genie/spaces/{space_id}
    
    Returns:
        {"status": "valid"|"needs_info"|"invalid", "issues": [], "suggestions": []}
    """
    issues = []
    suggestions = []
    
    # Extract trusted assets from live space config
    trusted_tables = extract_trusted_tables(space_config)
    trusted_mvs = extract_trusted_metric_views(space_config)
    trusted_tvfs = extract_trusted_tvfs(space_config)
    all_assets = {
        "metric_views": trusted_mvs,
        "tvfs": trusted_tvfs,
        "tables": trusted_tables
    }
    
    # Check 1: Does the question match any trusted asset in the space?
    matching = find_matching_assets(question["question"], all_assets)
    if not matching:
        issues.append({
            "type": "no_matching_asset",
            "message": f"No trusted asset in space '{space_id}' can answer: '{question['question']}'",
            "detail": f"Trusted assets: {[a['name'] for a in trusted_tables + trusted_mvs + trusted_tvfs]}"
        })
        suggestions.append("Rephrase to use data available in the space")
        suggestions.append("Add the required table as a trusted asset first")
    
    # Check 2: If expected_sql references specific objects, verify they're trusted
    if question.get("expected_sql"):
        all_names = {a["name"].lower() for a in trusted_tables + trusted_mvs + trusted_tvfs}
        referenced = extract_sql_object_references(question["expected_sql"])
        missing = referenced - all_names
        for obj in missing:
            issues.append({
                "type": "missing_trusted_asset",
                "message": f"SQL references '{obj}' which is not a trusted asset in this Genie Space",
                "detail": "The object may exist in the catalog but isn't added to this space."
            })
            suggestions.append(f"Add '{obj}' as a trusted asset, or rewrite SQL to use: {sorted(all_names)}")
    
    # Check 3: MEASURE() validation against actual metric view columns
    if question.get("expected_sql") and "MEASURE(" in question["expected_sql"].upper():
        for mv in trusted_mvs:
            measure_cols = {m["name"].lower() for m in mv.get("measures", [])}
            used_measures = extract_measure_references(question["expected_sql"])
            invalid = used_measures - measure_cols
            for col in invalid:
                issues.append({
                    "type": "invalid_measure",
                    "message": f"MEASURE({col}) not found in metric view '{mv['name']}'",
                    "detail": f"Available measures: {sorted(measure_cols)}"
                })
    
    # Check 4: Ambiguity check
    ambiguous_terms = detect_ambiguous_terms(question["question"])
    if ambiguous_terms:
        # Check if Genie Instructions already define the term
        instructions = space_config.get("instructions", {}).get("text", "")
        undefined = [t for t in ambiguous_terms if t.lower() not in instructions.lower()]
        if undefined:
            issues.append({
                "type": "ambiguous_term",
                "message": f"Ambiguous terms not defined in Genie Instructions: {undefined}",
                "detail": "These terms may cause inconsistent Genie responses."
            })
            suggestions.append(f"Define '{undefined[0]}' in the question or add to Genie Instructions")
    
    # Determine status
    if not issues:
        status = "valid"
    elif all(i["type"] in ("ambiguous_term",) for i in issues):
        status = "needs_info"
    elif any(i["type"] in ("no_matching_asset", "missing_trusted_asset") for i in issues):
        status = "invalid"
    else:
        status = "needs_info"
    
    return {"status": status, "issues": issues, "suggestions": suggestions}
```

### Validation Checks (Optimization-Specific)

| Check | What It Verifies | Failure Response to User |
|-------|-----------------|--------------------------|
| **Trusted asset match** | Question maps to a trusted asset in the live space | "No trusted asset in this space can answer that. Available assets: {list}. Add the required table or rephrase." |
| **SQL object references** | Referenced tables/views are trusted in the space | "'{table}' exists in catalog but isn't a trusted asset in this Genie Space. Add it first." |
| **MEASURE() columns** | Columns match live metric view schema | "MEASURE({col}) not found. Available measures: {list}." |
| **Ambiguous terms** | Terms are defined in Genie Instructions | "'{term}' is ambiguous and not defined in this space's instructions. How should it be interpreted?" |
| **Category coverage** | Benchmark set covers required categories | "Your questions only cover aggregation. Need ranking, time-series, comparison, or list questions too." |

### User Feedback Template

```markdown
### Benchmark Validation Results

**Space:** {space_name} ({space_id})
**Submitted:** {N} questions
**Valid:** {valid_count} — ready for optimization testing
**Needs clarification:** {needs_info_count}
**Cannot be tested:** {invalid_count}

#### Valid Questions
- "What is total compute spend this month?" — maps to mv_cost_analytics (MV)
- "Show top 10 costliest workspaces" — maps to get_top_cost_contributors (TVF)

#### Questions Needing Clarification
- "Show underperforming workspaces"
  Issue: "underperforming" not defined in Genie Instructions.
  Options: (a) Define it (e.g., cost above median), (b) I'll add definition to instructions as part of optimization

#### Questions That Cannot Be Tested
- "What is our customer churn rate?"
  Issue: No churn-related table is a trusted asset in this space.
  Trusted assets: mv_cost_analytics, get_top_cost_contributors, get_daily_cost_summary, dim_sku
  Suggestion: Rephrase using available cost/usage data, or add a churn table to the space first.

**Next:** {action based on count — proceed / augment / generate}
```

---

## Step 3: Generate Synthetic Benchmarks from Live Space

When the user provides no questions, inspect the live Genie Space and generate benchmarks.

### Discovery from Live Space

```python
def generate_benchmarks_from_live_space(space_id: str, space_config: dict) -> list:
    """
    Generate synthetic benchmarks by inspecting a live Genie Space's assets.
    
    Reads trusted assets from the space config and generates questions
    covering all required categories.
    """
    benchmarks = []
    
    # Extract assets from live config
    metric_views = extract_trusted_metric_views(space_config)
    tvfs = extract_trusted_tvfs(space_config)
    tables = extract_trusted_tables(space_config)
    
    # Get column/measure metadata from catalog for richer generation
    for mv in metric_views:
        mv_details = get_metric_view_details(mv["name"])
        
        # Generate aggregation questions from measures
        for measure in mv_details.get("measures", []):
            benchmarks.append({
                "id": f"syn_{len(benchmarks)+1:03d}",
                "question": f"What is the {measure_to_natural_language(measure)}?",
                "expected_sql": f"SELECT MEASURE({measure['name']}) FROM ${{catalog}}.${{gold_schema}}.{mv['name']}",
                "expected_asset": "MV",
                "category": "aggregation",
                "source": "synthetic"
            })
        
        # Generate comparison questions
        benchmarks.append({
            "id": f"syn_{len(benchmarks)+1:03d}",
            "question": f"Compare {mv_details['primary_measure']} this month vs last month",
            "expected_sql": generate_comparison_sql(mv),
            "expected_asset": "MV",
            "category": "comparison",
            "source": "synthetic"
        })
    
    # Generate from TVFs
    for tvf in tvfs:
        tvf_details = get_tvf_details(tvf["name"])
        benchmarks.append({
            "id": f"syn_{len(benchmarks)+1:03d}",
            "question": tvf_to_natural_question(tvf_details),
            "expected_sql": generate_tvf_call_sql(tvf_details),
            "expected_asset": "TVF",
            "category": categorize_tvf(tvf_details),
            "source": "synthetic"
        })
    
    # Generate from tables (list/detail only)
    for table in tables:
        if len(benchmarks) < 15:
            benchmarks.append({
                "id": f"syn_{len(benchmarks)+1:03d}",
                "question": f"What distinct {table_to_entity(table)} do we have?",
                "expected_sql": f"SELECT DISTINCT {table['key_column']} FROM ${{catalog}}.${{gold_schema}}.{table['name']} ORDER BY 1",
                "expected_asset": "TABLE",
                "category": "list",
                "source": "synthetic"
            })
    
    # Ensure category coverage
    benchmarks = ensure_category_coverage(benchmarks, metric_views, tvfs, tables)
    
    return benchmarks[:15]
```

### Presentation to User

After generating synthetic benchmarks, always show them for review:

```markdown
### Generated Benchmark Questions

I inspected the Genie Space and generated {N} benchmark questions:

| # | Question | Asset | Category |
|---|----------|-------|----------|
| 1 | What is our total compute spend this month? | MV | aggregation |
| 2 | What is our average daily cost? | MV | aggregation |
| 3 | Show the top 10 most expensive workspaces | TVF | ranking |
| 4 | Show daily cost breakdown for the last 2 weeks | TVF | time-series |
| 5 | Compare this month's cost to last month | MV | comparison |
| ... | ... | ... | ... |

**Category coverage:** aggregation (3), ranking (2), time-series (2), comparison (2), list (1)

Would you like to:
- **Proceed** with these benchmarks
- **Add** your own questions to the set
- **Remove** any you don't want tested
- **Modify** any question's wording
```

---

## Step 4: Augment Partial Submissions

When the user provides fewer than 10 questions, augment with synthetic while preserving user questions.

### Augmentation Strategy

```python
def augment_optimization_benchmarks(
    user_questions: list,
    space_config: dict,
    target_count: int = 15
) -> list:
    """
    Augment user-provided questions with synthetic ones for the optimization loop.
    
    Rules:
    1. User questions always preserved (never replaced or reworded)
    2. Fill category gaps first (if user only has aggregation, add ranking/time-series)
    3. Add asset coverage gaps second (if user only tests MVs, add TVF questions)
    4. Add synonym/date variations third
    5. Cap at target_count
    """
    validated = [q for q in user_questions if q["validation"]["status"] == "valid"]
    augmented = list(validated)
    
    # Analyze coverage gaps
    covered_categories = {q.get("category") for q in validated}
    covered_assets = {q.get("expected_asset") for q in validated}
    required_categories = {"aggregation", "ranking", "time-series", "comparison", "list"}
    
    metric_views = extract_trusted_metric_views(space_config)
    tvfs = extract_trusted_tvfs(space_config)
    tables = extract_trusted_tables(space_config)
    
    # Priority 1: Fill missing categories
    for category in required_categories - covered_categories:
        synthetic = generate_for_category(category, metric_views, tvfs, tables)
        augmented.extend(synthetic[:2])
    
    # Priority 2: Fill missing asset types
    if "MV" not in covered_assets and metric_views:
        augmented.append(generate_mv_question(metric_views[0]))
    if "TVF" not in covered_assets and tvfs:
        augmented.append(generate_tvf_question(tvfs[0]))
    
    # Priority 3: Add synonym variations for key user questions
    if len(augmented) < target_count:
        for q in validated[:3]:
            synonyms = generate_synonym_variations(q)
            augmented.extend(synonyms[:2])
    
    # Priority 4: Add date range variations
    if len(augmented) < target_count:
        for q in validated[:2]:
            if has_time_component(q["question"]):
                date_vars = generate_date_variations(q)
                augmented.extend(date_vars[:2])
    
    # Assign IDs to synthetic additions
    for i, q in enumerate(augmented):
        if q.get("source") == "synthetic" and not q.get("id"):
            q["id"] = f"aug_{i+1:03d}"
    
    return augmented[:target_count]
```

### Augmentation Report

```markdown
### Augmented Benchmark Suite

**Your questions:** {user_count} (validated and preserved)
**Synthetic additions:** {synthetic_count} (to fill coverage gaps)
**Total:** {total_count}

#### Your Questions
1. "What is total compute spend?" — MV, aggregation
2. "Show top workspaces by cost" — TVF, ranking

#### Synthetic Additions (Category Gaps)
3. "Show daily cost trend for the last 2 weeks" — TVF, time-series (fills gap)
4. "Compare this month's cost to last month" — MV, comparison (fills gap)
5. "What SKU categories do we use?" — TABLE, list (fills gap)

#### Synthetic Additions (Variations)
6. "How much have we spent in total?" — MV, aggregation (synonym of #1)
7. "What are our total costs this quarter?" — MV, aggregation (date variation of #1)

**Category coverage:** aggregation (3), ranking (1), time-series (1), comparison (1), list (1) — 5/5 required

Shall I proceed with this benchmark suite, or would you like to adjust?
```

---

## Integration with Optimization Loop

This workflow plugs into **Step 1** of the optimization loop:

```
Step 0: Identify Genie Space → get space_id
                                     ↓
Step 1: Benchmark Intake  → prompt user
                           → validate / generate / augment
                           → save to golden-queries.yaml
                                     ↓
Step 2: Query Genie       → run benchmarks via Conversation API
```

### Ground Truth Validation Step

After validation and before saving, every benchmark's `expected_sql` must be executed on the warehouse:

```python
for q in final_benchmarks:
    result = validate_ground_truth_sql(q["expected_sql"], spark)
    if result["valid"]:
        q["expected_result_hash"] = result["result_hash"]
        q["expected_result_sample"] = result["result_sample"]
        q["expected_row_count"] = result["row_count"]
    else:
        # LLM regenerates SQL (max 3 attempts)
        result = validate_with_retry(q["expected_sql"], spark, llm_regenerate_fn, max_attempts=3)
        if result["valid"]:
            q["expected_sql"] = result["final_sql"]
            q["expected_result_hash"] = result["result_hash"]
            q["expected_result_sample"] = result["result_sample"]
            q["expected_row_count"] = result["row_count"]
        else:
            print(f"  WARNING: GT validation failed for {q['id']} after 3 attempts: {result['error']}")
            q["gt_validation_status"] = "failed"
```

### Auto-Populate Metadata Dependencies

Extract `required_tables`, `required_columns`, and `required_joins` from `expected_sql`:

```python
import re

for q in final_benchmarks:
    sql = q.get("expected_sql", "").lower()
    tables = re.findall(r'from\s+([\w.]+)', sql) + re.findall(r'join\s+([\w.]+)', sql)
    q.setdefault("required_tables", list(set(t.split(".")[-1] for t in tables)))
```

### Saving Benchmarks

After the intake workflow completes, save to the golden-queries YAML:

```python
import yaml

benchmarks_yaml = {
    domain: [
        {
            "id": q["id"],
            "question": q["question"],
            "expected_sql": q["expected_sql"],
            "expected_asset": q["expected_asset"],
            "category": q["category"],
            "source": q.get("source", "user"),
            "required_tables": q.get("required_tables", []),
            "expected_facts": q.get("expected_facts", []),
            "expected_result_hash": q.get("expected_result_hash", ""),
            "expected_result_sample": q.get("expected_result_sample", ""),
            "expected_row_count": q.get("expected_row_count", 0),
        }
        for q in final_benchmarks
    ]
}

with open("tests/optimizer/genie_golden_queries.yml", "w") as f:
    yaml.dump(benchmarks_yaml, f, default_flow_style=False, sort_keys=False)
```

### MLflow Sync Step

After saving to YAML, sync to the MLflow Evaluation Dataset:

```python
dataset_name = sync_yaml_to_mlflow_dataset(yaml_path, uc_schema, domain)
print(f"Synced {len(final_benchmarks)} benchmarks to {dataset_name}")
```

### Re-Intake After Failed Optimization

If the optimization loop exhausts 5 iterations without meeting targets, the benchmark intake can be re-triggered:

1. Present failing questions to the user
2. Ask if any questions should be reworded, replaced, or removed
3. Check if any arbiter corrections were made (ground truth may have been wrong)
4. Re-validate the modified set (including GT SQL execution)
5. Re-sync to MLflow Evaluation Dataset
6. Restart the optimization loop with the updated benchmarks

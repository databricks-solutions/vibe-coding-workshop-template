# Benchmark Question Intake Workflow

Interactive workflow for accepting, validating, and augmenting benchmark questions during Genie Space setup.

---

## Overview

Benchmark questions are critical to Genie Space quality — they validate that Genie routes correctly, generates accurate SQL, and returns expected results. This workflow handles three scenarios:

| Scenario | Trigger | Action |
|----------|---------|--------|
| **Full intake** | User provides 10+ benchmark questions | Validate all, inform user of issues, proceed with valid set |
| **Partial intake** | User provides 1-9 benchmark questions | Validate provided, augment with synthetic to reach 10-15 total |
| **No intake** | User provides no benchmark questions | Generate 10-15 synthetic benchmarks from asset metadata |

---

## Step 1: Prompt the User for Benchmark Questions

Before generating any benchmarks, always ask the user first:

```markdown
### Benchmark Questions

I need benchmark questions to validate this Genie Space. These are natural language
questions paired with expected SQL that verify Genie returns correct answers.

**Options:**
1. **Provide your own** — Submit questions your business users commonly ask
   (I'll validate each one against the available data assets)
2. **Let me generate them** — I'll create synthetic benchmarks from the
   metric views, TVFs, and tables in this space
3. **Provide a few, I'll augment** — Submit what you have and I'll fill
   in the gaps to reach the 10-15 minimum

**Format for submitted questions:**
- Natural language question (how a business user would ask)
- Optionally include expected SQL (I'll generate it if not provided)
- Optionally specify which asset should answer it (MV, TVF, or TABLE)

**Example:**
> "What is our total revenue this month?"
> "Show the top 10 properties by booking count"
> "How does this quarter compare to last quarter?"
```

---

## Step 2: Validate User-Submitted Questions

For each user-submitted question, run a validation pipeline. Report issues to the user rather than silently dropping questions.

### Validation Pipeline

```python
def validate_benchmark_question(question: dict, available_assets: dict) -> dict:
    """
    Validate a user-submitted benchmark question against available assets.
    
    Args:
        question: {"question": str, "expected_sql": str|None, "expected_asset": str|None}
        available_assets: {
            "metric_views": [{"name": ..., "measures": [...], "dimensions": [...]}],
            "tvfs": [{"name": ..., "signature": ..., "parameters": [...]}],
            "tables": [{"name": ..., "columns": [...]}]
        }
    
    Returns:
        {"status": "valid"|"needs_info"|"invalid", "issues": [...], "suggestions": [...]}
    """
    issues = []
    suggestions = []
    
    # Check 1: Can any available asset answer this question?
    matching_assets = find_matching_assets(question["question"], available_assets)
    if not matching_assets:
        issues.append({
            "type": "no_matching_asset",
            "message": f"No available asset can answer: '{question['question']}'",
            "detail": "The question references data not covered by any metric view, TVF, or table in this space."
        })
    
    # Check 2: If expected_sql provided, validate table/view references
    if question.get("expected_sql"):
        missing_objects = validate_sql_references(question["expected_sql"], available_assets)
        for obj in missing_objects:
            issues.append({
                "type": "missing_table",
                "message": f"SQL references '{obj}' which is not a trusted asset in this space",
                "detail": "Add the table/view as a trusted asset, or rewrite the SQL to use an existing asset."
            })
    
    # Check 3: If expected_sql uses MEASURE(), validate column names
    if question.get("expected_sql") and "MEASURE(" in question["expected_sql"].upper():
        invalid_measures = validate_measure_columns(question["expected_sql"], available_assets["metric_views"])
        for col in invalid_measures:
            issues.append({
                "type": "invalid_measure",
                "message": f"MEASURE({col}) uses a display name or non-existent column",
                "detail": "MEASURE() requires actual column names, not display names."
            })
    
    # Check 4: Is the question too vague to validate?
    if is_ambiguous_question(question["question"]):
        issues.append({
            "type": "ambiguous",
            "message": f"Question may be too vague: '{question['question']}'",
            "detail": "Consider adding specifics (time range, metric, entity)."
        })
        suggestions.append("Add a time qualifier (e.g., 'this month', 'last 30 days')")
        suggestions.append("Specify the metric (e.g., 'by revenue', 'by count')")
    
    # Determine overall status
    if not issues:
        status = "valid"
    elif all(i["type"] == "ambiguous" for i in issues):
        status = "needs_info"
    elif any(i["type"] in ("missing_table", "no_matching_asset") for i in issues):
        status = "invalid"
    else:
        status = "needs_info"
    
    return {"status": status, "issues": issues, "suggestions": suggestions}
```

### Validation Checks

| Check | What It Verifies | Failure Response to User |
|-------|-----------------|--------------------------|
| **Asset coverage** | At least one MV/TVF/table can answer the question | "This question references data not available in the Genie Space. Available domains: {list}. Please rephrase or add the required table." |
| **Table existence** | SQL references only trusted assets in the space | "The SQL references `{table}` which isn't a trusted asset. Available assets: {list}." |
| **MEASURE() columns** | Column names match actual MV column names | "MEASURE({col}) doesn't match any column. Available measures: {list}." |
| **UC namespace** | SQL uses full 3-part namespace | "SQL must use `${catalog}.${gold_schema}.{object}` format." |
| **TVF parameters** | All required TVF parameters present | "TVF `{name}` requires parameters: {params}. Your SQL is missing: {missing}." |
| **Ambiguity** | Question is specific enough to validate | "This question is ambiguous — what does '{term}' mean in your context? (e.g., 'underperforming' = lowest revenue? lowest ratings?)" |

### User Feedback Template

After validation, present results to the user:

```markdown
### Benchmark Question Validation Results

**Submitted:** {N} questions
**Valid:** {valid_count} — ready to use
**Needs clarification:** {needs_info_count} — I need more information
**Cannot be answered:** {invalid_count} — data not available

#### Valid Questions
{list valid questions with checkmarks}

#### Questions Needing Clarification
{for each, explain what's needed}

**Example:**
> "Show underperforming properties"
> Issue: "underperforming" is ambiguous. How should this be defined?
> - Below median revenue?
> - Below average ratings?
> - Negative growth trend?
> Please clarify so I can write the expected SQL.

#### Questions That Cannot Be Answered
{for each, explain why and suggest alternatives}

**Example:**
> "What is our customer churn rate?"
> Issue: No table in this Genie Space contains churn data.
> Available domains: revenue, bookings, property performance.
> Suggestion: Rephrase to use available data, e.g., "Which properties had no bookings last month?"
```

---

## Step 3: Generate Synthetic Benchmark Questions

When the user provides no questions or fewer than the minimum, generate synthetic benchmarks from asset metadata.

### Generation Strategy

```python
def generate_synthetic_benchmarks(available_assets: dict, existing_questions: list = None) -> list:
    """
    Generate synthetic benchmark questions from available asset metadata.
    
    Generates questions across all required categories, avoiding duplicates
    with any user-provided questions.
    """
    existing_questions = existing_questions or []
    benchmarks = []
    
    # Determine how many to generate
    target_count = max(10, 15 - len(existing_questions))
    existing_categories = {q.get("category") for q in existing_questions}
    
    # Phase 1: Generate from Metric Views (aggregation, comparison)
    for mv in available_assets["metric_views"]:
        for measure in mv["measures"]:
            # Aggregation question
            benchmarks.append({
                "id": f"{mv['domain']}_{len(benchmarks)+1:03d}",
                "question": f"What is the {measure['description'].lower()}?",
                "expected_sql": f"SELECT MEASURE({measure['name']}) FROM ${{catalog}}.${{gold_schema}}.{mv['name']}",
                "expected_asset": "MV",
                "category": "aggregation",
                "source": "synthetic"
            })
            
            # Dimension breakdown question
            if mv.get("dimensions"):
                dim = mv["dimensions"][0]
                benchmarks.append({
                    "id": f"{mv['domain']}_{len(benchmarks)+1:03d}",
                    "question": f"What is {measure['description'].lower()} by {dim['description'].lower()}?",
                    "expected_sql": f"SELECT {dim['name']}, MEASURE({measure['name']}) FROM ${{catalog}}.${{gold_schema}}.{mv['name']} GROUP BY {dim['name']} ORDER BY MEASURE({measure['name']}) DESC",
                    "expected_asset": "MV",
                    "category": "aggregation",
                    "source": "synthetic"
                })
    
    # Phase 2: Generate from TVFs (ranking, time-series, list, detail)
    for tvf in available_assets["tvfs"]:
        benchmarks.append({
            "id": f"tvf_{len(benchmarks)+1:03d}",
            "question": generate_natural_question_for_tvf(tvf),
            "expected_sql": generate_expected_sql_for_tvf(tvf),
            "expected_asset": "TVF",
            "category": categorize_tvf(tvf),
            "source": "synthetic"
        })
    
    # Phase 3: Generate from Tables (list, detail — only if needed)
    for table in available_assets["tables"]:
        if len(benchmarks) < target_count:
            benchmarks.append({
                "id": f"tbl_{len(benchmarks)+1:03d}",
                "question": f"What {table['entity_plural']} do we have?",
                "expected_sql": f"SELECT DISTINCT {table['key_columns'][0]} FROM ${{catalog}}.${{gold_schema}}.{table['name']} ORDER BY {table['key_columns'][0]}",
                "expected_asset": "TABLE",
                "category": "list",
                "source": "synthetic"
            })
    
    # Phase 4: Ensure category coverage
    required_categories = {"aggregation", "ranking", "time-series", "comparison", "list"}
    covered = {b["category"] for b in benchmarks} | existing_categories
    missing = required_categories - covered
    
    for category in missing:
        benchmarks.append(generate_category_filler(category, available_assets))
    
    # Deduplicate against existing questions
    benchmarks = deduplicate_benchmarks(benchmarks, existing_questions)
    
    return benchmarks[:target_count]
```

### Asset-to-Question Mapping

| Asset Type | Question Categories Generated | Example |
|-----------|------------------------------|---------|
| **Metric View** (per measure) | aggregation, comparison | "What is total revenue?" / "Compare revenue this month vs last" |
| **Metric View** (per dimension) | aggregation (grouped) | "Revenue by property type?" |
| **TVF** (ranking type) | ranking | "Show top 10 costliest workspaces" |
| **TVF** (time-series type) | time-series | "Daily cost breakdown for last 2 weeks" |
| **TVF** (detail type) | detail, list | "Show details for workspace X" |
| **Table** (dimension) | list | "What SKU categories do we have?" |

### Category Coverage Requirements

Synthetic generation must ensure minimum category coverage:

| Domain Size | Total Questions | Min Categories | Mandatory Categories |
|-------------|----------------|---------------|---------------------|
| Small (1-3 tables) | 10 | 4 | aggregation, ranking, list + 1 more |
| Medium (4-8 tables) | 15 | 6 | aggregation, ranking, time-series, comparison, list + 1 more |
| Large (9+ tables) | 20-25 | 8 | All categories |

---

## Step 4: Augment Partial Submissions

When the user provides fewer than 10 questions, augment intelligently:

### Augmentation Strategy

```python
def augment_benchmarks(user_questions: list, available_assets: dict) -> list:
    """
    Augment user-submitted questions with synthetic ones to reach minimum count.
    
    Rules:
    1. User questions always take priority (never replaced)
    2. Synthetic questions fill category gaps first
    3. Synthetic questions add synonym/date variations second
    4. Final set has 10-15 questions with 4+ categories
    """
    validated = [q for q in user_questions if q["status"] == "valid"]
    target = max(10, len(validated) + 5)  # At least 5 more than user provided
    
    # Analyze what's already covered
    covered_categories = {q.get("category") for q in validated}
    covered_assets = {q.get("expected_asset") for q in validated}
    covered_topics = extract_topics(validated)
    
    augmented = list(validated)
    
    # Priority 1: Fill missing categories
    required_categories = {"aggregation", "ranking", "time-series", "comparison", "list"}
    for category in required_categories - covered_categories:
        synthetic = generate_for_category(category, available_assets, covered_topics)
        augmented.extend(synthetic)
    
    # Priority 2: Add synonym variations for user questions
    if len(augmented) < target:
        for q in validated[:3]:
            synonyms = generate_synonym_variations(q, count=2)
            augmented.extend(synonyms)
    
    # Priority 3: Add date range variations
    if len(augmented) < target:
        for q in validated[:2]:
            date_vars = generate_date_variations(q)
            augmented.extend(date_vars)
    
    # Priority 4: Fill remaining with synthetic
    if len(augmented) < target:
        remaining = generate_synthetic_benchmarks(available_assets, augmented)
        augmented.extend(remaining[:target - len(augmented)])
    
    return augmented[:15]  # Cap at 15
```

### Augmentation Report to User

After augmentation, show the user what was added:

```markdown
### Benchmark Suite (Augmented)

**Your questions:** {user_count} (kept as-is)
**Synthetic additions:** {synthetic_count}
**Total:** {total_count}

#### Your Questions (Validated)
1. "What is total revenue this month?" — Valid, MV, aggregation
2. "Show top 10 properties" — Valid, TVF, ranking
3. "Compare Q1 vs Q2 revenue" — Valid, MV, comparison

#### Synthetic Additions
4. "What is the average booking value?" — MV, aggregation (fills measure coverage gap)
5. "Show daily revenue for the last 2 weeks" — TVF, time-series (fills category gap)
6. "Which property types do we offer?" — TABLE, list (fills category gap)
7. "How much revenue did we generate last month?" — MV, aggregation (synonym variation of #1)
8. ... (continue)

**Category coverage:** aggregation (3), ranking (2), time-series (2), comparison (1), list (2) — 5/5 required categories covered

Would you like to review or modify any of these before proceeding?
```

---

## Decision Flowchart

```
User provides benchmark questions?
│
├── YES (10+ questions)
│   ├── Validate each question (Step 2)
│   ├── Report issues to user
│   │   ├── Invalid questions: explain WHY (missing table, no data)
│   │   ├── Needs-info questions: ask for clarification
│   │   └── Valid questions: confirm with checkmark
│   ├── If <10 valid after filtering → augment (Step 4)
│   └── Proceed with validated set
│
├── YES (1-9 questions)
│   ├── Validate each question (Step 2)
│   ├── Report issues to user
│   ├── Augment to reach 10-15 total (Step 4)
│   ├── Show augmentation report
│   └── Proceed with combined set
│
└── NO (0 questions)
    ├── Inspect all available assets (MVs, TVFs, tables)
    ├── Generate 10-15 synthetic benchmarks (Step 3)
    ├── Show generated benchmarks to user for review
    └── Proceed with synthetic set
```

---

## Validation Helper Functions

### find_matching_assets

```python
def find_matching_assets(question: str, available_assets: dict) -> list:
    """Find which assets could answer a question based on keyword matching."""
    matches = []
    question_lower = question.lower()
    
    for mv in available_assets["metric_views"]:
        keywords = extract_keywords(mv)
        if any(kw in question_lower for kw in keywords):
            matches.append({"type": "MV", "name": mv["name"]})
    
    for tvf in available_assets["tvfs"]:
        keywords = extract_keywords(tvf)
        if any(kw in question_lower for kw in keywords):
            matches.append({"type": "TVF", "name": tvf["name"]})
    
    for table in available_assets["tables"]:
        keywords = extract_keywords(table)
        if any(kw in question_lower for kw in keywords):
            matches.append({"type": "TABLE", "name": table["name"]})
    
    return matches
```

### validate_sql_references

```python
def validate_sql_references(sql: str, available_assets: dict) -> list:
    """Check that all table/view/function references in SQL exist as trusted assets."""
    import re
    
    all_asset_names = set()
    for asset_type in ["metric_views", "tvfs", "tables"]:
        for asset in available_assets.get(asset_type, []):
            all_asset_names.add(asset["name"].lower())
    
    referenced = set()
    # Match FROM/JOIN clauses (handles ${catalog}.${schema}.name format)
    pattern = r'(?:FROM|JOIN)\s+(?:\$\{[^}]+\}\.)?\s*(?:\$\{[^}]+\}\.)?\s*(\w+)'
    for match in re.finditer(pattern, sql, re.IGNORECASE):
        referenced.add(match.group(1).lower())
    
    missing = referenced - all_asset_names
    return list(missing)
```

### is_ambiguous_question

```python
AMBIGUOUS_TERMS = [
    "underperforming", "top performing", "best", "worst",
    "valuable", "important", "active", "inactive",
    "recent", "old", "expensive", "cheap"
]

def is_ambiguous_question(question: str) -> bool:
    """Check if a question contains ambiguous terms that need explicit definition."""
    question_lower = question.lower()
    return any(term in question_lower for term in AMBIGUOUS_TERMS)
```

---

## Integration with Genie Space Setup (Skill 03)

This workflow integrates into **Step 4: Write Benchmark Questions** of the Genie Space setup:

1. After completing Sections A-F, prompt the user for benchmark questions
2. Run the intake workflow (validate / generate / augment)
3. Write validated benchmarks into Section G of the deliverable
4. Include both the natural language question AND the expected SQL
5. Proceed to Step 5 (Deploy and Test)

## Integration with Genie Space Optimization (Skill 05)

This workflow integrates into **Step 1: Write Benchmark Questions** of the optimization loop:

1. Before starting the optimization loop, prompt the user for benchmark questions
2. Run the intake workflow (validate / generate / augment)
3. Save benchmarks to the golden-queries YAML file
4. Proceed to Step 2 (Query Genie via API)

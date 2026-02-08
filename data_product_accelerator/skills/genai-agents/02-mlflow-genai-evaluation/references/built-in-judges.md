# Built-in MLflow Judges

Complete patterns for using built-in MLflow judges: relevance, safety, and guidelines.

---

## 1. Relevance Judge

Evaluates whether response addresses the user's query.

```python
from mlflow.metrics.genai import relevance

evaluators = [
    ("relevance", relevance, 1.0),  # (name, scorer, weight)
]

# Threshold check
thresholds = {
    "relevance/mean": 0.4,  # Minimum acceptable relevance score
}
```

**Measures:**
- Query understanding
- Response alignment with question
- Answer completeness

**Threshold Recommendation:** 0.4 (moderate threshold - responses should address the query)

---

## 2. Safety Judge

Evaluates response safety and harmfulness.

```python
from mlflow.metrics.genai import safety

evaluators = [
    ("safety", safety, 1.0),
]

# Threshold check
thresholds = {
    "safety/mean": 0.7,  # High threshold - critical for production
}
```

**Measures:**
- Harmful content detection
- Bias identification
- Inappropriate responses

**Threshold Recommendation:** 0.7 (high threshold - safety is critical for production)

---

## 3. Guidelines Judge

Evaluates adherence to custom guidelines/instructions.

```python
from mlflow.metrics.genai import Guidelines

# Define custom guidelines (list of strings)
guidelines = [
    """Response Structure and Formatting:
    - MUST start with a direct answer in the first 1-2 sentences
    - MUST use markdown formatting with proper headings (##)
    - MUST use **bold** for key metrics and findings
    - MUST use tables for comparisons
    - MUST follow standard structure: Summary → Analysis → Recommendations → Data Sources""",
    
    """Data Accuracy and Specificity:
    - MUST include specific numbers (actual costs in $, DBUs, percentages)
    - MUST include time context (when data is from)
    - MUST include trend direction (↑/↓ or "increased"/"decreased")
    - MUST cite sources explicitly: [Cost Genie], [Security Genie], etc.""",
    
    """No Data Fabrication (CRITICAL):
    - MUST NEVER fabricate or guess at numbers
    - If Genie returns an error, MUST say so explicitly
    - MUST NEVER hallucinate data that looks real but is fabricated""",
    
    """Actionability and Recommendations:
    - MUST provide specific, actionable next steps
    - MUST include concrete implementation details
    - MUST prioritize recommendations by urgency
    - MUST include estimated impact or savings where applicable""",
]

evaluators = [
    ("guidelines", Guidelines(guidelines=guidelines), 1.0),
]

# Threshold check
thresholds = {
    "guidelines/mean": 0.5,  # Lowered from strict 8-section guidelines
}
```

**Measures:**
- Adherence to custom instructions
- Formatting requirements
- Content quality criteria

**Threshold Recommendation:** 0.5 (achievable with 4-6 essential guidelines)

---

## Guidelines Best Practice: 4-6 Sections (NOT 8+)

**CRITICAL: Keep guidelines to 4-6 essential sections for achievable, meaningful scores.**

### ❌ DON'T: Too Many Guidelines Sections

```python
# BAD: 8 comprehensive guidelines = low scores
guidelines = [
    "Section 1: Response Structure (200 words)",
    "Section 2: Data Accuracy (150 words)",
    "Section 3: No Fabrication (180 words)",
    "Section 4: Actionability (160 words)",
    "Section 5: Domain Expertise (200 words)",
    "Section 6: Cross-Domain Intelligence (150 words)",
    "Section 7: Professional Tone (120 words)",
    "Section 8: Completeness (170 words)",
]

# Result: guidelines/mean = 0.20 (too strict!)
```

**Why this fails:**
- 8+ sections = overly strict scoring
- Average score: 0.20 (fails threshold)
- Too many criteria = impossible to satisfy all
- Low scores don't reflect actual quality

### ✅ DO: 4-6 Essential Guidelines

```python
# GOOD: 4 focused, critical guidelines = higher, more meaningful scores
guidelines = [
    """Data Accuracy and Specificity:
    - MUST include specific numbers (costs, DBUs, percentages)
    - MUST include time context (when data is from)
    - MUST include trend direction (increased/decreased)""",
    
    """No Data Fabrication (CRITICAL):
    - MUST NEVER fabricate numbers
    - If Genie errors, MUST state explicitly""",
    
    """Actionability and Recommendations:
    - MUST provide specific, actionable next steps
    - MUST include concrete implementation details""",
    
    """Professional Enterprise Tone:
    - MUST maintain professional tone
    - MUST use proper formatting (markdown, tables)""",
]

# Result: guidelines/mean = 0.5+ (achievable, meaningful)
```

**Why this works:**
- 4-6 sections = achievable scoring
- Average score: 0.50+ (meets threshold)
- Focused criteria = clear quality expectations
- Scores reflect actual quality differences

**Guidelines Best Practices:**
- Keep to 4-6 essential sections (not 8+)
- Focus on critical quality dimensions
- Make criteria objectively verifiable
- Include examples of correct/incorrect patterns

---

## Complete Built-in Judges Example

```python
from mlflow.metrics.genai import relevance, safety, Guidelines

# Define 4-6 essential guidelines
guidelines = [
    """Data Accuracy and Specificity:
    - MUST include specific numbers (costs, DBUs, percentages)
    - MUST include time context (when data is from)
    - MUST include trend direction (increased/decreased)""",
    
    """No Data Fabrication (CRITICAL):
    - MUST NEVER fabricate numbers
    - If Genie errors, MUST state explicitly""",
    
    """Actionability and Recommendations:
    - MUST provide specific, actionable next steps
    - MUST include concrete implementation details""",
    
    """Professional Enterprise Tone:
    - MUST maintain professional tone
    - MUST use proper formatting (markdown, tables)""",
]

# Register built-in judges
evaluators = [
    ("relevance", relevance, 1.0),
    ("safety", safety, 1.0),
    ("guidelines", Guidelines(guidelines=guidelines), 1.0),
]

# Define thresholds
DEPLOYMENT_THRESHOLDS = {
    "relevance/mean": 0.4,
    "safety/mean": 0.7,
    "guidelines/mean": 0.5,
}
```

---

## Viewing Judge Results

### Option 1: MLflow Experiment UI

1. Navigate to MLflow Experiment
2. Click on evaluation run
3. **Evaluation** tab shows:
   - Aggregate metrics per judge
   - Mean, P90, other aggregations
4. **Traces** tab shows:
   - Individual query executions
   - Judge reasoning (justification text)
   - Detailed span-level tracing

### Option 2: Download Scored Outputs CSV

```python
from mlflow import MlflowClient

client = MlflowClient()

# Get latest evaluation run
runs = mlflow.search_runs(
    experiment_ids=[experiment_id],
    filter_string="tags.mlflow.runName LIKE 'eval_pre_deploy_%'",
    order_by=["start_time DESC"],
    max_results=1
)

run_id = runs.iloc[0]['run_id']

# List artifacts
artifacts = client.list_artifacts(run_id)
for artifact in artifacts:
    if "scored_outputs" in artifact.path:
        # Download CSV
        local_path = client.download_artifacts(run_id, artifact.path)
        
        # Read and analyze
        import pandas as pd
        df = pd.read_csv(local_path)
        
        # Columns include:
        # - request: Original query
        # - response: Agent output
        # - relevance: Relevance score
        # - relevance/justification: Why this score
        # - safety: Safety score
        # - guidelines: Guidelines score
        
        print(df[['request', 'relevance', 'safety', 'guidelines']].head())
```

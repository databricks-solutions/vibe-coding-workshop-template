# NO LLM Fallback Pattern (CRITICAL)

**MANDATORY: NEVER use LLM fallback when Genie queries fail. Always fail explicitly.**

## Production Learning (January 7, 2026)

**Incident:** Agent returned plausible-sounding but incorrect cost data when Genie queries failed.

**Root Cause:** LLM fallback pattern generated fake numbers when Genie API returned errors.

**Impact:**
- Business decisions made on incorrect data
- Data governance violation
- Loss of trust in agent accuracy
- Production incident requiring immediate rollback

**Resolution:** Removed all LLM fallback patterns, implemented explicit error handling.

---

## Decision Table: When LLM IS vs ISN'T Acceptable

| Scenario | LLM Acceptable? | Pattern |
|---|---|---|
| **Genie query fails** | ❌ NO | Fail explicitly with error message |
| **Genie returns no results** | ❌ NO | Return "No data available" message |
| **Genie query timeout** | ❌ NO | Return timeout error, don't fabricate |
| **Synthesizing multiple Genie results** | ✅ YES | LLM can combine real results |
| **Formatting Genie query results** | ✅ YES | LLM can format markdown tables |
| **Explaining Genie query results** | ✅ YES | LLM can add context to real data |
| **Intent classification** | ✅ YES | LLM can classify query intent |
| **Generating follow-up questions** | ✅ YES | LLM can suggest related queries |

**Key Principle:** LLM can process/transform real data, but NEVER generate data when queries fail.

---

## Error Message Template

```python
class GenieQueryError(Exception):
    """Base exception for Genie query failures."""
    pass

def raise_genie_error(domain: str, error: str, query: str) -> None:
    """
    Raise explicit error when Genie query fails.
    
    NEVER fall back to LLM-generated data.
    """
    error_message = f"""
**Genie Query Failed**

**Domain:** {domain}
**Query:** {query}
**Error:** {error}

**Action Required:**
1. Check Genie Space configuration for domain: {domain}
2. Verify data availability in queried tables
3. Review query syntax and domain relevance
4. Check Genie Space General Instructions

**Data Integrity:** This error prevents returning potentially incorrect data.
"""
    raise GenieQueryError(error_message)
```

## ❌ WRONG: LLM Fallback Patterns

### Pattern 1: Silent LLM Fallback

```python
def query_domain(domain: str, query: str) -> str:
    try:
        result = query_genie(domain, query)
        return result
    except Exception as e:
        # ❌ CRITICAL ERROR: LLM generates fake data
        llm_response = llm.generate(f"Answer: {query}")
        return llm_response  # ❌ Hallucinated numbers!
```

**Why this is wrong:**
- LLM generates plausible but incorrect data
- No way to distinguish real vs fake results
- Violates data governance
- Creates production incidents

### Pattern 2: Partial LLM Fallback

```python
def query_domain(domain: str, query: str) -> str:
    try:
        result = query_genie(domain, query)
        return result
    except Exception as e:
        # ❌ STILL WRONG: Even "helpful" fallback is dangerous
        return f"I couldn't query the data, but based on typical patterns: {llm.generate(query)}"
```

**Why this is wrong:**
- "Typical patterns" are still hallucinated
- Users may not notice the disclaimer
- Still violates data integrity

### Pattern 3: LLM Error Explanation

```python
def query_domain(domain: str, query: str) -> str:
    try:
        result = query_genie(domain, query)
        return result
    except Exception as e:
        # ❌ WRONG: LLM shouldn't explain errors with fake context
        explanation = llm.generate(f"Explain why query '{query}' might fail")
        return f"Query failed: {e}. {explanation}"
```

**Why this is wrong:**
- LLM explanation may include incorrect assumptions
- Better to use static error messages

---

## ✅ CORRECT: Explicit Failure Patterns

### Pattern 1: Explicit Exception

```python
def query_domain(domain: str, query: str) -> str:
    try:
        result = query_genie(domain, query)
        return result
    except Exception as e:
        # ✅ CORRECT: Fail explicitly
        raise GenieQueryError(
            f"Genie query failed for domain {domain}: {str(e)}. "
            f"Unable to retrieve data. Please check Genie Space configuration."
        )
```

### Pattern 2: Error Response Object

```python
def query_domain(domain: str, query: str) -> Dict[str, Any]:
    try:
        result = query_genie(domain, query)
        return {
            "success": True,
            "result": result,
            "error": None
        }
    except Exception as e:
        # ✅ CORRECT: Return error in structured format
        return {
            "success": False,
            "result": None,
            "error": {
                "domain": domain,
                "query": query,
                "message": str(e),
                "type": type(e).__name__
            }
        }
```

### Pattern 3: User-Friendly Error Message

```python
def query_domain(domain: str, query: str) -> str:
    try:
        result = query_genie(domain, query)
        return result
    except GenieTimeoutError as e:
        # ✅ CORRECT: User-friendly but explicit
        return f"""
**Unable to Retrieve Data**

The query timed out while accessing the {domain} domain.

**Query:** {query}

**Possible Causes:**
- Genie Space is experiencing high load
- Query is too complex
- Network connectivity issues

**Next Steps:**
1. Try again in a few moments
2. Simplify your query
3. Contact support if issue persists

**Data Integrity:** This error prevents returning potentially incorrect data.
"""
    except Exception as e:
        return f"""
**Genie Query Failed**

**Domain:** {domain}
**Error:** {str(e)}

**Action Required:**
Please check Genie Space configuration and data availability.

**Data Integrity:** This error prevents returning potentially incorrect data.
"""
```

---

## LLM Usage: Acceptable Patterns

### ✅ Pattern 1: Synthesizing Real Results

```python
def synthesize_results(domain_results: Dict[str, Any]) -> str:
    """
    ✅ CORRECT: LLM synthesizes REAL Genie results.
    
    All domain_results contain actual data from Genie queries.
    """
    prompt = f"Synthesize these real results: {domain_results}"
    return llm.generate(prompt)  # ✅ OK: Processing real data
```

### ✅ Pattern 2: Formatting Real Data

```python
def format_query_result(query_result: Dict[str, Any]) -> str:
    """
    ✅ CORRECT: LLM formats REAL query results.
    
    query_result contains actual data from Genie.
    """
    prompt = f"Format this data as markdown table: {query_result}"
    return llm.generate(prompt)  # ✅ OK: Formatting real data
```

### ✅ Pattern 3: Intent Classification

```python
def classify_intent(query: str) -> str:
    """
    ✅ CORRECT: LLM classifies query intent.
    
    No data generation, just classification.
    """
    prompt = f"Classify this query: {query}"
    return llm.generate(prompt)  # ✅ OK: Classification, not data
```

---

## Validation Checklist

Before deploying any Genie integration:

- [ ] ✅ **NO LLM fallback when Genie queries fail**
- [ ] ✅ **Explicit error messages for all failures**
- [ ] ✅ **Error messages don't include LLM-generated explanations**
- [ ] ✅ **All error paths tested**
- [ ] ✅ **Data integrity maintained**
- [ ] ✅ **LLM only used for processing/formatting real data**

---

## Code Review Checklist

When reviewing code that queries Genie:

1. **Find all exception handlers** that catch Genie query errors
2. **Verify no LLM calls** in exception handlers
3. **Check error messages** are static or use real error details
4. **Verify no data generation** when queries fail
5. **Confirm explicit failures** with clear error messages

---

## References

- Production Incident Report: January 7, 2026
- Data Governance Policy: Section 4.2 (No Fabricated Data)
- Genie API Documentation: Error Handling Best Practices

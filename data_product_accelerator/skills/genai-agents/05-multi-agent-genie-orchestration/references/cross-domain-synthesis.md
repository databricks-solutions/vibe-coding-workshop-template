# Cross-Domain Synthesis Patterns

LLM-based synthesis of results from multiple Genie Spaces into a unified, coherent response with proper source attribution and markdown formatting.

## Synthesis Prompt Template

```python
def build_synthesis_prompt(
    original_query: str,
    domain_results: Dict[str, Dict[str, Any]]
) -> str:
    """
    Build LLM prompt for synthesizing multi-domain results.
    
    Args:
        original_query: Original user query
        domain_results: {
            "domain_name": {
                "response_text": str,
                "query_result": dict | None,
                "formatted_result": str | None
            }
        }
    
    Returns:
        Formatted prompt string
    """
    # Build domain results section
    domain_sections = []
    for domain, result in domain_results.items():
        section = f"""
### {domain.upper()} Domain Results

**Response:**
{result.get('response_text', 'No response available')}

"""
        if result.get('formatted_result'):
            section += f"""
**Query Result:**
{result['formatted_result']}

"""
        domain_sections.append(section)
    
    prompt = f"""You are synthesizing results from multiple data domains to answer a user's query.

**Original Query:**
{original_query}

**Results from Multiple Domains:**

{''.join(domain_sections)}

**Instructions:**
1. Synthesize the information from all domains into a coherent, unified answer
2. Maintain accuracy - only use information from the provided domain results
3. If domains have conflicting information, note the discrepancy
4. Use markdown formatting (tables, lists, headers) for clarity
5. Include specific numbers, dates, and metrics from the results
6. Attribute information to source domains when relevant
7. If a domain returned no results, note that in the synthesis

**Synthesized Response:**
"""
    
    return prompt
```

## LLM Synthesis Function

```python
from databricks.sdk import WorkspaceClient
from typing import Dict, Any, Optional
import re

def synthesize_results(
    original_query: str,
    domain_results: Dict[str, Dict[str, Any]],
    workspace_client: WorkspaceClient,
    llm_endpoint: str = "databricks-claude-3-7-sonnet"
) -> str:
    """
    Synthesize results from multiple Genie Spaces using LLM.
    
    Args:
        original_query: Original user query
        domain_results: Results from multiple domain queries
        workspace_client: Authenticated WorkspaceClient
        llm_endpoint: LLM endpoint name for synthesis
    
    Returns:
        Synthesized response string
    """
    # Filter to successful results only
    successful_results = {
        domain: result
        for domain, result in domain_results.items()
        if result.get("success", False) and result.get("result")
    }
    
    if not successful_results:
        return _build_no_results_response(domain_results)
    
    # Build synthesis prompt
    prompt = build_synthesis_prompt(original_query, {
        domain: result["result"]
        for domain, result in successful_results.items()
    })
    
    # Call LLM for synthesis
    try:
        from databricks.sdk.service.serving import EndpointCoreInputs
        
        response = workspace_client.serving_endpoints.query(
            endpoint_name=llm_endpoint,
            inputs=[{"messages": [{"role": "user", "content": prompt}]}]
        )
        
        synthesized_text = response.predictions[0]["choices"][0]["message"]["content"]
        
        # Add source attribution
        synthesized_with_attribution = add_source_attribution(
            synthesized_text,
            successful_results
        )
        
        return synthesized_with_attribution
        
    except Exception as e:
        # Fallback: simple concatenation
        return _fallback_synthesis(original_query, successful_results, str(e))


def _build_no_results_response(
    domain_results: Dict[str, Dict[str, Any]]
) -> str:
    """Build response when no domains returned successful results."""
    failed_domains = [
        domain for domain, result in domain_results.items()
        if not result.get("success", False)
    ]
    
    return f"""I was unable to retrieve data from any of the queried domains.

**Failed Domains:**
{', '.join(failed_domains)}

**Errors:**
{chr(10).join(f"- {domain}: {result.get('error', 'Unknown error')}" 
              for domain, result in domain_results.items() 
              if not result.get('success', False))}

Please check:
1. Genie Space configurations
2. Data availability in queried domains
3. Query syntax and domain relevance
"""


def _fallback_synthesis(
    original_query: str,
    successful_results: Dict[str, Dict[str, Any]],
    error: str
) -> str:
    """Fallback synthesis when LLM call fails."""
    sections = []
    
    for domain, result in successful_results.items():
        sections.append(f"""
## {domain.upper()} Domain

{result['result'].get('response_text', 'No response')}

""")
        if result['result'].get('formatted_result'):
            sections.append(f"**Query Result:**\n{result['result']['formatted_result']}\n")
    
    return f"""**Query:** {original_query}

**Note:** LLM synthesis failed ({error}). Presenting domain results separately:

{''.join(sections)}
"""
```

## Source Attribution

```python
def add_source_attribution(
    synthesized_text: str,
    domain_results: Dict[str, Dict[str, Any]]
) -> str:
    """
    Add source attribution to synthesized response.
    
    Adds a "Sources" section at the end listing which domains contributed.
    """
    # Extract domains that contributed
    contributing_domains = list(domain_results.keys())
    
    # Build sources section
    sources_section = f"""

---

## Sources

This response synthesizes information from the following domains:
{chr(10).join(f"- **{domain}**: Genie Space query results" for domain in contributing_domains)}

*Generated by multi-agent Genie orchestration system*
"""
    
    # Append sources if not already present
    if "## Sources" not in synthesized_text:
        return synthesized_text + sources_section
    else:
        return synthesized_text
```

## Response Formatting with Markdown

```python
def format_synthesized_response(
    synthesized_text: str,
    include_metadata: bool = True
) -> str:
    """
    Format synthesized response with proper markdown structure.
    
    Args:
        synthesized_text: Raw synthesized text from LLM
        include_metadata: Whether to include query metadata
    
    Returns:
        Formatted markdown string
    """
    # Clean up markdown formatting
    formatted = synthesized_text.strip()
    
    # Ensure proper heading hierarchy
    formatted = re.sub(r'^### ', '## ', formatted, flags=re.MULTILINE)
    
    # Fix table formatting if needed
    formatted = _fix_table_formatting(formatted)
    
    # Add metadata section if requested
    if include_metadata:
        metadata = """
---

*This response was generated by querying multiple Genie Spaces and synthesizing the results.*
"""
        formatted = formatted + metadata
    
    return formatted


def _fix_table_formatting(text: str) -> str:
    """Fix common markdown table formatting issues."""
    # Ensure tables have proper spacing
    lines = text.split('\n')
    fixed_lines = []
    in_table = False
    
    for i, line in enumerate(lines):
        # Detect table start
        if '|' in line and not in_table:
            in_table = True
            fixed_lines.append(line)
            continue
        
        # Detect table end (empty line or non-table line)
        if in_table:
            if '|' in line:
                fixed_lines.append(line)
            else:
                in_table = False
                fixed_lines.append('')  # Add spacing after table
                fixed_lines.append(line)
            continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)
```

## Complete Synthesis Workflow

```python
def synthesize_cross_domain_results(
    original_query: str,
    domain_results: Dict[str, Dict[str, Any]],
    workspace_client: WorkspaceClient
) -> Dict[str, Any]:
    """
    Complete cross-domain synthesis workflow.
    
    Returns:
        {
            "synthesized_response": str,
            "contributing_domains": List[str],
            "failed_domains": List[str],
            "synthesis_method": str
        }
    """
    successful_results = {
        domain: result
        for domain, result in domain_results.items()
        if result.get("success", False)
    }
    
    failed_domains = [
        domain for domain, result in domain_results.items()
        if not result.get("success", False)
    ]
    
    if not successful_results:
        return {
            "synthesized_response": _build_no_results_response(domain_results),
            "contributing_domains": [],
            "failed_domains": failed_domains,
            "synthesis_method": "error"
        }
    
    # Attempt LLM synthesis
    try:
        synthesized = synthesize_results(
            original_query=original_query,
            domain_results=successful_results,
            workspace_client=workspace_client
        )
        
        formatted = format_synthesized_response(synthesized, include_metadata=True)
        
        return {
            "synthesized_response": formatted,
            "contributing_domains": list(successful_results.keys()),
            "failed_domains": failed_domains,
            "synthesis_method": "llm"
        }
        
    except Exception as e:
        # Fallback to simple concatenation
        fallback = _fallback_synthesis(original_query, successful_results, str(e))
        
        return {
            "synthesized_response": fallback,
            "contributing_domains": list(successful_results.keys()),
            "failed_domains": failed_domains,
            "synthesis_method": "fallback"
        }
```

## Usage Example

```python
from databricks.sdk import WorkspaceClient

workspace_client = WorkspaceClient()

# Domain results from parallel queries
domain_results = {
    "billing": {
        "success": True,
        "result": {
            "response_text": "Total cost last month: $12,345",
            "formatted_result": "| Month | Cost |\n|-------|------|\n| 2025-01 | $12,345 |"
        }
    },
    "monitoring": {
        "success": True,
        "result": {
            "response_text": "Average job runtime: 45 minutes",
            "formatted_result": "| Metric | Value |\n|--------|-------|\n| Avg Runtime | 45 min |"
        }
    }
}

# Synthesize results
synthesis = synthesize_cross_domain_results(
    original_query="What was the cost and performance last month?",
    domain_results=domain_results,
    workspace_client=workspace_client
)

print(synthesis["synthesized_response"])
```

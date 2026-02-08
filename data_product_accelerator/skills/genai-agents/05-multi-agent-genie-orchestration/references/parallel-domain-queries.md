# Parallel Domain Queries Patterns

ThreadPoolExecutor patterns for executing Genie queries across multiple domains in parallel, with error handling, timeout management, and result aggregation.

## ThreadPoolExecutor Pattern

```python
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from typing import Dict, List, Optional, Any
from databricks.sdk import WorkspaceClient
import logging

logger = logging.getLogger(__name__)

def query_domains_parallel(
    domains: List[str],
    domain_space_map: Dict[str, str],  # domain -> space_id
    query: str,
    workspace_client: WorkspaceClient,
    timeout: int = 30,
    max_workers: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Execute Genie queries across multiple domains in parallel.
    
    Args:
        domains: List of domain names to query
        domain_space_map: Mapping of domain names to Genie Space IDs
        query: User query string
        workspace_client: Authenticated WorkspaceClient
        timeout: Timeout in seconds for each query
        max_workers: Maximum number of parallel workers (default: len(domains))
    
    Returns:
        {
            "domain_name": {
                "success": bool,
                "result": dict | None,
                "error": str | None,
                "query_time": float
            }
        }
    """
    if max_workers is None:
        max_workers = len(domains)
    
    domain_results = {}
    
    def query_single_domain(domain: str) -> tuple[str, Dict[str, Any]]:
        """Query a single domain and return (domain, result)."""
        import time
        start_time = time.time()
        
        try:
            space_id = domain_space_map.get(domain)
            if not space_id:
                raise ValueError(f"No Space ID mapped for domain: {domain}")
            
            from .genie_conversation_api import query_genie
            
            result = query_genie(
                workspace_client=workspace_client,
                space_id=space_id,
                query=query
            )
            
            query_time = time.time() - start_time
            
            if result["success"]:
                return (domain, {
                    "success": True,
                    "result": result,
                    "error": None,
                    "query_time": query_time
                })
            else:
                return (domain, {
                    "success": False,
                    "result": None,
                    "error": result.get("error", "Unknown error"),
                    "query_time": query_time
                })
                
        except Exception as e:
            query_time = time.time() - start_time
            logger.error(f"Error querying domain {domain}: {str(e)}")
            return (domain, {
                "success": False,
                "result": None,
                "error": str(e),
                "query_time": query_time
            })
    
    # Execute queries in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all queries
        future_to_domain = {
            executor.submit(query_single_domain, domain): domain
            for domain in domains
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_domain, timeout=timeout):
            domain = future_to_domain[future]
            try:
                result_domain, result_data = future.result(timeout=1)
                domain_results[result_domain] = result_data
            except FutureTimeoutError:
                domain_results[domain] = {
                    "success": False,
                    "result": None,
                    "error": f"Query timed out after {timeout} seconds",
                    "query_time": timeout
                }
            except Exception as e:
                domain_results[domain] = {
                    "success": False,
                    "result": None,
                    "error": f"Unexpected error: {str(e)}",
                    "query_time": 0.0
                }
    
    return domain_results
```

## Error Handling Per Domain

```python
def query_domains_with_error_isolation(
    domains: List[str],
    domain_space_map: Dict[str, str],
    query: str,
    workspace_client: WorkspaceClient,
    timeout: int = 30
) -> Dict[str, Dict[str, Any]]:
    """
    Query domains with complete error isolation - one failure doesn't affect others.
    
    Returns results for all domains, with error details for failed ones.
    """
    results = query_domains_parallel(
        domains=domains,
        domain_space_map=domain_space_map,
        query=query,
        workspace_client=workspace_client,
        timeout=timeout
    )
    
    # Log errors but don't fail
    for domain, result in results.items():
        if not result["success"]:
            logger.warning(
                f"Domain {domain} query failed: {result['error']} "
                f"(took {result['query_time']:.2f}s)"
            )
        else:
            logger.info(
                f"Domain {domain} query succeeded "
                f"(took {result['query_time']:.2f}s)"
            )
    
    return results
```

## Timeout Handling

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal
from contextlib import contextmanager

@contextmanager
def timeout_context(seconds: int):
    """Context manager for timeout handling."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set signal handler
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)  # Cancel alarm

def query_domains_with_global_timeout(
    domains: List[str],
    domain_space_map: Dict[str, str],
    query: str,
    workspace_client: WorkspaceClient,
    per_query_timeout: int = 30,
    global_timeout: int = 60
) -> Dict[str, Dict[str, Any]]:
    """
    Query domains with both per-query and global timeout.
    
    Args:
        per_query_timeout: Timeout for each individual query
        global_timeout: Maximum total time for all queries
    """
    with timeout_context(global_timeout):
        return query_domains_parallel(
            domains=domains,
            domain_space_map=domain_space_map,
            query=query,
            workspace_client=workspace_client,
            timeout=per_query_timeout
        )
```

## Domain Results Aggregation

```python
def aggregate_domain_results(
    domain_results: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate results from multiple domain queries.
    
    Returns:
        {
            "successful_domains": List[str],
            "failed_domains": List[str],
            "total_queries": int,
            "success_rate": float,
            "average_query_time": float,
            "results_by_domain": dict
        }
    """
    successful_domains = [
        domain for domain, result in domain_results.items()
        if result["success"]
    ]
    
    failed_domains = [
        domain for domain, result in domain_results.items()
        if not result["success"]
    ]
    
    total_queries = len(domain_results)
    success_rate = len(successful_domains) / total_queries if total_queries > 0 else 0.0
    
    query_times = [
        result["query_time"] for result in domain_results.values()
        if result["query_time"] > 0
    ]
    average_query_time = sum(query_times) / len(query_times) if query_times else 0.0
    
    return {
        "successful_domains": successful_domains,
        "failed_domains": failed_domains,
        "total_queries": total_queries,
        "success_rate": success_rate,
        "average_query_time": average_query_time,
        "results_by_domain": domain_results
    }
```

## Usage Example

```python
from databricks.sdk import WorkspaceClient

workspace_client = WorkspaceClient()

# Domain to Space ID mapping
domain_space_map = {
    "billing": "1234567890abcdef",
    "monitoring": "abcdef1234567890",
    "jobs": "fedcba0987654321"
}

# Query multiple domains in parallel
domains = ["billing", "monitoring", "jobs"]
query = "What are the top 5 items by cost this month?"

results = query_domains_parallel(
    domains=domains,
    domain_space_map=domain_space_map,
    query=query,
    workspace_client=workspace_client,
    timeout=30
)

# Aggregate results
aggregated = aggregate_domain_results(results)

print(f"Success rate: {aggregated['success_rate']:.1%}")
print(f"Successful domains: {aggregated['successful_domains']}")
print(f"Failed domains: {aggregated['failed_domains']}")

# Process successful results
for domain in aggregated["successful_domains"]:
    result = results[domain]["result"]
    print(f"\n{domain}:\n{result['response_text']}")
    if result.get("formatted_result"):
        print(result["formatted_result"])
```

## Performance Optimization

```python
def query_domains_optimized(
    domains: List[str],
    domain_space_map: Dict[str, str],
    query: str,
    workspace_client: WorkspaceClient,
    timeout: int = 30,
    batch_size: int = 5
) -> Dict[str, Dict[str, Any]]:
    """
    Query domains in batches to avoid overwhelming Genie API.
    
    Useful when querying 10+ domains simultaneously.
    """
    all_results = {}
    
    # Process domains in batches
    for i in range(0, len(domains), batch_size):
        batch_domains = domains[i:i + batch_size]
        
        batch_results = query_domains_parallel(
            domains=batch_domains,
            domain_space_map=domain_space_map,
            query=query,
            workspace_client=workspace_client,
            timeout=timeout,
            max_workers=batch_size
        )
        
        all_results.update(batch_results)
    
    return all_results
```

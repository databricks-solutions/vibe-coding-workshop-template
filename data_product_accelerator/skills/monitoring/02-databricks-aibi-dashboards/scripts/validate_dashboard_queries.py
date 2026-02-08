"""
SQL Query Validation Script
Validates all dashboard queries before deployment using SELECT LIMIT 1.
"""

import json
import re
from pathlib import Path
from pyspark.sql import SparkSession


def substitute_parameters(query: str, parameters: list) -> str:
    """Substitute dashboard parameters with test values."""
    result = query
    
    # Parameter substitution patterns
    substitutions = {
        # Time range parameters
        r':time_range\.min': "CURRENT_DATE() - INTERVAL 30 DAYS",
        r':time_range\.max': "CURRENT_DATE()",
        r':monitor_time_start': "CURRENT_DATE() - INTERVAL 30 DAYS",
        r':monitor_time_end': "CURRENT_DATE()",
        
        # Multi-select parameters (return ARRAY)
        r':param_workspace': "ARRAY('All')",
        r':param_catalog': "ARRAY('All')",
        r':param_sku': "ARRAY('All')",
        
        # Single-select parameters
        r':monitor_slice_key': "'No Slice'",
        r':monitor_slice_value': "'No Slice'",
        
        # Text input parameters
        r':annual_commit': "1000000",
    }
    
    for pattern, replacement in substitutions.items():
        result = re.sub(pattern, replacement, result)
    
    return result


def validate_query(spark: SparkSession, dataset_name: str, query: str, parameters: list) -> dict:
    """Validate a single query by executing SELECT LIMIT 1."""
    try:
        # Substitute parameters
        test_query = substitute_parameters(query, parameters)
        
        # Wrap in LIMIT 1 for efficiency
        validation_query = f"SELECT * FROM ({test_query}) LIMIT 1"
        
        # Execute
        spark.sql(validation_query).collect()
        return {"dataset": dataset_name, "status": "OK", "error": None}
        
    except Exception as e:
        return {"dataset": dataset_name, "status": "ERROR", "error": str(e)}


def validate_dashboard(spark: SparkSession, dashboard_path: Path) -> list:
    """Validate all queries in a dashboard JSON file."""
    with open(dashboard_path) as f:
        dashboard = json.load(f)
    
    results = []
    for dataset in dashboard.get("datasets", []):
        name = dataset["name"]
        query = dataset["query"]
        params = dataset.get("parameters", [])
        
        result = validate_query(spark, name, query, params)
        results.append(result)
        
        # Print progress
        status = "✅" if result["status"] == "OK" else "❌"
        print(f"{status} {name}")
        if result["error"]:
            print(f"   Error: {result['error'][:200]}")
    
    return results


def categorize_error(error_str: str) -> dict:
    """Extract structured info from SQL errors."""
    result = {'error_type': 'OTHER'}
    
    if 'UNRESOLVED_COLUMN' in error_str:
        result['error_type'] = 'COLUMN_NOT_FOUND'
        # Extract column name
        match = re.search(r"name `([^`]+)`", error_str)
        if match:
            result['column'] = match.group(1)
        # Extract suggestions
        match = re.search(r"Did you mean one of the following\? \[([^\]]+)\]", error_str)
        if match:
            result['suggestions'] = match.group(1)
    
    elif 'AMBIGUOUS_REFERENCE' in error_str:
        result['error_type'] = 'AMBIGUOUS_COLUMN'
        match = re.search(r"Reference `([^`]+)`", error_str)
        if match:
            result['column'] = match.group(1)
    
    elif 'TABLE_OR_VIEW_NOT_FOUND' in error_str:
        result['error_type'] = 'TABLE_NOT_FOUND'
        match = re.search(r"table or view `([^`]+)`", error_str)
        if match:
            result['table'] = match.group(1)
    
    return result


if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()
    
    # Dashboard files to validate
    dashboard_dir = Path("src/dashboards")
    dashboards = [
        dashboard_dir / "cost.lvdash.json",
        dashboard_dir / "reliability.lvdash.json",
        dashboard_dir / "performance.lvdash.json",
        dashboard_dir / "security.lvdash.json",
        dashboard_dir / "quality.lvdash.json",
        dashboard_dir / "unified.lvdash.json",
    ]
    
    all_errors = []
    for dashboard_path in dashboards:
        if not dashboard_path.exists():
            print(f"⚠️  Skipping {dashboard_path.name} - file not found")
            continue
        
        print(f"\n{'='*60}\nValidating: {dashboard_path.name}\n{'='*60}")
        results = validate_dashboard(spark, dashboard_path)
        errors = [r for r in results if r["status"] == "ERROR"]
        all_errors.extend(errors)
    
    # Summary
    print(f"\n{'='*60}\nSUMMARY\n{'='*60}")
    print(f"Total errors: {len(all_errors)}")
    
    if all_errors:
        for e in all_errors:
            print(f"❌ {e['dataset']}: {e['error'][:100]}")
        raise RuntimeError(f"Validation failed with {len(all_errors)} errors")
    else:
        print("✅ All queries validated successfully!")

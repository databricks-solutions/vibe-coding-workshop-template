"""
Widget Encoding Validation Script
Validates widget fieldNames match dataset query aliases.
"""

import json
import re
from pathlib import Path


def extract_query_columns(query: str) -> set:
    """Extract column aliases from SELECT clause."""
    # Find SELECT ... FROM pattern
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.DOTALL | re.IGNORECASE)
    if not select_match:
        return set()
    
    select_clause = select_match.group(1)
    columns = set()
    
    # Match patterns: "expression AS alias" or "column_name"
    for match in re.finditer(r'(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:,|$)', select_clause):
        columns.add(match.group(1).lower())
    
    return columns


def extract_widget_fields(widget: dict) -> set:
    """Extract fieldName references from widget encodings."""
    fields = set()
    
    def walk(obj):
        if isinstance(obj, dict):
            if 'fieldName' in obj:
                fields.add(obj['fieldName'].lower())
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    
    walk(widget.get('spec', {}).get('encodings', {}))
    return fields


def validate_alignment(dashboard_path: Path) -> list:
    """Check widget fieldNames match dataset query aliases."""
    with open(dashboard_path) as f:
        dashboard = json.load(f)
    
    # Build dataset lookup
    datasets = {d['name']: d for d in dashboard.get('datasets', [])}
    
    issues = []
    for page in dashboard.get('pages', []):
        for layout_item in page.get('layout', []):
            widget = layout_item.get('widget', {})
            widget_name = widget.get('name', 'unknown')
            
            # Get linked datasets
            for query in widget.get('queries', []):
                dataset_name = query.get('name')
                if dataset_name not in datasets:
                    continue
                
                dataset = datasets[dataset_name]
                query_cols = extract_query_columns(dataset.get('query', ''))
                widget_fields = extract_widget_fields(widget)
                
                # Find mismatches
                missing = widget_fields - query_cols
                if missing:
                    issues.append({
                        'widget': widget_name,
                        'dataset': dataset_name,
                        'missing_columns': list(missing),
                        'available_columns': list(query_cols)
                    })
    
    return issues


if __name__ == "__main__":
    dashboard_dir = Path("src/dashboards")
    dashboards = [
        dashboard_dir / "cost.lvdash.json",
        dashboard_dir / "reliability.lvdash.json",
        dashboard_dir / "performance.lvdash.json",
        dashboard_dir / "security.lvdash.json",
        dashboard_dir / "quality.lvdash.json",
        dashboard_dir / "unified.lvdash.json",
    ]
    
    all_issues = []
    for dashboard_path in dashboards:
        if not dashboard_path.exists():
            print(f"⚠️  Skipping {dashboard_path.name} - file not found")
            continue
        
        issues = validate_alignment(dashboard_path)
        all_issues.extend(issues)
    
    if all_issues:
        for issue in all_issues:
            print(f"❌ {issue['widget']}: Missing {issue['missing_columns']}")
            print(f"   Dataset {issue['dataset']} returns: {issue['available_columns']}")
        raise SystemExit(1)
    else:
        print("✅ All widget encodings validated!")

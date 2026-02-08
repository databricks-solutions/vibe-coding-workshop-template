#!/usr/bin/env python3
"""Export Genie Space configuration via REST API.

This script exports a Genie Space configuration for backup, version control, or migration.
"""

import json
import requests
import argparse
import sys
from typing import Optional


def list_genie_spaces(host: str, token: str) -> dict:
    """List all Genie Spaces in the workspace.
    
    Args:
        host: Databricks workspace URL (e.g., https://workspace.cloud.databricks.com)
        token: Personal access token or OAuth token
        
    Returns:
        Dictionary with 'spaces' list containing space metadata
    """
    url = f"{host}/api/2.0/genie/spaces"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        spaces = result.get("spaces", [])
        print(f"✓ Found {len(spaces)} Genie Spaces")
        for space in spaces:
            print(f"  - {space['title']} ({space['space_id']})")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing spaces: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def get_genie_space(
    host: str,
    token: str,
    space_id: str,
    include_config: bool = True,
    output_file: Optional[str] = None
) -> dict:
    """Get a specific Genie Space configuration.
    
    Args:
        host: Databricks workspace URL
        token: Personal access token or OAuth token
        space_id: Genie Space ID to export
        include_config: Whether to include serialized_space in response
        output_file: Optional file path to save exported configuration
        
    Returns:
        Dictionary containing space configuration
    """
    url = f"{host}/api/2.0/genie/spaces/{space_id}"
    if include_config:
        url += "?include_serialized_space=true"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Retrieved Genie Space: {result['title']} ({result['space_id']})")
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✓ Saved configuration to {output_file}")
            
            # Also save just the serialized_space if present
            if 'serialized_space' in result:
                serialized_file = output_file.replace('.json', '_serialized.json')
                serialized_data = json.loads(result['serialized_space'])
                with open(serialized_file, 'w') as f:
                    json.dump(serialized_data, f, indent=2)
                print(f"✓ Saved serialized_space to {serialized_file}")
        
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting space: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Export Genie Space configurations via REST API"
    )
    parser.add_argument(
        "--host",
        required=True,
        help="Databricks workspace URL (e.g., https://workspace.cloud.databricks.com)"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Personal access token or OAuth token"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all Genie Spaces"
    )
    parser.add_argument(
        "--space-id",
        help="Genie Space ID to export"
    )
    parser.add_argument(
        "--output",
        help="Output file path for exported configuration (JSON format)"
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Don't include serialized_space in export (faster, less data)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_genie_spaces(args.host, args.token)
    elif args.space_id:
        get_genie_space(
            host=args.host,
            token=args.token,
            space_id=args.space_id,
            include_config=not args.no_config,
            output_file=args.output
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

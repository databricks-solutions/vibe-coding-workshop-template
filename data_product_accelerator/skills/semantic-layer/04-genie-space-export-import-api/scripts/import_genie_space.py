#!/usr/bin/env python3
"""Import/Deploy Genie Space configuration via REST API.

This script creates or updates Genie Spaces from JSON configuration files.
Supports variable substitution for cross-workspace deployment.
"""

import json
import requests
import argparse
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict


def generate_id() -> str:
    """Generate a Genie Space compatible ID (32 hex chars, no dashes)."""
    return uuid.uuid4().hex


def substitute_variables(data: dict, variables: dict) -> dict:
    """Replace template variables with actual values.
    
    Args:
        data: Genie Space configuration dictionary
        variables: Dictionary of variable substitutions (e.g., {'catalog': 'my_catalog'})
        
    Returns:
        Configuration with variables substituted
    """
    json_str = json.dumps(data)
    
    # Standard substitutions
    json_str = json_str.replace("${catalog}", variables.get('catalog', ''))
    json_str = json_str.replace("${gold_schema}", variables.get('gold_schema', ''))
    json_str = json_str.replace("${feature_schema}", variables.get('feature_schema', ''))
    
    # Monitoring schema pattern
    if 'gold_schema' in variables:
        monitoring_schema = f"{variables['gold_schema']}_monitoring"
        json_str = json_str.replace("${gold_schema}_monitoring", monitoring_schema)
    
    return json.loads(json_str)


def create_genie_space(
    host: str,
    token: str,
    title: str,
    description: str,
    warehouse_id: str,
    config: dict,
    parent_path: Optional[str] = None
) -> dict:
    """Create a new Genie Space using the REST API.
    
    Args:
        host: Databricks workspace URL
        token: Personal access token or OAuth token
        title: Display name for the Genie Space
        description: Description text
        warehouse_id: SQL Warehouse ID
        config: GenieSpaceExport configuration dictionary
        parent_path: Optional parent folder path
        
    Returns:
        Created space metadata
    """
    url = f"{host}/api/2.0/genie/spaces"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "title": title,
        "description": description,
        "warehouse_id": warehouse_id,
        "serialized_space": json.dumps(config)
    }
    
    if parent_path:
        payload["parent_path"] = parent_path
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Created Genie Space: {result['space_id']} ({result['title']})")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating space: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def update_genie_space(
    host: str,
    token: str,
    space_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    config: Optional[dict] = None,
    parent_path: Optional[str] = None
) -> dict:
    """Update an existing Genie Space using the REST API.
    
    All parameters except space_id are optional - only include what you want to update.
    
    Args:
        host: Databricks workspace URL
        token: Personal access token or OAuth token
        space_id: Genie Space ID to update
        title: Optional new title
        description: Optional new description
        warehouse_id: Optional new warehouse ID
        config: Optional new GenieSpaceExport configuration (replaces entire config)
        parent_path: Optional new parent folder path
        
    Returns:
        Updated space metadata
    """
    url = f"{host}/api/2.0/genie/spaces/{space_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Build payload with only provided fields
    payload = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if warehouse_id is not None:
        payload["warehouse_id"] = warehouse_id
    if config is not None:
        payload["serialized_space"] = json.dumps(config)
    if parent_path is not None:
        payload["parent_path"] = parent_path
    
    if not payload:
        print("⚠️  No fields to update. Provide at least one field to modify.", file=sys.stderr)
        sys.exit(1)
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Updated Genie Space: {result['space_id']} ({result['title']})")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Error updating space: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def delete_genie_space(host: str, token: str, space_id: str) -> dict:
    """Delete/trash a Genie Space.
    
    WARNING: This permanently deletes the space and cannot be undone.
    
    Args:
        host: Databricks workspace URL
        token: Personal access token or OAuth token
        space_id: Genie Space ID to delete
        
    Returns:
        Deletion confirmation
    """
    url = f"{host}/api/2.0/genie/spaces/{space_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Deleted Genie Space: {result['space_id']}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Error deleting space: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def load_config_file(config_path: str, variables: Optional[Dict[str, str]] = None) -> dict:
    """Load Genie Space configuration from JSON file.
    
    Args:
        config_path: Path to JSON configuration file
        variables: Optional dictionary for variable substitution
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if variables:
        config = substitute_variables(config, variables)
    
    return config


def main():
    parser = argparse.ArgumentParser(
        description="Import/Deploy Genie Space configurations via REST API"
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
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new Genie Space")
    create_parser.add_argument("--config", required=True, help="Path to JSON configuration file")
    create_parser.add_argument("--title", required=True, help="Display name for the space")
    create_parser.add_argument("--description", required=True, help="Description text")
    create_parser.add_argument("--warehouse-id", required=True, help="SQL Warehouse ID")
    create_parser.add_argument("--parent-path", help="Optional parent folder path")
    create_parser.add_argument("--vars", help="JSON file with variable substitutions")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update an existing Genie Space")
    update_parser.add_argument("--space-id", required=True, help="Genie Space ID to update")
    update_parser.add_argument("--config", help="Path to JSON configuration file (replaces entire config)")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--description", help="New description")
    update_parser.add_argument("--warehouse-id", help="New warehouse ID")
    update_parser.add_argument("--parent-path", help="New parent folder path")
    update_parser.add_argument("--vars", help="JSON file with variable substitutions")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a Genie Space")
    delete_parser.add_argument("--space-id", required=True, help="Genie Space ID to delete")
    delete_parser.add_argument("--confirm", action="store_true", help="Confirm deletion (required)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Load variables if provided
    variables = None
    if hasattr(args, 'vars') and args.vars:
        with open(args.vars, 'r') as f:
            variables = json.load(f)
    
    if args.command == "create":
        config = load_config_file(args.config, variables)
        create_genie_space(
            host=args.host,
            token=args.token,
            title=args.title,
            description=args.description,
            warehouse_id=args.warehouse_id,
            config=config,
            parent_path=getattr(args, 'parent_path', None)
        )
    elif args.command == "update":
        config = None
        if args.config:
            config = load_config_file(args.config, variables)
        
        update_genie_space(
            host=args.host,
            token=args.token,
            space_id=args.space_id,
            title=getattr(args, 'title', None),
            description=getattr(args, 'description', None),
            warehouse_id=getattr(args, 'warehouse_id', None),
            config=config,
            parent_path=getattr(args, 'parent_path', None)
        )
    elif args.command == "delete":
        if not args.confirm:
            print("❌ Deletion requires --confirm flag", file=sys.stderr)
            sys.exit(1)
        delete_genie_space(args.host, args.token, args.space_id)


if __name__ == "__main__":
    main()

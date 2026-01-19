#!/usr/bin/env python3
"""
Generate requirements.txt from pyproject.toml

This script extracts the main dependencies from pyproject.toml and writes
them to requirements.txt for deployment to Databricks Apps.

Databricks Apps requires a requirements.txt file (not pyproject.toml).
"""

import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python 3.10
    except ImportError:
        tomllib = None


def parse_pyproject_simple(filepath: Path) -> list[str]:
    """
    Simple parser for pyproject.toml dependencies.
    Works without tomllib/tomli by parsing the file directly.
    """
    content = filepath.read_text()
    dependencies = []
    
    in_dependencies = False
    bracket_count = 0
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        # Check if we're entering the dependencies section
        if stripped.startswith('dependencies') and '=' in stripped:
            in_dependencies = True
            # Check if there's an opening bracket on the same line
            if '[' in stripped:
                bracket_count += stripped.count('[') - stripped.count(']')
            continue
        
        if in_dependencies:
            # Track bracket depth
            bracket_count += stripped.count('[') - stripped.count(']')
            
            # Stop when we close all brackets
            if bracket_count <= 0 and stripped and not stripped.startswith('#') and not stripped.startswith('"'):
                if not stripped.startswith(']'):
                    break
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
            
            # Extract dependency from quoted string
            if '"' in stripped:
                # Extract content between quotes
                start = stripped.find('"')
                end = stripped.rfind('"')
                if start != end:
                    dep = stripped[start+1:end]
                    if dep and not dep.startswith('#'):
                        dependencies.append(dep)
            elif stripped == ']':
                break
    
    return dependencies


def parse_pyproject_toml(filepath: Path) -> list[str]:
    """
    Parse dependencies from pyproject.toml using tomllib if available.
    Falls back to simple parsing if not.
    """
    if tomllib:
        with open(filepath, 'rb') as f:
            data = tomllib.load(f)
        return data.get('project', {}).get('dependencies', [])
    else:
        return parse_pyproject_simple(filepath)


def write_requirements(dependencies: list[str], output_path: Path) -> None:
    """Write dependencies to requirements.txt."""
    header = """# Auto-generated from pyproject.toml
# Do not edit directly - modify pyproject.toml and run:
#   python scripts/generate_requirements.py
#
# These dependencies are installed in the Databricks App runtime.

"""
    
    with output_path.open('w') as f:
        f.write(header)
        for dep in dependencies:
            # Skip comments in dependencies
            if not dep.strip().startswith('#'):
                f.write(f"{dep}\n")


def main():
    """Main entry point."""
    # Find project root (where pyproject.toml is located)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    pyproject_path = project_root / "pyproject.toml"
    requirements_path = project_root / "requirements.txt"
    
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        sys.exit(1)
    
    print(f"Reading dependencies from: {pyproject_path}")
    dependencies = parse_pyproject_toml(pyproject_path)
    
    if not dependencies:
        print("Warning: No dependencies found!")
        # Create empty requirements file
        requirements_path.write_text("# No dependencies found in pyproject.toml\n")
        sys.exit(0)
    
    print(f"Found {len(dependencies)} dependencies")
    write_requirements(dependencies, requirements_path)
    
    print(f"✓ Generated: {requirements_path}")
    print("\nDependencies:")
    for dep in dependencies:
        print(f"  - {dep}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Pre-deployment validation script for Databricks Asset Bundles.
Catches common configuration errors before deployment.

Usage:
    python scripts/validate_bundle.py
    ./scripts/validate_bundle.py
"""

import os
import sys
import re
from pathlib import Path
from collections import defaultdict


def find_duplicate_files(resources_dir: Path) -> list[str]:
    """Find duplicate YAML files across resources directory."""
    file_names = defaultdict(list)
    
    for yml_file in resources_dir.rglob("*.yml"):
        file_names[yml_file.name].append(str(yml_file))
    
    duplicates = []
    for name, paths in file_names.items():
        if len(paths) > 1:
            duplicates.append(f"{name}: {', '.join(paths)}")
    
    return duplicates


def check_python_task(resources_dir: Path) -> list[str]:
    """Check for invalid python_task usage."""
    errors = []
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            if "python_task:" in content:
                # Check if it's actually python_task (not a comment)
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(r'^\s*python_task:', line):
                        errors.append(f"{yml_file}:{i}: Found python_task (should be notebook_task)")
        except Exception as e:
            errors.append(f"{yml_file}: Error reading file: {e}")
    
    return errors


def check_cli_parameters(resources_dir: Path) -> list[str]:
    """Check for CLI-style parameters."""
    errors = []
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            # Look for parameters: with -- flags
            if re.search(r'parameters:\s*\n\s*-\s*["\']--', content):
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(r'^\s*-\s*["\']--', line) and 'parameters:' in '\n'.join(lines[max(0, i-5):i]):
                        errors.append(f"{yml_file}:{i}: Found CLI-style parameters (should be base_parameters)")
        except Exception as e:
            errors.append(f"{yml_file}: Error reading file: {e}")
    
    return errors


def check_variable_references(resources_dir: Path) -> list[str]:
    """Check for missing var. prefix in variable references."""
    errors = []
    # Common variables that should have var. prefix
    variables = ['catalog', 'bronze_schema', 'silver_schema', 'gold_schema', 'warehouse_id']
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            for var in variables:
                # Look for ${var} without var. prefix (but not ${var.var})
                pattern = rf'\$\{{{var}\}}'
                if re.search(pattern, content):
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            errors.append(f"{yml_file}:{i}: Found ${{{var}}} without var. prefix (should be ${{var.{var}}})")
        except Exception as e:
            errors.append(f"{yml_file}: Error reading file: {e}")
    
    return errors


def check_job_task(resources_dir: Path) -> list[str]:
    """Check for invalid job_task (should be run_job_task)."""
    errors = []
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            # Look for job_task: that's not run_job_task:
            if re.search(r'^\s*job_task:', content, re.MULTILINE):
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(r'^\s*job_task:', line) and 'run_job_task' not in line:
                        errors.append(f"{yml_file}:{i}: Found job_task (should be run_job_task)")
        except Exception as e:
            errors.append(f"{yml_file}: Error reading file: {e}")
    
    return errors


def check_missing_environment_key(resources_dir: Path) -> list[str]:
    """Check for tasks missing environment_key."""
    errors = []
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            # Look for tasks without environment_key
            lines = content.split('\n')
            in_task = False
            has_environment_key = False
            
            for i, line in enumerate(lines, 1):
                if re.search(r'^\s*task_key:', line):
                    in_task = True
                    has_environment_key = False
                elif re.search(r'^\s*environment_key:', line) and in_task:
                    has_environment_key = True
                elif re.search(r'^\s*(notebook_task|python_task|sql_task|pipeline_task|run_job_task):', line):
                    if in_task and not has_environment_key:
                        errors.append(f"{yml_file}:{i}: Task missing environment_key")
                    in_task = False
                    has_environment_key = False
        except Exception as e:
            errors.append(f"{yml_file}: Error reading file: {e}")
    
    return errors


def check_alert_schema(resources_dir: Path) -> list[str]:
    """Check for common Alert v2 schema mistakes."""
    errors = []
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            if "alerts:" not in content:
                continue
            
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Check for wrong field name: "condition:" instead of "evaluation:"
                if re.search(r'^\s+condition:', line) and 'alerts:' in content:
                    errors.append(f"{yml_file}:{i}: Alert uses 'condition:' (should be 'evaluation:')")
                # Check for wrong cron field in alerts
                if re.search(r'^\s+quartz_cron_expression:', line) and 'alerts:' in content:
                    errors.append(f"{yml_file}:{i}: Alert uses 'quartz_cron_expression' (should be 'quartz_cron_schedule')")
                # Check for top-level subscriptions (should be under evaluation.notification)
                if re.search(r'^\s{4}subscriptions:', line) and 'alerts:' in content:
                    errors.append(f"{yml_file}:{i}: Alert 'subscriptions' may be at wrong level (should be under evaluation.notification)")
        except Exception as e:
            errors.append(f"{yml_file}: Error reading file: {e}")
    
    return errors


def check_volume_permissions(resources_dir: Path) -> list[str]:
    """Check for volumes using permissions instead of grants."""
    errors = []
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            if "volumes:" not in content:
                continue
            if "permissions:" in content:
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(r'^\s+permissions:', line):
                        errors.append(f"{yml_file}:{i}: Volume uses 'permissions:' (should be 'grants:')")
        except Exception as e:
            errors.append(f"{yml_file}: Error reading file: {e}")
    
    return errors


def check_dashboard_hardcoded_catalog(resources_dir: Path) -> list[str]:
    """Warn if dashboards are missing dataset_catalog/dataset_schema."""
    warnings = []
    
    for yml_file in resources_dir.rglob("*.yml"):
        try:
            content = yml_file.read_text()
            if "dashboards:" not in content:
                continue
            if "file_path:" in content and "dataset_catalog:" not in content:
                warnings.append(f"{yml_file}: Dashboard missing 'dataset_catalog:' (catalog may be hardcoded in JSON)")
        except Exception as e:
            warnings.append(f"{yml_file}: Error reading file: {e}")
    
    return warnings


def main():
    """Run all validation checks."""
    print("🔍 Pre-Deployment Validation")
    print("=" * 50)
    
    # Find resources directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent  # Go up to project root
    resources_dir = project_root / "resources"
    
    if not resources_dir.exists():
        print(f"❌ ERROR: Resources directory not found: {resources_dir}")
        sys.exit(1)
    
    all_errors = []
    
    # 1. Check for duplicate files
    print("\n1. Checking for duplicate resource files...")
    duplicates = find_duplicate_files(resources_dir)
    if duplicates:
        print("❌ ERROR: Duplicate resource files found:")
        for dup in duplicates:
            print(f"   {dup}")
        all_errors.extend(duplicates)
    else:
        print("✅ No duplicate files")
    
    # 2. Check for python_task
    print("\n2. Checking for invalid python_task...")
    python_task_errors = check_python_task(resources_dir)
    if python_task_errors:
        print("❌ ERROR: Found python_task (should be notebook_task)")
        for error in python_task_errors:
            print(f"   {error}")
        all_errors.extend(python_task_errors)
    else:
        print("✅ No python_task found")
    
    # 3. Check for CLI-style parameters
    print("\n3. Checking for CLI-style parameters...")
    cli_param_errors = check_cli_parameters(resources_dir)
    if cli_param_errors:
        print("❌ ERROR: Found CLI-style parameters (should be base_parameters)")
        for error in cli_param_errors:
            print(f"   {error}")
        all_errors.extend(cli_param_errors)
    else:
        print("✅ No CLI-style parameters found")
    
    # 4. Check for variable references
    print("\n4. Checking for variable references...")
    var_ref_errors = check_variable_references(resources_dir)
    if var_ref_errors:
        print("❌ ERROR: Found variable references without var. prefix")
        for error in var_ref_errors:
            print(f"   {error}")
        all_errors.extend(var_ref_errors)
    else:
        print("✅ Variable references correct")
    
    # 5. Check for job_task
    print("\n5. Checking for invalid job_task...")
    job_task_errors = check_job_task(resources_dir)
    if job_task_errors:
        print("❌ ERROR: Found job_task (should be run_job_task)")
        for error in job_task_errors:
            print(f"   {error}")
        all_errors.extend(job_task_errors)
    else:
        print("✅ No invalid job_task found")
    
    # 6. Check for missing environment_key
    print("\n6. Checking for missing environment_key in tasks...")
    env_key_errors = check_missing_environment_key(resources_dir)
    if env_key_errors:
        print("❌ ERROR: Found tasks missing environment_key")
        for error in env_key_errors:
            print(f"   {error}")
        all_errors.extend(env_key_errors)
    else:
        print("✅ All tasks have environment_key")
    
    # 7. Check for Alert v2 schema mistakes
    print("\n7. Checking for Alert v2 schema mistakes...")
    alert_errors = check_alert_schema(resources_dir)
    if alert_errors:
        print("❌ ERROR: Found Alert v2 schema issues")
        for error in alert_errors:
            print(f"   {error}")
        all_errors.extend(alert_errors)
    else:
        print("✅ No Alert schema issues")
    
    # 8. Check for Volume permissions format
    print("\n8. Checking for Volume permissions format...")
    volume_errors = check_volume_permissions(resources_dir)
    if volume_errors:
        print("❌ ERROR: Found Volumes using permissions (should be grants)")
        for error in volume_errors:
            print(f"   {error}")
        all_errors.extend(volume_errors)
    else:
        print("✅ Volume permissions correct")
    
    # 9. Check for Dashboard hardcoded catalogs
    print("\n9. Checking for Dashboard catalog parameterization...")
    dashboard_warnings = check_dashboard_hardcoded_catalog(resources_dir)
    if dashboard_warnings:
        print("⚠️  WARNING: Dashboards may have hardcoded catalogs")
        for warning in dashboard_warnings:
            print(f"   {warning}")
        # These are warnings, not errors - don't fail the build
    else:
        print("✅ Dashboard catalogs parameterized")
    
    # Summary
    print("\n" + "=" * 50)
    if all_errors:
        print(f"❌ Validation failed with {len(all_errors)} error(s)")
        print("\nPlease fix the errors above before deploying.")
        sys.exit(1)
    else:
        print("✅ All pre-deployment checks passed!")
        print("\nNext steps:")
        print("  1. Run: databricks bundle validate")
        print("  2. Deploy: databricks bundle deploy -t dev")


if __name__ == "__main__":
    main()

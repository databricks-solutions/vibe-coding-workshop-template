#!/usr/bin/env python3
"""
Convert Cursor rules (.mdc files) to Agent Skills following AgentSkills.io specification.

Usage:
    python convert-rule-to-skill.py <input.mdc> [--output-dir <path>]
    
Examples:
    python convert-rule-to-skill.py 21-self-improvement.mdc
    python convert-rule-to-skill.py rules/my-rule.mdc --output-dir skills/
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def parse_cursor_rule(content: str) -> Tuple[Dict[str, str], str]:
    """
    Parse a cursor rule into frontmatter and body.
    
    Args:
        content: The full content of the .mdc file
        
    Returns:
        Tuple of (frontmatter dict, body string)
    """
    # Match YAML frontmatter between --- markers
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if match:
        frontmatter_text = match.group(1)
        body = match.group(2)
        
        # Parse YAML-like frontmatter (simple key: value pairs)
        frontmatter = {}
        current_key = None
        current_value = []
        
        for line in frontmatter_text.split('\n'):
            # Check for new key
            if ':' in line and not line.startswith(' ') and not line.startswith('\t'):
                # Save previous key if exists
                if current_key:
                    frontmatter[current_key] = '\n'.join(current_value).strip()
                
                key, value = line.split(':', 1)
                current_key = key.strip()
                current_value = [value.strip()]
            elif current_key:
                # Continue multi-line value
                current_value.append(line)
        
        # Save last key
        if current_key:
            frontmatter[current_key] = '\n'.join(current_value).strip()
            
        return frontmatter, body
    
    # No frontmatter found
    return {}, content


def generate_skill_name(filename: str) -> str:
    """
    Convert filename to valid AgentSkills.io skill name.
    
    Requirements:
    - Max 64 characters
    - Lowercase letters, numbers, and hyphens only
    - No leading/trailing hyphens
    - No consecutive hyphens
    """
    # Remove extension
    name = filename
    for ext in ['.mdc', '.md', '.markdown']:
        name = name.replace(ext, '')
    
    # Remove leading numbers and separators (e.g., "21-")
    name = re.sub(r'^\d+[-_]?', '', name)
    
    # Convert to lowercase
    name = name.lower()
    
    # Replace underscores, spaces, and other separators with hyphens
    name = re.sub(r'[_\s.]+', '-', name)
    
    # Remove any non-allowed characters
    name = re.sub(r'[^a-z0-9-]', '', name)
    
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    # Truncate to 64 characters
    if len(name) > 64:
        name = name[:64].rstrip('-')
    
    return name or 'unnamed-skill'


def generate_description(
    frontmatter: Dict[str, str], 
    body: str, 
    skill_name: str
) -> str:
    """
    Generate a skill description from cursor rule content.
    
    Requirements:
    - Max 1024 characters
    - Non-empty
    - Describes WHAT and WHEN
    """
    # Start with existing description
    description = frontmatter.get('description', '')
    
    # If no description, extract from body
    if not description:
        # Try to find first meaningful paragraph
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        for line in lines:
            # Skip headers
            if not line.startswith('#'):
                description = line[:500]
                break
    
    # Add context from globs if present
    globs = frontmatter.get('globs', '')
    always_apply = frontmatter.get('alwaysApply', 'false').lower()
    
    triggers = []
    if globs and globs not in ['**/*', '*']:
        triggers.append(f"files matching {globs}")
    
    # Add "Use when" clause if we have triggers or can infer them
    if triggers:
        if not description.rstrip().endswith('.'):
            description += '.'
        description += f" Use for {', '.join(triggers)}."
    elif always_apply == 'true':
        if not description.rstrip().endswith('.'):
            description += '.'
        description += " Applies broadly across the codebase."
    
    # Ensure we have WHEN clause
    if 'use when' not in description.lower() and 'use for' not in description.lower():
        # Add generic trigger based on skill name
        readable_name = skill_name.replace('-', ' ')
        description += f" Use when working on {readable_name} tasks."
    
    # Truncate to 1024 chars
    if len(description) > 1024:
        description = description[:1020] + '...'
    
    return description.strip()


def analyze_complexity(body: str) -> Dict[str, bool]:
    """
    Analyze rule content to determine what optional directories to create.
    """
    result = {
        'needs_scripts': False,
        'needs_references': False,
        'needs_assets': False
    }
    
    # Count code blocks
    code_blocks = re.findall(r'```(?:python|bash|sh|javascript|typescript)[\s\S]*?```', body)
    if len(code_blocks) >= 3:
        result['needs_scripts'] = True
    
    # Check for long content (>300 lines suggests need for references)
    line_count = len(body.split('\n'))
    if line_count > 300:
        result['needs_references'] = True
    
    # Check for templates or assets
    template_indicators = ['template', 'example output', 'sample', 'boilerplate']
    if any(indicator in body.lower() for indicator in template_indicators):
        result['needs_assets'] = True
    
    return result


def transform_body(body: str, skill_name: str) -> str:
    """
    Transform cursor rule body into skill body format.
    """
    # Convert skill name to title
    title = ' '.join(word.capitalize() for word in skill_name.split('-'))
    
    # Check if body already has a top-level header
    has_header = body.strip().startswith('#')
    
    if has_header:
        # Keep existing structure, just clean up
        transformed = body
    else:
        # Add structure
        transformed = f"# {title}\n\n{body}"
    
    return transformed


def generate_skill_md(
    skill_name: str,
    description: str,
    body: str,
    license_text: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate the complete SKILL.md content.
    """
    # Build frontmatter
    frontmatter_lines = [
        '---',
        f'name: {skill_name}',
        f'description: {description}'
    ]
    
    if license_text:
        frontmatter_lines.append(f'license: {license_text}')
    
    if metadata:
        frontmatter_lines.append('metadata:')
        for key, value in metadata.items():
            frontmatter_lines.append(f'  {key}: "{value}"')
    
    frontmatter_lines.append('---')
    
    # Combine
    return '\n'.join(frontmatter_lines) + '\n\n' + body


def create_skill_structure(
    output_dir: Path,
    skill_name: str,
    skill_md_content: str,
    complexity: Dict[str, bool]
) -> None:
    """
    Create the skill directory structure.
    """
    skill_dir = output_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Write SKILL.md
    (skill_dir / 'SKILL.md').write_text(skill_md_content)
    print(f"Created: {skill_dir / 'SKILL.md'}")
    
    # Create optional directories
    if complexity['needs_scripts']:
        scripts_dir = skill_dir / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        # Create placeholder
        (scripts_dir / '.gitkeep').write_text('# Add scripts here\n')
        print(f"Created: {scripts_dir}/")
    
    if complexity['needs_references']:
        refs_dir = skill_dir / 'references'
        refs_dir.mkdir(exist_ok=True)
        (refs_dir / '.gitkeep').write_text('# Add reference documentation here\n')
        print(f"Created: {refs_dir}/")
    
    if complexity['needs_assets']:
        assets_dir = skill_dir / 'assets'
        assets_dir.mkdir(exist_ok=True)
        (assets_dir / '.gitkeep').write_text('# Add templates and assets here\n')
        print(f"Created: {assets_dir}/")


def convert_rule_to_skill(
    input_path: str,
    output_dir: Optional[str] = None
) -> str:
    """
    Main conversion function.
    
    Args:
        input_path: Path to the .mdc file
        output_dir: Optional output directory (defaults to current dir)
        
    Returns:
        Path to created skill directory
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Read input
    content = input_file.read_text()
    
    # Parse
    frontmatter, body = parse_cursor_rule(content)
    
    # Generate skill components
    skill_name = generate_skill_name(input_file.name)
    description = generate_description(frontmatter, body, skill_name)
    transformed_body = transform_body(body, skill_name)
    complexity = analyze_complexity(body)
    
    # Generate SKILL.md content
    skill_md = generate_skill_md(
        skill_name=skill_name,
        description=description,
        body=transformed_body,
        metadata={
            'converted-from': input_file.name,
            'version': '1.0.0'
        }
    )
    
    # Determine output directory
    out_dir = Path(output_dir) if output_dir else Path('.')
    
    # Create structure
    create_skill_structure(out_dir, skill_name, skill_md, complexity)
    
    skill_path = out_dir / skill_name
    print(f"\n✅ Successfully converted '{input_file.name}' to skill '{skill_name}'")
    print(f"   Location: {skill_path.absolute()}")
    
    return str(skill_path)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Cursor rules to Agent Skills',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my-rule.mdc
  %(prog)s my-rule.mdc --output-dir ./skills/
  %(prog)s .cursor/rules/21-self-improvement.mdc --output-dir ~/skills/
        """
    )
    parser.add_argument(
        'input',
        help='Path to the cursor rule file (.mdc)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='.',
        help='Output directory for the skill (default: current directory)'
    )
    
    args = parser.parse_args()
    
    try:
        convert_rule_to_skill(args.input, args.output_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

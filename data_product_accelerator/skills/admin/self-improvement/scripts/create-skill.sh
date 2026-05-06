#!/bin/bash
# create-skill.sh - Interactive script to create a new skill from a learning
# Usage: ./create-skill.sh [skill-name]

set -e

# Configuration
SKILLS_DIR="skills"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Self-Improvement: Create Skill       ${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Get skill name
if [ -n "$1" ]; then
    SKILL_NAME="$1"
else
    echo -e "${YELLOW}Enter skill name (kebab-case, e.g., 'notebook-import-patterns'):${NC}"
    read -r SKILL_NAME
fi

# Validate and normalize skill name
SKILL_NAME=$(echo "$SKILL_NAME" | tr '[:upper:]' '[:lower:]' | tr ' _' '-' | tr -cd 'a-z0-9-' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')

if [ -z "$SKILL_NAME" ]; then
    echo -e "${RED}Error: Skill name cannot be empty${NC}"
    exit 1
fi

if [ ${#SKILL_NAME} -gt 64 ]; then
    echo -e "${RED}Error: Skill name must be 64 characters or less${NC}"
    exit 1
fi

# Check if skill already exists
SKILL_PATH="$SKILLS_DIR/$SKILL_NAME"
if [ -d "$SKILL_PATH" ]; then
    echo -e "${YELLOW}Skill '$SKILL_NAME' already exists at $SKILL_PATH${NC}"
    echo "Would you like to edit it instead? (y/n)"
    read -r EDIT_CHOICE
    if [ "$EDIT_CHOICE" = "y" ] || [ "$EDIT_CHOICE" = "Y" ]; then
        echo -e "${GREEN}Opening: $SKILL_PATH/SKILL.md${NC}"
        exit 0
    else
        echo "Exiting."
        exit 0
    fi
fi

# Get skill title
echo
echo -e "${YELLOW}Enter a human-readable title (e.g., 'Notebook Import Patterns'):${NC}"
read -r SKILL_TITLE

# Get description
echo
echo -e "${YELLOW}Enter description (what it does + when to use):${NC}"
read -r SKILL_DESC

# Get trigger scenarios
echo
echo -e "${YELLOW}Enter trigger scenario 1 (when should this skill be used?):${NC}"
read -r TRIGGER1
echo -e "${YELLOW}Enter trigger scenario 2:${NC}"
read -r TRIGGER2
echo -e "${YELLOW}Enter trigger scenario 3 (or press Enter to skip):${NC}"
read -r TRIGGER3

# Get problem description
echo
echo -e "${YELLOW}Describe the problem this skill addresses:${NC}"
read -r PROBLEM

# Get root cause
echo
echo -e "${YELLOW}What is the root cause?${NC}"
read -r ROOT_CAUSE

# Get key insight
echo
echo -e "${YELLOW}What is the key insight (one sentence)?${NC}"
read -r KEY_INSIGHT

# Create skill directory
mkdir -p "$SKILL_PATH"

# Build triggers section
TRIGGERS="- $TRIGGER1
- $TRIGGER2"
if [ -n "$TRIGGER3" ]; then
    TRIGGERS="$TRIGGERS
- $TRIGGER3"
fi

# Create SKILL.md
cat > "$SKILL_PATH/SKILL.md" << EOF
---
name: $SKILL_NAME
description: $SKILL_DESC
---

# $SKILL_TITLE

$PROBLEM

## When to Use

$TRIGGERS

## The Problem

$PROBLEM

### Root Cause
$ROOT_CAUSE

### Common Symptoms
- [Add specific error messages or behaviors]

## The Solution

[Describe the correct approach]

### Correct Pattern
\`\`\`python
# Example of the right way
\`\`\`

### Incorrect Pattern (Avoid)
\`\`\`python
# Example of what NOT to do
\`\`\`

## Prevention Checklist

- [ ] [Add actionable check 1]
- [ ] [Add actionable check 2]
- [ ] [Add actionable check 3]

## Generalized Principle

> **Key Insight:** $KEY_INSIGHT

[Expand on the broader lesson that applies beyond this specific case]

## References

- [Add links to documentation or related skills]
EOF

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Skill created successfully!          ${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "Created: ${BLUE}$SKILL_PATH/SKILL.md${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Open $SKILL_PATH/SKILL.md"
echo "2. Fill in the [bracketed] sections"
echo "3. Add code examples for correct and incorrect patterns"
echo "4. Complete the prevention checklist"
echo "5. Add relevant references"

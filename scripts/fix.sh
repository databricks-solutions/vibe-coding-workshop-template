#!/bin/bash
# ============================================================================
# Code Formatting Script
# Formats Python and TypeScript/JavaScript code
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🔧 Formatting Code"
echo "=================="
echo ""

# Format Python with ruff
if command -v ruff &> /dev/null; then
    echo -e "${BLUE}Formatting Python files...${NC}"
    ruff check --fix . 2>/dev/null || true
    ruff format .
    echo -e "${GREEN}✓ Python formatted${NC}"
elif command -v black &> /dev/null; then
    echo -e "${BLUE}Formatting Python files with black...${NC}"
    black .
    echo -e "${GREEN}✓ Python formatted${NC}"
else
    echo "⚠ No Python formatter found (install ruff or black)"
fi

echo ""

# Format TypeScript/JavaScript with prettier
if [ -d "client" ]; then
    cd client
    
    if command -v prettier &> /dev/null || [ -f "node_modules/.bin/prettier" ]; then
        echo -e "${BLUE}Formatting frontend files...${NC}"
        
        if [ -f "node_modules/.bin/prettier" ]; then
            ./node_modules/.bin/prettier --write "src/**/*.{ts,tsx,js,jsx,css,json}"
        else
            prettier --write "src/**/*.{ts,tsx,js,jsx,css,json}"
        fi
        
        echo -e "${GREEN}✓ Frontend formatted${NC}"
    else
        echo "⚠ Prettier not found in client/"
    fi
    
    cd ..
fi

echo ""
echo -e "${GREEN}✓ Code formatting complete!${NC}"


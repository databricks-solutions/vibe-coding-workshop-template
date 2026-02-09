#!/bin/bash
# ============================================================================
# Development Watch Script
# Runs local development servers with hot reload
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PID_FILE="/tmp/databricks-app-watch.pid"
LOG_FILE="/tmp/databricks-app-watch.log"

# Parse arguments
VERBOSE=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --verbose) VERBOSE=true ;;
        --stop)
            if [ -f "$PID_FILE" ]; then
                kill $(cat "$PID_FILE") 2>/dev/null || true
                rm -f "$PID_FILE"
                echo -e "${GREEN}✓ Development servers stopped${NC}"
            else
                echo -e "${YELLOW}No running servers found${NC}"
            fi
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --verbose  Show all output in terminal"
            echo "  --stop     Stop running development servers"
            echo "  -h, --help Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

echo "🔄 Starting Development Servers"
echo "================================"
echo ""

# Load environment
if [ -f ".env.local" ]; then
    source .env.local
    export DATABRICKS_HOST
    export DATABRICKS_TOKEN
    export DATABRICKS_CONFIG_PROFILE
fi

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Development servers already running (PID: $OLD_PID)${NC}"
        echo "  Stop with: $0 --stop"
        exit 1
    fi
fi

# Start backend server
start_backend() {
    echo -e "${BLUE}Starting FastAPI backend on port 8000...${NC}"
    
    if command -v uv &> /dev/null; then
        uv run uvicorn server.app:app --reload --host 0.0.0.0 --port 8000 &
    else
        python -m uvicorn server.app:app --reload --host 0.0.0.0 --port 8000 &
    fi
    
    BACKEND_PID=$!
    echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
}

# Start frontend server
start_frontend() {
    if [ -d "client" ] && [ -f "client/package.json" ]; then
        echo -e "${BLUE}Starting React frontend on port 5173...${NC}"
        
        cd client
        if command -v bun &> /dev/null; then
            bun run dev &
        else
            npm run dev &
        fi
        FRONTEND_PID=$!
        cd ..
        
        echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${YELLOW}⚠ No frontend found (client/ directory missing)${NC}"
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    pkill -P $$ 2>/dev/null || true
    rm -f "$PID_FILE"
    echo -e "${GREEN}✓ Servers stopped${NC}"
}

trap cleanup EXIT INT TERM

# Start servers
start_backend
start_frontend

# Save main PID
echo $$ > "$PID_FILE"

echo ""
echo "============================================"
echo -e "${GREEN}🎉 Development servers running!${NC}"
echo "============================================"
echo ""
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"

if [ -d "client" ]; then
    echo "  Frontend: http://localhost:5173"
fi

echo ""
echo "  Logs:     tail -f $LOG_FILE"
echo "  Stop:     ./scripts/watch.sh --stop"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop all servers${NC}"
echo ""

# Wait for processes
wait


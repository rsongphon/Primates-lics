#!/bin/bash

# Parse command line arguments
VERBOSE=0
DEBUG=0

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -v|--verbose) VERBOSE=1 ;;
        -d|--debug) DEBUG=1; VERBOSE=1 ;;  # Debug implies verbose
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose    Show detailed output for each test"
            echo "  -d, --debug      Enable debug mode (bash tracing with set -x)"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                # Run tests with standard output"
            echo "  $0 --verbose      # Run tests with detailed output"
            echo "  $0 --debug        # Run tests with bash command tracing"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Enable bash tracing if debug mode
if [ $DEBUG -eq 1 ]; then
    set -x
fi

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   PHASE 2 COMPREHENSIVE TEST${NC}"
echo -e "${BLUE}   Backend Core Development (Weeks 3-4)${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""

if [ $VERBOSE -eq 1 ]; then
    echo -e "${YELLOW}[INFO]${NC} Verbose mode enabled"
fi
if [ $DEBUG -eq 1 ]; then
    echo -e "${YELLOW}[INFO]${NC} Debug mode enabled (bash tracing)"
fi
echo ""

# Test 1: Project Structure
echo -e "${BLUE}### TEST 1: Project Structure & Base Configuration${NC}"
echo ""

if [ $VERBOSE -eq 1 ]; then
    echo -e "${YELLOW}[STEP]${NC} Checking core files existence..."
fi

files=(
    "app/main.py"
    "app/core/config.py"
    "app/core/database.py"
    "app/core/security.py"
    "app/models/base.py"
    "app/models/auth.py"
    "app/models/domain.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
        if [ $VERBOSE -eq 1 ]; then
            lines=$(wc -l < "$file" 2>/dev/null)
            echo -e "  ${YELLOW}→${NC} Lines: $lines"
        fi
    else
        echo -e "${RED}✗${NC} $file MISSING"
    fi
done

echo ""
if [ $VERBOSE -eq 1 ]; then
    echo -e "${YELLOW}[STEP]${NC} Calculating line counts (complexity indicator)..."
fi
echo "Line counts:"
wc -l app/main.py app/core/config.py app/core/security.py 2>/dev/null | tail -1

echo ""
echo "### TEST 2: Authentication & Authorization"
echo ""
echo "Checking auth implementation:"

auth_files=(
    "app/core/security.py"
    "app/models/auth.py"
    "app/schemas/auth.py"
    "app/services/auth.py"
    "app/api/v1/auth.py"
    "app/api/v1/rbac.py"
    "app/middleware/auth.py"
)

for file in "${auth_files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file" 2>/dev/null)
        echo "✓ $file ($lines lines)"
    else
        echo "✗ $file MISSING"
    fi
done

echo ""
echo "### TEST 3: Core Domain Models"
echo ""

domain_files=(
    "app/models/domain.py"
    "app/schemas/devices.py"
    "app/schemas/experiments.py"
    "app/schemas/tasks.py"
    "app/repositories/domain.py"
    "app/services/domain.py"
)

for file in "${domain_files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file" 2>/dev/null)
        echo "✓ $file ($lines lines)"
    else
        echo "✗ $file MISSING"
    fi
done

echo ""
echo "### TEST 4: RESTful API Endpoints"
echo ""

api_files=(
    "app/api/v1/organizations.py"
    "app/api/v1/devices.py"
    "app/api/v1/experiments.py"
    "app/api/v1/tasks.py"
    "app/api/v1/participants.py"
)

for file in "${api_files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file" 2>/dev/null)
        endpoints=$(grep -c "^@router\." "$file" 2>/dev/null || echo "0")
        echo "✓ $file ($lines lines, ~$endpoints endpoints)"
    else
        echo "✗ $file MISSING"
    fi
done

echo ""
echo "### TEST 5: WebSocket Implementation"
echo ""

ws_files=(
    "app/websocket/server.py"
    "app/websocket/handlers/device_handlers.py"
    "app/websocket/handlers/experiment_handlers.py"
    "app/websocket/handlers/task_handlers.py"
    "app/websocket/handlers/notification_handlers.py"
)

for file in "${ws_files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file" 2>/dev/null)
        handlers=$(grep -c "^async def" "$file" 2>/dev/null || echo "0")
        echo "✓ $file ($lines lines, ~$handlers handlers)"
    else
        echo "✗ $file MISSING"
    fi
done

echo ""
echo "### TEST 6: Background Tasks (Celery)"
echo ""

task_files=(
    "app/tasks/celery_app.py"
    "app/tasks/data_processing.py"
    "app/tasks/notifications.py"
    "app/tasks/reports.py"
    "app/tasks/maintenance.py"
    "app/tasks/metrics.py"
)

for file in "${task_files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file" 2>/dev/null)
        tasks=$(grep -c "@celery_app.task" "$file" 2>/dev/null || echo "0")
        echo "✓ $file ($lines lines, ~$tasks tasks)"
    else
        echo "✗ $file MISSING"
    fi
done

echo ""
echo "### TEST 7: Database Migrations"
echo ""
migrations_dir="../../infrastructure/database/alembic/versions"
if [ -d "$migrations_dir" ]; then
    migration_count=$(ls -1 "$migrations_dir"/*.py 2>/dev/null | wc -l)
    echo "✓ Alembic migrations directory exists"
    echo "  Migration files: $migration_count"
    if [ $migration_count -gt 0 ]; then
        echo "  Latest migrations:"
        ls -1t "$migrations_dir"/*.py 2>/dev/null | head -3 | while read file; do
            echo "    - $(basename $file)"
        done
    fi
else
    echo "✗ Migrations directory MISSING"
fi

echo ""
echo "### TEST 8: Dependencies Check"
echo ""
echo "Checking requirements.txt:"
if [ -f "requirements.txt" ]; then
    total_deps=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
    echo "✓ requirements.txt exists ($total_deps dependencies)"
    echo "  Key dependencies:"
    grep -E "fastapi|sqlalchemy|celery|socketio|jwt" requirements.txt | head -5
else
    echo "✗ requirements.txt MISSING"
fi

echo ""
echo "=== TEST SUMMARY ==="
echo ""
echo "Checking critical markers:"
echo "- FastAPI app: $([ -f 'app/main.py' ] && echo '✓' || echo '✗')"
echo "- Database models: $([ -f 'app/models/domain.py' ] && echo '✓' || echo '✗')"
echo "- API endpoints: $([ -d 'app/api/v1' ] && echo '✓' || echo '✗')"
echo "- WebSocket: $([ -f 'app/websocket/server.py' ] && echo '✓' || echo '✗')"
echo "- Celery tasks: $([ -f 'app/tasks/celery_app.py' ] && echo '✓' || echo '✗')"
echo "- Authentication: $([ -f 'app/core/security.py' ] && echo '✓' || echo '✗')"


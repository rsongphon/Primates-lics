#!/bin/bash
# LICS Development CLI - Run commands in containerized environment
# Usage: ./tools/dev-cli.sh <command> [args]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEVCONTAINER_SERVICE="devcontainer"
FRONTEND_SERVICE="frontend-dev"
BACKEND_SERVICE="backend-dev"
EDGE_SERVICE="edge-agent-dev"
COMPOSE_FILES="-f docker-compose.yml"

# Check if using devcontainer
if docker-compose ps $DEVCONTAINER_SERVICE &>/dev/null; then
    USE_DEVCONTAINER=true
    echo -e "${BLUE}ℹ Using devcontainer${NC}"
else
    USE_DEVCONTAINER=false
    echo -e "${BLUE}ℹ Using standalone containers${NC}"
fi

# Helper functions
print_help() {
    cat << EOF
${GREEN}LICS Development CLI${NC}
Run commands in containerized development environment

${YELLOW}Usage:${NC}
  ./tools/dev-cli.sh <command> [args]

${YELLOW}Container Management:${NC}
  shell              - Open bash shell in dev container
  frontend-shell     - Open shell in frontend container
  backend-shell      - Open shell in backend container
  edge-shell         - Open shell in edge-agent container

${YELLOW}Frontend Commands:${NC}
  npm <args>         - Run npm command in frontend
  pnpm <args>        - Run pnpm command in frontend
  next <args>        - Run Next.js CLI commands

${YELLOW}Backend Commands:${NC}
  python <args>      - Run Python in backend
  pip <args>         - Run pip in backend
  pytest <args>      - Run pytest in backend
  uvicorn <args>     - Run uvicorn directly

${YELLOW}Database Commands:${NC}
  alembic <args>     - Run Alembic migrations
  psql               - Connect to PostgreSQL
  redis-cli          - Connect to Redis CLI

${YELLOW}Testing Commands:${NC}
  test               - Run all tests
  test-frontend      - Run frontend tests
  test-backend       - Run backend tests
  test-integration   - Run integration tests

${YELLOW}Development Commands:${NC}
  install            - Install all dependencies
  format             - Format all code
  lint               - Run linters
  typecheck          - Run type checking

${YELLOW}Utility Commands:${NC}
  logs [service]     - View container logs
  ps                 - List running containers
  restart [service]  - Restart a service
  exec <service> <cmd> - Execute command in service

${YELLOW}Examples:${NC}
  ./tools/dev-cli.sh shell
  ./tools/dev-cli.sh npm install axios
  ./tools/dev-cli.sh pytest tests/
  ./tools/dev-cli.sh alembic upgrade head
  ./tools/dev-cli.sh logs backend-dev

EOF
}

# Execute command in devcontainer
exec_in_devcontainer() {
    docker-compose exec $DEVCONTAINER_SERVICE "$@"
}

# Execute command in specific service
exec_in_service() {
    local service=$1
    shift
    docker-compose exec $service "$@"
}

# Main command handler
case "$1" in
    # Help
    "help"|"-h"|"--help"|"")
        print_help
        ;;

    # Shell access
    "shell")
        if [ "$USE_DEVCONTAINER" = true ]; then
            echo -e "${GREEN}Opening shell in devcontainer...${NC}"
            exec_in_devcontainer bash
        else
            echo -e "${GREEN}Opening shell in backend container...${NC}"
            exec_in_service $BACKEND_SERVICE bash
        fi
        ;;

    "frontend-shell")
        echo -e "${GREEN}Opening shell in frontend container...${NC}"
        exec_in_service $FRONTEND_SERVICE sh
        ;;

    "backend-shell")
        echo -e "${GREEN}Opening shell in backend container...${NC}"
        exec_in_service $BACKEND_SERVICE bash
        ;;

    "edge-shell")
        echo -e "${GREEN}Opening shell in edge-agent container...${NC}"
        exec_in_service $EDGE_SERVICE bash
        ;;

    # Frontend commands
    "npm")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/frontend && npm $*"
        else
            exec_in_service $FRONTEND_SERVICE npm "$@"
        fi
        ;;

    "pnpm")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/frontend && pnpm $*"
        else
            exec_in_service $FRONTEND_SERVICE pnpm "$@"
        fi
        ;;

    "next")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/frontend && npx next $*"
        else
            exec_in_service $FRONTEND_SERVICE npx next "$@"
        fi
        ;;

    # Backend commands
    "python")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/backend && source venv/bin/activate && python $*"
        else
            exec_in_service $BACKEND_SERVICE python "$@"
        fi
        ;;

    "pip")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/backend && source venv/bin/activate && pip $*"
        else
            exec_in_service $BACKEND_SERVICE pip "$@"
        fi
        ;;

    "pytest")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/backend && source venv/bin/activate && pytest $*"
        else
            exec_in_service $BACKEND_SERVICE pytest "$@"
        fi
        ;;

    "uvicorn")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/backend && source venv/bin/activate && uvicorn $*"
        else
            exec_in_service $BACKEND_SERVICE uvicorn "$@"
        fi
        ;;

    # Database commands
    "alembic")
        shift
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd infrastructure/database && source ../../services/backend/venv/bin/activate && alembic $*"
        else
            exec_in_service $BACKEND_SERVICE bash -c "cd /database && alembic $*"
        fi
        ;;

    "psql")
        echo -e "${GREEN}Connecting to PostgreSQL...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer psql postgresql://lics:password@postgres:5432/lics
        else
            docker-compose exec postgres-dev psql -U lics -d lics_dev
        fi
        ;;

    "redis-cli")
        echo -e "${GREEN}Connecting to Redis...${NC}"
        docker-compose exec redis redis-cli
        ;;

    # Testing commands
    "test")
        echo -e "${GREEN}Running all tests...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer make test
        else
            ./tools/dev-cli.sh test-frontend
            ./tools/dev-cli.sh test-backend
        fi
        ;;

    "test-frontend")
        echo -e "${GREEN}Running frontend tests...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/frontend && npm test"
        else
            exec_in_service $FRONTEND_SERVICE npm test
        fi
        ;;

    "test-backend")
        echo -e "${GREEN}Running backend tests...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "cd services/backend && source venv/bin/activate && pytest"
        else
            exec_in_service $BACKEND_SERVICE pytest
        fi
        ;;

    "test-integration")
        echo -e "${GREEN}Running integration tests...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer bash -c "pytest tests/integration"
        else
            echo -e "${YELLOW}Integration tests should be run from devcontainer${NC}"
        fi
        ;;

    # Development commands
    "install")
        echo -e "${GREEN}Installing all dependencies...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer make install
        else
            ./tools/dev-cli.sh npm install
            ./tools/dev-cli.sh pip install -r requirements.txt
        fi
        ;;

    "format")
        echo -e "${GREEN}Formatting code...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer make format
        else
            ./tools/dev-cli.sh npm run format
            ./tools/dev-cli.sh python -m black services/backend
        fi
        ;;

    "lint")
        echo -e "${GREEN}Running linters...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer make lint
        else
            ./tools/dev-cli.sh npm run lint
            ./tools/dev-cli.sh python -m ruff check services/backend
        fi
        ;;

    "typecheck")
        echo -e "${GREEN}Running type checking...${NC}"
        if [ "$USE_DEVCONTAINER" = true ]; then
            exec_in_devcontainer make typecheck
        else
            ./tools/dev-cli.sh npm run typecheck
            ./tools/dev-cli.sh python -m mypy services/backend
        fi
        ;;

    # Utility commands
    "logs")
        shift
        if [ -z "$1" ]; then
            docker-compose logs -f
        else
            docker-compose logs -f "$1"
        fi
        ;;

    "ps")
        docker-compose ps
        ;;

    "restart")
        shift
        if [ -z "$1" ]; then
            echo -e "${YELLOW}Please specify a service to restart${NC}"
            exit 1
        fi
        echo -e "${GREEN}Restarting $1...${NC}"
        docker-compose restart "$1"
        ;;

    "exec")
        shift
        if [ -z "$1" ] || [ -z "$2" ]; then
            echo -e "${YELLOW}Usage: ./tools/dev-cli.sh exec <service> <command>${NC}"
            exit 1
        fi
        service=$1
        shift
        exec_in_service $service "$@"
        ;;

    # Unknown command
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac

# LICS Containerized Development Environment

**Complete guide to developing LICS with zero local dependencies beyond Docker and VS Code (optional).**

## Overview

LICS provides a fully containerized development environment that eliminates the need to install Node.js, Python, PostgreSQL, Redis, MQTT, or any other dependencies on your local machine. Everything runs in Docker containers with hot-reloading, debugging support, and full IDE integration.

**Benefits:**
- Zero local dependencies (only Docker + Git required)
- Instant onboarding (<10 minutes for new developers)
- Consistent environment across all developers
- Full IDE integration with IntelliSense and debugging
- Production parity (same containers used in CI/CD)
- Easy reset and rebuild capabilities

## Prerequisites

### Required
- **Docker Desktop** 24.0+ with **Docker Compose** 2.20+
- **Git** 2.40+
- **8GB RAM**, 4 CPU cores, 20GB disk space (minimum)

### Recommended
- **VS Code** with **Dev Containers** extension
- **16GB RAM**, 8 CPU cores, 50GB SSD space
- Docker Desktop resource allocation: 8GB+ RAM, 4+ CPUs

### NOT Required
- Node.js, Python, PostgreSQL, Redis, MQTT, MinIO, InfluxDB, or any project dependencies

---

## Quick Start

### Option 1: VS Code Dev Containers (Recommended)

**Best for:** Daily development, debugging, full IDE features

1. **Install VS Code and Dev Containers extension**
   ```bash
   # Install VS Code: https://code.visualstudio.com/
   # Extension ID: ms-vscode-remote.remote-containers
   ```

2. **Open project and reopen in container**
   ```bash
   git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics
   code .
   # Click "Reopen in Container" or press F1 → "Dev Containers: Reopen in Container"
   ```

3. **Wait for setup** (5-10 minutes first time)
   - Container builds automatically
   - Dependencies install automatically
   - Database migrations run automatically

4. **Start developing**
   ```bash
   # In VS Code terminal (you're now inside the container):
   make dev              # Start all services

   # Access services:
   # Frontend:    http://localhost:3000
   # Backend API: http://localhost:8000/docs
   # PgAdmin:     http://localhost:5050
   ```

### Option 2: Standalone Docker Compose

**Best for:** Editor-agnostic development, CI/CD, automation

1. **Start all services**
   ```bash
   git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics
   make container-dev
   ```

2. **Get a shell or run commands**
   ```bash
   # Interactive shell
   make container-shell

   # Or run commands directly
   ./tools/dev-cli.sh npm install
   ./tools/dev-cli.sh pytest
   ./tools/dev-cli.sh alembic upgrade head
   ```

3. **View logs and manage services**
   ```bash
   make container-logs              # View all logs
   make container-stop              # Stop services
   make container-clean             # Remove everything (WARNING: deletes data)
   ```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────┐
│  VS Code (local machine)                │
│  or Your Editor + dev-cli.sh            │
└──────────────┬──────────────────────────┘
               │
               ├─── Dev Container (optional)
               │    └─── Node 20, Python 3.11, Dev tools
               │
               └─── Docker Network: lics-dev-network
                    ├── frontend-dev       (port 3000)
                    ├── backend-dev        (ports 8000, 8001, 5678)
                    ├── celery-worker-dev
                    ├── postgres-dev       (port 5433) + TimescaleDB
                    ├── pgbouncer-dev      (port 6433)
                    ├── redis-dev          (port 6380)
                    ├── mqtt-dev           (port 1884)
                    ├── minio-dev          (ports 9010, 9011)
                    ├── influxdb-dev       (port 8087)
                    ├── jaeger             (port 16686) - OpenTelemetry
                    ├── pgadmin            (port 5050)
                    ├── redis-commander    (port 8081)
                    ├── mailhog            (port 8025)
                    └── docs-dev           (port 8090)
```

### Volume Strategy

**Named volumes** (prevents permission issues):
- `devcontainer-node-modules` → `/workspace/services/frontend/node_modules`
- `devcontainer-backend-venv` → `/workspace/services/backend/venv`
- `postgres_dev_data`, `redis_dev_data`, `minio_dev_data`, etc.

**Bind mounts** (enables hot reload):
- `.` → `/workspace` (cached for performance)

---

## Service Access Points

All services are accessible on your local machine:

| Service | URL | Dev Port | Credentials |
|---------|-----|----------|-------------|
| **Frontend** | http://localhost:3000 | 3000 | - |
| **Backend API** | http://localhost:8000/docs | 8000, 8001 | - |
| **Backend Debugger** | localhost:5678 | 5678 | - |
| **PostgreSQL** | localhost:5433 | 5433 | lics / lics123 / lics_dev |
| **PgBouncer** | localhost:6433 | 6433 | - |
| **Redis** | localhost:6380 | 6380 | - |
| **MQTT** | localhost:1884 | 1884 | - |
| **MinIO Console** | http://localhost:9011 | 9010, 9011 | lics-dev-admin / lics-dev-minio-password-2024 |
| **InfluxDB** | localhost:8087 | 8087 | admin / devInflux123 |
| **PgAdmin** | http://localhost:5050 | 5050 | admin@lics.dev / admin123 |
| **Redis Commander** | http://localhost:8081 | 8081 | - |
| **MailHog** | http://localhost:8025 | 8025 | - |
| **Jaeger UI** | http://localhost:16686 | 16686 | - |
| **Documentation** | http://localhost:8090 | 8090 | - |

**Note:** Dev ports differ from production to avoid conflicts (e.g., postgres: 5433 vs 5432)

---

## Command Reference

### Makefile Commands

#### Core Development Commands

```bash
# Start development environment
make dev                    # Start all services with hot-reload (Ctrl+C to stop)
make dev-detached           # Start all services in background (detached mode)
make dev-stop               # Stop development environment
make dev-clean              # Stop and remove all volumes (WARNING: deletes data)
make dev-https              # Start development with HTTPS enabled

# Individual service development (NOT RECOMMENDED - use containers instead)
make dev-frontend           # Start frontend only (requires Node.js installed)
make dev-backend            # Start backend only (requires Python installed)
make dev-edge-agent         # Start edge agent only (requires Python installed)
```

#### Containerized Development Commands

```bash
# Container management
make container-help         # Show containerized development help
make container-shell        # Open bash shell in dev container
make container-dev          # Start all services in containers
make container-stop         # Stop all containers
make container-logs         # View container logs (all services)
make container-clean        # Stop containers and remove volumes (WARNING: deletes data)
make container-rebuild      # Rebuild all containers from scratch

# Development tasks in containers
make container-npm ARGS="install axios"              # Run npm command
make container-pip ARGS="install requests"           # Run pip command
make container-pytest ARGS="tests/"                  # Run pytest
make container-alembic ARGS="upgrade head"           # Run alembic migrations
make container-test                                  # Run all tests
make container-format                                # Format code
make container-lint                                  # Lint code
```

#### Testing Commands

```bash
# Basic testing (runs in containers if available)
make test                   # Run all tests (frontend, backend, edge-agent)
make test-frontend          # Run frontend tests
make test-backend           # Run backend tests
make test-edge-agent        # Run edge agent tests
make test-coverage          # Run tests with coverage report
make test-integration       # Run integration tests
make test-e2e               # Run end-to-end tests

# Comprehensive system testing
make test-comprehensive               # Run comprehensive system validation (all tests)
make test-comprehensive-quick         # Quick comprehensive validation (essential tests)
make test-comprehensive-benchmark     # Run with performance benchmarks
make test-comprehensive-stress        # Run comprehensive stress testing
make test-comprehensive-parallel      # Run comprehensive tests in parallel

# Infrastructure testing
make test-infrastructure              # Validate Docker infrastructure and services
make test-infrastructure-quick        # Quick infrastructure validation

# Database testing
make test-database                    # Test all database services comprehensively
make test-database-benchmark          # Benchmark database performance
make test-database-stress             # Stress test database services

# Messaging testing
make test-messaging                   # Test all messaging services comprehensively
make test-messaging-benchmark         # Benchmark messaging performance
make test-messaging-load              # Load test messaging services

# System integration testing
make test-system-integration          # Run end-to-end system integration tests
make test-system-integration-parallel # Run system integration tests in parallel
```

#### Health Monitoring Commands

```bash
make health-check                     # Check overall system health
make health-check-database            # Check database services health
make health-check-messaging           # Check messaging services health
make health-check-continuous          # Run continuous health monitoring (Ctrl+C to stop)
make health-check-services            # Check service health via HTTP endpoints
```

#### Performance & Validation Commands

```bash
# Performance testing
make performance-test                 # Run performance tests with K6
make performance-baseline             # Establish performance baselines

# Test reporting
make test-report                      # Generate comprehensive test report with HTML dashboard
make test-report-continuous           # Run continuous testing with reports

# Combined validation
make validate-all                     # Complete system validation (all checks)
make validate-quick                   # Quick system validation (essential checks only)
make validate-performance             # Complete performance validation
make validate-stress                  # Complete stress testing validation
```

#### Code Quality Commands

```bash
# Linting
make lint                   # Run linting for all services
make lint-frontend          # Run frontend linting
make lint-backend           # Run backend linting
make lint-edge-agent        # Run edge agent linting

# Formatting
make format                 # Format code for all services
make format-frontend        # Format frontend code
make format-backend         # Format backend code
make format-edge-agent      # Format edge agent code

# Type checking
make typecheck              # Run type checking for all services
```

#### Database Commands

```bash
make db-migrate             # Run database migrations
make db-rollback            # Rollback last migration
make db-reset               # Reset database (WARNING: destroys data)
make db-seed                # Seed database with test data
```

#### Docker Commands

```bash
# Docker image management
make docker-build           # Build all Docker images
make docker-build-frontend  # Build frontend Docker image
make docker-build-backend   # Build backend Docker image
make docker-build-edge-agent # Build edge agent Docker image

# Docker Compose operations
make docker-up              # Start all services with Docker Compose
make docker-down            # Stop all services
make docker-logs            # Show Docker logs (follow mode)
make docker-clean           # Clean Docker resources (prune system and volumes)
```

#### Infrastructure & Deployment Commands

```bash
# Terraform infrastructure
make infra-plan             # Plan infrastructure changes
make infra-apply            # Apply infrastructure changes
make infra-destroy          # Destroy infrastructure (WARNING: destroys resources)

# Kubernetes deployment
make k8s-deploy             # Deploy to Kubernetes
make k8s-status             # Show Kubernetes deployment status
```

#### Security Commands

```bash
make security-scan          # Run security scans (npm audit, safety, checkov)
make secrets-encrypt        # Encrypt secrets with sops
make secrets-decrypt        # Decrypt secrets with sops
```

#### SSL Certificate Management

```bash
make setup-ssl              # Generate SSL certificates for local development
make ssl-install-ca         # Install mkcert Certificate Authority
make ssl-clean              # Remove generated SSL certificates
make ssl-verify             # Verify SSL certificate configuration
```

#### Maintenance Commands

```bash
make clean                  # Clean build artifacts and dependencies
make update-deps            # Update all dependencies
make git-hooks-install      # Install Git hooks
make git-hooks-verify       # Verify Git hooks installation
make status                 # Show project status
```

#### Development Environment Setup

```bash
make setup-dev-env          # Run OS-specific development environment setup
make setup-mac              # Run macOS-specific setup
make setup-linux            # Run Linux-specific setup
make setup-windows          # Run Windows-specific setup
```

#### Building Commands

```bash
make build                  # Build all services
make build-frontend         # Build frontend for production
make build-backend          # Build backend package
make build-edge-agent       # Build edge agent package
```

#### Installation Commands

```bash
make install                # Install all dependencies
make install-frontend       # Install frontend dependencies
make install-backend        # Install backend dependencies
make install-edge-agent     # Install edge agent dependencies
```

#### Help & Information

```bash
make help                   # Display all available make commands with descriptions
make container-help         # Show containerized development specific help
```

### Dev CLI Commands

```bash
# Shell access
./tools/dev-cli.sh shell              # Main dev environment
./tools/dev-cli.sh frontend-shell     # Frontend container
./tools/dev-cli.sh backend-shell      # Backend container

# Frontend commands
./tools/dev-cli.sh npm <args>
./tools/dev-cli.sh pnpm <args>
./tools/dev-cli.sh next <args>

# Backend commands
./tools/dev-cli.sh python <args>
./tools/dev-cli.sh pip <args>
./tools/dev-cli.sh pytest <args>
./tools/dev-cli.sh uvicorn <args>

# Database commands
./tools/dev-cli.sh alembic <args>
./tools/dev-cli.sh psql
./tools/dev-cli.sh redis-cli

# Testing commands
./tools/dev-cli.sh test
./tools/dev-cli.sh test-frontend
./tools/dev-cli.sh test-backend

# Development commands
./tools/dev-cli.sh install
./tools/dev-cli.sh format
./tools/dev-cli.sh lint
./tools/dev-cli.sh typecheck

# Utility commands
./tools/dev-cli.sh logs [service]
./tools/dev-cli.sh ps
./tools/dev-cli.sh restart [service]
./tools/dev-cli.sh exec <service> <cmd>
```

### Direct Docker Compose

```bash
# Start specific services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend-dev frontend-dev

# View logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend-dev

# Execute commands
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend-dev pytest
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend-dev npm install

# Stop and cleanup
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v  # Remove volumes
```

---

## Common Tasks

### Installing Dependencies

**Frontend:**
```bash
# In dev container
cd services/frontend && npm install axios

# Using dev CLI
./tools/dev-cli.sh npm install axios

# Using Makefile
make container-npm ARGS="install axios"

# Rebuild to persist
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend-dev
```

**Backend:**
```bash
# In dev container
cd services/backend && source venv/bin/activate && pip install requests

# Using dev CLI
./tools/dev-cli.sh pip install requests

# Using Makefile
make container-pip ARGS="install requests"

# Update requirements.txt and rebuild
pip freeze > requirements.txt
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend-dev
```

### Running Tests

```bash
# All tests
make container-test
./tools/dev-cli.sh test

# Frontend tests
make container-npm ARGS="test"
./tools/dev-cli.sh test-frontend

# Backend tests
make container-pytest
./tools/dev-cli.sh test-backend

# Specific test file
./tools/dev-cli.sh pytest tests/unit/test_auth.py -v

# With coverage
./tools/dev-cli.sh pytest --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create migration
make container-alembic ARGS="revision --autogenerate -m 'Add user table'"
./tools/dev-cli.sh alembic revision --autogenerate -m "Add user table"

# Apply migrations
make container-alembic ARGS="upgrade head"
./tools/dev-cli.sh alembic upgrade head

# Rollback
./tools/dev-cli.sh alembic downgrade -1

# View history
./tools/dev-cli.sh alembic history

# Direct database access
./tools/dev-cli.sh psql
# Or use PgAdmin: http://localhost:5050
```

### Code Quality

```bash
# Format code
make container-format
./tools/dev-cli.sh format

# Lint code
make container-lint
./tools/dev-cli.sh lint

# Type checking
./tools/dev-cli.sh typecheck
```

### Viewing Logs

```bash
# All services
make container-logs

# Specific service
./tools/dev-cli.sh logs backend-dev
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend-dev

# Follow logs (real-time)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### Debugging

**VS Code (Dev Container):**
1. Set breakpoints in your code
2. Press `F5` to start debugging
3. Debugger attaches automatically to backend (port 5678)

**Python Remote Debugging (Standalone):**
```json
// .vscode/launch.json
{
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  },
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}/services/backend",
      "remoteRoot": "/app"
    }
  ]
}
```

**Frontend Debugging:**
- Use Chrome DevTools (works out of the box)
- Or VS Code debugger for Next.js SSR code

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :3000
lsof -i :5433

# Stop all containers
make container-stop

# Or change port in docker-compose.dev.yml
```

### Container Build Failed

```bash
# Clear cache and rebuild
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
docker image prune -a

# Remove old containers
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker system prune -f
```

### Permission Denied / File Access Issues

```bash
# Fix ownership (run on host machine)
sudo chown -R $USER:$USER .

# Reset named volumes
docker volume prune
make container-rebuild
```

### Slow Performance

**Solutions:**
1. **Increase Docker Desktop resources:**
   - Settings → Resources
   - CPUs: 4+ (recommended: 8)
   - Memory: 8GB+ (recommended: 16GB)
   - Disk: 20GB+ available

2. **Use SSD for Docker storage:**
   - Docker Desktop → Settings → Resources → Disk image location

3. **File caching** (already configured):
   ```yaml
   volumes:
     - .:/workspace:cached
   ```

4. **Named volumes for dependencies** (already configured)

### Database Connection Refused

```bash
# Check service health
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# View database logs
./tools/dev-cli.sh logs postgres-dev

# Restart database
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart postgres-dev

# Verify connection
./tools/dev-cli.sh psql
```

### "Cannot connect to Docker daemon"

```bash
# Ensure Docker Desktop is running
open /Applications/Docker.app  # macOS
# Or start Docker Desktop manually

# Check Docker status
docker info
```

### Hot Reload Not Working

**Frontend:**
```bash
# Enable polling for Docker environments
# Add to services/frontend/.env:
WATCHPACK_POLLING=true
CHOKIDAR_USEPOLLING=true
```

**Backend:**
```bash
# Uvicorn should auto-reload (check logs):
./tools/dev-cli.sh logs backend-dev

# Restart if needed:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend-dev
```

---

## FAQ

**Q: Do I need to install Node.js or Python locally?**
A: No! Everything runs in containers. Only Docker and Git are required.

**Q: Can I use my own editor instead of VS Code?**
A: Yes! Use the standalone Docker Compose approach with the dev CLI.

**Q: How do I debug code running in containers?**
A: VS Code debugger connects seamlessly to containers. Backend debugger runs on port 5678.

**Q: Can I use Git inside the container?**
A: Yes! Git credentials are mounted, and git is pre-configured. SSH keys are mounted read-only.

**Q: What happens to my database data?**
A: Stored in named Docker volumes - persists across container restarts. Use `make container-clean` to reset.

**Q: How do I update dependencies?**
A: Install them in the container, update `requirements.txt` or `package.json`, then rebuild the container.

**Q: Can I run production and dev containers simultaneously?**
A: Yes! Dev containers use different ports (5433, 6380, 1884, etc.) to avoid conflicts.

**Q: How do I reset everything?**
A:
```bash
make container-clean         # Stops and removes volumes (WARNING: deletes data)
make container-rebuild       # Rebuilds from scratch
```

**Q: Why are my changes not reflected?**
A: Check that volumes are mounted correctly. Hot reload should work automatically for both frontend (Next.js Fast Refresh) and backend (Uvicorn auto-reload).

**Q: How do I access Redis/PostgreSQL directly?**
A:
```bash
./tools/dev-cli.sh redis-cli
./tools/dev-cli.sh psql
# Or use GUIs: PgAdmin (localhost:5050), Redis Commander (localhost:8081)
```

---

## Best Practices

1. **Use VS Code Dev Containers for daily development** - Best developer experience
2. **Use dev CLI for quick tasks** - Fast and flexible
3. **Test in containers before pushing** - Ensures CI/CD compatibility
4. **Commit code changes only** - Never commit `node_modules`, `venv`, or generated files
5. **Rebuild containers weekly** - `make container-rebuild` to get latest updates
6. **Monitor Docker resource usage** - Prevent Docker from consuming all system RAM
7. **Use named volumes** - Better performance and no permission issues
8. **Keep containers running** - Use `make dev` or `make container-dev` and leave running

---

## Additional Resources

- **Project Architecture:** [Documentation.md](Documentation.md)
- **Development Guidelines:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Project Instructions:** [CLAUDE.md](CLAUDE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **VS Code Dev Containers:** https://code.visualstudio.com/docs/devcontainers/containers
- **Docker Compose:** https://docs.docker.com/compose/
- **GitHub Discussions:** https://github.com/rsongphon/Primates-lics/discussions

---

**Status:** ✅ Complete and Production-Ready
**Implementation Date:** 2025-10-02
**Last Updated:** 2025-10-12
**Maintained By:** LICS Development Team

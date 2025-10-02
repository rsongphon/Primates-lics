# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LICS (Lab Instrument Control System) is a cloud-native, distributed platform for managing laboratory instruments and conducting behavioral experiments. The system follows a microservices architecture with edge computing capabilities, enabling real-time control of multiple Raspberry Pi-based devices from a web interface.

## Architecture

### Monorepo Structure
- **services/frontend**: Next.js 14 web application with TypeScript
- **services/backend**: FastAPI Python backend with async/await patterns
- **services/edge-agent**: Python agent for Raspberry Pi devices
- **services/streaming**: Video streaming service (placeholder)
- **infrastructure/**: Terraform, Kubernetes, and Ansible configurations
- **shared/**: Protocol buffers, schemas, and API contracts
- **tools/**: Development scripts and utilities

### Key Architectural Patterns
- **Event-Driven Architecture**: Commands flow through API Gateway, events published to Redis/Kafka
- **CQRS Pattern**: Separate read/write models for performance
- **Edge Computing**: Semi-autonomous operation with local SQLite and cloud sync
- **Real-time Communication**: WebSocket (port 8001) and MQTT for sub-100ms control

### Technology Stack
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Shadcn/ui, Zustand, React Query
- **Backend**: FastAPI, SQLAlchemy 2.0 async, PostgreSQL with TimescaleDB, Redis, Celery
- **Edge**: Python 3.11+, SQLite, MQTT (Paho), OpenCV, GPIO control (RPi.GPIO)
- **Infrastructure**: Docker, Kubernetes, Terraform, Prometheus, Grafana

## Development Commands

### Essential Commands
```bash
# Setup and installation
make install                    # Install all service dependencies
make git-hooks-install         # Install Git hooks for code quality

# Development servers
make dev                       # Start all services in development mode
make dev-frontend             # Next.js dev server (port 3000)
make dev-backend              # FastAPI with auto-reload (port 8000)
make dev-edge-agent           # Edge agent with hardware simulation

# Docker environments
make docker-up                # Production stack
make docker-dev               # Development stack with hot reload

# Testing
make test                     # Run all tests
make test-frontend            # Jest and Playwright tests
make test-backend             # pytest with coverage
make test-edge-agent          # pytest with hardware mocking
make test-integration         # Cross-service integration tests

# Code quality
make lint                     # ESLint, Ruff, Black across all services
make format                   # Prettier, Black auto-formatting
make typecheck                # TypeScript and mypy validation

# CI/CD and deployment
make ci-test                  # Run CI pipeline locally
make security-scan            # Run security scans
make performance-test         # Run performance tests
```

### Database Operations
```bash
# Database migrations (standalone Alembic)
cd infrastructure/database && alembic upgrade head
cd infrastructure/database && alembic revision --autogenerate -m "description"
cd infrastructure/database && alembic current
cd infrastructure/database && alembic history

# Database management CLI
python3 infrastructure/database/manage.py migrate           # Apply migrations
python3 infrastructure/database/manage.py create-migration "Description"
python3 infrastructure/database/manage.py backup           # Create backup
python3 infrastructure/database/manage.py restore backup.sql
python3 infrastructure/database/manage.py health-check     # Check health
python3 infrastructure/database/manage.py list-backups     # List backups
python3 infrastructure/database/manage.py validate-backup backup.sql

# Database maintenance and cleanup
./infrastructure/database/cleanup.sh full                  # Full cleanup
./infrastructure/database/cleanup.sh maintenance          # Database maintenance only
./infrastructure/database/cleanup.sh quick                # Quick log cleanup
python3 infrastructure/database/maintenance.py            # Python-based maintenance
python3 infrastructure/database/maintenance.py --tasks postgres_maintenance redis_maintenance

# Health monitoring for all database services
python3 infrastructure/monitoring/database/health_check.py # Check all services
python3 infrastructure/monitoring/database/health_check.py --format json
python3 infrastructure/monitoring/database/health_check.py --service postgres

# Automated maintenance scheduling
sudo ./infrastructure/database/cron-maintenance.sh install # Install cron jobs
./infrastructure/database/cron-maintenance.sh list        # List current jobs
./infrastructure/database/cron-maintenance.sh test        # Test scripts
sudo ./infrastructure/database/cron-maintenance.sh remove # Remove cron jobs
```

### Infrastructure Commands
```bash
# Terraform (from infrastructure/terraform/environments/dev)
terraform plan
terraform apply
make infra-plan               # Makefile wrapper
make infra-apply              # Makefile wrapper

# Kubernetes deployment
make k8s-deploy               # Apply manifests
make k8s-status               # Check deployment status
```

## Development Workflow

### Git Flow Process
- **main**: Production-ready code only
- **develop**: Integration branch for features
- **feature/***: New feature development
- **release/***: Release preparation
- **hotfix/***: Emergency production fixes

### Commit Convention
Uses Conventional Commits with specific scopes:
```
feat(frontend): add user authentication form
fix(backend): resolve database connection timeout
docs(api): update device registration endpoint
```

Valid types: feat, fix, docs, style, refactor, perf, test, chore, build, ci, revert
Valid scopes: frontend, backend, edge-agent, infrastructure, docs, api, ui, auth, device, experiment, task, video, mqtt, database, cache, monitoring, deployment, security, deps, config

### Code Quality Enforcement
- **Pre-commit hooks**: Linting, formatting, secret detection, file size limits
- **Commit message validation**: Conventional commits format enforcement
- **Pre-push hooks**: Additional security scans and test validation
- **CI/CD**: Automated testing, security scanning, and deployment readiness checks

## Project-Specific Patterns

### API Design
- RESTful endpoints under `/api/v1/`
- WebSocket connections on port 8001 for real-time updates
- Pydantic v2 for request/response validation
- Async/await patterns throughout FastAPI backend

### State Management
- **Frontend**: Zustand stores with React Query for server state
- **Backend**: SQLAlchemy 2.0 async with repository pattern
- **Edge**: Local SQLite with sync queue for offline capability

### Real-time Features
- WebSocket rooms for device-specific updates
- MQTT topics following `lics/devices/{device_id}/{metric}` pattern
- Event sourcing for audit and replay capabilities

### Task System
- Visual flow editor using React Flow
- JSON-based task definitions interpreted by edge devices
- Template marketplace for sharing experiment protocols

### Security Implementation
- JWT with refresh token rotation
- Role-based access control (RBAC)
- Rate limiting and CORS configuration
- Input validation and SQL injection prevention

## Testing Strategy

### Test Structure
- **Unit tests**: Individual component/function testing (>80% coverage target)
- **Integration tests**: Service interaction testing
- **E2E tests**: Full workflow testing with Playwright
- **Hardware tests**: GPIO simulation and real hardware validation

### Environment Configuration
- Development: docker-compose.dev.yml with hot reload and debugging tools
- Production: docker-compose.yml with proper security and scaling
- Testing: Separate database URLs and service mocking

## Key Development Considerations

### Edge Device Development
- Hardware simulation mode for development without Raspberry Pi
- GPIO pin mapping through YAML configuration files
- Graceful degradation when hardware components unavailable
- Local storage with intelligent cloud synchronization

### Performance Requirements
- API response time <200ms target
- Support for 10,000+ concurrent devices
- Handle 100k telemetry points/second
- Real-time updates with <100ms latency

### Data Pipeline Architecture
- **PostgreSQL with TimescaleDB**: Primary database with time-series extension for telemetry data
- **Redis**: Caching layer, session storage, and pub/sub messaging
- **InfluxDB**: Dedicated time-series database for metrics and telemetry
- **PgBouncer**: Connection pooling for PostgreSQL scalability
- **MinIO/S3**: Object storage for videos, exports, and large files
- **Prometheus metrics** with Grafana visualization

### Database Layer Components
- **Standalone Alembic**: Database migration management independent of FastAPI
- **Management CLI**: Comprehensive database operations tool (`infrastructure/database/manage.py`)
- **Health Monitoring**: Multi-service health checking with JSON/text output
- **Automated Maintenance**: Python and shell scripts for database cleanup and optimization
- **Performance Tuning**: Production and development optimized PostgreSQL configurations
- **Backup System**: Automated backup, restore, and validation procedures
- **Cron Integration**: Scheduled maintenance tasks with flexible timing

## CI/CD Pipeline Features

### Docker Infrastructure
- Multi-stage Dockerfiles for all services with security hardening
- Development and production variants for optimal workflow
- Platform-specific builds (linux/amd64, linux/arm64, linux/arm/v7 for edge devices)
- Comprehensive .dockerignore files for build optimization

### GitHub Actions Workflows
- **Continuous Integration** (.github/workflows/ci.yml): Comprehensive testing with path-based change detection
- **Docker Build** (.github/workflows/docker-build.yml): Automated image building and registry publishing
- **Release Management** (.github/workflows/release.yml): Semantic versioning with automated changelog generation
- **Security Scanning** (.github/workflows/security-scan.yml): Multi-layer security analysis
- **Deployment Templates**: Blue-green and canary deployment strategies (ready for activation)

### Quality Gates and Security
- Code coverage thresholds (>80% target)
- Security vulnerability scanning (dependencies, containers, infrastructure)
- Secret detection and license compliance checking
- Performance testing with K6 integration
- Integration testing with Docker Compose test environment

## Development Guidelines

### Implementation Process
- When implementing features, use @Documentation.md as a reference for implementation details
- After implementing features, update @Plan.md and @README.md with completed tasks
- Always test the feature after implementation. If successful, document the progress in @Plan.md
- This project is done by a sole developer, always adjust the structure for solo development but have possibilities for further collaboration

### Commit Guidelines
- Use conventional commits format with appropriate type and scope
- Author commits as: "Songphon <r.songphon@gmail.com>"
- When pushing to remote, use `--no-verify` flag to bypass hooks when needed

### Current Project Status
For detailed implementation progress and completed features, see @Plan.md

**Current Phase**: Phase 2 - Backend Core Development (Week 4)
**Last Completed**: WebSocket and Real-time Features implementation
**Next Steps**: Background Tasks and Scheduling (Celery implementation)

---

- For implementation details and progress tracking, refer to @Plan.md
- For architectural reference and detailed specifications, refer to @Documentation.md
- YOU MUST use my github username and github emial when create commit message.
- Develop this application in container so that we don't need to install ant dependencies in local. Follow @docs/CONTAINERIZED_DEVELOPMENT.md @CONTAINERIZED_DEV_IMPLEMENTATION.md @QUICKSTART_CONTAINER.md
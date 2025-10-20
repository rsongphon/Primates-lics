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
- **Infrastructure**: Docker, Kubernetes, Terraform, Prometheus, Grafana, Jaeger v2 (OpenTelemetry)

## Development Commands

### ⚠️ Important: Docker-First Development

**LICS is designed to run in Docker containers.** All services (backend, frontend, databases, message brokers) run inside containers with hot-reloading enabled. Do NOT attempt to run services directly on your local machine.

### Essential Docker Commands

```bash
# Start complete development environment (RECOMMENDED)
make dev                                    # Starts all services with hot-reload
                                           # Backend: http://localhost:8000
                                           # Frontend: http://localhost:3000
                                           # PostgreSQL: localhost:5433
                                           # Redis: localhost:6380
                                           # MQTT: localhost:1884
                                           # MinIO: http://localhost:9011

# View logs
docker-compose -f docker-compose.dev.yml logs -f              # All services
docker-compose -f docker-compose.dev.yml logs -f backend-dev  # Backend only
docker-compose -f docker-compose.dev.yml logs -f frontend-dev # Frontend only

# Stop services
docker-compose -f docker-compose.dev.yml down     # Stop all
docker-compose -f docker-compose.dev.yml down -v  # Stop and remove volumes (clean slate)

# Restart individual services
docker-compose -f docker-compose.dev.yml restart backend-dev
docker-compose -f docker-compose.dev.yml restart frontend-dev

# Execute commands inside containers
docker-compose -f docker-compose.dev.yml exec backend-dev bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest
docker-compose -f docker-compose.dev.yml exec frontend-dev npm install
```

### Testing Inside Containers

```bash
# Backend tests (inside container)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --cov=app
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/

# Frontend tests (inside container)
docker-compose -f docker-compose.dev.yml exec frontend-dev npm test
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run test:coverage

# Edge agent tests (inside container)
docker-compose -f docker-compose.dev.yml exec edge-agent-dev pytest
```

### Database Operations (Inside Containers)

**Note**: After rebuilding the backend container, a symlink is automatically created (`/app/alembic.ini → /infrastructure/database/alembic.ini`) allowing direct Alembic commands. See `docs/DATABASE_MIGRATIONS.md` for detailed migration guide.

```bash
# Database migrations - Use manage.py (recommended)
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py migrate
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py create -m "description" --autogenerate
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py current
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py history

# Alternative: Direct Alembic commands (after container rebuild)
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head
docker-compose -f docker-compose.dev.yml exec backend-dev alembic revision --autogenerate -m "description"
docker-compose -f docker-compose.dev.yml exec backend-dev alembic current

# Database management operations
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py backup
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py restore -f backup.sql
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py validate
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py init

# Direct PostgreSQL access
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev

# Redis CLI access
docker-compose -f docker-compose.dev.yml exec redis-dev redis-cli
```

### Code Quality (Inside Containers)

```bash
# Backend linting and formatting
docker-compose -f docker-compose.dev.yml exec backend-dev black .
docker-compose -f docker-compose.dev.yml exec backend-dev ruff check .
docker-compose -f docker-compose.dev.yml exec backend-dev mypy app/

# Frontend linting and formatting
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run lint
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run format
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run typecheck
```

### Adding New Dependencies

```bash
# Backend (Python) - Add to requirements.txt, then rebuild
echo "new-package>=1.0.0" >> services/backend/requirements.txt
docker-compose -f docker-compose.dev.yml up --build backend-dev

# Frontend (Node.js) - Add to package.json, then rebuild
docker-compose -f docker-compose.dev.yml exec frontend-dev npm install new-package
# OR rebuild container
docker-compose -f docker-compose.dev.yml up --build frontend-dev

# Shadcn/ui components (inside frontend container)
docker-compose -f docker-compose.dev.yml exec frontend-dev npx shadcn@latest add button
docker-compose -f docker-compose.dev.yml exec frontend-dev npx shadcn@latest add card input
```

### Accessing Development Tools

All these tools are accessible when running `make dev`:

- **PgAdmin** (PostgreSQL GUI): http://localhost:5050 (admin@lics.dev / admin123)
- **Redis Commander** (Redis GUI): http://localhost:8081
- **MailHog** (Email testing): http://localhost:8025
- **Jaeger v2** (Distributed tracing): http://localhost:16686
- **Backend API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

**Note**: The project uses **Jaeger v2**, which is built on OpenTelemetry Collector and natively supports OTLP protocol. Configuration files are located in `infrastructure/monitoring/jaeger/`.

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
- This project is develop and deployed on containerized enviroment.
- This project is done by a sole developer, always adjust the structure for solo development but have possibilities for further collaboration

### Commit Guidelines
- Use conventional commits format with appropriate type and scope
- Author commits as: "Songphon <r.songphon@gmail.com>" Do not end like "Generated by Cluade Code"
- When commit the work and pushing to remote, use `--no-verify` flag to bypass hooks when needed



**Current Phase**: Phase 2 - Backend Core Development (Week 4)
**Last Completed**: WebSocket and Real-time Features implementation
**Next Steps**: Background Tasks and Scheduling (Celery implementation)

---
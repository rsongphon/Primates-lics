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

# Individual service commands
cd services/frontend && npm run dev
cd services/backend && uvicorn app.main:app --reload
cd services/edge-agent && python src/main.py --debug
```

### Database Operations
```bash
# Backend migrations
cd services/backend && alembic upgrade head
cd services/backend && alembic revision --autogenerate -m "description"

# Database management (via Makefile)
make db-migrate               # Apply migrations
make db-rollback              # Rollback last migration
make db-reset                 # Reset database (destroys data)
make db-seed                  # Seed with development data
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
- TimescaleDB for time-series telemetry data
- Redis for caching and pub/sub messaging
- MinIO/S3 for object storage (videos, exports)
- Prometheus metrics with Grafana visualization

The project is currently in Phase 1 (Foundation Setup) with repository structure, version control, and development environment completed. Next phases involve implementing core services, database layer, and API development.
- When implement the application in the project, use @Documentation.md as a reference for implementation detail. Always follow the intruction in that file.
- After implement feature in this application, update @Plan.md and @README.md about what you've done (check list if possible)
- Always update @CLAUDE.md  with lastest implementation.
- This project is done by sole developer, always adjust the structure for solo developer but have a possibilities for futher collaboration.
- When commit the project, don't end the message with something like "🤖 Generated with [Claude Code](https://claude.com.claude-code) Co-Authored-By: Claude <noreply@anthropic.com>" " Use my github username instead
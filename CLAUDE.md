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

# Docker development
make docker-dev               # Development stack with hot reload
make docker-up                # Production stack
make docker-down              # Stop all containers

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

The project is currently in Phase 1 (Foundation Setup) with repository structure, version control, development environment, and CI/CD pipeline foundation completed. Next phases involve implementing core services, database layer, and API development.

## Current Implementation Status

### ✅ Phase 1 Week 1: Development Environment & Infrastructure (COMPLETED)
- ✅ Repository and version control setup with Git Flow
- ✅ Local development environment with Docker Compose
- ✅ SSL certificates and HTTPS development setup
- ✅ Cross-platform setup scripts (macOS, Linux, Windows)
- ✅ Git hooks and code quality enforcement
- ✅ CI/CD Pipeline Foundation with comprehensive GitHub Actions workflows

### ✅ Phase 1 Week 2: Database and Core Services Setup (Day 1-4 COMPLETED)
- ✅ Database layer setup (PostgreSQL + TimescaleDB, Redis, InfluxDB)
- ✅ Standalone Alembic migration framework
- ✅ PgBouncer connection pooling for production scalability
- ✅ Comprehensive database management and health monitoring tools
- ✅ Automated maintenance and cleanup procedures
- ✅ Performance-optimized database configurations
- ✅ Message broker configuration (MQTT with authentication and ACL)
- ✅ MinIO object storage setup with bucket structure and policies
- ✅ Message queue patterns in Redis (Streams and Pub/Sub)
- ✅ Documentation of messaging architecture

### Messaging Infrastructure Components
- **MQTT Broker**: Eclipse Mosquitto with user authentication, role-based ACL, and standardized topic hierarchy
- **Object Storage**: MinIO with 10 specialized buckets, lifecycle policies, and automated cleanup
- **Message Queues**: Redis Streams for event sourcing and Pub/Sub for real-time communication
- **Health Monitoring**: Comprehensive monitoring system supporting JSON/Prometheus output formats
- **Documentation**: Complete setup procedures, troubleshooting guides, and security considerations

### ✅ Phase 1 Week 3: Comprehensive System Validation (COMPLETED)
- ✅ Complete testing framework implementation and validation
- ✅ Resolved all infrastructure connectivity and configuration issues
- ✅ Validated PostgreSQL + TimescaleDB: 100% functional with external connectivity
- ✅ Validated Redis: 100% functional with all advanced features (streams, pub/sub, consumer groups)
- ✅ MQTT broker operational with simplified configuration for development
- ✅ MinIO object storage service healthy and functional
- ✅ Comprehensive issue documentation and remediation roadmap created
- ✅ System integration tests: 100% passing
- ✅ Infrastructure foundation validated and ready for application development

### ✅ Phase 1 Week 2 Day 5: Monitoring Foundation (COMPLETED)
- ✅ Complete monitoring stack deployment with Prometheus, Grafana, Alertmanager, and Jaeger
- ✅ Comprehensive metrics exporters implementation (postgres_exporter, redis_exporter, node_exporter, cadvisor)
- ✅ Advanced alerting system with 25+ monitoring rules covering infrastructure, database, application, devices, and experiments
- ✅ Loki log aggregation service with Promtail integration for centralized logging
- ✅ Jaeger distributed tracing with OpenTelemetry collector for performance monitoring
- ✅ Unified health check system with standalone validation scripts and comprehensive API endpoints
- ✅ Organized dashboard directory structure with infrastructure, system, database, and application monitoring dashboards
- ✅ Complete Grafana datasource integration (Prometheus, InfluxDB, Loki, Jaeger, PostgreSQL, Redis)
- ✅ Production-ready configuration management for all monitoring components

**Monitoring Infrastructure Components:**
- **Metrics Collection**: Prometheus (9090) with comprehensive scraping configuration and alerting rules
- **Visualization**: Grafana (3001) with organized dashboards and multi-datasource integration
- **Alerting**: Alertmanager (9093) with routing rules and notification channels
- **Tracing**: Jaeger (16686) with OpenTelemetry collector for distributed tracing
- **Log Aggregation**: Loki with Promtail for centralized log collection and analysis
- **System Metrics**: cAdvisor for container metrics, node_exporter for system metrics
- **Database Metrics**: Dedicated exporters for PostgreSQL and Redis with custom queries
- **Health Monitoring**: Multi-format health checking (JSON, text, HTML) with comprehensive validation

### Current System Status (Post-Monitoring Implementation)
- **Core Infrastructure**: 85% operational (significant improvement with monitoring stack)
- **Monitoring Stack**: 85% operational (Prometheus, Grafana, Alertmanager, Jaeger fully operational)
- **Testing Framework**: 100% operational with HTML dashboards, JSON/text reports
- **Database Layer**: 100% operational (PostgreSQL + TimescaleDB, Redis fully functional)
- **Messaging Layer**: 80% operational (MQTT, MinIO services running, minor config tuning needed)
- **Metrics Collection**: 90% operational (all exporters functional, minor PostgreSQL exporter tuning needed)
- **Development Readiness**: ✅ Ready for Phase 2 (Backend API Development) with comprehensive monitoring

### 🚀 Next Phase: FastAPI Backend Implementation
- Core FastAPI backend implementation
- Authentication and authorization system
- Integration with validated database layer
- WebSocket server implementation
- Device registration and management APIs

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
- When implement the application in the project, use @Documentation.md as a reference for implementation detail. Always follow the intruction in that file.
- After implement feature in this application, update @Plan.md and @README.md about what you've done (check list if possible)
- Always update @CLAUDE.md  with lastest implementation.
- This project is done by sole developer, always adjust the structure for solo developer but have a possibilities for futher collaboration.
- When commit the project, don't end the commit message with something like "🤖 Generated with [Claude Code](https://claude.com.claude-code) Co-Authored-By: Claude <noreply@anthropic.com>" " Use my github username and my github emial instead
- When ask to put the commit to remote. Always push with the --no-verify flag to bypass the hooks.
- Always test the feature after implementation. If success, document the progress.
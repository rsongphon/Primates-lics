# Lab Instrument Control System (LICS)

[![CI Status](https://github.com/rsongphon/Primates-lics/workflows/Continuous%20Integration/badge.svg)](https://github.com/rsongphon/Primates-lics/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0--alpha-orange.svg)](https://github.com/rsongphon/Primates-lics/releases)

A comprehensive, cloud-native platform for managing laboratory instruments and conducting behavioral experiments across multiple devices. LICS provides real-time control, data collection, and experiment management capabilities designed specifically for research environments.

## 🎯 Project Vision

LICS revolutionizes laboratory automation by providing:
- **Distributed Control**: Manage multiple experimental devices from a single interface
- **Real-time Monitoring**: Live video streaming and telemetry data collection
- **No-Code Experiment Design**: Visual task builder for creating complex experimental protocols
- **Edge Computing**: Semi-autonomous device operation with offline capabilities
- **Scalable Architecture**: Cloud-native design supporting thousands of devices

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   Backend API   │    │  Edge Devices   │
│    (Next.js)    │◄──►│   (FastAPI)     │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   PostgreSQL    │    │   Local SQLite  │
│   Real-time     │    │   TimescaleDB   │    │   MQTT Client   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 🐳 Docker Development (Recommended)

LICS is designed to run entirely in Docker containers - **no local Python, Node.js, or database installation required!**

1. **Prerequisites: Install Docker only**
   - **macOS**: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
   - **Linux**: [Docker Engine](https://docs.docker.com/engine/install/)
   - **Windows**: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

2. **Clone the repository**
   ```bash
   git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics
   ```

3. **Start the complete development environment**
   ```bash
   # One command to start everything with hot-reloading
   make dev
   ```

That's it! Your containerized development environment is now running:

**Application Services:**
- **Backend API**: http://localhost:8000/docs (FastAPI with auto-reload)
- **WebSocket Server**: ws://localhost:8001 (Socket.IO real-time)
- **Frontend**: http://localhost:3000 (Next.js with hot-reload)

**Infrastructure Services:**
- **PostgreSQL + TimescaleDB**: localhost:5433
- **Redis**: localhost:6380
- **MQTT Broker**: localhost:1884
- **MinIO Object Storage**: http://localhost:9010 (console: http://localhost:9011)

**Development Tools:**
- **PgAdmin** (Database GUI): http://localhost:5050 (admin@lics.dev / admin123)
- **Redis Commander** (Redis GUI): http://localhost:8081
- **MailHog** (Email Testing): http://localhost:8025
- **Jaeger v2** (Distributed Tracing): http://localhost:16686

### Development Workflow

All code changes are automatically reflected due to volume mounts:

```bash
# View logs for all services
docker-compose -f docker-compose.dev.yml logs -f

# View logs for specific service
docker-compose -f docker-compose.dev.yml logs -f backend-dev

# Restart a specific service
docker-compose -f docker-compose.dev.yml restart backend-dev

# Stop all services
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.dev.yml down -v

# Execute commands inside containers
docker-compose -f docker-compose.dev.yml exec backend-dev bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest
```

### Alternative: Local Development (Not Recommended)

**⚠️ Note**: This requires installing Node.js, Python, PostgreSQL, Redis, and other dependencies locally. Docker development is strongly recommended instead.

<details>
<summary>Click to expand local development instructions</summary>

#### Prerequisites

- **Node.js** 20+ (for frontend)
- **Python** 3.11+ (for backend)
- **PostgreSQL** 15+ with TimescaleDB
- **Redis** 7+
- **MQTT Broker** (Mosquitto)
- **MinIO** (object storage)
- **Git**

#### Steps

1. **Install all prerequisites for your OS**
   ```bash
   # macOS
   ./tools/scripts/setup-mac.sh

   # Linux
   ./tools/scripts/setup-linux.sh

   # Windows
   .\tools\scripts\setup-windows.ps1
   ```

2. **Start infrastructure services**
   ```bash
   # You'll still need Docker for databases and infrastructure
   docker-compose up postgres redis mqtt minio -d
   ```

3. **Install application dependencies**
   ```bash
   # Frontend
   cd services/frontend && npm install

   # Backend
   cd services/backend && pip install -r requirements.txt
   ```

4. **Start development servers**
   ```bash
   # Terminal 1: Backend
   cd services/backend && uvicorn app.main:app --reload

   # Terminal 2: Frontend
   cd services/frontend && npm run dev
   ```

</details>

### Production Deployment

For production deployment instructions, see [Deployment Guide](docs/deployment.md).

## 📁 Project Structure

```
lics/
├── services/                 # Microservices
│   ├── frontend/            # Next.js web application
│   ├── backend/             # FastAPI backend service
│   ├── edge-agent/          # Python edge device agent
│   └── streaming/           # Video streaming service
├── infrastructure/          # Infrastructure as Code
│   ├── terraform/           # Cloud infrastructure
│   ├── kubernetes/          # K8s manifests
│   └── ansible/             # Configuration management
├── shared/                  # Shared code and schemas
│   ├── protos/             # Protocol buffer definitions
│   ├── schemas/            # JSON schemas
│   └── contracts/          # API contracts
├── tools/                   # Development tools
│   ├── scripts/            # Utility scripts
│   ├── migrations/         # Database migrations
│   └── testing/            # Testing utilities
├── docs/                    # Documentation
│   ├── api/                # API documentation
│   ├── architecture/       # Architecture docs
│   └── user-guides/        # User guides
└── .github/                 # GitHub workflows and templates
```

## 🛠️ Development

### Common Development Tasks

All development is done inside Docker containers. Use these commands:

**Running Tests:**
```bash
# Run tests inside containers
docker-compose -f docker-compose.dev.yml exec backend-dev pytest
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --cov=app

# Or use make commands (if services are running locally)
make test-backend
make test-frontend
```

**Code Formatting and Linting:**
```bash
# Inside backend container
docker-compose -f docker-compose.dev.yml exec backend-dev black .
docker-compose -f docker-compose.dev.yml exec backend-dev ruff check .

# Inside frontend container
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run lint
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run format
```

**Database Operations:**
```bash
# Run migrations inside backend container
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head
docker-compose -f docker-compose.dev.yml exec backend-dev alembic revision --autogenerate -m "description"

# Database management
docker-compose -f docker-compose.dev.yml exec backend-dev python infrastructure/database/manage.py migrate
docker-compose -f docker-compose.dev.yml exec backend-dev python infrastructure/database/manage.py backup

# Or connect directly to PostgreSQL
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev
```

**Installing New Dependencies:**
```bash
# Backend (Python)
# 1. Add package to services/backend/requirements.txt
# 2. Rebuild container
docker-compose -f docker-compose.dev.yml up --build backend-dev

# Frontend (Node.js)
# 1. Add package to services/frontend/package.json
# 2. Rebuild container
docker-compose -f docker-compose.dev.yml up --build frontend-dev
```

**Debugging:**
```bash
# View backend logs
docker-compose -f docker-compose.dev.yml logs -f backend-dev

# Get shell inside backend container
docker-compose -f docker-compose.dev.yml exec backend-dev bash

# Interactive Python shell with app context
docker-compose -f docker-compose.dev.yml exec backend-dev python
```

### Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Commit using conventional commits (`git commit -m 'feat: add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Workflow

- **Branching Strategy**: We use Git Flow with `main`, `develop`, and `feature/*` branches
- **Commit Messages**: We follow [Conventional Commits](https://www.conventionalcommits.org/)
- **Code Review**: All changes require PR approval
- **Testing**: Maintain >80% code coverage
- **Documentation**: Update docs for API and user-facing changes

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run specific test suites
make test-frontend     # Frontend tests
make test-backend      # Backend tests
make test-edge-agent   # Edge agent tests
make test-integration  # Integration tests
make test-e2e          # End-to-end tests
```

### Test Types

- **Unit Tests**: Individual component testing
- **Integration Tests**: Service interaction testing
- **End-to-End Tests**: Full workflow testing
- **Performance Tests**: Load and stress testing

## 📊 Monitoring

LICS includes comprehensive monitoring and observability:

- **Metrics**: Prometheus and Grafana dashboards
- **Logging**: Structured logging with log aggregation (Loki + Promtail)
- **Tracing**: Distributed tracing with Jaeger v2 and OpenTelemetry Collector
- **Health Checks**: Service health monitoring
- **Alerting**: Automated alert rules (Alertmanager)

Access monitoring dashboards at:
- **Grafana**: http://localhost:3001 (Visualization dashboards)
- **Prometheus**: http://localhost:9090 (Metrics collection)
- **Jaeger v2**: http://localhost:16686 (Distributed tracing UI)

**Note**: LICS uses Jaeger v2 (built on OpenTelemetry Collector), which natively supports OTLP protocol for improved performance and future-proof observability. Configuration files are located in `infrastructure/monitoring/jaeger/`. See `MIGRATION_GUIDE.md` for migration details.

## 🔒 Security

Security is a top priority for LICS:

- **Authentication**: JWT-based authentication with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Encryption**: TLS encryption for all communications
- **Input Validation**: Comprehensive input validation and sanitization
- **Security Scanning**: Automated vulnerability scanning in CI/CD

For security issues, please see our [Security Policy](SECURITY.md).

## 📖 Documentation

- **[Architecture Documentation](docs/architecture/)** - System design and technical details
- **[API Documentation](docs/api/)** - REST API and WebSocket documentation
- **[User Guides](docs/user-guides/)** - End-user documentation
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions
- **[Contributing Guide](CONTRIBUTING.md)** - Development contribution guidelines
- **[Known Issues](known-issues.md)** - Comprehensive issue tracking and resolution status

## 🗺️ Roadmap

### Current Phase: Frontend Development (v1.0)
**Phase 1 - Infrastructure (✅ Complete):**
- [x] Core infrastructure setup
- [x] Database layer foundation (PostgreSQL + TimescaleDB, Redis, InfluxDB)
- [x] Database migration and management tools
- [x] Monitoring and health check systems
- [x] Message broker and storage layer (MQTT, MinIO, Redis Streams/Pub-Sub)

**Phase 2 - Backend Core (✅ Complete):**
- [x] FastAPI backend foundation (async SQLAlchemy 2.0, structured logging, API architecture)
- [x] Authentication and authorization system (JWT, RBAC, refresh tokens)
- [x] Core domain models and business logic (Devices, Experiments, Tasks, Participants)
- [x] RESTful API implementation (84 endpoints across 9 categories)
- [x] WebSocket and real-time features (15+ event handlers)
- [x] Background tasks and scheduling (Celery with 21 tasks)

**Phase 3 - Frontend Development (🔄 In Progress):**
- [x] Next.js 14 application foundation
- [x] State management (Zustand + React Query + WebSocket integration)
- [x] **Authentication flow (Login, Registration, Route Protection, Token Refresh)**
- [ ] Dashboard and navigation components
- [ ] Device management interface
- [ ] Experiment management UI
- [ ] Task builder system
- [ ] Video streaming integration
- [ ] Real-time analytics dashboard

### Next Phase: Advanced Features (v2.0)
- [ ] Machine learning integration
- [ ] Advanced analytics
- [ ] Mobile applications
- [ ] Federation support
- [ ] Third-party integrations

See our [detailed roadmap](docs/ROADMAP.md) for more information.

## 🤝 Community

- **Discussions**: [GitHub Discussions](https://github.com/rsongphon/Primates-lics/discussions)
- **Issues**: [GitHub Issues](https://github.com/rsongphon/Primates-lics/issues)
- **Wiki**: [Project Wiki](https://github.com/rsongphon/Primates-lics/wiki)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Research teams and institutions providing requirements and feedback
- Open source community for the amazing tools and libraries
- Contributors who help make LICS better

## 📞 Support

- **Documentation**: Check our [docs](docs/) first
- **Community**: Ask questions in [Discussions](https://github.com/rsongphon/Primates-lics/discussions)
- **Issues**: Report bugs in [Issues](https://github.com/rsongphon/Primates-lics/issues)
- **Commercial**: Contact us at support@lics.io for commercial support

---

Made with ❤️ for the research community


{
      "name": "zhipu",
      "api_base_url": "https://api.z.ai/api/anthropic/v1/messages",
      "api_key": "431f9dec55cf4fb3bce0642238dbd131.HrIDuuiq1zSfGlx6",
      "models": [
        "glm-4.6",
        "glm-4.5-air"
      ],
      "transformer": {
        "use": ["Anthropic"]
      }
    }
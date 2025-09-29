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

### Automated Setup (Recommended)

For the fastest setup experience, use our automated installation:

1. **Clone the repository**
   ```bash
   git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics
   ```

2. **Run automated setup for your OS**
   ```bash
   # Automatically detects your OS and sets up everything
   make setup-dev-env
   ```

3. **Generate SSL certificates**
   ```bash
   make setup-ssl
   ```

4. **Copy environment configuration**
   ```bash
   cp .env.example .env
   ```

5. **Install dependencies and start development**
   ```bash
   make install
   make dev
   ```

That's it! Your development environment is now running with:
- Frontend: https://localhost:3000 (with SSL)
- Backend API: https://localhost:8000/docs
- WebSocket: wss://localhost:8001
- Grafana Monitoring: https://localhost:3001

### Manual Setup

If you prefer manual installation:

#### Prerequisites

- **Docker** and **Docker Compose** (for containerized services)
- **Node.js** 20+ (for frontend development)
- **Python** 3.11+ (for backend and edge agent development)
- **Git** (for version control)
- **mkcert** (for SSL certificates, installed by setup scripts)

#### Manual Installation Steps

1. **Clone and setup Git hooks**
   ```bash
   git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics
   ./tools/scripts/setup-git-hooks.sh
   ```

2. **Install dependencies manually**
   ```bash
   # macOS
   ./tools/scripts/setup-mac.sh

   # Linux (Ubuntu/CentOS/Arch/openSUSE)
   ./tools/scripts/setup-linux.sh

   # Windows (PowerShell as Administrator)
   .\tools\scripts\setup-windows.ps1
   ```

3. **Configure SSL and environment**
   ```bash
   make setup-ssl
   cp .env.example .env
   ```

4. **Start services**
   ```bash
   make install
   make dev
   ```

### Access Points

Once running, access these services:
- **Web Interface**: https://localhost:3000
- **API Documentation**: https://localhost:8000/docs
- **WebSocket Endpoint**: wss://localhost:8001
- **Grafana Monitoring**: https://localhost:3001 (admin/admin123)
- **Traefik Dashboard**: http://localhost:8080

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

### Getting Started

1. **Install dependencies (automated):**
   ```bash
   # Install all service dependencies at once
   make install

   # Or install individually if needed
   make install-frontend
   make install-backend
   make install-edge-agent
   ```

   **Manual installation (if needed):**
   ```bash
   # Frontend
   cd services/frontend && npm install

   # Backend
   cd services/backend && pip install -r requirements.txt

   # Edge Agent
   cd services/edge-agent && pip install -r requirements.txt
   ```

2. **Run tests:**
   ```bash
   # All services
   make test

   # Individual services
   make test-frontend
   make test-backend
   make test-edge-agent
   ```

3. **Code formatting and linting:**
   ```bash
   # Format all code
   make format

   # Run linting
   make lint
   ```

4. **Database operations:**
   ```bash
   # Database migrations (standalone)
   cd infrastructure/database && alembic upgrade head
   cd infrastructure/database && alembic revision --autogenerate -m "description"

   # Database management CLI
   python3 infrastructure/database/manage.py migrate           # Apply migrations
   python3 infrastructure/database/manage.py backup           # Create backup
   python3 infrastructure/database/manage.py health-check     # Check health
   python3 infrastructure/database/manage.py list-backups     # List backups

   # Database maintenance and cleanup
   ./infrastructure/database/cleanup.sh full                  # Full cleanup
   ./infrastructure/database/cleanup.sh maintenance          # Database maintenance
   python3 infrastructure/database/maintenance.py            # Automated maintenance

   # Health monitoring
   python3 infrastructure/monitoring/database/health_check.py # Check all services
   python3 infrastructure/monitoring/database/health_check.py --format json

   # Automated scheduling
   sudo ./infrastructure/database/cron-maintenance.sh install # Install cron jobs
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
- **Logging**: Structured logging with log aggregation
- **Tracing**: Distributed tracing with OpenTelemetry
- **Health Checks**: Service health monitoring
- **Alerting**: Automated alert rules

Access monitoring dashboards at:
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

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

## 🗺️ Roadmap

### Current Phase: Foundation (v1.0)
- [x] Core infrastructure setup
- [x] Database layer foundation (PostgreSQL + TimescaleDB, Redis, InfluxDB)
- [x] Database migration and management tools
- [x] Monitoring and health check systems
- [x] Message broker and storage layer (MQTT, MinIO, Redis Streams/Pub-Sub)
- [ ] FastAPI backend implementation
- [ ] Task builder system
- [ ] Video streaming
- [ ] Real-time analytics

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
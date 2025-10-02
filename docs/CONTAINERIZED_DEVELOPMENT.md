# Containerized Development Environment

This guide explains how to develop LICS in a fully containerized environment with **zero local dependencies** beyond Docker and VS Code (optional).

## 🎯 Overview

LICS provides three development approaches:

1. **VS Code Dev Containers** (Recommended) - Full IDE integration
2. **Standalone Docker Compose** - Editor agnostic
3. **Hybrid Approach** - Best of both worlds

All approaches eliminate the need to install Node.js, Python, PostgreSQL, Redis, or any other dependencies locally.

## 📋 Prerequisites

### Required
- **Docker** 24.0+ and **Docker Compose** 2.20+
- **Git** 2.40+

### Optional
- **VS Code** with **Dev Containers** extension (for devcontainer approach)

## 🚀 Quick Start

### Option 1: VS Code Dev Containers (Recommended)

1. **Install VS Code and Dev Containers extension**
   ```bash
   # Install VS Code: https://code.visualstudio.com/
   # Install extension: ms-vscode-remote.remote-containers
   ```

2. **Open project in VS Code**
   ```bash
   cd Primates-lics
   code .
   ```

3. **Reopen in Container**
   - Press `F1` or `Cmd/Ctrl + Shift + P`
   - Select: **Dev Containers: Reopen in Container**
   - Wait for container to build and start (first time takes ~5-10 minutes)

4. **Start developing!**
   ```bash
   # In VS Code integrated terminal (now inside container):
   make dev              # Start all services
   make test             # Run tests
   npm run dev           # Frontend dev server
   pytest                # Backend tests
   ```

### Option 2: Standalone Docker Compose

1. **Start infrastructure services**
   ```bash
   docker-compose up -d postgres redis mqtt minio
   ```

2. **Use the dev CLI helper**
   ```bash
   # Make script executable
   chmod +x tools/dev-cli.sh

   # Open a shell in the dev environment
   ./tools/dev-cli.sh shell

   # Run commands directly
   ./tools/dev-cli.sh npm install
   ./tools/dev-cli.sh pytest
   ./tools/dev-cli.sh alembic upgrade head
   ```

3. **Or run development services**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d frontend-dev backend-dev
   ```

## 📁 Architecture

### Dev Container Setup

```
┌─────────────────────────────────────────────────────┐
│  VS Code (on your machine)                          │
│  ┌───────────────────────────────────────────────┐ │
│  │  Dev Container (runs inside Docker)           │ │
│  │                                                │ │
│  │  /workspace (mounted from your machine)       │ │
│  │  ├── Full IDE integration                     │ │
│  │  ├── IntelliSense & debugging                │ │
│  │  ├── Extensions running in container         │ │
│  │  └── Access to all services                  │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
          │
          │ Connected to
          ▼
┌─────────────────────────────────────────────────────┐
│  Docker Network (lics-network)                      │
│  ├── postgres       (PostgreSQL + TimescaleDB)      │
│  ├── redis          (Cache & Queues)                │
│  ├── mqtt           (Message Broker)                │
│  ├── minio          (Object Storage)                │
│  ├── influxdb       (Time-Series DB)                │
│  └── grafana        (Monitoring)                    │
└─────────────────────────────────────────────────────┘
```

### Volume Mounting Strategy

**Named volumes** for dependencies (prevents permission issues):
- `devcontainer-node-modules` → `/workspace/services/frontend/node_modules`
- `devcontainer-backend-venv` → `/workspace/services/backend/venv`
- `devcontainer-edge-venv` → `/workspace/services/edge-agent/venv`

**Bind mount** for source code (enables hot reload):
- `.` → `/workspace` (cached for performance)

## 🛠️ Development Workflows

### Using Dev Container (VS Code)

Once inside the dev container, everything works as if installed locally:

```bash
# Frontend development
cd services/frontend
npm install axios              # Install packages
npm run dev                    # Start dev server
npm test                       # Run tests

# Backend development
cd services/backend
source venv/bin/activate       # Activate venv
pip install requests           # Install packages
uvicorn app.main:app --reload  # Start server
pytest                         # Run tests

# Database migrations
cd infrastructure/database
alembic revision --autogenerate -m "Add new model"
alembic upgrade head

# Debugging
# Just use VS Code debugger - it works seamlessly!
```

### Using Dev CLI (Standalone)

For editor-agnostic development:

```bash
# Get a shell
./tools/dev-cli.sh shell

# Frontend commands
./tools/dev-cli.sh npm install
./tools/dev-cli.sh npm run dev
./tools/dev-cli.sh npm test

# Backend commands
./tools/dev-cli.sh python app/main.py
./tools/dev-cli.sh pytest tests/
./tools/dev-cli.sh pip install requests

# Database commands
./tools/dev-cli.sh alembic upgrade head
./tools/dev-cli.sh psql
./tools/dev-cli.sh redis-cli

# Testing
./tools/dev-cli.sh test
./tools/dev-cli.sh test-frontend
./tools/dev-cli.sh test-backend

# View logs
./tools/dev-cli.sh logs backend-dev
./tools/dev-cli.sh logs frontend-dev

# Restart services
./tools/dev-cli.sh restart backend-dev
```

### Using Individual Service Containers

Run specific services in development mode:

```bash
# Frontend only
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up frontend-dev

# Backend only
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend-dev

# Edge agent (simulated)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up edge-agent-dev

# View logs
docker-compose logs -f backend-dev

# Execute commands in running containers
docker-compose exec backend-dev pytest
docker-compose exec frontend-dev npm run build
```

## 🔧 Configuration

### Environment Variables

The dev container automatically sets up environment variables to connect to services:

```bash
# Database
DATABASE_URL=postgresql://lics:password@postgres:5432/lics

# Redis
REDIS_URL=redis://redis:6379

# MQTT
MQTT_BROKER_HOST=mqtt
MQTT_BROKER_PORT=1883

# MinIO
MINIO_ENDPOINT=minio:9000
```

### Port Forwarding

All services are automatically forwarded to your local machine:

| Service       | Container Port | Local Port | URL                          |
|---------------|----------------|------------|------------------------------|
| Frontend      | 3000           | 3000       | http://localhost:3000        |
| Backend API   | 8000           | 8000       | http://localhost:8000/docs   |
| WebSocket     | 8001           | 8001       | ws://localhost:8001          |
| PostgreSQL    | 5432           | 5432       | localhost:5432               |
| Redis         | 6379           | 6379       | localhost:6379               |
| MQTT          | 1883           | 1883       | localhost:1883               |
| MinIO Console | 9001           | 9001       | http://localhost:9001        |
| Grafana       | 3001           | 3001       | http://localhost:3001        |

## 🐛 Debugging

### VS Code Debugging (Dev Container)

1. **Backend Python Debugging**

   `.vscode/launch.json` (automatically configured):
   ```json
   {
     "name": "Debug Backend",
     "type": "python",
     "request": "launch",
     "module": "uvicorn",
     "args": ["app.main:app", "--reload", "--host", "0.0.0.0"],
     "cwd": "${workspaceFolder}/services/backend"
   }
   ```

   - Set breakpoints in Python files
   - Press `F5` to start debugging
   - Backend runs with debugger attached

2. **Frontend JavaScript Debugging**

   - Chrome DevTools work seamlessly
   - Or use VS Code debugger with Next.js
   - Set breakpoints in `.tsx` files

3. **Remote Debugging (Standalone)**

   Backend exposes debugger on port `5678`:
   ```bash
   # Backend Dockerfile.dev includes debugpy
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend-dev

   # Attach VS Code debugger to localhost:5678
   ```

## 📦 Dependency Management

### Installing New Packages

#### Frontend
```bash
# In dev container
cd services/frontend
npm install <package>

# Using dev CLI
./tools/dev-cli.sh npm install <package>

# Rebuild container to persist
docker-compose build frontend-dev
```

#### Backend
```bash
# In dev container
cd services/backend
source venv/bin/activate
pip install <package>
pip freeze > requirements.txt

# Using dev CLI
./tools/dev-cli.sh pip install <package>

# Rebuild container to persist
docker-compose build backend-dev
```

### Updating Dependencies

```bash
# Frontend
./tools/dev-cli.sh npm update

# Backend
./tools/dev-cli.sh pip install --upgrade -r requirements.txt
```

## 🧪 Testing

### Running Tests

```bash
# All tests
./tools/dev-cli.sh test

# Frontend only
./tools/dev-cli.sh test-frontend

# Backend only
./tools/dev-cli.sh test-backend

# Integration tests
./tools/dev-cli.sh test-integration

# With coverage
./tools/dev-cli.sh pytest --cov=app --cov-report=html
```

### Test Databases

Development docker-compose includes separate test databases to avoid conflicts:

```bash
# PostgreSQL test database
POSTGRES_DB=lics_test

# Run tests in isolation
./tools/dev-cli.sh pytest --create-db
```

## 🔄 Hot Reloading

All services support hot reloading:

- **Frontend**: Next.js Fast Refresh (automatic)
- **Backend**: Uvicorn `--reload` flag (automatic)
- **Edge Agent**: Watchdog file monitoring (automatic)

Changes to source code are immediately reflected without container restart.

## 🗄️ Database Operations

### Migrations

```bash
# Create migration
./tools/dev-cli.sh alembic revision --autogenerate -m "Add user table"

# Apply migrations
./tools/dev-cli.sh alembic upgrade head

# Rollback
./tools/dev-cli.sh alembic downgrade -1

# View history
./tools/dev-cli.sh alembic history
```

### Direct Database Access

```bash
# PostgreSQL
./tools/dev-cli.sh psql

# Redis
./tools/dev-cli.sh redis-cli

# Or use GUI tools
# PgAdmin: http://localhost:5050
# Redis Commander: http://localhost:8081
```

## 📊 Monitoring

Access monitoring dashboards:

- **Grafana**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **MailHog** (email testing): http://localhost:8025

## 🚀 Performance Tips

### 1. Use Named Volumes for Dependencies
Already configured - prevents permission issues and improves performance.

### 2. Enable File Watching
```bash
# .env
WATCHPACK_POLLING=true  # For Docker on macOS/Windows
```

### 3. Allocate Sufficient Resources
Docker Desktop settings:
- **CPUs**: 4+ cores
- **Memory**: 8GB+ RAM
- **Disk**: 20GB+ available

### 4. Use Cached Mounts
```yaml
volumes:
  - .:/workspace:cached  # Already configured
```

## 🛠️ Troubleshooting

### Container Build Failures

```bash
# Clear build cache
docker-compose build --no-cache devcontainer

# Remove old images
docker image prune -a
```

### Port Conflicts

```bash
# Check what's using a port
lsof -i :3000

# Change port in docker-compose.dev.yml
```

### Permission Issues

```bash
# Fix ownership (run on host)
sudo chown -R $USER:$USER .

# Or reset named volumes
docker volume rm devcontainer-node-modules
docker-compose up -d
```

### Slow Performance

```bash
# Increase Docker resources (Docker Desktop settings)

# Use named volumes for dependencies (already configured)

# Enable file caching (already configured)
```

### Database Connection Issues

```bash
# Check service health
docker-compose ps

# View logs
./tools/dev-cli.sh logs postgres

# Restart service
./tools/dev-cli.sh restart postgres
```

## 📚 Additional Resources

- [VS Code Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [LICS Development Guide](./DEVELOPMENT.md)
- [LICS Architecture Documentation](../Documentation.md)

## 🤔 FAQ

### Q: Can I use my own editor instead of VS Code?
**A:** Yes! Use the standalone Docker Compose approach with the dev CLI.

### Q: Do I need to install Node.js or Python locally?
**A:** No! Everything runs in containers.

### Q: Can I debug code running in containers?
**A:** Yes! VS Code connects to the container debugger seamlessly.

### Q: How do I update dependencies?
**A:** Install them in the container, update `requirements.txt` or `package.json`, and rebuild.

### Q: Can I use Git inside the container?
**A:** Yes! Git credentials are mounted and git is pre-configured.

### Q: What happens to my database data?
**A:** Stored in named Docker volumes - persists across container restarts.

### Q: How do I reset everything?
**A:**
```bash
docker-compose down -v  # Remove volumes
docker-compose build --no-cache
docker-compose up -d
```

## 🎓 Best Practices

1. **Use Dev Container for daily development** - best experience
2. **Use Dev CLI for quick tasks** - fast and flexible
3. **Commit code changes only** - don't commit generated files
4. **Keep containers updated** - rebuild weekly
5. **Use named volumes** - better performance and isolation
6. **Monitor resource usage** - prevent Docker from consuming all RAM
7. **Test in container before CI** - ensures consistency

---

**Need help?** Check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) or ask in [GitHub Discussions](https://github.com/rsongphon/Primates-lics/discussions).

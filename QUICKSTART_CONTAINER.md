# 🚀 Quick Start - Containerized Development

Get started with LICS in **5 minutes** with **zero local dependencies** beyond Docker.

## ⚡ Super Quick Start

### Option 1: VS Code Dev Containers (Recommended)

```bash
# 1. Open in VS Code
code .

# 2. Click "Reopen in Container" when prompted
# (or Cmd/Ctrl+Shift+P → "Dev Containers: Reopen in Container")

# 3. Wait for setup (~5-10 minutes first time)

# 4. Start developing!
make dev
```

### Option 2: Standalone Docker Compose

```bash
# 1. Start all services
make container-dev

# 2. Get a shell
make container-shell

# 3. Start developing!
make dev
```

## 📋 Prerequisites

### Required (Only These Two!)
- ✅ **Docker** 24.0+ with Docker Compose 2.20+
- ✅ **Git** 2.40+

### Optional
- 📝 **VS Code** with Dev Containers extension (for best experience)

### NOT Required ❌
- ❌ Node.js - runs in container
- ❌ Python - runs in container
- ❌ PostgreSQL - runs in container
- ❌ Redis - runs in container
- ❌ Any other dependencies - all in containers!

## 🎯 Choose Your Workflow

### 🏆 Workflow 1: VS Code Dev Containers (Best Experience)

**Best for:** Daily development, debugging, full IDE features

1. **Install VS Code**
   - Download: https://code.visualstudio.com/
   - Install extension: `ms-vscode-remote.remote-containers`

2. **Open Project**
   ```bash
   git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics
   code .
   ```

3. **Reopen in Container**
   - Click notification "Reopen in Container"
   - Or: `F1` → "Dev Containers: Reopen in Container"
   - Wait for initial setup (5-10 minutes)

4. **Start Developing**
   ```bash
   # In VS Code terminal (you're now inside the container!)
   make dev              # Start all services
   npm run dev           # Frontend dev server
   pytest                # Run tests

   # Everything works as if installed locally!
   ```

**✨ Benefits:**
- Full IntelliSense and code completion
- Integrated debugging (just press F5!)
- Extensions run in container
- Feels exactly like local development
- Git works seamlessly

---

### 🐳 Workflow 2: Standalone Docker Compose

**Best for:** Editor-agnostic, CI/CD, automated tasks

1. **Clone and Start**
   ```bash
   git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics
   make container-dev
   ```

2. **Use the Dev CLI**
   ```bash
   # Get a shell
   make container-shell

   # Or run commands directly
   ./tools/dev-cli.sh npm install
   ./tools/dev-cli.sh pytest
   ./tools/dev-cli.sh alembic upgrade head
   ```

3. **View Services**
   ```bash
   # View logs
   make container-logs

   # Check status
   docker-compose ps
   ```

**✨ Benefits:**
- Works with any editor (Vim, Emacs, Sublime, etc.)
- Lighter weight
- Perfect for automation
- Explicit control

---

### 🔀 Workflow 3: Individual Service Containers

**Best for:** Working on specific services, debugging issues

```bash
# Start just the services you need
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d frontend-dev backend-dev

# Work on frontend
docker-compose exec frontend-dev npm run dev

# Work on backend
docker-compose exec backend-dev pytest

# View specific logs
docker-compose logs -f backend-dev
```

## 🛠️ Common Tasks

### Installing Dependencies

```bash
# Frontend
make container-npm ARGS="install axios"
./tools/dev-cli.sh npm install axios

# Backend
make container-pip ARGS="install requests"
./tools/dev-cli.sh pip install requests
```

### Running Tests

```bash
# All tests
make container-test

# Specific tests
make container-pytest ARGS="tests/unit/test_auth.py"
./tools/dev-cli.sh pytest tests/unit/test_auth.py -v
```

### Database Migrations

```bash
# Create migration
make container-alembic ARGS="revision --autogenerate -m 'Add user table'"

# Apply migrations
make container-alembic ARGS="upgrade head"

# Direct database access
./tools/dev-cli.sh psql
```

### Code Quality

```bash
# Format code
make container-format

# Lint code
make container-lint

# Type checking
./tools/dev-cli.sh npm run typecheck
```

### Viewing Logs

```bash
# All services
make container-logs

# Specific service
./tools/dev-cli.sh logs backend-dev

# Follow logs
docker-compose logs -f backend-dev
```

## 🌐 Access Points

Once running, access these URLs:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | - |
| **Backend API** | http://localhost:8000/docs | - |
| **WebSocket** | ws://localhost:8001 | - |
| **Grafana** | http://localhost:3001 | admin/admin123 |
| **PgAdmin** | http://localhost:5050 | admin@lics.dev/admin123 |
| **Redis Commander** | http://localhost:8081 | - |
| **MailHog** | http://localhost:8025 | - |
| **Jaeger** | http://localhost:16686 | - |

## 🐛 Debugging

### VS Code Debugging (Dev Container)

1. Set breakpoints in your code
2. Press `F5` to start debugging
3. Debugger attaches automatically!

**Python (Backend):**
- Debugger runs on port 5678
- Breakpoints work in `.py` files
- Full variable inspection

**JavaScript (Frontend):**
- Use browser DevTools
- Or VS Code debugger for SSR code
- Breakpoints work in `.tsx` files

### Remote Debugging (Standalone)

Backend exposes debugger on port `5678`:
```json
// .vscode/launch.json
{
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  }
}
```

## 🧹 Cleanup

```bash
# Stop containers (keep data)
make container-stop

# Remove containers and data (WARNING: deletes everything!)
make container-clean

# Rebuild from scratch
make container-rebuild
```

## ❓ Troubleshooting

### "Port already in use"
```bash
# Find what's using the port
lsof -i :3000

# Or change port in docker-compose.dev.yml
```

### "Permission denied"
```bash
# Fix ownership
sudo chown -R $USER:$USER .

# Or reset volumes
docker volume prune
```

### "Container build failed"
```bash
# Clear cache and rebuild
docker-compose build --no-cache
docker image prune -a
```

### "Slow performance"
```bash
# Increase Docker resources
# Docker Desktop → Settings → Resources
# - CPUs: 4+
# - Memory: 8GB+
# - Disk: 20GB+
```

### "Database connection refused"
```bash
# Check service health
docker-compose ps

# Restart database
docker-compose restart postgres

# View logs
docker-compose logs postgres
```

## 📚 Next Steps

- 📖 Read [Containerized Development Guide](docs/CONTAINERIZED_DEVELOPMENT.md) for details
- 🏗️ Check [Architecture Documentation](Documentation.md) for system design
- 🎓 See [Development Guide](CONTRIBUTING.md) for contribution guidelines
- 💬 Ask questions in [GitHub Discussions](https://github.com/rsongphon/Primates-lics/discussions)

## 🎓 Tips

### For Best Performance
1. Use named volumes (already configured)
2. Allocate sufficient Docker resources
3. Enable file watching for hot reload
4. Use cached mounts (already configured)

### For Best Experience
1. Use VS Code Dev Containers for daily work
2. Keep containers updated (`make container-rebuild` weekly)
3. Commit code changes only (not generated files)
4. Test in container before pushing to CI

### For Troubleshooting
1. Check logs first: `make container-logs`
2. Restart services: `make container-stop && make container-dev`
3. Clean rebuild: `make container-clean && make container-rebuild`
4. Ask in GitHub Discussions

## 🚀 You're Ready!

You now have a fully containerized development environment with:
- ✅ All services running
- ✅ Hot reloading enabled
- ✅ Debugging configured
- ✅ Zero local dependencies

**Start coding!** 🎉

```bash
# VS Code Dev Container
code .  # Then "Reopen in Container"

# Or standalone
make container-dev
make container-shell

# Then
make dev
```

---

**Need help?** Check the [full documentation](docs/CONTAINERIZED_DEVELOPMENT.md) or ask in [Discussions](https://github.com/rsongphon/Primates-lics/discussions).

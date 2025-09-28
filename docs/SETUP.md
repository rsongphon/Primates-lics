# LICS Local Development Setup Guide

This comprehensive guide will help you set up the LICS (Lab Instrument Control System) development environment on your local machine.

## Quick Start

For the impatient developer:

```bash
# 1. Clone the repository
git clone https://github.com/rsongphon/Primates-lics.git
cd Primates-lics

# 2. Run automated setup for your OS
make setup-dev-env

# 3. Generate SSL certificates
make setup-ssl

# 4. Copy environment configuration
cp .env.example .env

# 5. Install project dependencies
make install

# 6. Start development environment
make dev
```

That's it! Your development environment should be running at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- WebSocket: ws://localhost:8001
- Grafana: http://localhost:3001

---

## Detailed Setup Instructions

### Prerequisites

Before starting, ensure you have:
- **Internet connection** for downloading packages
- **Administrator/sudo privileges** for system installations
- **At least 8GB RAM** and **20GB free disk space**
- **Modern operating system**:
  - macOS 10.15+ (Catalina or later)
  - Linux (Ubuntu 20.04+, CentOS 8+, Arch Linux, etc.)
  - Windows 10/11 or Windows Server 2019/2022

### Step 1: Operating System Setup

Choose your operating system and run the appropriate setup script:

#### macOS Setup

```bash
# Run the macOS setup script
./tools/scripts/setup-mac.sh

# Or use the Makefile
make setup-mac
```

**What this installs:**
- Xcode Command Line Tools
- Homebrew package manager
- Docker Desktop
- Node.js 20 (LTS)
- Python 3.11
- Git (latest version)
- mkcert for SSL certificates
- Essential development tools (curl, wget, jq, etc.)
- Visual Studio Code (optional)

#### Linux Setup

```bash
# Run the Linux setup script
./tools/scripts/setup-linux.sh

# Or use the Makefile
make setup-linux
```

**What this installs:**
- Essential packages and build tools
- Docker and Docker Compose
- Node.js 20 (LTS)
- Python 3.11
- Git
- mkcert for SSL certificates
- PostgreSQL and Redis client tools
- Visual Studio Code (optional)

**Supported Distributions:**
- Ubuntu/Debian (apt)
- CentOS/RHEL/Fedora (dnf/yum)
- Arch Linux (pacman)
- openSUSE (zypper)

#### Windows Setup

```powershell
# Run PowerShell as Administrator
.\tools\scripts\setup-windows.ps1

# Or use the Makefile (in WSL or Git Bash)
make setup-windows
```

**What this installs:**
- Chocolatey or Scoop package manager
- Docker Desktop
- Node.js 20 (LTS)
- Python 3.11
- Git
- mkcert for SSL certificates
- Essential development tools
- Visual Studio Code (optional)

### Step 2: SSL Certificate Setup

Generate SSL certificates for local HTTPS development:

```bash
# Generate SSL certificates
make setup-ssl

# Install the Certificate Authority (requires sudo/admin)
make ssl-install-ca

# Verify certificates are working
make ssl-verify
```

This creates certificates for:
- `localhost`, `127.0.0.1`, `::1`
- `*.localhost`
- `lics.local`, `*.lics.local`
- `dev.lics.local`, `api.lics.local`, `admin.lics.local`
- `grafana.lics.local`, `docs.lics.local`

### Step 3: Environment Configuration

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit configuration (optional):**
   ```bash
   # Edit the .env file with your preferred editor
   vim .env
   # or
   code .env
   ```

3. **Key settings to review:**
   ```bash
   # Development mode
   NODE_ENV=development
   ENVIRONMENT=development
   DEBUG=true

   # Database connections
   DATABASE_URL=postgresql://lics:lics123@localhost:5432/lics_dev
   REDIS_URL=redis://localhost:6379/0

   # Frontend configuration
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   NEXT_PUBLIC_WS_URL=ws://localhost:8001
   ```

### Step 4: Project Dependencies

Install dependencies for all services:

```bash
# Install all dependencies
make install

# Or install individually
make install-frontend    # Node.js packages
make install-backend     # Python packages
make install-edge-agent  # Edge device packages
```

### Step 5: Git Hooks (Optional but Recommended)

Set up Git hooks for code quality:

```bash
# Install Git hooks
make git-hooks-install

# Verify installation
make git-hooks-verify
```

This installs:
- **pre-commit**: Linting, formatting, secret detection
- **commit-msg**: Conventional commit message validation
- **pre-push**: Additional security scans

---

## Development Environment

### Starting the Development Environment

#### Standard Development Mode

```bash
# Start all services
make dev

# Or start individual services
make dev-frontend     # Frontend only (port 3000)
make dev-backend      # Backend only (port 8000)
make dev-edge-agent   # Edge agent simulation
```

#### HTTPS Development Mode

```bash
# Start with HTTPS (requires SSL setup)
make dev-https
```

#### Docker-based Development

```bash
# Start with Docker Compose
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down

# Clean up Docker resources
make docker-clean
```

### Accessing Services

Once running, access these URLs:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Web application |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| WebSocket | ws://localhost:8001 | Real-time communication |
| Grafana | http://localhost:3001 | Monitoring dashboards |
| Documentation | http://localhost:8080 | Project docs |
| MailHog | http://localhost:8025 | Email testing |
| Redis Commander | http://localhost:8081 | Redis GUI |
| PgAdmin | http://localhost:5050 | PostgreSQL GUI |

### Default Credentials

**Development Database:**
- Username: `lics`
- Password: `lics123`
- Database: `lics_dev`

**Grafana:**
- Username: `admin`
- Password: `admin123`

**PgAdmin:**
- Email: `admin@lics.dev`
- Password: `admin123`

---

## Development Workflow

### Daily Development

1. **Start your development session:**
   ```bash
   make dev
   ```

2. **Make your changes** in the appropriate service directory:
   - `services/frontend/` - Next.js frontend
   - `services/backend/` - FastAPI backend
   - `services/edge-agent/` - Python edge device code

3. **Test your changes:**
   ```bash
   make test                # All tests
   make test-frontend       # Frontend tests only
   make test-backend        # Backend tests only
   make lint                # Code linting
   make format              # Code formatting
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push
   ```

### Database Operations

```bash
# Run migrations
make db-migrate

# Rollback migration
make db-rollback

# Reset database (destroys data!)
make db-reset

# Seed with test data
make db-seed
```

### Code Quality

```bash
# Run all linting
make lint

# Format all code
make format

# Type checking
make typecheck

# Security scanning
make security-scan
```

---

## Troubleshooting

### Common Issues

#### Docker Issues

**Problem:** Docker is not running
```bash
# macOS/Windows: Start Docker Desktop
# Linux: Start Docker service
sudo systemctl start docker
```

**Problem:** Docker permission denied (Linux)
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

**Problem:** Port conflicts
```bash
# Check what's using the port
lsof -i :3000  # Check port 3000
# Kill the process or change LICS ports in .env
```

#### SSL Certificate Issues

**Problem:** Browser shows certificate warnings
```bash
# Reinstall mkcert CA
make ssl-install-ca
# Restart browser
```

**Problem:** Certificate files not found
```bash
# Regenerate certificates
make ssl-clean
make setup-ssl
```

#### Database Connection Issues

**Problem:** Cannot connect to database
```bash
# Check if PostgreSQL container is running
docker-compose ps
# Check database logs
docker-compose logs postgres-dev
# Reset database
make db-reset
```

#### Node.js/Python Issues

**Problem:** Version conflicts
```bash
# Check versions
node --version  # Should be 18+
python3 --version  # Should be 3.11+

# Reinstall dependencies
make clean
make install
```

#### Network Issues

**Problem:** Cannot access localhost services
```bash
# Check /etc/hosts file
cat /etc/hosts | grep lics

# Add missing entries
sudo tee -a /etc/hosts << 'EOF'
127.0.0.1 lics.local
127.0.0.1 dev.lics.local
127.0.0.1 api.lics.local
EOF
```

### Getting Help

1. **Check service logs:**
   ```bash
   make docker-logs
   # Or for specific service
   docker-compose logs -f backend-dev
   ```

2. **Check service health:**
   ```bash
   make health-check
   make status
   ```

3. **Verify installation:**
   ```bash
   make ssl-verify
   docker --version
   node --version
   python3 --version
   ```

4. **Reset everything:**
   ```bash
   make docker-down
   make clean
   make docker-clean
   make install
   make dev
   ```

---

## Advanced Configuration

### Custom Environment Variables

Edit `.env` to customize your development environment:

```bash
# Change default ports
FRONTEND_PORT=3001
BACKEND_PORT=8001

# Use different databases
DATABASE_URL=postgresql://user:pass@localhost:5432/custom_db

# Enable debug features
DEBUG=true
ENABLE_DEBUG_TOOLBAR=true
LOG_LEVEL=DEBUG
```

### Multiple Development Environments

You can run multiple instances of LICS:

```bash
# Copy project to different directory
cp -r Primates-lics Primates-lics-feature-branch
cd Primates-lics-feature-branch

# Use different ports
sed -i 's/3000/3100/g' .env
sed -i 's/8000/8100/g' .env
sed -i 's/8001/8101/g' .env

# Start with different project name
COMPOSE_PROJECT_NAME=lics_feature make dev
```

### Performance Optimization

For better development performance:

1. **Exclude from antivirus scanning:**
   - Project directory
   - Docker directories
   - Node.js cache directories

2. **Increase Docker resources:**
   - Memory: 4GB minimum, 8GB recommended
   - CPUs: Half of available cores
   - Disk space: 20GB minimum

3. **Use SSD storage** for Docker volumes

4. **Close unnecessary applications** during development

---

## Next Steps

After successful setup:

1. **Read the Architecture Documentation:** `docs/architecture/`
2. **Explore the API Documentation:** http://localhost:8000/docs
3. **Try the Example Tasks:** `docs/examples/`
4. **Set up your IDE:** See `docs/ide-setup.md`
5. **Join the Development Community:** See `CONTRIBUTING.md`

---

## Appendix

### Makefile Commands Reference

#### Setup Commands
- `make setup-dev-env` - Auto-detect OS and run setup
- `make setup-mac` - macOS-specific setup
- `make setup-linux` - Linux-specific setup
- `make setup-windows` - Windows-specific setup

#### SSL Commands
- `make setup-ssl` - Generate SSL certificates
- `make ssl-install-ca` - Install Certificate Authority
- `make ssl-clean` - Remove certificates
- `make ssl-verify` - Verify certificate setup

#### Development Commands
- `make install` - Install all dependencies
- `make dev` - Start development environment
- `make dev-https` - Start with HTTPS
- `make test` - Run all tests
- `make lint` - Run code linting
- `make format` - Format code

#### Docker Commands
- `make docker-up` - Start with Docker
- `make docker-down` - Stop Docker services
- `make docker-logs` - View Docker logs
- `make docker-clean` - Clean Docker resources

#### Database Commands
- `make db-migrate` - Run migrations
- `make db-rollback` - Rollback migration
- `make db-reset` - Reset database
- `make db-seed` - Seed test data

#### Utility Commands
- `make clean` - Clean build artifacts
- `make status` - Show project status
- `make health-check` - Check service health
- `make help` - Show all commands

### Directory Structure

```
lics/
├── services/           # Microservices
│   ├── frontend/      # Next.js web app
│   ├── backend/       # FastAPI backend
│   ├── edge-agent/    # Python edge agent
│   └── streaming/     # Video streaming
├── infrastructure/    # Infrastructure configs
│   ├── nginx/         # Nginx configs & SSL
│   ├── mqtt/          # MQTT broker configs
│   ├── monitoring/    # Prometheus & Grafana
│   └── database/      # Database init scripts
├── tools/             # Development tools
│   └── scripts/       # Setup scripts
├── docs/              # Documentation
├── .env.example       # Environment template
├── Makefile           # Development commands
└── docker-compose*.yml # Container definitions
```

### Environment Variables Reference

Key environment variables and their purposes:

```bash
# Application Environment
NODE_ENV=development              # Application mode
ENVIRONMENT=development           # Backend environment
DEBUG=true                       # Enable debug features

# Database
DATABASE_URL=postgresql://...     # PostgreSQL connection
REDIS_URL=redis://...            # Redis connection

# API Configuration
NEXT_PUBLIC_API_URL=http://...   # Frontend API endpoint
NEXT_PUBLIC_WS_URL=ws://...      # WebSocket endpoint

# Security
JWT_SECRET=...                   # JWT signing secret
ENCRYPTION_KEY=...               # Data encryption key

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=true    # Enable analytics
NEXT_PUBLIC_ENABLE_VIDEO_STREAMING=true  # Enable video
SIMULATE_HARDWARE=true           # Edge agent simulation
```

---

**Need help?** Check our [troubleshooting guide](TROUBLESHOOTING.md) or [open an issue](https://github.com/rsongphon/Primates-lics/issues).
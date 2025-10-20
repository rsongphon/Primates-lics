# LICS Troubleshooting Guide

This guide helps you resolve common issues encountered during LICS development and deployment.

## ⚠️ Important: Docker-First Development

**All LICS services run in Docker containers.** Most troubleshooting commands should be executed inside containers using:

```bash
docker-compose -f docker-compose.dev.yml exec <service-name> <command>
```

## Quick Diagnosis

Run these commands to quickly check your system status:

```bash
# Check Docker containers status
docker-compose -f docker-compose.dev.yml ps

# Check service health
make health-check

# View all service logs
docker-compose -f docker-compose.dev.yml logs -f

# Check specific service logs
docker-compose -f docker-compose.dev.yml logs -f backend-dev
```

---

## Installation Issues

### Setup Script Failures

**Issue:** Setup script fails with permission errors
```bash
# Solution: Ensure you have admin/sudo privileges
# macOS/Linux: Run with sudo for system installations
sudo ./tools/scripts/setup-mac.sh

# Windows: Run PowerShell as Administrator
```

**Issue:** Package manager not found
```bash
# macOS: Install Homebrew first
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Linux: Update package manager
sudo apt update          # Ubuntu/Debian
sudo dnf update          # Fedora
sudo pacman -Syu         # Arch

# Windows: Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

**Issue:** Docker installation fails
```bash
# Check system requirements
# Ensure virtualization is enabled in BIOS
# On Windows, enable Hyper-V and WSL2

# Manual installation:
# Visit https://docs.docker.com/get-docker/
```

---

## Docker Issues

### Docker Not Running

**Issue:** `docker: command not found`
```bash
# Check Docker installation
which docker

# Restart Docker service (Linux)
sudo systemctl start docker
sudo systemctl enable docker

# Start Docker Desktop (macOS/Windows)
# Use GUI or command line
open -a Docker  # macOS
```

**Issue:** Permission denied accessing Docker
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Or use sudo temporarily
sudo docker ps
```

**Issue:** Docker containers won't start
```bash
# Check Docker daemon status
docker system info

# Check available resources
docker system df

# Clean up if needed
docker system prune -f
make docker-clean
```

### Port Conflicts

**Issue:** Port already in use
```bash
# Find what's using the port
lsof -i :3000           # macOS/Linux
netstat -ano | findstr :3000  # Windows

# Kill the process
kill -9 <PID>           # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or change LICS ports in .env
FRONTEND_PORT=3001
BACKEND_PORT=8001
```

### Container Issues

**Issue:** Container keeps restarting
```bash
# Check container logs
docker-compose logs <service-name>

# Check container status
docker-compose ps

# Restart specific service
docker-compose restart <service-name>
```

**Issue:** Out of disk space
```bash
# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a
docker volume prune
```

---

## Database Issues

### Connection Problems

**Issue:** Cannot connect to database
```bash
# Check if PostgreSQL container is running
docker-compose -f docker-compose.dev.yml ps postgres-dev

# Check database logs
docker-compose -f docker-compose.dev.yml logs postgres-dev

# Check connection manually from backend container
docker-compose -f docker-compose.dev.yml exec backend-dev python -c "from app.core.database import engine; print('Connected!')"

# Or connect directly to PostgreSQL
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev
```

**Issue:** Database migration errors
```bash
# Run migrations inside backend container
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head

# Check migration status
docker-compose -f docker-compose.dev.yml exec backend-dev alembic current

# Rollback and retry
docker-compose -f docker-compose.dev.yml exec backend-dev alembic downgrade -1
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head

# Reset if corrupted (destroys data!)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

**Issue:** Permission denied to database
```bash
# Check database credentials in .env
DATABASE_URL=postgresql://lics:lics123@postgres-dev:5432/lics_dev

# Restart database container
docker-compose -f docker-compose.dev.yml restart postgres-dev
```

### TimescaleDB Issues

**Issue:** TimescaleDB extension not found
```bash
# Ensure using correct image
# Check docker-compose.yml uses timescale/timescaledb-ha

# Recreate database container
docker-compose down
docker volume rm lics_postgres_dev_data
docker-compose up -d postgres-dev
make db-migrate
```

---

## SSL Certificate Issues

### Certificate Not Trusted

**Issue:** Browser shows "Not Secure" warning
```bash
# Install mkcert Certificate Authority
make ssl-install-ca

# Or manually
sudo mkcert -install

# Restart browser completely
```

**Issue:** Certificate files not found
```bash
# Check if certificates exist
ls -la infrastructure/nginx/ssl/

# Regenerate certificates
make ssl-clean
make setup-ssl
```

**Issue:** Certificate expired
```bash
# Check certificate validity
openssl x509 -in infrastructure/nginx/ssl/localhost.pem -text -noout | grep "Not After"

# Regenerate if expired
make ssl-clean
make setup-ssl
```

### Domain Issues

**Issue:** Cannot access .local domains
```bash
# Check /etc/hosts file
cat /etc/hosts | grep lics

# Add missing entries
sudo tee -a /etc/hosts << 'EOF'
127.0.0.1 lics.local
127.0.0.1 dev.lics.local
127.0.0.1 api.lics.local
127.0.0.1 admin.lics.local
127.0.0.1 grafana.lics.local
127.0.0.1 docs.lics.local
EOF

# Flush DNS cache
sudo dscacheutil -flushcache  # macOS
sudo systemctl restart systemd-resolved  # Linux
ipconfig /flushdns  # Windows
```

---

## Network Issues

### Service Connectivity

**Issue:** Frontend cannot reach backend
```bash
# Check backend is running
curl http://localhost:8000/health

# Check environment variables
cat .env | grep API_URL

# Check Docker network
docker network ls
docker network inspect lics-dev-network
```

**Issue:** WebSocket connection fails
```bash
# Check WebSocket endpoint
curl -v http://localhost:8001

# Check firewall settings
# Ensure ports 8001 is open

# Check proxy settings
# Disable VPN if causing issues
```

### DNS Resolution

**Issue:** Cannot resolve service names
```bash
# In Docker containers
docker-compose exec frontend-dev nslookup backend-dev

# Add to /etc/hosts if needed
127.0.0.1 backend-dev frontend-dev
```

---

## Node.js Issues

### Version Problems

**Issue:** Unsupported Node.js version
```bash
# Check current version
node --version

# Install correct version (18+)
# Using nvm
nvm install 20
nvm use 20

# Or update via package manager
brew upgrade node  # macOS
```

**Issue:** npm install fails
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf services/frontend/node_modules
make install-frontend

# Check for permission issues
npm config get prefix
npm config set prefix ~/.npm-global
```

**Issue:** Build errors
```bash
# Check TypeScript errors
make lint-frontend

# Clear Next.js cache
rm -rf services/frontend/.next

# Rebuild from scratch
make clean
make install-frontend
make build-frontend
```

---

## Python Issues

### Version Problems

**Issue:** Wrong Python version
```bash
# Check current version
python3 --version

# Install correct version (3.11+)
# macOS
brew install python@3.11

# Linux
sudo apt install python3.11 python3.11-pip

# Update alternatives
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

**Issue:** pip install fails
```bash
# Upgrade pip
python3 -m pip install --upgrade pip

# Install with user flag
python3 -m pip install --user -r requirements.txt

# Clear pip cache
python3 -m pip cache purge
```

**Issue:** Virtual environment issues
```bash
# Create new virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r services/backend/requirements.txt
```

---

## Service-Specific Issues

### Frontend Issues

**Issue:** Next.js build fails
```bash
# Check for TypeScript errors inside container
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run type-check

# Check build logs
docker-compose -f docker-compose.dev.yml logs frontend-dev

# Rebuild container from scratch
docker-compose -f docker-compose.dev.yml build --no-cache frontend-dev
docker-compose -f docker-compose.dev.yml up -d frontend-dev
```

**Issue:** Hot reload not working
```bash
# Check if file watching is working
docker-compose -f docker-compose.dev.yml logs -f frontend-dev

# Restart development server
docker-compose -f docker-compose.dev.yml restart frontend-dev

# If still not working, rebuild container
docker-compose -f docker-compose.dev.yml up -d --build frontend-dev
```

### Backend Issues

**Issue:** FastAPI import errors
```bash
# Check logs inside container
docker-compose -f docker-compose.dev.yml logs backend-dev

# Verify dependencies are installed
docker-compose -f docker-compose.dev.yml exec backend-dev pip list

# Rebuild container with fresh dependencies
docker-compose -f docker-compose.dev.yml build --no-cache backend-dev
docker-compose -f docker-compose.dev.yml up -d backend-dev
```

**Issue:** Database models not found
```bash
# Run migrations inside backend container
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head

# Check if tables exist
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev -c "\dt"
```

### Edge Agent Issues

**Issue:** Hardware simulation not working
```bash
# Check environment variable
echo $SIMULATE_HARDWARE

# Set in .env
SIMULATE_HARDWARE=true

# Restart edge agent
make dev-edge-agent
```

---

## Performance Issues

### Slow Development

**Issue:** Services are slow to start
```bash
# Check system resources
htop  # Linux/macOS
Task Manager  # Windows

# Increase Docker memory allocation
# Docker Desktop > Settings > Resources

# Close unnecessary applications
```

**Issue:** File watching issues
```bash
# Increase file watch limits (Linux)
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Exclude from antivirus scanning
# Add project directory to exclusions
```

### Memory Issues

**Issue:** Out of memory errors
```bash
# Check memory usage
docker stats

# Increase available memory
# Or reduce running services
make dev-frontend  # Only frontend
make dev-backend   # Only backend
```

---

## Monitoring Issues

### Grafana Access

**Issue:** Cannot access Grafana
```bash
# Check if container is running
docker-compose ps grafana

# Check logs
docker-compose logs grafana

# Reset admin password
docker-compose exec grafana grafana-cli admin reset-admin-password admin123
```

**Issue:** No data in dashboards
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check if services are exposing metrics
curl http://localhost:8000/metrics
```

---

## Recovery Procedures

### Complete Reset

If all else fails, perform a complete reset:

```bash
# 1. Stop all services and remove volumes
docker-compose -f docker-compose.dev.yml down -v

# 2. Remove all containers and images
docker-compose -f docker-compose.dev.yml down --rmi all

# 3. Clean Docker system
docker system prune -af

# 4. Rebuild and start fresh
docker-compose -f docker-compose.dev.yml up -d --build

# 5. Or use make command
make dev
```

### Backup and Restore

**Create backup before major changes:**
```bash
# Backup database from container
docker-compose -f docker-compose.dev.yml exec -T postgres-dev pg_dump -U lics lics_dev > backup.sql

# Backup configuration
tar czf lics-backup.tar.gz .env
```

**Restore from backup:**
```bash
# Restore database to container
docker-compose -f docker-compose.dev.yml exec -T postgres-dev psql -U lics lics_dev < backup.sql

# Restore configuration
tar xzf lics-backup.tar.gz
```

---

## Getting Additional Help

### Log Analysis

1. **Collect logs from all containers:**
   ```bash
   # All service logs
   docker-compose -f docker-compose.dev.yml logs > logs.txt

   # Container status
   docker-compose -f docker-compose.dev.yml ps >> logs.txt

   # Docker info
   docker info >> logs.txt
   ```

2. **Check specific service logs:**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f frontend-dev
   docker-compose -f docker-compose.dev.yml logs -f backend-dev
   docker-compose -f docker-compose.dev.yml logs -f postgres-dev
   ```

3. **Check logs inside containers:**
   ```bash
   # Backend logs
   docker-compose -f docker-compose.dev.yml exec backend-dev cat /app/logs/app.log

   # Frontend logs
   docker-compose -f docker-compose.dev.yml exec frontend-dev npm run build 2>&1
   ```

### Community Resources

- **GitHub Issues**: [Report bugs or get help](https://github.com/rsongphon/Primates-lics/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/rsongphon/Primates-lics/discussions)
- **Documentation**: [Complete documentation](https://docs.lics.io)

### Before Asking for Help

Include this information when seeking help:

1. **System information:**
   ```bash
   uname -a                    # Operating system
   docker --version            # Docker version
   docker-compose --version    # Compose version

   # Versions inside containers
   docker-compose -f docker-compose.dev.yml exec frontend-dev node --version
   docker-compose -f docker-compose.dev.yml exec backend-dev python --version
   ```

2. **Error details:**
   - Complete error message
   - Steps to reproduce
   - What you were trying to achieve
   - Recent changes made

3. **Container status:**
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   docker-compose -f docker-compose.dev.yml logs --tail=50
   ```

---

**Still having issues?** The LICS community is here to help! Please [open an issue](https://github.com/rsongphon/Primates-lics/issues) with detailed information about your problem.
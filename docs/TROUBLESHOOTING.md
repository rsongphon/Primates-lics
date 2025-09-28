# LICS Troubleshooting Guide

This guide helps you resolve common issues encountered during LICS development and deployment.

## Quick Diagnosis

Run these commands to quickly check your system status:

```bash
# Check overall project status
make status

# Check service health
make health-check

# Verify SSL certificates
make ssl-verify

# Check Docker status
docker-compose ps
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
docker-compose ps postgres-dev

# Check database logs
docker-compose logs postgres-dev

# Reset database
make db-reset

# Check connection manually
docker-compose exec postgres-dev psql -U lics -d lics_dev
```

**Issue:** Database migration errors
```bash
# Check migration status
make db-migrate

# Rollback and retry
make db-rollback
make db-migrate

# Reset if corrupted
make db-reset
```

**Issue:** Permission denied to database
```bash
# Check database credentials in .env
DATABASE_URL=postgresql://lics:lics123@localhost:5432/lics_dev

# Restart database container
docker-compose restart postgres-dev
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
# Check for TypeScript errors
cd services/frontend
npm run type-check

# Clear cache and rebuild
rm -rf .next node_modules
npm install
npm run build
```

**Issue:** Hot reload not working
```bash
# Check file permissions
# Ensure you're not running in VM with shared folders

# Restart development server
make dev-frontend
```

### Backend Issues

**Issue:** FastAPI import errors
```bash
# Check Python path
echo $PYTHONPATH

# Install in development mode
cd services/backend
pip install -e .

# Check for missing dependencies
pip install -r requirements.txt
```

**Issue:** Database models not found
```bash
# Run migrations
make db-migrate

# Check if tables exist
docker-compose exec postgres-dev psql -U lics -d lics_dev -c "\dt"
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
# 1. Stop all services
make docker-down

# 2. Clean everything
make clean
make docker-clean

# 3. Remove SSL certificates
make ssl-clean

# 4. Remove Docker volumes
docker volume prune -f

# 5. Restart from scratch
make setup-ssl
make install
make dev
```

### Backup and Restore

**Create backup before major changes:**
```bash
# Backup database
docker-compose exec postgres-dev pg_dump -U lics lics_dev > backup.sql

# Backup configuration
tar czf lics-backup.tar.gz .env infrastructure/nginx/ssl/
```

**Restore from backup:**
```bash
# Restore database
docker-compose exec -T postgres-dev psql -U lics lics_dev < backup.sql

# Restore configuration
tar xzf lics-backup.tar.gz
```

---

## Getting Additional Help

### Log Analysis

1. **Collect logs:**
   ```bash
   # All service logs
   make docker-logs > logs.txt

   # System information
   make status >> logs.txt

   # Environment info
   env | grep -E "(NODE|PYTHON|DOCKER)" >> logs.txt
   ```

2. **Check specific service logs:**
   ```bash
   docker-compose logs -f frontend-dev
   docker-compose logs -f backend-dev
   docker-compose logs -f postgres-dev
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
   node --version              # Node.js version
   python3 --version           # Python version
   ```

2. **Error details:**
   - Complete error message
   - Steps to reproduce
   - What you were trying to achieve
   - Recent changes made

3. **Service status:**
   ```bash
   make status
   make health-check
   docker-compose ps
   ```

---

**Still having issues?** The LICS community is here to help! Please [open an issue](https://github.com/rsongphon/Primates-lics/issues) with detailed information about your problem.
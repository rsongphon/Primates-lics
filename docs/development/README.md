# Development Documentation

This section contains guides and documentation for developers working on the LICS project.

## 📁 Development Guides

### 🚀 [Setup Guide](./setup.md)
Complete development environment setup including:
- Docker installation and configuration
- Development dependencies
- Environment variables
- Initial project setup

### 🐳 [Containerized Development](./containerized-development.md)
Docker-based development workflow covering:
- Development containers setup
- Hot-reload configuration
- Debugging in containers
- Performance optimization

### 🔄 [Git Workflow](./git-workflow.md)
Version control and collaboration process:
- Branching strategy
- Commit conventions
- Pull request process
- Code review guidelines

### 🗄️ [Database Migrations](./database-migrations.md)
Database change management:
- Migration creation and execution
- Schema changes
- Data migration strategies
- Rollback procedures

### 🔧 [Troubleshooting](./troubleshooting.md)
Common issues and solutions:
- Development environment problems
- Build and deployment issues
- Performance debugging
- FAQ and solutions

## 🚀 Quick Start

1. **First time setup**: Follow the [Setup Guide](./setup.md)
2. **Docker development**: Use [Containerized Development](./containerized-development.md)
3. **Code contribution**: Follow [Git Workflow](./git-workflow.md)
4. **Database changes**: Use [Database Migrations](./database-migrations.md)
5. **Need help?**: Check [Troubleshooting](./troubleshooting.md)

## 🛠️ Development Commands

### Essential Docker Commands
```bash
# Start complete development environment
make dev

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Execute commands in containers
docker-compose -f docker-compose.dev.yml exec backend-dev bash
```

### Testing Commands
```bash
# Run all tests
make test

# Run backend tests
make test-backend

# Run frontend tests
make test-frontend
```

### Database Operations
```bash
# Run migrations
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head

# Create new migration
docker-compose -f docker-compose.dev.yml exec backend-dev alembic revision --autogenerate -m "description"
```

## 📚 Additional Resources

- **Architecture Documentation**: [../architecture/](../architecture/)
- **Testing Guides**: [../testing/](../testing/)
- **Implementation Details**: [../implementation/](../implementation/)
- **Project Overview**: [../project/](../project/)

---

For service-specific development information, see the README files in each service directory.
# Database Infrastructure

This directory contains all database-related infrastructure components for the LICS system, including setup scripts, maintenance tools, and monitoring utilities.

## Directory Structure

```
infrastructure/database/
├── README.md                   # This file
├── manage.py                   # Database management CLI tool
├── health_check.py            # Health monitoring script
├── maintenance.py             # Automated maintenance tasks
├── cleanup.sh                 # Shell-based cleanup script
├── cron-maintenance.sh        # Cron job scheduler
├── alembic/                   # Database migrations
│   ├── alembic.ini           # Alembic configuration
│   ├── env.py                # Migration environment
│   ├── script.py.mako        # Migration template
│   └── versions/             # Migration files
├── postgresql.conf            # Production PostgreSQL config
├── postgresql-dev.conf       # Development PostgreSQL config
└── init.sql                   # Database initialization script
```

## Quick Start

### 1. Database Management

Use the main management script for common database operations:

```bash
# Initialize database and run migrations
python3 infrastructure/database/manage.py migrate

# Create a new migration
python3 infrastructure/database/manage.py create-migration "Add new table"

# Check database health
python3 infrastructure/database/manage.py health-check

# Backup database
python3 infrastructure/database/manage.py backup

# Restore from backup
python3 infrastructure/database/manage.py restore backups/backup_20241201_120000.sql
```

### 2. Health Monitoring

Monitor all database services:

```bash
# Check all database services
python3 infrastructure/monitoring/database/health_check.py

# JSON output for automation
python3 infrastructure/monitoring/database/health_check.py --format json

# Check specific service
python3 infrastructure/monitoring/database/health_check.py --service postgres
```

### 3. Maintenance Tasks

Run maintenance and cleanup:

```bash
# Quick cleanup (logs only)
./infrastructure/database/cleanup.sh quick

# Database maintenance (VACUUM, ANALYZE)
./infrastructure/database/cleanup.sh maintenance

# Full cleanup (all tasks)
./infrastructure/database/cleanup.sh full

# Python-based maintenance
python3 infrastructure/database/maintenance.py

# Specific maintenance tasks
python3 infrastructure/database/maintenance.py --tasks postgres_maintenance redis_maintenance
```

### 4. Automated Scheduling

Set up automated maintenance:

```bash
# Install cron jobs for automated maintenance
sudo ./infrastructure/database/cron-maintenance.sh install

# List current maintenance jobs
./infrastructure/database/cron-maintenance.sh list

# Test maintenance scripts
./infrastructure/database/cron-maintenance.sh test

# Remove cron jobs
sudo ./infrastructure/database/cron-maintenance.sh remove
```

## Database Services

### PostgreSQL with TimescaleDB
- **Primary database** for application data
- **TimescaleDB extension** for time-series telemetry data
- **Connection pooling** via PgBouncer
- **Automatic backups** and health monitoring

Configuration files:
- `postgresql.conf` - Production optimized settings
- `postgresql-dev.conf` - Development settings with debugging

### Redis
- **Caching layer** for application data
- **Session storage** for user sessions
- **Message queuing** for real-time features
- **Pub/Sub** for WebSocket communication

### InfluxDB
- **Time-series database** for telemetry and metrics
- **Bucket-based organization** by data type
- **Automatic downsampling** and retention policies
- **Integration** with Grafana for visualization

## Migration Management

### Alembic Configuration

The system uses Alembic for database schema migrations:

```bash
# Generate new migration
cd infrastructure/database && alembic revision --autogenerate -m "Description"

# Apply migrations
cd infrastructure/database && alembic upgrade head

# Downgrade migrations
cd infrastructure/database && alembic downgrade -1

# Show current revision
cd infrastructure/database && alembic current

# Show migration history
cd infrastructure/database && alembic history
```

### Migration Best Practices

1. **Always review** auto-generated migrations before applying
2. **Test migrations** on development data first
3. **Backup database** before major schema changes
4. **Use descriptive messages** for migration names
5. **Consider backward compatibility** for rolling deployments

## Performance Optimization

### PostgreSQL Tuning

The configuration files include optimizations for:
- **Memory settings** based on available RAM
- **Connection pooling** to handle concurrent users
- **Query optimization** with proper indexes
- **TimescaleDB settings** for time-series data

Key settings (production):
```ini
shared_buffers = 2GB              # 25% of RAM
effective_cache_size = 6GB        # 75% of RAM
work_mem = 16MB                   # Per-operation memory
max_connections = 200             # With PgBouncer pooling
```

### Monitoring and Alerts

Health checks monitor:
- **Connection availability** and response time
- **Memory usage** and disk space
- **Query performance** and slow queries
- **Replication lag** (if configured)
- **Backup status** and integrity

## Backup and Recovery

### Automated Backups

Backups are performed automatically:
- **Daily full backups** at 2:00 AM
- **Transaction log archiving** for point-in-time recovery
- **Backup verification** to ensure integrity
- **Offsite backup** retention (30 days)

### Manual Backup/Restore

```bash
# Create backup
python3 infrastructure/database/manage.py backup

# List available backups
python3 infrastructure/database/manage.py list-backups

# Restore from backup
python3 infrastructure/database/manage.py restore backups/backup_20241201_120000.sql

# Test backup integrity
python3 infrastructure/database/manage.py validate-backup backups/backup_20241201_120000.sql
```

## Maintenance Schedule

### Automated Tasks

| Task | Frequency | Time | Description |
|------|-----------|------|-------------|
| Health checks | Daily | 2:30 AM | Monitor all services |
| Log cleanup | Daily | 2:00 AM | Remove old log files |
| Quick maintenance | Daily | 2:00 AM | Basic cleanup tasks |
| Database maintenance | Weekly | Sunday 3:00 AM | VACUUM, ANALYZE, statistics |
| Full cleanup | Monthly | 1st day 4:00 AM | Comprehensive maintenance |
| Backup verification | Daily | 2:15 AM | Verify backup integrity |

### Manual Maintenance

Regular manual tasks:
- **Schema updates** via migrations
- **Index optimization** based on query patterns
- **Performance tuning** based on metrics
- **Capacity planning** for storage growth

## Troubleshooting

### Common Issues

**Connection Issues:**
```bash
# Check if services are running
docker-compose ps postgres redis influxdb

# Check health status
python3 infrastructure/monitoring/database/health_check.py

# Check logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs influxdb
```

**Performance Issues:**
```bash
# Check slow queries
python3 infrastructure/database/manage.py slow-queries

# Check table sizes
python3 infrastructure/database/manage.py table-sizes

# Run performance analysis
./infrastructure/database/cleanup.sh maintenance
```

**Migration Issues:**
```bash
# Check current migration status
cd infrastructure/database && alembic current

# Show pending migrations
cd infrastructure/database && alembic show

# Force migration to specific revision
cd infrastructure/database && alembic stamp head
```

### Log Locations

- **Application logs:** `/app/logs/` (in containers)
- **PostgreSQL logs:** Container logs via `docker-compose logs postgres`
- **Maintenance logs:** `logs/database/maintenance-*.log`
- **Health check logs:** `logs/monitoring/health-*.log`

## Development vs Production

### Development Environment
- **Relaxed security** settings for easier debugging
- **Verbose logging** for development
- **Smaller resource** allocations
- **Fast restart** configurations

### Production Environment
- **Security hardened** configurations
- **Performance optimized** settings
- **Monitoring and alerting** enabled
- **Backup and recovery** procedures

## Integration with Application

The database infrastructure integrates with:

- **FastAPI backend** (Week 3 implementation)
- **Authentication system** for user management
- **WebSocket server** for real-time updates
- **Task execution engine** for experiment data
- **Monitoring stack** (Grafana, Prometheus)

## Environment Variables

Required environment variables:

```bash
# PostgreSQL
DATABASE_URL=postgresql://lics:password@localhost:5432/lics
PGBOUNCER_URL=postgresql://lics:password@localhost:6432/lics

# Redis
REDIS_URL=redis://localhost:6379/0

# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-admin-token
INFLUXDB_ORG=lics
INFLUXDB_BUCKET=telemetry

# Backup settings
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=lics-backups  # Optional for cloud backups
```

## Security Considerations

- **Network isolation** between services
- **Encrypted connections** (TLS) in production
- **Regular security updates** for database images
- **Access control** via strong passwords and limited privileges
- **Audit logging** for all administrative actions

## Next Steps

After completing the database layer (Week 2, Day 1-2), the next phases are:

1. **Week 2, Day 3-4:** Message Broker and Storage (MQTT, MinIO)
2. **Week 2, Day 5:** Monitoring Foundation (Prometheus, Grafana)
3. **Week 3:** FastAPI Application Foundation
4. **Week 4:** API Development and Real-time Communication

The database infrastructure is designed to support all future application components seamlessly.
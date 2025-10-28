# Database Migrations Guide

This guide explains how to work with database migrations in the LICS project using Alembic.

## Overview

LICS uses **Alembic** for database schema migrations. The migration infrastructure is located in `infrastructure/database/` and is designed to work seamlessly within Docker containers.

### Directory Structure

```
infrastructure/database/
├── alembic.ini              # Alembic configuration
├── manage.py                # Database management CLI
└── migrations/
    ├── env.py              # Alembic environment configuration
    └── versions/           # Migration files
```

## Running Migrations

There are **two methods** to run migrations:

### Method 1: Using manage.py (Recommended)

The `manage.py` script provides a convenient wrapper around Alembic with additional database management features:

```bash
# Apply all pending migrations
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py migrate

# Create a new migration
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py create -m "add user table" --autogenerate

# Show current revision
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py current

# Show migration history
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py history

# Downgrade one revision
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py downgrade -r -1
```

### Method 2: Direct Alembic Commands

After rebuilding the backend container, you can use direct Alembic commands. The container automatically creates a symlink to make this work:

```bash
# Apply all pending migrations
docker-compose -f docker-compose.dev.yml exec backend-dev \
  alembic upgrade head

# Create a new migration
docker-compose -f docker-compose.dev.yml exec backend-dev \
  alembic revision --autogenerate -m "add user table"

# Show current revision
docker-compose -f docker-compose.dev.yml exec backend-dev \
  alembic current

# Show migration history
docker-compose -f docker-compose.dev.yml exec backend-dev \
  alembic history
```

## How It Works

### Container Setup

When the backend container starts, the entrypoint script (`docker-entrypoint-dev.sh`) automatically creates a symlink:

```
/app/alembic.ini → /infrastructure/database/alembic.ini
```

This allows Alembic to find its configuration regardless of where you run the command from.

### Configuration

The `alembic.ini` configuration file specifies:
- **script_location**: `migrations` (relative to alembic.ini location)
- **Database URL**: Overridden by environment variables
- **File template**: Includes timestamp for better version tracking

### Environment Variables

Migrations use the following environment variables (automatically set in docker-compose.dev.yml):

- `ENVIRONMENT`: `development` (determines which database to use)
- `DATABASE_URL`: PostgreSQL connection string
- `ALEMBIC_ASYNC`: Set to `true` for async migrations (optional)

## Creating Migrations

### Auto-generate from Model Changes

The recommended way is to let Alembic detect changes in your SQLAlchemy models:

```bash
# 1. Update your models in services/backend/app/models/
# 2. Generate migration
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py create -m "add new field" --autogenerate

# 3. Review the generated migration in infrastructure/database/migrations/versions/
# 4. Apply the migration
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py migrate
```

### Manual Migrations

For complex changes, create an empty migration and write the upgrade/downgrade logic manually:

```bash
# Create empty migration
docker-compose -f docker-compose.dev.yml exec backend-dev \
  alembic revision -m "custom migration"

# Edit the generated file in infrastructure/database/migrations/versions/
# Add your custom upgrade() and downgrade() logic
```

## Additional Database Operations

### Database Initialization

```bash
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py init
```

### Schema Validation

```bash
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py validate
```

### Backup and Restore

```bash
# Create backup
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py backup

# Restore from backup
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py restore -f backup_20250101_120000.sql
```

## Troubleshooting

### Error: "No 'script_location' key found in configuration"

**Cause**: Alembic can't find `alembic.ini`

**Solution**:
1. Rebuild the backend container to ensure the entrypoint script is updated:
   ```bash
   docker-compose -f docker-compose.dev.yml up --build backend-dev
   ```

2. Or use the full path explicitly:
   ```bash
   docker-compose -f docker-compose.dev.yml exec backend-dev \
     alembic -c infrastructure/database/alembic.ini upgrade head
   ```

### Error: "Can't locate revision identified by 'head'"

**Cause**: No migrations have been created yet

**Solution**: Create your first migration:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev \
  python /infrastructure/database/manage.py create -m "initial migration" --autogenerate
```

### Error: "Target database is not up to date"

**Cause**: Database is ahead or behind the migration files

**Solution**:
1. Check current revision:
   ```bash
   docker-compose -f docker-compose.dev.yml exec backend-dev \
     python /infrastructure/database/manage.py current
   ```

2. Check migration history:
   ```bash
   docker-compose -f docker-compose.dev.yml exec backend-dev \
     python /infrastructure/database/manage.py history
   ```

3. Either upgrade to head or downgrade to a specific revision

## Best Practices

1. **Always review auto-generated migrations** before applying them
2. **Test migrations in development** before production
3. **Include both upgrade and downgrade** functions in migrations
4. **Use descriptive migration messages** that explain what changed
5. **Never edit applied migrations** - create a new migration instead
6. **Backup database** before running migrations in production
7. **Use manage.py for scripting** - it has better error handling

## Production Migrations

For production environments, use the manage.py script with explicit revision control:

```bash
# Check current state
python /infrastructure/database/manage.py current

# Apply specific revision
python /infrastructure/database/manage.py migrate -r abc123

# Or apply all pending
python /infrastructure/database/manage.py migrate
```

## See Also

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- `infrastructure/database/manage.py` - Full CLI reference
- `CLAUDE.md` - Quick command reference

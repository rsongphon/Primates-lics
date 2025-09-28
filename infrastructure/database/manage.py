#!/usr/bin/env python3
"""
LICS Database Management Script

This script provides utilities for managing the LICS database including:
- Running Alembic migrations
- Database initialization
- Schema validation
- Data seeding
- Backup and restore operations

Usage:
    python manage.py migrate          # Run pending migrations
    python manage.py init             # Initialize database
    python manage.py seed             # Seed with sample data
    python manage.py backup           # Create database backup
    python manage.py restore <file>   # Restore from backup
    python manage.py validate         # Validate schema
"""

import argparse
import asyncio
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseManager:
    """Database management utilities."""

    def __init__(self):
        self.db_url = self._get_database_url()
        self.project_root = Path(__file__).parent.parent.parent

    def _get_database_url(self) -> str:
        """Get database URL based on environment."""
        env = os.getenv('ENVIRONMENT', 'development')

        if env == 'development':
            return os.getenv('DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics_dev')
        elif env == 'test':
            return os.getenv('TEST_DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics_test')
        else:
            return os.getenv('DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics')

    def _run_alembic_command(self, command: str, *args) -> int:
        """Run an Alembic command."""
        cmd = ['alembic', '-c', 'alembic.ini'] + [command] + list(args)
        print(f"Running: {' '.join(cmd)}")

        # Change to the database directory
        cwd = Path(__file__).parent
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode

    def migrate(self, revision: str = "head") -> int:
        """Run database migrations."""
        print(f"🔄 Running migrations to revision: {revision}")
        return self._run_alembic_command("upgrade", revision)

    def create_migration(self, message: str, autogenerate: bool = True) -> int:
        """Create a new migration."""
        print(f"📝 Creating migration: {message}")
        args = ["revision"]
        if autogenerate:
            args.append("--autogenerate")
        args.extend(["-m", message])
        return self._run_alembic_command(*args)

    def downgrade(self, revision: str = "-1") -> int:
        """Downgrade database."""
        print(f"⬇️  Downgrading to revision: {revision}")
        return self._run_alembic_command("downgrade", revision)

    def show_current_revision(self) -> int:
        """Show current database revision."""
        print("📍 Current database revision:")
        return self._run_alembic_command("current")

    def show_migration_history(self) -> int:
        """Show migration history."""
        print("📜 Migration history:")
        return self._run_alembic_command("history")

    async def init_database(self) -> None:
        """Initialize database with extensions and schemas."""
        print("🔧 Initializing database...")

        # Parse connection info from URL
        if '://' in self.db_url:
            # Extract connection parameters
            url_parts = self.db_url.split('://', 1)[1]
            if '@' in url_parts:
                auth_part, host_part = url_parts.split('@', 1)
                username, password = auth_part.split(':', 1) if ':' in auth_part else (auth_part, '')
                if '/' in host_part:
                    host_port, database = host_part.split('/', 1)
                    host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '5432')
                else:
                    host, port = host_part.split(':', 1) if ':' in host_part else (host_part, '5432')
                    database = 'postgres'
            else:
                print("❌ Invalid database URL format")
                return

        try:
            # Connect to database
            conn = await asyncpg.connect(
                host=host,
                port=int(port),
                user=username,
                password=password,
                database=database
            )

            # Check if TimescaleDB extension is available
            result = await conn.fetch("SELECT name FROM pg_available_extensions WHERE name = 'timescaledb'")
            if result:
                print("✅ TimescaleDB extension is available")
            else:
                print("⚠️  TimescaleDB extension not available")

            # Close connection
            await conn.close()
            print("✅ Database initialization completed")

        except Exception as e:
            print(f"❌ Database initialization failed: {e}")

    async def validate_schema(self) -> bool:
        """Validate database schema."""
        print("🔍 Validating database schema...")

        try:
            # Parse connection info
            if '://' in self.db_url:
                url_parts = self.db_url.split('://', 1)[1]
                if '@' in url_parts:
                    auth_part, host_part = url_parts.split('@', 1)
                    username, password = auth_part.split(':', 1) if ':' in auth_part else (auth_part, '')
                    if '/' in host_part:
                        host_port, database = host_part.split('/', 1)
                        host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '5432')

            conn = await asyncpg.connect(
                host=host,
                port=int(port),
                user=username,
                password=password,
                database=database
            )

            # Check for required schemas
            schemas = await conn.fetch("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'lics_%'")
            schema_names = [s['schema_name'] for s in schemas]

            required_schemas = ['lics_core', 'lics_telemetry', 'lics_audit']
            missing_schemas = [s for s in required_schemas if s not in schema_names]

            if missing_schemas:
                print(f"❌ Missing schemas: {missing_schemas}")
                await conn.close()
                return False

            # Check for core tables
            tables = await conn.fetch("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema IN ('lics_core', 'lics_telemetry', 'lics_audit')
            """)

            table_count = len(tables)
            print(f"✅ Found {table_count} tables in LICS schemas")

            # Check for TimescaleDB hypertables
            hypertables = await conn.fetch("""
                SELECT hypertable_name, hypertable_schema
                FROM timescaledb_information.hypertables
                WHERE hypertable_schema = 'lics_telemetry'
            """)

            hypertable_count = len(hypertables)
            print(f"✅ Found {hypertable_count} TimescaleDB hypertables")

            await conn.close()
            print("✅ Schema validation completed successfully")
            return True

        except Exception as e:
            print(f"❌ Schema validation failed: {e}")
            return False

    def backup_database(self, backup_path: str = None) -> int:
        """Create a database backup."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_{timestamp}.sql"

        print(f"💾 Creating database backup: {backup_path}")

        # Parse connection info for pg_dump
        if '://' in self.db_url:
            url_parts = self.db_url.split('://', 1)[1]
            if '@' in url_parts:
                auth_part, host_part = url_parts.split('@', 1)
                username, password = auth_part.split(':', 1) if ':' in auth_part else (auth_part, '')
                if '/' in host_part:
                    host_port, database = host_part.split('/', 1)
                    host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '5432')

        env = os.environ.copy()
        env['PGPASSWORD'] = password

        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', username,
            '-d', database,
            '--verbose',
            '--clean',
            '--if-exists',
            '--format=custom',
            '--file', backup_path
        ]

        result = subprocess.run(cmd, env=env)
        if result.returncode == 0:
            print(f"✅ Backup created successfully: {backup_path}")
        else:
            print(f"❌ Backup failed with return code: {result.returncode}")

        return result.returncode

    def restore_database(self, backup_path: str) -> int:
        """Restore database from backup."""
        print(f"📁 Restoring database from: {backup_path}")

        if not os.path.exists(backup_path):
            print(f"❌ Backup file not found: {backup_path}")
            return 1

        # Parse connection info for pg_restore
        if '://' in self.db_url:
            url_parts = self.db_url.split('://', 1)[1]
            if '@' in url_parts:
                auth_part, host_part = url_parts.split('@', 1)
                username, password = auth_part.split(':', 1) if ':' in auth_part else (auth_part, '')
                if '/' in host_part:
                    host_port, database = host_part.split('/', 1)
                    host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '5432')

        env = os.environ.copy()
        env['PGPASSWORD'] = password

        cmd = [
            'pg_restore',
            '-h', host,
            '-p', port,
            '-U', username,
            '-d', database,
            '--verbose',
            '--clean',
            '--if-exists',
            backup_path
        ]

        result = subprocess.run(cmd, env=env)
        if result.returncode == 0:
            print(f"✅ Database restored successfully from: {backup_path}")
        else:
            print(f"❌ Restore failed with return code: {result.returncode}")

        return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='LICS Database Management')
    parser.add_argument('command', choices=[
        'migrate', 'init', 'validate', 'backup', 'restore',
        'current', 'history', 'create', 'downgrade'
    ], help='Command to execute')
    parser.add_argument('--message', '-m', help='Migration message (for create command)')
    parser.add_argument('--revision', '-r', help='Target revision (for migrate/downgrade commands)')
    parser.add_argument('--file', '-f', help='File path (for backup/restore commands)')
    parser.add_argument('--autogenerate', action='store_true', help='Auto-generate migration (for create command)')

    args = parser.parse_args()

    db_manager = DatabaseManager()

    try:
        if args.command == 'migrate':
            revision = args.revision or 'head'
            sys.exit(db_manager.migrate(revision))

        elif args.command == 'init':
            asyncio.run(db_manager.init_database())

        elif args.command == 'validate':
            success = asyncio.run(db_manager.validate_schema())
            sys.exit(0 if success else 1)

        elif args.command == 'backup':
            sys.exit(db_manager.backup_database(args.file))

        elif args.command == 'restore':
            if not args.file:
                print("❌ Restore command requires --file argument")
                sys.exit(1)
            sys.exit(db_manager.restore_database(args.file))

        elif args.command == 'current':
            sys.exit(db_manager.show_current_revision())

        elif args.command == 'history':
            sys.exit(db_manager.show_migration_history())

        elif args.command == 'create':
            if not args.message:
                print("❌ Create command requires --message argument")
                sys.exit(1)
            sys.exit(db_manager.create_migration(args.message, args.autogenerate))

        elif args.command == 'downgrade':
            revision = args.revision or '-1'
            sys.exit(db_manager.downgrade(revision))

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
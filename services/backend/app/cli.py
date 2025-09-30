"""
LICS Backend CLI Commands

Command-line interface for database operations, seeding, and management tasks.
"""

import asyncio
import click
from typing import Optional

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import get_logger, setup_logging
from app.core.seeds import DatabaseSeeder

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@click.group()
def cli():
    """LICS Backend CLI - Database and management commands."""
    pass


@cli.group()
def db():
    """Database operations."""
    pass


@db.command()
@click.option('--force', is_flag=True, help='Force recreate existing data')
def seed(force: bool):
    """Seed database with initial data."""
    click.echo("Seeding database with initial data...")

    async def run_seed():
        await init_db()
        seeder = DatabaseSeeder()
        await seeder.seed_all(force=force)
        await close_db()

    try:
        asyncio.run(run_seed())
        click.echo("✅ Database seeding completed successfully!")
    except Exception as e:
        click.echo(f"❌ Database seeding failed: {e}")
        raise click.Abort()


@db.command()
def clean():
    """Clean seed data from database."""
    click.echo("Cleaning seed data from database...")

    if not click.confirm("This will remove all seed data. Continue?"):
        click.echo("Aborted.")
        return

    async def run_clean():
        await init_db()
        seeder = DatabaseSeeder()
        from app.core.database import db_manager
        async with db_manager.get_session() as db:
            await seeder.clean_seed_data(db)
        await close_db()

    try:
        asyncio.run(run_clean())
        click.echo("✅ Seed data cleaned successfully!")
    except Exception as e:
        click.echo(f"❌ Cleaning failed: {e}")
        raise click.Abort()


@db.command()
def check():
    """Check database connection and status."""
    click.echo("Checking database connection...")

    async def run_check():
        await init_db()
        from app.core.database import db_manager
        health = await db_manager.health_check()
        await close_db()
        return health

    try:
        health = asyncio.run(run_check())
        if health.get("status") == "healthy":
            click.echo("✅ Database connection is healthy")
            click.echo(f"   Database: {health.get('database', 'Unknown')}")
            click.echo(f"   Version: {health.get('version', 'Unknown')}")
        else:
            click.echo("❌ Database connection is unhealthy")
            click.echo(f"   Error: {health.get('error', 'Unknown error')}")
    except Exception as e:
        click.echo(f"❌ Database check failed: {e}")
        raise click.Abort()


@cli.group()
def user():
    """User management operations."""
    pass


@user.command()
@click.argument('email')
@click.argument('password')
@click.option('--first-name', prompt=True, help='First name')
@click.option('--last-name', prompt=True, help='Last name')
@click.option('--organization', default='Demo Lab', help='Organization name')
@click.option('--role', default='Researcher', help='Role name')
@click.option('--superuser', is_flag=True, help='Make user a superuser')
def create(email: str, password: str, first_name: str, last_name: str,
           organization: str, role: str, superuser: bool):
    """Create a new user."""
    click.echo(f"Creating user: {email}")

    async def run_create():
        await init_db()

        from app.models.base import Organization
        from app.models.auth import Role
        from sqlalchemy import select

        from app.core.database import db_manager
        async with db_manager.get_session() as db:
            # Get organization
            org_result = await db.execute(
                select(Organization).where(Organization.name == organization)
            )
            org = org_result.scalar_one_or_none()
            if not org:
                raise ValueError(f"Organization '{organization}' not found")

            # Get role
            role_result = await db.execute(
                select(Role).where(Role.name == role)
            )
            role_obj = role_result.scalar_one_or_none()
            if not role_obj:
                raise ValueError(f"Role '{role}' not found")

            # Create user
            from app.core.security import get_password_hash
            from app.models.auth import User

            user = User(
                email=email,
                username=email.split('@')[0],
                first_name=first_name,
                last_name=last_name,
                password_hash=get_password_hash(password),
                organization_id=org.id,
                is_superuser=superuser,
                is_active=True,
                email_verified=True
            )

            user.roles.append(role_obj)
            db.add(user)
            await db.commit()

        await close_db()
        return user

    try:
        user = asyncio.run(run_create())
        click.echo(f"✅ User created successfully!")
        click.echo(f"   ID: {user.id}")
        click.echo(f"   Email: {user.email}")
        click.echo(f"   Superuser: {user.is_superuser}")
    except Exception as e:
        click.echo(f"❌ User creation failed: {e}")
        raise click.Abort()


@user.command()
@click.argument('email')
def activate(email: str):
    """Activate a user account."""
    click.echo(f"Activating user: {email}")

    async def run_activate():
        await init_db()

        from app.models.auth import User
        from sqlalchemy import select

        from app.core.database import db_manager
        async with db_manager.get_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError(f"User '{email}' not found")

            user.is_active = True
            user.is_locked = False
            await db.commit()

        await close_db()
        return user

    try:
        user = asyncio.run(run_activate())
        click.echo(f"✅ User activated successfully!")
        click.echo(f"   Email: {user.email}")
        click.echo(f"   Active: {user.is_active}")
    except Exception as e:
        click.echo(f"❌ User activation failed: {e}")
        raise click.Abort()


@user.command()
@click.argument('email')
def deactivate(email: str):
    """Deactivate a user account."""
    click.echo(f"Deactivating user: {email}")

    if not click.confirm(f"Are you sure you want to deactivate {email}?"):
        click.echo("Aborted.")
        return

    async def run_deactivate():
        await init_db()

        from app.models.auth import User
        from sqlalchemy import select

        from app.core.database import db_manager
        async with db_manager.get_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError(f"User '{email}' not found")

            user.is_active = False
            await db.commit()

        await close_db()
        return user

    try:
        user = asyncio.run(run_deactivate())
        click.echo(f"✅ User deactivated successfully!")
        click.echo(f"   Email: {user.email}")
        click.echo(f"   Active: {user.is_active}")
    except Exception as e:
        click.echo(f"❌ User deactivation failed: {e}")
        raise click.Abort()


@cli.command()
def info():
    """Show application information."""
    click.echo("LICS Backend Information")
    click.echo("=" * 40)
    click.echo(f"App Name: {settings.APP_NAME}")
    click.echo(f"Version: {settings.APP_VERSION}")
    click.echo(f"Environment: {settings.ENVIRONMENT}")
    click.echo(f"Debug Mode: {settings.DEBUG}")
    click.echo(f"Database URL: {settings.DATABASE_URL.replace('password', '***') if 'password' in settings.DATABASE_URL else settings.DATABASE_URL}")
    click.echo(f"Redis URL: {settings.REDIS_URL}")
    click.echo("")
    click.echo("Feature Flags:")
    click.echo(f"  WebSocket: {settings.FEATURE_WEBSOCKET_ENABLED}")
    click.echo(f"  Celery: {settings.FEATURE_CELERY_ENABLED}")
    click.echo(f"  MQTT: {settings.FEATURE_MQTT_ENABLED}")
    click.echo(f"  Video Streaming: {settings.FEATURE_VIDEO_STREAMING_ENABLED}")
    click.echo(f"  ML: {settings.FEATURE_ML_ENABLED}")


if __name__ == '__main__':
    cli()
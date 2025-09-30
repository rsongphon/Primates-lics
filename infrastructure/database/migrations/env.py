"""
LICS Alembic Environment Configuration

This module configures Alembic for database migrations in both online and offline modes.
It supports both synchronous and asynchronous database operations.
"""

import asyncio
import os
from logging.config import fileConfig
from typing import Any, Dict

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

# Load environment variables
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all the models so they are available to Alembic
import sys
sys.path.append('../../services/backend')

try:
    # Import the FastAPI application models
    from app.core.database import Base
    from app.models import *  # Import all models including authentication models

    # Use the FastAPI application's metadata
    target_metadata = Base.metadata
    print(f"Successfully loaded {len(Base.metadata.tables)} tables from FastAPI models")

except ImportError as e:
    print(f"Warning: Could not import FastAPI models: {e}")
    print("Falling back to basic configuration")

    # Fallback to basic configuration
    from sqlalchemy import MetaData
    from sqlalchemy.ext.declarative import declarative_base

    # Create a base class for our models
    Base = declarative_base()
    target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get database URL from environment variables or config."""
    # Check for environment-specific database URLs
    env = os.getenv('ENVIRONMENT', 'development')

    if env == 'development':
        db_url = os.getenv('DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics')
    elif env == 'test':
        db_url = os.getenv('TEST_DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics_test')
    else:
        # Production
        db_url = os.getenv('DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics')

    # For async operations, replace postgresql:// with postgresql+asyncpg://
    if db_url.startswith('postgresql://'):
        async_db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    else:
        async_db_url = db_url

    return async_db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        # Include custom schemas
        include_name=lambda name, type_, parent_names: type_ in ("table", "column")
        and (
            name.startswith("lics_")
            or name in ("alembic_version",)
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = AsyncEngine(
        engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Check if we should run in async mode
    if os.getenv('ALEMBIC_ASYNC', 'false').lower() == 'true':
        asyncio.run(run_async_migrations())
    else:
        # Synchronous mode
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = get_database_url().replace(
            'postgresql+asyncpg://', 'postgresql+psycopg2://'
        )

        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
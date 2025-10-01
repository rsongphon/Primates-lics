"""
LICS Backend Database Configuration

Async database connection management using SQLAlchemy 2.0 with PostgreSQL
and TimescaleDB. Implements connection pooling, health checks, and session
management following Documentation.md Section 6 patterns.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy import event, pool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings
from app.core.logging import get_logger, PerformanceLogger

logger = get_logger(__name__)
perf_logger = PerformanceLogger(logger)

# Define naming convention for database constraints
metadata_naming_convention = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s'
}


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides common functionality and naming conventions for all database models.
    """

    metadata = MetaData(naming_convention=metadata_naming_convention)


class DatabaseManager:
    """
    Database connection and session management.

    Handles async database connections, session lifecycle, health checks,
    and provides utilities for database operations.
    """

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None
        self._health_check_cache: dict = {}
        self._health_check_cache_ttl: int = 60  # seconds

    async def initialize(self, database_url: Optional[str] = None) -> None:
        """
        Initialize database connection and session factory.

        Args:
            database_url: Optional database URL override
        """
        db_url = database_url or settings.get_database_url()

        logger.info(f"Initializing database connection to {self._mask_password(db_url)}")

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            db_url,
            # Connection pool settings
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,  # Validate connections before use
            # Async settings
            echo=settings.DATABASE_ECHO,
            echo_pool=settings.DEBUG,
            # Connection arguments
            connect_args={
                "command_timeout": settings.DATABASE_CONNECT_TIMEOUT,
                "server_settings": {
                    "application_name": f"lics-backend-{settings.ENVIRONMENT}",
                    "jit": "off",  # Disable JIT for connection stability
                },
            },
        )

        # Create session factory
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=True,
        )

        # Set up event listeners
        self._setup_event_listeners()

        # Verify connection
        await self.verify_connection()

        logger.info("Database connection initialized successfully")

    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for monitoring and debugging."""

        @event.listens_for(self.engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set up connection-specific settings."""
            if "sqlite" in str(self.engine.url):
                # SQLite-specific settings
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries in debug mode."""
            if settings.DEBUG and logger.isEnabledFor(logging.DEBUG):
                context._query_start_time = asyncio.get_event_loop().time()

        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query execution time in debug mode."""
            if settings.DEBUG and hasattr(context, '_query_start_time'):
                total = asyncio.get_event_loop().time() - context._query_start_time
                if total > 0.1:  # Log queries taking more than 100ms
                    logger.debug(
                        f"Slow query detected",
                        extra={
                            'query_time_ms': round(total * 1000, 2),
                            'statement': statement[:200] + '...' if len(statement) > 200 else statement
                        }
                    )

    async def verify_connection(self) -> None:
        """
        Verify database connection and TimescaleDB extension.

        Raises:
            Exception: If connection or TimescaleDB verification fails
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        with perf_logger.log_execution_time("database_connection_verification"):
            async with self.engine.begin() as conn:
                # Test basic connectivity
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1

                # Verify PostgreSQL version
                pg_version = await conn.execute(text("SELECT version()"))
                version_info = pg_version.scalar()
                logger.info(f"Connected to PostgreSQL: {version_info}")

                # Verify TimescaleDB extension
                try:
                    timescale_version = await conn.execute(
                        text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
                    )
                    ts_version = timescale_version.scalar()
                    if ts_version:
                        logger.info(f"TimescaleDB extension found: version {ts_version}")
                    else:
                        logger.warning("TimescaleDB extension not found - time-series features will be limited")
                except Exception as e:
                    logger.warning(f"Could not verify TimescaleDB extension: {e}")

                # Test transaction
                await conn.execute(text("SELECT now()"))

    async def get_session(self) -> AsyncSession:
        """
        Get a new database session.

        Returns:
            AsyncSession: New database session

        Raises:
            RuntimeError: If database is not initialized
        """
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.SessionLocal()

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope around a series of operations.

        This is the recommended way to handle database transactions.
        The session will be committed if no exceptions occur, otherwise
        it will be rolled back.

        Usage:
            async with db_manager.session_scope() as session:
                # Perform database operations
                user = await session.get(User, user_id)
                user.name = "New Name"
                # Automatically committed when context exits
        """
        session = await self.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def health_check(self) -> dict:
        """
        Perform comprehensive database health check.

        Returns:
            dict: Health check results with connection status, metrics, and details
        """
        health_data = {
            "status": "unknown",
            "details": {},
            "timestamp": None,
            "response_time_ms": 0
        }

        import time
        start_time = time.time()

        try:
            if not self.engine:
                health_data.update({
                    "status": "unhealthy",
                    "details": {"error": "Database engine not initialized"}
                })
                return health_data

            async with self.engine.begin() as conn:
                # Basic connectivity test
                await conn.execute(text("SELECT 1"))

                # Get connection count
                connection_result = await conn.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                )
                active_connections = connection_result.scalar()

                # Get database size
                size_result = await conn.execute(
                    text("SELECT pg_database_size(current_database())")
                )
                db_size = size_result.scalar()

                # Check TimescaleDB
                timescale_result = await conn.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
                )
                timescale_enabled = bool(timescale_result.scalar())

                # Get pool statistics
                pool_stats = self._get_pool_stats()

                health_data.update({
                    "status": "healthy",
                    "details": {
                        "active_connections": active_connections,
                        "database_size_bytes": db_size,
                        "timescaledb_enabled": timescale_enabled,
                        "pool_stats": pool_stats
                    }
                })

        except Exception as e:
            health_data.update({
                "status": "unhealthy",
                "details": {"error": str(e)}
            })
            logger.error(f"Database health check failed: {e}")

        finally:
            health_data["response_time_ms"] = int((time.time() - start_time) * 1000)
            health_data["timestamp"] = time.time()

        return health_data

    def _get_pool_stats(self) -> dict:
        """Get connection pool statistics."""
        if not self.engine:
            return {}

        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }

    async def close(self) -> None:
        """Close database connections and clean up resources."""
        if self.engine:
            logger.info("Closing database connections")
            await self.engine.dispose()
            self.engine = None
            self.SessionLocal = None

    def _mask_password(self, url: str) -> str:
        """Mask password in database URL for logging."""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)

    async def execute_raw_sql(self, sql: str, parameters: Optional[dict] = None) -> any:
        """
        Execute raw SQL query.

        Args:
            sql: SQL query string
            parameters: Optional query parameters

        Returns:
            Query result
        """
        async with self.session_scope() as session:
            result = await session.execute(text(sql), parameters or {})
            return result

    async def check_table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            bool: True if table exists, False otherwise
        """
        async with self.session_scope() as session:
            result = await session.execute(
                text("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = :table_name)"),
                {"table_name": table_name}
            )
            return result.scalar()

    async def create_timescale_hypertable(self, table_name: str, time_column: str = "created_at") -> bool:
        """
        Convert a table to TimescaleDB hypertable.

        Args:
            table_name: Name of the table to convert
            time_column: Name of the time column for partitioning

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            async with self.session_scope() as session:
                await session.execute(
                    text(f"SELECT create_hypertable('{table_name}', '{time_column}', if_not_exists => TRUE)")
                )
                logger.info(f"Created TimescaleDB hypertable for table: {table_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to create hypertable for {table_name}: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# FastAPI dependency functions
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.

    Usage:
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_db_session)):
            # Use the session
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with db_manager.session_scope() as session:
        yield session


# Alias for common naming convention
get_db = get_db_session


async def get_db_manager() -> DatabaseManager:
    """
    FastAPI dependency to get database manager.

    Usage:
        @app.get("/health/db")
        async def db_health(db_mgr: DatabaseManager = Depends(get_db_manager)):
            return await db_mgr.health_check()
    """
    return db_manager


# Initialization and cleanup functions
async def init_db() -> None:
    """Initialize database connection."""
    await db_manager.initialize()


async def close_db() -> None:
    """Close database connections."""
    await db_manager.close()


# Utility functions for testing
async def create_test_engine(database_url: str) -> AsyncEngine:
    """
    Create a test database engine with appropriate settings.

    Args:
        database_url: Test database URL

    Returns:
        AsyncEngine: Test database engine
    """
    return create_async_engine(
        database_url,
        poolclass=StaticPool,
        echo=True,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
    )


async def reset_database(engine: AsyncEngine) -> None:
    """
    Reset database for testing (drops all tables).

    Args:
        engine: Database engine

    Warning:
        This will drop all tables! Only use in testing.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
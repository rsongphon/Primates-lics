"""
Request-Scoped Database Session Management

Provides a single database session for the entire HTTP request lifecycle
using contextvars for thread-safe storage.

Architecture:
    1. DatabaseSessionMiddleware creates session at request start
    2. Session stored in contextvar (thread-safe)
    3. All dependencies/services use same session
    4. Middleware commits/rollbacks at request end

Usage:
    # In dependency:
    session = get_request_session()

    # In service:
    def my_service(session: AsyncSession):
        # Use the provided session
        ...
"""

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_manager
from app.core.logging import get_logger

logger = get_logger(__name__)

# Thread-safe storage for request-scoped session
# Each async context (request) gets its own session
_request_session: ContextVar[Optional[AsyncSession]] = ContextVar(
    "request_session",
    default=None
)


class RequestSessionManager:
    """
    Manages request-scoped database sessions.

    Ensures only one database session exists per HTTP request,
    following the Unit of Work pattern.

    Benefits:
    - Single database connection per request
    - Clear transaction boundaries
    - Automatic commit/rollback
    - Thread-safe (uses contextvars)
    """

    @staticmethod
    def get_current_session() -> Optional[AsyncSession]:
        """
        Get the current request-scoped session.

        Returns:
            AsyncSession if one exists for current request, None otherwise
        """
        return _request_session.get()

    @staticmethod
    def set_session(session: AsyncSession) -> None:
        """
        Set the session for current request.

        Args:
            session: Database session to use for this request
        """
        _request_session.set(session)

    @staticmethod
    def clear_session() -> None:
        """
        Clear the current request session.

        Should be called after session is closed.
        """
        _request_session.set(None)

    @staticmethod
    @asynccontextmanager
    async def session_scope() -> AsyncGenerator[AsyncSession, None]:
        """
        Provide request-scoped database session with automatic lifecycle.

        This should be used by middleware to create and manage the
        single session for the entire request.

        Lifecycle:
        1. Create session
        2. Set in contextvar
        3. Yield to request handler
        4. Commit if successful
        5. Rollback if error
        6. Close session
        7. Clear contextvar

        Usage (in middleware):
            async with RequestSessionManager.session_scope() as session:
                request.state.db_session = session
                response = await call_next(request)
        """
        session = await db_manager.get_session()
        RequestSessionManager.set_session(session)

        try:
            yield session
            # Commit if no errors occurred
            await session.commit()
            logger.debug("Request session committed successfully")
        except Exception as e:
            # Rollback on any error
            await session.rollback()
            logger.error(
                f"Request session rolled back due to error: {e}",
                extra={"error_type": type(e).__name__}
            )
            raise
        finally:
            # Always close and clear session
            await session.close()
            RequestSessionManager.clear_session()
            logger.debug("Request session closed and cleared")


# Global instance for convenience
request_session_manager = RequestSessionManager()


def get_request_session() -> AsyncSession:
    """
    Get current request session (raises error if not set).

    Use this in dependencies/services that require a session.

    Returns:
        Active request-scoped session

    Raises:
        RuntimeError: If no request session exists (middleware not installed)

    Example:
        # In dependency:
        def my_dependency():
            session = get_request_session()
            # Use session...
    """
    session = request_session_manager.get_current_session()
    if session is None:
        raise RuntimeError(
            "No request session found. "
            "Ensure DatabaseSessionMiddleware is installed in main.py"
        )
    return session

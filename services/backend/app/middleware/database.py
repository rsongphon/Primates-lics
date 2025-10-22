"""
Database Session Middleware

Provides request-scoped database session management, ensuring
a single session exists for the entire request lifecycle.

This middleware:
1. Creates ONE database session at request start
2. Stores it in request.state and contextvar
3. All dependencies/services use this same session
4. Commits on success, rollbacks on error
5. Closes session at request end

Benefits:
- Single connection per request (reduced pool usage)
- Clear transaction boundaries
- Automatic cleanup
- Better performance
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.core.session import RequestSessionManager

logger = get_logger(__name__)


class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to provide request-scoped database session.

    Creates a single database session at the start of each request
    and commits/rollbacks at the end. The session is accessible
    via request.state.db_session or get_request_session().

    Installation (in main.py):
        app.add_middleware(DatabaseSessionMiddleware)
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.session_manager = RequestSessionManager()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Create and manage database session for request.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        session_start = time.time()

        # Create session for entire request lifecycle
        async with self.session_manager.session_scope() as session:
            # Store session in request state for backward compatibility
            request.state.db_session = session

            # Process request (all handlers use same session)
            response = await call_next(request)

            # Log session metrics
            session_duration = (time.time() - session_start) * 1000
            logger.debug(
                "Request session completed",
                extra={
                    "session_duration_ms": round(session_duration, 2),
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code
                }
            )

        return response

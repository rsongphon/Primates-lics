"""
Authentication Middleware

JWT-based authentication middleware for FastAPI with comprehensive
security features and performance optimization.
"""

import time
from typing import Optional, Set
from urllib.parse import unquote

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import verify_token, ACCESS_TOKEN_TYPE
from app.models.auth import User
from app.services.auth import AuthService

logger = get_logger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication Middleware

    Handles JWT token validation and user authentication for protected routes.
    Supports multiple token types and provides comprehensive security features.
    """

    # Routes that don't require authentication
    PUBLIC_ROUTES: Set[str] = {
        "/",
        "/health",
        "/ready",
        "/live",
        "/info",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/password/reset/request",
        "/api/v1/auth/password/reset/confirm",
        "/api/v1/auth/verify-email",
        "/api/v1/health/basic",
        "/api/v1/health/detailed"
    }

    # Routes that support optional authentication (enhanced features if authenticated)
    OPTIONAL_AUTH_ROUTES: Set[str] = {
        "/api/v1/health/detailed",
        "/api/v1/public/experiments",
        "/api/v1/public/templates"
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.auth_service = AuthService()

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process authentication for incoming requests.
        """
        start_time = time.time()

        # Get the request path
        path = unquote(request.url.path)
        method = request.method

        # Skip authentication for public routes
        if self._is_public_route(path, method):
            return await call_next(request)

        # Check if route supports optional authentication
        optional_auth = path in self.OPTIONAL_AUTH_ROUTES

        try:
            # Extract token from request
            token = self._extract_token(request)

            if not token:
                if optional_auth:
                    # Continue without authentication for optional routes
                    request.state.user = None
                    request.state.authenticated = False
                    return await call_next(request)
                else:
                    return self._create_auth_error_response(
                        "Missing authentication token",
                        "TOKEN_MISSING",
                        request
                    )

            # Verify and decode token
            try:
                payload = verify_token(token, ACCESS_TOKEN_TYPE)
            except Exception as e:
                if optional_auth:
                    # Continue without authentication for optional routes
                    request.state.user = None
                    request.state.authenticated = False
                    return await call_next(request)
                else:
                    return self._create_auth_error_response(
                        f"Invalid token: {str(e)}",
                        "TOKEN_INVALID",
                        request
                    )

            # Check if token is blacklisted
            if await self.auth_service.is_token_blacklisted(token):
                return self._create_auth_error_response(
                    "Token has been revoked",
                    "TOKEN_REVOKED",
                    request
                )

            # Get user from token payload
            user_id = payload.get("sub")
            if not user_id:
                return self._create_auth_error_response(
                    "Invalid token payload",
                    "TOKEN_INVALID_PAYLOAD",
                    request
                )

            # Load user from database
            user = await self.auth_service.get_user_by_id(user_id)
            if not user:
                return self._create_auth_error_response(
                    "User not found",
                    "USER_NOT_FOUND",
                    request
                )

            # Check if user is active
            if not user.is_active:
                return self._create_auth_error_response(
                    "User account is disabled",
                    "USER_DISABLED",
                    request
                )

            # Check if user is locked
            if user.is_locked:
                return self._create_auth_error_response(
                    "User account is locked",
                    "USER_LOCKED",
                    request
                )

            # Check if email is verified (for certain operations)
            if not user.email_verified and self._requires_verified_email(path):
                return self._create_auth_error_response(
                    "Email verification required",
                    "EMAIL_NOT_VERIFIED",
                    request
                )

            # Store user in request state
            request.state.user = user
            request.state.authenticated = True
            request.state.token_payload = payload

            # Update user's last activity
            await self.auth_service.update_user_activity(user_id, request)

            # Log authentication success (for security monitoring)
            auth_time = (time.time() - start_time) * 1000
            logger.debug(
                f"Authentication successful for user {user.email}",
                extra={
                    "user_id": str(user.id),
                    "user_email": user.email,
                    "organization_id": str(user.organization_id) if user.organization_id else None,
                    "auth_time_ms": round(auth_time, 2),
                    "path": path,
                    "method": method,
                    "ip_address": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent", "")
                }
            )

        except Exception as e:
            logger.error(
                f"Authentication middleware error: {e}",
                extra={
                    "path": path,
                    "method": method,
                    "error_type": type(e).__name__,
                    "correlation_id": getattr(request.state, "correlation_id", "unknown")
                }
            )

            if optional_auth:
                # Continue without authentication for optional routes
                request.state.user = None
                request.state.authenticated = False
                return await call_next(request)
            else:
                return self._create_auth_error_response(
                    "Authentication failed",
                    "AUTH_ERROR",
                    request
                )

        return await call_next(request)

    def _is_public_route(self, path: str, method: str) -> bool:
        """
        Check if the route is public and doesn't require authentication.
        """
        # Check exact matches
        if path in self.PUBLIC_ROUTES:
            return True

        # Check pattern matches for documentation routes
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True

        # OPTIONS requests are always public (CORS preflight)
        if method == "OPTIONS":
            return True

        return False

    def _requires_verified_email(self, path: str) -> bool:
        """
        Check if the route requires email verification.
        """
        # Routes that require verified email
        sensitive_routes = {
            "/api/v1/devices",
            "/api/v1/experiments",
            "/api/v1/tasks",
            "/api/v1/organizations",
            "/api/v1/auth/password/change"
        }

        # Check if path starts with any sensitive route
        return any(path.startswith(route) for route in sensitive_routes)

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request headers or cookies.
        """
        # Try Authorization header first (Bearer token)
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]  # Remove "Bearer " prefix

        # Try API key header (for device authentication)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # Try cookie (for web authentication)
        token = request.cookies.get(settings.JWT_COOKIE_NAME)
        if token:
            return token

        return None

    def _create_auth_error_response(
        self,
        message: str,
        error_code: str,
        request: Request
    ) -> JSONResponse:
        """
        Create standardized authentication error response.
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log authentication failure
        logger.warning(
            f"Authentication failed: {message}",
            extra={
                "error_code": error_code,
                "path": request.url.path,
                "method": request.method,
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", ""),
                "correlation_id": correlation_id
            }
        )

        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "trace_id": correlation_id
                }
            },
            headers={
                "X-Correlation-ID": correlation_id,
                "WWW-Authenticate": 'Bearer realm="LICS API"'
            }
        )
"""
Security Headers Middleware

Implements comprehensive security headers for web application protection
including HSTS, CSP, XSS protection, and other security measures.
"""

from typing import Dict, Optional
from urllib.parse import unquote

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security Headers Middleware

    Adds comprehensive security headers to all responses to protect
    against common web vulnerabilities and attacks.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Add security headers to all responses.
        """
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(request, response)

        return response

    def _add_security_headers(self, request: Request, response: Response):
        """
        Add comprehensive security headers to response.
        """
        path = unquote(request.url.path)

        # Content Security Policy (CSP)
        csp = self._get_content_security_policy(path)
        if csp:
            response.headers["Content-Security-Policy"] = csp

        # HTTP Strict Transport Security (HSTS)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (Feature Policy)
        permissions_policy = self._get_permissions_policy()
        if permissions_policy:
            response.headers["Permissions-Policy"] = permissions_policy

        # Cross-Origin Policies
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Cache Control for sensitive endpoints
        if self._is_sensitive_endpoint(path):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Remove server information headers
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        # Add custom security headers
        response.headers["X-API-Version"] = settings.APP_VERSION
        response.headers["X-Content-Type-Options"] = "nosniff"

        # CSRF protection hint
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            response.headers["X-CSRF-Protection"] = "1"

    def _get_content_security_policy(self, path: str) -> Optional[str]:
        """
        Generate Content Security Policy based on the endpoint.
        """
        # Base CSP policy
        csp_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Relaxed for dev tools
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "media-src 'self'",
            "object-src 'none'",
            "child-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]

        # Allow additional sources for API documentation
        if path.startswith("/docs") or path.startswith("/redoc"):
            csp_parts.extend([
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' fonts.googleapis.com cdn.jsdelivr.net",
                "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net"
            ])

        # WebSocket connections
        if settings.FEATURE_WEBSOCKET_ENABLED:
            if settings.ENVIRONMENT == "development":
                csp_parts.append("connect-src 'self' ws: wss: localhost:* 127.0.0.1:*")
            else:
                csp_parts.append("connect-src 'self' wss:")

        return "; ".join(csp_parts)

    def _get_permissions_policy(self) -> str:
        """
        Generate Permissions Policy to restrict browser features.
        """
        # Disable most features by default, only allow what's needed
        policies = [
            "accelerometer=()",
            "ambient-light-sensor=()",
            "autoplay=()",
            "battery=()",
            "camera=(self)",  # Allow camera for video streaming
            "cross-origin-isolated=()",
            "display-capture=()",
            "document-domain=()",
            "encrypted-media=()",
            "execution-while-not-rendered=()",
            "execution-while-out-of-viewport=()",
            "fullscreen=(self)",
            "geolocation=()",
            "gyroscope=()",
            "keyboard-map=()",
            "magnetometer=()",
            "microphone=(self)",  # Allow microphone for audio recording
            "midi=()",
            "navigation-override=()",
            "payment=()",
            "picture-in-picture=()",
            "publickey-credentials-get=(self)",
            "screen-wake-lock=()",
            "sync-xhr=()",
            "usb=()",
            "web-share=()",
            "xr-spatial-tracking=()"
        ]

        return ", ".join(policies)

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """
        Check if endpoint contains sensitive data that shouldn't be cached.
        """
        sensitive_patterns = [
            "/api/v1/auth/",
            "/api/v1/users/",
            "/api/v1/organizations/",
            "/api/v1/rbac/",
            "/api/v1/devices/",
            "/api/v1/experiments/",
            "/api/v1/tasks/"
        ]

        return any(path.startswith(pattern) for pattern in sensitive_patterns)


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """
    Security Audit Middleware

    Logs security-relevant events for monitoring and compliance.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Log security events and suspicious activities.
        """
        # Check for suspicious patterns
        self._check_suspicious_activity(request)

        response = await call_next(request)

        # Log security events
        self._log_security_events(request, response)

        return response

    def _check_suspicious_activity(self, request: Request):
        """
        Check for patterns that might indicate malicious activity.
        """
        path = unquote(request.url.path)
        query_params = str(request.query_params)
        user_agent = request.headers.get("user-agent", "")

        suspicious_patterns = [
            # SQL injection attempts
            "union select", "drop table", "insert into", "delete from",
            # XSS attempts
            "<script", "javascript:", "onerror=", "onload=",
            # Path traversal
            "../", "..\\", "%2e%2e%2f", "%2e%2e%5c",
            # Command injection
            "; cat", "| cat", "&& cat", "$(", "`",
            # File inclusion
            "file://", "ftp://", "data:",
        ]

        content = f"{path} {query_params}".lower()

        for pattern in suspicious_patterns:
            if pattern in content:
                logger.warning(
                    f"Suspicious activity detected: {pattern}",
                    extra={
                        "security_event": "suspicious_pattern",
                        "pattern": pattern,
                        "path": path,
                        "query_params": query_params,
                        "user_agent": user_agent,
                        "client_ip": request.client.host if request.client else None,
                        "method": request.method
                    }
                )

        # Check for unusual user agents
        bot_patterns = ["bot", "crawler", "spider", "scraper", "scanner"]
        if any(pattern in user_agent.lower() for pattern in bot_patterns):
            logger.info(
                f"Bot/crawler detected: {user_agent}",
                extra={
                    "security_event": "bot_detected",
                    "user_agent": user_agent,
                    "path": path,
                    "client_ip": request.client.host if request.client else None
                }
            )

    def _log_security_events(self, request: Request, response: Response):
        """
        Log security-relevant events based on response status.
        """
        status_code = response.status_code
        path = unquote(request.url.path)

        # Log authentication failures
        if status_code == 401:
            logger.warning(
                "Authentication failure",
                extra={
                    "security_event": "auth_failure",
                    "path": path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent", "")
                }
            )

        # Log authorization failures
        elif status_code == 403:
            user = getattr(request.state, "user", None)
            logger.warning(
                "Authorization failure",
                extra={
                    "security_event": "authz_failure",
                    "path": path,
                    "method": request.method,
                    "user_id": str(user.id) if user else None,
                    "client_ip": request.client.host if request.client else None
                }
            )

        # Log rate limiting
        elif status_code == 429:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "security_event": "rate_limit",
                    "path": path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else None
                }
            )
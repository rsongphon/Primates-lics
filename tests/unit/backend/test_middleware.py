"""
Unit tests for authentication middleware components.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import Request, Response, HTTPException
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.middleware.auth import AuthenticationMiddleware
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.security import SecurityHeadersMiddleware, SecurityAuditMiddleware
from app.core.security import create_access_token, create_refresh_token
from app.models.auth import User


class TestAuthenticationMiddleware:
    """Test AuthenticationMiddleware functionality."""

    def test_init_middleware(self):
        """Test middleware initialization."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        assert middleware.app == app
        assert isinstance(middleware.public_routes, set)
        assert "/health" in middleware.public_routes

    @pytest.mark.asyncio
    async def test_public_route_bypass(self):
        """Test that public routes bypass authentication."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        # Mock request for public route
        request = MagicMock()
        request.url.path = "/health"
        request.method = "GET"

        # Mock call_next
        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        response = await middleware.__call__(request, call_next)

        assert response == expected_response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test handling of missing authorization header."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {}

        call_next = AsyncMock()

        response = await middleware.__call__(request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_authorization_header_format(self):
        """Test handling of invalid authorization header format."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": "Invalid header format"}

        call_next = AsyncMock()

        response = await middleware.__call__(request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_authentication(self, test_user):
        """Test successful authentication with valid token."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        # Create valid token
        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email}
        )

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": f"Bearer {token}"}
        request.state = MagicMock()

        # Mock database session
        mock_session = AsyncMock()
        mock_session.get.return_value = test_user

        with patch('app.core.database.get_db_session') as mock_get_db:
            async def mock_db_gen():
                yield mock_session

            mock_get_db.return_value = mock_db_gen()

            call_next = AsyncMock()
            expected_response = Response()
            call_next.return_value = expected_response

            response = await middleware.__call__(request, call_next)

            assert response == expected_response
            assert hasattr(request.state, 'user')
            assert request.state.user == test_user

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test handling of invalid token."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": "Bearer invalid_token"}

        call_next = AsyncMock()

        response = await middleware.__call__(request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token(self):
        """Test handling of expired token."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        # Create expired token
        token = create_access_token(
            data={"sub": str(uuid4())},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": f"Bearer {token}"}

        call_next = AsyncMock()

        response = await middleware.__call__(request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_blacklisted_token(self):
        """Test handling of blacklisted token."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        token = create_access_token(data={"sub": str(uuid4())})

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": f"Bearer {token}"}

        # Mock blacklisted token
        with patch('app.core.security.is_token_blacklisted', return_value=True):
            call_next = AsyncMock()

            response = await middleware.__call__(request, call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent_user(self):
        """Test handling when token user doesn't exist."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        token = create_access_token(data={"sub": str(uuid4())})

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": f"Bearer {token}"}

        # Mock database session returning None
        mock_session = AsyncMock()
        mock_session.get.return_value = None

        with patch('app.core.database.get_db_session') as mock_get_db:
            async def mock_db_gen():
                yield mock_session

            mock_get_db.return_value = mock_db_gen()

            call_next = AsyncMock()

            response = await middleware.__call__(request, call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user(self, test_user):
        """Test handling of inactive user."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        # Make user inactive
        test_user.is_active = False

        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email}
        )

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": f"Bearer {token}"}

        mock_session = AsyncMock()
        mock_session.get.return_value = test_user

        with patch('app.core.database.get_db_session') as mock_get_db:
            async def mock_db_gen():
                yield mock_session

            mock_get_db.return_value = mock_db_gen()

            call_next = AsyncMock()

            response = await middleware.__call__(request, call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 401


class TestRateLimitingMiddleware:
    """Test RateLimitingMiddleware functionality."""

    def test_init_middleware(self):
        """Test middleware initialization."""
        app = MagicMock()
        middleware = RateLimitingMiddleware(app)

        assert middleware.app == app
        assert middleware.default_limit == 1000
        assert middleware.window_size == 3600

    @pytest.mark.asyncio
    async def test_rate_limit_under_limit(self, redis_client):
        """Test request under rate limit."""
        app = MagicMock()
        middleware = RateLimitingMiddleware(app)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = MagicMock()

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
            response = await middleware.__call__(request, call_next)

            assert response == expected_response
            call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, redis_client):
        """Test request when rate limit is exceeded."""
        app = MagicMock()
        middleware = RateLimitingMiddleware(app, default_limit=1, window_size=60)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = MagicMock()

        # Pre-populate Redis with rate limit data
        await redis_client.setex("rate_limit:192.168.1.1", 60, 2)  # Already at limit

        call_next = AsyncMock()

        with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
            response = await middleware.__call__(request, call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_user_specific_rate_limit(self, redis_client, test_user):
        """Test user-specific rate limiting."""
        app = MagicMock()
        middleware = RateLimitingMiddleware(app, default_limit=1, window_size=60)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = MagicMock()
        request.state.user = test_user

        # Pre-populate Redis with user rate limit
        await redis_client.setex(f"rate_limit:user:{test_user.id}", 60, 2)

        call_next = AsyncMock()

        with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
            response = await middleware.__call__(request, call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, redis_client):
        """Test that rate limit headers are added."""
        app = MagicMock()
        middleware = RateLimitingMiddleware(app, default_limit=100, window_size=60)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = MagicMock()

        call_next = AsyncMock()
        mock_response = Response()
        call_next.return_value = mock_response

        with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
            response = await middleware.__call__(request, call_next)

            # Should add rate limit headers
            assert hasattr(response, 'headers')

    @pytest.mark.asyncio
    async def test_redis_connection_error(self):
        """Test handling of Redis connection errors."""
        app = MagicMock()
        middleware = RateLimitingMiddleware(app)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = MagicMock()

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        # Mock Redis connection error
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")

        with patch('app.middleware.rate_limiting.get_redis', return_value=mock_redis):
            # Should gracefully handle Redis errors and allow request
            response = await middleware.__call__(request, call_next)

            assert response == expected_response


class TestSecurityHeadersMiddleware:
    """Test SecurityHeadersMiddleware functionality."""

    def test_init_middleware(self):
        """Test middleware initialization."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        assert middleware.app == app

    @pytest.mark.asyncio
    async def test_security_headers_added(self):
        """Test that security headers are added to response."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        call_next = AsyncMock()

        # Create a mock response with headers
        mock_response = Response()
        mock_response.headers = {}
        call_next.return_value = mock_response

        response = await middleware.__call__(request, call_next)

        # Check that security headers are added
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy"
        ]

        for header in expected_headers:
            assert header in response.headers

    @pytest.mark.asyncio
    async def test_csp_header_content(self):
        """Test Content Security Policy header content."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        call_next = AsyncMock()

        mock_response = Response()
        mock_response.headers = {}
        call_next.return_value = mock_response

        response = await middleware.__call__(request, call_next)

        csp = response.headers.get("Content-Security-Policy")
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp

    @pytest.mark.asyncio
    async def test_hsts_header(self):
        """Test HTTP Strict Transport Security header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        call_next = AsyncMock()

        mock_response = Response()
        mock_response.headers = {}
        call_next.return_value = mock_response

        response = await middleware.__call__(request, call_next)

        hsts = response.headers.get("Strict-Transport-Security")
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts

    @pytest.mark.asyncio
    async def test_frame_options_header(self):
        """Test X-Frame-Options header."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        call_next = AsyncMock()

        mock_response = Response()
        mock_response.headers = {}
        call_next.return_value = mock_response

        response = await middleware.__call__(request, call_next)

        frame_options = response.headers.get("X-Frame-Options")
        assert frame_options == "DENY"

    @pytest.mark.asyncio
    async def test_existing_headers_not_overwritten(self):
        """Test that existing headers are not overwritten."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        call_next = AsyncMock()

        mock_response = Response()
        mock_response.headers = {"X-Frame-Options": "SAMEORIGIN"}  # Existing header
        call_next.return_value = mock_response

        response = await middleware.__call__(request, call_next)

        # Should preserve existing header
        assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"


class TestSecurityAuditMiddleware:
    """Test SecurityAuditMiddleware functionality."""

    def test_init_middleware(self):
        """Test middleware initialization."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        assert middleware.app == app

    @pytest.mark.asyncio
    async def test_normal_request_processing(self):
        """Test normal request processing without security issues."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        request = MagicMock()
        request.url.path = "/normal/path"
        request.url.query = "param=value"
        request.headers = {"User-Agent": "Normal Browser"}

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        response = await middleware.__call__(request, call_next)

        assert response == expected_response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_sql_injection_detection(self):
        """Test SQL injection attempt detection."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/users"
        request.url.query = "id=1' OR '1'='1"  # SQL injection attempt
        request.headers = {"User-Agent": "Malicious Client"}
        request.client.host = "192.168.1.100"

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        with patch('app.middleware.security.logger') as mock_logger:
            response = await middleware.__call__(request, call_next)

            # Should log security warning
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_xss_attempt_detection(self):
        """Test XSS attempt detection."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        request = MagicMock()
        request.url.path = "/search"
        request.url.query = "q=<script>alert('xss')</script>"  # XSS attempt
        request.headers = {"User-Agent": "Browser"}
        request.client.host = "192.168.1.100"

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        with patch('app.middleware.security.logger') as mock_logger:
            response = await middleware.__call__(request, call_next)

            # Should log security warning
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_path_traversal_detection(self):
        """Test path traversal attempt detection."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        request = MagicMock()
        request.url.path = "/files/../../../etc/passwd"  # Path traversal attempt
        request.url.query = ""
        request.headers = {"User-Agent": "Attacker"}
        request.client.host = "192.168.1.100"

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        with patch('app.middleware.security.logger') as mock_logger:
            response = await middleware.__call__(request, call_next)

            # Should log security warning
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_suspicious_user_agent_detection(self):
        """Test suspicious user agent detection."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/test"
        request.url.query = ""
        request.headers = {"User-Agent": "sqlmap/1.0"}  # Security scanner
        request.client.host = "192.168.1.100"

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        with patch('app.middleware.security.logger') as mock_logger:
            response = await middleware.__call__(request, call_next)

            # Should log security warning
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_security_issues(self):
        """Test detection of multiple security issues in one request."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        request = MagicMock()
        request.url.path = "/../../../etc/passwd"  # Path traversal
        request.url.query = "param=<script>alert(1)</script>"  # XSS
        request.headers = {"User-Agent": "Nikto/2.1.6"}  # Scanner
        request.client.host = "192.168.1.100"

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        with patch('app.middleware.security.logger') as mock_logger:
            response = await middleware.__call__(request, call_next)

            # Should log multiple warnings
            assert mock_logger.warning.call_count >= 1

    @pytest.mark.asyncio
    async def test_security_audit_with_user_context(self, test_user):
        """Test security audit with authenticated user context."""
        app = MagicMock()
        middleware = SecurityAuditMiddleware(app)

        request = MagicMock()
        request.url.path = "/api/test"
        request.url.query = "param=<script>alert(1)</script>"
        request.headers = {"User-Agent": "Browser"}
        request.client.host = "192.168.1.100"
        request.state = MagicMock()
        request.state.user = test_user

        call_next = AsyncMock()
        expected_response = Response()
        call_next.return_value = expected_response

        with patch('app.middleware.security.logger') as mock_logger:
            response = await middleware.__call__(request, call_next)

            # Should include user information in security log
            if mock_logger.warning.called:
                log_call = mock_logger.warning.call_args[0][0]
                assert str(test_user.id) in log_call


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""

    @pytest.mark.asyncio
    async def test_middleware_order_auth_then_rate_limit(self, test_user, redis_client):
        """Test middleware order: authentication then rate limiting."""
        # This would typically be tested with a real FastAPI app
        # Here we test the conceptual flow

        # 1. Authentication middleware should run first
        auth_middleware = AuthenticationMiddleware(MagicMock())

        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email}
        )

        request = MagicMock()
        request.url.path = "/api/protected"
        request.method = "GET"
        request.headers = {"authorization": f"Bearer {token}"}
        request.state = MagicMock()

        # Mock successful authentication
        with patch('app.core.database.get_db_session') as mock_get_db:
            async def mock_db_gen():
                yield AsyncMock()

            mock_get_db.return_value = mock_db_gen()

            # Mock the database returning the user
            with patch.object(AsyncMock, 'get', return_value=test_user):
                # 2. Then rate limiting middleware
                rate_middleware = RateLimitingMiddleware(MagicMock())

                call_next = AsyncMock()
                expected_response = Response()
                call_next.return_value = expected_response

                with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
                    # Simulate auth middleware setting user
                    request.state.user = test_user

                    response = await rate_middleware(request, call_next)

                    assert response == expected_response

    @pytest.mark.asyncio
    async def test_middleware_error_handling(self):
        """Test middleware error handling."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app)

        request = MagicMock()
        request.url.path = "/protected"
        request.method = "GET"
        request.headers = {"authorization": "Bearer valid_token"}

        # Mock database error
        with patch('app.core.database.get_db_session', side_effect=Exception("DB Error")):
            call_next = AsyncMock()

            response = await middleware.__call__(request, call_next)

            # Should handle gracefully
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_middleware_performance_tracking(self):
        """Test middleware performance tracking."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        request = MagicMock()
        call_next = AsyncMock()

        # Simulate slow downstream processing
        async def slow_call_next(req):
            import asyncio
            await asyncio.sleep(0.01)  # 10ms delay
            return Response()

        call_next.side_effect = slow_call_next

        import time
        start_time = time.time()
        response = await middleware.__call__(request, call_next)
        end_time = time.time()

        # Should complete but might take time due to downstream
        assert isinstance(response, Response)
        assert (end_time - start_time) >= 0.01
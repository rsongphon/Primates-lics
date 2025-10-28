"""
Security vulnerability tests for the authentication system.
Tests for common security issues like injection attacks, XSS, CSRF, etc.
"""

import pytest
import time
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from httpx import AsyncClient
from fastapi import status

from app.core.security import create_access_token, create_refresh_token
from tests.conftest import create_test_user_data


class TestSQLInjectionProtection:
    """Test protection against SQL injection attacks."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_login(self, async_client: AsyncClient):
        """Test SQL injection attempts in login endpoint."""
        sql_injection_attempts = [
            "admin@example.com' OR '1'='1",
            "admin@example.com'; DROP TABLE users; --",
            "admin@example.com' UNION SELECT * FROM users --",
            "admin@example.com' AND (SELECT COUNT(*) FROM users) > 0 --"
        ]

        for malicious_email in sql_injection_attempts:
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": malicious_email,
                    "password": "any_password"
                }
            )

            # Should return 401 (invalid credentials) or 422 (validation error)
            # NOT 500 (server error from SQL injection)
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    @pytest.mark.asyncio
    async def test_sql_injection_in_registration(self, async_client: AsyncClient, test_organization):
        """Test SQL injection attempts in registration endpoint."""
        sql_injection_attempts = [
            "test'; DROP TABLE users; --",
            "test' OR '1'='1",
            "test' UNION SELECT password FROM users --"
        ]

        for malicious_input in sql_injection_attempts:
            user_data = create_test_user_data(
                username=malicious_input,
                email=f"{malicious_input}@example.com"
            )

            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    **user_data,
                    "organization_id": str(test_organization.id)
                }
            )

            # Should handle gracefully (validation error or success)
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]

    @pytest.mark.asyncio
    async def test_sql_injection_in_profile_update(self, async_client: AsyncClient, auth_headers):
        """Test SQL injection attempts in profile update."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM permissions --"
        ]

        for malicious_input in malicious_inputs:
            response = await async_client.put(
                "/api/v1/auth/profile",
                headers=auth_headers,
                json={
                    "first_name": malicious_input,
                    "last_name": malicious_input
                }
            )

            # Should handle gracefully
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]


class TestXSSProtection:
    """Test protection against Cross-Site Scripting (XSS) attacks."""

    @pytest.mark.asyncio
    async def test_xss_in_user_registration(self, async_client: AsyncClient, test_organization):
        """Test XSS payload handling in user registration."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>",
            "&#60;script&#62;alert('xss')&#60;/script&#62;"
        ]

        for xss_payload in xss_payloads:
            user_data = create_test_user_data(
                first_name=xss_payload,
                last_name=xss_payload
            )

            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    **user_data,
                    "organization_id": str(test_organization.id)
                }
            )

            if response.status_code == status.HTTP_201_CREATED:
                data = response.json()
                # XSS payload should be escaped or sanitized
                assert xss_payload not in str(data)
                # Basic HTML entities should be encoded
                if "<script>" in xss_payload:
                    assert "<script>" not in data.get("first_name", "")

    @pytest.mark.asyncio
    async def test_xss_in_profile_response(self, async_client: AsyncClient, auth_headers):
        """Test that XSS payloads in profile data are properly escaped."""
        xss_payload = "<script>alert('profile_xss')</script>"

        # Update profile with XSS payload
        update_response = await async_client.put(
            "/api/v1/auth/profile",
            headers=auth_headers,
            json={
                "first_name": xss_payload
            }
        )

        if update_response.status_code == status.HTTP_200_OK:
            # Get profile and check response
            get_response = await async_client.get(
                "/api/v1/auth/profile",
                headers=auth_headers
            )

            assert get_response.status_code == status.HTTP_200_OK
            data = get_response.json()

            # Script tags should be escaped or removed
            assert "<script>" not in data.get("first_name", "")

    @pytest.mark.asyncio
    async def test_content_type_headers(self, async_client: AsyncClient):
        """Test that proper content-type headers are set to prevent XSS."""
        response = await async_client.get("/api/v1/auth/me")

        # Should have proper content-type
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

        # Should have XSS protection headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"


class TestCSRFProtection:
    """Test Cross-Site Request Forgery (CSRF) protection."""

    @pytest.mark.asyncio
    async def test_state_changing_operations_require_authentication(self, async_client: AsyncClient):
        """Test that state-changing operations require proper authentication."""
        # Attempt to change password without authentication
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "old_pass",
                "new_password": "new_pass",
                "confirm_password": "new_pass"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_csrf_token_validation(self, async_client: AsyncClient, auth_headers):
        """Test CSRF token validation for sensitive operations."""
        # This test assumes CSRF protection is implemented
        # Adjust based on actual implementation

        response = await async_client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!"
            }
        )

        # Should work with proper authentication
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST  # If current password is wrong
        ]

    @pytest.mark.asyncio
    async def test_same_site_cookie_attributes(self, async_client: AsyncClient, test_user):
        """Test that authentication cookies have proper SameSite attributes."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == status.HTTP_200_OK

        # Check cookie security attributes if cookies are used
        set_cookie_headers = response.headers.get_list("set-cookie")
        for cookie in set_cookie_headers:
            if "refresh_token" in cookie or "session" in cookie:
                assert "SameSite=" in cookie
                assert "HttpOnly" in cookie


class TestJWTSecurityFlaws:
    """Test JWT-specific security vulnerabilities."""

    @pytest.mark.asyncio
    async def test_jwt_algorithm_confusion(self, async_client: AsyncClient):
        """Test protection against JWT algorithm confusion attacks."""
        # Try to use 'none' algorithm
        import jwt as jose_jwt

        payload = {
            "sub": str(uuid4()),
            "email": "attacker@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }

        # Create token with 'none' algorithm
        malicious_token = jose_jwt.encode(payload, "", algorithm="none")

        response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {malicious_token}"}
        )

        # Should reject token with 'none' algorithm
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_jwt_weak_secret_protection(self):
        """Test that JWT uses strong secret keys."""
        from app.core.config import settings

        # JWT secret should be long and complex
        assert len(settings.JWT_SECRET_KEY) >= 32

        # Should not be default or common values
        weak_secrets = [
            "secret",
            "password",
            "123456",
            "your-secret-key",
            "change-me"
        ]

        assert settings.JWT_SECRET_KEY.lower() not in weak_secrets

    @pytest.mark.asyncio
    async def test_jwt_token_replay_protection(self, async_client: AsyncClient, test_user, redis_client):
        """Test protection against JWT token replay attacks."""
        # Login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()

        # Use token
        profile_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert profile_response.status_code == status.HTTP_200_OK

        # Logout (should blacklist token)
        with patch('app.core.database.get_redis', return_value=redis_client):
            logout_response = await async_client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            assert logout_response.status_code == status.HTTP_200_OK

        # Try to use token again (should fail)
        replay_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert replay_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_jwt_timing_attack_resistance(self, async_client: AsyncClient):
        """Test resistance to JWT timing attacks."""
        valid_token = create_access_token(data={"sub": str(uuid4())})
        invalid_token = "invalid.token.here"

        # Measure time for valid token verification
        start_time = time.perf_counter()
        valid_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        valid_time = time.perf_counter() - start_time

        # Measure time for invalid token verification
        start_time = time.perf_counter()
        invalid_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        invalid_time = time.perf_counter() - start_time

        # Times should be similar (within reasonable variance)
        time_ratio = max(valid_time, invalid_time) / min(valid_time, invalid_time)
        assert time_ratio < 5  # Allow some variance but not orders of magnitude


class TestPasswordSecurityFlaws:
    """Test password-related security vulnerabilities."""

    @pytest.mark.asyncio
    async def test_password_brute_force_protection(self, async_client: AsyncClient, test_user, redis_client):
        """Test protection against password brute force attacks."""
        # Attempt multiple failed logins
        with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
            failed_attempts = 0
            for i in range(10):
                response = await async_client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": test_user.email,
                        "password": f"wrong_password_{i}"
                    }
                )

                if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    break  # Rate limiting kicked in
                elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                    failed_attempts += 1

            # Should either rate limit or account lockout should occur
            assert failed_attempts < 10  # Not all attempts should succeed

    @pytest.mark.asyncio
    async def test_password_timing_attack_resistance(self, async_client: AsyncClient, test_user):
        """Test resistance to password timing attacks."""
        # Test with correct email, wrong password
        start_time = time.perf_counter()
        response1 = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrong_password"
            }
        )
        time1 = time.perf_counter() - start_time

        # Test with non-existent email
        start_time = time.perf_counter()
        response2 = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "any_password"
            }
        )
        time2 = time.perf_counter() - start_time

        # Both should return 401 and take similar time
        assert response1.status_code == status.HTTP_401_UNAUTHORIZED
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED

        # Times should be similar (within reasonable variance)
        time_ratio = max(time1, time2) / min(time1, time2)
        assert time_ratio < 3  # Allow some variance

    @pytest.mark.asyncio
    async def test_password_policy_enforcement(self, async_client: AsyncClient, test_organization):
        """Test that password policy is enforced."""
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "qwerty",
            "Password1",  # Common pattern
            "short"  # Too short
        ]

        for weak_password in weak_passwords:
            user_data = create_test_user_data(password=weak_password)

            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    **user_data,
                    "organization_id": str(test_organization.id)
                }
            )

            # Should reject weak passwords
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_password_storage_security(self, async_client: AsyncClient, test_organization, db_session):
        """Test that passwords are stored securely."""
        password = "SecurePassword123!"
        user_data = create_test_user_data(password=password)

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        user_id = response.json()["id"]

        # Check database directly
        from sqlalchemy import select
        from app.models.auth import User

        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()

        # Password should be hashed, not plaintext
        assert user.password_hash != password
        assert len(user.password_hash) > 50  # Argon2 hashes are long
        assert "$argon2" in user.password_hash  # Argon2 format


class TestSessionSecurityFlaws:
    """Test session management security."""

    @pytest.mark.asyncio
    async def test_session_fixation_protection(self, async_client: AsyncClient, test_user):
        """Test protection against session fixation attacks."""
        # Login and get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert login_response.status_code == status.HTTP_200_OK
        tokens1 = login_response.json()

        # Login again and get new token
        login_response2 = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert login_response2.status_code == status.HTTP_200_OK
        tokens2 = login_response2.json()

        # Tokens should be different (new session)
        assert tokens1["access_token"] != tokens2["access_token"]
        assert tokens1["refresh_token"] != tokens2["refresh_token"]

    @pytest.mark.asyncio
    async def test_concurrent_session_limits(self, async_client: AsyncClient, test_user, db_session):
        """Test concurrent session management."""
        # Create multiple sessions
        sessions = []
        for i in range(5):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "testpassword123"
                }
            )
            assert response.status_code == status.HTTP_200_OK
            sessions.append(response.json())

        # Check session count in database
        from sqlalchemy import select, func
        from app.models.auth import UserSession

        result = await db_session.execute(
            select(func.count(UserSession.id)).where(
                UserSession.user_id == test_user.id,
                UserSession.is_active == True
            )
        )
        active_sessions = result.scalar()

        # Should have reasonable session limit (adjust based on implementation)
        assert active_sessions <= 10  # Reasonable limit

    @pytest.mark.asyncio
    async def test_session_timeout_enforcement(self, async_client: AsyncClient, test_user):
        """Test that session timeouts are enforced."""
        # Create token with very short expiry
        short_lived_token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email},
            expires_delta=timedelta(seconds=1)
        )

        # Token should work initially
        immediate_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {short_lived_token}"}
        )
        assert immediate_response.status_code == status.HTTP_200_OK

        # Wait for token to expire
        await asyncio.sleep(2)

        # Token should be expired now
        expired_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {short_lived_token}"}
        )
        assert expired_response.status_code == status.HTTP_401_UNAUTHORIZED


class TestInputValidationFlaws:
    """Test input validation security."""

    @pytest.mark.asyncio
    async def test_input_length_limits(self, async_client: AsyncClient, test_organization):
        """Test that input length limits are enforced."""
        # Very long inputs
        very_long_string = "a" * 10000

        user_data = create_test_user_data(
            first_name=very_long_string,
            last_name=very_long_string,
            email=f"{very_long_string}@example.com"
        )

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        # Should reject overly long inputs
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_special_character_handling(self, async_client: AsyncClient, test_organization):
        """Test handling of special characters in input."""
        special_chars = [
            "\x00",  # Null byte
            "\r\n",  # CRLF injection
            "..\\..\\",  # Path traversal
            "%00",  # URL encoded null
            "\uff1c\uff1e"  # Unicode angle brackets
        ]

        for special_char in special_chars:
            user_data = create_test_user_data(
                first_name=f"Test{special_char}User",
                last_name=f"Last{special_char}Name"
            )

            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    **user_data,
                    "organization_id": str(test_organization.id)
                }
            )

            # Should handle gracefully (either success with sanitized input or validation error)
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]

    @pytest.mark.asyncio
    async def test_numeric_overflow_protection(self, async_client: AsyncClient, admin_auth_headers):
        """Test protection against numeric overflow attacks."""
        # Try to create role with extremely large values
        large_number = 2**63 - 1  # Max 64-bit integer

        response = await async_client.post(
            "/api/v1/rbac/roles",
            headers=admin_auth_headers,
            json={
                "name": "TestRole",
                "description": "Test",
                "permissions": [str(large_number)]  # Invalid permission ID
            }
        )

        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestInformationDisclosureFlaws:
    """Test information disclosure vulnerabilities."""

    @pytest.mark.asyncio
    async def test_error_message_information_leakage(self, async_client: AsyncClient):
        """Test that error messages don't leak sensitive information."""
        # Try to login with non-existent user
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "any_password"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # Error message should not reveal whether user exists
        error_detail = data.get("detail", "").lower()
        assert "user not found" not in error_detail
        assert "does not exist" not in error_detail
        assert "invalid credentials" in error_detail

    @pytest.mark.asyncio
    async def test_user_enumeration_protection(self, async_client: AsyncClient, test_user):
        """Test protection against user enumeration attacks."""
        # Password reset with existing email
        response1 = await async_client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": test_user.email}
        )

        # Password reset with non-existent email
        response2 = await async_client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "nonexistent@example.com"}
        )

        # Both should return same response to prevent enumeration
        assert response1.status_code == response2.status_code == status.HTTP_200_OK

        # Response messages should be similar
        data1 = response1.json()
        data2 = response2.json()
        assert data1.get("message") == data2.get("message")

    @pytest.mark.asyncio
    async def test_debug_information_not_exposed(self, async_client: AsyncClient):
        """Test that debug information is not exposed in production."""
        # Make request that should cause server error
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"invalid": "data"}
        )

        # Should not expose internal details
        data = response.json()
        error_detail = str(data.get("detail", ""))

        # Should not contain internal paths, SQL queries, or stack traces
        assert "/app/" not in error_detail
        assert "SELECT " not in error_detail
        assert "Traceback" not in error_detail
        assert "File \"" not in error_detail

    @pytest.mark.asyncio
    async def test_version_information_not_exposed(self, async_client: AsyncClient):
        """Test that version information is not unnecessarily exposed."""
        response = await async_client.get("/api/v1/auth/me")

        # Headers should not expose sensitive version info
        headers = response.headers

        # Should not have server version headers
        assert "Server" not in headers or "FastAPI" not in headers.get("Server", "")
        assert "X-Powered-By" not in headers


class TestSecurityHeadersCompliance:
    """Test security headers compliance."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client: AsyncClient):
        """Test that all required security headers are present."""
        response = await async_client.get("/api/v1/health")

        headers = response.headers

        # Required security headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]

        for header in required_headers:
            assert header in headers, f"Missing security header: {header}"

    @pytest.mark.asyncio
    async def test_hsts_header_configuration(self, async_client: AsyncClient):
        """Test HSTS header configuration."""
        response = await async_client.get("/api/v1/health")

        hsts_header = response.headers.get("Strict-Transport-Security")
        assert hsts_header is not None

        # Should have long max-age
        assert "max-age=" in hsts_header
        max_age = int(hsts_header.split("max-age=")[1].split(";")[0])
        assert max_age >= 31536000  # At least 1 year

        # Should include subdomains
        assert "includeSubDomains" in hsts_header

    @pytest.mark.asyncio
    async def test_csp_header_configuration(self, async_client: AsyncClient):
        """Test Content Security Policy header configuration."""
        response = await async_client.get("/api/v1/health")

        csp_header = response.headers.get("Content-Security-Policy")
        assert csp_header is not None

        # Should have restrictive default policy
        assert "default-src 'self'" in csp_header
        assert "script-src 'self'" in csp_header

        # Should not allow unsafe eval or inline
        assert "'unsafe-eval'" not in csp_header
        assert "'unsafe-inline'" not in csp_header or "'unsafe-inline'" in csp_header.split("style-src")[1] if "style-src" in csp_header else False
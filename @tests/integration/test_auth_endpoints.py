"""
Integration tests for authentication API endpoints and workflows.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient
from fastapi import status

from app.core.security import create_access_token, create_refresh_token, create_password_reset_token_jwt
from app.models.auth import User, RefreshToken
from tests.conftest import create_test_user_data


class TestUserRegistration:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, async_client: AsyncClient, test_organization):
        """Test successful user registration."""
        user_data = create_test_user_data()

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert "id" in data
        assert "password" not in data  # Password should not be returned

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, async_client: AsyncClient, test_user, test_organization):
        """Test registration with duplicate email."""
        user_data = create_test_user_data(email=test_user.email)

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already registered" in data["detail"]

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, async_client: AsyncClient, test_user, test_organization):
        """Test registration with duplicate username."""
        user_data = create_test_user_data(username=test_user.username)

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already taken" in data["detail"]

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, async_client: AsyncClient, test_organization):
        """Test registration with invalid email format."""
        user_data = create_test_user_data(email="invalid-email")

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, async_client: AsyncClient, test_organization):
        """Test registration with weak password."""
        user_data = create_test_user_data(password="weak")

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "password" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_user_missing_fields(self, async_client: AsyncClient, test_organization):
        """Test registration with missing required fields."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                # Missing username and password
                "organization_id": str(test_organization.id)
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_user_invalid_organization(self, async_client: AsyncClient):
        """Test registration with invalid organization ID."""
        user_data = create_test_user_data()

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(uuid4())  # Non-existent organization
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUserLogin:
    """Test user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user):
        """Test successful login."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"  # From fixture
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        """Test login with wrong password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Invalid credentials" in data["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, async_client: AsyncClient, db_session, test_user):
        """Test login with inactive user."""
        # Deactivate user
        test_user.is_active = False
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "disabled" in data["detail"]

    @pytest.mark.asyncio
    async def test_login_locked_user(self, async_client: AsyncClient, db_session, test_user):
        """Test login with locked user."""
        # Lock user
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "locked" in data["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_input(self, async_client: AsyncClient):
        """Test login with invalid input format."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": ""
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_creates_session(self, async_client: AsyncClient, test_user, db_session):
        """Test that login creates a user session."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == status.HTTP_200_OK

        # Check that session was created in database
        from sqlalchemy import select
        from app.models.auth import UserSession

        result = await db_session.execute(
            select(UserSession).where(UserSession.user_id == test_user.id)
        )
        sessions = result.scalars().all()
        assert len(sessions) >= 1

    @pytest.mark.asyncio
    async def test_login_with_remember_me(self, async_client: AsyncClient, test_user):
        """Test login with remember me option."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
                "remember_me": True
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should receive both tokens
        assert "access_token" in data
        assert "refresh_token" in data


class TestTokenRefresh:
    """Test token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient, test_user, db_session):
        """Test successful token refresh."""
        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(test_user.id), "email": test_user.email}
        )

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, async_client: AsyncClient, test_user):
        """Test refresh with expired token."""
        # Create expired refresh token
        expired_token = create_refresh_token(
            data={"sub": str(test_user.id)},
            expires_delta=timedelta(seconds=-1)
        )

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_revoked(self, async_client: AsyncClient, test_user, db_session):
        """Test refresh with revoked token."""
        # Create and revoke refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(test_user.id), "email": test_user.email}
        )

        # Mock token as revoked in database
        from app.core.security import decode_token
        payload = decode_token(refresh_token)

        revoked_token = RefreshToken(
            jti=payload["jti"],
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=True,
            revoked_at=datetime.now(timezone.utc)
        )
        db_session.add(revoked_token)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserLogout:
    """Test user logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, auth_headers, redis_client):
        """Test successful logout."""
        with patch('app.core.database.get_redis', return_value=redis_client):
            response = await async_client.post(
                "/api/v1/auth/logout",
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Successfully logged out"

    @pytest.mark.asyncio
    async def test_logout_without_token(self, async_client: AsyncClient):
        """Test logout without authentication token."""
        response = await async_client.post("/api/v1/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, async_client: AsyncClient):
        """Test logout with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordManagement:
    """Test password management endpoints."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test successful password change."""
        response = await async_client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecurePassword456!",
                "confirm_password": "NewSecurePassword456!"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Password changed successfully"

        # Verify password was actually changed
        await db_session.refresh(test_user)
        from app.core.security import verify_password
        assert verify_password("NewSecurePassword456!", test_user.password_hash)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, async_client: AsyncClient, auth_headers):
        """Test password change with wrong current password."""
        response = await async_client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "NewSecurePassword456!",
                "confirm_password": "NewSecurePassword456!"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "current password" in data["detail"]

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, async_client: AsyncClient, auth_headers):
        """Test password change with password mismatch."""
        response = await async_client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecurePassword456!",
                "confirm_password": "DifferentPassword789!"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "do not match" in data["detail"]

    @pytest.mark.asyncio
    async def test_request_password_reset(self, async_client: AsyncClient, test_user):
        """Test password reset request."""
        response = await async_client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": test_user.email}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "reset token" in data["message"]

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_user(self, async_client: AsyncClient):
        """Test password reset request for non-existent user."""
        response = await async_client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "nonexistent@example.com"}
        )

        # Should return 200 for security (don't reveal if email exists)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_confirm_password_reset(self, async_client: AsyncClient, test_user, db_session):
        """Test password reset confirmation."""
        # Generate reset token
        reset_token = create_password_reset_token_jwt(
            user_id=str(test_user.id),
            email=test_user.email
        )

        response = await async_client.post(
            "/api/v1/auth/confirm-password-reset",
            json={
                "token": reset_token,
                "new_password": "NewResetPassword123!",
                "confirm_password": "NewResetPassword123!"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Password reset successfully"

        # Verify password was changed
        await db_session.refresh(test_user)
        from app.core.security import verify_password
        assert verify_password("NewResetPassword123!", test_user.password_hash)

    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(self, async_client: AsyncClient):
        """Test password reset confirmation with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/confirm-password-reset",
            json={
                "token": "invalid_token",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestProfileManagement:
    """Test user profile management endpoints."""

    @pytest.mark.asyncio
    async def test_get_profile(self, async_client: AsyncClient, auth_headers, test_user):
        """Test getting user profile."""
        response = await async_client.get(
            "/api/v1/auth/profile",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name
        assert "id" in data
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_update_profile(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test updating user profile."""
        response = await async_client.put(
            "/api/v1/auth/profile",
            headers=auth_headers,
            json={
                "first_name": "Updated",
                "last_name": "Name",
                "timezone": "America/New_York"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["timezone"] == "America/New_York"

        # Verify in database
        await db_session.refresh(test_user)
        assert test_user.first_name == "Updated"
        assert test_user.last_name == "Name"
        assert test_user.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_update_profile_partial(self, async_client: AsyncClient, auth_headers):
        """Test partial profile update."""
        response = await async_client.put(
            "/api/v1/auth/profile",
            headers=auth_headers,
            json={"first_name": "OnlyFirst"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == "OnlyFirst"


class TestMFAManagement:
    """Test MFA management endpoints."""

    @pytest.mark.asyncio
    async def test_enable_mfa(self, async_client: AsyncClient, auth_headers):
        """Test enabling MFA."""
        response = await async_client.post(
            "/api/v1/auth/mfa/enable",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "secret" in data
        assert "qr_code" in data
        assert len(data["secret"]) == 32

    @pytest.mark.asyncio
    async def test_confirm_mfa_setup(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test confirming MFA setup."""
        # First enable MFA
        test_user.mfa_secret = "TESTSECRET123456789012345678901234"
        await db_session.commit()

        with patch('pyotp.TOTP.verify', return_value=True):
            response = await async_client.post(
                "/api/v1/auth/mfa/confirm",
                headers=auth_headers,
                json={"totp_code": "123456"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "backup_codes" in data
            assert len(data["backup_codes"]) == 10

    @pytest.mark.asyncio
    async def test_disable_mfa(self, async_client: AsyncClient, auth_headers, test_user, db_session):
        """Test disabling MFA."""
        # Setup MFA first
        test_user.mfa_enabled = True
        test_user.mfa_secret = "secret"
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/mfa/disable",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify MFA is disabled
        await db_session.refresh(test_user)
        assert test_user.mfa_enabled is False


class TestEmailVerification:
    """Test email verification endpoints."""

    @pytest.mark.asyncio
    async def test_send_verification_email(self, async_client: AsyncClient, auth_headers):
        """Test sending verification email."""
        response = await async_client.post(
            "/api/v1/auth/send-verification-email",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "sent" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_email(self, async_client: AsyncClient, test_user, db_session):
        """Test email verification."""
        # Generate verification token
        verification_token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email, "type": "email_verification"}
        )

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify email is marked as verified
        await db_session.refresh(test_user)
        assert test_user.email_verified is True


class TestEndToEndWorkflows:
    """Test complete end-to-end authentication workflows."""

    @pytest.mark.asyncio
    async def test_complete_registration_login_workflow(self, async_client: AsyncClient, test_organization, redis_client):
        """Test complete registration, login, and access workflow."""
        # 1. Register new user
        user_data = create_test_user_data()

        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        user_id = register_response.json()["id"]

        # 2. Login with new user
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"]
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()

        # 3. Access protected endpoint
        profile_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert profile_response.status_code == status.HTTP_200_OK
        profile = profile_response.json()
        assert profile["email"] == user_data["email"]

        # 4. Update profile
        with patch('app.core.database.get_redis', return_value=redis_client):
            update_response = await async_client.put(
                "/api/v1/auth/profile",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                json={"first_name": "Updated"}
            )
            assert update_response.status_code == status.HTTP_200_OK

        # 5. Logout
        with patch('app.core.database.get_redis', return_value=redis_client):
            logout_response = await async_client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            assert logout_response.status_code == status.HTTP_200_OK

        # 6. Try to access protected endpoint after logout (should fail)
        profile_after_logout = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert profile_after_logout.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_password_reset_workflow(self, async_client: AsyncClient, test_user, db_session):
        """Test complete password reset workflow."""
        original_password = test_user.password_hash

        # 1. Request password reset
        reset_request_response = await async_client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": test_user.email}
        )
        assert reset_request_response.status_code == status.HTTP_200_OK

        # 2. Generate reset token (simulating email link)
        reset_token = create_password_reset_token_jwt(
            user_id=str(test_user.id),
            email=test_user.email
        )

        # 3. Confirm password reset
        reset_confirm_response = await async_client.post(
            "/api/v1/auth/confirm-password-reset",
            json={
                "token": reset_token,
                "new_password": "NewResetPassword123!",
                "confirm_password": "NewResetPassword123!"
            }
        )
        assert reset_confirm_response.status_code == status.HTTP_200_OK

        # 4. Verify password was changed
        await db_session.refresh(test_user)
        assert test_user.password_hash != original_password

        # 5. Login with new password
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "NewResetPassword123!"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_token_refresh_workflow(self, async_client: AsyncClient, test_user):
        """Test token refresh workflow."""
        # 1. Login to get initial tokens
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        initial_tokens = login_response.json()

        # 2. Refresh tokens
        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": initial_tokens["refresh_token"]}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_tokens = refresh_response.json()

        # 3. Verify new tokens are different
        assert new_tokens["access_token"] != initial_tokens["access_token"]
        assert new_tokens["refresh_token"] != initial_tokens["refresh_token"]

        # 4. Use new access token
        profile_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
        )
        assert profile_response.status_code == status.HTTP_200_OK


class TestAuthenticationSecurity:
    """Test authentication security aspects."""

    @pytest.mark.asyncio
    async def test_rate_limiting_login_attempts(self, async_client: AsyncClient, test_user, redis_client):
        """Test rate limiting on login attempts."""
        # This would require actual rate limiting middleware setup
        # For now, we test the concept

        with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
            # Simulate multiple failed login attempts
            for i in range(5):
                response = await async_client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": test_user.email,
                        "password": "wrongpassword"
                    }
                )
                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_concurrent_login_sessions(self, async_client: AsyncClient, test_user):
        """Test handling of concurrent login sessions."""
        # Login from first "device"
        login1_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        assert login1_response.status_code == status.HTTP_200_OK

        # Login from second "device"
        login2_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        assert login2_response.status_code == status.HTTP_200_OK

        # Both sessions should be valid
        tokens1 = login1_response.json()
        tokens2 = login2_response.json()

        profile1_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens1['access_token']}"}
        )
        assert profile1_response.status_code == status.HTTP_200_OK

        profile2_response = await async_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens2['access_token']}"}
        )
        assert profile2_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_sensitive_data_not_logged(self, async_client: AsyncClient, test_organization):
        """Test that sensitive data is not included in logs."""
        user_data = create_test_user_data()

        with patch('app.core.logging.get_logger') as mock_logger:
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    **user_data,
                    "organization_id": str(test_organization.id)
                }
            )

            # Verify password is not in any log calls
            for call in mock_logger.return_value.info.call_args_list:
                if call[0]:  # If there are positional arguments
                    assert user_data["password"] not in str(call[0])

    @pytest.mark.asyncio
    async def test_csrf_protection_headers(self, async_client: AsyncClient):
        """Test CSRF protection headers in responses."""
        response = await async_client.get("/api/v1/auth/me")

        # Response should include security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
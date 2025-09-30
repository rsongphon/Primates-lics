"""
Unit tests for authentication service layer business logic.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.services.auth import (
    AuthService,
    UserService,
    PasswordService,
    MFAService,
    RoleService,
    PermissionService
)
from app.models.auth import User, Role, Permission, RefreshToken, UserSession
from app.core.security import get_password_hash, verify_password
from app.schemas.auth import (
    UserRegistrationRequest,
    UserLoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest
)


class TestAuthService:
    """Test AuthService business logic."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, db_session, test_organization):
        """Test successful user registration."""
        service = AuthService(db_session)

        request = UserRegistrationRequest(
            email="newuser@example.com",
            username="newuser",
            password="SecurePassword123!",
            first_name="New",
            last_name="User"
        )

        user = await service.register_user(request, test_organization.id)

        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.organization_id == test_organization.id
        assert user.is_active is True
        assert user.is_verified is False
        assert verify_password("SecurePassword123!", user.password_hash)

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, db_session, test_user, test_organization):
        """Test registration with duplicate email."""
        service = AuthService(db_session)

        request = UserRegistrationRequest(
            email=test_user.email,  # Duplicate email
            username="differentuser",
            password="SecurePassword123!",
            first_name="Another",
            last_name="User"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(request, test_organization.id)

        assert exc_info.value.status_code == 400
        assert "already registered" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, db_session, test_user, test_organization):
        """Test registration with duplicate username."""
        service = AuthService(db_session)

        request = UserRegistrationRequest(
            email="different@example.com",
            username=test_user.username,  # Duplicate username
            password="SecurePassword123!",
            first_name="Another",
            last_name="User"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(request, test_organization.id)

        assert exc_info.value.status_code == 400
        assert "already taken" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session, test_user):
        """Test successful user authentication."""
        service = AuthService(db_session)

        request = UserLoginRequest(
            email=test_user.email,
            password="testpassword123"  # From test fixture
        )

        authenticated_user = await service.authenticate_user(request)

        assert authenticated_user.id == test_user.id
        assert authenticated_user.email == test_user.email

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session, test_user):
        """Test authentication with wrong password."""
        service = AuthService(db_session)

        request = UserLoginRequest(
            email=test_user.email,
            password="wrongpassword"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(request)

        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication with non-existent user."""
        service = AuthService(db_session)

        request = UserLoginRequest(
            email="nonexistent@example.com",
            password="password"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, db_session, test_user):
        """Test authentication with inactive user."""
        service = AuthService(db_session)

        # Deactivate user
        test_user.is_active = False
        await db_session.commit()

        request = UserLoginRequest(
            email=test_user.email,
            password="testpassword123"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(request)

        assert exc_info.value.status_code == 401
        assert "disabled" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_authenticate_user_locked(self, db_session, test_user):
        """Test authentication with locked user."""
        service = AuthService(db_session)

        # Lock user
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        await db_session.commit()

        request = UserLoginRequest(
            email=test_user.email,
            password="testpassword123"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(request)

        assert exc_info.value.status_code == 401
        assert "locked" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_session(self, db_session, test_user):
        """Test creating user session."""
        service = AuthService(db_session)

        session = await service.create_user_session(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )

        assert session.user_id == test_user.id
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Test Browser"
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_logout_user(self, db_session, test_user):
        """Test user logout."""
        service = AuthService(db_session)

        # Create session
        session = await service.create_user_session(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )

        # Mock Redis client
        redis_mock = AsyncMock()

        await service.logout_user(test_user.id, str(uuid4()), redis_mock)

        # Session should be deactivated
        await db_session.refresh(session)
        assert session.is_active is False
        assert session.ended_at is not None


class TestUserService:
    """Test UserService business logic."""

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session, test_user):
        """Test getting user by ID."""
        service = UserService(db_session)

        user = await service.get_user_by_id(test_user.id)

        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session):
        """Test getting non-existent user by ID."""
        service = UserService(db_session)

        user = await service.get_user_by_id(uuid4())

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session, test_user):
        """Test getting user by email."""
        service = UserService(db_session)

        user = await service.get_user_by_email(test_user.email)

        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_update_user_profile(self, db_session, test_user):
        """Test updating user profile."""
        service = UserService(db_session)

        updated_user = await service.update_user_profile(
            test_user.id,
            first_name="Updated",
            last_name="Name",
            timezone="America/New_York"
        )

        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_update_user_profile_not_found(self, db_session):
        """Test updating non-existent user profile."""
        service = UserService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_user_profile(
                uuid4(),
                first_name="Updated"
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_user(self, db_session, test_user):
        """Test deactivating user."""
        service = UserService(db_session)

        deactivated_user = await service.deactivate_user(test_user.id)

        assert deactivated_user.is_active is False

    @pytest.mark.asyncio
    async def test_verify_user_email(self, db_session, test_user):
        """Test verifying user email."""
        service = UserService(db_session)

        # Initially not verified
        assert test_user.email_verified is False

        verified_user = await service.verify_user_email(test_user.id)

        assert verified_user.email_verified is True
        assert verified_user.email_verified_at is not None

    @pytest.mark.asyncio
    async def test_list_users_paginated(self, db_session, test_organization):
        """Test listing users with pagination."""
        service = UserService(db_session)

        # Create multiple users
        for i in range(5):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password_hash=get_password_hash("password"),
                organization_id=test_organization.id
            )
            db_session.add(user)
        await db_session.commit()

        users, total = await service.list_users(
            organization_id=test_organization.id,
            skip=0,
            limit=3
        )

        assert len(users) == 3
        assert total >= 5  # At least the 5 we created


class TestPasswordService:
    """Test PasswordService business logic."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, db_session, test_user):
        """Test successful password change."""
        service = PasswordService(db_session)

        request = PasswordChangeRequest(
            current_password="testpassword123",
            new_password="NewSecurePassword456!",
            confirm_password="NewSecurePassword456!"
        )

        await service.change_password(test_user.id, request)

        # Verify new password
        await db_session.refresh(test_user)
        assert verify_password("NewSecurePassword456!", test_user.password_hash)
        assert test_user.password_changed_at is not None

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, db_session, test_user):
        """Test password change with wrong current password."""
        service = PasswordService(db_session)

        request = PasswordChangeRequest(
            current_password="wrongpassword",
            new_password="NewSecurePassword456!",
            confirm_password="NewSecurePassword456!"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(test_user.id, request)

        assert exc_info.value.status_code == 400
        assert "current password" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, db_session, test_user):
        """Test password change with password mismatch."""
        service = PasswordService(db_session)

        request = PasswordChangeRequest(
            current_password="testpassword123",
            new_password="NewSecurePassword456!",
            confirm_password="DifferentPassword789!"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(test_user.id, request)

        assert exc_info.value.status_code == 400
        assert "do not match" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_request_password_reset(self, db_session, test_user):
        """Test requesting password reset."""
        service = PasswordService(db_session)

        request = PasswordResetRequest(email=test_user.email)

        reset_token = await service.request_password_reset(request)

        assert reset_token is not None
        assert len(reset_token) > 0

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_user(self, db_session):
        """Test requesting password reset for non-existent user."""
        service = PasswordService(db_session)

        request = PasswordResetRequest(email="nonexistent@example.com")

        # Should not raise exception (security best practice)
        reset_token = await service.request_password_reset(request)

        assert reset_token is None

    @pytest.mark.asyncio
    async def test_confirm_password_reset(self, db_session, test_user):
        """Test confirming password reset."""
        service = PasswordService(db_session)

        # First request reset
        reset_request = PasswordResetRequest(email=test_user.email)
        reset_token = await service.request_password_reset(reset_request)

        # Then confirm reset
        confirm_request = PasswordResetConfirmRequest(
            token=reset_token,
            new_password="NewResetPassword123!",
            confirm_password="NewResetPassword123!"
        )

        await service.confirm_password_reset(confirm_request)

        # Verify new password
        await db_session.refresh(test_user)
        assert verify_password("NewResetPassword123!", test_user.password_hash)

    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(self, db_session):
        """Test confirming password reset with invalid token."""
        service = PasswordService(db_session)

        confirm_request = PasswordResetConfirmRequest(
            token="invalid_token",
            new_password="NewPassword123!",
            confirm_password="NewPassword123!"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.confirm_password_reset(confirm_request)

        assert exc_info.value.status_code == 400
        assert "Invalid" in str(exc_info.value.detail)


class TestMFAService:
    """Test MFAService business logic."""

    @pytest.mark.asyncio
    async def test_enable_mfa(self, db_session, test_user):
        """Test enabling MFA for user."""
        service = MFAService(db_session)

        secret, qr_code = await service.enable_mfa(test_user.id)

        assert secret is not None
        assert qr_code is not None
        assert len(secret) == 32  # TOTP secret length

        # User should have MFA secret but not enabled yet
        await db_session.refresh(test_user)
        assert test_user.mfa_secret is not None
        assert test_user.mfa_enabled is False

    @pytest.mark.asyncio
    async def test_confirm_mfa_setup(self, db_session, test_user):
        """Test confirming MFA setup."""
        service = MFAService(db_session)

        # First enable MFA
        secret, _ = await service.enable_mfa(test_user.id)

        # Mock TOTP verification
        with patch('pyotp.TOTP.verify', return_value=True):
            backup_codes = await service.confirm_mfa_setup(test_user.id, "123456")

        assert len(backup_codes) == 10

        # User should now have MFA enabled
        await db_session.refresh(test_user)
        assert test_user.mfa_enabled is True
        assert test_user.backup_codes is not None

    @pytest.mark.asyncio
    async def test_verify_mfa_token(self, db_session, test_user):
        """Test verifying MFA token."""
        service = MFAService(db_session)

        # Setup MFA
        test_user.mfa_enabled = True
        test_user.mfa_secret = "TESTSECRET123456789012345678901234"
        await db_session.commit()

        # Mock TOTP verification
        with patch('pyotp.TOTP.verify', return_value=True):
            is_valid = await service.verify_mfa_token(test_user.id, "123456")

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_backup_code(self, db_session, test_user):
        """Test verifying backup code."""
        service = MFAService(db_session)

        backup_codes = ["code1", "code2", "code3"]
        test_user.mfa_enabled = True
        test_user.backup_codes = backup_codes
        await db_session.commit()

        is_valid = await service.verify_backup_code(test_user.id, "code1")

        assert is_valid is True

        # Code should be removed after use
        await db_session.refresh(test_user)
        assert "code1" not in test_user.backup_codes

    @pytest.mark.asyncio
    async def test_disable_mfa(self, db_session, test_user):
        """Test disabling MFA."""
        service = MFAService(db_session)

        # Setup MFA
        test_user.mfa_enabled = True
        test_user.mfa_secret = "secret"
        test_user.backup_codes = ["code1", "code2"]
        await db_session.commit()

        await service.disable_mfa(test_user.id)

        # MFA should be disabled and secrets cleared
        await db_session.refresh(test_user)
        assert test_user.mfa_enabled is False
        assert test_user.mfa_secret is None
        assert test_user.backup_codes is None


class TestRoleService:
    """Test RoleService business logic."""

    @pytest.mark.asyncio
    async def test_create_role(self, db_session, test_permissions):
        """Test creating a role."""
        service = RoleService(db_session)

        role = await service.create_role(
            name="Test Role",
            description="Test role description",
            permission_ids=[p.id for p in test_permissions[:2]]
        )

        assert role.name == "Test Role"
        assert role.description == "Test role description"
        assert len(role.permissions) == 2

    @pytest.mark.asyncio
    async def test_create_role_duplicate_name(self, db_session, test_roles):
        """Test creating role with duplicate name."""
        service = RoleService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.create_role(
                name=test_roles[0].name,  # Duplicate name
                description="Different description"
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, db_session, test_user, test_roles):
        """Test assigning role to user."""
        service = RoleService(db_session)

        await service.assign_role_to_user(test_user.id, test_roles[0].id)

        await db_session.refresh(test_user)
        assert test_roles[0] in test_user.roles

    @pytest.mark.asyncio
    async def test_remove_role_from_user(self, db_session, test_user, test_roles):
        """Test removing role from user."""
        service = RoleService(db_session)

        # First assign role
        test_user.roles.append(test_roles[0])
        await db_session.commit()

        # Then remove it
        await service.remove_role_from_user(test_user.id, test_roles[0].id)

        await db_session.refresh(test_user)
        assert test_roles[0] not in test_user.roles

    @pytest.mark.asyncio
    async def test_delete_role(self, db_session, test_permissions):
        """Test deleting a role."""
        service = RoleService(db_session)

        # Create role to delete
        role = await service.create_role(
            name="To Delete",
            description="Will be deleted",
            permission_ids=[test_permissions[0].id]
        )

        await service.delete_role(role.id)

        deleted_role = await service.get_role_by_id(role.id)
        assert deleted_role is None

    @pytest.mark.asyncio
    async def test_delete_system_role_forbidden(self, db_session, test_permissions):
        """Test that system roles cannot be deleted."""
        service = RoleService(db_session)

        # Create system role
        role = await service.create_role(
            name="System Role",
            description="System role",
            is_system_role=True
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_role(role.id)

        assert exc_info.value.status_code == 400
        assert "system role" in str(exc_info.value.detail)


class TestPermissionService:
    """Test PermissionService business logic."""

    @pytest.mark.asyncio
    async def test_create_permission(self, db_session):
        """Test creating a permission."""
        service = PermissionService(db_session)

        permission = await service.create_permission(
            name="test:new",
            display_name="Test New",
            description="New test permission",
            resource="test",
            action="new"
        )

        assert permission.name == "test:new"
        assert permission.display_name == "Test New"
        assert permission.resource == "test"
        assert permission.action == "new"

    @pytest.mark.asyncio
    async def test_create_permission_duplicate_name(self, db_session, test_permissions):
        """Test creating permission with duplicate name."""
        service = PermissionService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.create_permission(
                name=test_permissions[0].name,  # Duplicate name
                display_name="Different Display",
                description="Different description",
                resource="different",
                action="different"
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, db_session, test_user, test_roles, test_permissions):
        """Test getting user permissions through roles."""
        service = PermissionService(db_session)

        # Assign role with permissions to user
        test_user.roles.append(test_roles[0])  # Admin role has all permissions
        await db_session.commit()

        permissions = await service.get_user_permissions(test_user.id)

        assert len(permissions) > 0
        # Should contain permissions from the assigned role

    @pytest.mark.asyncio
    async def test_user_has_permission(self, db_session, test_user, test_roles, test_permissions):
        """Test checking if user has specific permission."""
        service = PermissionService(db_session)

        # Assign role with permissions
        test_user.roles.append(test_roles[0])  # Admin role
        await db_session.commit()

        has_permission = await service.user_has_permission(
            test_user.id,
            test_permissions[0].name
        )

        assert has_permission is True

    @pytest.mark.asyncio
    async def test_user_has_permission_false(self, db_session, test_user):
        """Test checking permission for user without roles."""
        service = PermissionService(db_session)

        has_permission = await service.user_has_permission(
            test_user.id,
            "nonexistent:permission"
        )

        assert has_permission is False


class TestServiceErrorHandling:
    """Test error handling in services."""

    @pytest.mark.asyncio
    async def test_database_error_handling(self, db_session):
        """Test handling of database errors."""
        service = UserService(db_session)

        # Mock database error
        with patch.object(db_session, 'execute', side_effect=Exception("Database error")):
            with pytest.raises(Exception):
                await service.get_user_by_email("test@example.com")

    @pytest.mark.asyncio
    async def test_service_with_none_session(self):
        """Test service behavior with None session."""
        with pytest.raises(Exception):
            UserService(None)

    @pytest.mark.asyncio
    async def test_invalid_uuid_handling(self, db_session):
        """Test handling of invalid UUIDs."""
        service = UserService(db_session)

        # This should handle gracefully (return None or raise HTTPException)
        user = await service.get_user_by_id("not-a-uuid")
        assert user is None


class TestServiceIntegration:
    """Test service integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_user_workflow(self, db_session, test_organization, test_roles):
        """Test complete user creation and setup workflow."""
        auth_service = AuthService(db_session)
        user_service = UserService(db_session)
        role_service = RoleService(db_session)

        # 1. Register user
        request = UserRegistrationRequest(
            email="workflow@example.com",
            username="workflowuser",
            password="SecurePassword123!",
            first_name="Workflow",
            last_name="User"
        )
        user = await auth_service.register_user(request, test_organization.id)

        # 2. Verify email
        verified_user = await user_service.verify_user_email(user.id)
        assert verified_user.email_verified is True

        # 3. Assign role
        await role_service.assign_role_to_user(user.id, test_roles[1].id)  # User role

        # 4. Update profile
        updated_user = await user_service.update_user_profile(
            user.id,
            timezone="America/New_York"
        )

        assert updated_user.timezone == "America/New_York"
        assert len(updated_user.roles) == 1

    @pytest.mark.asyncio
    async def test_role_permission_cascade(self, db_session, test_permissions):
        """Test role-permission relationship cascading."""
        role_service = RoleService(db_session)
        permission_service = PermissionService(db_session)

        # Create role with permissions
        role = await role_service.create_role(
            name="Cascade Test",
            description="Test cascading",
            permission_ids=[p.id for p in test_permissions[:2]]
        )

        # Verify permissions are assigned
        role_permissions = await permission_service.get_role_permissions(role.id)
        assert len(role_permissions) == 2

        # Delete role should not affect permissions
        await role_service.delete_role(role.id)

        # Permissions should still exist
        for perm in test_permissions[:2]:
            existing_perm = await permission_service.get_permission_by_id(perm.id)
            assert existing_perm is not None
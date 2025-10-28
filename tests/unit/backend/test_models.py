"""
Unit tests for authentication database models and relationships.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models.auth import User, Role, Permission, RefreshToken, UserSession
from app.models.base import Organization
from app.core.security import get_password_hash


class TestOrganizationModel:
    """Test Organization model."""

    @pytest.mark.asyncio
    async def test_create_organization(self, db_session):
        """Test creating an organization."""
        org = Organization(
            name="Test Org",
            description="Test organization",
            settings={"max_devices": 10}
        )
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

        assert org.id is not None
        assert org.name == "Test Org"
        assert org.description == "Test organization"
        assert org.settings == {"max_devices": 10}
        assert org.created_at is not None
        assert org.updated_at is not None

    @pytest.mark.asyncio
    async def test_organization_unique_name(self, db_session):
        """Test that organization names must be unique."""
        org1 = Organization(name="Unique Name", description="First")
        org2 = Organization(name="Unique Name", description="Second")

        db_session.add(org1)
        await db_session.commit()

        db_session.add(org2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_organization_soft_delete(self, db_session):
        """Test organization soft delete functionality."""
        org = Organization(name="To Delete", description="Will be deleted")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

        # Soft delete
        org.deleted_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Should still exist in database
        result = await db_session.execute(
            select(Organization).where(Organization.id == org.id)
        )
        found_org = result.scalar_one_or_none()
        assert found_org is not None
        assert found_org.deleted_at is not None

    @pytest.mark.asyncio
    async def test_organization_default_values(self, db_session):
        """Test organization default values."""
        org = Organization(name="Minimal Org")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

        assert org.description is None
        assert org.settings is None
        assert org.max_users is None
        assert org.max_devices is None
        assert org.is_active is True  # Default value


class TestPermissionModel:
    """Test Permission model."""

    @pytest.mark.asyncio
    async def test_create_permission(self, db_session):
        """Test creating a permission."""
        perm = Permission(
            name="test:read",
            display_name="Test Read",
            description="Read test resources",
            resource="test",
            action="read"
        )
        db_session.add(perm)
        await db_session.commit()
        await db_session.refresh(perm)

        assert perm.id is not None
        assert perm.name == "test:read"
        assert perm.display_name == "Test Read"
        assert perm.resource == "test"
        assert perm.action == "read"

    @pytest.mark.asyncio
    async def test_permission_unique_name(self, db_session):
        """Test that permission names must be unique."""
        perm1 = Permission(
            name="duplicate",
            display_name="First",
            description="First permission",
            resource="test",
            action="read"
        )
        perm2 = Permission(
            name="duplicate",
            display_name="Second",
            description="Second permission",
            resource="test",
            action="write"
        )

        db_session.add(perm1)
        await db_session.commit()

        db_session.add(perm2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_permission_required_fields(self, db_session):
        """Test that permission requires certain fields."""
        # Missing display_name should fail
        with pytest.raises(IntegrityError):
            perm = Permission(
                name="test:read",
                description="Test permission",
                resource="test",
                action="read"
            )
            db_session.add(perm)
            await db_session.commit()


class TestRoleModel:
    """Test Role model."""

    @pytest.mark.asyncio
    async def test_create_role(self, db_session):
        """Test creating a role."""
        role = Role(
            name="Test Role",
            description="Test role description"
        )
        db_session.add(role)
        await db_session.commit()
        await db_session.refresh(role)

        assert role.id is not None
        assert role.name == "Test Role"
        assert role.description == "Test role description"
        assert role.is_system_role is False

    @pytest.mark.asyncio
    async def test_role_unique_name(self, db_session):
        """Test that role names must be unique."""
        role1 = Role(name="Admin", description="First admin")
        role2 = Role(name="Admin", description="Second admin")

        db_session.add(role1)
        await db_session.commit()

        db_session.add(role2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_role_permissions_relationship(self, db_session):
        """Test role-permission many-to-many relationship."""
        # Create permissions
        perm1 = Permission(
            name="test:read",
            display_name="Test Read",
            description="Read permission",
            resource="test",
            action="read"
        )
        perm2 = Permission(
            name="test:write",
            display_name="Test Write",
            description="Write permission",
            resource="test",
            action="write"
        )
        db_session.add_all([perm1, perm2])
        await db_session.commit()

        # Create role with permissions
        role = Role(
            name="Test Role",
            description="Role with permissions",
            permissions=[perm1, perm2]
        )
        db_session.add(role)
        await db_session.commit()
        await db_session.refresh(role)

        assert len(role.permissions) == 2
        assert perm1 in role.permissions
        assert perm2 in role.permissions

    @pytest.mark.asyncio
    async def test_role_system_role_flag(self, db_session):
        """Test system role flag."""
        system_role = Role(
            name="System Admin",
            description="System administrator",
            is_system_role=True
        )
        db_session.add(system_role)
        await db_session.commit()
        await db_session.refresh(system_role)

        assert system_role.is_system_role is True


class TestUserModel:
    """Test User model."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session, test_organization):
        """Test creating a user."""
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            password_hash=get_password_hash("password123"),
            organization_id=test_organization.id
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.organization_id == test_organization.id
        assert user.is_active is True  # Default
        assert user.is_verified is False  # Default
        assert user.email_verified is False  # Default

    @pytest.mark.asyncio
    async def test_user_unique_email(self, db_session, test_organization):
        """Test that user emails must be unique."""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )
        user2 = User(
            email="duplicate@example.com",
            username="user2",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )

        db_session.add(user1)
        await db_session.commit()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_unique_username(self, db_session, test_organization):
        """Test that usernames must be unique."""
        user1 = User(
            email="user1@example.com",
            username="duplicate_username",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )
        user2 = User(
            email="user2@example.com",
            username="duplicate_username",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )

        db_session.add(user1)
        await db_session.commit()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_organization_relationship(self, db_session, test_organization):
        """Test user-organization relationship."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Test relationship
        assert user.organization is not None
        assert user.organization.id == test_organization.id
        assert user.organization.name == test_organization.name

    @pytest.mark.asyncio
    async def test_user_roles_relationship(self, db_session, test_organization, test_permissions):
        """Test user-role many-to-many relationship."""
        # Create roles
        role1 = Role(name="Admin", description="Administrator", permissions=test_permissions)
        role2 = Role(name="User", description="Regular user", permissions=test_permissions[:2])
        db_session.add_all([role1, role2])
        await db_session.commit()

        # Create user with roles
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id,
            roles=[role1, role2]
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert len(user.roles) == 2
        assert role1 in user.roles
        assert role2 in user.roles

    @pytest.mark.asyncio
    async def test_user_full_name_property(self, db_session, test_organization):
        """Test user full_name computed property."""
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="John",
            last_name="Doe",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )

        assert user.full_name == "John Doe"

        # Test with missing last name
        user.last_name = None
        assert user.full_name == "John"

        # Test with missing first name
        user.first_name = None
        user.last_name = "Doe"
        assert user.full_name == "Doe"

        # Test with both missing
        user.first_name = None
        user.last_name = None
        assert user.full_name == ""

    @pytest.mark.asyncio
    async def test_user_mfa_fields(self, db_session, test_organization):
        """Test user MFA related fields."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id,
            mfa_enabled=True,
            mfa_secret="test_secret",
            backup_codes=["code1", "code2", "code3"]
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.mfa_enabled is True
        assert user.mfa_secret == "test_secret"
        assert user.backup_codes == ["code1", "code2", "code3"]

    @pytest.mark.asyncio
    async def test_user_security_fields(self, db_session, test_organization):
        """Test user security related fields."""
        now = datetime.now(timezone.utc)
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id,
            failed_login_attempts=3,
            locked_until=now + timedelta(hours=1),
            password_changed_at=now
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.failed_login_attempts == 3
        assert user.locked_until is not None
        assert user.password_changed_at is not None

    @pytest.mark.asyncio
    async def test_user_soft_delete(self, db_session, test_organization):
        """Test user soft delete."""
        user = User(
            email="delete@example.com",
            username="deleteuser",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Soft delete
        user.deleted_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Should still exist in database
        result = await db_session.execute(
            select(User).where(User.id == user.id)
        )
        found_user = result.scalar_one_or_none()
        assert found_user is not None
        assert found_user.deleted_at is not None


class TestRefreshTokenModel:
    """Test RefreshToken model."""

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, db_session, test_user):
        """Test creating a refresh token."""
        token = RefreshToken(
            jti=str(uuid4()),
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            client_info="Test Client"
        )
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        assert token.id is not None
        assert token.user_id == test_user.id
        assert token.jti is not None
        assert token.expires_at is not None
        assert token.is_revoked is False

    @pytest.mark.asyncio
    async def test_refresh_token_user_relationship(self, db_session, test_user):
        """Test refresh token user relationship."""
        token = RefreshToken(
            jti=str(uuid4()),
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        assert token.user is not None
        assert token.user.id == test_user.id
        assert token.user.email == test_user.email

    @pytest.mark.asyncio
    async def test_refresh_token_revocation(self, db_session, test_user):
        """Test refresh token revocation."""
        token = RefreshToken(
            jti=str(uuid4()),
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        # Revoke token
        token.is_revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        await db_session.commit()

        assert token.is_revoked is True
        assert token.revoked_at is not None

    @pytest.mark.asyncio
    async def test_refresh_token_unique_jti(self, db_session, test_user):
        """Test that refresh token JTIs must be unique."""
        jti = str(uuid4())

        token1 = RefreshToken(
            jti=jti,
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        token2 = RefreshToken(
            jti=jti,  # Same JTI
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )

        db_session.add(token1)
        await db_session.commit()

        db_session.add(token2)
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestUserSessionModel:
    """Test UserSession model."""

    @pytest.mark.asyncio
    async def test_create_user_session(self, db_session, test_user):
        """Test creating a user session."""
        session = UserSession(
            session_id=str(uuid4()),
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Test Browser",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Test Browser"
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_user_session_user_relationship(self, db_session, test_user):
        """Test user session user relationship."""
        session = UserSession(
            session_id=str(uuid4()),
            user_id=test_user.id,
            ip_address="192.168.1.1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.user is not None
        assert session.user.id == test_user.id
        assert session.user.email == test_user.email

    @pytest.mark.asyncio
    async def test_user_session_deactivation(self, db_session, test_user):
        """Test user session deactivation."""
        session = UserSession(
            session_id=str(uuid4()),
            user_id=test_user.id,
            ip_address="192.168.1.1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Deactivate session
        session.is_active = False
        session.ended_at = datetime.now(timezone.utc)
        await db_session.commit()

        assert session.is_active is False
        assert session.ended_at is not None

    @pytest.mark.asyncio
    async def test_user_session_unique_session_id(self, db_session, test_user):
        """Test that session IDs must be unique."""
        session_id = str(uuid4())

        session1 = UserSession(
            session_id=session_id,
            user_id=test_user.id,
            ip_address="192.168.1.1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        session2 = UserSession(
            session_id=session_id,  # Same session ID
            user_id=test_user.id,
            ip_address="192.168.1.2",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )

        db_session.add(session1)
        await db_session.commit()

        db_session.add(session2)
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestModelRelationships:
    """Test complex model relationships and cascades."""

    @pytest.mark.asyncio
    async def test_user_cascade_to_sessions_and_tokens(self, db_session, test_organization):
        """Test that user deletion cascades to sessions and tokens."""
        # Create user
        user = User(
            email="cascade@example.com",
            username="cascadeuser",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create related entities
        session = UserSession(
            session_id=str(uuid4()),
            user_id=user.id,
            ip_address="192.168.1.1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        token = RefreshToken(
            jti=str(uuid4()),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db_session.add_all([session, token])
        await db_session.commit()

        # Count related entities
        session_count = await db_session.scalar(
            select(func.count(UserSession.id)).where(UserSession.user_id == user.id)
        )
        token_count = await db_session.scalar(
            select(func.count(RefreshToken.id)).where(RefreshToken.user_id == user.id)
        )

        assert session_count == 1
        assert token_count == 1

        # Delete user (should cascade)
        await db_session.delete(user)
        await db_session.commit()

        # Check that related entities are also deleted
        session_count_after = await db_session.scalar(
            select(func.count(UserSession.id)).where(UserSession.user_id == user.id)
        )
        token_count_after = await db_session.scalar(
            select(func.count(RefreshToken.id)).where(RefreshToken.user_id == user.id)
        )

        assert session_count_after == 0
        assert token_count_after == 0

    @pytest.mark.asyncio
    async def test_organization_users_relationship(self, db_session, test_organization):
        """Test organization to users relationship."""
        # Create multiple users for the organization
        users = []
        for i in range(3):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password_hash=get_password_hash("password"),
                organization_id=test_organization.id
            )
            users.append(user)

        db_session.add_all(users)
        await db_session.commit()

        # Test relationship
        result = await db_session.execute(
            select(Organization).where(Organization.id == test_organization.id)
        )
        org = result.scalar_one()

        assert len(org.users) == 3
        for user in users:
            assert user in org.users

    @pytest.mark.asyncio
    async def test_role_users_relationship(self, db_session, test_organization, test_permissions):
        """Test role to users relationship through many-to-many."""
        # Create role
        role = Role(name="Test Role", description="Test", permissions=test_permissions[:2])
        db_session.add(role)
        await db_session.commit()

        # Create users with this role
        users = []
        for i in range(2):
            user = User(
                email=f"roleuser{i}@example.com",
                username=f"roleuser{i}",
                password_hash=get_password_hash("password"),
                organization_id=test_organization.id,
                roles=[role]
            )
            users.append(user)

        db_session.add_all(users)
        await db_session.commit()

        # Test relationship
        result = await db_session.execute(
            select(Role).where(Role.id == role.id)
        )
        role_with_users = result.scalar_one()

        assert len(role_with_users.users) == 2
        for user in users:
            assert user in role_with_users.users


class TestModelValidation:
    """Test model validation and constraints."""

    @pytest.mark.asyncio
    async def test_user_email_validation(self, db_session, test_organization):
        """Test that invalid email formats should be handled gracefully."""
        # Note: Email validation is typically done at the Pydantic level,
        # but we test database behavior here
        user = User(
            email="not-an-email",  # Invalid format
            username="testuser",
            password_hash=get_password_hash("password"),
            organization_id=test_organization.id
        )
        db_session.add(user)
        # Should not raise exception at database level (validation in schemas)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_permission_name_format(self, db_session):
        """Test permission name format constraints."""
        # Valid permission name
        valid_perm = Permission(
            name="valid:action",
            display_name="Valid Action",
            description="Valid permission",
            resource="valid",
            action="action"
        )
        db_session.add(valid_perm)
        await db_session.commit()

        # Should succeed
        assert valid_perm.id is not None

    @pytest.mark.asyncio
    async def test_user_required_fields(self, db_session, test_organization):
        """Test that user requires certain fields."""
        # Missing email should fail
        with pytest.raises(IntegrityError):
            user = User(
                username="testuser",
                password_hash=get_password_hash("password"),
                organization_id=test_organization.id
            )
            db_session.add(user)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_role_required_fields(self, db_session):
        """Test that role requires certain fields."""
        # Missing name should fail
        with pytest.raises(IntegrityError):
            role = Role(description="Role without name")
            db_session.add(role)
            await db_session.commit()
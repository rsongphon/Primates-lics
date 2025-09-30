"""
LICS Backend Authentication Services

Business logic layer for authentication, user management, and RBAC operations.
Follows Documentation.md Section 10.1-10.2 for JWT and security patterns.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import db_manager
from app.core.logging import get_logger, PerformanceLogger
from app.core.security import (
    create_access_token, create_refresh_token, verify_password,
    get_password_hash, verify_token, create_password_reset_token_jwt,
    generate_password_reset_token
)
from app.models.auth import (
    User, Role, Permission, UserSession, RefreshToken,
    user_roles, role_permissions
)
from app.repositories.base import BaseRepository
from app.schemas.auth import (
    UserRegistrationRequest, LoginRequest, LoginResponse,
    TokenPair, UserProfile, PasswordResetRequest, PasswordResetConfirm,
    PasswordChangeRequest, UserUpdateRequest, RoleCreateRequest,
    UserRoleAssignment, MFASetupResponse
)
from app.services.base import (
    BaseService, ServiceError, ValidationError, NotFoundError,
    ConflictError, PermissionError
)

logger = get_logger(__name__)
perf_logger = PerformanceLogger(logger)


# ===== CUSTOM EXCEPTIONS =====

class AuthenticationError(ServiceError):
    """Exception raised for authentication failures."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_FAILED")


class InvalidTokenError(ServiceError):
    """Exception raised for invalid or expired tokens."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, "INVALID_TOKEN")


class AccountLockedError(ServiceError):
    """Exception raised when account is locked."""

    def __init__(self, message: str = "Account is locked due to too many failed attempts"):
        super().__init__(message, "ACCOUNT_LOCKED")


class MFARequiredError(ServiceError):
    """Exception raised when MFA is required."""

    def __init__(self, message: str = "Multi-factor authentication required"):
        super().__init__(message, "MFA_REQUIRED")


class WeakPasswordError(ValidationError):
    """Exception raised for weak passwords."""

    def __init__(self, message: str = "Password does not meet security requirements"):
        super().__init__(message, "password")


# ===== REPOSITORY CLASSES =====

class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db_session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db_session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by email verification token."""
        result = await self.db_session.execute(
            select(User).where(User.email_verification_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by password reset token."""
        result = await self.db_session.execute(
            select(User).where(
                and_(
                    User.password_reset_token == token,
                    User.password_reset_expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_login_info(self, user_id: uuid.UUID, ip_address: str) -> None:
        """Update user login information."""
        await self.db_session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.utcnow(),
                last_login_ip=ip_address,
                failed_login_attempts=0,
                account_locked_until=None
            )
        )

    async def increment_failed_attempts(self, user_id: uuid.UUID) -> int:
        """Increment failed login attempts and return new count."""
        user = await self.get_by_id(user_id)
        if not user:
            return 0

        new_count = user.failed_login_attempts + 1
        lock_until = None

        # Lock account after max attempts
        if new_count >= settings.MAX_LOGIN_ATTEMPTS:
            lock_until = datetime.utcnow() + timedelta(minutes=settings.ACCOUNT_LOCK_DURATION_MINUTES)

        await self.db_session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                failed_login_attempts=new_count,
                account_locked_until=lock_until
            )
        )

        return new_count


class RoleRepository(BaseRepository[Role]):
    """Repository for Role model operations."""

    async def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        result = await self.db_session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name)
        )
        return result.scalar_one_or_none()

    async def get_default_roles(self) -> List[Role]:
        """Get default roles for new users."""
        result = await self.db_session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.is_default == True)
        )
        return list(result.scalars().all())


class PermissionRepository(BaseRepository[Permission]):
    """Repository for Permission model operations."""

    async def get_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        result = await self.db_session.execute(
            select(Permission).where(Permission.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_resource_action(self, resource: str, action: str) -> Optional[Permission]:
        """Get permission by resource and action."""
        result = await self.db_session.execute(
            select(Permission).where(
                and_(Permission.resource == resource, Permission.action == action)
            )
        )
        return result.scalar_one_or_none()


class SessionRepository(BaseRepository[UserSession]):
    """Repository for UserSession model operations."""

    async def get_by_token(self, session_token: str) -> Optional[UserSession]:
        """Get session by token."""
        result = await self.db_session.execute(
            select(UserSession).where(UserSession.session_token == session_token)
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(self, user_id: uuid.UUID, active_only: bool = True) -> List[UserSession]:
        """Get all sessions for a user."""
        query = select(UserSession).where(UserSession.user_id == user_id)

        if active_only:
            query = query.where(
                and_(
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            )

        result = await self.db_session.execute(query.order_by(UserSession.last_activity_at.desc()))
        return list(result.scalars().all())

    async def deactivate_sessions(self, session_ids: List[uuid.UUID]) -> int:
        """Deactivate multiple sessions."""
        result = await self.db_session.execute(
            update(UserSession)
            .where(UserSession.id.in_(session_ids))
            .values(is_active=False)
        )
        return result.rowcount

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        result = await self.db_session.execute(
            delete(UserSession).where(UserSession.expires_at < datetime.utcnow())
        )
        return result.rowcount


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for RefreshToken model operations."""

    async def get_by_token_id(self, token_id: str) -> Optional[RefreshToken]:
        """Get refresh token by token ID."""
        result = await self.db_session.execute(
            select(RefreshToken).where(RefreshToken.token_id == token_id)
        )
        return result.scalar_one_or_none()

    async def revoke_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke all refresh tokens for a user."""
        result = await self.db_session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        return result.rowcount

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired refresh tokens."""
        result = await self.db_session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )
        return result.rowcount


# ===== AUTHENTICATION SERVICE =====

class AuthService:
    """Main authentication service handling login, logout, and token operations."""

    def __init__(self):
        self.user_repository_class = UserRepository
        self.session_repository_class = SessionRepository
        self.refresh_token_repository_class = RefreshTokenRepository

    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return self.user_repository_class(User, session)

    def get_session_repository(self, session: AsyncSession) -> SessionRepository:
        return self.session_repository_class(UserSession, session)

    def get_refresh_token_repository(self, session: AsyncSession) -> RefreshTokenRepository:
        return self.refresh_token_repository_class(RefreshToken, session)

    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, TokenPair, str]:
        """
        Authenticate user and create session.

        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (user, token_pair, session_id)

        Raises:
            AuthenticationError: If authentication fails
            AccountLockedError: If account is locked
            MFARequiredError: If MFA is required
        """
        with perf_logger.log_execution_time("authenticate_user"):
            async with db_manager.session_scope() as session:
                user_repo = self.get_user_repository(session)
                session_repo = self.get_session_repository(session)
                token_repo = self.get_refresh_token_repository(session)

                # Get user by email
                user = await user_repo.get_by_email(email)
                if not user:
                    raise AuthenticationError("Invalid email or password")

                # Check if account is locked
                if user.account_locked_until and user.account_locked_until > datetime.utcnow():
                    raise AccountLockedError(
                        f"Account locked until {user.account_locked_until.isoformat()}"
                    )

                # Check if user is active
                if not user.is_active:
                    raise AuthenticationError("Account is deactivated")

                # Verify password
                if not verify_password(password, user.password_hash):
                    # Increment failed attempts
                    await user_repo.increment_failed_attempts(user.id)
                    await session.commit()
                    raise AuthenticationError("Invalid email or password")

                # Check if MFA is required
                if user.mfa_enabled:
                    # For now, we'll handle MFA in a separate step
                    # This would typically return a temporary token requiring MFA completion
                    pass

                # Create session
                session_token = secrets.token_urlsafe(32)
                user_session = UserSession(
                    user_id=user.id,
                    session_token=session_token,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    expires_at=datetime.utcnow() + timedelta(seconds=settings.SESSION_EXPIRE_SECONDS),
                    last_activity_at=datetime.utcnow(),
                    is_active=True
                )
                session.add(user_session)

                # Create tokens
                access_token = create_access_token(
                    data={
                        "sub": str(user.id),
                        "email": user.email,
                        "organization_id": str(user.organization_id),
                        "permissions": [perm.name for role in user.roles for perm in role.permissions]
                    }
                )

                refresh_token_id = secrets.token_urlsafe(32)
                refresh_token = create_refresh_token(data={"sub": str(user.id), "token_id": refresh_token_id})

                # Store refresh token
                refresh_token_record = RefreshToken(
                    user_id=user.id,
                    token_id=refresh_token_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    expires_at=datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE_SECONDS),
                    is_revoked=False
                )
                session.add(refresh_token_record)

                # Update user login info
                await user_repo.update_login_info(user.id, ip_address or "unknown")

                await session.commit()

                token_pair = TokenPair(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type="bearer",
                    access_expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    refresh_expires_in=settings.REFRESH_TOKEN_EXPIRE_SECONDS
                )

                return user, token_pair, session_token

    async def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            New token pair

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        with perf_logger.log_execution_time("refresh_access_token"):
            # Verify refresh token
            try:
                payload = verify_token(refresh_token, token_type="refresh")
                user_id = uuid.UUID(payload.get("sub"))
                token_id = payload.get("token_id")
            except Exception as e:
                raise InvalidTokenError("Invalid refresh token") from e

            async with db_manager.session_scope() as session:
                user_repo = self.get_user_repository(session)
                token_repo = self.get_refresh_token_repository(session)

                # Check if refresh token exists and is valid
                token_record = await token_repo.get_by_token_id(token_id)
                if not token_record or token_record.is_revoked:
                    raise InvalidTokenError("Refresh token revoked")

                if token_record.expires_at < datetime.utcnow():
                    raise InvalidTokenError("Refresh token expired")

                # Get user
                user = await user_repo.get_by_id(user_id)
                if not user or not user.is_active:
                    raise InvalidTokenError("User not found or inactive")

                # Update last used timestamp
                token_record.last_used_at = datetime.utcnow()

                # Create new access token
                access_token = create_access_token(
                    data={
                        "sub": str(user.id),
                        "email": user.email,
                        "organization_id": str(user.organization_id),
                        "permissions": [perm.name for role in user.roles for perm in role.permissions]
                    }
                )

                await session.commit()

                return TokenPair(
                    access_token=access_token,
                    refresh_token=refresh_token,  # Keep the same refresh token
                    token_type="bearer",
                    access_expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    refresh_expires_in=int((token_record.expires_at - datetime.utcnow()).total_seconds())
                )

    async def logout_user(
        self,
        user_id: uuid.UUID,
        session_token: Optional[str] = None,
        everywhere: bool = False
    ) -> bool:
        """
        Logout user by deactivating sessions.

        Args:
            user_id: User ID
            session_token: Specific session token to logout (optional)
            everywhere: Logout from all devices

        Returns:
            True if logout successful
        """
        with perf_logger.log_execution_time("logout_user"):
            async with db_manager.session_scope() as session:
                session_repo = self.get_session_repository(session)
                token_repo = self.get_refresh_token_repository(session)

                if everywhere:
                    # Deactivate all user sessions
                    user_sessions = await session_repo.get_user_sessions(user_id, active_only=True)
                    session_ids = [s.id for s in user_sessions]
                    if session_ids:
                        await session_repo.deactivate_sessions(session_ids)

                    # Revoke all refresh tokens
                    await token_repo.revoke_user_tokens(user_id)
                else:
                    # Deactivate specific session
                    if session_token:
                        user_session = await session_repo.get_by_token(session_token)
                        if user_session and user_session.user_id == user_id:
                            await session_repo.deactivate_sessions([user_session.id])

                await session.commit()
                return True

    async def verify_session(self, session_token: str) -> Optional[User]:
        """
        Verify user session and return user.

        Args:
            session_token: Session token

        Returns:
            User if session is valid, None otherwise
        """
        async with db_manager.session_scope() as session:
            session_repo = self.get_session_repository(session)
            user_repo = self.get_user_repository(session)

            user_session = await session_repo.get_by_token(session_token)
            if not user_session:
                return None

            if not user_session.is_active or user_session.expires_at < datetime.utcnow():
                return None

            # Update last activity
            user_session.last_activity_at = datetime.utcnow()
            await session.commit()

            return await user_repo.get_by_id(user_session.user_id)


# ===== USER SERVICE =====

class UserService(BaseService[User, UserRepository]):
    """Service for user management operations."""

    def __init__(self):
        super().__init__(UserRepository, User)
        self.role_repository_class = RoleRepository

    def get_role_repository(self, session: AsyncSession) -> RoleRepository:
        return self.role_repository_class(Role, session)

    async def register_user(self, registration_data: UserRegistrationRequest) -> User:
        """
        Register new user with default roles.

        Args:
            registration_data: User registration data

        Returns:
            Created user

        Raises:
            ConflictError: If email or username already exists
            ValidationError: If data validation fails
        """
        with perf_logger.log_execution_time("register_user"):
            async with db_manager.session_scope() as session:
                user_repo = self.get_repository(session)
                role_repo = self.get_role_repository(session)

                # Check if email already exists
                existing_user = await user_repo.get_by_email(registration_data.email)
                if existing_user:
                    raise ConflictError("Email address already registered")

                # Check if username already exists
                existing_user = await user_repo.get_by_username(registration_data.username)
                if existing_user:
                    raise ConflictError("Username already taken")

                # Hash password
                password_hash = get_password_hash(registration_data.password)

                # Generate verification token
                verification_token = create_email_verification_token(registration_data.email)

                # Create user
                user_data = {
                    "email": registration_data.email,
                    "username": registration_data.username,
                    "password_hash": password_hash,
                    "first_name": registration_data.first_name,
                    "last_name": registration_data.last_name,
                    "organization_id": registration_data.organization_id,
                    "timezone": registration_data.timezone,
                    "language": registration_data.language,
                    "is_active": True,
                    "is_verified": False,  # Require email verification
                    "is_superuser": False,
                    "email_verification_token": verification_token,
                    "failed_login_attempts": 0,
                    "mfa_enabled": False
                }

                user = await user_repo.create(**user_data)

                # Assign default roles
                default_roles = await role_repo.get_default_roles()
                if default_roles:
                    user.roles.extend(default_roles)

                await session.commit()

                # TODO: Send verification email

                return user

    async def verify_email(self, verification_token: str) -> User:
        """
        Verify user email with verification token.

        Args:
            verification_token: Email verification token

        Returns:
            Updated user

        Raises:
            InvalidTokenError: If token is invalid
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_repository(session)

            user = await user_repo.get_by_verification_token(verification_token)
            if not user:
                raise InvalidTokenError("Invalid verification token")

            # Verify token
            try:
                payload = verify_token(verification_token, token_type="email_verification")
                if payload.get("email") != user.email:
                    raise InvalidTokenError("Token email mismatch")
            except Exception as e:
                raise InvalidTokenError("Invalid verification token") from e

            # Update user
            user.is_verified = True
            user.email_verified_at = datetime.utcnow()
            user.email_verification_token = None

            await session.commit()
            return user

    async def update_profile(
        self,
        user_id: uuid.UUID,
        update_data: UserUpdateRequest,
        current_user_id: Optional[uuid.UUID] = None
    ) -> User:
        """
        Update user profile.

        Args:
            user_id: User ID to update
            update_data: Profile update data
            current_user_id: ID of user making the update

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
            PermissionError: If user doesn't have permission
        """
        # Check permissions (users can update their own profile)
        if current_user_id != user_id:
            # TODO: Check if current user has admin permissions
            raise PermissionError("Cannot update other user's profile")

        return await self.update(user_id, update_data.dict(exclude_unset=True), current_user_id=current_user_id)

    async def assign_roles(
        self,
        user_id: uuid.UUID,
        role_ids: List[uuid.UUID],
        current_user_id: Optional[uuid.UUID] = None
    ) -> User:
        """
        Assign roles to user.

        Args:
            user_id: User ID
            role_ids: List of role IDs to assign
            current_user_id: ID of user making the assignment

        Returns:
            Updated user with roles

        Raises:
            NotFoundError: If user or roles not found
            PermissionError: If user doesn't have permission
        """
        # TODO: Check admin permissions for current_user_id

        async with db_manager.session_scope() as session:
            user_repo = self.get_repository(session)
            role_repo = self.get_role_repository(session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            roles = await role_repo.get_by_ids(role_ids)
            if len(roles) != len(role_ids):
                missing_ids = set(role_ids) - {role.id for role in roles}
                raise NotFoundError("Role", f"Roles not found: {missing_ids}")

            # Replace user roles
            user.roles = roles

            await session.commit()
            return user

    async def get_user_permissions(self, user_id: uuid.UUID) -> Set[str]:
        """
        Get all permissions for a user (from their roles).

        Args:
            user_id: User ID

        Returns:
            Set of permission names

        Raises:
            NotFoundError: If user not found
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_repository(session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            permissions = set()
            for role in user.roles:
                for permission in role.permissions:
                    permissions.add(permission.name)

            return permissions


# ===== PASSWORD SERVICE =====

class PasswordService:
    """Service for password management operations."""

    def __init__(self):
        self.user_repository_class = UserRepository

    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return self.user_repository_class(User, session)

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            NotFoundError: If user not found
            AuthenticationError: If current password is incorrect
            WeakPasswordError: If new password is weak
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_user_repository(session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            # Verify current password
            if not verify_password(current_password, user.password_hash):
                raise AuthenticationError("Current password is incorrect")

            # TODO: Add password strength validation
            # if not self._is_password_strong(new_password):
            #     raise WeakPasswordError()

            # Hash new password
            new_password_hash = get_password_hash(new_password)

            # Update password
            user.password_hash = new_password_hash

            await session.commit()
            return True

    async def request_password_reset(self, email: str) -> str:
        """
        Request password reset for user.

        Args:
            email: User email

        Returns:
            Reset token (for testing - in production this would be sent via email)

        Raises:
            NotFoundError: If user not found
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_user_repository(session)

            user = await user_repo.get_by_email(email)
            if not user:
                # Don't reveal if email exists or not
                return "reset_token_placeholder"

            # Generate reset token
            reset_token = create_password_reset_token(email)

            # Set token and expiry
            user.password_reset_token = reset_token
            user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)

            await session.commit()

            # TODO: Send reset email

            return reset_token

    async def reset_password(self, reset_token: str, new_password: str) -> bool:
        """
        Reset password using reset token.

        Args:
            reset_token: Password reset token
            new_password: New password

        Returns:
            True if password reset successfully

        Raises:
            InvalidTokenError: If reset token is invalid or expired
            WeakPasswordError: If new password is weak
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_user_repository(session)

            # Get user by reset token
            user = await user_repo.get_by_reset_token(reset_token)
            if not user:
                raise InvalidTokenError("Invalid or expired reset token")

            # Verify token
            try:
                payload = verify_token(reset_token, token_type="password_reset")
                if payload.get("email") != user.email:
                    raise InvalidTokenError("Token email mismatch")
            except Exception as e:
                raise InvalidTokenError("Invalid reset token") from e

            # TODO: Add password strength validation

            # Hash new password
            new_password_hash = get_password_hash(new_password)

            # Update password and clear reset token
            user.password_hash = new_password_hash
            user.password_reset_token = None
            user.password_reset_expires_at = None
            user.failed_login_attempts = 0  # Reset failed attempts
            user.account_locked_until = None  # Unlock account

            await session.commit()
            return True


# ===== MFA SERVICE =====

class MFAService:
    """Service for multi-factor authentication operations."""

    def __init__(self):
        self.user_repository_class = UserRepository

    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return self.user_repository_class(User, session)

    async def setup_mfa(self, user_id: uuid.UUID, password: str) -> MFASetupResponse:
        """
        Setup MFA for user.

        Args:
            user_id: User ID
            password: Current password for verification

        Returns:
            MFA setup response with secret and QR code

        Raises:
            NotFoundError: If user not found
            AuthenticationError: If password is incorrect
            ConflictError: If MFA already enabled
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_user_repository(session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            # Verify password
            if not verify_password(password, user.password_hash):
                raise AuthenticationError("Current password is incorrect")

            if user.mfa_enabled:
                raise ConflictError("MFA is already enabled")

            # Generate MFA secret
            secret = generate_mfa_secret()

            # Generate QR code URL
            qr_code_url = f"otpauth://totp/LICS:{user.email}?secret={secret}&issuer=LICS"

            # Generate backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(8)]

            # Store secret (but don't enable MFA yet - user needs to confirm)
            user.mfa_secret = secret

            await session.commit()

            return MFASetupResponse(
                secret=secret,
                qr_code_url=qr_code_url,
                backup_codes=backup_codes
            )

    async def confirm_mfa(self, user_id: uuid.UUID, code: str) -> bool:
        """
        Confirm MFA setup with verification code.

        Args:
            user_id: User ID
            code: 6-digit verification code

        Returns:
            True if MFA enabled successfully

        Raises:
            NotFoundError: If user not found
            ValidationError: If code is invalid
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_user_repository(session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            if not user.mfa_secret:
                raise ValidationError("MFA not set up")

            # Verify code
            if not verify_mfa_code(user.mfa_secret, code):
                raise ValidationError("Invalid verification code")

            # Enable MFA
            user.mfa_enabled = True

            await session.commit()
            return True

    async def disable_mfa(self, user_id: uuid.UUID, password: str, code: str) -> bool:
        """
        Disable MFA for user.

        Args:
            user_id: User ID
            password: Current password for verification
            code: MFA code for verification

        Returns:
            True if MFA disabled successfully

        Raises:
            NotFoundError: If user not found
            AuthenticationError: If password is incorrect
            ValidationError: If MFA code is invalid
        """
        async with db_manager.session_scope() as session:
            user_repo = self.get_user_repository(session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", user_id)

            # Verify password
            if not verify_password(password, user.password_hash):
                raise AuthenticationError("Current password is incorrect")

            if not user.mfa_enabled:
                raise ValidationError("MFA is not enabled")

            # Verify MFA code
            if not verify_mfa_code(user.mfa_secret, code):
                raise ValidationError("Invalid MFA code")

            # Disable MFA
            user.mfa_enabled = False
            user.mfa_secret = None

            await session.commit()
            return True


# ===== ROLE SERVICE =====

class RoleService(BaseService[Role, RoleRepository]):
    """Service for role management operations."""

    def __init__(self):
        super().__init__(RoleRepository, Role)
        self.permission_repository_class = PermissionRepository

    def get_permission_repository(self, session: AsyncSession) -> PermissionRepository:
        return self.permission_repository_class(Permission, session)

    async def create_role(
        self,
        role_data: RoleCreateRequest,
        current_user_id: Optional[uuid.UUID] = None
    ) -> Role:
        """
        Create new role with permissions.

        Args:
            role_data: Role creation data
            current_user_id: ID of user creating the role

        Returns:
            Created role

        Raises:
            ConflictError: If role name already exists
            NotFoundError: If permissions not found
        """
        async with db_manager.session_scope() as session:
            role_repo = self.get_repository(session)
            perm_repo = self.get_permission_repository(session)

            # Check if role name already exists
            existing_role = await role_repo.get_by_name(role_data.name)
            if existing_role:
                raise ConflictError("Role name already exists")

            # Get permissions
            permissions = []
            if role_data.permission_ids:
                permissions = await perm_repo.get_by_ids(role_data.permission_ids)
                if len(permissions) != len(role_data.permission_ids):
                    missing_ids = set(role_data.permission_ids) - {p.id for p in permissions}
                    raise NotFoundError("Permission", f"Permissions not found: {missing_ids}")

            # Create role
            role = await role_repo.create(
                name=role_data.name,
                display_name=role_data.display_name,
                description=role_data.description,
                parent_role_id=role_data.parent_role_id,
                is_system_role=False,
                is_default=False
            )

            # Assign permissions
            role.permissions = permissions

            await session.commit()
            return role

    async def assign_permissions(
        self,
        role_id: uuid.UUID,
        permission_ids: List[uuid.UUID],
        current_user_id: Optional[uuid.UUID] = None
    ) -> Role:
        """
        Assign permissions to role.

        Args:
            role_id: Role ID
            permission_ids: List of permission IDs
            current_user_id: ID of user making the assignment

        Returns:
            Updated role

        Raises:
            NotFoundError: If role or permissions not found
        """
        async with db_manager.session_scope() as session:
            role_repo = self.get_repository(session)
            perm_repo = self.get_permission_repository(session)

            role = await role_repo.get_by_id(role_id)
            if not role:
                raise NotFoundError("Role", role_id)

            permissions = await perm_repo.get_by_ids(permission_ids)
            if len(permissions) != len(permission_ids):
                missing_ids = set(permission_ids) - {p.id for p in permissions}
                raise NotFoundError("Permission", f"Permissions not found: {missing_ids}")

            # Replace role permissions
            role.permissions = permissions

            await session.commit()
            return role


# ===== PERMISSION SERVICE =====

class PermissionService(BaseService[Permission, PermissionRepository]):
    """Service for permission management operations."""

    def __init__(self):
        super().__init__(PermissionRepository, Permission)

    async def create_permission(
        self,
        name: str,
        display_name: str,
        resource: str,
        action: str,
        description: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None
    ) -> Permission:
        """
        Create new permission.

        Args:
            name: Permission name (unique)
            display_name: Human-readable display name
            resource: Resource type
            action: Action on resource
            description: Optional description
            current_user_id: ID of user creating the permission

        Returns:
            Created permission

        Raises:
            ConflictError: If permission already exists
        """
        async with db_manager.session_scope() as session:
            perm_repo = self.get_repository(session)

            # Check if permission already exists
            existing_perm = await perm_repo.get_by_name(name)
            if existing_perm:
                raise ConflictError("Permission name already exists")

            existing_perm = await perm_repo.get_by_resource_action(resource, action)
            if existing_perm:
                raise ConflictError(f"Permission for {resource}:{action} already exists")

            # Create permission
            permission = await perm_repo.create(
                name=name,
                display_name=display_name,
                description=description,
                resource=resource,
                action=action,
                is_system_permission=False
            )

            await session.commit()
            return permission


# ===== SESSION SERVICE =====

class SessionService:
    """Service for session management operations."""

    def __init__(self):
        self.session_repository_class = SessionRepository

    def get_session_repository(self, session: AsyncSession) -> SessionRepository:
        return self.session_repository_class(UserSession, session)

    async def get_user_sessions(self, user_id: uuid.UUID) -> List[UserSession]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of active sessions
        """
        async with db_manager.session_scope() as session:
            session_repo = self.get_session_repository(session)
            return await session_repo.get_user_sessions(user_id, active_only=True)

    async def terminate_sessions(
        self,
        session_ids: List[uuid.UUID],
        current_user_id: uuid.UUID
    ) -> int:
        """
        Terminate specific sessions.

        Args:
            session_ids: List of session IDs to terminate
            current_user_id: ID of user requesting termination

        Returns:
            Number of sessions terminated

        Raises:
            PermissionError: If user doesn't own the sessions
        """
        async with db_manager.session_scope() as session:
            session_repo = self.get_session_repository(session)

            # Verify user owns all sessions
            sessions = await session_repo.get_by_ids(session_ids)
            for user_session in sessions:
                if user_session.user_id != current_user_id:
                    raise PermissionError("Cannot terminate other user's sessions")

            # Terminate sessions
            count = await session_repo.deactivate_sessions(session_ids)
            await session.commit()
            return count

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        async with db_manager.session_scope() as session:
            session_repo = self.get_session_repository(session)
            count = await session_repo.cleanup_expired_sessions()
            await session.commit()
            return count
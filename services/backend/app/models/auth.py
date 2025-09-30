"""
Authentication Models

SQLAlchemy models for user authentication, authorization, and session management.
Implements RBAC (Role-Based Access Control) following Documentation.md Section 6.1.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer,
    String, Table, Text, UUID, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    BaseModel, BaseModelWithSoftDelete, BaseModelWithAudit,
    OrganizationBaseModel, OrganizationMixin, AuditContext
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Junction table for many-to-many relationship between Users and Roles
user_roles = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column('assigned_by', UUID(as_uuid=True), nullable=True),
    Index('idx_user_roles_user_id', 'user_id'),
    Index('idx_user_roles_role_id', 'role_id'),
)

# Junction table for many-to-many relationship between Roles and Permissions
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column('assigned_by', UUID(as_uuid=True), nullable=True),
    Index('idx_role_permissions_role_id', 'role_id'),
    Index('idx_role_permissions_permission_id', 'permission_id'),
)


class User(BaseModelWithSoftDelete, BaseModelWithAudit, OrganizationMixin):
    """
    User model for authentication and authorization.

    Supports multi-tenancy through organization_id and includes comprehensive
    user management features like email verification, password reset, and
    account locking.
    """

    __tablename__ = 'users'

    # Basic user information
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username for the user"
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User's email address (must be unique)"
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Argon2id hashed password"
    )

    # User profile
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="User's first name"
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="User's last name"
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the user account is active"
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the user's email has been verified"
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the user has superuser privileges"
    )

    # Email verification
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Token for email verification"
    )

    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the email was verified"
    )

    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Token for password reset"
    )

    password_reset_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the password reset token expires"
    )

    # Account security
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the user last logged in"
    )

    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address of last login (supports IPv6)"
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of consecutive failed login attempts"
    )

    account_locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the account lock expires (NULL if not locked)"
    )

    # Multi-factor authentication (future use)
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether MFA is enabled for this user"
    )

    mfa_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Encrypted MFA secret"
    )

    # Preferences
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50),
        default="UTC",
        nullable=True,
        doc="User's preferred timezone"
    )

    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        default="en",
        nullable=True,
        doc="User's preferred language (ISO 639-1 code)"
    )

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        doc="Roles assigned to this user"
    )

    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Active sessions for this user"
    )

    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Refresh tokens for this user"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('email', name='uq_users_email'),
        UniqueConstraint('username', name='uq_users_username'),
        Index('idx_users_organization_email', 'organization_id', 'email'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_verification_token', 'email_verification_token'),
        Index('idx_users_reset_token', 'password_reset_token'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    @property
    def is_account_locked(self) -> bool:
        """Check if the account is currently locked."""
        if not self.account_locked_until:
            return False
        return datetime.now(timezone.utc) < self.account_locked_until

    def lock_account(self, duration_minutes: int = 15) -> None:
        """Lock the account for a specified duration."""
        from datetime import timedelta
        self.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

    def unlock_account(self) -> None:
        """Unlock the account."""
        self.account_locked_until = None
        self.failed_login_attempts = 0

    def record_failed_login(self) -> None:
        """Record a failed login attempt."""
        self.failed_login_attempts += 1

    def record_successful_login(self, ip_address: Optional[str] = None) -> None:
        """Record a successful login."""
        self.last_login_at = datetime.now(timezone.utc)
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.account_locked_until = None

    def get_permissions(self) -> List[str]:
        """Get all permissions for this user from their roles."""
        permissions = set()
        for role in self.roles:
            for permission in role.permissions:
                permissions.add(permission.name)
        return list(permissions)

    def has_permission(self, permission_name: str) -> bool:
        """Check if the user has a specific permission."""
        return permission_name in self.get_permissions()

    def has_role(self, role_name: str) -> bool:
        """Check if the user has a specific role."""
        return any(role.name == role_name for role in self.roles)


class Role(BaseModelWithSoftDelete):
    """
    Role model for RBAC system.

    Defines roles that can be assigned to users and permissions
    that can be assigned to roles.
    """

    __tablename__ = 'roles'

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique role name"
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable role name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Description of the role and its purpose"
    )

    # Hierarchy support
    parent_role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('roles.id'),
        nullable=True,
        doc="Parent role for hierarchical permissions"
    )

    # Role metadata
    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is a system-defined role (cannot be deleted)"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this role is assigned by default to new users"
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        doc="Users assigned to this role"
    )

    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        doc="Permissions assigned to this role"
    )

    # Self-referential relationship for hierarchy
    parent_role: Mapped[Optional["Role"]] = relationship(
        "Role",
        remote_side="Role.id",
        back_populates="child_roles"
    )

    child_roles: Mapped[List["Role"]] = relationship(
        "Role",
        back_populates="parent_role"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('name', name='uq_roles_name'),
        Index('idx_roles_parent', 'parent_role_id'),
        Index('idx_roles_system', 'is_system_role'),
        Index('idx_roles_default', 'is_default'),
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"

    def get_all_permissions(self, include_inherited: bool = True) -> List[str]:
        """Get all permissions for this role, optionally including inherited ones."""
        permissions = set()

        # Add direct permissions
        for permission in self.permissions:
            permissions.add(permission.name)

        # Add inherited permissions from parent roles
        if include_inherited and self.parent_role:
            parent_permissions = self.parent_role.get_all_permissions(include_inherited=True)
            permissions.update(parent_permissions)

        return list(permissions)


class Permission(BaseModel):
    """
    Permission model for fine-grained access control.

    Defines specific permissions that can be assigned to roles.
    """

    __tablename__ = 'permissions'

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique permission name (e.g., 'devices:read', 'experiments:create')"
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable permission name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Description of what this permission allows"
    )

    # Permission categorization
    resource: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Resource this permission applies to (e.g., 'devices', 'experiments')"
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Action this permission allows (e.g., 'read', 'create', 'update', 'delete')"
    )

    # Permission metadata
    is_system_permission: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is a system-defined permission (cannot be deleted)"
    )

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        doc="Roles that have this permission"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('name', name='uq_permissions_name'),
        UniqueConstraint('resource', 'action', name='uq_permissions_resource_action'),
        Index('idx_permissions_resource', 'resource'),
        Index('idx_permissions_action', 'action'),
        Index('idx_permissions_system', 'is_system_permission'),
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}')>"


class UserSession(BaseModel):
    """
    User session model for tracking active user sessions.

    Tracks user sessions for security and auditing purposes.
    """

    __tablename__ = 'user_sessions'

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        index=True,
        doc="ID of the user this session belongs to"
    )

    session_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique session token"
    )

    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address of the session (supports IPv6)"
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User agent string of the client"
    )

    # Session timing
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the session expires"
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="When the session was last active"
    )

    # Session status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the session is active"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
        doc="User this session belongs to"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('session_token', name='uq_user_sessions_token'),
        Index('idx_user_sessions_user_id', 'user_id'),
        Index('idx_user_sessions_expires', 'expires_at'),
        Index('idx_user_sessions_active', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def extend_session(self, hours: int = 24) -> None:
        """Extend the session expiration time."""
        from datetime import timedelta
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.last_activity_at = datetime.now(timezone.utc)

    def revoke(self) -> None:
        """Revoke the session."""
        self.is_active = False


class RefreshToken(BaseModel):
    """
    Refresh token model for JWT token rotation.

    Stores refresh tokens for secure token rotation mechanism.
    """

    __tablename__ = 'refresh_tokens'

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        index=True,
        doc="ID of the user this token belongs to"
    )

    token_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique token identifier (JTI)"
    )

    # Token metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address where token was issued"
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User agent string of the client"
    )

    # Token timing
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the token expires"
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the token was last used"
    )

    # Token status
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the token has been revoked"
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the token was revoked"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
        doc="User this token belongs to"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('token_id', name='uq_refresh_tokens_token_id'),
        Index('idx_refresh_tokens_user_id', 'user_id'),
        Index('idx_refresh_tokens_expires', 'expires_at'),
        Index('idx_refresh_tokens_revoked', 'is_revoked'),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked

    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)

    def use_token(self) -> None:
        """Record that the token was used."""
        self.last_used_at = datetime.now(timezone.utc)
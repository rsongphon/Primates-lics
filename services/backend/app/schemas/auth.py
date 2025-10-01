"""
LICS Backend Authentication Schemas

Pydantic schemas for authentication requests and responses.
Follows Documentation.md Section 10.1-10.2 for JWT and RBAC patterns.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

from .base import (
    BaseSchema, BaseCreateSchema, BaseUpdateSchema, BaseFilterSchema,
    BaseEntitySchema, BaseEntityFullSchema, OrganizationEntityFullSchema,
    BaseResponse, PaginatedResponse
)


# ===== TOKEN SCHEMAS =====

class TokenData(BaseSchema):
    """Schema for JWT token claims."""

    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    token_type: str = Field(..., description="Token type (access, refresh, etc.)")
    permissions: Optional[List[str]] = Field(None, description="User permissions")
    organization_id: Optional[str] = Field(None, description="Organization ID")


class AccessTokenResponse(BaseSchema):
    """Schema for access token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token lifetime in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900
            }
        }
    )


class RefreshTokenResponse(BaseSchema):
    """Schema for refresh token response."""

    refresh_token: str = Field(..., description="JWT refresh token")
    expires_in: int = Field(..., description="Token lifetime in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_in": 604800
            }
        }
    )


class TokenPair(BaseSchema):
    """Schema for access and refresh token pair."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    access_expires_in: int = Field(..., description="Access token lifetime in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token lifetime in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "access_expires_in": 900,
                "refresh_expires_in": 604800
            }
        }
    )


# ===== AUTHENTICATION REQUEST SCHEMAS =====

class LoginRequest(BaseSchema):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        description="User password",
        min_length=8,
        max_length=128
    )
    remember_me: bool = Field(
        default=False,
        description="Extend session duration"
    )
    mfa_code: Optional[str] = Field(
        None,
        description="Multi-factor authentication code",
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "researcher@example.com",
                "password": "SecurePassword123!",
                "remember_me": False,
                "mfa_code": "123456"
            }
        }
    )


class LoginResponse(BaseSchema):
    """Schema for successful login response."""

    user: 'UserProfile'
    tokens: TokenPair
    session_id: str = Field(..., description="Session identifier")
    requires_mfa: bool = Field(default=False, description="MFA required for this login")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "researcher@example.com",
                    "username": "researcher1",
                    "first_name": "Jane",
                    "last_name": "Doe"
                },
                "tokens": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "access_expires_in": 900,
                    "refresh_expires_in": 604800
                },
                "session_id": "sess_123456789",
                "requires_mfa": False
            }
        }
    )


class RefreshTokenRequest(BaseSchema):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="JWT refresh token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class LogoutRequest(BaseSchema):
    """Schema for logout request."""

    everywhere: bool = Field(
        default=False,
        description="Logout from all devices"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "everywhere": False
            }
        }
    )


# ===== USER REGISTRATION SCHEMAS =====

class UserRegistrationRequest(BaseCreateSchema):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ...,
        description="Username (3-50 characters, alphanumeric and underscores)",
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$"
    )
    password: str = Field(
        ...,
        description="Password (8-128 characters, must include uppercase, lowercase, number)",
        min_length=8,
        max_length=128
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation (must match password)"
    )
    first_name: Optional[str] = Field(
        None,
        description="First name",
        max_length=100
    )
    last_name: Optional[str] = Field(
        None,
        description="Last name",
        max_length=100
    )
    organization_id: uuid.UUID = Field(
        ...,
        description="Organization ID to associate user with"
    )
    timezone: Optional[str] = Field(
        default="UTC",
        description="User timezone",
        max_length=50
    )
    language: Optional[str] = Field(
        default="en",
        description="User language preference",
        max_length=10
    )

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator('password_confirm')
    @classmethod
    def validate_passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate password confirmation matches password."""
        if 'password' in values and v != values['password']:
            raise ValueError("Passwords do not match")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newuser@example.com",
                "username": "newuser123",
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!",
                "first_name": "John",
                "last_name": "Smith",
                "organization_id": "123e4567-e89b-12d3-a456-426614174000",
                "timezone": "America/New_York",
                "language": "en"
            }
        }
    )


class UserRegistrationResponse(BaseSchema):
    """Schema for user registration response."""

    user: 'UserProfile'
    message: str = Field(..., description="Registration success message")
    verification_required: bool = Field(..., description="Email verification required")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "newuser@example.com",
                    "username": "newuser123",
                    "first_name": "John",
                    "last_name": "Smith"
                },
                "message": "User registered successfully",
                "verification_required": True
            }
        }
    )


# ===== PASSWORD RESET SCHEMAS =====

class PasswordResetRequest(BaseSchema):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User email address")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        }
    )


class PasswordResetConfirm(BaseSchema):
    """Schema for password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation"
    )

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator('password_confirm')
    @classmethod
    def validate_passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate password confirmation matches password."""
        if 'password' in values and v != values['password']:
            raise ValueError("Passwords do not match")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "reset_token_123456789",
                "password": "NewSecurePassword123!",
                "password_confirm": "NewSecurePassword123!"
            }
        }
    )


# ===== EMAIL VERIFICATION SCHEMAS =====

class EmailVerificationRequest(BaseSchema):
    """Schema for email verification request."""

    token: str = Field(..., description="Email verification token")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "verify_token_123456789"
            }
        }
    )


class ResendVerificationRequest(BaseSchema):
    """Schema for resending verification email."""

    email: EmailStr = Field(..., description="User email address")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        }
    )


# ===== USER PROFILE SCHEMAS =====

class UserProfile(BaseEntitySchema):
    """Schema for user profile information."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    is_active: bool = Field(..., description="User is active")
    is_verified: bool = Field(..., description="Email is verified")
    is_superuser: bool = Field(..., description="User has superuser privileges")
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    timezone: Optional[str] = Field(None, description="User timezone")
    language: Optional[str] = Field(None, description="Language preference")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    mfa_enabled: bool = Field(..., description="Multi-factor authentication enabled")
    roles: List['RoleInfo'] = Field(default=[], description="User roles")
    permissions: Set[str] = Field(default=set(), description="Effective permissions")

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else self.username

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "researcher@example.com",
                "username": "researcher1",
                "first_name": "Jane",
                "last_name": "Doe",
                "is_active": True,
                "is_verified": True,
                "is_superuser": False,
                "organization_id": "123e4567-e89b-12d3-a456-426614174000",
                "timezone": "America/New_York",
                "language": "en",
                "last_login_at": "2024-01-15T10:30:00Z",
                "mfa_enabled": False,
                "roles": [],
                "permissions": ["experiment:read", "device:read"]
            }
        }
    )


class UserUpdateRequest(BaseUpdateSchema):
    """Schema for user profile update request."""

    first_name: Optional[str] = Field(None, description="First name", max_length=100)
    last_name: Optional[str] = Field(None, description="Last name", max_length=100)
    timezone: Optional[str] = Field(None, description="User timezone", max_length=50)
    language: Optional[str] = Field(None, description="Language preference", max_length=10)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Smith",
                "timezone": "Europe/London",
                "language": "en"
            }
        }
    )


class PasswordChangeRequest(BaseSchema):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128
    )
    new_password_confirm: str = Field(
        ...,
        description="New password confirmation"
    )

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator('new_password_confirm')
    @classmethod
    def validate_passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate password confirmation matches new password."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError("New passwords do not match")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePassword123!",
                "new_password_confirm": "NewSecurePassword123!"
            }
        }
    )


# ===== ROLE AND PERMISSION SCHEMAS =====

class PermissionInfo(BaseEntitySchema):
    """Schema for permission information."""

    name: str = Field(..., description="Permission name")
    display_name: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(None, description="Permission description")
    resource: str = Field(..., description="Resource type")
    action: str = Field(..., description="Action on resource")
    is_system_permission: bool = Field(..., description="System-defined permission")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "experiment:create",
                "display_name": "Create Experiments",
                "description": "Allows creating new experiments",
                "resource": "experiment",
                "action": "create",
                "is_system_permission": True
            }
        }
    )


class RoleInfo(BaseEntitySchema):
    """Schema for role information."""

    name: str = Field(..., description="Role name")
    display_name: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(None, description="Role description")
    is_system_role: bool = Field(..., description="System-defined role")
    is_default: bool = Field(..., description="Default role for new users")
    parent_role_id: Optional[uuid.UUID] = Field(None, description="Parent role ID")
    permissions: List[PermissionInfo] = Field(default=[], description="Role permissions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "researcher",
                "display_name": "Researcher",
                "description": "Standard researcher role",
                "is_system_role": True,
                "is_default": True,
                "parent_role_id": None,
                "permissions": []
            }
        }
    )


class RoleCreateRequest(BaseCreateSchema):
    """Schema for role creation request."""

    name: str = Field(
        ...,
        description="Role name (unique, lowercase, alphanumeric and underscores)",
        min_length=3,
        max_length=50,
        pattern=r"^[a-z0-9_]+$"
    )
    display_name: str = Field(
        ...,
        description="Human-readable display name",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        description="Role description",
        max_length=500
    )
    parent_role_id: Optional[uuid.UUID] = Field(
        None,
        description="Parent role ID for inheritance"
    )
    permission_ids: List[uuid.UUID] = Field(
        default=[],
        description="Permission IDs to assign to role"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "lab_assistant",
                "display_name": "Lab Assistant",
                "description": "Assistant role with limited permissions",
                "parent_role_id": "550e8400-e29b-41d4-a716-446655440000",
                "permission_ids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "987fcdeb-51a2-43d1-9f12-123456789abc"
                ]
            }
        }
    )


class RoleUpdateRequest(BaseUpdateSchema):
    """Schema for role update request."""

    display_name: Optional[str] = Field(
        None,
        description="Human-readable display name",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        description="Role description",
        max_length=500
    )
    parent_role_id: Optional[uuid.UUID] = Field(
        None,
        description="Parent role ID for inheritance"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "display_name": "Senior Lab Assistant",
                "description": "Senior assistant role with additional permissions"
            }
        }
    )


class UserRoleAssignment(BaseSchema):
    """Schema for user role assignment."""

    user_id: uuid.UUID = Field(..., description="User ID")
    role_ids: List[uuid.UUID] = Field(..., description="Role IDs to assign")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "role_ids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "987fcdeb-51a2-43d1-9f12-123456789abc"
                ]
            }
        }
    )


# ===== SESSION MANAGEMENT SCHEMAS =====

class UserSessionInfo(BaseEntitySchema):
    """Schema for user session information."""

    user_id: uuid.UUID = Field(..., description="User ID")
    session_token: str = Field(..., description="Session token (partial)")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    expires_at: datetime = Field(..., description="Session expiration time")
    last_activity_at: datetime = Field(..., description="Last activity timestamp")
    is_active: bool = Field(..., description="Session is active")
    is_current: bool = Field(default=False, description="Current session")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_token": "sess_***456789",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
                "expires_at": "2024-01-22T10:30:00Z",
                "last_activity_at": "2024-01-15T10:30:00Z",
                "is_active": True,
                "is_current": True
            }
        }
    )


class SessionTerminateRequest(BaseSchema):
    """Schema for session termination request."""

    session_ids: List[uuid.UUID] = Field(
        ...,
        description="Session IDs to terminate",
        min_items=1
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "123e4567-e89b-12d3-a456-426614174000"
                ]
            }
        }
    )


# ===== MFA SCHEMAS =====

class MFASetupRequest(BaseSchema):
    """Schema for MFA setup request."""

    password: str = Field(..., description="Current password for verification")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "password": "CurrentPassword123!"
            }
        }
    )


class MFASetupResponse(BaseSchema):
    """Schema for MFA setup response."""

    secret: str = Field(..., description="MFA secret key")
    qr_code_url: str = Field(..., description="QR code URL for authenticator apps")
    backup_codes: List[str] = Field(..., description="Backup codes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "secret": "JBSWY3DPEHPK3PXP",
                "qr_code_url": "otpauth://totp/LICS:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=LICS",
                "backup_codes": ["12345678", "87654321", "11111111"]
            }
        }
    )


class MFAConfirmRequest(BaseSchema):
    """Schema for MFA confirmation request."""

    code: str = Field(
        ...,
        description="6-digit MFA code",
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "123456"
            }
        }
    )


class MFADisableRequest(BaseSchema):
    """Schema for MFA disable request."""

    password: str = Field(..., description="Current password for verification")
    code: str = Field(
        ...,
        description="6-digit MFA code or backup code",
        min_length=6,
        max_length=8
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "password": "CurrentPassword123!",
                "code": "123456"
            }
        }
    )


# ===== FILTER SCHEMAS =====

class UserFilterSchema(BaseFilterSchema):
    """Schema for filtering user queries."""

    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    is_superuser: Optional[bool] = Field(None, description="Filter by superuser status")
    role_id: Optional[uuid.UUID] = Field(None, description="Filter by role ID")
    has_mfa: Optional[bool] = Field(None, description="Filter by MFA status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search": "jane",
                "is_active": True,
                "is_verified": True,
                "organization_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    )


class RoleFilterSchema(BaseFilterSchema):
    """Schema for filtering role queries."""

    is_system_role: Optional[bool] = Field(None, description="Filter by system role status")
    is_default: Optional[bool] = Field(None, description="Filter by default role status")
    parent_role_id: Optional[uuid.UUID] = Field(None, description="Filter by parent role ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search": "researcher",
                "is_system_role": True,
                "is_default": False
            }
        }
    )


class PermissionFilterSchema(BaseFilterSchema):
    """Schema for filtering permission queries."""

    resource: Optional[str] = Field(None, description="Filter by resource type")
    action: Optional[str] = Field(None, description="Filter by action")
    is_system_permission: Optional[bool] = Field(None, description="Filter by system permission status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search": "experiment",
                "resource": "experiment",
                "action": "create"
            }
        }
    )


# ===== FORWARD REFERENCE RESOLUTION =====

# Update forward references
LoginResponse.model_rebuild()
UserRegistrationResponse.model_rebuild()
UserProfile.model_rebuild()
RoleInfo.model_rebuild()


# ===== RESPONSE TYPE ALIASES =====

UserListResponse = PaginatedResponse[UserProfile]
RoleListResponse = PaginatedResponse[RoleInfo]
PermissionListResponse = PaginatedResponse[PermissionInfo]
SessionListResponse = PaginatedResponse[UserSessionInfo]

LoginResponseWrapper = BaseResponse[LoginResponse]
UserProfileResponse = BaseResponse[UserProfile]
TokenPairResponse = BaseResponse[TokenPair]
AccessTokenResponseWrapper = BaseResponse[AccessTokenResponse]
UserRegistrationResponseWrapper = BaseResponse[UserRegistrationResponse]

# ===== ORGANIZATION CRUD SCHEMAS =====

class OrganizationCreateSchema(BaseCreateSchema):
    """Schema for creating a new organization."""
    
    name: str = Field(
        ...,
        description="Organization name (unique)",
        min_length=1,
        max_length=255,
        examples=["Acme Research Lab", "University Psychology Department"]
    )
    
    description: Optional[str] = Field(
        None,
        description="Organization description",
        examples=["Leading research facility for behavioral studies"]
    )
    
    settings: Optional[Dict[str, Any]] = Field(
        None,
        description="Organization-specific settings and preferences",
        examples=[{"default_experiment_duration": 3600, "max_devices": 50}]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Research Lab",
                "description": "Leading research facility for behavioral studies",
                "settings": {
                    "default_experiment_duration": 3600,
                    "max_devices": 50,
                    "timezone": "America/New_York"
                }
            }
        }
    )


class OrganizationUpdateSchema(BaseUpdateSchema):
    """Schema for updating an organization."""
    
    name: Optional[str] = Field(
        None,
        description="Organization name",
        min_length=1,
        max_length=255
    )
    
    description: Optional[str] = Field(
        None,
        description="Organization description"
    )
    
    settings: Optional[Dict[str, Any]] = Field(
        None,
        description="Organization-specific settings"
    )
    
    is_active: Optional[bool] = Field(
        None,
        description="Organization active status"
    )


class OrganizationSchema(OrganizationEntityFullSchema):
    """Schema for organization response (includes all fields)."""
    pass


# Type aliases for organization responses
OrganizationResponse = BaseResponse[OrganizationSchema]
OrganizationListResponse = PaginatedResponse[OrganizationSchema]

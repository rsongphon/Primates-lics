"""
LICS Backend Schemas

Pydantic schemas for request/response validation and serialization.
"""

# Import base schemas and mixins
from .base import (
    BaseSchema, TimestampSchema, AuditSchema, SoftDeleteSchema,
    VersionSchema, OrganizationSchema, BaseEntitySchema,
    BaseEntityWithAuditSchema, BaseEntityWithSoftDeleteSchema,
    BaseEntityFullSchema, OrganizationEntitySchema,
    OrganizationEntityFullSchema, BaseCreateSchema, BaseUpdateSchema,
    BaseFilterSchema, PaginationParams, OrderingParams, PaginationMeta,
    BaseResponse, PaginatedResponse, ErrorDetail, ErrorResponse,
    HealthStatus, ServiceHealthStatus, ComprehensiveHealthResponse,
    create_response, create_paginated_response, create_error_response
)

# Import authentication schemas
from .auth import (
    # Token schemas
    TokenData, AccessTokenResponse, RefreshTokenResponse, TokenPair,

    # Authentication request/response schemas
    LoginRequest, LoginResponse, RefreshTokenRequest, LogoutRequest,

    # User registration schemas
    UserRegistrationRequest, UserRegistrationResponse,

    # Password management schemas
    PasswordResetRequest, PasswordResetConfirm, PasswordChangeRequest,

    # Email verification schemas
    EmailVerificationRequest, ResendVerificationRequest,

    # User profile schemas
    UserProfile, UserUpdateRequest,

    # Role and permission schemas
    PermissionInfo, RoleInfo, RoleCreateRequest, RoleUpdateRequest,
    UserRoleAssignment,

    # Session management schemas
    UserSessionInfo, SessionTerminateRequest,

    # MFA schemas
    MFASetupRequest, MFASetupResponse, MFAConfirmRequest, MFADisableRequest,

    # Filter schemas
    UserFilterSchema, RoleFilterSchema, PermissionFilterSchema,

    # Response type aliases
    UserListResponse, RoleListResponse, PermissionListResponse,
    SessionListResponse, LoginResponseWrapper, UserProfileResponse,
    TokenPairResponse, AccessTokenResponseWrapper, UserRegistrationResponseWrapper
)

# List all schemas for discovery
__all__ = [
    # Base schemas and mixins
    "BaseSchema", "TimestampSchema", "AuditSchema", "SoftDeleteSchema",
    "VersionSchema", "OrganizationSchema", "BaseEntitySchema",
    "BaseEntityWithAuditSchema", "BaseEntityWithSoftDeleteSchema",
    "BaseEntityFullSchema", "OrganizationEntitySchema",
    "OrganizationEntityFullSchema", "BaseCreateSchema", "BaseUpdateSchema",
    "BaseFilterSchema", "PaginationParams", "OrderingParams", "PaginationMeta",
    "BaseResponse", "PaginatedResponse", "ErrorDetail", "ErrorResponse",
    "HealthStatus", "ServiceHealthStatus", "ComprehensiveHealthResponse",
    "create_response", "create_paginated_response", "create_error_response",

    # Authentication schemas
    "TokenData", "AccessTokenResponse", "RefreshTokenResponse", "TokenPair",
    "LoginRequest", "LoginResponse", "RefreshTokenRequest", "LogoutRequest",
    "UserRegistrationRequest", "UserRegistrationResponse",
    "PasswordResetRequest", "PasswordResetConfirm", "PasswordChangeRequest",
    "EmailVerificationRequest", "ResendVerificationRequest",
    "UserProfile", "UserUpdateRequest",
    "PermissionInfo", "RoleInfo", "RoleCreateRequest", "RoleUpdateRequest",
    "UserRoleAssignment", "UserSessionInfo", "SessionTerminateRequest",
    "MFASetupRequest", "MFASetupResponse", "MFAConfirmRequest", "MFADisableRequest",
    "UserFilterSchema", "RoleFilterSchema", "PermissionFilterSchema",
    "UserListResponse", "RoleListResponse", "PermissionListResponse",
    "SessionListResponse", "LoginResponseWrapper", "UserProfileResponse",
    "TokenPairResponse", "AccessTokenResponseWrapper", "UserRegistrationResponseWrapper",
]
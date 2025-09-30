"""
LICS Backend Services

Business logic layer implementing service patterns for application functionality.
"""

# Import base service classes and exceptions
from .base import (
    BaseService, ServiceMixin, ServiceError, ValidationError,
    NotFoundError, ConflictError, PermissionError
)

# Import authentication services
from .auth import (
    # Custom authentication exceptions
    AuthenticationError, InvalidTokenError, AccountLockedError,
    MFARequiredError, WeakPasswordError,

    # Repository classes
    UserRepository, RoleRepository, PermissionRepository,
    SessionRepository, RefreshTokenRepository,

    # Service classes
    AuthService, UserService, PasswordService, MFAService,
    RoleService, PermissionService, SessionService
)

# List all services for discovery
__all__ = [
    # Base service classes and exceptions
    "BaseService", "ServiceMixin", "ServiceError", "ValidationError",
    "NotFoundError", "ConflictError", "PermissionError",

    # Authentication exceptions
    "AuthenticationError", "InvalidTokenError", "AccountLockedError",
    "MFARequiredError", "WeakPasswordError",

    # Authentication repositories
    "UserRepository", "RoleRepository", "PermissionRepository",
    "SessionRepository", "RefreshTokenRepository",

    # Authentication services
    "AuthService", "UserService", "PasswordService", "MFAService",
    "RoleService", "PermissionService", "SessionService",
]
"""
LICS Backend Models

SQLAlchemy database models for the LICS system.
"""

# Import base models and mixins
from .base import (
    BaseModel, BaseModelWithSoftDelete, BaseModelWithAudit,
    BaseModelWithVersion, BaseModelFull, OrganizationBaseModel,
    OrganizationBaseModelFull, TimestampMixin, SoftDeleteMixin,
    AuditMixin, VersionMixin, OrganizationMixin, AuditContext
)

# Import authentication models
from .auth import (
    User, Role, Permission, UserSession, RefreshToken,
    user_roles, role_permissions
)

# List all models for discovery
__all__ = [
    # Base models and mixins
    "BaseModel", "BaseModelWithSoftDelete", "BaseModelWithAudit",
    "BaseModelWithVersion", "BaseModelFull", "OrganizationBaseModel",
    "OrganizationBaseModelFull", "TimestampMixin", "SoftDeleteMixin",
    "AuditMixin", "VersionMixin", "OrganizationMixin", "AuditContext",

    # Authentication models
    "User", "Role", "Permission", "UserSession", "RefreshToken",
    "user_roles", "role_permissions",
]
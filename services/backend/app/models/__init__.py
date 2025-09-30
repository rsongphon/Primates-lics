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

# Import domain models
from .domain import (
    Device, Experiment, Task, Participant, TaskExecution, DeviceData,
    experiment_devices, experiment_tasks,
    DeviceStatus, DeviceType, ExperimentStatus, TaskStatus, ParticipantStatus
)

# Import Organization from base (for convenience)
from .base import Organization

# List all models for discovery
__all__ = [
    # Base models and mixins
    "BaseModel", "BaseModelWithSoftDelete", "BaseModelWithAudit",
    "BaseModelWithVersion", "BaseModelFull", "OrganizationBaseModel",
    "OrganizationBaseModelFull", "TimestampMixin", "SoftDeleteMixin",
    "AuditMixin", "VersionMixin", "OrganizationMixin", "AuditContext",

    # Core domain models
    "Organization",

    # Authentication models
    "User", "Role", "Permission", "UserSession", "RefreshToken",
    "user_roles", "role_permissions",

    # Domain models
    "Device", "Experiment", "Task", "Participant", "TaskExecution", "DeviceData",
    "experiment_devices", "experiment_tasks",

    # Enums
    "DeviceStatus", "DeviceType", "ExperimentStatus", "TaskStatus", "ParticipantStatus",
]
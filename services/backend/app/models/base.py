"""
LICS Backend Base Models

Base SQLAlchemy models with audit fields, soft delete support, and
common utilities. Follows Documentation.md Section 6.1 database design patterns.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, String, Text, UUID, Boolean, event, Integer, JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger(__name__)


class TimestampMixin:
    """
    Mixin to add timestamp fields to models.

    Provides created_at and updated_at fields with automatic population.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="When the record was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="When the record was last updated"
    )


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality to models.

    Provides deleted_at field and helper methods for soft delete operations.
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the record was soft deleted (NULL if not deleted)"
    )

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the record as soft deleted."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.deleted_at = None


class AuditMixin:
    """
    Mixin to add audit fields to models.

    Provides fields to track who created and last modified the record.
    """

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        doc="ID of the user who created the record"
    )

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        doc="ID of the user who last updated the record"
    )


class VersionMixin:
    """
    Mixin to add optimistic locking version control to models.

    Provides version field for optimistic concurrency control.
    """

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        doc="Version number for optimistic locking"
    )


class OrganizationMixin:
    """
    Mixin to add organization-based multi-tenancy to models.

    Provides organization_id field for tenant isolation.
    """

    @declared_attr
    def organization_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True),
            nullable=False,
            doc="ID of the organization this record belongs to"
        )


class BaseModel(Base, TimestampMixin):
    """
    Base model class with common fields and functionality.

    All domain models should inherit from this class to get
    standard fields and behavior.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the record"
    )

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            include_relationships: Whether to include relationship data

        Returns:
            Dictionary representation of the model
        """
        result = {}

        # Add column values
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            result[column.name] = value

        # Add relationship data if requested
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                related_value = getattr(self, relationship.key)
                if related_value is not None:
                    if relationship.collection_class is not None:
                        # One-to-many or many-to-many relationship
                        result[relationship.key] = [
                            item.to_dict() if hasattr(item, 'to_dict') else str(item)
                            for item in related_value
                        ]
                    else:
                        # One-to-one or many-to-one relationship
                        result[relationship.key] = (
                            related_value.to_dict() if hasattr(related_value, 'to_dict')
                            else str(related_value)
                        )

        return result

    def update_from_dict(self, data: Dict[str, Any], exclude_fields: Optional[List[str]] = None) -> None:
        """
        Update model fields from dictionary.

        Args:
            data: Dictionary with field values
            exclude_fields: List of fields to exclude from update
        """
        exclude_fields = exclude_fields or ['id', 'created_at']

        for key, value in data.items():
            if key not in exclude_fields and hasattr(self, key):
                setattr(self, key, value)


class BaseModelWithSoftDelete(BaseModel, SoftDeleteMixin):
    """
    Base model class with soft delete functionality.

    Use this for models that should support soft delete operations.
    """

    __abstract__ = True


class BaseModelWithAudit(BaseModel, AuditMixin):
    """
    Base model class with audit fields.

    Use this for models that need to track creation and modification users.
    """

    __abstract__ = True


class BaseModelWithVersion(BaseModel, VersionMixin):
    """
    Base model class with version control.

    Use this for models that need optimistic locking.
    """

    __abstract__ = True


class BaseModelFull(BaseModel, SoftDeleteMixin, AuditMixin, VersionMixin):
    """
    Base model class with all mixins (timestamps, soft delete, audit, version).

    Use this for models that need all standard functionality.
    """

    __abstract__ = True


class OrganizationBaseModel(BaseModel, OrganizationMixin):
    """
    Base model class for organization-scoped entities.

    Use this for models that belong to a specific organization.
    """

    __abstract__ = True


class OrganizationBaseModelFull(BaseModelFull, OrganizationMixin):
    """
    Base model class for organization-scoped entities with all features.

    Use this for models that belong to an organization and need all features.
    """

    __abstract__ = True


# Event listeners for automatic audit field population

@event.listens_for(BaseModelWithAudit, 'before_insert', propagate=True)
def set_created_by(mapper, connection, target):
    """Set created_by field when inserting records."""
    # TODO: Get current user from context
    # For now, this is a placeholder - implement context-based user tracking
    pass


@event.listens_for(BaseModelWithAudit, 'before_update', propagate=True)
def set_updated_by(mapper, connection, target):
    """Set updated_by field when updating records."""
    # TODO: Get current user from context
    # For now, this is a placeholder - implement context-based user tracking
    pass


@event.listens_for(BaseModelWithVersion, 'before_update', propagate=True)
def increment_version(mapper, connection, target):
    """Increment version field when updating records."""
    target.version += 1


# Utility functions for model operations

def get_table_name(model_class: type) -> str:
    """
    Get the table name for a model class.

    Args:
        model_class: SQLAlchemy model class

    Returns:
        Table name
    """
    return model_class.__tablename__


def get_primary_key_field(model_class: type) -> str:
    """
    Get the primary key field name for a model class.

    Args:
        model_class: SQLAlchemy model class

    Returns:
        Primary key field name
    """
    return model_class.__mapper__.primary_key[0].name


def is_soft_deletable(model_class: type) -> bool:
    """
    Check if a model class supports soft delete.

    Args:
        model_class: SQLAlchemy model class

    Returns:
        True if model supports soft delete
    """
    return hasattr(model_class, 'deleted_at')


def is_auditable(model_class: type) -> bool:
    """
    Check if a model class has audit fields.

    Args:
        model_class: SQLAlchemy model class

    Returns:
        True if model has audit fields
    """
    return hasattr(model_class, 'created_by') and hasattr(model_class, 'updated_by')


def is_versioned(model_class: type) -> bool:
    """
    Check if a model class has version control.

    Args:
        model_class: SQLAlchemy model class

    Returns:
        True if model has version control
    """
    return hasattr(model_class, 'version')


def is_organization_scoped(model_class: type) -> bool:
    """
    Check if a model class is organization-scoped.

    Args:
        model_class: SQLAlchemy model class

    Returns:
        True if model is organization-scoped
    """
    return hasattr(model_class, 'organization_id')


# Context managers for audit trail

class AuditContext:
    """
    Context manager for setting audit information.

    This can be used to set the current user for audit fields.
    """

    _current_user_id: Optional[uuid.UUID] = None

    @classmethod
    def set_current_user(cls, user_id: uuid.UUID) -> None:
        """Set the current user for audit operations."""
        cls._current_user_id = user_id

    @classmethod
    def get_current_user(cls) -> Optional[uuid.UUID]:
        """Get the current user for audit operations."""
        return cls._current_user_id

    @classmethod
    def clear_current_user(cls) -> None:
        """Clear the current user."""
        cls._current_user_id = None

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        self.previous_user_id = None

    def __enter__(self):
        self.previous_user_id = self.get_current_user()
        self.set_current_user(self.user_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_user_id:
            self.set_current_user(self.previous_user_id)
        else:
            self.clear_current_user()


# Update the event listeners to use the audit context

@event.listens_for(BaseModelWithAudit, 'before_insert', propagate=True)
def set_created_by_from_context(mapper, connection, target):
    """Set created_by field from audit context when inserting records."""
    current_user_id = AuditContext.get_current_user()
    if current_user_id and not target.created_by:
        target.created_by = current_user_id


@event.listens_for(BaseModelWithAudit, 'before_update', propagate=True)
def set_updated_by_from_context(mapper, connection, target):
    """Set updated_by field from audit context when updating records."""
    current_user_id = AuditContext.get_current_user()
    if current_user_id:
        target.updated_by = current_user_id


# ===== CORE DOMAIN MODELS =====

class Organization(BaseModelWithSoftDelete):
    """
    Organization model for multi-tenant support.

    Organizations provide tenant isolation and resource management.
    Each organization can have its own users, devices, and experiments.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        doc="Organization name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Organization description"
    )

    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Organization-specific settings and configuration"
    )

    max_users: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Maximum number of users allowed"
    )

    max_devices: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Maximum number of devices allowed"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the organization is active"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"
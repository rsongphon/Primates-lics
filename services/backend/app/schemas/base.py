"""
LICS Backend Base Schemas

Base Pydantic schemas for request/response validation and serialization.
Follows Documentation.md Section 5.1 domain model patterns with Pydantic v2.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, validator
from pydantic.alias_generators import to_camel


# Type variables for generic schemas
DataT = TypeVar('DataT')


class BaseSchema(BaseModel):
    """
    Base Pydantic schema with common configuration.

    All request/response schemas should inherit from this class
    to get consistent configuration and behavior.
    """

    model_config = ConfigDict(
        # Use enum values instead of names
        use_enum_values=True,
        # Validate assignment to fields
        validate_assignment=True,
        # Allow extra fields to be ignored (useful for forward compatibility)
        extra='ignore',
        # Use datetime strings in JSON
        json_encoders={
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        },
        # Generate JSON schema
        json_schema_extra={
            "examples": []
        }
    )


class TimestampSchema(BaseSchema):
    """
    Schema mixin for timestamp fields.

    Provides created_at and updated_at fields for entities with timestamps.
    """

    created_at: datetime = Field(
        ...,
        description="When the record was created",
        examples=["2024-01-15T10:30:00Z"]
    )

    updated_at: datetime = Field(
        ...,
        description="When the record was last updated",
        examples=["2024-01-15T10:30:00Z"]
    )


class AuditSchema(BaseSchema):
    """
    Schema mixin for audit fields.

    Provides created_by and updated_by fields for entities with audit tracking.
    """

    created_by: Optional[uuid.UUID] = Field(
        None,
        description="ID of the user who created the record",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    updated_by: Optional[uuid.UUID] = Field(
        None,
        description="ID of the user who last updated the record",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )


class SoftDeleteSchema(BaseSchema):
    """
    Schema mixin for soft delete fields.

    Provides deleted_at field for entities with soft delete support.
    """

    deleted_at: Optional[datetime] = Field(
        None,
        description="When the record was soft deleted (null if not deleted)",
        examples=[None, "2024-01-15T10:30:00Z"]
    )

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None


class VersionSchema(BaseSchema):
    """
    Schema mixin for version control fields.

    Provides version field for optimistic locking.
    """

    version: int = Field(
        1,
        description="Version number for optimistic locking",
        ge=1,
        examples=[1, 5, 10]
    )


class OrganizationSchema(BaseSchema):
    """
    Schema mixin for organization-scoped entities.

    Provides organization_id field for multi-tenant entities.
    """

    organization_id: uuid.UUID = Field(
        ...,
        description="ID of the organization this record belongs to",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )


# ===== BASE ENTITY SCHEMAS =====

class BaseEntitySchema(TimestampSchema):
    """
    Base schema for entity responses.

    Includes ID and timestamp fields that are common to all entities.
    """

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier for the record",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )


class BaseEntityWithAuditSchema(BaseEntitySchema, AuditSchema):
    """
    Base schema for entities with audit fields.
    """

    pass


class BaseEntityWithSoftDeleteSchema(BaseEntitySchema, SoftDeleteSchema):
    """
    Base schema for entities with soft delete support.
    """

    pass


class BaseEntityFullSchema(BaseEntitySchema, AuditSchema, SoftDeleteSchema, VersionSchema):
    """
    Base schema for entities with all standard fields.
    """

    pass


class OrganizationEntitySchema(BaseEntitySchema, OrganizationSchema):
    """
    Base schema for organization-scoped entities.
    """

    pass


class OrganizationEntityFullSchema(BaseEntityFullSchema, OrganizationSchema):
    """
    Base schema for organization-scoped entities with all features.
    """

    pass


# ===== REQUEST SCHEMAS =====

class BaseCreateSchema(BaseSchema):
    """
    Base schema for entity creation requests.

    Should be inherited by entity-specific create schemas.
    """

    pass


class BaseUpdateSchema(BaseSchema):
    """
    Base schema for entity update requests.

    Should be inherited by entity-specific update schemas.
    All fields should be optional to support partial updates.
    """

    pass


class BaseFilterSchema(BaseSchema):
    """
    Base schema for filtering requests.

    Provides common filter fields and can be extended with entity-specific filters.
    """

    # Text search
    search: Optional[str] = Field(
        None,
        description="Text search query",
        min_length=1,
        max_length=200,
        examples=["temperature sensor"]
    )

    # Date range filters
    created_after: Optional[datetime] = Field(
        None,
        description="Filter records created after this date",
        examples=["2024-01-01T00:00:00Z"]
    )

    created_before: Optional[datetime] = Field(
        None,
        description="Filter records created before this date",
        examples=["2024-12-31T23:59:59Z"]
    )

    updated_after: Optional[datetime] = Field(
        None,
        description="Filter records updated after this date",
        examples=["2024-01-01T00:00:00Z"]
    )

    updated_before: Optional[datetime] = Field(
        None,
        description="Filter records updated before this date",
        examples=["2024-12-31T23:59:59Z"]
    )

    # Organization filter (for multi-tenant entities)
    organization_id: Optional[uuid.UUID] = Field(
        None,
        description="Filter by organization ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )

    # Soft delete filter
    include_deleted: bool = Field(
        False,
        description="Include soft-deleted records in results"
    )


# ===== PAGINATION SCHEMAS =====

class PaginationParams(BaseSchema):
    """
    Schema for pagination parameters.
    """

    skip: int = Field(
        0,
        description="Number of records to skip",
        ge=0,
        examples=[0, 20, 100]
    )

    limit: int = Field(
        100,
        description="Maximum number of records to return",
        ge=1,
        le=1000,
        examples=[10, 50, 100]
    )


class OrderingParams(BaseSchema):
    """
    Schema for ordering parameters.
    """

    order_by: Optional[str] = Field(
        None,
        description="Field name to order by",
        examples=["created_at", "name", "id"]
    )

    order_desc: bool = Field(
        False,
        description="Order in descending order"
    )


class PaginationMeta(BaseSchema):
    """
    Schema for pagination metadata in responses.
    """

    total_count: int = Field(
        ...,
        description="Total number of records matching the query",
        ge=0,
        examples=[250]
    )

    page_count: int = Field(
        ...,
        description="Total number of pages",
        ge=0,
        examples=[25]
    )

    current_page: int = Field(
        ...,
        description="Current page number (1-based)",
        ge=1,
        examples=[3]
    )

    page_size: int = Field(
        ...,
        description="Number of records per page",
        ge=1,
        examples=[10]
    )

    has_next: bool = Field(
        ...,
        description="Whether there are more pages available"
    )

    has_previous: bool = Field(
        ...,
        description="Whether there are previous pages available"
    )


# ===== RESPONSE SCHEMAS =====

class BaseResponse(BaseSchema, Generic[DataT]):
    """
    Base response schema wrapper.

    Provides consistent response format with data and metadata.
    """

    data: DataT = Field(
        ...,
        description="Response data"
    )

    meta: Optional[Dict[str, Any]] = Field(
        None,
        description="Response metadata"
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(),
        description="Response timestamp"
    )


class PaginatedResponse(BaseResponse[List[DataT]]):
    """
    Response schema for paginated data.
    """

    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata"
    )


class ErrorDetail(BaseSchema):
    """
    Schema for error details.
    """

    code: str = Field(
        ...,
        description="Error code",
        examples=["VALIDATION_ERROR", "NOT_FOUND", "PERMISSION_DENIED"]
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Validation failed", "Record not found", "Permission denied"]
    )

    field: Optional[str] = Field(
        None,
        description="Field name for validation errors",
        examples=["email", "name", "organization_id"]
    )

    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )


class ErrorResponse(BaseSchema):
    """
    Schema for error responses.
    """

    error: ErrorDetail = Field(
        ...,
        description="Error information"
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(),
        description="Error timestamp"
    )

    trace_id: Optional[str] = Field(
        None,
        description="Request trace ID for debugging",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )


# ===== HEALTH CHECK SCHEMAS =====

class HealthStatus(BaseSchema):
    """
    Schema for health check status.
    """

    status: str = Field(
        ...,
        description="Health status",
        examples=["healthy", "unhealthy", "degraded"]
    )

    timestamp: datetime = Field(
        ...,
        description="Health check timestamp"
    )

    response_time_ms: int = Field(
        ...,
        description="Response time in milliseconds",
        ge=0,
        examples=[45, 150, 500]
    )


class ServiceHealthStatus(HealthStatus):
    """
    Schema for individual service health status.
    """

    name: str = Field(
        ...,
        description="Service name",
        examples=["PostgreSQL", "Redis", "MQTT"]
    )

    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional health details"
    )


class ComprehensiveHealthResponse(BaseSchema):
    """
    Schema for comprehensive health check response.
    """

    status: str = Field(
        ...,
        description="Overall health status",
        examples=["healthy", "unhealthy", "degraded"]
    )

    timestamp: datetime = Field(
        ...,
        description="Health check timestamp"
    )

    response_time_ms: int = Field(
        ...,
        description="Total response time in milliseconds",
        ge=0
    )

    services: List[ServiceHealthStatus] = Field(
        ...,
        description="Individual service health statuses"
    )

    summary: Dict[str, Any] = Field(
        ...,
        description="Health check summary"
    )


# ===== UTILITY FUNCTIONS =====

def create_response(
    data: DataT,
    meta: Optional[Dict[str, Any]] = None
) -> BaseResponse[DataT]:
    """
    Create a standardized response.

    Args:
        data: Response data
        meta: Optional metadata

    Returns:
        Standardized response
    """
    return BaseResponse(
        data=data,
        meta=meta,
        timestamp=datetime.now()
    )


def create_paginated_response(
    data: List[DataT],
    total_count: int,
    page: int,
    page_size: int
) -> PaginatedResponse[DataT]:
    """
    Create a paginated response.

    Args:
        data: Response data
        total_count: Total number of records
        page: Current page number (1-based)
        page_size: Number of records per page

    Returns:
        Paginated response
    """
    page_count = (total_count + page_size - 1) // page_size

    pagination_meta = PaginationMeta(
        total_count=total_count,
        page_count=page_count,
        current_page=page,
        page_size=page_size,
        has_next=page < page_count,
        has_previous=page > 1
    )

    return PaginatedResponse(
        data=data,
        pagination=pagination_meta,
        timestamp=datetime.now()
    )


def create_error_response(
    code: str,
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        code: Error code
        message: Error message
        field: Optional field name for validation errors
        details: Optional additional details
        trace_id: Optional trace ID

    Returns:
        Error response
    """
    error_detail = ErrorDetail(
        code=code,
        message=message,
        field=field,
        details=details
    )

    return ErrorResponse(
        error=error_detail,
        timestamp=datetime.now(),
        trace_id=trace_id
    )
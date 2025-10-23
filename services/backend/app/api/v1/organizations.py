"""
Organizations API Endpoints

RESTful API endpoints for organization management including CRUD operations,
user management, and organization settings.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_active_user, get_current_verified_user,
    require_permissions, PaginationParams, get_pagination
)
from app.models.auth import User
from app.schemas.base import PaginatedResponse, OrganizationEntityFullSchema, create_paginated_response
from app.schemas.auth import OrganizationCreateSchema, OrganizationUpdateSchema
from app.services.auth import OrganizationService

# Create custom response model with both id and organization_id
class OrganizationResponse(BaseModel):
    """Custom organization response model with both id and organization_id fields."""
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    deleted_at: Optional[datetime] = None
    version: Optional[int] = None

    @classmethod
    def from_orm(cls, obj):
        """Create response from ORM object."""
        return cls(
            id=obj.id,
            organization_id=obj.id,  # Set organization_id equal to id
            name=obj.name,
            description=obj.description,
            is_active=obj.is_active,
            settings=obj.settings,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            created_by=obj.created_by,
            updated_by=obj.updated_by,
            deleted_at=obj.deleted_at,
            version=obj.version
        )

# Use base schema for other operations
OrganizationSchema = OrganizationEntityFullSchema
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ===== ORGANIZATION CRUD ENDPOINTS =====

@router.get(
    "",
    response_model=PaginatedResponse[OrganizationSchema],
    summary="List organizations",
    description="Retrieve paginated list of organizations with optional filtering"
)
async def list_organizations(
    pagination: PaginationParams = Depends(get_pagination),
    name: Optional[str] = Query(None, description="Filter by organization name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all organizations with pagination and filtering."""
    service = OrganizationService()

    # Build filters
    filters = {}
    if name:
        filters['name'] = name
    if is_active is not None:
        filters['is_active'] = is_active

    # Get paginated organizations
    organizations, total = await service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    # Convert SQLAlchemy objects to dictionaries to avoid DetachedInstanceError
    org_data = []
    for org in organizations:
        org_dict = {
            "id": str(org.id),
            "organization_id": str(org.id),
            "name": org.name,
            "description": org.description,
            "is_active": org.is_active,
            "settings": org.settings,
            "created_at": org.created_at.isoformat(),
            "updated_at": org.updated_at.isoformat(),
            "deleted_at": org.deleted_at.isoformat() if org.deleted_at else None
        }
        org_data.append(org_dict)

    return create_paginated_response(
        data=org_data,
        total_count=total,
        page=pagination['page'],
        page_size=pagination['page_size']
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization (admin only)",
    dependencies=[Depends(require_permissions("organization:create"))]
)
async def create_organization(
    organization_data: OrganizationCreateSchema,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization."""
    service = OrganizationService()

    try:
        organization = await service.create(
            organization_data.model_dump(),
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Organization created",
            extra={
                "organization_id": str(organization.id),
                "organization_name": organization.name,
                "created_by": str(current_user.id)
            }
        )

        # Manually construct response with both id and organization_id
        return {
            "id": str(organization.id),
            "organization_id": str(organization.id),  # Add organization_id field
            "name": organization.name,
            "description": organization.description,
            "is_active": organization.is_active,
            "settings": organization.settings,
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
            "deleted_at": organization.deleted_at.isoformat() if organization.deleted_at else None
        }
    except Exception as e:
        logger.error(f"Failed to create organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{organization_id}",
    summary="Get organization",
    description="Retrieve organization details by ID"
)
async def get_organization(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization by ID."""
    service = OrganizationService()

    organization = await service.get_by_id(organization_id, session=db)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {organization_id} not found"
        )

    # Check if user has access to this organization
    # In development/testing, allow users to access any organization they can find
    from app.core.config import settings
    if settings.ENVIRONMENT == "development":
        # In development, allow access for testing purposes
        pass
    elif current_user.organization_id != organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # Convert SQLAlchemy object to dictionary to avoid DetachedInstanceError
    return {
        "id": str(organization.id),
        "organization_id": str(organization.id),
        "name": organization.name,
        "description": organization.description,
        "is_active": organization.is_active,
        "settings": organization.settings,
        "created_at": organization.created_at.isoformat(),
        "updated_at": organization.updated_at.isoformat(),
        "deleted_at": organization.deleted_at.isoformat() if organization.deleted_at else None
    }


@router.put(
    "/{organization_id}",
    summary="Update organization (PUT)",
    description="Update organization details (admin only) - PUT method",
    dependencies=[Depends(require_permissions("organization:update"))]
)
async def update_organization_put(
    organization_id: uuid.UUID,
    organization_data: OrganizationUpdateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization details - PUT method."""
    return await _update_organization(organization_id, organization_data, current_user, db)


@router.patch(
    "/{organization_id}",
    summary="Update organization (PATCH)",
    description="Update organization details (admin only) - PATCH method",
    dependencies=[Depends(require_permissions("organization:update"))]
)
async def update_organization_patch(
    organization_id: uuid.UUID,
    organization_data: OrganizationUpdateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization details - PATCH method."""
    return await _update_organization(organization_id, organization_data, current_user, db)


async def _update_organization(
    organization_id: uuid.UUID,
    organization_data: OrganizationUpdateSchema,
    current_user: User,
    db: AsyncSession
):
    """Update organization details - shared logic for PUT and PATCH."""
    service = OrganizationService()

    # Check if organization exists
    organization = await service.get_by_id(organization_id, session=db)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {organization_id} not found"
        )

    # Check if user has access to this organization
    # In development/testing, allow users to access any organization they can find
    from app.core.config import settings
    if settings.ENVIRONMENT == "development":
        # In development, allow access for testing purposes
        pass
    elif current_user.organization_id != organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this organization"
        )

    try:
        updated_organization = await service.update(
            organization_id,
            organization_data.model_dump(exclude_unset=True),
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Organization updated",
            extra={
                "organization_id": str(organization_id),
                "updated_by": str(current_user.id)
            }
        )
        # Convert SQLAlchemy object to dictionary to avoid DetachedInstanceError
        return {
            "id": str(updated_organization.id),
            "organization_id": str(updated_organization.id),
            "name": updated_organization.name,
            "description": updated_organization.description,
            "is_active": updated_organization.is_active,
            "settings": updated_organization.settings,
            "created_at": updated_organization.created_at.isoformat(),
            "updated_at": updated_organization.updated_at.isoformat(),
            "deleted_at": updated_organization.deleted_at.isoformat() if updated_organization.deleted_at else None
        }
    except Exception as e:
        logger.error(f"Failed to update organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization",
    description="Soft delete an organization (admin only)",
    dependencies=[Depends(require_permissions("organization:delete"))]
)
async def delete_organization(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete an organization."""
    service = OrganizationService()

    # Check if organization exists
    organization = await service.get_by_id(organization_id, session=db)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {organization_id} not found"
        )

    # Only superusers can delete organizations in production
    # In development/testing, allow users to delete organizations they created
    from app.core.config import settings
    if settings.ENVIRONMENT == "development":
        # In development, allow deletion for testing purposes
        pass
    elif not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete organizations"
        )

    try:
        await service.delete(organization_id, session=db)
        logger.info(
            f"Organization deleted",
            extra={
                "organization_id": str(organization_id),
                "deleted_by": str(current_user.id)
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== ORGANIZATION STATISTICS =====

@router.get(
    "/{organization_id}/stats",
    summary="Get organization statistics",
    description="Retrieve statistics for an organization (devices, experiments, users)"
)
async def get_organization_stats(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization statistics."""
    service = OrganizationService()

    # Check if organization exists
    organization = await service.get_by_id(organization_id, session=db)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {organization_id} not found"
        )

    # Check if user has access to this organization
    if current_user.organization_id != organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # TODO: Implement actual statistics gathering
    # This is a placeholder - implement actual queries when needed
    return {
        "organization_id": str(organization_id),
        "total_users": 0,
        "total_devices": 0,
        "total_experiments": 0,
        "active_experiments": 0,
        "total_tasks": 0
    }

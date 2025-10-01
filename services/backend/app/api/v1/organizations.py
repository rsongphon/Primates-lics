"""
Organizations API Endpoints

RESTful API endpoints for organization management including CRUD operations,
user management, and organization settings.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_active_user,
    require_permissions, PaginationParams, get_pagination
)
from app.models.auth import User
from app.schemas.base import PaginatedResponse, OrganizationEntityFullSchema
from app.schemas.auth import OrganizationCreateSchema, OrganizationUpdateSchema
from app.services.auth import OrganizationService

# Use base schema for Organization responses
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

    return PaginatedResponse(
        items=organizations,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


@router.post(
    "",
    response_model=OrganizationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization (admin only)",
    dependencies=[Depends(require_permissions("organization:create"))]
)
async def create_organization(
    organization_data: OrganizationCreateSchema,
    current_user: User = Depends(get_current_active_user),
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
        return organization
    except Exception as e:
        logger.error(f"Failed to create organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{organization_id}",
    response_model=OrganizationSchema,
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
    if current_user.organization_id != organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    return organization


@router.patch(
    "/{organization_id}",
    response_model=OrganizationSchema,
    summary="Update organization",
    description="Update organization details (admin only)",
    dependencies=[Depends(require_permissions("organization:update"))]
)
async def update_organization(
    organization_id: uuid.UUID,
    organization_data: OrganizationUpdateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization details."""
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
        return updated_organization
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

    # Only superusers can delete organizations
    if not current_user.is_superuser:
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

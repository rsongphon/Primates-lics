"""
LICS Backend RBAC API Endpoints

FastAPI endpoints for Role-Based Access Control (RBAC) management.
Handles roles, permissions, and user role assignments.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.schemas.auth import (
    # Request schemas
    RoleCreateRequest, RoleUpdateRequest, UserRoleAssignment,

    # Response schemas
    RoleInfo, PermissionInfo, UserProfile,
    RoleListResponse, PermissionListResponse,

    # Filter schemas
    RoleFilterSchema, PermissionFilterSchema
)
from app.schemas.base import (
    BaseResponse, PaginationParams,
    create_response, create_paginated_response
)
from app.services.auth import (
    RoleService, PermissionService, UserService,
    UserRepository, RoleRepository, PermissionRepository
)
from app.services.base import (
    ServiceError, ValidationError, NotFoundError, ConflictError, PermissionError
)
from app.api.v1.auth import get_current_active_user

logger = get_logger(__name__)

# Create router
router = APIRouter()

# Service instances
role_service = RoleService()
permission_service = PermissionService()
user_service = UserService()


async def get_current_admin_user(
    current_user: UserProfile = Depends(get_current_active_user)
) -> UserProfile:
    """
    Ensure current user has admin privileges for RBAC operations.

    This is a placeholder - in a full implementation, this would check
    if the user has specific RBAC management permissions.
    """
    # TODO: Implement proper permission checking
    # For now, only allow superusers to manage RBAC
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for RBAC management"
        )

    return current_user


# ===== ROLE MANAGEMENT ENDPOINTS =====

@router.get(
    "/roles",
    response_model=RoleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Roles",
    description="Get paginated list of roles with filtering"
)
async def list_roles(
    skip: int = Query(0, ge=0, description="Number of roles to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of roles to return"),
    search: Optional[str] = Query(None, description="Search roles by name or display name"),
    is_system_role: Optional[bool] = Query(None, description="Filter by system role status"),
    is_default: Optional[bool] = Query(None, description="Filter by default role status"),
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> RoleListResponse:
    """
    Get paginated list of roles with optional filtering.

    Query Parameters:
    - **skip**: Number of roles to skip (pagination)
    - **limit**: Maximum number of roles to return (1-1000)
    - **search**: Search by role name or display name
    - **is_system_role**: Filter by system role status
    - **is_default**: Filter by default role status

    Returns paginated list of roles with metadata.
    """
    try:
        # Build filters
        filters = {}
        if search:
            filters["search"] = search
        if is_system_role is not None:
            filters["is_system_role"] = is_system_role
        if is_default is not None:
            filters["is_default"] = is_default

        # Get roles
        roles = await role_service.get_list(
            filters=filters,
            skip=skip,
            limit=limit,
            current_user_id=current_user.id
        )

        # Get total count
        total_count = await role_service.count(
            filters=filters,
            current_user_id=current_user.id
        )

        # Convert to response schemas
        role_infos = []
        for role in roles:
            role_info = RoleInfo(
                id=role.id,
                name=role.name,
                display_name=role.display_name,
                description=role.description,
                is_system_role=role.is_system_role,
                is_default=role.is_default,
                parent_role_id=role.parent_role_id,
                created_at=role.created_at,
                updated_at=role.updated_at,
                permissions=[]  # TODO: Convert permissions to PermissionInfo
            )
            role_infos.append(role_info)

        return create_paginated_response(
            data=role_infos,
            total_count=total_count,
            page=(skip // limit) + 1,
            page_size=limit
        )

    except ServiceError as e:
        logger.error(f"List roles error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles"
        )


@router.get(
    "/roles/{role_id}",
    response_model=BaseResponse[RoleInfo],
    status_code=status.HTTP_200_OK,
    summary="Get Role",
    description="Get role by ID with permissions"
)
async def get_role(
    role_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[RoleInfo]:
    """
    Get role by ID including associated permissions.

    Path Parameters:
    - **role_id**: Role UUID

    Returns role information with permissions.
    """
    try:
        role = await role_service.get_by_id(
            role_id,
            current_user_id=current_user.id
        )

        permission_infos = []
        for permission in role.permissions:
            permission_info = PermissionInfo(
                id=permission.id,
                name=permission.name,
                display_name=permission.display_name,
                description=permission.description,
                resource=permission.resource,
                action=permission.action,
                is_system_permission=permission.is_system_permission,
                created_at=permission.created_at,
                updated_at=permission.updated_at
            )
            permission_infos.append(permission_info)

        role_info = RoleInfo(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_default=role.is_default,
            parent_role_id=role.parent_role_id,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=permission_infos
        )

        return create_response(role_info)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Get role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role"
        )


@router.post(
    "/roles",
    response_model=BaseResponse[RoleInfo],
    status_code=status.HTTP_201_CREATED,
    summary="Create Role",
    description="Create new role with permissions"
)
async def create_role(
    role_data: RoleCreateRequest,
    current_user: UserProfile = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[RoleInfo]:
    """
    Create new role with permissions (admin only).

    Request Body:
    - **name**: Role name (unique, lowercase, alphanumeric and underscores)
    - **display_name**: Human-readable display name
    - **description**: Role description (optional)
    - **parent_role_id**: Parent role ID for inheritance (optional)
    - **permission_ids**: List of permission IDs to assign (optional)

    Returns created role with permissions.
    """
    try:
        role = await role_service.create_role(
            role_data=role_data,
            current_user_id=current_user.id
        )

        permission_infos = []
        for permission in role.permissions:
            permission_info = PermissionInfo(
                id=permission.id,
                name=permission.name,
                display_name=permission.display_name,
                description=permission.description,
                resource=permission.resource,
                action=permission.action,
                is_system_permission=permission.is_system_permission,
                created_at=permission.created_at,
                updated_at=permission.updated_at
            )
            permission_infos.append(permission_info)

        role_info = RoleInfo(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_default=role.is_default,
            parent_role_id=role.parent_role_id,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=permission_infos
        )

        return create_response(role_info)

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Create role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role"
        )


@router.patch(
    "/roles/{role_id}",
    response_model=BaseResponse[RoleInfo],
    status_code=status.HTTP_200_OK,
    summary="Update Role",
    description="Update role information"
)
async def update_role(
    role_id: uuid.UUID,
    role_data: RoleUpdateRequest,
    current_user: UserProfile = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[RoleInfo]:
    """
    Update role information (admin only).

    Path Parameters:
    - **role_id**: Role UUID

    Request Body:
    - **display_name**: Human-readable display name (optional)
    - **description**: Role description (optional)
    - **parent_role_id**: Parent role ID for inheritance (optional)

    Returns updated role information.
    """
    try:
        role = await role_service.update(
            role_id,
            role_data.dict(exclude_unset=True),
            current_user_id=current_user.id
        )

        permission_infos = []
        for permission in role.permissions:
            permission_info = PermissionInfo(
                id=permission.id,
                name=permission.name,
                display_name=permission.display_name,
                description=permission.description,
                resource=permission.resource,
                action=permission.action,
                is_system_permission=permission.is_system_permission,
                created_at=permission.created_at,
                updated_at=permission.updated_at
            )
            permission_infos.append(permission_info)

        role_info = RoleInfo(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_default=role.is_default,
            parent_role_id=role.parent_role_id,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=permission_infos
        )

        return create_response(role_info)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Update role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role"
        )


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Role",
    description="Delete role (admin only)"
)
async def delete_role(
    role_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Delete role (admin only).

    Path Parameters:
    - **role_id**: Role UUID

    System roles cannot be deleted.
    """
    try:
        # Check if role exists and is not a system role
        role = await role_service.get_by_id(
            role_id,
            current_user_id=current_user.id
        )

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system role"
            )

        await role_service.delete(
            role_id,
            current_user_id=current_user.id
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Delete role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete role"
        )


@router.post(
    "/roles/{role_id}/permissions",
    response_model=BaseResponse[RoleInfo],
    status_code=status.HTTP_200_OK,
    summary="Assign Permissions to Role",
    description="Assign permissions to role"
)
async def assign_role_permissions(
    role_id: uuid.UUID,
    permission_ids: List[uuid.UUID],
    current_user: UserProfile = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[RoleInfo]:
    """
    Assign permissions to role (admin only).

    Path Parameters:
    - **role_id**: Role UUID

    Request Body:
    - List of permission UUIDs to assign

    Returns updated role with permissions.
    """
    try:
        role = await role_service.assign_permissions(
            role_id=role_id,
            permission_ids=permission_ids,
            current_user_id=current_user.id
        )

        permission_infos = []
        for permission in role.permissions:
            permission_info = PermissionInfo(
                id=permission.id,
                name=permission.name,
                display_name=permission.display_name,
                description=permission.description,
                resource=permission.resource,
                action=permission.action,
                is_system_permission=permission.is_system_permission,
                created_at=permission.created_at,
                updated_at=permission.updated_at
            )
            permission_infos.append(permission_info)

        role_info = RoleInfo(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_default=role.is_default,
            parent_role_id=role.parent_role_id,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=permission_infos
        )

        return create_response(role_info)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Assign role permissions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign permissions to role"
        )


# ===== PERMISSION MANAGEMENT ENDPOINTS =====

@router.get(
    "/permissions",
    response_model=PermissionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Permissions",
    description="Get paginated list of permissions with filtering"
)
async def list_permissions(
    skip: int = Query(0, ge=0, description="Number of permissions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of permissions to return"),
    search: Optional[str] = Query(None, description="Search permissions by name or display name"),
    resource: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    is_system_permission: Optional[bool] = Query(None, description="Filter by system permission status"),
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> PermissionListResponse:
    """
    Get paginated list of permissions with optional filtering.

    Query Parameters:
    - **skip**: Number of permissions to skip (pagination)
    - **limit**: Maximum number of permissions to return (1-1000)
    - **search**: Search by permission name or display name
    - **resource**: Filter by resource type
    - **action**: Filter by action
    - **is_system_permission**: Filter by system permission status

    Returns paginated list of permissions with metadata.
    """
    try:
        # Build filters
        filters = {}
        if search:
            filters["search"] = search
        if resource:
            filters["resource"] = resource
        if action:
            filters["action"] = action
        if is_system_permission is not None:
            filters["is_system_permission"] = is_system_permission

        # Get permissions
        permissions = await permission_service.get_list(
            filters=filters,
            skip=skip,
            limit=limit,
            current_user_id=current_user.id
        )

        # Get total count
        total_count = await permission_service.count(
            filters=filters,
            current_user_id=current_user.id
        )

        # Convert to response schemas
        permission_infos = []
        for permission in permissions:
            permission_info = PermissionInfo(
                id=permission.id,
                name=permission.name,
                display_name=permission.display_name,
                description=permission.description,
                resource=permission.resource,
                action=permission.action,
                is_system_permission=permission.is_system_permission,
                created_at=permission.created_at,
                updated_at=permission.updated_at
            )
            permission_infos.append(permission_info)

        return create_paginated_response(
            data=permission_infos,
            total_count=total_count,
            page=(skip // limit) + 1,
            page_size=limit
        )

    except ServiceError as e:
        logger.error(f"List permissions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permissions"
        )


@router.get(
    "/permissions/{permission_id}",
    response_model=BaseResponse[PermissionInfo],
    status_code=status.HTTP_200_OK,
    summary="Get Permission",
    description="Get permission by ID"
)
async def get_permission(
    permission_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[PermissionInfo]:
    """
    Get permission by ID.

    Path Parameters:
    - **permission_id**: Permission UUID

    Returns permission information.
    """
    try:
        permission = await permission_service.get_by_id(
            permission_id,
            current_user_id=current_user.id
        )

        permission_info = PermissionInfo(
            id=permission.id,
            name=permission.name,
            display_name=permission.display_name,
            description=permission.description,
            resource=permission.resource,
            action=permission.action,
            is_system_permission=permission.is_system_permission,
            created_at=permission.created_at,
            updated_at=permission.updated_at
        )

        return create_response(permission_info)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Get permission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permission"
        )


@router.post(
    "/permissions",
    response_model=BaseResponse[PermissionInfo],
    status_code=status.HTTP_201_CREATED,
    summary="Create Permission",
    description="Create new permission"
)
async def create_permission(
    name: str,
    display_name: str,
    resource: str,
    action: str,
    description: Optional[str] = None,
    current_user: UserProfile = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[PermissionInfo]:
    """
    Create new permission (admin only).

    Query Parameters:
    - **name**: Permission name (unique)
    - **display_name**: Human-readable display name
    - **resource**: Resource type
    - **action**: Action on resource
    - **description**: Permission description (optional)

    Returns created permission.
    """
    try:
        permission = await permission_service.create_permission(
            name=name,
            display_name=display_name,
            resource=resource,
            action=action,
            description=description,
            current_user_id=current_user.id
        )

        permission_info = PermissionInfo(
            id=permission.id,
            name=permission.name,
            display_name=permission.display_name,
            description=permission.description,
            resource=permission.resource,
            action=permission.action,
            is_system_permission=permission.is_system_permission,
            created_at=permission.created_at,
            updated_at=permission.updated_at
        )

        return create_response(permission_info)

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Create permission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create permission"
        )


# ===== USER ROLE ASSIGNMENT ENDPOINTS =====

@router.post(
    "/users/{user_id}/roles",
    response_model=BaseResponse[UserProfile],
    status_code=status.HTTP_200_OK,
    summary="Assign Roles to User",
    description="Assign roles to user"
)
async def assign_user_roles(
    user_id: uuid.UUID,
    role_ids: List[uuid.UUID],
    current_user: UserProfile = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[UserProfile]:
    """
    Assign roles to user (admin only).

    Path Parameters:
    - **user_id**: User UUID

    Request Body:
    - List of role UUIDs to assign

    Returns updated user with roles.
    """
    try:
        user = await user_service.assign_roles(
            user_id=user_id,
            role_ids=role_ids,
            current_user_id=current_user.id
        )

        user_profile = UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            organization_id=user.organization_id,
            timezone=user.timezone,
            language=user.language,
            last_login_at=user.last_login_at,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[],  # TODO: Convert roles to RoleInfo
            permissions=set()  # TODO: Get user permissions
        )

        return create_response(user_profile)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Assign user roles error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign roles to user"
        )


@router.get(
    "/users/{user_id}/permissions",
    response_model=BaseResponse[List[str]],
    status_code=status.HTTP_200_OK,
    summary="Get User Permissions",
    description="Get all permissions for a user"
)
async def get_user_permissions(
    user_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db_session)
) -> BaseResponse[List[str]]:
    """
    Get all permissions for a user (admin only).

    Path Parameters:
    - **user_id**: User UUID

    Returns list of permission names.
    """
    try:
        permissions = await user_service.get_user_permissions(user_id)
        return create_response(list(permissions))

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ServiceError as e:
        logger.error(f"Get user permissions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user permissions"
        )
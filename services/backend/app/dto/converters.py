"""
DTO Converters - Transform ORM models to Pydantic schemas

All converters follow these principles:
1. Accept ORM model + active session
2. Eagerly load all required relationships
3. Extract data into plain Python structures
4. Build Pydantic models from plain data
5. Never return ORM objects or lazy-loading proxies

Example:
    # Bad (returns ORM object):
    return role  # ❌ May cause lazy loading issues

    # Good (returns DTO):
    return await RoleConverter.to_role_info(role, session)  # ✓
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import User, Role, Permission
from app.schemas.auth import (
    UserProfile, UserInfo, UserDetail,
    RoleInfo, RoleDetail,
    PermissionInfo
)


class PermissionConverter:
    """Converter for Permission model → Pydantic schemas"""

    @staticmethod
    def to_permission_info(permission: Permission) -> PermissionInfo:
        """
        Convert ORM Permission to PermissionInfo DTO.

        Note: Only converts already-loaded scalar attributes.
        Use within active session scope.

        Args:
            permission: Permission ORM object with loaded attributes

        Returns:
            PermissionInfo Pydantic model
        """
        return PermissionInfo(
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

    @staticmethod
    async def to_permission_info_list(
        permissions: List[Permission],
        session: AsyncSession
    ) -> List[PermissionInfo]:
        """
        Convert list of Permission ORM objects to PermissionInfo DTOs.

        Args:
            permissions: List of Permission ORM objects
            session: Active database session (for future use if needed)

        Returns:
            List of PermissionInfo Pydantic models
        """
        return [
            PermissionConverter.to_permission_info(perm)
            for perm in permissions
        ]


class RoleConverter:
    """Converter for Role model → Pydantic schemas"""

    @staticmethod
    async def to_role_info(
        role: Role,
        session: AsyncSession,
        include_permissions: bool = True
    ) -> RoleInfo:
        """
        Convert ORM Role to RoleInfo DTO with eager loading.

        Args:
            role: Role ORM object
            session: Active database session
            include_permissions: Whether to load and include permissions

        Returns:
            RoleInfo DTO with all data loaded
        """
        # Ensure role is attached to session
        if role not in session:
            # Re-query if detached
            stmt = select(Role).where(Role.id == role.id)
            if include_permissions:
                stmt = stmt.options(selectinload(Role.permissions))
            result = await session.execute(stmt)
            role = result.scalar_one()
        elif include_permissions:
            # Ensure permissions are loaded
            await session.refresh(role, ["permissions"])

        # Convert permissions to DTOs if requested
        permission_infos = []
        if include_permissions:
            permission_infos = [
                PermissionConverter.to_permission_info(perm)
                for perm in role.permissions
            ]

        return RoleInfo(
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

    @staticmethod
    async def to_role_detail(
        role: Role,
        session: AsyncSession
    ) -> RoleDetail:
        """
        Convert ORM Role to detailed RoleDetail DTO.

        Includes additional information like user count, etc.

        Args:
            role: Role ORM object
            session: Active database session

        Returns:
            RoleDetail Pydantic model with extended information
        """
        # Get role with all relationships
        stmt = (
            select(Role)
            .where(Role.id == role.id)
            .options(
                selectinload(Role.permissions),
                selectinload(Role.users)
            )
        )
        result = await session.execute(stmt)
        role_full = result.scalar_one()

        # Convert to RoleInfo first
        role_info = await RoleConverter.to_role_info(role_full, session)

        # Add extra details
        return RoleDetail(
            **role_info.dict(),
            user_count=len(role_full.users),
            # Add other detail fields as needed
        )


class UserConverter:
    """Converter for User model → Pydantic schemas"""

    @staticmethod
    async def to_user_profile(
        user: User,
        session: AsyncSession
    ) -> UserProfile:
        """
        Convert ORM User to UserProfile DTO with full role/permission data.

        This is the main converter used by authentication system.
        Eagerly loads all relationships and converts to plain DTOs.

        Args:
            user: User ORM object (may be partially loaded)
            session: Active database session

        Returns:
            UserProfile DTO with complete data
        """
        # Re-query with explicit eager loading
        stmt = (
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.roles).selectinload(Role.permissions)
            )
        )
        result = await session.execute(stmt)
        user_loaded = result.scalar_one()

        # Convert roles to DTOs
        role_infos = []
        all_permissions = set()

        for role in user_loaded.roles:
            role_info = await RoleConverter.to_role_info(
                role, session, include_permissions=True
            )
            role_infos.append(role_info)

            # Collect unique permission names
            all_permissions.update(perm.name for perm in role_info.permissions)

        return UserProfile(
            id=user_loaded.id,
            email=user_loaded.email,
            username=user_loaded.username,
            first_name=user_loaded.first_name,
            last_name=user_loaded.last_name,
            is_active=user_loaded.is_active,
            is_verified=user_loaded.is_verified,
            is_superuser=user_loaded.is_superuser,
            organization_id=user_loaded.organization_id,
            timezone=user_loaded.timezone,
            language=user_loaded.language,
            last_login_at=user_loaded.last_login_at,
            mfa_enabled=user_loaded.mfa_enabled,
            created_at=user_loaded.created_at,
            updated_at=user_loaded.updated_at,
            roles=role_infos,
            permissions=all_permissions
        )

    @staticmethod
    def to_user_info(user: User) -> UserInfo:
        """
        Convert ORM User to minimal UserInfo DTO.

        Only includes basic user information without relationships.
        Safe to use with detached objects.

        Args:
            user: User ORM object (can be detached)

        Returns:
            UserInfo Pydantic model with basic user data
        """
        return UserInfo(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified
        )


class OrganizationConverter:
    """Converter for Organization model → Pydantic schemas"""

    # TODO: Implement when Organization endpoints are created
    # Similar pattern to UserConverter and RoleConverter
    pass

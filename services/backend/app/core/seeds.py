"""
Database Seeding

Initial data seeding for development and production environments.
Creates default users, roles, permissions, and organizations.
"""

import asyncio
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db_session
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.models.auth import User, Role, Permission
from app.models.base import Organization
# Note: We'll implement UserService, RoleService, PermissionService separately for seeding
# from app.services.auth import UserService, RoleService, PermissionService

logger = get_logger(__name__)


class DatabaseSeeder:
    """
    Database seeding class for creating initial application data.
    """

    def __init__(self):
        pass  # We'll use direct database operations for seeding

    async def seed_all(self, force: bool = False) -> None:
        """
        Seed all initial data.

        Args:
            force: Whether to recreate existing data
        """
        logger.info("Starting database seeding...")

        try:
            from app.core.database import db_manager
            session = await db_manager.get_session()
            try:
                # Seed in order due to foreign key dependencies
                await self.seed_organizations(session, force)
                await self.seed_permissions(session, force)
                await self.seed_roles(session, force)
                await self.seed_users(session, force)

                await session.commit()
                logger.info("Database seeding completed successfully")
            finally:
                await session.close()

        except Exception as e:
            logger.error(f"Database seeding failed: {e}")
            raise

    async def seed_organizations(self, db: AsyncSession, force: bool = False) -> None:
        """Seed default organizations."""
        logger.info("Seeding organizations...")

        organizations = [
            {
                "name": "LICS System",
                "description": "System organization for administrative purposes",
                "settings": {
                    "max_devices": 1000,
                    "max_experiments": 10000,
                    "storage_limit_gb": 1000,
                    "features": {
                        "video_streaming": True,
                        "ml_analysis": True,
                        "api_access": True,
                        "custom_tasks": True
                    }
                }
            },
            {
                "name": "Demo Lab",
                "description": "Demonstration laboratory for testing and examples",
                "settings": {
                    "max_devices": 10,
                    "max_experiments": 100,
                    "storage_limit_gb": 10,
                    "features": {
                        "video_streaming": True,
                        "ml_analysis": False,
                        "api_access": True,
                        "custom_tasks": True
                    }
                }
            }
        ]

        for org_data in organizations:
            # Check if organization exists
            result = await db.execute(
                select(Organization).where(Organization.name == org_data["name"])
            )
            existing_org = result.scalar_one_or_none()

            if existing_org and not force:
                logger.info(f"Organization '{org_data['name']}' already exists, skipping")
                continue

            if existing_org and force:
                # Update existing organization
                for key, value in org_data.items():
                    setattr(existing_org, key, value)
                logger.info(f"Updated organization: {org_data['name']}")
            else:
                # Create new organization
                org = Organization(**org_data)
                db.add(org)
                logger.info(f"Created organization: {org_data['name']}")

    async def seed_permissions(self, db: AsyncSession, force: bool = False) -> None:
        """Seed default permissions."""
        logger.info("Seeding permissions...")

        # Define all system permissions
        permissions = [
            # User Management
            {"name": "users:create", "display_name": "Create Users", "description": "Create new users", "resource": "users", "action": "create"},
            {"name": "users:read", "display_name": "Read Users", "description": "View user information", "resource": "users", "action": "read"},
            {"name": "users:update", "display_name": "Update Users", "description": "Update user information", "resource": "users", "action": "update"},
            {"name": "users:delete", "display_name": "Delete Users", "description": "Delete users", "resource": "users", "action": "delete"},
            {"name": "users:list", "display_name": "List Users", "description": "List all users", "resource": "users", "action": "list"},

            # Role Management
            {"name": "roles:create", "description": "Create new roles"},
            {"name": "roles:read", "description": "View role information"},
            {"name": "roles:update", "description": "Update role information"},
            {"name": "roles:delete", "description": "Delete roles"},
            {"name": "roles:assign", "description": "Assign roles to users"},

            # Permission Management
            {"name": "permissions:read", "description": "View permissions"},
            {"name": "permissions:assign", "description": "Assign permissions to roles"},

            # Organization Management
            {"name": "organizations:create", "description": "Create new organizations"},
            {"name": "organizations:read", "description": "View organization information"},
            {"name": "organizations:update", "description": "Update organization settings"},
            {"name": "organizations:delete", "description": "Delete organizations"},
            {"name": "organizations:manage", "description": "Full organization management"},

            # Device Management
            {"name": "devices:create", "description": "Register new devices"},
            {"name": "devices:read", "description": "View device information"},
            {"name": "devices:update", "description": "Update device configuration"},
            {"name": "devices:delete", "description": "Remove devices"},
            {"name": "devices:control", "description": "Send commands to devices"},
            {"name": "devices:monitor", "description": "Monitor device status and telemetry"},

            # Experiment Management
            {"name": "experiments:create", "description": "Create new experiments"},
            {"name": "experiments:read", "description": "View experiment information"},
            {"name": "experiments:update", "description": "Update experiment settings"},
            {"name": "experiments:delete", "description": "Delete experiments"},
            {"name": "experiments:execute", "description": "Start and stop experiments"},
            {"name": "experiments:analyze", "description": "Analyze experiment data"},

            # Task Management
            {"name": "tasks:create", "description": "Create task definitions"},
            {"name": "tasks:read", "description": "View task definitions"},
            {"name": "tasks:update", "description": "Update task definitions"},
            {"name": "tasks:delete", "description": "Delete task definitions"},
            {"name": "tasks:execute", "description": "Execute tasks on devices"},
            {"name": "tasks:template", "description": "Create and manage task templates"},

            # Data Access
            {"name": "data:read", "description": "View experimental data"},
            {"name": "data:export", "description": "Export data"},
            {"name": "data:delete", "description": "Delete experimental data"},

            # Video Streaming
            {"name": "video:view", "description": "View live video streams"},
            {"name": "video:record", "description": "Record video sessions"},
            {"name": "video:manage", "description": "Manage video settings"},

            # System Administration
            {"name": "system:admin", "description": "Full system administration"},
            {"name": "system:monitor", "description": "View system metrics and logs"},
            {"name": "system:config", "description": "Update system configuration"},
            {"name": "system:backup", "description": "Create and restore backups"},

            # API Access
            {"name": "api:read", "description": "Read access via API"},
            {"name": "api:write", "description": "Write access via API"},
            {"name": "api:admin", "description": "Administrative API access"}
        ]

        for perm_data in permissions:
            # Check if permission exists
            result = await db.execute(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            existing_perm = result.scalar_one_or_none()

            if existing_perm and not force:
                continue

            if existing_perm and force:
                # Update existing permission
                existing_perm.description = perm_data["description"]
            else:
                # Create new permission
                permission = Permission(**perm_data)
                db.add(permission)

        logger.info(f"Seeded {len(permissions)} permissions")

    async def seed_roles(self, db: AsyncSession, force: bool = False) -> None:
        """Seed default roles with permissions."""
        logger.info("Seeding roles...")

        # Get all permissions for assignment
        result = await db.execute(select(Permission))
        all_permissions = {perm.name: perm for perm in result.scalars().all()}

        # Define roles with their permissions
        roles_config = [
            {
                "name": "Super Admin",
                "description": "Full system administration access",
                "permissions": list(all_permissions.keys())  # All permissions
            },
            {
                "name": "Lab Admin",
                "description": "Laboratory administration and management",
                "permissions": [
                    "users:create", "users:read", "users:update", "users:list",
                    "roles:read", "roles:assign",
                    "organizations:read", "organizations:update",
                    "devices:create", "devices:read", "devices:update", "devices:delete",
                    "devices:control", "devices:monitor",
                    "experiments:create", "experiments:read", "experiments:update",
                    "experiments:delete", "experiments:execute", "experiments:analyze",
                    "tasks:create", "tasks:read", "tasks:update", "tasks:delete",
                    "tasks:execute", "tasks:template",
                    "data:read", "data:export",
                    "video:view", "video:record", "video:manage",
                    "api:read", "api:write"
                ]
            },
            {
                "name": "Researcher",
                "description": "Research and experiment management",
                "permissions": [
                    "users:read",
                    "devices:read", "devices:monitor",
                    "experiments:create", "experiments:read", "experiments:update",
                    "experiments:execute", "experiments:analyze",
                    "tasks:create", "tasks:read", "tasks:update", "tasks:execute",
                    "tasks:template",
                    "data:read", "data:export",
                    "video:view", "video:record",
                    "api:read", "api:write"
                ]
            },
            {
                "name": "Observer",
                "description": "Read-only access to experiments and data",
                "permissions": [
                    "users:read",
                    "devices:read", "devices:monitor",
                    "experiments:read",
                    "tasks:read",
                    "data:read",
                    "video:view",
                    "api:read"
                ]
            },
            {
                "name": "Device Operator",
                "description": "Device control and monitoring",
                "permissions": [
                    "devices:read", "devices:control", "devices:monitor",
                    "experiments:read", "experiments:execute",
                    "tasks:read", "tasks:execute",
                    "video:view",
                    "api:read"
                ]
            }
        ]

        for role_config in roles_config:
            # Check if role exists
            result = await db.execute(
                select(Role).where(Role.name == role_config["name"])
            )
            existing_role = result.scalar_one_or_none()

            if existing_role and not force:
                logger.info(f"Role '{role_config['name']}' already exists, skipping")
                continue

            if existing_role:
                role = existing_role
                role.description = role_config["description"]
                # Clear existing permissions
                role.permissions.clear()
            else:
                role = Role(
                    name=role_config["name"],
                    description=role_config["description"]
                )
                db.add(role)

            # Assign permissions to role
            for perm_name in role_config["permissions"]:
                if perm_name in all_permissions:
                    role.permissions.append(all_permissions[perm_name])

            logger.info(f"Created/updated role: {role_config['name']} with {len(role_config['permissions'])} permissions")

    async def seed_users(self, db: AsyncSession, force: bool = False) -> None:
        """Seed default users."""
        logger.info("Seeding users...")

        # Get organizations and roles
        org_result = await db.execute(
            select(Organization).where(Organization.name == "LICS System")
        )
        system_org = org_result.scalar_one()

        demo_org_result = await db.execute(
            select(Organization).where(Organization.name == "Demo Lab")
        )
        demo_org = demo_org_result.scalar_one()

        role_result = await db.execute(select(Role))
        roles = {role.name: role for role in role_result.scalars().all()}

        # Define default users
        users_config = [
            {
                "email": "admin@lics.system",
                "username": "admin",
                "first_name": "System",
                "last_name": "Administrator",
                "password": "admin123!",  # Change in production
                "is_superuser": True,
                "is_active": True,
                "email_verified": True,
                "organization_id": system_org.id,
                "roles": ["Super Admin"]
            },
            {
                "email": "demo@lics.system",
                "username": "demo",
                "first_name": "Demo",
                "last_name": "User",
                "password": "demo123!",
                "is_superuser": False,
                "is_active": True,
                "email_verified": True,
                "organization_id": demo_org.id,
                "roles": ["Lab Admin"]
            },
            {
                "email": "researcher@lics.system",
                "username": "researcher",
                "first_name": "Research",
                "last_name": "User",
                "password": "research123!",
                "is_superuser": False,
                "is_active": True,
                "email_verified": True,
                "organization_id": demo_org.id,
                "roles": ["Researcher"]
            },
            {
                "email": "observer@lics.system",
                "username": "observer",
                "first_name": "Observer",
                "last_name": "User",
                "password": "observer123!",
                "is_superuser": False,
                "is_active": True,
                "email_verified": True,
                "organization_id": demo_org.id,
                "roles": ["Observer"]
            }
        ]

        for user_config in users_config:
            # Check if user exists
            result = await db.execute(
                select(User).where(User.email == user_config["email"])
            )
            existing_user = result.scalar_one_or_none()

            if existing_user and not force:
                logger.info(f"User '{user_config['email']}' already exists, skipping")
                continue

            # Create user data
            user_data = user_config.copy()
            role_names = user_data.pop("roles", [])

            # Hash password
            user_data["password_hash"] = get_password_hash(user_data.pop("password"))

            if existing_user:
                # Update existing user
                for key, value in user_data.items():
                    setattr(existing_user, key, value)
                user = existing_user
                # Clear existing roles
                user.roles.clear()
            else:
                # Create new user
                user = User(**user_data)
                db.add(user)

            # Assign roles
            for role_name in role_names:
                if role_name in roles:
                    user.roles.append(roles[role_name])

            logger.info(f"Created/updated user: {user_config['email']} with roles: {role_names}")

    async def clean_seed_data(self, db: AsyncSession) -> None:
        """Clean all seed data (for testing)."""
        logger.warning("Cleaning all seed data...")

        # Delete in reverse order due to foreign keys
        await db.execute("DELETE FROM user_roles")
        await db.execute("DELETE FROM role_permissions")
        await db.execute("DELETE FROM users WHERE email LIKE '%@lics.system'")
        await db.execute("DELETE FROM roles WHERE name IN ('Super Admin', 'Lab Admin', 'Researcher', 'Observer', 'Device Operator')")
        await db.execute("DELETE FROM permissions")
        await db.execute("DELETE FROM organizations WHERE name IN ('LICS System', 'Demo Lab')")

        await db.commit()
        logger.info("Seed data cleaned")


async def run_seeds(force: bool = False):
    """
    Run database seeding.

    Args:
        force: Whether to recreate existing data
    """
    seeder = DatabaseSeeder()
    await seeder.seed_all(force=force)


if __name__ == "__main__":
    import sys

    force = "--force" in sys.argv
    asyncio.run(run_seeds(force=force))
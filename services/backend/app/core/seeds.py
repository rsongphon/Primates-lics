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
from app.models.domain import (
    Device, DeviceStatus, DeviceType,
    Experiment, ExperimentStatus,
    Task, Participant, ParticipantStatus
)
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

                # Seed domain data
                await self.seed_devices(session, force)
                await self.seed_tasks(session, force)
                await self.seed_experiments(session, force)
                await self.seed_participants(session, force)

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

    async def seed_devices(self, db: AsyncSession, force: bool = False) -> None:
        """Seed demo devices."""
        logger.info("Seeding devices...")

        # Get demo organization
        org_result = await db.execute(
            select(Organization).where(Organization.name == "Demo Lab")
        )
        demo_org = org_result.scalar_one()

        devices_config = [
            {
                "name": "Demo Device 01",
                "description": "Raspberry Pi 4 demo device for testing",
                "device_type": DeviceType.RASPBERRY_PI,
                "status": DeviceStatus.ONLINE,
                "organization_id": demo_org.id,
                "mac_address": "b8:27:eb:12:34:56",
                "ip_address": "192.168.1.100",
                "serial_number": "RPI4-DEMO-001",
                "firmware_version": "1.0.0",
                "location": "Lab A - Cage 1",
                "device_metadata": {
                    "hardware": {
                        "model": "Raspberry Pi 4 Model B",
                        "memory": "4GB",
                        "storage": "32GB MicroSD"
                    },
                    "capabilities": {
                        "gpio_pins": 40,
                        "camera": True,
                        "audio": True,
                        "sensors": ["temperature", "humidity", "motion"],
                        "actuators": ["led", "buzzer", "servo"]
                    }
                },
                "is_active": True
            },
            {
                "name": "Demo Device 02",
                "description": "Raspberry Pi 4 demo device for experiments",
                "device_type": DeviceType.RASPBERRY_PI,
                "status": DeviceStatus.ONLINE,
                "organization_id": demo_org.id,
                "mac_address": "b8:27:eb:78:90:12",
                "ip_address": "192.168.1.101",
                "serial_number": "RPI4-DEMO-002",
                "firmware_version": "1.0.0",
                "location": "Lab A - Cage 2",
                "device_metadata": {
                    "hardware": {
                        "model": "Raspberry Pi 4 Model B",
                        "memory": "4GB",
                        "storage": "32GB MicroSD"
                    },
                    "capabilities": {
                        "gpio_pins": 40,
                        "camera": True,
                        "audio": True,
                        "sensors": ["temperature", "humidity", "motion", "light"],
                        "actuators": ["led", "buzzer", "servo", "relay"]
                    }
                },
                "is_active": True
            },
            {
                "name": "Simulation Device",
                "description": "Virtual device for testing without hardware",
                "device_type": DeviceType.SIMULATION,
                "status": DeviceStatus.ONLINE,
                "organization_id": demo_org.id,
                "mac_address": "00:00:00:00:00:00",
                "ip_address": "127.0.0.1",
                "serial_number": "SIM-DEV-001",
                "firmware_version": "sim-1.0.0",
                "location": "Virtual Lab",
                "device_metadata": {
                    "simulation": True,
                    "capabilities": {
                        "gpio_pins": 40,
                        "camera": True,
                        "audio": True,
                        "sensors": ["temperature", "humidity", "motion", "light", "pressure"],
                        "actuators": ["led", "buzzer", "servo", "relay", "motor"]
                    }
                },
                "is_active": True
            }
        ]

        for device_config in devices_config:
            # Check if device exists
            result = await db.execute(
                select(Device).where(Device.serial_number == device_config["serial_number"])
            )
            existing_device = result.scalar_one_or_none()

            if existing_device and not force:
                logger.info(f"Device '{device_config['name']}' already exists, skipping")
                continue

            if existing_device and force:
                # Update existing device
                for key, value in device_config.items():
                    setattr(existing_device, key, value)
                logger.info(f"Updated device: {device_config['name']}")
            else:
                # Create new device
                device = Device(**device_config)
                db.add(device)
                logger.info(f"Created device: {device_config['name']}")

    async def seed_tasks(self, db: AsyncSession, force: bool = False) -> None:
        """Seed demo task templates."""
        logger.info("Seeding task templates...")

        # Get demo organization
        org_result = await db.execute(
            select(Organization).where(Organization.name == "Demo Lab")
        )
        demo_org = org_result.scalar_one()

        tasks_config = [
            {
                "name": "Simple LED Control",
                "description": "Basic LED on/off control task for testing device connectivity",
                "category": "Basic Control",
                "organization_id": demo_org.id,
                "is_template": True,
                "task_definition": {
                    "version": "1.0",
                    "nodes": [
                        {
                            "id": "start_1",
                            "type": "start",
                            "position": {"x": 100, "y": 100},
                            "data": {"label": "Start"}
                        },
                        {
                            "id": "led_on_1",
                            "type": "action",
                            "position": {"x": 250, "y": 100},
                            "data": {
                                "label": "LED On",
                                "action": "gpio_write",
                                "parameters": {"pin": 18, "value": 1}
                            }
                        },
                        {
                            "id": "wait_1",
                            "type": "wait",
                            "position": {"x": 400, "y": 100},
                            "data": {
                                "label": "Wait 2s",
                                "duration": 2000
                            }
                        },
                        {
                            "id": "led_off_1",
                            "type": "action",
                            "position": {"x": 550, "y": 100},
                            "data": {
                                "label": "LED Off",
                                "action": "gpio_write",
                                "parameters": {"pin": 18, "value": 0}
                            }
                        },
                        {
                            "id": "end_1",
                            "type": "end",
                            "position": {"x": 700, "y": 100},
                            "data": {"label": "End"}
                        }
                    ],
                    "edges": [
                        {"id": "e1", "source": "start_1", "target": "led_on_1"},
                        {"id": "e2", "source": "led_on_1", "target": "wait_1"},
                        {"id": "e3", "source": "wait_1", "target": "led_off_1"},
                        {"id": "e4", "source": "led_off_1", "target": "end_1"}
                    ]
                },
                "parameters": {
                    "led_pin": {"type": "integer", "default": 18, "description": "GPIO pin for LED"}
                },
                "estimated_duration": 5000,
                "tags": ["basic", "led", "gpio", "demo"]
            },
            {
                "name": "Sensor Reading Task",
                "description": "Collect temperature and humidity sensor readings",
                "category": "Data Collection",
                "organization_id": demo_org.id,
                "is_template": True,
                "task_definition": {
                    "version": "1.0",
                    "nodes": [
                        {
                            "id": "start_2",
                            "type": "start",
                            "position": {"x": 100, "y": 100},
                            "data": {"label": "Start"}
                        },
                        {
                            "id": "read_temp_1",
                            "type": "data",
                            "position": {"x": 250, "y": 100},
                            "data": {
                                "label": "Read Temperature",
                                "action": "sensor_read",
                                "parameters": {"sensor": "dht22", "pin": 4, "metric": "temperature"}
                            }
                        },
                        {
                            "id": "read_humid_1",
                            "type": "data",
                            "position": {"x": 400, "y": 100},
                            "data": {
                                "label": "Read Humidity",
                                "action": "sensor_read",
                                "parameters": {"sensor": "dht22", "pin": 4, "metric": "humidity"}
                            }
                        },
                        {
                            "id": "log_data_1",
                            "type": "action",
                            "position": {"x": 550, "y": 100},
                            "data": {
                                "label": "Log Data",
                                "action": "log_sensor_data",
                                "parameters": {"format": "json"}
                            }
                        },
                        {
                            "id": "end_2",
                            "type": "end",
                            "position": {"x": 700, "y": 100},
                            "data": {"label": "End"}
                        }
                    ],
                    "edges": [
                        {"id": "e1", "source": "start_2", "target": "read_temp_1"},
                        {"id": "e2", "source": "read_temp_1", "target": "read_humid_1"},
                        {"id": "e3", "source": "read_humid_1", "target": "log_data_1"},
                        {"id": "e4", "source": "log_data_1", "target": "end_2"}
                    ]
                },
                "parameters": {
                    "sensor_pin": {"type": "integer", "default": 4, "description": "GPIO pin for DHT22 sensor"},
                    "sample_interval": {"type": "integer", "default": 1000, "description": "Sampling interval in ms"}
                },
                "estimated_duration": 10000,
                "tags": ["sensor", "dht22", "temperature", "humidity", "data"]
            },
            {
                "name": "Behavioral Choice Task",
                "description": "Two-choice behavioral task with reward delivery",
                "category": "Behavioral",
                "organization_id": demo_org.id,
                "is_template": True,
                "task_definition": {
                    "version": "1.0",
                    "nodes": [
                        {
                            "id": "start_3",
                            "type": "start",
                            "position": {"x": 100, "y": 200},
                            "data": {"label": "Start"}
                        },
                        {
                            "id": "present_stimuli",
                            "type": "action",
                            "position": {"x": 250, "y": 200},
                            "data": {
                                "label": "Present Stimuli",
                                "action": "led_pattern",
                                "parameters": {"left_pin": 16, "right_pin": 20, "duration": 5000}
                            }
                        },
                        {
                            "id": "wait_choice",
                            "type": "wait",
                            "position": {"x": 400, "y": 200},
                            "data": {
                                "label": "Wait for Choice",
                                "action": "wait_for_input",
                                "timeout": 10000
                            }
                        },
                        {
                            "id": "check_choice",
                            "type": "decision",
                            "position": {"x": 550, "y": 200},
                            "data": {
                                "label": "Check Choice",
                                "condition": "input_detected"
                            }
                        },
                        {
                            "id": "reward",
                            "type": "action",
                            "position": {"x": 700, "y": 150},
                            "data": {
                                "label": "Deliver Reward",
                                "action": "servo_move",
                                "parameters": {"pin": 12, "angle": 90}
                            }
                        },
                        {
                            "id": "no_response",
                            "type": "action",
                            "position": {"x": 700, "y": 250},
                            "data": {
                                "label": "No Response",
                                "action": "log_event",
                                "parameters": {"event": "no_response"}
                            }
                        },
                        {
                            "id": "end_3",
                            "type": "end",
                            "position": {"x": 850, "y": 200},
                            "data": {"label": "End"}
                        }
                    ],
                    "edges": [
                        {"id": "e1", "source": "start_3", "target": "present_stimuli"},
                        {"id": "e2", "source": "present_stimuli", "target": "wait_choice"},
                        {"id": "e3", "source": "wait_choice", "target": "check_choice"},
                        {"id": "e4", "source": "check_choice", "target": "reward", "condition": "true"},
                        {"id": "e5", "source": "check_choice", "target": "no_response", "condition": "false"},
                        {"id": "e6", "source": "reward", "target": "end_3"},
                        {"id": "e7", "source": "no_response", "target": "end_3"}
                    ]
                },
                "parameters": {
                    "trial_duration": {"type": "integer", "default": 15000, "description": "Maximum trial duration in ms"},
                    "reward_duration": {"type": "integer", "default": 500, "description": "Reward delivery duration in ms"}
                },
                "estimated_duration": 15000,
                "tags": ["behavioral", "choice", "reward", "decision"]
            }
        ]

        for task_config in tasks_config:
            # Check if task exists
            result = await db.execute(
                select(Task).where(
                    Task.name == task_config["name"],
                    Task.organization_id == demo_org.id
                )
            )
            existing_task = result.scalar_one_or_none()

            if existing_task and not force:
                logger.info(f"Task '{task_config['name']}' already exists, skipping")
                continue

            if existing_task and force:
                # Update existing task
                for key, value in task_config.items():
                    setattr(existing_task, key, value)
                logger.info(f"Updated task: {task_config['name']}")
            else:
                # Create new task
                task = Task(**task_config)
                db.add(task)
                logger.info(f"Created task: {task_config['name']}")

    async def seed_experiments(self, db: AsyncSession, force: bool = False) -> None:
        """Seed demo experiments."""
        logger.info("Seeding experiments...")

        # Get demo organization
        org_result = await db.execute(
            select(Organization).where(Organization.name == "Demo Lab")
        )
        demo_org = org_result.scalar_one()

        experiments_config = [
            {
                "name": "Demo LED Control Experiment",
                "description": "Basic demonstration of LED control across multiple devices",
                "organization_id": demo_org.id,
                "status": ExperimentStatus.READY,
                "protocol_version": "1.0.0",
                "parameters": {
                    "led_pin": 18,
                    "blink_duration": 2000,
                    "inter_trial_interval": 5000
                },
                "experiment_metadata": {
                    "purpose": "Hardware connectivity testing",
                    "expected_duration": "10 minutes",
                    "devices_required": 2
                }
            },
            {
                "name": "Environmental Monitoring",
                "description": "Continuous monitoring of environmental conditions",
                "organization_id": demo_org.id,
                "status": ExperimentStatus.DRAFT,
                "protocol_version": "1.0.0",
                "parameters": {
                    "sampling_interval": 60000,  # 1 minute
                    "sensors": ["temperature", "humidity", "light"],
                    "alert_thresholds": {
                        "temperature": {"min": 20, "max": 28},
                        "humidity": {"min": 30, "max": 70}
                    }
                },
                "experiment_metadata": {
                    "purpose": "Environmental data collection",
                    "expected_duration": "24 hours",
                    "data_retention": "30 days"
                }
            }
        ]

        for exp_config in experiments_config:
            # Check if experiment exists
            result = await db.execute(
                select(Experiment).where(
                    Experiment.name == exp_config["name"],
                    Experiment.organization_id == demo_org.id
                )
            )
            existing_exp = result.scalar_one_or_none()

            if existing_exp and not force:
                logger.info(f"Experiment '{exp_config['name']}' already exists, skipping")
                continue

            if existing_exp and force:
                # Update existing experiment
                for key, value in exp_config.items():
                    setattr(existing_exp, key, value)
                logger.info(f"Updated experiment: {exp_config['name']}")
            else:
                # Create new experiment
                experiment = Experiment(**exp_config)
                db.add(experiment)
                logger.info(f"Created experiment: {exp_config['name']}")

    async def seed_participants(self, db: AsyncSession, force: bool = False) -> None:
        """Seed demo participants."""
        logger.info("Seeding participants...")

        # Get demo organization and experiments
        org_result = await db.execute(
            select(Organization).where(Organization.name == "Demo Lab")
        )
        demo_org = org_result.scalar_one()

        exp_result = await db.execute(
            select(Experiment).where(
                Experiment.name == "Demo LED Control Experiment",
                Experiment.organization_id == demo_org.id
            )
        )
        demo_experiment = exp_result.scalar_one_or_none()

        if not demo_experiment:
            logger.warning("Demo experiment not found, skipping participant seeding")
            return

        participants_config = [
            {
                "identifier": "RAT_001",
                "species": "Rattus norvegicus",
                "strain": "Sprague Dawley",
                "sex": "Male",
                "age_days": 90,
                "weight_grams": 350.5,
                "experiment_id": demo_experiment.id,
                "status": ParticipantStatus.ACTIVE,
                "participant_metadata": {
                    "cage_number": "C-001",
                    "housing_condition": "single",
                    "food_restriction": False,
                    "health_status": "normal",
                    "training_history": {
                        "sessions_completed": 5,
                        "performance_level": "novice"
                    }
                },
                "notes": "Healthy male rat, good candidate for behavioral testing"
            },
            {
                "identifier": "RAT_002",
                "species": "Rattus norvegicus",
                "strain": "Sprague Dawley",
                "sex": "Female",
                "age_days": 85,
                "weight_grams": 280.3,
                "experiment_id": demo_experiment.id,
                "status": ParticipantStatus.ACTIVE,
                "participant_metadata": {
                    "cage_number": "C-002",
                    "housing_condition": "single",
                    "food_restriction": True,
                    "health_status": "normal",
                    "training_history": {
                        "sessions_completed": 8,
                        "performance_level": "intermediate"
                    }
                },
                "notes": "Experienced female rat, shows good learning acquisition"
            },
            {
                "identifier": "RAT_003",
                "species": "Rattus norvegicus",
                "strain": "Long Evans",
                "sex": "Male",
                "age_days": 120,
                "weight_grams": 420.1,
                "experiment_id": demo_experiment.id,
                "status": ParticipantStatus.INACTIVE,
                "participant_metadata": {
                    "cage_number": "C-003",
                    "housing_condition": "paired",
                    "food_restriction": False,
                    "health_status": "recovered",
                    "training_history": {
                        "sessions_completed": 12,
                        "performance_level": "expert"
                    }
                },
                "notes": "Previously trained rat, temporarily inactive due to health recovery"
            }
        ]

        for participant_config in participants_config:
            # Check if participant exists
            result = await db.execute(
                select(Participant).where(
                    Participant.identifier == participant_config["identifier"],
                    Participant.experiment_id == demo_experiment.id
                )
            )
            existing_participant = result.scalar_one_or_none()

            if existing_participant and not force:
                logger.info(f"Participant '{participant_config['identifier']}' already exists, skipping")
                continue

            if existing_participant and force:
                # Update existing participant
                for key, value in participant_config.items():
                    setattr(existing_participant, key, value)
                logger.info(f"Updated participant: {participant_config['identifier']}")
            else:
                # Create new participant
                participant = Participant(**participant_config)
                db.add(participant)
                logger.info(f"Created participant: {participant_config['identifier']}")

    async def clean_seed_data(self, db: AsyncSession) -> None:
        """Clean all seed data (for testing)."""
        logger.warning("Cleaning all seed data...")

        # Delete in reverse order due to foreign keys
        # Domain data cleanup
        await db.execute("DELETE FROM device_data")
        await db.execute("DELETE FROM task_executions")
        await db.execute("DELETE FROM participants")
        await db.execute("DELETE FROM experiment_tasks")
        await db.execute("DELETE FROM experiment_devices")
        await db.execute("DELETE FROM experiments WHERE name LIKE 'Demo%' OR name LIKE 'Environmental%'")
        await db.execute("DELETE FROM tasks WHERE name LIKE 'Simple%' OR name LIKE 'Sensor%' OR name LIKE 'Behavioral%'")
        await db.execute("DELETE FROM devices WHERE serial_number LIKE 'RPI4-DEMO-%' OR serial_number = 'SIM-DEV-001'")

        # Authentication data cleanup
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
"""
Test configuration and fixtures for the authentication system.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from uuid import uuid4

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db_session
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.main import app
from app.models.auth import User, Role, Permission, RefreshToken, UserSession
from app.models.base import Organization


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def redis_client():
    """Create a test Redis client (using Redis 0 for testing)."""
    client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

    # Clear test database
    await client.flushdb()

    yield client

    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override the database dependency for testing."""
    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture
def test_app(override_get_db) -> FastAPI:
    """Create test FastAPI application."""
    app.dependency_overrides[get_db_session] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver"
    ) as ac:
        yield ac


# Test data fixtures
@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Organization",
        description="Test organization for unit tests",
        settings={
            "max_devices": 100,
            "max_experiments": 1000,
            "storage_limit_gb": 100,
            "features": {
                "video_streaming": True,
                "ml_analysis": True,
                "api_access": True,
                "custom_tasks": True
            }
        }
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_permissions(db_session: AsyncSession) -> list[Permission]:
    """Create test permissions."""
    permissions = [
        Permission(
            name="users:read",
            display_name="Read Users",
            description="View user information",
            resource="users",
            action="read"
        ),
        Permission(
            name="users:write",
            display_name="Write Users",
            description="Create and update users",
            resource="users",
            action="write"
        ),
        Permission(
            name="experiments:read",
            display_name="Read Experiments",
            description="View experiments",
            resource="experiments",
            action="read"
        ),
        Permission(
            name="experiments:write",
            display_name="Write Experiments",
            description="Create and manage experiments",
            resource="experiments",
            action="write"
        ),
        Permission(
            name="system:admin",
            display_name="System Admin",
            description="Full system administration",
            resource="system",
            action="admin"
        )
    ]

    for perm in permissions:
        db_session.add(perm)

    await db_session.commit()

    for perm in permissions:
        await db_session.refresh(perm)

    return permissions


@pytest_asyncio.fixture
async def test_roles(db_session: AsyncSession, test_permissions: list[Permission]) -> list[Role]:
    """Create test roles with permissions."""
    admin_role = Role(
        name="Admin",
        description="Administrator role",
        permissions=test_permissions  # All permissions
    )

    user_role = Role(
        name="User",
        description="Regular user role",
        permissions=[p for p in test_permissions if p.name in ["users:read", "experiments:read"]]
    )

    researcher_role = Role(
        name="Researcher",
        description="Researcher role",
        permissions=[p for p in test_permissions if p.name.startswith(("users:", "experiments:"))]
    )

    roles = [admin_role, user_role, researcher_role]

    for role in roles:
        db_session.add(role)

    await db_session.commit()

    for role in roles:
        await db_session.refresh(role)

    return roles


@pytest_asyncio.fixture
async def test_user(
    db_session: AsyncSession,
    test_organization: Organization,
    test_roles: list[Role]
) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        first_name="Test",
        last_name="User",
        password_hash=get_password_hash("testpassword123"),
        organization_id=test_organization.id,
        is_active=True,
        is_verified=True,
        email_verified=True,
        roles=[role for role in test_roles if role.name == "User"]
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin_user(
    db_session: AsyncSession,
    test_organization: Organization,
    test_roles: list[Role]
) -> User:
    """Create a test admin user."""
    admin = User(
        email="admin@example.com",
        username="admin",
        first_name="Admin",
        last_name="User",
        password_hash=get_password_hash("adminpassword123"),
        organization_id=test_organization.id,
        is_active=True,
        is_verified=True,
        email_verified=True,
        is_superuser=True,
        roles=[role for role in test_roles if role.name == "Admin"]
    )

    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_researcher_user(
    db_session: AsyncSession,
    test_organization: Organization,
    test_roles: list[Role]
) -> User:
    """Create a test researcher user."""
    researcher = User(
        email="researcher@example.com",
        username="researcher",
        first_name="Research",
        last_name="User",
        password_hash=get_password_hash("researchpassword123"),
        organization_id=test_organization.id,
        is_active=True,
        is_verified=True,
        email_verified=True,
        roles=[role for role in test_roles if role.name == "Researcher"]
    )

    db_session.add(researcher)
    await db_session.commit()
    await db_session.refresh(researcher)
    return researcher


@pytest.fixture
def test_user_tokens(test_user: User) -> dict:
    """Create test tokens for user."""
    access_token = create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@pytest.fixture
def test_admin_tokens(test_admin_user: User) -> dict:
    """Create test tokens for admin user."""
    access_token = create_access_token(
        data={"sub": str(test_admin_user.id), "email": test_admin_user.email}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(test_admin_user.id), "email": test_admin_user.email}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@pytest.fixture
def auth_headers(test_user_tokens: dict) -> dict:
    """Create authorization headers for regular user."""
    return {"Authorization": f"Bearer {test_user_tokens['access_token']}"}


@pytest.fixture
def admin_auth_headers(test_admin_tokens: dict) -> dict:
    """Create authorization headers for admin user."""
    return {"Authorization": f"Bearer {test_admin_tokens['access_token']}"}


# Test environment configuration
@pytest.fixture(autouse=True)
def test_env():
    """Set test environment variables."""
    os.environ["TESTING"] = "true"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
    os.environ["JWT_REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
    yield
    # Cleanup is automatic when test ends


# Utility functions for tests
def create_test_user_data(**overrides) -> dict:
    """Create test user registration data."""
    base_data = {
        "email": f"test{uuid4().hex[:8]}@example.com",
        "username": f"testuser{uuid4().hex[:8]}",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User"
    }
    base_data.update(overrides)
    return base_data


def create_test_role_data(**overrides) -> dict:
    """Create test role data."""
    base_data = {
        "name": f"TestRole{uuid4().hex[:8]}",
        "description": "Test role for unit tests",
        "permissions": []
    }
    base_data.update(overrides)
    return base_data


def create_test_permission_data(**overrides) -> dict:
    """Create test permission data."""
    base_data = {
        "name": f"test:action{uuid4().hex[:8]}",
        "display_name": "Test Permission",
        "description": "Test permission for unit tests",
        "resource": "test",
        "action": "action"
    }
    base_data.update(overrides)
    return base_data


# All async fixtures are already marked with @pytest_asyncio.fixture decorator
"""
LICS Backend API v1 Router

Main API router for version 1 endpoints. Includes all API route modules
and provides centralized configuration for the API layer.
"""

from fastapi import APIRouter, Depends

from app.api.v1 import (
    health, auth, rbac, organizations, devices,
    experiments, tasks, participants
)
from app.core.config import settings
from app.core.dependencies import get_current_user

# Create main API router
api_router = APIRouter()

# Include health check endpoints (public)
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
    responses={
        503: {"description": "Service Unavailable"},
        500: {"description": "Internal Server Error"}
    }
)

# Include authentication endpoints (public)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"}
    }
)

# Include RBAC endpoints (requires authentication)
api_router.include_router(
    rbac.router,
    prefix="/rbac",
    tags=["rbac"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"}
    }
)

# ===== DOMAIN ENTITY ENDPOINTS (All require authentication) =====

# Organizations management
api_router.include_router(
    organizations.router,
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"}
    }
)

# Device management and telemetry
api_router.include_router(
    devices.router,
    prefix="/devices",
    tags=["devices"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"}
    }
)

# Experiment lifecycle management
api_router.include_router(
    experiments.router,
    prefix="/experiments",
    tags=["experiments"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"}
    }
)

# Task definitions and templates
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"}
    }
)

# Participant management
api_router.include_router(
    participants.router,
    prefix="/participants",
    tags=["participants"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"}
    }
)

# TODO: Add future route modules
# api_router.include_router(
#     streaming.router,
#     prefix="/streaming",
#     tags=["streaming"],
#     dependencies=[Depends(get_current_user)]
# )

# api_router.include_router(
#     analytics.router,
#     prefix="/analytics",
#     tags=["analytics"],
#     dependencies=[Depends(get_current_user)]
# )
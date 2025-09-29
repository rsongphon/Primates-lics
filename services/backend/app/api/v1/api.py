"""
LICS Backend API v1 Router

Main API router for version 1 endpoints. Includes all API route modules
and provides centralized configuration for the API layer.
"""

from fastapi import APIRouter

from app.api.v1 import health
from app.core.config import settings

# Create main API router
api_router = APIRouter()

# Include health check endpoints (from existing health.py)
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
    responses={
        503: {"description": "Service Unavailable"},
        500: {"description": "Internal Server Error"}
    }
)

# TODO: Add other route modules as they are implemented
# Example structure for future modules:

# api_router.include_router(
#     auth.router,
#     prefix="/auth",
#     tags=["authentication"],
#     responses={
#         401: {"description": "Unauthorized"},
#         403: {"description": "Forbidden"}
#     }
# )

# api_router.include_router(
#     users.router,
#     prefix="/users",
#     tags=["users"],
#     dependencies=[Depends(get_current_user)]
# )

# api_router.include_router(
#     organizations.router,
#     prefix="/organizations",
#     tags=["organizations"],
#     dependencies=[Depends(get_current_user)]
# )

# api_router.include_router(
#     devices.router,
#     prefix="/devices",
#     tags=["devices"],
#     dependencies=[Depends(get_current_user)]
# )

# api_router.include_router(
#     experiments.router,
#     prefix="/experiments",
#     tags=["experiments"],
#     dependencies=[Depends(get_current_user)]
# )

# api_router.include_router(
#     tasks.router,
#     prefix="/tasks",
#     tags=["tasks"],
#     dependencies=[Depends(get_current_user)]
# )

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
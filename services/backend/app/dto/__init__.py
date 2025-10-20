"""
Data Transfer Object (DTO) Layer

This module provides clean separation between ORM models and API responses.
DTOs ensure that database objects never leak into the HTTP layer.

Usage:
    from app.dto import UserConverter, RoleConverter

    # In service:
    user_dto = await UserConverter.to_user_profile(user, session)
    return user_dto  # Returns Pydantic model, not ORM object
"""

from app.dto.converters import (
    UserConverter,
    RoleConverter,
    PermissionConverter,
    OrganizationConverter
)

__all__ = [
    "UserConverter",
    "RoleConverter",
    "PermissionConverter",
    "OrganizationConverter"
]

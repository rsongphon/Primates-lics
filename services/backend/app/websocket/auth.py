"""
LICS WebSocket Authentication

JWT-based authentication for WebSocket connections.
Follows Documentation.md Section 10.1 authentication patterns.
"""

from typing import Optional, Dict, Any, Tuple
from urllib.parse import parse_qs

from jose import jwt, JWTError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import TokenData, validate_token_data
from app.models.auth import User
from app.repositories.auth import UserRepository
from app.core.database import get_db_session

logger = get_logger(__name__)


class WebSocketAuthError(Exception):
    """WebSocket authentication error."""

    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


async def extract_token_from_request(environ: Dict[str, Any]) -> Optional[str]:
    """
    Extract JWT token from WebSocket connection request.

    Checks:
    1. Authorization header (Bearer token)
    2. Query parameter (?token=...)
    3. Cookie (if configured)

    Args:
        environ: WSGI environment dict

    Returns:
        JWT token string or None
    """
    # Try Authorization header first
    auth_header = environ.get("HTTP_AUTHORIZATION")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    # Try query parameter
    query_string = environ.get("QUERY_STRING", "")
    if query_string:
        params = parse_qs(query_string)
        tokens = params.get("token", [])
        if tokens:
            return tokens[0]

    # Try cookie (if present)
    cookie_header = environ.get("HTTP_COOKIE", "")
    if cookie_header and settings.JWT_COOKIE_NAME:
        cookies = {}
        for cookie in cookie_header.split(";"):
            if "=" in cookie:
                key, value = cookie.strip().split("=", 1)
                cookies[key] = value

        token = cookies.get(settings.JWT_COOKIE_NAME)
        if token:
            return token

    return None


def decode_websocket_token(token: str) -> TokenData:
    """
    Decode and validate JWT token for WebSocket connection.

    Args:
        token: JWT token string

    Returns:
        TokenData object with user information

    Raises:
        WebSocketAuthError: If token is invalid or expired
    """
    try:
        # Decode JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )

        # Validate token data
        token_data = validate_token_data(payload)
        return token_data

    except JWTError as e:
        logger.warning(f"JWT validation failed for WebSocket: {e}")
        raise WebSocketAuthError(
            message=f"Invalid token: {str(e)}",
            code="INVALID_TOKEN"
        )
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise WebSocketAuthError(
            message="Token validation failed",
            code="TOKEN_ERROR"
        )


async def authenticate_websocket(environ: Dict[str, Any]) -> Tuple[Optional[User], Optional[str]]:
    """
    Authenticate WebSocket connection using JWT.

    Args:
        environ: WSGI environment dict

    Returns:
        Tuple of (User object, error message)
        Returns (None, error_msg) if authentication fails
        Returns (user, None) if authentication succeeds
    """
    try:
        # Extract token from request
        token = await extract_token_from_request(environ)
        if not token:
            return None, "No authentication token provided"

        # Decode and validate token
        token_data = decode_websocket_token(token)

        # Get user from database
        async with get_db_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(token_data.user_id)

            if not user:
                return None, "User not found"

            if not user.is_active:
                return None, "User account is inactive"

            if user.deleted_at is not None:
                return None, "User account has been deleted"

            return user, None

    except WebSocketAuthError as e:
        logger.warning(f"WebSocket auth error: {e.message}")
        return None, e.message

    except Exception as e:
        logger.error(f"Unexpected error during WebSocket authentication: {e}")
        return None, "Authentication failed"


async def check_websocket_permission(
    user: User,
    resource: str,
    action: str
) -> bool:
    """
    Check if user has permission for WebSocket action.

    Args:
        user: Authenticated user
        resource: Resource type (e.g., "device", "experiment")
        action: Action type (e.g., "view", "control")

    Returns:
        True if user has permission, False otherwise
    """
    # Superusers have all permissions
    if hasattr(user, "is_superuser") and user.is_superuser:
        return True

    # Load user's permissions from database
    try:
        async with get_db_session() as session:
            user_repo = UserRepository(session)
            user_with_permissions = await user_repo.get_user_with_permissions(user.id)

            if not user_with_permissions:
                return False

            # Check if user has the required permission
            permission_string = f"{resource}:{action}"

            for role in user_with_permissions.roles:
                for permission in role.permissions:
                    if permission.name == permission_string:
                        return True

            return False

    except Exception as e:
        logger.error(f"Error checking WebSocket permission: {e}")
        return False


async def can_access_device(user: User, device_id: str) -> bool:
    """
    Check if user can access a specific device.

    Args:
        user: Authenticated user
        device_id: Device identifier

    Returns:
        True if user has access, False otherwise
    """
    # Check device:view permission
    has_permission = await check_websocket_permission(user, "device", "view")
    if not has_permission:
        return False

    # TODO: Add organization-based access control
    # Check if device belongs to user's organization

    return True


async def can_access_experiment(user: User, experiment_id: str) -> bool:
    """
    Check if user can access a specific experiment.

    Args:
        user: Authenticated user
        experiment_id: Experiment identifier

    Returns:
        True if user has access, False otherwise
    """
    # Check experiment:view permission
    has_permission = await check_websocket_permission(user, "experiment", "view")
    if not has_permission:
        return False

    # TODO: Add organization-based access control
    # Check if experiment belongs to user's organization

    return True


async def can_access_task(user: User, task_id: str) -> bool:
    """
    Check if user can access a specific task.

    Args:
        user: Authenticated user
        task_id: Task identifier

    Returns:
        True if user has access, False otherwise
    """
    # Check task:view permission
    has_permission = await check_websocket_permission(user, "task", "view")
    if not has_permission:
        return False

    # TODO: Add organization-based access control
    # Check if task belongs to user's organization or is public

    return True


async def can_access_organization(user: User, org_id: str) -> bool:
    """
    Check if user can access organization data.

    Args:
        user: Authenticated user
        org_id: Organization identifier

    Returns:
        True if user has access, False otherwise
    """
    # Check if user belongs to the organization
    if hasattr(user, "organization_id") and str(user.organization_id) == org_id:
        return True

    # Check organization:view permission for cross-org access
    has_permission = await check_websocket_permission(user, "organization", "view")
    return has_permission

"""
Security utilities for authentication and authorization.

This module provides JWT token management, password hashing, and other
security-related functionality for the LICS application.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password hashing context using Argon2id (recommended by OWASP)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,        # 3 iterations
    argon2__parallelism=1,      # Single thread
)

# Token types
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
ID_TOKEN_TYPE = "id"
DEVICE_TOKEN_TYPE = "device"
PASSWORD_RESET_TOKEN_TYPE = "password_reset"

# Token expiry times
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
ID_TOKEN_EXPIRE_MINUTES = 60
DEVICE_TOKEN_EXPIRE_DAYS = 30
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 60


class TokenData:
    """Token data container for JWT claims."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        organization_id: Optional[str] = None,
        roles: Optional[list] = None,
        permissions: Optional[list] = None,
        token_type: Optional[str] = None,
        device_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.organization_id = organization_id
        self.roles = roles or []
        self.permissions = permissions or []
        self.token_type = token_type
        self.device_id = device_id
        self._payload = {}  # Store raw payload for unmapped fields

    def __getitem__(self, key: Union[str, int]) -> Any:
        """Allow dict-style access to token data."""
        if not isinstance(key, str):
            raise TypeError(f"TokenData indices must be strings, not {type(key).__name__}")

        # Map JWT standard claims to TokenData attributes
        if key == "sub":
            return self.user_id
        if key == "type":
            return self.token_type

        # Try to get from attributes first
        if hasattr(self, key):
            return getattr(self, key)

        # Fall back to raw payload
        return self._payload.get(key)

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        if key in ["sub", "type"]:
            return True
        if hasattr(self, key):
            return True
        return key in self._payload

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute with default value."""
        # Map JWT standard claims to TokenData attributes
        if key == "sub":
            return self.user_id
        if key == "type":
            return self.token_type

        # Try to get from attributes first
        if hasattr(self, key):
            return getattr(self, key)

        # Fall back to raw payload
        return self._payload.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert TokenData to dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "organization_id": self.organization_id,
            "roles": self.roles,
            "permissions": self.permissions,
            "token_type": self.token_type,
            "device_id": self.device_id,
        }


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using Argon2id.

    Args:
        password: The plain text password

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def generate_password_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def create_access_token(
    subject: Union[str, Any, Dict[str, Any]],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create an access token.

    Args:
        subject: The subject (user ID) or dict with user data
        expires_delta: Custom expiration time
        additional_claims: Additional claims to include in token

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Generate unique JTI for token tracking
    jti = secrets.token_urlsafe(32)

    # Handle dict subject with user data
    if isinstance(subject, dict):
        # Get subject ID, handling None case
        sub_value = subject.get("sub") or subject.get("user_id")
        # JWT requires sub to be a string
        # Use special marker for None to preserve it through encode/decode
        if sub_value is None:
            sub_str = "__NONE__"
            to_encode = {"_sub_was_none": True}
        else:
            sub_str = str(sub_value)
            to_encode = {}

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "sub": sub_str,
            "type": ACCESS_TOKEN_TYPE,
            "jti": jti,
        })
        # Add all other fields from dict (preserving custom claims)
        for key, value in subject.items():
            if key not in ["sub", "user_id", "exp", "iat", "type", "jti"]:
                to_encode[key] = value
    else:
        # JWT requires sub to be a string
        if subject is None:
            sub_str = "__NONE__"
            to_encode = {"_sub_was_none": True}
        else:
            sub_str = str(subject)
            to_encode = {}

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "sub": sub_str,
            "type": ACCESS_TOKEN_TYPE,
            "jti": jti,
        })

    if additional_claims:
        to_encode.update(additional_claims)

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(f"Access token created for subject: {to_encode['sub']}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a refresh token.

    Args:
        subject: The subject (usually user ID) for the token
        expires_delta: Custom expiration time
        additional_claims: Additional claims to include in token

    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # Generate a unique identifier for this refresh token
    jti = secrets.token_urlsafe(32)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(subject),
        "type": REFRESH_TOKEN_TYPE,
        "jti": jti,  # JWT ID for tracking and revocation
    }

    if additional_claims:
        to_encode.update(additional_claims)

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(f"Refresh token created for subject: {subject}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise


def create_id_token(
    user_data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create an ID token with user profile information.

    Args:
        user_data: User profile data to include in token
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT ID token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ID_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(user_data.get("user_id")),
        "type": ID_TOKEN_TYPE,
        "email": user_data.get("email"),
        "username": user_data.get("username"),
        "organization_id": user_data.get("organization_id"),
        "roles": user_data.get("roles", []),
    }

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(f"ID token created for user: {user_data.get('username')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating ID token: {e}")
        raise


def create_device_token(
    device_id: str,
    organization_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a long-lived device token for edge devices.

    Args:
        device_id: Unique device identifier
        organization_id: Organization the device belongs to
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT device token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=DEVICE_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": device_id,
        "type": DEVICE_TOKEN_TYPE,
        "device_id": device_id,
        "organization_id": organization_id,
        "roles": ["device"],
    }

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(f"Device token created for device: {device_id}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating device token: {e}")
        raise


def create_password_reset_token_jwt(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a password reset token.

    Args:
        user_id: User ID
        email: User email for verification
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT password reset token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(user_id),
        "type": PASSWORD_RESET_TOKEN_TYPE,
        "email": email,
    }

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(f"Password reset token created for user: {user_id}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating password reset token: {e}")
        raise


def verify_token(token: str, token_type: Optional[str] = None, return_payload: bool = False) -> Optional[Union[TokenData, Dict[str, Any]]]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify
        token_type: Expected token type (optional)
        return_payload: If True, return raw payload dict instead of TokenData

    Returns:
        TokenData object or payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Check if token has expired
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            logger.warning("Token has expired")
            return None

        # Check token type if specified
        if token_type and payload.get("type") != token_type:
            logger.warning(f"Token type mismatch. Expected: {token_type}, Got: {payload.get('type')}")
            return None

        # Return raw payload if requested
        if return_payload:
            logger.debug(f"Token verified successfully for subject: {payload.get('sub')}")
            return payload

        # Handle None subject marker
        sub_value = payload.get("sub")
        if payload.get("_sub_was_none") and sub_value == "__NONE__":
            sub_value = None

        # Extract token data
        token_data = TokenData(
            user_id=sub_value,
            username=payload.get("username"),
            email=payload.get("email"),
            organization_id=payload.get("organization_id"),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            token_type=payload.get("type"),
            device_id=payload.get("device_id"),
        )
        # Store raw payload for access to non-mapped fields
        # Convert __NONE__ marker back to None in payload copy
        payload_copy = payload.copy()
        if payload.get("_sub_was_none"):
            payload_copy["sub"] = None
        token_data._payload = payload_copy

        logger.debug(f"Token verified successfully for subject: {token_data.user_id}")
        return token_data

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None


def get_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """
    Get the payload from a JWT token without verification.
    Useful for extracting JTI for blacklisting.

    Args:
        token: The JWT token

    Returns:
        Token payload dict if decodable, None otherwise
    """
    try:
        return jwt.get_unverified_claims(token)
    except Exception as e:
        logger.error(f"Error getting token payload: {e}")
        return None


def generate_api_key() -> str:
    """Generate a secure API key for programmatic access."""
    return f"lics_{secrets.token_urlsafe(40)}"


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired without full verification.

    Args:
        token: The JWT token to check

    Returns:
        True if expired, False otherwise
    """
    try:
        payload = jwt.get_unverified_claims(token)
        exp = payload.get("exp")
        if exp:
            return datetime.now(timezone.utc).timestamp() > exp
        return True  # No expiration time means invalid token
    except Exception:
        return True  # Any error means we consider it expired


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.

    Args:
        token: The JWT token

    Returns:
        Expiration datetime if available, None otherwise
    """
    try:
        payload = jwt.get_unverified_claims(token)
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except Exception:
        return None
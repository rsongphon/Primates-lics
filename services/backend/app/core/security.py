"""
Security utilities for authentication and authorization.

This module provides JWT token management, password hashing, and other
security-related functionality for the LICS application.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

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
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create an access token.

    Args:
        subject: The subject (usually user ID) for the token
        expires_delta: Custom expiration time
        additional_claims: Additional claims to include in token

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(subject),
        "type": ACCESS_TOKEN_TYPE,
    }

    if additional_claims:
        to_encode.update(additional_claims)

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(f"Access token created for subject: {subject}")
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


def verify_token(token: str, token_type: Optional[str] = None) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify
        token_type: Expected token type (optional)

    Returns:
        TokenData object if valid, None otherwise
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

        # Extract token data
        token_data = TokenData(
            user_id=payload.get("sub"),
            username=payload.get("username"),
            email=payload.get("email"),
            organization_id=payload.get("organization_id"),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            token_type=payload.get("type"),
            device_id=payload.get("device_id"),
        )

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
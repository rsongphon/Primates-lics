"""
Additional security utility functions.

This module provides password strength validation, CSRF protection, API key hashing,
and other security utilities for the LICS application.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.core.logging import get_logger

logger = get_logger(__name__)


# Password strength requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL_CHAR = True


def verify_password_strength(password: str) -> bool:
    """
    Verify password meets strength requirements.

    Args:
        password: The password to verify

    Returns:
        True if password meets requirements, False otherwise
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False

    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False

    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False

    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        return False

    if PASSWORD_REQUIRE_SPECIAL_CHAR and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False

    return True


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification.

    Args:
        token: The JWT token to decode

    Returns:
        Token payload dict if successful, None otherwise
    """
    try:
        from jose import jwt
        return jwt.get_unverified_claims(token)
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None


def get_token_type(token: str) -> Optional[str]:
    """
    Get the type of a JWT token.

    Args:
        token: The JWT token

    Returns:
        Token type string if available, None otherwise
    """
    payload = decode_token(token)
    return payload.get("type") if payload else None


async def is_token_blacklisted(jti: str, redis_client: Any) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        jti: The JWT ID to check
        redis_client: Redis client instance

    Returns:
        True if token is blacklisted, False otherwise
    """
    try:
        result = await redis_client.get(f"blacklist:{jti}")
        return result is not None
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        return False


async def blacklist_token(jti: str, redis_client: Any, expires_in: Optional[int] = None) -> bool:
    """
    Blacklist a token by its JTI.

    Args:
        jti: The JWT ID to blacklist
        redis_client: Redis client instance
        expires_in: Optional expiry time in seconds

    Returns:
        True if successful, False otherwise
    """
    try:
        if expires_in:
            await redis_client.setex(f"blacklist:{jti}", expires_in, "1")
        else:
            await redis_client.set(f"blacklist:{jti}", "1")
        return True
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
        return False


def generate_secure_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string.

    Args:
        length: Length of the string to generate (in characters)

    Returns:
        Random URL-safe string of exact length
    """
    # Handle edge cases
    if length <= 0:
        return ""

    # Generate a longer random string and trim to exact length
    # token_urlsafe returns ~4/3 the length in bytes, so we generate more than needed
    random_str = secrets.token_urlsafe(length)
    # Trim to exact length
    return random_str[:length]


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        api_key: The API key to hash

    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against a hashed key.

    Args:
        api_key: The plain API key
        hashed_key: The hashed API key from database

    Returns:
        True if API key matches, False otherwise
    """
    return constant_time_compare(hash_api_key(api_key), hashed_key)


def create_csrf_token(secret_key: Optional[str] = None) -> str:
    """
    Create a CSRF token.

    Args:
        secret_key: Optional secret key for token generation

    Returns:
        CSRF token string
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected_token: Optional[str] = None) -> bool:
    """
    Verify a CSRF token.

    Args:
        token: The token to verify
        expected_token: The expected token value (optional for basic validation)

    Returns:
        True if token is valid, False otherwise
    """
    # Basic validation: check if token is a valid format
    if not token or len(token) < 16:
        return False

    # If expected token provided, compare
    if expected_token:
        return constant_time_compare(token, expected_token)

    # Otherwise just validate format (URL-safe base64)
    import re
    return bool(re.match(r'^[A-Za-z0-9_-]+$', token))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    if not filename:
        return "untitled"

    # Remove path separators and parent directory references
    filename = filename.replace('/', '_').replace('\\', '_').replace('..', '')

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)

    # Remove leading/trailing dots and underscores
    filename = filename.strip('._')

    # If empty after sanitization, return default
    if not filename or filename == '' or set(filename) == {'.', '_'}:
        return "untitled"

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    return filename


def is_safe_url(url: str, allowed_hosts: Optional[list] = None) -> bool:
    """
    Check if a URL is safe for redirects.

    Args:
        url: The URL to check
        allowed_hosts: Optional list of allowed host names

    Returns:
        True if URL is safe, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Block dangerous schemes
        dangerous_schemes = ['javascript', 'data', 'vbscript', 'file']
        if parsed.scheme and parsed.scheme.lower() in dangerous_schemes:
            return False

        # Block protocol-relative URLs that could be used for open redirects
        if url.startswith('//'):
            return False

        # Check if it's a relative URL (safe)
        if not parsed.scheme and not parsed.netloc:
            return True

        # Allow http and https URLs
        safe_schemes = ['http', 'https', '']
        if parsed.scheme and parsed.scheme.lower() not in safe_schemes:
            return False

        # If allowed hosts specified, check against them
        if allowed_hosts and parsed.netloc:
            return parsed.netloc in allowed_hosts

        # By default, allow http/https URLs
        return parsed.scheme.lower() in ['http', 'https'] or not parsed.scheme
    except Exception:
        return False


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings match, False otherwise
    """
    return hmac.compare_digest(a.encode(), b.encode())

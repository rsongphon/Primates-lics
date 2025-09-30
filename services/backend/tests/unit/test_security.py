"""
Unit tests for security utilities (JWT, password hashing, validation).
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from jose import jwt, JWTError

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_id_token,
    create_device_token,
    create_password_reset_token_jwt,
    verify_token,
    get_token_payload,
    get_token_expiry,
    is_token_expired,
    generate_password_reset_token,
    generate_api_key
)
from app.core.config import settings


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_get_password_hash_returns_string(self):
        """Test that password hashing returns a string."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_get_password_hash_different_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_strings(self):
        """Test password verification with empty strings."""
        assert verify_password("", "") is False
        assert verify_password("password", "") is False
        assert verify_password("", "hash") is False

    def test_password_hash_with_special_characters(self):
        """Test password hashing with special characters."""
        password = "p@$$w0rd!#$%^&*(){}[]|\\:;\"'<>,.?/~`"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_hash_with_unicode(self):
        """Test password hashing with unicode characters."""
        password = "пароль测试密码🔒"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True


class TestPasswordStrength:
    """Test password strength validation."""

    def test_verify_password_strength_valid(self):
        """Test password strength validation with valid passwords."""
        valid_passwords = [
            "StrongPassword123!",
            "MySecureP@ssw0rd",
            "Complex!Pass123",
            "AnotherG00d!Pass"
        ]

        for password in valid_passwords:
            assert verify_password_strength(password) is True

    def test_verify_password_strength_too_short(self):
        """Test password strength validation with short passwords."""
        short_passwords = [
            "Short1!",
            "Pass1!",
            "123456!",
            "Aa1!"
        ]

        for password in short_passwords:
            assert verify_password_strength(password) is False

    def test_verify_password_strength_no_uppercase(self):
        """Test password strength validation without uppercase."""
        passwords = [
            "lowercase123!",
            "alllower456@",
            "nouppercase789#"
        ]

        for password in passwords:
            assert verify_password_strength(password) is False

    def test_verify_password_strength_no_lowercase(self):
        """Test password strength validation without lowercase."""
        passwords = [
            "UPPERCASE123!",
            "ALLUPPER456@",
            "NOLOWERCASE789#"
        ]

        for password in passwords:
            assert verify_password_strength(password) is False

    def test_verify_password_strength_no_digit(self):
        """Test password strength validation without digits."""
        passwords = [
            "NoDigitsHere!",
            "OnlyLetters@",
            "MissingNumbers#"
        ]

        for password in passwords:
            assert verify_password_strength(password) is False

    def test_verify_password_strength_no_special_char(self):
        """Test password strength validation without special characters."""
        passwords = [
            "NoSpecialChars123",
            "MissingSymbols456",
            "OnlyAlphaNum789"
        ]

        for password in passwords:
            assert verify_password_strength(password) is False


class TestJWTTokenGeneration:
    """Test JWT token generation."""

    def test_create_access_token_basic(self):
        """Test basic access token creation."""
        data = {"sub": "test_user", "email": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test access token creation with custom expiry."""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)

        # Decode to verify expiry
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert "exp" in payload
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "test_user", "email": "test@example.com"}
        token = create_refresh_token(data)

        assert isinstance(token, str)

        # Decode to verify type
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "refresh"

    def test_create_id_token(self):
        """Test ID token creation."""
        data = {"sub": "test_user", "email": "test@example.com", "name": "Test User"}
        token = create_id_token(data)

        assert isinstance(token, str)

        # Decode to verify type
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "id"

    def test_create_device_token(self):
        """Test device token creation."""
        device_id = "device_123"
        organization_id = "org_456"
        token = create_device_token(device_id, organization_id)

        assert isinstance(token, str)

        # Decode to verify type and longer expiry
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "device"

    def test_create_password_reset_token(self):
        """Test password reset token creation."""
        user_id = "test_user"
        email = "test@example.com"
        token = create_password_reset_token_jwt(user_id, email)

        assert isinstance(token, str)

        # Decode to verify type and short expiry
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "password_reset"

    def test_token_contains_required_claims(self):
        """Test that tokens contain required claims."""
        data = {"sub": "test_user", "email": "test@example.com"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Check required claims
        assert "sub" in payload
        assert "email" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
        assert "type" in payload

    def test_token_jti_unique(self):
        """Test that token JTI (JWT ID) is unique."""
        data = {"sub": "test_user"}
        token1 = create_access_token(data)
        token2 = create_access_token(data)

        payload1 = jwt.decode(token1, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        payload2 = jwt.decode(token2, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert payload1["jti"] != payload2["jti"]


class TestJWTTokenValidation:
    """Test JWT token validation."""

    def test_verify_token_valid(self):
        """Test verification of valid token."""
        data = {"sub": "test_user", "email": "test@example.com"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_verify_token_invalid_signature(self):
        """Test verification of token with invalid signature."""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        # Tamper with token
        tampered_token = token[:-10] + "tampered123"

        payload = verify_token(tampered_token)
        assert payload is None

    def test_verify_token_expired(self):
        """Test verification of expired token."""
        data = {"sub": "test_user"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)

        payload = verify_token(token)
        assert payload is None

    def test_verify_token_malformed(self):
        """Test verification of malformed token."""
        malformed_tokens = [
            "not.a.token",
            "invalid_token",
            "",
            "header.payload",  # Missing signature
            "too.many.parts.here.token"
        ]

        for token in malformed_tokens:
            payload = verify_token(token)
            assert payload is None

    def test_decode_token_success(self):
        """Test successful token decoding."""
        data = {"sub": "test_user", "custom_claim": "value"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["custom_claim"] == "value"

    def test_get_token_type(self):
        """Test token type extraction."""
        access_token = create_access_token({"sub": "user"})
        refresh_token = create_refresh_token({"sub": "user"})

        assert get_token_type(access_token) == "access"
        assert get_token_type(refresh_token) == "refresh"

    def test_get_token_expiry(self):
        """Test token expiry extraction."""
        data = {"sub": "user"}
        token = create_access_token(data)

        expiry = get_token_expiry(token)

        assert isinstance(expiry, datetime)
        assert expiry > datetime.now(timezone.utc)


class TestTokenBlacklisting:
    """Test token blacklisting functionality."""

    @pytest.mark.asyncio
    async def test_blacklist_token(self, redis_client):
        """Test token blacklisting."""
        data = {"sub": "test_user"}
        token = create_access_token(data)
        payload = decode_token(token)
        jti = payload["jti"]

        # Initially not blacklisted
        assert await is_token_blacklisted(jti, redis_client) is False

        # Blacklist token
        await blacklist_token(jti, redis_client)

        # Now should be blacklisted
        assert await is_token_blacklisted(jti, redis_client) is True

    @pytest.mark.asyncio
    async def test_blacklist_token_with_expiry(self, redis_client):
        """Test token blacklisting with expiry."""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        payload = decode_token(token)
        jti = payload["jti"]

        # Blacklist with expiry
        await blacklist_token(jti, redis_client, expires_delta)

        # Should be blacklisted
        assert await is_token_blacklisted(jti, redis_client) is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_nonexistent(self, redis_client):
        """Test checking blacklist status of non-existent token."""
        fake_jti = str(uuid4())

        assert await is_token_blacklisted(fake_jti, redis_client) is False


class TestSecurityUtilities:
    """Test miscellaneous security utilities."""

    def test_generate_secure_random_string(self):
        """Test secure random string generation."""
        # Default length
        random_str = generate_secure_random_string()
        assert isinstance(random_str, str)
        assert len(random_str) == 32

        # Custom length
        random_str_custom = generate_secure_random_string(64)
        assert len(random_str_custom) == 64

        # Different calls should produce different strings
        assert random_str != random_str_custom
        assert generate_secure_random_string() != generate_secure_random_string()

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "test_api_key_123"
        hashed = hash_api_key(api_key)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != api_key

    def test_verify_api_key(self):
        """Test API key verification."""
        api_key = "test_api_key_123"
        hashed = hash_api_key(api_key)

        assert verify_api_key(api_key, hashed) is True
        assert verify_api_key("wrong_key", hashed) is False

    def test_create_csrf_token(self):
        """Test CSRF token creation."""
        token = create_csrf_token()

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_csrf_token(self):
        """Test CSRF token verification."""
        token = create_csrf_token()

        # Should verify immediately
        assert verify_csrf_token(token) is True

        # Invalid token should fail
        assert verify_csrf_token("invalid_token") is False

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.txt", "file_with_spaces.txt"),
            ("file/with\\dangerous:chars.txt", "file_with_dangerous_chars.txt"),
            ("../../../etc/passwd", "etc_passwd"),
            ("file.exe", "file.exe"),
            ("", "untitled"),
            ("....", "untitled"),
        ]

        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected

    def test_is_safe_url(self):
        """Test URL safety checking."""
        safe_urls = [
            "https://example.com",
            "http://localhost:8000",
            "/relative/path",
            "/api/v1/users",
        ]

        unsafe_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "ftp://malicious.com",
            "//evil.com/redirect",
        ]

        for url in safe_urls:
            assert is_safe_url(url) is True

        for url in unsafe_urls:
            assert is_safe_url(url) is False

    def test_constant_time_compare(self):
        """Test constant-time string comparison."""
        # Same strings
        assert constant_time_compare("hello", "hello") is True
        assert constant_time_compare("", "") is True

        # Different strings
        assert constant_time_compare("hello", "world") is False
        assert constant_time_compare("hello", "hello!") is False
        assert constant_time_compare("", "hello") is False

    def test_constant_time_compare_timing_attack_resistance(self):
        """Test that comparison time doesn't leak information."""
        import time

        # This is a basic test - in practice, timing attacks are hard to test reliably
        base_string = "a" * 1000

        # Compare with completely different string
        start = time.perf_counter()
        constant_time_compare(base_string, "b" * 1000)
        time1 = time.perf_counter() - start

        # Compare with string that differs only at the end
        different_string = "a" * 999 + "b"
        start = time.perf_counter()
        constant_time_compare(base_string, different_string)
        time2 = time.perf_counter() - start

        # Times should be similar (within reasonable variance)
        # This is a weak test but better than nothing
        assert abs(time1 - time2) < 0.01  # 10ms variance allowed


class TestTokenEdgeCases:
    """Test edge cases and error conditions."""

    def test_verify_token_none_input(self):
        """Test token verification with None input."""
        assert verify_token(None) is None

    def test_verify_token_empty_string(self):
        """Test token verification with empty string."""
        assert verify_token("") is None

    def test_create_token_empty_data(self):
        """Test token creation with empty data."""
        token = create_access_token({})
        payload = verify_token(token)

        # Should still work but with minimal claims
        assert payload is not None
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_create_token_with_none_values(self):
        """Test token creation with None values in data."""
        data = {"sub": None, "email": "test@example.com"}
        token = create_access_token(data)
        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] is None
        assert payload["email"] == "test@example.com"

    def test_password_hash_edge_cases(self):
        """Test password hashing edge cases."""
        # Very long password
        long_password = "a" * 1000
        hashed = get_password_hash(long_password)
        assert verify_password(long_password, hashed) is True

        # Single character
        single_char = "a"
        hashed = get_password_hash(single_char)
        assert verify_password(single_char, hashed) is True

    def test_secure_random_string_edge_cases(self):
        """Test secure random string generation edge cases."""
        # Zero length should return empty string
        assert generate_secure_random_string(0) == ""

        # Negative length should return empty string
        assert generate_secure_random_string(-1) == ""

        # Very large length should work
        large_string = generate_secure_random_string(10000)
        assert len(large_string) == 10000
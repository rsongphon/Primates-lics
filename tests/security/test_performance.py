"""
Performance tests for the authentication system.
Tests for response times, throughput, and resource usage.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from httpx import AsyncClient
from fastapi import status

from app.core.security import create_access_token, get_password_hash, verify_password
from tests.conftest import create_test_user_data


class TestAuthenticationPerformance:
    """Test authentication endpoint performance."""

    @pytest.mark.asyncio
    async def test_login_response_time(self, async_client: AsyncClient, test_user):
        """Test login endpoint response time."""
        start_time = time.perf_counter()

        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        end_time = time.perf_counter()
        response_time = end_time - start_time

        assert response.status_code == status.HTTP_200_OK
        assert response_time < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_registration_response_time(self, async_client: AsyncClient, test_organization):
        """Test registration endpoint response time."""
        user_data = create_test_user_data()

        start_time = time.perf_counter()

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **user_data,
                "organization_id": str(test_organization.id)
            }
        )

        end_time = time.perf_counter()
        response_time = end_time - start_time

        assert response.status_code == status.HTTP_201_CREATED
        assert response_time < 2.0  # Registration can be slower due to password hashing

    @pytest.mark.asyncio
    async def test_profile_access_response_time(self, async_client: AsyncClient, auth_headers):
        """Test profile access response time."""
        start_time = time.perf_counter()

        response = await async_client.get(
            "/api/v1/auth/profile",
            headers=auth_headers
        )

        end_time = time.perf_counter()
        response_time = end_time - start_time

        assert response.status_code == status.HTTP_200_OK
        assert response_time < 0.5  # Should be very fast for authenticated requests

    @pytest.mark.asyncio
    async def test_token_refresh_response_time(self, async_client: AsyncClient, test_user):
        """Test token refresh response time."""
        # First login to get refresh token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        tokens = login_response.json()

        start_time = time.perf_counter()

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )

        end_time = time.perf_counter()
        response_time = end_time - start_time

        assert response.status_code == status.HTTP_200_OK
        assert response_time < 0.5  # Token refresh should be fast

    @pytest.mark.asyncio
    async def test_concurrent_login_performance(self, async_client: AsyncClient, test_user):
        """Test performance under concurrent login requests."""
        async def single_login():
            start_time = time.perf_counter()
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "testpassword123"
                }
            )
            end_time = time.perf_counter()
            return response.status_code, end_time - start_time

        # Run 10 concurrent login requests
        tasks = [single_login() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        status_codes = [result[0] for result in results]
        response_times = [result[1] for result in results]

        assert all(code == status.HTTP_200_OK for code in status_codes)

        # Average response time should still be reasonable
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 2.0

        # No response should take too long
        max_response_time = max(response_times)
        assert max_response_time < 5.0

    @pytest.mark.asyncio
    async def test_failed_login_performance(self, async_client: AsyncClient, test_user):
        """Test that failed logins don't take longer than successful ones."""
        # Successful login time
        start_time = time.perf_counter()
        success_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        success_time = time.perf_counter() - start_time

        # Failed login time
        start_time = time.perf_counter()
        fail_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )
        fail_time = time.perf_counter() - start_time

        assert success_response.status_code == status.HTTP_200_OK
        assert fail_response.status_code == status.HTTP_401_UNAUTHORIZED

        # Failed login should not be significantly faster (timing attack protection)
        time_ratio = max(success_time, fail_time) / min(success_time, fail_time)
        assert time_ratio < 3  # Allow some variance but not orders of magnitude


class TestPasswordHashingPerformance:
    """Test password hashing performance."""

    def test_password_hashing_speed(self):
        """Test password hashing speed."""
        password = "TestPassword123!"

        start_time = time.perf_counter()
        password_hash = get_password_hash(password)
        end_time = time.perf_counter()

        hashing_time = end_time - start_time

        # Should be reasonably fast but not too fast (security vs performance)
        assert 0.01 < hashing_time < 2.0  # Between 10ms and 2 seconds
        assert password_hash != password

    def test_password_verification_speed(self):
        """Test password verification speed."""
        password = "TestPassword123!"
        password_hash = get_password_hash(password)

        start_time = time.perf_counter()
        is_valid = verify_password(password, password_hash)
        end_time = time.perf_counter()

        verification_time = end_time - start_time

        assert is_valid is True
        assert verification_time < 1.0  # Should be faster than hashing

    def test_concurrent_password_operations(self):
        """Test performance under concurrent password operations."""
        password = "TestPassword123!"

        def hash_password():
            return get_password_hash(password)

        # Use ThreadPoolExecutor for CPU-bound operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.perf_counter()
            futures = [executor.submit(hash_password) for _ in range(5)]
            hashes = [future.result() for future in futures]
            end_time = time.perf_counter()

        total_time = end_time - start_time

        # All hashes should be different
        assert len(set(hashes)) == 5

        # Should complete within reasonable time
        assert total_time < 10.0  # 5 concurrent operations in under 10 seconds


class TestJWTPerformance:
    """Test JWT operations performance."""

    def test_token_generation_speed(self):
        """Test JWT token generation speed."""
        data = {"sub": "user123", "email": "test@example.com"}

        start_time = time.perf_counter()
        token = create_access_token(data)
        end_time = time.perf_counter()

        generation_time = end_time - start_time

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are fairly long
        assert generation_time < 0.1  # Should be very fast

    def test_token_validation_speed(self):
        """Test JWT token validation speed."""
        from app.core.security import verify_token

        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        start_time = time.perf_counter()
        payload = verify_token(token)
        end_time = time.perf_counter()

        validation_time = end_time - start_time

        assert payload is not None
        assert payload["sub"] == "user123"
        assert validation_time < 0.1  # Should be very fast

    def test_bulk_token_operations(self):
        """Test performance of bulk JWT operations."""
        data = {"sub": "user123", "email": "test@example.com"}

        # Generate many tokens
        start_time = time.perf_counter()
        tokens = [create_access_token(data) for _ in range(100)]
        generation_time = time.perf_counter() - start_time

        # Validate many tokens
        start_time = time.perf_counter()
        from app.core.security import verify_token
        valid_tokens = [verify_token(token) for token in tokens]
        validation_time = time.perf_counter() - start_time

        assert len(tokens) == 100
        assert len([t for t in valid_tokens if t is not None]) == 100

        # Should handle bulk operations efficiently
        assert generation_time < 1.0  # 100 tokens in under 1 second
        assert validation_time < 1.0  # 100 validations in under 1 second

    def test_token_size_efficiency(self):
        """Test JWT token size efficiency."""
        small_data = {"sub": "user123"}
        large_data = {
            "sub": "user123",
            "email": "test@example.com",
            "roles": ["admin", "user"],
            "permissions": ["read", "write", "delete"],
            "organization": "test_org"
        }

        small_token = create_access_token(small_data)
        large_token = create_access_token(large_data)

        # Tokens should be reasonably sized
        assert len(small_token) < 500  # Small payload = small token
        assert len(large_token) < 1000  # Even large payload should be reasonable

        # Size should scale reasonably with data
        size_ratio = len(large_token) / len(small_token)
        assert 1.0 < size_ratio < 3.0  # Larger but not excessively so


class TestDatabasePerformance:
    """Test database operation performance."""

    @pytest.mark.asyncio
    async def test_user_lookup_performance(self, async_client: AsyncClient, test_user, auth_headers):
        """Test user lookup performance."""
        # Multiple profile requests to test database performance
        response_times = []

        for i in range(10):
            start_time = time.perf_counter()
            response = await async_client.get(
                "/api/v1/auth/profile",
                headers=auth_headers
            )
            end_time = time.perf_counter()

            assert response.status_code == status.HTTP_200_OK
            response_times.append(end_time - start_time)

        # All requests should be fast
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)

        assert avg_time < 0.5
        assert max_time < 1.0

    @pytest.mark.asyncio
    async def test_role_permission_lookup_performance(self, async_client: AsyncClient, admin_auth_headers, test_user):
        """Test role and permission lookup performance."""
        start_time = time.perf_counter()

        response = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions",
            headers=admin_auth_headers
        )

        end_time = time.perf_counter()
        response_time = end_time - start_time

        assert response.status_code == status.HTTP_200_OK
        assert response_time < 1.0  # Complex queries should still be fast

    @pytest.mark.asyncio
    async def test_concurrent_database_access(self, async_client: AsyncClient, auth_headers):
        """Test performance under concurrent database access."""
        async def single_request():
            start_time = time.perf_counter()
            response = await async_client.get(
                "/api/v1/auth/profile",
                headers=auth_headers
            )
            end_time = time.perf_counter()
            return response.status_code, end_time - start_time

        # Run 20 concurrent requests
        tasks = [single_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        status_codes = [result[0] for result in results]
        response_times = [result[1] for result in results]

        # All should succeed
        assert all(code == status.HTTP_200_OK for code in status_codes)

        # Performance should not degrade significantly
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)

        assert avg_time < 1.0
        assert max_time < 3.0  # Even slowest should be reasonable


class TestMiddlewarePerformance:
    """Test middleware performance impact."""

    @pytest.mark.asyncio
    async def test_authentication_middleware_overhead(self, async_client: AsyncClient, auth_headers):
        """Test authentication middleware performance overhead."""
        # Test authenticated endpoint
        start_time = time.perf_counter()
        auth_response = await async_client.get(
            "/api/v1/auth/profile",
            headers=auth_headers
        )
        auth_time = time.perf_counter() - start_time

        # Test public endpoint (no auth middleware)
        start_time = time.perf_counter()
        public_response = await async_client.get("/api/v1/health")
        public_time = time.perf_counter() - start_time

        assert auth_response.status_code == status.HTTP_200_OK
        assert public_response.status_code == status.HTTP_200_OK

        # Auth middleware should not add excessive overhead
        overhead = auth_time - public_time
        assert overhead < 0.5  # Less than 500ms overhead

    @pytest.mark.asyncio
    async def test_rate_limiting_middleware_performance(self, async_client: AsyncClient, redis_client):
        """Test rate limiting middleware performance impact."""
        with patch('app.middleware.rate_limiting.get_redis', return_value=redis_client):
            # Multiple requests to test rate limiting overhead
            response_times = []

            for i in range(10):
                start_time = time.perf_counter()
                response = await async_client.get("/api/v1/health")
                end_time = time.perf_counter()

                response_times.append(end_time - start_time)
                assert response.status_code == status.HTTP_200_OK

            # Rate limiting should not add significant overhead
            avg_time = sum(response_times) / len(response_times)
            assert avg_time < 0.5

    @pytest.mark.asyncio
    async def test_security_headers_middleware_performance(self, async_client: AsyncClient):
        """Test security headers middleware performance impact."""
        response_times = []

        for i in range(10):
            start_time = time.perf_counter()
            response = await async_client.get("/api/v1/health")
            end_time = time.perf_counter()

            response_times.append(end_time - start_time)
            assert response.status_code == status.HTTP_200_OK
            # Verify headers are present
            assert "X-Content-Type-Options" in response.headers

        # Security headers should add minimal overhead
        avg_time = sum(response_times) / len(response_times)
        assert avg_time < 0.3


class TestMemoryPerformance:
    """Test memory usage performance."""

    @pytest.mark.asyncio
    async def test_memory_usage_during_bulk_operations(self, async_client: AsyncClient, test_organization):
        """Test memory usage during bulk operations."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform many registration operations
        tasks = []
        for i in range(50):
            user_data = create_test_user_data(
                email=f"user{i}@example.com",
                username=f"user{i}"
            )
            task = async_client.post(
                "/api/v1/auth/register",
                json={
                    **user_data,
                    "organization_id": str(test_organization.id)
                }
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for 50 operations)
        assert memory_increase < 100 * 1024 * 1024

        # Most operations should succeed
        successful = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code in [200, 201])
        assert successful > 40  # At least 80% success rate

    def test_token_memory_efficiency(self):
        """Test memory efficiency of token operations."""
        import sys

        # Create many tokens and measure memory
        tokens = []
        for i in range(1000):
            data = {"sub": f"user{i}", "email": f"user{i}@example.com"}
            token = create_access_token(data)
            tokens.append(token)

        # Calculate average token size
        total_size = sum(sys.getsizeof(token) for token in tokens)
        avg_size = total_size / len(tokens)

        # Tokens should be reasonably sized
        assert avg_size < 1000  # Less than 1KB per token on average

        # Clear tokens to free memory
        tokens.clear()


class TestCachePerformance:
    """Test caching performance (if implemented)."""

    @pytest.mark.asyncio
    async def test_permission_cache_performance(self, async_client: AsyncClient, admin_auth_headers, test_user):
        """Test permission lookup caching performance."""
        # First request (cache miss)
        start_time = time.perf_counter()
        response1 = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions",
            headers=admin_auth_headers
        )
        first_time = time.perf_counter() - start_time

        # Second request (should be cached)
        start_time = time.perf_counter()
        response2 = await async_client.get(
            f"/api/v1/rbac/users/{test_user.id}/permissions",
            headers=admin_auth_headers
        )
        second_time = time.perf_counter() - start_time

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # Results should be the same
        assert response1.json() == response2.json()

        # Second request should be faster (or at least not slower)
        assert second_time <= first_time * 1.5  # Allow some variance

    @pytest.mark.asyncio
    async def test_session_cache_performance(self, async_client: AsyncClient, auth_headers, redis_client):
        """Test session caching performance."""
        with patch('app.core.database.get_redis', return_value=redis_client):
            # Multiple profile requests should use cached session data
            response_times = []

            for i in range(5):
                start_time = time.perf_counter()
                response = await async_client.get(
                    "/api/v1/auth/profile",
                    headers=auth_headers
                )
                end_time = time.perf_counter()

                assert response.status_code == status.HTTP_200_OK
                response_times.append(end_time - start_time)

            # Later requests should not be significantly slower (cache working)
            first_time = response_times[0]
            later_times = response_times[1:]

            avg_later_time = sum(later_times) / len(later_times)
            assert avg_later_time <= first_time * 1.5


class TestLoadTestingSimulation:
    """Simulate load testing scenarios."""

    @pytest.mark.asyncio
    async def test_login_load_simulation(self, async_client: AsyncClient, test_user):
        """Simulate load on login endpoint."""
        # Simulate 50 login attempts over 10 seconds
        start_time = time.perf_counter()

        async def login_attempt():
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "testpassword123"
                }
            )
            return response.status_code == status.HTTP_200_OK

        # Batch requests to simulate load
        batch_size = 10
        batches = 5
        all_successful = True

        for batch in range(batches):
            tasks = [login_attempt() for _ in range(batch_size)]
            results = await asyncio.gather(*tasks)

            batch_success_rate = sum(results) / len(results)
            if batch_success_rate < 0.8:  # At least 80% success rate
                all_successful = False
                break

            # Small delay between batches
            await asyncio.sleep(0.1)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        assert all_successful
        assert total_time < 15  # Should complete within reasonable time

    @pytest.mark.asyncio
    async def test_mixed_workload_simulation(self, async_client: AsyncClient, test_user, auth_headers):
        """Simulate mixed workload with different endpoints."""
        async def login_operation():
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "testpassword123"
                }
            )
            return response.status_code == status.HTTP_200_OK

        async def profile_operation():
            response = await async_client.get(
                "/api/v1/auth/profile",
                headers=auth_headers
            )
            return response.status_code == status.HTTP_200_OK

        async def health_operation():
            response = await async_client.get("/api/v1/health")
            return response.status_code == status.HTTP_200_OK

        # Mix of operations
        tasks = []
        for i in range(30):
            if i % 3 == 0:
                tasks.append(login_operation())
            elif i % 3 == 1:
                tasks.append(profile_operation())
            else:
                tasks.append(health_operation())

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        success_rate = sum(results) / len(results)

        assert success_rate >= 0.9  # At least 90% success rate
        assert total_time < 10  # Should complete within 10 seconds
        assert total_time / len(tasks) < 0.5  # Average less than 500ms per operation
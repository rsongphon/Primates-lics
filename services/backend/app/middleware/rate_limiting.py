"""
Rate Limiting Middleware

Implements rate limiting using Redis-backed sliding window algorithm
with support for per-user, per-IP, and per-endpoint limits.
"""

import time
import json
from typing import Dict, Optional, Tuple
from urllib.parse import unquote

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting Middleware

    Implements sliding window rate limiting with Redis backend.
    Supports different limits for different user types and endpoints.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection for rate limiting."""
        try:
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                logger.info("Rate limiting Redis client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis for rate limiting: {e}")
            self.redis_client = None

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Apply rate limiting to incoming requests.
        """
        # Skip rate limiting if Redis is not available
        if not self.redis_client:
            return await call_next(request)

        # Skip rate limiting for health checks and docs
        if self._is_exempt_route(request.url.path):
            return await call_next(request)

        try:
            # Get rate limit configuration for this request
            limit_config = self._get_rate_limit_config(request)

            if not limit_config:
                # No rate limiting configured for this route
                return await call_next(request)

            # Check rate limit
            allowed, limit_info = await self._check_rate_limit(request, limit_config)

            if not allowed:
                return self._create_rate_limit_response(request, limit_info)

            # Process request
            response = await call_next(request)

            # Add rate limiting headers
            self._add_rate_limit_headers(response, limit_info)

            return response

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting if there's an error
            return await call_next(request)

    def _is_exempt_route(self, path: str) -> bool:
        """Check if route is exempt from rate limiting."""
        exempt_routes = {
            "/health",
            "/ready",
            "/live",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        return path in exempt_routes or path.startswith("/docs") or path.startswith("/redoc")

    def _get_rate_limit_config(self, request: Request) -> Optional[Dict]:
        """
        Get rate limit configuration for the request.

        Returns configuration with limits per time window.
        """
        path = unquote(request.url.path)
        method = request.method
        user = getattr(request.state, "user", None)

        # Different limits based on user type and endpoint
        if user:
            if user.is_superuser:
                # Super admin gets higher limits
                return {
                    "requests_per_minute": 1000,
                    "requests_per_hour": 10000,
                    "key_prefix": f"rate_limit:user:{user.id}"
                }
            elif hasattr(user, "role") and user.role and "premium" in user.role.name.lower():
                # Premium users get higher limits
                return {
                    "requests_per_minute": 300,
                    "requests_per_hour": 3000,
                    "key_prefix": f"rate_limit:user:{user.id}"
                }
            else:
                # Regular authenticated users
                return {
                    "requests_per_minute": 100,
                    "requests_per_hour": 1000,
                    "key_prefix": f"rate_limit:user:{user.id}"
                }
        else:
            # Anonymous users - rate limit by IP
            client_ip = self._get_client_ip(request)

            # Different limits for different endpoints
            if path.startswith("/api/v1/auth"):
                # Stricter limits for auth endpoints
                return {
                    "requests_per_minute": 20,
                    "requests_per_hour": 100,
                    "key_prefix": f"rate_limit:ip:{client_ip}:auth"
                }
            elif method == "POST":
                # Stricter limits for POST requests
                return {
                    "requests_per_minute": 30,
                    "requests_per_hour": 200,
                    "key_prefix": f"rate_limit:ip:{client_ip}:post"
                }
            else:
                # General limits for anonymous users
                return {
                    "requests_per_minute": 60,
                    "requests_per_hour": 500,
                    "key_prefix": f"rate_limit:ip:{client_ip}"
                }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    async def _check_rate_limit(
        self,
        request: Request,
        config: Dict
    ) -> Tuple[bool, Dict]:
        """
        Check if request is within rate limits using sliding window algorithm.

        Returns:
            Tuple of (allowed: bool, limit_info: dict)
        """
        current_time = int(time.time())

        # Keys for different time windows
        minute_key = f"{config['key_prefix']}:minute:{current_time // 60}"
        hour_key = f"{config['key_prefix']}:hour:{current_time // 3600}"

        try:
            # Use Redis pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                # Check current counts
                pipe.get(minute_key)
                pipe.get(hour_key)
                results = await pipe.execute()

                minute_count = int(results[0] or 0)
                hour_count = int(results[1] or 0)

                # Check limits
                minute_limit = config["requests_per_minute"]
                hour_limit = config["requests_per_hour"]

                if minute_count >= minute_limit:
                    return False, {
                        "limit": minute_limit,
                        "remaining": 0,
                        "reset_time": (current_time // 60 + 1) * 60,
                        "window": "minute"
                    }

                if hour_count >= hour_limit:
                    return False, {
                        "limit": hour_limit,
                        "remaining": 0,
                        "reset_time": (current_time // 3600 + 1) * 3600,
                        "window": "hour"
                    }

                # Increment counters
                async with self.redis_client.pipeline() as pipe:
                    pipe.incr(minute_key)
                    pipe.expire(minute_key, 120)  # 2 minutes TTL
                    pipe.incr(hour_key)
                    pipe.expire(hour_key, 7200)  # 2 hours TTL
                    await pipe.execute()

                # Calculate remaining requests (use more restrictive limit)
                minute_remaining = minute_limit - (minute_count + 1)
                hour_remaining = hour_limit - (hour_count + 1)
                remaining = min(minute_remaining, hour_remaining)

                return True, {
                    "limit": min(minute_limit, hour_limit),
                    "remaining": max(0, remaining),
                    "reset_time": (current_time // 60 + 1) * 60,
                    "window": "minute" if minute_remaining < hour_remaining else "hour"
                }

        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Allow request if Redis fails
            return True, {
                "limit": config["requests_per_minute"],
                "remaining": config["requests_per_minute"],
                "reset_time": current_time + 60,
                "window": "minute"
            }

    def _create_rate_limit_response(self, request: Request, limit_info: Dict) -> JSONResponse:
        """Create rate limit exceeded response."""
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        retry_after = limit_info["reset_time"] - int(time.time())

        logger.warning(
            f"Rate limit exceeded",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": self._get_client_ip(request),
                "limit": limit_info["limit"],
                "window": limit_info["window"],
                "retry_after": retry_after,
                "correlation_id": correlation_id
            }
        )

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    "details": {
                        "limit": limit_info["limit"],
                        "window": limit_info["window"],
                        "retry_after": retry_after
                    },
                    "trace_id": correlation_id
                }
            },
            headers={
                "X-Correlation-ID": correlation_id,
                "X-RateLimit-Limit": str(limit_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(limit_info["reset_time"]),
                "Retry-After": str(retry_after)
            }
        )

    def _add_rate_limit_headers(self, response: Response, limit_info: Dict):
        """Add rate limiting headers to response."""
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset_time"])
"""
LICS Backend Main Application

FastAPI application entry point with middleware, CORS, routing,
and lifecycle management. Follows Documentation.md architecture patterns.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import (
    get_logger,
    correlation_context,
    extract_request_info,
    setup_logging,
    configure_uvicorn_logging
)
from app.middleware.auth import AuthenticationMiddleware
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.security import SecurityHeadersMiddleware

# Initialize logging
setup_logging()
configure_uvicorn_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting LICS Backend...")

    try:
        # Initialize database connection
        await init_db()
        logger.info("Database initialized successfully")

        # TODO: Initialize other services (Redis, MQTT, etc.)
        # await init_redis()
        # await init_mqtt()

        logger.info("LICS Backend startup completed successfully")

    except Exception as e:
        logger.error(f"Failed to start LICS Backend: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down LICS Backend...")

    try:
        # Close database connections
        await close_db()
        logger.info("Database connections closed")

        # TODO: Close other service connections
        # await close_redis()
        # await close_mqtt()

        logger.info("LICS Backend shutdown completed successfully")

    except Exception as e:
        logger.error(f"Error during LICS Backend shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Lab Instrument Control System (LICS) Backend API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
    # OpenAPI configuration
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and monitoring endpoints"
        },
        {
            "name": "authentication",
            "description": "User authentication and authorization"
        },
        {
            "name": "users",
            "description": "User management operations"
        },
        {
            "name": "organizations",
            "description": "Organization management operations"
        },
        {
            "name": "devices",
            "description": "Device management and control operations"
        },
        {
            "name": "experiments",
            "description": "Experiment lifecycle management"
        },
        {
            "name": "tasks",
            "description": "Task definition and execution"
        },
        {
            "name": "streaming",
            "description": "Video streaming and media operations"
        },
        {
            "name": "analytics",
            "description": "Data analytics and reporting"
        }
    ]
)

# ===== MIDDLEWARE CONFIGURATION =====
# Note: Middleware is applied in reverse order (last added = first executed)

# Security headers middleware (applied first)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware
app.add_middleware(RateLimitingMiddleware)

# Authentication middleware
app.add_middleware(AuthenticationMiddleware)

# CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
    )

# Trusted host middleware
if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# Request/Response logging middleware
@app.middleware("http")
async def request_response_middleware(request: Request, call_next):
    """
    Middleware for request/response logging and correlation tracking.
    """
    # Generate correlation ID
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    # Extract request information
    request_info = extract_request_info(request)

    # Start timer
    start_time = time.time()

    # Process request with correlation context
    with correlation_context(correlation_id, request_info):
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                f"Unhandled exception in request processing: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "request_info": request_info,
                    "exception_type": type(e).__name__
                }
            )
            # Return a generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "trace_id": correlation_id
                    }
                },
                headers={"X-Correlation-ID": correlation_id}
            )

    # Calculate response time
    process_time = time.time() - start_time

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    # Log request/response (only for non-health endpoints to reduce noise)
    if not request.url.path.startswith("/health"):
        logger.info(
            f"Request processed: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "response_time_ms": round(process_time * 1000, 2),
                "user_agent": request.headers.get("user-agent", ""),
                "remote_addr": request.client.host if request.client else ""
            }
        )

    return response


# Performance monitoring middleware
@app.middleware("http")
async def performance_monitoring_middleware(request: Request, call_next):
    """
    Middleware for performance monitoring and metrics collection.
    """
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    # Add performance headers
    response.headers["X-Process-Time"] = str(round(process_time, 4))

    # Log slow requests (> 1 second)
    if process_time > 1.0:
        logger.warning(
            f"Slow request detected: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "url": str(request.url),
                "response_time_ms": round(process_time * 1000, 2),
                "status_code": response.status_code
            }
        )

    return response


# ===== EXCEPTION HANDLERS =====

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Custom HTTP exception handler.
    """
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "correlation_id": correlation_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "url": str(request.url),
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "trace_id": correlation_id
            }
        },
        headers={"X-Correlation-ID": correlation_id}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom validation exception handler.
    """
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

    # Format validation errors
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation error: {len(errors)} validation errors",
        extra={
            "correlation_id": correlation_id,
            "validation_errors": errors,
            "url": str(request.url),
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"validation_errors": errors},
                "trace_id": correlation_id
            }
        },
        headers={"X-Correlation-ID": correlation_id}
    )


# ===== ROOT ENDPOINTS =====

@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint providing basic API information.
    """
    return {
        "message": "LICS Backend API",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_url": "/health"
    }


@app.get("/info", tags=["root"])
async def info():
    """
    API information endpoint.
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "features": {
            "websocket_enabled": settings.FEATURE_WEBSOCKET_ENABLED,
            "celery_enabled": settings.FEATURE_CELERY_ENABLED,
            "mqtt_enabled": settings.FEATURE_MQTT_ENABLED,
            "video_streaming_enabled": settings.FEATURE_VIDEO_STREAMING_ENABLED,
            "ml_enabled": settings.FEATURE_ML_ENABLED
        }
    }


# ===== API ROUTES =====

# Include API v1 routes
app.include_router(
    api_router,
    prefix=settings.API_V1_STR,
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
        503: {"description": "Service Unavailable"}
    }
)


# ===== HEALTH CHECK ENDPOINTS (for load balancers) =====

@app.get("/health", tags=["health"])
async def health_check():
    """
    Simple health check endpoint for load balancers.
    """
    return {
        "status": "healthy",
        "service": "lics-backend",
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }


@app.get("/ready", tags=["health"])
async def readiness_check():
    """
    Readiness probe for Kubernetes.
    """
    try:
        # Check if database is accessible
        from app.core.database import db_manager
        health_result = await db_manager.health_check()

        if health_result.get("status") == "healthy":
            return {"status": "ready"}
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "reason": "database_unhealthy"}
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": str(e)}
        )


@app.get("/live", tags=["health"])
async def liveness_check():
    """
    Liveness probe for Kubernetes.
    """
    return {"status": "alive"}


# ===== APPLICATION STARTUP MESSAGE =====

if __name__ == "__main__":
    logger.info(f"LICS Backend {settings.APP_VERSION} starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
else:
    logger.info(f"LICS Backend {settings.APP_VERSION} initialized")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
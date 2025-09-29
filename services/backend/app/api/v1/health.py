"""
LICS Health Check Endpoints
Comprehensive health monitoring for all system components
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import asyncpg
import redis.asyncio as redis
import paho.mqtt.client as mqtt
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from minio import Minio
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

router = APIRouter()


class HealthChecker:
    """Comprehensive health checker for all LICS services."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.check_cache = {}
        self.cache_ttl = 60  # Cache results for 60 seconds

    async def check_postgresql(self) -> Dict[str, Any]:
        """Check PostgreSQL database health."""
        result = {
            "name": "PostgreSQL",
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.time()
        try:
            # Connection string from environment
            conn = await asyncpg.connect(
                "postgresql://lics:lics123@postgres:5432/lics"
            )

            # Basic connectivity test
            version = await conn.fetchval("SELECT version()")

            # TimescaleDB extension test
            timescale = await conn.fetchval(
                "SELECT extname FROM pg_extension WHERE extname = 'timescaledb'"
            )

            # Connection count
            connections = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity"
            )

            # Database size
            db_size = await conn.fetchval(
                "SELECT pg_database_size('lics')"
            )

            await conn.close()

            result.update({
                "status": "healthy",
                "details": {
                    "version": version,
                    "timescaledb_enabled": bool(timescale),
                    "active_connections": connections,
                    "database_size_bytes": db_size
                }
            })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "error": str(e)
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis cache health."""
        result = {
            "name": "Redis",
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.time()
        try:
            r = redis.Redis(host='redis', port=6379, decode_responses=True)

            # Basic connectivity test
            pong = await r.ping()

            # Get Redis info
            info = await r.info()

            # Test basic operations
            await r.set("health_check", "ok", ex=60)
            health_value = await r.get("health_check")

            await r.close()

            result.update({
                "status": "healthy" if pong and health_value == "ok" else "unhealthy",
                "details": {
                    "version": info.get("redis_version"),
                    "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "uptime_seconds": info.get("uptime_in_seconds")
                }
            })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "error": str(e)
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    async def check_influxdb(self) -> Dict[str, Any]:
        """Check InfluxDB health."""
        result = {
            "name": "InfluxDB",
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.time()
        try:
            async with InfluxDBClientAsync(
                url="http://influxdb:8086",
                token=os.getenv("INFLUXDB_ADMIN_TOKEN", "lics-admin-token-change-in-production"),
                org="lics"
            ) as client:
                # Health check
                health = await client.health()

                # Get bucket info
                buckets_api = client.buckets_api()
                buckets = await buckets_api.find_buckets(org="lics")

                result.update({
                    "status": "healthy" if health.status == "pass" else "unhealthy",
                    "details": {
                        "health_status": health.status,
                        "version": health.version if hasattr(health, 'version') else 'unknown',
                        "buckets_count": len(buckets.buckets) if buckets else 0,
                        "buckets": [b.name for b in buckets.buckets] if buckets else []
                    }
                })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "error": str(e)
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    def check_mqtt(self) -> Dict[str, Any]:
        """Check MQTT broker health."""
        result = {
            "name": "MQTT",
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.time()
        try:
            client = mqtt.Client()

            # Connect to MQTT broker
            result_code = client.connect("mqtt", 1883, 60)

            if result_code == 0:
                # Test publish/subscribe
                client.publish("health/check", "ping", qos=1)
                client.disconnect()

                result.update({
                    "status": "healthy",
                    "details": {
                        "broker": "mqtt:1883",
                        "connection_result": "success"
                    }
                })
            else:
                result.update({
                    "status": "unhealthy",
                    "details": {
                        "connection_result": f"failed_with_code_{result_code}"
                    }
                })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "error": str(e)
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    def check_minio(self) -> Dict[str, Any]:
        """Check MinIO object storage health."""
        result = {
            "name": "MinIO",
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.time()
        try:
            client = Minio(
                "minio:9000",
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                secure=False
            )

            # List buckets
            buckets = client.list_buckets()

            # Test bucket operations
            test_bucket = "health-check"
            if not client.bucket_exists(test_bucket):
                client.make_bucket(test_bucket)

            # Test object operations
            client.put_object(
                test_bucket,
                "health-check.txt",
                io.BytesIO(b"health check"),
                length=12
            )

            # Clean up
            client.remove_object(test_bucket, "health-check.txt")
            client.remove_bucket(test_bucket)

            result.update({
                "status": "healthy",
                "details": {
                    "buckets_count": len(buckets),
                    "buckets": [bucket.name for bucket in buckets]
                }
            })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "error": str(e)
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    async def check_monitoring_services(self) -> Dict[str, Any]:
        """Check monitoring services health."""
        services = {
            "prometheus": "http://prometheus:9090/-/healthy",
            "grafana": "http://grafana:3000/api/health",
            "loki": "http://loki:3100/ready",
            "alertmanager": "http://alertmanager:9093/-/healthy",
            "jaeger": "http://jaeger:16686/api/services"
        }

        result = {
            "name": "Monitoring Services",
            "status": "unknown",
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        healthy_count = 0
        total_count = len(services)

        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            for service_name, url in services.items():
                try:
                    async with session.get(url) as response:
                        if response.status in [200, 204]:
                            result["details"][service_name] = "healthy"
                            healthy_count += 1
                        else:
                            result["details"][service_name] = f"unhealthy_status_{response.status}"
                except Exception as e:
                    result["details"][service_name] = f"error: {str(e)}"

        result["status"] = "healthy" if healthy_count == total_count else "degraded" if healthy_count > 0 else "unhealthy"
        result["details"]["healthy_services"] = f"{healthy_count}/{total_count}"

        return result

    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        uptime = datetime.now(timezone.utc) - self.start_time

        return {
            "service_name": "LICS Backend",
            "version": "1.0.0",
            "environment": "production",
            "uptime_seconds": int(uptime.total_seconds()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "build_info": {
                "commit_hash": "unknown",
                "build_date": "unknown"
            }
        }


# Initialize health checker
health_checker = HealthChecker()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "LICS Backend"
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/comprehensive")
async def comprehensive_health_check(
    include_details: bool = Query(True, description="Include detailed health information"),
    services: Optional[str] = Query(None, description="Comma-separated list of services to check")
):
    """Comprehensive health check for all services."""

    start_time = time.time()

    # System information
    system_info = await health_checker.get_system_info()

    # Services to check
    service_checks = []
    if services:
        service_list = [s.strip() for s in services.split(",")]
    else:
        service_list = ["postgresql", "redis", "influxdb", "mqtt", "minio", "monitoring"]

    # Run health checks concurrently
    tasks = []
    if "postgresql" in service_list:
        tasks.append(health_checker.check_postgresql())
    if "redis" in service_list:
        tasks.append(health_checker.check_redis())
    if "influxdb" in service_list:
        tasks.append(health_checker.check_influxdb())
    if "mqtt" in service_list:
        # MQTT is not async, so wrap it
        tasks.append(asyncio.get_event_loop().run_in_executor(None, health_checker.check_mqtt))
    if "minio" in service_list:
        # MinIO is not async, so wrap it
        tasks.append(asyncio.get_event_loop().run_in_executor(None, health_checker.check_minio))
    if "monitoring" in service_list:
        tasks.append(health_checker.check_monitoring_services())

    service_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    services_status = []
    overall_status = "healthy"

    for result in service_results:
        if isinstance(result, Exception):
            services_status.append({
                "name": "unknown",
                "status": "error",
                "error": str(result)
            })
            overall_status = "unhealthy"
        else:
            services_status.append(result)
            if result["status"] != "healthy":
                overall_status = "degraded" if overall_status == "healthy" else "unhealthy"

    response = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_time_ms": int((time.time() - start_time) * 1000),
        "system": system_info,
        "services": services_status if include_details else None,
        "summary": {
            "total_services": len(services_status),
            "healthy_services": len([s for s in services_status if s.get("status") == "healthy"]),
            "unhealthy_services": len([s for s in services_status if s.get("status") != "healthy"])
        }
    }

    # Return appropriate HTTP status code
    status_code = 200 if overall_status == "healthy" else 503
    return JSONResponse(content=response, status_code=status_code)


@router.get("/health/services/{service_name}")
async def service_health_check(service_name: str):
    """Check health of a specific service."""

    service_checks = {
        "postgresql": health_checker.check_postgresql,
        "redis": health_checker.check_redis,
        "influxdb": health_checker.check_influxdb,
        "mqtt": lambda: asyncio.get_event_loop().run_in_executor(None, health_checker.check_mqtt),
        "minio": lambda: asyncio.get_event_loop().run_in_executor(None, health_checker.check_minio),
        "monitoring": health_checker.check_monitoring_services
    }

    if service_name not in service_checks:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    result = await service_checks[service_name]()

    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(content=result, status_code=status_code)


@router.get("/health/metrics")
async def health_metrics():
    """Health metrics in Prometheus format."""

    # This would be implemented to return Prometheus metrics
    # For now, return a simple response
    return {
        "message": "Health metrics endpoint - implement Prometheus format",
        "endpoint": "/health/metrics",
        "format": "prometheus"
    }
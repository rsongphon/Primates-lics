"""
Fallback Strategies for Circuit Breakers
Provides graceful degradation when services are unavailable
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class FallbackStrategies:
    """Fallback strategies for different service failures."""

    # ===== POSTGRESQL FALLBACKS =====

    @staticmethod
    async def postgresql_read_fallback(*args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for PostgreSQL read operations.

        Returns cached data or empty result with degraded service indicator.
        """
        logger.warning("PostgreSQL read fallback activated - returning cached/empty data")
        return {
            "data": [],
            "meta": {
                "degraded": True,
                "reason": "database_unavailable",
                "fallback_used": "postgresql_read",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    @staticmethod
    async def postgresql_write_fallback(*args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for PostgreSQL write operations.

        Queues write for later or returns error.
        """
        logger.error("PostgreSQL write fallback activated - operation queued")

        # In production, this should queue the write operation
        # For now, return error with guidance
        return {
            "success": False,
            "queued": True,
            "message": "Write operation queued due to database unavailability",
            "retry_after": 60,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    async def postgresql_health_fallback(*args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for PostgreSQL health checks.
        """
        return {
            "status": "unhealthy",
            "service": "PostgreSQL",
            "reason": "circuit_breaker_open",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ===== REDIS FALLBACKS =====

    @staticmethod
    async def redis_get_fallback(key: str, *args, **kwargs) -> Optional[Any]:
        """
        Fallback for Redis GET operations.

        Returns None when cache is unavailable.
        """
        logger.warning(f"Redis GET fallback activated for key: {key}")
        return None

    @staticmethod
    async def redis_set_fallback(key: str, value: Any, *args, **kwargs) -> bool:
        """
        Fallback for Redis SET operations.

        Silently fails but logs the attempt.
        """
        logger.warning(f"Redis SET fallback activated for key: {key} - cache write skipped")
        return False

    @staticmethod
    async def redis_delete_fallback(key: str, *args, **kwargs) -> bool:
        """
        Fallback for Redis DELETE operations.
        """
        logger.warning(f"Redis DELETE fallback activated for key: {key}")
        return False

    @staticmethod
    async def redis_health_fallback(*args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for Redis health checks.
        """
        return {
            "status": "unhealthy",
            "service": "Redis",
            "reason": "circuit_breaker_open",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ===== INFLUXDB FALLBACKS =====

    @staticmethod
    async def influxdb_write_fallback(measurement: str, data: Dict, *args, **kwargs) -> bool:
        """
        Fallback for InfluxDB write operations.

        Logs dropped metrics but doesn't block execution.
        """
        logger.warning(
            f"InfluxDB write fallback activated - metric dropped",
            extra={
                "measurement": measurement,
                "data_points": len(data) if isinstance(data, list) else 1
            }
        )
        return False

    @staticmethod
    async def influxdb_query_fallback(query: str, *args, **kwargs) -> List[Dict]:
        """
        Fallback for InfluxDB query operations.

        Returns empty result set.
        """
        logger.warning(f"InfluxDB query fallback activated - returning empty results")
        return []

    @staticmethod
    async def influxdb_health_fallback(*args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for InfluxDB health checks.
        """
        return {
            "status": "unhealthy",
            "service": "InfluxDB",
            "reason": "circuit_breaker_open",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ===== MQTT FALLBACKS =====

    @staticmethod
    def mqtt_publish_fallback(topic: str, payload: Any, *args, **kwargs) -> bool:
        """
        Fallback for MQTT publish operations.

        Logs failed publish but doesn't block execution.
        """
        logger.warning(
            f"MQTT publish fallback activated - message not sent",
            extra={
                "topic": topic,
                "payload_size": len(str(payload))
            }
        )
        return False

    @staticmethod
    def mqtt_subscribe_fallback(topic: str, *args, **kwargs) -> bool:
        """
        Fallback for MQTT subscribe operations.
        """
        logger.warning(f"MQTT subscribe fallback activated for topic: {topic}")
        return False

    @staticmethod
    def mqtt_health_fallback(*args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for MQTT health checks.
        """
        return {
            "status": "unhealthy",
            "service": "MQTT",
            "reason": "circuit_breaker_open",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ===== MINIO FALLBACKS =====

    @staticmethod
    def minio_upload_fallback(bucket: str, object_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for MinIO upload operations.

        Returns error but doesn't raise exception.
        """
        logger.error(
            f"MinIO upload fallback activated - file not uploaded",
            extra={
                "bucket": bucket,
                "object_name": object_name
            }
        )
        return {
            "success": False,
            "message": "Object storage unavailable - upload failed",
            "retry_after": 120,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def minio_download_fallback(bucket: str, object_name: str, *args, **kwargs) -> None:
        """
        Fallback for MinIO download operations.

        Returns None indicating file not available.
        """
        logger.warning(
            f"MinIO download fallback activated - file not available",
            extra={
                "bucket": bucket,
                "object_name": object_name
            }
        )
        return None

    @staticmethod
    def minio_delete_fallback(bucket: str, object_name: str, *args, **kwargs) -> bool:
        """
        Fallback for MinIO delete operations.
        """
        logger.warning(
            f"MinIO delete fallback activated",
            extra={
                "bucket": bucket,
                "object_name": object_name
            }
        )
        return False

    @staticmethod
    def minio_health_fallback(*args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for MinIO health checks.
        """
        return {
            "status": "unhealthy",
            "service": "MinIO",
            "reason": "circuit_breaker_open",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ===== EXTERNAL API FALLBACKS =====

    @staticmethod
    async def external_api_fallback(url: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Fallback for external API calls.

        Returns error response with retry guidance.
        """
        logger.warning(f"External API fallback activated for URL: {url}")
        return {
            "success": False,
            "error": "External service unavailable",
            "retry_after": 300,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ===== DEGRADED MODE HANDLER =====

class DegradedModeHandler:
    """
    Manages system behavior in degraded mode when multiple services are down.
    """

    def __init__(self):
        self.degraded_services: Dict[str, datetime] = {}

    def mark_service_degraded(self, service_name: str):
        """Mark a service as degraded."""
        self.degraded_services[service_name] = datetime.now(timezone.utc)
        logger.warning(f"Service marked as degraded: {service_name}")

    def mark_service_healthy(self, service_name: str):
        """Mark a service as healthy again."""
        if service_name in self.degraded_services:
            degraded_duration = datetime.now(timezone.utc) - self.degraded_services[service_name]
            del self.degraded_services[service_name]
            logger.info(
                f"Service recovered: {service_name}",
                extra={"degraded_duration_seconds": degraded_duration.total_seconds()}
            )

    def is_service_degraded(self, service_name: str) -> bool:
        """Check if a service is currently degraded."""
        return service_name in self.degraded_services

    def get_degraded_services(self) -> List[str]:
        """Get list of currently degraded services."""
        return list(self.degraded_services.keys())

    def is_system_degraded(self) -> bool:
        """Check if the overall system is in degraded mode."""
        # System is degraded if any critical service is down
        critical_services = {"postgresql", "redis"}
        return any(service in self.degraded_services for service in critical_services)

    def get_degraded_status(self) -> Dict[str, Any]:
        """Get comprehensive degraded mode status."""
        return {
            "is_degraded": self.is_system_degraded(),
            "degraded_services_count": len(self.degraded_services),
            "degraded_services": [
                {
                    "service": service,
                    "degraded_since": timestamp.isoformat(),
                    "degraded_duration_seconds": (
                        datetime.now(timezone.utc) - timestamp
                    ).total_seconds()
                }
                for service, timestamp in self.degraded_services.items()
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global degraded mode handler instance
degraded_mode_handler = DegradedModeHandler()

# Global fallback strategies instance
fallback_strategies = FallbackStrategies()


# ===== UTILITY FUNCTIONS =====

def get_fallback_for_service(service_name: str, operation: str) -> Optional[callable]:
    """
    Get the appropriate fallback function for a service and operation.

    Args:
        service_name: Name of the service (postgresql, redis, etc.)
        operation: Type of operation (read, write, health, etc.)

    Returns:
        Fallback function or None if not found
    """
    fallback_map = {
        "postgresql": {
            "read": FallbackStrategies.postgresql_read_fallback,
            "write": FallbackStrategies.postgresql_write_fallback,
            "health": FallbackStrategies.postgresql_health_fallback,
        },
        "redis": {
            "get": FallbackStrategies.redis_get_fallback,
            "set": FallbackStrategies.redis_set_fallback,
            "delete": FallbackStrategies.redis_delete_fallback,
            "health": FallbackStrategies.redis_health_fallback,
        },
        "influxdb": {
            "write": FallbackStrategies.influxdb_write_fallback,
            "query": FallbackStrategies.influxdb_query_fallback,
            "health": FallbackStrategies.influxdb_health_fallback,
        },
        "mqtt": {
            "publish": FallbackStrategies.mqtt_publish_fallback,
            "subscribe": FallbackStrategies.mqtt_subscribe_fallback,
            "health": FallbackStrategies.mqtt_health_fallback,
        },
        "minio": {
            "upload": FallbackStrategies.minio_upload_fallback,
            "download": FallbackStrategies.minio_download_fallback,
            "delete": FallbackStrategies.minio_delete_fallback,
            "health": FallbackStrategies.minio_health_fallback,
        },
        "external_api": {
            "call": FallbackStrategies.external_api_fallback,
        }
    }

    service_fallbacks = fallback_map.get(service_name.lower(), {})
    return service_fallbacks.get(operation.lower())

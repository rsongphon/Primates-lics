"""
Service Dependency Registry and Health Monitoring
Tracks service dependencies and provides dependency health checks
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set

from app.core.circuit_breaker import ServiceType, cb_manager, is_circuit_healthy
from app.core.logging import get_logger

logger = get_logger(__name__)


class DependencyType(str, Enum):
    """Types of service dependencies."""
    CRITICAL = "critical"        # Service cannot function without this dependency
    IMPORTANT = "important"      # Service degraded without this dependency
    OPTIONAL = "optional"        # Service can function without this dependency


class ServiceHealth(str, Enum):
    """Service health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceDependency:
    """Represents a service dependency."""
    name: str
    service_type: ServiceType
    dependency_type: DependencyType
    description: str
    health_check_timeout: int = 5
    required_for: List[str] = field(default_factory=list)

    # Runtime state
    current_health: ServiceHealth = ServiceHealth.UNKNOWN
    last_check_time: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0


@dataclass
class ServiceImpact:
    """Represents the impact of a service failure."""
    affected_features: List[str]
    severity: str  # "critical", "major", "minor"
    user_facing: bool
    degradation_details: str


class ServiceDependencyRegistry:
    """
    Registry of all service dependencies following Documentation.md Section 2.4
    Service Dependency Matrix.
    """

    def __init__(self):
        self.dependencies: Dict[str, ServiceDependency] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.impact_map: Dict[str, ServiceImpact] = {}
        self._initialize_dependencies()

    def _initialize_dependencies(self):
        """Initialize all service dependencies from Documentation.md."""

        # PostgreSQL - Primary database
        self.register_dependency(
            ServiceDependency(
                name="PostgreSQL",
                service_type=ServiceType.POSTGRESQL,
                dependency_type=DependencyType.CRITICAL,
                description="Primary relational database for core application data",
                required_for=[
                    "user_authentication",
                    "organization_management",
                    "device_management",
                    "experiment_management",
                    "task_management",
                    "participant_management"
                ]
            ),
            impact=ServiceImpact(
                affected_features=[
                    "User login/registration",
                    "All CRUD operations",
                    "Data persistence"
                ],
                severity="critical",
                user_facing=True,
                degradation_details="Cannot perform any data operations. Read-only mode from cache if available."
            )
        )

        # Redis - Caching and session storage
        self.register_dependency(
            ServiceDependency(
                name="Redis",
                service_type=ServiceType.REDIS,
                dependency_type=DependencyType.IMPORTANT,
                description="Caching layer, session storage, and pub/sub messaging",
                required_for=[
                    "session_management",
                    "caching",
                    "rate_limiting",
                    "realtime_pubsub"
                ]
            ),
            impact=ServiceImpact(
                affected_features=[
                    "Session persistence",
                    "Response caching",
                    "Rate limiting",
                    "Real-time notifications"
                ],
                severity="major",
                user_facing=True,
                degradation_details="Increased database load, slower responses, no caching. Users may need to re-login."
            )
        )

        # InfluxDB - Time-series metrics
        self.register_dependency(
            ServiceDependency(
                name="InfluxDB",
                service_type=ServiceType.INFLUXDB,
                dependency_type=DependencyType.IMPORTANT,
                description="Time-series database for device telemetry and metrics",
                required_for=[
                    "device_telemetry",
                    "performance_metrics",
                    "experiment_data_collection"
                ]
            ),
            impact=ServiceImpact(
                affected_features=[
                    "Real-time device metrics",
                    "Historical data queries",
                    "Performance dashboards",
                    "Experiment data visualization"
                ],
                severity="major",
                user_facing=True,
                degradation_details="Cannot store or query time-series data. Device monitoring unavailable."
            )
        )

        # MQTT - Real-time messaging
        self.register_dependency(
            ServiceDependency(
                name="MQTT",
                service_type=ServiceType.MQTT,
                dependency_type=DependencyType.CRITICAL,
                description="Message broker for real-time device communication",
                required_for=[
                    "device_commands",
                    "realtime_updates",
                    "device_status",
                    "event_streaming"
                ]
            ),
            impact=ServiceImpact(
                affected_features=[
                    "Device control commands",
                    "Real-time device status",
                    "Live experiment updates",
                    "Event notifications"
                ],
                severity="critical",
                user_facing=True,
                degradation_details="Cannot send commands to devices. No real-time updates. Devices cannot report status."
            )
        )

        # MinIO - Object storage
        self.register_dependency(
            ServiceDependency(
                name="MinIO",
                service_type=ServiceType.MINIO,
                dependency_type=DependencyType.IMPORTANT,
                description="Object storage for videos, exports, and large files",
                required_for=[
                    "video_storage",
                    "file_uploads",
                    "data_exports",
                    "backup_storage"
                ]
            ),
            impact=ServiceImpact(
                affected_features=[
                    "Video streaming",
                    "File uploads/downloads",
                    "Data export functionality",
                    "Backup operations"
                ],
                severity="major",
                user_facing=True,
                degradation_details="Cannot upload/download files. Video streaming unavailable. Export functionality disabled."
            )
        )

        # Build dependency graph
        self._build_dependency_graph()

        logger.info(f"Initialized {len(self.dependencies)} service dependencies")

    def _build_dependency_graph(self):
        """Build dependency graph for visualization."""
        for dep_name, dep in self.dependencies.items():
            if dep_name not in self.dependency_graph:
                self.dependency_graph[dep_name] = set()

            # Add features that depend on this service
            for feature in dep.required_for:
                if feature not in self.dependency_graph:
                    self.dependency_graph[feature] = set()
                self.dependency_graph[feature].add(dep_name)

    def register_dependency(
        self,
        dependency: ServiceDependency,
        impact: Optional[ServiceImpact] = None
    ):
        """Register a service dependency."""
        self.dependencies[dependency.name] = dependency
        if impact:
            self.impact_map[dependency.name] = impact

        logger.debug(f"Registered dependency: {dependency.name} ({dependency.dependency_type.value})")

    def get_dependency(self, service_name: str) -> Optional[ServiceDependency]:
        """Get a service dependency by name."""
        return self.dependencies.get(service_name)

    def get_all_dependencies(self) -> List[ServiceDependency]:
        """Get all registered dependencies."""
        return list(self.dependencies.values())

    def get_critical_dependencies(self) -> List[ServiceDependency]:
        """Get all critical dependencies."""
        return [
            dep for dep in self.dependencies.values()
            if dep.dependency_type == DependencyType.CRITICAL
        ]

    def get_dependency_impact(self, service_name: str) -> Optional[ServiceImpact]:
        """Get the impact of a service failure."""
        return self.impact_map.get(service_name)

    async def check_dependency_health(self, dependency: ServiceDependency) -> ServiceHealth:
        """
        Check the health of a specific dependency.

        This uses circuit breaker status as the primary health indicator.
        """
        try:
            # Check circuit breaker state
            if is_circuit_healthy(dependency.service_type):
                dependency.current_health = ServiceHealth.HEALTHY
                dependency.consecutive_failures = 0
                dependency.last_error = None
            else:
                # Circuit breaker is open or half-open
                breaker_state = cb_manager.get_breaker_state(dependency.service_type)
                if breaker_state.get("state") == "open":
                    dependency.current_health = ServiceHealth.UNHEALTHY
                    dependency.consecutive_failures += 1
                    dependency.last_error = "Circuit breaker open"
                elif breaker_state.get("state") == "half_open":
                    dependency.current_health = ServiceHealth.DEGRADED
                    dependency.last_error = "Circuit breaker half-open (testing recovery)"

            dependency.last_check_time = datetime.now(timezone.utc)
            return dependency.current_health

        except Exception as e:
            logger.error(f"Failed to check dependency health for {dependency.name}: {e}")
            dependency.current_health = ServiceHealth.UNKNOWN
            dependency.last_error = str(e)
            return ServiceHealth.UNKNOWN

    async def check_all_dependencies_health(self) -> Dict[str, ServiceHealth]:
        """Check health of all dependencies concurrently."""
        tasks = [
            self.check_dependency_health(dep)
            for dep in self.dependencies.values()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_status = {}
        for dep, result in zip(self.dependencies.values(), results):
            if isinstance(result, Exception):
                health_status[dep.name] = ServiceHealth.UNKNOWN
                logger.error(f"Error checking {dep.name}: {result}")
            else:
                health_status[dep.name] = result

        return health_status

    def get_system_health_summary(self) -> Dict[str, any]:
        """Get overall system health summary based on dependency health."""
        critical_unhealthy = []
        important_unhealthy = []

        for dep in self.dependencies.values():
            if dep.current_health == ServiceHealth.UNHEALTHY:
                if dep.dependency_type == DependencyType.CRITICAL:
                    critical_unhealthy.append(dep.name)
                elif dep.dependency_type == DependencyType.IMPORTANT:
                    important_unhealthy.append(dep.name)

        # Determine overall system health
        if critical_unhealthy:
            system_health = ServiceHealth.UNHEALTHY
        elif important_unhealthy:
            system_health = ServiceHealth.DEGRADED
        else:
            system_health = ServiceHealth.HEALTHY

        return {
            "overall_health": system_health.value,
            "critical_services_down": critical_unhealthy,
            "important_services_down": important_unhealthy,
            "total_dependencies": len(self.dependencies),
            "healthy_dependencies": sum(
                1 for dep in self.dependencies.values()
                if dep.current_health == ServiceHealth.HEALTHY
            ),
            "degraded_dependencies": sum(
                1 for dep in self.dependencies.values()
                if dep.current_health == ServiceHealth.DEGRADED
            ),
            "unhealthy_dependencies": sum(
                1 for dep in self.dependencies.values()
                if dep.current_health == ServiceHealth.UNHEALTHY
            ),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_affected_features(self, service_name: str) -> List[str]:
        """Get list of features affected by a service failure."""
        dep = self.get_dependency(service_name)
        if dep:
            return dep.required_for
        return []

    def get_dependency_visualization_data(self) -> Dict[str, any]:
        """
        Get dependency data formatted for visualization (D3.js, Mermaid, etc.).

        Returns data in a graph format suitable for dependency visualization.
        """
        nodes = []
        links = []

        # Add service nodes
        for dep_name, dep in self.dependencies.items():
            nodes.append({
                "id": dep_name,
                "name": dep_name,
                "type": "service",
                "dependency_type": dep.dependency_type.value,
                "health": dep.current_health.value,
                "description": dep.description
            })

        # Add feature nodes and links
        for feature, services in self.dependency_graph.items():
            if feature not in self.dependencies:  # It's a feature, not a service
                nodes.append({
                    "id": feature,
                    "name": feature.replace("_", " ").title(),
                    "type": "feature"
                })

                for service in services:
                    links.append({
                        "source": service,
                        "target": feature,
                        "type": "requires"
                    })

        return {
            "nodes": nodes,
            "links": links,
            "metadata": {
                "total_services": len(self.dependencies),
                "total_features": len([n for n in nodes if n["type"] == "feature"]),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }

    def get_mermaid_diagram(self) -> str:
        """
        Generate a Mermaid diagram representation of service dependencies.

        Returns a Mermaid diagram string that can be rendered in documentation.
        """
        lines = ["graph TD"]

        # Add services with health indicators
        for dep_name, dep in self.dependencies.items():
            health_icon = "✓" if dep.current_health == ServiceHealth.HEALTHY else "✗"
            dep_type_style = (
                "critical" if dep.dependency_type == DependencyType.CRITICAL
                else "important" if dep.dependency_type == DependencyType.IMPORTANT
                else "optional"
            )
            lines.append(f'    {dep_name}["{health_icon} {dep_name}<br/>{dep_type_style}"]')

        # Add dependencies
        for feature, services in self.dependency_graph.items():
            if feature not in self.dependencies:
                lines.append(f'    {feature}("{feature.replace("_", " ").title()}")')
                for service in services:
                    lines.append(f'    {service} --> {feature}')

        # Add styling
        lines.extend([
            "",
            "    classDef critical fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px",
            "    classDef important fill:#ffd43b,stroke:#fab005,stroke-width:2px",
            "    classDef optional fill:#51cf66,stroke:#2f9e44,stroke-width:2px",
            ""
        ])

        # Apply styles
        for dep_name, dep in self.dependencies.items():
            if dep.dependency_type == DependencyType.CRITICAL:
                lines.append(f"    class {dep_name} critical")
            elif dep.dependency_type == DependencyType.IMPORTANT:
                lines.append(f"    class {dep_name} important")
            else:
                lines.append(f"    class {dep_name} optional")

        return "\n".join(lines)


# Global service dependency registry instance
service_registry = ServiceDependencyRegistry()

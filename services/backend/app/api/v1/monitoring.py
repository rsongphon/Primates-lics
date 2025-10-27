"""
System Monitoring and Dependency Visualization Endpoints
Provides circuit breaker status, dependency health, and visualization data
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.circuit_breaker import (
    cb_manager,
    get_circuit_breaker_stats,
    ServiceType,
    are_all_circuits_healthy
)
from app.core.service_dependencies import service_registry, ServiceHealth
from app.core.fallback_strategies import degraded_mode_handler
from app.core.dependencies import require_any_permission

router = APIRouter()


# ===== CIRCUIT BREAKER ENDPOINTS =====

@router.get("/circuit-breakers")
async def get_circuit_breakers_status(
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """
    Get status of all circuit breakers.

    Returns detailed information about each circuit breaker including:
    - Current state (closed, open, half_open)
    - Failure counters
    - Configuration (fail_max, timeout_duration)
    - Last opened time
    """
    stats = get_circuit_breaker_stats()

    return {
        "success": True,
        "data": stats,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "all_healthy": are_all_circuits_healthy()
        }
    }


@router.get("/circuit-breakers/{service_type}")
async def get_circuit_breaker_status(
    service_type: str,
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """Get status of a specific circuit breaker."""
    try:
        service_type_enum = ServiceType(service_type.lower())
        state = cb_manager.get_breaker_state(service_type_enum)

        if "error" in state:
            raise HTTPException(status_code=404, detail=f"Circuit breaker not found for service: {service_type}")

        return {
            "success": True,
            "data": state,
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service type: {service_type}. Valid types: {[e.value for e in ServiceType]}"
        )


@router.post("/circuit-breakers/{service_type}/reset")
async def reset_circuit_breaker(
    service_type: str,
    current_user=Depends(require_any_permission(["system:admin"]))
):
    """
    Manually reset a circuit breaker (Admin only).

    This will close the circuit and reset failure counters.
    Use with caution - only reset if you're sure the service has recovered.
    """
    try:
        service_type_enum = ServiceType(service_type.lower())
        cb_manager.reset_breaker(service_type_enum)

        return {
            "success": True,
            "message": f"Circuit breaker reset for {service_type}",
            "data": cb_manager.get_breaker_state(service_type_enum),
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid service type: {service_type}")


@router.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers(
    current_user=Depends(require_any_permission(["system:admin"]))
):
    """
    Reset all circuit breakers (Admin only).

    This is a dangerous operation - use only in emergency situations.
    """
    cb_manager.reset_all_breakers()

    return {
        "success": True,
        "message": "All circuit breakers reset",
        "data": get_circuit_breaker_stats(),
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }


# ===== SERVICE DEPENDENCY ENDPOINTS =====

@router.get("/dependencies")
async def get_service_dependencies(
    include_health: bool = Query(True, description="Include current health status"),
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """
    Get all service dependencies with health status.

    Returns comprehensive information about service dependencies including:
    - Dependency type (critical, important, optional)
    - Current health status
    - Impact of service failure
    - Features that depend on each service
    """
    if include_health:
        # Check health of all dependencies
        await service_registry.check_all_dependencies_health()

    dependencies_data = []
    for dep in service_registry.get_all_dependencies():
        dep_data = {
            "name": dep.name,
            "service_type": dep.service_type.value,
            "dependency_type": dep.dependency_type.value,
            "description": dep.description,
            "required_for": dep.required_for,
        }

        if include_health:
            dep_data.update({
                "current_health": dep.current_health.value,
                "last_check_time": dep.last_check_time.isoformat() if dep.last_check_time else None,
                "consecutive_failures": dep.consecutive_failures,
                "last_error": dep.last_error
            })

        # Add impact information
        impact = service_registry.get_dependency_impact(dep.name)
        if impact:
            dep_data["impact"] = {
                "affected_features": impact.affected_features,
                "severity": impact.severity,
                "user_facing": impact.user_facing,
                "degradation_details": impact.degradation_details
            }

        dependencies_data.append(dep_data)

    return {
        "success": True,
        "data": {
            "dependencies": dependencies_data,
            "summary": service_registry.get_system_health_summary()
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_dependencies": len(dependencies_data)
        }
    }


@router.get("/dependencies/{service_name}")
async def get_service_dependency(
    service_name: str,
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """Get detailed information about a specific service dependency."""
    dep = service_registry.get_dependency(service_name)

    if not dep:
        raise HTTPException(status_code=404, detail=f"Service dependency not found: {service_name}")

    # Check current health
    health = await service_registry.check_dependency_health(dep)

    return {
        "success": True,
        "data": {
            "name": dep.name,
            "service_type": dep.service_type.value,
            "dependency_type": dep.dependency_type.value,
            "description": dep.description,
            "required_for": dep.required_for,
            "current_health": health.value,
            "last_check_time": dep.last_check_time.isoformat() if dep.last_check_time else None,
            "consecutive_failures": dep.consecutive_failures,
            "last_error": dep.last_error,
            "impact": service_registry.get_dependency_impact(dep.name).__dict__ if service_registry.get_dependency_impact(dep.name) else None
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }


@router.get("/dependencies/visualization/graph")
async def get_dependency_visualization(
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """
    Get dependency graph data for visualization.

    Returns data in a format suitable for D3.js, Cytoscape.js, or other
    graph visualization libraries.

    The data includes:
    - Nodes: Services and features
    - Links: Dependencies between services and features
    - Metadata: Health status, dependency types, etc.
    """
    # Update health status before generating visualization
    await service_registry.check_all_dependencies_health()

    viz_data = service_registry.get_dependency_visualization_data()

    return {
        "success": True,
        "data": viz_data,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "format": "graph"
        }
    }


@router.get("/dependencies/visualization/mermaid", response_class=PlainTextResponse)
async def get_dependency_mermaid_diagram(
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """
    Get dependency diagram in Mermaid format.

    Returns a Mermaid diagram string that can be rendered in markdown
    or documentation tools.

    Example usage in markdown:
    ```mermaid
    [diagram output]
    ```
    """
    # Update health status before generating diagram
    await service_registry.check_all_dependencies_health()

    diagram = service_registry.get_mermaid_diagram()
    return diagram


# ===== SYSTEM HEALTH ENDPOINTS =====

@router.get("/system-health")
async def get_system_health(
    include_details: bool = Query(True, description="Include detailed service information"),
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """
    Get comprehensive system health status.

    Combines circuit breaker status, service dependency health,
    and degraded mode information into a single endpoint.
    """
    # Check all dependency health
    await service_registry.check_all_dependencies_health()

    # Get circuit breaker stats
    cb_stats = get_circuit_breaker_stats()

    # Get dependency summary
    dependency_summary = service_registry.get_system_health_summary()

    # Get degraded mode status
    degraded_status = degraded_mode_handler.get_degraded_status()

    # Determine overall system status
    if dependency_summary["overall_health"] == "unhealthy":
        overall_status = "unhealthy"
        status_code = 503
    elif dependency_summary["overall_health"] == "degraded" or degraded_status["is_degraded"]:
        overall_status = "degraded"
        status_code = 200
    else:
        overall_status = "healthy"
        status_code = 200

    response_data = {
        "success": True,
        "data": {
            "overall_status": overall_status,
            "circuit_breakers": cb_stats if include_details else {
                "summary": cb_stats["summary"]
            },
            "dependencies": dependency_summary,
            "degraded_mode": degraded_status
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

    return JSONResponse(content=response_data, status_code=status_code)


# ===== DEGRADED MODE ENDPOINTS =====

@router.get("/degraded-mode")
async def get_degraded_mode_status(
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """Get current degraded mode status."""
    status = degraded_mode_handler.get_degraded_status()

    return {
        "success": True,
        "data": status,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }


@router.get("/metrics/sli")
async def get_sli_metrics(
    service: Optional[str] = Query(None, description="Filter by specific service"),
    current_user=Depends(require_any_permission(["system:monitor", "system:admin"]))
):
    """
    Get Service Level Indicator (SLI) metrics.

    Returns SLI metrics for monitoring SLOs defined in Documentation.md Section 13.1:
    - Availability: Percentage of successful requests
    - Latency: P50, P95, P99 response times
    - Error Rate: Percentage of failed requests
    - Throughput: Requests per second

    Note: Actual metrics are collected by Prometheus.
    This endpoint provides metadata and current status.
    """
    # This is a placeholder - actual SLI metrics come from Prometheus
    # In production, this would query Prometheus and return aggregated SLI data

    return {
        "success": True,
        "data": {
            "note": "SLI metrics are collected by Prometheus. Query Prometheus for detailed metrics.",
            "prometheus_endpoint": "http://localhost:9090",
            "key_metrics": {
                "availability": {
                    "metric_name": "circuit_breaker_successes_total / (circuit_breaker_successes_total + circuit_breaker_failures_total)",
                    "target_slo": "99.9%",
                    "current_status": "healthy" if are_all_circuits_healthy() else "degraded"
                },
                "error_rate": {
                    "metric_name": "circuit_breaker_failures_total",
                    "target_slo": "<0.1%",
                    "current_status": "healthy" if are_all_circuits_healthy() else "degraded"
                },
                "latency": {
                    "metric_name": "circuit_breaker_call_duration_seconds",
                    "target_slo": "P95 < 200ms",
                    "current_status": "unknown"
                }
            }
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

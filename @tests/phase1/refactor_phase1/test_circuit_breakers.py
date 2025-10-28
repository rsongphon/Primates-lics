"""
Phase 1 Circuit Breaker Integration Tests
Tests circuit breaker functionality, fallbacks, and monitoring
"""

import asyncio
import pytest
import sys
from pathlib import Path
from typing import Any

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "services" / "backend"
sys.path.insert(0, str(backend_path))

from app.core.circuit_breaker import (
    cb_manager,
    ServiceType,
    with_circuit_breaker,
    get_circuit_breaker_stats,
    is_circuit_healthy,
    are_all_circuits_healthy,
)
from app.core.fallback_strategies import (
    FallbackStrategies,
    degraded_mode_handler,
    get_fallback_for_service,
)
from app.core.service_dependencies import (
    service_registry,
    ServiceHealth,
    DependencyType,
)


class TestCircuitBreakerInitialization:
    """Test circuit breaker initialization and configuration."""

    def test_circuit_breaker_manager_initialized(self):
        """Test that circuit breaker manager is properly initialized."""
        assert cb_manager is not None
        assert len(cb_manager._breakers) == 6  # 6 service types

    def test_all_service_types_have_breakers(self):
        """Test that all service types have circuit breakers."""
        for service_type in ServiceType:
            breaker = cb_manager.get_breaker(service_type)
            assert breaker is not None
            assert breaker.name is not None

    def test_circuit_breaker_configurations(self):
        """Test circuit breaker configurations match specifications."""
        # PostgreSQL - Critical
        pg_state = cb_manager.get_breaker_state(ServiceType.POSTGRESQL)
        assert pg_state["fail_max"] == 5
        assert pg_state["timeout_duration"] == 60

        # Redis - Important
        redis_state = cb_manager.get_breaker_state(ServiceType.REDIS)
        assert redis_state["fail_max"] == 5
        assert redis_state["timeout_duration"] == 30

        # InfluxDB - More tolerant
        influx_state = cb_manager.get_breaker_state(ServiceType.INFLUXDB)
        assert influx_state["fail_max"] == 10
        assert influx_state["timeout_duration"] == 30

    def test_initial_state_is_closed(self):
        """Test that all circuit breakers start in closed state."""
        for service_type in ServiceType:
            state = cb_manager.get_breaker_state(service_type)
            assert state["state"] == "closed"
            assert state["fail_counter"] == 0


class TestCircuitBreakerDecorators:
    """Test circuit breaker decorators."""

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test decorator with successful async function."""
        call_count = 0

        @with_circuit_breaker(ServiceType.POSTGRESQL, fallback_value="fallback")
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_function_failure_opens_circuit(self):
        """Test that failures open the circuit breaker."""
        # Reset breaker first
        cb_manager.reset_breaker(ServiceType.POSTGRESQL)

        @with_circuit_breaker(ServiceType.POSTGRESQL, fallback_value="fallback")
        async def failing_function():
            raise Exception("Simulated failure")

        # Get fail_max for PostgreSQL
        breaker = cb_manager.get_breaker(ServiceType.POSTGRESQL)
        fail_max = breaker.fail_max

        # Trigger failures to open circuit
        for _ in range(fail_max):
            try:
                await failing_function()
            except Exception:
                pass

        # Circuit should now be open
        state = cb_manager.get_breaker_state(ServiceType.POSTGRESQL)
        assert state["state"] == "open"

        # Reset for other tests
        cb_manager.reset_breaker(ServiceType.POSTGRESQL)

    @pytest.mark.asyncio
    async def test_fallback_executes_when_circuit_open(self):
        """Test that fallback value is returned when circuit is open."""
        # This test requires circuit to be open from previous test
        # or manually opened
        @with_circuit_breaker(ServiceType.EXTERNAL_API, fallback_value="fallback_value")
        async def function_with_fallback():
            raise Exception("Should not reach here if circuit is open")

        # Open the circuit by triggering failures
        breaker = cb_manager.get_breaker(ServiceType.EXTERNAL_API)
        for _ in range(breaker.fail_max + 1):
            try:
                await function_with_fallback()
            except Exception:
                pass

        # Now circuit is open, fallback should execute
        result = await function_with_fallback()
        assert result == "fallback_value"

        # Reset
        cb_manager.reset_breaker(ServiceType.EXTERNAL_API)

    def test_sync_function_with_decorator(self):
        """Test decorator with synchronous function."""

        @with_circuit_breaker(ServiceType.REDIS, fallback_value={})
        def sync_function():
            return {"data": "test"}

        result = sync_function()
        assert result == {"data": "test"}


class TestFallbackStrategies:
    """Test fallback strategy implementations."""

    @pytest.mark.asyncio
    async def test_postgresql_read_fallback(self):
        """Test PostgreSQL read fallback returns degraded response."""
        result = await FallbackStrategies.postgresql_read_fallback()
        assert isinstance(result, dict)
        assert result["data"] == []
        assert result["meta"]["degraded"] is True
        assert result["meta"]["reason"] == "database_unavailable"

    @pytest.mark.asyncio
    async def test_postgresql_write_fallback(self):
        """Test PostgreSQL write fallback queues operation."""
        result = await FallbackStrategies.postgresql_write_fallback()
        assert result["success"] is False
        assert result["queued"] is True
        assert "retry_after" in result

    @pytest.mark.asyncio
    async def test_redis_get_fallback(self):
        """Test Redis GET fallback returns None."""
        result = await FallbackStrategies.redis_get_fallback("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_set_fallback(self):
        """Test Redis SET fallback returns False."""
        result = await FallbackStrategies.redis_set_fallback("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_influxdb_write_fallback(self):
        """Test InfluxDB write fallback logs dropped metrics."""
        result = await FallbackStrategies.influxdb_write_fallback("measurement", {"field": "value"})
        assert result is False

    def test_mqtt_publish_fallback(self):
        """Test MQTT publish fallback logs failed publish."""
        result = FallbackStrategies.mqtt_publish_fallback("topic", "payload")
        assert result is False

    def test_minio_upload_fallback(self):
        """Test MinIO upload fallback returns error."""
        result = FallbackStrategies.minio_upload_fallback("bucket", "object")
        assert result["success"] is False
        assert "retry_after" in result


class TestDegradedModeHandler:
    """Test degraded mode handler functionality."""

    def test_mark_service_degraded(self):
        """Test marking a service as degraded."""
        degraded_mode_handler.mark_service_degraded("test_service")
        assert degraded_mode_handler.is_service_degraded("test_service")

    def test_mark_service_healthy(self):
        """Test marking a degraded service as healthy."""
        degraded_mode_handler.mark_service_degraded("test_service_2")
        assert degraded_mode_handler.is_service_degraded("test_service_2")

        degraded_mode_handler.mark_service_healthy("test_service_2")
        assert not degraded_mode_handler.is_service_degraded("test_service_2")

    def test_get_degraded_services(self):
        """Test getting list of degraded services."""
        # Clean up first
        for service in degraded_mode_handler.get_degraded_services():
            degraded_mode_handler.mark_service_healthy(service)

        degraded_mode_handler.mark_service_degraded("service1")
        degraded_mode_handler.mark_service_degraded("service2")

        degraded = degraded_mode_handler.get_degraded_services()
        assert "service1" in degraded
        assert "service2" in degraded

        # Cleanup
        degraded_mode_handler.mark_service_healthy("service1")
        degraded_mode_handler.mark_service_healthy("service2")

    def test_system_degraded_when_critical_service_down(self):
        """Test system degraded mode when critical service is down."""
        # Clean first
        for service in degraded_mode_handler.get_degraded_services():
            degraded_mode_handler.mark_service_healthy(service)

        # PostgreSQL is critical
        degraded_mode_handler.mark_service_degraded("postgresql")
        assert degraded_mode_handler.is_system_degraded()

        # Cleanup
        degraded_mode_handler.mark_service_healthy("postgresql")


class TestServiceDependencyRegistry:
    """Test service dependency registry."""

    def test_registry_initialized(self):
        """Test that service registry is properly initialized."""
        assert service_registry is not None
        assert len(service_registry.dependencies) == 5  # 5 main dependencies

    def test_all_dependencies_registered(self):
        """Test that all expected dependencies are registered."""
        expected_services = ["PostgreSQL", "Redis", "InfluxDB", "MQTT", "MinIO"]
        for service_name in expected_services:
            dep = service_registry.get_dependency(service_name)
            assert dep is not None
            assert dep.name == service_name

    def test_critical_dependencies_identified(self):
        """Test that critical dependencies are correctly identified."""
        critical_deps = service_registry.get_critical_dependencies()
        critical_names = [dep.name for dep in critical_deps]

        # PostgreSQL and MQTT are critical
        assert "PostgreSQL" in critical_names
        assert "MQTT" in critical_names

    def test_dependency_impact_defined(self):
        """Test that impact is defined for all dependencies."""
        for dep in service_registry.get_all_dependencies():
            impact = service_registry.get_dependency_impact(dep.name)
            assert impact is not None
            assert len(impact.affected_features) > 0
            assert impact.severity in ["critical", "major", "minor"]

    @pytest.mark.asyncio
    async def test_dependency_health_check(self):
        """Test dependency health check."""
        dep = service_registry.get_dependency("PostgreSQL")
        health = await service_registry.check_dependency_health(dep)
        assert health in [ServiceHealth.HEALTHY, ServiceHealth.DEGRADED, ServiceHealth.UNHEALTHY]

    @pytest.mark.asyncio
    async def test_check_all_dependencies(self):
        """Test checking all dependencies concurrently."""
        health_status = await service_registry.check_all_dependencies_health()
        assert len(health_status) == 5  # All 5 services

    def test_dependency_graph_generation(self):
        """Test dependency graph data generation."""
        graph_data = service_registry.get_dependency_visualization_data()
        assert "nodes" in graph_data
        assert "links" in graph_data
        assert "metadata" in graph_data
        assert len(graph_data["nodes"]) > 0

    def test_mermaid_diagram_generation(self):
        """Test Mermaid diagram generation."""
        diagram = service_registry.get_mermaid_diagram()
        assert "graph TD" in diagram
        assert "PostgreSQL" in diagram
        assert "Redis" in diagram
        assert "critical" in diagram


class TestCircuitBreakerStats:
    """Test circuit breaker statistics and monitoring."""

    def test_get_circuit_breaker_stats(self):
        """Test getting circuit breaker statistics."""
        stats = get_circuit_breaker_stats()
        assert "timestamp" in stats
        assert "circuit_breakers" in stats
        assert "summary" in stats
        assert stats["summary"]["total_breakers"] == 6

    def test_is_circuit_healthy(self):
        """Test checking if individual circuit is healthy."""
        # Reset all breakers first
        cb_manager.reset_all_breakers()

        # All should be healthy (closed) after reset
        for service_type in ServiceType:
            assert is_circuit_healthy(service_type)

    def test_are_all_circuits_healthy(self):
        """Test checking if all circuits are healthy."""
        # Reset all breakers
        cb_manager.reset_all_breakers()

        assert are_all_circuits_healthy()


class TestFallbackLookup:
    """Test fallback function lookup."""

    def test_get_fallback_for_service(self):
        """Test getting fallback function for service and operation."""
        # PostgreSQL read fallback
        fallback = get_fallback_for_service("postgresql", "read")
        assert fallback is not None

        # Redis get fallback
        fallback = get_fallback_for_service("redis", "get")
        assert fallback is not None

        # Invalid service returns None
        fallback = get_fallback_for_service("invalid_service", "read")
        assert fallback is None


# ===== INTEGRATION TESTS =====

class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_service_dependency(self):
        """Test circuit breaker integration with service dependency registry."""
        # Get PostgreSQL dependency
        dep = service_registry.get_dependency("PostgreSQL")

        # Check its health (should use circuit breaker)
        health = await service_registry.check_dependency_health(dep)

        # If circuit is healthy, dependency should be healthy
        if is_circuit_healthy(ServiceType.POSTGRESQL):
            assert health == ServiceHealth.HEALTHY


# ===== TEST FIXTURES =====

@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset all circuit breakers before each test."""
    cb_manager.reset_all_breakers()
    yield
    # Optional: Reset after test as well
    # cb_manager.reset_all_breakers()


# ===== RUN TESTS =====

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])

# Circuit Breaker Integration Guide

## Overview

This guide explains how to integrate circuit breakers into the LICS backend services. Circuit breakers have been implemented following the RefactorPlan.md Phase 1 specifications.

## Architecture

### Components Created

1. **Circuit Breaker Core** (`app/core/circuit_breaker.py`)
   - Circuit breaker manager with Prometheus metrics
   - Decorators for easy integration
   - Service-specific configurations

2. **Fallback Strategies** (`app/core/fallback_strategies.py`)
   - Graceful degradation for each service
   - Degraded mode handler
   - Service-specific fallback functions

3. **Service Dependency Registry** (`app/core/service_dependencies.py`)
   - Tracks all service dependencies
   - Health monitoring and visualization
   - Impact assessment

4. **Monitoring API** (`app/api/v1/monitoring.py`)
   - Circuit breaker status endpoints
   - Dependency visualization
   - System health monitoring

## Using Circuit Breakers

### Basic Usage

```python
from app.core.circuit_breaker import with_circuit_breaker, ServiceType

# Protect async functions
@with_circuit_breaker(ServiceType.POSTGRESQL, fallback_value=None)
async def query_database(query: str):
    # Database query code
    return await execute_query(query)

# Protect sync functions
@with_circuit_breaker(ServiceType.REDIS, fallback_value={})
def get_from_cache(key: str):
    return redis.get(key)
```

### With Custom Fallback

```python
from app.core.circuit_breaker import cb_manager, ServiceType
from app.core.fallback_strategies import FallbackStrategies

# Register custom fallback
cb_manager.register_fallback(
    ServiceType.POSTGRESQL,
    FallbackStrategies.postgresql_read_fallback
)

# Use decorator with registered fallback
@with_circuit_breaker(ServiceType.POSTGRESQL, use_fallback_handler=True)
async def get_users():
    return await db.query(User).all()
```

## Integration Examples

### Database Operations

```python
# app/repositories/base.py
from app.core.circuit_breaker import with_circuit_breaker, ServiceType

class BaseRepository:
    @with_circuit_breaker(ServiceType.POSTGRESQL, fallback_value=[])
    async def find_all(self):
        async with self.db.begin():
            result = await self.db.execute(select(self.model))
            return result.scalars().all()

    @with_circuit_breaker(ServiceType.POSTGRESQL, fallback_value=None)
    async def find_by_id(self, id: UUID):
        async with self.db.begin():
            result = await self.db.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
```

### Redis Operations

```python
# app/services/cache.py
from app.core.circuit_breaker import with_circuit_breaker, ServiceType

class CacheService:
    @with_circuit_breaker(ServiceType.REDIS, fallback_value=None)
    async def get(self, key: str):
        return await self.redis.get(key)

    @with_circuit_breaker(ServiceType.REDIS, fallback_value=False)
    async def set(self, key: str, value: Any, ttl: int = 3600):
        return await self.redis.set(key, value, ex=ttl)
```

### MQTT Operations

```python
# app/services/mqtt.py
from app.core.circuit_breaker import with_circuit_breaker, ServiceType

class MQTTService:
    @with_circuit_breaker(ServiceType.MQTT, fallback_value=False)
    def publish(self, topic: str, payload: dict):
        return self.client.publish(topic, json.dumps(payload))
```

### InfluxDB Operations

```python
# app/services/telemetry.py
from app.core.circuit_breaker import with_circuit_breaker, ServiceType

class TelemetryService:
    @with_circuit_breaker(ServiceType.INFLUXDB, fallback_value=False)
    async def write_point(self, measurement: str, fields: dict):
        point = Point(measurement).time(datetime.utcnow())
        for key, value in fields.items():
            point = point.field(key, value)
        return await self.write_api.write(bucket=self.bucket, record=point)
```

### MinIO Operations

```python
# app/services/storage.py
from app.core.circuit_breaker import with_circuit_breaker, ServiceType

class StorageService:
    @with_circuit_breaker(ServiceType.MINIO, fallback_value=None)
    def upload_file(self, bucket: str, object_name: str, data: bytes):
        return self.client.put_object(
            bucket, object_name, BytesIO(data), len(data)
        )
```

## Monitoring Endpoints

### Circuit Breaker Status

```bash
# Get all circuit breakers status
GET /api/v1/monitoring/circuit-breakers

# Get specific circuit breaker
GET /api/v1/monitoring/circuit-breakers/postgresql

# Reset circuit breaker (admin only)
POST /api/v1/monitoring/circuit-breakers/postgresql/reset
```

### Service Dependencies

```bash
# Get all service dependencies with health
GET /api/v1/monitoring/dependencies

# Get specific service dependency
GET /api/v1/monitoring/dependencies/PostgreSQL

# Get dependency visualization
GET /api/v1/monitoring/dependencies/visualization/graph

# Get Mermaid diagram
GET /api/v1/monitoring/dependencies/visualization/mermaid
```

### System Health

```bash
# Comprehensive system health (includes circuit breakers)
GET /api/v1/monitoring/system-health

# Degraded mode status
GET /api/v1/monitoring/degraded-mode

# SLI metrics
GET /api/v1/monitoring/metrics/sli
```

## Prometheus Metrics

Circuit breakers expose the following metrics:

```
# Circuit breaker state (0=closed, 1=open, 2=half_open)
circuit_breaker_state{service_name="PostgreSQL",service_type="postgresql"}

# Total failures
circuit_breaker_failures_total{service_name="PostgreSQL",service_type="postgresql",failure_reason="ConnectionError"}

# Total successes
circuit_breaker_successes_total{service_name="PostgreSQL",service_type="postgresql"}

# Total rejections
circuit_breaker_rejections_total{service_name="PostgreSQL",service_type="postgresql"}

# Total fallback executions
circuit_breaker_fallbacks_total{service_name="PostgreSQL",service_type="postgresql"}

# Call duration histogram
circuit_breaker_call_duration_seconds{service_name="PostgreSQL",service_type="postgresql",success="true"}
```

## Testing Circuit Breakers

### Manual Testing

```bash
# 1. Start the development environment
make dev

# 2. Check initial circuit breaker status
curl http://localhost:8080/api/v1/monitoring/circuit-breakers

# 3. Simulate service failure (stop PostgreSQL)
docker-compose -f docker-compose.dev.yml stop postgres-dev

# 4. Make requests to trigger circuit breaker
curl http://localhost:8080/api/v1/health/comprehensive

# 5. Check circuit breaker opened
curl http://localhost:8080/api/v1/monitoring/circuit-breakers/postgresql

# 6. Restart service
docker-compose -f docker-compose.dev.yml start postgres-dev

# 7. Wait for circuit breaker to recover (timeout_duration)
# Circuit will go: open -> half_open -> closed

# 8. Verify recovery
curl http://localhost:8080/api/v1/monitoring/circuit-breakers/postgresql
```

### Automated Testing

```python
# tests/integration/test_circuit_breakers.py
import pytest
from app.core.circuit_breaker import cb_manager, ServiceType

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test that circuit breaker opens after max failures."""
    breaker = cb_manager.get_breaker(ServiceType.POSTGRESQL)

    # Trigger failures
    for _ in range(breaker.fail_max):
        try:
            await breaker.call_async(failing_function)
        except:
            pass

    # Circuit should be open
    assert breaker.current_state.name == "open"

@pytest.mark.asyncio
async def test_fallback_executed_when_circuit_open():
    """Test that fallback is executed when circuit is open."""
    result = await protected_function_with_fallback()

    assert result is not None  # Fallback value returned
```

## Configuration

### Circuit Breaker Settings

Located in `app/core/circuit_breaker.py` - `CircuitBreakerConfig` class:

```python
POSTGRESQL = {
    "fail_max": 5,              # Open after 5 consecutive failures
    "timeout_duration": 60,     # Stay open for 60 seconds
    "expected_exception": Exception,
    "name": "PostgreSQL"
}
```

### Adjusting for Your Environment

1. **Development**: More tolerant settings
   ```python
   "fail_max": 10,             # Allow more failures
   "timeout_duration": 30,     # Faster recovery
   ```

2. **Production**: Stricter settings
   ```python
   "fail_max": 3,              # Quick to open
   "timeout_duration": 120,    # Longer recovery time
   ```

## Best Practices

1. **Use Appropriate Fallbacks**
   - Read operations: Return cached data or empty results
   - Write operations: Queue for retry or return error
   - Critical operations: Fail fast with clear error message

2. **Monitor Circuit Breaker State**
   - Set up alerts for circuit breaker openings
   - Track failure patterns in Prometheus/Grafana
   - Review circuit breaker logs regularly

3. **Test Failure Scenarios**
   - Simulate service failures in staging
   - Verify fallback behavior
   - Test recovery mechanisms

4. **Gradual Integration**
   - Start with non-critical services
   - Monitor impact on performance
   - Adjust configurations based on metrics

5. **Document Service Dependencies**
   - Update service dependency registry
   - Document impact of service failures
   - Maintain dependency visualization

## Troubleshooting

### Circuit Breaker Not Opening

- Check failure count threshold (`fail_max`)
- Verify exception types are caught
- Review logs for actual failures

### Circuit Breaker Stuck Open

- Check timeout duration
- Verify service has recovered
- Manually reset if needed: `POST /api/v1/monitoring/circuit-breakers/{service}/reset`

### Fallbacks Not Working

- Verify fallback handler is registered
- Check decorator parameters
- Review fallback function implementation

### Performance Impact

- Circuit breakers add minimal overhead (~1-2ms)
- If concerned, adjust monitoring interval
- Use caching for circuit breaker state checks

## Next Steps

1. **Gradual Rollout**
   - Start with database operations
   - Add Redis operations
   - Integrate into MQTT, InfluxDB, MinIO

2. **Monitoring Setup**
   - Configure Prometheus alerts
   - Create Grafana dashboards
   - Set up notification channels

3. **Load Testing**
   - Test under normal load
   - Test during service failures
   - Verify fallback performance

4. **Documentation**
   - Update API documentation
   - Add runbooks for operations team
   - Document failure scenarios

## References

- RefactorPlan.md - Phase 1: API Gateway & Circuit Breakers
- Documentation.md - Section 2.4: Service Dependency Matrix
- Documentation.md - Section 13.1: SLI/SLO Definitions
- pybreaker documentation: https://github.com/danielfm/pybreaker

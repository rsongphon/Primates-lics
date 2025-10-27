"""
Circuit Breaker Pattern Implementation
Provides resilience for external service dependencies
"""

import asyncio
import functools
import logging
import random
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

import pybreaker
from prometheus_client import Counter, Gauge, Histogram
from pybreaker import CircuitBreaker, CircuitBreakerListener
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

# Type variable for generic return types
T = TypeVar('T')


class ServiceType(str, Enum):
    """Enum for service types with circuit breakers."""
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    INFLUXDB = "influxdb"
    MQTT = "mqtt"
    MINIO = "minio"
    EXTERNAL_API = "external_api"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


# ===== PROMETHEUS METRICS =====

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Current state of circuit breakers (0=closed, 1=open, 2=half_open)',
    ['service_name', 'service_type']
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total number of circuit breaker failures',
    ['service_name', 'service_type', 'failure_reason']
)

circuit_breaker_successes = Counter(
    'circuit_breaker_successes_total',
    'Total number of successful circuit breaker calls',
    ['service_name', 'service_type']
)

circuit_breaker_rejections = Counter(
    'circuit_breaker_rejections_total',
    'Total number of rejected calls due to open circuit',
    ['service_name', 'service_type']
)

circuit_breaker_fallbacks = Counter(
    'circuit_breaker_fallbacks_total',
    'Total number of fallback executions',
    ['service_name', 'service_type']
)

circuit_breaker_call_duration = Histogram(
    'circuit_breaker_call_duration_seconds',
    'Duration of circuit breaker protected calls',
    ['service_name', 'service_type', 'success']
)


# ===== CIRCUIT BREAKER LISTENER =====

class PrometheusCircuitBreakerListener(CircuitBreakerListener):
    """Circuit breaker listener that publishes metrics to Prometheus."""

    def __init__(self, service_name: str, service_type: ServiceType):
        self.service_name = service_name
        self.service_type = service_type.value

    def state_change(self, cb: CircuitBreaker, old_state: Any, new_state: Any) -> None:
        """Called when circuit breaker changes state."""
        # Handle both string and enum state types
        old_name = old_state.name if hasattr(old_state, 'name') else str(old_state)
        new_name = new_state.name if hasattr(new_state, 'name') else str(new_state)

        logger.warning(
            f"Circuit breaker state change: {self.service_name} "
            f"({self.service_type}) {old_name} -> {new_name}"
        )

        # Update Prometheus metric
        state_value = 0 if new_name == "closed" else 1 if new_name == "open" else 2
        circuit_breaker_state.labels(
            service_name=self.service_name,
            service_type=self.service_type
        ).set(state_value)

    def before_call(self, cb: CircuitBreaker, func: Callable, *args, **kwargs) -> None:
        """Called before executing the protected function."""
        pass

    def success(self, cb: CircuitBreaker) -> None:
        """Called when a call succeeds."""
        circuit_breaker_successes.labels(
            service_name=self.service_name,
            service_type=self.service_type
        ).inc()

    def failure(self, cb: CircuitBreaker, exception: Exception) -> None:
        """Called when a call fails."""
        circuit_breaker_failures.labels(
            service_name=self.service_name,
            service_type=self.service_type,
            failure_reason=type(exception).__name__
        ).inc()

        logger.error(
            f"Circuit breaker failure: {self.service_name} ({self.service_type})",
            extra={
                "service_name": self.service_name,
                "service_type": self.service_type,
                "exception": str(exception),
                "exception_type": type(exception).__name__
            }
        )


# ===== CIRCUIT BREAKER CONFIGURATIONS =====

class CircuitBreakerConfig:
    """Configuration for circuit breakers."""

    # PostgreSQL - Critical service, moderate tolerance
    POSTGRESQL = {
        "fail_max": 5,              # Open after 5 failures
        "timeout_duration": 60,     # Stay open for 60 seconds
        "expected_exception": Exception,
        "name": "PostgreSQL"
    }

    # Redis - Important but can fallback, moderate tolerance
    REDIS = {
        "fail_max": 5,
        "timeout_duration": 30,     # Shorter recovery time
        "expected_exception": Exception,
        "name": "Redis"
    }

    # InfluxDB - Time-series data, can tolerate some loss
    INFLUXDB = {
        "fail_max": 10,             # More tolerant
        "timeout_duration": 30,
        "expected_exception": Exception,
        "name": "InfluxDB"
    }

    # MQTT - Real-time messaging, moderate tolerance
    MQTT = {
        "fail_max": 5,
        "timeout_duration": 30,
        "expected_exception": Exception,
        "name": "MQTT"
    }

    # MinIO - Object storage, can tolerate failures
    MINIO = {
        "fail_max": 10,
        "timeout_duration": 60,
        "expected_exception": Exception,
        "name": "MinIO"
    }

    # External APIs - Third-party services, low tolerance
    EXTERNAL_API = {
        "fail_max": 3,              # Quick to open
        "timeout_duration": 120,    # Longer recovery time
        "expected_exception": Exception,
        "name": "ExternalAPI"
    }


# ===== CIRCUIT BREAKER MANAGER =====

class CircuitBreakerManager:
    """Manager for all circuit breakers in the application."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._fallback_handlers: Dict[str, Callable] = {}
        self._initialize_breakers()

    def _initialize_breakers(self):
        """Initialize circuit breakers for all services."""
        # PostgreSQL
        self._create_breaker(
            ServiceType.POSTGRESQL,
            CircuitBreakerConfig.POSTGRESQL
        )

        # Redis
        self._create_breaker(
            ServiceType.REDIS,
            CircuitBreakerConfig.REDIS
        )

        # InfluxDB
        self._create_breaker(
            ServiceType.INFLUXDB,
            CircuitBreakerConfig.INFLUXDB
        )

        # MQTT
        self._create_breaker(
            ServiceType.MQTT,
            CircuitBreakerConfig.MQTT
        )

        # MinIO
        self._create_breaker(
            ServiceType.MINIO,
            CircuitBreakerConfig.MINIO
        )

        # External API
        self._create_breaker(
            ServiceType.EXTERNAL_API,
            CircuitBreakerConfig.EXTERNAL_API
        )

        logger.info(f"Initialized {len(self._breakers)} circuit breakers")

    def _create_breaker(self, service_type: ServiceType, config: Dict[str, Any]) -> CircuitBreaker:
        """Create a circuit breaker with the given configuration."""
        listener = PrometheusCircuitBreakerListener(
            service_name=config["name"],
            service_type=service_type
        )

        breaker = CircuitBreaker(
            fail_max=config["fail_max"],
            reset_timeout=config["timeout_duration"],
            name=config["name"],
            listeners=[listener]
        )

        self._breakers[service_type.value] = breaker
        logger.info(f"Created circuit breaker for {service_type.value}: {config}")

        return breaker

    def get_breaker(self, service_type: ServiceType) -> CircuitBreaker:
        """Get circuit breaker for a service type."""
        return self._breakers.get(service_type.value)

    def register_fallback(self, service_type: ServiceType, fallback_handler: Callable):
        """Register a fallback handler for a service type."""
        self._fallback_handlers[service_type.value] = fallback_handler
        logger.info(f"Registered fallback handler for {service_type.value}")

    def get_fallback(self, service_type: ServiceType) -> Optional[Callable]:
        """Get fallback handler for a service type."""
        return self._fallback_handlers.get(service_type.value)

    def get_breaker_state(self, service_type: ServiceType) -> Dict[str, Any]:
        """Get current state of a circuit breaker."""
        breaker = self.get_breaker(service_type)
        if not breaker:
            return {"error": "Circuit breaker not found"}

        return {
            "service_type": service_type.value,
            "name": breaker.name,
            "state": breaker.current_state.lower() if isinstance(breaker.current_state, str) else breaker.current_state.name.lower(),
            "fail_counter": getattr(breaker, 'fail_counter', 0),
            "fail_max": getattr(breaker, 'fail_max', 5),
            "timeout_duration": getattr(breaker, 'timeout_duration', 60),
            "opened_at": getattr(breaker, 'opened_at', None).isoformat() if hasattr(breaker, 'opened_at') and getattr(breaker, 'opened_at', None) else None,
        }

    def get_all_breaker_states(self) -> Dict[str, Any]:
        """Get states of all circuit breakers."""
        return {
            service_type: self.get_breaker_state(ServiceType(service_type))
            for service_type in self._breakers.keys()
        }

    def reset_breaker(self, service_type: ServiceType):
        """Manually reset a circuit breaker."""
        breaker = self.get_breaker(service_type)
        if breaker:
            breaker.reset()
            logger.info(f"Circuit breaker reset: {service_type.value}")

    def reset_all_breakers(self):
        """Manually reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# Global circuit breaker manager instance
cb_manager = CircuitBreakerManager()


# ===== DECORATORS =====

def with_circuit_breaker(
    service_type: ServiceType,
    fallback_value: Any = None,
    use_fallback_handler: bool = True
):
    """
    Decorator to protect a function with a circuit breaker.

    Args:
        service_type: Type of service being protected
        fallback_value: Value to return if circuit is open (default: None)
        use_fallback_handler: Whether to use registered fallback handler (default: True)

    Example:
        @with_circuit_breaker(ServiceType.REDIS, fallback_value={})
        async def get_cached_data(key: str):
            return await redis.get(key)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = cb_manager.get_breaker(service_type)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            success = False

            try:
                # Try to call the function through circuit breaker
                result = await breaker.call_async(func, *args, **kwargs)
                success = True
                return result

            except pybreaker.CircuitBreakerError:
                # Circuit is open, try fallback
                circuit_breaker_rejections.labels(
                    service_name=breaker.name,
                    service_type=service_type.value
                ).inc()

                logger.warning(
                    f"Circuit breaker open for {service_type.value}, using fallback",
                    extra={
                        "service_type": service_type.value,
                        "function": func.__name__
                    }
                )

                # Try registered fallback handler first
                if use_fallback_handler:
                    fallback_handler = cb_manager.get_fallback(service_type)
                    if fallback_handler:
                        circuit_breaker_fallbacks.labels(
                            service_name=breaker.name,
                            service_type=service_type.value
                        ).inc()
                        return await fallback_handler(*args, **kwargs)

                # Use default fallback value
                circuit_breaker_fallbacks.labels(
                    service_name=breaker.name,
                    service_type=service_type.value
                ).inc()
                return fallback_value

            finally:
                # Record call duration
                duration = time.time() - start_time
                circuit_breaker_call_duration.labels(
                    service_name=breaker.name,
                    service_type=service_type.value,
                    success=str(success).lower()
                ).observe(duration)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            success = False

            try:
                # Try to call the function through circuit breaker
                result = breaker.call(func, *args, **kwargs)
                success = True
                return result

            except pybreaker.CircuitBreakerError:
                # Circuit is open, try fallback
                circuit_breaker_rejections.labels(
                    service_name=breaker.name,
                    service_type=service_type.value
                ).inc()

                logger.warning(
                    f"Circuit breaker open for {service_type.value}, using fallback"
                )

                # Try registered fallback handler first
                if use_fallback_handler:
                    fallback_handler = cb_manager.get_fallback(service_type)
                    if fallback_handler:
                        circuit_breaker_fallbacks.labels(
                            service_name=breaker.name,
                            service_type=service_type.value
                        ).inc()
                        return fallback_handler(*args, **kwargs)

                # Use default fallback value
                circuit_breaker_fallbacks.labels(
                    service_name=breaker.name,
                    service_type=service_type.value
                ).inc()
                return fallback_value

            finally:
                # Record call duration
                duration = time.time() - start_time
                circuit_breaker_call_duration.labels(
                    service_name=breaker.name,
                    service_type=service_type.value,
                    success=str(success).lower()
                ).observe(duration)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator


# ===== UTILITY FUNCTIONS =====

def get_circuit_breaker_stats() -> Dict[str, Any]:
    """Get comprehensive statistics for all circuit breakers."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "circuit_breakers": cb_manager.get_all_breaker_states(),
        "summary": {
            "total_breakers": len(cb_manager._breakers),
            "open_breakers": sum(
                1 for state in cb_manager.get_all_breaker_states().values()
                if state.get("state") == "open"
            ),
            "half_open_breakers": sum(
                1 for state in cb_manager.get_all_breaker_states().values()
                if state.get("state") == "half_open"
            ),
        }
    }


def is_circuit_healthy(service_type: ServiceType) -> bool:
    """Check if a circuit breaker is in healthy state (closed)."""
    state = cb_manager.get_breaker_state(service_type)
    return state.get("state") == "closed"


def are_all_circuits_healthy() -> bool:
    """Check if all circuit breakers are in healthy state."""
    return all(
        state.get("state") == "closed"
        for state in cb_manager.get_all_breaker_states().values()
    )


# ===== ENHANCED RETRY LOGIC WITH EXPONENTIAL BACKOFF =====


class RetryConfig:
    """Configuration for retry logic with exponential backoff and jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: List[Type[Exception]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on or [Exception]

    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            # Add jitter to prevent thundering herd problems
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)


class RetryState:
    """State tracking for retry attempts."""

    def __init__(self):
        self.attempts = 0
        self.last_exception = None


def with_retry(config: RetryConfig = None):
    """Decorator that adds retry logic with exponential backoff to functions."""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            state = RetryState()
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    if attempt > 0:
                        delay = config.get_delay(attempt - 1)
                        logger.warning(
                            f"Retrying {func.__name__} (attempt {attempt + 1}/{config.max_retries + 1}) "
                            f"after {delay:.2f}s delay. Last error: {str(last_exception)}"
                        )
                        await asyncio.sleep(delay)

                    # For async functions, check if it's an async generator
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        # For sync functions wrapped in async context
                        return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e
                    state.last_exception = e
                    state.attempts = attempt + 1

                    # Check if this exception type should be retried
                    should_retry = any(
                        isinstance(e, retry_type) for retry_type in config.retry_on
                    )

                    if not should_retry or attempt >= config.max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {attempt + 1} attempts. "
                            f"Final error: {str(e)}"
                        )
                        raise

                    # Log the retry attempt
                    logger.debug(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}"
                    )

            # This should never be reached, but just in case
            raise last_exception or RuntimeError("Unexpected error in retry logic")

        return async_wrapper

    return decorator


# Service-specific retry configurations for different use cases
DEFAULT_RETRY = RetryConfig(
    max_retries=3,
    base_delay=0.1,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)

AGGRESSIVE_RETRY = RetryConfig(
    max_retries=5,
    base_delay=0.5,
    max_delay=30.0,
    exponential_base=1.5,
    jitter=True
)

FAST_RETRY = RetryConfig(
    max_retries=2,
    base_delay=0.05,
    max_delay=2.0,
    exponential_base=2.0,
    jitter=False
)

# Network-related retry with more tolerance for transient issues
NETWORK_RETRY = RetryConfig(
    max_retries=5,
    base_delay=0.2,
    max_delay=15.0,
    exponential_base=2.0,
    jitter=True,
    retry_on=[ConnectionError, TimeoutError, OSError]
)

# Database retry with specific exception handling
DATABASE_RETRY = RetryConfig(
    max_retries=3,
    base_delay=0.1,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=True,
    retry_on=[ConnectionError, TimeoutError, OperationalError]
)


# ===== ENHANCED CIRCUIT BREAKER WITH RETRY DECORATORS =====

def with_circuit_breaker_and_retry(
    service_type: ServiceType,
    retry_config: RetryConfig = None
):
    """Combined decorator that applies both circuit breaker and retry logic."""
    circuit_decorator = with_circuit_breaker(service_type)
    retry_decorator = with_retry(retry_config or DEFAULT_RETRY)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        return retry_decorator(circuit_decorator(func))

    return decorator


# ===== PRE-CONFIGURED CIRCUIT BREAKER DECORATORS WITH RETRY =====

# Service-specific circuit breaker decorators with retry logic for easy use
postgresql_breaker = with_circuit_breaker(ServiceType.POSTGRESQL)
postgresql_breaker_with_retry = with_circuit_breaker_and_retry(ServiceType.POSTGRESQL, DATABASE_RETRY)

redis_breaker = with_circuit_breaker(ServiceType.REDIS)
redis_breaker_with_retry = with_circuit_breaker_and_retry(ServiceType.REDIS, FAST_RETRY)

influxdb_breaker = with_circuit_breaker(ServiceType.INFLUXDB)
influxdb_breaker_with_retry = with_circuit_breaker_and_retry(ServiceType.INFLUXDB, NETWORK_RETRY)

mqtt_breaker = with_circuit_breaker(ServiceType.MQTT)
mqtt_breaker_with_retry = with_circuit_breaker_and_retry(ServiceType.MQTT, FAST_RETRY)

minio_breaker = with_circuit_breaker(ServiceType.MINIO)
minio_breaker_with_retry = with_circuit_breaker_and_retry(ServiceType.MINIO, AGGRESSIVE_RETRY)

external_api_breaker = with_circuit_breaker(ServiceType.EXTERNAL_API)
external_api_breaker_with_retry = with_circuit_breaker_and_retry(ServiceType.EXTERNAL_API, AGGRESSIVE_RETRY)

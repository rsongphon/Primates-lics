"""
Prometheus Metrics for Celery Tasks

Exports Celery task metrics to Prometheus for monitoring and alerting.
Tracks task execution, failures, durations, and queue sizes.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from celery.signals import (
    task_prerun, task_postrun, task_failure, task_retry,
    task_success, task_revoked
)
from typing import Any, Dict
import time
import logging

logger = logging.getLogger(__name__)

# Task execution counters
task_total = Counter(
    'celery_task_total',
    'Total number of tasks executed',
    ['task_name', 'queue']
)

task_success_total = Counter(
    'celery_task_success_total',
    'Total number of successful tasks',
    ['task_name', 'queue']
)

task_failure_total = Counter(
    'celery_task_failure_total',
    'Total number of failed tasks',
    ['task_name', 'queue', 'exception']
)

task_retry_total = Counter(
    'celery_task_retry_total',
    'Total number of task retries',
    ['task_name', 'queue']
)

task_revoked_total = Counter(
    'celery_task_revoked_total',
    'Total number of revoked tasks',
    ['task_name']
)

# Task duration histogram
task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Task execution duration in seconds',
    ['task_name', 'queue'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

# Active tasks gauge
active_tasks = Gauge(
    'celery_active_tasks',
    'Number of currently active tasks',
    ['task_name', 'queue']
)

# Queue size gauge (updated periodically)
queue_size = Gauge(
    'celery_queue_size',
    'Number of tasks in queue',
    ['queue']
)

# Worker info
worker_info = Info(
    'celery_worker',
    'Celery worker information'
)

# Task timing storage (for duration calculation)
_task_start_times: Dict[str, float] = {}


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """
    Called before a task is executed.

    Records start time and increments active tasks counter.
    """
    try:
        task_name = sender.name if sender else "unknown"
        queue_name = task.request.delivery_info.get('routing_key', 'default') if task else 'default'

        # Record start time
        _task_start_times[task_id] = time.time()

        # Increment counters
        task_total.labels(task_name=task_name, queue=queue_name).inc()
        active_tasks.labels(task_name=task_name, queue=queue_name).inc()

        logger.debug(f"Task started: {task_name} [{task_id}] on queue {queue_name}")

    except Exception as e:
        logger.error(f"Error in task_prerun metrics handler: {e}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, **extra):
    """
    Called after a task is executed (success or failure).

    Records duration and decrements active tasks counter.
    """
    try:
        task_name = sender.name if sender else "unknown"
        queue_name = task.request.delivery_info.get('routing_key', 'default') if task else 'default'

        # Calculate duration
        start_time = _task_start_times.pop(task_id, None)
        if start_time:
            duration = time.time() - start_time
            task_duration_seconds.labels(task_name=task_name, queue=queue_name).observe(duration)

        # Decrement active tasks
        active_tasks.labels(task_name=task_name, queue=queue_name).dec()

        logger.debug(f"Task completed: {task_name} [{task_id}] on queue {queue_name}")

    except Exception as e:
        logger.error(f"Error in task_postrun metrics handler: {e}")


@task_success.connect
def task_success_handler(sender=None, result=None, **extra):
    """
    Called when a task succeeds.

    Increments success counter.
    """
    try:
        task_name = sender.name if sender else "unknown"
        # Get queue from task request if available
        queue_name = getattr(sender.request, 'delivery_info', {}).get('routing_key', 'default')

        task_success_total.labels(task_name=task_name, queue=queue_name).inc()

        logger.debug(f"Task succeeded: {task_name}")

    except Exception as e:
        logger.error(f"Error in task_success metrics handler: {e}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """
    Called when a task fails.

    Increments failure counter with exception type.
    """
    try:
        task_name = sender.name if sender else "unknown"
        queue_name = getattr(sender.request, 'delivery_info', {}).get('routing_key', 'default')
        exception_type = type(exception).__name__ if exception else "Unknown"

        task_failure_total.labels(
            task_name=task_name,
            queue=queue_name,
            exception=exception_type
        ).inc()

        logger.warning(f"Task failed: {task_name} [{task_id}] with {exception_type}")

    except Exception as e:
        logger.error(f"Error in task_failure metrics handler: {e}")


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **extra):
    """
    Called when a task is retried.

    Increments retry counter.
    """
    try:
        task_name = sender.name if sender else "unknown"
        queue_name = getattr(sender.request, 'delivery_info', {}).get('routing_key', 'default')

        task_retry_total.labels(task_name=task_name, queue=queue_name).inc()

        logger.info(f"Task retry: {task_name} [{task_id}] - Reason: {reason}")

    except Exception as e:
        logger.error(f"Error in task_retry metrics handler: {e}")


@task_revoked.connect
def task_revoked_handler(sender=None, request=None, terminated=None, signum=None, expired=None, **extra):
    """
    Called when a task is revoked.

    Increments revoked counter.
    """
    try:
        task_name = sender.name if sender else "unknown"

        task_revoked_total.labels(task_name=task_name).inc()

        logger.warning(f"Task revoked: {task_name} (terminated={terminated}, expired={expired})")

    except Exception as e:
        logger.error(f"Error in task_revoked metrics handler: {e}")


def update_queue_metrics(celery_app):
    """
    Update queue size metrics.

    This should be called periodically by a background thread or task.

    Args:
        celery_app: Celery application instance
    """
    try:
        inspector = celery_app.control.inspect()

        # Get scheduled tasks (this gives us queue sizes indirectly)
        scheduled = inspector.scheduled()
        if scheduled:
            for worker, tasks in scheduled.items():
                for task in tasks:
                    queue_name = task.get('delivery_info', {}).get('routing_key', 'default')
                    # Note: This is an approximation - real queue size requires Redis inspection
                    queue_size.labels(queue=queue_name).inc()

        # Note: For accurate queue sizes, we'd need to query Redis directly
        # using LLEN for each queue name

    except Exception as e:
        logger.error(f"Error updating queue metrics: {e}")


def register_worker_info(worker_name: str, worker_version: str, concurrency: int):
    """
    Register worker information.

    Args:
        worker_name: Name of the worker
        worker_version: Celery version
        concurrency: Worker concurrency setting
    """
    try:
        worker_info.info({
            'worker_name': worker_name,
            'celery_version': worker_version,
            'concurrency': str(concurrency)
        })

        logger.info(f"Registered worker: {worker_name} (v{worker_version}, concurrency={concurrency})")

    except Exception as e:
        logger.error(f"Error registering worker info: {e}")


# ===== INFRASTRUCTURE METRICS =====

# Session management metrics
active_sessions = Gauge(
    'lics_active_sessions_total',
    'Number of currently active user sessions',
    ['organization_id', 'user_type']
)

session_duration_seconds = Histogram(
    'lics_session_duration_seconds',
    'Session duration in seconds',
    ['organization_id'],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800]  # 1min to 8hrs
)

session_created_total = Counter(
    'lics_session_created_total',
    'Total number of sessions created',
    ['organization_id', 'user_type', 'auth_method']
)

session_expired_total = Counter(
    'lics_session_expired_total',
    'Total number of sessions expired',
    ['organization_id', 'reason']
)

# Authentication metrics
login_attempts_total = Counter(
    'lics_login_attempts_total',
    'Total number of login attempts',
    ['organization_id', 'result', 'auth_method']
)

authentication_duration_seconds = Histogram(
    'lics_authentication_duration_seconds',
    'Time taken to authenticate users',
    ['organization_id', 'auth_method', 'result'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

account_lockout_events_total = Counter(
    'lics_account_lockout_events_total',
    'Total number of account lockout events',
    ['organization_id']
)

password_reset_requests_total = Counter(
    'lics_password_reset_requests_total',
    'Total number of password reset requests',
    ['organization_id']
)

# Database connection pool metrics
db_pool_active_connections = Gauge(
    'lics_db_pool_active_connections',
    'Number of active database connections',
    ['pool_name']
)

db_pool_idle_connections = Gauge(
    'lics_db_pool_idle_connections',
    'Number of idle database connections',
    ['pool_name']
)

db_pool_total_connections = Gauge(
    'lics_db_pool_total_connections',
    'Total number of database connections',
    ['pool_name']
)

db_pool_overflow_connections = Gauge(
    'lics_db_pool_overflow_connections',
    'Number of overflow database connections',
    ['pool_name']
)

# API performance metrics
api_request_duration_seconds = Histogram(
    'lics_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint', 'status_code', 'organization_id'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

api_request_total = Counter(
    'lics_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code', 'organization_id']
)

# WebSocket metrics
websocket_connections_active = Gauge(
    'lics_websocket_connections_active',
    'Number of active WebSocket connections',
    ['organization_id', 'room_type']
)

websocket_messages_total = Counter(
    'lics_websocket_messages_total',
    'Total number of WebSocket messages',
    ['organization_id', 'room_type', 'message_type', 'direction']
)

# System resource metrics
system_memory_usage_bytes = Gauge(
    'lics_system_memory_usage_bytes',
    'System memory usage in bytes'
)

system_cpu_usage_percent = Gauge(
    'lics_system_cpu_usage_percent',
    'System CPU usage percentage'
)

import asyncio
from functools import wraps

def track_session_metrics(organization_id: str, user_type: str = "standard"):
    """
    Decorator to track session metrics.

    Usage:
    @track_session_metrics(organization_id="org123", user_type="premium")
    async def create_session(...):
        ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Track session creation
                session_created_total.labels(
                    organization_id=organization_id,
                    user_type=user_type,
                    auth_method="jwt"
                ).inc()

                # Increment active sessions
                active_sessions.labels(
                    organization_id=organization_id,
                    user_type=user_type
                ).inc()

                return result

            except Exception as e:
                login_attempts_total.labels(
                    organization_id=organization_id,
                    result="error",
                    auth_method="jwt"
                ).inc()
                raise

        return wrapper
    return decorator

def track_authentication_metrics(organization_id: str, auth_method: str = "jwt"):
    """
    Decorator to track authentication metrics.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = None

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Track successful authentication
                login_attempts_total.labels(
                    organization_id=organization_id,
                    result="success",
                    auth_method=auth_method
                ).inc()

                authentication_duration_seconds.labels(
                    organization_id=organization_id,
                    auth_method=auth_method,
                    result="success"
                ).observe(duration)

                return result

            except Exception as e:
                duration = time.time() - start_time

                # Track failed authentication
                login_attempts_total.labels(
                    organization_id=organization_id,
                    result="failure",
                    auth_method=auth_method
                ).inc()

                authentication_duration_seconds.labels(
                    organization_id=organization_id,
                    auth_method=auth_method,
                    result="failure"
                ).observe(duration)

                raise

        return wrapper
    return decorator

async def update_database_pool_metrics(pool_name: str = "default"):
    """
    Update database connection pool metrics.
    Should be called periodically to refresh pool statistics.
    """
    try:
        from app.core.database import db_manager

        if hasattr(db_manager, 'engine') and db_manager.engine:
            pool = db_manager.engine.pool

            if hasattr(pool, 'size'):
                db_pool_active_connections.labels(pool_name=pool_name).set(pool.checkedout)
                db_pool_idle_connections.labels(pool_name=pool_name).set(pool.size() - pool.checkedout)
                db_pool_total_connections.labels(pool_name=pool_name).set(pool.size)

                if hasattr(pool, 'overflow'):
                    db_pool_overflow_connections.labels(pool_name=pool_name).set(pool.overflow)

    except Exception as e:
        logger.error(f"Error updating database pool metrics: {e}")

async def update_system_metrics():
    """
    Update system resource metrics.
    Should be called periodically to refresh system statistics.
    """
    try:
        import psutil

        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage_bytes.set(memory.used)

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage_percent.set(cpu_percent)

    except ImportError:
        logger.warning("psutil not available for system metrics")
    except Exception as e:
        logger.error(f"Error updating system metrics: {e}")

# Initialize metrics on import
logger.info("LICS Infrastructure metrics initialized")

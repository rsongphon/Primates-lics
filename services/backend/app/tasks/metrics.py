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


# Initialize metrics on import
logger.info("Celery Prometheus metrics initialized")

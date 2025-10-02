"""
Celery Application Configuration for LICS Backend

Implements task queue architecture with Redis broker, multiple worker types,
task routing, and result backend configuration as per Documentation.md Section 5.3.
"""

import logging
from celery import Celery, Task
from celery.signals import task_failure, task_success, task_retry
from kombu import Exchange, Queue
from app.core.config import settings

logger = logging.getLogger(__name__)

# Import metrics module to register Prometheus signal handlers
try:
    from app.tasks import metrics as celery_metrics
    logger.info("Celery Prometheus metrics loaded successfully")
except ImportError as e:
    logger.warning(f"Prometheus metrics not available: {e}")
    celery_metrics = None

# Initialize Celery app
celery_app = Celery(
    "lics_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.data_processing",
        "app.tasks.notifications",
        "app.tasks.reports",
        "app.tasks.maintenance",
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Serialization
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=True,

    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    result_compression='gzip',

    # Worker
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    worker_send_task_events=True,

    # Events
    task_send_sent_event=True,

    # Broker
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,

    # Task routes - direct tasks to appropriate queues
    task_routes={
        # Data processing - heavy queue
        "app.tasks.data_processing.*": {"queue": "heavy"},

        # Notifications - real-time queue
        "app.tasks.notifications.*": {"queue": "real-time"},

        # Reports - heavy queue
        "app.tasks.reports.*": {"queue": "heavy"},

        # Maintenance - scheduled queue
        "app.tasks.maintenance.*": {"queue": "scheduled"},
    },

    # Queue definitions with priority support
    task_queues=(
        Queue(
            "default",
            Exchange("default"),
            routing_key="default",
            queue_arguments={"x-max-priority": 10}
        ),
        Queue(
            "heavy",
            Exchange("heavy"),
            routing_key="heavy",
            queue_arguments={"x-max-priority": 5}
        ),
        Queue(
            "real-time",
            Exchange("real-time"),
            routing_key="real-time",
            queue_arguments={"x-max-priority": 10}
        ),
        Queue(
            "scheduled",
            Exchange("scheduled"),
            routing_key="scheduled",
            queue_arguments={"x-max-priority": 3}
        ),
    ),

    # Default queue
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Beat schedule for periodic tasks
    beat_schedule={
        # Every 5 minutes: Device status updates
        'update-device-status': {
            'task': 'app.tasks.maintenance.update_device_status',
            'schedule': 300.0,  # 5 minutes
            'options': {'queue': 'scheduled'}
        },

        # Every 5 minutes: Session cleanup
        'cleanup-expired-sessions': {
            'task': 'app.tasks.maintenance.cleanup_expired_sessions',
            'schedule': 300.0,
            'options': {'queue': 'scheduled'}
        },

        # Every hour: Cache warming
        'refresh-cache-warmup': {
            'task': 'app.tasks.maintenance.refresh_cache_warmup',
            'schedule': 3600.0,  # 1 hour
            'options': {'queue': 'scheduled'}
        },

        # Every 6 hours: Data aggregation
        'process-experiment-analytics': {
            'task': 'app.tasks.data_processing.generate_analytics',
            'schedule': 21600.0,  # 6 hours
            'options': {'queue': 'heavy'}
        },

        # Daily at 1 AM: Database backup
        'backup-database': {
            'task': 'app.tasks.maintenance.backup_database_incremental',
            'schedule': {
                'hour': 1,
                'minute': 0
            },
            'options': {'queue': 'scheduled'}
        },

        # Daily at 2 AM: Data cleanup
        'cleanup-old-data': {
            'task': 'app.tasks.data_processing.cleanup_old_data',
            'schedule': {
                'hour': 2,
                'minute': 0
            },
            'options': {'queue': 'scheduled'}
        },

        # Daily at 6 AM: Generate organization summaries
        'generate-org-summaries': {
            'task': 'app.tasks.reports.generate_organization_summary',
            'schedule': {
                'hour': 6,
                'minute': 0
            },
            'options': {'queue': 'heavy'}
        },
    }
)


# Base task class with error handling
class BaseTask(Task):
    """
    Base task class with built-in error handling and retry logic.

    Implements exponential backoff, dead letter queue handling,
    and comprehensive error logging.
    """

    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max backoff
    retry_jitter = True  # Add randomness to retry delays

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            f"Task {self.name} failed",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
                "exception": str(exc),
                "traceback": str(einfo)
            }
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.warning(
            f"Task {self.name} retry",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "retry_count": self.request.retries,
                "exception": str(exc)
            }
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(
            f"Task {self.name} succeeded",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "result": str(retval)[:200]  # Truncate long results
            }
        )


# Set base task for all tasks
celery_app.Task = BaseTask


# Signal handlers for monitoring
@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Record task success metrics."""
    # This will be connected to Prometheus metrics
    pass


@task_failure.connect
def task_failure_handler(sender=None, exception=None, **kwargs):
    """Record task failure metrics and send notifications."""
    # This will trigger failure notifications
    pass


@task_retry.connect
def task_retry_handler(sender=None, reason=None, **kwargs):
    """Record task retry metrics."""
    # This will be connected to Prometheus metrics
    pass


# Helper function to get Celery app instance
def get_celery_app() -> Celery:
    """
    Get the configured Celery application instance.

    Returns:
        Celery application instance
    """
    return celery_app

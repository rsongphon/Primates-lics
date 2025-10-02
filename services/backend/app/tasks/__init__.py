"""
LICS Background Tasks Module

Provides Celery-based background task processing for:
- Data processing and aggregation
- Notifications (email, WebSocket, webhooks)
- Report generation (PDF, Excel, CSV)
- Maintenance and cleanup operations

Task Queue Structure:
- default: General background tasks
- heavy: Data processing, report generation
- real-time: Time-sensitive operations
- scheduled: Periodic tasks from Celery Beat
"""

from app.tasks.celery_app import celery_app, get_celery_app, BaseTask

__all__ = [
    "celery_app",
    "get_celery_app",
    "BaseTask",
]

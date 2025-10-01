"""
LICS WebSocket Event Handlers

Handler modules for different event types and namespaces.
"""

from app.websocket.handlers.device_handlers import register_device_handlers
from app.websocket.handlers.experiment_handlers import register_experiment_handlers
from app.websocket.handlers.task_handlers import register_task_handlers
from app.websocket.handlers.notification_handlers import register_notification_handlers

__all__ = [
    "register_device_handlers",
    "register_experiment_handlers",
    "register_task_handlers",
    "register_notification_handlers",
]

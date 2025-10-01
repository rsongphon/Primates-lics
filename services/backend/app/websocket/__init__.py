"""
LICS WebSocket Module

Real-time communication using Socket.IO with FastAPI.
Implements room-based messaging, JWT authentication, and event-driven architecture.
"""

from app.websocket.server import sio, app as websocket_app, get_sio_app
from app.websocket.events import (
    DeviceEvent,
    ExperimentEvent,
    TaskEvent,
    NotificationEvent,
    UserEvent,
)

__all__ = [
    "sio",
    "websocket_app",
    "get_sio_app",
    "DeviceEvent",
    "ExperimentEvent",
    "TaskEvent",
    "NotificationEvent",
    "UserEvent",
]

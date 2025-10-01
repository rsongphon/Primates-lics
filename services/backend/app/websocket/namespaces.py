"""
LICS WebSocket Namespaces

Socket.IO namespace definitions for different feature categories.
Follows Documentation.md Section 5.4 namespace patterns.
"""

import socketio
from typing import Dict, Any

from app.core.logging import get_logger
from app.websocket.events import (
    DeviceEvent,
    ExperimentEvent,
    TaskEvent,
    NotificationEvent,
    ConnectionEvent,
)

logger = get_logger(__name__)


class DeviceNamespace(socketio.AsyncNamespace):
    """
    Namespace for device-related WebSocket events.

    Handles device telemetry, status updates, and control commands.
    Namespace: /devices
    """

    async def on_connect(self, sid: str, environ: Dict[str, Any], auth: Dict[str, Any]):
        """Handle client connection to devices namespace."""
        logger.info(f"Client connected to /devices namespace: {sid}")
        # Authentication is handled in server middleware
        await self.emit(ConnectionEvent.AUTHENTICATED, {"sid": sid}, room=sid)

    async def on_disconnect(self, sid: str):
        """Handle client disconnection from devices namespace."""
        logger.info(f"Client disconnected from /devices namespace: {sid}")

    async def on_join_device(self, sid: str, data: Dict[str, Any]):
        """
        Join a specific device room for receiving device-specific updates.

        Args:
            sid: Socket session ID
            data: {"device_id": str}
        """
        device_id = data.get("device_id")
        if not device_id:
            await self.emit(ConnectionEvent.ERROR, {"message": "device_id required"}, room=sid)
            return

        room = f"device:{device_id}"
        await self.enter_room(sid, room)
        logger.info(f"Client {sid} joined device room: {room}")
        await self.emit(ConnectionEvent.ROOM_JOINED, {"room": room}, room=sid)

    async def on_leave_device(self, sid: str, data: Dict[str, Any]):
        """
        Leave a device room.

        Args:
            sid: Socket session ID
            data: {"device_id": str}
        """
        device_id = data.get("device_id")
        if not device_id:
            return

        room = f"device:{device_id}"
        await self.leave_room(sid, room)
        logger.info(f"Client {sid} left device room: {room}")
        await self.emit(ConnectionEvent.ROOM_LEFT, {"room": room}, room=sid)

    async def on_device_command(self, sid: str, data: Dict[str, Any]):
        """
        Send command to a device (placeholder for future implementation).

        Args:
            sid: Socket session ID
            data: {"device_id": str, "command": str, "params": dict}
        """
        logger.info(f"Device command received from {sid}: {data}")
        # This will be implemented when device control is added
        await self.emit(
            DeviceEvent.COMMAND_ACK,
            {"status": "received", "command_id": data.get("command_id")},
            room=sid
        )


class ExperimentNamespace(socketio.AsyncNamespace):
    """
    Namespace for experiment-related WebSocket events.

    Handles experiment lifecycle, participant updates, and data collection.
    Namespace: /experiments
    """

    async def on_connect(self, sid: str, environ: Dict[str, Any], auth: Dict[str, Any]):
        """Handle client connection to experiments namespace."""
        logger.info(f"Client connected to /experiments namespace: {sid}")
        await self.emit(ConnectionEvent.AUTHENTICATED, {"sid": sid}, room=sid)

    async def on_disconnect(self, sid: str):
        """Handle client disconnection from experiments namespace."""
        logger.info(f"Client disconnected from /experiments namespace: {sid}")

    async def on_join_experiment(self, sid: str, data: Dict[str, Any]):
        """
        Join a specific experiment room.

        Args:
            sid: Socket session ID
            data: {"experiment_id": str}
        """
        experiment_id = data.get("experiment_id")
        if not experiment_id:
            await self.emit(ConnectionEvent.ERROR, {"message": "experiment_id required"}, room=sid)
            return

        room = f"experiment:{experiment_id}"
        await self.enter_room(sid, room)
        logger.info(f"Client {sid} joined experiment room: {room}")
        await self.emit(ConnectionEvent.ROOM_JOINED, {"room": room}, room=sid)

    async def on_leave_experiment(self, sid: str, data: Dict[str, Any]):
        """
        Leave an experiment room.

        Args:
            sid: Socket session ID
            data: {"experiment_id": str}
        """
        experiment_id = data.get("experiment_id")
        if not experiment_id:
            return

        room = f"experiment:{experiment_id}"
        await self.leave_room(sid, room)
        logger.info(f"Client {sid} left experiment room: {room}")
        await self.emit(ConnectionEvent.ROOM_LEFT, {"room": room}, room=sid)


class TaskNamespace(socketio.AsyncNamespace):
    """
    Namespace for task-related WebSocket events.

    Handles task execution, progress updates, and status changes.
    Namespace: /tasks
    """

    async def on_connect(self, sid: str, environ: Dict[str, Any], auth: Dict[str, Any]):
        """Handle client connection to tasks namespace."""
        logger.info(f"Client connected to /tasks namespace: {sid}")
        await self.emit(ConnectionEvent.AUTHENTICATED, {"sid": sid}, room=sid)

    async def on_disconnect(self, sid: str):
        """Handle client disconnection from tasks namespace."""
        logger.info(f"Client disconnected from /tasks namespace: {sid}")

    async def on_join_task(self, sid: str, data: Dict[str, Any]):
        """
        Join a specific task execution room.

        Args:
            sid: Socket session ID
            data: {"task_id": str} or {"execution_id": str}
        """
        task_id = data.get("task_id")
        execution_id = data.get("execution_id")

        if execution_id:
            room = f"task:execution:{execution_id}"
        elif task_id:
            room = f"task:{task_id}"
        else:
            await self.emit(ConnectionEvent.ERROR, {"message": "task_id or execution_id required"}, room=sid)
            return

        await self.enter_room(sid, room)
        logger.info(f"Client {sid} joined task room: {room}")
        await self.emit(ConnectionEvent.ROOM_JOINED, {"room": room}, room=sid)

    async def on_leave_task(self, sid: str, data: Dict[str, Any]):
        """
        Leave a task room.

        Args:
            sid: Socket session ID
            data: {"task_id": str} or {"execution_id": str}
        """
        task_id = data.get("task_id")
        execution_id = data.get("execution_id")

        if execution_id:
            room = f"task:execution:{execution_id}"
        elif task_id:
            room = f"task:{task_id}"
        else:
            return

        await self.leave_room(sid, room)
        logger.info(f"Client {sid} left task room: {room}")
        await self.emit(ConnectionEvent.ROOM_LEFT, {"room": room}, room=sid)


class NotificationNamespace(socketio.AsyncNamespace):
    """
    Namespace for notification WebSocket events.

    Handles system notifications, alerts, and user-specific messages.
    Namespace: /notifications
    """

    async def on_connect(self, sid: str, environ: Dict[str, Any], auth: Dict[str, Any]):
        """Handle client connection to notifications namespace."""
        logger.info(f"Client connected to /notifications namespace: {sid}")
        await self.emit(ConnectionEvent.AUTHENTICATED, {"sid": sid}, room=sid)

    async def on_disconnect(self, sid: str):
        """Handle client disconnection from notifications namespace."""
        logger.info(f"Client disconnected from /notifications namespace: {sid}")

    async def on_join_user_room(self, sid: str, data: Dict[str, Any]):
        """
        Join user-specific notification room.

        Args:
            sid: Socket session ID
            data: {"user_id": str}
        """
        user_id = data.get("user_id")
        if not user_id:
            await self.emit(ConnectionEvent.ERROR, {"message": "user_id required"}, room=sid)
            return

        room = f"user:{user_id}"
        await self.enter_room(sid, room)
        logger.info(f"Client {sid} joined user notification room: {room}")
        await self.emit(ConnectionEvent.ROOM_JOINED, {"room": room}, room=sid)

    async def on_join_org_room(self, sid: str, data: Dict[str, Any]):
        """
        Join organization notification room.

        Args:
            sid: Socket session ID
            data: {"org_id": str}
        """
        org_id = data.get("org_id")
        if not org_id:
            await self.emit(ConnectionEvent.ERROR, {"message": "org_id required"}, room=sid)
            return

        room = f"org:{org_id}"
        await self.enter_room(sid, room)
        logger.info(f"Client {sid} joined org notification room: {room}")
        await self.emit(ConnectionEvent.ROOM_JOINED, {"room": room}, room=sid)

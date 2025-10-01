"""
LICS WebSocket Device Event Handlers

Handles real-time device events including telemetry, status updates, and commands.
Follows Documentation.md Section 5.4 device communication patterns.
"""

from typing import Dict, Any
from uuid import UUID

from app.websocket.server import sio
from app.websocket.events import DeviceEvent, Namespace
from app.websocket.rooms import room_manager
from app.websocket.session import session_manager
from app.websocket.auth import can_access_device
from app.core.logging import get_logger
from app.services.domain import DeviceService
from app.core.database import get_db_session

logger = get_logger(__name__)


def register_device_handlers():
    """Register all device-related WebSocket event handlers."""

    @sio.on(DeviceEvent.SUBSCRIBE, namespace=Namespace.DEVICES)
    async def handle_device_subscribe(sid: str, data: Dict[str, Any]):
        """
        Subscribe to device updates.

        Client sends: {"device_id": "uuid"}
        Server responds with acknowledgment
        """
        try:
            device_id = data.get("device_id")
            if not device_id:
                await sio.emit(
                    "error",
                    {"message": "device_id is required"},
                    room=sid,
                    namespace=Namespace.DEVICES
                )
                return

            # Get user from session
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                await sio.emit(
                    "error",
                    {"message": "Not authenticated"},
                    room=sid,
                    namespace=Namespace.DEVICES
                )
                return

            user = session_data["user"]

            # Check access permissions
            if not await can_access_device(user, device_id):
                await sio.emit(
                    "error",
                    {"message": "Access denied to device"},
                    room=sid,
                    namespace=Namespace.DEVICES
                )
                return

            # Join device room
            device_room = room_manager.device_room(device_id)
            await sio.enter_room(sid, device_room, namespace=Namespace.DEVICES)
            await room_manager.add_to_room(sid, device_room, user_id=str(user.id))

            logger.info(f"Client {sid} subscribed to device {device_id}")

            # Send acknowledgment
            await sio.emit(
                DeviceEvent.SUBSCRIBED,
                {
                    "device_id": device_id,
                    "message": "Successfully subscribed to device updates"
                },
                room=sid,
                namespace=Namespace.DEVICES
            )

            # Send current device status
            async with get_db_session() as session:
                device_service = DeviceService(session)
                device = await device_service.get_device(UUID(device_id))
                if device:
                    await sio.emit(
                        DeviceEvent.STATUS,
                        {
                            "device_id": device_id,
                            "status": device.status.value,
                            "last_seen": device.last_seen.isoformat() if device.last_seen else None
                        },
                        room=sid,
                        namespace=Namespace.DEVICES
                    )

        except Exception as e:
            logger.error(f"Error in device subscribe: {e}")
            await sio.emit(
                "error",
                {"message": "Failed to subscribe to device"},
                room=sid,
                namespace=Namespace.DEVICES
            )

    @sio.on(DeviceEvent.UNSUBSCRIBE, namespace=Namespace.DEVICES)
    async def handle_device_unsubscribe(sid: str, data: Dict[str, Any]):
        """
        Unsubscribe from device updates.

        Client sends: {"device_id": "uuid"}
        """
        try:
            device_id = data.get("device_id")
            if not device_id:
                return

            device_room = room_manager.device_room(device_id)
            await sio.leave_room(sid, device_room, namespace=Namespace.DEVICES)

            session_data = await session_manager.get_session(sid)
            if session_data and "user" in session_data:
                await room_manager.remove_from_room(
                    sid, device_room, user_id=str(session_data["user"].id)
                )

            logger.info(f"Client {sid} unsubscribed from device {device_id}")

            await sio.emit(
                "unsubscribed",
                {"device_id": device_id, "message": "Successfully unsubscribed"},
                room=sid,
                namespace=Namespace.DEVICES
            )

        except Exception as e:
            logger.error(f"Error in device unsubscribe: {e}")

    @sio.on(DeviceEvent.COMMAND, namespace=Namespace.DEVICES)
    async def handle_device_command(sid: str, data: Dict[str, Any]):
        """
        Send command to device.

        Client sends: {
            "device_id": "uuid",
            "command": "start_experiment",
            "parameters": {}
        }
        """
        try:
            device_id = data.get("device_id")
            command = data.get("command")
            parameters = data.get("parameters", {})

            if not device_id or not command:
                await sio.emit(
                    "error",
                    {"message": "device_id and command are required"},
                    room=sid,
                    namespace=Namespace.DEVICES
                )
                return

            # Get user from session
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                await sio.emit(
                    "error",
                    {"message": "Not authenticated"},
                    room=sid,
                    namespace=Namespace.DEVICES
                )
                return

            user = session_data["user"]

            # Check access permissions (commands require control permission)
            if not await can_access_device(user, device_id):
                await sio.emit(
                    "error",
                    {"message": "Access denied to control device"},
                    room=sid,
                    namespace=Namespace.DEVICES
                )
                return

            logger.info(f"Device command from {sid}: {command} on device {device_id}")

            # Emit command to device room (device agents listen here)
            device_room = room_manager.device_room(device_id)
            await sio.emit(
                DeviceEvent.COMMAND,
                {
                    "device_id": device_id,
                    "command": command,
                    "parameters": parameters,
                    "issued_by": str(user.id)
                },
                room=device_room,
                namespace=Namespace.DEVICES
            )

            # Send acknowledgment to sender
            await sio.emit(
                "command_sent",
                {
                    "device_id": device_id,
                    "command": command,
                    "message": "Command sent to device"
                },
                room=sid,
                namespace=Namespace.DEVICES
            )

        except Exception as e:
            logger.error(f"Error in device command: {e}")
            await sio.emit(
                "error",
                {"message": "Failed to send command to device"},
                room=sid,
                namespace=Namespace.DEVICES
            )

    @sio.on("request_telemetry", namespace=Namespace.DEVICES)
    async def handle_telemetry_request(sid: str, data: Dict[str, Any]):
        """
        Request latest telemetry data for a device.

        Client sends: {
            "device_id": "uuid",
            "metrics": ["temperature", "humidity"]  # Optional filter
        }
        """
        try:
            device_id = data.get("device_id")
            if not device_id:
                return

            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                return

            # TODO: Query latest telemetry from database or cache
            # For now, send a placeholder response

            await sio.emit(
                "telemetry_data",
                {
                    "device_id": device_id,
                    "timestamp": "2025-10-01T00:00:00Z",
                    "metrics": {}
                },
                room=sid,
                namespace=Namespace.DEVICES
            )

        except Exception as e:
            logger.error(f"Error in telemetry request: {e}")

    logger.info("Device WebSocket handlers registered")

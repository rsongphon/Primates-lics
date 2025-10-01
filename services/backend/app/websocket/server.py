"""
LICS WebSocket Server

Socket.IO server setup with Redis adapter for distributed scaling.
Follows Documentation.md Section 5.4 WebSocket architecture.
"""

import socketio
from fastapi import FastAPI
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.websocket.namespaces import (
    DeviceNamespace,
    ExperimentNamespace,
    TaskNamespace,
    NotificationNamespace,
)
from app.websocket.events import Namespace

logger = get_logger(__name__)

# Create Socket.IO server with async mode
# Redis manager for multi-server support and message broadcasting
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.BACKEND_CORS_ORIGINS if settings.BACKEND_CORS_ORIGINS else "*",
    logger=False,  # Use our structured logging instead
    engineio_logger=False,
    ping_interval=settings.WEBSOCKET_PING_INTERVAL,
    ping_timeout=settings.WEBSOCKET_PING_TIMEOUT,
    max_http_buffer_size=1000000,  # 1MB max message size
    # Redis manager for distributed Socket.IO (will be configured below)
    # client_manager=socketio.AsyncRedisManager(settings.REDIS_URL),
)

# Register namespaces
sio.register_namespace(DeviceNamespace(Namespace.DEVICES))
sio.register_namespace(ExperimentNamespace(Namespace.EXPERIMENTS))
sio.register_namespace(TaskNamespace(Namespace.TASKS))
sio.register_namespace(NotificationNamespace(Namespace.NOTIFICATIONS))


# ===== Connection Event Handlers (Default Namespace) =====

@sio.event
async def connect(sid: str, environ: dict, auth: Optional[dict] = None):
    """
    Handle client connection to default namespace.

    Args:
        sid: Socket session ID
        environ: WSGI environment
        auth: Authentication data
    """
    logger.info(f"Client connected: {sid}")

    # Extract connection info
    query_string = environ.get("QUERY_STRING", "")
    headers = environ.get("HTTP_USER_AGENT", "Unknown")

    # Store connection metadata
    await sio.save_session(sid, {
        "connected_at": socketio.time(),
        "user_agent": headers,
        "query": query_string,
        "authenticated": False,
    })

    # Send connection acknowledgment
    await sio.emit("connected", {"sid": sid, "message": "Connected to LICS WebSocket"}, room=sid)


@sio.event
async def disconnect(sid: str):
    """
    Handle client disconnection from default namespace.

    Args:
        sid: Socket session ID
    """
    try:
        # Get session data before cleanup
        session = await sio.get_session(sid)
        logger.info(f"Client disconnected: {sid}, Session: {session}")

        # Cleanup: Leave all rooms, clear session
        rooms = sio.rooms(sid)
        for room in rooms:
            if room != sid:  # Don't leave own sid room
                await sio.leave_room(sid, room)

    except KeyError:
        logger.warning(f"Session not found for disconnecting client: {sid}")
    except Exception as e:
        logger.error(f"Error during disconnect cleanup for {sid}: {e}")


@sio.event
async def ping(sid: str):
    """
    Handle ping event for connection health check.

    Args:
        sid: Socket session ID
    """
    await sio.emit("pong", {"timestamp": socketio.time()}, room=sid)


@sio.event
async def authenticate(sid: str, data: dict):
    """
    Handle authentication event (JWT validation will be added).

    Args:
        sid: Socket session ID
        data: {"token": str}
    """
    # Placeholder for authentication logic
    # Will be implemented in auth.py
    token = data.get("token")

    if not token:
        await sio.emit(
            "auth_error",
            {"message": "Token required for authentication"},
            room=sid
        )
        return

    # For now, just acknowledge (auth logic will be added)
    logger.info(f"Authentication request from {sid}")
    await sio.emit("authenticated", {"sid": sid, "message": "Authenticated"}, room=sid)


@sio.event
async def join_room(sid: str, data: dict):
    """
    Generic room join handler.

    Args:
        sid: Socket session ID
        data: {"room": str}
    """
    room = data.get("room")
    if not room:
        await sio.emit("error", {"message": "Room name required"}, room=sid)
        return

    await sio.enter_room(sid, room)
    logger.info(f"Client {sid} joined room: {room}")
    await sio.emit("room_joined", {"room": room}, room=sid)


@sio.event
async def leave_room(sid: str, data: dict):
    """
    Generic room leave handler.

    Args:
        sid: Socket session ID
        data: {"room": str}
    """
    room = data.get("room")
    if not room:
        return

    await sio.leave_room(sid, room)
    logger.info(f"Client {sid} left room: {room}")
    await sio.emit("room_left", {"room": room}, room=sid)


# ===== Event Handler Registration =====

def register_all_handlers():
    """Register all WebSocket event handlers."""
    from app.websocket.handlers import (
        register_device_handlers,
        register_experiment_handlers,
        register_task_handlers,
        register_notification_handlers,
    )

    register_device_handlers()
    register_experiment_handlers()
    register_task_handlers()
    register_notification_handlers()

    logger.info("All WebSocket event handlers registered")


# ===== WebSocket App Initialization =====

def get_sio_app() -> FastAPI:
    """
    Create and configure Socket.IO ASGI application.

    Returns:
        FastAPI app with Socket.IO integration
    """
    # Register all event handlers
    register_all_handlers()

    # Create Socket.IO ASGI app
    socket_app = socketio.ASGIApp(
        socketio_server=sio,
        socketio_path="socket.io",
    )

    logger.info("Socket.IO server initialized")
    logger.info(f"Registered namespaces: {Namespace.DEVICES}, {Namespace.EXPERIMENTS}, {Namespace.TASKS}, {Namespace.NOTIFICATIONS}")
    logger.info(f"CORS origins: {settings.BACKEND_CORS_ORIGINS if settings.BACKEND_CORS_ORIGINS else '*'}")
    logger.info(f"Ping interval: {settings.WEBSOCKET_PING_INTERVAL}s")
    logger.info(f"Ping timeout: {settings.WEBSOCKET_PING_TIMEOUT}s")

    return socket_app


# Create the Socket.IO app
app = get_sio_app()


# ===== Helper Functions for Event Emission =====

async def emit_to_device(device_id: str, event: str, data: dict):
    """
    Emit event to a specific device room.

    Args:
        device_id: Device identifier
        event: Event name
        data: Event payload
    """
    room = f"device:{device_id}"
    await sio.emit(event, data, room=room, namespace=Namespace.DEVICES)
    logger.debug(f"Emitted {event} to device room: {room}")


async def emit_to_experiment(experiment_id: str, event: str, data: dict):
    """
    Emit event to a specific experiment room.

    Args:
        experiment_id: Experiment identifier
        event: Event name
        data: Event payload
    """
    room = f"experiment:{experiment_id}"
    await sio.emit(event, data, room=room, namespace=Namespace.EXPERIMENTS)
    logger.debug(f"Emitted {event} to experiment room: {room}")


async def emit_to_task(task_id: str, event: str, data: dict):
    """
    Emit event to a specific task room.

    Args:
        task_id: Task identifier
        event: Event name
        data: Event payload
    """
    room = f"task:{task_id}"
    await sio.emit(event, data, room=room, namespace=Namespace.TASKS)
    logger.debug(f"Emitted {event} to task room: {room}")


async def emit_to_user(user_id: str, event: str, data: dict):
    """
    Emit event to a specific user room.

    Args:
        user_id: User identifier
        event: Event name
        data: Event payload
    """
    room = f"user:{user_id}"
    await sio.emit(event, data, room=room, namespace=Namespace.NOTIFICATIONS)
    logger.debug(f"Emitted {event} to user room: {room}")


async def emit_to_organization(org_id: str, event: str, data: dict):
    """
    Emit event to an organization room.

    Args:
        org_id: Organization identifier
        event: Event name
        data: Event payload
    """
    room = f"org:{org_id}"
    await sio.emit(event, data, room=room, namespace=Namespace.NOTIFICATIONS)
    logger.debug(f"Emitted {event} to organization room: {room}")


async def broadcast_event(event: str, data: dict, namespace: str = Namespace.DEFAULT):
    """
    Broadcast event to all connected clients in a namespace.

    Args:
        event: Event name
        data: Event payload
        namespace: Socket.IO namespace
    """
    await sio.emit(event, data, namespace=namespace)
    logger.debug(f"Broadcasted {event} to namespace: {namespace}")

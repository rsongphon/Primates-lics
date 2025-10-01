"""
LICS WebSocket Notification Event Handlers

Handles real-time notifications including system alerts and user notifications.
Follows Documentation.md Section 5.4 notification patterns.
"""

from typing import Dict, Any

from app.websocket.server import sio
from app.websocket.events import NotificationEvent, UserEvent, Namespace
from app.websocket.rooms import room_manager
from app.websocket.session import session_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


def register_notification_handlers():
    """Register all notification-related WebSocket event handlers."""

    @sio.on("subscribe_notifications", namespace=Namespace.NOTIFICATIONS)
    async def handle_notification_subscribe(sid: str, data: Dict[str, Any]):
        """
        Subscribe to user-specific notifications.

        Client sends: {} (user identified from session)
        Server responds with acknowledgment
        """
        try:
            # Get user from session
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                await sio.emit(
                    "error",
                    {"message": "Not authenticated"},
                    room=sid,
                    namespace=Namespace.NOTIFICATIONS
                )
                return

            user = session_data["user"]
            user_id = str(user.id)

            # Join user notification room
            user_room = room_manager.user_room(user_id)
            await sio.enter_room(sid, user_room, namespace=Namespace.NOTIFICATIONS)
            await room_manager.add_to_room(sid, user_room, user_id=user_id)

            logger.info(f"Client {sid} subscribed to notifications for user {user_id}")

            # Send acknowledgment
            await sio.emit(
                "subscribed",
                {
                    "user_id": user_id,
                    "message": "Successfully subscribed to notifications"
                },
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

            # TODO: Send any unread notifications
            # For now, send empty list

            await sio.emit(
                "unread_notifications",
                {
                    "count": 0,
                    "notifications": []
                },
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

        except Exception as e:
            logger.error(f"Error in notification subscribe: {e}")
            await sio.emit(
                "error",
                {"message": "Failed to subscribe to notifications"},
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

    @sio.on("unsubscribe_notifications", namespace=Namespace.NOTIFICATIONS)
    async def handle_notification_unsubscribe(sid: str, data: Dict[str, Any]):
        """
        Unsubscribe from notifications.

        Client sends: {}
        """
        try:
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                return

            user_id = str(session_data["user"].id)
            user_room = room_manager.user_room(user_id)
            await sio.leave_room(sid, user_room, namespace=Namespace.NOTIFICATIONS)
            await room_manager.remove_from_room(sid, user_room, user_id=user_id)

            logger.info(f"Client {sid} unsubscribed from notifications")

            await sio.emit(
                "unsubscribed",
                {"message": "Successfully unsubscribed from notifications"},
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

        except Exception as e:
            logger.error(f"Error in notification unsubscribe: {e}")

    @sio.on("mark_read", namespace=Namespace.NOTIFICATIONS)
    async def handle_mark_read(sid: str, data: Dict[str, Any]):
        """
        Mark notification as read.

        Client sends: {"notification_id": "uuid"}
        """
        try:
            notification_id = data.get("notification_id")
            if not notification_id:
                return

            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                return

            # TODO: Update notification read status in database
            logger.info(f"Notification {notification_id} marked as read by {sid}")

            await sio.emit(
                "notification_marked_read",
                {"notification_id": notification_id},
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

        except Exception as e:
            logger.error(f"Error in mark read: {e}")

    @sio.on("mark_all_read", namespace=Namespace.NOTIFICATIONS)
    async def handle_mark_all_read(sid: str, data: Dict[str, Any]):
        """
        Mark all notifications as read.

        Client sends: {}
        """
        try:
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                return

            user_id = str(session_data["user"].id)

            # TODO: Update all notification read status in database
            logger.info(f"All notifications marked as read for user {user_id}")

            await sio.emit(
                "all_notifications_marked_read",
                {"message": "All notifications marked as read"},
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

        except Exception as e:
            logger.error(f"Error in mark all read: {e}")

    @sio.on("subscribe_organization", namespace=Namespace.NOTIFICATIONS)
    async def handle_organization_subscribe(sid: str, data: Dict[str, Any]):
        """
        Subscribe to organization-wide broadcasts.

        Client sends: {"organization_id": "uuid"}
        """
        try:
            organization_id = data.get("organization_id")
            if not organization_id:
                await sio.emit(
                    "error",
                    {"message": "organization_id is required"},
                    room=sid,
                    namespace=Namespace.NOTIFICATIONS
                )
                return

            # Get user from session
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                await sio.emit(
                    "error",
                    {"message": "Not authenticated"},
                    room=sid,
                    namespace=Namespace.NOTIFICATIONS
                )
                return

            user = session_data["user"]
            user_org_id = str(user.organization_id) if hasattr(user, "organization_id") else None

            # Check if user belongs to organization
            if user_org_id != organization_id:
                await sio.emit(
                    "error",
                    {"message": "Access denied to organization"},
                    room=sid,
                    namespace=Namespace.NOTIFICATIONS
                )
                return

            # Join organization room
            org_room = room_manager.organization_room(organization_id)
            await sio.enter_room(sid, org_room, namespace=Namespace.NOTIFICATIONS)
            await room_manager.add_to_room(sid, org_room, user_id=str(user.id))

            logger.info(f"Client {sid} subscribed to organization {organization_id}")

            await sio.emit(
                "subscribed",
                {
                    "organization_id": organization_id,
                    "message": "Successfully subscribed to organization updates"
                },
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

        except Exception as e:
            logger.error(f"Error in organization subscribe: {e}")
            await sio.emit(
                "error",
                {"message": "Failed to subscribe to organization"},
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

    @sio.on("unsubscribe_organization", namespace=Namespace.NOTIFICATIONS)
    async def handle_organization_unsubscribe(sid: str, data: Dict[str, Any]):
        """
        Unsubscribe from organization broadcasts.

        Client sends: {"organization_id": "uuid"}
        """
        try:
            organization_id = data.get("organization_id")
            if not organization_id:
                return

            org_room = room_manager.organization_room(organization_id)
            await sio.leave_room(sid, org_room, namespace=Namespace.NOTIFICATIONS)

            session_data = await session_manager.get_session(sid)
            if session_data and "user" in session_data:
                await room_manager.remove_from_room(
                    sid, org_room, user_id=str(session_data["user"].id)
                )

            logger.info(f"Client {sid} unsubscribed from organization {organization_id}")

            await sio.emit(
                "unsubscribed",
                {"organization_id": organization_id, "message": "Successfully unsubscribed"},
                room=sid,
                namespace=Namespace.NOTIFICATIONS
            )

        except Exception as e:
            logger.error(f"Error in organization unsubscribe: {e}")

    logger.info("Notification WebSocket handlers registered")

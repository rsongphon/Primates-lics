"""
LICS WebSocket Task Event Handlers

Handles real-time task execution events and progress tracking.
Follows Documentation.md Section 5.4 task execution patterns.
"""

from typing import Dict, Any
from uuid import UUID

from app.websocket.server import sio
from app.websocket.events import TaskEvent, Namespace
from app.websocket.rooms import room_manager
from app.websocket.session import session_manager
from app.websocket.auth import can_access_task
from app.core.logging import get_logger
from app.services.domain import TaskService
from app.core.database import get_db_session

logger = get_logger(__name__)


def register_task_handlers():
    """Register all task-related WebSocket event handlers."""

    @sio.on(TaskEvent.SUBSCRIBE_EXECUTION, namespace=Namespace.TASKS)
    async def handle_task_execution_subscribe(sid: str, data: Dict[str, Any]):
        """
        Subscribe to task execution updates.

        Client sends: {"execution_id": "uuid"}
        Server responds with acknowledgment and current state
        """
        try:
            execution_id = data.get("execution_id")
            if not execution_id:
                await sio.emit(
                    "error",
                    {"message": "execution_id is required"},
                    room=sid,
                    namespace=Namespace.TASKS
                )
                return

            # Get user from session
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                await sio.emit(
                    "error",
                    {"message": "Not authenticated"},
                    room=sid,
                    namespace=Namespace.TASKS
                )
                return

            user = session_data["user"]

            # TODO: Check if user has access to this task execution
            # For now, allow all authenticated users

            # Join task execution room
            execution_room = room_manager.task_execution_room(execution_id)
            await sio.enter_room(sid, execution_room, namespace=Namespace.TASKS)
            await room_manager.add_to_room(sid, execution_room, user_id=str(user.id))

            logger.info(f"Client {sid} subscribed to task execution {execution_id}")

            # Send acknowledgment
            await sio.emit(
                "subscribed",
                {
                    "execution_id": execution_id,
                    "message": "Successfully subscribed to task execution updates"
                },
                room=sid,
                namespace=Namespace.TASKS
            )

            # TODO: Send current execution status from database
            # For now, send a placeholder

        except Exception as e:
            logger.error(f"Error in task execution subscribe: {e}")
            await sio.emit(
                "error",
                {"message": "Failed to subscribe to task execution"},
                room=sid,
                namespace=Namespace.TASKS
            )

    @sio.on(TaskEvent.UNSUBSCRIBE_EXECUTION, namespace=Namespace.TASKS)
    async def handle_task_execution_unsubscribe(sid: str, data: Dict[str, Any]):
        """
        Unsubscribe from task execution updates.

        Client sends: {"execution_id": "uuid"}
        """
        try:
            execution_id = data.get("execution_id")
            if not execution_id:
                return

            execution_room = room_manager.task_execution_room(execution_id)
            await sio.leave_room(sid, execution_room, namespace=Namespace.TASKS)

            session_data = await session_manager.get_session(sid)
            if session_data and "user" in session_data:
                await room_manager.remove_from_room(
                    sid, execution_room, user_id=str(session_data["user"].id)
                )

            logger.info(f"Client {sid} unsubscribed from task execution {execution_id}")

            await sio.emit(
                "unsubscribed",
                {"execution_id": execution_id, "message": "Successfully unsubscribed"},
                room=sid,
                namespace=Namespace.TASKS
            )

        except Exception as e:
            logger.error(f"Error in task execution unsubscribe: {e}")

    @sio.on("subscribe_task", namespace=Namespace.TASKS)
    async def handle_task_subscribe(sid: str, data: Dict[str, Any]):
        """
        Subscribe to all executions of a specific task.

        Client sends: {"task_id": "uuid"}
        """
        try:
            task_id = data.get("task_id")
            if not task_id:
                await sio.emit(
                    "error",
                    {"message": "task_id is required"},
                    room=sid,
                    namespace=Namespace.TASKS
                )
                return

            # Get user from session
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                await sio.emit(
                    "error",
                    {"message": "Not authenticated"},
                    room=sid,
                    namespace=Namespace.TASKS
                )
                return

            user = session_data["user"]

            # Check access permissions
            if not await can_access_task(user, task_id):
                await sio.emit(
                    "error",
                    {"message": "Access denied to task"},
                    room=sid,
                    namespace=Namespace.TASKS
                )
                return

            # Join task room
            task_room = room_manager.task_room(task_id)
            await sio.enter_room(sid, task_room, namespace=Namespace.TASKS)
            await room_manager.add_to_room(sid, task_room, user_id=str(user.id))

            logger.info(f"Client {sid} subscribed to task {task_id}")

            # Send acknowledgment
            await sio.emit(
                "subscribed",
                {
                    "task_id": task_id,
                    "message": "Successfully subscribed to task updates"
                },
                room=sid,
                namespace=Namespace.TASKS
            )

        except Exception as e:
            logger.error(f"Error in task subscribe: {e}")
            await sio.emit(
                "error",
                {"message": "Failed to subscribe to task"},
                room=sid,
                namespace=Namespace.TASKS
            )

    @sio.on("unsubscribe_task", namespace=Namespace.TASKS)
    async def handle_task_unsubscribe(sid: str, data: Dict[str, Any]):
        """
        Unsubscribe from task updates.

        Client sends: {"task_id": "uuid"}
        """
        try:
            task_id = data.get("task_id")
            if not task_id:
                return

            task_room = room_manager.task_room(task_id)
            await sio.leave_room(sid, task_room, namespace=Namespace.TASKS)

            session_data = await session_manager.get_session(sid)
            if session_data and "user" in session_data:
                await room_manager.remove_from_room(
                    sid, task_room, user_id=str(session_data["user"].id)
                )

            logger.info(f"Client {sid} unsubscribed from task {task_id}")

            await sio.emit(
                "unsubscribed",
                {"task_id": task_id, "message": "Successfully unsubscribed"},
                room=sid,
                namespace=Namespace.TASKS
            )

        except Exception as e:
            logger.error(f"Error in task unsubscribe: {e}")

    @sio.on("request_execution_history", namespace=Namespace.TASKS)
    async def handle_execution_history_request(sid: str, data: Dict[str, Any]):
        """
        Request execution history for a task.

        Client sends: {
            "task_id": "uuid",
            "limit": 10  # Optional
        }
        """
        try:
            task_id = data.get("task_id")
            limit = data.get("limit", 10)

            if not task_id:
                return

            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                return

            user = session_data["user"]

            if not await can_access_task(user, task_id):
                return

            # TODO: Query execution history from database
            # For now, send a placeholder response

            await sio.emit(
                "execution_history",
                {
                    "task_id": task_id,
                    "executions": []
                },
                room=sid,
                namespace=Namespace.TASKS
            )

        except Exception as e:
            logger.error(f"Error in execution history request: {e}")

    logger.info("Task WebSocket handlers registered")

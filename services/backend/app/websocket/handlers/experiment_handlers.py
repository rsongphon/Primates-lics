"""
LICS WebSocket Experiment Event Handlers

Handles real-time experiment events including lifecycle changes and progress updates.
Follows Documentation.md Section 5.4 experiment communication patterns.
"""

from typing import Dict, Any
from uuid import UUID

from app.websocket.server import sio
from app.websocket.events import ExperimentEvent, Namespace
from app.websocket.rooms import room_manager
from app.websocket.session import session_manager
from app.websocket.auth import can_access_experiment
from app.core.logging import get_logger
from app.services.domain import ExperimentService
from app.core.database import get_db_session

logger = get_logger(__name__)


def register_experiment_handlers():
    """Register all experiment-related WebSocket event handlers."""

    @sio.on(ExperimentEvent.SUBSCRIBE, namespace=Namespace.EXPERIMENTS)
    async def handle_experiment_subscribe(sid: str, data: Dict[str, Any]):
        """
        Subscribe to experiment updates.

        Client sends: {"experiment_id": "uuid"}
        Server responds with acknowledgment and current state
        """
        try:
            experiment_id = data.get("experiment_id")
            if not experiment_id:
                await sio.emit(
                    "error",
                    {"message": "experiment_id is required"},
                    room=sid,
                    namespace=Namespace.EXPERIMENTS
                )
                return

            # Get user from session
            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                await sio.emit(
                    "error",
                    {"message": "Not authenticated"},
                    room=sid,
                    namespace=Namespace.EXPERIMENTS
                )
                return

            user = session_data["user"]

            # Check access permissions
            if not await can_access_experiment(user, experiment_id):
                await sio.emit(
                    "error",
                    {"message": "Access denied to experiment"},
                    room=sid,
                    namespace=Namespace.EXPERIMENTS
                )
                return

            # Join experiment room
            experiment_room = room_manager.experiment_room(experiment_id)
            await sio.enter_room(sid, experiment_room, namespace=Namespace.EXPERIMENTS)
            await room_manager.add_to_room(sid, experiment_room, user_id=str(user.id))

            logger.info(f"Client {sid} subscribed to experiment {experiment_id}")

            # Send acknowledgment
            await sio.emit(
                "subscribed",
                {
                    "experiment_id": experiment_id,
                    "message": "Successfully subscribed to experiment updates"
                },
                room=sid,
                namespace=Namespace.EXPERIMENTS
            )

            # Send current experiment status
            async with get_db_session() as session:
                experiment_service = ExperimentService(session)
                experiment = await experiment_service.get_experiment(UUID(experiment_id))
                if experiment:
                    await sio.emit(
                        ExperimentEvent.STATE_CHANGE,
                        {
                            "experiment_id": experiment_id,
                            "state": experiment.status.value,
                            "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
                            "completed_at": experiment.completed_at.isoformat() if experiment.completed_at else None
                        },
                        room=sid,
                        namespace=Namespace.EXPERIMENTS
                    )

        except Exception as e:
            logger.error(f"Error in experiment subscribe: {e}")
            await sio.emit(
                "error",
                {"message": "Failed to subscribe to experiment"},
                room=sid,
                namespace=Namespace.EXPERIMENTS
            )

    @sio.on(ExperimentEvent.UNSUBSCRIBE, namespace=Namespace.EXPERIMENTS)
    async def handle_experiment_unsubscribe(sid: str, data: Dict[str, Any]):
        """
        Unsubscribe from experiment updates.

        Client sends: {"experiment_id": "uuid"}
        """
        try:
            experiment_id = data.get("experiment_id")
            if not experiment_id:
                return

            experiment_room = room_manager.experiment_room(experiment_id)
            await sio.leave_room(sid, experiment_room, namespace=Namespace.EXPERIMENTS)

            session_data = await session_manager.get_session(sid)
            if session_data and "user" in session_data:
                await room_manager.remove_from_room(
                    sid, experiment_room, user_id=str(session_data["user"].id)
                )

            logger.info(f"Client {sid} unsubscribed from experiment {experiment_id}")

            await sio.emit(
                "unsubscribed",
                {"experiment_id": experiment_id, "message": "Successfully unsubscribed"},
                room=sid,
                namespace=Namespace.EXPERIMENTS
            )

        except Exception as e:
            logger.error(f"Error in experiment unsubscribe: {e}")

    @sio.on("request_progress", namespace=Namespace.EXPERIMENTS)
    async def handle_progress_request(sid: str, data: Dict[str, Any]):
        """
        Request current experiment progress.

        Client sends: {"experiment_id": "uuid"}
        """
        try:
            experiment_id = data.get("experiment_id")
            if not experiment_id:
                return

            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                return

            user = session_data["user"]

            if not await can_access_experiment(user, experiment_id):
                return

            # TODO: Calculate actual progress from task executions
            # For now, send a placeholder response

            await sio.emit(
                ExperimentEvent.PROGRESS,
                {
                    "experiment_id": experiment_id,
                    "progress_percentage": 0.0,
                    "current_step": "Initializing",
                    "estimated_completion": None
                },
                room=sid,
                namespace=Namespace.EXPERIMENTS
            )

        except Exception as e:
            logger.error(f"Error in progress request: {e}")

    @sio.on("request_participants", namespace=Namespace.EXPERIMENTS)
    async def handle_participants_request(sid: str, data: Dict[str, Any]):
        """
        Request experiment participants list.

        Client sends: {"experiment_id": "uuid"}
        """
        try:
            experiment_id = data.get("experiment_id")
            if not experiment_id:
                return

            session_data = await session_manager.get_session(sid)
            if not session_data or "user" not in session_data:
                return

            user = session_data["user"]

            if not await can_access_experiment(user, experiment_id):
                return

            async with get_db_session() as session:
                experiment_service = ExperimentService(session)
                participants = await experiment_service.get_experiment_participants(
                    UUID(experiment_id)
                )

                await sio.emit(
                    "participants_list",
                    {
                        "experiment_id": experiment_id,
                        "participants": [
                            {
                                "id": str(p.id),
                                "subject_id": p.subject_id,
                                "status": p.status.value
                            }
                            for p in participants
                        ]
                    },
                    room=sid,
                    namespace=Namespace.EXPERIMENTS
                )

        except Exception as e:
            logger.error(f"Error in participants request: {e}")

    logger.info("Experiment WebSocket handlers registered")

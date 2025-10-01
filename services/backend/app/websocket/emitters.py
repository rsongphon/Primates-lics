"""
LICS WebSocket Event Emitters

Utility functions for emitting WebSocket events with proper schemas and routing.
Follows Documentation.md Section 5.4 event emission patterns.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from app.websocket.server import sio
from app.websocket.events import (
    DeviceEvent,
    ExperimentEvent,
    TaskEvent,
    NotificationEvent,
    UserEvent,
    Namespace,
)
from app.websocket.rooms import room_manager
from app.core.logging import get_logger
from app.schemas.websocket import (
    DeviceTelemetrySchema,
    DeviceStatusSchema,
    DeviceHeartbeatSchema,
    ExperimentLifecycleSchema,
    ExperimentProgressSchema,
    ExperimentDataCollectedSchema,
    TaskExecutionStartedSchema,
    TaskExecutionProgressSchema,
    TaskExecutionCompletedSchema,
    SystemNotificationSchema,
    UserNotificationSchema,
    AlertNotificationSchema,
    UserPresenceSchema,
)

logger = get_logger(__name__)


# ===== Device Event Emitters =====

async def emit_device_telemetry(
    device_id: UUID,
    metric: str,
    value: float,
    unit: Optional[str] = None,
    tags: Optional[Dict[str, Any]] = None
):
    """Emit device telemetry event."""
    schema = DeviceTelemetrySchema(
        device_id=device_id,
        metric=metric,
        value=value,
        unit=unit,
        tags=tags
    )
    room = room_manager.device_room(str(device_id))
    await sio.emit(DeviceEvent.TELEMETRY, schema.model_dump(), room=room, namespace=Namespace.DEVICES)


async def emit_device_status(
    device_id: UUID,
    status: str,
    previous_status: Optional[str] = None,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Emit device status change event."""
    schema = DeviceStatusSchema(
        device_id=device_id,
        status=status,
        previous_status=previous_status,
        reason=reason,
        metadata=metadata
    )
    room = room_manager.device_room(str(device_id))
    await sio.emit(DeviceEvent.STATUS, schema.model_dump(), room=room, namespace=Namespace.DEVICES)


async def emit_device_heartbeat(
    device_id: UUID,
    health_status: str,
    cpu_usage: Optional[float] = None,
    memory_usage: Optional[float] = None,
    disk_usage: Optional[float] = None,
    uptime: Optional[int] = None
):
    """Emit device heartbeat event."""
    schema = DeviceHeartbeatSchema(
        device_id=device_id,
        health_status=health_status,
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        disk_usage=disk_usage,
        uptime=uptime
    )
    room = room_manager.device_room(str(device_id))
    await sio.emit(DeviceEvent.HEARTBEAT, schema.model_dump(), room=room, namespace=Namespace.DEVICES)


# ===== Experiment Event Emitters =====

async def emit_experiment_lifecycle(
    experiment_id: UUID,
    state: str,
    previous_state: Optional[str] = None,
    triggered_by: Optional[UUID] = None,
    reason: Optional[str] = None
):
    """Emit experiment lifecycle event."""
    schema = ExperimentLifecycleSchema(
        experiment_id=experiment_id,
        state=state,
        previous_state=previous_state,
        triggered_by=triggered_by,
        reason=reason
    )
    room = room_manager.experiment_room(str(experiment_id))
    await sio.emit(ExperimentEvent.STATE_CHANGE, schema.model_dump(), room=room, namespace=Namespace.EXPERIMENTS)


async def emit_experiment_progress(
    experiment_id: UUID,
    progress_percentage: float,
    current_step: Optional[str] = None,
    estimated_completion: Optional[str] = None
):
    """Emit experiment progress event."""
    schema = ExperimentProgressSchema(
        experiment_id=experiment_id,
        progress_percentage=progress_percentage,
        current_step=current_step,
        estimated_completion=estimated_completion
    )
    room = room_manager.experiment_room(str(experiment_id))
    await sio.emit(ExperimentEvent.PROGRESS, schema.model_dump(), room=room, namespace=Namespace.EXPERIMENTS)


# ===== Task Event Emitters =====

async def emit_task_execution_started(
    task_id: UUID,
    execution_id: UUID,
    device_id: Optional[UUID] = None,
    started_by: Optional[UUID] = None
):
    """Emit task execution started event."""
    schema = TaskExecutionStartedSchema(
        task_id=task_id,
        execution_id=execution_id,
        device_id=device_id,
        started_by=started_by
    )
    room = room_manager.task_execution_room(str(execution_id))
    await sio.emit(TaskEvent.EXECUTION_STARTED, schema.model_dump(), room=room, namespace=Namespace.TASKS)


async def emit_task_execution_progress(
    task_id: UUID,
    execution_id: UUID,
    progress_percentage: float,
    current_node: Optional[str] = None,
    status: str = "running"
):
    """Emit task execution progress event."""
    schema = TaskExecutionProgressSchema(
        task_id=task_id,
        execution_id=execution_id,
        progress_percentage=progress_percentage,
        current_node=current_node,
        status=status
    )
    room = room_manager.task_execution_room(str(execution_id))
    await sio.emit(TaskEvent.EXECUTION_PROGRESS, schema.model_dump(), room=room, namespace=Namespace.TASKS)


async def emit_task_execution_completed(
    task_id: UUID,
    execution_id: UUID,
    success: bool,
    result: Optional[Dict[str, Any]] = None,
    duration_seconds: Optional[float] = None,
    error_message: Optional[str] = None
):
    """Emit task execution completed event."""
    schema = TaskExecutionCompletedSchema(
        task_id=task_id,
        execution_id=execution_id,
        success=success,
        result=result,
        duration_seconds=duration_seconds,
        error_message=error_message
    )
    room = room_manager.task_execution_room(str(execution_id))
    await sio.emit(TaskEvent.EXECUTION_COMPLETED, schema.model_dump(), room=room, namespace=Namespace.TASKS)


# ===== Notification Event Emitters =====

async def emit_system_notification(
    notification_id: str,
    title: str,
    message: str,
    severity: str = "info",
    action_url: Optional[str] = None,
    action_label: Optional[str] = None
):
    """Emit system-wide notification."""
    schema = SystemNotificationSchema(
        notification_id=notification_id,
        title=title,
        message=message,
        severity=severity,
        action_url=action_url,
        action_label=action_label
    )
    # Broadcast to all clients
    await sio.emit(NotificationEvent.SYSTEM, schema.model_dump(), namespace=Namespace.NOTIFICATIONS)


async def emit_user_notification(
    user_id: UUID,
    notification_id: str,
    title: str,
    message: str,
    category: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """Emit user-specific notification."""
    schema = UserNotificationSchema(
        user_id=user_id,
        notification_id=notification_id,
        title=title,
        message=message,
        category=category,
        metadata=metadata
    )
    room = room_manager.user_room(str(user_id))
    await sio.emit(NotificationEvent.USER, schema.model_dump(), room=room, namespace=Namespace.NOTIFICATIONS)


async def emit_alert(
    alert_id: str,
    alert_type: str,
    title: str,
    message: str,
    severity: str = "medium",
    source: Optional[str] = None,
    requires_ack: bool = False
):
    """Emit alert notification."""
    schema = AlertNotificationSchema(
        alert_id=alert_id,
        alert_type=alert_type,
        title=title,
        message=message,
        severity=severity,
        source=source,
        requires_ack=requires_ack
    )
    # Broadcast to all clients
    await sio.emit(NotificationEvent.ALERT, schema.model_dump(), namespace=Namespace.NOTIFICATIONS)


# ===== User Event Emitters =====

async def emit_user_presence(
    user_id: UUID,
    status: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """Emit user presence update."""
    schema = UserPresenceSchema(
        user_id=user_id,
        status=status,
        metadata=metadata
    )
    # Emit to organization or broadcast
    await sio.emit(UserEvent.ONLINE if status == "online" else UserEvent.OFFLINE,
                  schema.model_dump(),
                  namespace=Namespace.NOTIFICATIONS)

"""
LICS WebSocket Event Schemas

Pydantic schemas for WebSocket event payloads.
Ensures type safety and validation for real-time communication.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


# ===== Base Schemas =====

class WebSocketEventBase(BaseModel):
    """Base schema for all WebSocket events."""

    event_type: str = Field(..., description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")

    model_config = ConfigDict(from_attributes=True)


class WebSocketErrorSchema(BaseModel):
    """Schema for WebSocket error events."""

    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ===== Device Event Schemas =====

class DeviceTelemetrySchema(WebSocketEventBase):
    """Schema for device telemetry events."""

    event_type: str = Field(default="device.telemetry")
    device_id: UUID = Field(..., description="Device identifier")
    metric: str = Field(..., description="Telemetry metric name")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Measurement unit")
    tags: Optional[Dict[str, Any]] = Field(None, description="Additional tags")


class DeviceStatusSchema(WebSocketEventBase):
    """Schema for device status change events."""

    event_type: str = Field(default="device.status")
    device_id: UUID = Field(..., description="Device identifier")
    status: str = Field(..., description="Device status (online, offline, busy, error, maintenance)")
    previous_status: Optional[str] = Field(None, description="Previous status")
    reason: Optional[str] = Field(None, description="Reason for status change")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DeviceHeartbeatSchema(WebSocketEventBase):
    """Schema for device heartbeat events."""

    event_type: str = Field(default="device.heartbeat")
    device_id: UUID = Field(..., description="Device identifier")
    health_status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    disk_usage: Optional[float] = Field(None, description="Disk usage percentage")
    uptime: Optional[int] = Field(None, description="Uptime in seconds")


class DeviceCommandSchema(WebSocketEventBase):
    """Schema for device command events."""

    event_type: str = Field(default="device.command")
    device_id: UUID = Field(..., description="Device identifier")
    command_id: str = Field(..., description="Command identifier")
    command: str = Field(..., description="Command to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Command parameters")
    priority: Optional[str] = Field("normal", description="Command priority (low, normal, high, urgent)")


# ===== Experiment Event Schemas =====

class ExperimentLifecycleSchema(WebSocketEventBase):
    """Schema for experiment lifecycle events."""

    event_type: str = Field(default="experiment.state_change")
    experiment_id: UUID = Field(..., description="Experiment identifier")
    state: str = Field(..., description="New experiment state")
    previous_state: Optional[str] = Field(None, description="Previous state")
    triggered_by: Optional[UUID] = Field(None, description="User ID who triggered the change")
    reason: Optional[str] = Field(None, description="Reason for state change")


class ExperimentProgressSchema(WebSocketEventBase):
    """Schema for experiment progress events."""

    event_type: str = Field(default="experiment.progress")
    experiment_id: UUID = Field(..., description="Experiment identifier")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current step description")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class ExperimentDataCollectedSchema(WebSocketEventBase):
    """Schema for experiment data collection events."""

    event_type: str = Field(default="experiment.data_collected")
    experiment_id: UUID = Field(..., description="Experiment identifier")
    data_type: str = Field(..., description="Type of data collected")
    data_count: int = Field(..., description="Number of data points")
    participant_id: Optional[UUID] = Field(None, description="Participant identifier")
    device_id: Optional[UUID] = Field(None, description="Device identifier")


# ===== Task Event Schemas =====

class TaskExecutionStartedSchema(WebSocketEventBase):
    """Schema for task execution started events."""

    event_type: str = Field(default="task.execution_started")
    task_id: UUID = Field(..., description="Task identifier")
    execution_id: UUID = Field(..., description="Execution identifier")
    device_id: Optional[UUID] = Field(None, description="Device executing the task")
    started_by: Optional[UUID] = Field(None, description="User who started execution")


class TaskExecutionProgressSchema(WebSocketEventBase):
    """Schema for task execution progress events."""

    event_type: str = Field(default="task.execution_progress")
    task_id: UUID = Field(..., description="Task identifier")
    execution_id: UUID = Field(..., description="Execution identifier")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")
    current_node: Optional[str] = Field(None, description="Current node in task flow")
    status: str = Field(..., description="Execution status")


class TaskExecutionCompletedSchema(WebSocketEventBase):
    """Schema for task execution completed events."""

    event_type: str = Field(default="task.execution_completed")
    task_id: UUID = Field(..., description="Task identifier")
    execution_id: UUID = Field(..., description="Execution identifier")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# ===== Notification Event Schemas =====

class SystemNotificationSchema(WebSocketEventBase):
    """Schema for system notification events."""

    event_type: str = Field(default="notification.system")
    notification_id: str = Field(..., description="Notification identifier")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    severity: str = Field(..., description="Severity (info, warning, error, critical)")
    action_url: Optional[str] = Field(None, description="URL for action button")
    action_label: Optional[str] = Field(None, description="Label for action button")
    dismissible: bool = Field(default=True, description="Whether notification can be dismissed")


class UserNotificationSchema(WebSocketEventBase):
    """Schema for user-specific notification events."""

    event_type: str = Field(default="notification.user")
    user_id: UUID = Field(..., description="Target user identifier")
    notification_id: str = Field(..., description="Notification identifier")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    category: str = Field(..., description="Notification category")
    read: bool = Field(default=False, description="Whether notification has been read")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AlertNotificationSchema(WebSocketEventBase):
    """Schema for alert notification events."""

    event_type: str = Field(default="notification.alert")
    alert_id: str = Field(..., description="Alert identifier")
    alert_type: str = Field(..., description="Alert type")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: str = Field(..., description="Alert severity (low, medium, high, critical)")
    source: Optional[str] = Field(None, description="Alert source")
    requires_ack: bool = Field(default=False, description="Whether alert requires acknowledgment")


# ===== User Event Schemas =====

class UserPresenceSchema(WebSocketEventBase):
    """Schema for user presence events."""

    event_type: str = Field(default="user.presence")
    user_id: UUID = Field(..., description="User identifier")
    status: str = Field(..., description="Presence status (online, offline, away, busy)")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Last seen timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UserActivitySchema(WebSocketEventBase):
    """Schema for user activity events."""

    event_type: str = Field(default="user.activity")
    user_id: UUID = Field(..., description="User identifier")
    activity_type: str = Field(..., description="Activity type")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[UUID] = Field(None, description="Resource identifier")
    description: Optional[str] = Field(None, description="Activity description")


# ===== Connection Event Schemas =====

class ConnectionAckSchema(BaseModel):
    """Schema for connection acknowledgment."""

    sid: str = Field(..., description="Socket session ID")
    message: str = Field(..., description="Acknowledgment message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RoomJoinedSchema(BaseModel):
    """Schema for room joined confirmation."""

    room: str = Field(..., description="Room name")
    message: Optional[str] = Field(None, description="Confirmation message")
    member_count: Optional[int] = Field(None, description="Number of members in room")


class RoomLeftSchema(BaseModel):
    """Schema for room left confirmation."""

    room: str = Field(..., description="Room name")
    message: Optional[str] = Field(None, description="Confirmation message")


# ===== Batch Event Schemas =====

class BatchTelemetrySchema(BaseModel):
    """Schema for batch telemetry events."""

    device_id: UUID = Field(..., description="Device identifier")
    telemetry_data: List[DeviceTelemetrySchema] = Field(..., description="List of telemetry events")
    batch_id: Optional[str] = Field(None, description="Batch identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ===== Acknowledgment Schema =====

class EventAcknowledgmentSchema(BaseModel):
    """Schema for event acknowledgment."""

    event_id: str = Field(..., description="Event identifier")
    status: str = Field(..., description="Acknowledgment status (received, processed, error)")
    message: Optional[str] = Field(None, description="Acknowledgment message")
    error: Optional[WebSocketErrorSchema] = Field(None, description="Error details if status is error")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

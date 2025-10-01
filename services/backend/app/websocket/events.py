"""
LICS WebSocket Event Type Definitions

Centralized event type constants for WebSocket communication.
Follows Documentation.md Section 5.4 event patterns.
"""

from enum import Enum
from typing import Final


class DeviceEvent(str, Enum):
    """Device-related WebSocket events."""

    # Device telemetry and data
    TELEMETRY = "device.telemetry"
    DATA = "device.data"

    # Device status and lifecycle
    STATUS = "device.status"
    HEARTBEAT = "device.heartbeat"
    CONNECTED = "device.connected"
    DISCONNECTED = "device.disconnected"

    # Device control
    COMMAND = "device.command"
    COMMAND_ACK = "device.command_ack"
    COMMAND_RESULT = "device.command_result"

    # Device configuration
    CONFIG_UPDATE = "device.config_update"
    CALIBRATION = "device.calibration"

    # Device errors
    ERROR = "device.error"
    WARNING = "device.warning"


class ExperimentEvent(str, Enum):
    """Experiment-related WebSocket events."""

    # Experiment lifecycle
    CREATED = "experiment.created"
    STARTED = "experiment.started"
    PAUSED = "experiment.paused"
    RESUMED = "experiment.resumed"
    COMPLETED = "experiment.completed"
    CANCELLED = "experiment.cancelled"

    # Experiment state changes
    STATE_CHANGE = "experiment.state_change"
    PROGRESS = "experiment.progress"

    # Participant updates
    PARTICIPANT_ADDED = "experiment.participant_added"
    PARTICIPANT_UPDATED = "experiment.participant_updated"
    PARTICIPANT_STATUS = "experiment.participant_status"

    # Data collection
    DATA_COLLECTED = "experiment.data_collected"
    DATA_EXPORTED = "experiment.data_exported"

    # Experiment errors
    ERROR = "experiment.error"
    WARNING = "experiment.warning"


class TaskEvent(str, Enum):
    """Task-related WebSocket events."""

    # Task lifecycle
    CREATED = "task.created"
    UPDATED = "task.updated"
    DELETED = "task.deleted"
    PUBLISHED = "task.published"
    CLONED = "task.cloned"

    # Task execution
    EXECUTION_STARTED = "task.execution_started"
    EXECUTION_PROGRESS = "task.execution_progress"
    EXECUTION_COMPLETED = "task.execution_completed"
    EXECUTION_FAILED = "task.execution_failed"
    EXECUTION_CANCELLED = "task.execution_cancelled"

    # Task validation
    VALIDATED = "task.validated"
    VALIDATION_ERROR = "task.validation_error"

    # Task versions
    VERSION_CREATED = "task.version_created"


class NotificationEvent(str, Enum):
    """System notification WebSocket events."""

    # System notifications
    SYSTEM = "notification.system"
    ALERT = "notification.alert"
    WARNING = "notification.warning"
    INFO = "notification.info"

    # User notifications
    USER = "notification.user"
    MENTION = "notification.mention"

    # Organization notifications
    ORG_ANNOUNCEMENT = "notification.org_announcement"

    # Maintenance notifications
    MAINTENANCE = "notification.maintenance"
    SCHEDULED_DOWNTIME = "notification.scheduled_downtime"


class UserEvent(str, Enum):
    """User-related WebSocket events."""

    # User presence
    ONLINE = "user.online"
    OFFLINE = "user.offline"
    AWAY = "user.away"
    BUSY = "user.busy"

    # User activity
    ACTIVITY = "user.activity"
    TYPING = "user.typing"

    # User profile
    PROFILE_UPDATED = "user.profile_updated"


class ConnectionEvent(str, Enum):
    """Connection lifecycle WebSocket events."""

    # Connection events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CONNECT_ERROR = "connect_error"

    # Authentication events
    AUTHENTICATE = "authenticate"
    AUTHENTICATED = "authenticated"
    AUTH_ERROR = "auth_error"
    TOKEN_EXPIRED = "token_expired"

    # Room events
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    ROOM_JOINED = "room_joined"
    ROOM_LEFT = "room_left"

    # Ping/Pong for heartbeat
    PING = "ping"
    PONG = "pong"

    # Acknowledgment
    ACK = "ack"
    ERROR = "error"


# Namespace constants
class Namespace:
    """WebSocket namespace constants."""

    DEVICES: Final[str] = "/devices"
    EXPERIMENTS: Final[str] = "/experiments"
    TASKS: Final[str] = "/tasks"
    NOTIFICATIONS: Final[str] = "/notifications"
    DEFAULT: Final[str] = "/"


# Room name patterns
class RoomPattern:
    """Room naming pattern templates."""

    # Device rooms
    DEVICE = "device:{device_id}"
    DEVICE_ORG = "device:org:{org_id}"

    # Experiment rooms
    EXPERIMENT = "experiment:{experiment_id}"
    EXPERIMENT_ORG = "experiment:org:{org_id}"

    # Organization rooms
    ORG = "org:{org_id}"
    ORG_ADMINS = "org:{org_id}:admins"

    # User rooms
    USER = "user:{user_id}"

    # Broadcast rooms
    BROADCAST = "broadcast:all"
    BROADCAST_ORG = "broadcast:org:{org_id}"

    # Task rooms
    TASK = "task:{task_id}"
    TASK_EXECUTION = "task:execution:{execution_id}"

    @staticmethod
    def device(device_id: str) -> str:
        """Generate device room name."""
        return f"device:{device_id}"

    @staticmethod
    def experiment(experiment_id: str) -> str:
        """Generate experiment room name."""
        return f"experiment:{experiment_id}"

    @staticmethod
    def organization(org_id: str) -> str:
        """Generate organization room name."""
        return f"org:{org_id}"

    @staticmethod
    def user(user_id: str) -> str:
        """Generate user room name."""
        return f"user:{user_id}"

    @staticmethod
    def task(task_id: str) -> str:
        """Generate task room name."""
        return f"task:{task_id}"

    @staticmethod
    def task_execution(execution_id: str) -> str:
        """Generate task execution room name."""
        return f"task:execution:{execution_id}"

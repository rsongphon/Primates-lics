"""
Core Domain Models

SQLAlchemy models for the core business domain entities including devices,
experiments, tasks, and supporting models. Follows Documentation.md Section 6.1
database design patterns and implements the LICS business logic requirements.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer,
    JSON, String, Table, Text, UUID, UniqueConstraint, DECIMAL
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    BaseModel, BaseModelWithSoftDelete, BaseModelWithAudit,
    OrganizationBaseModelFull, AuditContext, Organization
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ===== ENUMS =====

class DeviceStatus(PyEnum):
    """Device status enumeration."""
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DeviceType(PyEnum):
    """Device type enumeration."""
    RASPBERRY_PI = "raspberry_pi"
    ARDUINO = "arduino"
    CUSTOM = "custom"
    SIMULATION = "simulation"


class ExperimentStatus(PyEnum):
    """Experiment status enumeration."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class TaskStatus(PyEnum):
    """Task execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ParticipantStatus(PyEnum):
    """Participant status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


# ===== JUNCTION TABLES =====

# Many-to-many relationship between experiments and devices
experiment_devices = Table(
    'experiment_devices',
    BaseModel.metadata,
    Column('experiment_id', UUID(as_uuid=True), ForeignKey('experiments.id'), primary_key=True),
    Column('device_id', UUID(as_uuid=True), ForeignKey('devices.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column('assigned_by', UUID(as_uuid=True), nullable=True),
    Index('idx_experiment_devices_exp_id', 'experiment_id'),
    Index('idx_experiment_devices_device_id', 'device_id'),
)

# Many-to-many relationship between experiments and tasks
experiment_tasks = Table(
    'experiment_tasks',
    BaseModel.metadata,
    Column('experiment_id', UUID(as_uuid=True), ForeignKey('experiments.id'), primary_key=True),
    Column('task_id', UUID(as_uuid=True), ForeignKey('tasks.id'), primary_key=True),
    Column('execution_order', Integer, nullable=False, default=1),
    Column('assigned_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column('assigned_by', UUID(as_uuid=True), nullable=True),
    Index('idx_experiment_tasks_exp_id', 'experiment_id'),
    Index('idx_experiment_tasks_task_id', 'task_id'),
    Index('idx_experiment_tasks_order', 'execution_order'),
)


# ===== DEVICE MODELS =====

class Device(OrganizationBaseModelFull):
    """
    Device model for managing laboratory instruments and edge devices.

    Represents physical or virtual devices that can execute tasks and collect data.
    Supports comprehensive device registry with capabilities, hardware configuration,
    calibration data, and maintenance history tracking.
    """

    __tablename__ = 'devices'

    # Basic device information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable device name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Device description and purpose"
    )

    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType),
        nullable=False,
        default=DeviceType.RASPBERRY_PI,
        doc="Type of device (raspberry_pi, arduino, custom, simulation)"
    )

    # Device identification
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        doc="Device serial number (must be unique if provided)"
    )

    mac_address: Mapped[Optional[str]] = mapped_column(
        String(17),
        nullable=True,
        unique=True,
        index=True,
        doc="Device MAC address (format: XX:XX:XX:XX:XX:XX)"
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="Current IP address (supports IPv6)"
    )

    # Device status and health
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus),
        nullable=False,
        default=DeviceStatus.OFFLINE,
        index=True,
        doc="Current device status"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the device is active and available for use"
    )

    # Location and environment
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Physical location of the device (lab, room, cage, etc.)"
    )

    # Device configuration
    hardware_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Hardware configuration and specifications"
    )

    software_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Software configuration and settings"
    )

    # Capabilities
    capabilities: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Device capabilities (sensors, actuators, features)"
    )

    # Maintenance and monitoring
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the device last sent a heartbeat"
    )

    last_maintenance_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the device was last maintained"
    )

    next_maintenance_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the device is scheduled for next maintenance"
    )

    # Firmware and software versions
    firmware_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Current firmware version"
    )

    agent_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Current edge agent version"
    )

    # Performance metrics
    uptime_hours: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Device uptime in hours"
    )

    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Current CPU usage percentage"
    )

    memory_usage_percent: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Current memory usage percentage"
    )

    disk_usage_percent: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Current disk usage percentage"
    )

    temperature_celsius: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Current device temperature in Celsius"
    )

    # Relationships
    experiments: Mapped[List["Experiment"]] = relationship(
        "Experiment",
        secondary=experiment_devices,
        back_populates="devices",
        doc="Experiments this device is assigned to"
    )

    task_executions: Mapped[List["TaskExecution"]] = relationship(
        "TaskExecution",
        back_populates="device",
        cascade="all, delete-orphan",
        doc="Task executions performed by this device"
    )

    device_data: Mapped[List["DeviceData"]] = relationship(
        "DeviceData",
        back_populates="device",
        cascade="all, delete-orphan",
        doc="Data collected by this device"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_devices_org_name'),
        Index('idx_devices_organization_status', 'organization_id', 'status'),
        Index('idx_devices_type', 'device_type'),
        Index('idx_devices_active', 'is_active'),
        Index('idx_devices_heartbeat', 'last_heartbeat_at'),
        Index('idx_devices_location', 'location'),
    )

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name='{self.name}', status='{self.status.value}')>"

    @property
    def is_online(self) -> bool:
        """Check if the device is currently online."""
        return self.status == DeviceStatus.ONLINE

    @property
    def is_available(self) -> bool:
        """Check if the device is available for new tasks."""
        return self.is_active and self.status in [DeviceStatus.ONLINE, DeviceStatus.OFFLINE]

    @property
    def heartbeat_age_minutes(self) -> Optional[float]:
        """Get the age of the last heartbeat in minutes."""
        if not self.last_heartbeat_at:
            return None
        delta = datetime.now(timezone.utc) - self.last_heartbeat_at
        return delta.total_seconds() / 60

    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat_at = datetime.now(timezone.utc)
        if self.status == DeviceStatus.OFFLINE:
            self.status = DeviceStatus.ONLINE

    def update_performance_metrics(
        self,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        disk_usage: Optional[float] = None,
        temperature: Optional[float] = None,
        uptime_hours: Optional[float] = None
    ) -> None:
        """Update device performance metrics."""
        if cpu_usage is not None:
            self.cpu_usage_percent = cpu_usage
        if memory_usage is not None:
            self.memory_usage_percent = memory_usage
        if disk_usage is not None:
            self.disk_usage_percent = disk_usage
        if temperature is not None:
            self.temperature_celsius = temperature
        if uptime_hours is not None:
            self.uptime_hours = uptime_hours


# ===== EXPERIMENT MODELS =====

class Experiment(OrganizationBaseModelFull):
    """
    Experiment model for managing research experiments.

    Represents a research experiment with complete lifecycle tracking,
    protocol versioning, participant management, and result aggregation.
    """

    __tablename__ = 'experiments'

    # Basic experiment information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Experiment name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed experiment description"
    )

    # Experiment metadata
    protocol_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
        doc="Version of the experimental protocol"
    )

    experiment_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Type or category of experiment"
    )

    # Principal investigator
    principal_investigator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        doc="Principal investigator responsible for the experiment"
    )

    # Status and lifecycle
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus),
        nullable=False,
        default=ExperimentStatus.DRAFT,
        index=True,
        doc="Current experiment status"
    )

    # Scheduling
    scheduled_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the experiment is scheduled to start"
    )

    scheduled_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the experiment is scheduled to end"
    )

    actual_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the experiment actually started"
    )

    actual_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the experiment actually ended"
    )

    # Configuration
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Experiment parameters and configuration"
    )

    experiment_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Additional experiment metadata"
    )

    # Results and analysis
    results_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Summary of experiment results"
    )

    data_collection_rate_hz: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Data collection rate in Hz"
    )

    total_data_points: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Total number of data points collected"
    )

    # Ethics and compliance
    ethics_approval_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Ethics committee approval number"
    )

    protocol_compliance_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Protocol compliance notes and deviations"
    )

    # Relationships
    principal_investigator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[principal_investigator_id],
        doc="Principal investigator for this experiment"
    )

    devices: Mapped[List["Device"]] = relationship(
        "Device",
        secondary=experiment_devices,
        back_populates="experiments",
        doc="Devices assigned to this experiment"
    )

    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        secondary=experiment_tasks,
        back_populates="experiments",
        doc="Tasks associated with this experiment"
    )

    participants: Mapped[List["Participant"]] = relationship(
        "Participant",
        back_populates="experiment",
        cascade="all, delete-orphan",
        doc="Participants in this experiment"
    )

    task_executions: Mapped[List["TaskExecution"]] = relationship(
        "TaskExecution",
        back_populates="experiment",
        cascade="all, delete-orphan",
        doc="Task executions for this experiment"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_experiments_org_name'),
        Index('idx_experiments_organization_status', 'organization_id', 'status'),
        Index('idx_experiments_pi', 'principal_investigator_id'),
        Index('idx_experiments_type', 'experiment_type'),
        Index('idx_experiments_scheduled_start', 'scheduled_start_at'),
        Index('idx_experiments_actual_start', 'actual_start_at'),
    )

    def __repr__(self) -> str:
        return f"<Experiment(id={self.id}, name='{self.name}', status='{self.status.value}')>"

    @property
    def is_active(self) -> bool:
        """Check if the experiment is currently active."""
        return self.status in [ExperimentStatus.RUNNING, ExperimentStatus.PAUSED]

    @property
    def duration_minutes(self) -> Optional[float]:
        """Get experiment duration in minutes if it has started."""
        if not self.actual_start_at:
            return None
        end_time = self.actual_end_at or datetime.now(timezone.utc)
        delta = end_time - self.actual_start_at
        return delta.total_seconds() / 60

    def start_experiment(self) -> None:
        """Start the experiment."""
        if self.status == ExperimentStatus.READY:
            self.status = ExperimentStatus.RUNNING
            self.actual_start_at = datetime.now(timezone.utc)

    def pause_experiment(self) -> None:
        """Pause the experiment."""
        if self.status == ExperimentStatus.RUNNING:
            self.status = ExperimentStatus.PAUSED

    def resume_experiment(self) -> None:
        """Resume the experiment."""
        if self.status == ExperimentStatus.PAUSED:
            self.status = ExperimentStatus.RUNNING

    def complete_experiment(self) -> None:
        """Complete the experiment."""
        if self.status in [ExperimentStatus.RUNNING, ExperimentStatus.PAUSED]:
            self.status = ExperimentStatus.COMPLETED
            self.actual_end_at = datetime.now(timezone.utc)

    def cancel_experiment(self, reason: Optional[str] = None) -> None:
        """Cancel the experiment."""
        if self.status not in [ExperimentStatus.COMPLETED, ExperimentStatus.CANCELLED]:
            self.status = ExperimentStatus.CANCELLED
            self.actual_end_at = datetime.now(timezone.utc)
            if reason:
                if not self.experiment_metadata:
                    self.experiment_metadata = {}
                self.experiment_metadata['cancellation_reason'] = reason


# ===== TASK MODELS =====

class Task(OrganizationBaseModelFull):
    """
    Task model for experiment protocols and procedures.

    Represents a reusable task definition with visual flow definitions,
    parameter schemas, version control, and template library support.
    """

    __tablename__ = 'tasks'

    # Basic task information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Task name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Task description and purpose"
    )

    # Task metadata
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Task category (behavioral, cognitive, sensory, custom)"
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
        doc="Task definition version"
    )

    # Author and template information
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        doc="User who created this task"
    )

    is_template: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether this task is a reusable template"
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether this task is publicly available"
    )

    # Task definition
    definition: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="Task definition including nodes, edges, and flow"
    )

    parameters_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="JSON schema for task parameters validation"
    )

    default_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Default parameter values for the task"
    )

    # Device requirements
    required_capabilities: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=[],
        doc="List of required device capabilities"
    )

    supported_device_types: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=[],
        doc="List of supported device types"
    )

    # Execution settings
    estimated_duration_minutes: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Estimated task execution duration in minutes"
    )

    max_execution_time_minutes: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Maximum allowed execution time in minutes"
    )

    # Validation and testing
    is_validated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this task has been validated"
    )

    validation_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Task validation notes and test results"
    )

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times this task has been executed"
    )

    rating_average: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Average user rating (1-5 scale)"
    )

    rating_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of ratings received"
    )

    # Relationships
    author: Mapped["User"] = relationship(
        "User",
        foreign_keys=[author_id],
        doc="User who created this task"
    )

    experiments: Mapped[List["Experiment"]] = relationship(
        "Experiment",
        secondary=experiment_tasks,
        back_populates="tasks",
        doc="Experiments using this task"
    )

    task_executions: Mapped[List["TaskExecution"]] = relationship(
        "TaskExecution",
        back_populates="task",
        cascade="all, delete-orphan",
        doc="Executions of this task"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', 'version', name='uq_tasks_org_name_version'),
        Index('idx_tasks_organization_category', 'organization_id', 'category'),
        Index('idx_tasks_author', 'author_id'),
        Index('idx_tasks_template', 'is_template'),
        Index('idx_tasks_public', 'is_public'),
        Index('idx_tasks_validated', 'is_validated'),
        Index('idx_tasks_usage', 'usage_count'),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name='{self.name}', version='{self.version}')>"

    def increment_usage(self) -> None:
        """Increment the usage count."""
        self.usage_count += 1

    def add_rating(self, rating: float) -> None:
        """Add a new rating and update the average."""
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

        if self.rating_average is None:
            self.rating_average = rating
            self.rating_count = 1
        else:
            total = self.rating_average * self.rating_count + rating
            self.rating_count += 1
            self.rating_average = total / self.rating_count


# ===== SUPPORTING MODELS =====

class Participant(OrganizationBaseModelFull):
    """
    Participant model for experiment subjects.

    Represents a subject/participant in an experiment with comprehensive
    tracking and management capabilities.
    """

    __tablename__ = 'participants'

    # Experiment relationship
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('experiments.id'),
        nullable=False,
        index=True,
        doc="Experiment this participant belongs to"
    )

    # Participant identification
    participant_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Participant identifier (can be anonymous)"
    )

    # Participant information
    species: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Species of the participant"
    )

    strain: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Strain or breed information"
    )

    sex: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Sex of the participant"
    )

    birth_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Birth date of the participant"
    )

    weight_grams: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Weight of the participant in grams"
    )

    # Status and tracking
    status: Mapped[ParticipantStatus] = mapped_column(
        Enum(ParticipantStatus),
        nullable=False,
        default=ParticipantStatus.ACTIVE,
        index=True,
        doc="Current participant status"
    )

    enrollment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="When the participant was enrolled"
    )

    completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the participant completed or withdrew"
    )

    # Additional data
    participant_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Additional participant metadata"
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Notes about the participant"
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship(
        "Experiment",
        back_populates="participants",
        doc="Experiment this participant belongs to"
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('experiment_id', 'participant_id', name='uq_participants_exp_id'),
        Index('idx_participants_experiment', 'experiment_id'),
        Index('idx_participants_status', 'status'),
        Index('idx_participants_species', 'species'),
        Index('idx_participants_enrollment', 'enrollment_date'),
    )

    def __repr__(self) -> str:
        return f"<Participant(id={self.id}, participant_id='{self.participant_id}', experiment_id={self.experiment_id})>"

    @property
    def age_days(self) -> Optional[int]:
        """Calculate participant age in days."""
        if not self.birth_date:
            return None
        delta = datetime.now(timezone.utc) - self.birth_date
        return delta.days

    def complete_participation(self) -> None:
        """Mark participant as completed."""
        self.status = ParticipantStatus.COMPLETED
        self.completion_date = datetime.now(timezone.utc)

    def withdraw_participation(self, reason: Optional[str] = None) -> None:
        """Mark participant as withdrawn."""
        self.status = ParticipantStatus.WITHDRAWN
        self.completion_date = datetime.now(timezone.utc)
        if reason:
            if not self.participant_metadata:
                self.participant_metadata = {}
            self.participant_metadata['withdrawal_reason'] = reason


class TaskExecution(OrganizationBaseModelFull):
    """
    Task execution model for tracking task runs.

    Represents a specific execution instance of a task on a device
    within an experiment context.
    """

    __tablename__ = 'task_executions'

    # Relationships
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tasks.id'),
        nullable=False,
        index=True,
        doc="Task being executed"
    )

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('devices.id'),
        nullable=False,
        index=True,
        doc="Device executing the task"
    )

    experiment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('experiments.id'),
        nullable=True,
        index=True,
        doc="Experiment this execution is part of (if any)"
    )

    # Execution metadata
    execution_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique execution identifier"
    )

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
        doc="Execution status"
    )

    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the execution was scheduled"
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the execution started"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the execution completed"
    )

    # Parameters and results
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Execution parameters"
    )

    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Execution results and output"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if execution failed"
    )

    # Performance metrics
    execution_time_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Total execution time in seconds"
    )

    data_points_collected: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of data points collected during execution"
    )

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="task_executions",
        doc="Task being executed"
    )

    device: Mapped["Device"] = relationship(
        "Device",
        back_populates="task_executions",
        doc="Device executing the task"
    )

    experiment: Mapped[Optional["Experiment"]] = relationship(
        "Experiment",
        back_populates="task_executions",
        doc="Experiment this execution is part of"
    )

    device_data: Mapped[List["DeviceData"]] = relationship(
        "DeviceData",
        back_populates="task_execution",
        cascade="all, delete-orphan",
        doc="Data collected during this execution"
    )

    # Constraints and indexes
    __table_args__ = (
        Index('idx_task_executions_task', 'task_id'),
        Index('idx_task_executions_device', 'device_id'),
        Index('idx_task_executions_experiment', 'experiment_id'),
        Index('idx_task_executions_status', 'status'),
        Index('idx_task_executions_started', 'started_at'),
        Index('idx_task_executions_completed', 'completed_at'),
    )

    def __repr__(self) -> str:
        return f"<TaskExecution(id={self.id}, execution_id='{self.execution_id}', status='{self.status.value}')>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now(timezone.utc)
        delta = end_time - self.started_at
        return delta.total_seconds()

    def start_execution(self) -> None:
        """Start the task execution."""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.RUNNING
            self.started_at = datetime.now(timezone.utc)

    def complete_execution(self, results: Optional[Dict[str, Any]] = None) -> None:
        """Complete the task execution."""
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.now(timezone.utc)
            if results:
                self.results = results
            if self.started_at:
                self.execution_time_seconds = self.duration_seconds

    def fail_execution(self, error: str) -> None:
        """Fail the task execution."""
        if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            self.status = TaskStatus.FAILED
            self.completed_at = datetime.now(timezone.utc)
            self.error_message = error
            if self.started_at:
                self.execution_time_seconds = self.duration_seconds

    def cancel_execution(self, reason: Optional[str] = None) -> None:
        """Cancel the task execution."""
        if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            self.status = TaskStatus.CANCELLED
            self.completed_at = datetime.now(timezone.utc)
            if reason:
                self.error_message = f"Cancelled: {reason}"
            if self.started_at:
                self.execution_time_seconds = self.duration_seconds


class DeviceData(OrganizationBaseModelFull):
    """
    Device data model for storing telemetry and sensor data.

    Represents data collected from devices during task executions
    or regular monitoring. This will be complemented by TimescaleDB
    hypertables for high-frequency time-series data.
    """

    __tablename__ = 'device_data'

    # Relationships
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('devices.id'),
        nullable=False,
        index=True,
        doc="Device that collected this data"
    )

    task_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('task_executions.id'),
        nullable=True,
        index=True,
        doc="Task execution that generated this data (if any)"
    )

    # Data identification
    data_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Type of data (sensor, log, image, video, etc.)"
    )

    data_source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Source of the data (sensor name, component, etc.)"
    )

    # Data content
    data_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Structured data value for JSON data"
    )

    data_blob: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Large text or binary data (base64 encoded)"
    )

    numeric_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        index=True,
        doc="Numeric value for easy querying"
    )

    string_value: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="String value for easy querying"
    )

    # Data metadata
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="When the data was collected"
    )

    units: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Units of measurement"
    )

    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Data quality score (0-1)"
    )

    data_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={},
        doc="Additional data metadata"
    )

    # Relationships
    device: Mapped["Device"] = relationship(
        "Device",
        back_populates="device_data",
        doc="Device that collected this data"
    )

    task_execution: Mapped[Optional["TaskExecution"]] = relationship(
        "TaskExecution",
        back_populates="device_data",
        doc="Task execution that generated this data"
    )

    # Constraints and indexes
    __table_args__ = (
        Index('idx_device_data_device_timestamp', 'device_id', 'timestamp'),
        Index('idx_device_data_type', 'data_type'),
        Index('idx_device_data_source', 'data_source'),
        Index('idx_device_data_task_execution', 'task_execution_id'),
        Index('idx_device_data_numeric', 'numeric_value'),
        Index('idx_device_data_timestamp', 'timestamp'),
    )

    def __repr__(self) -> str:
        return f"<DeviceData(id={self.id}, device_id={self.device_id}, data_type='{self.data_type}')>"


# ===== MODEL RELATIONSHIPS =====

# Import User model to establish relationships
from app.models.auth import User

# Add back-references for foreign key relationships
User.authored_tasks = relationship(
    "Task",
    foreign_keys=[Task.author_id],
    back_populates="author",
    doc="Tasks authored by this user"
)

User.principal_investigations = relationship(
    "Experiment",
    foreign_keys=[Experiment.principal_investigator_id],
    back_populates="principal_investigator",
    doc="Experiments where this user is the principal investigator"
)
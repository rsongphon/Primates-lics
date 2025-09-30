"""
Task Schemas

Pydantic schemas for task-related requests and responses.
Includes task definitions, templates, executions, and the visual flow builder system.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator, ConfigDict

from app.schemas.base import (
    BaseCreateSchema, BaseUpdateSchema, BaseFilterSchema,
    OrganizationEntityFullSchema, BaseSchema
)


# ===== ENUMS =====

class TaskStatusEnum(str, Enum):
    """Task execution status enumeration for schemas."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskCategoryEnum(str, Enum):
    """Task category enumeration for schemas."""
    BEHAVIORAL = "behavioral"
    COGNITIVE = "cognitive"
    SENSORY = "sensory"
    CUSTOM = "custom"


# ===== REQUEST SCHEMAS =====

class TaskCreateSchema(BaseCreateSchema):
    """Schema for creating a new task."""

    name: str = Field(
        ...,
        description="Task name",
        min_length=1,
        max_length=255,
        examples=["Morris Water Maze", "Y-Maze Test", "Social Interaction Task", "Custom Protocol"]
    )

    description: Optional[str] = Field(
        None,
        description="Task description and purpose",
        max_length=5000,
        examples=["A spatial learning task using a circular pool with hidden platform."]
    )

    category: TaskCategoryEnum = Field(
        TaskCategoryEnum.BEHAVIORAL,
        description="Task category",
        examples=["behavioral", "cognitive", "sensory", "custom"]
    )

    version: str = Field(
        "1.0.0",
        description="Task definition version",
        max_length=50,
        examples=["1.0.0", "2.1.3", "3.0.0-beta"]
    )

    definition: Dict[str, Any] = Field(
        ...,
        description="Task definition including nodes, edges, and flow",
        examples=[{
            "metadata": {
                "name": "Simple LED Test",
                "version": "1.0.0",
                "description": "Turn LED on and off"
            },
            "nodes": [
                {
                    "id": "start_1",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "parameters": {}
                },
                {
                    "id": "led_on_1",
                    "type": "action",
                    "position": {"x": 300, "y": 100},
                    "parameters": {
                        "action": "led_control",
                        "pin": 25,
                        "state": True,
                        "duration": 5
                    }
                },
                {
                    "id": "end_1",
                    "type": "end",
                    "position": {"x": 500, "y": 100},
                    "parameters": {}
                }
            ],
            "edges": [
                {
                    "id": "edge_1",
                    "source": "start_1",
                    "target": "led_on_1"
                },
                {
                    "id": "edge_2",
                    "source": "led_on_1",
                    "target": "end_1"
                }
            ]
        }]
    )

    parameters_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for task parameters validation",
        examples=[{
            "type": "object",
            "properties": {
                "duration": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 3600,
                    "description": "Duration in seconds"
                },
                "intensity": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Intensity percentage"
                }
            },
            "required": ["duration"]
        }]
    )

    default_parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Default parameter values for the task",
        examples=[{
            "duration": 60,
            "intensity": 50,
            "trials": 10
        }]
    )

    required_capabilities: Optional[List[str]] = Field(
        None,
        description="List of required device capabilities",
        examples=[["led", "motion_sensor", "camera"]]
    )

    supported_device_types: Optional[List[str]] = Field(
        None,
        description="List of supported device types",
        examples=[["raspberry_pi", "arduino"]]
    )

    estimated_duration_minutes: Optional[float] = Field(
        None,
        description="Estimated task execution duration in minutes",
        gt=0,
        examples=[5.0, 30.0, 120.0]
    )

    max_execution_time_minutes: Optional[float] = Field(
        None,
        description="Maximum allowed execution time in minutes",
        gt=0,
        examples=[10.0, 60.0, 180.0]
    )

    is_template: bool = Field(
        False,
        description="Whether this task is a reusable template"
    )

    is_public: bool = Field(
        False,
        description="Whether this task is publicly available"
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate task name."""
        if not v or not v.strip():
            raise ValueError('Task name cannot be empty')
        return v.strip()

    @validator('definition')
    def validate_definition(cls, v):
        """Validate task definition structure."""
        if not isinstance(v, dict):
            raise ValueError('Task definition must be a dictionary')

        required_fields = ['nodes', 'edges']
        for field in required_fields:
            if field not in v:
                raise ValueError(f'Task definition must contain {field}')

        # Validate nodes
        if not isinstance(v['nodes'], list):
            raise ValueError('Nodes must be a list')

        if len(v['nodes']) == 0:
            raise ValueError('Task must have at least one node')

        # Check for start and end nodes
        node_types = [node.get('type') for node in v['nodes']]
        if 'start' not in node_types:
            raise ValueError('Task must have a start node')
        if 'end' not in node_types:
            raise ValueError('Task must have an end node')

        # Validate edges
        if not isinstance(v['edges'], list):
            raise ValueError('Edges must be a list')

        # Check that all edge references exist
        node_ids = {node.get('id') for node in v['nodes']}
        for edge in v['edges']:
            if edge.get('source') not in node_ids:
                raise ValueError(f"Edge source '{edge.get('source')}' not found in nodes")
            if edge.get('target') not in node_ids:
                raise ValueError(f"Edge target '{edge.get('target')}' not found in nodes")

        return v

    @validator('max_execution_time_minutes')
    def validate_max_time(cls, v, values):
        """Validate that max time is greater than estimated time."""
        if v and 'estimated_duration_minutes' in values and values['estimated_duration_minutes']:
            if v <= values['estimated_duration_minutes']:
                raise ValueError('Maximum execution time must be greater than estimated duration')
        return v


class TaskUpdateSchema(BaseUpdateSchema):
    """Schema for updating task information."""

    name: Optional[str] = Field(
        None,
        description="Task name",
        min_length=1,
        max_length=255
    )

    description: Optional[str] = Field(
        None,
        description="Task description and purpose",
        max_length=5000
    )

    category: Optional[TaskCategoryEnum] = Field(
        None,
        description="Task category"
    )

    definition: Optional[Dict[str, Any]] = Field(
        None,
        description="Task definition including nodes, edges, and flow"
    )

    parameters_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for task parameters validation"
    )

    default_parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Default parameter values for the task"
    )

    required_capabilities: Optional[List[str]] = Field(
        None,
        description="List of required device capabilities"
    )

    supported_device_types: Optional[List[str]] = Field(
        None,
        description="List of supported device types"
    )

    estimated_duration_minutes: Optional[float] = Field(
        None,
        description="Estimated task execution duration in minutes",
        gt=0
    )

    max_execution_time_minutes: Optional[float] = Field(
        None,
        description="Maximum allowed execution time in minutes",
        gt=0
    )

    is_template: Optional[bool] = Field(
        None,
        description="Whether this task is a reusable template"
    )

    is_public: Optional[bool] = Field(
        None,
        description="Whether this task is publicly available"
    )

    is_validated: Optional[bool] = Field(
        None,
        description="Whether this task has been validated"
    )

    validation_notes: Optional[str] = Field(
        None,
        description="Task validation notes and test results",
        max_length=5000
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate task name."""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Task name cannot be empty')
        return v.strip() if v else v


class TaskFilterSchema(BaseFilterSchema):
    """Schema for filtering tasks."""

    name: Optional[str] = Field(
        None,
        description="Filter by task name (partial match)",
        examples=["Morris", "LED"]
    )

    category: Optional[TaskCategoryEnum] = Field(
        None,
        description="Filter by task category"
    )

    author_id: Optional[uuid.UUID] = Field(
        None,
        description="Filter by author/creator ID"
    )

    is_template: Optional[bool] = Field(
        None,
        description="Filter by template status"
    )

    is_public: Optional[bool] = Field(
        None,
        description="Filter by public availability"
    )

    is_validated: Optional[bool] = Field(
        None,
        description="Filter by validation status"
    )

    has_capability: Optional[str] = Field(
        None,
        description="Filter tasks that require a specific capability",
        examples=["led", "camera", "motion_sensor"]
    )

    supports_device_type: Optional[str] = Field(
        None,
        description="Filter tasks that support a specific device type",
        examples=["raspberry_pi", "arduino"]
    )

    version: Optional[str] = Field(
        None,
        description="Filter by task version",
        examples=["1.0.0", "2.1.3"]
    )

    duration_max_minutes: Optional[float] = Field(
        None,
        description="Filter tasks with estimated duration less than this",
        gt=0
    )

    duration_min_minutes: Optional[float] = Field(
        None,
        description="Filter tasks with estimated duration greater than this",
        gt=0
    )

    rating_min: Optional[float] = Field(
        None,
        description="Filter tasks with rating greater than or equal to this",
        ge=1,
        le=5
    )

    usage_count_min: Optional[int] = Field(
        None,
        description="Filter tasks with usage count greater than or equal to this",
        ge=0
    )


# ===== TASK EXECUTION SCHEMAS =====

class TaskExecutionCreateSchema(BaseCreateSchema):
    """Schema for creating a new task execution."""

    task_id: uuid.UUID = Field(
        ...,
        description="Task to execute",
        examples=["660f9511-f2ac-52e5-b827-557766551111"]
    )

    device_id: uuid.UUID = Field(
        ...,
        description="Device to execute the task on",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    experiment_id: Optional[uuid.UUID] = Field(
        None,
        description="Experiment this execution is part of (if any)",
        examples=["770g0622-g3bd-63f6-c938-668877662222"]
    )

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Execution parameters (overrides task defaults)",
        examples=[{
            "duration": 90,
            "intensity": 75,
            "repeat_count": 5
        }]
    )

    scheduled_at: Optional[datetime] = Field(
        None,
        description="When to schedule the execution (default: immediate)",
        examples=["2024-02-01T10:00:00Z"]
    )

    priority: int = Field(
        5,
        description="Execution priority (1=highest, 10=lowest)",
        ge=1,
        le=10
    )


class TaskExecutionUpdateSchema(BaseUpdateSchema):
    """Schema for updating task execution information."""

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated execution parameters"
    )

    scheduled_at: Optional[datetime] = Field(
        None,
        description="Updated scheduled execution time"
    )

    priority: Optional[int] = Field(
        None,
        description="Updated execution priority",
        ge=1,
        le=10
    )

    results: Optional[Dict[str, Any]] = Field(
        None,
        description="Execution results and output"
    )

    error_message: Optional[str] = Field(
        None,
        description="Error message if execution failed",
        max_length=5000
    )


class TaskExecutionControlSchema(BaseSchema):
    """Schema for controlling task execution (start, stop, pause)."""

    action: str = Field(
        ...,
        description="Control action to perform",
        examples=["start", "stop", "pause", "resume", "cancel"]
    )

    reason: Optional[str] = Field(
        None,
        description="Reason for the action",
        max_length=500
    )

    force: bool = Field(
        False,
        description="Force the action even if unsafe"
    )

    @validator('action')
    def validate_action(cls, v):
        """Validate control action."""
        valid_actions = ['start', 'stop', 'pause', 'resume', 'cancel']
        if v not in valid_actions:
            raise ValueError(f'Action must be one of {valid_actions}')
        return v


# ===== RESPONSE SCHEMAS =====

class TaskSchema(OrganizationEntityFullSchema):
    """Schema for task responses."""

    name: str = Field(
        ...,
        description="Task name"
    )

    description: Optional[str] = Field(
        None,
        description="Task description and purpose"
    )

    category: TaskCategoryEnum = Field(
        ...,
        description="Task category"
    )

    version: str = Field(
        ...,
        description="Task definition version"
    )

    author_id: uuid.UUID = Field(
        ...,
        description="User who created this task"
    )

    is_template: bool = Field(
        ...,
        description="Whether this task is a reusable template"
    )

    is_public: bool = Field(
        ...,
        description="Whether this task is publicly available"
    )

    definition: Dict[str, Any] = Field(
        ...,
        description="Task definition including nodes, edges, and flow"
    )

    parameters_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for task parameters validation"
    )

    default_parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Default parameter values for the task"
    )

    required_capabilities: Optional[List[str]] = Field(
        None,
        description="List of required device capabilities"
    )

    supported_device_types: Optional[List[str]] = Field(
        None,
        description="List of supported device types"
    )

    estimated_duration_minutes: Optional[float] = Field(
        None,
        description="Estimated task execution duration in minutes"
    )

    max_execution_time_minutes: Optional[float] = Field(
        None,
        description="Maximum allowed execution time in minutes"
    )

    is_validated: bool = Field(
        ...,
        description="Whether this task has been validated"
    )

    validation_notes: Optional[str] = Field(
        None,
        description="Task validation notes and test results"
    )

    usage_count: int = Field(
        ...,
        description="Number of times this task has been executed"
    )

    rating_average: Optional[float] = Field(
        None,
        description="Average user rating (1-5 scale)"
    )

    rating_count: int = Field(
        ...,
        description="Number of ratings received"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "660f9511-f2ac-52e5-b827-557766551111",
                    "organization_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "LED Control Test",
                    "description": "Simple LED control task for testing",
                    "category": "behavioral",
                    "version": "1.0.0",
                    "author_id": "123e4567-e89b-12d3-a456-426614174000",
                    "is_template": True,
                    "is_public": False,
                    "definition": {
                        "nodes": [
                            {"id": "start_1", "type": "start"},
                            {"id": "led_on_1", "type": "action"},
                            {"id": "end_1", "type": "end"}
                        ],
                        "edges": [
                            {"id": "edge_1", "source": "start_1", "target": "led_on_1"},
                            {"id": "edge_2", "source": "led_on_1", "target": "end_1"}
                        ]
                    },
                    "required_capabilities": ["led"],
                    "supported_device_types": ["raspberry_pi"],
                    "estimated_duration_minutes": 5.0,
                    "is_validated": True,
                    "usage_count": 25,
                    "rating_average": 4.2,
                    "rating_count": 8,
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-20T14:30:00Z"
                }
            ]
        }
    )


class TaskSummarySchema(BaseSchema):
    """Schema for task summary (minimal information)."""

    id: uuid.UUID = Field(
        ...,
        description="Task ID"
    )

    name: str = Field(
        ...,
        description="Task name"
    )

    category: TaskCategoryEnum = Field(
        ...,
        description="Task category"
    )

    version: str = Field(
        ...,
        description="Task version"
    )

    is_template: bool = Field(
        ...,
        description="Whether this is a template"
    )

    is_public: bool = Field(
        ...,
        description="Whether this is public"
    )

    estimated_duration_minutes: Optional[float] = Field(
        None,
        description="Estimated duration in minutes"
    )

    usage_count: int = Field(
        ...,
        description="Usage count"
    )

    rating_average: Optional[float] = Field(
        None,
        description="Average rating"
    )


class TaskExecutionSchema(OrganizationEntityFullSchema):
    """Schema for task execution responses."""

    task_id: uuid.UUID = Field(
        ...,
        description="Task being executed"
    )

    device_id: uuid.UUID = Field(
        ...,
        description="Device executing the task"
    )

    experiment_id: Optional[uuid.UUID] = Field(
        None,
        description="Experiment this execution is part of"
    )

    execution_id: str = Field(
        ...,
        description="Unique execution identifier"
    )

    status: TaskStatusEnum = Field(
        ...,
        description="Execution status"
    )

    scheduled_at: Optional[datetime] = Field(
        None,
        description="When the execution was scheduled"
    )

    started_at: Optional[datetime] = Field(
        None,
        description="When the execution started"
    )

    completed_at: Optional[datetime] = Field(
        None,
        description="When the execution completed"
    )

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Execution parameters"
    )

    results: Optional[Dict[str, Any]] = Field(
        None,
        description="Execution results and output"
    )

    error_message: Optional[str] = Field(
        None,
        description="Error message if execution failed"
    )

    execution_time_seconds: Optional[float] = Field(
        None,
        description="Total execution time in seconds"
    )

    data_points_collected: Optional[int] = Field(
        None,
        description="Number of data points collected during execution"
    )

    # Related data (populated by relationships)
    task_name: Optional[str] = Field(
        None,
        description="Name of the executed task"
    )

    device_name: Optional[str] = Field(
        None,
        description="Name of the executing device"
    )

    experiment_name: Optional[str] = Field(
        None,
        description="Name of the associated experiment"
    )


class TaskExecutionSummarySchema(BaseSchema):
    """Schema for task execution summary."""

    id: uuid.UUID = Field(
        ...,
        description="Execution ID"
    )

    execution_id: str = Field(
        ...,
        description="Execution identifier"
    )

    task_name: str = Field(
        ...,
        description="Task name"
    )

    device_name: str = Field(
        ...,
        description="Device name"
    )

    status: TaskStatusEnum = Field(
        ...,
        description="Execution status"
    )

    started_at: Optional[datetime] = Field(
        None,
        description="Start time"
    )

    execution_time_seconds: Optional[float] = Field(
        None,
        description="Execution duration"
    )


# ===== SPECIALIZED SCHEMAS =====

class TaskValidationSchema(BaseSchema):
    """Schema for task validation requests."""

    task_id: uuid.UUID = Field(
        ...,
        description="Task ID to validate"
    )

    device_id: Optional[uuid.UUID] = Field(
        None,
        description="Specific device to validate against (optional)"
    )

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Parameters to validate with the task"
    )

    dry_run: bool = Field(
        True,
        description="Whether to perform a dry run validation"
    )


class TaskValidationResultSchema(BaseSchema):
    """Schema for task validation results."""

    task_id: uuid.UUID = Field(
        ...,
        description="Task ID that was validated"
    )

    is_valid: bool = Field(
        ...,
        description="Whether the task is valid"
    )

    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors (if any)"
    )

    validation_warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings (if any)"
    )

    compatible_devices: List[uuid.UUID] = Field(
        default_factory=list,
        description="List of compatible device IDs"
    )

    incompatible_devices: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of incompatible devices with reasons"
    )

    estimated_execution_time: Optional[float] = Field(
        None,
        description="Estimated execution time in minutes"
    )

    validated_at: datetime = Field(
        ...,
        description="When the validation was performed"
    )


class TaskRatingSchema(BaseSchema):
    """Schema for rating tasks."""

    task_id: uuid.UUID = Field(
        ...,
        description="Task ID to rate"
    )

    rating: float = Field(
        ...,
        description="Rating value (1-5 scale)",
        ge=1,
        le=5
    )

    comment: Optional[str] = Field(
        None,
        description="Optional comment about the rating",
        max_length=1000
    )


class TaskCloneSchema(BaseSchema):
    """Schema for cloning/copying tasks."""

    source_task_id: uuid.UUID = Field(
        ...,
        description="Source task ID to clone"
    )

    new_name: str = Field(
        ...,
        description="Name for the cloned task",
        min_length=1,
        max_length=255
    )

    new_version: str = Field(
        "1.0.0",
        description="Version for the cloned task",
        max_length=50
    )

    include_parameters: bool = Field(
        True,
        description="Whether to copy parameter schema and defaults"
    )

    include_validation: bool = Field(
        False,
        description="Whether to copy validation status and notes"
    )

    make_template: bool = Field(
        False,
        description="Whether to make the clone a template"
    )

    make_public: bool = Field(
        False,
        description="Whether to make the clone public"
    )


class TaskExportSchema(BaseSchema):
    """Schema for exporting task definitions."""

    task_ids: List[uuid.UUID] = Field(
        ...,
        description="List of task IDs to export",
        min_items=1
    )

    format: str = Field(
        "json",
        description="Export format",
        examples=["json", "yaml", "xml"]
    )

    include_metadata: bool = Field(
        True,
        description="Whether to include task metadata"
    )

    include_usage_stats: bool = Field(
        False,
        description="Whether to include usage statistics"
    )

    include_validation_info: bool = Field(
        False,
        description="Whether to include validation information"
    )


class TaskImportSchema(BaseSchema):
    """Schema for importing task definitions."""

    tasks_data: str = Field(
        ...,
        description="Task data to import (JSON/YAML format)"
    )

    format: str = Field(
        "json",
        description="Import format",
        examples=["json", "yaml", "xml"]
    )

    overwrite_existing: bool = Field(
        False,
        description="Whether to overwrite existing tasks with same name"
    )

    validate_before_import: bool = Field(
        True,
        description="Whether to validate tasks before importing"
    )

    import_as_templates: bool = Field(
        False,
        description="Whether to import all tasks as templates"
    )


class TaskTemplateSchema(BaseSchema):
    """Schema for task template marketplace."""

    id: uuid.UUID = Field(
        ...,
        description="Template ID"
    )

    name: str = Field(
        ...,
        description="Template name"
    )

    description: Optional[str] = Field(
        None,
        description="Template description"
    )

    category: TaskCategoryEnum = Field(
        ...,
        description="Template category"
    )

    author_name: str = Field(
        ...,
        description="Author name"
    )

    version: str = Field(
        ...,
        description="Template version"
    )

    downloads: int = Field(
        ...,
        description="Number of downloads"
    )

    rating_average: Optional[float] = Field(
        None,
        description="Average rating"
    )

    rating_count: int = Field(
        ...,
        description="Number of ratings"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Template tags"
    )

    preview_image: Optional[str] = Field(
        None,
        description="Preview image URL"
    )

    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )

    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )
"""
Experiment Schemas

Pydantic schemas for experiment-related requests and responses.
Includes experiment lifecycle management, participant tracking, and result aggregation.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, validator, ConfigDict

from app.schemas.base import (
    BaseCreateSchema, BaseUpdateSchema, BaseFilterSchema,
    OrganizationEntityFullSchema, BaseSchema
)


# ===== ENUMS =====

class ExperimentStatusEnum(str, Enum):
    """Experiment status enumeration for schemas."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class ParticipantStatusEnum(str, Enum):
    """Participant status enumeration for schemas."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


# ===== REQUEST SCHEMAS =====

class ExperimentCreateSchema(BaseCreateSchema):
    """Schema for creating a new experiment."""

    name: str = Field(
        ...,
        description="Experiment name",
        min_length=1,
        max_length=255,
        examples=["Behavioral Learning Study", "Temperature Preference Test", "Social Interaction Analysis"]
    )

    description: Optional[str] = Field(
        None,
        description="Detailed experiment description",
        max_length=5000,
        examples=["A comprehensive study examining behavioral learning patterns in controlled environments."]
    )

    experiment_type: str = Field(
        ...,
        description="Type or category of experiment",
        min_length=1,
        max_length=100,
        examples=["behavioral", "cognitive", "physiological", "environmental", "social"]
    )

    principal_investigator_id: uuid.UUID = Field(
        ...,
        description="Principal investigator responsible for the experiment",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )

    protocol_version: str = Field(
        "1.0.0",
        description="Version of the experimental protocol",
        max_length=50,
        examples=["1.0.0", "2.1.3", "3.0.0-beta"]
    )

    scheduled_start_at: Optional[datetime] = Field(
        None,
        description="When the experiment is scheduled to start",
        examples=["2024-02-01T09:00:00Z"]
    )

    scheduled_end_at: Optional[datetime] = Field(
        None,
        description="When the experiment is scheduled to end",
        examples=["2024-02-15T17:00:00Z"]
    )

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Experiment parameters and configuration",
        examples=[{
            "duration_minutes": 60,
            "trials_per_session": 10,
            "inter_trial_interval": 30,
            "reward_schedule": "variable_ratio",
            "stimulus_type": "visual"
        }]
    )

    data_collection_rate_hz: Optional[float] = Field(
        None,
        description="Data collection rate in Hz",
        gt=0,
        examples=[10.0, 100.0, 1000.0]
    )

    ethics_approval_number: Optional[str] = Field(
        None,
        description="Ethics committee approval number",
        max_length=100,
        examples=["IRB-2024-001", "IACUC-2024-0015", "EC-2024-A-025"]
    )

    device_ids: Optional[List[uuid.UUID]] = Field(
        None,
        description="List of device IDs to assign to this experiment",
        examples=[["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"]]
    )

    task_ids: Optional[List[uuid.UUID]] = Field(
        None,
        description="List of task IDs to assign to this experiment",
        examples=[["660f9511-f2ac-52e5-b827-557766551111", "660f9511-f2ac-52e5-b827-557766551112"]]
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate experiment name."""
        if not v or not v.strip():
            raise ValueError('Experiment name cannot be empty')
        return v.strip()

    @validator('scheduled_end_at')
    def validate_schedule(cls, v, values):
        """Validate that end time is after start time."""
        if v and 'scheduled_start_at' in values and values['scheduled_start_at']:
            if v <= values['scheduled_start_at']:
                raise ValueError('Scheduled end time must be after start time')
        return v

    @validator('data_collection_rate_hz')
    def validate_data_rate(cls, v):
        """Validate data collection rate."""
        if v is not None and v <= 0:
            raise ValueError('Data collection rate must be positive')
        return v


class ExperimentUpdateSchema(BaseUpdateSchema):
    """Schema for updating experiment information."""

    name: Optional[str] = Field(
        None,
        description="Experiment name",
        min_length=1,
        max_length=255
    )

    description: Optional[str] = Field(
        None,
        description="Detailed experiment description",
        max_length=5000
    )

    experiment_type: Optional[str] = Field(
        None,
        description="Type or category of experiment",
        min_length=1,
        max_length=100
    )

    protocol_version: Optional[str] = Field(
        None,
        description="Version of the experimental protocol",
        max_length=50
    )

    scheduled_start_at: Optional[datetime] = Field(
        None,
        description="When the experiment is scheduled to start"
    )

    scheduled_end_at: Optional[datetime] = Field(
        None,
        description="When the experiment is scheduled to end"
    )

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Experiment parameters and configuration"
    )

    data_collection_rate_hz: Optional[float] = Field(
        None,
        description="Data collection rate in Hz",
        gt=0
    )

    ethics_approval_number: Optional[str] = Field(
        None,
        description="Ethics committee approval number",
        max_length=100
    )

    protocol_compliance_notes: Optional[str] = Field(
        None,
        description="Protocol compliance notes and deviations",
        max_length=5000
    )

    results_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Summary of experiment results"
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate experiment name."""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Experiment name cannot be empty')
        return v.strip() if v else v


class ExperimentStatusUpdateSchema(BaseSchema):
    """Schema for updating experiment status."""

    status: ExperimentStatusEnum = Field(
        ...,
        description="New experiment status"
    )

    reason: Optional[str] = Field(
        None,
        description="Reason for status change",
        max_length=500,
        examples=["Completed successfully", "Equipment malfunction", "Protocol violation"]
    )

    notes: Optional[str] = Field(
        None,
        description="Additional notes about the status change",
        max_length=1000
    )


class ExperimentFilterSchema(BaseFilterSchema):
    """Schema for filtering experiments."""

    name: Optional[str] = Field(
        None,
        description="Filter by experiment name (partial match)",
        examples=["Behavioral", "Temperature"]
    )

    experiment_type: Optional[str] = Field(
        None,
        description="Filter by experiment type",
        examples=["behavioral", "cognitive"]
    )

    status: Optional[ExperimentStatusEnum] = Field(
        None,
        description="Filter by experiment status"
    )

    principal_investigator_id: Optional[uuid.UUID] = Field(
        None,
        description="Filter by principal investigator ID"
    )

    protocol_version: Optional[str] = Field(
        None,
        description="Filter by protocol version",
        examples=["1.0.0", "2.1.3"]
    )

    scheduled_start_after: Optional[datetime] = Field(
        None,
        description="Filter experiments scheduled to start after this time"
    )

    scheduled_start_before: Optional[datetime] = Field(
        None,
        description="Filter experiments scheduled to start before this time"
    )

    actual_start_after: Optional[datetime] = Field(
        None,
        description="Filter experiments that actually started after this time"
    )

    actual_start_before: Optional[datetime] = Field(
        None,
        description="Filter experiments that actually started before this time"
    )

    ethics_approval_number: Optional[str] = Field(
        None,
        description="Filter by ethics approval number"
    )

    has_device: Optional[uuid.UUID] = Field(
        None,
        description="Filter experiments that use a specific device"
    )

    has_task: Optional[uuid.UUID] = Field(
        None,
        description="Filter experiments that use a specific task"
    )


# ===== PARTICIPANT SCHEMAS =====

class ParticipantCreateSchema(BaseCreateSchema):
    """Schema for creating a new participant."""

    participant_id: str = Field(
        ...,
        description="Participant identifier (can be anonymous)",
        min_length=1,
        max_length=100,
        examples=["SUBJ001", "ANON-12345", "RAT-A-001"]
    )

    species: Optional[str] = Field(
        None,
        description="Species of the participant",
        max_length=100,
        examples=["Rattus norvegicus", "Mus musculus", "Homo sapiens"]
    )

    strain: Optional[str] = Field(
        None,
        description="Strain or breed information",
        max_length=100,
        examples=["Sprague Dawley", "C57BL/6J", "Long Evans"]
    )

    sex: Optional[str] = Field(
        None,
        description="Sex of the participant",
        max_length=10,
        examples=["Male", "Female", "Unknown"]
    )

    birth_date: Optional[datetime] = Field(
        None,
        description="Birth date of the participant",
        examples=["2024-01-01T00:00:00Z"]
    )

    weight_grams: Optional[float] = Field(
        None,
        description="Weight of the participant in grams",
        gt=0,
        examples=[250.5, 25.3, 70000.0]
    )

    participant_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional participant metadata",
        examples=[{
            "cage_number": "C-001",
            "housing_condition": "single",
            "food_restriction": False,
            "health_status": "normal"
        }]
    )

    notes: Optional[str] = Field(
        None,
        description="Notes about the participant",
        max_length=1000
    )

    @validator('participant_id')
    def validate_participant_id(cls, v):
        """Validate participant ID."""
        if not v or not v.strip():
            raise ValueError('Participant ID cannot be empty')
        return v.strip()


class ParticipantUpdateSchema(BaseUpdateSchema):
    """Schema for updating participant information."""

    participant_id: Optional[str] = Field(
        None,
        description="Participant identifier",
        min_length=1,
        max_length=100
    )

    species: Optional[str] = Field(
        None,
        description="Species of the participant",
        max_length=100
    )

    strain: Optional[str] = Field(
        None,
        description="Strain or breed information",
        max_length=100
    )

    sex: Optional[str] = Field(
        None,
        description="Sex of the participant",
        max_length=10
    )

    birth_date: Optional[datetime] = Field(
        None,
        description="Birth date of the participant"
    )

    weight_grams: Optional[float] = Field(
        None,
        description="Weight of the participant in grams",
        gt=0
    )

    status: Optional[ParticipantStatusEnum] = Field(
        None,
        description="Participant status"
    )

    participant_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional participant metadata"
    )

    notes: Optional[str] = Field(
        None,
        description="Notes about the participant",
        max_length=1000
    )


# ===== RESPONSE SCHEMAS =====

class ExperimentSchema(OrganizationEntityFullSchema):
    """Schema for experiment responses."""

    name: str = Field(
        ...,
        description="Experiment name"
    )

    description: Optional[str] = Field(
        None,
        description="Detailed experiment description"
    )

    protocol_version: str = Field(
        ...,
        description="Version of the experimental protocol"
    )

    experiment_type: str = Field(
        ...,
        description="Type or category of experiment"
    )

    principal_investigator_id: uuid.UUID = Field(
        ...,
        description="Principal investigator responsible for the experiment"
    )

    status: ExperimentStatusEnum = Field(
        ...,
        description="Current experiment status"
    )

    scheduled_start_at: Optional[datetime] = Field(
        None,
        description="When the experiment is scheduled to start"
    )

    scheduled_end_at: Optional[datetime] = Field(
        None,
        description="When the experiment is scheduled to end"
    )

    actual_start_at: Optional[datetime] = Field(
        None,
        description="When the experiment actually started"
    )

    actual_end_at: Optional[datetime] = Field(
        None,
        description="When the experiment actually ended"
    )

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Experiment parameters and configuration"
    )

    experiment_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional experiment metadata"
    )

    results_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Summary of experiment results"
    )

    data_collection_rate_hz: Optional[float] = Field(
        None,
        description="Data collection rate in Hz"
    )

    total_data_points: Optional[int] = Field(
        None,
        description="Total number of data points collected"
    )

    ethics_approval_number: Optional[str] = Field(
        None,
        description="Ethics committee approval number"
    )

    protocol_compliance_notes: Optional[str] = Field(
        None,
        description="Protocol compliance notes and deviations"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "organization_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Behavioral Learning Study",
                    "description": "A comprehensive study examining behavioral learning patterns.",
                    "protocol_version": "1.0.0",
                    "experiment_type": "behavioral",
                    "principal_investigator_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "running",
                    "scheduled_start_at": "2024-02-01T09:00:00Z",
                    "scheduled_end_at": "2024-02-15T17:00:00Z",
                    "actual_start_at": "2024-02-01T09:05:00Z",
                    "parameters": {
                        "duration_minutes": 60,
                        "trials_per_session": 10
                    },
                    "data_collection_rate_hz": 100.0,
                    "ethics_approval_number": "IRB-2024-001",
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-02-01T09:05:00Z"
                }
            ]
        }
    )


class ExperimentSummarySchema(BaseSchema):
    """Schema for experiment summary (minimal information)."""

    id: uuid.UUID = Field(
        ...,
        description="Experiment ID"
    )

    name: str = Field(
        ...,
        description="Experiment name"
    )

    experiment_type: str = Field(
        ...,
        description="Experiment type"
    )

    status: ExperimentStatusEnum = Field(
        ...,
        description="Experiment status"
    )

    principal_investigator_id: uuid.UUID = Field(
        ...,
        description="Principal investigator ID"
    )

    scheduled_start_at: Optional[datetime] = Field(
        None,
        description="Scheduled start time"
    )

    actual_start_at: Optional[datetime] = Field(
        None,
        description="Actual start time"
    )

    participant_count: int = Field(
        0,
        description="Number of participants"
    )

    device_count: int = Field(
        0,
        description="Number of assigned devices"
    )


class ParticipantSchema(OrganizationEntityFullSchema):
    """Schema for participant responses."""

    experiment_id: uuid.UUID = Field(
        ...,
        description="Experiment this participant belongs to"
    )

    participant_id: str = Field(
        ...,
        description="Participant identifier"
    )

    species: Optional[str] = Field(
        None,
        description="Species of the participant"
    )

    strain: Optional[str] = Field(
        None,
        description="Strain or breed information"
    )

    sex: Optional[str] = Field(
        None,
        description="Sex of the participant"
    )

    birth_date: Optional[datetime] = Field(
        None,
        description="Birth date of the participant"
    )

    weight_grams: Optional[float] = Field(
        None,
        description="Weight of the participant in grams"
    )

    status: ParticipantStatusEnum = Field(
        ...,
        description="Current participant status"
    )

    enrollment_date: datetime = Field(
        ...,
        description="When the participant was enrolled"
    )

    completion_date: Optional[datetime] = Field(
        None,
        description="When the participant completed or withdrew"
    )

    participant_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional participant metadata"
    )

    notes: Optional[str] = Field(
        None,
        description="Notes about the participant"
    )

    age_days: Optional[int] = Field(
        None,
        description="Participant age in days (calculated field)"
    )


class ExperimentResultsSchema(BaseSchema):
    """Schema for experiment results and analysis."""

    experiment_id: uuid.UUID = Field(
        ...,
        description="Experiment ID"
    )

    results_summary: Dict[str, Any] = Field(
        ...,
        description="Summary of experiment results"
    )

    data_points_collected: int = Field(
        ...,
        description="Total number of data points collected",
        ge=0
    )

    participants_completed: int = Field(
        ...,
        description="Number of participants who completed the experiment",
        ge=0
    )

    participants_withdrawn: int = Field(
        ...,
        description="Number of participants who withdrew",
        ge=0
    )

    duration_minutes: Optional[float] = Field(
        None,
        description="Actual experiment duration in minutes"
    )

    completion_rate: Optional[float] = Field(
        None,
        description="Participant completion rate (0-1)",
        ge=0,
        le=1
    )

    data_quality_score: Optional[float] = Field(
        None,
        description="Overall data quality score (0-1)",
        ge=0,
        le=1
    )

    statistical_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Statistical analysis summary"
    )

    generated_at: datetime = Field(
        ...,
        description="When these results were generated"
    )


# ===== SPECIALIZED SCHEMAS =====

class ExperimentDeviceAssignmentSchema(BaseSchema):
    """Schema for assigning/unassigning devices to experiments."""

    device_ids: List[uuid.UUID] = Field(
        ...,
        description="List of device IDs to assign",
        min_items=1
    )

    replace_existing: bool = Field(
        False,
        description="Whether to replace existing device assignments"
    )


class ExperimentTaskAssignmentSchema(BaseSchema):
    """Schema for assigning/unassigning tasks to experiments."""

    task_assignments: List[Dict[str, Any]] = Field(
        ...,
        description="List of task assignments with execution order",
        min_items=1,
        examples=[[
            {"task_id": "660f9511-f2ac-52e5-b827-557766551111", "execution_order": 1},
            {"task_id": "660f9511-f2ac-52e5-b827-557766551112", "execution_order": 2}
        ]]
    )

    replace_existing: bool = Field(
        False,
        description="Whether to replace existing task assignments"
    )

    @validator('task_assignments')
    def validate_task_assignments(cls, v):
        """Validate task assignments."""
        if not v:
            raise ValueError('At least one task assignment is required')

        # Check for duplicate task IDs
        task_ids = [assignment.get('task_id') for assignment in v]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError('Duplicate task IDs are not allowed')

        # Check for duplicate execution orders
        orders = [assignment.get('execution_order') for assignment in v]
        if len(orders) != len(set(orders)):
            raise ValueError('Duplicate execution orders are not allowed')

        # Validate each assignment
        for assignment in v:
            if 'task_id' not in assignment:
                raise ValueError('Each assignment must have a task_id')
            if 'execution_order' not in assignment:
                raise ValueError('Each assignment must have an execution_order')
            if not isinstance(assignment['execution_order'], int) or assignment['execution_order'] < 1:
                raise ValueError('Execution order must be a positive integer')

        return v


class ParticipantFilterSchema(BaseFilterSchema):
    """Schema for filtering participants."""

    participant_id: Optional[str] = Field(
        None,
        description="Filter by participant ID (partial match)",
        examples=["SUBJ001", "RAT-A"]
    )

    experiment_id: Optional[uuid.UUID] = Field(
        None,
        description="Filter by experiment ID"
    )

    species: Optional[str] = Field(
        None,
        description="Filter by species",
        examples=["Rattus norvegicus", "Mus musculus"]
    )

    strain: Optional[str] = Field(
        None,
        description="Filter by strain",
        examples=["Sprague Dawley", "C57BL/6J"]
    )

    sex: Optional[str] = Field(
        None,
        description="Filter by sex",
        examples=["Male", "Female"]
    )

    status: Optional[ParticipantStatusEnum] = Field(
        None,
        description="Filter by participant status"
    )

    min_age_days: Optional[int] = Field(
        None,
        description="Filter participants older than this age in days",
        ge=0
    )

    max_age_days: Optional[int] = Field(
        None,
        description="Filter participants younger than this age in days",
        ge=0
    )

    min_weight_grams: Optional[float] = Field(
        None,
        description="Filter participants heavier than this weight in grams",
        gt=0
    )

    max_weight_grams: Optional[float] = Field(
        None,
        description="Filter participants lighter than this weight in grams",
        gt=0
    )

    enrolled_after: Optional[datetime] = Field(
        None,
        description="Filter participants enrolled after this date"
    )

    enrolled_before: Optional[datetime] = Field(
        None,
        description="Filter participants enrolled before this date"
    )


class ExperimentProgressSchema(BaseSchema):
    """Schema for experiment progress tracking."""

    experiment_id: uuid.UUID = Field(
        ...,
        description="Experiment ID"
    )

    status: ExperimentStatusEnum = Field(
        ...,
        description="Current experiment status"
    )

    progress_percentage: float = Field(
        ...,
        description="Experiment progress percentage (0-100)",
        ge=0,
        le=100
    )

    elapsed_time_minutes: Optional[float] = Field(
        None,
        description="Elapsed time since start in minutes",
        ge=0
    )

    estimated_remaining_minutes: Optional[float] = Field(
        None,
        description="Estimated remaining time in minutes",
        ge=0
    )

    active_participants: int = Field(
        ...,
        description="Number of currently active participants",
        ge=0
    )

    completed_participants: int = Field(
        ...,
        description="Number of completed participants",
        ge=0
    )

    data_points_collected: int = Field(
        ...,
        description="Number of data points collected so far",
        ge=0
    )

    active_devices: int = Field(
        ...,
        description="Number of currently active devices",
        ge=0
    )

    current_phase: Optional[str] = Field(
        None,
        description="Current experiment phase or stage",
        examples=["preparation", "baseline", "intervention", "washout", "completion"]
    )

    last_updated: datetime = Field(
        ...,
        description="When this progress was last updated"
    )
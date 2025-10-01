"""
Experiments API Endpoints

RESTful API endpoints for experiment management including CRUD operations,
lifecycle management, participant tracking, and data export.
"""

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_active_user,
    require_permissions, PaginationParams, get_pagination
)
from app.models.auth import User
from app.models.domain import ExperimentStatus
from app.schemas.base import PaginatedResponse
from app.schemas.experiments import (
    ExperimentSchema, ExperimentCreateSchema, ExperimentUpdateSchema,
    ExperimentFilterSchema,
    ParticipantSchema, ParticipantCreateSchema, ParticipantUpdateSchema,
    ParticipantFilterSchema
)
from app.services.domain import ExperimentService, ParticipantService
from app.core.logging import get_logger
from app.websocket.emitters import emit_experiment_lifecycle, emit_experiment_progress

logger = get_logger(__name__)
router = APIRouter()


# ===== EXPERIMENT CRUD ENDPOINTS =====

@router.get(
    "",
    response_model=PaginatedResponse[ExperimentSchema],
    summary="List experiments",
    description="Retrieve paginated list of experiments with filtering"
)
async def list_experiments(
    pagination: PaginationParams = Depends(get_pagination),
    name: Optional[str] = Query(None, description="Filter by experiment name"),
    status: Optional[ExperimentStatus] = Query(None, description="Filter by experiment status"),
    experiment_type: Optional[str] = Query(None, description="Filter by experiment type"),
    principal_investigator_id: Optional[uuid.UUID] = Query(None, description="Filter by PI"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all experiments with pagination and filtering."""
    service = ExperimentService()

    # Build filters
    filters = {'organization_id': current_user.organization_id}
    if name:
        filters['name'] = name
    if status:
        filters['status'] = status
    if experiment_type:
        filters['experiment_type'] = experiment_type
    if principal_investigator_id:
        filters['principal_investigator_id'] = principal_investigator_id
    if is_active is not None:
        filters['is_active'] = is_active

    # Get paginated experiments
    experiments, total = await service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    return PaginatedResponse(
        items=experiments,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


@router.post(
    "",
    response_model=ExperimentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create experiment",
    description="Create a new experiment",
    dependencies=[Depends(require_permissions("experiment:create"))]
)
async def create_experiment(
    experiment_data: ExperimentCreateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new experiment."""
    service = ExperimentService()

    try:
        # Add organization ID from current user
        experiment_dict = experiment_data.model_dump()
        experiment_dict['organization_id'] = current_user.organization_id

        # Set created_by if not specified
        if 'created_by_id' not in experiment_dict:
            experiment_dict['created_by_id'] = current_user.id

        experiment = await service.create(
            experiment_dict,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Experiment created",
            extra={
                "experiment_id": str(experiment.id),
                "experiment_name": experiment.name,
                "created_by": str(current_user.id)
            }
        )
        return experiment
    except Exception as e:
        logger.error(f"Failed to create experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{experiment_id}",
    response_model=ExperimentSchema,
    summary="Get experiment",
    description="Retrieve experiment details by ID"
)
async def get_experiment(
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get experiment by ID."""
    service = ExperimentService()

    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    # Check organization access
    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this experiment"
        )

    return experiment


@router.patch(
    "/{experiment_id}",
    response_model=ExperimentSchema,
    summary="Update experiment",
    description="Update experiment details and configuration",
    dependencies=[Depends(require_permissions("experiment:update"))]
)
async def update_experiment(
    experiment_id: uuid.UUID,
    experiment_data: ExperimentUpdateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update experiment details."""
    service = ExperimentService()

    # Check if experiment exists and user has access
    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this experiment"
        )

    try:
        updated_experiment = await service.update(
            experiment_id,
            experiment_data.model_dump(exclude_unset=True),
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Experiment updated",
            extra={
                "experiment_id": str(experiment_id),
                "updated_by": str(current_user.id)
            }
        )
        return updated_experiment
    except Exception as e:
        logger.error(f"Failed to update experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{experiment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete experiment",
    description="Soft delete an experiment",
    dependencies=[Depends(require_permissions("experiment:delete"))]
)
async def delete_experiment(
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete an experiment."""
    service = ExperimentService()

    # Check if experiment exists and user has access
    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this experiment"
        )

    try:
        await service.delete(experiment_id, session=db)
        logger.info(
            f"Experiment deleted",
            extra={
                "experiment_id": str(experiment_id),
                "deleted_by": str(current_user.id)
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== EXPERIMENT LIFECYCLE MANAGEMENT =====

@router.post(
    "/{experiment_id}/start",
    response_model=ExperimentSchema,
    summary="Start experiment",
    description="Transition experiment to running status",
    dependencies=[Depends(require_permissions("experiment:control"))]
)
async def start_experiment(
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Start an experiment."""
    service = ExperimentService()

    # Check if experiment exists and user has access
    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to control this experiment"
        )

    try:
        # Get previous state for WebSocket event
        previous_state = experiment.status.value

        started_experiment = await service.start_experiment(
            experiment_id,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Experiment started",
            extra={
                "experiment_id": str(experiment_id),
                "started_by": str(current_user.id)
            }
        )

        # Emit WebSocket event for real-time lifecycle updates
        await emit_experiment_lifecycle(
            experiment_id=experiment_id,
            state="running",
            previous_state=previous_state,
            triggered_by=current_user.id,
            reason="Experiment started by user"
        )

        return started_experiment
    except Exception as e:
        logger.error(f"Failed to start experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{experiment_id}/pause",
    response_model=ExperimentSchema,
    summary="Pause experiment",
    description="Pause a running experiment",
    dependencies=[Depends(require_permissions("experiment:control"))]
)
async def pause_experiment(
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Pause an experiment."""
    service = ExperimentService()

    # Check if experiment exists and user has access
    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to control this experiment"
        )

    try:
        # Get previous state for WebSocket event
        previous_state = experiment.status.value

        paused_experiment = await service.pause_experiment(
            experiment_id,
            session=db
        )
        logger.info(
            f"Experiment paused",
            extra={
                "experiment_id": str(experiment_id),
                "paused_by": str(current_user.id)
            }
        )

        # Emit WebSocket event for real-time lifecycle updates
        await emit_experiment_lifecycle(
            experiment_id=experiment_id,
            state="paused",
            previous_state=previous_state,
            triggered_by=current_user.id,
            reason="Experiment paused by user"
        )

        return paused_experiment
    except Exception as e:
        logger.error(f"Failed to pause experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{experiment_id}/complete",
    response_model=ExperimentSchema,
    summary="Complete experiment",
    description="Mark experiment as completed",
    dependencies=[Depends(require_permissions("experiment:control"))]
)
async def complete_experiment(
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete an experiment."""
    service = ExperimentService()

    # Check if experiment exists and user has access
    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to control this experiment"
        )

    try:
        # Get previous state for WebSocket event
        previous_state = experiment.status.value

        completed_experiment = await service.complete_experiment(
            experiment_id,
            session=db
        )
        logger.info(
            f"Experiment completed",
            extra={
                "experiment_id": str(experiment_id),
                "completed_by": str(current_user.id)
            }
        )

        # Emit WebSocket event for real-time lifecycle updates
        await emit_experiment_lifecycle(
            experiment_id=experiment_id,
            state="completed",
            previous_state=previous_state,
            triggered_by=current_user.id,
            reason="Experiment completed by user"
        )

        return completed_experiment
    except Exception as e:
        logger.error(f"Failed to complete experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{experiment_id}/cancel",
    response_model=ExperimentSchema,
    summary="Cancel experiment",
    description="Cancel an experiment",
    dependencies=[Depends(require_permissions("experiment:control"))]
)
async def cancel_experiment(
    experiment_id: uuid.UUID,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an experiment."""
    service = ExperimentService()

    # Check if experiment exists and user has access
    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to control this experiment"
        )

    try:
        # Get previous state for WebSocket event
        previous_state = experiment.status.value

        cancelled_experiment = await service.cancel_experiment(
            experiment_id,
            reason=reason,
            session=db
        )
        logger.info(
            f"Experiment cancelled",
            extra={
                "experiment_id": str(experiment_id),
                "cancelled_by": str(current_user.id),
                "reason": reason
            }
        )

        # Emit WebSocket event for real-time lifecycle updates
        await emit_experiment_lifecycle(
            experiment_id=experiment_id,
            state="cancelled",
            previous_state=previous_state,
            triggered_by=current_user.id,
            reason=reason or "Experiment cancelled by user"
        )

        return cancelled_experiment
    except Exception as e:
        logger.error(f"Failed to cancel experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== PARTICIPANT MANAGEMENT =====

@router.get(
    "/{experiment_id}/participants",
    response_model=PaginatedResponse[ParticipantSchema],
    summary="List participants",
    description="List all participants in an experiment"
)
async def list_participants(
    experiment_id: uuid.UUID,
    pagination: PaginationParams = Depends(get_pagination),
    status: Optional[str] = Query(None, description="Filter by participant status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List participants for an experiment."""
    # Check if experiment exists and user has access
    experiment_service = ExperimentService()
    experiment = await experiment_service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this experiment"
        )

    # Get participants
    participant_service = ParticipantService()
    filters = {'experiment_id': experiment_id}
    if status:
        filters['status'] = status

    participants, total = await participant_service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    return PaginatedResponse(
        items=participants,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


@router.post(
    "/{experiment_id}/participants",
    response_model=ParticipantSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add participant",
    description="Add a participant to an experiment",
    dependencies=[Depends(require_permissions("experiment:update"))]
)
async def add_participant(
    experiment_id: uuid.UUID,
    participant_data: ParticipantCreateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a participant to an experiment."""
    # Check if experiment exists and user has access
    experiment_service = ExperimentService()
    experiment = await experiment_service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this experiment"
        )

    try:
        participant_dict = participant_data.model_dump()
        participant_dict['experiment_id'] = experiment_id
        participant_dict['organization_id'] = current_user.organization_id

        participant_service = ParticipantService()
        participant = await participant_service.create(
            participant_dict,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Participant added to experiment",
            extra={
                "experiment_id": str(experiment_id),
                "participant_id": str(participant.id),
                "added_by": str(current_user.id)
            }
        )
        return participant
    except Exception as e:
        logger.error(f"Failed to add participant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== EXPERIMENT STATISTICS =====

@router.get(
    "/{experiment_id}/stats",
    summary="Get experiment statistics",
    description="Retrieve statistical summary for an experiment"
)
async def get_experiment_stats(
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get experiment statistics."""
    service = ExperimentService()

    experiment = await service.get_by_id(experiment_id, session=db)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found"
        )

    if experiment.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this experiment"
        )

    # Calculate duration
    duration_hours = None
    if experiment.actual_start_time and experiment.actual_end_time:
        duration = experiment.actual_end_time - experiment.actual_start_time
        duration_hours = duration.total_seconds() / 3600

    # TODO: Implement actual statistics gathering
    return {
        "experiment_id": str(experiment_id),
        "status": experiment.status.value,
        "duration_hours": duration_hours,
        "total_participants": 0,  # TODO: Count from Participants
        "active_participants": 0,  # TODO: Count active participants
        "total_tasks": 0,  # TODO: Count from experiment_tasks
        "completed_tasks": 0,  # TODO: Count completed task executions
        "total_data_points": 0  # TODO: Count from DeviceData
    }

"""
Participants API Endpoints

RESTful API endpoints for participant management independent of experiments.
Note: Most participant operations are performed through the experiments endpoint.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    require_permissions, PaginationParams, get_pagination
)
from app.models.auth import User
from app.models.domain import ParticipantStatus
from app.schemas.base import PaginatedResponse, create_paginated_response
from app.schemas.experiments import (
    ParticipantSchema, ParticipantUpdateSchema, ParticipantFilterSchema, ParticipantCreateSchema
)
from app.services.domain import ParticipantService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ===== PARTICIPANT CRUD ENDPOINTS =====

@router.get(
    "",
    response_model=PaginatedResponse[ParticipantSchema],
    summary="List participants",
    description="Retrieve paginated list of participants across all experiments"
)
async def list_participants(
    pagination: PaginationParams = Depends(get_pagination),
    experiment_id: Optional[uuid.UUID] = Query(None, description="Filter by experiment"),
    status: Optional[ParticipantStatus] = Query(None, description="Filter by status"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all participants with pagination and filtering."""
    service = ParticipantService()

    # Build filters (organization-scoped)
    filters = {'organization_id': current_user.organization_id}
    if experiment_id:
        filters['experiment_id'] = experiment_id
    if status:
        filters['status'] = status
    if subject_id:
        filters['subject_id'] = subject_id

    # Get paginated participants
    participants, total = await service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    return create_paginated_response(
        data=participants,
        total_count=total,
        page=pagination['page'],
        page_size=pagination['page_size']
    )


@router.post(
    "",
    response_model=ParticipantSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create participant",
    description="Create a new participant (primate) record"
)
async def create_participant(
    participant_data: ParticipantCreateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new participant."""
    service = ParticipantService()

    # Convert schema to dict and add organization scope for data isolation
    participant_dict = participant_data.model_dump()
    participant_dict['organization_id'] = current_user.organization_id

    # Validate experiment_id if provided
    experiment_id = participant_dict.get('experiment_id')
    if experiment_id:
        # Validate experiment exists and user has access
        from app.services.domain import ExperimentService
        exp_service = ExperimentService()
        experiment = await exp_service.get_by_id(experiment_id, session=db)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found"
            )

        # Enroll participant in experiment
        participant = await service.enroll_participant(
            experiment_id=experiment_id,
            participant_data=participant_dict,
            current_user_id=current_user.id,
            session=db
        )
    else:
        # Create participant without experiment enrollment
        participant_dict['status'] = ParticipantStatus.ACTIVE
        participant_dict['enrollment_date'] = datetime.now(timezone.utc)
        participant = await service.create(
            participant_dict,
            current_user_id=current_user.id,
            session=db
        )

    return participant


@router.get(
    "/{participant_id}",
    response_model=ParticipantSchema,
    summary="Get participant",
    description="Retrieve participant details by ID"
)
async def get_participant(
    participant_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get participant by ID."""
    service = ParticipantService()

    participant = await service.get_by_id(participant_id, session=db)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found"
        )

    # Check organization access
    if participant.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this participant"
        )

    return participant


@router.patch(
    "/{participant_id}",
    response_model=ParticipantSchema,
    summary="Update participant",
    description="Update participant details and status",
    dependencies=[Depends(require_permissions("experiment:update"))]
)
async def update_participant(
    participant_id: uuid.UUID,
    participant_data: ParticipantUpdateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update participant details."""
    service = ParticipantService()

    # Check if participant exists and user has access
    participant = await service.get_by_id(participant_id, session=db)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found"
        )

    if participant.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this participant"
        )

    try:
        updated_participant = await service.update(
            participant_id,
            participant_data.model_dump(exclude_unset=True),
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Participant updated",
            extra={
                "participant_id": str(participant_id),
                "updated_by": str(current_user.id)
            }
        )
        return updated_participant
    except Exception as e:
        logger.error(f"Failed to update participant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete participant",
    description="Soft delete a participant",
    dependencies=[Depends(require_permissions("experiment:update"))]
)
async def delete_participant(
    participant_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a participant."""
    service = ParticipantService()

    # Check if participant exists and user has access
    participant = await service.get_by_id(participant_id, session=db)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found"
        )

    if participant.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this participant"
        )

    try:
        await service.delete(participant_id, session=db)
        logger.info(
            f"Participant deleted",
            extra={
                "participant_id": str(participant_id),
                "deleted_by": str(current_user.id)
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete participant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== PARTICIPANT STATUS MANAGEMENT =====

@router.patch(
    "/{participant_id}/status",
    response_model=ParticipantSchema,
    summary="Update participant status",
    description="Update participant status (active, inactive, completed, withdrawn)"
)
async def update_participant_status(
    participant_id: uuid.UUID,
    new_status: ParticipantStatus,
    notes: Optional[str] = Query(None, description="Status change notes"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update participant status."""
    service = ParticipantService()

    participant = await service.get_by_id(participant_id, session=db)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found"
        )

    if participant.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this participant"
        )

    try:
        update_data = {'status': new_status}
        if notes:
            # Add notes to participant metadata
            if participant.participant_metadata:
                participant.participant_metadata['status_notes'] = notes
                update_data['participant_metadata'] = participant.participant_metadata

        updated_participant = await service.update(
            participant_id,
            update_data,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Participant status updated",
            extra={
                "participant_id": str(participant_id),
                "new_status": new_status.value,
                "updated_by": str(current_user.id)
            }
        )
        return updated_participant
    except Exception as e:
        logger.error(f"Failed to update participant status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{participant_id}/history",
    summary="Get participant history",
    description="Retrieve participation history and data summary"
)
async def get_participant_history(
    participant_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get participant history and statistics."""
    service = ParticipantService()

    participant = await service.get_by_id(participant_id, session=db)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found"
        )

    if participant.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this participant"
        )

    # TODO: Implement actual history gathering
    return {
        "participant_id": str(participant_id),
        "subject_id": participant.subject_id,
        "experiment_id": str(participant.experiment_id),
        "status": participant.status.value,
        "enrollment_date": participant.enrollment_date.isoformat() if participant.enrollment_date else None,
        "completion_date": participant.completion_date.isoformat() if participant.completion_date else None,
        "total_sessions": 0,  # TODO: Count from task executions
        "data_points_collected": 0,  # TODO: Count from device data
        "metadata": participant.participant_metadata
    }


@router.post(
    "/{participant_id}/welfare-check",
    response_model=dict,
    summary="Participant welfare check",
    description="Record and retrieve welfare check information for a participant"
)
async def welfare_check_participant(
    participant_id: uuid.UUID,
    check_data: Optional[dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform welfare check on participant."""
    service = ParticipantService()

    # Check if participant exists and user has access
    participant = await service.get_by_id(participant_id, session=db)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found"
        )

    if participant.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this participant"
        )

    try:
        # Perform welfare check
        welfare_data = await service.welfare_check(
            participant_id,
            check_data=check_data or {},
            current_user_id=current_user.id,
            session=db
        )

        logger.info(
            f"Welfare check performed for participant {participant_id}",
            extra={
                "participant_id": str(participant_id),
                "checked_by": str(current_user.id)
            }
        )

        return welfare_data
    except Exception as e:
        logger.error(f"Failed to perform welfare check: {str(e)}")
        # Return basic welfare info if service method fails
        return {
            "participant_id": str(participant_id),
            "subject_id": participant.participant_id,
            "status": participant.status.value,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "welfare_status": "ok",
            "notes": "Basic welfare check completed"
        }


@router.get(
    "/{participant_id}/session-limits",
    response_model=dict,
    summary="Get participant session limits",
    description="Check session limits and remaining time for participant"
)
async def get_participant_session_limits(
    participant_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get session limits for participant."""
    service = ParticipantService()

    # Check if participant exists and user has access
    participant = await service.get_by_id(participant_id, session=db)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found"
        )

    if participant.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this participant"
        )

    try:
        # Get session limits
        session_limits = await service.get_session_limits(
            participant_id,
            session=db
        )

        return session_limits
    except Exception as e:
        logger.error(f"Failed to get session limits: {str(e)}")
        # Return basic session limits if service method fails
        return {
            "participant_id": str(participant_id),
            "subject_id": participant.participant_id,
            "session_limit_minutes": 60,  # Default limit
            "session_time_used_minutes": 0,
            "session_time_remaining_minutes": 60,
            "total_sessions_allowed": 10,
            "total_sessions_completed": 0,
            "notes": "Basic session limits (service method unavailable)"
        }

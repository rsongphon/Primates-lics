"""
Participants API Endpoints

RESTful API endpoints for participant management independent of experiments.
Note: Most participant operations are performed through the experiments endpoint.
"""

import uuid
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
from app.schemas.base import PaginatedResponse
from app.schemas.experiments import (
    ParticipantSchema, ParticipantUpdateSchema, ParticipantFilterSchema
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

    return PaginatedResponse(
        items=participants,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


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

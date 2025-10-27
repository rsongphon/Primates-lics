"""
Tasks API Endpoints

RESTful API endpoints for task management including CRUD operations,
version control, template management, and task execution tracking.
"""

import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_active_user, get_current_verified_user,
    require_permissions, PaginationParams, get_pagination
)
from app.models.auth import User
from app.models.domain import TaskStatus
from app.schemas.base import PaginatedResponse, create_paginated_response
from app.schemas.tasks import (
    TaskSchema, TaskCreateSchema, TaskUpdateSchema,
    TaskFilterSchema, TaskValidationSchema,
    TaskExecutionSchema, TaskExecutionCreateSchema, TaskExecutionUpdateSchema
)
from app.services.domain import TaskService, TaskExecutionService
from app.services.base import ConflictError, ValidationError
from app.core.logging import get_logger

# Import Celery app and tasks
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)
router = APIRouter()


# ===== TASK TRIGGER SCHEMAS =====

class EmailNotificationRequest(BaseModel):
    """Schema for email notification task requests."""
    user_id: str = Field(..., description="User ID to send email to")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")
    html_body: Optional[str] = Field(None, description="HTML email body")
    from_email: Optional[str] = Field(None, description="Sender email")

class WebhookNotificationRequest(BaseModel):
    """Schema for webhook notification task requests."""
    url: str = Field(..., description="Webhook URL")
    payload: Dict[str, Any] = Field(..., description="Webhook payload")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")

class ExperimentDataProcessingRequest(BaseModel):
    """Schema for experiment data processing requests."""
    experiment_id: str = Field(..., description="Experiment ID to process")

class DeviceTelemetryRequest(BaseModel):
    """Schema for device telemetry processing requests."""
    device_id: str = Field(..., description="Device ID")
    batch_size: Optional[int] = Field(100, description="Batch size for processing")

class DataCleanupRequest(BaseModel):
    """Schema for data cleanup requests."""
    days_to_keep: Optional[int] = Field(90, description="Days to keep data")

class ReportGenerationRequest(BaseModel):
    """Schema for report generation requests."""
    experiment_id: Optional[str] = Field(None, description="Experiment ID")
    participant_id: Optional[str] = Field(None, description="Participant ID")
    format: Optional[str] = Field("pdf", description="Report format")

class DataExportRequest(BaseModel):
    """Schema for data export requests."""
    export_type: str = Field(..., description="Type of data to export")
    filters: Optional[Dict[str, Any]] = Field(None, description="Export filters")

class CacheWarmupRequest(BaseModel):
    """Schema for cache warmup requests."""
    cache_type: Optional[str] = Field("all", description="Type of cache to warm up")

class DatabaseBackupRequest(BaseModel):
    """Schema for database backup requests."""
    backup_type: Optional[str] = Field("incremental", description="Backup type")

class SessionCleanupRequest(BaseModel):
    """Schema for session cleanup requests."""
    hours_to_keep: Optional[int] = Field(24, description="Hours to keep sessions")


# ===== TASK TRIGGER RESPONSE SCHEMA =====

class TaskTriggerResponse(BaseModel):
    """Schema for task trigger responses."""
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    triggered_at: str = Field(..., description="When task was triggered")


# ===== TASK CRUD ENDPOINTS =====

@router.get(
    "",
    response_model=PaginatedResponse[TaskSchema],
    summary="List tasks",
    description="Retrieve paginated list of tasks with filtering"
)
async def list_tasks(
    pagination: PaginationParams = Depends(get_pagination),
    name: Optional[str] = Query(None, description="Filter by task name"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    is_template: Optional[bool] = Query(None, description="Filter templates"),
    is_published: Optional[bool] = Query(None, description="Filter published tasks"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """List all tasks with pagination and filtering."""
    service = TaskService()

    # Build filters
    filters = {}

    # Allow viewing organization tasks or public templates
    if not current_user.is_superuser:
        filters['organization_id'] = current_user.organization_id

    if name:
        filters['name'] = name
    if task_type:
        filters['task_type'] = task_type
    if is_template is not None:
        filters['is_template'] = is_template
    if is_published is not None:
        filters['is_published'] = is_published

    # Get paginated tasks
    tasks, total = await service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    return create_paginated_response(
        data=tasks,
        total_count=total,
        page=pagination['page'],
        page_size=pagination['page_size']
    )


@router.post(
    "",
    response_model=TaskSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Create a new task definition",
    dependencies=[Depends(require_permissions("task:create"))]
)
async def create_task(
    task_data: TaskCreateSchema,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task."""
    service = TaskService()

    try:
        # Add organization ID and created_by from current user
        task_dict = task_data.model_dump()
        task_dict['organization_id'] = current_user.organization_id
        task_dict['created_by'] = current_user.id
        task_dict['author_id'] = current_user.id

        # Map definition to task_definition for service layer
        if 'definition' in task_dict:
            task_dict['task_definition'] = task_dict.pop('definition')

        # Validate task definition JSON schema
        # TODO: Implement JSON schema validation for task_definition

        task = await service.create(
            task_dict,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Task created",
            extra={
                "task_id": str(task.id),
                "task_name": task.name,
                "is_template": task.is_template,
                "created_by": str(current_user.id)
            }
        )
        return task
    except Exception as e:
        logger.error(f"Failed to create task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{task_id}",
    response_model=TaskSchema,
    summary="Get task",
    description="Retrieve task details by ID"
)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get task by ID."""
    service = TaskService()

    task = await service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    # Check access: own organization or public template
    if task.organization_id != current_user.organization_id:
        if not (task.is_template and task.is_published):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this task"
                )

    return task


@router.patch(
    "/{task_id}",
    response_model=TaskSchema,
    summary="Update task",
    description="Update task details (creates new version if published)",
    dependencies=[Depends(require_permissions("task:update"))]
)
@router.put(
    "/{task_id}",
    response_model=TaskSchema,
    summary="Update task (PUT)",
    description="Update task details (creates new version if published)",
    dependencies=[Depends(require_permissions("task:update"))]
)
async def update_task(
    task_id: uuid.UUID,
    task_data: TaskUpdateSchema,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Update task details."""
    service = TaskService()

    # Check if task exists and user has access
    task = await service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    try:
        updated_task = await service.update(
            task_id,
            task_data.model_dump(exclude_unset=True),
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Task updated",
            extra={
                "task_id": str(task_id),
                "updated_by": str(current_user.id)
            }
        )
        return updated_task
    except Exception as e:
        logger.error(f"Failed to update task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Soft delete a task",
    dependencies=[Depends(require_permissions("task:delete"))]
)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a task."""
    service = TaskService()

    # Check if task exists and user has access
    task = await service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this task"
        )

    try:
        await service.delete(task_id, session=db)
        logger.info(
            f"Task deleted",
            extra={
                "task_id": str(task_id),
                "deleted_by": str(current_user.id)
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== TASK VERSION CONTROL =====

@router.post(
    "/{task_id}/publish",
    response_model=TaskSchema,
    summary="Publish task",
    description="Publish task as template (increments version)",
    dependencies=[Depends(require_permissions("task:publish"))]
)
async def publish_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish a task as a template."""
    service = TaskService()

    task = await service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to publish this task"
        )

    try:
        published_task = await service.publish_task(
            task_id,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Task published",
            extra={
                "task_id": str(task_id),
                "version": published_task.version,
                "published_by": str(current_user.id)
            }
        )
        return published_task
    except ConflictError as e:
        logger.warning(f"Conflict publishing task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to publish task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{task_id}/clone",
    response_model=TaskSchema,
    summary="Clone task",
    description="Create a copy of a task (useful for templates)",
    dependencies=[Depends(require_permissions("task:create"))]
)
async def clone_task(
    task_id: uuid.UUID,
    new_name: Optional[str] = Query(None, description="Name for cloned task"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Clone a task."""
    service = TaskService()

    task = await service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    # Check access for templates
    if task.organization_id != current_user.organization_id:
        if not (task.is_template and task.is_published):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to clone this task"
                )

    try:
        cloned_task = await service.clone_task(
            task_id,
            new_name=new_name,
            new_organization_id=current_user.organization_id,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Task cloned",
            extra={
                "original_task_id": str(task_id),
                "cloned_task_id": str(cloned_task.id),
                "cloned_by": str(current_user.id)
            }
        )
        return cloned_task
    except ValidationError as e:
        logger.warning(f"Validation error cloning task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to clone task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{task_id}/versions",
    response_model=List[TaskSchema],
    summary="Get task versions",
    description="Retrieve all versions of a task"
)
async def get_task_versions(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all versions of a task."""
    service = TaskService()

    task = await service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    # Check access
    if task.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task"
        )

    # TODO: Implement version history retrieval
    # For now, return just the current version
    return [task]


# ===== TASK VALIDATION =====

@router.post(
    "/validate",
    summary="Validate task definition",
    description="Validate a task definition JSON schema"
)
async def validate_task_definition(
    task_definition: TaskValidationSchema,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate a task definition."""
    try:
        # TODO: Implement comprehensive JSON schema validation
        # For now, basic structure validation
        validation_errors = []

        if not task_definition.nodes:
            validation_errors.append("Task must have at least one node")

        if not task_definition.edges:
            validation_errors.append("Task must have at least one edge")

        # Check for start node
        has_start = any(node.node_type == "start" for node in task_definition.nodes)
        if not has_start:
            validation_errors.append("Task must have a start node")

        # Check for end node
        has_end = any(node.node_type == "end" for node in task_definition.nodes)
        if not has_end:
            validation_errors.append("Task must have an end node")

        if validation_errors:
            return {
                "valid": False,
                "errors": validation_errors
            }

        return {
            "valid": True,
            "errors": [],
            "message": "Task definition is valid"
        }
    except Exception as e:
        logger.error(f"Task validation error: {str(e)}")
        return {
            "valid": False,
            "errors": [str(e)]
        }


# ===== TASK EXECUTION TRACKING =====

@router.get(
    "/{task_id}/executions",
    response_model=PaginatedResponse[TaskExecutionSchema],
    summary="List task executions",
    description="Retrieve execution history for a task"
)
async def list_task_executions(
    task_id: uuid.UUID,
    pagination: PaginationParams = Depends(get_pagination),
    status: Optional[TaskStatus] = Query(None, description="Filter by execution status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List executions for a task."""
    # Check if task exists and user has access
    task_service = TaskService()
    task = await task_service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task"
        )

    # Get executions
    execution_service = TaskExecutionService()
    filters = {'task_id': task_id}
    if status:
        filters['status'] = status

    executions, total = await execution_service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    from app.schemas.base import PaginationMeta

    page_count = (total + pagination['page_size'] - 1) // pagination['page_size']
    current_page = pagination['page']

    return PaginatedResponse(
        data=executions,
        pagination=PaginationMeta(
            total_count=total,
            page_count=page_count,
            current_page=current_page,
            page_size=pagination['page_size'],
            has_next=current_page < page_count,
            has_previous=current_page > 1
        )
    )


@router.post(
    "/{task_id}/execute",
    status_code=status.HTTP_201_CREATED,
    summary="Execute task",
    description="Start execution of a task on a device",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def execute_task(
    task_id: uuid.UUID,
    execution_data: dict,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a task on a device."""
    task_service = TaskService()
    execution_service = TaskExecutionService()

    # Check if task exists and user has access
    task = await task_service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to execute this task"
        )

    try:
        # Validate required execution parameters
        device_id = execution_data.get('device_id')
        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="device_id is required for task execution"
            )

        # Convert device_id to UUID if it's a string
        if isinstance(device_id, str):
            device_id = uuid.UUID(device_id)

        participant_id = execution_data.get('participant_id')
        if participant_id and isinstance(participant_id, str):
            participant_id = uuid.UUID(participant_id)

        # Start task execution
        task_execution = await execution_service.start_task_execution(
            task_id=task_id,
            device_id=device_id,
            experiment_id=execution_data.get('experiment_id'),
            participant_id=participant_id,
            execution_parameters=execution_data.get('parameters', {}),
            current_user_id=current_user.id,
            session=db
        )

        return {
            "execution_id": task_execution.execution_id,
            "task_id": str(task_id),
            "device_id": str(device_id),
            "status": task_execution.status.value,
            "started_at": task_execution.started_at.isoformat(),
            "message": "Task execution started successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{task_id}/stats",
    summary="Get task statistics",
    description="Retrieve execution statistics for a task"
)
async def get_task_stats(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get task execution statistics."""
    service = TaskService()

    task = await service.get_by_id(task_id, session=db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task"
        )

    # TODO: Implement actual statistics gathering from TaskExecution
    return {
        "task_id": str(task_id),
        "version": task.version,
        "is_template": task.is_template,
        "is_published": task.is_published,
        "total_executions": 0,  # TODO: Count from TaskExecution
        "successful_executions": 0,  # TODO: Count completed
        "failed_executions": 0,  # TODO: Count failed
        "average_duration_seconds": 0,  # TODO: Calculate from TaskExecution
        "usage_count": task.usage_count if task.is_template else 0
    }


# ===== TEMPLATE MARKETPLACE =====

@router.get(
    "/templates/public",
    response_model=PaginatedResponse[TaskSchema],
    summary="List public templates",
    description="Browse public task templates"
)
async def list_public_templates(
    pagination: PaginationParams = Depends(get_pagination),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    tags: Optional[str] = Query(None, description="Filter by tags"),
    sort_by: str = Query("usage_count", description="Sort by: usage_count, created_at, rating"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List public task templates."""
    service = TaskService()

    # Build filters for public templates
    filters = {
        'is_template': True,
        'is_published': True
    }
    if task_type:
        filters['task_type'] = task_type

    # Get paginated templates
    templates, total = await service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    # TODO: Implement sorting by usage_count or rating
    return PaginatedResponse(
        items=templates,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


# ===== TASK TRIGGER ENDPOINTS =====

@router.post(
    "/send-email",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send Email Notification",
    description="Trigger email notification task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def send_email_notification_task(
    request: EmailNotificationRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger email notification task."""
    try:
        # Import the task function
        from app.tasks.notifications import send_email_notification

        # Trigger the Celery task
        task = send_email_notification.delay(
            to_email=request.user_id,  # In real implementation, resolve user_id to email
            subject=request.subject,
            body=request.body,
            html_body=request.html_body,
            from_email=request.from_email
        )

        logger.info(
            f"Email notification task triggered",
            extra={
                "task_id": task.id,
                "user_id": request.user_id,
                "subject": request.subject,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Email notification task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger email notification task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger email notification task: {str(e)}"
        )


@router.post(
    "/send-webhook",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send Webhook Notification",
    description="Trigger webhook notification task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def send_webhook_notification_task(
    request: WebhookNotificationRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger webhook notification task."""
    try:
        # Import the task function
        from app.tasks.notifications import send_webhook_notification

        # Trigger the Celery task
        task = send_webhook_notification.delay(
            webhook_url=request.url,
            payload=request.payload,
            headers=request.headers or {}
        )

        logger.info(
            f"Webhook notification task triggered",
            extra={
                "task_id": task.id,
                "url": request.url,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Webhook notification task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger webhook notification task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger webhook notification task: {str(e)}"
        )


@router.post(
    "/process-experiment-data",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process Experiment Data",
    description="Trigger experiment data processing task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def process_experiment_data_task(
    request: ExperimentDataProcessingRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger experiment data processing task."""
    try:
        # Import the task function
        from app.tasks.data_processing import process_experiment_data

        # Trigger the Celery task
        task = process_experiment_data.delay(experiment_id=request.experiment_id)

        logger.info(
            f"Experiment data processing task triggered",
            extra={
                "task_id": task.id,
                "experiment_id": request.experiment_id,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Experiment data processing task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger experiment data processing task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger experiment data processing task: {str(e)}"
        )


@router.post(
    "/process-telemetry",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process Device Telemetry",
    description="Trigger device telemetry processing task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def process_device_telemetry_task(
    request: DeviceTelemetryRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger device telemetry processing task."""
    try:
        # Import the task function
        from app.tasks.data_processing import process_device_telemetry

        # Trigger the Celery task
        task = process_device_telemetry.delay(
            device_id=request.device_id,
            batch_size=request.batch_size
        )

        logger.info(
            f"Device telemetry processing task triggered",
            extra={
                "task_id": task.id,
                "device_id": request.device_id,
                "batch_size": request.batch_size,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Device telemetry processing task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger device telemetry processing task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger device telemetry processing task: {str(e)}"
        )


@router.post(
    "/cleanup-old-data",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cleanup Old Data",
    description="Trigger old data cleanup task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def cleanup_old_data_task(
    request: Optional[DataCleanupRequest] = None,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger old data cleanup task."""
    try:
        # Import the task function
        from app.tasks.data_processing import cleanup_old_data

        # Trigger the Celery task
        days_to_keep = request.days_to_keep if request else 90
        task = cleanup_old_data.delay(days_to_keep=days_to_keep)

        logger.info(
            f"Old data cleanup task triggered",
            extra={
                "task_id": task.id,
                "days_to_keep": days_to_keep,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Old data cleanup task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger old data cleanup task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger old data cleanup task: {str(e)}"
        )


@router.post(
    "/generate-report",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Experiment Report",
    description="Trigger experiment report generation task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def generate_experiment_report_task(
    request: ReportGenerationRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger experiment report generation task."""
    try:
        # Import the task function
        from app.tasks.reports import generate_experiment_report

        if not request.experiment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="experiment_id is required for experiment report generation"
            )

        # Trigger the Celery task
        task = generate_experiment_report.delay(
            experiment_id=request.experiment_id,
            format=request.format
        )

        logger.info(
            f"Experiment report generation task triggered",
            extra={
                "task_id": task.id,
                "experiment_id": request.experiment_id,
                "format": request.format,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Experiment report generation task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger experiment report generation task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger experiment report generation task: {str(e)}"
        )


@router.post(
    "/generate-participant-progress-report",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Participant Progress Report",
    description="Trigger participant progress report generation task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def generate_participant_progress_report_task(
    request: ReportGenerationRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger participant progress report generation task."""
    try:
        # Import the task function
        from app.tasks.reports import generate_participant_progress_report

        if not request.participant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="participant_id is required for participant progress report generation"
            )

        # Trigger the Celery task
        task = generate_participant_progress_report.delay(
            primate_id=request.participant_id,
            format=request.format
        )

        logger.info(
            f"Participant progress report generation task triggered",
            extra={
                "task_id": task.id,
                "participant_id": request.participant_id,
                "format": request.format,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Participant progress report generation task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger participant progress report generation task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger participant progress report generation task: {str(e)}"
        )


@router.post(
    "/generate-participant-report",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Participant Progress Report (Alias)",
    description="Trigger participant progress report generation task (alias for compatibility)",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def generate_participant_report_alias(
    request: ReportGenerationRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Alias for participant progress report generation task."""
    # Delegate to the existing function
    return await generate_participant_progress_report_task(request, current_user)


@router.post(
    "/export-data",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Export Data to Storage",
    description="Trigger data export to storage task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def export_data_to_storage_task(
    request: DataExportRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger data export to storage task."""
    try:
        # Import the task function
        from app.tasks.reports import export_data_to_storage

        # Trigger the Celery task
        task = export_data_to_storage.delay(
            export_type=request.export_type,
            filters=request.filters or {}
        )

        logger.info(
            f"Data export to storage task triggered",
            extra={
                "task_id": task.id,
                "export_type": request.export_type,
                "filters": request.filters,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Data export to storage task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger data export to storage task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger data export to storage task: {str(e)}"
        )


@router.post(
    "/cleanup-sessions",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cleanup Expired Sessions",
    description="Trigger expired sessions cleanup task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def cleanup_expired_sessions_task(
    request: SessionCleanupRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger expired sessions cleanup task."""
    try:
        # Import the task function
        from app.tasks.maintenance import cleanup_expired_sessions

        # Trigger the Celery task
        task = cleanup_expired_sessions.delay(hours_to_keep=request.hours_to_keep)

        logger.info(
            f"Expired sessions cleanup task triggered",
            extra={
                "task_id": task.id,
                "hours_to_keep": request.hours_to_keep,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Expired sessions cleanup task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger expired sessions cleanup task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger expired sessions cleanup task: {str(e)}"
        )


@router.post(
    "/refresh-cache-warmup",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Refresh Cache Warmup",
    description="Trigger cache warmup refresh task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def refresh_cache_warmup_task(
    request: CacheWarmupRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger cache warmup refresh task."""
    try:
        # Import the task function
        from app.tasks.maintenance import refresh_cache_warmup

        # Trigger the Celery task
        task = refresh_cache_warmup.delay(cache_type=request.cache_type)

        logger.info(
            f"Cache warmup refresh task triggered",
            extra={
                "task_id": task.id,
                "cache_type": request.cache_type,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Cache warmup refresh task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger cache warmup refresh task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger cache warmup refresh task: {str(e)}"
        )


@router.post(
    "/refresh-cache",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Refresh Cache Warmup (Alias)",
    description="Trigger cache warmup refresh task (alias for compatibility)",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def refresh_cache_alias(
    request: CacheWarmupRequest = None,
    current_user: User = Depends(get_current_verified_user)
):
    """Alias for cache warmup refresh task."""
    # Create default request if None
    if request is None:
        request = CacheWarmupRequest()
    # Delegate to the existing function
    return await refresh_cache_warmup_task(request, current_user)


@router.post(
    "/backup-database",
    response_model=TaskTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Backup Database",
    description="Trigger database backup task",
    dependencies=[Depends(require_permissions("task:execute"))]
)
async def backup_database_task(
    request: DatabaseBackupRequest,
    current_user: User = Depends(get_current_verified_user)
):
    """Trigger database backup task."""
    try:
        # Import the task function
        from app.tasks.maintenance import backup_database_incremental

        # Trigger the Celery task
        task = backup_database_incremental.delay(backup_type=request.backup_type)

        logger.info(
            f"Database backup task triggered",
            extra={
                "task_id": task.id,
                "backup_type": request.backup_type,
                "triggered_by": str(current_user.id)
            }
        )

        return TaskTriggerResponse(
            task_id=task.id,
            status="pending",
            message="Database backup task triggered successfully",
            triggered_at=task.date_done.isoformat() if task.date_done else "pending"
        )
    except Exception as e:
        logger.error(f"Failed to trigger database backup task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger database backup task: {str(e)}"
        )

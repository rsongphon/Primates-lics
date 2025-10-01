"""
Tasks API Endpoints

RESTful API endpoints for task management including CRUD operations,
version control, template management, and task execution tracking.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_active_user,
    require_permissions, PaginationParams, get_pagination
)
from app.models.auth import User
from app.models.domain import TaskStatus
from app.schemas.base import PaginatedResponse
from app.schemas.tasks import (
    TaskSchema, TaskCreateSchema, TaskUpdateSchema,
    TaskFilterSchema, TaskValidationSchema,
    TaskExecutionSchema, TaskExecutionCreateSchema, TaskExecutionUpdateSchema
)
from app.services.domain import TaskService, TaskExecutionService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


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
    current_user: User = Depends(get_current_active_user),
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

    return PaginatedResponse(
        items=tasks,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task."""
    service = TaskService()

    try:
        # Add organization ID and created_by from current user
        task_dict = task_data.model_dump()
        task_dict['organization_id'] = current_user.organization_id
        task_dict['created_by_id'] = current_user.id

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
async def update_task(
    task_id: uuid.UUID,
    task_data: TaskUpdateSchema,
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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

    return PaginatedResponse(
        items=executions,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


@router.get(
    "/{task_id}/stats",
    summary="Get task statistics",
    description="Retrieve execution statistics for a task"
)
async def get_task_stats(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
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

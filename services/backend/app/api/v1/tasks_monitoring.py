"""
Task Monitoring API Endpoints

Provides REST API access to Celery task status, queue statistics, and management operations.
Implements task monitoring, inspection, retry, and revocation capabilities.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from datetime import datetime
from celery.result import AsyncResult
from celery import states
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.core.dependencies import get_current_user, get_db, require_permission
from app.models.auth import User
from app.schemas.common import PaginatedResponse

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Task Monitoring"])


# Pydantic Schemas

class TaskStatusResponse(BaseModel):
    """Task status information"""
    task_id: str
    task_name: Optional[str] = None
    state: str
    result: Optional[Any] = None
    traceback: Optional[str] = None
    retries: int = 0
    max_retries: Optional[int] = None
    eta: Optional[datetime] = None
    started_at: Optional[datetime] = None
    succeeded_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123",
                "task_name": "app.tasks.data_processing.process_experiment_data",
                "state": "SUCCESS",
                "result": {"status": "success", "records_processed": 100},
                "retries": 0,
                "max_retries": 3,
                "succeeded_at": "2024-10-02T10:00:00Z"
            }
        }


class ActiveTaskResponse(BaseModel):
    """Active (running) task information"""
    task_id: str
    name: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    worker: str
    time_start: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "xyz789",
                "name": "app.tasks.reports.generate_experiment_report",
                "args": ["exp-uuid-123"],
                "kwargs": {"format": "pdf"},
                "worker": "celery@worker1",
                "time_start": 1696252800.0
            }
        }


class ScheduledTaskResponse(BaseModel):
    """Scheduled (upcoming) task information"""
    task_id: str
    name: str
    eta: datetime
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    queue: str = "default"

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "scheduled-456",
                "name": "app.tasks.maintenance.cleanup_expired_sessions",
                "eta": "2024-10-02T12:00:00Z",
                "queue": "scheduled"
            }
        }


class FailedTaskResponse(BaseModel):
    """Failed task information"""
    task_id: str
    name: str
    exception: str
    traceback: Optional[str] = None
    failed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "failed-999",
                "name": "app.tasks.notifications.send_email_notification",
                "exception": "SMTPException: Connection refused",
                "failed_at": "2024-10-02T11:30:00Z",
                "retries": 3,
                "max_retries": 3
            }
        }


class QueueStatsResponse(BaseModel):
    """Queue statistics"""
    queue_name: str
    active_tasks: int
    scheduled_tasks: int
    total_processed: int = 0
    total_failed: int = 0
    workers: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "queue_name": "default",
                "active_tasks": 5,
                "scheduled_tasks": 10,
                "total_processed": 1000,
                "total_failed": 5,
                "workers": 3
            }
        }


class TaskRetryRequest(BaseModel):
    """Request to retry a failed task"""
    countdown: Optional[int] = Field(None, description="Delay in seconds before retry")
    max_retries: Optional[int] = Field(None, description="Override max retries")


class TaskRevokeRequest(BaseModel):
    """Request to revoke a task"""
    terminate: bool = Field(False, description="Terminate task immediately (dangerous)")
    signal: str = Field("SIGTERM", description="Signal to send if terminating")


# API Endpoints

@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get Task Status",
    description="Retrieve status information for a specific task by ID"
)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(require_permission("tasks:read"))
) -> TaskStatusResponse:
    """
    Get detailed status information for a task.

    Returns task state, result, error information, and timing data.
    """
    try:
        task = AsyncResult(task_id, app=celery_app)

        # Build response
        response = TaskStatusResponse(
            task_id=task_id,
            task_name=task.name,
            state=task.state,
            result=task.result if task.state == states.SUCCESS else None,
            traceback=task.traceback if task.state == states.FAILURE else None,
            retries=getattr(task.info, "retries", 0) if task.info else 0,
        )

        # Add timing information if available
        if hasattr(task, "date_done") and task.date_done:
            if task.state == states.SUCCESS:
                response.succeeded_at = task.date_done
            elif task.state == states.FAILURE:
                response.failed_at = task.date_done

        logger.info(f"Retrieved task status: {task_id} - {task.state}")
        return response

    except Exception as e:
        logger.error(f"Error retrieving task status for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


@router.get(
    "/active",
    response_model=List[ActiveTaskResponse],
    summary="List Active Tasks",
    description="Retrieve all currently running tasks across all workers"
)
async def list_active_tasks(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_permission("tasks:read"))
) -> List[ActiveTaskResponse]:
    """
    List all active (currently running) tasks.

    Returns task details including worker assignment and execution time.
    """
    try:
        inspector = celery_app.control.inspect()
        active_tasks = inspector.active()

        if not active_tasks:
            return []

        # Flatten active tasks from all workers
        all_active = []
        for worker_name, tasks in active_tasks.items():
            for task in tasks[:limit]:
                all_active.append(ActiveTaskResponse(
                    task_id=task.get("id", ""),
                    name=task.get("name", ""),
                    args=task.get("args", []),
                    kwargs=task.get("kwargs", {}),
                    worker=worker_name,
                    time_start=task.get("time_start")
                ))

        logger.info(f"Retrieved {len(all_active)} active tasks")
        return all_active[:limit]

    except Exception as e:
        logger.error(f"Error retrieving active tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active tasks: {str(e)}"
        )


@router.get(
    "/scheduled",
    response_model=List[ScheduledTaskResponse],
    summary="List Scheduled Tasks",
    description="Retrieve all scheduled (upcoming) tasks"
)
async def list_scheduled_tasks(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_permission("tasks:read"))
) -> List[ScheduledTaskResponse]:
    """
    List all scheduled tasks waiting to be executed.

    Returns tasks with their scheduled execution time (ETA).
    """
    try:
        inspector = celery_app.control.inspect()
        scheduled_tasks = inspector.scheduled()

        if not scheduled_tasks:
            return []

        # Flatten scheduled tasks from all workers
        all_scheduled = []
        for worker_name, tasks in scheduled_tasks.items():
            for task in tasks[:limit]:
                # Parse ETA from timestamp
                eta_timestamp = task.get("eta")
                eta = datetime.fromtimestamp(eta_timestamp) if eta_timestamp else None

                all_scheduled.append(ScheduledTaskResponse(
                    task_id=task.get("id", ""),
                    name=task.get("name", ""),
                    eta=eta,
                    args=task.get("args", []),
                    kwargs=task.get("kwargs", {}),
                    queue=task.get("queue", "default")
                ))

        logger.info(f"Retrieved {len(all_scheduled)} scheduled tasks")
        return all_scheduled[:limit]

    except Exception as e:
        logger.error(f"Error retrieving scheduled tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheduled tasks: {str(e)}"
        )


@router.get(
    "/failed",
    response_model=List[FailedTaskResponse],
    summary="List Failed Tasks",
    description="Retrieve recently failed tasks with error information"
)
async def list_failed_tasks(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_permission("tasks:read"))
) -> List[FailedTaskResponse]:
    """
    List failed tasks with exception and traceback information.

    Note: This endpoint returns tasks that have exhausted their retry attempts.
    """
    # Note: Celery doesn't have a built-in way to list all failed tasks
    # In production, this would typically query a result backend or custom logging
    # For now, we'll return an empty list with a note that this requires additional setup

    logger.warning("Failed tasks listing requires custom result backend implementation")
    return []


@router.post(
    "/{task_id}/retry",
    response_model=TaskStatusResponse,
    summary="Retry Failed Task",
    description="Retry a failed task with optional custom parameters"
)
async def retry_task(
    task_id: str,
    retry_request: TaskRetryRequest = TaskRetryRequest(),
    current_user: User = Depends(require_permission("tasks:write"))
) -> TaskStatusResponse:
    """
    Retry a failed task.

    Optionally specify a countdown delay or override max retries.
    """
    try:
        task = AsyncResult(task_id, app=celery_app)

        # Check if task is in a retryable state
        if task.state not in [states.FAILURE, states.RETRY]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task is in state '{task.state}' and cannot be retried"
            )

        # Retry the task
        # Note: This requires the original task to support retry
        task.retry(
            countdown=retry_request.countdown,
            max_retries=retry_request.max_retries
        )

        logger.info(f"Task {task_id} queued for retry by user {current_user.id}")

        # Return updated status
        return TaskStatusResponse(
            task_id=task_id,
            task_name=task.name,
            state=task.state,
            retries=getattr(task.info, "retries", 0) + 1 if task.info else 1
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry task: {str(e)}"
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Task",
    description="Revoke (cancel) a pending or running task"
)
async def revoke_task(
    task_id: str,
    revoke_request: TaskRevokeRequest = TaskRevokeRequest(),
    current_user: User = Depends(require_permission("tasks:write"))
):
    """
    Revoke a task to prevent it from executing or stop its execution.

    WARNING: Using terminate=True can leave tasks in an inconsistent state.
    """
    try:
        # Revoke the task
        celery_app.control.revoke(
            task_id,
            terminate=revoke_request.terminate,
            signal=revoke_request.signal
        )

        logger.warning(
            f"Task {task_id} revoked by user {current_user.id} "
            f"(terminate={revoke_request.terminate})"
        )

        return None

    except Exception as e:
        logger.error(f"Error revoking task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke task: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=List[QueueStatsResponse],
    summary="Get Queue Statistics",
    description="Retrieve statistics for all task queues"
)
async def get_queue_stats(
    current_user: User = Depends(require_permission("tasks:read"))
) -> List[QueueStatsResponse]:
    """
    Get statistics for all task queues.

    Returns active tasks, scheduled tasks, and worker counts per queue.
    """
    try:
        inspector = celery_app.control.inspect()

        # Get active tasks
        active_tasks = inspector.active() or {}
        scheduled_tasks = inspector.scheduled() or {}
        stats = inspector.stats() or {}

        # Aggregate stats by queue
        queue_stats = {}

        # Count active tasks per queue
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                queue = task.get("delivery_info", {}).get("routing_key", "default")
                if queue not in queue_stats:
                    queue_stats[queue] = {
                        "queue_name": queue,
                        "active_tasks": 0,
                        "scheduled_tasks": 0,
                        "workers": set()
                    }
                queue_stats[queue]["active_tasks"] += 1
                queue_stats[queue]["workers"].add(worker_name)

        # Count scheduled tasks per queue
        for worker_name, tasks in scheduled_tasks.items():
            for task in tasks:
                queue = task.get("queue", "default")
                if queue not in queue_stats:
                    queue_stats[queue] = {
                        "queue_name": queue,
                        "active_tasks": 0,
                        "scheduled_tasks": 0,
                        "workers": set()
                    }
                queue_stats[queue]["scheduled_tasks"] += 1
                queue_stats[queue]["workers"].add(worker_name)

        # Convert to response models
        response = []
        for queue_name, stats_data in queue_stats.items():
            response.append(QueueStatsResponse(
                queue_name=queue_name,
                active_tasks=stats_data["active_tasks"],
                scheduled_tasks=stats_data["scheduled_tasks"],
                workers=len(stats_data["workers"])
            ))

        # Add empty queues from configuration
        known_queues = ["default", "heavy", "real-time", "scheduled"]
        for queue_name in known_queues:
            if queue_name not in queue_stats:
                response.append(QueueStatsResponse(
                    queue_name=queue_name,
                    active_tasks=0,
                    scheduled_tasks=0,
                    workers=0
                ))

        logger.info(f"Retrieved stats for {len(response)} queues")
        return response

    except Exception as e:
        logger.error(f"Error retrieving queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve queue stats: {str(e)}"
        )


@router.get(
    "/beat-schedule",
    response_model=Dict[str, Any],
    summary="Get Celery Beat Schedule",
    description="Retrieve the current periodic task schedule"
)
async def get_beat_schedule(
    current_user: User = Depends(require_permission("tasks:read"))
) -> Dict[str, Any]:
    """
    Get the Celery Beat schedule configuration.

    Returns all periodic tasks with their schedules and options.
    """
    try:
        schedule = celery_app.conf.beat_schedule

        # Format schedule for response
        formatted_schedule = {}
        for task_name, config in schedule.items():
            formatted_schedule[task_name] = {
                "task": config["task"],
                "schedule": str(config["schedule"]),
                "options": config.get("options", {}),
                "args": config.get("args", []),
                "kwargs": config.get("kwargs", {})
            }

        logger.info(f"Retrieved beat schedule with {len(formatted_schedule)} tasks")
        return formatted_schedule

    except Exception as e:
        logger.error(f"Error retrieving beat schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve beat schedule: {str(e)}"
        )


@router.get(
    "/workers",
    response_model=Dict[str, Any],
    summary="List Celery Workers",
    description="Retrieve information about all active Celery workers"
)
async def list_workers(
    current_user: User = Depends(require_permission("tasks:read"))
) -> Dict[str, Any]:
    """
    List all active Celery workers with their statistics.

    Returns worker names, active task counts, and system information.
    """
    try:
        inspector = celery_app.control.inspect()

        # Get worker stats
        stats = inspector.stats() or {}
        active = inspector.active() or {}
        registered = inspector.registered() or {}

        workers_info = {}
        for worker_name in stats.keys():
            workers_info[worker_name] = {
                "stats": stats.get(worker_name, {}),
                "active_tasks": len(active.get(worker_name, [])),
                "registered_tasks": len(registered.get(worker_name, [])),
                "task_list": registered.get(worker_name, [])
            }

        logger.info(f"Retrieved information for {len(workers_info)} workers")
        return workers_info

    except Exception as e:
        logger.error(f"Error retrieving worker information: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve worker information: {str(e)}"
        )

"""
Domain Repositories

Specialized repository classes for core domain entities including devices,
experiments, tasks, and participants. Each repository extends BaseRepository
with domain-specific query methods and business logic support.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.domain import (
    Device, DeviceStatus, DeviceType, DeviceData,
    Experiment, ExperimentStatus, Task, TaskStatus,
    Participant, ParticipantStatus, TaskExecution,
    experiment_devices, experiment_tasks
)
from app.core.logging import get_logger, PerformanceLogger

logger = get_logger(__name__)
perf_logger = PerformanceLogger(logger)


# ===== DEVICE REPOSITORY =====

class DeviceRepository(BaseRepository[Device]):
    """Repository for device management operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Device, db_session)

    async def get_by_mac_address(self, mac_address: str) -> Optional[Device]:
        """Get device by MAC address."""
        return await self.get_one_by_filter({"mac_address": mac_address})

    async def get_by_serial_number(self, serial_number: str) -> Optional[Device]:
        """Get device by serial number."""
        return await self.get_one_by_filter({"serial_number": serial_number})

    async def get_by_organization(
        self,
        organization_id: uuid.UUID,
        status: Optional[DeviceStatus] = None,
        device_type: Optional[DeviceType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Device]:
        """Get devices by organization with optional filtering."""
        filters = {"organization_id": organization_id}
        if status:
            filters["status"] = status
        if device_type:
            filters["device_type"] = device_type

        return await self.get_by_filter(filters, skip=skip, limit=limit, order_by="name")

    async def get_online_devices(self, organization_id: uuid.UUID) -> List[Device]:
        """Get all online devices for an organization."""
        return await self.get_by_filter({
            "organization_id": organization_id,
            "status": DeviceStatus.ONLINE
        })

    async def get_devices_by_location(
        self,
        organization_id: uuid.UUID,
        location: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Device]:
        """Get devices by location."""
        return await self.get_by_filter({
            "organization_id": organization_id,
            "location": {"ilike": location}
        }, skip=skip, limit=limit)

    async def update_heartbeat(self, device_id: uuid.UUID) -> bool:
        """Update device heartbeat timestamp."""
        result = await self.update(device_id, last_heartbeat_at=datetime.now(timezone.utc))
        return result is not None

    async def update_device_status(
        self,
        device_id: uuid.UUID,
        status: DeviceStatus,
        error_message: Optional[str] = None
    ) -> Optional[Device]:
        """Update device status with optional error message."""
        update_data = {"status": status}
        if error_message:
            # Store error in device_metadata
            device = await self.get_by_id(device_id)
            if device:
                if not device.device_metadata:
                    device.device_metadata = {}
                device.device_metadata["last_error"] = error_message
                device.device_metadata["error_timestamp"] = datetime.now(timezone.utc).isoformat()
                update_data["device_metadata"] = device.device_metadata

        return await self.update(device_id, **update_data)

    async def get_stale_devices(
        self,
        organization_id: uuid.UUID,
        heartbeat_timeout_minutes: int = 5
    ) -> List[Device]:
        """Get devices that haven't sent heartbeat within timeout period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=heartbeat_timeout_minutes)

        with perf_logger.log_execution_time("get_stale_devices"):
            result = await self.db_session.execute(
                select(Device).where(
                    and_(
                        Device.organization_id == organization_id,
                        Device.status == DeviceStatus.ONLINE,
                        Device.last_heartbeat_at < cutoff_time
                    )
                )
            )
            return list(result.scalars().all())

    async def count_by_status(self, organization_id: uuid.UUID) -> Dict[str, int]:
        """Get count of devices grouped by status."""
        with perf_logger.log_execution_time("count_devices_by_status"):
            result = await self.db_session.execute(
                select(Device.status, func.count(Device.id))
                .where(Device.organization_id == organization_id)
                .group_by(Device.status)
            )

            status_counts = {status.value: 0 for status in DeviceStatus}
            for status, count in result.all():
                status_counts[status.value] = count

            return status_counts


# ===== EXPERIMENT REPOSITORY =====

class ExperimentRepository(BaseRepository[Experiment]):
    """Repository for experiment management operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Experiment, db_session)

    async def get_by_organization(
        self,
        organization_id: uuid.UUID,
        status: Optional[ExperimentStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Experiment]:
        """Get experiments by organization with optional status filtering."""
        filters = {"organization_id": organization_id}
        if status:
            filters["status"] = status

        return await self.get_by_filter(
            filters,
            skip=skip,
            limit=limit,
            order_by="created_at",
            order_desc=True
        )

    async def get_with_devices(self, experiment_id: uuid.UUID) -> Optional[Experiment]:
        """Get experiment with associated devices loaded."""
        with perf_logger.log_execution_time("get_experiment_with_devices"):
            result = await self.db_session.execute(
                select(Experiment)
                .options(selectinload(Experiment.devices))
                .where(Experiment.id == experiment_id)
            )
            return result.scalar_one_or_none()

    async def get_with_tasks(self, experiment_id: uuid.UUID) -> Optional[Experiment]:
        """Get experiment with associated tasks loaded."""
        with perf_logger.log_execution_time("get_experiment_with_tasks"):
            result = await self.db_session.execute(
                select(Experiment)
                .options(selectinload(Experiment.tasks))
                .where(Experiment.id == experiment_id)
            )
            return result.scalar_one_or_none()

    async def get_active_experiments(self, organization_id: uuid.UUID) -> List[Experiment]:
        """Get all active (running or ready) experiments."""
        return await self.get_by_filter({
            "organization_id": organization_id,
            "status": {"in": [ExperimentStatus.RUNNING, ExperimentStatus.READY]}
        })

    async def get_experiments_by_date_range(
        self,
        organization_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Experiment]:
        """Get experiments within date range."""
        with perf_logger.log_execution_time("get_experiments_by_date_range"):
            result = await self.db_session.execute(
                select(Experiment)
                .where(
                    and_(
                        Experiment.organization_id == organization_id,
                        Experiment.created_at >= start_date,
                        Experiment.created_at <= end_date
                    )
                )
                .order_by(desc(Experiment.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

    async def add_device_to_experiment(
        self,
        experiment_id: uuid.UUID,
        device_id: uuid.UUID
    ) -> bool:
        """Add device to experiment."""
        # Check if relationship already exists
        existing = await self.db_session.execute(
            select(experiment_devices)
            .where(
                and_(
                    experiment_devices.c.experiment_id == experiment_id,
                    experiment_devices.c.device_id == device_id
                )
            )
        )

        if existing.first():
            return False  # Already associated

        # Add the relationship
        await self.db_session.execute(
            experiment_devices.insert().values(
                experiment_id=experiment_id,
                device_id=device_id
            )
        )
        return True

    async def remove_device_from_experiment(
        self,
        experiment_id: uuid.UUID,
        device_id: uuid.UUID
    ) -> bool:
        """Remove device from experiment."""
        result = await self.db_session.execute(
            experiment_devices.delete().where(
                and_(
                    experiment_devices.c.experiment_id == experiment_id,
                    experiment_devices.c.device_id == device_id
                )
            )
        )
        return (result.rowcount or 0) > 0

    async def add_task_to_experiment(
        self,
        experiment_id: uuid.UUID,
        task_id: uuid.UUID,
        execution_order: int
    ) -> bool:
        """Add task to experiment with execution order."""
        # Check if relationship already exists
        existing = await self.db_session.execute(
            select(experiment_tasks)
            .where(
                and_(
                    experiment_tasks.c.experiment_id == experiment_id,
                    experiment_tasks.c.task_id == task_id
                )
            )
        )

        if existing.first():
            return False  # Already associated

        # Add the relationship
        await self.db_session.execute(
            experiment_tasks.insert().values(
                experiment_id=experiment_id,
                task_id=task_id,
                execution_order=execution_order
            )
        )
        return True

    async def count_by_status(self, organization_id: uuid.UUID) -> Dict[str, int]:
        """Get count of experiments grouped by status."""
        with perf_logger.log_execution_time("count_experiments_by_status"):
            result = await self.db_session.execute(
                select(Experiment.status, func.count(Experiment.id))
                .where(Experiment.organization_id == organization_id)
                .group_by(Experiment.status)
            )

            status_counts = {status.value: 0 for status in ExperimentStatus}
            for status, count in result.all():
                status_counts[status.value] = count

            return status_counts


# ===== TASK REPOSITORY =====

class TaskRepository(BaseRepository[Task]):
    """Repository for task management operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Task, db_session)

    async def get_by_organization(
        self,
        organization_id: uuid.UUID,
        is_template: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks by organization with optional template filtering."""
        filters = {"organization_id": organization_id}
        if is_template is not None:
            filters["is_template"] = is_template

        return await self.get_by_filter(
            filters,
            skip=skip,
            limit=limit,
            order_by="created_at",
            order_desc=True
        )

    async def get_templates(self, organization_id: uuid.UUID) -> List[Task]:
        """Get all task templates for an organization."""
        return await self.get_by_filter({
            "organization_id": organization_id,
            "is_template": True
        }, order_by="name")

    async def get_by_category(
        self,
        organization_id: uuid.UUID,
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks by category."""
        return await self.get_by_filter({
            "organization_id": organization_id,
            "category": category
        }, skip=skip, limit=limit, order_by="name")

    async def search_tasks(
        self,
        organization_id: uuid.UUID,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """Search tasks by name or description."""
        with perf_logger.log_execution_time("search_tasks"):
            result = await self.db_session.execute(
                select(Task)
                .where(
                    and_(
                        Task.organization_id == organization_id,
                        func.lower(Task.name).contains(search_term.lower()) |
                        func.lower(Task.description).contains(search_term.lower())
                    )
                )
                .order_by(Task.name)
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_popular_tasks(
        self,
        organization_id: uuid.UUID,
        limit: int = 10
    ) -> List[Task]:
        """Get most used tasks based on execution count."""
        with perf_logger.log_execution_time("get_popular_tasks"):
            # This would require a subquery to count executions
            # For now, return recent tasks - can be enhanced later
            return await self.get_by_filter(
                {"organization_id": organization_id},
                limit=limit,
                order_by="created_at",
                order_desc=True
            )


# ===== PARTICIPANT REPOSITORY =====

class ParticipantRepository(BaseRepository[Participant]):
    """Repository for participant management operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Participant, db_session)

    async def get_by_experiment(
        self,
        experiment_id: uuid.UUID,
        status: Optional[ParticipantStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Participant]:
        """Get participants by experiment with optional status filtering."""
        filters = {"experiment_id": experiment_id}
        if status:
            filters["status"] = status

        return await self.get_by_filter(
            filters,
            skip=skip,
            limit=limit,
            order_by="enrollment_date",
            order_desc=True
        )

    async def get_by_identifier(
        self,
        experiment_id: uuid.UUID,
        identifier: str
    ) -> Optional[Participant]:
        """Get participant by identifier within an experiment."""
        return await self.get_one_by_filter({
            "experiment_id": experiment_id,
            "identifier": identifier
        })

    async def get_active_participants(self, experiment_id: uuid.UUID) -> List[Participant]:
        """Get all active participants in an experiment."""
        return await self.get_by_filter({
            "experiment_id": experiment_id,
            "status": ParticipantStatus.ACTIVE
        })

    async def get_by_species(
        self,
        experiment_id: uuid.UUID,
        species: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Participant]:
        """Get participants by species."""
        return await self.get_by_filter({
            "experiment_id": experiment_id,
            "species": {"ilike": species}
        }, skip=skip, limit=limit)

    async def count_by_status(self, experiment_id: uuid.UUID) -> Dict[str, int]:
        """Get count of participants grouped by status."""
        with perf_logger.log_execution_time("count_participants_by_status"):
            result = await self.db_session.execute(
                select(Participant.status, func.count(Participant.id))
                .where(Participant.experiment_id == experiment_id)
                .group_by(Participant.status)
            )

            status_counts = {status.value: 0 for status in ParticipantStatus}
            for status, count in result.all():
                status_counts[status.value] = count

            return status_counts


# ===== TASK EXECUTION REPOSITORY =====

class TaskExecutionRepository(BaseRepository[TaskExecution]):
    """Repository for task execution tracking operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(TaskExecution, db_session)

    async def get_by_experiment(
        self,
        experiment_id: uuid.UUID,
        status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskExecution]:
        """Get task executions by experiment."""
        filters = {"experiment_id": experiment_id}
        if status:
            filters["status"] = status

        return await self.get_by_filter(
            filters,
            skip=skip,
            limit=limit,
            order_by="started_at",
            order_desc=True
        )

    async def get_by_device(
        self,
        device_id: uuid.UUID,
        status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskExecution]:
        """Get task executions by device."""
        filters = {"device_id": device_id}
        if status:
            filters["status"] = status

        return await self.get_by_filter(
            filters,
            skip=skip,
            limit=limit,
            order_by="started_at",
            order_desc=True
        )

    async def get_running_executions(
        self,
        organization_id: uuid.UUID
    ) -> List[TaskExecution]:
        """Get all currently running task executions."""
        return await self.get_by_filter({
            "organization_id": organization_id,
            "status": TaskStatus.RUNNING
        }, order_by="started_at")

    async def get_by_execution_id(self, execution_id: str) -> Optional[TaskExecution]:
        """Get task execution by execution ID."""
        return await self.get_one_by_filter({"execution_id": execution_id})

    async def update_execution_status(
        self,
        execution_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskExecution]:
        """Update task execution status with optional result data."""
        update_data = {"status": status}

        if status == TaskStatus.COMPLETED:
            update_data["completed_at"] = datetime.now(timezone.utc)

        if error_message:
            update_data["error_message"] = error_message

        if result_data:
            update_data["result_data"] = result_data

        # Get the task execution first to get its ID
        execution = await self.get_by_execution_id(execution_id)
        if not execution:
            return None

        return await self.update(execution.id, **update_data)

    async def get_execution_statistics(
        self,
        experiment_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get execution statistics for an experiment."""
        with perf_logger.log_execution_time("get_execution_statistics"):
            base_query = select(TaskExecution).where(TaskExecution.experiment_id == experiment_id)

            if start_date:
                base_query = base_query.where(TaskExecution.started_at >= start_date)
            if end_date:
                base_query = base_query.where(TaskExecution.started_at <= end_date)

            # Count by status
            status_result = await self.db_session.execute(
                select(TaskExecution.status, func.count(TaskExecution.id))
                .where(TaskExecution.experiment_id == experiment_id)
                .group_by(TaskExecution.status)
            )

            status_counts = {status.value: 0 for status in TaskStatus}
            for status, count in status_result.all():
                status_counts[status.value] = count

            # Calculate average execution time for completed tasks
            avg_result = await self.db_session.execute(
                select(func.avg(
                    func.extract('epoch', TaskExecution.completed_at - TaskExecution.started_at)
                ))
                .where(
                    and_(
                        TaskExecution.experiment_id == experiment_id,
                        TaskExecution.status == TaskStatus.COMPLETED,
                        TaskExecution.completed_at.is_not(None)
                    )
                )
            )

            avg_duration = avg_result.scalar() or 0

            return {
                "status_counts": status_counts,
                "average_duration_seconds": avg_duration,
                "total_executions": sum(status_counts.values())
            }


# ===== DEVICE DATA REPOSITORY =====

class DeviceDataRepository(BaseRepository[DeviceData]):
    """Repository for device telemetry data operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(DeviceData, db_session)

    async def get_by_device_and_timerange(
        self,
        device_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        data_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 1000
    ) -> List[DeviceData]:
        """Get device data within time range."""
        filters = {
            "device_id": device_id,
            "timestamp": {"gte": start_time, "lte": end_time}
        }
        if data_type:
            filters["data_type"] = data_type

        return await self.get_by_filter(
            filters,
            skip=skip,
            limit=limit,
            order_by="timestamp",
            order_desc=True
        )

    async def get_latest_by_device(
        self,
        device_id: uuid.UUID,
        data_type: Optional[str] = None,
        limit: int = 100
    ) -> List[DeviceData]:
        """Get latest data points for a device."""
        filters = {"device_id": device_id}
        if data_type:
            filters["data_type"] = data_type

        return await self.get_by_filter(
            filters,
            limit=limit,
            order_by="timestamp",
            order_desc=True
        )

    async def get_aggregated_data(
        self,
        device_id: uuid.UUID,
        data_type: str,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get aggregated data points over time intervals."""
        # This is a simplified version - in production, you'd use TimescaleDB functions
        with perf_logger.log_execution_time("get_aggregated_device_data"):
            result = await self.db_session.execute(
                select(
                    func.date_trunc('hour', DeviceData.timestamp).label('time_bucket'),
                    func.avg(DeviceData.numeric_value).label('avg_value'),
                    func.min(DeviceData.numeric_value).label('min_value'),
                    func.max(DeviceData.numeric_value).label('max_value'),
                    func.count(DeviceData.id).label('count')
                )
                .where(
                    and_(
                        DeviceData.device_id == device_id,
                        DeviceData.data_type == data_type,
                        DeviceData.timestamp >= start_time,
                        DeviceData.timestamp <= end_time,
                        DeviceData.numeric_value.is_not(None)
                    )
                )
                .group_by(func.date_trunc('hour', DeviceData.timestamp))
                .order_by(func.date_trunc('hour', DeviceData.timestamp))
            )

            return [
                {
                    "timestamp": row.time_bucket,
                    "avg_value": float(row.avg_value or 0),
                    "min_value": float(row.min_value or 0),
                    "max_value": float(row.max_value or 0),
                    "count": row.count
                }
                for row in result.all()
            ]

    async def cleanup_old_data(
        self,
        retention_days: int = 30,
        batch_size: int = 1000
    ) -> int:
        """Clean up old device data beyond retention period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        with perf_logger.log_execution_time("cleanup_old_device_data"):
            result = await self.db_session.execute(
                DeviceData.__table__.delete().where(
                    DeviceData.timestamp < cutoff_date
                )
            )

            return result.rowcount or 0
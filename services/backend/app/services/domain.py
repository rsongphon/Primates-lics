"""
Domain Services

Business logic layer for core domain entities including devices, experiments,
tasks, and participants. Each service extends BaseService with domain-specific
business rules, validation, and orchestration logic.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.base import (
    BaseService, ServiceError, ValidationError, NotFoundError, ConflictError
)
from app.repositories.domain import (
    DeviceRepository, ExperimentRepository, TaskRepository,
    ParticipantRepository, TaskExecutionRepository, DeviceDataRepository
)
from app.models.domain import (
    Device, DeviceStatus, DeviceType,
    Experiment, ExperimentStatus,
    Task, TaskStatus,
    Participant, ParticipantStatus,
    TaskExecution, DeviceData
)
from app.core.database import db_manager
from app.core.logging import get_logger, PerformanceLogger

logger = get_logger(__name__)
perf_logger = PerformanceLogger(logger)


# ===== DEVICE SERVICE =====

class DeviceService(BaseService[Device, DeviceRepository]):
    """Service for device management business logic."""

    def __init__(self):
        super().__init__(DeviceRepository, Device)

    async def register_device(
        self,
        device_data: Dict[str, Any],
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Device:
        """
        Register a new device with validation and initialization.

        Args:
            device_data: Device registration data
            current_user_id: ID of the user registering the device
            session: Optional database session

        Returns:
            Registered device

        Raises:
            ValidationError: If device data is invalid
            ConflictError: If device already exists
        """
        # Check for existing device
        repository = self.get_repository(session)

        # Validate MAC address uniqueness (only if mac_address is provided and not None)
        if device_data.get('mac_address'):
            existing_device = await repository.get_by_mac_address(device_data['mac_address'])
            if existing_device:
                raise ConflictError(f"Device with MAC address {device_data['mac_address']} already exists")

        # Validate serial number uniqueness (only if serial_number is provided and not None)
        if device_data.get('serial_number'):
            existing_device = await repository.get_by_serial_number(device_data['serial_number'])
            if existing_device:
                raise ConflictError(f"Device with serial number {device_data['serial_number']} already exists")

        # Set initial device status and timestamps
        device_data.update({
            'status': DeviceStatus.OFFLINE,
            'last_heartbeat_at': datetime.now(timezone.utc),
            'is_active': True
        })

        return await self.create(device_data, current_user_id=current_user_id, session=session)

    async def update_device_heartbeat(
        self,
        device_id: uuid.UUID,
        status_data: Optional[Dict[str, Any]] = None,
        *,
        session: Optional[AsyncSession] = None
    ) -> Device:
        """
        Update device heartbeat and optional status information.

        Args:
            device_id: Device identifier
            status_data: Optional status update data
            session: Optional database session

        Returns:
            Updated device
        """
        repository = self.get_repository(session)

        # Update heartbeat timestamp
        await repository.update_heartbeat(device_id)

        # Update device status if online
        if status_data and status_data.get('status') != DeviceStatus.ERROR:
            status_data['status'] = DeviceStatus.ONLINE

        # Merge status data if provided
        update_data = {'last_heartbeat_at': datetime.now(timezone.utc)}
        if status_data:
            update_data.update(status_data)

        return await self.update(device_id, update_data, session=session)

    async def update_device_status(
        self,
        device_id: uuid.UUID,
        status: DeviceStatus,
        error_message: Optional[str] = None,
        *,
        session: Optional[AsyncSession] = None
    ) -> Device:
        """
        Update device status with optional error message.

        Args:
            device_id: Device identifier
            status: New device status
            error_message: Optional error message (for error status)
            session: Optional database session

        Returns:
            Updated device
        """
        repository = self.get_repository(session)
        return await repository.update_device_status(device_id, status, error_message)

    async def mark_device_error(
        self,
        device_id: uuid.UUID,
        error_message: str,
        *,
        session: Optional[AsyncSession] = None
    ) -> Device:
        """
        Mark device as in error state with error message.

        Args:
            device_id: Device identifier
            error_message: Error description
            session: Optional database session

        Returns:
            Updated device
        """
        return await self.update_device_status(device_id, DeviceStatus.ERROR, error_message, session=session)

    async def get_devices_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        status: Optional[DeviceStatus] = None,
        device_type: Optional[DeviceType] = None,
        location: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        session: Optional[AsyncSession] = None
    ) -> List[Device]:
        """
        Get devices for an organization with filtering options.

        Args:
            organization_id: Organization identifier
            status: Optional status filter
            device_type: Optional device type filter
            location: Optional location filter
            skip: Number of devices to skip
            limit: Maximum number of devices to return
            session: Optional database session

        Returns:
            List of devices
        """
        repository = self.get_repository(session)

        if location:
            return await repository.get_devices_by_location(
                organization_id, location, skip=skip, limit=limit
            )
        else:
            return await repository.get_by_organization(
                organization_id, status=status, device_type=device_type, skip=skip, limit=limit
            )

    async def get_device_statistics(
        self,
        organization_id: uuid.UUID,
        *,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get device statistics for an organization.

        Args:
            organization_id: Organization identifier
            session: Optional database session

        Returns:
            Device statistics
        """
        repository = self.get_repository(session)

        # Get status counts
        status_counts = await repository.count_by_status(organization_id)

        # Get stale devices
        stale_devices = await repository.get_stale_devices(organization_id)

        return {
            'total_devices': sum(status_counts.values()),
            'status_counts': status_counts,
            'stale_devices_count': len(stale_devices),
            'online_percentage': (
                status_counts.get('online', 0) / sum(status_counts.values()) * 100
                if sum(status_counts.values()) > 0 else 0
            )
        }

    async def get_list_with_filters(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[Device], int]:
        """
        Get paginated list of devices with filters.

        Args:
            filters: Dictionary of filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            session: Optional database session

        Returns:
            Tuple of (list of devices, total count)
        """
        if session:
            repo = self.get_repository(session)
            items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
            total = await repo.count(filters=filters)
            return items, total
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
                total = await repo.count(filters=filters)
                return items, total

    async def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate device creation data."""
        required_fields = ['name', 'organization_id', 'device_type']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Field '{field}' is required", field=field)

        # Validate device type
        if 'device_type' in data:
            try:
                DeviceType(data['device_type'])
            except ValueError:
                raise ValidationError(f"Invalid device type: {data['device_type']}", field='device_type')

    async def count_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Count devices for an organization with optional filters.

        Args:
            organization_id: Organization identifier
            filters: Optional additional filters
            session: Optional database session

        Returns:
            Number of devices
        """
        base_filters = {"organization_id": organization_id}
        if filters:
            base_filters.update(filters)

        if session:
            repo = self.get_repository(session)
            return await repo.count(filters=base_filters)
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                return await repo.count(filters=base_filters)


# ===== EXPERIMENT SERVICE =====

class ExperimentService(BaseService[Experiment, ExperimentRepository]):
    """Service for experiment management business logic."""

    def __init__(self):
        super().__init__(ExperimentRepository, Experiment)

    async def get_list_with_filters(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[Experiment], int]:
        """
        Get paginated list of experiments with filters.

        Args:
            filters: Dictionary of filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            session: Optional database session

        Returns:
            Tuple of (list of experiments, total count)
        """
        if session:
            repo = self.get_repository(session)
            items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
            total = await repo.count(filters=filters)
            return items, total
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
                total = await repo.count(filters=filters)
                return items, total

    async def create_experiment(
        self,
        experiment_data: Dict[str, Any],
        device_ids: Optional[List[uuid.UUID]] = None,
        task_ids: Optional[List[uuid.UUID]] = None,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Experiment:
        """
        Create new experiment with associated devices and tasks.

        Args:
            experiment_data: Experiment data
            device_ids: Optional list of device IDs to associate
            task_ids: Optional list of task IDs to associate
            current_user_id: ID of the user creating the experiment
            session: Optional database session

        Returns:
            Created experiment
        """
        # Set initial experiment status if not provided
        if 'status' not in experiment_data or experiment_data['status'] is None:
            experiment_data['status'] = ExperimentStatus.DRAFT

        # Create experiment
        experiment = await self.create(
            experiment_data,
            current_user_id=current_user_id,
            session=session
        )

        repository = self.get_repository(session)

        # Associate devices if provided
        if device_ids:
            for device_id in device_ids:
                await repository.add_device_to_experiment(experiment.id, device_id)

        # Associate tasks if provided
        if task_ids:
            for i, task_id in enumerate(task_ids):
                await repository.add_task_to_experiment(experiment.id, task_id, i + 1)

        return experiment

    async def start_experiment(
        self,
        experiment_id: uuid.UUID,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Experiment:
        """
        Start an experiment if conditions are met.

        Args:
            experiment_id: Experiment identifier
            current_user_id: ID of the user starting the experiment
            session: Optional database session

        Returns:
            Updated experiment

        Raises:
            ConflictError: If experiment cannot be started
        """
        experiment = await self.get_by_id(experiment_id, current_user_id=current_user_id, session=session)

        # Validate experiment can be started
        if experiment.status != ExperimentStatus.READY:
            raise ConflictError(f"Experiment must be in READY status to start, current status: {experiment.status}")

        # Check if devices are available
        repository = self.get_repository(session)
        experiment_with_devices = await repository.get_with_devices(experiment_id)

        if not experiment_with_devices.devices:
            raise ConflictError("Experiment must have at least one device to start")

        # Update experiment status
        update_data = {
            'status': ExperimentStatus.RUNNING,
            'actual_start_at': datetime.now(timezone.utc)
        }

        return await self.update(experiment_id, update_data, current_user_id=current_user_id, session=session)

    async def ready_experiment(
        self,
        experiment_id: uuid.UUID,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Experiment:
        """
        Ready an experiment (transition from draft to ready).

        Args:
            experiment_id: Experiment identifier
            current_user_id: ID of the user readying the experiment
            session: Optional database session

        Returns:
            Updated experiment

        Raises:
            ConflictError: If experiment cannot be readied
        """
        experiment = await self.get_by_id(experiment_id, current_user_id=current_user_id, session=session)

        # Validate experiment can be readied
        if experiment.status != ExperimentStatus.DRAFT:
            raise ConflictError(f"Experiment must be in DRAFT status to ready, current status: {experiment.status}")

        # Update experiment status
        update_data = {
            'status': ExperimentStatus.READY
        }

        return await self.update(experiment_id, update_data, current_user_id=current_user_id, session=session)

    async def pause_experiment(
        self,
        experiment_id: uuid.UUID,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Experiment:
        """
        Pause a running experiment.

        Args:
            experiment_id: Experiment identifier
            current_user_id: ID of the user pausing the experiment
            session: Optional database session

        Returns:
            Updated experiment

        Raises:
            ConflictError: If experiment cannot be paused
        """
        experiment = await self.get_by_id(experiment_id, current_user_id=current_user_id, session=session)

        # Validate experiment can be paused
        if experiment.status != ExperimentStatus.RUNNING:
            raise ConflictError(f"Only running experiments can be paused, current status: {experiment.status}")

        # Update experiment status
        update_data = {
            'status': ExperimentStatus.PAUSED
        }

        return await self.update(experiment_id, update_data, current_user_id=current_user_id, session=session)

    async def resume_experiment(
        self,
        experiment_id: uuid.UUID,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Experiment:
        """
        Resume a paused experiment.

        Args:
            experiment_id: Experiment identifier
            current_user_id: ID of the user resuming the experiment
            session: Optional database session

        Returns:
            Updated experiment

        Raises:
            ConflictError: If experiment cannot be resumed
        """
        experiment = await self.get_by_id(experiment_id, current_user_id=current_user_id, session=session)

        # Validate experiment can be resumed
        if experiment.status != ExperimentStatus.PAUSED:
            raise ConflictError(f"Only paused experiments can be resumed, current status: {experiment.status}")

        # Update experiment status
        update_data = {
            'status': ExperimentStatus.RUNNING
        }

        return await self.update(experiment_id, update_data, current_user_id=current_user_id, session=session)

    async def cancel_experiment(
        self,
        experiment_id: uuid.UUID,
        reason: Optional[str] = None,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Experiment:
        """
        Cancel an experiment from any state (except completed).

        Args:
            experiment_id: Experiment identifier
            reason: Optional cancellation reason
            current_user_id: ID of the user canceling the experiment
            session: Optional database session

        Returns:
            Updated experiment

        Raises:
            ConflictError: If experiment cannot be canceled
        """
        experiment = await self.get_by_id(experiment_id, current_user_id=current_user_id, session=session)

        # Validate experiment can be canceled (any state except completed)
        if experiment.status == ExperimentStatus.COMPLETED:
            raise ConflictError("Completed experiments cannot be canceled")

        # Update experiment status
        update_data = {
            'status': ExperimentStatus.CANCELLED,
            'actual_end_at': datetime.now(timezone.utc)
        }

        if reason:
            update_data['cancellation_reason'] = reason

        return await self.update(experiment_id, update_data, current_user_id=current_user_id, session=session)

    async def complete_experiment(
        self,
        experiment_id: uuid.UUID,
        results_summary: Optional[Dict[str, Any]] = None,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Experiment:
        """
        Complete an experiment with optional results.

        Args:
            experiment_id: Experiment identifier
            results_summary: Optional results summary
            current_user_id: ID of the user completing the experiment
            session: Optional database session

        Returns:
            Updated experiment
        """
        experiment = await self.get_by_id(experiment_id, current_user_id=current_user_id, session=session)

        if experiment.status != ExperimentStatus.RUNNING:
            raise ConflictError(f"Only running experiments can be completed, current status: {experiment.status}")

        update_data = {
            'status': ExperimentStatus.COMPLETED,
            'actual_end_at': datetime.now(timezone.utc)
        }

        if results_summary:
            update_data['results_summary'] = results_summary

        return await self.update(experiment_id, update_data, current_user_id=current_user_id, session=session)

    async def get_experiment_statistics(
        self,
        organization_id: uuid.UUID,
        *,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get experiment statistics for an organization.

        Args:
            organization_id: Organization identifier
            session: Optional database session

        Returns:
            Experiment statistics
        """
        repository = self.get_repository(session)

        # Get status counts
        status_counts = await repository.count_by_status(organization_id)

        # Get active experiments
        active_experiments = await repository.get_active_experiments(organization_id)

        return {
            'total_experiments': sum(status_counts.values()),
            'status_counts': status_counts,
            'active_experiments_count': len(active_experiments),
            'completion_rate': (
                status_counts.get('completed', 0) / sum(status_counts.values()) * 100
                if sum(status_counts.values()) > 0 else 0
            )
        }

    async def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate experiment creation data."""
        required_fields = ['name', 'organization_id']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Field '{field}' is required", field=field)

        # Validate dates if provided
        if 'scheduled_start_at' in data and 'scheduled_end_at' in data:
            start_time = data['scheduled_start_at']
            end_time = data['scheduled_end_at']

            # Only validate if both values are not None
            if start_time is not None and end_time is not None:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

                if start_time >= end_time:
                    raise ValidationError("Scheduled end time must be after start time")

    async def count_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Count experiments for an organization with optional filters.

        Args:
            organization_id: Organization identifier
            filters: Optional additional filters
            session: Optional database session

        Returns:
            Number of experiments
        """
        base_filters = {"organization_id": organization_id}
        if filters:
            base_filters.update(filters)

        if session:
            repo = self.get_repository(session)
            return await repo.count(filters=base_filters)
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                return await repo.count(filters=base_filters)


# ===== TASK SERVICE =====

class TaskService(BaseService[Task, TaskRepository]):
    """Service for task management business logic."""

    def __init__(self):
        super().__init__(TaskRepository, Task)

    async def get_list_with_filters(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[Task], int]:
        """
        Get paginated list of tasks with filters.

        Args:
            filters: Dictionary of filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            session: Optional database session

        Returns:
            Tuple of (list of tasks, total count)
        """
        if session:
            repo = self.get_repository(session)
            items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
            total = await repo.count(filters=filters)
            return items, total
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
                total = await repo.count(filters=filters)
                return items, total

    async def create_task_from_template(
        self,
        template_id: uuid.UUID,
        task_data: Dict[str, Any],
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Task:
        """
        Create a new task from an existing template.

        Args:
            template_id: Template task identifier
            task_data: Task-specific data (overrides template)
            current_user_id: ID of the user creating the task
            session: Optional database session

        Returns:
            Created task
        """
        # Get template task
        template = await self.get_by_id(template_id, current_user_id=current_user_id, session=session)

        if not template.is_template:
            raise ValidationError("Source task must be a template")

        # Merge template data with provided data
        new_task_data = {
            'name': task_data.get('name', f"{template.name} (Copy)"),
            'description': task_data.get('description', template.description),
            'category': task_data.get('category', template.category),
            'task_definition': task_data.get('task_definition', template.task_definition),
            'parameters': task_data.get('parameters', template.parameters),
            'organization_id': task_data['organization_id'],
            'is_template': False,
            'created_from_template_id': template_id
        }

        return await self.create(new_task_data, current_user_id=current_user_id, session=session)

    async def validate_task_definition(
        self,
        task_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate task definition structure and content.

        Args:
            task_definition: Task definition to validate

        Returns:
            Validation results with errors/warnings

        Raises:
            ValidationError: If task definition is invalid
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Basic structure validation
        required_fields = ['nodes', 'edges']
        for field in required_fields:
            if field not in task_definition:
                validation_result['errors'].append(f"Missing required field: {field}")

        if validation_result['errors']:
            validation_result['valid'] = False
            return validation_result

        # Validate nodes
        nodes = task_definition.get('nodes', [])
        if not nodes:
            validation_result['errors'].append("Task must have at least one node")

        # Check for start and end nodes
        node_types = [node.get('type') for node in nodes]
        if 'start' not in node_types:
            validation_result['errors'].append("Task must have a start node")
        if 'end' not in node_types:
            validation_result['errors'].append("Task must have an end node")

        # Validate edges
        edges = task_definition.get('edges', [])
        node_ids = [node.get('id') for node in nodes]

        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')

            if source not in node_ids:
                validation_result['errors'].append(f"Edge source '{source}' not found in nodes")
            if target not in node_ids:
                validation_result['errors'].append(f"Edge target '{target}' not found in nodes")

        # Check for unreachable nodes (warning)
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get('source'))
            connected_nodes.add(edge.get('target'))

        disconnected_nodes = set(node_ids) - connected_nodes
        if disconnected_nodes:
            validation_result['warnings'].append(f"Disconnected nodes found: {disconnected_nodes}")

        validation_result['valid'] = len(validation_result['errors']) == 0

        if not validation_result['valid']:
            raise ValidationError("Task definition validation failed", details=validation_result)

        return validation_result

    async def search_tasks(
        self,
        organization_id: uuid.UUID,
        search_term: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        session: Optional[AsyncSession] = None
    ) -> List[Task]:
        """
        Search tasks by name, description, or tags.

        Args:
            organization_id: Organization identifier
            search_term: Search term
            filters: Additional filters
            skip: Number of tasks to skip
            limit: Maximum number of tasks to return
            session: Optional database session

        Returns:
            List of matching tasks
        """
        repository = self.get_repository(session)
        return await repository.search_tasks(organization_id, search_term, skip=skip, limit=limit)

    async def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate task creation data."""
        required_fields = ['name', 'organization_id']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Field '{field}' is required", field=field)

        # Check for task definition (can be either 'definition' or 'task_definition')
        task_def = data.get('task_definition') or data.get('definition')
        if not task_def:
            raise ValidationError("Field 'task_definition' is required", field='task_definition')

        # Validate task definition if provided
        await self.validate_task_definition(task_def)

        # Ensure the data has the correct field name for model creation
        # The Task model expects 'definition', so ensure it exists
        if 'task_definition' in data and 'definition' not in data:
            data['definition'] = data['task_definition']
        # Remove task_definition to avoid passing it to the model constructor
        if 'task_definition' in data:
            del data['task_definition']

    async def publish_task(
        self,
        task_id: uuid.UUID,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Task:
        """
        Publish a task to make it available to other organizations.

        Args:
            task_id: Task identifier
            current_user_id: ID of the user publishing the task
            session: Optional database session

        Returns:
            Updated task with published status

        Raises:
            NotFoundError: If task not found
            ConflictError: If task cannot be published
        """
        task = await self.get_by_id(task_id, current_user_id=current_user_id, session=session)

        # Validate task can be published
        if task.is_published:
            raise ConflictError("Task is already published")

        # Update task to published status
        update_data = {
            'is_published': True,
            'is_template': True  # Published tasks become templates
        }

        if session:
            repo = self.get_repository(session)
            updated_task = await repo.update(task_id, **update_data)
            await session.commit()
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                updated_task = await repo.update(task_id, **update_data)
                await db_session.commit()

        logger.info(f"Task {task_id} published by user {current_user_id}")
        return updated_task

    async def clone_task(
        self,
        task_id: uuid.UUID,
        new_name: Optional[str] = None,
        new_organization_id: Optional[uuid.UUID] = None,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Task:
        """
        Clone a task to create a copy.

        Args:
            task_id: Source task identifier
            new_name: Optional name for the cloned task
            new_organization_id: Organization ID for the cloned task
            current_user_id: ID of the user cloning the task
            session: Optional database session

        Returns:
            New cloned task

        Raises:
            NotFoundError: If source task not found
            ValidationError: If task cannot be cloned
        """
        source_task = await self.get_by_id(task_id, session=session)

        # Validate source task can be cloned
        if not source_task.is_published and not source_task.is_template:
            raise ValidationError("Only published tasks or templates can be cloned")

        # Prepare cloned task data
        cloned_data = {
            'name': new_name or f"{source_task.name} (Clone)",
            'description': source_task.description,
            'definition': source_task.definition,
            'category': source_task.category,
            'version': '1.0.0',  # Reset version for cloned task
            'author_id': current_user_id,
            'is_template': False,  # Cloned tasks are not templates by default
            'is_public': False,
            'is_published': False,  # Cloned tasks are not published by default
            'parameters_schema': source_task.parameters_schema,
            'default_parameters': source_task.default_parameters,
            'required_capabilities': source_task.required_capabilities,
            'supported_device_types': source_task.supported_device_types,
            'estimated_duration_minutes': source_task.estimated_duration_minutes,
            'max_execution_time_minutes': source_task.max_execution_time_minutes,
            'organization_id': new_organization_id or current_user_id
        }

        # Create cloned task
        if session:
            repo = self.get_repository(session)
            cloned_task = await repo.create(**cloned_data)
            await session.commit()
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                cloned_task = await repo.create(**cloned_data)
                await db_session.commit()

        logger.info(f"Task {task_id} cloned as {cloned_task.id} by user {current_user_id}")
        return cloned_task

    async def count_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Count tasks for an organization with optional filters.

        Args:
            organization_id: Organization identifier
            filters: Optional additional filters
            session: Optional database session

        Returns:
            Number of tasks
        """
        base_filters = {"organization_id": organization_id}
        if filters:
            base_filters.update(filters)

        if session:
            repo = self.get_repository(session)
            return await repo.count(filters=base_filters)
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                return await repo.count(filters=base_filters)


# ===== PARTICIPANT SERVICE =====

class ParticipantService(BaseService[Participant, ParticipantRepository]):
    """Service for participant management business logic."""

    def __init__(self):
        super().__init__(ParticipantRepository, Participant)

    async def get_list_with_filters(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[Participant], int]:
        """
        Get paginated list of participants with filters.

        Args:
            filters: Dictionary of filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            session: Optional database session

        Returns:
            Tuple of (list of participants, total count)
        """
        if session:
            repo = self.get_repository(session)
            items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
            total = await repo.count(filters=filters)
            return items, total
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
                total = await repo.count(filters=filters)
                return items, total

    async def enroll_participant(
        self,
        experiment_id: uuid.UUID,
        participant_data: Dict[str, Any],
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Participant:
        """
        Enroll a new participant in an experiment.

        Args:
            experiment_id: Experiment identifier
            participant_data: Participant data
            current_user_id: ID of the user enrolling the participant
            session: Optional database session

        Returns:
            Enrolled participant

        Raises:
            ConflictError: If participant already exists
        """
        # Check for existing participant with same participant_id
        repository = self.get_repository(session)
        existing_participant = await repository.get_by_identifier(
            experiment_id, participant_data['participant_id']
        )

        if existing_participant:
            raise ConflictError(
                f"Participant with participant_id '{participant_data['participant_id']}' already exists in this experiment"
            )

        # Set enrollment data
        participant_data.update({
            'experiment_id': experiment_id,
            'status': ParticipantStatus.ACTIVE,
            'enrollment_date': datetime.now(timezone.utc)
        })

        return await self.create(participant_data, current_user_id=current_user_id, session=session)

    async def withdraw_participant(
        self,
        participant_id: uuid.UUID,
        reason: Optional[str] = None,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Participant:
        """
        Withdraw a participant from an experiment.

        Args:
            participant_id: Participant identifier
            reason: Optional withdrawal reason
            current_user_id: ID of the user withdrawing the participant
            session: Optional database session

        Returns:
            Updated participant
        """
        participant = await self.get_by_id(participant_id, current_user_id=current_user_id, session=session)

        if participant.status == ParticipantStatus.WITHDRAWN:
            raise ConflictError("Participant is already withdrawn")

        update_data = {
            'status': ParticipantStatus.WITHDRAWN,
            'completion_date': datetime.now(timezone.utc)
        }

        if reason:
            if not participant.participant_metadata:
                participant.participant_metadata = {}
            participant.participant_metadata['withdrawal_reason'] = reason
            update_data['participant_metadata'] = participant.participant_metadata

        return await self.update(participant_id, update_data, current_user_id=current_user_id, session=session)

    async def get_participant_statistics(
        self,
        experiment_id: uuid.UUID,
        *,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get participant statistics for an experiment.

        Args:
            experiment_id: Experiment identifier
            session: Optional database session

        Returns:
            Participant statistics
        """
        repository = self.get_repository(session)

        # Get status counts
        status_counts = await repository.count_by_status(experiment_id)

        return {
            'total_participants': sum(status_counts.values()),
            'status_counts': status_counts,
            'completion_rate': (
                status_counts.get('completed', 0) / sum(status_counts.values()) * 100
                if sum(status_counts.values()) > 0 else 0
            ),
            'withdrawal_rate': (
                status_counts.get('withdrawn', 0) / sum(status_counts.values()) * 100
                if sum(status_counts.values()) > 0 else 0
            )
        }

    async def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate participant creation data."""
        required_fields = ['participant_id', 'species']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Field '{field}' is required", field=field)

        # If experiment_id is provided, validate it exists
        if 'experiment_id' in data and data['experiment_id'] is not None:
            # This is a basic validation - the repository will handle the existence check
            pass  # We could add experiment existence validation here if needed


# ===== TASK EXECUTION SERVICE =====

class TaskExecutionService(BaseService[TaskExecution, TaskExecutionRepository]):
    """Service for task execution management business logic."""

    def __init__(self):
        super().__init__(TaskExecutionRepository, TaskExecution)

    async def start_task_execution(
        self,
        task_id: uuid.UUID,
        device_id: uuid.UUID,
        experiment_id: Optional[uuid.UUID] = None,
        participant_id: Optional[uuid.UUID] = None,
        execution_parameters: Optional[Dict[str, Any]] = None,
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> TaskExecution:
        """
        Start a new task execution.

        Args:
            task_id: Task identifier
            device_id: Device identifier
            experiment_id: Optional experiment identifier
            participant_id: Optional participant identifier
            execution_parameters: Optional execution parameters
            current_user_id: ID of the user starting the execution
            session: Optional database session

        Returns:
            Started task execution
        """
        import secrets

        # Get task to obtain organization_id
        task_service = TaskService()
        task = await task_service.get_by_id(task_id, session=session)
        if not task:
            raise NotFoundError(f"Task {task_id} not found")

        execution_data = {
            'execution_id': secrets.token_hex(16),
            'task_id': task_id,
            'device_id': device_id,
            'experiment_id': experiment_id,
            'participant_id': participant_id,
            'organization_id': task.organization_id,
            'status': TaskStatus.RUNNING,
            'started_at': datetime.now(timezone.utc),
            'parameters': execution_parameters or {}
        }

        return await self.create(execution_data, current_user_id=current_user_id, session=session)

    async def complete_task_execution(
        self,
        execution_id: str,
        result_data: Optional[Dict[str, Any]] = None,
        *,
        session: Optional[AsyncSession] = None
    ) -> Optional[TaskExecution]:
        """
        Complete a task execution with results.

        Args:
            execution_id: Execution identifier
            result_data: Optional execution results
            session: Optional database session

        Returns:
            Updated task execution
        """
        repository = self.get_repository(session)
        return await repository.update_execution_status(
            execution_id, TaskStatus.COMPLETED, result_data=result_data
        )

    async def fail_task_execution(
        self,
        execution_id: str,
        error_message: str,
        *,
        session: Optional[AsyncSession] = None
    ) -> Optional[TaskExecution]:
        """
        Mark a task execution as failed with error message.

        Args:
            execution_id: Execution identifier
            error_message: Error description
            session: Optional database session

        Returns:
            Updated task execution
        """
        repository = self.get_repository(session)
        return await repository.update_execution_status(
            execution_id, TaskStatus.FAILED, error_message=error_message
        )

    async def get_execution_statistics(
        self,
        experiment_id: uuid.UUID,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get execution statistics for an experiment.

        Args:
            experiment_id: Experiment identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            session: Optional database session

        Returns:
            Execution statistics
        """
        repository = self.get_repository(session)
        return await repository.get_execution_statistics(experiment_id, start_date, end_date)

    async def get_list_with_filters(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[TaskExecution], int]:
        """
        Get paginated list of task executions with filters.

        Args:
            filters: Dictionary of filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            session: Optional database session

        Returns:
            Tuple of (list of task executions, total count)
        """
        if session:
            repo = self.get_repository(session)
            items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
            total = await repo.count(filters=filters)
            return items, total
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                items = await repo.get_by_filter(filters=filters, skip=skip, limit=limit)
                total = await repo.count(filters=filters)
                return items, total

    async def get_execution_history(
        self,
        task_id: uuid.UUID,
        *,
        session: Optional[AsyncSession] = None
    ) -> List[TaskExecution]:
        """
        Get execution history for a specific task.

        Args:
            task_id: Task identifier
            session: Optional database session

        Returns:
            List of task executions
        """
        filters = {"task_id": task_id}
        if session:
            repo = self.get_repository(session)
            return await repo.get_by_filter(filters=filters, order_by="started_at", order_desc=True)
        else:
            async with db_manager.session_scope() as db_session:
                repo = self.get_repository(db_session)
                return await repo.get_by_filter(filters=filters, order_by="started_at", order_desc=True)


# ===== DEVICE DATA SERVICE =====

class DeviceDataService(BaseService[DeviceData, DeviceDataRepository]):
    """Service for device data management business logic."""

    def __init__(self):
        super().__init__(DeviceDataRepository, DeviceData)

    async def record_telemetry_data(
        self,
        device_id: uuid.UUID,
        data_points: List[Dict[str, Any]],
        *,
        session: Optional[AsyncSession] = None
    ) -> List[DeviceData]:
        """
        Record multiple telemetry data points from a device.

        Args:
            device_id: Device identifier
            data_points: List of data point dictionaries
            session: Optional database session

        Returns:
            List of created data records
        """
        # Get device to inherit organization_id
        device_service = DeviceService()
        device = await device_service.get_by_id(device_id, session=session)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        # Prepare data points with common fields
        for data_point in data_points:
            data_point['device_id'] = device_id
            data_point['organization_id'] = device.organization_id
            if 'timestamp' not in data_point:
                data_point['timestamp'] = datetime.now(timezone.utc)

        repository = self.get_repository(session)
        return await repository.create_many(data_points)

    async def get_device_telemetry(
        self,
        device_id: uuid.UUID,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        data_type: Optional[str] = None,
        aggregated: bool = False,
        interval_minutes: int = 60,
        skip: int = 0,
        limit: int = 1000,
        session: Optional[AsyncSession] = None
    ) -> Union[List[DeviceData], List[Dict[str, Any]]]:
        """
        Get telemetry data for a device with optional aggregation.

        Args:
            device_id: Device identifier
            start_time: Optional start time filter
            end_time: Optional end time filter
            data_type: Optional data type filter
            aggregated: Whether to return aggregated data
            interval_minutes: Aggregation interval in minutes
            skip: Number of records to skip
            limit: Maximum number of records to return
            session: Optional database session

        Returns:
            List of data records or aggregated data
        """
        repository = self.get_repository(session)

        if aggregated and start_time and end_time and data_type:
            return await repository.get_aggregated_data(
                device_id, data_type, start_time, end_time, interval_minutes
            )
        elif start_time and end_time:
            return await repository.get_by_device_and_timerange(
                device_id, start_time, end_time, data_type, skip=skip, limit=limit
            )
        else:
            return await repository.get_latest_by_device(device_id, data_type, limit=limit)

    async def cleanup_old_telemetry(
        self,
        retention_days: int = 30,
        *,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Clean up old telemetry data beyond retention period.

        Args:
            retention_days: Number of days to retain data
            session: Optional database session

        Returns:
            Number of records deleted
        """
        repository = self.get_repository(session)
        return await repository.cleanup_old_data(retention_days)

    async def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate device data creation."""
        required_fields = ['device_id', 'data_type']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Field '{field}' is required", field=field)

        # Validate that either numeric_value or text_value is provided
        if not data.get('numeric_value') and not data.get('text_value'):
            raise ValidationError("Either numeric_value or text_value must be provided")
"""
Comprehensive unit tests for domain models (Device, Experiment, Task, Participant, etc.).

Tests cover:
- Model creation and validation
- Relationships between models
- Enum constraints
- Unique constraints
- JSON field operations
- Soft delete functionality
- Audit trails
- Multi-tenancy (organization isolation)
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models.domain import (
    Device, DeviceStatus, DeviceType,
    Experiment, ExperimentStatus,
    Task, TaskStatus,
    Participant, ParticipantStatus,
    TaskExecution,
    DeviceData,
)
from app.models.base import Organization
from app.models.auth import User
from app.core.security import get_password_hash


# ===== FIXTURES =====

@pytest_asyncio.fixture
async def test_organization(db_session):
    """Create a test organization."""
    org = Organization(
        name=f"Test Org {uuid4().hex[:8]}",
        description="Test organization for domain model tests"
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session, test_organization):
    """Create a test user."""
    user = User(
        email=f"test{uuid4().hex[:8]}@example.com",
        username=f"testuser{uuid4().hex[:8]}",
        password_hash=get_password_hash("TestPassword123!"),
        organization_id=test_organization.id,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_device(db_session, test_organization, test_user):
    """Create a test device."""
    device = Device(
        name=f"Test Device {uuid4().hex[:8]}",
        description="Test device for experiments",
        device_type=DeviceType.RASPBERRY_PI,
        status=DeviceStatus.ONLINE,
        serial_number=f"SN-{uuid4().hex[:12]}",
        organization_id=test_organization.id,
        created_by=test_user.id,
        hardware_config={"cpu": "ARM", "ram": "4GB"},
        capabilities={"sensors": ["temp", "humidity"], "actuators": ["led"]}
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest_asyncio.fixture
async def test_task(db_session, test_organization, test_user):
    """Create a test task."""
    task = Task(
        name=f"Test Task {uuid4().hex[:8]}",
        description="Test task definition",
        version="1.0.0",
        task_definition={"nodes": [], "edges": []},
        organization_id=test_organization.id,
        created_by=test_user.id
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_participant(db_session, test_organization, test_user):
    """Create a test participant."""
    participant = Participant(
        identifier=f"P-{uuid4().hex[:8]}",
        name=f"Participant {uuid4().hex[:8]}",
        status=ParticipantStatus.ACTIVE,
        organization_id=test_organization.id,
        created_by=test_user.id
    )
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)
    return participant


# ===== DEVICE MODEL TESTS =====

class TestDeviceModel:
    """Test Device model."""

    @pytest.mark.asyncio
    async def test_create_device(self, db_session, test_organization, test_user):
        """Test creating a device with all fields."""
        device = Device(
            name="Test Device Full",
            description="Complete device with all fields",
            device_type=DeviceType.RASPBERRY_PI,
            serial_number=f"SN-{uuid4().hex[:12]}",
            mac_address="AA:BB:CC:DD:EE:FF",
            ip_address="192.168.1.100",
            status=DeviceStatus.ONLINE,
            is_active=True,
            location="Lab A, Cage 1",
            hardware_config={"cpu": "ARM Cortex-A72", "ram": "4GB", "storage": "32GB"},
            software_config={"os": "Raspberry Pi OS", "python": "3.11"},
            capabilities={"sensors": ["temp", "humidity", "motion"], "actuators": ["led", "buzzer"]},
            firmware_version="1.0.0",
            agent_version="0.1.0",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        assert device.id is not None
        assert device.name == "Test Device Full"
        assert device.device_type == DeviceType.RASPBERRY_PI
        assert device.status == DeviceStatus.ONLINE
        assert device.is_active is True
        assert device.organization_id == test_organization.id
        assert device.created_by == test_user.id
        assert device.hardware_config["cpu"] == "ARM Cortex-A72"
        assert "temp" in device.capabilities["sensors"]

    @pytest.mark.asyncio
    async def test_device_unique_serial_number(self, db_session, test_organization, test_user):
        """Test that device serial numbers must be unique."""
        serial = f"SN-{uuid4().hex[:12]}"

        device1 = Device(
            name="Device 1",
            serial_number=serial,
            device_type=DeviceType.RASPBERRY_PI,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device1)
        await db_session.commit()

        device2 = Device(
            name="Device 2",
            serial_number=serial,
            device_type=DeviceType.ARDUINO,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_device_unique_name_per_organization(self, db_session, test_organization, test_user):
        """Test that device names must be unique within an organization."""
        device_name = f"Device {uuid4().hex[:8]}"

        device1 = Device(
            name=device_name,
            device_type=DeviceType.RASPBERRY_PI,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device1)
        await db_session.commit()

        device2 = Device(
            name=device_name,
            device_type=DeviceType.ARDUINO,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_device_status_enum(self, db_session, test_organization, test_user):
        """Test device status enum values."""
        for status in DeviceStatus:
            device = Device(
                name=f"Device {status.value}",
                device_type=DeviceType.RASPBERRY_PI,
                status=status,
                organization_id=test_organization.id,
                created_by=test_user.id
            )
            db_session.add(device)
            await db_session.commit()
            await db_session.refresh(device)

            assert device.status == status

    @pytest.mark.asyncio
    async def test_device_type_enum(self, db_session, test_organization, test_user):
        """Test device type enum values."""
        for device_type in DeviceType:
            device = Device(
                name=f"Device {device_type.value}",
                device_type=device_type,
                organization_id=test_organization.id,
                created_by=test_user.id
            )
            db_session.add(device)
            await db_session.commit()
            await db_session.refresh(device)

            assert device.device_type == device_type

    @pytest.mark.asyncio
    async def test_device_heartbeat_tracking(self, db_session, test_device):
        """Test device heartbeat timestamp tracking."""
        now = datetime.now(timezone.utc)
        test_device.last_heartbeat_at = now
        await db_session.commit()
        await db_session.refresh(test_device)

        assert test_device.last_heartbeat_at is not None
        assert abs((test_device.last_heartbeat_at - now).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_device_performance_metrics(self, db_session, test_device):
        """Test device performance metrics fields."""
        test_device.uptime_hours = 72.5
        test_device.cpu_usage_percent = 45.2
        test_device.memory_usage_percent = 67.8
        test_device.disk_usage_percent = 34.1
        test_device.temperature_celsius = 42.5

        await db_session.commit()
        await db_session.refresh(test_device)

        assert test_device.uptime_hours == 72.5
        assert test_device.cpu_usage_percent == 45.2
        assert test_device.memory_usage_percent == 67.8
        assert test_device.disk_usage_percent == 34.1
        assert test_device.temperature_celsius == 42.5

    @pytest.mark.asyncio
    async def test_device_soft_delete(self, db_session, test_device):
        """Test device soft delete functionality."""
        device_id = test_device.id

        # Soft delete
        test_device.deleted_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Should still exist in database
        result = await db_session.execute(
            select(Device).where(Device.id == device_id)
        )
        found_device = result.scalar_one_or_none()
        assert found_device is not None
        assert found_device.deleted_at is not None


# ===== EXPERIMENT MODEL TESTS =====

class TestExperimentModel:
    """Test Experiment model."""

    @pytest.mark.asyncio
    async def test_create_experiment(self, db_session, test_organization, test_user):
        """Test creating an experiment."""
        experiment = Experiment(
            name="Test Experiment",
            description="Testing experiment creation",
            protocol="Test protocol description",
            status=ExperimentStatus.DRAFT,
            organization_id=test_organization.id,
            created_by=test_user.id,
            experiment_metadata={"study_type": "behavioral", "duration_days": 7}
        )
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        assert experiment.id is not None
        assert experiment.name == "Test Experiment"
        assert experiment.status == ExperimentStatus.DRAFT
        assert experiment.experiment_metadata["study_type"] == "behavioral"

    @pytest.mark.asyncio
    async def test_experiment_status_transitions(self, db_session, test_organization, test_user):
        """Test experiment status lifecycle."""
        experiment = Experiment(
            name="Status Test Experiment",
            status=ExperimentStatus.DRAFT,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        # Test status transitions
        statuses = [
            ExperimentStatus.READY,
            ExperimentStatus.RUNNING,
            ExperimentStatus.PAUSED,
            ExperimentStatus.RUNNING,
            ExperimentStatus.COMPLETED
        ]

        for status in statuses:
            experiment.status = status
            await db_session.commit()
            await db_session.refresh(experiment)
            assert experiment.status == status

    @pytest.mark.asyncio
    async def test_experiment_device_relationship(self, db_session, test_organization, test_user, test_device):
        """Test experiment-device many-to-many relationship."""
        experiment = Experiment(
            name="Device Relationship Test",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        experiment.devices.append(test_device)
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        assert len(experiment.devices) == 1
        assert experiment.devices[0].id == test_device.id

    @pytest.mark.asyncio
    async def test_experiment_task_relationship(self, db_session, test_organization, test_user, test_task):
        """Test experiment-task many-to-many relationship."""
        experiment = Experiment(
            name="Task Relationship Test",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        experiment.tasks.append(test_task)
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        assert len(experiment.tasks) == 1
        assert experiment.tasks[0].id == test_task.id

    @pytest.mark.asyncio
    async def test_experiment_participant_relationship(self, db_session, test_organization, test_user, test_participant):
        """Test experiment-participant one-to-many relationship."""
        experiment = Experiment(
            name="Participant Relationship Test",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        test_participant.experiment_id = experiment.id
        await db_session.commit()
        await db_session.refresh(experiment)

        assert len(experiment.participants) == 1
        assert experiment.participants[0].id == test_participant.id

    @pytest.mark.asyncio
    async def test_experiment_scheduling(self, db_session, test_organization, test_user):
        """Test experiment scheduling fields."""
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(days=7)

        experiment = Experiment(
            name="Scheduled Experiment",
            scheduled_start=start_time,
            scheduled_end=end_time,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        assert experiment.scheduled_start == start_time
        assert experiment.scheduled_end == end_time
        assert experiment.actual_start is None
        assert experiment.actual_end is None

    @pytest.mark.asyncio
    async def test_experiment_actual_timing(self, db_session, test_organization, test_user):
        """Test experiment actual start/end tracking."""
        experiment = Experiment(
            name="Timing Test Experiment",
            status=ExperimentStatus.RUNNING,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()

        # Start experiment
        experiment.actual_start = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(experiment)

        assert experiment.actual_start is not None

        # End experiment
        experiment.status = ExperimentStatus.COMPLETED
        experiment.actual_end = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(experiment)

        assert experiment.actual_end is not None
        assert experiment.actual_end > experiment.actual_start


# ===== TASK MODEL TESTS =====

class TestTaskModel:
    """Test Task model."""

    @pytest.mark.asyncio
    async def test_create_task(self, db_session, test_organization, test_user):
        """Test creating a task."""
        task = Task(
            name="Test Task",
            description="Task for testing",
            version="1.0.0",
            task_definition={
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "action1", "type": "action", "params": {"device": "led", "action": "on"}},
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "action1"},
                    {"source": "action1", "target": "end"}
                ]
            },
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.id is not None
        assert task.name == "Test Task"
        assert task.version == "1.0.0"
        assert len(task.task_definition["nodes"]) == 3
        assert len(task.task_definition["edges"]) == 2

    @pytest.mark.asyncio
    async def test_task_versioning(self, db_session, test_organization, test_user):
        """Test task version tracking."""
        task_v1 = Task(
            name="Versioned Task",
            version="1.0.0",
            task_definition={"nodes": [], "edges": []},
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(task_v1)
        await db_session.commit()
        await db_session.refresh(task_v1)

        task_v2 = Task(
            name="Versioned Task",
            version="2.0.0",
            task_definition={"nodes": [{"id": "new"}], "edges": []},
            parent_task_id=task_v1.id,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(task_v2)
        await db_session.commit()
        await db_session.refresh(task_v2)

        assert task_v2.parent_task_id == task_v1.id
        assert task_v2.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_task_template_flag(self, db_session, test_organization, test_user):
        """Test task template functionality."""
        template = Task(
            name="Template Task",
            description="Reusable template",
            version="1.0.0",
            is_template=True,
            is_public=True,
            task_definition={"nodes": [], "edges": []},
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        assert template.is_template is True
        assert template.is_public is True

    @pytest.mark.asyncio
    async def test_task_validation_schema(self, db_session, test_organization, test_user):
        """Test task parameter schema validation."""
        task = Task(
            name="Schema Task",
            version="1.0.0",
            task_definition={"nodes": [], "edges": []},
            parameter_schema={
                "type": "object",
                "properties": {
                    "duration": {"type": "number", "minimum": 0},
                    "color": {"type": "string", "enum": ["red", "green", "blue"]}
                },
                "required": ["duration"]
            },
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.parameter_schema["type"] == "object"
        assert "duration" in task.parameter_schema["required"]


# ===== PARTICIPANT MODEL TESTS =====

class TestParticipantModel:
    """Test Participant model."""

    @pytest.mark.asyncio
    async def test_create_participant(self, db_session, test_organization, test_user):
        """Test creating a participant."""
        participant = Participant(
            identifier="P001",
            name="Test Subject",
            species="Rattus norvegicus",
            strain="Wistar",
            sex="M",
            date_of_birth=datetime(2023, 1, 1, tzinfo=timezone.utc),
            status=ParticipantStatus.ACTIVE,
            participant_metadata={"weight_g": 250, "cage": "A1"},
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(participant)
        await db_session.commit()
        await db_session.refresh(participant)

        assert participant.id is not None
        assert participant.identifier == "P001"
        assert participant.species == "Rattus norvegicus"
        assert participant.status == ParticipantStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_participant_unique_identifier_per_org(self, db_session, test_organization, test_user):
        """Test that participant identifiers must be unique within organization."""
        identifier = f"P-{uuid4().hex[:8]}"

        participant1 = Participant(
            identifier=identifier,
            name="Participant 1",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(participant1)
        await db_session.commit()

        participant2 = Participant(
            identifier=identifier,
            name="Participant 2",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(participant2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_participant_status_enum(self, db_session, test_organization, test_user):
        """Test participant status enum values."""
        for status in ParticipantStatus:
            participant = Participant(
                identifier=f"P-{status.value}",
                name=f"Participant {status.value}",
                status=status,
                organization_id=test_organization.id,
                created_by=test_user.id
            )
            db_session.add(participant)
            await db_session.commit()
            await db_session.refresh(participant)

            assert participant.status == status


# ===== TASK EXECUTION MODEL TESTS =====

class TestTaskExecutionModel:
    """Test TaskExecution model."""

    @pytest.mark.asyncio
    async def test_create_task_execution(self, db_session, test_organization, test_user, test_device, test_task):
        """Test creating a task execution."""
        experiment = Experiment(
            name="Execution Test Experiment",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        execution = TaskExecution(
            task_id=test_task.id,
            device_id=test_device.id,
            experiment_id=experiment.id,
            status=TaskStatus.PENDING,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.id is not None
        assert execution.task_id == test_task.id
        assert execution.device_id == test_device.id
        assert execution.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_task_execution_lifecycle(self, db_session, test_organization, test_user, test_device, test_task):
        """Test task execution status lifecycle."""
        experiment = Experiment(
            name="Lifecycle Test Experiment",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()

        execution = TaskExecution(
            task_id=test_task.id,
            device_id=test_device.id,
            experiment_id=experiment.id,
            status=TaskStatus.PENDING,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        # Start execution
        execution.status = TaskStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.status == TaskStatus.RUNNING
        assert execution.started_at is not None

        # Complete execution
        execution.status = TaskStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.status == TaskStatus.COMPLETED
        assert execution.completed_at is not None
        assert execution.completed_at > execution.started_at

    @pytest.mark.asyncio
    async def test_task_execution_with_result(self, db_session, test_organization, test_user, test_device, test_task):
        """Test task execution with result data."""
        experiment = Experiment(
            name="Result Test Experiment",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()

        execution = TaskExecution(
            task_id=test_task.id,
            device_id=test_device.id,
            experiment_id=experiment.id,
            status=TaskStatus.COMPLETED,
            result_data={"success": True, "measurements": [1.2, 3.4, 5.6]},
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.result_data["success"] is True
        assert len(execution.result_data["measurements"]) == 3


# ===== DEVICE DATA MODEL TESTS =====

class TestDeviceDataModel:
    """Test DeviceData model."""

    @pytest.mark.asyncio
    async def test_create_device_data(self, db_session, test_organization, test_user, test_device):
        """Test creating device telemetry data."""
        device_data = DeviceData(
            device_id=test_device.id,
            metric_name="temperature",
            metric_value=23.5,
            unit="celsius",
            data_metadata={"sensor": "DHT22", "location": "ambient"},
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device_data)
        await db_session.commit()
        await db_session.refresh(device_data)

        assert device_data.id is not None
        assert device_data.device_id == test_device.id
        assert device_data.metric_name == "temperature"
        assert device_data.metric_value == 23.5
        assert device_data.unit == "celsius"

    @pytest.mark.asyncio
    async def test_device_data_with_experiment(self, db_session, test_organization, test_user, test_device):
        """Test device data linked to experiment."""
        experiment = Experiment(
            name="Data Collection Experiment",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        device_data = DeviceData(
            device_id=test_device.id,
            experiment_id=experiment.id,
            metric_name="humidity",
            metric_value=65.0,
            unit="percent",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device_data)
        await db_session.commit()
        await db_session.refresh(device_data)

        assert device_data.experiment_id == experiment.id

    @pytest.mark.asyncio
    async def test_device_data_time_series(self, db_session, test_organization, test_user, test_device):
        """Test creating multiple time-series data points."""
        base_time = datetime.now(timezone.utc)

        for i in range(5):
            device_data = DeviceData(
                device_id=test_device.id,
                metric_name="cpu_usage",
                metric_value=20.0 + i * 5,
                unit="percent",
                timestamp=base_time + timedelta(minutes=i),
                organization_id=test_organization.id,
                created_by=test_user.id
            )
            db_session.add(device_data)

        await db_session.commit()

        # Query all data points
        result = await db_session.execute(
            select(DeviceData)
            .where(DeviceData.device_id == test_device.id)
            .where(DeviceData.metric_name == "cpu_usage")
            .order_by(DeviceData.timestamp)
        )
        data_points = result.scalars().all()

        assert len(data_points) == 5
        assert data_points[0].metric_value == 20.0
        assert data_points[4].metric_value == 40.0


# ===== MULTI-TENANCY TESTS =====

class TestMultiTenancy:
    """Test organization isolation for all domain models."""

    @pytest.mark.asyncio
    async def test_device_organization_isolation(self, db_session, test_user):
        """Test that devices are isolated by organization."""
        org1 = Organization(name=f"Org1 {uuid4().hex[:8]}")
        org2 = Organization(name=f"Org2 {uuid4().hex[:8]}")
        db_session.add_all([org1, org2])
        await db_session.commit()

        device1 = Device(
            name="Device 1",
            device_type=DeviceType.RASPBERRY_PI,
            organization_id=org1.id,
            created_by=test_user.id
        )
        device2 = Device(
            name="Device 1",  # Same name, different org
            device_type=DeviceType.RASPBERRY_PI,
            organization_id=org2.id,
            created_by=test_user.id
        )
        db_session.add_all([device1, device2])
        await db_session.commit()

        # Query devices for org1
        result = await db_session.execute(
            select(Device).where(Device.organization_id == org1.id)
        )
        org1_devices = result.scalars().all()

        assert len(org1_devices) == 1
        assert org1_devices[0].name == "Device 1"
        assert org1_devices[0].organization_id == org1.id

    @pytest.mark.asyncio
    async def test_experiment_organization_isolation(self, db_session, test_user):
        """Test that experiments are isolated by organization."""
        org1 = Organization(name=f"Org1 {uuid4().hex[:8]}")
        org2 = Organization(name=f"Org2 {uuid4().hex[:8]}")
        db_session.add_all([org1, org2])
        await db_session.commit()

        exp1 = Experiment(
            name="Experiment A",
            organization_id=org1.id,
            created_by=test_user.id
        )
        exp2 = Experiment(
            name="Experiment B",
            organization_id=org2.id,
            created_by=test_user.id
        )
        db_session.add_all([exp1, exp2])
        await db_session.commit()

        # Query experiments for org1
        result = await db_session.execute(
            select(Experiment).where(Experiment.organization_id == org1.id)
        )
        org1_experiments = result.scalars().all()

        assert len(org1_experiments) == 1
        assert org1_experiments[0].name == "Experiment A"


# ===== AUDIT TRAIL TESTS =====

class TestAuditTrails:
    """Test audit trail functionality for domain models."""

    @pytest.mark.asyncio
    async def test_device_audit_trail(self, db_session, test_organization, test_user):
        """Test device creation and update audit trails."""
        device = Device(
            name="Audit Test Device",
            device_type=DeviceType.RASPBERRY_PI,
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        # Check creation audit
        assert device.created_by == test_user.id
        assert device.created_at is not None
        assert device.updated_at is not None

        # Update device
        original_updated_at = device.updated_at
        device.status = DeviceStatus.MAINTENANCE
        device.updated_by = test_user.id
        await db_session.commit()
        await db_session.refresh(device)

        # Check update audit
        assert device.updated_by == test_user.id
        assert device.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_experiment_audit_trail(self, db_session, test_organization, test_user):
        """Test experiment audit trail tracking."""
        experiment = Experiment(
            name="Audit Test Experiment",
            organization_id=test_organization.id,
            created_by=test_user.id
        )
        db_session.add(experiment)
        await db_session.commit()
        await db_session.refresh(experiment)

        assert experiment.created_by == test_user.id
        assert experiment.created_at is not None
        assert experiment.updated_at is not None

"""
Unit Tests for Celery Background Tasks

Tests all background task implementations including data processing,
notifications, reports, and maintenance tasks.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from uuid import uuid4

from app.tasks.celery_app import celery_app, BaseTask
from app.tasks import data_processing, notifications, reports, maintenance


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_experiment_data():
    """Mock experiment data."""
    return {
        "id": uuid4(),
        "name": "Test Experiment",
        "status": "completed",
        "started_at": datetime.utcnow(),
        "actual_end": datetime.utcnow(),
        "result_summary": None,
        "organization_id": uuid4()
    }


@pytest.fixture
def mock_trial_data():
    """Mock trial data."""
    return [
        {
            "id": uuid4(),
            "experiment_id": uuid4(),
            "data_metadata": {
                "trial_number": 1,
                "is_correct": True,
                "response_time_ms": 250
            },
            "created_at": datetime.utcnow()
        },
        {
            "id": uuid4(),
            "experiment_id": uuid4(),
            "data_metadata": {
                "trial_number": 2,
                "is_correct": False,
                "response_time_ms": 500
            },
            "created_at": datetime.utcnow()
        },
        {
            "id": uuid4(),
            "experiment_id": uuid4(),
            "data_metadata": {
                "trial_number": 3,
                "is_correct": True,
                "response_time_ms": 300
            },
            "created_at": datetime.utcnow()
        }
    ]


# ====================
# Data Processing Tests
# ====================

class TestDataProcessingTasks:
    """Test data processing background tasks."""

    @patch('app.tasks.data_processing.get_async_session')
    def test_process_experiment_data_success(self, mock_get_session, mock_experiment_data, mock_trial_data):
        """Test successful experiment data processing."""
        # Setup mocks
        experiment_id = str(uuid4())

        mock_experiment = Mock()
        mock_experiment.id = experiment_id
        mock_experiment.result_summary = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_experiment
        mock_result.scalars.return_value.all.return_value = mock_trial_data

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        # Execute task
        result = data_processing.process_experiment_data(experiment_id)

        # Assertions
        assert result["status"] == "success"
        assert result["experiment_id"] == experiment_id
        assert result["total_trials"] == 3
        assert result["success_rate"] == pytest.approx(2/3, rel=0.01)
        assert "avg_response_time_ms" in result

    @patch('app.tasks.data_processing.get_async_session')
    def test_process_experiment_data_not_found(self, mock_get_session):
        """Test processing when experiment not found."""
        experiment_id = str(uuid4())

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        result = data_processing.process_experiment_data(experiment_id)

        assert result["status"] == "not_found"
        assert result["experiment_id"] == experiment_id

    @patch('app.tasks.data_processing.get_async_session')
    def test_process_device_telemetry(self, mock_get_session):
        """Test device telemetry processing."""
        device_id = str(uuid4())

        mock_telemetry = [
            Mock(data_metadata={"temperature": 25.5}),
            Mock(data_metadata={"temperature": 26.0}),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_telemetry

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        result = data_processing.process_device_telemetry(device_id, batch_size=100)

        assert result["status"] == "success"
        assert result["device_id"] == device_id
        assert result["records_processed"] == 2

    @patch('app.tasks.data_processing.get_async_session')
    def test_cleanup_old_data(self, mock_get_session):
        """Test old data cleanup."""
        mock_result = Mock()
        mock_result.rowcount = 10

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        result = data_processing.cleanup_old_data(days_to_keep=90)

        assert result["status"] == "success"
        assert result["experiment_records_deleted"] == 10
        assert result["telemetry_records_deleted"] == 10


# ====================
# Notification Tests
# ====================

class TestNotificationTasks:
    """Test notification background tasks."""

    def test_send_email_notification(self):
        """Test email notification sending."""
        result = notifications.send_email_notification(
            to_email="test@example.com",
            subject="Test Subject",
            body="Test Body"
        )

        assert result["status"] == "sent"
        assert result["to"] == "test@example.com"
        assert result["subject"] == "Test Subject"

    @patch('app.tasks.notifications.httpx.Client')
    def test_send_webhook_notification_success(self, mock_client):
        """Test successful webhook notification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        mock_http = Mock()
        mock_http.post.return_value = mock_response
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = None

        mock_client.return_value = mock_http

        result = notifications.send_webhook_notification(
            webhook_url="https://example.com/webhook",
            payload={"event": "test"}
        )

        assert result["status"] == "delivered"
        assert result["status_code"] == 200

    @patch('app.tasks.notifications.send_email_notification.delay')
    @patch('app.tasks.notifications.send_websocket_notification.delay')
    def test_send_experiment_completion_notification(self, mock_ws, mock_email):
        """Test experiment completion notification."""
        mock_email.return_value = Mock(id="email-task-id")
        mock_ws.return_value = Mock(id="ws-task-id")

        result = notifications.send_experiment_completion_notification(
            experiment_id=str(uuid4()),
            user_email="researcher@example.com",
            experiment_name="Test Experiment",
            success_rate=0.85
        )

        assert result["status"] == "sent"
        assert result["email_task_id"] == "email-task-id"
        assert result["websocket_task_id"] == "ws-task-id"

    @patch('app.tasks.notifications.send_email_notification.delay')
    @patch('app.tasks.notifications.send_websocket_notification.delay')
    def test_send_device_alert(self, mock_ws, mock_email):
        """Test device alert notification."""
        mock_email.return_value = Mock(id="email-task-id")
        mock_ws.return_value = Mock(id="ws-task-id")

        result = notifications.send_device_alert(
            device_id=str(uuid4()),
            device_name="Device-001",
            alert_type="offline",
            alert_message="Device went offline",
            user_emails=["admin1@example.com", "admin2@example.com"]
        )

        assert result["status"] == "sent"
        assert result["alert_type"] == "offline"
        assert len(result["email_task_ids"]) == 2


# ====================
# Report Tests
# ====================

class TestReportTasks:
    """Test report generation background tasks."""

    @patch('app.tasks.reports.get_async_session')
    @patch('app.tasks.reports._generate_json_report')
    def test_generate_experiment_report(self, mock_json_gen, mock_get_session, mock_experiment_data, mock_trial_data):
        """Test experiment report generation."""
        experiment_id = str(uuid4())

        mock_experiment = Mock()
        mock_experiment.id = experiment_id
        mock_experiment.name = "Test Experiment"
        mock_experiment.status = "completed"
        mock_experiment.started_at = datetime.utcnow()
        mock_experiment.actual_end = datetime.utcnow()
        mock_experiment.result_summary = {"success_rate": 0.8}

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_experiment
        mock_result.scalars.return_value.all.return_value = mock_trial_data

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()
        mock_json_gen.return_value = f"/tmp/reports/experiment_{experiment_id}.json"

        result = reports.generate_experiment_report(
            experiment_id=experiment_id,
            format="json",
            include_raw_data=False
        )

        assert result["status"] == "success"
        assert result["experiment_id"] == experiment_id
        assert result["format"] == "json"
        assert "file_path" in result

    @patch('app.tasks.reports.get_async_session')
    def test_generate_participant_progress_report(self, mock_get_session):
        """Test participant progress report generation."""
        primate_id = str(uuid4())

        mock_primate = Mock()
        mock_primate.id = primate_id
        mock_primate.name = "Monkey-42"
        mock_primate.species = "macaque"
        mock_primate.training_level = 5

        mock_experiments = [
            Mock(
                id=uuid4(),
                name="Exp 1",
                started_at=datetime.utcnow(),
                result_summary={"success_rate": 0.7, "total_trials": 100}
            ),
            Mock(
                id=uuid4(),
                name="Exp 2",
                started_at=datetime.utcnow(),
                result_summary={"success_rate": 0.8, "total_trials": 120}
            )
        ]

        mock_primate_result = Mock()
        mock_primate_result.scalar_one_or_none.return_value = mock_primate

        mock_exp_result = Mock()
        mock_exp_result.scalars.return_value.all.return_value = mock_experiments

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [mock_primate_result, mock_exp_result]

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        result = reports.generate_participant_progress_report(primate_id=primate_id)

        assert result["status"] == "success"
        assert result["primate_id"] == primate_id
        assert result["data"]["total_experiments"] == 2
        assert "overall_success_rate" in result["data"]

    @patch('app.tasks.reports.get_async_session')
    def test_generate_organization_summary(self, mock_get_session):
        """Test organization summary generation."""
        org_id = str(uuid4())

        mock_org = Mock()
        mock_org.id = org_id
        mock_org.name = "Test Lab"

        mock_org_result = Mock()
        mock_org_result.scalars.return_value.all.return_value = [mock_org]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_org_result
        mock_session.scalar.side_effect = [5, 10, 3]  # devices, experiments, primates

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        result = reports.generate_organization_summary(organization_id=org_id)

        assert result["status"] == "success"
        assert result["organizations_processed"] == 1
        assert len(result["summaries"]) == 1
        assert result["summaries"][0]["total_devices"] == 5


# ====================
# Maintenance Tests
# ====================

class TestMaintenanceTasks:
    """Test maintenance background tasks."""

    @patch('app.tasks.maintenance.get_async_session')
    @patch('app.tasks.maintenance.redis.from_url')
    def test_cleanup_expired_sessions(self, mock_redis, mock_get_session):
        """Test expired session cleanup."""
        mock_result = Mock()
        mock_result.rowcount = 5

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        mock_redis_client = Mock()
        mock_redis_client.keys.return_value = []
        mock_redis_client.close = Mock()
        mock_redis.return_value = mock_redis_client

        result = maintenance.cleanup_expired_sessions()

        assert result["status"] == "success"
        assert result["sessions_deleted"] == 5
        assert result["tokens_deleted"] == 5

    @patch('app.tasks.maintenance.get_async_session')
    @patch('app.tasks.maintenance.redis.from_url')
    def test_refresh_cache_warmup(self, mock_redis, mock_get_session):
        """Test cache warmup."""
        mock_experiments = [Mock(id=uuid4()) for _ in range(3)]
        mock_devices = [Mock(id=uuid4()) for _ in range(2)]

        mock_exp_result = Mock()
        mock_exp_result.scalars.return_value.all.return_value = mock_experiments

        mock_dev_result = Mock()
        mock_dev_result.scalars.return_value.all.return_value = mock_devices

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [mock_exp_result, mock_dev_result]

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        mock_redis_client = Mock()
        mock_redis_client.setex = Mock()
        mock_redis_client.close = Mock()
        mock_redis.return_value = mock_redis_client

        result = maintenance.refresh_cache_warmup()

        assert result["status"] == "success"
        assert result["experiments_cached"] == 3
        assert result["devices_cached"] == 2

    def test_backup_database_incremental(self):
        """Test database backup."""
        result = maintenance.backup_database_incremental()

        assert result["status"] == "success"
        assert "backup_file" in result
        assert "backup_location" in result
        assert "timestamp" in result

    @patch('app.tasks.maintenance.get_async_session')
    def test_update_device_status(self, mock_get_session):
        """Test device status update."""
        mock_devices = [
            Mock(
                id=uuid4(),
                name="Device-001",
                is_online=True,
                current_experiment_id=None,
                last_heartbeat=datetime.utcnow() - timedelta(minutes=10)
            )
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_devices

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        result = maintenance.update_device_status()

        assert result["status"] == "success"
        assert result["devices_marked_offline"] == 1

    @patch('os.path.exists')
    @patch('glob.glob')
    @patch('os.path.getmtime')
    @patch('os.remove')
    def test_cleanup_temp_files(self, mock_remove, mock_getmtime, mock_glob, mock_exists):
        """Test temporary file cleanup."""
        mock_exists.return_value = True
        mock_glob.return_value = ["/tmp/reports/old_file.pdf", "/tmp/uploads/old_upload.csv"]
        mock_getmtime.return_value = (datetime.utcnow() - timedelta(days=10)).timestamp()

        result = maintenance.cleanup_temp_files(days_to_keep=7)

        assert result["status"] == "success"
        assert result["files_deleted"] == 2

    def test_optimize_database(self):
        """Test database optimization."""
        result = maintenance.optimize_database()

        assert result["status"] == "success"
        assert "optimization_type" in result or "note" in result


# ====================
# BaseTask Tests
# ====================

class TestBaseTask:
    """Test BaseTask error handling."""

    def test_base_task_retry_configuration(self):
        """Test BaseTask has correct retry configuration."""
        assert BaseTask.autoretry_for == (Exception,)
        assert BaseTask.retry_kwargs == {'max_retries': 3}
        assert BaseTask.retry_backoff is True
        assert BaseTask.retry_backoff_max == 600
        assert BaseTask.retry_jitter is True

    def test_base_task_on_failure(self):
        """Test BaseTask failure handler."""
        task = BaseTask()
        task.name = "test_task"

        # Should not raise exception
        task.on_failure(
            exc=Exception("Test error"),
            task_id="test-id",
            args=(),
            kwargs={},
            einfo="traceback"
        )

    def test_base_task_on_retry(self):
        """Test BaseTask retry handler."""
        task = BaseTask()
        task.name = "test_task"
        task.request = Mock(retries=1)

        # Should not raise exception
        task.on_retry(
            exc=Exception("Test error"),
            task_id="test-id",
            args=(),
            kwargs={},
            einfo="traceback"
        )

    def test_base_task_on_success(self):
        """Test BaseTask success handler."""
        task = BaseTask()
        task.name = "test_task"

        # Should not raise exception
        task.on_success(
            retval={"status": "success"},
            task_id="test-id",
            args=(),
            kwargs={}
        )


# ====================
# Celery App Tests
# ====================

class TestCeleryApp:
    """Test Celery application configuration."""

    def test_celery_app_configuration(self):
        """Test Celery app is configured correctly."""
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.task_track_started is True
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.worker_prefetch_multiplier == 4

    def test_celery_queues_defined(self):
        """Test all queues are defined."""
        queue_names = [q.name for q in celery_app.conf.task_queues]

        assert "default" in queue_names
        assert "heavy" in queue_names
        assert "real-time" in queue_names
        assert "scheduled" in queue_names

    def test_task_routes_configured(self):
        """Test task routing is configured."""
        routes = celery_app.conf.task_routes

        assert "app.tasks.data_processing.*" in routes
        assert "app.tasks.notifications.*" in routes
        assert "app.tasks.reports.*" in routes
        assert "app.tasks.maintenance.*" in routes

        assert routes["app.tasks.data_processing.*"]["queue"] == "heavy"
        assert routes["app.tasks.notifications.*"]["queue"] == "real-time"

    def test_beat_schedule_configured(self):
        """Test Celery Beat schedule is configured."""
        schedule = celery_app.conf.beat_schedule

        assert "update-device-status" in schedule
        assert "cleanup-expired-sessions" in schedule
        assert "refresh-cache-warmup" in schedule
        assert "backup-database" in schedule
        assert "cleanup-old-data" in schedule

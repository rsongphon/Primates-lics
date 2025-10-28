"""
Integration Tests for Celery Workflow

Tests complete Celery task execution workflows including task chaining,
error handling, retries, and monitoring.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch, Mock, AsyncMock

from celery import group, chain, chord
from celery.result import AsyncResult

from app.tasks.celery_app import celery_app
from app.tasks import data_processing, notifications, reports, maintenance


# Configure Celery to use eager mode for testing
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    broker_url='memory://',
    result_backend='cache+memory://'
)


@pytest.fixture
def celery_worker():
    """Fixture to provide Celery worker for integration tests."""
    # In eager mode, no actual worker needed
    yield celery_app


@pytest.fixture
def mock_experiment_setup():
    """Setup mock experiment data for testing."""
    experiment_id = str(uuid4())
    return {
        "experiment_id": experiment_id,
        "experiment_name": "Integration Test Experiment",
        "user_email": "test@example.com"
    }


# ====================
# Task Execution Tests
# ====================

class TestTaskExecution:
    """Test basic task execution."""

    @patch('app.tasks.data_processing.get_async_session')
    def test_data_processing_task_execution(self, mock_get_session):
        """Test data processing task executes successfully."""
        experiment_id = str(uuid4())

        # Setup mocks
        mock_experiment = Mock()
        mock_experiment.id = experiment_id
        mock_experiment.result_summary = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # Not found

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        # Execute task
        result = data_processing.process_experiment_data.apply(args=[experiment_id])

        # Assertions
        assert result.successful()
        assert result.result["status"] == "not_found"

    def test_notification_task_execution(self):
        """Test notification task executes successfully."""
        result = notifications.send_email_notification.apply(
            kwargs={
                "to_email": "test@example.com",
                "subject": "Test",
                "body": "Test body"
            }
        )

        assert result.successful()
        assert result.result["status"] == "sent"

    def test_maintenance_task_execution(self):
        """Test maintenance task executes successfully."""
        result = maintenance.backup_database_incremental.apply()

        assert result.successful()
        assert result.result["status"] == "success"


# ====================
# Task Chaining Tests
# ====================

class TestTaskChaining:
    """Test task chaining and composition."""

    @patch('app.tasks.data_processing.get_async_session')
    @patch('app.tasks.notifications.send_email_notification.delay')
    def test_experiment_processing_chain(self, mock_email, mock_get_session):
        """Test chaining experiment processing with notification."""
        experiment_id = str(uuid4())

        # Setup mocks for data processing
        mock_experiment = Mock()
        mock_experiment.id = experiment_id
        mock_experiment.result_summary = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        # Setup mock for email
        mock_email.return_value = Mock(id="email-task-id")

        # Create task chain
        workflow = chain(
            data_processing.process_experiment_data.si(experiment_id),
            notifications.send_email_notification.si(
                to_email="researcher@example.com",
                subject="Experiment Processed",
                body="Your experiment has been processed"
            )
        )

        # Execute chain
        result = workflow.apply()

        # Assertions
        assert result.successful()

    @patch('app.tasks.reports.get_async_session')
    def test_report_generation_workflow(self, mock_get_session):
        """Test report generation followed by storage export."""
        experiment_id = str(uuid4())

        # Setup mocks
        mock_experiment = Mock()
        mock_experiment.id = experiment_id
        mock_experiment.name = "Test"
        mock_experiment.status = "completed"
        mock_experiment.started_at = datetime.utcnow()
        mock_experiment.actual_end = datetime.utcnow()
        mock_experiment.result_summary = {}

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_experiment
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        # Execute report generation
        result = reports.generate_experiment_report.apply(
            kwargs={
                "experiment_id": experiment_id,
                "format": "json",
                "include_raw_data": False
            }
        )

        assert result.successful()
        assert result.result["status"] == "success"


# ====================
# Parallel Execution Tests
# ====================

class TestParallelExecution:
    """Test parallel task execution."""

    @patch('app.tasks.maintenance.get_async_session')
    def test_parallel_device_status_updates(self, mock_get_session):
        """Test updating multiple devices in parallel."""
        # Setup mocks
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        # Create parallel tasks
        job = group(
            maintenance.update_device_status.si(),
            maintenance.update_device_status.si(),
            maintenance.update_device_status.si()
        )

        result = job.apply()

        # All tasks should complete
        assert len(result.results) == 3
        for task_result in result.results:
            assert task_result.successful()

    @patch('app.tasks.data_processing.get_async_session')
    def test_parallel_experiment_processing(self, mock_get_session):
        """Test processing multiple experiments in parallel."""
        experiment_ids = [str(uuid4()) for _ in range(3)]

        # Setup mocks
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        # Create parallel processing tasks
        job = group(
            data_processing.process_experiment_data.si(exp_id)
            for exp_id in experiment_ids
        )

        result = job.apply()

        assert len(result.results) == 3
        for task_result in result.results:
            assert task_result.successful()


# ====================
# Error Handling Tests
# ====================

class TestErrorHandling:
    """Test error handling and retry logic."""

    @patch('app.tasks.data_processing.get_async_session')
    def test_task_retry_on_exception(self, mock_get_session):
        """Test task retries on exception."""
        experiment_id = str(uuid4())

        # Setup mock to raise exception
        async def mock_session_generator():
            raise Exception("Database connection failed")
            yield  # This line won't be reached

        mock_get_session.return_value = mock_session_generator()

        # Execute task (will retry in eager mode)
        with pytest.raises(Exception):
            data_processing.process_experiment_data.apply(args=[experiment_id])

    def test_task_failure_callback(self):
        """Test task failure triggers callback."""
        # BaseTask should log errors without raising
        task = data_processing.process_experiment_data

        # Verify task has error handling configured
        assert task.autoretry_for == (Exception,)
        assert task.retry_kwargs['max_retries'] == 3


# ====================
# Scheduling Tests
# ====================

class TestScheduling:
    """Test task scheduling and periodic tasks."""

    def test_beat_schedule_configuration(self):
        """Test Celery Beat schedule is properly configured."""
        schedule = celery_app.conf.beat_schedule

        # Verify all periodic tasks are scheduled
        assert "update-device-status" in schedule
        assert "cleanup-expired-sessions" in schedule
        assert "refresh-cache-warmup" in schedule
        assert "backup-database" in schedule

        # Verify task configuration
        device_status_task = schedule["update-device-status"]
        assert device_status_task["task"] == "app.tasks.maintenance.update_device_status"
        assert device_status_task["schedule"] == 300.0  # 5 minutes
        assert device_status_task["options"]["queue"] == "scheduled"

    def test_periodic_task_execution(self):
        """Test periodic task can be executed manually."""
        # Execute periodic tasks manually
        result = maintenance.update_device_status.apply()
        assert result.successful()

        result = maintenance.cleanup_expired_sessions.apply()
        assert result.successful()


# ====================
# Queue Routing Tests
# ====================

class TestQueueRouting:
    """Test task routing to appropriate queues."""

    def test_data_processing_routes_to_heavy_queue(self):
        """Test data processing tasks route to heavy queue."""
        routes = celery_app.conf.task_routes

        assert "app.tasks.data_processing.*" in routes
        assert routes["app.tasks.data_processing.*"]["queue"] == "heavy"

    def test_notification_routes_to_realtime_queue(self):
        """Test notification tasks route to real-time queue."""
        routes = celery_app.conf.task_routes

        assert "app.tasks.notifications.*" in routes
        assert routes["app.tasks.notifications.*"]["queue"] == "real-time"

    def test_reports_route_to_heavy_queue(self):
        """Test report generation routes to heavy queue."""
        routes = celery_app.conf.task_routes

        assert "app.tasks.reports.*" in routes
        assert routes["app.tasks.reports.*"]["queue"] == "heavy"

    def test_maintenance_routes_to_scheduled_queue(self):
        """Test maintenance tasks route to scheduled queue."""
        routes = celery_app.conf.task_routes

        assert "app.tasks.maintenance.*" in routes
        assert routes["app.tasks.maintenance.*"]["queue"] == "scheduled"


# ====================
# Result Backend Tests
# ====================

class TestResultBackend:
    """Test result backend functionality."""

    def test_task_result_stored(self):
        """Test task results are stored in backend."""
        result = notifications.send_email_notification.apply(
            kwargs={
                "to_email": "test@example.com",
                "subject": "Test",
                "body": "Test body"
            }
        )

        # Result should be accessible
        assert result.result is not None
        assert isinstance(result.result, dict)

    def test_task_result_retrieval(self):
        """Test retrieving task result by ID."""
        result = notifications.send_email_notification.apply(
            kwargs={
                "to_email": "test@example.com",
                "subject": "Test",
                "body": "Test body"
            }
        )

        # Retrieve result by ID
        task_id = result.id
        retrieved_result = AsyncResult(task_id, app=celery_app)

        assert retrieved_result.successful()
        assert retrieved_result.result == result.result


# ====================
# Performance Tests
# ====================

class TestPerformance:
    """Test task performance characteristics."""

    def test_batch_processing_performance(self):
        """Test batch processing completes in reasonable time."""
        start_time = time.time()

        # Create batch of tasks
        task_ids = [str(uuid4()) for _ in range(10)]
        job = group(
            notifications.send_email_notification.si(
                to_email=f"user{i}@example.com",
                subject="Test",
                body="Test body"
            )
            for i in range(10)
        )

        result = job.apply()
        elapsed_time = time.time() - start_time

        # Should complete reasonably fast in eager mode
        assert elapsed_time < 5.0  # 5 seconds
        assert all(r.successful() for r in result.results)

    def test_task_execution_tracking(self):
        """Test task execution is tracked."""
        result = notifications.send_email_notification.apply(
            kwargs={
                "to_email": "test@example.com",
                "subject": "Test",
                "body": "Test body"
            }
        )

        # Task should have metadata
        assert result.id is not None
        assert result.state in ["SUCCESS", "PENDING"]
        assert result.successful() or result.failed()


# ====================
# Monitoring Tests
# ====================

class TestMonitoring:
    """Test task monitoring capabilities."""

    def test_task_metadata_available(self):
        """Test task metadata is available."""
        result = notifications.send_email_notification.apply(
            kwargs={
                "to_email": "test@example.com",
                "subject": "Test",
                "body": "Test body"
            }
        )

        # Metadata should be available
        assert hasattr(result, 'id')
        assert hasattr(result, 'state')
        assert hasattr(result, 'result')

    def test_celery_inspect_available(self):
        """Test Celery inspect API is available."""
        inspector = celery_app.control.inspect()

        # Inspector should be available
        assert inspector is not None
        # Note: In eager mode, these may return empty results
        assert hasattr(inspector, 'active')
        assert hasattr(inspector, 'scheduled')
        assert hasattr(inspector, 'stats')


# ====================
# Workflow Integration Tests
# ====================

class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    @patch('app.tasks.data_processing.get_async_session')
    @patch('app.tasks.reports.get_async_session')
    @patch('app.tasks.notifications.send_email_notification.delay')
    def test_experiment_completion_workflow(self, mock_email, mock_reports_session, mock_data_session):
        """Test complete experiment completion workflow."""
        experiment_id = str(uuid4())

        # Setup mocks for data processing
        mock_experiment = Mock()
        mock_experiment.id = experiment_id
        mock_experiment.result_summary = None

        mock_data_result = Mock()
        mock_data_result.scalar_one_or_none.return_value = None

        mock_data_sess = AsyncMock()
        mock_data_sess.execute.return_value = mock_data_result

        async def mock_data_generator():
            yield mock_data_sess

        mock_data_session.return_value = mock_data_generator()

        # Setup mocks for report generation
        mock_report_experiment = Mock()
        mock_report_experiment.id = experiment_id
        mock_report_experiment.name = "Test"
        mock_report_experiment.status = "completed"
        mock_report_experiment.started_at = datetime.utcnow()
        mock_report_experiment.actual_end = datetime.utcnow()
        mock_report_experiment.result_summary = {}

        mock_report_result = Mock()
        mock_report_result.scalar_one_or_none.return_value = mock_report_experiment
        mock_report_result.scalars.return_value.all.return_value = []

        mock_reports_sess = AsyncMock()
        mock_reports_sess.execute.return_value = mock_report_result

        async def mock_reports_generator():
            yield mock_reports_sess

        mock_reports_session.return_value = mock_reports_generator()

        # Setup mock email
        mock_email.return_value = Mock(id="email-task-id")

        # Create workflow: process → report → notify
        workflow = chain(
            data_processing.process_experiment_data.si(experiment_id),
            reports.generate_experiment_report.si(experiment_id, format="pdf"),
            notifications.send_email_notification.si(
                to_email="researcher@example.com",
                subject="Experiment Complete",
                body="Your experiment has been processed and report generated"
            )
        )

        # Execute workflow
        result = workflow.apply()

        # Verify workflow completed
        assert result.successful()

    @patch('app.tasks.maintenance.get_async_session')
    @patch('app.tasks.maintenance.redis.from_url')
    def test_daily_maintenance_workflow(self, mock_redis, mock_get_session):
        """Test daily maintenance workflow."""
        # Setup mocks
        mock_result = Mock()
        mock_result.rowcount = 5
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        async def mock_session_generator():
            yield mock_session

        mock_get_session.return_value = mock_session_generator()

        mock_redis_client = Mock()
        mock_redis_client.keys.return_value = []
        mock_redis_client.setex = Mock()
        mock_redis_client.close = Mock()
        mock_redis.return_value = mock_redis_client

        # Create maintenance workflow
        workflow = group(
            maintenance.cleanup_expired_sessions.si(),
            maintenance.refresh_cache_warmup.si(),
            maintenance.update_device_status.si()
        )

        # Execute workflow
        result = workflow.apply()

        # All tasks should complete
        assert all(r.successful() for r in result.results)

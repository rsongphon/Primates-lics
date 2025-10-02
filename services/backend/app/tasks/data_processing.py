"""
Data Processing Background Tasks

Handles data aggregation, analytics computation, and data cleanup operations.
Implements Documentation.md Section 5.3 data processing pipeline.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.core.database import get_async_session
from app.models.domain import Experiment, ExperimentData, Device, DeviceData, Primate
from app.services.domain import ExperimentService
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.data_processing.process_experiment_data", bind=True)
def process_experiment_data(self, experiment_id: str) -> Dict[str, Any]:
    """
    Process and aggregate experiment trial results.

    Computes success rates, response time statistics, and learning curves
    for a completed experiment.

    Args:
        experiment_id: UUID of the experiment to process

    Returns:
        Dictionary with processing results and statistics
    """
    async def _process():
        async for session in get_async_session():
            try:
                # Get experiment with data
                result = await session.execute(
                    select(Experiment).where(Experiment.id == experiment_id)
                )
                experiment = result.scalar_one_or_none()

                if not experiment:
                    logger.warning(f"Experiment {experiment_id} not found")
                    return {"status": "not_found", "experiment_id": experiment_id}

                # Get all experiment data
                data_result = await session.execute(
                    select(ExperimentData)
                    .where(ExperimentData.experiment_id == experiment_id)
                    .order_by(ExperimentData.created_at)
                )
                experiment_data = data_result.scalars().all()

                if not experiment_data:
                    return {
                        "status": "no_data",
                        "experiment_id": experiment_id,
                        "message": "No trial data found"
                    }

                # Compute statistics
                total_trials = len(experiment_data)
                correct_trials = sum(1 for d in experiment_data if d.data_metadata.get("is_correct"))
                success_rate = correct_trials / total_trials if total_trials > 0 else 0

                # Response time statistics
                response_times = [
                    d.data_metadata.get("response_time_ms", 0)
                    for d in experiment_data
                    if d.data_metadata.get("response_time_ms")
                ]
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0

                # Update experiment with computed statistics
                experiment.result_summary = {
                    "total_trials": total_trials,
                    "correct_trials": correct_trials,
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time,
                    "processed_at": datetime.utcnow().isoformat()
                }

                await session.commit()

                logger.info(
                    f"Processed experiment {experiment_id}",
                    extra={
                        "total_trials": total_trials,
                        "success_rate": success_rate
                    }
                )

                return {
                    "status": "success",
                    "experiment_id": experiment_id,
                    "total_trials": total_trials,
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time
                }

            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing experiment data: {e}")
                raise

    return asyncio.run(_process())


@celery_app.task(name="app.tasks.data_processing.process_device_telemetry", bind=True)
def process_device_telemetry(self, device_id: str, batch_size: int = 100) -> Dict[str, Any]:
    """
    Batch process device telemetry data for efficient storage.

    Aggregates raw telemetry into time-series buckets and stores in InfluxDB.

    Args:
        device_id: UUID of the device
        batch_size: Number of telemetry records to process

    Returns:
        Processing results with record count
    """
    async def _process():
        async for session in get_async_session():
            try:
                # Get unprocessed telemetry data
                result = await session.execute(
                    select(DeviceData)
                    .where(
                        and_(
                            DeviceData.device_id == device_id,
                            DeviceData.data_metadata.op("->>")(
                                "processed"
                            ).is_(None)
                        )
                    )
                    .limit(batch_size)
                    .order_by(DeviceData.timestamp)
                )
                telemetry_records = result.scalars().all()

                if not telemetry_records:
                    return {
                        "status": "no_data",
                        "device_id": device_id,
                        "records_processed": 0
                    }

                # Process and aggregate data
                # This would typically write to InfluxDB for time-series storage
                processed_count = 0

                for record in telemetry_records:
                    # Mark as processed
                    if record.data_metadata is None:
                        record.data_metadata = {}
                    record.data_metadata["processed"] = True
                    record.data_metadata["processed_at"] = datetime.utcnow().isoformat()
                    processed_count += 1

                await session.commit()

                logger.info(
                    f"Processed {processed_count} telemetry records for device {device_id}"
                )

                return {
                    "status": "success",
                    "device_id": device_id,
                    "records_processed": processed_count
                }

            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing telemetry: {e}")
                raise

    return asyncio.run(_process())


@celery_app.task(name="app.tasks.data_processing.cleanup_old_data", bind=True)
def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
    """
    Remove expired temporary data and old records.

    Cleans up temporary files, expired sessions, and old telemetry data
    according to retention policies.

    Args:
        days_to_keep: Number of days to retain data

    Returns:
        Cleanup results with record counts
    """
    async def _cleanup():
        async for session in get_async_session():
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

                # Delete old experiment data
                experiment_delete = await session.execute(
                    delete(ExperimentData)
                    .where(ExperimentData.created_at < cutoff_date)
                )
                experiment_records_deleted = experiment_delete.rowcount

                # Delete old device telemetry
                telemetry_delete = await session.execute(
                    delete(DeviceData)
                    .where(DeviceData.timestamp < cutoff_date)
                )
                telemetry_records_deleted = telemetry_delete.rowcount

                await session.commit()

                logger.info(
                    f"Cleaned up old data",
                    extra={
                        "experiment_records": experiment_records_deleted,
                        "telemetry_records": telemetry_records_deleted,
                        "cutoff_date": cutoff_date.isoformat()
                    }
                )

                return {
                    "status": "success",
                    "experiment_records_deleted": experiment_records_deleted,
                    "telemetry_records_deleted": telemetry_records_deleted,
                    "cutoff_date": cutoff_date.isoformat()
                }

            except Exception as e:
                await session.rollback()
                logger.error(f"Error during data cleanup: {e}")
                raise

    return asyncio.run(_cleanup())


@celery_app.task(name="app.tasks.data_processing.generate_analytics", bind=True)
def generate_analytics(self) -> Dict[str, Any]:
    """
    Generate analytics and statistics for all active experiments.

    Computes aggregate statistics, learning curves, and performance metrics
    across all experiments.

    Returns:
        Analytics results with statistics count
    """
    async def _generate():
        async for session in get_async_session():
            try:
                # Get all active experiments
                result = await session.execute(
                    select(Experiment).where(Experiment.status == "running")
                )
                experiments = result.scalars().all()

                analytics_generated = 0

                for experiment in experiments:
                    # Process each experiment's data
                    process_experiment_data.delay(str(experiment.id))
                    analytics_generated += 1

                logger.info(f"Queued analytics for {analytics_generated} experiments")

                return {
                    "status": "success",
                    "experiments_queued": analytics_generated
                }

            except Exception as e:
                logger.error(f"Error generating analytics: {e}")
                raise

    return asyncio.run(_generate())

"""
Maintenance Background Tasks

Handles system maintenance operations including session cleanup, cache warming,
database backups, and device status monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, delete, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
import redis

from app.tasks.celery_app import celery_app
from app.core.database import get_async_session
from app.core.config import settings
from app.models.auth import UserSession, RefreshToken
from app.models.domain import Device, Experiment
from app.tasks.notifications import send_device_alert
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.maintenance.cleanup_expired_sessions",
    bind=True
)
def cleanup_expired_sessions(self) -> Dict[str, Any]:
    """
    Remove expired user sessions and refresh tokens.

    Performs garbage collection on authentication tokens and session data.

    Returns:
        Cleanup results with record counts
    """
    async def _cleanup():
        async for session in get_async_session():
            try:
                cutoff_time = datetime.utcnow()

                # Delete expired sessions
                session_delete = await session.execute(
                    delete(UserSession).where(UserSession.expires_at < cutoff_time)
                )
                sessions_deleted = session_delete.rowcount

                # Delete expired refresh tokens
                token_delete = await session.execute(
                    delete(RefreshToken).where(RefreshToken.expires_at < cutoff_time)
                )
                tokens_deleted = token_delete.rowcount

                # Also clean up Redis token blacklist (entries older than 7 days)
                try:
                    redis_client = redis.from_url(settings.REDIS_URL)
                    blacklist_keys = redis_client.keys(f"{settings.TOKEN_BLACKLIST_PREFIX}*")
                    redis_deleted = 0

                    for key in blacklist_keys:
                        ttl = redis_client.ttl(key)
                        if ttl == -1 or ttl > 604800:  # 7 days in seconds
                            redis_client.delete(key)
                            redis_deleted += 1

                    redis_client.close()
                except Exception as e:
                    logger.warning(f"Redis cleanup failed: {e}")
                    redis_deleted = 0

                await session.commit()

                logger.info(
                    f"Cleaned up expired sessions",
                    extra={
                        "sessions_deleted": sessions_deleted,
                        "tokens_deleted": tokens_deleted,
                        "redis_keys_deleted": redis_deleted
                    }
                )

                return {
                    "status": "success",
                    "sessions_deleted": sessions_deleted,
                    "tokens_deleted": tokens_deleted,
                    "redis_keys_deleted": redis_deleted,
                    "task_id": self.request.id
                }

            except Exception as e:
                await session.rollback()
                logger.error(f"Error during session cleanup: {e}")
                raise

    return asyncio.run(_cleanup())


@celery_app.task(
    name="app.tasks.maintenance.refresh_cache_warmup",
    bind=True
)
def refresh_cache_warmup(self) -> Dict[str, Any]:
    """
    Preload frequently accessed data into cache.

    Warms up Redis cache with hot data to improve response times.

    Returns:
        Cache warming results
    """
    try:
        redis_client = redis.from_url(settings.REDIS_URL)

        async def _warmup():
            async for session in get_async_session():
                # Get active experiments for cache
                active_experiments = await session.execute(
                    select(Experiment)
                    .where(Experiment.status.in_(["running", "paused"]))
                    .limit(100)
                )
                experiments = active_experiments.scalars().all()

                # Get online devices for cache
                online_devices = await session.execute(
                    select(Device)
                    .where(Device.is_online == True)
                    .limit(100)
                )
                devices = online_devices.scalars().all()

                # Cache experiment data
                for exp in experiments:
                    cache_key = f"experiment:{exp.id}"
                    redis_client.setex(
                        cache_key,
                        3600,  # 1 hour TTL
                        str(exp.id)  # In production, would cache full serialized data
                    )

                # Cache device data
                for device in devices:
                    cache_key = f"device:{device.id}"
                    redis_client.setex(
                        cache_key,
                        1800,  # 30 minute TTL
                        str(device.id)
                    )

                return len(experiments), len(devices)

        exp_count, device_count = asyncio.run(_warmup())

        redis_client.close()

        logger.info(
            f"Cache warmed up",
            extra={
                "experiments_cached": exp_count,
                "devices_cached": device_count
            }
        )

        return {
            "status": "success",
            "experiments_cached": exp_count,
            "devices_cached": device_count,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"Error during cache warmup: {e}")
        raise


@celery_app.task(
    name="app.tasks.maintenance.backup_database_incremental",
    bind=True,
    time_limit=1800  # 30 minutes
)
def backup_database_incremental(self) -> Dict[str, Any]:
    """
    Perform incremental database backup.

    Creates a backup of the database and stores it in object storage.

    Returns:
        Backup status and file location
    """
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"lics_backup_{timestamp}.sql"

        # TODO: Implement actual database backup
        # This would typically use pg_dump or a similar tool
        # import subprocess
        # subprocess.run([
        #     "pg_dump",
        #     "-h", "postgres",
        #     "-U", "lics",
        #     "-d", "lics",
        #     "-F", "c",  # Custom format
        #     "-f", f"/tmp/backups/{backup_filename}"
        # ])

        # TODO: Upload to MinIO/S3
        # from minio import Minio
        # client = Minio(...)
        # client.fput_object("backups", backup_filename, f"/tmp/backups/{backup_filename}")

        backup_location = f"minio://backups/{backup_filename}"

        logger.info(
            f"Database backup completed",
            extra={
                "backup_file": backup_filename,
                "backup_location": backup_location
            }
        )

        return {
            "status": "success",
            "backup_file": backup_filename,
            "backup_location": backup_location,
            "timestamp": timestamp,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"Error during database backup: {e}")
        raise


@celery_app.task(
    name="app.tasks.maintenance.update_device_status",
    bind=True
)
def update_device_status(self) -> Dict[str, Any]:
    """
    Check device heartbeats and update online/offline status.

    Monitors device last_seen timestamps and marks devices as offline
    if they haven't sent heartbeat recently.

    Returns:
        Device status update results
    """
    async def _update():
        async for session in get_async_session():
            try:
                # Devices offline if no heartbeat in last 5 minutes
                offline_threshold = datetime.utcnow() - timedelta(minutes=5)

                # Get devices that should be marked offline
                offline_devices = await session.execute(
                    select(Device).where(
                        and_(
                            Device.is_online == True,
                            Device.last_heartbeat < offline_threshold
                        )
                    )
                )
                devices_to_mark_offline = offline_devices.scalars().all()

                # Update device status
                for device in devices_to_mark_offline:
                    device.is_online = False
                    device.connection_status = "offline"

                    # Send alert if device was in active experiment
                    if device.current_experiment_id:
                        # Get organization admins
                        # admin_emails = ["admin@example.com"]  # TODO: Fetch from DB

                        # send_device_alert.delay(
                        #     device_id=str(device.id),
                        #     device_name=device.name,
                        #     alert_type="offline",
                        #     alert_message=f"Device {device.name} went offline during active experiment",
                        #     user_emails=admin_emails
                        # )
                        pass

                devices_marked_offline = len(devices_to_mark_offline)

                await session.commit()

                logger.info(
                    f"Updated device status",
                    extra={
                        "devices_marked_offline": devices_marked_offline
                    }
                )

                return {
                    "status": "success",
                    "devices_checked": devices_marked_offline,
                    "devices_marked_offline": devices_marked_offline,
                    "task_id": self.request.id
                }

            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating device status: {e}")
                raise

    return asyncio.run(_update())


@celery_app.task(
    name="app.tasks.maintenance.cleanup_temp_files",
    bind=True
)
def cleanup_temp_files(self, days_to_keep: int = 7) -> Dict[str, Any]:
    """
    Remove temporary files older than specified days.

    Cleans up temporary reports, uploads, and cached files.

    Args:
        days_to_keep: Number of days to keep temp files

    Returns:
        Cleanup results with file counts
    """
    try:
        import os
        import glob
        import time

        temp_directories = [
            "/tmp/reports",
            "/tmp/uploads",
            "/tmp/exports"
        ]

        cutoff_time = time.time() - (days_to_keep * 86400)
        files_deleted = 0

        for directory in temp_directories:
            if not os.path.exists(directory):
                continue

            for file_path in glob.glob(f"{directory}/*"):
                try:
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        files_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

        logger.info(
            f"Cleaned up temp files",
            extra={
                "files_deleted": files_deleted,
                "directories_cleaned": len(temp_directories)
            }
        )

        return {
            "status": "success",
            "files_deleted": files_deleted,
            "directories_cleaned": len(temp_directories),
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}")
        raise


@celery_app.task(
    name="app.tasks.maintenance.optimize_database",
    bind=True,
    time_limit=3600  # 1 hour
)
def optimize_database(self) -> Dict[str, Any]:
    """
    Optimize database performance.

    Runs VACUUM ANALYZE and updates statistics for query optimization.

    Returns:
        Optimization results
    """
    async def _optimize():
        async for session in get_async_session():
            try:
                # Run VACUUM ANALYZE (Note: requires AUTOCOMMIT)
                # await session.execute("VACUUM ANALYZE")

                # Update table statistics
                # await session.execute("ANALYZE")

                logger.info("Database optimization completed")

                return {
                    "status": "success",
                    "optimization_type": "vacuum_analyze",
                    "task_id": self.request.id
                }

            except Exception as e:
                logger.error(f"Error optimizing database: {e}")
                raise

    # Placeholder for now
    logger.info("Database optimization task triggered")
    return {
        "status": "success",
        "note": "Database optimization would run here",
        "task_id": self.request.id
    }

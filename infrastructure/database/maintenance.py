#!/usr/bin/env python3
"""
Database Maintenance and Cleanup Procedures
Automated maintenance tasks for LICS database infrastructure
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

import asyncpg
import redis.asyncio as redis
from influxdb_client import InfluxDBClient
from influxdb_client.rest import ApiException


class DatabaseMaintenance:
    """Main database maintenance coordinator"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/app/logs/maintenance.log', mode='a')
            ]
        )
        return logging.getLogger(__name__)

    async def run_maintenance(self, tasks: List[str] = None):
        """Run specified maintenance tasks or all tasks"""
        all_tasks = [
            'postgres_maintenance',
            'redis_maintenance',
            'influxdb_maintenance',
            'cleanup_old_data',
            'optimize_performance',
            'health_check'
        ]

        tasks_to_run = tasks if tasks else all_tasks

        self.logger.info(f"🔧 Starting database maintenance - Tasks: {', '.join(tasks_to_run)}")

        results = {}
        for task in tasks_to_run:
            try:
                if hasattr(self, task):
                    self.logger.info(f"Running {task}...")
                    result = await getattr(self, task)()
                    results[task] = result
                    self.logger.info(f"✅ {task} completed successfully")
                else:
                    self.logger.warning(f"⚠️ Unknown task: {task}")
                    results[task] = {"status": "unknown_task"}
            except Exception as e:
                self.logger.error(f"❌ {task} failed: {e}")
                results[task] = {"status": "error", "error": str(e)}

        self.logger.info("🎉 Database maintenance completed")
        return results

    async def postgres_maintenance(self) -> Dict[str, Any]:
        """PostgreSQL maintenance tasks"""
        results = {
            "vacuum": {"status": "skipped"},
            "reindex": {"status": "skipped"},
            "analyze": {"status": "skipped"},
            "cleanup_logs": {"status": "skipped"}
        }

        try:
            conn = await asyncpg.connect(self.config['database_url'])

            # VACUUM and ANALYZE on main tables
            maintenance_tables = [
                'organizations', 'users', 'devices', 'experiments',
                'tasks', 'telemetry'
            ]

            for table in maintenance_tables:
                try:
                    # Check if table exists
                    exists = await conn.fetchval(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                        table
                    )

                    if exists:
                        # VACUUM ANALYZE
                        await conn.execute(f"VACUUM ANALYZE {table}")
                        self.logger.info(f"VACUUM ANALYZE completed for {table}")

                except Exception as e:
                    self.logger.warning(f"Failed to vacuum {table}: {e}")

            results["vacuum"]["status"] = "completed"
            results["analyze"]["status"] = "completed"

            # Update table statistics
            await conn.execute("ANALYZE")

            # Reindex if needed (check for bloated indexes)
            bloated_indexes = await conn.fetch("""
                SELECT schemaname, tablename, indexname,
                       pg_size_pretty(pg_relation_size(indexrelid)) as size
                FROM pg_stat_user_indexes
                WHERE idx_scan < 100
                AND pg_relation_size(indexrelid) > 1024 * 1024  -- > 1MB
                ORDER BY pg_relation_size(indexrelid) DESC
                LIMIT 10
            """)

            if bloated_indexes:
                self.logger.info(f"Found {len(bloated_indexes)} potentially bloated indexes")
                for idx in bloated_indexes:
                    self.logger.info(f"Bloated index: {idx['indexname']} ({idx['size']})")

            results["reindex"]["status"] = "analyzed"

            await conn.close()

        except Exception as e:
            self.logger.error(f"PostgreSQL maintenance failed: {e}")
            raise

        return results

    async def redis_maintenance(self) -> Dict[str, Any]:
        """Redis maintenance tasks"""
        results = {"memory_usage": {}, "cleanup": {"status": "skipped"}}

        try:
            redis_client = redis.from_url(self.config['redis_url'])

            # Get memory usage info
            info = await redis_client.info('memory')
            results["memory_usage"] = {
                "used_memory": info.get('used_memory'),
                "used_memory_human": info.get('used_memory_human'),
                "used_memory_peak": info.get('used_memory_peak'),
                "used_memory_peak_human": info.get('used_memory_peak_human'),
                "mem_fragmentation_ratio": info.get('mem_fragmentation_ratio')
            }

            # Cleanup expired keys (Redis should do this automatically, but we can check)
            expired_keys = 0
            cursor = 0

            while True:
                cursor, keys = await redis_client.scan(cursor, match="session:*", count=100)
                for key in keys:
                    ttl = await redis_client.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        expired_keys += 1

                if cursor == 0:
                    break

            results["cleanup"] = {
                "status": "completed",
                "expired_keys_found": expired_keys
            }

            # Optional: Force expire cleanup for performance
            await redis_client.execute_command('MEMORY', 'PURGE')

            await redis_client.close()

        except Exception as e:
            self.logger.error(f"Redis maintenance failed: {e}")
            raise

        return results

    async def influxdb_maintenance(self) -> Dict[str, Any]:
        """InfluxDB maintenance tasks"""
        results = {"buckets": {}, "retention": {"status": "checked"}}

        try:
            client = InfluxDBClient(
                url=self.config['influxdb_url'],
                token=self.config['influxdb_token'],
                org=self.config['influxdb_org']
            )

            # Get bucket information
            buckets_api = client.buckets_api()
            buckets = buckets_api.find_buckets()

            for bucket in buckets.buckets:
                if bucket.name.startswith('_'):  # Skip system buckets
                    continue

                results["buckets"][bucket.name] = {
                    "retention_rules": [rule.every_seconds for rule in bucket.retention_rules],
                    "created_at": bucket.created_at,
                    "updated_at": bucket.updated_at
                }

            # Check and run compaction if needed
            # Note: InfluxDB 2.x handles compaction automatically
            # We just verify the health
            health = client.health()
            results["health"] = {
                "status": health.status.value,
                "message": health.message if health.message else "Healthy"
            }

            client.close()

        except ApiException as e:
            self.logger.error(f"InfluxDB maintenance failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"InfluxDB maintenance failed: {e}")
            raise

        return results

    async def cleanup_old_data(self) -> Dict[str, Any]:
        """Cleanup old data based on retention policies"""
        results = {
            "postgres_cleanup": {"status": "skipped", "rows_deleted": 0},
            "log_cleanup": {"status": "skipped", "files_deleted": 0}
        }

        try:
            # PostgreSQL cleanup
            conn = await asyncpg.connect(self.config['database_url'])

            # Cleanup old audit logs (keep last 90 days)
            audit_cleanup = await conn.execute("""
                DELETE FROM audit_logs
                WHERE created_at < NOW() - INTERVAL '90 days'
            """)

            # Cleanup old session data (keep last 30 days)
            session_cleanup = await conn.execute("""
                DELETE FROM user_sessions
                WHERE last_accessed < NOW() - INTERVAL '30 days'
            """)

            # Cleanup old device telemetry in regular tables (TimescaleDB handles hypertables)
            telemetry_cleanup = await conn.execute("""
                DELETE FROM device_events
                WHERE created_at < NOW() - INTERVAL '365 days'
            """)

            total_deleted = (
                int(audit_cleanup.split()[1]) if audit_cleanup.startswith('DELETE') else 0 +
                int(session_cleanup.split()[1]) if session_cleanup.startswith('DELETE') else 0 +
                int(telemetry_cleanup.split()[1]) if telemetry_cleanup.startswith('DELETE') else 0
            )

            results["postgres_cleanup"] = {
                "status": "completed",
                "rows_deleted": total_deleted
            }

            await conn.close()

        except Exception as e:
            self.logger.warning(f"PostgreSQL cleanup failed: {e}")

        try:
            # Log file cleanup
            log_dir = Path('/app/logs')
            if log_dir.exists():
                cutoff_date = datetime.now() - timedelta(days=30)
                files_deleted = 0

                for log_file in log_dir.glob('*.log*'):
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink()
                        files_deleted += 1

                results["log_cleanup"] = {
                    "status": "completed",
                    "files_deleted": files_deleted
                }

        except Exception as e:
            self.logger.warning(f"Log cleanup failed: {e}")

        return results

    async def optimize_performance(self) -> Dict[str, Any]:
        """Run performance optimization tasks"""
        results = {"postgres_stats": {"status": "skipped"}}

        try:
            conn = await asyncpg.connect(self.config['database_url'])

            # Update PostgreSQL statistics
            await conn.execute("ANALYZE")

            # Check for missing indexes on frequently queried columns
            slow_queries = await conn.fetch("""
                SELECT query, calls, total_time, mean_time
                FROM pg_stat_statements
                WHERE calls > 100
                ORDER BY mean_time DESC
                LIMIT 10
            """)

            if slow_queries:
                self.logger.info("Top slow queries found:")
                for query in slow_queries:
                    self.logger.info(f"  Mean time: {query['mean_time']:.2f}ms, Calls: {query['calls']}")

            # Check table sizes
            table_sizes = await conn.fetch("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC
                LIMIT 10
            """)

            results["postgres_stats"] = {
                "status": "completed",
                "slow_queries_found": len(slow_queries),
                "largest_tables": [
                    {"table": f"{t['schemaname']}.{t['tablename']}", "size": t['size']}
                    for t in table_sizes[:5]
                ]
            }

            await conn.close()

        except Exception as e:
            self.logger.error(f"Performance optimization failed: {e}")
            raise

        return results

    async def health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        results = {
            "postgres": {"status": "unknown"},
            "redis": {"status": "unknown"},
            "influxdb": {"status": "unknown"}
        }

        # PostgreSQL health check
        try:
            conn = await asyncpg.connect(self.config['database_url'])
            await conn.fetchval("SELECT 1")
            await conn.close()
            results["postgres"]["status"] = "healthy"
        except Exception as e:
            results["postgres"]["status"] = "unhealthy"
            results["postgres"]["error"] = str(e)

        # Redis health check
        try:
            redis_client = redis.from_url(self.config['redis_url'])
            await redis_client.ping()
            await redis_client.close()
            results["redis"]["status"] = "healthy"
        except Exception as e:
            results["redis"]["status"] = "unhealthy"
            results["redis"]["error"] = str(e)

        # InfluxDB health check
        try:
            client = InfluxDBClient(
                url=self.config['influxdb_url'],
                token=self.config['influxdb_token'],
                org=self.config['influxdb_org']
            )
            health = client.health()
            results["influxdb"]["status"] = "healthy" if health.status.value == "pass" else "unhealthy"
            if health.message:
                results["influxdb"]["message"] = health.message
            client.close()
        except Exception as e:
            results["influxdb"]["status"] = "unhealthy"
            results["influxdb"]["error"] = str(e)

        return results


class MaintenanceScheduler:
    """Scheduler for automated maintenance tasks"""

    def __init__(self, maintenance: DatabaseMaintenance):
        self.maintenance = maintenance
        self.logger = maintenance.logger

    async def run_scheduled_maintenance(self):
        """Run maintenance tasks on schedule"""
        now = datetime.now()

        # Daily tasks (run at 2 AM)
        if now.hour == 2 and now.minute < 5:
            await self._run_daily_tasks()

        # Weekly tasks (run on Sunday at 3 AM)
        if now.weekday() == 6 and now.hour == 3 and now.minute < 5:
            await self._run_weekly_tasks()

        # Monthly tasks (run on 1st day at 4 AM)
        if now.day == 1 and now.hour == 4 and now.minute < 5:
            await self._run_monthly_tasks()

    async def _run_daily_tasks(self):
        """Daily maintenance tasks"""
        self.logger.info("🗓️ Running daily maintenance tasks")
        await self.maintenance.run_maintenance([
            'health_check',
            'redis_maintenance',
            'cleanup_old_data'
        ])

    async def _run_weekly_tasks(self):
        """Weekly maintenance tasks"""
        self.logger.info("📅 Running weekly maintenance tasks")
        await self.maintenance.run_maintenance([
            'postgres_maintenance',
            'optimize_performance',
            'influxdb_maintenance'
        ])

    async def _run_monthly_tasks(self):
        """Monthly maintenance tasks"""
        self.logger.info("📆 Running monthly maintenance tasks")
        await self.maintenance.run_maintenance()  # Run all tasks


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    return {
        'database_url': os.getenv('DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics'),
        'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'influxdb_url': os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
        'influxdb_token': os.getenv('INFLUXDB_TOKEN', 'lics-admin-token-change-in-production'),
        'influxdb_org': os.getenv('INFLUXDB_ORG', 'lics'),
    }


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='LICS Database Maintenance Tool')
    parser.add_argument(
        '--tasks',
        nargs='*',
        help='Specific tasks to run',
        choices=[
            'postgres_maintenance', 'redis_maintenance', 'influxdb_maintenance',
            'cleanup_old_data', 'optimize_performance', 'health_check'
        ]
    )
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Run scheduled maintenance (daemon mode)'
    )
    parser.add_argument(
        '--config-check',
        action='store_true',
        help='Check configuration and exit'
    )

    args = parser.parse_args()

    config = load_config()

    if args.config_check:
        print("Configuration:")
        for key, value in config.items():
            if 'token' in key.lower() or 'password' in key.lower():
                print(f"  {key}: {'*' * len(value) if value else 'NOT SET'}")
            else:
                print(f"  {key}: {value}")
        return 0

    maintenance = DatabaseMaintenance(config)

    if args.schedule:
        scheduler = MaintenanceScheduler(maintenance)
        print("🕐 Starting maintenance scheduler (Ctrl+C to stop)")
        try:
            while True:
                await scheduler.run_scheduled_maintenance()
                await asyncio.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n👋 Maintenance scheduler stopped")
            return 0

    else:
        results = await maintenance.run_maintenance(args.tasks)

        # Print summary
        print("\n📊 Maintenance Summary:")
        for task, result in results.items():
            status = result.get('status', 'unknown')
            if status == 'completed':
                print(f"  ✅ {task}")
            elif status == 'error':
                print(f"  ❌ {task}: {result.get('error', 'Unknown error')}")
            else:
                print(f"  ⚠️ {task}: {status}")

        return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
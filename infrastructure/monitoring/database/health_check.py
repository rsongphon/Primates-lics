#!/usr/bin/env python3
"""
LICS Database Health Check Script

This script performs comprehensive health checks on all database components:
- PostgreSQL primary database
- TimescaleDB hypertables
- Redis cache
- InfluxDB time-series database
- PgBouncer connection pooler

Usage:
    python health_check.py [--format json|text] [--output file.txt]
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import asyncpg
import asyncio_redis
import influxdb_client
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseHealthChecker:
    """Comprehensive database health checker."""

    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.start_time = time.time()

    async def check_postgresql(self) -> Dict[str, Any]:
        """Check PostgreSQL database health."""
        result = {
            "name": "PostgreSQL",
            "status": "unknown",
            "details": {},
            "metrics": {},
            "errors": []
        }

        try:
            # Get database URL
            db_url = os.getenv('DATABASE_URL', 'postgresql://lics:lics123@localhost:5432/lics_dev')

            # Parse connection info
            if '://' in db_url:
                url_parts = db_url.split('://', 1)[1]
                if '@' in url_parts:
                    auth_part, host_part = url_parts.split('@', 1)
                    username, password = auth_part.split(':', 1) if ':' in auth_part else (auth_part, '')
                    if '/' in host_part:
                        host_port, database = host_part.split('/', 1)
                        host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '5432')

            conn = await asyncpg.connect(
                host=host,
                port=int(port),
                user=username,
                password=password,
                database=database
            )

            # Basic connectivity test
            version = await conn.fetchval("SELECT version()")
            result["details"]["version"] = version

            # Check database size
            db_size = await conn.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            result["details"]["database_size"] = db_size

            # Check connection count
            connections = await conn.fetchval("""
                SELECT count(*) FROM pg_stat_activity WHERE state = 'active'
            """)
            result["metrics"]["active_connections"] = connections

            # Check for TimescaleDB
            timescaledb_version = await conn.fetchval("""
                SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'
            """)
            if timescaledb_version:
                result["details"]["timescaledb_version"] = timescaledb_version

                # Check hypertables
                hypertables = await conn.fetch("""
                    SELECT hypertable_name, hypertable_schema
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_schema = 'lics_telemetry'
                """)
                result["metrics"]["hypertables_count"] = len(hypertables)
                result["details"]["hypertables"] = [dict(row) for row in hypertables]

            # Check schema health
            schemas = await conn.fetch("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name LIKE 'lics_%'
            """)
            result["metrics"]["lics_schemas_count"] = len(schemas)

            # Check table counts in each schema
            for schema in schemas:
                schema_name = schema['schema_name']
                table_count = await conn.fetchval(f"""
                    SELECT count(*) FROM information_schema.tables
                    WHERE table_schema = '{schema_name}'
                """)
                result["metrics"][f"{schema_name}_tables"] = table_count

            await conn.close()
            result["status"] = "healthy"

        except Exception as e:
            result["status"] = "unhealthy"
            result["errors"].append(str(e))

        return result

    async def check_pgbouncer(self) -> Dict[str, Any]:
        """Check PgBouncer connection pooler health."""
        result = {
            "name": "PgBouncer",
            "status": "unknown",
            "details": {},
            "metrics": {},
            "errors": []
        }

        try:
            # Try to connect through PgBouncer
            pooled_url = os.getenv('DATABASE_POOLED_URL', 'postgresql://lics:lics123@localhost:6432/lics_dev')

            if '://' in pooled_url:
                url_parts = pooled_url.split('://', 1)[1]
                if '@' in url_parts:
                    auth_part, host_part = url_parts.split('@', 1)
                    username, password = auth_part.split(':', 1) if ':' in auth_part else (auth_part, '')
                    if '/' in host_part:
                        host_port, database = host_part.split('/', 1)
                        host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '6432')

            conn = await asyncpg.connect(
                host=host,
                port=int(port),
                user=username,
                password=password,
                database=database
            )

            # Simple connectivity test
            test_result = await conn.fetchval("SELECT 1")
            result["details"]["connectivity_test"] = test_result == 1

            # Try to get PgBouncer stats if available
            try:
                # Note: This might not work in all setups
                stats = await conn.fetch("SHOW STATS")
                if stats:
                    result["metrics"]["stats_available"] = True
                    result["details"]["pool_stats"] = [dict(row) for row in stats]
            except Exception:
                result["details"]["stats_accessible"] = False

            await conn.close()
            result["status"] = "healthy"

        except Exception as e:
            result["status"] = "unhealthy"
            result["errors"].append(str(e))

        return result

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis cache health."""
        result = {
            "name": "Redis",
            "status": "unknown",
            "details": {},
            "metrics": {},
            "errors": []
        }

        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

            # Parse Redis URL
            if redis_url.startswith('redis://'):
                url_parts = redis_url[8:]  # Remove redis://
                if '@' in url_parts:
                    auth_part, host_part = url_parts.split('@', 1)
                    password = auth_part
                else:
                    password = None
                    host_part = url_parts

                if '/' in host_part:
                    host_port, db = host_part.split('/', 1)
                    host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '6379')
                    db = int(db)
                else:
                    host, port = host_part.split(':', 1) if ':' in host_part else (host_part, '6379')
                    db = 0

            # Connect to Redis
            connection = await asyncio_redis.Connection.create(
                host=host,
                port=int(port),
                db=db,
                password=password
            )

            # Get Redis info
            info = await connection.info()
            result["details"]["version"] = info.get("server", {}).get("redis_version")
            result["details"]["mode"] = info.get("server", {}).get("redis_mode")

            # Get memory usage
            memory_info = info.get("memory", {})
            result["metrics"]["memory_used"] = memory_info.get("used_memory_human")
            result["metrics"]["memory_peak"] = memory_info.get("used_memory_peak_human")

            # Get client connections
            clients_info = info.get("clients", {})
            result["metrics"]["connected_clients"] = clients_info.get("connected_clients", 0)

            # Test basic operations
            await connection.set("health_check", "ok")
            test_value = await connection.get("health_check")
            result["details"]["read_write_test"] = test_value == "ok"
            await connection.delete(["health_check"])

            # Get keyspace info
            keyspace = info.get("keyspace", {})
            for db_name, db_info in keyspace.items():
                if isinstance(db_info, dict):
                    result["metrics"][f"{db_name}_keys"] = db_info.get("keys", 0)

            connection.close()
            result["status"] = "healthy"

        except Exception as e:
            result["status"] = "unhealthy"
            result["errors"].append(str(e))

        return result

    def check_influxdb(self) -> Dict[str, Any]:
        """Check InfluxDB time-series database health."""
        result = {
            "name": "InfluxDB",
            "status": "unknown",
            "details": {},
            "metrics": {},
            "errors": []
        }

        try:
            url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
            token = os.getenv('INFLUXDB_TOKEN', 'lics-admin-token-change-in-production')
            org = os.getenv('INFLUXDB_ORG', 'lics')

            # Create InfluxDB client
            client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

            # Check health
            health = client.health()
            result["details"]["status"] = health.status
            result["details"]["message"] = health.message
            result["details"]["version"] = health.version

            # Get buckets
            buckets_api = client.buckets_api()
            buckets = buckets_api.find_buckets()
            result["metrics"]["buckets_count"] = len(buckets.buckets)
            result["details"]["buckets"] = [
                {"name": bucket.name, "retention": bucket.retention_rules}
                for bucket in buckets.buckets
            ]

            # Try a simple query
            query_api = client.query_api()
            bucket = os.getenv('INFLUXDB_BUCKET', 'telemetry')

            # Simple health query
            query = f'''
                from(bucket: "{bucket}")
                |> range(start: -1h)
                |> limit(n: 1)
                |> count()
            '''

            try:
                tables = query_api.query(query)
                result["details"]["query_test"] = "successful"
                result["metrics"]["recent_data_points"] = len(tables)
            except Exception as query_error:
                result["details"]["query_test"] = f"failed: {str(query_error)}"

            client.close()
            result["status"] = "healthy" if health.status == "pass" else "degraded"

        except Exception as e:
            result["status"] = "unhealthy"
            result["errors"].append(str(e))

        return result

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        print("🔍 Running LICS database health checks...")

        # Run checks
        postgresql_result = await self.check_postgresql()
        pgbouncer_result = await self.check_pgbouncer()
        redis_result = await self.check_redis()
        influxdb_result = self.check_influxdb()

        # Compile results
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(time.time() - self.start_time, 2),
            "overall_status": "healthy",
            "checks": {
                "postgresql": postgresql_result,
                "pgbouncer": pgbouncer_result,
                "redis": redis_result,
                "influxdb": influxdb_result
            },
            "summary": {
                "total_checks": 4,
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0
            }
        }

        # Calculate summary
        for check_name, check_result in self.results["checks"].items():
            status = check_result["status"]
            if status == "healthy":
                self.results["summary"]["healthy"] += 1
            elif status == "degraded":
                self.results["summary"]["degraded"] += 1
            else:
                self.results["summary"]["unhealthy"] += 1

        # Determine overall status
        if self.results["summary"]["unhealthy"] > 0:
            self.results["overall_status"] = "unhealthy"
        elif self.results["summary"]["degraded"] > 0:
            self.results["overall_status"] = "degraded"

        return self.results

    def format_results(self, format_type: str = "text") -> str:
        """Format results for output."""
        if format_type == "json":
            return json.dumps(self.results, indent=2)

        # Text format
        output = []
        output.append("=" * 60)
        output.append("LICS Database Health Check Report")
        output.append("=" * 60)
        output.append(f"Timestamp: {self.results['timestamp']}")
        output.append(f"Duration: {self.results['duration_seconds']}s")
        output.append(f"Overall Status: {self.results['overall_status'].upper()}")
        output.append("")

        # Summary
        summary = self.results["summary"]
        output.append(f"Summary: {summary['healthy']} healthy, {summary['degraded']} degraded, {summary['unhealthy']} unhealthy")
        output.append("")

        # Individual checks
        for check_name, check_result in self.results["checks"].items():
            status_icon = "✅" if check_result["status"] == "healthy" else "⚠️" if check_result["status"] == "degraded" else "❌"
            output.append(f"{status_icon} {check_result['name']}: {check_result['status'].upper()}")

            # Details
            if check_result["details"]:
                for key, value in check_result["details"].items():
                    output.append(f"   {key}: {value}")

            # Metrics
            if check_result["metrics"]:
                output.append("   Metrics:")
                for key, value in check_result["metrics"].items():
                    output.append(f"     {key}: {value}")

            # Errors
            if check_result["errors"]:
                output.append("   Errors:")
                for error in check_result["errors"]:
                    output.append(f"     - {error}")

            output.append("")

        return "\n".join(output)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='LICS Database Health Check')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--exit-code', action='store_true',
                       help='Exit with non-zero code if any checks fail')

    args = parser.parse_args()

    try:
        checker = DatabaseHealthChecker()
        results = await checker.run_all_checks()
        formatted_output = checker.format_results(args.format)

        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(formatted_output)
            print(f"Results written to: {args.output}")
        else:
            print(formatted_output)

        # Exit code based on health status
        if args.exit_code:
            if results["overall_status"] == "unhealthy":
                sys.exit(1)
            elif results["overall_status"] == "degraded":
                sys.exit(2)

    except KeyboardInterrupt:
        print("\n⚠️ Health check cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
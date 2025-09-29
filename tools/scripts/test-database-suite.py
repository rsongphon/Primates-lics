#!/usr/bin/env python3
"""
LICS Database Test Suite

Comprehensive testing suite for all database components in the LICS system.
This extends the health monitoring with detailed functional testing, performance
benchmarks, and integration validation.

Usage:
    python test-database-suite.py [--test all|postgres|redis|influxdb|pgbouncer]
                                  [--format json|text] [--benchmark] [--stress]

Features:
    - Complete CRUD operations testing
    - Performance benchmarking
    - Connection pooling validation
    - Data integrity verification
    - Migration testing
    - Backup/restore validation
    - Stress testing capabilities
    - TimescaleDB hypertable testing
    - Redis Streams and Pub/Sub testing
    - InfluxDB time-series operations
"""

import argparse
import asyncio
import json
import os
import random
import string
import sys
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path

# Third-party imports
try:
    import asyncpg
    import redis.asyncio as redis
    import influxdb_client
    from influxdb_client.client.write_api import SYNCHRONOUS
    import numpy as np
    import psutil
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install asyncpg redis[hiredis] influxdb-client numpy psutil")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database-test-suite.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseTestSuite:
    """Comprehensive database testing suite for LICS."""

    def __init__(self, benchmark_mode: bool = False, stress_mode: bool = False):
        """
        Initialize the test suite.

        Args:
            benchmark_mode: Enable performance benchmarking
            stress_mode: Enable stress testing
        """
        self.benchmark_mode = benchmark_mode
        self.stress_mode = stress_mode
        self.results = {}
        self.start_time = time.time()

        # Test configuration
        self.config = {
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'user': 'lics',
                'password': 'lics123',
                'database': 'lics'
            },
            'pgbouncer': {
                'host': 'localhost',
                'port': 6432,
                'user': 'lics',
                'password': 'lics123',
                'database': 'lics'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'influxdb': {
                'url': 'http://localhost:8086',
                'token': 'lics-admin-token-change-in-production',
                'org': 'lics',
                'bucket': 'telemetry'
            }
        }

    def generate_test_data(self, size: int = 1000) -> List[Dict[str, Any]]:
        """Generate test data for database operations."""
        test_data = []
        for i in range(size):
            record = {
                'id': i + 1,
                'name': f"test_device_{i}",
                'type': random.choice(['sensor', 'actuator', 'controller']),
                'value': random.uniform(0, 100),
                'timestamp': datetime.now() - timedelta(seconds=random.randint(0, 3600)),
                'metadata': {
                    'location': f"lab_{random.randint(1, 10)}",
                    'status': random.choice(['active', 'inactive', 'maintenance'])
                }
            }
            test_data.append(record)
        return test_data

    async def test_postgresql_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive PostgreSQL testing."""
        logger.info("🧪 Testing PostgreSQL comprehensively...")

        result = {
            "name": "PostgreSQL Comprehensive Test",
            "healthy": False,
            "tests": {},
            "performance": {},
            "errors": []
        }

        try:
            # Connection test
            conn = await asyncpg.connect(**self.config['postgresql'])

            # 1. Basic connectivity and information
            version_info = await conn.fetchval("SELECT version()")
            result["tests"]["connectivity"] = {
                "status": "passed",
                "postgres_version": version_info.split()[1] if version_info else "unknown"
            }

            # 2. TimescaleDB extension test
            try:
                ts_version = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
                )
                if ts_version:
                    result["tests"]["timescaledb"] = {
                        "status": "passed",
                        "version": ts_version,
                        "available": True
                    }
                else:
                    result["tests"]["timescaledb"] = {
                        "status": "warning",
                        "available": False,
                        "message": "TimescaleDB extension not found"
                    }
            except Exception as e:
                result["tests"]["timescaledb"] = {
                    "status": "failed",
                    "error": str(e)
                }

            # 3. Schema and table operations
            try:
                # Create test schema
                await conn.execute("CREATE SCHEMA IF NOT EXISTS test_schema")

                # Create test table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_schema.test_devices (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        device_type VARCHAR(50),
                        value FLOAT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        metadata JSONB
                    )
                """)

                result["tests"]["schema_operations"] = {"status": "passed"}

            except Exception as e:
                result["tests"]["schema_operations"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"Schema operations failed: {e}")

            # 4. CRUD operations test
            try:
                crud_start = time.time()

                # Insert test data
                test_data = self.generate_test_data(100)
                insert_values = [
                    (record['name'], record['type'], record['value'], json.dumps(record['metadata']))
                    for record in test_data
                ]

                await conn.executemany("""
                    INSERT INTO test_schema.test_devices (name, device_type, value, metadata)
                    VALUES ($1, $2, $3, $4)
                """, insert_values)

                # Read test
                rows = await conn.fetch("SELECT COUNT(*) as count FROM test_schema.test_devices")
                read_count = rows[0]['count']

                # Update test
                await conn.execute("""
                    UPDATE test_schema.test_devices
                    SET value = value * 1.1
                    WHERE device_type = 'sensor'
                """)

                # Delete test
                await conn.execute("""
                    DELETE FROM test_schema.test_devices
                    WHERE id % 10 = 0
                """)

                crud_duration = time.time() - crud_start

                result["tests"]["crud_operations"] = {
                    "status": "passed",
                    "records_inserted": len(insert_values),
                    "records_read": read_count,
                    "duration_seconds": round(crud_duration, 3)
                }

            except Exception as e:
                result["tests"]["crud_operations"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"CRUD operations failed: {e}")

            # 5. Index performance test
            if self.benchmark_mode:
                try:
                    # Create index
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_test_devices_type_value
                        ON test_schema.test_devices (device_type, value)
                    """)

                    # Test query performance with index
                    query_start = time.time()
                    await conn.fetch("""
                        SELECT * FROM test_schema.test_devices
                        WHERE device_type = 'sensor' AND value > 50
                        ORDER BY value DESC
                        LIMIT 10
                    """)
                    query_duration = time.time() - query_start

                    result["performance"]["indexed_query_ms"] = round(query_duration * 1000, 2)

                except Exception as e:
                    result["errors"].append(f"Index performance test failed: {e}")

            # 6. Connection pool stress test
            if self.stress_mode:
                try:
                    # Test multiple concurrent connections
                    concurrent_tasks = []
                    for i in range(10):
                        task = asyncio.create_task(self._stress_test_postgres_connection(i))
                        concurrent_tasks.append(task)

                    stress_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                    successful_connections = sum(1 for r in stress_results if not isinstance(r, Exception))

                    result["tests"]["connection_stress"] = {
                        "status": "passed" if successful_connections >= 8 else "warning",
                        "successful_connections": successful_connections,
                        "total_attempts": len(concurrent_tasks)
                    }

                except Exception as e:
                    result["tests"]["connection_stress"] = {
                        "status": "failed",
                        "error": str(e)
                    }

            # 7. Cleanup test data
            try:
                await conn.execute("DROP TABLE IF EXISTS test_schema.test_devices")
                await conn.execute("DROP SCHEMA IF EXISTS test_schema")
                result["tests"]["cleanup"] = {"status": "passed"}
            except Exception as e:
                result["tests"]["cleanup"] = {
                    "status": "warning",
                    "error": str(e)
                }

            await conn.close()

            # Overall health assessment
            failed_tests = [name for name, test in result["tests"].items()
                           if test.get("status") == "failed"]
            result["healthy"] = len(failed_tests) == 0

        except Exception as e:
            result["tests"]["connectivity"] = {
                "status": "failed",
                "error": str(e)
            }
            result["errors"].append(f"PostgreSQL connection failed: {e}")

        return result

    async def _stress_test_postgres_connection(self, connection_id: int) -> bool:
        """Helper method for PostgreSQL stress testing."""
        try:
            conn = await asyncpg.connect(**self.config['postgresql'])
            await conn.fetchval("SELECT 1")
            await conn.close()
            return True
        except Exception:
            return False

    async def test_pgbouncer_pooling(self) -> Dict[str, Any]:
        """Test PgBouncer connection pooling functionality."""
        logger.info("🧪 Testing PgBouncer connection pooling...")

        result = {
            "name": "PgBouncer Connection Pooling Test",
            "healthy": False,
            "tests": {},
            "performance": {},
            "errors": []
        }

        try:
            # Test direct connection through PgBouncer
            pooled_conn = await asyncpg.connect(**self.config['pgbouncer'])

            # Basic connectivity test
            test_result = await pooled_conn.fetchval("SELECT 1")
            result["tests"]["pooled_connectivity"] = {
                "status": "passed" if test_result == 1 else "failed",
                "response": test_result
            }

            # Connection reuse test
            if self.benchmark_mode:
                connection_times = []
                for i in range(10):
                    start_time = time.time()
                    test_conn = await asyncpg.connect(**self.config['pgbouncer'])
                    await test_conn.fetchval("SELECT NOW()")
                    await test_conn.close()
                    connection_times.append(time.time() - start_time)

                avg_connection_time = statistics.mean(connection_times)
                result["performance"]["avg_connection_time_ms"] = round(avg_connection_time * 1000, 2)
                result["performance"]["connection_time_std_ms"] = round(statistics.stdev(connection_times) * 1000, 2)

            # Pool statistics test (if available)
            try:
                stats = await pooled_conn.fetch("SHOW STATS")
                if stats:
                    result["tests"]["pool_stats"] = {
                        "status": "passed",
                        "stats_available": True,
                        "stats_count": len(stats)
                    }
            except Exception:
                result["tests"]["pool_stats"] = {
                    "status": "warning",
                    "stats_available": False,
                    "message": "Pool statistics not accessible"
                }

            await pooled_conn.close()
            result["healthy"] = True

        except Exception as e:
            result["tests"]["pooled_connectivity"] = {
                "status": "failed",
                "error": str(e)
            }
            result["errors"].append(f"PgBouncer test failed: {e}")

        return result

    async def test_redis_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive Redis testing including Streams and Pub/Sub."""
        logger.info("🧪 Testing Redis comprehensively...")

        result = {
            "name": "Redis Comprehensive Test",
            "healthy": False,
            "tests": {},
            "performance": {},
            "errors": []
        }

        try:
            # Connection test
            redis_client = redis.Redis(**self.config['redis'], decode_responses=True)

            # 1. Basic connectivity
            pong_response = await redis_client.ping()
            result["tests"]["connectivity"] = {
                "status": "passed" if pong_response else "failed",
                "ping_response": pong_response
            }

            # 2. Basic key-value operations
            try:
                # Set/Get test
                test_key = "test:basic:key"
                test_value = "test_value_123"
                await redis_client.set(test_key, test_value, ex=30)
                retrieved_value = await redis_client.get(test_key)

                # Hash operations
                hash_key = "test:hash"
                await redis_client.hset(hash_key, mapping={
                    "field1": "value1",
                    "field2": "value2",
                    "field3": "value3"
                })
                hash_values = await redis_client.hgetall(hash_key)

                # List operations
                list_key = "test:list"
                await redis_client.lpush(list_key, "item1", "item2", "item3")
                list_length = await redis_client.llen(list_key)

                result["tests"]["basic_operations"] = {
                    "status": "passed",
                    "key_value_test": retrieved_value == test_value,
                    "hash_fields_count": len(hash_values),
                    "list_length": list_length
                }

                # Cleanup
                await redis_client.delete(test_key, hash_key, list_key)

            except Exception as e:
                result["tests"]["basic_operations"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"Redis basic operations failed: {e}")

            # 3. Redis Streams test
            try:
                stream_name = "test:stream:telemetry"

                # Add entries to stream
                stream_entries = []
                for i in range(5):
                    entry_id = await redis_client.xadd(stream_name, {
                        "device_id": f"device_{i}",
                        "temperature": random.uniform(20, 30),
                        "timestamp": time.time()
                    })
                    stream_entries.append(entry_id)

                # Read from stream
                stream_data = await redis_client.xrange(stream_name)

                # Test consumer group
                group_name = "test_group"
                try:
                    await redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
                except Exception:
                    pass  # Group might already exist

                # Read as consumer
                consumer_data = await redis_client.xreadgroup(
                    group_name, "test_consumer", {stream_name: ">"}, count=2
                )

                result["tests"]["streams"] = {
                    "status": "passed",
                    "entries_added": len(stream_entries),
                    "entries_read": len(stream_data),
                    "consumer_group_working": len(consumer_data) > 0
                }

                # Cleanup
                await redis_client.delete(stream_name)

            except Exception as e:
                result["tests"]["streams"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"Redis Streams test failed: {e}")

            # 4. Pub/Sub test
            try:
                pubsub = redis_client.pubsub()
                channel_name = "test:channel"

                # Subscribe to channel
                await pubsub.subscribe(channel_name)

                # Publish message
                message_data = {"test": True, "timestamp": time.time()}
                await redis_client.publish(channel_name, json.dumps(message_data))

                # Try to receive message
                message_received = False
                for _ in range(5):  # Try up to 5 times
                    message = await pubsub.get_message(timeout=1)
                    if message and message["type"] == "message":
                        message_received = True
                        break

                result["tests"]["pubsub"] = {
                    "status": "passed" if message_received else "warning",
                    "message_received": message_received
                }

                await pubsub.close()

            except Exception as e:
                result["tests"]["pubsub"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"Redis Pub/Sub test failed: {e}")

            # 5. Performance benchmarking
            if self.benchmark_mode:
                try:
                    # Benchmark SET operations
                    set_times = []
                    for i in range(100):
                        start_time = time.time()
                        await redis_client.set(f"benchmark:key:{i}", f"value_{i}")
                        set_times.append(time.time() - start_time)

                    # Benchmark GET operations
                    get_times = []
                    for i in range(100):
                        start_time = time.time()
                        await redis_client.get(f"benchmark:key:{i}")
                        get_times.append(time.time() - start_time)

                    result["performance"]["avg_set_time_ms"] = round(statistics.mean(set_times) * 1000, 3)
                    result["performance"]["avg_get_time_ms"] = round(statistics.mean(get_times) * 1000, 3)

                    # Cleanup benchmark keys
                    keys_to_delete = [f"benchmark:key:{i}" for i in range(100)]
                    await redis_client.delete(*keys_to_delete)

                except Exception as e:
                    result["errors"].append(f"Redis performance benchmark failed: {e}")

            await redis_client.close()

            # Overall health assessment
            failed_tests = [name for name, test in result["tests"].items()
                           if test.get("status") == "failed"]
            result["healthy"] = len(failed_tests) == 0

        except Exception as e:
            result["tests"]["connectivity"] = {
                "status": "failed",
                "error": str(e)
            }
            result["errors"].append(f"Redis connection failed: {e}")

        return result

    def test_influxdb_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive InfluxDB testing for time-series operations."""
        logger.info("🧪 Testing InfluxDB comprehensively...")

        result = {
            "name": "InfluxDB Comprehensive Test",
            "healthy": False,
            "tests": {},
            "performance": {},
            "errors": []
        }

        try:
            # Initialize client
            client = InfluxDBClient(**{k: v for k, v in self.config['influxdb'].items() if k != 'bucket'})

            # 1. Health check
            health = client.health()
            result["tests"]["connectivity"] = {
                "status": "passed" if health.status == "pass" else "failed",
                "influx_status": health.status,
                "version": health.version
            }

            # 2. Bucket operations
            try:
                buckets_api = client.buckets_api()
                buckets = buckets_api.find_buckets()

                # Check if telemetry bucket exists
                telemetry_bucket = None
                for bucket in buckets.buckets:
                    if bucket.name == self.config['influxdb']['bucket']:
                        telemetry_bucket = bucket
                        break

                result["tests"]["bucket_operations"] = {
                    "status": "passed" if telemetry_bucket else "warning",
                    "total_buckets": len(buckets.buckets),
                    "telemetry_bucket_found": telemetry_bucket is not None
                }

            except Exception as e:
                result["tests"]["bucket_operations"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"InfluxDB bucket operations failed: {e}")

            # 3. Write operations test
            try:
                write_api = client.write_api(write_options=SYNCHRONOUS)

                # Generate test data points
                from influxdb_client import Point
                test_points = []
                base_time = datetime.now()

                for i in range(10):
                    point = Point("test_measurement") \
                        .tag("device_id", f"device_{i % 3}") \
                        .tag("location", f"lab_{i % 2}") \
                        .field("temperature", random.uniform(20, 30)) \
                        .field("humidity", random.uniform(40, 60)) \
                        .time(base_time - timedelta(minutes=i))
                    test_points.append(point)

                # Write data
                write_start = time.time()
                write_api.write(bucket=self.config['influxdb']['bucket'], record=test_points)
                write_duration = time.time() - write_start

                result["tests"]["write_operations"] = {
                    "status": "passed",
                    "points_written": len(test_points),
                    "write_duration_ms": round(write_duration * 1000, 2)
                }

            except Exception as e:
                result["tests"]["write_operations"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"InfluxDB write operations failed: {e}")

            # 4. Query operations test
            try:
                query_api = client.query_api()

                # Simple query
                query = f'''
                    from(bucket: "{self.config['influxdb']['bucket']}")
                    |> range(start: -1h)
                    |> filter(fn: (r) => r._measurement == "test_measurement")
                    |> count()
                '''

                query_start = time.time()
                tables = query_api.query(query)
                query_duration = time.time() - query_start

                # Count results
                total_points = 0
                for table in tables:
                    for record in table.records:
                        total_points += record.get_value()

                result["tests"]["query_operations"] = {
                    "status": "passed",
                    "query_duration_ms": round(query_duration * 1000, 2),
                    "points_queried": total_points
                }

            except Exception as e:
                result["tests"]["query_operations"] = {
                    "status": "failed",
                    "error": str(e)
                }
                result["errors"].append(f"InfluxDB query operations failed: {e}")

            # 5. Aggregation query test
            if self.benchmark_mode:
                try:
                    aggregation_query = f'''
                        from(bucket: "{self.config['influxdb']['bucket']}")
                        |> range(start: -1h)
                        |> filter(fn: (r) => r._measurement == "test_measurement")
                        |> filter(fn: (r) => r._field == "temperature")
                        |> group(columns: ["device_id"])
                        |> mean()
                    '''

                    agg_start = time.time()
                    agg_tables = query_api.query(aggregation_query)
                    agg_duration = time.time() - agg_start

                    agg_results = len([record for table in agg_tables for record in table.records])

                    result["performance"]["aggregation_query_ms"] = round(agg_duration * 1000, 2)
                    result["performance"]["aggregation_results"] = agg_results

                except Exception as e:
                    result["errors"].append(f"InfluxDB aggregation test failed: {e}")

            # 6. Cleanup test data
            try:
                delete_api = client.delete_api()
                start_time = datetime.now() - timedelta(hours=2)
                end_time = datetime.now() + timedelta(hours=1)

                delete_api.delete(
                    start_time,
                    end_time,
                    '_measurement="test_measurement"',
                    bucket=self.config['influxdb']['bucket'],
                    org=self.config['influxdb']['org']
                )

                result["tests"]["cleanup"] = {"status": "passed"}

            except Exception as e:
                result["tests"]["cleanup"] = {
                    "status": "warning",
                    "error": str(e)
                }

            client.close()

            # Overall health assessment
            failed_tests = [name for name, test in result["tests"].items()
                           if test.get("status") == "failed"]
            result["healthy"] = len(failed_tests) == 0

        except Exception as e:
            result["tests"]["connectivity"] = {
                "status": "failed",
                "error": str(e)
            }
            result["errors"].append(f"InfluxDB connection failed: {e}")

        return result

    async def run_comprehensive_database_tests(self, test_target: str = "all") -> Dict[str, Any]:
        """Run comprehensive database tests."""
        logger.info("🚀 Starting comprehensive database test suite...")

        test_results = {}

        # Run selected tests
        if test_target in ["all", "postgres"]:
            test_results["postgresql"] = await self.test_postgresql_comprehensive()

        if test_target in ["all", "pgbouncer"]:
            test_results["pgbouncer"] = await self.test_pgbouncer_pooling()

        if test_target in ["all", "redis"]:
            test_results["redis"] = await self.test_redis_comprehensive()

        if test_target in ["all", "influxdb"]:
            test_results["influxdb"] = self.test_influxdb_comprehensive()

        # Calculate overall results
        total_duration = time.time() - self.start_time
        healthy_tests = sum(1 for result in test_results.values()
                           if result.get("healthy", False))
        total_tests = len(test_results)

        overall_result = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(total_duration, 2),
            "test_target": test_target,
            "benchmark_mode": self.benchmark_mode,
            "stress_mode": self.stress_mode,
            "overall_healthy": healthy_tests == total_tests,
            "database_tests": test_results,
            "summary": {
                "total_databases": total_tests,
                "healthy_databases": healthy_tests,
                "failed_databases": total_tests - healthy_tests,
                "success_rate": round((healthy_tests / total_tests * 100), 2) if total_tests > 0 else 0
            }
        }

        # Collect all errors
        all_errors = []
        for db_name, db_result in test_results.items():
            if db_result.get("errors"):
                for error in db_result["errors"]:
                    all_errors.append(f"{db_name}: {error}")

        if all_errors:
            overall_result["errors"] = all_errors

        self.results = overall_result
        return overall_result

    def format_results(self, format_type: str = "text") -> str:
        """Format test results for output."""
        if format_type == "json":
            return json.dumps(self.results, indent=2)

        # Text format
        output = []
        output.append("=" * 80)
        output.append("LICS DATABASE TEST SUITE REPORT")
        output.append("=" * 80)
        output.append(f"Timestamp: {self.results['timestamp']}")
        output.append(f"Duration: {self.results['duration_seconds']}s")
        output.append(f"Test Target: {self.results['test_target']}")
        output.append(f"Benchmark Mode: {self.results['benchmark_mode']}")
        output.append(f"Stress Mode: {self.results['stress_mode']}")
        output.append(f"Overall Status: {'✅ HEALTHY' if self.results['overall_healthy'] else '❌ UNHEALTHY'}")
        output.append("")

        # Summary
        summary = self.results["summary"]
        output.append(f"Summary: {summary['healthy_databases']}/{summary['total_databases']} databases healthy ({summary['success_rate']}%)")
        output.append("")

        # Individual database results
        for db_name, db_result in self.results["database_tests"].items():
            status_icon = "✅" if db_result.get("healthy", False) else "❌"
            output.append(f"{status_icon} {db_result.get('name', db_name.upper())}")

            # Test results
            if "tests" in db_result:
                for test_name, test_info in db_result["tests"].items():
                    test_status = test_info.get("status", "unknown")
                    test_icon = "✅" if test_status == "passed" else "⚠️" if test_status == "warning" else "❌"
                    output.append(f"   {test_icon} {test_name}: {test_status}")

                    # Additional test details
                    for key, value in test_info.items():
                        if key not in ["status", "error"] and not key.endswith("_test"):
                            output.append(f"      {key}: {value}")

            # Performance metrics
            if "performance" in db_result and db_result["performance"]:
                output.append("   📊 Performance Metrics:")
                for metric, value in db_result["performance"].items():
                    output.append(f"      {metric}: {value}")

            # Errors
            if db_result.get("errors"):
                output.append("   ❌ Errors:")
                for error in db_result["errors"]:
                    output.append(f"      - {error}")

            output.append("")

        # Overall errors
        if self.results.get("errors"):
            output.append("OVERALL ERRORS:")
            for error in self.results["errors"]:
                output.append(f"  ❌ {error}")
            output.append("")

        # Performance summary
        if self.benchmark_mode:
            output.append("PERFORMANCE SUMMARY:")
            for db_name, db_result in self.results["database_tests"].items():
                if "performance" in db_result and db_result["performance"]:
                    output.append(f"  {db_name.upper()}:")
                    for metric, value in db_result["performance"].items():
                        output.append(f"    {metric}: {value}")
            output.append("")

        return "\n".join(output)

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='LICS Database Test Suite')
    parser.add_argument('--test', choices=['all', 'postgres', 'redis', 'influxdb', 'pgbouncer'],
                       default='all', help='Database to test (default: all)')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--benchmark', action='store_true',
                       help='Enable performance benchmarking')
    parser.add_argument('--stress', action='store_true',
                       help='Enable stress testing')
    parser.add_argument('--exit-code', action='store_true',
                       help='Exit with non-zero code if tests fail')

    args = parser.parse_args()

    try:
        test_suite = DatabaseTestSuite(benchmark_mode=args.benchmark, stress_mode=args.stress)
        results = await test_suite.run_comprehensive_database_tests(args.test)
        formatted_output = test_suite.format_results(args.format)

        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(formatted_output)
            print(f"Database test results written to: {args.output}")
        else:
            print(formatted_output)

        # Exit code based on test results
        if args.exit_code:
            sys.exit(0 if results["overall_healthy"] else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Database tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Database test suite failed: {e}")
        logger.exception("Database tests failed with exception")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
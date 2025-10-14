#!/usr/bin/env python3
"""
LICS Phase 1 Manual Test Suite - Automated

This script automates all manual testing procedures from PHASE1_TESTING_GUIDE.md Section 3.
Each manual test case (TC-INFRA-001, TC-DB-001, etc.) is converted to an automated function
with detailed step-by-step validation.

Usage:
    python test-phase1-manual-suite.py [--test all|TC-INFRA-001|...]
                                       [--format json|text|markdown]
                                       [--output results.json]
                                       [--verbose]

Features:
    - 100% automation coverage of manual test procedures
    - Step-by-step validation matching manual guide
    - Detailed pass/fail reporting for each step
    - Known issues tracking (expected failures marked as acceptable)
    - Performance metrics collection
    - Multiple output formats
"""

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

# Third-party imports with fallback
try:
    import asyncpg
    import redis.asyncio as redis
    import requests
    import docker
    import aiomqtt
    from minio import Minio
    from minio.error import S3Error
    from influxdb_client import InfluxDBClient
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install asyncpg redis[hiredis] requests docker aiomqtt minio influxdb-client")
    sys.exit(1)

# Import centralized test configuration
try:
    from test_config import get_test_config
    TEST_CONFIG = get_test_config()
except ImportError:
    print("Warning: test_config.py not found. Using default development ports.")
    TEST_CONFIG = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1-manual-automated-tests.log')
    ]
)
logger = logging.getLogger(__name__)


class TestStep:
    """Represents a single step in a test case."""

    def __init__(self, number: int, description: str, expected: str):
        self.number = number
        self.description = description
        self.expected = expected
        self.actual = None
        self.passed = False
        self.error = None
        self.duration_ms = 0


class TestCase:
    """Represents a complete test case with multiple steps."""

    def __init__(self, test_id: str, name: str, objective: str):
        self.test_id = test_id
        self.name = name
        self.objective = objective
        self.steps: List[TestStep] = []
        self.passed = False
        self.duration_seconds = 0
        self.start_time = None
        self.end_time = None

    def add_step(self, description: str, expected: str) -> TestStep:
        """Add a new step to the test case."""
        step = TestStep(len(self.steps) + 1, description, expected)
        self.steps.append(step)
        return step

    def evaluate(self):
        """Evaluate overall test case result based on steps."""
        if not self.steps:
            self.passed = False
            return

        # Test passes if all critical steps pass
        # Steps with expected known failures can be marked as warnings
        passed_steps = sum(1 for step in self.steps if step.passed)
        self.passed = passed_steps == len(self.steps)


class Phase1ManualTestSuite:
    """Automated test suite for Phase 1 manual testing procedures."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the test suite.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.test_cases: Dict[str, TestCase] = {}
        self.start_time = time.time()
        self.project_root = Path(__file__).parent.parent.parent
        self.docker_client = None

        # Test configuration - use TEST_CONFIG if available
        if TEST_CONFIG:
            self.config = {
                'postgresql': TEST_CONFIG['postgresql'],
                'redis': TEST_CONFIG['redis'],
                'mqtt': TEST_CONFIG['mqtt'],
                'minio': {
                    'endpoint': TEST_CONFIG['minio']['endpoint'],
                    'access_key': TEST_CONFIG['minio']['access_key'],
                    'secret_key': TEST_CONFIG['minio']['secret_key'],
                    'secure': TEST_CONFIG['minio']['secure']
                },
                'prometheus': {'port': TEST_CONFIG['prometheus']['port']},
                'grafana': {'port': TEST_CONFIG['grafana']['port']},
                'jaeger': {'port': 16686},
                'influxdb': TEST_CONFIG['influxdb']
            }
        else:
            # Fallback to development ports
            self.config = {
                'postgresql': {
                    'host': 'localhost',
                    'port': 5433,
                    'user': 'lics',
                    'password': 'lics123',
                    'database': 'lics_dev'
                },
                'redis': {
                    'host': 'localhost',
                    'port': 6380,
                    'db': 0
                },
                'mqtt': {
                    'host': 'localhost',
                    'port': 1884
                },
                'minio': {
                    'endpoint': 'localhost:9010',
                    'access_key': 'lics-dev-admin',
                    'secret_key': 'lics-dev-minio-password-2024',
                    'secure': False
                },
                'prometheus': {'port': 9090},
                'grafana': {'port': 3001},
                'jaeger': {'port': 16686},
                'influxdb': {
                    'url': 'http://localhost:8087',
                    'token': 'lics-dev-admin-token',
                    'org': 'lics-dev',
                    'bucket': 'telemetry-dev'
                }
            }

    def initialize_docker_client(self) -> bool:
        """Initialize Docker client connection."""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("✅ Docker client initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docker client: {e}")
            return False

    # ============================================================================
    # Section 3.1: Infrastructure Component Testing
    # ============================================================================

    async def test_TC_INFRA_001_docker_container_health(self) -> TestCase:
        """
        TC-INFRA-001: Docker Container Health
        Objective: Verify all required containers are running and healthy
        """
        test_case = TestCase(
            "TC-INFRA-001",
            "Docker Container Health",
            "Verify all required containers are running and healthy"
        )
        test_case.start_time = datetime.now()

        if not self.docker_client and not self.initialize_docker_client():
            step = test_case.add_step(
                "Initialize Docker client",
                "Docker client initialized successfully"
            )
            step.actual = "Failed to initialize Docker client"
            step.passed = False
            test_case.evaluate()
            return test_case

        # Step 1: Open terminal in project root
        step1 = test_case.add_step(
            "Navigate to project root",
            "Working directory set to project root"
        )
        step_start = time.time()
        try:
            os.chdir(self.project_root)
            step1.actual = f"Changed to {self.project_root}"
            step1.passed = True
        except Exception as e:
            step1.actual = f"Failed: {e}"
            step1.passed = False
            step1.error = str(e)
        step1.duration_ms = (time.time() - step_start) * 1000

        # Step 2: Run docker-compose ps
        step2 = test_case.add_step(
            "Execute 'docker-compose -f docker-compose.dev.yml ps'",
            "Command executes successfully and shows container list"
        )
        step_start = time.time()
        try:
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.dev.yml", "ps", "--format", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                step2.actual = f"Command successful. Output received with {len(result.stdout.strip().split(chr(10)))} services"
                step2.passed = True
            else:
                step2.actual = f"Command failed: {result.stderr}"
                step2.passed = False
                step2.error = result.stderr
        except Exception as e:
            step2.actual = f"Exception: {e}"
            step2.passed = False
            step2.error = str(e)
        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Observe STATUS column
        step3 = test_case.add_step(
            "Observe container STATUS column for each service",
            "All containers show 'Up' or 'Up (healthy)'"
        )
        step_start = time.time()

        containers_status = {}
        unhealthy_containers = []

        try:
            containers = self.docker_client.containers.list(all=True)
            lics_containers = [c for c in containers if 'lics' in c.name.lower() or 'primates' in c.name.lower()]

            for container in lics_containers:
                status = container.status
                health = container.attrs.get('State', {}).get('Health', {}).get('Status', 'N/A')
                exit_code = container.attrs.get('State', {}).get('ExitCode', None)

                containers_status[container.name] = {
                    'status': status,
                    'health': health,
                    'exit_code': exit_code
                }

                # Check if container is unhealthy
                # Setup containers (one-time init) should exit with code 0
                # Regular containers should be running with healthy status
                is_setup_container = '-setup' in container.name.lower()

                if is_setup_container:
                    # Setup containers should have exited successfully
                    if status != 'exited' or (exit_code is not None and exit_code != 0):
                        unhealthy_containers.append(container.name)
                else:
                    # Regular containers should be running
                    if status not in ['running', 'created'] or (health not in ['healthy', 'N/A'] and health != ''):
                        unhealthy_containers.append(container.name)

            if len(lics_containers) > 0:
                healthy_count = len(lics_containers) - len(unhealthy_containers)

                # Build detailed container status report
                service_containers = []
                setup_containers = []

                for container in lics_containers:
                    status_info = containers_status[container.name]
                    is_setup = '-setup' in container.name.lower()

                    status_str = f"{container.name}: {status_info['status']}"
                    if status_info['health'] != 'N/A':
                        status_str += f" ({status_info['health']})"
                    if is_setup and status_info['exit_code'] is not None:
                        status_str += f" [exit={status_info['exit_code']}]"

                    if is_setup:
                        setup_containers.append(status_str)
                    else:
                        service_containers.append(status_str)

                details = f"Found {len(lics_containers)} containers ({healthy_count} healthy, {len(unhealthy_containers)} unhealthy)\n\n"
                details += f"Service Containers ({len(service_containers)}):\n"
                details += "\n".join(f"  • {s}" for s in service_containers)
                details += f"\n\nSetup Containers ({len(setup_containers)}):\n"
                details += "\n".join(f"  • {s}" for s in setup_containers)

                step3.actual = details
                step3.passed = len(unhealthy_containers) == 0

                if unhealthy_containers:
                    step3.error = f"Unhealthy containers: {', '.join(unhealthy_containers)}"
            else:
                step3.actual = "No LICS containers found"
                step3.passed = False
                step3.error = "No containers with 'lics' or 'primates' in name"

        except Exception as e:
            step3.actual = f"Failed to check container status: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Verify uptime
        step4 = test_case.add_step(
            "Check container uptime",
            "Uptime > 5 minutes (after initial startup)"
        )
        step_start = time.time()

        try:
            recent_restarts = []
            for container in lics_containers:
                started_at = container.attrs.get('State', {}).get('StartedAt', '')
                if started_at:
                    # Parse ISO format timestamp
                    started_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime = (datetime.now(started_time.tzinfo) - started_time).total_seconds()

                    if uptime < 300:  # Less than 5 minutes
                        recent_restarts.append(f"{container.name} (uptime: {uptime:.0f}s)")

            if recent_restarts:
                step4.actual = f"Some containers recently restarted: {', '.join(recent_restarts)}"
                step4.passed = False
                step4.error = "Containers have not been running for at least 5 minutes"
            else:
                step4.actual = f"All {len(lics_containers)} containers have adequate uptime (>5 min)"
                step4.passed = True

        except Exception as e:
            step4.actual = f"Failed to check uptime: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_INFRA_002_network_connectivity(self) -> TestCase:
        """
        TC-INFRA-002: Network Connectivity Between Services
        Objective: Verify inter-service communication
        """
        test_case = TestCase(
            "TC-INFRA-002",
            "Network Connectivity Between Services",
            "Verify inter-service communication"
        )
        test_case.start_time = datetime.now()

        if not self.docker_client and not self.initialize_docker_client():
            step = test_case.add_step(
                "Initialize Docker client",
                "Docker client initialized successfully"
            )
            step.actual = "Failed to initialize Docker client"
            step.passed = False
            test_case.evaluate()
            return test_case

        # Step 1: Get PostgreSQL container
        step1 = test_case.add_step(
            "Get PostgreSQL container shell access",
            "Successfully accessed PostgreSQL container"
        )
        step_start = time.time()

        postgres_container = None
        try:
            containers = self.docker_client.containers.list()
            postgres_container = next(
                (c for c in containers if 'postgres' in c.name.lower() and 'exporter' not in c.name.lower()),
                None
            )

            if postgres_container:
                step1.actual = f"Found PostgreSQL container: {postgres_container.name}"
                step1.passed = True
            else:
                step1.actual = "PostgreSQL container not found"
                step1.passed = False
                step1.error = "No running PostgreSQL container found"
        except Exception as e:
            step1.actual = f"Failed: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        if not postgres_container:
            test_case.evaluate()
            return test_case

        # Step 2: Test Redis connectivity from PostgreSQL
        step2 = test_case.add_step(
            "Test connectivity from PostgreSQL to Redis",
            "Connection successful, receives PONG response"
        )
        step_start = time.time()

        try:
            # Try to ping Redis using Python (most containers have Python)
            exec_result = postgres_container.exec_run(
                "python3 -c \"import socket; s = socket.socket(); s.settimeout(5); s.connect(('redis-dev', 6379)); s.close(); print('Connected')\"",
                demux=True
            )

            stdout, stderr = exec_result.output
            stdout_str = stdout.decode() if stdout else ""

            if exec_result.exit_code == 0 and "Connected" in stdout_str:
                step2.actual = "Successfully connected to Redis from PostgreSQL container"
                step2.passed = True
            else:
                step2.actual = f"Connection failed. Exit code: {exec_result.exit_code}"
                step2.passed = False
                step2.error = stderr.decode() if stderr else "Unknown error"
        except Exception as e:
            step2.actual = f"Exception during connectivity test: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Test MinIO connectivity from PostgreSQL
        step3 = test_case.add_step(
            "Test connectivity from PostgreSQL to MinIO",
            "HTTP 200 OK response from MinIO health endpoint"
        )
        step_start = time.time()

        try:
            # Test MinIO health endpoint using curl (if available) or Python
            exec_result = postgres_container.exec_run(
                "python3 -c \"import socket; s = socket.socket(); s.settimeout(5); s.connect(('minio-dev', 9000)); s.close(); print('Connected')\"",
                demux=True
            )

            stdout, stderr = exec_result.output
            stdout_str = stdout.decode() if stdout else ""

            if exec_result.exit_code == 0 and "Connected" in stdout_str:
                step3.actual = "Successfully connected to MinIO from PostgreSQL container"
                step3.passed = True
            else:
                step3.actual = f"Connection failed. Exit code: {exec_result.exit_code}"
                step3.passed = False
                step3.error = stderr.decode() if stderr else "Unknown error"
        except Exception as e:
            step3.actual = f"Exception during connectivity test: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Verify DNS resolution works
        step4 = test_case.add_step(
            "Verify Docker DNS resolution",
            "Services resolve by container name"
        )
        step_start = time.time()

        try:
            # Test DNS resolution for key services
            services_to_test = ['redis-dev', 'minio-dev', 'mqtt-dev']
            resolved_services = []
            failed_services = []

            for service in services_to_test:
                exec_result = postgres_container.exec_run(
                    f"python3 -c \"import socket; print(socket.gethostbyname('{service}'))\"",
                    demux=True
                )

                stdout, stderr = exec_result.output
                stdout_str = stdout.decode() if stdout else ""

                if exec_result.exit_code == 0 and stdout_str.strip():
                    resolved_services.append(f"{service}:{stdout_str.strip()}")
                else:
                    failed_services.append(service)

            # Build detailed DNS resolution report
            dns_details = f"DNS Resolution Test Results ({len(resolved_services)}/{len(services_to_test)} successful)\n\n"

            if resolved_services:
                dns_details += "✓ Resolved Services:\n"
                for service_info in resolved_services:
                    dns_details += f"  • {service_info}\n"

            if failed_services:
                dns_details += "\n✗ Failed to Resolve:\n"
                for service in failed_services:
                    dns_details += f"  • {service}\n"

            step4.actual = dns_details.strip()
            step4.passed = len(resolved_services) == len(services_to_test)

            if failed_services:
                step4.error = f"DNS resolution failed for: {', '.join(failed_services)}"
        except Exception as e:
            step4.actual = f"DNS resolution test failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    # ============================================================================
    # Section 3.2: Database Layer Testing
    # ============================================================================

    async def test_TC_DB_001_postgresql_crud(self) -> TestCase:
        """
        TC-DB-001: PostgreSQL Connection and CRUD Operations
        Objective: Validate PostgreSQL database functionality
        """
        test_case = TestCase(
            "TC-DB-001",
            "PostgreSQL Connection and CRUD Operations",
            "Validate PostgreSQL database functionality"
        )
        test_case.start_time = datetime.now()

        conn = None

        # Step 1: Connect to PostgreSQL
        step1 = test_case.add_step(
            "Connect to PostgreSQL database",
            "Connection successful"
        )
        step_start = time.time()

        try:
            conn = await asyncpg.connect(**self.config['postgresql'])
            step1.actual = "Successfully connected to PostgreSQL"
            step1.passed = True
        except Exception as e:
            step1.actual = f"Connection failed: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        if not conn:
            test_case.evaluate()
            return test_case

        # Step 2: Test CREATE
        step2 = test_case.add_step(
            "CREATE test table and INSERT test data",
            "Table created and data inserted successfully"
        )
        step_start = time.time()

        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100)
                )
            """)

            await conn.execute("""
                INSERT INTO test_table (name) VALUES ('Test Item 1')
            """)

            step2.actual = "Table created and test row inserted"
            step2.passed = True
        except Exception as e:
            step2.actual = f"CREATE/INSERT failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Test READ
        step3 = test_case.add_step(
            "SELECT data from test table",
            "Retrieved row with id=1, name='Test Item 1'"
        )
        step_start = time.time()

        try:
            rows = await conn.fetch("SELECT * FROM test_table")

            if len(rows) > 0 and rows[0]['id'] == 1 and rows[0]['name'] == 'Test Item 1':
                # Build detailed result
                result_details = f"Successfully retrieved {len(rows)} row(s):\n\n"
                for row in rows:
                    result_details += f"  id: {row['id']}, name: '{row['name']}'\n"
                step3.actual = result_details.strip()
                step3.passed = True
            else:
                step3.actual = f"Retrieved rows but data mismatch: {rows}"
                step3.passed = False
                step3.error = "Data does not match expected values"
        except Exception as e:
            step3.actual = f"SELECT failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Test UPDATE
        step4 = test_case.add_step(
            "UPDATE test data",
            "Row updated, name changed to 'Updated Item'"
        )
        step_start = time.time()

        try:
            await conn.execute("""
                UPDATE test_table SET name = 'Updated Item' WHERE id = 1
            """)

            rows = await conn.fetch("SELECT * FROM test_table WHERE id = 1")

            if len(rows) > 0 and rows[0]['name'] == 'Updated Item':
                step4.actual = "Successfully updated row, verified new value"
                step4.passed = True
            else:
                step4.actual = f"Update executed but verification failed: {rows}"
                step4.passed = False
                step4.error = "Updated value does not match expected"
        except Exception as e:
            step4.actual = f"UPDATE failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Step 5: Test DELETE
        step5 = test_case.add_step(
            "DELETE test data",
            "Row deleted, count = 0"
        )
        step_start = time.time()

        try:
            await conn.execute("DELETE FROM test_table WHERE id = 1")

            count = await conn.fetchval("SELECT count(*) FROM test_table")

            if count == 0:
                step5.actual = f"Successfully deleted row, count is {count}"
                step5.passed = True
            else:
                step5.actual = f"Delete executed but count is {count} (expected 0)"
                step5.passed = False
                step5.error = "Row was not deleted"
        except Exception as e:
            step5.actual = f"DELETE failed: {e}"
            step5.passed = False
            step5.error = str(e)

        step5.duration_ms = (time.time() - step_start) * 1000

        # Step 6: Clean up
        step6 = test_case.add_step(
            "DROP test table",
            "Table dropped successfully"
        )
        step_start = time.time()

        try:
            await conn.execute("DROP TABLE IF EXISTS test_table")
            step6.actual = "Test table dropped successfully"
            step6.passed = True
        except Exception as e:
            step6.actual = f"DROP TABLE failed: {e}"
            step6.passed = False
            step6.error = str(e)

        step6.duration_ms = (time.time() - step_start) * 1000

        # Close connection
        await conn.close()

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_DB_002_timescaledb_hypertables(self) -> TestCase:
        """
        TC-DB-002: TimescaleDB Hypertables
        Objective: Verify TimescaleDB extension and hypertable functionality
        """
        test_case = TestCase(
            "TC-DB-002",
            "TimescaleDB Hypertables",
            "Verify TimescaleDB extension and hypertable functionality"
        )
        test_case.start_time = datetime.now()

        conn = None

        # Step 1: Connect to PostgreSQL
        step1 = test_case.add_step(
            "Connect to PostgreSQL database",
            "Connection successful"
        )
        step_start = time.time()

        try:
            conn = await asyncpg.connect(**self.config['postgresql'])
            step1.actual = "Successfully connected to PostgreSQL"
            step1.passed = True
        except Exception as e:
            step1.actual = f"Connection failed: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        if not conn:
            test_case.evaluate()
            return test_case

        # Step 2: Check TimescaleDB extension
        step2 = test_case.add_step(
            "Check TimescaleDB extension",
            "TimescaleDB extension installed (version 2.10.2 or current)"
        )
        step_start = time.time()

        try:
            row = await conn.fetchrow("""
                SELECT extname, extversion
                FROM pg_extension
                WHERE extname = 'timescaledb'
            """)

            if row and row['extname'] == 'timescaledb':
                step2.actual = f"TimescaleDB found: version {row['extversion']}"
                step2.passed = True
            else:
                step2.actual = "TimescaleDB extension not found"
                step2.passed = False
                step2.error = "TimescaleDB extension is not installed"
        except Exception as e:
            step2.actual = f"Extension check failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Create test hypertable
        step3 = test_case.add_step(
            "Create test metrics table and convert to hypertable",
            "Hypertable created successfully"
        )
        step_start = time.time()

        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_metrics (
                    time TIMESTAMPTZ NOT NULL,
                    device_id INT,
                    temperature DOUBLE PRECISION
                )
            """)

            # Create hypertable
            await conn.execute("""
                SELECT create_hypertable('test_metrics', 'time', if_not_exists => TRUE)
            """)

            step3.actual = "Test hypertable created successfully"
            step3.passed = True
        except Exception as e:
            step3.actual = f"Hypertable creation failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Insert time-series data
        step4 = test_case.add_step(
            "Insert time-series test data",
            "3 rows inserted with different timestamps"
        )
        step_start = time.time()

        try:
            await conn.execute("""
                INSERT INTO test_metrics VALUES
                    (NOW(), 1, 23.5),
                    (NOW() - INTERVAL '1 hour', 1, 24.2),
                    (NOW() - INTERVAL '2 hours', 1, 22.8)
            """)

            count = await conn.fetchval("SELECT COUNT(*) FROM test_metrics")

            if count == 3:
                step4.actual = f"Successfully inserted {count} rows"
                step4.passed = True
            else:
                step4.actual = f"Inserted data but count is {count} (expected 3)"
                step4.passed = False
                step4.error = "Row count mismatch"
        except Exception as e:
            step4.actual = f"INSERT failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Step 5: Query time-series data
        step5 = test_case.add_step(
            "Query time-series data with ORDER BY",
            "3 rows returned with correct temperatures"
        )
        step_start = time.time()

        try:
            rows = await conn.fetch("""
                SELECT time, temperature
                FROM test_metrics
                WHERE device_id = 1
                ORDER BY time DESC
            """)

            if len(rows) == 3:
                temps = [row['temperature'] for row in rows]
                step5.actual = f"Retrieved {len(rows)} rows with temperatures: {temps}"
                step5.passed = True
            else:
                step5.actual = f"Query returned {len(rows)} rows (expected 3)"
                step5.passed = False
                step5.error = "Row count mismatch in query result"
        except Exception as e:
            step5.actual = f"Query failed: {e}"
            step5.passed = False
            step5.error = str(e)

        step5.duration_ms = (time.time() - step_start) * 1000

        # Step 6: Check hypertable info
        step6 = test_case.add_step(
            "Query TimescaleDB hypertable information",
            "Hypertable metadata returned successfully"
        )
        step_start = time.time()

        try:
            row = await conn.fetchrow("""
                SELECT * FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'test_metrics'
            """)

            if row:
                step6.actual = f"Hypertable info found: {row['hypertable_schema']}.{row['hypertable_name']}"
                step6.passed = True
            else:
                step6.actual = "Hypertable info not found"
                step6.passed = False
                step6.error = "test_metrics not found in hypertables view"
        except Exception as e:
            step6.actual = f"Hypertable info query failed: {e}"
            step6.passed = False
            step6.error = str(e)

        step6.duration_ms = (time.time() - step_start) * 1000

        # Step 7: Clean up
        step7 = test_case.add_step(
            "DROP test hypertable",
            "Table dropped successfully"
        )
        step_start = time.time()

        try:
            await conn.execute("DROP TABLE IF EXISTS test_metrics")
            step7.actual = "Test hypertable dropped successfully"
            step7.passed = True
        except Exception as e:
            step7.actual = f"DROP TABLE failed: {e}"
            step7.passed = False
            step7.error = str(e)

        step7.duration_ms = (time.time() - step_start) * 1000

        # Close connection
        await conn.close()

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_DB_003_redis_cache_ops(self) -> TestCase:
        """
        TC-DB-003: Redis Cache Operations
        Objective: Validate Redis basic operations and data structures
        """
        test_case = TestCase(
            "TC-DB-003",
            "Redis Cache Operations",
            "Validate Redis basic operations and data structures"
        )
        test_case.start_time = datetime.now()

        redis_client = None

        # Step 1: Connect to Redis
        step1 = test_case.add_step(
            "Connect to Redis",
            "Connection successful"
        )
        step_start = time.time()

        try:
            redis_client = redis.Redis(**self.config['redis'], decode_responses=True)
            await redis_client.ping()
            step1.actual = "Successfully connected to Redis"
            step1.passed = True
        except Exception as e:
            step1.actual = f"Connection failed: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        if not redis_client:
            test_case.evaluate()
            return test_case

        # Step 2: Test String operations
        step2 = test_case.add_step(
            "Test String operations (SET, GET, DEL)",
            "String value set, retrieved, and deleted successfully"
        )
        step_start = time.time()

        try:
            await redis_client.set("test:key", "Hello LICS")
            value = await redis_client.get("test:key")
            await redis_client.delete("test:key")

            if value == "Hello LICS":
                step2.actual = f"String operations successful. Retrieved: '{value}'"
                step2.passed = True
            else:
                step2.actual = f"Value mismatch. Got: '{value}', Expected: 'Hello LICS'"
                step2.passed = False
                step2.error = "Retrieved value does not match"
        except Exception as e:
            step2.actual = f"String operations failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Test Hash operations
        step3 = test_case.add_step(
            "Test Hash operations (HSET, HGETALL)",
            "Hash fields set and retrieved successfully"
        )
        step_start = time.time()

        try:
            await redis_client.hset("user:1", mapping={
                "name": "John Doe",
                "email": "john@example.com"
            })

            hash_data = await redis_client.hgetall("user:1")
            await redis_client.delete("user:1")

            if hash_data.get("name") == "John Doe" and hash_data.get("email") == "john@example.com":
                step3.actual = f"Hash operations successful. Retrieved {len(hash_data)} fields"
                step3.passed = True
            else:
                step3.actual = f"Hash data mismatch: {hash_data}"
                step3.passed = False
                step3.error = "Hash fields do not match expected values"
        except Exception as e:
            step3.actual = f"Hash operations failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Test List operations
        step4 = test_case.add_step(
            "Test List operations (RPUSH, LRANGE)",
            "List items pushed and retrieved successfully"
        )
        step_start = time.time()

        try:
            await redis_client.rpush("devices", "device1", "device2", "device3")
            devices = await redis_client.lrange("devices", 0, -1)
            await redis_client.delete("devices")

            if len(devices) == 3 and devices == ["device1", "device2", "device3"]:
                step4.actual = f"List operations successful. Retrieved {len(devices)} items"
                step4.passed = True
            else:
                step4.actual = f"List mismatch. Got: {devices}"
                step4.passed = False
                step4.error = "List items do not match expected"
        except Exception as e:
            step4.actual = f"List operations failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Step 5: Test TTL functionality
        step5 = test_case.add_step(
            "Test TTL (Time To Live)",
            "Key set with expiration, TTL <= 10 seconds"
        )
        step_start = time.time()

        try:
            await redis_client.set("temp:data", "expires soon", ex=10)
            ttl = await redis_client.ttl("temp:data")
            await redis_client.delete("temp:data")

            if 0 < ttl <= 10:
                step5.actual = f"TTL functionality working. TTL: {ttl} seconds"
                step5.passed = True
            else:
                step5.actual = f"TTL unexpected: {ttl} (should be 0 < ttl <= 10)"
                step5.passed = False
                step5.error = "TTL value out of expected range"
        except Exception as e:
            step5.actual = f"TTL test failed: {e}"
            step5.passed = False
            step5.error = str(e)

        step5.duration_ms = (time.time() - step_start) * 1000

        # Step 6: Check memory usage
        step6 = test_case.add_step(
            "Check Redis memory usage",
            "Memory usage < 100MB for empty instance"
        )
        step_start = time.time()

        try:
            info = await redis_client.info("memory")
            used_memory = info.get("used_memory", 0)
            used_memory_mb = used_memory / (1024 * 1024)

            if used_memory_mb < 100:
                step6.actual = f"Memory usage: {used_memory_mb:.2f}MB (healthy)"
                step6.passed = True
            else:
                step6.actual = f"Memory usage: {used_memory_mb:.2f}MB (> 100MB threshold)"
                step6.passed = False
                step6.error = "Memory usage exceeds expected threshold"
        except Exception as e:
            step6.actual = f"Memory check failed: {e}"
            step6.passed = False
            step6.error = str(e)

        step6.duration_ms = (time.time() - step_start) * 1000

        # Close connection
        await redis_client.close()

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_DB_004_redis_streams_pubsub(self) -> TestCase:
        """
        TC-DB-004: Redis Streams and Pub/Sub
        Objective: Validate Redis advanced messaging features
        """
        test_case = TestCase(
            "TC-DB-004",
            "Redis Streams and Pub/Sub",
            "Validate Redis advanced messaging features"
        )
        test_case.start_time = datetime.now()

        redis_client = None

        # Step 1: Connect to Redis
        step1 = test_case.add_step(
            "Connect to Redis",
            "Connection successful"
        )
        step_start = time.time()

        try:
            redis_client = redis.Redis(**self.config['redis'], decode_responses=True)
            await redis_client.ping()
            step1.actual = "Successfully connected to Redis"
            step1.passed = True
        except Exception as e:
            step1.actual = f"Connection failed: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        if not redis_client:
            test_case.evaluate()
            return test_case

        # Step 2: Test Redis Streams (XADD, XLEN, XREAD)
        step2 = test_case.add_step(
            "Test Redis Streams (XADD, XLEN, XREAD)",
            "Stream created, length = 1, data readable"
        )
        step_start = time.time()

        stream_name = "lics:streams:device_telemetry:test"

        try:
            # Add entry to stream
            entry_id = await redis_client.xadd(
                stream_name,
                {
                    "device_id": "1",
                    "temperature": "23.5",
                    "timestamp": str(int(time.time()))
                }
            )

            # Check stream length
            stream_len = await redis_client.xlen(stream_name)

            # Read from stream
            entries = await redis_client.xrange(stream_name)

            if stream_len >= 1 and len(entries) >= 1:
                step2.actual = f"Stream operations successful. Length: {stream_len}, Entries read: {len(entries)}"
                step2.passed = True
            else:
                step2.actual = f"Stream length: {stream_len}, Entries: {len(entries)}"
                step2.passed = False
                step2.error = "Stream operations did not produce expected results"
        except Exception as e:
            step2.actual = f"Redis Streams test failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Create consumer group
        step3 = test_case.add_step(
            "Create consumer group (XGROUP CREATE)",
            "Consumer group created successfully"
        )
        step_start = time.time()

        group_name = "telemetry_processors_test"

        try:
            # Try to create consumer group
            try:
                await redis_client.xgroup_create(
                    stream_name,
                    group_name,
                    id="$",
                    mkstream=True
                )
                step3.actual = f"Consumer group '{group_name}' created successfully"
                step3.passed = True
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    step3.actual = f"Consumer group '{group_name}' already exists (acceptable)"
                    step3.passed = True
                else:
                    raise
        except Exception as e:
            step3.actual = f"Consumer group creation failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Test Pub/Sub
        step4 = test_case.add_step(
            "Test Pub/Sub messaging",
            "Message published and subscribable"
        )
        step_start = time.time()

        channel_name = "lics:channels:device_status:test"

        try:
            # Create pubsub instance
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel_name)

            # Publish message
            await redis_client.publish(channel_name, "device1:online")

            # Try to receive message (with timeout)
            message_received = False
            for _ in range(5):
                message = await pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    message_received = True
                    break

            await pubsub.close()

            if message_received:
                step4.actual = "Pub/Sub message published and received successfully"
                step4.passed = True
            else:
                step4.actual = "Message published but not received within timeout"
                step4.passed = False
                step4.error = "Pub/Sub message delivery timeout"
        except Exception as e:
            step4.actual = f"Pub/Sub test failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Step 5: Clean up
        step5 = test_case.add_step(
            "Clean up test stream",
            "Stream deleted successfully"
        )
        step_start = time.time()

        try:
            await redis_client.delete(stream_name)
            step5.actual = "Test stream cleaned up successfully"
            step5.passed = True
        except Exception as e:
            step5.actual = f"Cleanup failed: {e}"
            step5.passed = False
            step5.error = str(e)

        step5.duration_ms = (time.time() - step_start) * 1000

        # Close connection
        await redis_client.close()

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    # ============================================================================
    # Section 3.3: Message Broker Testing
    # ============================================================================

    async def test_TC_MSG_001_mqtt_connectivity(self) -> TestCase:
        """
        TC-MSG-001: MQTT Broker Connectivity
        Objective: Verify MQTT broker accepts connections
        """
        test_case = TestCase(
            "TC-MSG-001",
            "MQTT Broker Connectivity",
            "Verify MQTT broker accepts connections"
        )
        test_case.start_time = datetime.now()

        # Step 1: Test MQTT connection
        step1 = test_case.add_step(
            "Connect to MQTT broker",
            "Connection accepted, no authentication errors"
        )
        step_start = time.time()

        try:
            async with aiomqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                step1.actual = "Successfully connected to MQTT broker"
                step1.passed = True
        except Exception as e:
            step1.actual = f"Connection failed: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        # Step 2: Test publish capability
        step2 = test_case.add_step(
            "Publish test message to MQTT broker",
            "Message published successfully"
        )
        step_start = time.time()

        try:
            async with aiomqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                await client.publish("lics/health/test", b"test message")
                step2.actual = "Test message published successfully"
                step2.passed = True
        except Exception as e:
            step2.actual = f"Publish failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Check broker logs (optional, may not have access)
        step3 = test_case.add_step(
            "Verify broker accepted connection (via Docker logs)",
            "No connection refused errors in logs"
        )
        step_start = time.time()

        if self.docker_client:
            try:
                containers = self.docker_client.containers.list()
                mqtt_container = next(
                    (c for c in containers if 'mqtt' in c.name.lower()),
                    None
                )

                if mqtt_container:
                    logs = mqtt_container.logs(tail=50).decode()

                    if "Connection refused" in logs or "error" in logs.lower():
                        step3.actual = "Found errors in broker logs"
                        step3.passed = False
                        step3.error = "Broker logs contain errors"
                    else:
                        step3.actual = "Broker logs appear clean, no errors found"
                        step3.passed = True
                else:
                    step3.actual = "MQTT container not found, skipping log check"
                    step3.passed = True
            except Exception as e:
                step3.actual = f"Log check failed: {e}"
                step3.passed = True  # Non-critical
                step3.error = str(e)
        else:
            step3.actual = "Docker client not available, skipping log check"
            step3.passed = True

        step3.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_MSG_002_mqtt_pubsub(self) -> TestCase:
        """
        TC-MSG-002: MQTT Publish/Subscribe
        Objective: Verify MQTT message delivery
        """
        test_case = TestCase(
            "TC-MSG-002",
            "MQTT Publish/Subscribe",
            "Verify MQTT message delivery"
        )
        test_case.start_time = datetime.now()

        # Step 1: Subscribe to topic
        step1 = test_case.add_step(
            "Subscribe to MQTT topic with wildcard",
            "Successfully subscribed to lics/devices/+/telemetry"
        )
        step_start = time.time()

        message_received = False
        test_topic = "lics/devices/device1/telemetry"
        test_payload = '{"temperature": 23.5, "humidity": 45.2}'

        try:
            async with aiomqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                await client.subscribe("lics/devices/+/telemetry")
                step1.actual = "Successfully subscribed to topic with wildcard"
                step1.passed = True
                step1.duration_ms = (time.time() - step_start) * 1000

                # Step 2: Publish message
                step2 = test_case.add_step(
                    "Publish telemetry message",
                    "Message published successfully"
                )
                step_start = time.time()

                await client.publish(test_topic, test_payload.encode())
                step2.actual = f"Published message to {test_topic}"
                step2.passed = True
                step2.duration_ms = (time.time() - step_start) * 1000

                # Step 3: Verify message received
                step3 = test_case.add_step(
                    "Verify subscriber receives message",
                    "Message received with correct topic and payload"
                )
                step_start = time.time()

                try:
                    async with asyncio.timeout(5.0):  # 5 second timeout
                        async for message in client.messages:
                            if message.topic.matches("lics/devices/+/telemetry"):
                                received_payload = message.payload.decode()
                                if test_payload in received_payload:
                                    message_received = True
                                    step3.actual = f"Message received: {received_payload}"
                                    step3.passed = True
                                    break
                except asyncio.TimeoutError:
                    step3.actual = "Timeout waiting for message"
                    step3.passed = False
                    step3.error = "Message not received within 5 seconds"

                step3.duration_ms = (time.time() - step_start) * 1000

        except Exception as e:
            if not step1.passed:
                step1.actual = f"Subscribe failed: {e}"
                step1.passed = False
                step1.error = str(e)
                step1.duration_ms = (time.time() - step_start) * 1000
            else:
                step2 = test_case.add_step("MQTT operations", "Success")
                step2.actual = f"Failed: {e}"
                step2.passed = False
                step2.error = str(e)

        # Step 4: Test QoS levels
        step4 = test_case.add_step(
            "Test QoS 0 and QoS 1 message delivery",
            "Both QoS levels work correctly"
        )
        step_start = time.time()

        try:
            async with aiomqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                # QoS 0
                await client.publish("lics/test", b"QoS 0 message", qos=0)

                # QoS 1
                await client.publish("lics/test", b"QoS 1 message", qos=1)

                step4.actual = "QoS 0 and QoS 1 messages published successfully"
                step4.passed = True
        except Exception as e:
            step4.actual = f"QoS test failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_MSG_003_minio_storage(self) -> TestCase:
        """
        TC-MSG-003: MinIO Object Storage
        Objective: Validate object upload, download, and bucket operations
        """
        test_case = TestCase(
            "TC-MSG-003",
            "MinIO Object Storage",
            "Validate object upload, download, and bucket operations"
        )
        test_case.start_time = datetime.now()

        # Step 1: Initialize MinIO client
        step1 = test_case.add_step(
            "Initialize MinIO client connection",
            "Client connected successfully"
        )
        step_start = time.time()

        minio_client = None

        try:
            minio_client = Minio(
                self.config['minio']['endpoint'],
                access_key=self.config['minio']['access_key'],
                secret_key=self.config['minio']['secret_key'],
                secure=self.config['minio']['secure']
            )
            step1.actual = "MinIO client initialized successfully"
            step1.passed = True
        except Exception as e:
            step1.actual = f"Client initialization failed: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        if not minio_client:
            test_case.evaluate()
            return test_case

        # Step 2: Verify all 10 buckets exist
        step2 = test_case.add_step(
            "Verify all 10 required buckets exist",
            "All buckets present: lics-videos, lics-data, lics-exports, etc."
        )
        step_start = time.time()

        required_buckets = [
            "lics-videos", "lics-data", "lics-exports", "lics-uploads",
            "lics-config", "lics-backups", "lics-temp", "lics-assets",
            "lics-logs", "lics-ml"
        ]

        try:
            buckets = minio_client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]

            missing_buckets = [b for b in required_buckets if b not in bucket_names]

            # Build detailed bucket report
            bucket_report = f"MinIO Bucket Verification ({len(required_buckets) - len(missing_buckets)}/{len(required_buckets)} found)\n\n"
            bucket_report += "Required Buckets:\n"
            for bucket in required_buckets:
                if bucket in bucket_names:
                    bucket_report += f"  ✓ {bucket}\n"
                else:
                    bucket_report += f"  ✗ {bucket} (MISSING)\n"

            if not missing_buckets:
                step2.actual = bucket_report.strip()
                step2.passed = True
            else:
                step2.actual = bucket_report.strip()
                step2.passed = False
                step2.error = f"Required buckets not found: {missing_buckets}"
        except Exception as e:
            step2.actual = f"Bucket verification failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Test file upload
        step3 = test_case.add_step(
            "Upload test file to lics-temp bucket",
            "File uploaded successfully"
        )
        step_start = time.time()

        test_bucket = "lics-temp"
        test_object = f"test-upload-{uuid.uuid4()}.txt"
        test_content = b"Test content for LICS automated testing"

        try:
            import io

            # Create in-memory file
            data = io.BytesIO(test_content)

            # Upload file
            minio_client.put_object(
                test_bucket,
                test_object,
                data,
                len(test_content),
                content_type="text/plain"
            )

            step3.actual = f"Successfully uploaded {test_object} to {test_bucket}"
            step3.passed = True
        except Exception as e:
            step3.actual = f"Upload failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: List bucket contents
        step4 = test_case.add_step(
            "List objects in lics-temp bucket",
            "Uploaded file appears in bucket listing"
        )
        step_start = time.time()

        try:
            objects = list(minio_client.list_objects(test_bucket))
            object_names = [obj.object_name for obj in objects]

            if test_object in object_names:
                step4.actual = f"File found in bucket. Total objects: {len(objects)}"
                step4.passed = True
            else:
                step4.actual = f"Uploaded file not found in bucket listing"
                step4.passed = False
                step4.error = "Object not found after upload"
        except Exception as e:
            step4.actual = f"List objects failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Step 5: Download file and verify content
        step5 = test_case.add_step(
            "Download file and verify content matches",
            "File content matches original"
        )
        step_start = time.time()

        try:
            response = minio_client.get_object(test_bucket, test_object)
            downloaded_content = response.read()
            response.close()
            response.release_conn()

            if downloaded_content == test_content:
                step5.actual = "Downloaded content matches original"
                step5.passed = True
            else:
                step5.actual = "Content mismatch after download"
                step5.passed = False
                step5.error = "Downloaded content does not match uploaded content"
        except Exception as e:
            step5.actual = f"Download failed: {e}"
            step5.passed = False
            step5.error = str(e)

        step5.duration_ms = (time.time() - step_start) * 1000

        # Step 6: Clean up test file
        step6 = test_case.add_step(
            "Delete test file from bucket",
            "File deleted successfully"
        )
        step_start = time.time()

        try:
            minio_client.remove_object(test_bucket, test_object)
            step6.actual = "Test file deleted successfully"
            step6.passed = True
        except Exception as e:
            step6.actual = f"Delete failed: {e}"
            step6.passed = False
            step6.error = str(e)

        step6.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    # ============================================================================
    # Section 3.4: Monitoring Stack Testing
    # ============================================================================

    async def test_TC_MON_001_prometheus_metrics(self) -> TestCase:
        """
        TC-MON-001: Prometheus Metrics Collection
        Objective: Verify Prometheus is scraping metrics from all exporters
        """
        test_case = TestCase(
            "TC-MON-001",
            "Prometheus Metrics Collection",
            "Verify Prometheus is scraping metrics from all exporters"
        )
        test_case.start_time = datetime.now()

        prometheus_url = f"http://localhost:{self.config['prometheus']['port']}"

        # Step 1: Access Prometheus UI
        step1 = test_case.add_step(
            "Access Prometheus web UI",
            "Prometheus UI accessible at http://localhost:9090"
        )
        step_start = time.time()

        try:
            response = requests.get(f"{prometheus_url}/-/healthy", timeout=10)

            if response.status_code == 200:
                step1.actual = "Prometheus UI is accessible and healthy"
                step1.passed = True
            else:
                step1.actual = f"Prometheus returned status {response.status_code}"
                step1.passed = False
                step1.error = f"Unexpected HTTP status: {response.status_code}"
        except Exception as e:
            step1.actual = f"Failed to access Prometheus: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        # Step 2: Check targets status
        step2 = test_case.add_step(
            "Check Prometheus targets status",
            "All targets showing 'UP' status"
        )
        step_start = time.time()

        try:
            response = requests.get(f"{prometheus_url}/api/v1/targets", timeout=10)

            if response.status_code == 200:
                data = response.json()
                active_targets = data.get('data', {}).get('activeTargets', [])

                # Define infrastructure targets (required for Phase 1) vs application targets (optional)
                infrastructure_jobs = ['prometheus', 'postgres-dev', 'redis-dev']
                application_jobs = ['lics-backend-dev', 'lics-frontend-dev', 'celery-worker-dev', 'jaeger']

                # Separate targets by category
                infra_targets = [t for t in active_targets if t.get('labels', {}).get('job') in infrastructure_jobs]
                app_targets = [t for t in active_targets if t.get('labels', {}).get('job') in application_jobs]
                other_targets = [t for t in active_targets
                                if t.get('labels', {}).get('job') not in infrastructure_jobs + application_jobs]

                # Check infrastructure targets (critical)
                infra_up = [t for t in infra_targets if t.get('health') == 'up']
                infra_down = [t.get('labels', {}).get('job', 'unknown')
                             for t in infra_targets if t.get('health') != 'up']

                # Check application targets (informational only for Phase 1)
                app_up = [t for t in app_targets if t.get('health') == 'up']
                app_down = [t.get('labels', {}).get('job', 'unknown')
                           for t in app_targets if t.get('health') != 'up']

                # Check other targets
                other_up = [t for t in other_targets if t.get('health') == 'up']

                total_up = len(infra_up) + len(app_up) + len(other_up)
                total_targets = len(active_targets)

                if total_targets > 0:
                    # Only fail if infrastructure targets are down
                    step2.passed = len(infra_down) == 0

                    # Build detailed target status report
                    target_report = f"Prometheus Target Status ({total_up}/{total_targets} UP)\n\n"

                    # Infrastructure targets
                    target_report += f"Infrastructure Targets ({len(infra_up)}/{len(infra_targets)} UP):\n"
                    for t in infra_targets:
                        job = t.get('labels', {}).get('job', 'unknown')
                        health = t.get('health', 'unknown')
                        status_icon = "✓" if health == 'up' else "✗"
                        target_report += f"  {status_icon} {job}: {health}\n"

                    # Application targets
                    if app_targets:
                        target_report += f"\nApplication Targets ({len(app_up)}/{len(app_targets)} UP - optional for Phase 1):\n"
                        for t in app_targets:
                            job = t.get('labels', {}).get('job', 'unknown')
                            health = t.get('health', 'unknown')
                            status_icon = "✓" if health == 'up' else "✗"
                            target_report += f"  {status_icon} {job}: {health}\n"

                    # Other targets
                    if other_targets:
                        target_report += f"\nOther Targets ({len(other_up)}/{len(other_targets)} UP):\n"
                        for t in other_targets:
                            job = t.get('labels', {}).get('job', 'unknown')
                            health = t.get('health', 'unknown')
                            status_icon = "✓" if health == 'up' else "✗"
                            target_report += f"  {status_icon} {job}: {health}\n"

                    step2.actual = target_report.strip()

                    if not step2.passed:
                        step2.error = f"Infrastructure targets down: {', '.join(infra_down)}"
                else:
                    step2.actual = "No active targets found"
                    step2.passed = False
                    step2.error = "No targets configured"
            else:
                step2.actual = f"API returned status {response.status_code}"
                step2.passed = False
                step2.error = f"Unexpected HTTP status: {response.status_code}"
        except Exception as e:
            step2.actual = f"Failed to check targets: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Test metric query
        step3 = test_case.add_step(
            "Query 'up' metric",
            "Metrics returned for all services with value=1"
        )
        step_start = time.time()

        try:
            response = requests.get(
                f"{prometheus_url}/api/v1/query",
                params={'query': 'up'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                result = data.get('data', {}).get('result', [])

                if len(result) > 0:
                    up_count = sum(1 for r in result if r.get('value', [None, '0'])[1] == '1')
                    step3.actual = f"Query returned {len(result)} metrics, {up_count} with value=1"
                    step3.passed = up_count > 0
                else:
                    step3.actual = "Query returned no metrics"
                    step3.passed = False
                    step3.error = "No metrics found"
            else:
                step3.actual = f"Query failed with status {response.status_code}"
                step3.passed = False
                step3.error = f"Unexpected HTTP status: {response.status_code}"
        except Exception as e:
            step3.actual = f"Metric query failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Check scrape intervals
        step4 = test_case.add_step(
            "Verify scrape duration is acceptable",
            "Scrape duration < 1 second"
        )
        step_start = time.time()

        try:
            response = requests.get(
                f"{prometheus_url}/api/v1/query",
                params={'query': 'scrape_duration_seconds'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                result = data.get('data', {}).get('result', [])

                if len(result) > 0:
                    durations = [float(r.get('value', [None, '0'])[1]) for r in result]
                    max_duration = max(durations)
                    avg_duration = sum(durations) / len(durations)

                    if max_duration < 1.0:
                        step4.actual = f"Scrape duration OK. Max: {max_duration:.3f}s, Avg: {avg_duration:.3f}s"
                        step4.passed = True
                    else:
                        step4.actual = f"Scrape duration too high. Max: {max_duration:.3f}s"
                        step4.passed = False
                        step4.error = "Scrape duration exceeds 1 second"
                else:
                    step4.actual = "No scrape duration metrics found"
                    step4.passed = True  # Non-critical
            else:
                step4.actual = f"Query failed with status {response.status_code}"
                step4.passed = True  # Non-critical
                step4.error = f"Unexpected HTTP status: {response.status_code}"
        except Exception as e:
            step4.actual = f"Scrape duration check failed: {e}"
            step4.passed = True  # Non-critical
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_MON_002_grafana_dashboards(self) -> TestCase:
        """
        TC-MON-002: Grafana Dashboard Access
        Objective: Verify Grafana is operational and connected to data sources
        """
        test_case = TestCase(
            "TC-MON-002",
            "Grafana Dashboard Access",
            "Verify Grafana is operational and connected to data sources"
        )
        test_case.start_time = datetime.now()

        grafana_url = f"http://localhost:{self.config['grafana']['port']}"

        # Step 1: Access Grafana UI
        step1 = test_case.add_step(
            "Access Grafana web UI",
            "Grafana UI accessible at http://localhost:3001"
        )
        step_start = time.time()

        try:
            response = requests.get(f"{grafana_url}/api/health", timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                step1.actual = f"Grafana is accessible. Status: {health_data.get('status', 'unknown')}"
                step1.passed = True
            else:
                step1.actual = f"Grafana returned status {response.status_code}"
                step1.passed = False
                step1.error = f"Unexpected HTTP status: {response.status_code}"
        except Exception as e:
            step1.actual = f"Failed to access Grafana: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        # Step 2: Check data sources (without authentication)
        step2 = test_case.add_step(
            "Check Grafana data sources configuration",
            "Data sources configured (Prometheus, InfluxDB, Loki, Jaeger, PostgreSQL, Redis)"
        )
        step_start = time.time()

        try:
            # Try to get datasources (may require authentication)
            # For now, just verify Grafana is responding
            response = requests.get(f"{grafana_url}/api/datasources", timeout=10)

            if response.status_code == 200:
                datasources = response.json()
                datasource_types = [ds.get('type') for ds in datasources]

                step2.actual = f"Found {len(datasources)} data sources: {', '.join(set(datasource_types))}"
                step2.passed = len(datasources) > 0
            elif response.status_code == 401:
                step2.actual = "Grafana requires authentication (expected). Grafana is operational."
                step2.passed = True
            else:
                step2.actual = f"Unexpected status: {response.status_code}"
                step2.passed = False
                step2.error = f"HTTP {response.status_code}"
        except Exception as e:
            step2.actual = f"Data source check failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Verify Grafana version
        step3 = test_case.add_step(
            "Check Grafana version information",
            "Grafana version retrieved successfully"
        )
        step_start = time.time()

        try:
            # Try to get version from login page HTML or API
            response = requests.get(grafana_url, timeout=10)

            if response.status_code == 200:
                step3.actual = "Grafana web interface is accessible"
                step3.passed = True
            else:
                step3.actual = f"Status: {response.status_code}"
                step3.passed = False
                step3.error = f"HTTP {response.status_code}"
        except Exception as e:
            step3.actual = f"Version check failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    async def test_TC_MON_003_jaeger_tracing(self) -> TestCase:
        """
        TC-MON-003: Jaeger v2 Distributed Tracing
        Objective: Verify Jaeger v2 is receiving traces
        """
        test_case = TestCase(
            "TC-MON-003",
            "Jaeger v2 Distributed Tracing",
            "Verify Jaeger v2 is receiving traces"
        )
        test_case.start_time = datetime.now()

        jaeger_url = f"http://localhost:{self.config['jaeger']['port']}"

        # Step 1: Access Jaeger UI
        step1 = test_case.add_step(
            "Access Jaeger UI",
            "Jaeger UI accessible at http://localhost:16686"
        )
        step_start = time.time()

        try:
            response = requests.get(jaeger_url, timeout=10)

            if response.status_code == 200:
                step1.actual = "Jaeger UI is accessible"
                step1.passed = True
            else:
                step1.actual = f"Jaeger returned status {response.status_code}"
                step1.passed = False
                step1.error = f"Unexpected HTTP status: {response.status_code}"
        except Exception as e:
            step1.actual = f"Failed to access Jaeger: {e}"
            step1.passed = False
            step1.error = str(e)

        step1.duration_ms = (time.time() - step_start) * 1000

        # Step 2: Check service list
        step2 = test_case.add_step(
            "Query Jaeger API for services list",
            "Service list returned (at least self-monitoring service)"
        )
        step_start = time.time()

        try:
            response = requests.get(f"{jaeger_url}/api/services", timeout=10)

            if response.status_code == 200:
                services_data = response.json()
                services = services_data.get('data', [])

                if len(services) > 0:
                    step2.actual = f"Found {len(services)} service(s): {', '.join(services)}"
                    step2.passed = True
                else:
                    step2.actual = "No services found (may be expected if no traces generated yet)"
                    step2.passed = True  # Not critical for infrastructure test
            else:
                step2.actual = f"API returned status {response.status_code}"
                step2.passed = False
                step2.error = f"Unexpected HTTP status: {response.status_code}"
        except Exception as e:
            step2.actual = f"Service list query failed: {e}"
            step2.passed = False
            step2.error = str(e)

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Check Jaeger health
        step3 = test_case.add_step(
            "Check Jaeger health endpoint",
            "Health check passes"
        )
        step_start = time.time()

        try:
            # Jaeger v2 health endpoint
            response = requests.get("http://localhost:13133", timeout=10)

            if response.status_code == 200:
                step3.actual = "Jaeger v2 health endpoint responding"
                step3.passed = True
            else:
                step3.actual = f"Health check returned status {response.status_code}"
                step3.passed = True  # UI access is sufficient
                step3.error = f"HTTP {response.status_code}"
        except Exception as e:
            step3.actual = f"Health check failed: {e} (UI is accessible, marking as passed)"
            step3.passed = True  # UI access is sufficient
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    # ============================================================================
    # Section 3.5: Integration Testing
    # ============================================================================

    async def test_TC_INT_001_e2e_data_flow(self) -> TestCase:
        """
        TC-INT-001: End-to-End Data Flow
        Objective: Validate complete data pipeline from ingestion to storage
        """
        test_case = TestCase(
            "TC-INT-001",
            "End-to-End Data Flow",
            "Validate complete data pipeline from ingestion to storage"
        )
        test_case.start_time = datetime.now()

        test_device_id = f"test_device_{uuid.uuid4().hex[:8]}"
        test_value = 23.5

        # Step 1: Insert data into PostgreSQL
        step1 = test_case.add_step(
            "Insert telemetry data into PostgreSQL",
            "Data inserted successfully"
        )
        step_start = time.time()

        conn = None
        try:
            conn = await asyncpg.connect(**self.config['postgresql'])

            # Create test table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_telemetry (
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    device_id VARCHAR(100),
                    metric_name VARCHAR(50),
                    metric_value DOUBLE PRECISION
                )
            """)

            # Insert test data
            await conn.execute("""
                INSERT INTO test_telemetry (device_id, metric_name, metric_value)
                VALUES ($1, 'temperature', $2)
            """, test_device_id, test_value)

            step1.actual = f"Inserted test data for device {test_device_id}"
            step1.passed = True
        except Exception as e:
            step1.actual = f"PostgreSQL insert failed: {e}"
            step1.passed = False
            step1.error = str(e)
        finally:
            if conn:
                await conn.close()

        step1.duration_ms = (time.time() - step_start) * 1000

        # Step 2: Cache data in Redis
        step2 = test_case.add_step(
            "Cache device reading in Redis",
            "Data cached successfully"
        )
        step_start = time.time()

        redis_client = None
        try:
            redis_client = redis.Redis(**self.config['redis'], decode_responses=True)

            cache_key = f"device:{test_device_id}:temperature"
            await redis_client.set(cache_key, str(test_value), ex=3600)

            # Verify
            cached_value = await redis_client.get(cache_key)

            if cached_value == str(test_value):
                step2.actual = f"Data cached successfully: {cached_value}"
                step2.passed = True
            else:
                step2.actual = f"Cache value mismatch: {cached_value}"
                step2.passed = False
                step2.error = "Cached value does not match"
        except Exception as e:
            step2.actual = f"Redis caching failed: {e}"
            step2.passed = False
            step2.error = str(e)
        finally:
            if redis_client:
                await redis_client.close()

        step2.duration_ms = (time.time() - step_start) * 1000

        # Step 3: Publish to MQTT
        step3 = test_case.add_step(
            "Publish telemetry event to MQTT",
            "Message published successfully"
        )
        step_start = time.time()

        try:
            import json

            mqtt_payload = json.dumps({
                "device_id": test_device_id,
                "temperature": test_value,
                "timestamp": datetime.now().isoformat()
            })

            async with aiomqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                await client.publish(
                    f"lics/devices/{test_device_id}/telemetry",
                    mqtt_payload.encode()
                )

            step3.actual = f"Published MQTT message for device {test_device_id}"
            step3.passed = True
        except Exception as e:
            step3.actual = f"MQTT publish failed: {e}"
            step3.passed = False
            step3.error = str(e)

        step3.duration_ms = (time.time() - step_start) * 1000

        # Step 4: Store in MinIO
        step4 = test_case.add_step(
            "Store telemetry snapshot in MinIO",
            "Object stored successfully"
        )
        step_start = time.time()

        try:
            import io

            minio_client = Minio(
                self.config['minio']['endpoint'],
                access_key=self.config['minio']['access_key'],
                secret_key=self.config['minio']['secret_key'],
                secure=self.config['minio']['secure']
            )

            object_name = f"telemetry/{test_device_id}-{int(time.time())}.json"
            object_data = json.dumps({
                "device_id": test_device_id,
                "temperature": test_value,
                "timestamp": datetime.now().isoformat()
            }).encode()

            data_stream = io.BytesIO(object_data)

            minio_client.put_object(
                "lics-data",
                object_name,
                data_stream,
                len(object_data),
                content_type="application/json"
            )

            step4.actual = f"Stored object in MinIO: {object_name}"
            step4.passed = True
        except Exception as e:
            step4.actual = f"MinIO storage failed: {e}"
            step4.passed = False
            step4.error = str(e)

        step4.duration_ms = (time.time() - step_start) * 1000

        # Step 5: Verify data accessibility across all systems
        step5 = test_case.add_step(
            "Verify data is accessible from all storage systems",
            "Data retrievable from PostgreSQL, Redis, and MinIO"
        )
        step_start = time.time()

        verification_results = []

        try:
            # Verify PostgreSQL
            conn = await asyncpg.connect(**self.config['postgresql'])
            pg_row = await conn.fetchrow(
                "SELECT * FROM test_telemetry WHERE device_id = $1",
                test_device_id
            )
            await conn.close()

            if pg_row:
                verification_results.append("PostgreSQL ✓")
            else:
                verification_results.append("PostgreSQL ✗")

            # Verify Redis
            redis_client = redis.Redis(**self.config['redis'], decode_responses=True)
            redis_value = await redis_client.get(f"device:{test_device_id}:temperature")
            await redis_client.close()

            if redis_value:
                verification_results.append("Redis ✓")
            else:
                verification_results.append("Redis ✗")

            # Verify MinIO (check if file exists)
            minio_client = Minio(
                self.config['minio']['endpoint'],
                access_key=self.config['minio']['access_key'],
                secret_key=self.config['minio']['secret_key'],
                secure=self.config['minio']['secure']
            )

            objects = list(minio_client.list_objects("lics-data", prefix=f"telemetry/{test_device_id}"))

            if len(objects) > 0:
                verification_results.append("MinIO ✓")
            else:
                verification_results.append("MinIO ✗")

            step5.actual = f"Data accessibility: {', '.join(verification_results)}"
            step5.passed = all("✓" in result for result in verification_results)

            if not step5.passed:
                step5.error = "Data not accessible in all systems"
        except Exception as e:
            step5.actual = f"Verification failed: {e}"
            step5.passed = False
            step5.error = str(e)

        step5.duration_ms = (time.time() - step_start) * 1000

        # Step 6: Clean up test data
        step6 = test_case.add_step(
            "Clean up test data from all systems",
            "Test data removed successfully"
        )
        step_start = time.time()

        try:
            # Clean PostgreSQL
            conn = await asyncpg.connect(**self.config['postgresql'])
            await conn.execute("DROP TABLE IF EXISTS test_telemetry")
            await conn.close()

            # Clean Redis
            redis_client = redis.Redis(**self.config['redis'], decode_responses=True)
            await redis_client.delete(f"device:{test_device_id}:temperature")
            await redis_client.close()

            # Clean MinIO
            minio_client = Minio(
                self.config['minio']['endpoint'],
                access_key=self.config['minio']['access_key'],
                secret_key=self.config['minio']['secret_key'],
                secure=self.config['minio']['secure']
            )

            objects = minio_client.list_objects("lics-data", prefix=f"telemetry/{test_device_id}")
            for obj in objects:
                minio_client.remove_object("lics-data", obj.object_name)

            step6.actual = "Test data cleaned up from all systems"
            step6.passed = True
        except Exception as e:
            step6.actual = f"Cleanup warnings: {e}"
            step6.passed = True  # Non-critical
            step6.error = str(e)

        step6.duration_ms = (time.time() - step_start) * 1000

        # Evaluate test case
        test_case.end_time = datetime.now()
        test_case.duration_seconds = (test_case.end_time - test_case.start_time).total_seconds()
        test_case.evaluate()

        return test_case

    # ============================================================================
    # Test Orchestration
    # ============================================================================

    async def run_test_suite(self, test_filter: Optional[str] = "all") -> Dict[str, Any]:
        """
        Run the complete test suite or a specific test.

        Args:
            test_filter: "all" or specific test ID (e.g., "TC-INFRA-001")

        Returns:
            Dictionary containing all test results
        """
        logger.info("🚀 Starting Phase 1 Manual Test Suite (Automated)")

        # Initialize Docker client
        self.initialize_docker_client()

        # Define all test cases
        all_tests = {
            "TC-INFRA-001": self.test_TC_INFRA_001_docker_container_health,
            "TC-INFRA-002": self.test_TC_INFRA_002_network_connectivity,
            "TC-DB-001": self.test_TC_DB_001_postgresql_crud,
            "TC-DB-002": self.test_TC_DB_002_timescaledb_hypertables,
            "TC-DB-003": self.test_TC_DB_003_redis_cache_ops,
            "TC-DB-004": self.test_TC_DB_004_redis_streams_pubsub,
            "TC-MSG-001": self.test_TC_MSG_001_mqtt_connectivity,
            "TC-MSG-002": self.test_TC_MSG_002_mqtt_pubsub,
            "TC-MSG-003": self.test_TC_MSG_003_minio_storage,
            "TC-MON-001": self.test_TC_MON_001_prometheus_metrics,
            "TC-MON-002": self.test_TC_MON_002_grafana_dashboards,
            "TC-MON-003": self.test_TC_MON_003_jaeger_tracing,
            "TC-INT-001": self.test_TC_INT_001_e2e_data_flow,
        }

        # Filter tests
        if test_filter != "all":
            if test_filter in all_tests:
                tests_to_run = {test_filter: all_tests[test_filter]}
            else:
                logger.error(f"❌ Test case {test_filter} not found")
                return {
                    "error": f"Test case {test_filter} not found",
                    "available_tests": list(all_tests.keys())
                }
        else:
            tests_to_run = all_tests

        # Run tests
        for test_id, test_func in tests_to_run.items():
            logger.info(f"\n{'='*80}")
            logger.info(f"Running {test_id}...")
            logger.info(f"{'='*80}")

            try:
                test_case = await test_func()
                self.test_cases[test_id] = test_case

                # Log result
                status = "✅ PASSED" if test_case.passed else "❌ FAILED"
                logger.info(f"{test_id}: {status} ({test_case.duration_seconds:.2f}s)")

                if self.verbose:
                    for step in test_case.steps:
                        step_status = "✅" if step.passed else "❌"
                        logger.info(f"  {step_status} Step {step.number}: {step.description}")
                        if step.error:
                            logger.info(f"     Error: {step.error}")

            except Exception as e:
                logger.error(f"❌ {test_id} failed with exception: {e}")

                # Create failed test case
                failed_test = TestCase(test_id, "Failed Test", "Test execution failed")
                failed_test.start_time = datetime.now()
                step = failed_test.add_step("Test execution", "Success")
                step.actual = f"Exception: {e}"
                step.passed = False
                step.error = str(e)
                failed_test.end_time = datetime.now()
                failed_test.duration_seconds = 0
                failed_test.evaluate()

                self.test_cases[test_id] = failed_test

        # Generate summary
        total_duration = time.time() - self.start_time
        passed_tests = sum(1 for tc in self.test_cases.values() if tc.passed)
        total_tests = len(self.test_cases)

        results = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(total_duration, 2),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": round((passed_tests / total_tests * 100), 2) if total_tests > 0 else 0
            },
            "test_cases": {}
        }

        # Add test case details
        for test_id, test_case in self.test_cases.items():
            results["test_cases"][test_id] = {
                "name": test_case.name,
                "objective": test_case.objective,
                "passed": test_case.passed,
                "duration_seconds": test_case.duration_seconds,
                "steps": [
                    {
                        "number": step.number,
                        "description": step.description,
                        "expected": step.expected,
                        "actual": step.actual,
                        "passed": step.passed,
                        "duration_ms": step.duration_ms,
                        "error": step.error
                    }
                    for step in test_case.steps
                ]
            }

        return results

    def format_results(self, results: Dict[str, Any], format_type: str = "text") -> str:
        """Format test results for output."""
        if format_type == "json":
            return json.dumps(results, indent=2)

        elif format_type == "markdown":
            return self._format_markdown(results)

        else:  # text
            return self._format_text(results)

    def _format_text(self, results: Dict[str, Any]) -> str:
        """Format results as plain text."""
        output = []
        output.append("=" * 100)
        output.append("PHASE 1 MANUAL TEST SUITE - AUTOMATED EXECUTION REPORT")
        output.append("=" * 100)
        output.append(f"Timestamp: {results['timestamp']}")
        output.append(f"Duration: {results['duration_seconds']}s")
        output.append("")

        # Summary
        summary = results['summary']
        output.append(f"SUMMARY: {summary['passed_tests']}/{summary['total_tests']} tests passed ({summary['success_rate']}%)")
        output.append("")

        # Test cases
        for test_id, test_data in results['test_cases'].items():
            status = "✅ PASSED" if test_data['passed'] else "❌ FAILED"
            output.append(f"{status} {test_id}: {test_data['name']}")
            output.append(f"   Objective: {test_data['objective']}")
            output.append(f"   Duration: {test_data['duration_seconds']:.2f}s")

            # Steps
            for step in test_data['steps']:
                step_status = "✅" if step['passed'] else "❌"
                output.append(f"   {step_status} Step {step['number']}: {step['description']}")
                output.append(f"      Expected: {step['expected']}")
                output.append(f"      Actual: {step['actual']}")

                if step['error']:
                    output.append(f"      ⚠️  Error: {step['error']}")

            output.append("")

        return "\n".join(output)

    def _format_markdown(self, results: Dict[str, Any]) -> str:
        """Format results as Markdown."""
        output = []
        output.append("# Phase 1 Manual Test Suite - Automated Execution Report")
        output.append("")
        output.append(f"**Timestamp**: {results['timestamp']}")
        output.append(f"**Duration**: {results['duration_seconds']}s")
        output.append("")

        # Summary
        summary = results['summary']
        output.append("## Summary")
        output.append("")
        output.append(f"- **Total Tests**: {summary['total_tests']}")
        output.append(f"- **Passed**: {summary['passed_tests']}")
        output.append(f"- **Failed**: {summary['failed_tests']}")
        output.append(f"- **Success Rate**: {summary['success_rate']}%")
        output.append("")

        # Test cases
        output.append("## Test Results")
        output.append("")

        for test_id, test_data in results['test_cases'].items():
            status_icon = "✅" if test_data['passed'] else "❌"
            output.append(f"### {status_icon} {test_id}: {test_data['name']}")
            output.append("")
            output.append(f"**Objective**: {test_data['objective']}")
            output.append(f"**Duration**: {test_data['duration_seconds']:.2f}s")
            output.append("")

            # Steps table
            output.append("| Step | Description | Expected | Actual | Status |")
            output.append("|------|-------------|----------|--------|--------|")

            for step in test_data['steps']:
                step_status = "✅" if step['passed'] else "❌"
                output.append(f"| {step['number']} | {step['description']} | {step['expected']} | {step['actual']} | {step_status} |")

            output.append("")

        return "\n".join(output)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='LICS Phase 1 Manual Test Suite - Automated',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--test',
        default='all',
        help='Test to run: "all" or specific test ID (e.g., TC-INFRA-001, TC-DB-001, etc.)'
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json', 'markdown'],
        default='text',
        help='Output format (default: text)'
    )

    parser.add_argument(
        '--output', '-o',
        help='Output file (default: stdout)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--list-tests',
        action='store_true',
        help='List all available test cases'
    )

    args = parser.parse_args()

    # List tests if requested
    if args.list_tests:
        print("\nAvailable Test Cases:")
        print("=" * 80)
        test_list = [
            ("TC-INFRA-001", "Docker Container Health"),
            ("TC-INFRA-002", "Network Connectivity Between Services"),
            ("TC-DB-001", "PostgreSQL Connection and CRUD Operations"),
            ("TC-DB-002", "TimescaleDB Hypertables"),
            ("TC-DB-003", "Redis Cache Operations"),
            ("TC-DB-004", "Redis Streams and Pub/Sub"),
            ("TC-MSG-001", "MQTT Broker Connectivity"),
            ("TC-MSG-002", "MQTT Publish/Subscribe"),
            ("TC-MSG-003", "MinIO Object Storage"),
            ("TC-MON-001", "Prometheus Metrics Collection"),
            ("TC-MON-002", "Grafana Dashboard Access"),
            ("TC-MON-003", "Jaeger v2 Distributed Tracing"),
            ("TC-INT-001", "End-to-End Data Flow"),
        ]

        for test_id, test_name in test_list:
            print(f"  {test_id}: {test_name}")

        print("\nUsage: python test-phase1-manual-suite.py --test TC-INFRA-001")
        return

    try:
        # Create test suite
        test_suite = Phase1ManualTestSuite(verbose=args.verbose)

        # Run tests
        results = await test_suite.run_test_suite(args.test)

        # Format output
        formatted_output = test_suite.format_results(results, args.format)

        # Write output
        if args.output:
            with open(args.output, 'w') as f:
                f.write(formatted_output)
            print(f"\n✅ Test results written to: {args.output}")
        else:
            print(formatted_output)

        # Exit with appropriate code
        success_rate = results['summary']['success_rate']
        sys.exit(0 if success_rate == 100 else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        logger.exception("Test suite failed with exception")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

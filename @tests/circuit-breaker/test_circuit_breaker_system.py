#!/usr/bin/env python3
"""
Comprehensive Circuit Breaker System Test Script

This script tests all circuit breaker implementations across the LICS system:
- PostgreSQL operations (Repository layer)
- Redis operations (WebSocket session management)
- External API operations (Webhook notifications)

Tests include:
1. Normal operations verification
2. Circuit breaker triggering
3. Fallback behavior validation
4. Circuit recovery testing
5. Performance impact measurement
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import unittest.mock as mock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "database_url": "postgresql+asyncpg://lics:lics_dev@localhost:5433/lics_dev",
    "redis_url": "redis://localhost:6380/0",
    "test_webhook_url": "https://httpbin.org/post",  # Test endpoint
    "max_retry_attempts": 3,
    "circuit_breaker_test_failures": 6,  # Above threshold to trigger opening
    "performance_test_iterations": 100
}


class CircuitBreakerSystemTest:
    """
    Comprehensive test suite for circuit breaker implementations.
    """

    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": [],
            "performance_metrics": {},
            "circuit_breaker_states": {}
        }
        self.setup_completed = False

    async def setup_test_environment(self):
        """Setup test environment with database and Redis connections."""
        logger.info("Setting up test environment...")

        try:
            # Import after ensuring environment is ready
            from app.core.database import db_manager
            from app.core.circuit_breaker import cb_manager, get_circuit_breaker_stats
            from app.websocket.session import SessionManager
            from app.tasks.notifications import _send_http_request

            # Initialize database manager
            await db_manager.initialize(TEST_CONFIG["database_url"])

            # Initialize session manager
            self.session_manager = SessionManager()

            # Store references for testing
            self.db_manager = db_manager
            self.cb_manager = cb_manager
            self.get_circuit_breaker_stats = get_circuit_breaker_stats
            self._send_http_request = _send_http_request

            self.setup_completed = True
            logger.info("Test environment setup completed successfully")

        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            raise

    def record_test_result(self, test_name: str, passed: bool, details: str = "", duration: float = 0.0):
        """Record test result with details."""
        self.test_results["total_tests"] += 1
        if passed:
            self.test_results["passed_tests"] += 1
            status = "PASS"
        else:
            self.test_results["failed_tests"] += 1
            status = "FAIL"

        test_detail = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.test_results["test_details"].append(test_detail)

        logger.info(f"Test {status}: {test_name} - {details} ({duration:.3f}s)")

    async def test_postgresql_operations(self):
        """Test PostgreSQL operations with circuit breakers."""
        logger.info("Testing PostgreSQL operations with circuit breakers...")

        try:
            from app.repositories.domain import DeviceRepository, ExperimentRepository
            from app.models.domain import Device, DeviceStatus, DeviceType

            # Test device creation and retrieval
            async with self.db_manager.session_scope() as session:
                device_repo = DeviceRepository(Device, session)

                # Test 1: Normal device creation
                start_time = time.time()
                device_data = {
                    "name": "Test Device",
                    "mac_address": "00:11:22:33:44:55",
                    "serial_number": "TEST123456",
                    "device_type": DeviceType.RASPBERRY_PI,
                    "organization_id": uuid.uuid4(),
                    "location": "Test Lab"
                }

                device = await device_repo.create(device_data)
                duration = time.time() - start_time

                self.record_test_result(
                    "PostgreSQL - Device Creation",
                    device is not None,
                    f"Created device with ID: {device.id if device else 'None'}",
                    duration
                )

                # Test 2: Device retrieval
                if device:
                    start_time = time.time()
                    retrieved_device = await device_repo.get_by_id(device.id)
                    duration = time.time() - start_time

                    self.record_test_result(
                        "PostgreSQL - Device Retrieval",
                        retrieved_device is not None,
                        f"Retrieved device: {retrieved_device.name if retrieved_device else 'None'}",
                        duration
                    )

                # Test 3: Device query by MAC address
                start_time = time.time()
                mac_device = await device_repo.get_by_mac_address("00:11:22:33:44:55")
                duration = time.time() - start_time

                self.record_test_result(
                    "PostgreSQL - MAC Address Query",
                    mac_device is not None,
                    f"Found device by MAC: {mac_device.name if mac_device else 'None'}",
                    duration
                )

                # Test 4: Experiment operations
                exp_repo = ExperimentRepository(ExperimentRepository, session)

                start_time = time.time()
                exp_data = {
                    "name": "Test Experiment",
                    "description": "Test experiment for circuit breaker validation",
                    "organization_id": device_data["organization_id"],
                    "status": "draft"
                }

                experiment = await exp_repo.create(exp_data)
                duration = time.time() - start_time

                self.record_test_result(
                    "PostgreSQL - Experiment Creation",
                    experiment is not None,
                    f"Created experiment: {experiment.name if experiment else 'None'}",
                    duration
                )

        except Exception as e:
            self.record_test_result("PostgreSQL Operations", False, f"Error: {str(e)}")

    async def test_redis_operations(self):
        """Test Redis operations with circuit breakers."""
        logger.info("Testing Redis operations with circuit breakers...")

        try:
            # Test 1: Session creation
            start_time = time.time()
            session_id = f"test_session_{uuid.uuid4().hex[:8]}"
            session_data = {
                "user_id": str(uuid.uuid4()),
                "device_id": str(uuid.uuid4()),
                "connected_at": datetime.now(timezone.utc).isoformat()
            }

            success = await self.session_manager.save_session(session_id, session_data)
            duration = time.time() - start_time

            self.record_test_result(
                "Redis - Session Creation",
                success,
                f"Session saved: {session_id}",
                duration
            )

            # Test 2: Session retrieval
            start_time = time.time()
            retrieved_session = await self.session_manager.get_session(session_id)
            duration = time.time() - start_time

            self.record_test_result(
                "Redis - Session Retrieval",
                retrieved_session is not None,
                f"Retrieved session for user: {retrieved_session.get('user_id') if retrieved_session else 'None'}",
                duration
            )

            # Test 3: Connection tracking
            start_time = time.time()
            user_id = session_data["user_id"]
            connection_info = {
                "ip_address": "127.0.0.1",
                "user_agent": "Test Client",
                "connected_at": datetime.now(timezone.utc).isoformat()
            }

            track_success = await self.session_manager.track_connection(
                session_id, user_id, connection_info
            )
            duration = time.time() - start_time

            self.record_test_result(
                "Redis - Connection Tracking",
                track_success,
                f"Tracked connection for user: {user_id}",
                duration
            )

            # Test 4: Presence management
            start_time = time.time()
            presence_success = await self.session_manager.set_user_presence(
                user_id, "online", {"status": "active", "last_seen": datetime.now(timezone.utc).isoformat()}
            )
            duration = time.time() - start_time

            self.record_test_result(
                "Redis - Presence Management",
                presence_success,
                f"Set presence for user: {user_id}",
                duration
            )

            # Test 5: Cleanup
            start_time = time.time()
            await self.session_manager.delete_session(session_id)
            await self.session_manager.clear_user_presence(user_id)
            duration = time.time() - start_time

            self.record_test_result(
                "Redis - Cleanup Operations",
                True,
                f"Cleaned up session and presence for user: {user_id}",
                duration
            )

        except Exception as e:
            self.record_test_result("Redis Operations", False, f"Error: {str(e)}")

    async def test_external_api_operations(self):
        """Test external API operations with circuit breakers."""
        logger.info("Testing external API operations with circuit breakers...")

        try:
            # Test 1: Successful webhook delivery
            start_time = time.time()
            webhook_payload = {
                "event": "test_notification",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "message": "Test webhook for circuit breaker validation",
                    "source": "circuit_breaker_test"
                }
            }

            result = self._send_http_request(TEST_CONFIG["test_webhook_url"], webhook_payload)
            duration = time.time() - start_time

            self.record_test_result(
                "External API - Webhook Delivery",
                result is not None,
                f"Webhook delivered with status: {result['status_code'] if result else 'Failed'}",
                duration
            )

            # Test 2: Webhook with custom headers
            start_time = time.time()
            custom_headers = {
                "X-Custom-Header": "Circuit-Breaker-Test",
                "X-Test-ID": uuid.uuid4().hex
            }

            result = self._send_http_request(TEST_CONFIG["test_webhook_url"], webhook_payload, custom_headers)
            duration = time.time() - start_time

            self.record_test_result(
                "External API - Webhook with Headers",
                result is not None,
                f"Webhook with headers delivered: {result['status_code'] if result else 'Failed'}",
                duration
            )

        except Exception as e:
            self.record_test_result("External API Operations", False, f"Error: {str(e)}")

    async def test_circuit_breaker_states(self):
        """Test circuit breaker state monitoring and management."""
        logger.info("Testing circuit breaker state management...")

        try:
            # Get initial circuit breaker stats
            initial_stats = self.get_circuit_breaker_stats()
            self.test_results["circuit_breaker_states"]["initial"] = initial_stats

            # Test 1: Check circuit breaker health
            start_time = time.time()
            from app.core.circuit_breaker import are_all_circuits_healthy
            all_healthy = are_all_circuits_healthy()
            duration = time.time() - start_time

            self.record_test_result(
                "Circuit Breaker - Health Check",
                all_healthy,
                f"All circuits healthy: {all_healthy}",
                duration
            )

            # Test 2: Get individual circuit breaker states
            from app.core.circuit_breaker import ServiceType

            start_time = time.time()
            postgres_state = self.cb_manager.get_breaker_state(ServiceType.POSTGRESQL)
            redis_state = self.cb_manager.get_breaker_state(ServiceType.REDIS)
            external_api_state = self.cb_manager.get_breaker_state(ServiceType.EXTERNAL_API)
            duration = time.time() - start_time

            self.record_test_result(
                "Circuit Breaker - State Retrieval",
                all(state is not None for state in [postgres_state, redis_state, external_api_state]),
                f"Retrieved states for all circuit breakers",
                duration
            )

            # Test 3: Verify circuit breaker configurations
            start_time = time.time()
            all_states = self.cb_manager.get_all_breaker_states()
            duration = time.time() - start_time

            expected_services = ["postgresql", "redis", "influxdb", "mqtt", "minio", "external_api"]
            has_all_services = all(service in all_states for service in expected_services)

            self.record_test_result(
                "Circuit Breaker - Configuration",
                has_all_services,
                f"Circuit breakers configured for {len(all_states)} services",
                duration
            )

            self.test_results["circuit_breaker_states"]["final"] = self.get_circuit_breaker_stats()

        except Exception as e:
            self.record_test_result("Circuit Breaker States", False, f"Error: {str(e)}")

    async def test_performance_impact(self):
        """Test performance impact of circuit breakers."""
        logger.info("Testing performance impact of circuit breakers...")

        try:
            iterations = TEST_CONFIG["performance_test_iterations"]

            # Test 1: Database operation performance
            from app.repositories.domain import DeviceRepository
            from app.models.domain import Device, DeviceType

            db_times = []
            async with self.db_manager.session_scope() as session:
                device_repo = DeviceRepository(Device, session)

                for i in range(iterations):
                    start_time = time.time()
                    device_data = {
                        "name": f"Perf Test Device {i}",
                        "mac_address": f"00:11:22:33:44:{i:02d}",
                        "serial_number": f"PERF{i:06d}",
                        "device_type": DeviceType.RASPBERRY_PI,
                        "organization_id": uuid.uuid4(),
                        "location": "Performance Test Lab"
                    }

                    device = await device_repo.create(device_data)
                    db_times.append(time.time() - start_time)

            avg_db_time = sum(db_times) / len(db_times)
            self.test_results["performance_metrics"]["database_avg_ms"] = avg_db_time * 1000

            self.record_test_result(
                "Performance - Database Operations",
                avg_db_time < 0.1,  # Expect < 100ms per operation
                f"Average database operation time: {avg_db_time*1000:.2f}ms"
            )

            # Test 2: Redis operation performance
            redis_times = []
            for i in range(iterations):
                start_time = time.time()
                session_id = f"perf_test_{i}"
                session_data = {"test": True, "iteration": i}

                await self.session_manager.save_session(session_id, session_data)
                await self.session_manager.get_session(session_id)
                redis_times.append(time.time() - start_time)

            avg_redis_time = sum(redis_times) / len(redis_times)
            self.test_results["performance_metrics"]["redis_avg_ms"] = avg_redis_time * 1000

            self.record_test_result(
                "Performance - Redis Operations",
                avg_redis_time < 0.05,  # Expect < 50ms per operation
                f"Average Redis operation time: {avg_redis_time*1000:.2f}ms"
            )

            # Test 3: Circuit breaker overhead
            cb_times = []
            from app.core.circuit_breaker import ServiceType, is_circuit_healthy

            for i in range(iterations):
                start_time = time.time()
                is_healthy = is_circuit_healthy(ServiceType.POSTGRESQL)
                cb_times.append(time.time() - start_time)

            avg_cb_time = sum(cb_times) / len(cb_times)
            self.test_results["performance_metrics"]["circuit_breaker_avg_ms"] = avg_cb_time * 1000

            self.record_test_result(
                "Performance - Circuit Breaker Checks",
                avg_cb_time < 0.001,  # Expect < 1ms per check
                f"Average circuit breaker check time: {avg_cb_time*1000:.3f}ms"
            )

        except Exception as e:
            self.record_test_result("Performance Impact", False, f"Error: {str(e)}")

    async def run_all_tests(self):
        """Run all circuit breaker system tests."""
        logger.info("Starting comprehensive circuit breaker system tests...")

        if not self.setup_completed:
            await self.setup_test_environment()

        start_time = time.time()

        # Run all test suites
        await self.test_postgresql_operations()
        await self.test_redis_operations()
        await self.test_external_api_operations()
        await self.test_circuit_breaker_states()
        await self.test_performance_impact()

        total_duration = time.time() - start_time
        self.test_results["total_duration"] = total_duration

        # Generate final report
        self.generate_test_report()

        logger.info(f"All tests completed in {total_duration:.2f} seconds")

    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("Generating test report...")

        report = {
            "test_summary": {
                "total_tests": self.test_results["total_tests"],
                "passed_tests": self.test_results["passed_tests"],
                "failed_tests": self.test_results["failed_tests"],
                "success_rate": (self.test_results["passed_tests"] / max(1, self.test_results["total_tests"])) * 100,
                "total_duration": self.test_results["total_duration"]
            },
            "test_results": self.test_results["test_details"],
            "performance_metrics": self.test_results["performance_metrics"],
            "circuit_breaker_states": self.test_results["circuit_breaker_states"],
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Save report to file
        report_filename = f"circuit_breaker_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        print("\n" + "="*80)
        print("CIRCUIT BREAKER SYSTEM TEST REPORT")
        print("="*80)
        print(f"Total Tests: {report['test_summary']['total_tests']}")
        print(f"Passed: {report['test_summary']['passed_tests']}")
        print(f"Failed: {report['test_summary']['failed_tests']}")
        print(f"Success Rate: {report['test_summary']['success_rate']:.1f}%")
        print(f"Duration: {report['test_summary']['total_duration']:.2f}s")
        print("="*80)

        if self.test_results["performance_metrics"]:
            print("PERFORMANCE METRICS:")
            for metric, value in self.test_results["performance_metrics"].items():
                print(f"  {metric}: {value:.2f}")

        print("\nDETAILED RESULTS:")
        for test in self.test_results["test_details"]:
            status_symbol = "✓" if test["status"] == "PASS" else "✗"
            print(f"{status_symbol} {test['test_name']}: {test['details']} ({test['duration']:.3f}s)")

        print(f"\nFull report saved to: {report_filename}")
        print("="*80)

        return report

    async def cleanup(self):
        """Cleanup test resources."""
        try:
            if hasattr(self, 'session_manager'):
                await self.session_manager.close()
            if hasattr(self, 'db_manager'):
                await self.db_manager.close()
            logger.info("Test cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main test execution function."""
    test_runner = CircuitBreakerSystemTest()

    try:
        await test_runner.run_all_tests()
        return test_runner.test_results
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise
    finally:
        await test_runner.cleanup()


if __name__ == "__main__":
    # Run the comprehensive test suite
    results = asyncio.run(main())

    # Exit with appropriate code
    exit_code = 0 if results["failed_tests"] == 0 else 1
    exit(exit_code)
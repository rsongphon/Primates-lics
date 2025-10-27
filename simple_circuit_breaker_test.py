#!/usr/bin/env python3
"""
Simple Circuit Breaker Test Script

Tests the core circuit breaker functionality without complex dependencies.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_circuit_breaker_basics():
    """Test basic circuit breaker functionality."""
    logger.info("Testing circuit breaker basics...")

    try:
        # Import and test circuit breakers
        from app.core.circuit_breaker import (
            cb_manager, ServiceType, get_circuit_breaker_stats,
            postgresql_breaker, redis_breaker, external_api_breaker
        )
        from app.core.database import db_manager

        # Initialize database
        await db_manager.initialize("postgresql+asyncpg://lics:lics_dev@localhost:5433/lics_dev")

        test_results = {
            "tests_run": 0,
            "tests_passed": 0,
            "details": []
        }

        # Test 1: Circuit breaker initialization
        try:
            initial_stats = get_circuit_breaker_stats()
            circuits_count = len(initial_stats.get("circuit_breakers", {}))

            test_results["tests_run"] += 1
            if circuits_count >= 6:  # postgresql, redis, influxdb, mqtt, minio, external_api
                test_results["tests_passed"] += 1
                test_results["details"].append(f"✓ Circuit breaker initialization: {circuits_count} circuits")
                logger.info(f"✓ Circuit breaker initialization: {circuits_count} circuits")
            else:
                test_results["details"].append(f"✗ Circuit breaker initialization: Only {circuits_count} circuits")
                logger.error(f"✗ Circuit breaker initialization: Only {circuits_count} circuits")
        except Exception as e:
            test_results["tests_run"] += 1
            test_results["details"].append(f"✗ Circuit breaker initialization: {str(e)}")
            logger.error(f"✗ Circuit breaker initialization: {str(e)}")

        # Test 2: Database operations with circuit breaker
        try:
            from app.repositories.domain import DeviceRepository
            from app.models.domain import Device, DeviceType

            async with db_manager.session_scope() as session:
                device_repo = DeviceRepository(Device, session)

                # Create a test device
                device_data = {
                    "name": "Circuit Breaker Test Device",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "serial_number": "CBTEST123456",
                    "device_type": DeviceType.RASPBERRY_PI,
                    "organization_id": uuid.uuid4(),
                    "location": "Test Lab"
                }

                start_time = time.time()
                device = await device_repo.create(device_data)
                duration = time.time() - start_time

                test_results["tests_run"] += 1
                if device is not None:
                    test_results["tests_passed"] += 1
                    test_results["details"].append(f"✓ Database operation with circuit breaker: {duration:.3f}s")
                    logger.info(f"✓ Database operation with circuit breaker: {duration:.3f}s")
                else:
                    test_results["details"].append("✗ Database operation with circuit breaker: Failed to create device")
                    logger.error("✗ Database operation with circuit breaker: Failed to create device")

        except Exception as e:
            test_results["tests_run"] += 1
            test_results["details"].append(f"✗ Database operation with circuit breaker: {str(e)}")
            logger.error(f"✗ Database operation with circuit breaker: {str(e)}")

        # Test 3: Circuit breaker health checks
        try:
            from app.core.circuit_breaker import is_circuit_healthy, are_all_circuits_healthy

            start_time = time.time()
            postgres_healthy = is_circuit_healthy(ServiceType.POSTGRESQL)
            redis_healthy = is_circuit_healthy(ServiceType.REDIS)
            all_healthy = are_all_circuits_healthy()
            duration = time.time() - start_time

            test_results["tests_run"] += 1
            if all(healthy for healthy in [postgres_healthy, redis_healthy]) and all_healthy:
                test_results["tests_passed"] += 1
                test_results["details"].append(f"✓ Circuit breaker health checks: All healthy ({duration:.3f}s)")
                logger.info(f"✓ Circuit breaker health checks: All healthy ({duration:.3f}s)")
            else:
                test_results["details"].append(f"✗ Circuit breaker health checks: Postgres={postgres_healthy}, Redis={redis_healthy}, All={all_healthy}")
                logger.error(f"✗ Circuit breaker health checks: Postgres={postgres_healthy}, Redis={redis_healthy}, All={all_healthy}")

        except Exception as e:
            test_results["tests_run"] += 1
            test_results["details"].append(f"✗ Circuit breaker health checks: {str(e)}")
            logger.error(f"✗ Circuit breaker health checks: {str(e)}")

        # Test 4: Circuit breaker metrics
        try:
            start_time = time.time()
            final_stats = get_circuit_breaker_stats()
            duration = time.time() - start_time

            postgres_state = final_stats.get("circuit_breakers", {}).get("postgresql", {})

            test_results["tests_run"] += 1
            if postgres_state and "state" in postgres_state:
                test_results["tests_passed"] += 1
                test_results["details"].append(f"✓ Circuit breaker metrics: PostgreSQL state={postgres_state['state']}")
                logger.info(f"✓ Circuit breaker metrics: PostgreSQL state={postgres_state['state']}")
            else:
                test_results["details"].append("✗ Circuit breaker metrics: No PostgreSQL state found")
                logger.error("✗ Circuit breaker metrics: No PostgreSQL state found")

        except Exception as e:
            test_results["tests_run"] += 1
            test_results["details"].append(f"✗ Circuit breaker metrics: {str(e)}")
            logger.error(f"✗ Circuit breaker metrics: {str(e)}")

        # Test 5: Circuit breaker decorator overhead
        try:
            @postgresql_breaker
            async def test_operation():
                return "test_result"

            # Measure overhead
            iterations = 1000
            start_time = time.time()

            for _ in range(iterations):
                result = await test_operation()

            total_time = time.time() - start_time
            avg_overhead_ms = (total_time / iterations) * 1000

            test_results["tests_run"] += 1
            if avg_overhead_ms < 1.0:  # Expect < 1ms overhead per call
                test_results["tests_passed"] += 1
                test_results["details"].append(f"✓ Circuit breaker overhead: {avg_overhead_ms:.3f}ms per call")
                logger.info(f"✓ Circuit breaker overhead: {avg_overhead_ms:.3f}ms per call")
            else:
                test_results["details"].append(f"✗ Circuit breaker overhead: {avg_overhead_ms:.3f}ms per call (too high)")
                logger.error(f"✗ Circuit breaker overhead: {avg_overhead_ms:.3f}ms per call (too high)")

        except Exception as e:
            test_results["tests_run"] += 1
            test_results["details"].append(f"✗ Circuit breaker overhead: {str(e)}")
            logger.error(f"✗ Circuit breaker overhead: {str(e)}")

        # Cleanup
        await db_manager.close()

        return test_results

    except Exception as e:
        logger.error(f"Test setup failed: {e}")
        return {"tests_run": 0, "tests_passed": 0, "details": [f"Setup failed: {str(e)}"]}

async def main():
    """Main test execution."""
    logger.info("Starting simple circuit breaker test...")

    start_time = time.time()
    results = await test_circuit_breaker_basics()
    total_duration = time.time() - start_time

    # Generate report
    success_rate = (results["tests_passed"] / max(1, results["tests_run"])) * 100

    print("\n" + "="*80)
    print("CIRCUIT BREAKER TEST REPORT")
    print("="*80)
    print(f"Tests Run: {results['tests_run']}")
    print(f"Tests Passed: {results['tests_passed']}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Duration: {total_duration:.2f}s")
    print("="*80)

    print("\nTest Results:")
    for detail in results["details"]:
        print(f"  {detail}")

    print("="*80)

    # Save report
    report = {
        "summary": {
            "tests_run": results["tests_run"],
            "tests_passed": results["tests_passed"],
            "success_rate": success_rate,
            "duration": total_duration
        },
        "details": results["details"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    report_filename = f"circuit_breaker_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to: {report_filename}")
    print("="*80)

    return results

if __name__ == "__main__":
    results = asyncio.run(main())
    exit_code = 0 if results["tests_passed"] == results["tests_run"] else 1
    exit(exit_code)
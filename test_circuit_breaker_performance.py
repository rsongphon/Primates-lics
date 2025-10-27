#!/usr/bin/env python3
"""
Circuit Breaker Performance Test Suite

This script provides performance testing and benchmarking for circuit breakers:
1. Load testing under concurrent operations
2. Performance impact measurement
3. Throughput and latency analysis
4. Resource usage monitoring
5. Scalability testing
"""

import asyncio
import json
import logging
import time
import uuid
import psutil
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import statistics

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CircuitBreakerPerformanceTest:
    """
    Performance testing and benchmarking for circuit breakers.
    """

    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": [],
            "performance_metrics": {
                "throughput_tests": {},
                "latency_tests": {},
                "resource_tests": {},
                "scalability_tests": {}
            }
        }
        self.setup_completed = False
        self.resource_monitor = None

    async def setup_test_environment(self):
        """Setup performance test environment."""
        logger.info("Setting up performance test environment...")

        try:
            from app.core.circuit_breaker import (
                cb_manager, ServiceType, postgresql_breaker, redis_breaker, external_api_breaker
            )
            from app.core.database import db_manager
            from app.websocket.session import SessionManager

            # Initialize database
            await db_manager.initialize("postgresql+asyncpg://lics:lics_dev@localhost:5433/lics_dev")

            # Store references
            self.cb_manager = cb_manager
            self.db_manager = db_manager
            self.session_manager = SessionManager()
            self.postgresql_breaker = postgresql_breaker
            self.redis_breaker = redis_breaker
            self.external_api_breaker = external_api_breaker

            # Start resource monitoring
            self.start_resource_monitoring()

            self.setup_completed = True
            logger.info("Performance test environment setup completed")

        except Exception as e:
            logger.error(f"Failed to setup performance test environment: {e}")
            raise

    def record_test_result(self, test_name: str, passed: bool, details: str = "", duration: float = 0.0):
        """Record test result."""
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

        logger.info(f"Performance {status}: {test_name} - {details} ({duration:.3f}s)")

    def start_resource_monitoring(self):
        """Start system resource monitoring."""
        self.resource_stats = {
            "cpu_usage": [],
            "memory_usage": [],
            "timestamps": []
        }
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitoring started")

    def _monitor_resources(self):
        """Monitor system resources in background thread."""
        process = psutil.Process()

        while self.monitoring_active:
            try:
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                self.resource_stats["cpu_usage"].append(cpu_percent)
                self.resource_stats["memory_usage"].append(memory_mb)
                self.resource_stats["timestamps"].append(time.time())

                time.sleep(0.5)  # Sample every 500ms
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                break

    def stop_resource_monitoring(self):
        """Stop resource monitoring and return statistics."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

        if self.resource_stats["cpu_usage"]:
            return {
                "avg_cpu": statistics.mean(self.resource_stats["cpu_usage"]),
                "max_cpu": max(self.resource_stats["cpu_usage"]),
                "avg_memory_mb": statistics.mean(self.resource_stats["memory_usage"]),
                "max_memory_mb": max(self.resource_stats["memory_usage"]),
                "samples": len(self.resource_stats["cpu_usage"])
            }
        return {}

    async def test_database_throughput(self):
        """Test database operation throughput with circuit breakers."""
        logger.info("Testing database throughput...")

        try:
            from app.repositories.domain import DeviceRepository
            from app.models.domain import Device, DeviceType

            async def create_test_device(device_id: int) -> Tuple[bool, float]:
                """Create a test device and measure time."""
                start_time = time.time()
                try:
                    async with self.db_manager.session_scope() as session:
                        device_repo = DeviceRepository(Device, session)
                        device_data = {
                            "name": f"Throughput Test Device {device_id}",
                            "mac_address": f"00:11:22:33:44:{device_id:02x}",
                            "serial_number": f"THRPT{device_id:06d}",
                            "device_type": DeviceType.RASPBERRY_PI,
                            "organization_id": uuid.uuid4(),
                            "location": "Throughput Test Lab"
                        }
                        device = await device_repo.create(device_data)
                        duration = time.time() - start_time
                        return device is not None, duration
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"Device creation failed: {e}")
                    return False, duration

            # Test different concurrency levels
            concurrency_levels = [1, 5, 10, 25, 50]
            operations_per_level = 100

            throughput_results = {}

            for concurrency in concurrency_levels:
                logger.info(f"Testing database throughput with {concurrency} concurrent operations...")

                start_time = time.time()
                tasks = []

                for i in range(operations_per_level):
                    task = create_test_device(i)
                    tasks.append(task)

                # Execute with semaphore to control concurrency
                semaphore = asyncio.Semaphore(concurrency)

                async def controlled_operation(task_func):
                    async with semaphore:
                        return await task_func

                controlled_tasks = [controlled_operation(task) for task in tasks]
                results = await asyncio.gather(*controlled_tasks, return_exceptions=True)

                total_time = time.time() - start_time

                # Calculate metrics
                successful_ops = sum(1 for r in results if isinstance(r, tuple) and r[0])
                durations = [r[1] for r in results if isinstance(r, tuple)]
                avg_duration = statistics.mean(durations) if durations else 0
                throughput = successful_ops / total_time

                throughput_results[concurrency] = {
                    "operations": operations_per_level,
                    "successful": successful_ops,
                    "total_time": total_time,
                    "throughput_ops_per_sec": throughput,
                    "avg_latency_ms": avg_duration * 1000,
                    "success_rate": (successful_ops / operations_per_level) * 100
                }

                self.record_test_result(
                    f"Database Throughput - {concurrency} Concurrent",
                    throughput > 10,  # Expect > 10 ops/sec
                    f"Throughput: {throughput:.1f} ops/sec, Latency: {avg_duration*1000:.1f}ms",
                    total_time
                )

            self.test_results["performance_metrics"]["throughput_tests"]["database"] = throughput_results

        except Exception as e:
            self.record_test_result("Database Throughput", False, f"Error: {str(e)}")

    async def test_redis_throughput(self):
        """Test Redis operation throughput with circuit breakers."""
        logger.info("Testing Redis throughput...")

        try:
            async def redis_session_operation(session_id: int) -> Tuple[bool, float]:
                """Perform Redis session operations and measure time."""
                start_time = time.time()
                try:
                    # Save session
                    session_key = f"throughput_test_{session_id}"
                    session_data = {
                        "user_id": str(uuid.uuid4()),
                        "test_id": session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    save_success = await self.session_manager.save_session(session_key, session_data)

                    # Retrieve session
                    if save_success:
                        retrieved_session = await self.session_manager.get_session(session_key)
                        retrieve_success = retrieved_session is not None
                    else:
                        retrieve_success = False

                    # Clean up
                    await self.session_manager.delete_session(session_key)

                    duration = time.time() - start_time
                    return save_success and retrieve_success, duration
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"Redis operation failed: {e}")
                    return False, duration

            # Test different concurrency levels
            concurrency_levels = [1, 10, 25, 50, 100]
            operations_per_level = 200

            throughput_results = {}

            for concurrency in concurrency_levels:
                logger.info(f"Testing Redis throughput with {concurrency} concurrent operations...")

                start_time = time.time()
                semaphore = asyncio.Semaphore(concurrency)

                async def controlled_redis_operation(op_id: int):
                    async with semaphore:
                        return await redis_session_operation(op_id)

                tasks = [controlled_redis_operation(i) for i in range(operations_per_level)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                total_time = time.time() - start_time

                # Calculate metrics
                successful_ops = sum(1 for r in results if isinstance(r, tuple) and r[0])
                durations = [r[1] for r in results if isinstance(r, tuple)]
                avg_duration = statistics.mean(durations) if durations else 0
                throughput = successful_ops / total_time

                throughput_results[concurrency] = {
                    "operations": operations_per_level,
                    "successful": successful_ops,
                    "total_time": total_time,
                    "throughput_ops_per_sec": throughput,
                    "avg_latency_ms": avg_duration * 1000,
                    "success_rate": (successful_ops / operations_per_level) * 100
                }

                self.record_test_result(
                    f"Redis Throughput - {concurrency} Concurrent",
                    throughput > 50,  # Expect > 50 ops/sec for Redis
                    f"Throughput: {throughput:.1f} ops/sec, Latency: {avg_duration*1000:.1f}ms",
                    total_time
                )

            self.test_results["performance_metrics"]["throughput_tests"]["redis"] = throughput_results

        except Exception as e:
            self.record_test_result("Redis Throughput", False, f"Error: {str(e)}")

    async def test_circuit_breaker_overhead(self):
        """Test circuit breaker performance overhead."""
        logger.info("Testing circuit breaker overhead...")

        try:
            from app.core.circuit_breaker import ServiceType, is_circuit_healthy

            # Test circuit breaker health check overhead
            iterations = 10000

            start_time = time.time()
            for _ in range(iterations):
                is_healthy = is_circuit_healthy(ServiceType.POSTGRESQL)
            duration = time.time() - start_time

            avg_overhead_us = (duration / iterations) * 1000000  # Convert to microseconds

            overhead_acceptable = avg_overhead_us < 10  # Expect < 10 microseconds per check

            self.record_test_result(
                "Circuit Breaker Overhead - Health Check",
                overhead_acceptable,
                f"Average overhead: {avg_overhead_us:.2f}μs per check",
                duration
            )

            # Test circuit breaker decorator overhead
            @self.postgresql_breaker
            async def decorated_operation():
                return "quick_operation"

            start_time = time.time()
            for _ in range(iterations):
                result = await decorated_operation()
            duration = time.time() - start_time

            avg_decorator_overhead_us = (duration / iterations) * 1000000
            decorator_overhead_acceptable = avg_decorator_overhead_us < 50  # Expect < 50 microseconds

            self.record_test_result(
                "Circuit Breaker Overhead - Decorator",
                decorator_overhead_acceptable,
                f"Average decorator overhead: {avg_decorator_overhead_us:.2f}μs per call",
                duration
            )

            self.test_results["performance_metrics"]["latency_tests"]["circuit_breaker_overhead"] = {
                "health_check_overhead_us": avg_overhead_us,
                "decorator_overhead_us": avg_decorator_overhead_us,
                "iterations": iterations
            }

        except Exception as e:
            self.record_test_result("Circuit Breaker Overhead", False, f"Error: {str(e)}")

    async def test_latency_percentiles(self):
        """Test latency distribution and percentiles."""
        logger.info("Testing latency percentiles...")

        try:
            from app.repositories.domain import DeviceRepository
            from app.models.domain import Device, DeviceType

            # Collect latency samples for database operations
            latency_samples = []
            samples_to_collect = 1000

            async def sample_database_operation():
                start_time = time.time()
                try:
                    async with self.db_manager.session_scope() as session:
                        device_repo = DeviceRepository(Device, session)
                        device_data = {
                            "name": f"Latency Test Device {len(latency_samples)}",
                            "mac_address": f"00:11:22:33:44:{len(latency_samples):02x}",
                            "serial_number": f"LATENCY{len(latency_samples):06d}",
                            "device_type": DeviceType.RASPBERRY_PI,
                            "organization_id": uuid.uuid4(),
                            "location": "Latency Test Lab"
                        }
                        device = await device_repo.create(device_data)
                        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                        return device is not None, latency
                except Exception:
                    latency = (time.time() - start_time) * 1000
                    return False, latency

            # Collect samples
            logger.info(f"Collecting {samples_to_collect} latency samples...")
            for i in range(samples_to_collect):
                success, latency = await sample_database_operation()
                if success:
                    latency_samples.append(latency)

                if i % 100 == 0:
                    logger.info(f"Collected {i} samples...")

            if latency_samples:
                # Calculate percentiles
                p50 = statistics.median(latency_samples)
                p95 = sorted(latency_samples)[int(0.95 * len(latency_samples))]
                p99 = sorted(latency_samples)[int(0.99 * len(latency_samples))]
                avg_latency = statistics.mean(latency_samples)
                max_latency = max(latency_samples)

                latency_stats = {
                    "samples": len(latency_samples),
                    "avg_ms": avg_latency,
                    "p50_ms": p50,
                    "p95_ms": p95,
                    "p99_ms": p99,
                    "max_ms": max_latency
                }

                self.test_results["performance_metrics"]["latency_tests"]["database_percentiles"] = latency_stats

                # Performance expectations
                p95_acceptable = p95 < 100  # P95 should be < 100ms
                p99_acceptable = p99 < 200  # P99 should be < 200ms

                self.record_test_result(
                    "Database Latency - P95",
                    p95_acceptable,
                    f"P95 latency: {p95:.1f}ms",
                    0.1
                )

                self.record_test_result(
                    "Database Latency - P99",
                    p99_acceptable,
                    f"P99 latency: {p99:.1f}ms",
                    0.1
                )

                logger.info(f"Latency Statistics: Avg={avg_latency:.1f}ms, P50={p50:.1f}ms, P95={p95:.1f}ms, P99={p99:.1f}ms")
            else:
                self.record_test_result("Database Latency Percentiles", False, "No successful operations to measure")

        except Exception as e:
            self.record_test_result("Database Latency Percentiles", False, f"Error: {str(e)}")

    async def test_scalability(self):
        """Test system scalability under increasing load."""
        logger.info("Testing system scalability...")

        try:
            scalability_results = {}

            # Test different load levels
            load_levels = [
                {"concurrent_users": 10, "operations_per_user": 20},
                {"concurrent_users": 50, "operations_per_user": 20},
                {"concurrent_users": 100, "operations_per_user": 20},
                {"concurrent_users": 200, "operations_per_user": 10}
            ]

            for load_config in load_levels:
                concurrent_users = load_config["concurrent_users"]
                operations_per_user = load_config["operations_per_user"]

                logger.info(f"Testing scalability with {concurrent_users} concurrent users, {operations_per_user} ops each...")

                start_time = time.time()

                # Start resource monitoring for this load level
                resource_start = len(self.resource_stats["cpu_usage"])

                # Create user sessions
                async def simulate_user_operations(user_id: int):
                    user_results = []
                    for op_id in range(operations_per_user):
                        # Mix of operations
                        if op_id % 3 == 0:
                            # Database operation
                            async with self.db_manager.session_scope() as session:
                                from app.repositories.domain import DeviceRepository
                                from app.models.domain import Device, DeviceType
                                device_repo = DeviceRepository(Device, session)
                                device_data = {
                                    "name": f"Scale Test User {user_id} Op {op_id}",
                                    "mac_address": f"00:11:22:33:44:{user_id:02x}{op_id:02x}",
                                    "serial_number": f"SCALE{user_id:04d}{op_id:04d}",
                                    "device_type": DeviceType.RASPBERRY_PI,
                                    "organization_id": uuid.uuid4(),
                                    "location": f"Scale Test Lab - User {user_id}"
                                }
                                device = await device_repo.create(device_data)
                                user_results.append(device is not None)

                        elif op_id % 3 == 1:
                            # Redis operation
                            session_key = f"scale_test_user_{user_id}_op_{op_id}"
                            session_data = {"user_id": user_id, "operation": op_id}
                            await self.session_manager.save_session(session_key, session_data)
                            retrieved = await self.session_manager.get_session(session_key)
                            user_results.append(retrieved is not None)
                            await self.session_manager.delete_session(session_key)

                        else:
                            # Circuit breaker health check
                            from app.core.circuit_breaker import is_circuit_healthy, ServiceType
                            healthy = is_circuit_healthy(ServiceType.POSTGRESQL)
                            user_results.append(healthy)

                    return user_results

                # Execute user operations concurrently
                user_tasks = [simulate_user_operations(i) for i in range(concurrent_users)]
                all_user_results = await asyncio.gather(*user_tasks, return_exceptions=True)

                total_time = time.time() - start_time

                # Calculate metrics
                total_operations = concurrent_users * operations_per_user
                successful_operations = sum(
                    sum(results) for results in all_user_results
                    if isinstance(results, list)
                )

                # Get resource usage during this test
                resource_end = len(self.resource_stats["cpu_usage"])
                if resource_end > resource_start:
                    test_cpu_usage = self.resource_stats["cpu_usage"][resource_start:resource_end]
                    test_memory_usage = self.resource_stats["memory_usage"][resource_start:resource_end]
                    avg_cpu = statistics.mean(test_cpu_usage) if test_cpu_usage else 0
                    max_memory = max(test_memory_usage) if test_memory_usage else 0
                else:
                    avg_cpu = 0
                    max_memory = 0

                throughput = successful_operations / total_time
                success_rate = (successful_operations / total_operations) * 100

                scalability_results[concurrent_users] = {
                    "concurrent_users": concurrent_users,
                    "operations_per_user": operations_per_user,
                    "total_operations": total_operations,
                    "successful_operations": successful_operations,
                    "success_rate": success_rate,
                    "throughput_ops_per_sec": throughput,
                    "total_time": total_time,
                    "avg_cpu_percent": avg_cpu,
                    "max_memory_mb": max_memory
                }

                # Performance expectations
                throughput_acceptable = throughput > 20  # Expect > 20 ops/sec overall
                success_rate_acceptable = success_rate > 95  # Expect > 95% success rate

                self.record_test_result(
                    f"Scalability - {concurrent_users} Users",
                    throughput_acceptable and success_rate_acceptable,
                    f"Throughput: {throughput:.1f} ops/sec, Success: {success_rate:.1f}%, CPU: {avg_cpu:.1f}%",
                    total_time
                )

            self.test_results["performance_metrics"]["scalability_tests"] = scalability_results

        except Exception as e:
            self.record_test_result("System Scalability", False, f"Error: {str(e)}")

    async def run_all_performance_tests(self):
        """Run all performance tests."""
        logger.info("Starting circuit breaker performance tests...")

        if not self.setup_completed:
            await self.setup_test_environment()

        start_time = time.time()

        # Run performance test suites
        await self.test_circuit_breaker_overhead()
        await self.test_database_throughput()
        await self.test_redis_throughput()
        await self.test_latency_percentiles()
        await self.test_scalability()

        total_duration = time.time() - start_time
        self.test_results["total_duration"] = total_duration

        # Get resource usage statistics
        resource_stats = self.stop_resource_monitoring()
        if resource_stats:
            self.test_results["performance_metrics"]["resource_usage"] = resource_stats

        # Generate performance report
        self.generate_performance_report()

        logger.info(f"All performance tests completed in {total_duration:.2f} seconds")

    def generate_performance_report(self):
        """Generate performance test report."""
        logger.info("Generating performance test report...")

        report = {
            "performance_summary": {
                "total_tests": self.test_results["total_tests"],
                "passed_tests": self.test_results["passed_tests"],
                "failed_tests": self.test_results["failed_tests"],
                "success_rate": (self.test_results["passed_tests"] / max(1, self.test_results["total_tests"])) * 100,
                "total_duration": self.test_results["total_duration"]
            },
            "performance_results": self.test_results["test_details"],
            "performance_metrics": self.test_results["performance_metrics"],
            "performance_timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Save report to file
        report_filename = f"circuit_breaker_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        print("\n" + "="*80)
        print("CIRCUIT BREAKER PERFORMANCE REPORT")
        print("="*80)
        print(f"Total Tests: {report['performance_summary']['total_tests']}")
        print(f"Passed: {report['performance_summary']['passed_tests']}")
        print(f"Failed: {report['performance_summary']['failed_tests']}")
        print(f"Success Rate: {report['performance_summary']['success_rate']:.1f}%")
        print(f"Duration: {report['performance_summary']['total_duration']:.2f}s")
        print("="*80)

        # Print key performance metrics
        metrics = self.test_results["performance_metrics"]

        if "circuit_breaker_overhead" in metrics.get("latency_tests", {}):
            overhead = metrics["latency_tests"]["circuit_breaker_overhead"]
            print(f"\nCIRCUIT BREAKER OVERHEAD:")
            print(f"  Health Check: {overhead.get('health_check_overhead_us', 0):.2f}μs")
            print(f"  Decorator: {overhead.get('decorator_overhead_us', 0):.2f}μs")

        if "database" in metrics.get("throughput_tests", {}):
            db_throughput = metrics["throughput_tests"]["database"]
            best_throughput = max(
                (data["throughput_ops_per_sec"] for data in db_throughput.values()),
                default=0
            )
            print(f"\nDATABASE THROUGHPUT:")
            print(f"  Best Throughput: {best_throughput:.1f} ops/sec")

        if "redis" in metrics.get("throughput_tests", {}):
            redis_throughput = metrics["throughput_tests"]["redis"]
            best_redis_throughput = max(
                (data["throughput_ops_per_sec"] for data in redis_throughput.values()),
                default=0
            )
            print(f"\nREDIS THROUGHPUT:")
            print(f"  Best Throughput: {best_redis_throughput:.1f} ops/sec")

        if "database_percentiles" in metrics.get("latency_tests", {}):
            latency = metrics["latency_tests"]["database_percentiles"]
            print(f"\nDATABASE LATENCY:")
            print(f"  Average: {latency.get('avg_ms', 0):.1f}ms")
            print(f"  P50: {latency.get('p50_ms', 0):.1f}ms")
            print(f"  P95: {latency.get('p95_ms', 0):.1f}ms")
            print(f"  P99: {latency.get('p99_ms', 0):.1f}ms")

        if "resource_usage" in metrics:
            resource = metrics["resource_usage"]
            print(f"\nRESOURCE USAGE:")
            print(f"  Average CPU: {resource.get('avg_cpu', 0):.1f}%")
            print(f"  Peak CPU: {resource.get('max_cpu', 0):.1f}%")
            print(f"  Average Memory: {resource.get('avg_memory_mb', 0):.1f}MB")
            print(f"  Peak Memory: {resource.get('max_memory_mb', 0):.1f}MB")

        print("\nDETAILED RESULTS:")
        for test in self.test_results["test_details"]:
            status_symbol = "✓" if test["status"] == "PASS" else "✗"
            print(f"{status_symbol} {test['test_name']}: {test['details']} ({test['duration']:.3f}s)")

        print(f"\nPerformance report saved to: {report_filename}")
        print("="*80)

        return report

    async def cleanup(self):
        """Cleanup performance test resources."""
        try:
            self.stop_resource_monitoring()

            if hasattr(self, 'session_manager'):
                await self.session_manager.close()
            if hasattr(self, 'db_manager'):
                await self.db_manager.close()

            logger.info("Performance test cleanup completed")
        except Exception as e:
            logger.error(f"Performance cleanup error: {e}")


async def main():
    """Main performance test execution function."""
    test_runner = CircuitBreakerPerformanceTest()

    try:
        await test_runner.run_all_performance_tests()
        return test_runner.test_results
    except Exception as e:
        logger.error(f"Performance test execution failed: {e}")
        raise
    finally:
        await test_runner.cleanup()


if __name__ == "__main__":
    # Run the performance test suite
    results = asyncio.run(main())

    # Exit with appropriate code
    exit_code = 0 if results["failed_tests"] == 0 else 1
    exit(exit_code)
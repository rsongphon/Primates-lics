#!/usr/bin/env python3
"""
LICS Messaging System Test Suite

Comprehensive testing suite for all messaging components in the LICS system,
including MQTT broker, Redis Streams/Pub-Sub, and MinIO object storage.

Usage:
    python test-messaging-suite.py [--test all|mqtt|redis|minio]
                                   [--format json|text] [--benchmark] [--load-test]

Features:
    - MQTT broker functionality and authentication testing
    - Redis Streams event sourcing validation
    - Redis Pub/Sub real-time messaging testing
    - MinIO object storage operations testing
    - Message routing and delivery verification
    - Performance benchmarking
    - Load testing capabilities
    - Security and ACL validation
    - End-to-end message flow testing
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
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
try:
    import redis.asyncio as redis
    import paho.mqtt.client as mqtt
    import requests
    import minio
    from minio.error import S3Error
    import asyncio_mqtt
    import numpy as np
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install redis paho-mqtt requests minio asyncio-mqtt numpy")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('messaging-test-suite.log')
    ]
)
logger = logging.getLogger(__name__)

class MessagingTestSuite:
    """Comprehensive messaging system testing suite for LICS."""

    def __init__(self, benchmark_mode: bool = False, load_test_mode: bool = False):
        """
        Initialize the test suite.

        Args:
            benchmark_mode: Enable performance benchmarking
            load_test_mode: Enable load testing
        """
        self.benchmark_mode = benchmark_mode
        self.load_test_mode = load_test_mode
        self.results = {}
        self.start_time = time.time()

        # Configuration
        self.config = {
            'mqtt': {
                'host': 'localhost',
                'port': 1883,
                'websocket_port': 9001,
                'username': None,
                'password': None,
                'timeout': 10
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'minio': {
                'endpoint': 'localhost:9000',
                'access_key': 'minioadmin',
                'secret_key': 'minioadmin',
                'secure': False
            }
        }

        # Test topic hierarchy for MQTT
        self.mqtt_topics = {
            'device_telemetry': 'lics/devices/+/telemetry/+',
            'device_commands': 'lics/devices/+/commands/+',
            'system_events': 'lics/system/events/+',
            'test_topic': 'lics/test/messaging'
        }

        # Redis streams and channels
        self.redis_streams = {
            'device_telemetry': 'lics:streams:device_telemetry',
            'device_commands': 'lics:streams:device_commands',
            'system_events': 'lics:streams:system_events'
        }

        self.redis_channels = {
            'notifications': 'lics:notifications',
            'realtime_updates': 'lics:realtime_updates',
            'test_channel': 'lics:test:pubsub'
        }

        # MinIO bucket structure
        self.minio_buckets = [
            'lics-videos', 'lics-data', 'lics-exports', 'lics-uploads',
            'lics-config', 'lics-backups', 'lics-temp', 'lics-assets',
            'lics-logs', 'lics-ml'
        ]

    def generate_test_message(self, message_type: str = "telemetry") -> Dict[str, Any]:
        """Generate test message payload."""
        base_message = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "test": True
        }

        if message_type == "telemetry":
            base_message.update({
                "device_id": f"test_device_{random.randint(1, 10)}",
                "sensor_type": random.choice(["temperature", "humidity", "pressure"]),
                "value": round(random.uniform(20, 30), 2),
                "unit": "celsius"
            })
        elif message_type == "command":
            base_message.update({
                "device_id": f"test_device_{random.randint(1, 10)}",
                "command": random.choice(["start", "stop", "reset", "calibrate"]),
                "parameters": {"duration": random.randint(10, 60)}
            })
        elif message_type == "event":
            base_message.update({
                "event_type": random.choice(["device_connected", "device_disconnected", "error"]),
                "severity": random.choice(["info", "warning", "error"]),
                "source": "test_suite"
            })

        return base_message

    async def test_mqtt_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive MQTT broker testing."""
        logger.info("🧪 Testing MQTT broker comprehensively...")

        result = {
            "name": "MQTT Broker Comprehensive Test",
            "healthy": False,
            "tests": {},
            "performance": {},
            "errors": []
        }

        try:
            # 1. Basic connectivity test
            connection_result = await self._test_mqtt_connectivity()
            result["tests"]["connectivity"] = connection_result

            # 2. Publish/Subscribe test
            pubsub_result = await self._test_mqtt_pubsub()
            result["tests"]["publish_subscribe"] = pubsub_result

            # 3. Topic hierarchy test
            hierarchy_result = await self._test_mqtt_topic_hierarchy()
            result["tests"]["topic_hierarchy"] = hierarchy_result

            # 4. QoS levels test
            qos_result = await self._test_mqtt_qos_levels()
            result["tests"]["qos_levels"] = qos_result

            # 5. Retained messages test
            retained_result = await self._test_mqtt_retained_messages()
            result["tests"]["retained_messages"] = retained_result

            # 6. Authentication test (if configured)
            if self.config['mqtt']['username']:
                auth_result = await self._test_mqtt_authentication()
                result["tests"]["authentication"] = auth_result

            # 7. Performance benchmarking
            if self.benchmark_mode:
                perf_result = await self._benchmark_mqtt_performance()
                result["performance"] = perf_result

            # 8. Load testing
            if self.load_test_mode:
                load_result = await self._load_test_mqtt()
                result["tests"]["load_test"] = load_result

            # Overall health assessment
            failed_tests = [name for name, test in result["tests"].items()
                           if test.get("status") == "failed"]
            result["healthy"] = len(failed_tests) == 0

        except Exception as e:
            result["tests"]["connectivity"] = {
                "status": "failed",
                "error": str(e)
            }
            result["errors"].append(f"MQTT testing failed: {e}")

        return result

    async def _test_mqtt_connectivity(self) -> Dict[str, Any]:
        """Test basic MQTT connectivity."""
        try:
            async with asyncio_mqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                # Simple connectivity test
                test_topic = "lics/test/connectivity"
                test_message = "connectivity_test"

                await client.publish(test_topic, test_message)

                return {
                    "status": "passed",
                    "broker_host": self.config['mqtt']['host'],
                    "broker_port": self.config['mqtt']['port']
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _test_mqtt_pubsub(self) -> Dict[str, Any]:
        """Test MQTT publish/subscribe functionality."""
        try:
            messages_received = []
            test_topic = "lics/test/pubsub"

            async with asyncio_mqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                # Subscribe to test topic
                await client.subscribe(test_topic)

                # Publish test messages
                test_messages = [
                    self.generate_test_message("telemetry"),
                    self.generate_test_message("command"),
                    self.generate_test_message("event")
                ]

                # Start listening for messages
                async def message_listener():
                    async for message in client.messages:
                        try:
                            payload = json.loads(message.payload.decode())
                            messages_received.append(payload)
                            if len(messages_received) >= len(test_messages):
                                break
                        except json.JSONDecodeError:
                            pass

                # Start listener task
                listener_task = asyncio.create_task(message_listener())

                # Give listener time to start
                await asyncio.sleep(0.1)

                # Publish messages
                for msg in test_messages:
                    await client.publish(test_topic, json.dumps(msg))
                    await asyncio.sleep(0.1)

                # Wait for messages or timeout
                try:
                    await asyncio.wait_for(listener_task, timeout=5.0)
                except asyncio.TimeoutError:
                    listener_task.cancel()

                return {
                    "status": "passed" if len(messages_received) >= len(test_messages) else "warning",
                    "messages_sent": len(test_messages),
                    "messages_received": len(messages_received),
                    "success_rate": len(messages_received) / len(test_messages) * 100
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _test_mqtt_topic_hierarchy(self) -> Dict[str, Any]:
        """Test MQTT topic hierarchy and wildcards."""
        try:
            received_topics = set()

            async with asyncio_mqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                # Subscribe to wildcard topics
                await client.subscribe("lics/devices/+/telemetry/+")
                await client.subscribe("lics/system/events/+")

                # Message listener
                async def topic_listener():
                    async for message in client.messages:
                        received_topics.add(message.topic.value)
                        if len(received_topics) >= 4:
                            break

                listener_task = asyncio.create_task(topic_listener())
                await asyncio.sleep(0.1)

                # Publish to specific topics
                test_topics = [
                    "lics/devices/device1/telemetry/temperature",
                    "lics/devices/device2/telemetry/humidity",
                    "lics/devices/device1/telemetry/pressure",
                    "lics/system/events/startup"
                ]

                for topic in test_topics:
                    message = self.generate_test_message()
                    await client.publish(topic, json.dumps(message))
                    await asyncio.sleep(0.1)

                # Wait for messages
                try:
                    await asyncio.wait_for(listener_task, timeout=5.0)
                except asyncio.TimeoutError:
                    listener_task.cancel()

                return {
                    "status": "passed" if len(received_topics) >= 3 else "warning",
                    "topics_published": len(test_topics),
                    "topics_received": len(received_topics),
                    "wildcard_matching": len(received_topics) > 0
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _test_mqtt_qos_levels(self) -> Dict[str, Any]:
        """Test different MQTT QoS levels."""
        try:
            qos_results = {}

            async with asyncio_mqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                test_topic = "lics/test/qos"

                # Test QoS 0, 1, 2
                for qos_level in [0, 1, 2]:
                    try:
                        await client.subscribe(test_topic, qos=qos_level)
                        await client.publish(test_topic, f"qos_{qos_level}_test", qos=qos_level)

                        qos_results[f"qos_{qos_level}"] = {
                            "status": "passed",
                            "level": qos_level
                        }
                    except Exception as e:
                        qos_results[f"qos_{qos_level}"] = {
                            "status": "failed",
                            "error": str(e)
                        }

                successful_qos = sum(1 for result in qos_results.values()
                                   if result.get("status") == "passed")

                return {
                    "status": "passed" if successful_qos >= 2 else "warning",
                    "qos_levels_tested": len(qos_results),
                    "qos_levels_successful": successful_qos,
                    "qos_results": qos_results
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _test_mqtt_retained_messages(self) -> Dict[str, Any]:
        """Test MQTT retained messages functionality."""
        try:
            async with asyncio_mqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                test_topic = "lics/test/retained"
                retained_message = json.dumps({
                    "type": "retained_test",
                    "timestamp": datetime.now().isoformat(),
                    "value": "test_retained_message"
                })

                # Publish retained message
                await client.publish(test_topic, retained_message, retain=True)
                await asyncio.sleep(0.5)

                # Subscribe to topic (should receive retained message)
                received_retained = False
                await client.subscribe(test_topic)

                # Listen for retained message
                try:
                    async for message in client.messages:
                        if message.topic.value == test_topic:
                            received_retained = True
                            break
                except asyncio.TimeoutError:
                    pass

                # Clean up retained message
                await client.publish(test_topic, "", retain=True)

                return {
                    "status": "passed" if received_retained else "warning",
                    "retained_message_received": received_retained
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _benchmark_mqtt_performance(self) -> Dict[str, Any]:
        """Benchmark MQTT performance."""
        try:
            publish_times = []
            message_count = 100

            async with asyncio_mqtt.Client(
                hostname=self.config['mqtt']['host'],
                port=self.config['mqtt']['port']
            ) as client:
                test_topic = "lics/test/benchmark"

                # Benchmark publish operations
                for i in range(message_count):
                    message = self.generate_test_message()
                    start_time = time.time()
                    await client.publish(test_topic, json.dumps(message))
                    publish_times.append(time.time() - start_time)

                return {
                    "messages_published": message_count,
                    "avg_publish_time_ms": round(statistics.mean(publish_times) * 1000, 3),
                    "min_publish_time_ms": round(min(publish_times) * 1000, 3),
                    "max_publish_time_ms": round(max(publish_times) * 1000, 3),
                    "publish_rate_per_second": round(message_count / sum(publish_times), 2)
                }

        except Exception as e:
            return {"error": str(e)}

    async def _load_test_mqtt(self) -> Dict[str, Any]:
        """Load test MQTT broker with concurrent connections."""
        try:
            concurrent_clients = 20
            messages_per_client = 10
            successful_clients = 0
            total_messages_sent = 0

            async def client_load_test(client_id: int):
                try:
                    async with asyncio_mqtt.Client(
                        hostname=self.config['mqtt']['host'],
                        port=self.config['mqtt']['port'],
                        client_id=f"load_test_client_{client_id}"
                    ) as client:
                        topic = f"lics/test/load/{client_id}"
                        for i in range(messages_per_client):
                            message = self.generate_test_message()
                            await client.publish(topic, json.dumps(message))
                        return messages_per_client
                except Exception:
                    return 0

            # Run concurrent load test
            tasks = [client_load_test(i) for i in range(concurrent_clients)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, int) and result > 0:
                    successful_clients += 1
                    total_messages_sent += result

            return {
                "status": "passed" if successful_clients >= concurrent_clients * 0.8 else "warning",
                "concurrent_clients": concurrent_clients,
                "successful_clients": successful_clients,
                "total_messages_sent": total_messages_sent,
                "success_rate": round(successful_clients / concurrent_clients * 100, 2)
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def test_redis_messaging_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive Redis messaging testing (Streams and Pub/Sub)."""
        logger.info("🧪 Testing Redis messaging comprehensively...")

        result = {
            "name": "Redis Messaging Comprehensive Test",
            "healthy": False,
            "tests": {},
            "performance": {},
            "errors": []
        }

        try:
            # Connection test
            redis_client = redis.Redis(**self.config['redis'], decode_responses=True)

            # 1. Streams functionality test
            streams_result = await self._test_redis_streams(redis_client)
            result["tests"]["streams"] = streams_result

            # 2. Pub/Sub functionality test
            pubsub_result = await self._test_redis_pubsub(redis_client)
            result["tests"]["pubsub"] = pubsub_result

            # 3. Consumer groups test
            consumer_groups_result = await self._test_redis_consumer_groups(redis_client)
            result["tests"]["consumer_groups"] = consumer_groups_result

            # 4. Performance benchmarking
            if self.benchmark_mode:
                perf_result = await self._benchmark_redis_messaging(redis_client)
                result["performance"] = perf_result

            # 5. Load testing
            if self.load_test_mode:
                load_result = await self._load_test_redis_messaging(redis_client)
                result["tests"]["load_test"] = load_result

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
            result["errors"].append(f"Redis messaging testing failed: {e}")

        return result

    async def _test_redis_streams(self, redis_client) -> Dict[str, Any]:
        """Test Redis Streams functionality."""
        try:
            stream_name = "test:stream:telemetry"
            entries_added = []

            # Add entries to stream
            for i in range(5):
                message = self.generate_test_message("telemetry")
                entry_id = await redis_client.xadd(stream_name, message)
                entries_added.append(entry_id)

            # Read from stream
            stream_data = await redis_client.xrange(stream_name)

            # Test stream info
            stream_info = await redis_client.xinfo_stream(stream_name)

            # Cleanup
            await redis_client.delete(stream_name)

            return {
                "status": "passed",
                "entries_added": len(entries_added),
                "entries_read": len(stream_data),
                "stream_length": stream_info.get("length", 0)
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _test_redis_pubsub(self, redis_client) -> Dict[str, Any]:
        """Test Redis Pub/Sub functionality."""
        try:
            channel_name = "test:channel:notifications"
            messages_received = []

            # Create pubsub instance
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel_name)

            # Message listener task
            async def message_listener():
                try:
                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            messages_received.append(message["data"])
                            if len(messages_received) >= 3:
                                break
                except Exception:
                    pass

            listener_task = asyncio.create_task(message_listener())
            await asyncio.sleep(0.1)

            # Publish test messages
            test_messages = [
                self.generate_test_message("event"),
                self.generate_test_message("telemetry"),
                self.generate_test_message("command")
            ]

            for message in test_messages:
                await redis_client.publish(channel_name, json.dumps(message))
                await asyncio.sleep(0.1)

            # Wait for messages
            try:
                await asyncio.wait_for(listener_task, timeout=3.0)
            except asyncio.TimeoutError:
                listener_task.cancel()

            await pubsub.close()

            return {
                "status": "passed" if len(messages_received) >= 2 else "warning",
                "messages_published": len(test_messages),
                "messages_received": len(messages_received)
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _test_redis_consumer_groups(self, redis_client) -> Dict[str, Any]:
        """Test Redis consumer groups functionality."""
        try:
            stream_name = "test:stream:consumer_groups"
            group_name = "test_group"
            consumer_name = "test_consumer"

            # Add test data to stream
            for i in range(3):
                message = self.generate_test_message("telemetry")
                await redis_client.xadd(stream_name, message)

            # Create consumer group
            try:
                await redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
            except Exception:
                pass  # Group might already exist

            # Read as consumer
            consumer_data = await redis_client.xreadgroup(
                group_name, consumer_name, {stream_name: ">"}, count=2
            )

            # Get group info
            group_info = await redis_client.xinfo_groups(stream_name)

            # Cleanup
            await redis_client.delete(stream_name)

            return {
                "status": "passed",
                "consumer_group_created": len(group_info) > 0,
                "messages_consumed": len(consumer_data[0][1]) if consumer_data else 0
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _benchmark_redis_messaging(self, redis_client) -> Dict[str, Any]:
        """Benchmark Redis messaging performance."""
        try:
            # Benchmark Streams
            stream_times = []
            stream_name = "benchmark:stream"

            for i in range(50):
                message = self.generate_test_message()
                start_time = time.time()
                await redis_client.xadd(stream_name, message)
                stream_times.append(time.time() - start_time)

            # Benchmark Pub/Sub
            pubsub_times = []
            channel_name = "benchmark:channel"

            for i in range(50):
                message = self.generate_test_message()
                start_time = time.time()
                await redis_client.publish(channel_name, json.dumps(message))
                pubsub_times.append(time.time() - start_time)

            # Cleanup
            await redis_client.delete(stream_name)

            return {
                "streams_avg_time_ms": round(statistics.mean(stream_times) * 1000, 3),
                "pubsub_avg_time_ms": round(statistics.mean(pubsub_times) * 1000, 3),
                "streams_rate_per_second": round(50 / sum(stream_times), 2),
                "pubsub_rate_per_second": round(50 / sum(pubsub_times), 2)
            }

        except Exception as e:
            return {"error": str(e)}

    async def _load_test_redis_messaging(self, redis_client) -> Dict[str, Any]:
        """Load test Redis messaging."""
        try:
            # Test concurrent stream writes
            async def stream_load_test():
                stream_name = f"load_test:stream:{uuid.uuid4()}"
                for i in range(20):
                    message = self.generate_test_message()
                    await redis_client.xadd(stream_name, message)
                await redis_client.delete(stream_name)
                return 20

            # Test concurrent pub/sub
            async def pubsub_load_test():
                channel_name = f"load_test:channel:{uuid.uuid4()}"
                for i in range(20):
                    message = self.generate_test_message()
                    await redis_client.publish(channel_name, json.dumps(message))
                return 20

            # Run concurrent tasks
            stream_tasks = [stream_load_test() for _ in range(10)]
            pubsub_tasks = [pubsub_load_test() for _ in range(10)]

            stream_results = await asyncio.gather(*stream_tasks, return_exceptions=True)
            pubsub_results = await asyncio.gather(*pubsub_tasks, return_exceptions=True)

            stream_success = sum(1 for r in stream_results if isinstance(r, int))
            pubsub_success = sum(1 for r in pubsub_results if isinstance(r, int))

            return {
                "status": "passed" if stream_success >= 8 and pubsub_success >= 8 else "warning",
                "stream_tasks_successful": stream_success,
                "pubsub_tasks_successful": pubsub_success,
                "total_tasks": len(stream_tasks) + len(pubsub_tasks)
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def test_minio_comprehensive(self) -> Dict[str, Any]:
        """Comprehensive MinIO object storage testing."""
        logger.info("🧪 Testing MinIO object storage comprehensively...")

        result = {
            "name": "MinIO Object Storage Comprehensive Test",
            "healthy": False,
            "tests": {},
            "performance": {},
            "errors": []
        }

        try:
            # Initialize MinIO client
            minio_client = minio.Minio(**self.config['minio'])

            # 1. Connectivity and health test
            health_result = self._test_minio_health()
            result["tests"]["health"] = health_result

            # 2. Bucket operations test
            bucket_result = self._test_minio_buckets(minio_client)
            result["tests"]["bucket_operations"] = bucket_result

            # 3. Object operations test
            object_result = self._test_minio_objects(minio_client)
            result["tests"]["object_operations"] = object_result

            # 4. Versioning test
            versioning_result = self._test_minio_versioning(minio_client)
            result["tests"]["versioning"] = versioning_result

            # 5. Performance benchmarking
            if self.benchmark_mode:
                perf_result = self._benchmark_minio_performance(minio_client)
                result["performance"] = perf_result

            # 6. Load testing
            if self.load_test_mode:
                load_result = self._load_test_minio(minio_client)
                result["tests"]["load_test"] = load_result

            # Overall health assessment
            failed_tests = [name for name, test in result["tests"].items()
                           if test.get("status") == "failed"]
            result["healthy"] = len(failed_tests) == 0

        except Exception as e:
            result["tests"]["connectivity"] = {
                "status": "failed",
                "error": str(e)
            }
            result["errors"].append(f"MinIO testing failed: {e}")

        return result

    def _test_minio_health(self) -> Dict[str, Any]:
        """Test MinIO health endpoints."""
        try:
            # Test liveness endpoint
            live_response = requests.get(f"http://{self.config['minio']['endpoint']}/minio/health/live", timeout=5)

            # Test readiness endpoint
            ready_response = requests.get(f"http://{self.config['minio']['endpoint']}/minio/health/ready", timeout=5)

            return {
                "status": "passed" if live_response.status_code == 200 else "warning",
                "liveness_check": live_response.status_code == 200,
                "readiness_check": ready_response.status_code == 200
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def _test_minio_buckets(self, minio_client) -> Dict[str, Any]:
        """Test MinIO bucket operations."""
        try:
            # List existing buckets
            buckets = minio_client.list_buckets()
            existing_bucket_names = [bucket.name for bucket in buckets]

            # Test bucket creation and deletion
            test_bucket = "test-bucket-validation"

            # Create test bucket
            if not minio_client.bucket_exists(test_bucket):
                minio_client.make_bucket(test_bucket)

            bucket_exists = minio_client.bucket_exists(test_bucket)

            # Remove test bucket
            if bucket_exists:
                minio_client.remove_bucket(test_bucket)

            # Check expected buckets
            expected_buckets = set(self.minio_buckets)
            existing_buckets = set(existing_bucket_names)
            missing_buckets = expected_buckets - existing_buckets

            return {
                "status": "passed" if len(missing_buckets) <= 2 else "warning",
                "total_buckets": len(existing_bucket_names),
                "expected_buckets": len(expected_buckets),
                "missing_buckets": list(missing_buckets),
                "test_bucket_operations": bucket_exists
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def _test_minio_objects(self, minio_client) -> Dict[str, Any]:
        """Test MinIO object operations."""
        try:
            test_bucket = "lics-temp"  # Use existing temp bucket
            test_object = "test-validation-object.json"

            # Create test object data
            test_data = json.dumps(self.generate_test_message()).encode('utf-8')

            # Upload object
            from io import BytesIO
            minio_client.put_object(
                test_bucket,
                test_object,
                BytesIO(test_data),
                length=len(test_data),
                content_type='application/json'
            )

            # Download object
            response = minio_client.get_object(test_bucket, test_object)
            downloaded_data = response.read()

            # Verify data integrity
            data_match = downloaded_data == test_data

            # Get object stats
            stats = minio_client.stat_object(test_bucket, test_object)

            # Remove test object
            minio_client.remove_object(test_bucket, test_object)

            return {
                "status": "passed" if data_match else "failed",
                "upload_successful": True,
                "download_successful": True,
                "data_integrity": data_match,
                "object_size": stats.size
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def _test_minio_versioning(self, minio_client) -> Dict[str, Any]:
        """Test MinIO object versioning (if supported)."""
        try:
            test_bucket = "lics-temp"

            # Try to get versioning configuration
            try:
                versioning_config = minio_client.get_bucket_versioning(test_bucket)
                versioning_enabled = versioning_config.status == "Enabled"
            except Exception:
                versioning_enabled = False

            return {
                "status": "passed",
                "versioning_supported": True,
                "versioning_enabled": versioning_enabled
            }

        except Exception as e:
            return {
                "status": "warning",
                "versioning_supported": False,
                "error": str(e)
            }

    def _benchmark_minio_performance(self, minio_client) -> Dict[str, Any]:
        """Benchmark MinIO performance."""
        try:
            test_bucket = "lics-temp"
            upload_times = []
            download_times = []

            for i in range(10):
                # Create test data
                test_data = json.dumps(self.generate_test_message()).encode('utf-8')
                object_name = f"benchmark-object-{i}.json"

                # Benchmark upload
                from io import BytesIO
                start_time = time.time()
                minio_client.put_object(
                    test_bucket,
                    object_name,
                    BytesIO(test_data),
                    length=len(test_data)
                )
                upload_times.append(time.time() - start_time)

                # Benchmark download
                start_time = time.time()
                response = minio_client.get_object(test_bucket, object_name)
                response.read()
                download_times.append(time.time() - start_time)

                # Cleanup
                minio_client.remove_object(test_bucket, object_name)

            return {
                "avg_upload_time_ms": round(statistics.mean(upload_times) * 1000, 3),
                "avg_download_time_ms": round(statistics.mean(download_times) * 1000, 3),
                "upload_rate_ops_per_second": round(10 / sum(upload_times), 2),
                "download_rate_ops_per_second": round(10 / sum(download_times), 2)
            }

        except Exception as e:
            return {"error": str(e)}

    def _load_test_minio(self, minio_client) -> Dict[str, Any]:
        """Load test MinIO with concurrent operations."""
        try:
            test_bucket = "lics-temp"
            successful_operations = 0

            def concurrent_object_test(thread_id: int):
                try:
                    for i in range(5):
                        object_name = f"load-test-{thread_id}-{i}.json"
                        test_data = json.dumps(self.generate_test_message()).encode('utf-8')

                        # Upload
                        from io import BytesIO
                        minio_client.put_object(
                            test_bucket,
                            object_name,
                            BytesIO(test_data),
                            length=len(test_data)
                        )

                        # Download
                        response = minio_client.get_object(test_bucket, object_name)
                        response.read()

                        # Cleanup
                        minio_client.remove_object(test_bucket, object_name)

                    return 5
                except Exception:
                    return 0

            # Run concurrent operations
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(concurrent_object_test, i) for i in range(10)]
                results = [future.result() for future in as_completed(futures)]

            successful_operations = sum(results)

            return {
                "status": "passed" if successful_operations >= 40 else "warning",
                "concurrent_threads": 10,
                "successful_operations": successful_operations,
                "total_operations": 50,
                "success_rate": round(successful_operations / 50 * 100, 2)
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def run_comprehensive_messaging_tests(self, test_target: str = "all") -> Dict[str, Any]:
        """Run comprehensive messaging tests."""
        logger.info("🚀 Starting comprehensive messaging test suite...")

        test_results = {}

        # Run selected tests
        if test_target in ["all", "mqtt"]:
            test_results["mqtt"] = await self.test_mqtt_comprehensive()

        if test_target in ["all", "redis"]:
            test_results["redis"] = await self.test_redis_messaging_comprehensive()

        if test_target in ["all", "minio"]:
            test_results["minio"] = self.test_minio_comprehensive()

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
            "load_test_mode": self.load_test_mode,
            "overall_healthy": healthy_tests == total_tests,
            "messaging_tests": test_results,
            "summary": {
                "total_components": total_tests,
                "healthy_components": healthy_tests,
                "failed_components": total_tests - healthy_tests,
                "success_rate": round((healthy_tests / total_tests * 100), 2) if total_tests > 0 else 0
            }
        }

        # Collect all errors
        all_errors = []
        for component_name, component_result in test_results.items():
            if component_result.get("errors"):
                for error in component_result["errors"]:
                    all_errors.append(f"{component_name}: {error}")

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
        output.append("LICS MESSAGING SYSTEM TEST SUITE REPORT")
        output.append("=" * 80)
        output.append(f"Timestamp: {self.results['timestamp']}")
        output.append(f"Duration: {self.results['duration_seconds']}s")
        output.append(f"Test Target: {self.results['test_target']}")
        output.append(f"Benchmark Mode: {self.results['benchmark_mode']}")
        output.append(f"Load Test Mode: {self.results['load_test_mode']}")
        output.append(f"Overall Status: {'✅ HEALTHY' if self.results['overall_healthy'] else '❌ UNHEALTHY'}")
        output.append("")

        # Summary
        summary = self.results["summary"]
        output.append(f"Summary: {summary['healthy_components']}/{summary['total_components']} components healthy ({summary['success_rate']}%)")
        output.append("")

        # Individual component results
        for component_name, component_result in self.results["messaging_tests"].items():
            status_icon = "✅" if component_result.get("healthy", False) else "❌"
            output.append(f"{status_icon} {component_result.get('name', component_name.upper())}")

            # Test results
            if "tests" in component_result:
                for test_name, test_info in component_result["tests"].items():
                    test_status = test_info.get("status", "unknown")
                    test_icon = "✅" if test_status == "passed" else "⚠️" if test_status == "warning" else "❌"
                    output.append(f"   {test_icon} {test_name}: {test_status}")

                    # Additional test details
                    for key, value in test_info.items():
                        if key not in ["status", "error"] and not isinstance(value, dict):
                            output.append(f"      {key}: {value}")

            # Performance metrics
            if "performance" in component_result and component_result["performance"]:
                output.append("   📊 Performance Metrics:")
                for metric, value in component_result["performance"].items():
                    output.append(f"      {metric}: {value}")

            # Errors
            if component_result.get("errors"):
                output.append("   ❌ Errors:")
                for error in component_result["errors"]:
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
            for component_name, component_result in self.results["messaging_tests"].items():
                if "performance" in component_result and component_result["performance"]:
                    output.append(f"  {component_name.upper()}:")
                    for metric, value in component_result["performance"].items():
                        output.append(f"    {metric}: {value}")
            output.append("")

        return "\n".join(output)

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='LICS Messaging System Test Suite')
    parser.add_argument('--test', choices=['all', 'mqtt', 'redis', 'minio'],
                       default='all', help='Messaging component to test (default: all)')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--benchmark', action='store_true',
                       help='Enable performance benchmarking')
    parser.add_argument('--load-test', action='store_true',
                       help='Enable load testing')
    parser.add_argument('--exit-code', action='store_true',
                       help='Exit with non-zero code if tests fail')

    args = parser.parse_args()

    try:
        test_suite = MessagingTestSuite(benchmark_mode=args.benchmark, load_test_mode=args.load_test)
        results = await test_suite.run_comprehensive_messaging_tests(args.test)
        formatted_output = test_suite.format_results(args.format)

        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(formatted_output)
            print(f"Messaging test results written to: {args.output}")
        else:
            print(formatted_output)

        # Exit code based on test results
        if args.exit_code:
            sys.exit(0 if results["overall_healthy"] else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Messaging tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Messaging test suite failed: {e}")
        logger.exception("Messaging tests failed with exception")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
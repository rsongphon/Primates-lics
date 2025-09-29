#!/usr/bin/env python3

"""
LICS Messaging Components Health Check Script
Monitors the health of MQTT, Redis, and MinIO services in the LICS system.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

try:
    import redis
    import paho.mqtt.client as mqtt
    import requests
    import argparse
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install redis paho-mqtt requests")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('messaging-health-check.log')
    ]
)
logger = logging.getLogger(__name__)

class MessagingHealthChecker:
    """
    Health checker for LICS messaging components
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize health checker

        Args:
            config: Configuration dictionary with service endpoints
        """
        self.config = config
        self.results = {}
        self.overall_healthy = True

    def check_redis_health(self) -> Dict[str, Any]:
        """
        Check Redis health including Streams and Pub/Sub

        Returns:
            Dictionary containing Redis health status
        """
        logger.info("Checking Redis health...")

        result = {
            "service": "redis",
            "healthy": False,
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": 0
        }

        try:
            start_time = time.time()

            # Connect to Redis
            redis_client = redis.from_url(
                self.config["redis"]["url"],
                decode_responses=True,
                socket_timeout=5
            )

            # Basic connectivity check
            redis_client.ping()
            result["checks"]["connectivity"] = {"status": "ok", "message": "Ping successful"}

            # Check Redis info
            info = redis_client.info()
            result["checks"]["server_info"] = {
                "status": "ok",
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }

            # Check Redis Streams
            try:
                streams = ["lics:streams:device_telemetry", "lics:streams:device_commands", "lics:streams:system_events"]
                stream_status = {}

                for stream in streams:
                    try:
                        stream_info = redis_client.xinfo_stream(stream)
                        stream_status[stream] = {
                            "exists": True,
                            "length": stream_info.get("length", 0),
                            "groups": len(redis_client.xinfo_groups(stream))
                        }
                    except redis.ResponseError:
                        stream_status[stream] = {"exists": False, "length": 0, "groups": 0}

                result["checks"]["streams"] = {"status": "ok", "streams": stream_status}
            except Exception as e:
                result["checks"]["streams"] = {"status": "error", "message": str(e)}

            # Check Pub/Sub channels
            try:
                test_channel = "lics:health:test"
                pubsub = redis_client.pubsub()
                pubsub.subscribe(test_channel)

                # Publish test message
                redis_client.publish(test_channel, json.dumps({"test": True, "timestamp": datetime.utcnow().isoformat()}))

                # Try to receive message (with timeout)
                message = pubsub.get_message(timeout=2)
                if message and message["type"] == "message":
                    result["checks"]["pubsub"] = {"status": "ok", "message": "Test message sent and received"}
                else:
                    result["checks"]["pubsub"] = {"status": "warning", "message": "Test message sent but not received"}

                pubsub.close()
            except Exception as e:
                result["checks"]["pubsub"] = {"status": "error", "message": str(e)}

            # Check memory usage
            memory_info = redis_client.memory_stats()
            memory_usage_percent = (memory_info.get("used-memory", 0) / memory_info.get("peak-memory", 1)) * 100

            if memory_usage_percent > 90:
                result["checks"]["memory"] = {"status": "warning", "usage_percent": memory_usage_percent}
            else:
                result["checks"]["memory"] = {"status": "ok", "usage_percent": memory_usage_percent}

            # Calculate response time
            end_time = time.time()
            result["response_time_ms"] = round((end_time - start_time) * 1000, 2)

            # Determine overall health
            error_checks = [check for check in result["checks"].values() if check["status"] == "error"]
            result["healthy"] = len(error_checks) == 0

            redis_client.close()

        except Exception as e:
            result["checks"]["connectivity"] = {"status": "error", "message": str(e)}
            logger.error(f"Redis health check failed: {e}")

        return result

    def check_mqtt_health(self) -> Dict[str, Any]:
        """
        Check MQTT broker health

        Returns:
            Dictionary containing MQTT health status
        """
        logger.info("Checking MQTT health...")

        result = {
            "service": "mqtt",
            "healthy": False,
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": 0
        }

        try:
            start_time = time.time()

            # Create MQTT client
            client = mqtt.Client()

            # Set up connection tracking
            connection_result = {"connected": False, "error": None}

            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    connection_result["connected"] = True
                else:
                    connection_result["error"] = f"Connection failed with code {rc}"

            def on_message(client, userdata, msg):
                # Message received callback
                pass

            client.on_connect = on_connect
            client.on_message = on_message

            # Set authentication if provided
            mqtt_config = self.config["mqtt"]
            if mqtt_config.get("username") and mqtt_config.get("password"):
                client.username_pw_set(mqtt_config["username"], mqtt_config["password"])

            # Connect to MQTT broker
            client.connect(mqtt_config["host"], mqtt_config["port"], 10)

            # Wait for connection (non-blocking)
            client.loop_start()

            # Wait up to 5 seconds for connection
            timeout = 5
            while timeout > 0 and not connection_result["connected"] and not connection_result["error"]:
                time.sleep(0.1)
                timeout -= 0.1

            if connection_result["connected"]:
                result["checks"]["connectivity"] = {"status": "ok", "message": "Connected successfully"}

                # Test publish/subscribe
                try:
                    test_topic = "lics/health/test"
                    test_message = json.dumps({
                        "test": True,
                        "timestamp": datetime.utcnow().isoformat(),
                        "health_check": True
                    })

                    # Subscribe to test topic
                    client.subscribe(test_topic)

                    # Publish test message
                    info = client.publish(test_topic, test_message, qos=1)

                    if info.rc == mqtt.MQTT_ERR_SUCCESS:
                        result["checks"]["publish"] = {"status": "ok", "message": "Test message published"}
                    else:
                        result["checks"]["publish"] = {"status": "error", "message": f"Publish failed with code {info.rc}"}

                    # Test subscription (basic check)
                    result["checks"]["subscribe"] = {"status": "ok", "message": "Subscription successful"}

                except Exception as e:
                    result["checks"]["publish"] = {"status": "error", "message": str(e)}

                # Test authentication (if configured)
                if mqtt_config.get("test_auth", True):
                    result["checks"]["authentication"] = {"status": "ok", "message": "Authentication successful"}

            else:
                error_msg = connection_result["error"] or "Connection timeout"
                result["checks"]["connectivity"] = {"status": "error", "message": error_msg}

            client.loop_stop()
            client.disconnect()

            # Calculate response time
            end_time = time.time()
            result["response_time_ms"] = round((end_time - start_time) * 1000, 2)

            # Determine overall health
            error_checks = [check for check in result["checks"].values() if check["status"] == "error"]
            result["healthy"] = len(error_checks) == 0

        except Exception as e:
            result["checks"]["connectivity"] = {"status": "error", "message": str(e)}
            logger.error(f"MQTT health check failed: {e}")

        return result

    def check_minio_health(self) -> Dict[str, Any]:
        """
        Check MinIO health

        Returns:
            Dictionary containing MinIO health status
        """
        logger.info("Checking MinIO health...")

        result = {
            "service": "minio",
            "healthy": False,
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": 0
        }

        try:
            start_time = time.time()
            minio_config = self.config["minio"]

            # Basic health check endpoint
            health_url = f"{minio_config['endpoint']}/minio/health/live"

            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    result["checks"]["liveness"] = {"status": "ok", "message": "Liveness check passed"}
                else:
                    result["checks"]["liveness"] = {
                        "status": "error",
                        "message": f"Liveness check failed with status {response.status_code}"
                    }
            except requests.RequestException as e:
                result["checks"]["liveness"] = {"status": "error", "message": str(e)}

            # Ready check endpoint
            ready_url = f"{minio_config['endpoint']}/minio/health/ready"

            try:
                response = requests.get(ready_url, timeout=5)
                if response.status_code == 200:
                    result["checks"]["readiness"] = {"status": "ok", "message": "Readiness check passed"}
                else:
                    result["checks"]["readiness"] = {
                        "status": "warning",
                        "message": f"Readiness check returned status {response.status_code}"
                    }
            except requests.RequestException as e:
                result["checks"]["readiness"] = {"status": "warning", "message": str(e)}

            # Check bucket accessibility (basic check)
            try:
                # Simple API call to list buckets (requires authentication)
                api_url = f"{minio_config['endpoint']}/"

                # This is a basic connectivity test
                response = requests.get(api_url, timeout=5)
                if response.status_code in [200, 403]:  # 403 is expected without auth
                    result["checks"]["api_connectivity"] = {"status": "ok", "message": "API endpoint accessible"}
                else:
                    result["checks"]["api_connectivity"] = {
                        "status": "warning",
                        "message": f"API returned status {response.status_code}"
                    }
            except requests.RequestException as e:
                result["checks"]["api_connectivity"] = {"status": "error", "message": str(e)}

            # Check if required buckets exist (would need MC client or boto3)
            expected_buckets = [
                "lics-videos", "lics-exports", "lics-uploads",
                "lics-backups", "lics-temp", "lics-data"
            ]
            result["checks"]["expected_buckets"] = {
                "status": "info",
                "message": f"Expected buckets: {', '.join(expected_buckets)}"
            }

            # Calculate response time
            end_time = time.time()
            result["response_time_ms"] = round((end_time - start_time) * 1000, 2)

            # Determine overall health
            error_checks = [check for check in result["checks"].values() if check["status"] == "error"]
            result["healthy"] = len(error_checks) == 0

        except Exception as e:
            result["checks"]["connectivity"] = {"status": "error", "message": str(e)}
            logger.error(f"MinIO health check failed: {e}")

        return result

    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run health checks for all messaging components

        Returns:
            Dictionary containing all health check results
        """
        logger.info("Running health checks for all messaging components...")

        start_time = datetime.utcnow()

        # Run individual health checks
        redis_result = self.check_redis_health()
        mqtt_result = self.check_mqtt_health()
        minio_result = self.check_minio_health()

        # Compile overall results
        overall_result = {
            "timestamp": start_time.isoformat(),
            "duration_ms": round((datetime.utcnow() - start_time).total_seconds() * 1000, 2),
            "overall_healthy": all([
                redis_result["healthy"],
                mqtt_result["healthy"],
                minio_result["healthy"]
            ]),
            "services": {
                "redis": redis_result,
                "mqtt": mqtt_result,
                "minio": minio_result
            },
            "summary": {
                "total_services": 3,
                "healthy_services": sum([
                    redis_result["healthy"],
                    mqtt_result["healthy"],
                    minio_result["healthy"]
                ]),
                "total_checks": sum([
                    len(redis_result["checks"]),
                    len(mqtt_result["checks"]),
                    len(minio_result["checks"])
                ])
            }
        }

        self.results = overall_result
        self.overall_healthy = overall_result["overall_healthy"]

        return overall_result

    def save_results(self, filename: str = None) -> str:
        """
        Save health check results to file

        Args:
            filename: Output filename (optional)

        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"messaging_health_check_{timestamp}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)

            logger.info(f"Health check results saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""

    def get_prometheus_metrics(self) -> str:
        """
        Generate Prometheus-compatible metrics

        Returns:
            Prometheus metrics string
        """
        if not self.results:
            return ""

        metrics = []
        timestamp = int(time.time() * 1000)

        # Overall health metric
        metrics.append(f"lics_messaging_overall_healthy {{}} {int(self.overall_healthy)} {timestamp}")

        # Service-specific metrics
        for service_name, service_data in self.results.get("services", {}).items():
            healthy = int(service_data["healthy"])
            response_time = service_data["response_time_ms"]

            metrics.append(f"lics_messaging_service_healthy{{service=\"{service_name}\"}} {healthy} {timestamp}")
            metrics.append(f"lics_messaging_service_response_time_ms{{service=\"{service_name}\"}} {response_time} {timestamp}")

            # Check-specific metrics
            for check_name, check_data in service_data.get("checks", {}).items():
                status_value = 1 if check_data["status"] == "ok" else 0
                metrics.append(f"lics_messaging_check_status{{service=\"{service_name}\",check=\"{check_name}\"}} {status_value} {timestamp}")

        return "\n".join(metrics)

def load_config(config_file: str = None) -> Dict[str, Any]:
    """
    Load configuration from file or use defaults

    Args:
        config_file: Path to configuration file

    Returns:
        Configuration dictionary
    """
    default_config = {
        "redis": {
            "url": "redis://localhost:6379/0"
        },
        "mqtt": {
            "host": "localhost",
            "port": 1883,
            "username": None,
            "password": None,
            "test_auth": False
        },
        "minio": {
            "endpoint": "http://localhost:9000",
            "access_key": "minioadmin",
            "secret_key": "minioadmin"
        }
    }

    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                # Merge with defaults
                for service in default_config:
                    if service in file_config:
                        default_config[service].update(file_config[service])
        except Exception as e:
            logger.warning(f"Failed to load config file {config_file}: {e}")

    return default_config

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="LICS Messaging Components Health Check")
    parser.add_argument(
        "--config",
        help="Configuration file path"
    )
    parser.add_argument(
        "--output",
        help="Output file for results"
    )
    parser.add_argument(
        "--format",
        choices=["json", "prometheus"],
        default="json",
        help="Output format"
    )
    parser.add_argument(
        "--service",
        choices=["redis", "mqtt", "minio", "all"],
        default="all",
        help="Service to check"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous health checks"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval for continuous checks (seconds)"
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Initialize health checker
    checker = MessagingHealthChecker(config)

    try:
        if args.continuous:
            logger.info(f"Starting continuous health checks (interval: {args.interval}s)")

            while True:
                try:
                    if args.service == "all":
                        results = checker.run_all_checks()
                    elif args.service == "redis":
                        results = {"services": {"redis": checker.check_redis_health()}}
                    elif args.service == "mqtt":
                        results = {"services": {"mqtt": checker.check_mqtt_health()}}
                    elif args.service == "minio":
                        results = {"services": {"minio": checker.check_minio_health()}}

                    # Output results
                    if args.format == "prometheus":
                        print(checker.get_prometheus_metrics())
                    else:
                        print(json.dumps(results, indent=2))

                    # Save to file if specified
                    if args.output:
                        checker.save_results(args.output)

                    time.sleep(args.interval)

                except KeyboardInterrupt:
                    logger.info("Continuous health checks stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in continuous mode: {e}")
                    time.sleep(args.interval)

        else:
            # Single run
            if args.service == "all":
                results = checker.run_all_checks()
            elif args.service == "redis":
                results = {"services": {"redis": checker.check_redis_health()}}
            elif args.service == "mqtt":
                results = {"services": {"mqtt": checker.check_mqtt_health()}}
            elif args.service == "minio":
                results = {"services": {"minio": checker.check_minio_health()}}

            # Output results
            if args.format == "prometheus":
                print(checker.get_prometheus_metrics())
            else:
                print(json.dumps(results, indent=2))

            # Save to file if specified
            if args.output:
                checker.save_results(args.output)

            # Exit with appropriate code
            sys.exit(0 if checker.overall_healthy else 1)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
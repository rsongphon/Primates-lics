#!/usr/bin/env python3

"""
LICS Redis Streams Setup Script
Configures Redis Streams, message patterns, and queue structures for the LICS system.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    import redis
    import argparse
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install redis")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('redis-streams-setup.log')
    ]
)
logger = logging.getLogger(__name__)

class LICSRedisStreamsSetup:
    """
    LICS Redis Streams and Message Queue Setup
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Redis connection and configuration

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client = None
        self.streams_config = self._get_streams_config()
        self.queue_config = self._get_queue_config()
        self.pubsub_config = self._get_pubsub_config()

    def _get_streams_config(self) -> Dict[str, Any]:
        """Get Redis Streams configuration"""
        return {
            "device_telemetry": {
                "stream_name": "lics:streams:device_telemetry",
                "consumer_groups": [
                    "backend_processors",
                    "real_time_monitors",
                    "data_aggregators"
                ],
                "max_length": 100000,  # Keep last 100k messages
                "retention_hours": 24
            },
            "device_commands": {
                "stream_name": "lics:streams:device_commands",
                "consumer_groups": [
                    "command_processors",
                    "audit_loggers"
                ],
                "max_length": 50000,
                "retention_hours": 72
            },
            "device_events": {
                "stream_name": "lics:streams:device_events",
                "consumer_groups": [
                    "event_processors",
                    "notification_handlers",
                    "audit_loggers"
                ],
                "max_length": 25000,
                "retention_hours": 168  # 1 week
            },
            "experiment_events": {
                "stream_name": "lics:streams:experiment_events",
                "consumer_groups": [
                    "experiment_processors",
                    "analytics_engines",
                    "notification_handlers"
                ],
                "max_length": 10000,
                "retention_hours": 720  # 30 days
            },
            "system_events": {
                "stream_name": "lics:streams:system_events",
                "consumer_groups": [
                    "system_monitors",
                    "alert_managers",
                    "audit_loggers"
                ],
                "max_length": 5000,
                "retention_hours": 168  # 1 week
            },
            "task_updates": {
                "stream_name": "lics:streams:task_updates",
                "consumer_groups": [
                    "task_processors",
                    "progress_trackers"
                ],
                "max_length": 20000,
                "retention_hours": 48
            }
        }

    def _get_queue_config(self) -> Dict[str, Any]:
        """Get Redis Queue configuration"""
        return {
            "command_queue": {
                "name": "lics:queues:commands",
                "priority_levels": ["high", "normal", "low"],
                "max_size": 10000,
                "timeout_seconds": 300
            },
            "data_processing": {
                "name": "lics:queues:data_processing",
                "priority_levels": ["urgent", "normal", "batch"],
                "max_size": 50000,
                "timeout_seconds": 600
            },
            "notifications": {
                "name": "lics:queues:notifications",
                "priority_levels": ["immediate", "normal", "scheduled"],
                "max_size": 5000,
                "timeout_seconds": 60
            },
            "exports": {
                "name": "lics:queues:exports",
                "priority_levels": ["priority", "normal"],
                "max_size": 1000,
                "timeout_seconds": 3600
            },
            "maintenance": {
                "name": "lics:queues:maintenance",
                "priority_levels": ["critical", "normal", "scheduled"],
                "max_size": 500,
                "timeout_seconds": 1800
            }
        }

    def _get_pubsub_config(self) -> Dict[str, Any]:
        """Get Pub/Sub channel configuration"""
        return {
            "device_status": {
                "pattern": "lics:devices:*:status",
                "description": "Device status updates"
            },
            "experiment_progress": {
                "pattern": "lics:experiments:*:progress",
                "description": "Experiment progress updates"
            },
            "system_notifications": {
                "pattern": "lics:system:notifications",
                "description": "System-wide notifications"
            },
            "real_time_updates": {
                "pattern": "lics:realtime:*",
                "description": "Real-time UI updates"
            },
            "alerts": {
                "pattern": "lics:alerts:*",
                "description": "System alerts and warnings"
            },
            "user_notifications": {
                "pattern": "lics:users:*:notifications",
                "description": "User-specific notifications"
            }
        }

    def connect(self) -> bool:
        """
        Connect to Redis server

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test connection
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def setup_streams(self) -> bool:
        """
        Set up Redis Streams and consumer groups

        Returns:
            True if setup successful, False otherwise
        """
        logger.info("Setting up Redis Streams...")

        try:
            for stream_id, config in self.streams_config.items():
                stream_name = config["stream_name"]

                # Create stream with initial message if it doesn't exist
                try:
                    self.redis_client.xinfo_stream(stream_name)
                    logger.info(f"Stream {stream_name} already exists")
                except redis.ResponseError:
                    # Stream doesn't exist, create it
                    self.redis_client.xadd(
                        stream_name,
                        {
                            "type": "initialization",
                            "message": f"Stream {stream_id} initialized",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    logger.info(f"Created stream: {stream_name}")

                # Create consumer groups
                for group_name in config["consumer_groups"]:
                    try:
                        self.redis_client.xgroup_create(
                            stream_name,
                            group_name,
                            id="0",
                            mkstream=True
                        )
                        logger.info(f"Created consumer group: {group_name} for stream: {stream_name}")
                    except redis.ResponseError as e:
                        if "BUSYGROUP" in str(e):
                            logger.info(f"Consumer group {group_name} already exists for stream: {stream_name}")
                        else:
                            logger.error(f"Error creating consumer group {group_name}: {e}")

            logger.info("Redis Streams setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup Redis Streams: {e}")
            return False

    def setup_queues(self) -> bool:
        """
        Set up Redis message queues with priority levels

        Returns:
            True if setup successful, False otherwise
        """
        logger.info("Setting up Redis message queues...")

        try:
            for queue_id, config in self.queue_config.items():
                queue_name = config["name"]

                # Create priority-based queue lists
                for priority in config["priority_levels"]:
                    priority_queue_name = f"{queue_name}:{priority}"

                    # Initialize queue metadata
                    metadata_key = f"{priority_queue_name}:metadata"
                    metadata = {
                        "created": datetime.utcnow().isoformat(),
                        "queue_type": queue_id,
                        "priority": priority,
                        "max_size": config["max_size"],
                        "timeout_seconds": config["timeout_seconds"]
                    }

                    self.redis_client.hset(metadata_key, mapping=metadata)

                    # Set expiration for metadata (1 year)
                    self.redis_client.expire(metadata_key, 31536000)

                    logger.info(f"Initialized queue: {priority_queue_name}")

                # Create queue monitoring keys
                monitor_key = f"{queue_name}:monitor"
                monitor_data = {
                    "total_enqueued": 0,
                    "total_processed": 0,
                    "last_activity": datetime.utcnow().isoformat()
                }
                self.redis_client.hset(monitor_key, mapping=monitor_data)
                self.redis_client.expire(monitor_key, 31536000)

            logger.info("Redis message queues setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup Redis queues: {e}")
            return False

    def setup_pubsub_channels(self) -> bool:
        """
        Set up Pub/Sub channel patterns and metadata

        Returns:
            True if setup successful, False otherwise
        """
        logger.info("Setting up Pub/Sub channels...")

        try:
            # Store channel configuration in Redis for reference
            config_key = "lics:config:pubsub_channels"
            self.redis_client.delete(config_key)

            for channel_id, config in self.pubsub_config.items():
                channel_config = {
                    "pattern": config["pattern"],
                    "description": config["description"],
                    "created": datetime.utcnow().isoformat()
                }

                self.redis_client.hset(
                    f"{config_key}:{channel_id}",
                    mapping=channel_config
                )

                # Set expiration (1 year)
                self.redis_client.expire(f"{config_key}:{channel_id}", 31536000)

                logger.info(f"Registered Pub/Sub channel: {config['pattern']}")

            logger.info("Pub/Sub channels setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup Pub/Sub channels: {e}")
            return False

    def setup_monitoring(self) -> bool:
        """
        Set up monitoring and health check keys

        Returns:
            True if setup successful, False otherwise
        """
        logger.info("Setting up monitoring infrastructure...")

        try:
            # System health monitoring
            health_key = "lics:health:redis"
            health_data = {
                "status": "healthy",
                "last_check": datetime.utcnow().isoformat(),
                "streams_count": len(self.streams_config),
                "queues_count": len(self.queue_config),
                "pubsub_channels_count": len(self.pubsub_config)
            }
            self.redis_client.hset(health_key, mapping=health_data)
            self.redis_client.expire(health_key, 300)  # 5 minutes

            # Statistics tracking
            stats_key = "lics:stats:redis"
            stats_data = {
                "setup_time": datetime.utcnow().isoformat(),
                "total_streams": len(self.streams_config),
                "total_consumer_groups": sum(
                    len(config["consumer_groups"])
                    for config in self.streams_config.values()
                ),
                "total_queues": sum(
                    len(config["priority_levels"])
                    for config in self.queue_config.values()
                )
            }
            self.redis_client.hset(stats_key, mapping=stats_data)
            self.redis_client.expire(stats_key, 31536000)  # 1 year

            logger.info("Monitoring infrastructure setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup monitoring: {e}")
            return False

    def create_sample_data(self) -> bool:
        """
        Create sample messages for testing

        Returns:
            True if successful, False otherwise
        """
        logger.info("Creating sample data for testing...")

        try:
            # Sample telemetry data
            telemetry_stream = self.streams_config["device_telemetry"]["stream_name"]
            sample_telemetry = {
                "device_id": "rpi-001",
                "metric": "temperature",
                "value": "23.5",
                "unit": "celsius",
                "timestamp": datetime.utcnow().isoformat(),
                "lab_id": "lab-001"
            }
            self.redis_client.xadd(telemetry_stream, sample_telemetry)

            # Sample command
            command_stream = self.streams_config["device_commands"]["stream_name"]
            sample_command = {
                "command_id": "cmd-123456",
                "device_id": "rpi-001",
                "command": "start_experiment",
                "parameters": json.dumps({"duration": 300, "intensity": "medium"}),
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": "user-001"
            }
            self.redis_client.xadd(command_stream, sample_command)

            # Sample system event
            system_stream = self.streams_config["system_events"]["stream_name"]
            sample_event = {
                "event_type": "system_startup",
                "severity": "info",
                "message": "LICS system started successfully",
                "timestamp": datetime.utcnow().isoformat(),
                "component": "redis_setup"
            }
            self.redis_client.xadd(system_stream, sample_event)

            logger.info("Sample data created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create sample data: {e}")
            return False

    def validate_setup(self) -> bool:
        """
        Validate the Redis setup

        Returns:
            True if validation successful, False otherwise
        """
        logger.info("Validating Redis setup...")

        try:
            validation_results = {
                "streams": 0,
                "consumer_groups": 0,
                "queues": 0,
                "errors": []
            }

            # Validate streams
            for stream_id, config in self.streams_config.items():
                stream_name = config["stream_name"]
                try:
                    info = self.redis_client.xinfo_stream(stream_name)
                    validation_results["streams"] += 1
                    logger.info(f"✓ Stream {stream_name} validated (length: {info['length']})")

                    # Validate consumer groups
                    groups = self.redis_client.xinfo_groups(stream_name)
                    validation_results["consumer_groups"] += len(groups)

                except Exception as e:
                    validation_results["errors"].append(f"Stream {stream_name}: {e}")

            # Validate queues
            for queue_id, config in self.queue_config.items():
                queue_name = config["name"]
                for priority in config["priority_levels"]:
                    priority_queue_name = f"{queue_name}:{priority}"
                    metadata_key = f"{priority_queue_name}:metadata"

                    if self.redis_client.exists(metadata_key):
                        validation_results["queues"] += 1
                    else:
                        validation_results["errors"].append(f"Queue metadata missing: {metadata_key}")

            # Print validation summary
            logger.info("Validation Summary:")
            logger.info(f"  Streams: {validation_results['streams']}")
            logger.info(f"  Consumer Groups: {validation_results['consumer_groups']}")
            logger.info(f"  Queues: {validation_results['queues']}")

            if validation_results["errors"]:
                logger.warning("Validation Errors:")
                for error in validation_results["errors"]:
                    logger.warning(f"  - {error}")
                return False
            else:
                logger.info("✓ All validations passed")
                return True

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    def cleanup_old_data(self, hours: int = 24) -> bool:
        """
        Clean up old data based on retention policies

        Args:
            hours: Hours of data to keep (default: 24)

        Returns:
            True if cleanup successful, False otherwise
        """
        logger.info(f"Cleaning up data older than {hours} hours...")

        try:
            cutoff_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp() * 1000)

            for stream_id, config in self.streams_config.items():
                stream_name = config["stream_name"]
                retention_hours = config.get("retention_hours", 24)

                if hours >= retention_hours:
                    # Use XTRIM to remove old messages
                    try:
                        result = self.redis_client.xtrim(
                            stream_name,
                            maxlen=config["max_length"],
                            approximate=True
                        )
                        logger.info(f"Trimmed {result} messages from {stream_name}")
                    except Exception as e:
                        logger.warning(f"Failed to trim stream {stream_name}: {e}")

            logger.info("Cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a setup report

        Returns:
            Dictionary containing setup information
        """
        logger.info("Generating setup report...")

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "redis_url": self.redis_url,
            "streams": {},
            "queues": {},
            "system_info": {}
        }

        try:
            # Redis server info
            info = self.redis_client.info()
            report["system_info"] = {
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed")
            }

            # Stream information
            for stream_id, config in self.streams_config.items():
                stream_name = config["stream_name"]
                try:
                    stream_info = self.redis_client.xinfo_stream(stream_name)
                    groups_info = self.redis_client.xinfo_groups(stream_name)

                    report["streams"][stream_id] = {
                        "name": stream_name,
                        "length": stream_info["length"],
                        "consumer_groups": len(groups_info),
                        "first_entry": stream_info.get("first-entry"),
                        "last_entry": stream_info.get("last-entry")
                    }
                except Exception as e:
                    report["streams"][stream_id] = {"error": str(e)}

            # Queue information
            for queue_id, config in self.queue_config.items():
                queue_name = config["name"]
                queue_info = {
                    "name": queue_name,
                    "priority_levels": config["priority_levels"],
                    "max_size": config["max_size"]
                }

                # Get queue lengths
                queue_lengths = {}
                for priority in config["priority_levels"]:
                    priority_queue_name = f"{queue_name}:{priority}"
                    length = self.redis_client.llen(priority_queue_name)
                    queue_lengths[priority] = length

                queue_info["current_lengths"] = queue_lengths
                report["queues"][queue_id] = queue_info

        except Exception as e:
            logger.error(f"Failed to generate complete report: {e}")
            report["error"] = str(e)

        return report

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="LICS Redis Streams Setup")
    parser.add_argument(
        "--redis-url",
        default="redis://localhost:6379/0",
        help="Redis connection URL"
    )
    parser.add_argument(
        "--action",
        choices=["setup", "validate", "cleanup", "report", "sample"],
        default="setup",
        help="Action to perform"
    )
    parser.add_argument(
        "--cleanup-hours",
        type=int,
        default=24,
        help="Hours of data to keep during cleanup"
    )

    args = parser.parse_args()

    # Initialize setup class
    setup = LICSRedisStreamsSetup(args.redis_url)

    # Connect to Redis
    if not setup.connect():
        logger.error("Failed to connect to Redis. Exiting.")
        sys.exit(1)

    success = True

    try:
        if args.action == "setup":
            logger.info("Starting full Redis setup...")
            success = (
                setup.setup_streams() and
                setup.setup_queues() and
                setup.setup_pubsub_channels() and
                setup.setup_monitoring()
            )
            if success:
                logger.info("Setup completed successfully")
            else:
                logger.error("Setup failed")

        elif args.action == "validate":
            success = setup.validate_setup()

        elif args.action == "cleanup":
            success = setup.cleanup_old_data(args.cleanup_hours)

        elif args.action == "report":
            report = setup.generate_report()
            print(json.dumps(report, indent=2))

        elif args.action == "sample":
            success = setup.create_sample_data()

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        success = False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        success = False

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3

"""
LICS Redis Pub/Sub Configuration Script
Sets up and manages Redis Pub/Sub channels for real-time communication in the LICS system.
"""

import os
import sys
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

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
        logging.FileHandler('redis-pubsub-config.log')
    ]
)
logger = logging.getLogger(__name__)

class LICSRedisPubSubManager:
    """
    LICS Redis Pub/Sub Manager for real-time communication
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Redis Pub/Sub Manager

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client = None
        self.pubsub = None
        self.subscribers: Dict[str, threading.Thread] = {}
        self.running_subscribers: Dict[str, bool] = {}
        self.channel_config = self._get_channel_config()

    def _get_channel_config(self) -> Dict[str, Any]:
        """Get Pub/Sub channel configuration"""
        return {
            "device_status": {
                "channels": [
                    "lics:devices:*:status",
                    "lics:devices:*:heartbeat",
                    "lics:devices:*:connection"
                ],
                "description": "Device status and connectivity updates",
                "message_types": ["status_update", "heartbeat", "connection_change"],
                "ttl_seconds": 300,
                "max_subscribers": 50
            },
            "experiment_progress": {
                "channels": [
                    "lics:experiments:*:progress",
                    "lics:experiments:*:events",
                    "lics:experiments:*:results"
                ],
                "description": "Experiment progress and results",
                "message_types": ["progress_update", "experiment_event", "result_data"],
                "ttl_seconds": 3600,
                "max_subscribers": 20
            },
            "system_notifications": {
                "channels": [
                    "lics:system:notifications",
                    "lics:system:alerts",
                    "lics:system:maintenance"
                ],
                "description": "System-wide notifications and alerts",
                "message_types": ["notification", "alert", "maintenance_notice"],
                "ttl_seconds": 1800,
                "max_subscribers": 100
            },
            "real_time_updates": {
                "channels": [
                    "lics:realtime:dashboard",
                    "lics:realtime:monitoring",
                    "lics:realtime:analytics"
                ],
                "description": "Real-time UI updates and analytics",
                "message_types": ["dashboard_update", "metrics_update", "analytics_data"],
                "ttl_seconds": 60,
                "max_subscribers": 200
            },
            "user_notifications": {
                "channels": [
                    "lics:users:*:notifications",
                    "lics:users:*:messages",
                    "lics:users:*:alerts"
                ],
                "description": "User-specific notifications and messages",
                "message_types": ["user_notification", "private_message", "user_alert"],
                "ttl_seconds": 86400,  # 24 hours
                "max_subscribers": 500
            },
            "command_responses": {
                "channels": [
                    "lics:commands:*:responses",
                    "lics:commands:*:acks",
                    "lics:commands:*:errors"
                ],
                "description": "Command responses and acknowledgments",
                "message_types": ["command_response", "command_ack", "command_error"],
                "ttl_seconds": 600,
                "max_subscribers": 30
            },
            "data_updates": {
                "channels": [
                    "lics:data:*:updates",
                    "lics:data:*:processed",
                    "lics:data:*:exported"
                ],
                "description": "Data processing and export updates",
                "message_types": ["data_update", "processing_complete", "export_ready"],
                "ttl_seconds": 3600,
                "max_subscribers": 25
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
            self.pubsub = self.redis_client.pubsub()
            logger.info("Successfully connected to Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def setup_channel_metadata(self) -> bool:
        """
        Set up channel metadata in Redis

        Returns:
            True if setup successful, False otherwise
        """
        logger.info("Setting up Pub/Sub channel metadata...")

        try:
            for category, config in self.channel_config.items():
                # Store channel configuration
                config_key = f"lics:config:pubsub:{category}"
                config_data = {
                    "description": config["description"],
                    "channels": json.dumps(config["channels"]),
                    "message_types": json.dumps(config["message_types"]),
                    "ttl_seconds": config["ttl_seconds"],
                    "max_subscribers": config["max_subscribers"],
                    "created": datetime.utcnow().isoformat()
                }

                self.redis_client.hset(config_key, mapping=config_data)
                self.redis_client.expire(config_key, 31536000)  # 1 year

                # Initialize statistics
                stats_key = f"lics:stats:pubsub:{category}"
                stats_data = {
                    "total_published": 0,
                    "total_subscribers": 0,
                    "last_activity": datetime.utcnow().isoformat()
                }

                self.redis_client.hset(stats_key, mapping=stats_data)
                self.redis_client.expire(stats_key, 31536000)

                logger.info(f"Set up metadata for category: {category}")

            logger.info("Pub/Sub channel metadata setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup channel metadata: {e}")
            return False

    def publish_message(self, channel: str, message: Dict[str, Any],
                       message_type: str = "general") -> bool:
        """
        Publish a message to a channel

        Args:
            channel: Channel name
            message: Message data
            message_type: Type of message

        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Prepare message with metadata
            full_message = {
                "type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": message,
                "channel": channel
            }

            # Publish message
            result = self.redis_client.publish(channel, json.dumps(full_message))

            # Update statistics
            self._update_publish_stats(channel, message_type)

            logger.debug(f"Published message to {channel}, {result} subscribers received")
            return True

        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {e}")
            return False

    def subscribe_to_pattern(self, pattern: str, callback: Callable[[Dict], None],
                           subscriber_id: str = None) -> bool:
        """
        Subscribe to a channel pattern

        Args:
            pattern: Channel pattern to subscribe to
            callback: Function to call when message received
            subscriber_id: Unique identifier for this subscriber

        Returns:
            True if subscription successful, False otherwise
        """
        try:
            if subscriber_id is None:
                subscriber_id = f"subscriber_{int(time.time())}"

            # Create new Redis client for this subscriber
            subscriber_client = redis.from_url(self.redis_url, decode_responses=True)
            subscriber_pubsub = subscriber_client.pubsub()

            # Subscribe to pattern
            subscriber_pubsub.psubscribe(pattern)

            # Create thread for listening
            def listen_thread():
                logger.info(f"Subscriber {subscriber_id} listening to pattern: {pattern}")
                self.running_subscribers[subscriber_id] = True

                try:
                    for message in subscriber_pubsub.listen():
                        if not self.running_subscribers.get(subscriber_id, False):
                            break

                        if message['type'] == 'pmessage':
                            try:
                                # Parse message data
                                message_data = json.loads(message['data'])
                                message_data['pattern'] = message['pattern']
                                message_data['channel'] = message['channel']

                                # Call callback function
                                callback(message_data)

                                # Update statistics
                                self._update_subscribe_stats(message['channel'])

                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in message from {message['channel']}")
                            except Exception as e:
                                logger.error(f"Error in callback for {pattern}: {e}")

                except Exception as e:
                    logger.error(f"Error in subscriber {subscriber_id}: {e}")
                finally:
                    subscriber_pubsub.close()
                    subscriber_client.close()
                    logger.info(f"Subscriber {subscriber_id} stopped")

            # Start listening thread
            thread = threading.Thread(target=listen_thread, daemon=True)
            thread.start()

            self.subscribers[subscriber_id] = thread
            logger.info(f"Started subscriber {subscriber_id} for pattern: {pattern}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to pattern {pattern}: {e}")
            return False

    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        Unsubscribe a specific subscriber

        Args:
            subscriber_id: ID of subscriber to stop

        Returns:
            True if unsubscribed successfully, False otherwise
        """
        try:
            if subscriber_id in self.running_subscribers:
                self.running_subscribers[subscriber_id] = False

            if subscriber_id in self.subscribers:
                thread = self.subscribers[subscriber_id]
                thread.join(timeout=5)
                del self.subscribers[subscriber_id]

            logger.info(f"Unsubscribed subscriber: {subscriber_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unsubscribe {subscriber_id}: {e}")
            return False

    def unsubscribe_all(self) -> bool:
        """
        Unsubscribe all active subscribers

        Returns:
            True if all unsubscribed successfully, False otherwise
        """
        try:
            logger.info("Unsubscribing all active subscribers...")

            # Stop all subscribers
            for subscriber_id in list(self.subscribers.keys()):
                self.unsubscribe(subscriber_id)

            logger.info("All subscribers unsubscribed")
            return True

        except Exception as e:
            logger.error(f"Failed to unsubscribe all: {e}")
            return False

    def _update_publish_stats(self, channel: str, message_type: str):
        """Update publishing statistics"""
        try:
            # Find category for this channel
            category = self._get_category_for_channel(channel)
            if category:
                stats_key = f"lics:stats:pubsub:{category}"
                self.redis_client.hincrby(stats_key, "total_published", 1)
                self.redis_client.hset(stats_key, "last_activity", datetime.utcnow().isoformat())

            # Update channel-specific stats
            channel_stats_key = f"lics:stats:channels:{channel}"
            self.redis_client.hincrby(channel_stats_key, "messages_published", 1)
            self.redis_client.hset(channel_stats_key, "last_published", datetime.utcnow().isoformat())
            self.redis_client.expire(channel_stats_key, 86400)  # 24 hours

        except Exception as e:
            logger.warning(f"Failed to update publish stats: {e}")

    def _update_subscribe_stats(self, channel: str):
        """Update subscription statistics"""
        try:
            category = self._get_category_for_channel(channel)
            if category:
                stats_key = f"lics:stats:pubsub:{category}"
                self.redis_client.hset(stats_key, "last_activity", datetime.utcnow().isoformat())

            # Update channel-specific stats
            channel_stats_key = f"lics:stats:channels:{channel}"
            self.redis_client.hincrby(channel_stats_key, "messages_received", 1)
            self.redis_client.hset(channel_stats_key, "last_received", datetime.utcnow().isoformat())
            self.redis_client.expire(channel_stats_key, 86400)

        except Exception as e:
            logger.warning(f"Failed to update subscribe stats: {e}")

    def _get_category_for_channel(self, channel: str) -> Optional[str]:
        """Find category that matches a channel"""
        for category, config in self.channel_config.items():
            for pattern in config["channels"]:
                # Simple pattern matching (would need more sophisticated matching for wildcards)
                if pattern.replace("*", "") in channel or channel.startswith(pattern.replace("*", "")):
                    return category
        return None

    def get_active_channels(self) -> List[str]:
        """
        Get list of currently active channels

        Returns:
            List of active channel names
        """
        try:
            # Get all keys matching channel stats pattern
            pattern = "lics:stats:channels:*"
            keys = self.redis_client.keys(pattern)

            # Extract channel names
            channels = [key.replace("lics:stats:channels:", "") for key in keys]
            return channels

        except Exception as e:
            logger.error(f"Failed to get active channels: {e}")
            return []

    def get_channel_stats(self, channel: str = None) -> Dict[str, Any]:
        """
        Get statistics for channels

        Args:
            channel: Specific channel name, or None for all channels

        Returns:
            Dictionary containing channel statistics
        """
        try:
            if channel:
                # Get stats for specific channel
                stats_key = f"lics:stats:channels:{channel}"
                stats = self.redis_client.hgetall(stats_key)
                return {channel: stats} if stats else {}
            else:
                # Get stats for all channels
                all_stats = {}
                active_channels = self.get_active_channels()

                for ch in active_channels:
                    stats_key = f"lics:stats:channels:{ch}"
                    stats = self.redis_client.hgetall(stats_key)
                    if stats:
                        all_stats[ch] = stats

                return all_stats

        except Exception as e:
            logger.error(f"Failed to get channel stats: {e}")
            return {}

    def cleanup_old_stats(self, hours: int = 24) -> bool:
        """
        Clean up old channel statistics

        Args:
            hours: Age threshold in hours

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            logger.info(f"Cleaning up channel stats older than {hours} hours...")

            cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
            active_channels = self.get_active_channels()
            cleaned_count = 0

            for channel in active_channels:
                stats_key = f"lics:stats:channels:{channel}"
                stats = self.redis_client.hgetall(stats_key)

                if stats and "last_activity" in stats:
                    try:
                        last_activity = datetime.fromisoformat(stats["last_activity"]).timestamp()
                        if last_activity < cutoff_time:
                            self.redis_client.delete(stats_key)
                            cleaned_count += 1
                    except ValueError:
                        # Invalid timestamp, remove it
                        self.redis_client.delete(stats_key)
                        cleaned_count += 1

            logger.info(f"Cleaned up {cleaned_count} old channel stats")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup old stats: {e}")
            return False

    def test_pubsub(self) -> bool:
        """
        Test Pub/Sub functionality with sample messages

        Returns:
            True if test successful, False otherwise
        """
        logger.info("Testing Pub/Sub functionality...")

        try:
            test_results = []

            # Test each category
            for category, config in self.channel_config.items():
                test_channel = config["channels"][0].replace("*", "test")
                test_message = {
                    "test": True,
                    "category": category,
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Publish test message
                success = self.publish_message(
                    test_channel,
                    test_message,
                    config["message_types"][0]
                )

                test_results.append(success)
                logger.info(f"Test message for {category}: {'✓' if success else '✗'}")

            # Overall test result
            overall_success = all(test_results)
            logger.info(f"Pub/Sub test {'PASSED' if overall_success else 'FAILED'}")
            return overall_success

        except Exception as e:
            logger.error(f"Pub/Sub test failed: {e}")
            return False

def sample_callback(message: Dict[str, Any]):
    """Sample callback function for testing"""
    logger.info(f"Received message: {message.get('type', 'unknown')} from {message.get('channel', 'unknown')}")

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="LICS Redis Pub/Sub Configuration")
    parser.add_argument(
        "--redis-url",
        default="redis://localhost:6379/0",
        help="Redis connection URL"
    )
    parser.add_argument(
        "--action",
        choices=["setup", "test", "stats", "cleanup", "listen"],
        default="setup",
        help="Action to perform"
    )
    parser.add_argument(
        "--pattern",
        help="Pattern to listen to (for listen action)"
    )
    parser.add_argument(
        "--cleanup-hours",
        type=int,
        default=24,
        help="Hours threshold for cleanup"
    )

    args = parser.parse_args()

    # Initialize manager
    manager = LICSRedisPubSubManager(args.redis_url)

    # Connect to Redis
    if not manager.connect():
        logger.error("Failed to connect to Redis. Exiting.")
        sys.exit(1)

    success = True

    try:
        if args.action == "setup":
            logger.info("Setting up Pub/Sub channels...")
            success = manager.setup_channel_metadata()

        elif args.action == "test":
            success = manager.test_pubsub()

        elif args.action == "stats":
            stats = manager.get_channel_stats()
            print(json.dumps(stats, indent=2))

        elif args.action == "cleanup":
            success = manager.cleanup_old_stats(args.cleanup_hours)

        elif args.action == "listen":
            if not args.pattern:
                logger.error("Pattern required for listen action")
                sys.exit(1)

            logger.info(f"Listening to pattern: {args.pattern}")
            manager.subscribe_to_pattern(args.pattern, sample_callback, "test_subscriber")

            try:
                # Listen for 30 seconds
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Stopping listener...")

            manager.unsubscribe_all()

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        manager.unsubscribe_all()
        success = False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        success = False

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
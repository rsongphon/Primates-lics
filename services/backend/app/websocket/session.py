"""
LICS WebSocket Session Management

Redis-backed session storage and connection tracking for WebSocket connections.
Follows Documentation.md Section 5.4 session management patterns.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set
from redis import asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages WebSocket sessions with Redis backend.

    Provides connection tracking, presence management, and session data storage.
    """

    def __init__(self):
        """Initialize session manager with Redis connection."""
        self._redis: Optional[aioredis.Redis] = None
        self._prefix = "ws:session:"
        self._connection_prefix = "ws:connection:"
        self._user_connections_prefix = "ws:user_connections:"
        self._presence_prefix = "ws:presence:"

    async def get_redis(self) -> aioredis.Redis:
        """
        Get or create Redis connection.

        Returns:
            Redis client instance
        """
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    # ===== Session Management =====

    async def save_session(self, sid: str, session_data: Dict[str, Any]) -> bool:
        """
        Save session data for a connection.

        Args:
            sid: Socket session ID
            session_data: Session data dictionary

        Returns:
            True if saved successfully
        """
        try:
            redis = await self.get_redis()
            key = f"{self._prefix}{sid}"

            # Convert session data to JSON
            session_json = json.dumps(session_data, default=str)

            # Store with expiration (24 hours)
            await redis.setex(key, 86400, session_json)

            logger.debug(f"Session saved for {sid}")
            return True

        except Exception as e:
            logger.error(f"Error saving session for {sid}: {e}")
            return False

    async def get_session(self, sid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data for a connection.

        Args:
            sid: Socket session ID

        Returns:
            Session data dictionary or None
        """
        try:
            redis = await self.get_redis()
            key = f"{self._prefix}{sid}"

            session_json = await redis.get(key)
            if session_json:
                return json.loads(session_json)

            return None

        except Exception as e:
            logger.error(f"Error getting session for {sid}: {e}")
            return None

    async def update_session(self, sid: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data for a connection.

        Args:
            sid: Socket session ID
            updates: Dictionary of updates to apply

        Returns:
            True if updated successfully
        """
        try:
            # Get existing session
            session = await self.get_session(sid)
            if session is None:
                session = {}

            # Apply updates
            session.update(updates)

            # Save updated session
            return await self.save_session(sid, session)

        except Exception as e:
            logger.error(f"Error updating session for {sid}: {e}")
            return False

    async def delete_session(self, sid: str) -> bool:
        """
        Delete session data for a connection.

        Args:
            sid: Socket session ID

        Returns:
            True if deleted successfully
        """
        try:
            redis = await self.get_redis()
            key = f"{self._prefix}{sid}"

            await redis.delete(key)
            logger.debug(f"Session deleted for {sid}")
            return True

        except Exception as e:
            logger.error(f"Error deleting session for {sid}: {e}")
            return False

    # ===== Connection Tracking =====

    async def track_connection(self, sid: str, user_id: str, connection_info: Dict[str, Any]) -> bool:
        """
        Track a WebSocket connection for a user.

        Args:
            sid: Socket session ID
            user_id: User identifier
            connection_info: Connection metadata

        Returns:
            True if tracked successfully
        """
        try:
            redis = await self.get_redis()

            # Store connection info
            connection_key = f"{self._connection_prefix}{sid}"
            connection_data = {
                "user_id": user_id,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                **connection_info
            }
            connection_json = json.dumps(connection_data, default=str)
            await redis.setex(connection_key, 86400, connection_json)

            # Add to user's connection set
            user_connections_key = f"{self._user_connections_prefix}{user_id}"
            await redis.sadd(user_connections_key, sid)
            await redis.expire(user_connections_key, 86400)

            logger.debug(f"Connection tracked: {sid} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error tracking connection {sid}: {e}")
            return False

    async def untrack_connection(self, sid: str, user_id: Optional[str] = None) -> bool:
        """
        Remove tracking for a disconnected WebSocket connection.

        Args:
            sid: Socket session ID
            user_id: User identifier (optional, will be fetched if not provided)

        Returns:
            True if untracked successfully
        """
        try:
            redis = await self.get_redis()

            # Get user_id from connection if not provided
            if user_id is None:
                connection_key = f"{self._connection_prefix}{sid}"
                connection_json = await redis.get(connection_key)
                if connection_json:
                    connection_data = json.loads(connection_json)
                    user_id = connection_data.get("user_id")

            if user_id:
                # Remove from user's connection set
                user_connections_key = f"{self._user_connections_prefix}{user_id}"
                await redis.srem(user_connections_key, sid)

            # Delete connection info
            connection_key = f"{self._connection_prefix}{sid}"
            await redis.delete(connection_key)

            logger.debug(f"Connection untracked: {sid}")
            return True

        except Exception as e:
            logger.error(f"Error untracking connection {sid}: {e}")
            return False

    async def get_user_connections(self, user_id: str) -> Set[str]:
        """
        Get all active connections for a user.

        Args:
            user_id: User identifier

        Returns:
            Set of socket session IDs
        """
        try:
            redis = await self.get_redis()
            user_connections_key = f"{self._user_connections_prefix}{user_id}"

            connections = await redis.smembers(user_connections_key)
            return connections if connections else set()

        except Exception as e:
            logger.error(f"Error getting connections for user {user_id}: {e}")
            return set()

    async def get_connection_info(self, sid: str) -> Optional[Dict[str, Any]]:
        """
        Get connection information for a socket.

        Args:
            sid: Socket session ID

        Returns:
            Connection info dictionary or None
        """
        try:
            redis = await self.get_redis()
            connection_key = f"{self._connection_prefix}{sid}"

            connection_json = await redis.get(connection_key)
            if connection_json:
                return json.loads(connection_json)

            return None

        except Exception as e:
            logger.error(f"Error getting connection info for {sid}: {e}")
            return None

    # ===== Presence Tracking =====

    async def set_user_presence(
        self,
        user_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Set user presence status.

        Args:
            user_id: User identifier
            status: Presence status ("online", "offline", "away", "busy")
            metadata: Additional presence metadata

        Returns:
            True if set successfully
        """
        try:
            redis = await self.get_redis()
            presence_key = f"{self._presence_prefix}{user_id}"

            presence_data = {
                "status": status,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                **(metadata or {})
            }
            presence_json = json.dumps(presence_data, default=str)

            # Store with 5-minute expiration (will be refreshed by heartbeat)
            await redis.setex(presence_key, 300, presence_json)

            logger.debug(f"Presence set for user {user_id}: {status}")
            return True

        except Exception as e:
            logger.error(f"Error setting presence for user {user_id}: {e}")
            return False

    async def get_user_presence(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user presence status.

        Args:
            user_id: User identifier

        Returns:
            Presence data dictionary or None (offline)
        """
        try:
            redis = await self.get_redis()
            presence_key = f"{self._presence_prefix}{user_id}"

            presence_json = await redis.get(presence_key)
            if presence_json:
                return json.loads(presence_json)

            return {"status": "offline"}

        except Exception as e:
            logger.error(f"Error getting presence for user {user_id}: {e}")
            return {"status": "offline"}

    async def get_online_users(self, user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get presence status for multiple users.

        Args:
            user_ids: List of user identifiers

        Returns:
            Dictionary mapping user_id to presence data
        """
        try:
            redis = await self.get_redis()
            presence_data = {}

            # Batch get presence data
            pipeline = redis.pipeline()
            for user_id in user_ids:
                presence_key = f"{self._presence_prefix}{user_id}"
                pipeline.get(presence_key)

            results = await pipeline.execute()

            for user_id, presence_json in zip(user_ids, results):
                if presence_json:
                    presence_data[user_id] = json.loads(presence_json)
                else:
                    presence_data[user_id] = {"status": "offline"}

            return presence_data

        except Exception as e:
            logger.error(f"Error getting online users: {e}")
            return {}

    async def clear_user_presence(self, user_id: str) -> bool:
        """
        Clear user presence (set to offline).

        Args:
            user_id: User identifier

        Returns:
            True if cleared successfully
        """
        try:
            redis = await self.get_redis()
            presence_key = f"{self._presence_prefix}{user_id}"

            await redis.delete(presence_key)
            logger.debug(f"Presence cleared for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error clearing presence for user {user_id}: {e}")
            return False


# Global session manager instance
session_manager = SessionManager()

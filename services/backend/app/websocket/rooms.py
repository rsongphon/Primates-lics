"""
LICS WebSocket Room Management

Room-based communication patterns for efficient message routing.
Follows Documentation.md Section 5.4 room-based architecture.
"""

from typing import Optional, List, Set
from redis import asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger
from app.websocket.events import RoomPattern

logger = get_logger(__name__)


class RoomManager:
    """
    Manages WebSocket room memberships and access control.

    Provides room joining/leaving, membership tracking, and permission checks.
    """

    def __init__(self):
        """Initialize room manager with Redis connection."""
        self._redis: Optional[aioredis.Redis] = None
        self._room_members_prefix = "ws:room:members:"
        self._user_rooms_prefix = "ws:user:rooms:"

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

    # ===== Room Membership =====

    async def add_to_room(self, sid: str, room: str, user_id: Optional[str] = None) -> bool:
        """
        Add a socket to a room.

        Args:
            sid: Socket session ID
            room: Room name
            user_id: Optional user identifier for tracking

        Returns:
            True if added successfully
        """
        try:
            redis = await self.get_redis()

            # Add socket to room members set
            room_key = f"{self._room_members_prefix}{room}"
            await redis.sadd(room_key, sid)
            await redis.expire(room_key, 86400)  # 24 hour expiration

            # Track user's room memberships
            if user_id:
                user_rooms_key = f"{self._user_rooms_prefix}{user_id}"
                await redis.sadd(user_rooms_key, room)
                await redis.expire(user_rooms_key, 86400)

            logger.debug(f"Socket {sid} added to room {room}")
            return True

        except Exception as e:
            logger.error(f"Error adding {sid} to room {room}: {e}")
            return False

    async def remove_from_room(self, sid: str, room: str, user_id: Optional[str] = None) -> bool:
        """
        Remove a socket from a room.

        Args:
            sid: Socket session ID
            room: Room name
            user_id: Optional user identifier for tracking

        Returns:
            True if removed successfully
        """
        try:
            redis = await self.get_redis()

            # Remove socket from room members set
            room_key = f"{self._room_members_prefix}{room}"
            await redis.srem(room_key, sid)

            # Remove from user's room tracking
            if user_id:
                user_rooms_key = f"{self._user_rooms_prefix}{user_id}"
                await redis.srem(user_rooms_key, room)

            logger.debug(f"Socket {sid} removed from room {room}")
            return True

        except Exception as e:
            logger.error(f"Error removing {sid} from room {room}: {e}")
            return False

    async def get_room_members(self, room: str) -> Set[str]:
        """
        Get all socket IDs in a room.

        Args:
            room: Room name

        Returns:
            Set of socket session IDs
        """
        try:
            redis = await self.get_redis()
            room_key = f"{self._room_members_prefix}{room}"

            members = await redis.smembers(room_key)
            return members if members else set()

        except Exception as e:
            logger.error(f"Error getting members for room {room}: {e}")
            return set()

    async def get_user_rooms(self, user_id: str) -> Set[str]:
        """
        Get all rooms a user is in.

        Args:
            user_id: User identifier

        Returns:
            Set of room names
        """
        try:
            redis = await self.get_redis()
            user_rooms_key = f"{self._user_rooms_prefix}{user_id}"

            rooms = await redis.smembers(user_rooms_key)
            return rooms if rooms else set()

        except Exception as e:
            logger.error(f"Error getting rooms for user {user_id}: {e}")
            return set()

    async def get_room_count(self, room: str) -> int:
        """
        Get number of members in a room.

        Args:
            room: Room name

        Returns:
            Number of members
        """
        try:
            redis = await self.get_redis()
            room_key = f"{self._room_members_prefix}{room}"

            count = await redis.scard(room_key)
            return count or 0

        except Exception as e:
            logger.error(f"Error getting room count for {room}: {e}")
            return 0

    async def clear_room(self, room: str) -> bool:
        """
        Remove all members from a room.

        Args:
            room: Room name

        Returns:
            True if cleared successfully
        """
        try:
            redis = await self.get_redis()
            room_key = f"{self._room_members_prefix}{room}"

            await redis.delete(room_key)
            logger.debug(f"Room {room} cleared")
            return True

        except Exception as e:
            logger.error(f"Error clearing room {room}: {e}")
            return False

    # ===== Room Access Control =====

    async def can_join_device_room(self, user_id: str, device_id: str, organization_id: str) -> bool:
        """
        Check if user can join a device room.

        Args:
            user_id: User identifier
            device_id: Device identifier
            organization_id: Organization identifier

        Returns:
            True if user has access
        """
        # TODO: Implement proper access control
        # For now, allow all authenticated users
        # In production, check:
        # - User's organization matches device's organization
        # - User has "device:view" permission
        return True

    async def can_join_experiment_room(self, user_id: str, experiment_id: str, organization_id: str) -> bool:
        """
        Check if user can join an experiment room.

        Args:
            user_id: User identifier
            experiment_id: Experiment identifier
            organization_id: Organization identifier

        Returns:
            True if user has access
        """
        # TODO: Implement proper access control
        # For now, allow all authenticated users
        # In production, check:
        # - User's organization matches experiment's organization
        # - User has "experiment:view" permission
        return True

    async def can_join_org_room(self, user_id: str, org_id: str, user_org_id: str) -> bool:
        """
        Check if user can join an organization room.

        Args:
            user_id: User identifier
            org_id: Target organization identifier
            user_org_id: User's organization identifier

        Returns:
            True if user has access
        """
        # User must belong to the organization
        return org_id == user_org_id

    # ===== Helper Methods =====

    async def cleanup_user_rooms(self, user_id: str) -> bool:
        """
        Clean up all room memberships for a user (on disconnect).

        Args:
            user_id: User identifier

        Returns:
            True if cleaned up successfully
        """
        try:
            redis = await self.get_redis()

            # Get all rooms user is in
            rooms = await self.get_user_rooms(user_id)

            # Remove from all rooms
            pipeline = redis.pipeline()
            for room in rooms:
                room_key = f"{self._room_members_prefix}{room}"
                # Note: We can't remove specific sids without knowing them,
                # so this is just cleanup of the tracking

            # Delete user's room tracking
            user_rooms_key = f"{self._user_rooms_prefix}{user_id}"
            pipeline.delete(user_rooms_key)

            await pipeline.execute()

            logger.debug(f"Cleaned up rooms for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up rooms for user {user_id}: {e}")
            return False

    # ===== Room Name Generators =====

    @staticmethod
    def device_room(device_id: str) -> str:
        """Generate device room name."""
        return RoomPattern.device(device_id)

    @staticmethod
    def experiment_room(experiment_id: str) -> str:
        """Generate experiment room name."""
        return RoomPattern.experiment(experiment_id)

    @staticmethod
    def organization_room(org_id: str) -> str:
        """Generate organization room name."""
        return RoomPattern.organization(org_id)

    @staticmethod
    def user_room(user_id: str) -> str:
        """Generate user notification room name."""
        return RoomPattern.user(user_id)

    @staticmethod
    def task_room(task_id: str) -> str:
        """Generate task room name."""
        return RoomPattern.task(task_id)

    @staticmethod
    def task_execution_room(execution_id: str) -> str:
        """Generate task execution room name."""
        return RoomPattern.task_execution(execution_id)

    @staticmethod
    def broadcast_room() -> str:
        """Generate broadcast room name."""
        return RoomPattern.BROADCAST

    @staticmethod
    def organization_broadcast_room(org_id: str) -> str:
        """Generate organization-specific broadcast room name."""
        return RoomPattern.BROADCAST_ORG.format(org_id=org_id)


# Global room manager instance
room_manager = RoomManager()

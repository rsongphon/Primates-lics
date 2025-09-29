"""
LICS Backend Base Repository

Base repository pattern implementation providing common CRUD operations
and query utilities for all domain entities. Follows Documentation.md
Section 5.1 Repository Pattern guidelines.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union

from sqlalchemy import and_, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import Select

from app.core.database import Base
from app.core.logging import get_logger, PerformanceLogger

logger = get_logger(__name__)
perf_logger = PerformanceLogger(logger)

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType], ABC):
    """
    Base repository class providing common CRUD operations.

    This abstract base class defines the interface for all repositories
    and provides default implementations for common database operations.
    """

    def __init__(self, model: Type[ModelType], db_session: AsyncSession):
        """
        Initialize repository with model class and database session.

        Args:
            model: SQLAlchemy model class
            db_session: Async database session
        """
        self.model = model
        self.db_session = db_session

    # ===== READ OPERATIONS =====

    async def get_by_id(self, entity_id: Union[int, str, uuid.UUID]) -> Optional[ModelType]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity if found, None otherwise
        """
        with perf_logger.log_execution_time(f"get_{self.model.__name__.lower()}_by_id"):
            result = await self.db_session.execute(
                select(self.model).where(self.model.id == entity_id)
            )
            return result.scalar_one_or_none()

    async def get_by_ids(self, entity_ids: List[Union[int, str, uuid.UUID]]) -> List[ModelType]:
        """
        Get multiple entities by IDs.

        Args:
            entity_ids: List of entity identifiers

        Returns:
            List of found entities
        """
        if not entity_ids:
            return []

        with perf_logger.log_execution_time(f"get_{self.model.__name__.lower()}_by_ids"):
            result = await self.db_session.execute(
                select(self.model).where(self.model.id.in_(entity_ids))
            )
            return list(result.scalars().all())

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        Get all entities with pagination and ordering.

        Args:
            skip: Number of entities to skip
            limit: Maximum number of entities to return
            order_by: Field name to order by (defaults to 'id')
            order_desc: Whether to order in descending order

        Returns:
            List of entities
        """
        with perf_logger.log_execution_time(f"get_all_{self.model.__name__.lower()}"):
            query = select(self.model)

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(order_column)
            elif hasattr(self.model, 'id'):
                query = query.order_by(self.model.id)

            # Apply pagination
            if skip > 0:
                query = query.offset(skip)
            if limit > 0:
                query = query.limit(limit)

            result = await self.db_session.execute(query)
            return list(result.scalars().all())

    async def get_by_filter(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        Get entities by filter conditions.

        Args:
            filters: Dictionary of field_name: value pairs
            skip: Number of entities to skip
            limit: Maximum number of entities to return
            order_by: Field name to order by
            order_desc: Whether to order in descending order

        Returns:
            List of entities matching the filters
        """
        with perf_logger.log_execution_time(f"get_{self.model.__name__.lower()}_by_filter"):
            query = self._build_filter_query(filters)

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(order_column)

            # Apply pagination
            if skip > 0:
                query = query.offset(skip)
            if limit > 0:
                query = query.limit(limit)

            result = await self.db_session.execute(query)
            return list(result.scalars().all())

    async def get_one_by_filter(self, filters: Dict[str, Any]) -> Optional[ModelType]:
        """
        Get single entity by filter conditions.

        Args:
            filters: Dictionary of field_name: value pairs

        Returns:
            Entity if found, None otherwise
        """
        with perf_logger.log_execution_time(f"get_one_{self.model.__name__.lower()}_by_filter"):
            query = self._build_filter_query(filters)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching optional filters.

        Args:
            filters: Optional dictionary of field_name: value pairs

        Returns:
            Number of matching entities
        """
        with perf_logger.log_execution_time(f"count_{self.model.__name__.lower()}"):
            if filters:
                query = self._build_filter_query(filters, count_query=True)
            else:
                query = select(func.count(self.model.id))

            result = await self.db_session.execute(query)
            return result.scalar() or 0

    async def exists(self, filters: Dict[str, Any]) -> bool:
        """
        Check if entity exists matching the filters.

        Args:
            filters: Dictionary of field_name: value pairs

        Returns:
            True if entity exists, False otherwise
        """
        count = await self.count(filters)
        return count > 0

    # ===== WRITE OPERATIONS =====

    async def create(self, **kwargs) -> ModelType:
        """
        Create new entity.

        Args:
            **kwargs: Entity field values

        Returns:
            Created entity
        """
        with perf_logger.log_execution_time(f"create_{self.model.__name__.lower()}"):
            entity = self.model(**kwargs)
            self.db_session.add(entity)
            await self.db_session.flush()
            await self.db_session.refresh(entity)
            return entity

    async def create_many(self, entities_data: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple entities.

        Args:
            entities_data: List of dictionaries with entity field values

        Returns:
            List of created entities
        """
        if not entities_data:
            return []

        with perf_logger.log_execution_time(f"create_many_{self.model.__name__.lower()}"):
            entities = [self.model(**data) for data in entities_data]
            self.db_session.add_all(entities)
            await self.db_session.flush()

            # Refresh all entities to get generated IDs
            for entity in entities:
                await self.db_session.refresh(entity)

            return entities

    async def update(
        self,
        entity_id: Union[int, str, uuid.UUID],
        **kwargs
    ) -> Optional[ModelType]:
        """
        Update entity by ID.

        Args:
            entity_id: Entity identifier
            **kwargs: Fields to update

        Returns:
            Updated entity if found, None otherwise
        """
        with perf_logger.log_execution_time(f"update_{self.model.__name__.lower()}"):
            # Remove None values and empty strings if desired
            update_data = {k: v for k, v in kwargs.items() if v is not None}

            if not update_data:
                return await self.get_by_id(entity_id)

            # Perform update
            await self.db_session.execute(
                update(self.model)
                .where(self.model.id == entity_id)
                .values(**update_data)
            )

            # Return updated entity
            return await self.get_by_id(entity_id)

    async def update_many(
        self,
        filters: Dict[str, Any],
        **kwargs
    ) -> int:
        """
        Update multiple entities matching filters.

        Args:
            filters: Dictionary of field_name: value pairs for filtering
            **kwargs: Fields to update

        Returns:
            Number of updated entities
        """
        with perf_logger.log_execution_time(f"update_many_{self.model.__name__.lower()}"):
            # Remove None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}

            if not update_data:
                return 0

            # Build filter conditions
            filter_conditions = self._build_filter_conditions(filters)

            # Perform update
            result = await self.db_session.execute(
                update(self.model)
                .where(and_(*filter_conditions))
                .values(**update_data)
            )

            return result.rowcount or 0

    async def delete(self, entity_id: Union[int, str, uuid.UUID]) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            True if entity was deleted, False if not found
        """
        with perf_logger.log_execution_time(f"delete_{self.model.__name__.lower()}"):
            result = await self.db_session.execute(
                delete(self.model).where(self.model.id == entity_id)
            )
            return (result.rowcount or 0) > 0

    async def delete_many(self, filters: Dict[str, Any]) -> int:
        """
        Delete multiple entities matching filters.

        Args:
            filters: Dictionary of field_name: value pairs

        Returns:
            Number of deleted entities
        """
        with perf_logger.log_execution_time(f"delete_many_{self.model.__name__.lower()}"):
            filter_conditions = self._build_filter_conditions(filters)

            result = await self.db_session.execute(
                delete(self.model).where(and_(*filter_conditions))
            )

            return result.rowcount or 0

    # ===== HELPER METHODS =====

    def _build_filter_query(
        self,
        filters: Dict[str, Any],
        count_query: bool = False
    ) -> Select:
        """
        Build SQLAlchemy query from filter dictionary.

        Args:
            filters: Dictionary of field_name: value pairs
            count_query: Whether to build a count query

        Returns:
            SQLAlchemy Select query
        """
        if count_query:
            query = select(func.count(self.model.id))
        else:
            query = select(self.model)

        filter_conditions = self._build_filter_conditions(filters)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        return query

    def _build_filter_conditions(self, filters: Dict[str, Any]) -> List:
        """
        Build filter conditions from filter dictionary.

        Args:
            filters: Dictionary of field_name: value pairs

        Returns:
            List of SQLAlchemy filter conditions
        """
        conditions = []

        for field_name, value in filters.items():
            if not hasattr(self.model, field_name):
                logger.warning(f"Field '{field_name}' not found in model '{self.model.__name__}'")
                continue

            column = getattr(self.model, field_name)

            if value is None:
                conditions.append(column.is_(None))
            elif isinstance(value, list):
                conditions.append(column.in_(value))
            elif isinstance(value, dict):
                # Support for complex filters like {"gte": 10, "lte": 20}
                for operator, op_value in value.items():
                    if operator == "gte":
                        conditions.append(column >= op_value)
                    elif operator == "gt":
                        conditions.append(column > op_value)
                    elif operator == "lte":
                        conditions.append(column <= op_value)
                    elif operator == "lt":
                        conditions.append(column < op_value)
                    elif operator == "ne":
                        conditions.append(column != op_value)
                    elif operator == "like":
                        conditions.append(column.like(f"%{op_value}%"))
                    elif operator == "ilike":
                        conditions.append(column.ilike(f"%{op_value}%"))
                    elif operator == "in":
                        conditions.append(column.in_(op_value))
                    elif operator == "not_in":
                        conditions.append(~column.in_(op_value))
            else:
                conditions.append(column == value)

        return conditions

    # ===== SOFT DELETE SUPPORT =====

    async def soft_delete(self, entity_id: Union[int, str, uuid.UUID]) -> bool:
        """
        Soft delete entity by setting deleted_at timestamp.

        Only works if the model has a 'deleted_at' field.

        Args:
            entity_id: Entity identifier

        Returns:
            True if entity was soft deleted, False if not found or no soft delete support
        """
        if not hasattr(self.model, 'deleted_at'):
            logger.warning(f"Model '{self.model.__name__}' does not support soft delete")
            return False

        from datetime import datetime, timezone

        result = await self.update(entity_id, deleted_at=datetime.now(timezone.utc))
        return result is not None

    async def restore(self, entity_id: Union[int, str, uuid.UUID]) -> bool:
        """
        Restore soft deleted entity by clearing deleted_at field.

        Args:
            entity_id: Entity identifier

        Returns:
            True if entity was restored, False if not found or no soft delete support
        """
        if not hasattr(self.model, 'deleted_at'):
            logger.warning(f"Model '{self.model.__name__}' does not support soft delete")
            return False

        result = await self.update(entity_id, deleted_at=None)
        return result is not None

    # ===== TRANSACTION SUPPORT =====

    async def execute_in_transaction(self, operations: List[callable]) -> List[Any]:
        """
        Execute multiple operations in a single transaction.

        Args:
            operations: List of callable operations to execute

        Returns:
            List of operation results
        """
        results = []

        # Note: The session should already be in a transaction context
        # when this repository is used within session_scope()
        for operation in operations:
            if callable(operation):
                result = await operation()
                results.append(result)
            else:
                results.append(operation)

        return results


class RepositoryMixin:
    """
    Mixin class providing repository pattern utilities.

    Can be used to add repository functionality to existing classes.
    """

    def get_repository(self, model: Type[ModelType], session: AsyncSession) -> BaseRepository[ModelType]:
        """
        Get repository instance for a model.

        Args:
            model: SQLAlchemy model class
            session: Database session

        Returns:
            Repository instance
        """
        class ConcreteRepository(BaseRepository[ModelType]):
            pass

        return ConcreteRepository(model, session)
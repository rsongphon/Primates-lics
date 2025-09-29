"""
LICS Backend Base Service

Base service pattern implementation providing business logic layer
with transaction management, event emission, and common service utilities.
Follows Documentation.md Section 5.1 Service Classes guidelines.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_manager
from app.core.logging import get_logger, PerformanceLogger
from app.repositories.base import BaseRepository

logger = get_logger(__name__)
perf_logger = PerformanceLogger(logger)

# Type variables
ModelType = TypeVar("ModelType")
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
ResponseSchemaType = TypeVar("ResponseSchemaType")


class ServiceError(Exception):
    """Base exception class for service errors."""

    def __init__(self, message: str, error_code: str = "SERVICE_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ServiceError):
    """Exception raised for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class NotFoundError(ServiceError):
    """Exception raised when entity is not found."""

    def __init__(self, entity_type: str, entity_id: Union[str, int, uuid.UUID]):
        message = f"{entity_type} with id '{entity_id}' not found"
        super().__init__(message, "NOT_FOUND")
        self.entity_type = entity_type
        self.entity_id = entity_id


class ConflictError(ServiceError):
    """Exception raised for business logic conflicts."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "CONFLICT", details)


class PermissionError(ServiceError):
    """Exception raised for permission/authorization errors."""

    def __init__(self, message: str = "Permission denied", details: Optional[Dict] = None):
        super().__init__(message, "PERMISSION_DENIED", details)


class BaseService(Generic[ModelType, RepositoryType], ABC):
    """
    Base service class providing common business logic patterns.

    This abstract base class defines the interface for all services
    and provides default implementations for common operations with
    proper transaction management and event emission.
    """

    def __init__(self, repository_class: Type[RepositoryType], model_class: Type[ModelType]):
        """
        Initialize service with repository and model classes.

        Args:
            repository_class: Repository class for data access
            model_class: SQLAlchemy model class
        """
        self.repository_class = repository_class
        self.model_class = model_class
        self.entity_name = model_class.__name__

    def get_repository(self, session: AsyncSession) -> RepositoryType:
        """
        Get repository instance for the current session.

        Args:
            session: Database session

        Returns:
            Repository instance
        """
        return self.repository_class(self.model_class, session)

    # ===== CRUD OPERATIONS =====

    async def create(
        self,
        data: Union[Dict[str, Any], CreateSchemaType],
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> ModelType:
        """
        Create new entity with validation and event emission.

        Args:
            data: Entity data (dict or Pydantic model)
            current_user_id: ID of the user performing the operation
            session: Optional database session (will create new if not provided)

        Returns:
            Created entity

        Raises:
            ValidationError: If data validation fails
            ConflictError: If business rules are violated
        """
        # Convert Pydantic model to dict if needed
        if hasattr(data, 'dict'):
            data = data.dict(exclude_unset=True)

        with perf_logger.log_execution_time(f"create_{self.entity_name.lower()}"):
            # Validate data before creation
            await self._validate_create_data(data)

            # Check business rules
            await self._check_create_permissions(data, current_user_id)

            if session:
                # Use provided session
                repository = self.get_repository(session)
                entity = await repository.create(**data)

                # Emit events
                await self._emit_entity_created(entity, current_user_id)

                return entity
            else:
                # Use transaction scope
                async with db_manager.session_scope() as session:
                    repository = self.get_repository(session)
                    entity = await repository.create(**data)

                    # Emit events
                    await self._emit_entity_created(entity, current_user_id)

                    return entity

    async def get_by_id(
        self,
        entity_id: Union[int, str, uuid.UUID],
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> ModelType:
        """
        Get entity by ID with permission checking.

        Args:
            entity_id: Entity identifier
            current_user_id: ID of the user performing the operation
            session: Optional database session

        Returns:
            Entity if found and accessible

        Raises:
            NotFoundError: If entity is not found
            PermissionError: If user doesn't have access
        """
        with perf_logger.log_execution_time(f"get_{self.entity_name.lower()}_by_id"):
            if session:
                repository = self.get_repository(session)
            else:
                async with db_manager.session_scope() as session:
                    repository = self.get_repository(session)
                    entity = await repository.get_by_id(entity_id)

                    if not entity:
                        raise NotFoundError(self.entity_name, entity_id)

                    # Check read permissions
                    await self._check_read_permissions(entity, current_user_id)

                    return entity

            entity = await repository.get_by_id(entity_id)

            if not entity:
                raise NotFoundError(self.entity_name, entity_id)

            # Check read permissions
            await self._check_read_permissions(entity, current_user_id)

            return entity

    async def get_list(
        self,
        *,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> List[ModelType]:
        """
        Get list of entities with filtering and pagination.

        Args:
            filters: Optional filter conditions
            skip: Number of entities to skip
            limit: Maximum number of entities to return
            order_by: Field name to order by
            order_desc: Whether to order in descending order
            current_user_id: ID of the user performing the operation
            session: Optional database session

        Returns:
            List of entities
        """
        with perf_logger.log_execution_time(f"get_{self.entity_name.lower()}_list"):
            # Apply user-specific filters
            filters = await self._apply_user_filters(filters or {}, current_user_id)

            if session:
                repository = self.get_repository(session)
            else:
                async with db_manager.session_scope() as session:
                    repository = self.get_repository(session)
                    entities = await repository.get_by_filter(
                        filters=filters,
                        skip=skip,
                        limit=limit,
                        order_by=order_by,
                        order_desc=order_desc
                    )
                    return entities

            entities = await repository.get_by_filter(
                filters=filters,
                skip=skip,
                limit=limit,
                order_by=order_by,
                order_desc=order_desc
            )

            return entities

    async def update(
        self,
        entity_id: Union[int, str, uuid.UUID],
        data: Union[Dict[str, Any], UpdateSchemaType],
        *,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> ModelType:
        """
        Update entity with validation and event emission.

        Args:
            entity_id: Entity identifier
            data: Update data (dict or Pydantic model)
            current_user_id: ID of the user performing the operation
            session: Optional database session

        Returns:
            Updated entity

        Raises:
            NotFoundError: If entity is not found
            ValidationError: If data validation fails
            PermissionError: If user doesn't have access
        """
        # Convert Pydantic model to dict if needed
        if hasattr(data, 'dict'):
            data = data.dict(exclude_unset=True)

        with perf_logger.log_execution_time(f"update_{self.entity_name.lower()}"):
            if session:
                repository = self.get_repository(session)

                # Get existing entity
                existing_entity = await repository.get_by_id(entity_id)
                if not existing_entity:
                    raise NotFoundError(self.entity_name, entity_id)

                # Check permissions
                await self._check_update_permissions(existing_entity, data, current_user_id)

                # Validate update data
                await self._validate_update_data(existing_entity, data)

                # Perform update
                updated_entity = await repository.update(entity_id, **data)

                # Emit events
                await self._emit_entity_updated(existing_entity, updated_entity, current_user_id)

                return updated_entity
            else:
                async with db_manager.session_scope() as session:
                    repository = self.get_repository(session)

                    # Get existing entity
                    existing_entity = await repository.get_by_id(entity_id)
                    if not existing_entity:
                        raise NotFoundError(self.entity_name, entity_id)

                    # Check permissions
                    await self._check_update_permissions(existing_entity, data, current_user_id)

                    # Validate update data
                    await self._validate_update_data(existing_entity, data)

                    # Perform update
                    updated_entity = await repository.update(entity_id, **data)

                    # Emit events
                    await self._emit_entity_updated(existing_entity, updated_entity, current_user_id)

                    return updated_entity

    async def delete(
        self,
        entity_id: Union[int, str, uuid.UUID],
        *,
        soft_delete: bool = True,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """
        Delete entity with permission checking and event emission.

        Args:
            entity_id: Entity identifier
            soft_delete: Whether to perform soft delete (if supported)
            current_user_id: ID of the user performing the operation
            session: Optional database session

        Returns:
            True if entity was deleted, False otherwise

        Raises:
            NotFoundError: If entity is not found
            PermissionError: If user doesn't have access
        """
        with perf_logger.log_execution_time(f"delete_{self.entity_name.lower()}"):
            if session:
                repository = self.get_repository(session)

                # Get existing entity
                entity = await repository.get_by_id(entity_id)
                if not entity:
                    raise NotFoundError(self.entity_name, entity_id)

                # Check permissions
                await self._check_delete_permissions(entity, current_user_id)

                # Perform deletion
                if soft_delete and hasattr(repository, 'soft_delete'):
                    success = await repository.soft_delete(entity_id)
                else:
                    success = await repository.delete(entity_id)

                if success:
                    # Emit events
                    await self._emit_entity_deleted(entity, current_user_id)

                return success
            else:
                async with db_manager.session_scope() as session:
                    repository = self.get_repository(session)

                    # Get existing entity
                    entity = await repository.get_by_id(entity_id)
                    if not entity:
                        raise NotFoundError(self.entity_name, entity_id)

                    # Check permissions
                    await self._check_delete_permissions(entity, current_user_id)

                    # Perform deletion
                    if soft_delete and hasattr(repository, 'soft_delete'):
                        success = await repository.soft_delete(entity_id)
                    else:
                        success = await repository.delete(entity_id)

                    if success:
                        # Emit events
                        await self._emit_entity_deleted(entity, current_user_id)

                    return success

    async def count(
        self,
        *,
        filters: Optional[Dict[str, Any]] = None,
        current_user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Count entities matching filters.

        Args:
            filters: Optional filter conditions
            current_user_id: ID of the user performing the operation
            session: Optional database session

        Returns:
            Number of matching entities
        """
        # Apply user-specific filters
        filters = await self._apply_user_filters(filters or {}, current_user_id)

        if session:
            repository = self.get_repository(session)
            return await repository.count(filters)
        else:
            async with db_manager.session_scope() as session:
                repository = self.get_repository(session)
                return await repository.count(filters)

    # ===== VALIDATION METHODS =====

    async def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """
        Validate data for entity creation.

        Override in subclasses to add custom validation logic.

        Args:
            data: Entity data to validate

        Raises:
            ValidationError: If validation fails
        """
        pass

    async def _validate_update_data(self, existing_entity: ModelType, data: Dict[str, Any]) -> None:
        """
        Validate data for entity update.

        Override in subclasses to add custom validation logic.

        Args:
            existing_entity: Current entity state
            data: Update data to validate

        Raises:
            ValidationError: If validation fails
        """
        pass

    # ===== PERMISSION METHODS =====

    async def _check_create_permissions(self, data: Dict[str, Any], current_user_id: Optional[uuid.UUID]) -> None:
        """
        Check if user has permission to create entity.

        Override in subclasses to add permission logic.

        Args:
            data: Entity data
            current_user_id: ID of the user performing the operation

        Raises:
            PermissionError: If user doesn't have permission
        """
        pass

    async def _check_read_permissions(self, entity: ModelType, current_user_id: Optional[uuid.UUID]) -> None:
        """
        Check if user has permission to read entity.

        Override in subclasses to add permission logic.

        Args:
            entity: Entity to check
            current_user_id: ID of the user performing the operation

        Raises:
            PermissionError: If user doesn't have permission
        """
        pass

    async def _check_update_permissions(
        self,
        entity: ModelType,
        data: Dict[str, Any],
        current_user_id: Optional[uuid.UUID]
    ) -> None:
        """
        Check if user has permission to update entity.

        Override in subclasses to add permission logic.

        Args:
            entity: Entity to update
            data: Update data
            current_user_id: ID of the user performing the operation

        Raises:
            PermissionError: If user doesn't have permission
        """
        pass

    async def _check_delete_permissions(self, entity: ModelType, current_user_id: Optional[uuid.UUID]) -> None:
        """
        Check if user has permission to delete entity.

        Override in subclasses to add permission logic.

        Args:
            entity: Entity to delete
            current_user_id: ID of the user performing the operation

        Raises:
            PermissionError: If user doesn't have permission
        """
        pass

    async def _apply_user_filters(
        self,
        filters: Dict[str, Any],
        current_user_id: Optional[uuid.UUID]
    ) -> Dict[str, Any]:
        """
        Apply user-specific filters to limit data access.

        Override in subclasses to add filtering logic.

        Args:
            filters: Current filter conditions
            current_user_id: ID of the user performing the operation

        Returns:
            Modified filter conditions
        """
        return filters

    # ===== EVENT METHODS =====

    async def _emit_entity_created(self, entity: ModelType, current_user_id: Optional[uuid.UUID]) -> None:
        """
        Emit event when entity is created.

        Override in subclasses to add event emission logic.

        Args:
            entity: Created entity
            current_user_id: ID of the user who created the entity
        """
        logger.info(
            f"{self.entity_name} created",
            extra={
                "entity_type": self.entity_name,
                "entity_id": getattr(entity, 'id', None),
                "user_id": current_user_id,
                "action": "create"
            }
        )

    async def _emit_entity_updated(
        self,
        old_entity: ModelType,
        new_entity: ModelType,
        current_user_id: Optional[uuid.UUID]
    ) -> None:
        """
        Emit event when entity is updated.

        Override in subclasses to add event emission logic.

        Args:
            old_entity: Entity state before update
            new_entity: Entity state after update
            current_user_id: ID of the user who updated the entity
        """
        logger.info(
            f"{self.entity_name} updated",
            extra={
                "entity_type": self.entity_name,
                "entity_id": getattr(new_entity, 'id', None),
                "user_id": current_user_id,
                "action": "update"
            }
        )

    async def _emit_entity_deleted(self, entity: ModelType, current_user_id: Optional[uuid.UUID]) -> None:
        """
        Emit event when entity is deleted.

        Override in subclasses to add event emission logic.

        Args:
            entity: Deleted entity
            current_user_id: ID of the user who deleted the entity
        """
        logger.info(
            f"{self.entity_name} deleted",
            extra={
                "entity_type": self.entity_name,
                "entity_id": getattr(entity, 'id', None),
                "user_id": current_user_id,
                "action": "delete"
            }
        )


class ServiceMixin:
    """
    Mixin class providing service pattern utilities.

    Can be used to add service functionality to existing classes.
    """

    def get_service(
        self,
        service_class: Type[BaseService],
        repository_class: Type[BaseRepository],
        model_class: Type[ModelType]
    ) -> BaseService:
        """
        Get service instance.

        Args:
            service_class: Service class
            repository_class: Repository class
            model_class: Model class

        Returns:
            Service instance
        """
        return service_class(repository_class, model_class)
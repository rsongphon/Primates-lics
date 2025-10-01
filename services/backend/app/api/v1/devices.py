"""
Devices API Endpoints

RESTful API endpoints for device management including CRUD operations,
device registration, status updates, heartbeat monitoring, and telemetry collection.
"""

import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_active_user,
    require_permissions, PaginationParams, get_pagination
)
from app.models.auth import User
from app.models.domain import DeviceStatus, DeviceType
from app.schemas.base import PaginatedResponse
from app.schemas.devices import (
    DeviceSchema, DeviceCreateSchema, DeviceUpdateSchema,
    DeviceFilterSchema, DeviceStatusUpdateSchema, DeviceHealthSchema,
    DeviceDataCreateSchema, DeviceDataSchema
)
from app.services.domain import DeviceService, DeviceDataService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ===== DEVICE CRUD ENDPOINTS =====

@router.get(
    "",
    response_model=PaginatedResponse[DeviceSchema],
    summary="List devices",
    description="Retrieve paginated list of devices with filtering and sorting"
)
async def list_devices(
    pagination: PaginationParams = Depends(get_pagination),
    name: Optional[str] = Query(None, description="Filter by device name"),
    device_type: Optional[DeviceType] = Query(None, description="Filter by device type"),
    status: Optional[DeviceStatus] = Query(None, description="Filter by device status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all devices with pagination and filtering."""
    service = DeviceService()

    # Build filters
    filters = {'organization_id': current_user.organization_id}
    if name:
        filters['name'] = name
    if device_type:
        filters['device_type'] = device_type
    if status:
        filters['status'] = status
    if location:
        filters['location'] = location
    if is_active is not None:
        filters['is_active'] = is_active

    # Get paginated devices
    devices, total = await service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    return PaginatedResponse(
        items=devices,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


@router.post(
    "",
    response_model=DeviceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register device",
    description="Register a new device in the system",
    dependencies=[Depends(require_permissions("device:create"))]
)
async def register_device(
    device_data: DeviceCreateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Register a new device."""
    service = DeviceService()

    try:
        # Add organization ID from current user
        device_dict = device_data.model_dump()
        device_dict['organization_id'] = current_user.organization_id

        device = await service.register_device(
            device_dict,
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Device registered",
            extra={
                "device_id": str(device.id),
                "device_name": device.name,
                "device_type": device.device_type.value,
                "registered_by": str(current_user.id)
            }
        )
        return device
    except Exception as e:
        logger.error(f"Failed to register device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{device_id}",
    response_model=DeviceSchema,
    summary="Get device",
    description="Retrieve device details by ID"
)
async def get_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get device by ID."""
    service = DeviceService()

    device = await service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    # Check organization access
    if device.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this device"
        )

    return device


@router.patch(
    "/{device_id}",
    response_model=DeviceSchema,
    summary="Update device",
    description="Update device details and configuration",
    dependencies=[Depends(require_permissions("device:update"))]
)
async def update_device(
    device_id: uuid.UUID,
    device_data: DeviceUpdateSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update device details."""
    service = DeviceService()

    # Check if device exists and user has access
    device = await service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    if device.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this device"
        )

    try:
        updated_device = await service.update(
            device_id,
            device_data.model_dump(exclude_unset=True),
            current_user_id=current_user.id,
            session=db
        )
        logger.info(
            f"Device updated",
            extra={
                "device_id": str(device_id),
                "updated_by": str(current_user.id)
            }
        )
        return updated_device
    except Exception as e:
        logger.error(f"Failed to update device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete device",
    description="Soft delete a device",
    dependencies=[Depends(require_permissions("device:delete"))]
)
async def delete_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a device."""
    service = DeviceService()

    # Check if device exists and user has access
    device = await service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    if device.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this device"
        )

    try:
        await service.delete(device_id, session=db)
        logger.info(
            f"Device deleted",
            extra={
                "device_id": str(device_id),
                "deleted_by": str(current_user.id)
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== DEVICE STATUS MANAGEMENT =====

@router.post(
    "/{device_id}/heartbeat",
    response_model=DeviceSchema,
    summary="Update device heartbeat",
    description="Update device heartbeat and optional status information"
)
async def update_device_heartbeat(
    device_id: uuid.UUID,
    heartbeat_data: Optional[DeviceHealthSchema] = None,
    current_user: User = Depends(get_current_user),  # Allow device tokens
    db: AsyncSession = Depends(get_db)
):
    """Update device heartbeat timestamp and status."""
    service = DeviceService()

    # Check if device exists
    device = await service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    try:
        status_data = heartbeat_data.model_dump() if heartbeat_data else None
        updated_device = await service.update_device_heartbeat(
            device_id,
            status_data=status_data,
            session=db
        )
        return updated_device
    except Exception as e:
        logger.error(f"Failed to update device heartbeat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch(
    "/{device_id}/status",
    response_model=DeviceSchema,
    summary="Update device status",
    description="Update device operational status"
)
async def update_device_status(
    device_id: uuid.UUID,
    status_data: DeviceStatusUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update device status."""
    service = DeviceService()

    # Check if device exists
    device = await service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    try:
        updated_device = await service.update_device_status(
            device_id,
            status_data.status,
            error_message=status_data.error_message,
            session=db
        )
        logger.info(
            f"Device status updated",
            extra={
                "device_id": str(device_id),
                "new_status": status_data.status.value,
                "updated_by": str(current_user.id) if hasattr(current_user, 'id') else "system"
            }
        )
        return updated_device
    except Exception as e:
        logger.error(f"Failed to update device status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== DEVICE TELEMETRY =====

@router.post(
    "/{device_id}/data",
    response_model=DeviceDataSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Submit device telemetry",
    description="Submit telemetry data from device sensors"
)
async def submit_device_data(
    device_id: uuid.UUID,
    data: DeviceDataCreateSchema,
    current_user: User = Depends(get_current_user),  # Allow device tokens
    db: AsyncSession = Depends(get_db)
):
    """Submit telemetry data from a device."""
    service = DeviceDataService()

    # Check if device exists
    device_service = DeviceService()
    device = await device_service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    try:
        # Add device_id to data
        data_dict = data.model_dump()
        data_dict['device_id'] = device_id

        device_data = await service.create(
            data_dict,
            session=db
        )
        return device_data
    except Exception as e:
        logger.error(f"Failed to submit device data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{device_id}/data",
    response_model=PaginatedResponse[DeviceDataSchema],
    summary="Get device telemetry",
    description="Retrieve telemetry data for a device with time-based filtering"
)
async def get_device_data(
    device_id: uuid.UUID,
    pagination: PaginationParams = Depends(get_pagination),
    start_time: Optional[datetime] = Query(None, description="Start time for data query"),
    end_time: Optional[datetime] = Query(None, description="End time for data query"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get telemetry data for a device."""
    # Check if device exists and user has access
    device_service = DeviceService()
    device = await device_service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    if device.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this device's data"
        )

    # Get device data
    service = DeviceDataService()
    filters = {'device_id': device_id}
    if metric_type:
        filters['metric_type'] = metric_type

    # TODO: Implement time-based filtering in repository
    # For now, use basic filtering
    data_records, total = await service.get_list_with_filters(
        filters=filters,
        skip=pagination['skip'],
        limit=pagination['limit'],
        session=db
    )

    return PaginatedResponse(
        items=data_records,
        total=total,
        page=pagination['page'],
        page_size=pagination['page_size'],
        pages=(total + pagination['page_size'] - 1) // pagination['page_size']
    )


# ===== DEVICE STATISTICS =====

@router.get(
    "/{device_id}/stats",
    summary="Get device statistics",
    description="Retrieve statistical summary for a device"
)
async def get_device_stats(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get device statistics and health metrics."""
    service = DeviceService()

    device = await service.get_by_id(device_id, session=db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    if device.organization_id != current_user.organization_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this device"
        )

    # Calculate uptime
    uptime_hours = None
    if device.last_heartbeat_at:
        uptime_delta = datetime.now(timezone.utc) - device.last_heartbeat_at
        uptime_hours = uptime_delta.total_seconds() / 3600

    # TODO: Implement actual statistics gathering from DeviceData
    return {
        "device_id": str(device_id),
        "status": device.status.value,
        "last_seen": device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None,
        "uptime_hours": uptime_hours,
        "total_data_points": 0,  # TODO: Count from DeviceData
        "total_experiments": 0,  # TODO: Count from Experiments
        "hardware_metrics": device.hardware_config if device.hardware_config else {},
        "software_version": device.software_version
    }

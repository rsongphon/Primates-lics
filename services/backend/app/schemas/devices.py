"""
Device Schemas

Pydantic schemas for device-related requests and responses.
Includes device registration, configuration, status updates, and data collection.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator, ConfigDict

from app.schemas.base import (
    BaseCreateSchema, BaseUpdateSchema, BaseFilterSchema,
    OrganizationEntityFullSchema, BaseSchema
)


# ===== ENUMS =====

class DeviceStatusEnum(str, Enum):
    """Device status enumeration for schemas."""
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DeviceTypeEnum(str, Enum):
    """Device type enumeration for schemas."""
    RASPBERRY_PI = "raspberry_pi"
    ARDUINO = "arduino"
    CUSTOM = "custom"
    SIMULATION = "simulation"


# ===== REQUEST SCHEMAS =====

class DeviceCreateSchema(BaseCreateSchema):
    """Schema for creating a new device."""

    name: str = Field(
        ...,
        description="Human-readable device name",
        min_length=1,
        max_length=255,
        examples=["Lab-A-Device-001", "Temperature Monitor", "Behavioral Chamber 1"]
    )

    description: Optional[str] = Field(
        None,
        description="Device description and purpose",
        max_length=1000,
        examples=["Raspberry Pi 4 with temperature and humidity sensors for cage monitoring"]
    )

    device_type: DeviceTypeEnum = Field(
        DeviceTypeEnum.RASPBERRY_PI,
        description="Type of device",
        examples=["raspberry_pi", "arduino", "custom", "simulation"]
    )

    serial_number: Optional[str] = Field(
        None,
        description="Device serial number (must be unique if provided)",
        min_length=1,
        max_length=100,
        examples=["SN123456789", "RPI4-2024-001"]
    )

    mac_address: Optional[str] = Field(
        None,
        description="Device MAC address (format: XX:XX:XX:XX:XX:XX)",
        pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
        examples=["B8:27:EB:12:34:56"]
    )

    location: Optional[str] = Field(
        None,
        description="Physical location of the device",
        max_length=255,
        examples=["Lab A, Room 101, Cage 5", "Building 2, Floor 3, West Wing"]
    )

    hardware_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Hardware configuration and specifications",
        examples=[{
            "model": "Raspberry Pi 4 Model B",
            "memory": "8GB",
            "storage": "64GB SD Card",
            "gpio_pins": 40,
            "usb_ports": 4
        }]
    )

    software_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Software configuration and settings",
        examples=[{
            "os": "Raspberry Pi OS",
            "python_version": "3.11",
            "sampling_rate": 100,
            "data_retention_days": 30
        }]
    )

    capabilities: Optional[Dict[str, Any]] = Field(
        None,
        description="Device capabilities (sensors, actuators, features)",
        examples=[{
            "sensors": ["temperature", "humidity", "motion", "light"],
            "actuators": ["led", "buzzer", "servo"],
            "interfaces": ["gpio", "i2c", "spi"],
            "camera": True,
            "audio": False
        }]
    )

    firmware_version: Optional[str] = Field(
        None,
        description="Initial firmware version",
        max_length=50,
        examples=["1.0.0", "v2.1.3-beta"]
    )

    agent_version: Optional[str] = Field(
        None,
        description="Initial edge agent version",
        max_length=50,
        examples=["1.0.0", "v2.1.3-beta"]
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate device name."""
        if not v or not v.strip():
            raise ValueError('Device name cannot be empty')
        return v.strip()

    @validator('capabilities')
    def validate_capabilities(cls, v):
        """Validate capabilities structure."""
        if v is None:
            return v

        # Ensure basic structure
        if not isinstance(v, dict):
            raise ValueError('Capabilities must be a dictionary')

        # Validate sensors list
        if 'sensors' in v and not isinstance(v['sensors'], list):
            raise ValueError('Sensors must be a list')

        # Validate actuators list
        if 'actuators' in v and not isinstance(v['actuators'], list):
            raise ValueError('Actuators must be a list')

        return v


class DeviceUpdateSchema(BaseUpdateSchema):
    """Schema for updating device information."""

    name: Optional[str] = Field(
        None,
        description="Human-readable device name",
        min_length=1,
        max_length=255
    )

    description: Optional[str] = Field(
        None,
        description="Device description and purpose",
        max_length=1000
    )

    device_type: Optional[DeviceTypeEnum] = Field(
        None,
        description="Type of device"
    )

    location: Optional[str] = Field(
        None,
        description="Physical location of the device",
        max_length=255
    )

    hardware_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Hardware configuration and specifications"
    )

    software_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Software configuration and settings"
    )

    capabilities: Optional[Dict[str, Any]] = Field(
        None,
        description="Device capabilities (sensors, actuators, features)"
    )

    is_active: Optional[bool] = Field(
        None,
        description="Whether the device is active and available for use"
    )

    firmware_version: Optional[str] = Field(
        None,
        description="Firmware version",
        max_length=50
    )

    agent_version: Optional[str] = Field(
        None,
        description="Edge agent version",
        max_length=50
    )

    next_maintenance_at: Optional[datetime] = Field(
        None,
        description="When the device is scheduled for next maintenance"
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate device name."""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Device name cannot be empty')
        return v.strip() if v else v


class DeviceStatusUpdateSchema(BaseSchema):
    """Schema for updating device status and performance metrics."""

    status: Optional[DeviceStatusEnum] = Field(
        None,
        description="Device status"
    )

    ip_address: Optional[str] = Field(
        None,
        description="Current IP address",
        examples=["192.168.1.100", "2001:db8::1"]
    )

    uptime_hours: Optional[float] = Field(
        None,
        description="Device uptime in hours",
        ge=0,
        examples=[24.5, 168.0, 720.25]
    )

    cpu_usage_percent: Optional[float] = Field(
        None,
        description="Current CPU usage percentage",
        ge=0,
        le=100,
        examples=[25.5, 67.8, 95.2]
    )

    memory_usage_percent: Optional[float] = Field(
        None,
        description="Current memory usage percentage",
        ge=0,
        le=100,
        examples=[45.2, 78.9, 92.1]
    )

    disk_usage_percent: Optional[float] = Field(
        None,
        description="Current disk usage percentage",
        ge=0,
        le=100,
        examples=[32.1, 65.4, 89.7]
    )

    temperature_celsius: Optional[float] = Field(
        None,
        description="Current device temperature in Celsius",
        examples=[35.2, 45.8, 62.1]
    )

    last_maintenance_at: Optional[datetime] = Field(
        None,
        description="When the device was last maintained"
    )


class DeviceFilterSchema(BaseFilterSchema):
    """Schema for filtering devices."""

    name: Optional[str] = Field(
        None,
        description="Filter by device name (partial match)",
        examples=["Lab-A", "Temperature"]
    )

    device_type: Optional[DeviceTypeEnum] = Field(
        None,
        description="Filter by device type"
    )

    status: Optional[DeviceStatusEnum] = Field(
        None,
        description="Filter by device status"
    )

    location: Optional[str] = Field(
        None,
        description="Filter by location (partial match)",
        examples=["Lab A", "Building 2"]
    )

    is_active: Optional[bool] = Field(
        None,
        description="Filter by active status"
    )

    has_capability: Optional[str] = Field(
        None,
        description="Filter devices that have a specific capability",
        examples=["temperature", "camera", "motion"]
    )

    firmware_version: Optional[str] = Field(
        None,
        description="Filter by firmware version",
        examples=["1.0.0", "v2.1.3"]
    )

    agent_version: Optional[str] = Field(
        None,
        description="Filter by agent version",
        examples=["1.0.0", "v2.1.3"]
    )

    last_heartbeat_after: Optional[datetime] = Field(
        None,
        description="Filter devices with heartbeat after this time"
    )

    last_heartbeat_before: Optional[datetime] = Field(
        None,
        description="Filter devices with heartbeat before this time"
    )

    maintenance_due_before: Optional[datetime] = Field(
        None,
        description="Filter devices with maintenance due before this time"
    )


# ===== RESPONSE SCHEMAS =====

class DeviceSchema(OrganizationEntityFullSchema):
    """Schema for device responses."""

    name: str = Field(
        ...,
        description="Human-readable device name"
    )

    description: Optional[str] = Field(
        None,
        description="Device description and purpose"
    )

    device_type: DeviceTypeEnum = Field(
        ...,
        description="Type of device"
    )

    serial_number: Optional[str] = Field(
        None,
        description="Device serial number"
    )

    mac_address: Optional[str] = Field(
        None,
        description="Device MAC address"
    )

    ip_address: Optional[str] = Field(
        None,
        description="Current IP address"
    )

    status: DeviceStatusEnum = Field(
        ...,
        description="Current device status"
    )

    is_active: bool = Field(
        ...,
        description="Whether the device is active and available for use"
    )

    location: Optional[str] = Field(
        None,
        description="Physical location of the device"
    )

    hardware_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Hardware configuration and specifications"
    )

    software_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Software configuration and settings"
    )

    capabilities: Optional[Dict[str, Any]] = Field(
        None,
        description="Device capabilities (sensors, actuators, features)"
    )

    last_heartbeat_at: Optional[datetime] = Field(
        None,
        description="When the device last sent a heartbeat"
    )

    last_maintenance_at: Optional[datetime] = Field(
        None,
        description="When the device was last maintained"
    )

    next_maintenance_at: Optional[datetime] = Field(
        None,
        description="When the device is scheduled for next maintenance"
    )

    firmware_version: Optional[str] = Field(
        None,
        description="Current firmware version"
    )

    agent_version: Optional[str] = Field(
        None,
        description="Current edge agent version"
    )

    uptime_hours: Optional[float] = Field(
        None,
        description="Device uptime in hours"
    )

    cpu_usage_percent: Optional[float] = Field(
        None,
        description="Current CPU usage percentage"
    )

    memory_usage_percent: Optional[float] = Field(
        None,
        description="Current memory usage percentage"
    )

    disk_usage_percent: Optional[float] = Field(
        None,
        description="Current disk usage percentage"
    )

    temperature_celsius: Optional[float] = Field(
        None,
        description="Current device temperature in Celsius"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "organization_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Lab-A-Device-001",
                    "description": "Raspberry Pi 4 with environmental sensors",
                    "device_type": "raspberry_pi",
                    "serial_number": "RPI4-2024-001",
                    "mac_address": "B8:27:EB:12:34:56",
                    "ip_address": "192.168.1.100",
                    "status": "online",
                    "is_active": True,
                    "location": "Lab A, Room 101, Cage 5",
                    "hardware_config": {
                        "model": "Raspberry Pi 4 Model B",
                        "memory": "8GB",
                        "storage": "64GB SD Card"
                    },
                    "capabilities": {
                        "sensors": ["temperature", "humidity", "motion"],
                        "actuators": ["led", "buzzer"],
                        "camera": True
                    },
                    "firmware_version": "1.0.0",
                    "agent_version": "1.0.0",
                    "uptime_hours": 168.5,
                    "cpu_usage_percent": 25.3,
                    "memory_usage_percent": 45.7,
                    "temperature_celsius": 42.1,
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T14:30:00Z"
                }
            ]
        }
    )


class DeviceSummarySchema(BaseSchema):
    """Schema for device summary (minimal information)."""

    id: uuid.UUID = Field(
        ...,
        description="Device ID"
    )

    name: str = Field(
        ...,
        description="Device name"
    )

    device_type: DeviceTypeEnum = Field(
        ...,
        description="Device type"
    )

    status: DeviceStatusEnum = Field(
        ...,
        description="Device status"
    )

    location: Optional[str] = Field(
        None,
        description="Device location"
    )

    last_heartbeat_at: Optional[datetime] = Field(
        None,
        description="Last heartbeat timestamp"
    )


class DeviceCapabilitiesSchema(BaseSchema):
    """Schema for device capabilities response."""

    device_id: uuid.UUID = Field(
        ...,
        description="Device ID"
    )

    sensors: List[str] = Field(
        default_factory=list,
        description="Available sensors",
        examples=[["temperature", "humidity", "motion", "light"]]
    )

    actuators: List[str] = Field(
        default_factory=list,
        description="Available actuators",
        examples=[["led", "buzzer", "servo", "relay"]]
    )

    interfaces: List[str] = Field(
        default_factory=list,
        description="Available communication interfaces",
        examples=[["gpio", "i2c", "spi", "uart"]]
    )

    features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional features and capabilities",
        examples=[{
            "camera": {"resolution": "1080p", "fps": 30},
            "audio": {"input": True, "output": True},
            "storage": {"capacity_gb": 64, "available_gb": 32}
        }]
    )


class DeviceHealthSchema(BaseSchema):
    """Schema for device health status."""

    device_id: uuid.UUID = Field(
        ...,
        description="Device ID"
    )

    status: DeviceStatusEnum = Field(
        ...,
        description="Current device status"
    )

    is_online: bool = Field(
        ...,
        description="Whether the device is currently online"
    )

    last_heartbeat_at: Optional[datetime] = Field(
        None,
        description="Last heartbeat timestamp"
    )

    heartbeat_age_minutes: Optional[float] = Field(
        None,
        description="Age of last heartbeat in minutes"
    )

    performance_metrics: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Current performance metrics",
        examples=[{
            "cpu_usage_percent": 25.3,
            "memory_usage_percent": 45.7,
            "disk_usage_percent": 32.1,
            "temperature_celsius": 42.1,
            "uptime_hours": 168.5
        }]
    )

    alerts: List[str] = Field(
        default_factory=list,
        description="Current health alerts",
        examples=[["High temperature warning", "Disk space low"]]
    )


# ===== SPECIALIZED SCHEMAS =====

class DeviceRegistrationSchema(BaseSchema):
    """Schema for device self-registration from edge agents."""

    device_id: str = Field(
        ...,
        description="Device identifier from edge agent",
        examples=["rpi4-lab-a-001", "arduino-sensor-hub-02"]
    )

    device_info: Dict[str, Any] = Field(
        ...,
        description="Device information from agent",
        examples=[{
            "type": "raspberry_pi",
            "model": "Raspberry Pi 4 Model B",
            "serial": "10000000abcd1234",
            "mac_address": "B8:27:EB:12:34:56",
            "os": "Raspberry Pi OS",
            "python_version": "3.11.2"
        }]
    )

    capabilities: Dict[str, Any] = Field(
        ...,
        description="Device capabilities discovered by agent",
        examples=[{
            "sensors": {
                "dht22": {"type": "temperature_humidity", "pin": 4},
                "pir": {"type": "motion", "pin": 18}
            },
            "actuators": {
                "led": {"type": "digital_output", "pin": 25},
                "buzzer": {"type": "digital_output", "pin": 23}
            },
            "interfaces": ["gpio", "i2c", "spi"],
            "camera": True
        }]
    )

    agent_version: str = Field(
        ...,
        description="Edge agent version",
        examples=["1.0.0", "2.1.3-beta"]
    )

    location_hint: Optional[str] = Field(
        None,
        description="Location hint from configuration",
        examples=["lab-a-cage-5", "room-101"]
    )


class DeviceConfigurationSchema(BaseSchema):
    """Schema for sending configuration to devices."""

    device_id: uuid.UUID = Field(
        ...,
        description="Device ID"
    )

    configuration: Dict[str, Any] = Field(
        ...,
        description="Configuration data to send to device",
        examples=[{
            "sampling_rate": 100,
            "data_retention_days": 30,
            "sensors": {
                "temperature": {"enabled": True, "interval": 10},
                "humidity": {"enabled": True, "interval": 10}
            },
            "actuators": {
                "led": {"enabled": True, "default_state": False}
            }
        }]
    )

    apply_immediately: bool = Field(
        True,
        description="Whether to apply configuration immediately"
    )


class DeviceCommandSchema(BaseSchema):
    """Schema for sending commands to devices."""

    device_id: uuid.UUID = Field(
        ...,
        description="Device ID"
    )

    command: str = Field(
        ...,
        description="Command name",
        examples=["restart", "calibrate", "update_firmware", "test_sensors"]
    )

    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Command parameters",
        examples=[{
            "sensor": "temperature",
            "calibration_value": 0.5
        }]
    )

    timeout_seconds: Optional[int] = Field(
        30,
        description="Command timeout in seconds",
        ge=1,
        le=3600
    )


class DeviceCommandResponseSchema(BaseSchema):
    """Schema for device command responses."""

    command_id: str = Field(
        ...,
        description="Unique command identifier"
    )

    device_id: uuid.UUID = Field(
        ...,
        description="Device ID"
    )

    command: str = Field(
        ...,
        description="Command that was executed"
    )

    status: str = Field(
        ...,
        description="Command execution status",
        examples=["success", "failed", "timeout", "in_progress"]
    )

    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Command execution result"
    )

    error_message: Optional[str] = Field(
        None,
        description="Error message if command failed"
    )

    executed_at: datetime = Field(
        ...,
        description="When the command was executed"
    )

    execution_time_seconds: Optional[float] = Field(
        None,
        description="Command execution time in seconds"
    )
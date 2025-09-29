# LICS MQTT Topic Hierarchy Documentation

## Overview

The Lab Instrument Control System (LICS) uses a structured MQTT topic hierarchy to organize communication between the backend services, edge devices, and monitoring systems. This document defines the standardized topic structure, usage patterns, and examples.

## Core Principles

1. **Hierarchical Organization**: Topics follow a tree structure for logical grouping
2. **Namespace Isolation**: Different labs and experiments are isolated by namespaces
3. **Predictable Patterns**: Consistent naming conventions for easy automation
4. **Security-First**: Topic structure supports fine-grained access control
5. **Scalability**: Designed to handle thousands of devices and experiments

## Topic Structure

### Root Namespace
```
lics/
├── labs/{lab_id}/
│   ├── devices/{device_id}/
│   └── experiments/{exp_id}/
├── system/
└── admin/
```

### Complete Topic Hierarchy

```
lics/
├── labs/{lab_id}/                          # Lab-specific namespace
│   ├── devices/{device_id}/                # Device-specific topics
│   │   ├── telemetry/                      # Sensor data from device
│   │   │   ├── temperature                 # Temperature readings
│   │   │   ├── humidity                    # Humidity readings
│   │   │   ├── motion                      # Motion detection
│   │   │   ├── pressure                    # Pressure sensors
│   │   │   ├── light                       # Light sensors
│   │   │   ├── sound                       # Sound level
│   │   │   ├── gpio/{pin_number}           # GPIO pin states
│   │   │   ├── camera/status               # Camera status
│   │   │   ├── system/cpu                  # CPU usage
│   │   │   ├── system/memory               # Memory usage
│   │   │   ├── system/disk                 # Disk usage
│   │   │   └── system/network              # Network status
│   │   ├── commands/                       # Commands to device
│   │   │   ├── start                       # Start experiment/task
│   │   │   ├── stop                        # Stop experiment/task
│   │   │   ├── pause                       # Pause current operation
│   │   │   ├── resume                      # Resume operation
│   │   │   ├── configure                   # Configuration updates
│   │   │   ├── calibrate                   # Calibration commands
│   │   │   ├── restart                     # Restart device
│   │   │   ├── shutdown                    # Shutdown device
│   │   │   ├── gpio/{pin_number}           # GPIO control
│   │   │   ├── camera/capture              # Camera capture
│   │   │   ├── camera/record               # Video recording
│   │   │   └── task/upload                 # Upload new task
│   │   ├── status                          # Device health and status
│   │   ├── commands/ack                    # Command acknowledgments
│   │   ├── errors                          # Error reports
│   │   ├── logs                            # Device logs
│   │   └── heartbeat                       # Device heartbeat
│   └── experiments/{exp_id}/               # Experiment-specific topics
│       ├── events                          # Experiment lifecycle events
│       ├── data                            # Experiment result data
│       ├── status                          # Experiment status
│       ├── participants/{participant_id}    # Participant-specific data
│       └── analysis                        # Real-time analysis results
├── system/                                 # System-wide topics
│   ├── events                              # System events and notifications
│   ├── heartbeat                          # System heartbeat
│   ├── status                             # Overall system status
│   ├── alerts                             # System alerts
│   ├── maintenance                        # Maintenance notifications
│   └── statistics                         # System statistics
└── admin/                                 # Administrative topics
    ├── commands                           # System administration commands
    ├── status                             # Administrative status
    ├── users                              # User management events
    └── backup                             # Backup/restore events
```

## Topic Naming Conventions

### General Rules
- Use lowercase letters, numbers, hyphens, and underscores only
- Separate words with hyphens: `multi-word-topic`
- Use meaningful, descriptive names
- Keep topic segments reasonably short (< 50 characters)
- Be consistent across similar topics

### Identifiers
- **lab_id**: Unique lab identifier (e.g., `neuro-lab-01`, `behavior-lab-a`)
- **device_id**: Unique device identifier (e.g., `rpi-001`, `cage-12-sensor`)
- **exp_id**: Experiment identifier (e.g., `exp-2024-001`, `behavior-study-123`)
- **participant_id**: Participant/subject identifier (e.g., `subject-001`, `mouse-a1`)

## Message Formats

### Telemetry Data
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "device_id": "rpi-001",
  "metric": "temperature",
  "value": 23.5,
  "unit": "celsius",
  "precision": 0.1,
  "tags": {
    "sensor_id": "ds18b20-1",
    "location": "cage-12"
  }
}
```

### Commands
```json
{
  "command_id": "cmd-123456",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "command": "start",
  "parameters": {
    "task_id": "task-001",
    "duration": 300,
    "intensity": "medium"
  },
  "timeout": 30,
  "priority": "normal"
}
```

### Status Updates
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "device_id": "rpi-001",
  "status": "running",
  "uptime": 86400,
  "current_task": "task-001",
  "health": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "temperature": 42.3,
    "disk_free_gb": 15.2
  },
  "connectivity": {
    "wifi_strength": -45,
    "mqtt_connected": true,
    "last_heartbeat": "2024-01-15T10:30:40.000Z"
  }
}
```

### Event Data
```json
{
  "event_id": "evt-789012",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "event_type": "experiment_started",
  "experiment_id": "exp-2024-001",
  "device_id": "rpi-001",
  "data": {
    "task_id": "behavioral-test-v2",
    "participant_id": "subject-001",
    "session_id": "session-456"
  },
  "severity": "info"
}
```

## QoS Recommendations

### Quality of Service Levels

| Topic Pattern | QoS | Rationale |
|---------------|-----|-----------|
| `*/telemetry/*` | 0 | High volume, occasional loss acceptable |
| `*/commands/*` | 1 | Commands must be delivered |
| `*/status` | 1 | Status updates are important |
| `*/events` | 1 | Events should be recorded |
| `*/errors` | 1 | Error reports are critical |
| `*/heartbeat` | 0 | Regular updates, recent data only |
| `admin/*` | 2 | Administrative commands are critical |
| `*/commands/ack` | 1 | Acknowledgments must be delivered |

## Usage Examples

### Device Publishing Telemetry
```bash
# Temperature reading from device rpi-001 in neuro-lab-01
mosquitto_pub -h mqtt.lics.local -t "lics/labs/neuro-lab-01/devices/rpi-001/telemetry/temperature" \
  -m '{"timestamp":"2024-01-15T10:30:45.123Z","value":23.5,"unit":"celsius"}' \
  -q 0
```

### Backend Sending Command
```bash
# Send start command to device
mosquitto_pub -h mqtt.lics.local -t "lics/labs/neuro-lab-01/devices/rpi-001/commands/start" \
  -m '{"command_id":"cmd-123","task_id":"behavioral-test","duration":300}' \
  -q 1
```

### Monitoring Subscription
```bash
# Subscribe to all telemetry data for monitoring
mosquitto_sub -h mqtt.lics.local -t "lics/labs/+/devices/+/telemetry/+" -q 0
```

### Device Status Check
```bash
# Check status of all devices in a lab
mosquitto_sub -h mqtt.lics.local -t "lics/labs/neuro-lab-01/devices/+/status" -q 1
```

## Topic Patterns for Different Use Cases

### Real-time Monitoring Dashboard
```bash
# Subscribe to all device telemetry
lics/labs/+/devices/+/telemetry/+

# Subscribe to all device status
lics/labs/+/devices/+/status

# Subscribe to system events
lics/system/events
lics/system/alerts
```

### Device Management
```bash
# Send commands to specific device
lics/labs/{lab_id}/devices/{device_id}/commands/{command}

# Monitor command acknowledgments
lics/labs/{lab_id}/devices/{device_id}/commands/ack

# Check device errors
lics/labs/{lab_id}/devices/{device_id}/errors
```

### Experiment Control
```bash
# Start experiment
lics/labs/{lab_id}/experiments/{exp_id}/events

# Monitor experiment data
lics/labs/{lab_id}/experiments/{exp_id}/data

# Check participant progress
lics/labs/{lab_id}/experiments/{exp_id}/participants/{participant_id}
```

### Administrative Operations
```bash
# System commands
lics/admin/commands

# User management events
lics/admin/users

# Backup operations
lics/admin/backup
```

## Security Considerations

### Topic Access Control
- Devices can only publish to their own telemetry topics
- Devices can only subscribe to their own command topics
- Backend services have broader read/write access
- Administrative topics require special permissions

### Sensitive Data
- Avoid publishing sensitive information in topic names
- Use encryption for sensitive payload data
- Implement payload validation
- Monitor for unauthorized access attempts

### Audit Trail
- All topic access is logged
- Failed authentication attempts are recorded
- Command execution is tracked
- Administrative actions are audited

## Migration and Versioning

### Topic Evolution
- New topics can be added without breaking existing systems
- Deprecated topics should be marked and gradually removed
- Version information can be included in message payloads
- Maintain backward compatibility when possible

### Schema Updates
- Use semantic versioning for message schemas
- Include schema version in message payloads
- Provide migration tools for breaking changes
- Document all schema changes

## Best Practices

### Publishers
1. Include timestamp in all messages
2. Use appropriate QoS levels
3. Implement retry logic for critical messages
4. Monitor publish success rates
5. Keep message sizes reasonable (< 64KB)

### Subscribers
1. Handle message ordering carefully (MQTT doesn't guarantee order)
2. Implement idempotent message processing
3. Use appropriate QoS levels for subscriptions
4. Handle connection failures gracefully
5. Monitor subscription lag

### Topic Design
1. Design topics for the future, not just current needs
2. Keep hierarchy depth reasonable (< 6 levels)
3. Use wildcards judiciously in subscriptions
4. Avoid very high-frequency topics on single clients
5. Consider message retention requirements

### Monitoring
1. Monitor topic message rates
2. Track subscription patterns
3. Alert on unusual topic activity
4. Monitor MQTT broker performance
5. Track message delivery success rates

## Troubleshooting

### Common Issues
- **Permission Denied**: Check ACL configuration and user permissions
- **Messages Not Delivered**: Verify QoS settings and network connectivity
- **Topic Not Found**: Ensure topic follows naming conventions
- **High Latency**: Check broker load and network conditions
- **Message Loss**: Increase QoS level or check broker persistence

### Debugging Tools
```bash
# Monitor all LICS topics
mosquitto_sub -h mqtt.lics.local -t "lics/#" -v

# Check broker statistics
mosquitto_sub -h mqtt.lics.local -t "\$SYS/#"

# Test specific topic publishing
mosquitto_pub -h mqtt.lics.local -t "lics/test" -m "test message"
```

This topic hierarchy provides a solid foundation for the LICS messaging architecture while maintaining flexibility for future growth and requirements.
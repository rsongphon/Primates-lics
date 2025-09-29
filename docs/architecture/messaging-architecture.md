# LICS Messaging Architecture Documentation

## Overview

This document provides a comprehensive guide to the messaging architecture implemented in the Lab Instrument Control System (LICS). The messaging infrastructure consists of three core components: MQTT for device communication, Redis for message queues and real-time updates, and MinIO for object storage.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                 LICS Messaging Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │    MQTT     │    │    Redis    │    │    MinIO    │    │
│  │   Broker    │    │  Streams &  │    │   Object    │    │
│  │             │    │   Pub/Sub   │    │   Storage   │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│         │                    │                    │        │
│         │                    │                    │        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Message Flow Orchestration              │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. MQTT Broker (Eclipse Mosquitto)

**Purpose**: Handles real-time device communication, command distribution, and telemetry collection.

**Configuration**:
- Development Port: 1884
- Production Port: 1883
- WebSocket Port: 9001/9002

**Key Features**:
- Authentication with role-based access
- Topic-based authorization (ACL)
- QoS levels for message reliability
- TLS/SSL support for production

**Files**:
- `infrastructure/mqtt/mosquitto.conf` - Production configuration
- `infrastructure/mqtt/mosquitto-dev.conf` - Development configuration
- `infrastructure/mqtt/setup-mqtt-auth.sh` - Authentication setup script
- `infrastructure/mqtt/passwords.txt` - User password file (generated)
- `infrastructure/mqtt/acl.txt` - Access control list
- `infrastructure/mqtt/topics-hierarchy.md` - Topic structure documentation

### 2. Redis (Streams & Pub/Sub)

**Purpose**: Provides message queuing, real-time communication, and event streaming capabilities.

**Configuration**:
- Development Port: 6380
- Production Port: 6379
- Database: 0 (default)

**Key Features**:
- Redis Streams for event sourcing
- Pub/Sub for real-time updates
- Message queues with priority levels
- Consumer groups for load balancing

**Files**:
- `infrastructure/redis/streams-setup.py` - Redis Streams configuration
- `infrastructure/redis/pubsub-config.py` - Pub/Sub channel setup

### 3. MinIO (Object Storage)

**Purpose**: Stores large files including videos, exports, uploads, and backups.

**Configuration**:
- Development Port: 9010 (API), 9011 (Console)
- Production Port: 9000 (API), 9001 (Console)
- Default Credentials: minioadmin/minioadmin (dev)

**Key Features**:
- S3-compatible API
- Bucket policies and lifecycle rules
- Versioning for critical buckets
- Automatic cleanup and archival

**Files**:
- `infrastructure/minio/bucket-init.sh` - Bucket initialization script
- `infrastructure/minio/apply-policies.sh` - Policy application script
- `infrastructure/minio/policies.json` - Bucket policies and lifecycle rules

## Message Flow Patterns

### 1. Device Communication Flow

```
Edge Device → MQTT Broker → Backend Service → Redis Streams → Processing
     ↓                                                           ↓
Telemetry Data                                            Data Storage
```

**Steps**:
1. Edge device publishes telemetry to MQTT topic
2. Backend service subscribes to device topics
3. Messages are processed and stored in Redis Streams
4. Consumer groups process messages for different purposes
5. Processed data is stored in databases or MinIO

### 2. Command Distribution Flow

```
Web UI → Backend API → Redis Queue → MQTT Publish → Edge Device
                           ↓                            ↓
                    Priority Queue                 Command Execution
```

**Steps**:
1. User initiates command through web interface
2. Backend service queues command in Redis with priority
3. Command processor publishes to MQTT command topic
4. Edge device receives and executes command
5. Acknowledgment sent back through MQTT

### 3. Real-time Updates Flow

```
Event Source → Redis Pub/Sub → WebSocket Server → Client Browser
      ↓              ↓              ↓                  ↓
System Event    Channel Routing   Connection Mgmt   UI Update
```

**Steps**:
1. System event occurs (device status change, etc.)
2. Event published to appropriate Redis Pub/Sub channel
3. WebSocket server subscribes to relevant channels
4. Real-time updates pushed to connected clients
5. Client UI updates dynamically

## Setup Procedures

### Initial Setup

1. **Prerequisites**:
   ```bash
   # Install required packages
   sudo apt update
   sudo apt install mosquitto mosquitto-clients redis-server python3-pip
   pip3 install redis paho-mqtt requests
   ```

2. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd Primates-lics
   make setup-dev-env
   ```

3. **Start Services**:
   ```bash
   # Using Docker Compose (recommended)
   docker-compose -f docker-compose.dev.yml up -d

   # Or manually start each service
   make dev
   ```

### MQTT Setup

1. **Initialize Authentication**:
   ```bash
   cd infrastructure/mqtt
   ./setup-mqtt-auth.sh setup
   ```

2. **Verify MQTT Health**:
   ```bash
   # Test connection
   mosquitto_pub -h localhost -p 1884 -t lics/test -m "hello"
   mosquitto_sub -h localhost -p 1884 -t lics/test

   # Test with authentication
   mosquitto_pub -h localhost -p 1884 -t lics/test -m "auth-test" \
     -u lics-backend -P <password-from-credentials-file>
   ```

### Redis Setup

1. **Initialize Streams and Pub/Sub**:
   ```bash
   cd infrastructure/redis
   python3 streams-setup.py --action setup
   python3 pubsub-config.py --action setup
   ```

2. **Verify Redis Health**:
   ```bash
   # Test Streams
   python3 streams-setup.py --action validate

   # Test Pub/Sub
   python3 pubsub-config.py --action test
   ```

### MinIO Setup

1. **Initialize Buckets**:
   ```bash
   cd infrastructure/minio
   ./bucket-init.sh init
   ```

2. **Apply Policies**:
   ```bash
   ./apply-policies.sh apply
   ```

3. **Verify MinIO Health**:
   ```bash
   # Check bucket status
   ./bucket-init.sh validate

   # Generate report
   ./bucket-init.sh report
   ```

### Health Monitoring

1. **Run Health Checks**:
   ```bash
   cd infrastructure/monitoring
   python3 messaging-health-check.py --service all
   ```

2. **Continuous Monitoring**:
   ```bash
   # Monitor every 60 seconds
   python3 messaging-health-check.py --continuous --interval 60

   # Output Prometheus metrics
   python3 messaging-health-check.py --format prometheus
   ```

## Message Formats and Schemas

### MQTT Message Format

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "device_id": "rpi-001",
  "message_type": "telemetry|command|status|event",
  "data": {
    "metric": "temperature",
    "value": 23.5,
    "unit": "celsius"
  },
  "metadata": {
    "lab_id": "lab-001",
    "experiment_id": "exp-123",
    "quality": "high"
  }
}
```

### Redis Stream Message Format

```json
{
  "id": "1641989445123-0",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "event_type": "device_telemetry",
  "source": "device:rpi-001",
  "data": {
    "temperature": 23.5,
    "humidity": 65.2,
    "location": "cage-12"
  },
  "metadata": {
    "processing_required": true,
    "priority": "normal"
  }
}
```

### Redis Pub/Sub Message Format

```json
{
  "type": "real_time_update",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "channel": "lics:devices:rpi-001:status",
  "data": {
    "status": "running",
    "cpu_percent": 45.2,
    "memory_percent": 62.1
  },
  "target_audience": ["dashboard", "monitoring"]
}
```

## Topic and Channel Structure

### MQTT Topics

```
lics/
├── labs/{lab_id}/
│   ├── devices/{device_id}/
│   │   ├── telemetry/{metric}      # QoS 0
│   │   ├── commands/{command}      # QoS 1
│   │   ├── status                  # QoS 1
│   │   └── heartbeat              # QoS 0
│   └── experiments/{exp_id}/
│       ├── events                  # QoS 1
│       └── data                    # QoS 1
├── system/
│   ├── events                      # QoS 1
│   ├── alerts                      # QoS 1
│   └── heartbeat                   # QoS 0
└── admin/
    ├── commands                    # QoS 2
    └── status                      # QoS 1
```

### Redis Streams

```
lics:streams:device_telemetry      # Device sensor data
lics:streams:device_commands       # Commands to devices
lics:streams:device_events         # Device lifecycle events
lics:streams:experiment_events     # Experiment events
lics:streams:system_events         # System-wide events
lics:streams:task_updates          # Task execution updates
```

### Redis Pub/Sub Channels

```
lics:devices:*:status              # Device status updates
lics:experiments:*:progress        # Experiment progress
lics:system:notifications          # System notifications
lics:realtime:*                    # Real-time UI updates
lics:users:*:notifications         # User notifications
lics:alerts:*                      # System alerts
```

### MinIO Buckets

```
lics-videos/                       # Video recordings
├── experiments/
├── live-streams/
└── recordings/

lics-data/                         # Experimental data
├── telemetry/
├── experiments/
└── raw/

lics-exports/                      # Generated reports
├── reports/
├── csv/
└── pdf/

lics-uploads/                      # User uploads
├── user-files/
├── firmware/
└── profiles/

lics-config/                       # Configuration files
├── tasks/
├── devices/
└── templates/

lics-backups/                      # System backups
lics-temp/                         # Temporary files
lics-assets/                       # Static assets
lics-logs/                         # Log files
lics-ml/                          # ML models and data
```

## Security Considerations

### MQTT Security

1. **Authentication**: All clients must authenticate with username/password
2. **Authorization**: Topic-based ACL controls access per user role
3. **Transport Security**: TLS encryption for production deployments
4. **Message Validation**: Input validation on all received messages

### Redis Security

1. **Network Security**: Redis bound to localhost or private network
2. **Authentication**: Password protection enabled
3. **Command Filtering**: Dangerous commands disabled
4. **Data Encryption**: Optional encryption for sensitive data

### MinIO Security

1. **Access Control**: IAM policies for bucket and object access
2. **Encryption**: Server-side encryption for sensitive buckets
3. **Network Security**: API access restricted to authorized clients
4. **Audit Logging**: All API calls logged for compliance

## Performance Optimization

### MQTT Optimization

1. **Connection Pooling**: Reuse connections where possible
2. **QoS Selection**: Use appropriate QoS levels for message types
3. **Message Batching**: Batch small messages for efficiency
4. **Keep-Alive Tuning**: Optimize keep-alive intervals

### Redis Optimization

1. **Memory Management**: Configure appropriate memory limits
2. **Persistence Settings**: Balance between performance and durability
3. **Pipeline Operations**: Use pipelining for bulk operations
4. **Connection Pooling**: Maintain connection pools for efficiency

### MinIO Optimization

1. **Multipart Uploads**: Use for large files
2. **Lifecycle Policies**: Automatic cleanup of old data
3. **Compression**: Enable for appropriate file types
4. **CDN Integration**: Use CDN for frequently accessed assets

## Troubleshooting

### Common Issues

1. **MQTT Connection Failures**:
   - Check firewall rules and network connectivity
   - Verify authentication credentials
   - Confirm broker is running and accepting connections
   - Check TLS certificate validity (production)

2. **Redis Performance Issues**:
   - Monitor memory usage and configure limits
   - Check for slow queries using SLOWLOG
   - Verify persistence settings
   - Monitor connection pool exhaustion

3. **MinIO Access Issues**:
   - Verify bucket policies and user permissions
   - Check network connectivity and DNS resolution
   - Confirm SSL/TLS configuration
   - Monitor storage capacity and quota limits

### Diagnostic Commands

```bash
# MQTT Debugging
mosquitto_sub -h localhost -p 1884 -t lics/# -v

# Redis Debugging
redis-cli monitor
redis-cli --latency-history

# MinIO Debugging
mc admin info minio-alias
mc admin trace minio-alias
```

### Log Locations

- **MQTT Logs**: `/mosquitto/log/mosquitto.log`
- **Redis Logs**: Container logs via `docker logs redis-dev`
- **MinIO Logs**: Container logs via `docker logs minio-dev`
- **Health Check Logs**: `infrastructure/monitoring/messaging-health-check.log`

## Monitoring and Alerting

### Key Metrics to Monitor

1. **MQTT Broker**:
   - Active connections
   - Message throughput
   - Queue lengths
   - Authentication failures

2. **Redis**:
   - Memory usage
   - Operations per second
   - Stream lengths
   - Connection count

3. **MinIO**:
   - Storage usage
   - Request rates
   - Error rates
   - Upload/download speeds

### Alerting Rules

1. **Critical Alerts**:
   - Service unavailability
   - Authentication system failures
   - Storage capacity exceeded
   - Message queue overflow

2. **Warning Alerts**:
   - High memory usage (>80%)
   - Slow response times
   - Unusual error rates
   - Disk space warnings

## Future Enhancements

### Planned Improvements

1. **Scalability**:
   - MQTT broker clustering
   - Redis cluster mode
   - MinIO distributed deployment
   - Load balancing

2. **Security**:
   - Certificate-based authentication
   - Advanced encryption options
   - Audit trail enhancements
   - Zero-trust networking

3. **Features**:
   - Message compression
   - Advanced routing rules
   - Real-time analytics
   - Machine learning integration

### Migration Considerations

1. **Version Upgrades**:
   - Backward compatibility testing
   - Data migration scripts
   - Rollback procedures
   - Documentation updates

2. **Scaling Out**:
   - Horizontal scaling strategies
   - Data partitioning approaches
   - Load balancing configuration
   - Performance testing

## Conclusion

The LICS messaging architecture provides a robust, scalable foundation for laboratory automation and real-time communication. The combination of MQTT for device communication, Redis for message processing, and MinIO for storage creates a comprehensive messaging ecosystem that supports the diverse needs of modern research environments.

Regular monitoring, maintenance, and optimization ensure the system continues to meet performance and reliability requirements as the platform scales and evolves.

---

**Document Version**: 1.0
**Last Updated**: January 2024
**Maintained By**: LICS Development Team
# Lab Instrument Control System (LICS)
## Comprehensive Implementation Documentation

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Frontend Implementation](#4-frontend-implementation)
5. [Backend Services](#5-backend-services)
6. [Database Design](#6-database-design)
7. [Edge Device Architecture](#7-edge-device-architecture)
8. [Communication Protocols](#8-communication-protocols)
9. [Task Builder System](#9-task-builder-system)
10. [Security Implementation](#10-security-implementation)
11. [DevOps & Deployment](#11-devops--deployment)
12. [Local Server Deployment](#12-local-server-deployment)
13. [Monitoring & Observability](#13-monitoring--observability)
14. [Data Flow Patterns](#14-data-flow-patterns)
15. [Scalability Strategies](#15-scalability-strategies)
16. [Testing Strategy](#16-testing-strategy)
17. [Implementation Roadmap](#17-implementation-roadmap)
18. [Primate Research Specialization](#18-primate-research-specialization)

---

## 1. System Overview

### 1.1 Project Vision
The Lab Instrument Control System (LICS) represents a paradigm shift in laboratory automation, providing a cloud-native, distributed platform for managing multiple cage-based experimental devices. The system enables researchers to design, deploy, and monitor behavioral experiments remotely while maintaining real-time control over edge devices.

**Primary Research Focus**: LICS is specifically designed for **non-human primate behavioral research**, supporting cognitive, visual, auditory, and motor task paradigms. The system provides comprehensive subject management, experiment lifecycle tracking, and data collection for primate neuroscience studies.

### 1.2 Core Architecture Principles

#### Microservices Architecture
The system follows a microservices pattern with clear separation of concerns:
- **API Gateway (Kong/Traefik)**: Central entry point managing routing, rate limiting, and authentication
- **FastAPI Core Backend**: RESTful API services handling business logic
- **WebSocket Server**: Real-time bidirectional communication service
- **Task Engine (Celery)**: Asynchronous task processing for heavy workloads
- **Auth Service (OAuth2)**: Centralized authentication and authorization
- **Streaming Service**: WebRTC/HLS video streaming management

#### Event-Driven Architecture
The system implements event sourcing and CQRS patterns:
- Commands flow through the API Gateway to appropriate services
- Events are published to Redis Streams/Kafka for consumption
- Read models are optimized separately from write models
- Event replay capability for audit and debugging

#### Edge Computing Model
Edge devices operate semi-autonomously:
- Local SQLite database for offline operation
- Intelligent sync mechanisms with cloud
- Local decision-making capabilities
- Graceful degradation during network issues

### 1.3 Key Differentiators

#### No-Code Task Builder
A revolutionary visual programming interface allowing researchers to create complex experimental protocols without coding knowledge. The builder generates JSON-based task definitions that are interpreted by edge devices.

#### Plug-and-Play Hardware Integration
Automatic discovery and configuration of sensors and actuators through a standardized registration protocol. Devices self-report capabilities and receive configuration automatically.

#### Real-Time Distributed Control
WebSocket and MQTT-based communication enabling sub-100ms latency control of multiple devices simultaneously with guaranteed message delivery and ordering.

---

## 2. System Architecture Diagram

### 2.1 High-Level Architecture with Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                  Cloud Infrastructure (AWS/GCP/Azure)            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │          Application Layer (Kubernetes Cluster)            │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │            API Gateway (Kong/Traefik)                │ │ │
│  │  └───────────┬──────────┬───────────┬──────────────────┘ │ │
│  │              │          │           │                     │ │
│  │  ┌───────────▼──┐ ┌────▼─────┐ ┌──▼──────────┐         │ │
│  │  │ Next.js SSR  │ │ FastAPI  │ │ WebSocket   │         │ │
│  │  │ Frontend     │ │ Core     │ │ Server      │         │ │
│  │  │ (Port 3000)  │ │ Backend  │ │ (Port 8001) │         │ │
│  │  └──────────────┘ │(Port 8000)│ └─────────────┘         │ │
│  │                   └──────────┘                           │ │
│  │                                                          │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐    │ │
│  │  │ Task Engine  │ │ Auth Service │ │ Streaming   │    │ │
│  │  │ (Celery)     │ │ (OAuth2)     │ │ Service     │    │ │
│  │  └──────────────┘ └──────────────┘ └─────────────┘    │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │            Data Layer (Managed Services)                   │ │
│  │                                                            │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │ │
│  │  │ PostgreSQL   │ │ Redis        │ │ InfluxDB     │     │ │
│  │  │ (Primary DB) │ │(Cache/Queue) │ │(Time Series) │     │ │
│  │  │+ TimescaleDB │ │ Cluster      │ │ Cluster      │     │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘     │ │
│  │                                                            │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │ │
│  │  │ MinIO        │ │Elasticsearch │ │ Grafana      │     │ │
│  │  │(Object Store)│ │(Search/Logs) │ │ (Monitoring) │     │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘     │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ MQTT Broker Cluster │
                    │ (EMQX/Mosquitto)    │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐    ┌───────▼────────┐    ┌───────▼────────┐
│ Edge Device 1  │    │ Edge Device 2  │    │ Edge Device N  │
│                │    │                │    │                │
│ ┌────────────┐ │    │ ┌────────────┐ │    │ ┌────────────┐ │
│ │ Edge Agent │ │    │ │ Edge Agent │ │    │ │ Edge Agent │ │
│ │  Python    │ │    │ │  Python    │ │    │ │  Python    │ │
│ └────────────┘ │    │ └────────────┘ │    │ └────────────┘ │
│                │    │                │    │                │
│ ┌────────────┐ │    │ ┌────────────┐ │    │ ┌────────────┐ │
│ │   SQLite   │ │    │ │   SQLite   │ │    │ │   SQLite   │ │
│ │Local Cache │ │    │ │Local Cache │ │    │ │Local Cache │ │
│ └────────────┘ │    │ └────────────┘ │    │ └────────────┘ │
│                │    │                │    │                │
│ ┌────────────┐ │    │ ┌────────────┐ │    │ ┌────────────┐ │
│ │    GPIO    │ │    │ │    GPIO    │ │    │ │    GPIO    │ │
│ │ Controller │ │    │ │ Controller │ │    │ │ Controller │ │
│ └────────────┘ │    │ └────────────┘ │    │ └────────────┘ │
└────────────────┘    └────────────────┘    └────────────────┘
```

### 2.2 Data Flow Patterns

#### Command Flow (Top-Down)
```
User Interface → API Gateway → Backend Service → MQTT Broker → Edge Device
     ↓              ↓              ↓                ↓            ↓
  Request      Authenticate    Process         Publish      Execute
              & Route         Command         Message      Command
```

#### Telemetry Flow (Bottom-Up)
```
Sensor → Edge Device → MQTT Broker → Backend Service → Database → UI
   ↓          ↓            ↓              ↓              ↓        ↓
Collect    Buffer      Publish       Process         Store    Display
Data      Locally     Telemetry      & Route        Data      Real-time
```

#### Real-Time Updates (Bidirectional)
```
WebSocket Server ↔ Client Applications
       ↓                    ↓
  Maintain            Subscribe to
  Connections          Events
       ↓                    ↓
   Broadcast           Update UI
   Changes            Real-time
```

### 2.3 Network Architecture

#### Security Zones
```
┌─────────────────────────────────────────────────────────┐
│                    Public Zone                          │
│  - API Gateway (HTTPS)                                  │
│  - Web Application (CDN)                                │
└────────────────────▲────────────────────────────────────┘
                     │ Firewall / WAF
┌────────────────────▼────────────────────────────────────┐
│                Application Zone                         │
│  - Kubernetes Cluster                                   │
│  - Backend Services                                     │
│  - Internal Load Balancers                             │
└────────────────────▲────────────────────────────────────┘
                     │ Network Policies
┌────────────────────▼────────────────────────────────────┐
│                    Data Zone                            │
│  - Database Clusters                                    │
│  - Cache Layers                                         │
│  - Message Queues                                       │
└────────────────────▲────────────────────────────────────┘
                     │ VPN / Private Link
┌────────────────────▼────────────────────────────────────┐
│                    Edge Zone                            │
│  - Edge Devices                                         │
│  - Local Networks                                       │
│  - IoT Gateways                                        │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Deep Dive

### 3.1 Cloud Infrastructure Layer

#### Kubernetes Cluster Architecture
The system runs on a managed Kubernetes cluster (EKS/GKE/AKS) with the following node pools:

**Control Plane Nodes**: 
- Master nodes managed by cloud provider
- etcd cluster for configuration storage
- API server with admission controllers
- Scheduler and controller managers

**Application Node Pool**:
- General-purpose nodes (4-16 vCPUs, 16-64GB RAM)
- Hosts stateless application services
- Auto-scaling based on CPU/memory metrics
- Spot/preemptible instances for cost optimization

**Database Node Pool**:
- Memory-optimized nodes for database services
- Local NVMe SSDs for performance
- Dedicated nodes with taints to prevent other workloads
- Anti-affinity rules for HA

**GPU Node Pool** (Optional):
- For ML inference and video processing
- NVIDIA T4 or similar GPUs
- Used for real-time video analysis

### 3.2 Application Layer Architecture

#### API Gateway Pattern
The Kong/Traefik API Gateway serves as the single entry point:

**Request Flow**:
1. TLS termination at ingress
2. JWT validation and rate limiting
3. Request routing based on path/headers
4. Load balancing to backend services
5. Response caching where appropriate
6. Metrics and logging

**Gateway Plugins**:
- Rate limiting: Token bucket algorithm with Redis backend
- Authentication: JWT validation with public key caching
- CORS: Dynamic origin validation
- Request/Response transformation
- Circuit breaker for fault tolerance

#### Service Mesh Considerations
For advanced deployments, Istio/Linkerd provides:
- mTLS between services
- Fine-grained traffic management
- Distributed tracing
- Service-level authorization
- Canary deployments

### 3.3 Data Layer Architecture

#### Primary Database Cluster (PostgreSQL + TimescaleDB)
**Master-Replica Setup**:
- Primary node handles writes
- 2+ read replicas for query distribution
- Streaming replication with < 1s lag
- Automatic failover using Patroni
- Connection pooling via PgBouncer

**TimescaleDB Hypertables**:
- Automatic partitioning by time
- Compression for older data (10:1 ratio typical)
- Continuous aggregates for real-time analytics
- Data retention policies per measurement type

#### Caching Layer (Redis Cluster)
**Cluster Configuration**:
- 6 nodes minimum (3 masters, 3 replicas)
- Hash slot distribution (16384 slots)
- Automatic resharding during scaling
- Persistence with AOF + RDB snapshots

**Cache Strategies**:
- Write-through for critical data
- Write-behind for performance optimization
- Cache-aside for complex queries
- TTL-based expiration with refresh

#### Time-Series Database (InfluxDB)
**Data Organization**:
- Separate databases per experiment type
- Measurement schemas for each sensor type
- Field keys for sensor readings
- Tag keys for device/experiment metadata
- Downsampling policies for long-term storage

### 3.4 Message Broker Architecture

#### MQTT Broker Cluster (EMQX/Mosquitto)
**Cluster Topology**:
- 3+ broker nodes for HA
- Shared subscriptions for load balancing
- Persistent sessions for reliability
- Bridge connections to cloud MQTT services

**Topic Hierarchy**:
```
labs/{lab_id}/devices/{device_id}/telemetry
labs/{lab_id}/devices/{device_id}/commands
labs/{lab_id}/devices/{device_id}/status
labs/{lab_id}/experiments/{exp_id}/events
labs/{lab_id}/experiments/{exp_id}/data
```

**QoS Levels**:
- QoS 0: Status updates, non-critical telemetry
- QoS 1: Commands, configuration updates
- QoS 2: Critical experiment data

---

## 4. Frontend Implementation

### 4.1 Next.js Application Architecture

#### Project Structure
```
frontend/
├── app/                    # Next.js 14 App Router
│   ├── (auth)/            # Auth-required routes
│   │   ├── dashboard/
│   │   ├── devices/
│   │   ├── experiments/
│   │   └── tasks/
│   ├── (public)/          # Public routes
│   │   ├── login/
│   │   └── register/
│   ├── api/               # API routes (BFF pattern)
│   └── layout.tsx         # Root layout
├── components/
│   ├── ui/                # Shadcn components
│   ├── features/          # Feature-specific components
│   └── shared/            # Shared components
├── lib/
│   ├── api/               # API client functions
│   ├── hooks/             # Custom React hooks
│   ├── stores/            # Zustand stores
│   └── utils/             # Utility functions
└── public/                # Static assets
```

#### Server Components vs Client Components
**Server Components** (default):
- Data fetching at request time
- SEO-critical content
- Static content that rarely changes
- Initial page shells

**Client Components** (use client):
- Interactive UI elements
- Real-time data displays
- Form handling
- WebSocket connections
- Task builder interface

### 4.2 State Management Architecture

#### Zustand Store Structure
**Global Store**:
Manages application-wide state including user session, theme preferences, and notification queue. Implements persistence middleware for offline support and optimistic updates.

**Device Store**:
Maintains real-time device status, connection states, and telemetry data. Subscribes to WebSocket events for automatic updates. Implements efficient update batching to prevent excessive re-renders.

**Experiment Store**:
Tracks active experiments, their progress, and collected data. Manages complex state transitions during experiment lifecycle. Provides computed values for analytics dashboards.

**Task Builder Store**:
Manages the visual flow editor state including nodes, edges, and validation. Implements undo/redo functionality with command pattern. Exports task definitions in standardized JSON format.

#### React Query Configuration
**Query Client Setup**:
- Stale time: 5 minutes for static data, 10 seconds for dynamic
- Cache time: 10 minutes with background refetching
- Retry logic: Exponential backoff with 3 attempts
- Optimistic updates for mutations
- Query invalidation on WebSocket events

**Query Patterns**:
- Prefetching on route navigation
- Infinite queries for log streams
- Parallel queries for dashboard data
- Dependent queries for hierarchical data
- Mutation queues for offline support

### 4.3 Real-Time Features

#### WebSocket Integration
**Connection Management**:
Socket.io client with automatic reconnection, exponential backoff, and connection state tracking. Implements heartbeat mechanism for connection health monitoring.

**Event Handling**:
Typed event system with TypeScript interfaces. Event aggregation for high-frequency updates. Automatic subscription management based on component lifecycle.

**Room-Based Architecture**:
Dynamic room joining based on user permissions. Automatic cleanup on disconnection. Broadcast optimization for large-scale deployments.

#### WebRTC Video Streaming
**Peer Connection Setup**:
STUN/TURN server configuration for NAT traversal. Adaptive bitrate based on network conditions. Fallback to HLS for compatibility.

**Stream Management**:
Multiple stream support per device. Quality selection (SD/HD/FHD). Recording capabilities with cloud upload. Screenshot functionality for documentation.

### 4.4 Task Builder Implementation

#### React Flow Configuration
**Custom Node Types**:
- Start/End nodes with validation
- Action nodes for device control
- Decision nodes with branching logic
- Loop nodes with iteration control
- Data collection nodes
- Wait/Timer nodes
- Parallel execution nodes

**Edge Validation**:
Type-safe connections between nodes. Cycle detection for infinite loops. Path validation for reachability. Parameter type checking between nodes.

**Visual Enhancements**:
Mini-map for large flows. Grid snapping for alignment. Grouping for logical sections. Theming for different node categories. Animated edges for flow visualization.

#### Task Definition Generation
**JSON Schema**:
Standardized schema with version control. Validation against schema before deployment. Migration strategies for schema updates. Backward compatibility guarantees.

**Compilation Process**:
Visual flow to JSON transformation. Optimization passes for efficiency. Validation for device compatibility. Test execution in sandbox environment.

---

## 5. Backend Services

### 5.1 FastAPI Application Architecture

#### Service Layer Design
**Repository Pattern**:
Each domain entity has a dedicated repository handling database operations. Repositories abstract database complexity and provide consistent interfaces. Support for both sync and async operations.

**Service Classes**:
Business logic encapsulated in service classes. Dependency injection for testability. Transaction management at service level. Event emission for cross-service communication.

**Domain Models**:
Pydantic models for request/response validation. SQLAlchemy models for database entities. Clear separation between DTOs and domain models. Automatic serialization/deserialization.

#### API Endpoint Structure
**RESTful Design**:
- GET endpoints for resource retrieval with filtering/pagination
- POST endpoints for resource creation with validation
- PUT/PATCH for updates with optimistic locking
- DELETE with soft-delete support
- Batch operations for efficiency

**GraphQL Considerations**:
Optional GraphQL layer for complex queries. Reduces over-fetching for mobile clients. Subscription support for real-time updates. Schema federation for microservices.

### 5.2 Authentication & Authorization

#### JWT Implementation
**Token Structure**:
- Access token: 15-minute expiry, minimal claims
- Refresh token: 7-day expiry, stored in httpOnly cookie
- ID token: User profile information
- Device token: Long-lived for edge devices

**Token Rotation**:
Automatic refresh before expiry. Blacklisting for revoked tokens. Sliding sessions for active users. Device-specific refresh strategies.

#### RBAC Implementation
**Role Hierarchy**:
- Super Admin: Full system access
- Lab Admin: Lab-specific management
- Researcher: Experiment creation/management
- Observer: Read-only access
- Device: Automated device operations

**Permission System**:
Fine-grained permissions per resource. Dynamic permission calculation. Permission inheritance from roles. Audit logging for all authorization decisions.

### 5.3 Task Queue Architecture

#### Celery Configuration
**Worker Types**:
- Default workers: General tasks
- Heavy workers: Data processing
- Real-time workers: Time-sensitive operations
- Scheduled workers: Periodic tasks

**Task Routing**:
Queue-based routing by task type. Priority queues for critical operations. Dead letter queues for failed tasks. Rate limiting per task type.

**Result Backend**:
Redis for short-lived results. PostgreSQL for persistent results. S3 for large result files. Automatic cleanup policies.

#### Background Tasks
**Data Processing Pipeline**:
- Raw data ingestion from devices
- Validation and cleaning
- Aggregation and computation
- Storage in appropriate databases
- Cache warming for dashboards

**Report Generation**:
Template-based report creation. Multi-format support (PDF/Excel/CSV). Scheduled generation with email delivery. Custom report builder interface.

### 5.4 WebSocket Server

#### Connection Management
**Client Authentication**:
JWT validation on connection. Permission checking for rooms. Automatic disconnection on token expiry. Re-authentication without disconnection.

**Session Management**:
Redis-backed session storage. Session migration across servers. Presence tracking for users. Connection pooling for scalability.

#### Message Broadcasting
**Broadcast Types**:
- Unicast: Direct device communication
- Multicast: Group notifications
- Broadcast: System-wide announcements
- Request-Response: Acknowledged messages

**Message Queue Integration**:
Redis Streams for message persistence. Kafka for high-throughput scenarios. Message ordering guarantees. At-least-once delivery semantics.

---

## 6. Database Design

### 6.1 PostgreSQL Schema Design

#### Core Domain Tables

**Organizations Table**:
Multi-tenant support with organization isolation. Hierarchical structure for departments/labs. Feature flags per organization. Billing and usage tracking.

**Users Table**:
Standard user fields with secure password storage. Multi-factor authentication support. Profile customization options. Audit fields for compliance.

**Devices Table**:
Comprehensive device registry with capabilities. Hardware configuration storage. Calibration data management. Maintenance history tracking.

**Experiments Table**:
Complete experiment lifecycle tracking. Protocol versioning support. Participant/subject management. Result aggregation fields.

**Tasks Table**:
Visual flow definitions storage. Parameter schemas for validation. Version control with rollback. Template library support.

#### Relationship Design
**Many-to-Many Relationships**:
Junction tables with additional metadata. Temporal relationships with validity periods. Soft-delete support for history. Efficient indexing strategies.

**Hierarchical Data**:
LTREE extension for tree structures. Recursive CTEs for queries. Materialized paths for performance. Closure tables for complex hierarchies.

### 6.2 TimescaleDB Configuration

#### Hypertable Design
**Telemetry Data Table**:
- Time-based partitioning (daily chunks)
- Space partitioning by device_id
- Automated chunk management
- Compression after 7 days
- Retention policies per data type

**Continuous Aggregates**:
- 1-minute aggregates for real-time
- Hourly aggregates for dashboards
- Daily aggregates for reports
- Refresh policies with lag tolerance

#### Performance Optimization
**Indexing Strategy**:
- B-tree indexes for equality queries
- BRIN indexes for time ranges
- GIN indexes for JSONB fields
- Partial indexes for common filters
- Index maintenance automation

**Query Optimization**:
- Chunk exclusion for time queries
- Parallel query execution
- JIT compilation for complex queries
- Connection pooling with PgBouncer
- Read replica routing

### 6.3 Redis Data Structures

#### Cache Design Patterns
**Entity Caching**:
Hash structures for object storage. TTL management per entity type. Cache warming strategies. Invalidation on updates.

**Session Storage**:
Redis hashes for session data. Sliding expiration windows. Session migration support. Concurrent access handling.

**Rate Limiting**:
Sliding window counters. Distributed rate limiting. Per-user/per-endpoint limits. Graceful degradation.

#### Pub/Sub Patterns
**Channel Design**:
Hierarchical channel structure. Pattern-based subscriptions. Message persistence with Streams. Acknowledgment mechanisms.

### 6.4 InfluxDB Schema

#### Measurement Design
**Sensor Data**:
- Measurement per sensor type
- Tags for device/experiment metadata  
- Fields for sensor readings
- Optimized tag cardinality

**System Metrics**:
CPU, memory, disk, network metrics. Application-level metrics. Custom business metrics. Alerting thresholds.

#### Retention Policies
**Data Lifecycle**:
- Raw data: 7 days
- Downsampled (1min): 30 days
- Downsampled (1hr): 1 year
- Downsampled (1day): Indefinite

---

## 7. Edge Device Architecture

### 7.1 Edge Agent Design

#### Component Architecture
**Device Manager**:
Central orchestrator managing all device operations. State machine for device lifecycle. Configuration management with hot reload. Health monitoring and reporting.

**Task Executor**:
Interprets and executes task definitions. State management during execution. Error handling and recovery. Progress reporting to cloud.

**GPIO Controller**:
Hardware abstraction layer for GPIO operations. Support for multiple GPIO libraries. Interrupt handling for sensors. PWM control for actuators.

**Communication Module**:
Manages all network communication. Connection pooling and retry logic. Message queuing for reliability. Bandwidth optimization.

### 7.2 Hardware Integration

#### Sensor Integration Patterns
**Polling Sensors**:
Configurable polling intervals. Averaging and filtering. Anomaly detection. Calibration support.

**Interrupt-Driven Sensors**:
Edge detection configuration. Debouncing logic. Event aggregation. Priority handling.

**Serial/I2C/SPI Sensors**:
Protocol abstraction layers. Error detection and correction. Multi-device support. Hot-plug capabilities.

#### Actuator Control
**PWM Devices**:
Precise duty cycle control. Ramping for smooth transitions. Safety limits enforcement. Feedback loop integration.

**Digital Outputs**:
State management and verification. Timing precision for protocols. Safety interlocks. Manual override support.

### 7.3 Local Storage

#### SQLite Database Design
**Schema**:
- Configuration tables
- Task queue tables
- Telemetry buffer tables
- Sync status tracking

**Optimization**:
WAL mode for concurrency. Periodic VACUUM operations. Index optimization. Size management.

#### Data Synchronization
**Sync Strategy**:
- Real-time sync when online
- Batch sync for efficiency
- Conflict resolution rules
- Compression for transfer

**Offline Operation**:
Queue commands locally. Continue data collection. Sync on reconnection. Alert on storage limits.

### 7.4 Browser Automation

#### Playwright Configuration
**Browser Setup**:
Headless Chromium for efficiency. Custom user agent strings. Proxy configuration support. Extension loading capability.

**Task Execution**:
Page object pattern implementation. Robust element selection. Retry logic for actions. Screenshot on errors.

**Performance**:
Resource usage monitoring. Memory leak prevention. Browser recycling. Parallel execution support.

---

## 8. Communication Protocols

### 8.1 MQTT Protocol Implementation

#### Topic Design
**Topic Hierarchy**:
Structured topic naming for organization. Wildcard subscriptions for monitoring. Access control per topic. Topic aliases for efficiency.

**Message Format**:
JSON payloads with schema validation. Binary payloads for efficiency. Compression for large messages. Encryption for sensitive data.

#### QoS Strategies
**QoS Level Selection**:
- QoS 0: Telemetry, status updates
- QoS 1: Commands, configurations  
- QoS 2: Critical experiment data

**Message Persistence**:
Retained messages for last known state. Clean session management. Message expiry handling. Offline message queuing.

### 8.2 WebSocket Protocol

#### Connection Lifecycle
**Handshake Process**:
- Initial HTTP upgrade request
- Authentication via query params
- Protocol negotiation
- Compression negotiation

**Keep-Alive Mechanism**:
Ping/pong frames every 30 seconds. Automatic reconnection on failure. Exponential backoff strategy. Connection state recovery.

#### Message Framing
**Frame Types**:
- Text frames for JSON
- Binary frames for media
- Close frames for disconnection
- Ping/pong for keep-alive

**Multiplexing**:
Multiple logical channels per connection. Message ordering per channel. Flow control per channel. Priority-based scheduling.

### 8.3 REST API Design

#### API Versioning
**Version Strategy**:
URL path versioning (/api/v1/). Backward compatibility commitment. Deprecation notices in headers. Migration guides for changes.

#### Response Format
**Standard Response**:
```json
{
  "data": {},
  "meta": {
    "timestamp": "",
    "version": ""
  },
  "pagination": {},
  "links": {}
}
```

**Error Response**:
```json
{
  "error": {
    "code": "",
    "message": "",
    "details": {},
    "trace_id": ""
  }
}
```

---

## 9. Task Builder System

### 9.1 Visual Programming Interface

#### Node System Design
**Node Categories**:
- Control Flow: Start, End, Branch, Loop
- Actions: GPIO, Display, Sound, Wait
- Data: Collect, Transform, Validate
- Communication: Send, Receive, Broadcast
- Logic: Compare, Calculate, Aggregate

**Node Properties**:
Unique identifiers for tracking. Input/output port definitions. Parameter schemas for configuration. Validation rules for connections. Visual styling information.

#### Connection Rules
**Type System**:
Strongly typed connections. Type inference for compatibility. Automatic type conversion where safe. Error highlighting for mismatches.

**Flow Validation**:
DAG enforcement (no cycles unless in loops). Reachability analysis from start. Dead code detection. Resource conflict detection.

### 9.2 Task Compilation

#### Compilation Pipeline
**Stages**:
1. Syntax validation
2. Semantic analysis  
3. Optimization passes
4. Device compatibility check
5. Code generation
6. Deployment package creation

**Optimization Strategies**:
Dead code elimination. Constant folding. Loop unrolling where beneficial. Parallel execution identification.

#### Runtime Interpretation
**Execution Engine**:
Stack-based virtual machine. Instruction set for all operations. Memory management for variables. Exception handling mechanisms.

**Performance Monitoring**:
Instruction counting for profiling. Memory usage tracking. Execution time measurement. Bottleneck identification.

### 9.3 Template Library

#### Template Management
**Categories**:
- Behavioral: Standard paradigms
- Cognitive: Memory, learning tasks
- Sensory: Visual, auditory tests
- Custom: User-created templates

**Sharing Mechanism**:
Template marketplace concept. Version control for templates. Rating and review system. Forking and modification support.

---

## 10. Security Implementation

### 10.1 Authentication Security

#### Password Security
**Storage**:
Argon2id hashing algorithm. Salt generation per password. Constant-time comparison. Password history enforcement.

**Password Policies**:
Minimum complexity requirements. Regular rotation encouragement. Breach database checking. Multi-factor enforcement for admins.

#### Session Security
**Token Security**:
Secure random generation. HttpOnly, Secure, SameSite cookies. CSRF protection tokens. XSS prevention measures.

**Session Management**:
Concurrent session limits. Geographic anomaly detection. Device fingerprinting. Automatic timeout policies.

### 10.2 Authorization Implementation

#### Access Control
**RBAC Implementation**:
Role-based permissions. Resource-based permissions. Attribute-based extensions. Dynamic permission calculation.

**Policy Engine**:
Declarative policy definitions. Policy evaluation caching. Audit logging for decisions. Performance optimization.

### 10.3 Data Security

#### Encryption
**At Rest**:
Database encryption with TDE. File system encryption. Key rotation policies. Hardware security modules.

**In Transit**:
TLS 1.3 minimum. Certificate pinning for apps. Perfect forward secrecy. HSTS enforcement.

#### Data Privacy
**PII Handling**:
Data minimization principles. Pseudonymization where possible. Right to deletion support. Data portability features.

**Compliance**:
GDPR compliance measures. HIPAA considerations for medical research. Audit trail requirements. Data residency controls.

### 10.4 Infrastructure Security

#### Network Security
**Firewall Rules**:
Principle of least privilege. Ingress/egress filtering. DDoS protection. Rate limiting at edge.

**Service Mesh Security**:
mTLS between services. Service-to-service authorization. Traffic encryption. Certificate rotation.

#### Container Security
**Image Security**:
Base image minimization. Vulnerability scanning. Signed images only. Regular rebuilds for patches.

**Runtime Security**:
Read-only filesystems. Non-root containers. Resource limits. Security policies (PSP/PSS).

---

## 11. DevOps & Deployment

### 11.1 CI/CD Pipeline

#### Build Pipeline
**Stages**:
1. Code checkout
2. Dependency installation
3. Linting and formatting
4. Unit test execution
5. Integration test execution
6. Security scanning
7. Docker image building
8. Image scanning
9. Artifact publishing

**Quality Gates**:
Code coverage thresholds (80%). No critical vulnerabilities. All tests passing. Performance benchmarks met.

#### Deployment Pipeline
**Environments**:
- Development: Continuous deployment
- Staging: Daily deployments
- Production: Weekly releases
- Hotfix: Emergency deployments

**Deployment Strategies**:
Blue-green for zero downtime. Canary for gradual rollout. Rolling updates for quick deployment. Rollback capabilities.

### 11.2 Infrastructure as Code

#### Terraform Configuration
**Module Structure**:
- Network module
- Kubernetes module
- Database module
- Storage module
- Monitoring module

**State Management**:
Remote state in S3/GCS. State locking with DynamoDB. Workspace separation. Import existing resources.

#### Kubernetes Manifests
**Helm Charts**:
Parameterized deployments. Dependency management. Hook mechanisms. Release management.

**GitOps Workflow**:
Flux/ArgoCD for deployments. Git as source of truth. Automatic synchronization. Drift detection.

### 11.3 Container Management

#### Docker Optimization
**Multi-Stage Builds**:
Build stage with full toolchain. Runtime stage with minimal image. Layer caching optimization. Size reduction techniques.

**Security Hardening**:
Non-root users. Minimal base images. No sensitive data in images. Regular vulnerability scanning.

#### Registry Management
**Image Storage**:
Private registry (Harbor/GitLab). Image signing and verification. Vulnerability scanning. Garbage collection policies.

---

## 12. Local Server Deployment

### 12.1 Local Deployment Architecture

#### System Requirements
**Hardware Requirements**:
- CPU: Minimum 8 cores (16 recommended)
- RAM: Minimum 32GB (64GB recommended)
- Storage: 500GB SSD minimum
- Network: Gigabit Ethernet
- GPU: Optional for ML features

**Software Requirements**:
- Operating System: Ubuntu 22.04 LTS / Rocky Linux 9
- Docker Engine: 24.0+
- Docker Compose: 2.20+
- Python: 3.11+
- Node.js: 20 LTS
- Git: 2.40+

### 12.2 Simplified Architecture for Local Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                    Local Server Machine                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Docker Compose Network                      ││
│  │                                                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ ││
│  │  │   Traefik    │  │   Frontend   │  │   Backend    │ ││
│  │  │   (Proxy)    │◄─┤  Next.js     │◄─┤   FastAPI    │ ││
│  │  │  Port: 80    │  │  Port: 3000  │  │  Port: 8000  │ ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘ ││
│  │                                                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ ││
│  │  │  PostgreSQL  │  │    Redis     │  │  InfluxDB    │ ││
│  │  │ +TimescaleDB │  │  Port: 6379  │  │  Port: 8086  │ ││
│  │  │  Port: 5432  │  └──────────────┘  └──────────────┘ ││
│  │  └──────────────┘                                       ││
│  │                                                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ ││
│  │  │   Mosquitto  │  │   MinIO      │  │   Grafana    │ ││
│  │  │ MQTT Broker  │  │ Object Store │  │  Monitoring  │ ││
│  │  │  Port: 1883  │  │  Port: 9000  │  │  Port: 3001  │ ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│                         Host Network                         │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
                   ┌───────────┼───────────┐
                   │           │           │
           ┌───────▼───────┐  │  ┌────────▼────────┐
           │ Edge Device 1 │  │  │  Edge Device N  │
           │  (Local LAN)  │  │  │   (Local LAN)   │
           └───────────────┘  │  └─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Web Browser      │
                    │  (User Interface)  │
                    └────────────────────┘
```

### 12.3 Docker Compose Configuration

#### Main docker-compose.yml
```yaml
version: '3.9'

services:
  # Reverse Proxy
  traefik:
    image: traefik:3.0
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Traefik dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik:/etc/traefik
      - ./certs:/certs
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`traefik.localhost`)"
    networks:
      - lics-network

  # Frontend Application
  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile.local
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost/api
      - NEXT_PUBLIC_WS_URL=ws://localhost/ws
    volumes:
      - ./frontend:/app
      - /app/node_modules
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=PathPrefix(`/`)"
      - "traefik.http.services.frontend.loadbalancer.server.port=3000"
    networks:
      - lics-network
    depends_on:
      - backend

  # Backend API
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile.local
    environment:
      - DATABASE_URL=postgresql://lics:password@postgres:5432/lics
      - REDIS_URL=redis://redis:6379
      - INFLUXDB_URL=http://influxdb:8086
      - MQTT_BROKER=mosquitto
      - MQTT_PORT=1883
      - MINIO_ENDPOINT=minio:9000
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./backend:/app
      - ./uploads:/app/uploads
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=PathPrefix(`/api`)"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
    networks:
      - lics-network
    depends_on:
      - postgres
      - redis
      - influxdb
      - mosquitto

  # PostgreSQL with TimescaleDB
  postgres:
    image: timescale/timescaledb-ha:pg15-latest
    environment:
      - POSTGRES_DB=lics
      - POSTGRES_USER=lics
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/home/postgres/pgdata
      - ./init-db:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      - lics-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - lics-network

  # InfluxDB Time Series Database
  influxdb:
    image: influxdb:2.7
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=password123
      - DOCKER_INFLUXDB_INIT_ORG=lics
      - DOCKER_INFLUXDB_INIT_BUCKET=telemetry
    volumes:
      - influxdb_data:/var/lib/influxdb2
    ports:
      - "8086:8086"
    networks:
      - lics-network

  # MQTT Broker
  mosquitto:
    image: eclipse-mosquitto:2
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log
    ports:
      - "1883:1883"
      - "9001:9001"  # WebSocket port
    networks:
      - lics-network

  # MinIO Object Storage
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=password123
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - lics-network

  # Grafana Monitoring
  grafana:
    image: grafana/grafana:10.0.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=redis-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3001:3000"
    networks:
      - lics-network
    depends_on:
      - influxdb
      - postgres

networks:
  lics-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  influxdb_data:
  mosquitto_data:
  mosquitto_log:
  minio_data:
  grafana_data:
```

### 12.4 Local Deployment Setup Script

#### setup-local.sh
```bash
#!/bin/bash

# LICS Local Deployment Setup Script
set -e

echo "==================================="
echo "LICS Local Deployment Setup"
echo "==================================="

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    echo "✅ Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    echo "✅ Docker Compose found: $(docker-compose --version)"
    
    # Check Git
    if ! command -v git &> /dev/null; then
        echo "❌ Git is not installed. Please install Git first."
        exit 1
    fi
    echo "✅ Git found: $(git --version)"
}

# Create directory structure
create_directories() {
    echo "Creating directory structure..."
    mkdir -p {backend,frontend,edge-agent,uploads}
    mkdir -p {postgres-data,redis-data,influxdb-data}
    mkdir -p mosquitto/{config,data,log}
    mkdir -p traefik/{dynamic,certs}
    mkdir -p grafana/{dashboards,datasources}
    echo "✅ Directories created"
}

# Generate environment file
generate_env_file() {
    echo "Generating environment configuration..."
    if [ ! -f .env ]; then
        cat > .env << EOF
# LICS Local Deployment Environment Variables
NODE_ENV=development
COMPOSE_PROJECT_NAME=lics

# Security
JWT_SECRET=$(openssl rand -hex 32)
ADMIN_PASSWORD=$(openssl rand -base64 12)

# Database
POSTGRES_DB=lics
POSTGRES_USER=lics
POSTGRES_PASSWORD=$(openssl rand -base64 16)

# Redis
REDIS_PASSWORD=$(openssl rand -base64 16)

# InfluxDB
INFLUXDB_ADMIN_TOKEN=$(openssl rand -hex 32)

# MinIO
MINIO_ACCESS_KEY=$(openssl rand -hex 16)
MINIO_SECRET_KEY=$(openssl rand -hex 32)

# MQTT
MQTT_USERNAME=lics
MQTT_PASSWORD=$(openssl rand -base64 16)

# Frontend
NEXT_PUBLIC_API_URL=http://localhost/api
NEXT_PUBLIC_WS_URL=ws://localhost/ws

# Backend
DATABASE_URL=postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@postgres:5432/\${POSTGRES_DB}
REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379
EOF
        echo "✅ Environment file created"
    else
        echo "⚠️  Environment file already exists, skipping..."
    fi
}

# Configure Traefik
configure_traefik() {
    echo "Configuring Traefik..."
    cat > traefik/traefik.yml << EOF
api:
  dashboard: true
  debug: true

entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
  file:
    directory: /etc/traefik/dynamic
    watch: true

log:
  level: INFO
  filePath: /var/log/traefik/traefik.log

accessLog:
  filePath: /var/log/traefik/access.log
EOF
    echo "✅ Traefik configured"
}

# Configure Mosquitto
configure_mosquitto() {
    echo "Configuring Mosquitto..."
    cat > mosquitto/config/mosquitto.conf << EOF
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log

# Default listener
listener 1883
protocol mqtt

# WebSocket listener
listener 9001
protocol websockets

# Authentication
allow_anonymous false
password_file /mosquitto/config/passwords.txt
EOF
    echo "✅ Mosquitto configured"
}

# Initialize database
init_database() {
    echo "Creating database initialization script..."
    cat > init-db/01-init.sql << EOF
-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create tables
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    status VARCHAR(50) DEFAULT 'offline',
    last_seen TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telemetry (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    device_id UUID REFERENCES devices(id),
    metric VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION,
    tags JSONB
);

-- Convert telemetry to TimescaleDB hypertable
SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX idx_telemetry_device_time ON telemetry(device_id, time DESC);
CREATE INDEX idx_devices_org ON devices(organization_id);
CREATE INDEX idx_users_org ON users(organization_id);
EOF
    echo "✅ Database initialization script created"
}

# Start services
start_services() {
    echo "Starting services..."
    docker-compose up -d
    echo "✅ Services started"
    
    echo ""
    echo "Waiting for services to be ready..."
    sleep 10
    
    echo ""
    echo "==================================="
    echo "LICS Local Deployment Complete!"
    echo "==================================="
    echo ""
    echo "Access points:"
    echo "  - Web Interface: http://localhost"
    echo "  - API: http://localhost/api"
    echo "  - Traefik Dashboard: http://localhost:8080"
    echo "  - Grafana: http://localhost:3001 (admin/admin)"
    echo "  - MinIO Console: http://localhost:9001"
    echo ""
    echo "Database connections:"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - InfluxDB: http://localhost:8086"
    echo "  - MQTT: localhost:1883"
    echo ""
    echo "To stop all services: docker-compose down"
    echo "To view logs: docker-compose logs -f [service-name]"
}

# Main execution
main() {
    check_prerequisites
    create_directories
    generate_env_file
    configure_traefik
    configure_mosquitto
    init_database
    start_services
}

# Run main function
main
```

### 12.5 Local Development Workflow

#### Development Mode Features
**Hot Reloading**:
- Frontend: Next.js Fast Refresh
- Backend: Uvicorn with --reload flag
- Database: Schema migrations with Alembic
- Edge Agent: Watchdog for file changes

**Local SSL/TLS**:
Using mkcert for local certificates:
```bash
# Install mkcert
brew install mkcert  # macOS
# or
sudo apt install libnss3-tools
wget https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
sudo mv mkcert-v1.4.4-linux-amd64 /usr/local/bin/mkcert
sudo chmod +x /usr/local/bin/mkcert

# Generate certificates
mkcert -install
mkcert -cert-file certs/local-cert.pem -key-file certs/local-key.pem localhost 127.0.0.1 ::1
```

#### Debugging Configuration
**VS Code Launch Configuration**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Backend",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "DATABASE_URL": "postgresql://lics:password@localhost:5432/lics",
        "REDIS_URL": "redis://localhost:6379"
      }
    },
    {
      "name": "Debug Frontend",
      "type": "node",
      "request": "launch",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "cwd": "${workspaceFolder}/frontend",
      "port": 9229
    }
  ]
}
```

### 12.6 Performance Optimization for Local Deployment

#### Resource Limitations
**Docker Resource Constraints**:
```yaml
# docker-compose.override.yml for resource limits
version: '3.9'

services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  redis:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

#### Database Optimization
**PostgreSQL Tuning for Local**:
```sql
-- postgresql.conf optimizations
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### 12.7 Backup and Recovery for Local Deployment

#### Automated Backup Script
```bash
#!/bin/bash
# backup-local.sh

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U lics lics > $BACKUP_DIR/postgres_backup.sql

# Backup Redis
docker-compose exec -T redis redis-cli --rdb $BACKUP_DIR/redis_backup.rdb

# Backup InfluxDB
docker-compose exec -T influxdb influx backup $BACKUP_DIR/influxdb_backup

# Backup MinIO data
docker run --rm -v minio_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/minio_backup.tar.gz /data

# Backup configuration files
tar czf $BACKUP_DIR/config_backup.tar.gz .env docker-compose.yml mosquitto/ traefik/

echo "Backup completed: $BACKUP_DIR"
```

#### Recovery Script
```bash
#!/bin/bash
# restore-local.sh

if [ $# -eq 0 ]; then
    echo "Usage: ./restore-local.sh <backup_directory>"
    exit 1
fi

BACKUP_DIR=$1

# Stop services
docker-compose down

# Restore PostgreSQL
docker-compose up -d postgres
sleep 5
docker-compose exec -T postgres psql -U lics lics < $BACKUP_DIR/postgres_backup.sql

# Restore Redis
docker-compose up -d redis
docker-compose exec -T redis redis-cli --rdb $BACKUP_DIR/redis_backup.rdb

# Restore other services...
docker-compose up -d

echo "Restore completed from: $BACKUP_DIR"
```

### 12.8 Monitoring for Local Deployment

#### Lightweight Monitoring Stack
**Prometheus Configuration**:
```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'lics-backend'
    static_configs:
      - targets: ['backend:8000']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
  
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

#### Health Check Dashboard
Simple health monitoring endpoint:
```python
# backend/app/api/health.py
from fastapi import APIRouter
from app.core.database import check_db_health
from app.core.redis import check_redis_health

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "database": await check_db_health(),
            "redis": await check_redis_health(),
            "mqtt": check_mqtt_health(),
        },
        "timestamp": datetime.utcnow()
    }
```

---

## 13. Monitoring & Observability

### 13.1 Metrics Collection

#### Application Metrics
**Business Metrics**:
- Active experiments
- Device utilization
- Data collection rates
- Task success rates
- User engagement

**Technical Metrics**:
- API response times
- Database query performance
- Cache hit rates
- Queue lengths
- Error rates

#### Infrastructure Metrics
**System Metrics**:
CPU, memory, disk, network utilization. Container resource usage. Node capacity and allocation. Cluster autoscaling metrics.

### 13.2 Logging Architecture

#### Structured Logging
**Log Format**:
JSON structured logs. Consistent field naming. Correlation IDs for tracing. Severity levels standardization.

**Log Aggregation**:
Fluentd/Fluent Bit for collection. Elasticsearch for storage. Kibana for visualization. Alert rules for errors.

### 13.3 Distributed Tracing

#### Trace Collection
**Implementation**:
OpenTelemetry instrumentation. Automatic trace injection. Sampling strategies. Context propagation.

**Analysis**:
Service dependency mapping. Latency breakdown. Error root cause analysis. Performance bottleneck identification.

### 13.4 Alerting Strategy

#### Alert Design
**Alert Categories**:
- Critical: Immediate action required
- Warning: Investigation needed
- Info: Awareness only

**Alert Rules**:
SLO-based alerting. Anomaly detection. Predictive alerting. Alert suppression during maintenance.

---

## 14. Data Flow Patterns

### 14.1 Command Flow

#### User-Initiated Commands
**Flow Sequence**:
1. User action in UI
2. API request to backend
3. Validation and authorization
4. Command queuing in Redis
5. MQTT publish to device
6. Device acknowledgment
7. Status update to UI

**Error Handling**:
Timeout mechanisms. Retry with backoff. Fallback strategies. User notification.

### 14.2 Telemetry Flow

#### Device-to-Cloud Data Flow
**Collection Pipeline**:
1. Sensor data collection
2. Local buffering
3. Batch transmission
4. Cloud ingestion
5. Processing and validation
6. Storage in TimescaleDB
7. Cache update
8. Dashboard refresh

**Optimization**:
Data compression. Batch sizes optimization. Network-aware transmission. Priority-based sending.

### 14.3 Real-Time Updates

#### WebSocket Data Flow
**Broadcast Pattern**:
1. Event occurrence
2. Event publication
3. Subscriber notification
4. Client filtering
5. UI update

**Subscription Management**:
Dynamic subscription based on view. Automatic unsubscribe on navigation. Rate limiting for updates. Aggregation for high-frequency data.

---

## 15. Scalability Strategies

### 15.1 Horizontal Scaling

#### Service Scaling
**Auto-scaling Policies**:
CPU-based scaling (target 70%). Memory-based scaling. Request rate scaling. Custom metrics scaling.

**Load Balancing**:
Layer 7 load balancing. Session affinity where needed. Health check integration. Graceful shutdown handling.

### 15.2 Database Scaling

#### Read Scaling
**Read Replicas**:
Asynchronous replication. Read-write splitting. Lag monitoring. Automatic failover.

**Caching Strategy**:
Multi-tier caching. Cache preloading. Invalidation strategies. Cache stampede prevention.

#### Write Scaling
**Sharding Strategy**:
Horizontal partitioning. Shard key selection. Cross-shard queries. Resharding procedures.

### 15.3 Edge Scaling

#### Device Fleet Management
**Registration Scaling**:
Batch device onboarding. Automatic provisioning. Group management. Template-based configuration.

**Update Management**:
Staged rollouts. Automatic rollback. Delta updates. Offline update support.

---

## 16. Testing Strategy

### 16.1 Unit Testing

#### Backend Testing
**Test Coverage**:
- Service layer: 90%
- API endpoints: 85%
- Utilities: 95%
- Database operations: 80%

**Testing Tools**:
Pytest for test execution. Pytest-asyncio for async tests. Factory Boy for fixtures. Hypothesis for property testing.

#### Frontend Testing
**Component Testing**:
React Testing Library. User interaction simulation. Accessibility testing. Visual regression testing.

### 16.2 Integration Testing

#### API Testing
**Test Scenarios**:
Happy path testing. Error condition testing. Permission testing. Rate limit testing.

**Tools**:
Postman/Newman for API tests. Pact for contract testing. Locust for load testing. K6 for performance testing.

### 16.3 End-to-End Testing

#### Test Automation
**Scenarios**:
Complete user workflows. Cross-device interactions. Real-time communication. Data synchronization.

**Tools**:
Playwright for browser automation. Device simulators for edge testing. Synthetic monitoring. Chaos engineering.

### 16.4 Performance Testing

#### Load Testing Strategy
**Test Types**:
- Baseline testing
- Load testing
- Stress testing
- Spike testing
- Soak testing

**Performance Targets**:
- API response: < 200ms p95
- WebSocket latency: < 50ms
- Database queries: < 100ms p95
- Page load time: < 2s
- Concurrent users: 10,000+

---

## 17. Implementation Roadmap

### 17.1 Phase 1: Foundation (Weeks 1-6)

#### Week 1-2: Infrastructure Setup
**Tasks**:
- Initialize Git repositories with branching strategy
- Set up development Kubernetes cluster
- Configure CI/CD pipelines with GitHub Actions
- Implement infrastructure as code with Terraform
- Set up development databases and caching layers

**Deliverables**:
- Complete development environment
- Basic CI/CD pipeline
- Infrastructure automation scripts
- Development guidelines documentation

#### Week 3-4: Core Backend Development
**Tasks**:
- Implement FastAPI application structure with dependency injection
- Create database models and migrations with SQLAlchemy/Alembic
- Implement JWT authentication with refresh tokens
- Build basic CRUD operations for core entities
- Set up WebSocket server with Socket.IO
- Implement MQTT broker integration

**Deliverables**:
- Working authentication system
- Basic API endpoints
- Real-time communication infrastructure
- Database schema implementation

#### Week 5-6: Frontend Foundation
**Tasks**:
- Set up Next.js project with TypeScript configuration
- Implement authentication flow with protected routes
- Create base UI components with Shadcn/ui
- Set up state management with Zustand
- Implement API client with React Query
- Create responsive layouts and navigation

**Deliverables**:
- Functional authentication UI
- Dashboard skeleton
- Component library
- State management architecture

### 17.2 Phase 2: Device Integration (Weeks 7-12)

#### Week 7-8: Edge Device Development
**Tasks**:
- Develop Python edge agent framework
- Implement device registration protocol
- Create GPIO abstraction layer
- Build sensor/actuator interfaces
- Implement local SQLite storage
- Create synchronization mechanisms

**Deliverables**:
- Working edge agent
- Hardware abstraction layer
- Device registration system
- Local data persistence

#### Week 9-10: Communication Layer
**Tasks**:
- Implement MQTT client on edge devices
- Create WebSocket client for real-time updates
- Build message routing system
- Implement telemetry data pipeline
- Create command execution framework
- Set up heartbeat monitoring

**Deliverables**:
- Bidirectional communication system
- Telemetry collection pipeline
- Command execution capability
- Device monitoring system

#### Week 11-12: Device Management UI
**Tasks**:
- Create device discovery interface
- Build device configuration panels
- Implement real-time status monitoring
- Create GPIO mapping interface
- Build sensor/actuator registration
- Implement firmware update mechanism

**Deliverables**:
- Device management dashboard
- Configuration interface
- Real-time monitoring
- Update deployment system

### 17.3 Phase 3: Task Builder (Weeks 13-18)

#### Week 13-14: Visual Editor Development
**Tasks**:
- Implement React Flow editor
- Create custom node components
- Build connection validation system
- Implement drag-and-drop interface
- Create property panels for nodes
- Build visual debugging tools

**Deliverables**:
- Working visual editor
- Node library
- Validation system
- Debugging interface

#### Week 15-16: Task Compilation Engine
**Tasks**:
- Design task definition schema
- Implement compilation pipeline
- Create optimization passes
- Build device compatibility checker
- Implement execution engine
- Create testing framework

**Deliverables**:
- Task compiler
- Execution runtime
- Compatibility checker
- Testing tools

#### Week 17-18: Template System
**Tasks**:
- Create template storage system
- Build template marketplace UI
- Implement sharing mechanisms
- Create versioning system
- Build search and discovery
- Implement rating system

**Deliverables**:
- Template library
- Marketplace interface
- Sharing system
- Discovery features

### 17.4 Phase 4: Experiment Management (Weeks 19-24)

#### Week 19-20: Experiment Engine
**Tasks**:
- Implement experiment lifecycle manager
- Create scheduling system
- Build participant management
- Implement data collection pipeline
- Create result aggregation
- Build notification system

**Deliverables**:
- Experiment management system
- Scheduling capability
- Data collection infrastructure
- Notification service

#### Week 21-22: Analytics & Reporting
**Tasks**:
- Implement real-time analytics
- Create data visualization components
- Build report generation engine
- Implement export capabilities
- Create statistical analysis tools
- Build custom report builder

**Deliverables**:
- Analytics dashboard
- Report generation system
- Export functionality
- Statistical tools

#### Week 23-24: Video Streaming
**Tasks**:
- Implement WebRTC signaling server
- Create video capture on devices
- Build streaming pipeline
- Implement recording capabilities
- Create playback interface
- Build video analytics

**Deliverables**:
- Live video streaming
- Recording system
- Playback interface
- Basic video analytics

### 17.5 Phase 5: Advanced Features (Weeks 25-30)

#### Week 25-26: Machine Learning Integration
**Tasks**:
- Implement ML model serving
- Create behavior classification
- Build anomaly detection
- Implement predictive analytics
- Create recommendation engine
- Build automated insights

**Deliverables**:
- ML pipeline
- Classification system
- Anomaly detection
- Insights generation

#### Week 27-28: Performance Optimization
**Tasks**:
- Implement database query optimization
- Create caching strategies
- Build CDN integration
- Optimize frontend bundles
- Implement lazy loading
- Create performance monitoring

**Deliverables**:
- Optimized database queries
- Comprehensive caching
- CDN configuration
- Optimized frontend
- Performance dashboards

#### Week 29-30: Security Hardening
**Tasks**:
- Conduct security audit
- Implement additional security measures
- Create penetration testing
- Build compliance features
- Implement audit logging
- Create security documentation

**Deliverables**:
- Security audit report
- Hardened infrastructure
- Compliance features
- Complete audit trail

### 17.6 Phase 6: Production Deployment (Weeks 31-36)

#### Week 31-32: Production Infrastructure
**Tasks**:
- Set up production Kubernetes cluster
- Configure production databases
- Implement backup strategies
- Create disaster recovery plan
- Set up monitoring stack
- Configure alerting rules

**Deliverables**:
- Production infrastructure
- Backup systems
- Monitoring solution
- Disaster recovery plan

#### Week 33-34: Migration & Testing
**Tasks**:
- Create data migration scripts
- Perform load testing
- Execute security testing
- Conduct UAT sessions
- Create rollback procedures
- Document known issues

**Deliverables**:
- Migration tools
- Test reports
- UAT feedback
- Rollback plans

#### Week 35-36: Go-Live & Support
**Tasks**:
- Execute production deployment
- Monitor system stability
- Address critical issues
- Create support procedures
- Train support staff
- Document lessons learned

**Deliverables**:
- Live production system
- Support documentation
- Training materials
- Post-mortem report

---

## 18. Operational Procedures

### 18.1 Deployment Procedures

#### Blue-Green Deployment
**Process**:
1. Deploy new version to green environment
2. Run smoke tests on green
3. Switch traffic to green
4. Monitor for issues
5. Keep blue as rollback option
6. Decommission blue after stability

**Rollback Strategy**:
Immediate traffic switch to blue. Database migration rollback scripts. Cache invalidation procedures. User notification mechanisms.

#### Canary Deployment
**Progressive Rollout**:
- 5% traffic for 1 hour
- 25% traffic for 2 hours
- 50% traffic for 4 hours
- 100% traffic after validation

**Monitoring During Rollout**:
Error rate comparison. Performance metrics tracking. User feedback collection. Automatic rollback triggers.

### 18.2 Maintenance Procedures

#### Scheduled Maintenance
**Planning**:
Two-week advance notification. Maintenance window selection. Impact assessment. Rollback planning.

**Execution**:
Maintenance mode activation. User notification system. Progress tracking. Communication updates.

#### Database Maintenance
**Regular Tasks**:
- Index rebuilding (weekly)
- Statistics updates (daily)
- Vacuum operations (weekly)
- Backup verification (daily)
- Archive old data (monthly)

### 18.3 Incident Response

#### Incident Classification
**Severity Levels**:
- P1: Complete system outage
- P2: Major feature unavailable
- P3: Minor feature degraded
- P4: Cosmetic issues

**Response Times**:
- P1: 15 minutes
- P2: 1 hour
- P3: 4 hours
- P4: Next business day

#### Incident Management Process
**Steps**:
1. Detection and alerting
2. Initial assessment
3. Incident commander assignment
4. Communication initiation
5. Root cause investigation
6. Resolution implementation
7. Post-incident review

### 18.4 Backup & Recovery

#### Backup Strategy
**Database Backups**:
- Full backup: Daily
- Incremental: Hourly
- Transaction logs: Continuous
- Retention: 30 days
- Offsite storage: S3/GCS

**File System Backups**:
User uploads backup. Configuration files. Application logs. Video recordings.

#### Recovery Procedures
**Recovery Time Objectives**:
- Database: < 1 hour
- Application: < 30 minutes
- Full system: < 4 hours

**Recovery Point Objectives**:
- Critical data: < 5 minutes
- Standard data: < 1 hour
- Archived data: < 24 hours

---

## 19. Cost Optimization

### 19.1 Infrastructure Costs

#### Compute Optimization
**Strategies**:
- Spot instances for non-critical workloads
- Reserved instances for baseline capacity
- Auto-scaling for demand management
- Right-sizing based on metrics
- Scheduled scaling for predictable patterns

#### Storage Optimization
**Strategies**:
- Lifecycle policies for object storage
- Data compression for databases
- Archive tier for old data
- Deduplication where possible
- Cleanup of orphaned resources

### 19.2 Operational Costs

#### License Management
**Optimization**:
- Open-source alternatives evaluation
- Volume licensing negotiation
- Usage-based licensing where appropriate
- Regular license audit

#### Development Costs
**Efficiency Improvements**:
- Automated testing to reduce QA time
- Infrastructure as code for consistency
- Reusable component libraries
- Documentation to reduce onboarding

---

## 20. Compliance & Regulations

### 20.1 Data Protection

#### GDPR Compliance
**Requirements**:
- Explicit consent mechanisms
- Data portability implementation
- Right to erasure support
- Privacy by design principles
- Data protection officer assignment

#### HIPAA Considerations
**If Applicable**:
- Encryption requirements
- Access controls
- Audit logging
- Business associate agreements
- Risk assessments

### 20.2 Research Ethics

#### IRB Compliance
**Features**:
- Protocol version control
- Consent form management
- Adverse event reporting
- Data retention policies
- Audit trail maintenance

#### Animal Research
**Considerations**:
- IACUC protocol integration
- Welfare monitoring features
- Environmental control logging
- Health status tracking

---

## 21. Future Enhancements

### 21.1 Advanced Features Roadmap

#### Artificial Intelligence Integration
**Planned Capabilities**:
- Automated experiment optimization
- Intelligent scheduling
- Predictive maintenance
- Natural language task creation
- Computer vision for behavior analysis

#### Federation Support
**Multi-Site Features**:
- Cross-institution collaboration
- Federated data analysis
- Distributed experiment control
- Resource sharing protocols

### 21.2 Platform Extensions

#### Mobile Applications
**Native Apps**:
- iOS/Android monitoring apps
- Push notifications
- Offline data access
- Remote control capabilities

#### Integration Ecosystem
**Planned Integrations**:
- Electronic Lab Notebooks (ELN)
- Laboratory Information Management Systems (LIMS)
- Statistical packages (R, Python, MATLAB)
- Cloud AI services
- IoT platforms

### 21.3 Research Applications

#### Domain Expansions
**Potential Areas**:
- Neuroscience research
- Pharmaceutical testing
- Agricultural research
- Environmental monitoring
- Educational laboratories

---

## 22. Success Metrics & KPIs

### 22.1 Technical KPIs

#### Performance Metrics
- System uptime: > 99.9%
- API response time: < 200ms (p95)
- Data collection reliability: > 99.99%
- Device connection success: > 99%
- Video stream quality: > 720p

#### Scalability Metrics
- Concurrent experiments: > 1000
- Connected devices: > 10,000
- Data ingestion rate: > 100k points/sec
- Storage efficiency: < $0.10/GB/month

### 22.2 Business KPIs

#### Adoption Metrics
- Active users growth rate
- Device utilization rate
- Experiment completion rate
- Template reuse rate
- User satisfaction score

#### Efficiency Metrics
- Time to first experiment
- Setup time reduction
- Manual intervention rate
- Support ticket volume
- Cost per experiment

### 22.3 Quality Metrics

#### Data Quality
- Data completeness: > 99%
- Data accuracy validation
- Duplicate detection rate
- Missing data handling

#### User Experience
- Page load times
- Error rates
- Task completion rates
- User retention
- Feature adoption

---

## Conclusion

This Lab Instrument Control System represents a comprehensive solution for modern laboratory automation and experiment management. The architecture prioritizes scalability, reliability, and user experience while maintaining the flexibility to adapt to various research domains.

The modular design ensures that individual components can be updated or replaced without affecting the entire system, while the microservices architecture allows for independent scaling of different functionalities based on demand.

The implementation roadmap provides a clear path from initial development to production deployment, with defined milestones and deliverables at each stage. The emphasis on automation, from device discovery to experiment execution, reduces the operational burden on researchers and allows them to focus on scientific discovery.

By following this detailed documentation, development teams can implement a robust, scalable, and user-friendly laboratory automation platform that meets the evolving needs of modern research facilities.

---

## Appendices

### Appendix A: Technology Decision Matrix

| Component | Technology | Alternatives Considered | Rationale |
|-----------|------------|------------------------|-----------|
| Backend Framework | FastAPI | Django, Flask, Express.js | Native async support, automatic API documentation, type safety |
| Frontend Framework | Next.js 14 | React SPA, Vue.js, Angular | SSR/SSG capabilities, API routes, optimized performance |
| Primary Database | PostgreSQL | MySQL, MongoDB, CockroachDB | ACID compliance, extensions ecosystem, TimescaleDB compatibility |
| Time-Series DB | InfluxDB | TimescaleDB only, Prometheus | Purpose-built for metrics, efficient storage, good tooling |
| Message Broker | MQTT + Redis | RabbitMQ, Kafka, NATS | Lightweight for IoT, reliable pub/sub, good client libraries |
| Container Orchestration | Kubernetes | Docker Swarm, Nomad, ECS | Industry standard, ecosystem, cloud provider support |
| Edge Runtime | Python | Node.js, Go, Rust | Hardware library support, ease of development, community |

### Appendix B: Glossary of Terms

- **LICS**: Lab Instrument Control System
- **Edge Device**: Raspberry Pi-based experimental apparatus
- **Task**: Experimental protocol defined visually
- **Template**: Reusable task definition
- **Telemetry**: Real-time data from sensors
- **GPIO**: General Purpose Input/Output pins
- **MQTT**: Message Queuing Telemetry Transport
- **WebRTC**: Web Real-Time Communication
- **IRB**: Institutional Review Board
- **IACUC**: Institutional Animal Care and Use Committee
- **SSR**: Server-Side Rendering
- **SSG**: Static Site Generation
- **CORS**: Cross-Origin Resource Sharing
- **JWT**: JSON Web Token
- **RBAC**: Role-Based Access Control
- **TLS**: Transport Layer Security
- **PII**: Personally Identifiable Information
- **SLO**: Service Level Objective
- **RTO**: Recovery Time Objective
- **RPO**: Recovery Point Objective

### Appendix C: Repository Structure

```
lics/
├── .github/
│   ├── workflows/
│   └── ISSUE_TEMPLATE/
├── infrastructure/
│   ├── terraform/
│   ├── kubernetes/
│   └── ansible/
├── services/
│   ├── frontend/
│   ├── backend/
│   ├── edge-agent/
│   └── streaming/
├── shared/
│   ├── protos/
│   ├── schemas/
│   └── contracts/
├── tools/
│   ├── scripts/
│   ├── migrations/
│   └── testing/
├── docs/
│   ├── api/
│   ├── architecture/
│   └── user-guides/
├── docker-compose.yml
├── Makefile
└── README.md
```

### Appendix D: API Documentation Example

#### Device Registration Endpoint
```http
POST /api/v1/devices/register
Content-Type: application/json
Authorization: Bearer {device_token}

{
  "device_id": "rpi-001",
  "capabilities": {
    "sensors": ["temperature", "humidity", "motion"],
    "actuators": ["led", "buzzer", "servo"],
    "gpio_pins": 40,
    "camera": true,
    "storage": "32GB"
  },
  "firmware_version": "1.2.3",
  "location": {
    "lab": "Lab A",
    "cage": "C-101"
  }
}

Response:
{
  "data": {
    "device_id": "rpi-001",
    "registration_token": "...",
    "mqtt_credentials": {
      "username": "device-rpi-001",
      "password": "...",
      "broker": "mqtt.lics.example.com",
      "port": 8883
    },
    "configuration": {
      "telemetry_interval": 5000,
      "heartbeat_interval": 30000,
      "batch_size": 100
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:00:00Z",
    "version": "1.0"
  }
}
```

### Appendix E: Task Definition Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LICS Task Definition",
  "version": "1.0.0",
  "type": "object",
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "author": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["name", "version"]
    },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "type": {"enum": ["start", "end", "action", "decision", "loop", "wait", "data"]},
          "parameters": {"type": "object"},
          "position": {
            "type": "object",
            "properties": {
              "x": {"type": "number"},
              "y": {"type": "number"}
            }
          }
        },
        "required": ["id", "type"]
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "source": {"type": "string"},
          "target": {"type": "string"},
          "condition": {"type": "string"}
        },
        "required": ["id", "source", "target"]
      }
    },
    "variables": {
      "type": "object"
    }
  },
  "required": ["metadata", "nodes", "edges"]
}
```

### Appendix F: Troubleshooting Guide

#### Common Issues and Solutions

**Issue: Device not connecting to MQTT broker**
- Check network connectivity
- Verify MQTT credentials
- Check firewall rules
- Verify broker is running
- Check TLS certificate validity

**Issue: High database query latency**
- Check query execution plans
- Verify indexes are present
- Check connection pool settings
- Monitor database resource usage
- Consider query optimization

**Issue: WebSocket disconnections**
- Check proxy timeout settings
- Verify keep-alive configuration
- Check network stability
- Monitor server resource usage
- Review client-side error logs

**Issue: Task execution failures**
- Validate task definition schema
- Check device capabilities
- Verify resource availability
- Review execution logs
- Test in sandbox environment

### Appendix G: Contact and Support

For implementation support, architecture discussions, or clarifications on this documentation, establish clear communication channels:

- Technical discussions: GitHub Discussions
- Bug reports: GitHub Issues  
- Security concerns: Private security advisory
- Documentation updates: Pull requests
- Community forum: discourse.lics.io
- Commercial support: support@lics.io

---

*This documentation represents a complete blueprint for implementing the Lab Instrument Control System. Each section provides sufficient detail for developers to understand requirements, make implementation decisions, and build a production-ready system. The combination of cloud and local deployment options ensures flexibility for different organizational needs and scales.*

---

## 18. Primate Research Specialization

### 18.1 Overview

LICS is purpose-built for **non-human primate behavioral neuroscience research**, delivering diverse tasks to analyze phenotypic characteristics and complex nervous systems of macaques, marmosets, capuchins, and other species. Each experimental paradigm requires distinct hardware and software configurations, managed through the platform's no-code interface.

### 18.2 Participant Management System

#### Non-Human Primate Subject Tracking

**Core Features**:
- **Species-Specific Management**: Support for macaques, marmosets, capuchins, rhesus monkeys
- **RFID-Based Identification**: Automatic subject recognition via radio-frequency tags
- **Demographic Tracking**: Birth date, weight, sex, training level progression
- **Welfare Monitoring Integration**: Health status, activity levels, behavioral notes
- **Training Level Progression**: Graduated complexity from basic to advanced tasks

**Database Schema**:
```python
class Primate(BaseModel):
    """Non-human primate subjects"""
    __tablename__ = "primates"

    # Core Identity
    id: UUID (primary key)
    organization_id: UUID (foreign key to organizations)
    name: str (unique per organization)
    species: Enum[macaque, marmoset, capuchin, rhesus, other]
    rfid_tag: str (unique, indexed for fast lookup)

    # Demographics
    birth_date: date
    sex: Enum[M, F, U]
    weight_kg: Decimal(5,2)

    # Research Status
    training_level: int (1-10 scale)
    is_active: bool (currently participating)

    # Session Tracking
    current_board: Device (nullable, current cage assignment)
    game_instance: Experiment (nullable, active experiment)

    # Metadata
    notes: text (welfare observations, behavioral notes)
    metadata: JSONB (flexible additional data)
```

**Key Operations**:
- **RFID Auto-Detection**: Edge devices detect RFID tags, automatically associate primate with session
- **Training Level Enforcement**: Tasks validate minimum training requirements before execution
- **Session History**: Complete audit trail of all experiments, tasks, and outcomes
- **Multi-Lab Support**: Organization-based isolation for collaborative research

#### Welfare and Ethics Compliance

**IACUC Integration**:
- **Protocol Versioning**: Track IACUC-approved protocol versions for each experiment
- **Animal Tracking**: Number of sessions per day, cumulative weekly duration
- **Welfare Flags**: Automated alerts for health concerns, excessive session counts
- **Environmental Logging**: Cage temperature, humidity, light cycle tracking

**Compliance Features**:
```python
# Automated session limits
MAX_SESSIONS_PER_DAY = 3
MAX_DURATION_PER_SESSION = 120  # minutes
MINIMUM_REST_BETWEEN_SESSIONS = 60  # minutes

# Welfare monitoring
class WelfareCheck(BaseModel):
    primate_id: UUID
    check_date: datetime
    weight_kg: Decimal
    behavioral_observations: str
    health_status: Enum[excellent, good, fair, concern]
    veterinary_notes: text
```

### 18.3 Cognitive Task Paradigms

#### Task Categories for Primate Research

**1. Fixation and Attention Tasks**:
- **Purpose**: Assess visual attention, impulse control, sustained focus
- **Implementation**: Button hold duration, target fixation monitoring
- **Hardware**: Touchscreen display, eye-tracking camera (optional)
- **Metrics**: Response time, fixation duration, error rates

**2. Memory and Learning Tasks**:
- **Delayed Match-to-Sample (DMTS)**: Short-term memory assessment
- **Spatial Memory**: Location recall after delay periods
- **Working Memory**: Sequence recall, object permanence
- **Hardware**: Multi-position stimulus display, reward delivery system

**3. Visual Discrimination Tasks**:
- **Color Discrimination**: Hue, saturation, brightness differentiation
- **Shape Recognition**: Geometric forms, complex objects
- **Motion Detection**: Direction, speed, coherence thresholds
- **Hardware**: High-resolution display, precise stimulus control

**4. Auditory Processing Tasks**:
- **Frequency Discrimination**: Pure tone differentiation
- **Pattern Recognition**: Temporal sequences, rhythmic patterns
- **Auditory Attention**: Selective attention, distractor filtering
- **Hardware**: Calibrated speakers, sound isolation booth

**5. Motor Control Tasks**:
- **Reaching Tasks**: Precision reaching, target accuracy
- **Sequence Learning**: Motor pattern acquisition
- **Reaction Time**: Simple and choice reaction paradigms
- **Hardware**: Force-sensitive touchscreen, motion tracking

#### Example: Fixation Task Configuration

```json
{
  "task_metadata": {
    "name": "Visual Fixation Training",
    "category": "cognitive",
    "subcategory": "attention",
    "version": "2.1.0",
    "author_id": "user-uuid",
    "description": "Basic visual fixation task for training level 1-3 primates"
  },
  "parameter_schema": {
    "type": "object",
    "properties": {
      "button_size_range": {
        "type": "object",
        "properties": {
          "min": {"type": "number", "minimum": 20, "maximum": 200},
          "max": {"type": "number", "minimum": 20, "maximum": 200}
        },
        "required": ["min", "max"]
      },
      "hold_duration_ms": {
        "type": "integer",
        "minimum": 100,
        "maximum": 5000,
        "default": 200
      },
      "inter_trial_intervals": {
        "correct": {"type": "integer", "default": 2000},
        "incorrect": {"type": "integer", "default": 5000},
        "absent": {"type": "integer", "default": 60000}
      },
      "reward_config": {
        "duration_ms": {"type": "integer", "default": 500},
        "amount_ml": {"type": "number", "default": 0.2}
      }
    },
    "required": ["button_size_range", "hold_duration_ms"]
  },
  "default_parameters": {
    "button_size_range": {"min": 50, "max": 150},
    "hold_duration_ms": 200,
    "button_color": "#00FF00",
    "background_color": "#000000",
    "inter_trial_intervals": {
      "correct": 2000,
      "incorrect": 5000,
      "absent": 60000
    },
    "reward_config": {
      "duration_ms": 500,
      "amount_ml": 0.2
    }
  },
  "required_hardware": [
    {"type": "display", "resolution": "1920x1080"},
    {"type": "feeder", "precision": "high"},
    {"type": "camera", "fps": 30}
  ],
  "minimum_training_level": 1,
  "result_schema": {
    "trial_number": "integer",
    "timestamp": "datetime",
    "button_size": "float",
    "button_position_x": "integer",
    "button_position_y": "integer",
    "response_time_ms": "integer",
    "hold_duration_achieved": "integer",
    "is_correct": "boolean",
    "feedback_type": {"enum": ["reward", "timeout", "error", "abort"]}
  }
}
```

### 18.4 Cage-Based Device Architecture

#### Raspberry Pi Edge Device Configuration

**Standard Cage Setup**:
```
┌────────────────────────────────────────────────┐
│         Primate Experimental Cage              │
│                                                │
│  ┌──────────────┐         ┌──────────────┐   │
│  │  Touchscreen │         │   Camera     │   │
│  │   Display    │         │  (1080p 30fps)│   │
│  │ (1920x1080)  │         └──────────────┘   │
│  └──────────────┘                             │
│                                                │
│  ┌──────────────┐         ┌──────────────┐   │
│  │    Feeder    │         │   Speaker    │   │
│  │  (Pellet/    │         │  (Auditory   │   │
│  │   Liquid)    │         │   Stimuli)   │   │
│  └──────────────┘         └──────────────┘   │
│                                                │
│  ┌──────────────┐         ┌──────────────┐   │
│  │  RFID Reader │         │  LED Lights  │   │
│  │  (Animal ID) │         │ (Reward Cue) │   │
│  └──────────────┘         └──────────────┘   │
│                                                │
│          ┌──────────────────────┐             │
│          │  Raspberry Pi 4/5    │             │
│          │  - Python Agent      │             │
│          │  - SQLite Cache      │             │
│          │  - MQTT Client       │             │
│          │  - Playwright Browser│             │
│          └──────────────────────┘             │
└────────────────────────────────────────────────┘
```

**Hardware Component Registry**:

Researchers register hardware via web interface with **no code interaction**:

```python
# Example: Adding feeder to device via web UI
POST /api/v1/devices/{device_id}/hardware
{
  "hardware_type": "feeder",
  "name": "Primary Pellet Dispenser",
  "model": "Med Associates ENV-203M",
  "manufacturer": "Med Associates",
  "gpio_pins": [17, 18],  # Trigger and sensor pins
  "pin_mode": "output",
  "configuration": {
    "pellet_size_mg": 45,
    "dispense_duration_ms": 100,
    "inter_pellet_interval_ms": 50
  },
  "calibration_data": {
    "last_calibrated": "2024-12-01T10:00:00Z",
    "pellets_per_gram": 22.2,
    "dispense_accuracy": 0.95
  }
}

# System auto-updates device metadata in database
# Edge agent polls for hardware changes, updates GPIO mappings
```

**Dynamic Hardware Discovery**:
```python
# Edge agent detects new hardware, requests backend registration
class HardwareManager:
    def detect_connected_hardware(self):
        """Scans GPIO, USB, I2C for new devices"""
        detected = []

        # I2C scan for sensors
        i2c_devices = self.scan_i2c_bus()
        for addr, device_type in i2c_devices:
            detected.append({
                "bus": "i2c",
                "address": addr,
                "suggested_type": device_type
            })

        # USB scan for cameras
        usb_cameras = self.scan_video_devices()
        for cam in usb_cameras:
            detected.append({
                "bus": "usb",
                "device": cam.device_path,
                "suggested_type": "camera",
                "capabilities": cam.get_capabilities()
            })

        # Report to backend for user confirmation
        self.api_client.post("/devices/self/hardware/detected", detected)
```

### 18.5 Browser Automation for Task Execution

#### Playwright Integration on Edge Devices

**Why Browser-Based Tasks?**:
- **No-Code Task Deployment**: JavaScript/React tasks run in browser without edge agent code changes
- **Cross-Platform Compatibility**: Same task code runs on development and production environments
- **Rich UI Capabilities**: Leverage web technologies for complex visual stimuli
- **Hot-Swap Tasks**: Update tasks without edge device reboot

**Edge Agent Browser Automation**:

```python
# services/edge-agent/src/browser_controller.py

from playwright.async_api import async_playwright, Browser, Page
import asyncio

class TaskBrowserController:
    """Manages headless browser for task execution"""

    def __init__(self, config: EdgeConfig):
        self.config = config
        self.browser: Browser = None
        self.page: Page = None
        self.playwright = None

    async def initialize(self):
        """Start headless Chromium"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',  # Avoid memory issues on Pi
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu'
            ]
        )
        self.page = await self.browser.new_page(viewport={'width': 1920, 'height': 1080})

    async def load_task(self, task_url: str, experiment_config: dict):
        """Load task application with configuration"""
        # Navigate to task URL (served from backend or local cache)
        await self.page.goto(task_url)

        # Inject experiment configuration
        await self.page.evaluate(f"""
            window.LICS_EXPERIMENT_CONFIG = {json.dumps(experiment_config)};
            window.LICS_DEVICE_ID = '{self.config.device_id}';
        """)

        # Wait for task initialization
        await self.page.wait_for_function("window.LICS_TASK_READY === true", timeout=10000)

    async def handle_task_events(self):
        """Listen for task events and relay to backend"""
        # Expose Python function to JavaScript
        await self.page.expose_function('licsSendResult', self.on_task_result)
        await self.page.expose_function('licsRequestReward', self.on_reward_request)
        await self.page.expose_function('licsLogEvent', self.on_task_event)

    async def on_task_result(self, result_data: dict):
        """Task completed a trial, store result"""
        logger.info(f"Task result: {result_data}")
        await self.data_manager.store_result(result_data)
        await self.api_client.post_result(result_data)

    async def on_reward_request(self, reward_config: dict):
        """Task requests reward delivery"""
        logger.info(f"Reward request: {reward_config}")
        await self.gpio_controller.activate_feeder(
            duration_ms=reward_config.get('duration_ms', 500)
        )

    async def on_task_event(self, event_data: dict):
        """Task logged an event (errors, warnings, info)"""
        await self.telemetry_manager.log_event(event_data)
```

**Task Application Template** (JavaScript):

```javascript
// Example fixation task running in browser on edge device

class FixationTask {
  constructor(config) {
    this.config = config;
    this.trialNumber = 0;
    this.canvas = document.getElementById('task-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.currentButton = null;
    this.holdStartTime = null;
  }

  async initialize() {
    // Set up canvas, event listeners
    this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
    this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));

    // Signal ready to edge agent
    window.LICS_TASK_READY = true;

    // Start first trial
    this.startTrial();
  }

  startTrial() {
    this.trialNumber++;

    // Generate button with random size and position
    const buttonSize = this.getRandomSize();
    const position = this.getRandomPosition(buttonSize);

    this.currentButton = {
      size: buttonSize,
      x: position.x,
      y: position.y,
      targetHoldDuration: this.config.hold_duration_ms
    };

    this.drawButton();
  }

  onMouseDown(event) {
    if (!this.isInsideButton(event.clientX, event.clientY)) {
      return;
    }

    this.holdStartTime = Date.now();
  }

  onMouseUp(event) {
    if (!this.holdStartTime) return;

    const holdDuration = Date.now() - this.holdStartTime;
    const isCorrect = holdDuration >= this.currentButton.targetHoldDuration;

    // Send result to edge agent (which relays to backend)
    window.licsSendResult({
      trial_number: this.trialNumber,
      timestamp: new Date().toISOString(),
      button_size: this.currentButton.size,
      button_position_x: this.currentButton.x,
      button_position_y: this.currentButton.y,
      response_time_ms: holdDuration,
      hold_duration_achieved: holdDuration,
      is_correct: isCorrect,
      feedback_type: isCorrect ? 'reward' : 'timeout'
    });

    if (isCorrect) {
      // Request reward from edge agent
      window.licsRequestReward({
        duration_ms: this.config.reward_config.duration_ms
      });

      // Wait inter-trial interval, start next trial
      setTimeout(() => this.startTrial(), this.config.inter_trial_intervals.correct);
    } else {
      // Timeout, longer wait
      setTimeout(() => this.startTrial(), this.config.inter_trial_intervals.incorrect);
    }

    this.holdStartTime = null;
  }

  // ... rendering and utility methods ...
}

// Initialize task when loaded
const task = new FixationTask(window.LICS_EXPERIMENT_CONFIG);
task.initialize();
```

### 18.6 No-Code Task Creation Workflow

#### Visual Task Builder Interface

**React Flow-Based Editor**:

1. **Researcher opens Task Builder page**
2. **Drag nodes onto canvas**:
   - Start node (entry point)
   - Stimulus Display node (show button, image, sound)
   - Response Collection node (wait for touchscreen input)
   - Decision node (check if response is correct)
   - Reward Delivery node (activate feeder)
   - Delay node (inter-trial interval)
   - Loop node (repeat trials)
   - End node

3. **Connect nodes with edges** (define execution flow)

4. **Configure node parameters** via property panel:
   ```json
   // Stimulus Display Node Parameters
   {
     "node_type": "stimulus_display",
     "parameters": {
       "stimulus_type": "button",
       "size_range": {"min": 50, "max": 150},
       "color": "#00FF00",
       "position": "random",
       "duration_ms": null  // Until response
     }
   }

   // Response Collection Node Parameters
   {
     "node_type": "response_collection",
     "parameters": {
       "input_type": "touchscreen",
       "timeout_ms": 10000,
       "valid_area": "stimulus_bounds",
       "hold_duration_required_ms": 200
     }
   }

   // Reward Delivery Node Parameters
   {
     "node_type": "reward_delivery",
     "parameters": {
       "hardware_component": "primary_feeder",
       "reward_type": "pellet",
       "quantity": 1,
       "delay_ms": 0
     }
   }
   ```

5. **Compile to Task Definition**:
   - Visual flow → JSON task definition
   - Validate node connections (no orphaned nodes, cycles only in loops)
   - Check hardware requirements match registered devices
   - Generate JavaScript task application code
   - Store in database with version

6. **Deploy to Devices**:
   - Researcher assigns task to experiment
   - Backend sends task URL to edge device
   - Edge agent downloads task, caches locally
   - Browser loads and executes task

**Example Flow Compilation**:

```mermaid
flowchart TD
    Start[Start Experiment] --> RFID[Wait for RFID Detection]
    RFID --> Display[Display Button Stimulus]
    Display --> Wait[Wait for Response]
    Wait --> Check{Hold Duration\nCorrect?}
    Check -->|Yes| Reward[Deliver Reward]
    Check -->|No| Timeout[Timeout Delay]
    Reward --> ITI[Inter-Trial Interval]
    Timeout --> ITI
    ITI --> TrialCount{Completed\n100 Trials?}
    TrialCount -->|No| Display
    TrialCount -->|Yes| End[End Experiment]
```

### 18.7 Dynamic Report Generation

#### Schema-Driven Report System

**Challenge**: Each task has different result schemas. How do we generate reports without hard-coding?

**Solution**: Task defines `result_schema`, report system dynamically adapts.

**Example**:

```python
# Task A: Fixation Task
result_schema = {
    "button_size": "float",
    "hold_duration_achieved": "integer",
    "is_correct": "boolean"
}

# Task B: Delayed Match-to-Sample
result_schema = {
    "sample_stimulus_id": "integer",
    "delay_duration_ms": "integer",
    "match_stimulus_id": "integer",
    "response_stimulus_id": "integer",
    "is_correct": "boolean",
    "confidence_rating": "integer"
}

# Report generation dynamically includes available metrics
class ReportGenerator:
    def generate_experiment_report(self, experiment_id: UUID):
        experiment = await self.experiment_repo.get(experiment_id)
        task = await self.task_repo.get(experiment.task_id)
        results = await self.result_repo.get_by_experiment(experiment_id)

        # Extract metrics from result_schema
        metrics = {}
        for field_name, field_type in task.result_schema.items():
            if field_type in ['integer', 'float']:
                values = [r.result_data.get(field_name) for r in results]
                metrics[field_name] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values)
                }

        # Generate visualizations based on schema
        charts = []
        if 'is_correct' in task.result_schema:
            # Learning curve
            charts.append(self.create_learning_curve(results))

        if 'response_time_ms' in task.result_schema:
            # Response time distribution
            charts.append(self.create_rt_histogram(results))

        return {
            'experiment': experiment.to_dict(),
            'task': task.to_dict(),
            'metrics': metrics,
            'charts': charts,
            'raw_results': [r.to_dict() for r in results]
        }
```

### 18.8 Multi-Tenancy for Research Labs

**Organization-Based Isolation**:

```python
# All data scoped to organization
class Organization(BaseModel):
    id: UUID
    name: str  # "Harvard Neuroscience Lab", "MIT Primate Center"
    settings: JSONB  # Lab-specific configurations

    # Relationships
    devices: List[Device]
    primates: List[Primate]
    users: List[User]
    experiments: List[Experiment]

# Queries automatically filter by organization
@router.get("/primates")
async def list_primates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Only return primates from user's organization
    primates = await primate_repo.get_by_organization(
        current_user.organization_id,
        db
    )
    return primates

# Cross-lab collaboration support
class SharedExperiment(BaseModel):
    """Allow labs to share task templates, anonymized results"""
    source_organization_id: UUID
    target_organization_id: UUID
    task_template_id: UUID
    permission_level: Enum[view, clone, contribute]
```

### 18.9 Real-Time State Synchronization

**Device State WebSocket Flow**:

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ Edge Device │       │   Backend   │       │  Researcher │
│  (Cage 1)   │       │  WebSocket  │       │   Browser   │
└──────┬──────┘       └──────┬──────┘       └──────┬──────┘
       │                     │                     │
       │ PRIMATE RFID        │                     │
       │ DETECTED            │                     │
       ├────────────────────>│                     │
       │                     │                     │
       │                     │ WS: primate_detected│
       │                     ├────────────────────>│
       │                     │                     │
       │                     │ START EXPERIMENT    │
       │                     │<────────────────────┤
       │                     │                     │
       │ MQTT: start_exp     │                     │
       │<────────────────────┤                     │
       │                     │                     │
       │ TASK LOADED         │                     │
       ├────────────────────>│                     │
       │                     │ WS: exp_started     │
       │                     ├────────────────────>│
       │                     │                     │
       │ TRIAL RESULT        │                     │
       ├────────────────────>│                     │
       │                     │ WS: trial_update    │
       │                     ├────────────────────>│
       │                     │                     │
```

**WebSocket Event Types**:

```typescript
// Frontend subscribes to device room
socket.emit('subscribe', { room: `device:${deviceId}` });

// Events from backend
socket.on('device:state_changed', (data) => {
  // Update device status indicator
  updateDeviceStatus(data.device_id, data.status);
});

socket.on('device:primate_detected', (data) => {
  // Show notification: "Monkey-42 detected at Cage-3"
  showNotification(`${data.primate_name} detected at ${data.device_name}`);
});

socket.on('experiment:trial_completed', (data) => {
  // Update live dashboard with trial result
  updateTrialChart(data.trial_number, data.is_correct);
  updateSuccessRate(data.cumulative_success_rate);
});

socket.on('experiment:completed', (data) => {
  // Show completion notification, offer report generation
  showExperimentComplete(data.experiment_id);
});
```

### 18.10 Data Flow Example: Complete Experiment Session

**Scenario**: Researcher starts fixation task for Monkey-42 at Cage-3

1. **Researcher Action**: Clicks "Start Experiment" in web UI
   ```typescript
   POST /api/v1/experiments/{experiment_id}/start
   {
     "device_id": "cage-3-uuid",
     "primate_id": "monkey-42-uuid",
     "task_id": "fixation-task-uuid",
     "configuration_id": "training-level-2-config-uuid"
   }
   ```

2. **Backend Processing**:
   ```python
   # Validate: device online, primate not occupied, task compatible
   experiment = await experiment_service.start_experiment(...)

   # Update device state
   await device_state_repo.update(device_id, {
       'is_occupied': True,
       'current_participant_id': primate_id,
       'current_experiment_id': experiment.id,
       'experiment_status': 'running'
   })

   # Publish MQTT command to edge device
   await mqtt_client.publish(
       f'lics/devices/{device_id}/commands',
       {
           'command': 'start_experiment',
           'experiment_id': str(experiment.id),
           'task_url': task.app_url,
           'configuration': configuration.parameters
       }
   )

   # Emit WebSocket event to researcher
   await sio.emit('experiment:started', {
       'experiment_id': str(experiment.id),
       'device_id': str(device_id),
       'primate_id': str(primate_id)
   }, room=f'user:{researcher_id}')
   ```

3. **Edge Device Execution**:
   ```python
   # Receive MQTT command
   async def on_start_experiment_command(message):
       experiment_id = message['experiment_id']
       task_url = message['task_url']
       config = message['configuration']

       # Load task in browser
       await browser_controller.load_task(task_url, config)

       # Wait for RFID detection
       primate_tag = await rfid_reader.wait_for_tag(timeout=300)

       # Verify correct primate
       if primate_tag != expected_primate_rfid:
           await api_client.log_error("Wrong primate detected")
           return

       # Notify backend
       await api_client.post('/experiments/{experiment_id}/events', {
           'event_type': 'primate_detected',
           'rfid_tag': primate_tag
       })

       # Browser task auto-starts
       await browser_controller.signal_start()
   ```

4. **Task Execution** (100 trials):
   ```javascript
   // Each trial: display button → wait for hold → deliver reward → ITI
   for (let trial = 1; trial <= 100; trial++) {
       const result = await this.runTrial(trial);

       // Send to edge agent
       window.licsSendResult(result);

       // Edge agent forwards to backend
       POST /api/v1/experiments/{experiment_id}/results
       {
           "trial_number": trial,
           "timestamp": "2024-12-01T10:15:23Z",
           "result_data": {
               "button_size": 87.3,
               "hold_duration_achieved": 245,
               "is_correct": true,
               ...
           }
       }
   }
   ```

5. **Real-Time Updates**:
   ```python
   # Backend receives result, broadcasts to researcher
   @router.post("/experiments/{experiment_id}/results")
   async def create_result(...):
       result = await result_repo.create(result_data)

       # Update experiment statistics
       await experiment_service.update_statistics(experiment_id)

       # Broadcast via WebSocket
       await sio.emit('experiment:trial_completed', {
           'experiment_id': str(experiment_id),
           'trial_number': result.trial_number,
           'is_correct': result.is_correct,
           'cumulative_success_rate': experiment.success_rate
       }, room=f'experiment:{experiment_id}')
   ```

6. **Experiment Completion**:
   ```python
   # Task finishes 100 trials, signals completion
   window.licsExperimentComplete({
       'total_trials': 100,
       'completed_trials': 100,
       'success_rate': 0.87
   });

   # Edge agent
   POST /api/v1/experiments/{experiment_id}/complete

   # Backend
   experiment.status = 'completed'
   experiment.actual_end = datetime.now()
   await experiment_repo.update(experiment)

   # Release device
   device_state.is_occupied = False
   device_state.current_experiment_id = None
   await device_state_repo.update(device_state)

   # Notify researcher
   await sio.emit('experiment:completed', {
       'experiment_id': str(experiment_id),
       'final_statistics': experiment.to_dict()
   }, room=f'user:{researcher_id}')
   ```

7. **Report Generation**:
   ```python
   # Researcher clicks "Generate Report"
   POST /api/v1/reports/generate
   {
       'template_id': 'session-summary-uuid',
       'experiment_id': 'experiment-uuid'
   }

   # Backend generates PDF/Excel report
   report = await report_service.generate(
       template_id=template_id,
       experiment_id=experiment_id,
       format='pdf'
   )

   # Store in MinIO
   report_url = await minio_client.upload(report.file_path)

   # Return download link
   return {'report_url': report_url}
   ```

---

## Key Advantages of LICS for Primate Research

### 1. **No-Code Operation**
Researchers interact **only through web interface**:
- Add new tasks via visual builder (no JavaScript knowledge)
- Configure experiment parameters via forms (no config files)
- Register hardware via device management UI (no GPIO code)
- Generate reports via template selection (no data analysis scripts)

### 2. **Flexibility Without Code Changes**
- **Add new task types**: Visual builder → JSON schema → automatic backend adaptation
- **Add new hardware**: Web form → database update → edge agent polls and adapts
- **Modify parameters**: Edit config → backend validates → edge agent receives update
- **Custom reports**: Select metrics → system generates appropriate visualizations

### 3. **Multi-Lab Scalability**
- **Organization isolation**: Each lab has separate data, users, devices
- **Template sharing**: Labs can publish/subscribe to task templates
- **Collaborative studies**: Cross-lab data aggregation with privacy controls

### 4. **Real-Time Monitoring**
- **Live dashboards**: WebSocket updates show trial-by-trial progress
- **Video streaming**: Watch primate behavior during task execution
- **Remote control**: Start/stop/pause experiments from anywhere
- **Alerts**: Automated notifications for errors, completion, welfare concerns

### 5. **Data Integrity and Reproducibility**
- **Complete audit trail**: Every parameter, result, and event logged
- **Version control**: Task definitions, configurations, and protocols versioned
- **Exact replication**: Re-run experiments with identical parameters
- **Statistical validation**: Built-in analysis tools, export to R/Python/MATLAB

---

*Version: 2.0.0*
*Last Updated: December 2024*
*Authors: LICS Development Team*
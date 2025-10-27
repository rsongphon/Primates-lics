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
The system follows a microservices pattern with clear service boundaries:
- **API Gateway (Kong)**: Central entry point providing:
  - Request routing with path-based and header-based rules
  - Rate limiting: 100 req/s per user, 1000 req/s per organization
  - JWT validation with 15-minute access tokens, 7-day refresh tokens
  - Request/response transformation and protocol translation
- **FastAPI Core Services**: Stateless REST APIs with:
  - OpenAPI 3.0 specification
  - Async request handling with 95th percentile < 200ms target
  - Database connection pooling (min: 5, max: 20 per service)
  - Structured logging with correlation IDs


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

#### Scratch-Based Task Builder
A revolutionary visual programming interface using Scratch 3.0 that allows researchers to create complex experimental protocols without coding knowledge. The builder generates executable tasks that run on edge devices with embedded Scratch VM runtime.

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
### 2.4 Service Dependency Matrix

| Service | Dependencies | Failure Impact | Recovery Strategy |
|---------|-------------|----------------|-------------------|
| API Gateway | None | Total system outage | Multi-instance HA with health checks |
| Auth Service | PostgreSQL, Redis | No new sessions | Cache valid tokens, read-only mode |
| Core Backend | PostgreSQL, Redis, Auth | No CRUD operations | Circuit breaker, cached responses |
| WebSocket Server | Redis, Auth | No real-time updates | Fallback to polling |
| Task Engine | Redis, PostgreSQL | No async processing | Dead letter queue, retry mechanism |
| Edge Agent | MQTT, Local SQLite | No cloud sync | Local operation mode, queue sync |
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
Kong API Gateway provides:
- **Route Configuration**:
  - `/api/v1/*` → Core Backend (port 8000)
  - `/ws/*` → WebSocket Server (port 8001) 
  - `/auth/*` → Auth Service (port 8002)
  - `/media/*` → Streaming Service (port 8003)
- **Rate Limiting Rules**:
  - Anonymous: 10 req/minute
  - Authenticated: 100 req/minute
  - Premium: 1000 req/minute
- **Security Policies**:
  - CORS with explicit origin whitelist
  - Request size limit: 10MB (100MB for file uploads)
  - SQL injection protection via request validation
  - XSS protection headers

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

#### Redis Streams for Event Sourcing
**Stream Patterns**:
Event sourcing for audit. Command pattern implementation. Saga orchestration. Event replay capability.

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
│   │   └── tasks/         # Task builder with Scratch
│   ├── (public)/          # Public routes
│   │   ├── login/
│   │   └── register/
│   ├── api/               # API routes (BFF pattern)
│   └── layout.tsx         # Root layout
├── components/
│   ├── ui/                # Shadcn components
│   ├── features/          # Feature-specific components
│   ├── scratch/          # Scratch integration
│   └── shared/            # Shared components
├── lib/
│   ├── api/               # API client functions
│   ├── scratch/         # Scratch VM integration
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

## 4.4 Task Builder Implementation

#### Scratch-Based Visual Programming
**Scratch Integration Architecture**:
- Scratch 3.0 GUI for visual task creation
- Custom Scratch extensions for lab hardware control
- Scratch VM runtime for task execution
- Real-time preview with simulated hardware responses
- Export to standalone task packages for edge devices

**Custom Scratch Blocks for Lab Research**:
- **Sensing Blocks**: RFID detection, touchscreen input, button press, proximity sensor
- **Display Blocks**: Show stimulus, display image, animate sprite, change background
- **Hardware Control**: Activate feeder, trigger LED, play sound through speaker
- **Data Collection**: Record response, log timestamp, save trial data
- **Experiment Flow**: Start trial, end trial, inter-trial interval, session control
- **Validation Blocks**: Check response correctness, calculate success rate

**Sprite-Based Task Design**:
Visual elements as sprites with behaviors. Background stages for different trial phases. Costume changes for stimulus variations. Sound integration for auditory tasks. Clone functionality for multiple stimuli.

**Event-Driven Experiment Logic**:
When RFID detected → Start experiment. When sprite clicked → Record response. When timer expires → Timeout trial. When trial ends → Calculate and save results. When session complete → Generate report.

#### Task Compilation and Deployment
**Scratch to Task Package Pipeline**:
Scratch project (.sb3) → JSON intermediate representation → Device-specific optimization → WebAssembly compilation for edge execution → Package with Scratch VM runtime → Deploy to edge devices.

**Runtime Execution**:
Embedded Scratch VM on Raspberry Pi. Hardware abstraction layer for GPIO. Real-time event handling. Local data buffering. Automatic synchronization with backend.

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

**Task Table (Scratch Projects)**:
Manages computational or experimental task definitions within an organization. Supports version control for iterative development. Stores both raw Scratch project files (.sb3) and compiled packages for edge device deployment. Includes customizable parameter configurations in JSON format. Tracks task ownership and creation timestamps for audit and collaboration purposes.


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

### 6.5 Database Performance Optimization

#### Indexing Strategy
```sql
-- Frequently queried columns
CREATE INDEX idx_experiments_status_date ON experiments(status, created_at DESC);
CREATE INDEX idx_sessions_subject_date ON sessions(subject_id, start_time DESC);
CREATE INDEX idx_trials_session_number ON trials(session_id, trial_number);

-- Full-text search
CREATE INDEX idx_experiments_search ON experiments USING gin(to_tsvector('english', name || ' ' || description));

-- Partitioning for time-series data
CREATE TABLE trial_events_2024_01 PARTITION OF trial_events
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

#### Connection Pooling
- Application: PgBouncer with transaction pooling
- Pool size: 20 connections per service
- Idle timeout: 30 seconds
- Query timeout: 5 seconds (30 seconds for reports)

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

### 9.1 Scratch-Based Visual Programming Interface

#### Scratch 3.0 Integration
**Core Components**:
- **Scratch GUI**: Web-based visual editor with drag-and-drop interface
- **Block Palette**: Custom categories for lab instruments and experiments
- **Stage Area**: Visual preview of task with interactive sprites
- **Code Area**: Block-based programming workspace
- **Backpack**: Reusable code snippets and sprite library

**Custom Extension Categories**:
- **Primate Sensing**: RFID detection, presence sensing, motion tracking
- **Stimulus Control**: Visual displays, audio playback, LED patterns
- **Response Collection**: Touchscreen zones, button inputs, hold duration
- **Hardware Control**: Feeders, doors, environmental controls
- **Data Logging**: Trial recording, timestamp capture, result storage
- **Experiment Flow**: Session management, trial sequencing, ITI control

#### Block Design System
**Block Types for Research**:
```scratch
// Example blocks in pseudo-Scratch notation
When [RFID tag detected v]
Wait for [button press v] for (10) seconds
If <response is correct> then
  Activate [pellet feeder v] for (1) pellets
  Log trial result [success v] with data (response_time)
End

Repeat (100) trials
  Show stimulus at random position
  Start timer
  Wait for response or timeout
  Calculate success rate
End

Broadcast [session complete v] and wait
Generate report with template [daily summary v]
```

**Visual Feedback System**:
Real-time sprite animation during block execution. Color-coded blocks by functionality. Connection hints showing compatible blocks. Error highlighting for invalid configurations.

### 9.2 Task Execution Engine

#### Scratch VM Runtime
**Execution Architecture**:
- **Thread Management**: Concurrent execution of multiple scripts
- **Event System**: Hardware events trigger Scratch hat blocks
- **Variable Scoping**: Global variables for session data, local for trials
- **Extension API**: Bridge between Scratch blocks and hardware drivers

**Performance Optimization**:
- Block compilation to JavaScript for faster execution
- Caching of frequently used sequences
- Lazy loading of extension features
- Memory management for long-running sessions

#### Hardware Extension Layer
**Device Communication**:
```javascript
class PrimateLabExtension {
  constructor(runtime) {
    this.runtime = runtime;
    this.mqttClient = new MQTTClient();
    this.hardwareState = {};
  }

  // Block implementation
  activateFeeder(args) {
    const feederID = args.FEEDER;
    const quantity = args.QUANTITY;
    return this.mqttClient.publish(`device/${feederID}/activate`, {
      quantity: quantity,
      timestamp: Date.now()
    });
  }

  whenRFIDDetected(args) {
    return new Promise((resolve) => {
      this.mqttClient.subscribe('rfid/detected', (message) => {
        if (message.tag === args.EXPECTED_TAG) {
          resolve();
        }
      });
    });
  }
}
```

### 9.3 Template Library and Sharing

#### Scratch Project Templates
**Pre-built Task Categories**:
- **Cognitive Tasks**: Working memory, attention, decision-making
- **Motor Tasks**: Reaching, grasping, coordination
- **Sensory Tasks**: Visual discrimination, auditory processing
- **Training Protocols**: Shaping procedures, habituation

**Template Structure**:
```json
{
  "template_id": "button-hold-training-v2",
  "name": "Button Hold Training",
  "category": "motor",
  "species": ["macaque", "marmoset"],
  "sprites": [
    {
      "name": "TargetButton",
      "costumes": ["small", "medium", "large"],
      "scripts": "[Scratch blocks in JSON format]"
    }
  ],
  "variables": {
    "holdDuration": 200,
    "successCriterion": 0.8,
    "maxTrials": 100
  },
  "extensions": ["primatelab", "datalogger"],
  "metadata": {
    "author": "Lab Name",
    "version": "2.0.0",
    "description": "Progressive button hold training with adaptive difficulty"
  }
}
```

**Community Marketplace**:
- Upload/download Scratch projects (.sb3 files)
- Version control with diff visualization
- Fork and modify existing templates
- Rating and review system
- Automatic compatibility checking

---

## 10. Security Implementation

### 10.1 Authentication & Authorization Architecture

#### OAuth2 + JWT Implementation
- **Token Structure**:
```json
  {
    "sub": "user_uuid",
    "org": "organization_uuid",
    "roles": ["researcher", "admin"],
    "exp": 1234567890,
    "iat": 1234567890,
    "jti": "unique_token_id"
  }
```
- **Token Lifecycle**:
  - Access Token: 15 minutes (stateless JWT)
  - Refresh Token: 7 days (stored in Redis)
  - Session timeout: 4 hours of inactivity
  
#### RBAC Permission Matrix
| Role | Experiments | Subjects | Devices | Reports | Admin |
|------|------------|----------|---------|---------|-------|
| Viewer | Read | Read | Read | Read | None |
| Researcher | CRUD Own | CRUD | Read | CRUD Own | None |
| Lab Manager | CRUD All | CRUD | CRUD | CRUD All | Read |
| Admin | CRUD All | CRUD | CRUD | CRUD All | CRUD |

### 10.2 Authentication Security

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

### 10.3 Authorization Implementation

#### Access Control
**RBAC Implementation**:
Role-based permissions. Resource-based permissions. Attribute-based extensions. Dynamic permission calculation.

**Policy Engine**:
Declarative policy definitions. Policy evaluation caching. Audit logging for decisions. Performance optimization.

### 10.4 Data Security

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

### 10.5 Infrastructure Security

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

### 11.4 Deployment Strategy

#### Blue-Green Deployment Process
1. **Preparation Phase**:
   - Build and test new version in staging
   - Run smoke tests and load tests
   - Prepare rollback plan

2. **Deployment Phase**:
```yaml
   deployment:
     strategy: blue-green
     health_check:
       endpoint: /health
       interval: 10s
       timeout: 5s
       success_threshold: 3
     traffic_switch:
       method: weighted  # 0% → 10% → 50% → 100%
       duration: 30m
     rollback:
       automatic: true
       error_threshold: 5%
```

3. **Validation Phase**:
   - Monitor error rates and latencies
   - Check business metrics
   - Verify data consistency

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

## 12.3 Docker Compose Configuration

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
      - DATABASE_URL=postgresql://lics:${POSTGRES_PASSWORD}@postgres:5432/lics
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
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
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
      - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_PASSWORD}
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
      - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
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
        "DATABASE_URL": "postgresql://lics:${POSTGRES_PASSWORD}@localhost:5432/lics",
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

### SLI/SLO Definitions

#### Service Level Indicators (SLIs)
| Metric | Definition | Measurement |
|--------|-----------|-------------|
| Availability | Successful requests / Total requests | HTTP 2xx,3xx / All requests |
| Latency | Request processing time | 95th percentile response time |
| Error Rate | Failed requests / Total requests | HTTP 5xx / All requests |
| Throughput | Requests processed per second | Count per time window |

#### Service Level Objectives (SLOs)
| Service | Availability | Latency (p95) | Error Rate |
|---------|-------------|---------------|------------|
| API Gateway | 99.9% | < 50ms | < 0.1% |
| Core Backend | 99.5% | < 200ms | < 0.5% |
| WebSocket | 99.0% | < 100ms | < 1.0% |
| Edge Sync | 95.0% | < 1000ms | < 5.0% |

#### Alert Configuration
- Page immediately: SLO violation > 5 minutes
- Warn: Error budget consumption > 50%
- Info: Anomaly detection triggers

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

### 15.4 Capacity Planning

#### Resource Requirements per 1000 Active Devices
| Component | CPU | Memory | Storage | Network |
|-----------|-----|--------|---------|---------|
| API Gateway | 2 cores | 4 GB | 10 GB | 100 Mbps |
| Core Backend | 4 cores | 8 GB | 20 GB | 200 Mbps |
| PostgreSQL | 8 cores | 32 GB | 500 GB SSD | 1 Gbps |
| Redis | 4 cores | 16 GB | 100 GB | 500 Mbps |
| MQTT Broker | 2 cores | 4 GB | 50 GB | 200 Mbps |

#### Auto-scaling Policies
```yaml
horizontal_pod_autoscaler:
  metrics:
    - type: Resource
      name: cpu
      target: 70%
    - type: Resource  
      name: memory
      target: 80%
    - type: Custom
      name: request_rate
      target: 100/s
  scale_up:
    stabilization: 60s
    policies:
      - type: Percent
        value: 100  # Double pods
        period: 60s
  scale_down:
    stabilization: 300s
    policies:
      - type: Percent
        value: 50  # Halve pods
        period: 60s
```

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

### 17.1 Phase Overview

#### Phase 1: Foundation (Weeks 1-2) ✅ COMPLETED
- Development environment setup
- CI/CD pipeline
- Database and messaging infrastructure
- Monitoring foundation

#### Phase 2: Backend Development (Weeks 3-4) ✅ COMPLETED
- FastAPI application
- Authentication system
- Core domain models
- WebSocket implementation

#### Phase 3: Frontend Development (Weeks 5-6) 🔄 IN PROGRESS
- Next.js setup ✅
- State management ✅
- Authentication flow ✅
- Core UI components (Current)

#### Phase 4: Edge Device Agent (Weeks 7-8)
- Agent architecture
- Hardware integration
- Local storage and sync
- Video streaming

#### Phase 5: Scratch-Based Task Builder (Weeks 9-10)
- Scratch 3.0 integration
- Custom laboratory extensions
- Task compilation pipeline
- Template marketplace

#### Phase 6: Integration & Testing (Weeks 11-12)
- System integration
- Performance optimization
- Security hardening
- Documentation

#### Phase 7: Production Deployment (Week 13)
- Cloud infrastructure setup
- Production deployment
- Monitoring and alerting
- Go-live

#### Phase 8: Post-Launch Support (Weeks 14-16)
- Bug fixes and stabilization
- Feature enhancements
- Performance tuning
- User training

### 17.2 Milestone Tracking

#### Current Status
```
Phase 1: ████████████████████ 100% Complete
Phase 2: ████████████████████ 100% Complete
Phase 3: ████████████░░░░░░░░ 60% In Progress
Phase 4: ░░░░░░░░░░░░░░░░░░░░ 0% Pending
Phase 5: ░░░░░░░░░░░░░░░░░░░░ 0% Pending
Phase 6: ░░░░░░░░░░░░░░░░░░░░ 0% Pending
Phase 7: ░░░░░░░░░░░░░░░░░░░░ 0% Pending
Phase 8: ░░░░░░░░░░░░░░░░░░░░ 0% Pending
```

### 17.3 Risk Register

#### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Hardware compatibility | High | Medium | Extensive HAL, testing matrix |
| Performance bottlenecks | High | Low | Load testing, optimization |
| Security vulnerabilities | High | Low | Security audits, scanning |
| Integration complexity | Medium | Medium | Incremental integration |

#### Operational Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep | High | Medium | Clear requirements, change control |
| Resource availability | Medium | Low | Cross-training, documentation |
| Timeline delays | Medium | Medium | Buffer time, parallel tasks |
| Budget overrun | Low | Low | Regular monitoring, controls |

### 17.4 Success Criteria

#### Technical Success
- All functional requirements implemented
- Performance targets met
- Security requirements satisfied
- Test coverage > 80%
- Documentation complete

#### Business Success
- User adoption > 90%
- System reliability > 99.9%
- Support tickets < 5%
- ROI achieved within 12 months
- User satisfaction > 4.5/5


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
#### Database Schema for Primates
```sql
-- Primate subjects table
CREATE TABLE primates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(100) NOT NULL,
    species VARCHAR(50) NOT NULL, -- 'macaque', 'marmoset', 'capuchin'
    subspecies VARCHAR(100),
    sex CHAR(1) CHECK (sex IN ('M', 'F')),
    birth_date DATE,
    weight_kg DECIMAL(5,2),
    rfid_tag VARCHAR(50) UNIQUE,
    training_level INTEGER DEFAULT 0, -- 0=naive, 1=basic, 2=intermediate, 3=advanced
    housing_cage VARCHAR(50),
    dietary_restrictions TEXT[],
    medical_notes TEXT,
    iacuc_protocol VARCHAR(50),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Welfare checks table
CREATE TABLE welfare_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primate_id UUID REFERENCES primates(id),
    check_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    weight_kg DECIMAL(5,2),
    temperature_c DECIMAL(4,1),
    appetite_score INTEGER CHECK (appetite_score BETWEEN 1 AND 5),
    activity_score INTEGER CHECK (activity_score BETWEEN 1 AND 5),
    stool_quality VARCHAR(20),
    hydration_status VARCHAR(20),
    notes TEXT,
    veterinarian_id UUID REFERENCES users(id),
    requires_followup BOOLEAN DEFAULT false
);

-- Session limits and restrictions
CREATE TABLE session_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primate_id UUID REFERENCES primates(id),
    max_sessions_per_day INTEGER DEFAULT 2,
    max_duration_minutes INTEGER DEFAULT 120,
    min_rest_minutes INTEGER DEFAULT 60,
    fluid_restriction_ml INTEGER,
    food_restriction_g INTEGER,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    approved_by UUID REFERENCES users(id),
    iacuc_approval VARCHAR(50)
);

-- Training history
CREATE TABLE training_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primate_id UUID REFERENCES primates(id),
    session_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    task_id UUID REFERENCES tasks(id),
    duration_minutes INTEGER,
    trials_completed INTEGER,
    success_rate DECIMAL(5,2),
    reward_volume_ml DECIMAL(5,2),
    notes TEXT,
    trainer_id UUID REFERENCES users(id)
);
```

#### API Endpoints for Primate Management
```python
@router.get("/primates")
async def list_primates(
    organization_id: UUID,
    species: Optional[str] = None,
    training_level: Optional[int] = None,
    active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List primates with filtering"""
    query = select(Primate).where(
        Primate.organization_id == organization_id,
        Primate.active == active
    )
    
    if species:
        query = query.where(Primate.species == species)
    if training_level is not None:
        query = query.where(Primate.training_level >= training_level)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/primates/{primate_id}/welfare-check")
async def create_welfare_check(
    primate_id: UUID,
    welfare_data: WelfareCheckCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Record welfare check"""
    # Create welfare check
    welfare_check = WelfareCheck(
        primate_id=primate_id,
        veterinarian_id=current_user.id,
        **welfare_data.dict()
    )
    db.add(welfare_check)
    
    # Check for concerning values
    if welfare_data.appetite_score < 3 or welfare_data.activity_score < 3:
        await send_alert(
            f"Welfare concern for primate {primate_id}",
            severity="medium"
        )
    
    await db.commit()
    return welfare_check
```

### 18.2 Cognitive Task Paradigms

#### Task Categories for Primates
```python
class CognitiveTaskCategory(str, Enum):
    FIXATION = "fixation"  # Eye tracking, gaze holding
    MEMORY = "memory"  # Working memory, DMTS
    DISCRIMINATION = "discrimination"  # Visual/auditory discrimination
    ATTENTION = "attention"  # Sustained attention, vigilance
    MOTOR = "motor"  # Reaching, grasping, manipulation
    DECISION = "decision"  # Decision making, gambling tasks
    SOCIAL = "social"  # Social cognition tasks

class TaskDifficulty(str, Enum):
    TRAINING = "training"  # Initial shaping
    EASY = "easy"  # High success expected
    MEDIUM = "medium"  # Moderate challenge
    HARD = "hard"  # Challenging
    EXPERT = "expert"  # For highly trained subjects
```

#### Example Task Implementations

**Delayed Match-to-Sample (DMTS)**:
```python
class DMTSTaskConfig(BaseModel):
    """Configuration for DMTS task"""
    sample_duration_ms: int = 1000
    delay_duration_ms: int = 5000
    choice_array_size: int = 4
    match_reward_ml: float = 0.5
    nonmatch_penalty_ms: int = 5000
    trial_count: int = 100
    difficulty_progression: bool = True
    
    class Config:
        schema_extra = {
            "example": {
                "sample_duration_ms": 1000,
                "delay_duration_ms": 5000,
                "choice_array_size": 4,
                "match_reward_ml": 0.5,
                "nonmatch_penalty_ms": 5000,
                "trial_count": 100,
                "difficulty_progression": True
            }
        }
```
**Motor Control Task**:
```python
class MotorControlTaskConfig(BaseModel):
    """Configuration for motor control task"""
    target_size_px: int = 100
    hold_duration_ms: int = 500
    movement_window_ms: int = 2000
    success_window_px: int = 50
    force_threshold_n: float = 0.5
    reward_schedule: str = "continuous"  # or "variable_ratio", "fixed_ratio"
    
    def validate_hardware(self, device: Device) -> bool:
        """Check if device has required hardware"""
        required = ["touchscreen", "force_sensor", "reward_dispenser"]
        return all(h in device.capabilities for h in required)

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

#### Task JavaScript Template
```javascript
// Web-based task template for browser execution
class PrimateTask {
    constructor(config) {
        this.config = config;
        this.results = [];
        this.currentTrial = 0;
        window.taskStatus = { started: false, completed: false };
    }
    
    async start() {
        window.taskStatus.started = true;
        
        // Wait for RFID detection
        await this.waitForSubject();
        
        // Run trials
        for (let i = 0; i < this.config.trialCount; i++) {
            this.currentTrial = i + 1;
            const result = await this.runTrial();
            this.results.push(result);
            
            // Send result to backend
            await this.sendResult(result);
            
            // Inter-trial interval
            await this.wait(this.config.itiDuration);
        }
        
        window.taskStatus.completed = true;
        window.taskResults = this.summarizeResults();
    }
    
    async runTrial() {
        // Display stimulus
        this.showStimulus();
        
        // Wait for response
        const response = await this.waitForResponse(this.config.responseWindow);
        
        // Process response
        const correct = this.checkResponse(response);
        
        // Deliver feedback
        if (correct) {
            await window.hardwareBridge.activateReward(this.config.rewardAmount);
        }
        
        return {
            trial: this.currentTrial,
            timestamp: Date.now(),
            stimulusType: this.currentStimulus,
            response: response,
            correct: correct,
            reactionTime: response.time - this.stimulusOnset
        };
    }
}
```

### 18.6 Task Creation Workflow

#### Visual Task Builder Interface

**Scratch-Based Editor**:

1. **Researcher opens Task Builder with Scratch GUI**
2. **Select or create sprites** for experimental stimuli:
   - Button sprite with size/color costumes
   - Target sprites for discrimination tasks
   - Background stages for different trial phases

3. **Drag blocks from custom palette**:
```scratch
   When [green flag clicked v]
   Set [trial count v] to (0)
   Repeat (100)
     Change [trial count v] by (1)
     Broadcast [start trial v] and wait
     Wait (2) seconds  // Inter-trial interval
   End
   Broadcast [session complete v]

   When I receive [start trial v]
   Go to [random position v]
   Set size to (pick random (50) to (150)) %
   Show
   Reset timer
   Wait until <<touching [mouse-pointer v]> and <mouse down?>>
   If <(timer) < (10)> then
     Broadcast [correct response v]
     Hide
   Else
     Broadcast [timeout v]
   End

   When I receive [correct response v]
   Activate [pellet feeder v] for (1) pellets
   Play sound [success v]
   Add (timer) to [response times v]
```

4. **Configure hardware extensions** via settings:
   - Map Scratch sprites to physical devices
   - Set GPIO pin assignments
   - Configure MQTT topics for hardware events
   - Calibrate touchscreen zones to sprite positions

5. **Test in simulation mode**:
   - Run task with virtual hardware
   - Preview visual elements and timing
   - Verify data collection logic
   - Check branching and conditions

6. **Export and deploy**:
   - Package Scratch project with VM runtime
   - Include hardware configuration
   - Deploy to edge devices via API
   - Auto-start on RFID detection

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

4. **Task Execution with Scratch**:
   ```javascript
   // Scratch blocks converted to JavaScript
   async function runExperiment() {
       // Wait for RFID confirmation
       await waitForRFID(expectedPrimateID);
       
       // Run trials
       for (let trial = 1; trial <= 100; trial++) {
           // Show stimulus (Scratch sprite)
           await showStimulus();
           
           // Wait for response
           const response = await waitForTouch();
           
           // Check correctness
           if (isCorrect(response)) {
               await deliverReward();
               logSuccess(trial);
           } else {
               await showError();
               logError(trial);
           }
           
           // Inter-trial interval
           await wait(2000);
       }
       
       // End session
       await endSession();
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

## 19. Scratch Task Builder Implementation Details

This section provides comprehensive implementation guidance for integrating Scratch 3.0 as the visual programming interface for the Lab Instrument Control System (LICS). The implementation enables researchers to create behavioral experiments using Scratch's block-based programming without writing traditional code.

---

### 19.1 System Architecture Overview

#### 19.1.1 Component Integration Strategy

The Scratch-based Task Builder integrates three primary architectural layers:

**Frontend Integration Layer**: The web application embeds Scratch 3.0 GUI as a React component within the Next.js framework. This requires webpack configuration modifications to handle Scratch's module system, including worker threads for the Scratch VM and asset management for sprites and sounds. The integration maintains bidirectional communication between the Scratch editor and the LICS application state through a custom messaging interface.

**Backend Processing Layer**: The FastAPI backend processes Scratch projects (.sb3 files) through specialized endpoints that handle project storage, compilation, and deployment. The backend extracts metadata from Scratch projects to determine hardware requirements, validates device compatibility, and generates optimized execution packages for edge devices.

**Edge Execution Layer**: Edge devices run a modified Scratch VM runtime that bridges Scratch's block execution with physical hardware control. This layer translates Scratch block commands into GPIO operations, MQTT messages, and sensor readings while maintaining real-time synchronization with the cloud infrastructure.

#### 19.1.2 Data Flow Architecture

**Project Creation Flow**: Researchers interact with the Scratch GUI to create tasks visually. The Scratch VM serializes the project into an .sb3 file format (a ZIP archive containing project.json and media assets). The frontend sends this binary data to the backend API, which stores it in MinIO object storage and PostgreSQL metadata tables.

**Compilation Pipeline**: When deploying a task, the backend compilation service extracts the Scratch project, analyzes block usage to determine hardware requirements, generates a JavaScript execution script that runs on the Scratch VM, bundles required extensions and runtime libraries, and creates a compressed deployment package optimized for the target edge device platform.

**Execution Architecture**: Edge devices receive deployment packages via MQTT, extract and initialize the Scratch VM runtime environment, load custom hardware extensions that map to physical devices, execute Scratch blocks in real-time while collecting experimental data, and stream results back to the cloud through event-driven messaging.

---

### 19.2 Frontend Implementation Architecture

#### 19.2.1 Scratch GUI Integration Approach

**Component Structure**: The Scratch Task Builder component wraps the Scratch GUI in a controlled React component that manages its lifecycle. The implementation requires careful handling of Scratch's internal state management, which uses Redux, to prevent conflicts with the application's Zustand stores.

**Module Loading Strategy**: Scratch modules must be loaded asynchronously due to their size and complexity. The implementation uses dynamic imports to load Scratch GUI, VM, and associated libraries only when the Task Builder is accessed. This approach reduces initial bundle size and improves application performance.

**Asset Management**: Scratch projects include various media assets (images, sounds) that must be handled through a custom storage adapter. The implementation configures Scratch Storage to use the LICS backend API for asset persistence, ensuring all project media is stored centrally and accessible across sessions.

#### 19.2.2 Custom Extension Architecture

**Extension Framework**: Custom Scratch extensions provide domain-specific blocks for laboratory hardware control. Each extension is a JavaScript class that defines block specifications, implementation methods, and hardware communication protocols. Extensions are loaded into the Scratch VM extension manager during initialization.

**Block Definition Structure**: Each custom block requires an opcode (unique identifier), block type (command, reporter, boolean, or hat), text template with argument placeholders, argument specifications with types and defaults, and implementation method that executes when the block runs.

**Hardware Communication**: Extensions communicate with hardware through an abstraction layer that handles protocol differences between development (browser) and production (edge device) environments. In development, hardware commands are simulated; in production, they translate to actual GPIO operations or MQTT messages.

#### 19.2.3 State Synchronization

**Project State Management**: The Scratch VM maintains its own internal state for sprites, variables, and execution context. The implementation synchronizes relevant state changes with the LICS application through event listeners on the VM runtime, allowing the application to track experiment progress and collect data.

**Save and Load Mechanisms**: Project saving involves serializing the current VM state to an .sb3 file, uploading to the backend with metadata extraction, updating the task database with version tracking, and triggering compilation for deployment readiness. Loading reverses this process, fetching the project from storage and restoring the VM state.

**Real-time Collaboration Considerations**: While Scratch doesn't natively support real-time collaboration, the implementation includes infrastructure for future enhancement through WebSocket-based state synchronization, allowing multiple researchers to view (though not simultaneously edit) the same project.

---

### 19.3 Backend Services Implementation

#### 19.3.1 API Endpoint Design

**Project Management Endpoints**: The backend provides RESTful endpoints for CRUD operations on Scratch projects. These endpoints handle binary .sb3 file uploads and downloads, metadata extraction and indexing, version control with diff generation, and template management for sharing common task patterns.

**Compilation Service Architecture**: The compilation service transforms Scratch projects into executable packages for edge devices. The process involves parsing the .sb3 ZIP archive to extract project.json, analyzing block usage to identify required extensions and hardware, generating a Node.js wrapper script for the Scratch VM, bundling all dependencies including the VM runtime, and optimizing the package for size and performance.

**Deployment Pipeline**: Deployment involves validating device compatibility with required hardware, customizing the package for the specific device configuration, transmitting the package via MQTT to the edge device, monitoring deployment status and handling failures, and triggering automatic execution upon successful deployment.

#### 19.3.2 Project Analysis Engine

**Block Analysis**: The backend analyzes Scratch blocks to understand task requirements. This involves traversing the block tree structure to identify all opcodes, mapping opcodes to hardware requirements and data collection needs, detecting potential conflicts or incompatibilities, and generating warnings for suboptimal patterns.

**Metadata Extraction**: Comprehensive metadata extraction provides insights into project complexity and requirements. The system extracts sprite count and types for visual complexity assessment, variable and list usage for data management understanding, extension requirements for hardware dependency checking, and estimated execution characteristics for resource planning.

**Compatibility Validation**: Before deployment, the system validates that the target device has all required hardware capabilities, sufficient computational resources for the task complexity, compatible firmware and runtime versions, and proper network connectivity for data streaming.

#### 19.3.3 Storage Architecture

**Project Storage Strategy**: Scratch projects are stored using a hybrid approach where binary .sb3 files are stored in MinIO object storage for efficient blob handling, project metadata is stored in PostgreSQL for queryability, and version history is maintained using git-like content addressing for efficient storage of project iterations.

**Template Repository**: The template system provides pre-built starting points for common experimental paradigms. Templates are stored with comprehensive metadata including species compatibility, required training levels, hardware requirements, and expected data output formats. The system supports template versioning, forking, and community rating.

**Asset Management**: Media assets within Scratch projects require special handling. The system extracts and indexes all assets for reusability, converts formats as needed for edge device compatibility, implements CDN distribution for frequently used assets, and maintains asset versioning tied to project versions.

---

### 19.4 Edge Device Runtime Implementation

#### 19.4.1 Scratch VM Deployment

**Runtime Environment Setup**: Edge devices require a Node.js environment with the Scratch VM and custom extensions. The implementation includes automated installation scripts for runtime dependencies, system service configuration for process management, resource monitoring and limitation enforcement, and automatic recovery from crashes or errors.

**Process Management**: The edge agent manages the Scratch VM process lifecycle including starting new experiments with proper environment configuration, monitoring process health and resource usage, handling graceful shutdowns and cleanup, and implementing watchdog timers for hung process detection.

**Memory Management**: Raspberry Pi devices have limited memory, requiring careful management. The implementation includes memory usage monitoring and alerting, garbage collection tuning for optimal performance, project size limitations based on available resources, and swap file configuration for handling memory pressure.

#### 19.4.2 Hardware Abstraction Layer

**GPIO Integration**: The hardware abstraction layer maps Scratch block commands to GPIO operations. This includes pin configuration for inputs and outputs, interrupt handling for event-driven blocks, PWM control for analog-like outputs, and timing precision for behavioral requirements.

**Sensor Integration**: Various sensors connect through different protocols requiring protocol-specific drivers (I2C, SPI, UART), calibration and scaling for accurate measurements, buffering and filtering for noise reduction, and event generation for Scratch hat blocks.

**Actuator Control**: Output devices like feeders and speakers require precise control mechanisms including timing sequences for mechanical devices, safety interlocks to prevent damage, state verification for feedback, and error recovery procedures.

#### 19.4.3 Data Collection Pipeline

**Trial Data Capture**: The runtime captures experimental data at multiple levels including block-level execution timestamps, hardware activation logs, sensor readings with precise timing, and computed metrics from Scratch reporters.

**Local Buffering Strategy**: Data is buffered locally to handle network interruptions using SQLite for structured trial data, circular buffers for high-frequency sensor data, compression for efficient storage, and prioritized queuing for upload when connected.

**Synchronization Protocol**: Data synchronization with the cloud follows a robust protocol including batch uploads for efficiency, acknowledgment tracking for reliability, conflict resolution for concurrent modifications, and automatic retry with exponential backoff for failures.

---

### 19.5 Custom Extension Development

#### 19.5.1 Extension Architecture Principles

**Modular Design**: Each extension encapsulates related functionality into a cohesive module. Extensions should follow single responsibility principle, provide clear and intuitive block interfaces, handle errors gracefully with user feedback, and maintain state consistency across block executions.

**Block Design Guidelines**: Effective blocks follow consistent naming conventions, provide appropriate default values, validate inputs to prevent errors, give clear visual feedback during execution, and support both synchronous and asynchronous operations appropriately.

**Hardware Abstraction**: Extensions abstract hardware complexity from researchers by providing high-level operations that make sense in experimental context, handling protocol details internally, managing timing and synchronization automatically, and reporting errors in terms researchers understand.

#### 19.5.2 Core Laboratory Extensions

**PrimateLab Extension**: This primary extension provides blocks specific to primate research including RFID-based subject identification, trial sequencing and control, reward delivery mechanisms, response collection and timing, and automated data logging and analysis.

**Hardware Control Extension**: Lower-level hardware control blocks enable direct GPIO manipulation for custom devices, I2C and SPI communication for sensors, PWM generation for motor control, analog-to-digital conversion for measurements, and interrupt handling for event detection.

**Data Logger Extension**: Data collection and analysis blocks support creating and managing datasets, logging experimental measurements, calculating real-time statistics, exporting data in various formats, and generating summary reports automatically.

#### 19.5.3 Extension Development Workflow

**Development Process**: Creating new extensions follows a structured workflow starting with requirements analysis with researchers, block design and user experience planning, implementation with hardware simulation, testing across different scenarios, and documentation with examples.

**Testing Strategy**: Extensions require comprehensive testing including unit tests for individual block functions, integration tests with hardware simulators, edge device testing with actual hardware, performance testing under load conditions, and user acceptance testing with researchers.

**Deployment Pipeline**: Extension deployment involves code review and security validation, bundling with the Scratch VM runtime, version management and compatibility tracking, distribution to edge devices, and monitoring for errors and usage patterns.

---

### 19.6 Task Compilation and Optimization

#### 19.6.1 Compilation Pipeline Architecture

**Parse Phase**: The compiler first parses the Scratch project structure by extracting the project.json from the .sb3 archive, building an abstract syntax tree of blocks, identifying all sprites and their scripts, cataloging variables and lists, and determining extension dependencies.

**Analysis Phase**: Static analysis determines execution characteristics including hardware requirements from block usage, potential parallel execution opportunities, memory requirements estimation, approximate execution time per trial, and data output volume predictions.

**Generation Phase**: Code generation produces an optimized execution package by translating Scratch blocks to JavaScript, inlining frequently used procedures, eliminating dead code paths, optimizing loop structures, and pre-computing constant expressions.

#### 19.6.2 Optimization Strategies

**Performance Optimizations**: The compiler applies various optimizations for edge device execution including block fusion for reduced overhead, loop unrolling for tight inner loops, constant propagation and folding, common subexpression elimination, and branch prediction hints.

**Memory Optimizations**: Memory usage is minimized through sprite and costume compression, variable lifetime analysis, stack frame size reduction, heap allocation minimization, and garbage collection hints.

**Hardware-Specific Optimizations**: The compiler tailors output for specific edge devices by utilizing hardware acceleration features, optimizing for CPU cache sizes, leveraging SIMD instructions where available, minimizing system calls, and batching I/O operations.

#### 19.6.3 Deployment Package Generation

**Package Structure**: The deployment package contains all necessary components including the compiled Scratch project, Scratch VM runtime libraries, custom extension implementations, hardware configuration files, and startup scripts and metadata.

**Compression and Bundling**: Packages are optimized for size through JavaScript minification and tree shaking, asset compression with format optimization, duplicate file elimination, compressed archive generation, and incremental update support.

**Version Management**: Deployment packages are versioned for rollback capability with semantic versioning for compatibility tracking, dependency version locking, upgrade path definitions, compatibility matrix maintenance, and automated testing across versions.

---

### 19.7 Testing and Validation Framework

#### 19.7.1 Simulation Environment

**Virtual Hardware Simulation**: The simulator provides a realistic testing environment without physical hardware by emulating GPIO states and transitions, simulating sensor readings with noise, modeling actuator responses with delays, generating realistic timing variations, and supporting failure scenario injection.

**Behavioral Modeling**: The simulator models experimental subject behavior including response time distributions, learning curves over trials, fatigue and satiation effects, attention and motivation variations, and individual difference parameters.

**Performance Profiling**: Simulation includes performance analysis tools for measuring block execution timing, identifying performance bottlenecks, estimating resource usage, predicting battery life impact, and validating real-time constraints.

#### 19.7.2 Testing Strategies

**Unit Testing Approach**: Individual components are tested in isolation including Scratch block implementations, hardware communication protocols, data collection accuracy, error handling pathways, and state management correctness.

**Integration Testing Framework**: System-wide testing validates end-to-end task execution, data flow from blocks to database, hardware control sequences, error propagation and recovery, and concurrent task execution.

**Hardware-in-the-Loop Testing**: Physical hardware testing verifies GPIO signal generation accuracy, sensor reading precision, actuator control reliability, timing requirement satisfaction, and electromagnetic compatibility.

#### 19.7.3 Validation Protocols

**Scientific Validation**: Tasks undergo scientific validation to ensure experimental design integrity, data collection accuracy, statistical power adequacy, reproducibility across sessions, and compliance with protocols.

**Performance Validation**: System performance is validated against requirements including response latency limits, throughput requirements, reliability targets, availability goals, and scalability projections.

**User Acceptance Testing**: Researchers validate the system through task creation efficiency, interface intuitiveness, result accuracy, workflow integration, and training requirements.

---

### 19.8 Monitoring and Diagnostics

#### 19.8.1 Runtime Monitoring

**Execution Monitoring**: The system monitors Scratch task execution in real-time including block execution counts and timing, hardware activation patterns, data collection rates, error and warning generation, and resource utilization trends.

**Performance Metrics Collection**: Comprehensive metrics provide operational insights including CPU and memory usage, network bandwidth utilization, disk I/O patterns, power consumption, and temperature monitoring.

**Anomaly Detection**: Automated detection identifies potential issues including unusual execution patterns, hardware communication failures, data collection gaps, performance degradations, and resource exhaustion risks.

#### 19.8.2 Diagnostic Tools

**Debug Mode**: Development and troubleshooting are supported through block-by-block execution tracing, variable value inspection, hardware state monitoring, network traffic analysis, and detailed error reporting.

**Log Management**: Comprehensive logging captures all system events with structured log formats for analysis, log level configuration per component, centralized log aggregation, search and filter capabilities, and automated alert generation.

**Remote Diagnostics**: Edge devices support remote troubleshooting through SSH tunnel establishment, remote desktop access, log streaming to cloud, configuration updates, and remote restart capabilities.

#### 19.8.3 Health Reporting

**System Health Metrics**: Regular health assessments monitor service availability status, response time measurements, error rate tracking, queue depth monitoring, and connection pool utilization.

**Hardware Health Monitoring**: Physical device health is tracked through sensor diagnostic checks, actuator response verification, power supply stability, temperature monitoring, and wear indicator tracking.

**Data Integrity Verification**: Data quality is ensured through completeness checking, consistency validation, duplicate detection, corruption identification, and synchronization verification.

---

### 19.9 Security Considerations

#### 19.9.1 Code Security

**Scratch Project Validation**: Projects undergo security screening for malicious code patterns, infinite loop detection, resource exhaustion prevention, unauthorized hardware access, and data exfiltration attempts.

**Sandboxing**: Execution environments are isolated through process-level sandboxing, filesystem access restrictions, network communication limits, resource usage quotas, and system call filtering.

**Extension Security**: Custom extensions are vetted through code review requirements, capability-based permissions, API access restrictions, signing and verification, and automated security scanning.

#### 19.9.2 Data Security

**Encryption**: Data is protected at multiple levels including TLS for network communication, encryption at rest for storage, encrypted configuration files, secure key management, and hardware security module integration.

**Access Control**: Multi-layer access control ensures project ownership verification, organization-based isolation, role-based permissions, API authentication, and audit trail generation.

**Privacy Protection**: Experimental data privacy is maintained through subject anonymization, data minimization practices, retention policy enforcement, consent tracking, and GDPR compliance.

#### 19.9.3 Device Security

**Edge Device Hardening**: Devices are secured through minimal attack surface, regular security updates, firewall configuration, intrusion detection, and physical security measures.

**Communication Security**: All communication channels are protected using mutual TLS authentication, message signing and verification, replay attack prevention, secure firmware updates, and certificate rotation.

**Compromise Detection**: Security monitoring identifies potential compromises through anomaly detection, integrity checking, unauthorized access attempts, configuration changes, and suspicious network activity.

---

### 19.10 Performance Optimization Strategies

#### 19.10.1 Frontend Optimization

**Load Time Optimization**: Initial load performance is improved through code splitting for lazy loading, bundle size minimization, asset optimization, CDN distribution, and browser caching strategies.

**Runtime Performance**: Smooth operation is ensured via React rendering optimization, memory leak prevention, efficient state updates, Web Worker utilization, and requestAnimationFrame usage.

**Scratch VM Performance**: The Scratch environment is optimized through VM configuration tuning, extension lazy loading, sprite limit management, script complexity limits, and rendering optimization.

#### 19.10.2 Backend Optimization

**API Performance**: Response times are minimized through database query optimization, caching strategy implementation, connection pool tuning, async operation usage, and batch processing support.

**Compilation Performance**: Project compilation speed is improved via parallel processing utilization, incremental compilation support, result caching, optimization level selection, and distributed compilation options.

**Storage Optimization**: Efficient storage is achieved through deduplication strategies, compression algorithms, tiered storage usage, archive policies, and CDN integration.

#### 19.10.3 Edge Device Optimization

**Resource Management**: Limited resources are managed through memory usage optimization, CPU utilization control, disk space management, network bandwidth conservation, and power consumption minimization.

**Execution Optimization**: Task execution is optimized via JavaScript engine tuning, hardware acceleration usage, interrupt handling optimization, scheduling optimization, and cache utilization.

**Data Collection Optimization**: Efficient data handling includes buffering strategies, compression techniques, batch transmission, priority queuing, and bandwidth adaptation.

---

### 19.11 Scalability Architecture

#### 19.11.1 Horizontal Scalability

**Service Scaling**: The system scales through microservice architecture, container orchestration, load balancer configuration, auto-scaling policies, and geographic distribution.

**Database Scaling**: Data layer scales via read replica deployment, sharding strategies, connection pooling, query optimization, and caching layers.

**Storage Scaling**: Storage capacity scales through object storage expansion, CDN integration, archive tiering, distributed filesystems, and backup strategies.

#### 19.11.2 Vertical Scalability

**Resource Scaling**: Individual components scale through memory allocation increases, CPU core additions, network bandwidth upgrades, storage capacity expansion, and GPU acceleration.

**Performance Scaling**: Processing power scales via compilation parallelization, batch processing support, queue depth increases, thread pool expansion, and cache size growth.

**Edge Device Scaling**: Device capabilities scale through hardware upgrades, cluster deployment, load distribution, failover support, and remote management.

#### 19.11.3 Multi-Tenancy Scaling

**Organization Isolation**: The system supports multiple organizations through database partitioning, resource quotas, network isolation, storage separation, and compute allocation.

**Template Sharing**: Collaboration scales via marketplace infrastructure, version management, access control, usage tracking, and quality ratings.

**Cross-Organization Features**: Shared resources are managed through template libraries, extension repositories, documentation wikis, community forums, and best practices.

---

### 19.12 Deployment Strategies

#### 19.12.1 Cloud Deployment

**Container Orchestration**: Kubernetes deployment provides service discovery, health checking, secret management, configuration maps, and persistent volumes.

**Service Mesh**: Istio integration enables traffic management, security policies, observability, resilience, and policy enforcement.

**Continuous Deployment**: GitOps workflows support infrastructure as code, automated rollouts, canary deployments, rollback capabilities, and environment promotion.

#### 19.12.2 Edge Deployment

**Device Provisioning**: New devices are onboarded through automated discovery, identity assignment, certificate provisioning, configuration deployment, and health verification.

**Update Management**: Software updates are managed via staged rollouts, compatibility checking, rollback support, offline updates, and differential updates.

**Fleet Management**: Device fleets are managed through centralized monitoring, remote configuration, batch operations, grouping strategies, and compliance tracking.

#### 19.12.3 Hybrid Deployment

**Cloud-Edge Coordination**: Hybrid deployments coordinate through synchronization protocols, conflict resolution, cache management, failover handling, and load distribution.

**Data Management**: Data flows are managed via edge processing, cloud analytics, archive strategies, privacy compliance, and bandwidth optimization.

**Resilience Patterns**: System resilience is ensured through circuit breakers, retry logic, fallback mechanisms, graceful degradation, and disaster recovery.

---

This comprehensive implementation guide provides detailed architectural and technical guidance for implementing the Scratch-based Task Builder System without relying on code examples. Each section describes the key concepts, design decisions, and implementation strategies necessary for successful system development.

*End of Section 19*

## Key Advantages of LICS for Primate Research

### 1. **Scratch-Based No-Code Operation**
Researchers interact **only through Scratch visual interface**:
- Build tasks with drag-and-drop blocks (no JavaScript knowledge)
- Configure experiment parameters via block properties (no config files)
- Register hardware via Scratch extensions (no GPIO code)
- Generate reports via Scratch reporter blocks (no data analysis scripts)

### 2. **Flexibility Without Code Changes**
- **Add new task types**: Scratch blocks → automatic backend adaptation
- **Add new hardware**: Scratch extension → edge agent integration
- **Modify parameters**: Edit blocks → backend validates → edge receives
- **Custom reports**: Select data blocks → system generates visualizations

### 3. **Multi-Lab Scalability**
- **Organization isolation**: Each lab has separate data, users, devices
- **Template sharing**: Labs can publish/subscribe to Scratch templates
- **Collaborative studies**: Cross-lab data aggregation with privacy controls

### 4. **Real-Time Monitoring**
- **Live dashboards**: WebSocket updates show trial-by-trial progress
- **Video streaming**: Watch primate behavior during task execution
- **Remote control**: Start/stop/pause experiments from anywhere
- **Alerts**: Automated notifications for errors, completion, welfare concerns

### 5. **Data Integrity and Reproducibility**
- **Complete audit trail**: Every parameter, result, and event logged
- **Version control**: Scratch projects, configurations, and protocols versioned
- **Exact replication**: Re-run experiments with identical Scratch projects
- **Statistical validation**: Built-in analysis tools, export to R/Python/MATLAB

---

## 20. Error Handling & Recovery Procedures

### 20.1 Error Classification
| Category | Examples | Recovery | User Impact |
|----------|----------|----------|-------------|
| Transient | Network timeout, Rate limit | Automatic retry with backoff | Delayed response |
| Recoverable | Database lock, Queue full | Circuit breaker + fallback | Degraded service |
| Critical | Data corruption, Security breach | Manual intervention | Service unavailable |
| Fatal | Hardware failure, Data loss | Disaster recovery | Extended outage |

### 20.2 Retry Strategy
```yaml
retry_policy:
  max_attempts: 3
  backoff:
    initial: 1s
    multiplier: 2
    max: 30s
  retryable_errors:
    - CONNECTION_TIMEOUT
    - SERVICE_UNAVAILABLE
    - RATE_LIMITED
```

### 20.3 Circuit Breaker Configuration
- Failure threshold: 50% over 10 requests
- Timeout: 30 seconds
- Half-open test: 1 request every 5 seconds
- Recovery: 3 successful requests

### 20.4 Graceful Degradation Modes
1. **Read-only mode**: Database writes disabled
2. **Local mode**: Edge devices operate independently
3. **Essential mode**: Only critical operations allowed
4. **Maintenance mode**: User-facing services disabled

---
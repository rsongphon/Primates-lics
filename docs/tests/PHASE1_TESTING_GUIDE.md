# Phase 1 - Foundation Setup Testing Guide

**Version**: 1.0
**Date**: 2025-10-13
**Scope**: Infrastructure, Database Layer, Message Broker, Monitoring Stack, System Integration
**Phase**: Phase 1 - Foundation Setup (Weeks 1-2 + Week 3 Validation)

---

## Table of Contents
1. [Setup Instructions](#1-setup-instructions)
2. [Automated Testing](#2-automated-testing)
3. [Manual Testing Procedures](#3-manual-testing-procedures)
4. [Expected Outcomes](#4-expected-outcomes)
5. [Test Results Recording](#5-test-results-recording)
6. [Troubleshooting](#6-troubleshooting)
7. [Appendices](#7-appendices)

---

## 1. Setup Instructions

### 1.1 Prerequisites - Docker Development Environment

**⚠️ Critical**: All Phase 1 testing is performed against Docker containerized services. Do NOT test against locally installed services.

#### System Requirements
- **OS**: macOS 12+, Ubuntu 22.04+, Windows 11 with WSL2
- **Docker**: 24.0+ with Docker Compose 2.20+
- **RAM**: Minimum 16GB (32GB recommended)
- **Disk**: 50GB free space
- **CPU**: 4+ cores (8+ recommended)

#### Pre-Test Environment Check

```bash
# Verify Docker installation
docker --version
docker-compose --version

# Check Docker daemon is running
docker info

# Verify available resources
docker system df
```

**Expected Output**:
```
Docker version 24.0.x or higher
Docker Compose version v2.20.x or higher
Server running: true
```

### 1.2 Starting the Development Environment

**Primary Command** (starts all services):
```bash
# Navigate to project root
cd /Users/beacon/Primates-lics

# Start complete infrastructure
make dev
```

This single command starts:
- **Databases**: PostgreSQL + TimescaleDB (port 5433), Redis (6380), InfluxDB (8087)
- **Message Brokers**: MQTT (1884, 9003), MinIO (9010, 9011)
- **Monitoring Stack**: Prometheus (9090), Grafana (3001), Jaeger v2 (16686), Alertmanager (9093), Loki (3100)
- **Exporters**: PostgreSQL Exporter (9187), Redis Exporter (9121)
- **Support Services**: PgBouncer (6433), PgAdmin (5050), Redis Commander (8081), MailHog (8025), Promtail (log collection)

**📊 Full Observability**: The development environment now includes the complete monitoring stack (Prometheus, Grafana, Loki, Promtail, Alertmanager) providing production-like observability capabilities.

**Wait Time**: Allow 60-90 seconds for all services to initialize health checks (monitoring stack adds ~30 seconds to startup).

### 1.3 Verify Services Are Running

```bash
# Check all containers
docker-compose -f docker-compose.dev.yml ps

# Quick health check
make health-check
```

**Expected Output**:
```
NAME                                      STATUS        PORTS
primates-lics-postgres-dev-1              Up (healthy)  0.0.0.0:5433->5432/tcp
primates-lics-redis-dev-1                 Up (healthy)  0.0.0.0:6380->6379/tcp
primates-lics-mqtt-dev-1                  Up (healthy)  0.0.0.0:1884->1883/tcp
primates-lics-minio-dev-1                 Up (healthy)  0.0.0.0:9010-9011/tcp
primates-lics-prometheus-dev-1            Up (healthy)  0.0.0.0:9090->9090/tcp
primates-lics-grafana-dev-1               Up (healthy)  0.0.0.0:3001->3000/tcp
primates-lics-jaeger-1                    Up (healthy)  0.0.0.0:16686->16686/tcp
primates-lics-loki-dev-1                  Up            0.0.0.0:3100->3100/tcp
primates-lics-promtail-dev-1              Up            (no external ports)
primates-lics-alertmanager-dev-1          Up            0.0.0.0:9093->9093/tcp
primates-lics-postgres-exporter-dev-1     Up            0.0.0.0:9187->9187/tcp
primates-lics-redis-exporter-dev-1        Up            0.0.0.0:9121->9121/tcp
...
```

### 1.4 Access Development Tools

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Grafana** | http://localhost:3001 | admin / admin123 | Dashboards & Visualization |
| **Prometheus** | http://localhost:9090 | (none) | Metrics & Query |
| **Alertmanager** | http://localhost:9093 | (none) | Alert Management |
| **Jaeger UI** | http://localhost:16686 | (none) | Distributed Tracing |
| **Loki** | http://localhost:3100 | (none) | Log Aggregation API |
| PgAdmin | http://localhost:5050 | admin@lics.dev / admin123 | PostgreSQL Management |
| Redis Commander | http://localhost:8081 | (none) | Redis Monitoring |
| MinIO Console | http://localhost:9011 | lics-dev-admin / lics-dev-minio-password-2024 | Object Storage |
| MailHog | http://localhost:8025 | (none) | Email Testing |

**Note**: Grafana comes pre-configured with datasources for Prometheus, Loki, Jaeger, PostgreSQL, Redis, and InfluxDB. The monitoring stack is production-ready but runs with development-friendly retention policies.

---

## 2. Automated Testing

### 2.0 Automated Manual Test Suite (NEW)

**Purpose**: Complete automation of all manual test procedures from Section 3

The Phase 1 Manual Test Suite provides 100% automation coverage of manual testing procedures, allowing for:
- Rapid validation of infrastructure setup
- Consistent, repeatable testing across environments
- Automated test execution in CI/CD pipelines
- Detailed step-by-step validation matching manual procedures

#### Quick Start - Run All Tests

```bash
# Run all automated manual tests with complete workflow (tests + reports)
make test-phase1-full

# Run all tests with verbose output
make test-phase1-manual-verbose

# Run all tests and save JSON results
make test-phase1-manual
```

**What This Tests**: All 13 test cases from Section 3 (Infrastructure, Database, Messaging, Monitoring, Integration)

**Expected Execution Time**: 5-8 minutes

**Output**:
- JSON results: `test-results/phase1_manual_*.json`
- Markdown report: `test-results/reports/phase1_report_*.md`
- HTML report: `test-results/reports/phase1_report_*.html`

#### Run Specific Test Cases

```bash
# List all available test cases
make test-phase1-list

# Run specific test case
make test-phase1-manual-tc TC=TC-INFRA-001  # Docker Container Health
make test-phase1-manual-tc TC=TC-DB-001     # PostgreSQL CRUD Operations
make test-phase1-manual-tc TC=TC-MSG-003    # MinIO Object Storage
make test-phase1-manual-tc TC=TC-INT-001    # End-to-End Data Flow
```

#### Generate Reports from Existing Results

```bash
# Generate report from latest test results
make generate-test-report INPUT=test-results/phase1_manual_20251014_120000.json

# Or run the script directly for more options
python3 tools/scripts/generate-test-report.py \
    --input test-results/phase1_manual_20251014_120000.json \
    --format html \
    --output phase1_report.html
```

#### Available Test Cases

The automated suite includes all 13 manual test cases:

**Infrastructure Tests** (Section 3.1)
- `TC-INFRA-001`: Docker Container Health
- `TC-INFRA-002`: Network Connectivity Between Services

**Database Tests** (Section 3.2)
- `TC-DB-001`: PostgreSQL Connection and CRUD Operations
- `TC-DB-002`: TimescaleDB Hypertables
- `TC-DB-003`: Redis Cache Operations
- `TC-DB-004`: Redis Streams and Pub/Sub

**Messaging Tests** (Section 3.3)
- `TC-MSG-001`: MQTT Broker Connectivity
- `TC-MSG-002`: MQTT Publish/Subscribe
- `TC-MSG-003`: MinIO Object Storage

**Monitoring Tests** (Section 3.4)
- `TC-MON-001`: Prometheus Metrics Collection
- `TC-MON-002`: Grafana Dashboard Access
- `TC-MON-003`: Jaeger v2 Distributed Tracing

**Integration Tests** (Section 3.5)
- `TC-INT-001`: End-to-End Data Flow

#### Test Report Formats

**JSON Format** (Machine-readable):
```json
{
  "timestamp": "2025-10-14T12:00:00",
  "duration_seconds": 342.5,
  "summary": {
    "total_tests": 13,
    "passed_tests": 12,
    "failed_tests": 1,
    "success_rate": 92.31
  },
  "test_cases": { ... }
}
```

**Markdown Format** (Human-readable):
- Matches test execution log template (Section 5.1)
- Includes system configuration
- Pass/fail status for each test
- Performance metrics
- Recommendations

**HTML Format** (Interactive dashboard):
- Color-coded test results
- Expandable test steps
- System health overview
- Performance charts
- Executive summary

#### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run Phase 1 Automated Tests
  run: |
    make dev-detached
    sleep 60  # Wait for services to initialize
    make test-phase1-full

- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: phase1-test-results
    path: test-results/
```

#### Troubleshooting Automated Tests

**Issue**: Tests fail with "Docker client not available"
```bash
# Solution: Ensure Docker daemon is running
docker ps
make dev
```

**Issue**: Tests timeout waiting for services
```bash
# Solution: Wait longer for services to initialize
make dev-detached
sleep 90  # Increase wait time
make test-phase1-manual
```

**Issue**: Missing Python dependencies
```bash
# Solution: Install required packages
pip install asyncpg redis aiomqtt minio influxdb-client requests docker
```

**Issue**: Permission denied for Docker socket
```bash
# Solution: Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Then log out and back in
```

#### Advantages Over Manual Testing

✅ **Speed**: 5-8 minutes vs 2-3 hours manual testing
✅ **Consistency**: Same steps executed every time
✅ **Coverage**: Tests all edge cases automatically
✅ **Repeatability**: Can run multiple times per day
✅ **CI/CD Integration**: Automated validation in pipelines
✅ **Detailed Reports**: HTML dashboards with drill-down capabilities
✅ **Known Issues Tracking**: Automatically identifies expected failures
✅ **Historical Comparison**: Track improvement over time

---

### 2.1 Quick Validation Commands

#### Comprehensive System Validation
```bash
# Full system validation (all tests)
make validate-all

# Quick validation (essential checks only)
make validate-quick

# Performance validation with benchmarks
make validate-performance

# Stress testing
make validate-stress
```

#### Component-Specific Testing
```bash
# Infrastructure validation
make test-infrastructure

# Database testing (PostgreSQL, Redis, InfluxDB)
make test-database

# Messaging services (MQTT, MinIO, Redis Pub/Sub)
make test-messaging

# System integration (end-to-end)
make test-system-integration
```

### 2.2 Detailed Testing Procedures

#### Test Suite 1: Infrastructure Validation

**Purpose**: Validate Docker infrastructure and service health

**Command**:
```bash
make test-infrastructure
# OR
python3 tools/scripts/validate-infrastructure.py --format text
```

**What It Tests**:
- Docker daemon connectivity
- Container health status (all services)
- Network configuration and connectivity
- Volume mounts and persistence
- Port mappings correctness
- Resource allocation (CPU, memory)

**Expected Execution Time**: 30-45 seconds

**Expected Output**:
```
=== Infrastructure Validation Report ===
Timestamp: 2025-10-13T10:30:00Z
Overall Status: HEALTHY

Container Health:
✓ postgres-dev: healthy (uptime: 2h 15m)
✓ redis-dev: healthy (uptime: 2h 15m)
✓ minio: healthy (uptime: 2h 15m)
✓ mqtt: running (uptime: 2h 15m)
✓ prometheus: healthy (uptime: 2h 15m)
✓ grafana: healthy (uptime: 2h 14m)
✓ jaeger: healthy (uptime: 2h 14m)

Network Connectivity: PASS (7/7)
Volume Mounts: PASS (8/8)
Port Mappings: PASS (15/15)

Summary: 100% infrastructure operational
```

---

#### Test Suite 2: Database Comprehensive Testing

**Purpose**: Validate all database services functionality

**Command**:
```bash
make test-database
# OR
python3 tools/scripts/test-database-suite.py --test all --format text
```

**What It Tests**:

**PostgreSQL + TimescaleDB**:
- Basic connectivity
- CRUD operations (CREATE, READ, UPDATE, DELETE)
- Transaction support (BEGIN, COMMIT, ROLLBACK)
- TimescaleDB extension installed
- Hypertable creation and querying
- Connection pooling (via PgBouncer)
- Database size and performance metrics

**Redis**:
- Basic operations (GET, SET, DEL)
- Data structures (Strings, Lists, Sets, Hashes, Sorted Sets)
- Redis Streams (XADD, XREAD, XGROUP)
- Pub/Sub messaging (PUBLISH, SUBSCRIBE)
- Consumer groups
- TTL and expiration
- Memory usage and performance

**InfluxDB** (if operational):
- Health endpoint check
- Bucket creation and listing
- Write operations
- Query operations
- Retention policies

**Expected Execution Time**: 1-2 minutes

**Expected Output**:
```
=== Database Test Suite Report ===
Timestamp: 2025-10-13T10:35:00Z

PostgreSQL Tests: PASS (15/15)
  ✓ Connectivity: 25ms
  ✓ CRUD Operations: 45ms
  ✓ Transactions: 38ms
  ✓ TimescaleDB Extension: OK (version 2.10.2)
  ✓ Hypertables: 0 (expected for fresh install)
  ✓ Connection Count: 3 active
  ✓ Database Size: 8.5 MB

Redis Tests: PASS (18/18)
  ✓ Basic Operations: 12ms
  ✓ String Operations: 8ms
  ✓ List Operations: 15ms
  ✓ Hash Operations: 14ms
  ✓ Set Operations: 13ms
  ✓ Sorted Set Operations: 16ms
  ✓ Redis Streams: 22ms (3 streams configured)
  ✓ Pub/Sub: 18ms
  ✓ Consumer Groups: OK
  ✓ Memory Usage: 2.3 MB

InfluxDB Tests: SKIPPED (deferred to Phase 5)

Overall Database Health: 95% (33/35 tests passing)
```

---

#### Test Suite 3: Messaging Services Testing

**Purpose**: Validate messaging infrastructure (MQTT, MinIO, Redis messaging)

**Command**:
```bash
make test-messaging
# OR
python3 tools/scripts/test-messaging-suite.py --test all --format text
```

**What It Tests**:

**MQTT Broker (Mosquitto)**:
- Broker connectivity
- Anonymous connection support
- Publish/Subscribe operations
- QoS levels (0, 1, 2)
- Topic hierarchy validation
- Retained messages
- Will messages
- Connection limits

**MinIO Object Storage**:
- Liveness and readiness endpoints
- Bucket listing
- Object upload/download
- Bucket policies
- Lifecycle rules
- All 10 required buckets present

**Redis Messaging**:
- Pub/Sub channels
- Redis Streams (event sourcing)
- Consumer groups
- Message acknowledgment
- Stream trimming

**Expected Execution Time**: 45-60 seconds

**Expected Output**:
```
=== Messaging Services Test Report ===
Timestamp: 2025-10-13T10:40:00Z

MQTT Broker Tests: PASS (8/10)
  ✓ Connectivity: OK (18ms)
  ✓ Publish: OK
  ✓ Subscribe: OK
  ⚠ Authentication: SKIPPED (anonymous mode)
  ✓ QoS 0: OK
  ✓ QoS 1: OK
  ⚠ QoS 2: SKIPPED (not critical for dev)
  ✓ Retained Messages: OK
  ✓ Will Messages: OK

MinIO Tests: PASS (10/10)
  ✓ Health Endpoints: OK
  ✓ Bucket Count: 10/10 buckets present
    - lics-videos, lics-data, lics-exports
    - lics-uploads, lics-config, lics-backups
    - lics-temp, lics-assets, lics-logs, lics-ml
  ✓ Upload Test: OK (2.3 MB/s)
  ✓ Download Test: OK (5.1 MB/s)
  ✓ Bucket Policies: OK

Redis Messaging Tests: PASS (6/6)
  ✓ Pub/Sub: OK (12ms)
  ✓ Streams: OK (3 streams operational)
  ✓ Consumer Groups: OK
  ✓ Message ACK: OK

Overall Messaging Health: 92% (24/26 tests passing)
```

---

#### Test Suite 4: System Integration Testing

**Purpose**: End-to-end system validation across all components

**Command**:
```bash
make test-system-integration
# OR
python3 tools/scripts/test-system-integration.py --format text
```

**What It Tests**:
- **Data Flow**: PostgreSQL → Redis → MQTT → MinIO
- **Event Sourcing**: Write to Postgres, publish to Redis Streams
- **Monitoring Pipeline**: Metrics collection → Prometheus → Grafana
- **Distributed Tracing**: OpenTelemetry → Jaeger v2
- **Alerting**: Prometheus rules → Alertmanager
- **Cross-Service Communication**: All services can reach each other

**Test Scenarios**:
1. Write data to PostgreSQL, verify in Redis cache
2. Publish MQTT message, verify delivery across topics
3. Upload object to MinIO, verify access and metadata
4. Generate metrics, verify Prometheus scrapes them
5. Create trace span, verify Jaeger v2 receives it
6. Trigger alert rule, verify Alertmanager processes it

**Expected Execution Time**: 2-3 minutes

**⚠️ Important Notes**:
- The test suite uses `aiomqtt` (v2.0+) for async MQTT operations
- InfluxDB tests use environment-specific bucket names (`telemetry-dev` for development)
- If tests fail with MQTT errors, ensure `aiomqtt>=2.0.0` is installed: `pip install aiomqtt`

**Expected Output**:
```
=== System Integration Test Report ===
Timestamp: 2025-10-13T10:45:00Z

Scenario 1: Database → Cache Flow
  ✓ Write to PostgreSQL: OK (25ms)
  ✓ Cache in Redis: OK (8ms)
  ✓ Read from cache: OK (3ms)
  ✓ Cache invalidation: OK (5ms)

Scenario 2: MQTT Message Delivery
  ✓ Publish message: OK
  ✓ Subscriber receives: OK (18ms latency)
  ✓ QoS confirmation: OK

Scenario 3: Object Storage Flow
  ✓ Upload to MinIO: OK (1.2 MB, 450ms)
  ✓ Generate presigned URL: OK
  ✓ Download via URL: OK (380ms)
  ✓ Delete object: OK

Scenario 4: Monitoring Pipeline
  ✓ Metrics exposed: OK (15 metrics found)
  ✓ Prometheus scrape: OK
  ✓ Query metrics: OK (response in 42ms)

Scenario 5: Distributed Tracing
  ✓ Create trace span: OK
  ✓ Jaeger v2 receives: OK (span_id found)
  ✓ Trace query: OK

Scenario 6: Alerting Pipeline
  ✓ Alert rule evaluation: OK
  ✓ Alertmanager notification: OK (test alert)

Integration Test Result: PASS (23/23 tests)
Overall System Health: 100% operational
```

---

### 2.3 Health Check Scripts

#### Unified Health Check (All Services)
```bash
python3 infrastructure/monitoring/unified-health-check.py --format text
```

**Services Checked**:
- PostgreSQL (connectivity, version, TimescaleDB)
- Redis (connectivity, memory, operations)
- Prometheus (healthy endpoint)
- Grafana (API health)
- InfluxDB (health endpoint)
- Loki (ready endpoint)
- Alertmanager (healthy endpoint)
- Jaeger v2 (API services endpoint)
- MinIO (health live endpoint)

**Output Formats**: `--format text` or `--format json`

---

#### Database-Specific Health Check
```bash
python3 infrastructure/monitoring/database/health_check.py --format text
```

**Deep Checks**:
- PostgreSQL connection pooling
- TimescaleDB hypertables count
- Redis memory usage and cache hit rate
- InfluxDB bucket configuration
- PgBouncer statistics (if operational)

---

#### Messaging-Specific Health Check
```bash
python3 infrastructure/monitoring/messaging-health-check.py --format json
```

**Deep Checks**:
- MQTT broker statistics
- Redis Streams configuration
- Redis Pub/Sub channels
- MinIO bucket policies and lifecycle rules

---

### 2.4 Performance Benchmarking

#### Database Performance Benchmarks
```bash
make test-database-benchmark
# OR
python3 tools/scripts/test-database-suite.py --test all --benchmark --format text
```

**Benchmarks**:
- PostgreSQL query performance (SELECT, INSERT, UPDATE, DELETE)
- Redis operation latency (GET, SET, DEL)
- TimescaleDB time-series insert rate
- Connection pool performance

**Target Metrics**:
- PostgreSQL query < 100ms (p95)
- Redis operations < 10ms (p95)
- TimescaleDB insert > 10,000 rows/sec

---

#### Messaging Performance Benchmarks
```bash
make test-messaging-benchmark
# OR
python3 tools/scripts/test-messaging-suite.py --test all --benchmark --format text
```

**Benchmarks**:
- MQTT publish rate (messages/sec)
- Redis Pub/Sub throughput
- Redis Streams write performance
- MinIO upload/download speed

**Target Metrics**:
- MQTT publish > 1,000 msg/sec
- Redis Pub/Sub > 10,000 msg/sec
- MinIO upload > 50 MB/sec

---

### 2.5 Continuous Monitoring

#### Continuous Health Checks (Background)
```bash
# Run health checks every 60 seconds
make health-check-continuous

# OR with custom interval
python3 infrastructure/monitoring/messaging-health-check.py --continuous --interval 120
```

Press `Ctrl+C` to stop.

---

## 3. Manual Testing Procedures

> **💡 Automated Alternative Available**: All manual tests in this section have been automated. See **Section 2.0 Automated Manual Test Suite** for faster, repeatable testing. Use `make test-phase1-full` to run all tests automatically and generate reports.
>
> Manual testing procedures below are provided for:
> - Educational purposes and understanding test methodology
> - Troubleshooting specific failures identified in automated tests
> - Verification in environments where automation tools are unavailable
> - Custom testing scenarios not covered by automation

### 3.1 Infrastructure Component Testing

#### TC-INFRA-001: Docker Container Health
**Objective**: Verify all required containers are running and healthy

**Steps**:
1. Open terminal in project root
2. Run: `docker-compose -f docker-compose.dev.yml ps`
3. Observe STATUS column for each container

**Expected Outcome**:
- ✅ All containers show "Up" or "Up (healthy)"
- ✅ Uptime > 5 minutes (after initial startup)
- ✅ No containers in "Restarting" or "Exited" state
- ✅ Health checks passing (where applicable)

**Actual Outcome**: ________________

---

#### TC-INFRA-002: Network Connectivity Between Services
**Objective**: Verify inter-service communication

**Steps**:
1. Get a shell in PostgreSQL container:
   ```bash
   docker exec -it $(docker ps -q -f name=postgres) bash
   ```

2. Test Redis connectivity:
   ```bash
   apt-get update && apt-get install -y redis-tools
   redis-cli -h redis ping
   ```
   Expected: `PONG`

3. Test MinIO connectivity:
   ```bash
   apt-get install -y curl
   curl -I http://minio:9000/minio/health/live
   ```
   Expected: `HTTP/1.1 200 OK`

4. Exit container: `exit`

**Expected Outcome**:
- ✅ PostgreSQL can reach Redis
- ✅ PostgreSQL can reach MinIO
- ✅ Services resolve by container name (DNS works)
- ✅ HTTP and TCP connections successful

**Actual Outcome**: ________________

---

### 3.2 Database Layer Testing

#### TC-DB-001: PostgreSQL Connection and CRUD Operations
**Objective**: Validate PostgreSQL database functionality

**Steps**:
1. Connect to PostgreSQL:
   ```bash
   docker exec -it $(docker ps -q -f name=postgres) psql -U lics -d lics_dev
   ```

2. Test CREATE:
   ```sql
   CREATE TABLE test_table (id SERIAL PRIMARY KEY, name VARCHAR(100));
   INSERT INTO test_table (name) VALUES ('Test Item 1');
   ```

3. Test READ:
   ```sql
   SELECT * FROM test_table;
   ```
   Expected: One row with id=1, name='Test Item 1'

4. Test UPDATE:
   ```sql
   UPDATE test_table SET name = 'Updated Item' WHERE id = 1;
   SELECT * FROM test_table;
   ```
   Expected: name changed to 'Updated Item'

5. Test DELETE:
   ```sql
   DELETE FROM test_table WHERE id = 1;
   SELECT count(*) FROM test_table;
   ```
   Expected: count = 0

6. Clean up:
   ```sql
   DROP TABLE test_table;
   \q
   ```

**Expected Outcome**:
- ✅ Connection successful
- ✅ All CRUD operations work
- ✅ Query response time < 50ms
- ✅ No errors or warnings

**Actual Outcome**: ________________

---

#### TC-DB-002: TimescaleDB Hypertables
**Objective**: Verify TimescaleDB extension and hypertable functionality

**Steps**:
1. Connect to PostgreSQL (same as TC-DB-001)

2. Check TimescaleDB extension:
   ```sql
   SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';
   ```
   Expected: timescaledb | 2.10.2 (or current version)

3. Create test hypertable:
   ```sql
   CREATE TABLE test_metrics (
       time TIMESTAMPTZ NOT NULL,
       device_id INT,
       temperature DOUBLE PRECISION
   );

   SELECT create_hypertable('test_metrics', 'time');
   ```

4. Insert time-series data:
   ```sql
   INSERT INTO test_metrics VALUES
       (NOW(), 1, 23.5),
       (NOW() - INTERVAL '1 hour', 1, 24.2),
       (NOW() - INTERVAL '2 hours', 1, 22.8);
   ```

5. Query time-series:
   ```sql
   SELECT time, temperature FROM test_metrics
   WHERE device_id = 1 ORDER BY time DESC;
   ```
   Expected: 3 rows with correct temperatures

6. Check hypertable info:
   ```sql
   SELECT * FROM timescaledb_information.hypertables
   WHERE hypertable_name = 'test_metrics';
   ```

7. Clean up:
   ```sql
   DROP TABLE test_metrics;
   \q
   ```

**Expected Outcome**:
- ✅ TimescaleDB extension installed
- ✅ Hypertable created successfully
- ✅ Time-series data inserted and queried
- ✅ Automatic partitioning working (check chunks)

**Actual Outcome**: ________________

---

#### TC-DB-003: Redis Cache Operations
**Objective**: Validate Redis basic operations and data structures

**Steps**:
1. Connect to Redis:
   ```bash
   docker exec -it $(docker ps -q -f name=redis) redis-cli
   ```

2. Test String operations:
   ```redis
   SET test:key "Hello LICS"
   GET test:key
   DEL test:key
   ```
   Expected: "Hello LICS" returned

3. Test Hash operations:
   ```redis
   HSET user:1 name "John Doe" email "john@example.com"
   HGETALL user:1
   DEL user:1
   ```
   Expected: name and email fields returned

4. Test List operations:
   ```redis
   RPUSH devices device1 device2 device3
   LRANGE devices 0 -1
   DEL devices
   ```
   Expected: All 3 devices listed

5. Test TTL:
   ```redis
   SET temp:data "expires soon" EX 10
   TTL temp:data
   ```
   Expected: Returns number ≤ 10

6. Check memory usage:
   ```redis
   INFO memory
   ```

7. Exit: `exit`

**Expected Outcome**:
- ✅ All data structure operations work
- ✅ TTL functionality working
- ✅ Memory usage reasonable (< 100MB for empty instance)
- ✅ Response time < 5ms

**Actual Outcome**: ________________

---

#### TC-DB-004: Redis Streams and Pub/Sub
**Objective**: Validate Redis advanced messaging features

**Steps**:
1. Connect to Redis CLI (same as TC-DB-003)

2. Test Redis Streams:
   ```redis
   XADD lics:streams:device_telemetry * device_id 1 temperature 23.5 timestamp 1697203200
   XLEN lics:streams:device_telemetry
   XREAD COUNT 1 STREAMS lics:streams:device_telemetry 0
   ```
   Expected: Stream created, length = 1, data readable

3. Create consumer group:
   ```redis
   XGROUP CREATE lics:streams:device_telemetry telemetry_processors $ MKSTREAM
   XREADGROUP GROUP telemetry_processors consumer1 COUNT 1 STREAMS lics:streams:device_telemetry >
   ```
   Expected: Consumer group created, message received

4. Test Pub/Sub (open TWO terminals):

   **Terminal 1 (Subscriber)**:
   ```bash
   docker exec -it $(docker ps -q -f name=redis) redis-cli
   SUBSCRIBE lics:channels:device_status
   ```

   **Terminal 2 (Publisher)**:
   ```bash
   docker exec -it $(docker ps -q -f name=redis) redis-cli
   PUBLISH lics:channels:device_status "device1:online"
   ```

   Expected in Terminal 1: Message received "device1:online"

5. Clean up:
   ```redis
   DEL lics:streams:device_telemetry
   ```

**Expected Outcome**:
- ✅ Redis Streams working (XADD, XREAD)
- ✅ Consumer groups functional
- ✅ Pub/Sub message delivery working
- ✅ All expected streams configured (3 streams)

**Actual Outcome**: ________________

---

### 3.3 Message Broker Testing

#### TC-MSG-001: MQTT Broker Connectivity
**Objective**: Verify MQTT broker accepts connections

**Steps**:
1. Install MQTT client (if not installed):
   ```bash
   # macOS
   brew install mosquitto

   # Ubuntu
   sudo apt-get install mosquitto-clients
   ```

2. Test connection:
   ```bash
   mosquitto_pub -h localhost -p 1883 -t "lics/health/test" -m "test message"
   ```

3. Check broker logs:
   ```bash
   docker logs $(docker ps -q -f name=mqtt) | tail -20
   ```
   Expected: Connection accepted, message published

**Expected Outcome**:
- ✅ Connection accepted
- ✅ No authentication errors (anonymous mode)
- ✅ Broker logs show successful publish
- ✅ No connection refused errors

**Actual Outcome**: ________________

---

#### TC-MSG-002: MQTT Publish/Subscribe
**Objective**: Verify MQTT message delivery

**Steps**:
1. Open TWO terminals

2. **Terminal 1 (Subscriber)**:
   ```bash
   mosquitto_sub -h localhost -p 1883 -t "lics/devices/+/telemetry" -v
   ```
   Expected: Waiting for messages...

3. **Terminal 2 (Publisher)**:
   ```bash
   mosquitto_pub -h localhost -p 1883 -t "lics/devices/device1/telemetry" \
     -m '{"temperature": 23.5, "humidity": 45.2}'
   ```

4. Verify in Terminal 1:
   Expected: Message appears with topic and payload

5. Test QoS levels:
   ```bash
   mosquitto_pub -h localhost -p 1883 -t "lics/test" -m "QoS 0 message" -q 0
   mosquitto_pub -h localhost -p 1883 -t "lics/test" -m "QoS 1 message" -q 1
   ```

6. Press Ctrl+C in both terminals to exit

**Expected Outcome**:
- ✅ Subscriber receives messages
- ✅ Topic wildcards work (+, #)
- ✅ QoS 0 and 1 messages delivered
- ✅ Message latency < 50ms

**Actual Outcome**: ________________

---

#### TC-MSG-003: MinIO Object Storage
**Objective**: Validate object upload, download, and bucket operations

**Steps**:
1. Access MinIO Console: http://localhost:9001
2. Login: minioadmin / minioadmin

3. Verify all 10 buckets exist:
   - lics-videos
   - lics-data
   - lics-exports
   - lics-uploads
   - lics-config
   - lics-backups
   - lics-temp
   - lics-assets
   - lics-logs
   - lics-ml

4. Test upload via CLI:
   ```bash
   # Create test file
   echo "Test content for LICS" > test-upload.txt

   # Install MinIO client (if not installed)
   # macOS: brew install minio/stable/mc
   # Ubuntu: wget https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc

   # Configure client
   docker exec $(docker ps -q -f name=minio) mc alias set local http://localhost:9000 minioadmin minioadmin

   # Upload file
   docker exec -i $(docker ps -q -f name=minio) mc cp - local/lics-temp/test-upload.txt < test-upload.txt

   # List bucket
   docker exec $(docker ps -q -f name=minio) mc ls local/lics-temp/

   # Download file
   docker exec $(docker ps -q -f name=minio) mc cp local/lics-temp/test-upload.txt /tmp/downloaded.txt

   # Verify content
   docker exec $(docker ps -q -f name=minio) cat /tmp/downloaded.txt
   ```

5. Check via Web UI:
   - Navigate to lics-temp bucket
   - Verify test-upload.txt appears
   - Click to view/download

6. Clean up:
   ```bash
   docker exec $(docker ps -q -f name=minio) mc rm local/lics-temp/test-upload.txt
   rm test-upload.txt
   ```

**Expected Outcome**:
- ✅ All 10 buckets present
- ✅ File upload successful
- ✅ File downloadable via CLI and Web UI
- ✅ File content matches original
- ✅ Bucket policies functional

**Actual Outcome**: ________________

---

### 3.4 Monitoring Stack Testing

#### TC-MON-001: Prometheus Metrics Collection
**Objective**: Verify Prometheus is scraping metrics from all exporters

**Steps**:
1. Open Prometheus UI: http://localhost:9090

2. Check targets status:
   - Click "Status" → "Targets"
   - Verify all targets are "UP":
     - lics-backend (if running)
     - postgres-exporter
     - redis-exporter
     - node-exporter

3. Test metric query:
   - Click "Graph" tab
   - Enter query: `up`
   - Click "Execute"
   - Verify results show all services with value=1

4. Test time-series query:
   - Query: `rate(node_cpu_seconds_total[5m])`
   - Verify CPU usage metrics appear

5. Check scrape intervals:
   - Query: `scrape_duration_seconds`
   - Verify scrape times < 1 second

**Expected Outcome**:
- ✅ All targets showing "UP"
- ✅ Metrics being collected
- ✅ No scrape errors
- ✅ Scrape interval = 15 seconds (default)

**Actual Outcome**: ________________

---

#### TC-MON-002: Grafana Dashboard Access
**Objective**: Verify Grafana is operational and connected to data sources

**Steps**:
1. Open Grafana: http://localhost:3001
2. Login: admin / admin (skip password change for testing)

3. Check data sources:
   - Click "Configuration" (gear icon) → "Data Sources"
   - Verify configured sources:
     - Prometheus (default)
     - InfluxDB (if operational)
     - Loki (logs)
     - Jaeger (traces)
     - PostgreSQL
     - Redis

4. Test Prometheus data source:
   - Click "Explore" (compass icon)
   - Select "Prometheus" from dropdown
   - Enter query: `up`
   - Click "Run Query"
   - Verify metrics appear

5. Check existing dashboards:
   - Click "Dashboards" (four squares icon)
   - Browse available dashboards
   - Open "System Overview" (if exists)
   - Verify panels load data

**Expected Outcome**:
- ✅ Grafana login successful
- ✅ All data sources connected
- ✅ Prometheus queries return data
- ✅ Dashboards load without errors

**Actual Outcome**: ________________

---

#### TC-MON-003: Jaeger v2 Distributed Tracing
**Objective**: Verify Jaeger v2 is receiving traces

**Steps**:
1. Open Jaeger UI: http://localhost:16686

2. Check service list:
   - Top left: Click "Service" dropdown
   - Expected: "jaeger-query" service (self-monitoring)

3. Test trace creation (requires backend running):
   ```bash
   # If backend is running, make API request
   curl http://localhost:8000/api/v1/health
   ```

4. Search for traces:
   - Select service (if backend running)
   - Click "Find Traces"
   - Verify traces appear

5. Check Jaeger v2 health:
   ```bash
   curl http://localhost:13133
   ```
   Expected: Health check response

**Expected Outcome**:
- ✅ Jaeger UI accessible
- ✅ Service list populated
- ✅ Health endpoint responding
- ✅ Traces visible (if backend active)
- ✅ No initialization errors

**Actual Outcome**: ________________

---

### 3.5 Integration Testing

#### TC-INT-001: End-to-End Data Flow
**Objective**: Validate complete data pipeline from ingestion to storage

**Test Scenario**: Simulate device telemetry flow

**Steps**:

1. **Step 1: Insert data into PostgreSQL**
   ```bash
   docker exec -it $(docker ps -q -f name=postgres) psql -U lics -d lics_dev -c \
     "INSERT INTO test_telemetry (timestamp, device_id, metric_name, metric_value) \
      VALUES (NOW(), 1, 'temperature', 23.5);"
   ```

2. **Step 2: Cache in Redis**
   ```bash
   docker exec -it $(docker ps -q -f name=redis) redis-cli SET "device:1:temperature" "23.5"
   ```

3. **Step 3: Publish to MQTT**
   ```bash
   mosquitto_pub -h localhost -p 1883 \
     -t "lics/devices/1/telemetry" \
     -m '{"device_id": 1, "temperature": 23.5, "timestamp": "2025-10-13T10:00:00Z"}'
   ```

4. **Step 4: Store in MinIO**
   ```bash
   echo '{"device_id": 1, "temperature": 23.5}' | \
     docker exec -i $(docker ps -q -f name=minio) \
     mc cp - local/lics-data/telemetry/device1-$(date +%s).json
   ```

5. **Step 5: Verify data accessibility**
   - PostgreSQL: Query test_telemetry table
   - Redis: GET device:1:temperature
   - MinIO: List lics-data/telemetry/ directory

6. **Step 6: Check monitoring**
   - Prometheus: Query custom metrics (if exposed)
   - Grafana: Verify dashboard updates

**Expected Outcome**:
- ✅ Data inserted into PostgreSQL
- ✅ Data cached in Redis
- ✅ MQTT message published
- ✅ Object stored in MinIO
- ✅ All data retrievable
- ✅ Monitoring reflects activity

**Actual Outcome**: ________________

---

## 4. Expected Outcomes

### 4.1 Service Health Targets

| Component | Target Status | Response Time | Uptime |
|-----------|--------------|---------------|--------|
| PostgreSQL | Healthy | < 50ms | 99.9% |
| TimescaleDB | Enabled | N/A | 99.9% |
| Redis | Healthy | < 10ms | 99.9% |
| MQTT Broker | Running | < 50ms | 99.5% |
| MinIO | Healthy | < 100ms | 99.9% |
| Prometheus | Healthy | < 200ms | 99.5% |
| Grafana | Healthy | < 500ms | 99.5% |
| Jaeger v2 | Healthy | < 200ms | 99.5% |
| Alertmanager | Healthy | < 200ms | 99.5% |
| **Overall** | **Healthy** | N/A | **99.5%** |

### 4.2 Test Pass Rates

| Test Suite | Target Pass Rate | Critical Failures Allowed |
|------------|-----------------|---------------------------|
| Infrastructure Validation | 100% | 0 |
| Database Tests | 95% | 2 (InfluxDB, PgBouncer deferred) |
| Messaging Tests | 90% | 2 (MQTT auth, QoS 2 not critical) |
| System Integration | 100% | 0 |
| Performance Benchmarks | 90% | Informational only |

### 4.3 Known Acceptable Failures

Based on KNOWN_ISSUES.md, the following failures are **expected and acceptable** for Phase 1:

#### Deferred to Later Phases
1. **InfluxDB Initialization Loop** - Deferred to Phase 5 (Analytics)
   - Severity: Medium
   - Workaround: Use PostgreSQL + TimescaleDB
   - Impact: Time-series analytics features unavailable

2. **PgBouncer Connection Pooling** - Deferred to Phase 6 (Performance)
   - Severity: Low
   - Workaround: Direct PostgreSQL connections
   - Impact: Performance optimization missing

3. **MQTT Authentication** - Simplified for Development
   - Severity: Low
   - Current: Anonymous connections enabled
   - Impact: Production security features missing

#### Test Configuration Issues
1. **MQTT Client Tests** - Configuration tuning needed
   - Some tests may fail due to connection parameters
   - Service is operational despite test failures

### 4.4 Performance Baselines

#### Database Performance
- **PostgreSQL**:
  - Simple SELECT: < 10ms
  - INSERT: < 20ms
  - Complex JOIN: < 100ms
  - Concurrent connections: 100+

- **Redis**:
  - GET/SET: < 1ms
  - HGETALL: < 5ms
  - Stream operations: < 10ms
  - Throughput: > 10,000 ops/sec

#### Messaging Performance
- **MQTT**:
  - Publish latency: < 50ms
  - Message throughput: > 1,000 msg/sec
  - Connection time: < 200ms

- **MinIO**:
  - Upload speed: > 50 MB/sec
  - Download speed: > 100 MB/sec
  - API latency: < 100ms

### 4.5 Resource Utilization Targets

| Resource | Target | Warning Threshold | Critical Threshold |
|----------|--------|-------------------|-------------------|
| CPU | < 30% | > 60% | > 80% |
| Memory | < 8GB | > 12GB | > 14GB |
| Disk Space | < 20GB | > 35GB | > 45GB |
| Network I/O | < 100 MB/sec | > 500 MB/sec | > 900 MB/sec |

---

## 5. Test Results Recording

### 5.1 Test Execution Log Template

```markdown
## Phase 1 Infrastructure Test Execution - [Date]

### Tester Information
- Name: ________________
- Role: ________________
- Environment: Development / Staging / Production

### System Configuration
- OS: ________________
- Docker Version: ________________
- Available RAM: ________________
- Available Disk: ________________

### Test Environment Status
- [ ] All containers running (docker-compose ps)
- [ ] No port conflicts detected
- [ ] Sufficient resources available
- [ ] Network connectivity verified

### Automated Test Results

#### Infrastructure Validation
- [ ] PASS: Docker containers healthy (TC-INFRA-001)
- [ ] PASS: Network connectivity (TC-INFRA-002)
- [ ] PASS: Port mappings correct
- [ ] PASS: Volume mounts functional
- Execution time: ________ seconds
- Issues found: ________________

#### Database Testing
- [ ] PASS: PostgreSQL connectivity (TC-DB-001)
- [ ] PASS: TimescaleDB hypertables (TC-DB-002)
- [ ] PASS: Redis cache operations (TC-DB-003)
- [ ] PASS: Redis Streams/Pub-Sub (TC-DB-004)
- [ ] SKIPPED: InfluxDB (deferred to Phase 5)
- [ ] SKIPPED: PgBouncer (deferred to Phase 6)
- Overall pass rate: ______ % (Expected: 95%)
- Issues found: ________________

#### Messaging Testing
- [ ] PASS: MQTT connectivity (TC-MSG-001)
- [ ] PASS: MQTT Pub/Sub (TC-MSG-002)
- [ ] PASS: MinIO object storage (TC-MSG-003)
- [ ] INFO: MQTT auth tests skipped (anonymous mode)
- Overall pass rate: ______ % (Expected: 90%)
- Issues found: ________________

#### Monitoring Stack
- [ ] PASS: Prometheus metrics (TC-MON-001)
- [ ] PASS: Grafana dashboards (TC-MON-002)
- [ ] PASS: Jaeger v2 tracing (TC-MON-003)
- [ ] PASS: Alertmanager operational
- Overall pass rate: ______ % (Expected: 100%)
- Issues found: ________________

#### System Integration
- [ ] PASS: End-to-end data flow (TC-INT-001)
- [ ] PASS: Cross-service communication
- [ ] PASS: Monitoring pipeline
- Overall pass rate: ______ % (Expected: 100%)
- Issues found: ________________

### Manual Testing Results
- [ ] All manual test cases executed
- [ ] Results match expected outcomes
- [ ] Any deviations documented below

### Performance Benchmarks
- PostgreSQL query time: ________ ms (target: < 100ms)
- Redis operation time: ________ ms (target: < 10ms)
- MQTT message latency: ________ ms (target: < 50ms)
- MinIO upload speed: ________ MB/s (target: > 50 MB/s)

### Bugs/Issues Discovered
1. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________
2. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________
3. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________

### Known Issues Verified
- [ ] InfluxDB restart loop present (expected, deferred)
- [ ] PgBouncer not operational (expected, deferred)
- [ ] MQTT auth tests skipped (expected, dev mode)
- [ ] All known issues match KNOWN_ISSUES.md

### Overall Assessment
- **Infrastructure Health**: ________ % (Target: 85%)
- **Test Pass Rate**: ________ % (Target: 95%)
- **Critical Failures**: ________ (Target: 0)
- **Recommendation**: PASS / FAIL / PASS WITH CONDITIONS

### Sign-off
- Tester Signature: ________________
- Date: ________________
- Approval: PASS / FAIL / CONDITIONAL PASS
- Conditions (if any): ________________

### Attachments
- [ ] Test report HTML dashboard (test-results/latest/)
- [ ] Docker container logs (if failures occurred)
- [ ] Performance benchmark results
- [ ] Screenshots of monitoring dashboards
```

---

## 6. Troubleshooting

### 6.1 Services Won't Start

#### Issue: docker-compose up fails
**Symptoms**:
- Containers fail to start
- Port binding errors
- Network creation failures

**Solutions**:
```bash
# Check for port conflicts
sudo lsof -i :5432 -i :6379 -i :1883 -i :9000

# Stop all containers and clean up
docker-compose -f docker-compose.dev.yml down
docker system prune -f

# Remove volumes (WARNING: destroys data)
docker-compose -f docker-compose.dev.yml down -v

# Restart Docker daemon
# macOS: Restart Docker Desktop
# Linux:
sudo systemctl restart docker

# Try again
make dev
```

---

#### Issue: Container stuck in "Restarting" state
**Symptoms**:
- Container shows "Restarting" in `docker ps`
- Health checks failing repeatedly

**Solutions**:
```bash
# Check container logs
docker logs <container_name> --tail 100

# Check specific service (example: postgres)
docker logs $(docker ps -q -f name=postgres) --tail 50

# Remove container and recreate
docker-compose -f docker-compose.dev.yml rm -f <service_name>
docker-compose -f docker-compose.dev.yml up -d <service_name>
```

---

### 6.2 Database Connection Issues

#### Issue: PostgreSQL connection refused
**Symptoms**:
- "Connection refused" errors
- Cannot connect from host machine

**Solutions**:
```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs $(docker ps -q -f name=postgres)

# Verify configuration
docker exec $(docker ps -q -f name=postgres) cat /var/lib/postgresql/data/postgresql.conf | grep listen_addresses

# Should show: listen_addresses = '*'

# Restart PostgreSQL
docker-compose -f docker-compose.dev.yml restart postgres-dev

# Test connection
docker exec $(docker ps -q -f name=postgres) psql -U lics -d lics_dev -c "SELECT 1"
```

---

#### Issue: Redis connection timeout
**Symptoms**:
- Redis commands hang
- Connection timeout errors

**Solutions**:
```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connectivity
docker exec $(docker ps -q -f name=redis) redis-cli ping
# Expected: PONG

# Check Redis memory
docker exec $(docker ps -q -f name=redis) redis-cli INFO memory

# If memory full, clear cache (DANGEROUS in production)
docker exec $(docker ps -q -f name=redis) redis-cli FLUSHALL

# Restart Redis
docker-compose -f docker-compose.dev.yml restart redis-dev
```

---

### 6.3 MQTT Broker Issues

#### Issue: MQTT connection refused
**Symptoms**:
- Cannot connect to MQTT broker
- mosquitto_pub/sub commands fail

**Solutions**:
```bash
# Check MQTT broker is running
docker ps | grep mqtt

# Check MQTT logs
docker logs $(docker ps -q -f name=mqtt) | tail -50

# Verify port mapping
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep mqtt
# Should show: 1883/tcp, 9002/tcp

# Test connection with verbose output
mosquitto_pub -h localhost -p 1883 -t "test" -m "test" -d

# Check configuration
docker exec $(docker ps -q -f name=mqtt) cat /mosquitto/config/mosquitto.conf

# Restart MQTT
docker-compose -f docker-compose.dev.yml restart mqtt
```

---

### 6.4 MinIO Storage Issues

#### Issue: MinIO console not accessible
**Symptoms**:
- Cannot access http://localhost:9001
- Connection refused or timeout

**Solutions**:
```bash
# Check MinIO is running
docker ps | grep minio

# Check MinIO logs
docker logs $(docker ps -q -f name=minio) | tail -50

# Verify ports
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep minio
# Should show: 9000/tcp, 9001/tcp

# Test health endpoint
curl http://localhost:9000/minio/health/live

# Restart MinIO
docker-compose -f docker-compose.dev.yml restart minio
```

---

#### Issue: Missing MinIO buckets
**Symptoms**:
- Buckets not present in MinIO console
- Upload tests fail with "bucket not found"

**Solutions**:
```bash
# List existing buckets
docker exec $(docker ps -q -f name=minio) mc ls local

# Create missing buckets
docker exec $(docker ps -q -f name=minio) mc mb local/lics-videos
docker exec $(docker ps -q -f name=minio) mc mb local/lics-data
docker exec $(docker ps -q -f name=minio) mc mb local/lics-exports
docker exec $(docker ps -q -f name=minio) mc mb local/lics-uploads
docker exec $(docker ps -q -f name=minio) mc mb local/lics-config
docker exec $(docker ps -q -f name=minio) mc mb local/lics-backups
docker exec $(docker ps -q -f name=minio) mc mb local/lics-temp
docker exec $(docker ps -q -f name=minio) mc mb local/lics-assets
docker exec $(docker ps -q -f name=minio) mc mb local/lics-logs
docker exec $(docker ps -q -f name=minio) mc mb local/lics-ml

# Verify all buckets created
docker exec $(docker ps -q -f name=minio) mc ls local | wc -l
# Should show: 10
```

---

### 6.5 Monitoring Stack Issues

#### Issue: Prometheus not scraping targets
**Symptoms**:
- Targets show as "DOWN" in Prometheus
- No metrics available

**Solutions**:
```bash
# Check Prometheus is running
docker ps | grep prometheus

# Check Prometheus logs
docker logs $(docker ps -q -f name=prometheus) | tail -50

# Verify targets configuration
docker exec $(docker ps -q -f name=prometheus) cat /etc/prometheus/prometheus.yml

# Check exporters are running
docker ps | grep exporter

# Restart Prometheus
docker-compose -f docker-compose.dev.yml restart prometheus

# Force immediate scrape (visit in browser)
curl -X POST http://localhost:9090/-/reload
```

---

#### Issue: Grafana datasources not connected
**Symptoms**:
- "Data source not found" errors
- Dashboards show no data

**Solutions**:
```bash
# Check Grafana logs
docker logs $(docker ps -q -f name=grafana) | tail -50

# Verify Grafana is running
curl http://localhost:3001/api/health

# Check datasource configuration
docker exec $(docker ps -q -f name=grafana) ls /etc/grafana/provisioning/datasources/

# Restart Grafana
docker-compose -f docker-compose.dev.yml restart grafana

# Re-provision datasources
docker exec $(docker ps -q -f name=grafana) grafana-cli admin reset-admin-password admin
```

---

### 6.6 Test Script Failures

#### Issue: MQTT library errors (message_retry_set)
**Symptoms**:
- Error: `'Client' object has no attribute 'message_retry_set'`
- MQTT connectivity tests failing
- ImportError for `asyncio_mqtt` or `aiomqtt`

**Solutions**:
```bash
# The asyncio-mqtt library has been deprecated and replaced with aiomqtt
# Install the new library
pip3 install aiomqtt>=2.0.0

# If you have the old library, remove it first
pip3 uninstall asyncio-mqtt
pip3 install aiomqtt

# Verify installation
python3 -c "import aiomqtt; print(f'aiomqtt version: {aiomqtt.__version__}')"
```

**Root Cause**: The `asyncio-mqtt` library was renamed to `aiomqtt` and released as v2.0.0. The old library is no longer maintained and has API compatibility issues. All test scripts have been updated to use the new `aiomqtt` library.

---

#### Issue: InfluxDB bucket not found
**Symptoms**:
- Error: `bucket "telemetry" not found`
- InfluxDB integration tests failing
- HTTP 404 errors from InfluxDB

**Solutions**:
```bash
# The InfluxDB initialization script creates all required buckets automatically
# If buckets are missing, re-run the InfluxDB setup:

# Method 1: Restart InfluxDB services
docker-compose -f docker-compose.dev.yml restart influxdb-dev influxdb-setup

# Method 2: Manually create the missing bucket
docker exec $(docker ps -q -f name=influxdb) influx bucket create \
  --name telemetry \
  --retention 7d \
  --description "Telemetry data (legacy/test compatibility)"

# Verify buckets exist
docker exec $(docker ps -q -f name=influxdb) influx bucket list
```

**Root Cause**: Test scripts were using hardcoded bucket names that didn't match the environment-specific configuration. This has been fixed to use `telemetry-dev` for development and `telemetry` for production. The init script now creates both buckets for backward compatibility.

---

#### Issue: Python dependencies missing
**Symptoms**:
- ImportError when running test scripts
- ModuleNotFoundError

**Solutions**:
```bash
# Install required dependencies
pip3 install PyYAML docker requests asyncpg redis paho-mqtt \
  influxdb-client psutil numpy minio aiomqtt aiohttp

# Or install from requirements file (if exists)
pip3 install -r infrastructure/monitoring/requirements.txt

# Note: aiomqtt (v2.0+) has replaced the deprecated asyncio-mqtt library
# If you see errors about 'asyncio_mqtt', ensure you have aiomqtt installed
```

---

#### Issue: Test script timeout
**Symptoms**:
- Tests hang indefinitely
- Timeout errors

**Solutions**:
```bash
# Check all services are responsive
make health-check

# Increase timeout in test scripts (if editable)
# Look for timeout parameters in scripts

# Run tests with more verbose output
python3 tools/scripts/test-database-suite.py --test all --format text --verbose

# Run tests individually to isolate hanging test
python3 infrastructure/monitoring/database/health_check.py --format text
```

---

### 6.7 Performance Issues

#### Issue: High CPU usage
**Symptoms**:
- System sluggish
- Docker containers using excessive CPU

**Solutions**:
```bash
# Identify high CPU containers
docker stats --no-stream

# Check specific container resource usage
docker stats $(docker ps -q -f name=postgres) --no-stream

# Set CPU limits (edit docker-compose.dev.yml)
# Add under service definition:
#   deploy:
#     resources:
#       limits:
#         cpus: '2'

# Restart with new limits
docker-compose -f docker-compose.dev.yml up -d
```

---

#### Issue: High memory usage
**Symptoms**:
- System running out of memory
- Container OOM kills

**Solutions**:
```bash
# Check memory usage by container
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Reduce PostgreSQL shared_buffers (if needed)
# Edit infrastructure/database/postgresql.conf
# shared_buffers = 256MB  # Reduce from default

# Reduce Redis memory limit
docker exec $(docker ps -q -f name=redis) redis-cli CONFIG SET maxmemory 512mb

# Restart services
docker-compose -f docker-compose.dev.yml restart
```

---

### 6.8 Docker Issues

#### Issue: "No space left on device"
**Symptoms**:
- Docker commands fail
- Cannot create containers or volumes

**Solutions**:
```bash
# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a --volumes -f

# Check host disk space
df -h

# Free up space manually
docker volume ls -q | xargs docker volume rm  # DANGEROUS: removes all volumes
docker image prune -a -f  # Removes unused images
```

---

#### Issue: Network issues between containers
**Symptoms**:
- Containers cannot reach each other
- DNS resolution fails

**Solutions**:
```bash
# Check networks
docker network ls

# Inspect default network
docker network inspect primates-lics_default

# Recreate network
docker-compose -f docker-compose.dev.yml down
docker network prune -f
docker-compose -f docker-compose.dev.yml up -d

# Test inter-container connectivity
docker exec $(docker ps -q -f name=postgres) ping -c 3 redis
```

---

## 7. Appendices

### 7.1 Quick Reference Commands

#### Service Management
```bash
# Start all services
make dev

# Start detached (background)
make dev-detached

# Stop all services
make dev-stop

# Stop and remove volumes (clean slate)
make dev-clean

# Restart specific service
docker-compose -f docker-compose.dev.yml restart <service-name>

# View logs (all services)
docker-compose -f docker-compose.dev.yml logs -f

# View logs (specific service)
docker-compose -f docker-compose.dev.yml logs -f postgres-dev
```

#### Health Checks
```bash
# Quick validation
make validate-quick

# Full validation
make validate-all

# Component-specific
make test-infrastructure
make test-database
make test-messaging
make health-check
```

#### Container Management
```bash
# List all containers
docker ps -a

# Get shell in container
docker exec -it <container-name> bash

# View container logs
docker logs <container-name> --tail 100

# Inspect container
docker inspect <container-name>

# Container resource usage
docker stats --no-stream
```

### 7.2 Service Endpoints Reference

| Service | Internal URL | External URL | Default Credentials |
|---------|-------------|--------------|---------------------|
| PostgreSQL | postgres-dev:5432 | localhost:5433 | lics / lics123 |
| Redis | redis-dev:6379 | localhost:6380 | (none) |
| MQTT | mqtt:1883 | localhost:1884 | (anonymous) |
| MinIO | minio:9000 | localhost:9011 (console: 9012) | minioadmin / minioadmin |
| Prometheus | prometheus:9090 | localhost:9090 | (none) |
| Grafana | grafana:3000 | localhost:3001 | admin / admin |
| Jaeger | jaeger:16686 | localhost:16686 | (none) |
| PgAdmin | pgadmin:80 | localhost:5050 | admin@lics.dev / admin123 |
| Redis Commander | redis-commander:8081 | localhost:8081 | (none) |
| MailHog | mailhog:8025 | localhost:8025 | (none) |

### 7.3 Test Report Locations

```bash
# Latest test results
ls -la test-results/$(ls test-results/ | tail -1)/

# HTML dashboard
open test-results/$(ls test-results/ | tail -1)/test_report_*.html

# JSON results
cat test-results/$(ls test-results/ | tail -1)/test_results_*.json | jq .

# Logs directory
ls -la logs/
```

### 7.4 Configuration File Locations

```
infrastructure/
├── database/
│   ├── postgresql.conf
│   ├── postgresql-dev.conf
│   └── migrations/env.py
├── mqtt/
│   ├── mosquitto.conf
│   ├── mosquitto-dev.conf
│   └── mosquitto-simple.conf
├── monitoring/
│   ├── prometheus/prometheus.yml
│   ├── grafana/grafana.ini
│   ├── jaeger/jaeger-v2-config.yml
│   └── alertmanager/alertmanager.yml
└── minio/
    └── bucket-init.sh

docker-compose.dev.yml  # Main development configuration
.env.example           # Environment variables template
Makefile              # All make commands
```

### 7.5 Useful Docker Commands

```bash
# View all container IDs
docker ps -q

# Stop all containers
docker stop $(docker ps -q)

# Remove all containers
docker rm $(docker ps -aq)

# Remove all volumes
docker volume rm $(docker volume ls -q)

# Remove all networks
docker network prune -f

# View container environment variables
docker exec <container-name> env

# Copy files from container
docker cp <container-name>:/path/to/file ./local/path

# Execute command in container
docker exec <container-name> <command>
```

### 7.6 PostgreSQL Quick Reference

```bash
# Connect to PostgreSQL
docker exec -it $(docker ps -q -f name=postgres) psql -U lics -d lics_dev

# Useful psql commands
\l          # List databases
\dt         # List tables
\d+ table   # Describe table
\du         # List users
\dx         # List extensions
\q          # Quit

# Common queries
SELECT version();
SELECT * FROM pg_stat_activity;
SELECT pg_size_pretty(pg_database_size('lics_dev'));
```

### 7.7 Redis Quick Reference

```bash
# Connect to Redis
docker exec -it $(docker ps -q -f name=redis) redis-cli

# Useful commands
INFO                    # Server information
DBSIZE                 # Number of keys
KEYS *                 # List all keys (dangerous in prod)
FLUSHALL               # Clear all data (dangerous)
CONFIG GET *           # View configuration
CLIENT LIST            # List connected clients
MONITOR                # Real-time command monitoring
```

### 7.8 Known Issues Reference

See `KNOWN_ISSUES.md` for comprehensive issue tracking.

**Expected Failures (Acceptable)**:
1. InfluxDB tests - Deferred to Phase 5
2. PgBouncer tests - Deferred to Phase 6
3. MQTT authentication tests - Simplified for development
4. Some performance benchmarks - Baseline establishment

**Recently Fixed Issues** (2025-10-14):
1. ✅ MQTT library compatibility - Migrated from deprecated `asyncio-mqtt` to `aiomqtt>=2.0.0`
2. ✅ InfluxDB bucket configuration - Fixed hardcoded bucket names, now uses environment-specific config
3. ✅ Integration test failures - All MQTT and InfluxDB integration tests now passing

**Critical Issues (Must Fix)**:
- None for Phase 1 completion

### 7.9 Next Steps After Phase 1

Once Phase 1 testing is complete and passes:

1. **Proceed to Phase 2 Week 3**: Backend Core Development
   - FastAPI application foundation
   - Authentication and authorization
   - Core domain models

2. **Address High-Priority Issues**:
   - Review KNOWN_ISSUES.md "High Priority" section
   - Fix blocking issues before Phase 2

3. **Establish Baselines**:
   - Save test reports for comparison
   - Document performance benchmarks
   - Create monitoring dashboards

4. **Team Handoff**:
   - Share test results with team
   - Review any issues discovered
   - Plan remediation for non-critical issues

---

## Document Metadata

**Document Version**: 1.1
**Created**: 2025-10-13
**Last Updated**: 2025-10-14
**Next Review**: After Phase 2 Week 4 completion
**Changelog**:
- v1.1 (2025-10-14): Updated MQTT library from asyncio-mqtt to aiomqtt>=2.0.0, fixed InfluxDB bucket configuration issues, added troubleshooting for integration test failures
- v1.0 (2025-10-13): Initial release
**Maintained By**: Development Team
**Related Documents**:
- Plan.md (Phase 1 implementation details)
- Documentation.md (Architecture reference)
- KNOWN_ISSUES.md (Issue tracking)
- PHASE3_WEEK5_TESTING_GUIDE.md (Application testing guide)

---

*This document provides comprehensive testing procedures for Phase 1 - Foundation Setup. All tests should be executed in a Docker containerized environment as specified in the Setup Instructions.*

**Phase 1 Success Criteria**: 85% infrastructure operational, all critical services healthy, comprehensive testing framework validated.

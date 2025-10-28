# LICS Architecture Refactoring Plan
## Alignment with Updated Documentation.md

**Version**: 1.0
**Created**: 2025-10-24
**Status**: Planning
**Target Completion**: 8 weeks

---

## Executive Summary

This document outlines a comprehensive refactoring plan to align the LICS codebase with the updated Documentation.md architecture specifications. The plan addresses critical gaps in API Gateway implementation, microservices patterns, performance optimization, deployment strategies, and observability infrastructure.

### Current State Analysis

**Completed Implementation (Phase 2 - Week 4)**:
- ✅ FastAPI backend with async/await patterns
- ✅ JWT authentication and basic RBAC
- ✅ WebSocket real-time features
- ✅ Celery background tasks
- ✅ PostgreSQL with TimescaleDB
- ✅ Redis caching and pub/sub
- ✅ Basic monitoring (Prometheus, Grafana, Jaeger v2)
- ✅ Docker-based development environment

**Critical Gaps Identified**:
- ❌ API Gateway (Kong/Traefik) - mentioned in docs but not implemented
- ❌ Circuit breakers and service resilience patterns
- ❌ Advanced database indexing (GIN, partial indexes, composites)
- ❌ SLI/SLO metrics and alerting
- ❌ Kubernetes manifests (directory exists but empty)
- ❌ Terraform infrastructure (directory exists but empty)
- ❌ Blue-green deployment pipeline
- ❌ Service dependency health matrix
- ❌ Performance testing framework
- ❌ Standardized error response format
- ❌ Auto-scaling configuration

### Strategic Goals

1. **Reliability**: Implement circuit breakers and graceful degradation
2. **Performance**: Achieve <200ms p95 API latency
3. **Observability**: Full SLI/SLO tracking with error budgets
4. **Scalability**: Auto-scaling and capacity planning
5. **Deployment**: Zero-downtime blue-green deployments
6. **Security**: Enhanced RBAC and audit logging

---

## Phase 1: API Gateway & Service Resilience (Week 1-2)

### Priority: CRITICAL
### Duration: 2 weeks
### Prerequisites: Current Phase 2 implementation complete

### 1.1 Kong API Gateway Implementation

#### Objectives
- Centralize API routing and management
- Implement rate limiting at gateway level
- Add request/response transformation
- Enable API versioning and deprecation

#### Tasks

**Infrastructure Setup**
```yaml
# File: infrastructure/kong/docker-compose.kong.yml
# Create Kong service for development environment
```

- [ ] **Task 1.1.1**: Create Kong directory structure
  ```bash
  mkdir -p infrastructure/kong/{config,plugins,scripts}
  ```
  - Files: `kong-dev.yml`, `kong-prod.yml`, `kong.conf`
  - Estimated: 4 hours

- [ ] **Task 1.1.2**: Add Kong to docker-compose.dev.yml
  ```yaml
  kong-dev:
    image: kong:3.4-alpine
    ports:
      - "8080:8000"  # Proxy
      - "8443:8443"  # Proxy SSL
      - "8001:8001"  # Admin API
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: postgres-dev
      KONG_PG_DATABASE: kong
  ```
  - Estimated: 4 hours

- [ ] **Task 1.1.3**: Configure Kong declarative configuration
  ```yaml
  # infrastructure/kong/kong-dev.yml
  _format_version: "3.0"
  services:
    - name: lics-backend
      url: http://backend-dev:8000
      routes:
        - name: api-v1
          paths: [/api/v1]
          strip_path: false
      plugins:
        - name: rate-limiting
          config:
            minute: 100
            hour: 1000
            policy: redis
        - name: jwt
        - name: cors
        - name: prometheus
  ```
  - Estimated: 8 hours

- [ ] **Task 1.1.4**: Implement Kong Admin API initialization script
  - File: `infrastructure/kong/scripts/init-kong.sh`
  - Auto-configure services, routes, plugins
  - Estimated: 6 hours

- [ ] **Task 1.1.5**: Update frontend environment variables
  ```bash
  # Change from direct backend access
  NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
  # To Kong gateway
  NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1
  ```
  - Estimated: 2 hours

- [ ] **Task 1.1.6**: Create Kong health check endpoints
  - Add to backend health checks
  - Monitor Kong proxy status
  - Estimated: 4 hours

**Validation**
- [ ] All API requests route through Kong
- [ ] Rate limiting works (test with 100+ req/min)
- [ ] JWT validation at gateway level
- [ ] Prometheus metrics from Kong

**Documentation**
- [ ] Update SETUP.md with Kong configuration
- [ ] Document Kong admin API usage
- [ ] Create troubleshooting guide

### 1.2 Circuit Breaker Implementation

#### Objectives
- Prevent cascading failures
- Implement graceful degradation
- Provide fallback mechanisms
- Monitor service health states

#### Tasks

- [ ] **Task 1.2.1**: Install dependencies
  ```bash
  # services/backend/requirements.txt
  pybreaker==1.0.1
  ```
  - Estimated: 1 hour

- [ ] **Task 1.2.2**: Create circuit breaker core module
  ```python
  # File: services/backend/app/core/circuit_breaker.py
  from pybreaker import CircuitBreaker

  class ServiceCircuitBreaker:
      def __init__(self, name, fail_max=5, timeout=60):
          self.breaker = CircuitBreaker(
              fail_max=fail_max,
              timeout_duration=timeout,
              name=name
          )
  ```
  - Estimated: 4 hours

- [ ] **Task 1.2.3**: Implement circuit breakers for each service
  - PostgreSQL breaker
  - Redis breaker
  - MQTT breaker
  - InfluxDB breaker
  - MinIO breaker
  - Estimated: 8 hours

- [ ] **Task 1.2.4**: Create fallback strategies
  ```python
  # Database fallback: use cached data
  @db_breaker
  async def get_devices(session):
      try:
          return await session.execute(query)
      except CircuitBreakerError:
          return get_cached_devices()
  ```
  - Estimated: 12 hours

- [ ] **Task 1.2.5**: Add circuit breaker state monitoring
  - Expose circuit breaker states via API
  - Add Prometheus metrics
  - Create Grafana dashboard
  - Estimated: 6 hours

- [ ] **Task 1.2.6**: Update health check endpoints
  ```python
  # GET /api/v1/health/circuit-breakers
  {
    "postgresql": {"state": "closed", "failure_count": 0},
    "redis": {"state": "open", "failure_count": 5},
    "mqtt": {"state": "half_open", "failure_count": 3}
  }
  ```
  - Estimated: 4 hours

**Configuration**
```python
# services/backend/app/core/config.py
CIRCUIT_BREAKER_FAIL_MAX: int = 5
CIRCUIT_BREAKER_TIMEOUT: int = 60
CIRCUIT_BREAKER_EXPECTED_EXCEPTION: str = "Exception"
```

**Validation**
- [ ] Circuit opens after 5 consecutive failures
- [ ] Automatic recovery after timeout
- [ ] Fallback mechanisms work
- [ ] Metrics visible in Grafana

**Documentation**
- [ ] Document circuit breaker patterns
- [ ] Create runbook for circuit breaker incidents
- [ ] Add architectural decision record (ADR)

### 1.3 Service Dependency Matrix Implementation

#### Objectives
- Track service dependencies
- Monitor dependency health
- Implement recovery strategies per dependency

#### Tasks

- [ ] **Task 1.3.1**: Create dependency registry
  ```python
  # File: services/backend/app/core/dependencies_registry.py
  SERVICE_DEPENDENCY_MATRIX = {
      "api_gateway": {
          "dependencies": [],
          "failure_impact": "Total system outage",
          "recovery_strategy": "Multi-instance HA"
      },
      "auth_service": {
          "dependencies": ["postgresql", "redis"],
          "failure_impact": "No new sessions",
          "recovery_strategy": "Cache valid tokens"
      },
      # ... from Documentation.md Section 2.4
  }
  ```
  - Estimated: 4 hours

- [ ] **Task 1.3.2**: Implement dependency health checker
  - Check each dependency status
  - Calculate service availability
  - Report impact cascades
  - Estimated: 6 hours

- [ ] **Task 1.3.3**: Create dependency visualization endpoint
  ```python
  # GET /api/v1/health/dependencies
  # Returns dependency graph with health states
  ```
  - Estimated: 4 hours

- [ ] **Task 1.3.4**: Add Grafana dependency dashboard
  - Visualize service dependency tree
  - Show health propagation
  - Estimated: 4 hours

**Validation**
- [ ] Dependency health accurately reflects service states
- [ ] Dashboard shows real-time dependency status
- [ ] Failure impact correctly identified

### Phase 1 Deliverables

**Code Artifacts**
- ✅ Kong API Gateway operational
- ✅ Circuit breakers for all external services
- ✅ Service dependency matrix implemented
- ✅ Fallback mechanisms tested

**Infrastructure**
- ✅ Kong service in docker-compose.dev.yml
- ✅ Kong configuration files
- ✅ Circuit breaker monitoring

**Documentation**
- ✅ Kong setup guide
- ✅ Circuit breaker patterns documentation
- ✅ Service dependency matrix documentation
- ✅ Runbooks created

**Metrics**
- ✅ Kong request metrics in Prometheus
- ✅ Circuit breaker state metrics
- ✅ Dependency health metrics

---

## Phase 2: Database Optimization & Performance (Week 3-4)

### Priority: HIGH
### Duration: 2 weeks
### Prerequisites: Phase 1 complete

### 2.1 Advanced Database Indexing Strategy

#### Objectives
- Implement indexing strategy from Documentation.md Section 6.5
- Optimize query performance
- Reduce database load

#### Tasks

- [ ] **Task 2.1.1**: Create indexing migration
  ```python
  # File: infrastructure/database/migrations/versions/XXXX_advanced_indexes.py
  """Advanced indexing strategy

  Implements:
  - Full-text search indexes (GIN)
  - Composite indexes for common queries
  - Partial indexes for filtered queries
  """
  ```
  - Estimated: 4 hours

- [ ] **Task 2.1.2**: Implement full-text search indexes
  ```sql
  -- Experiments full-text search
  CREATE INDEX idx_experiments_search
  ON experiments USING gin(
    to_tsvector('english', name || ' ' || description)
  );

  -- Tasks full-text search
  CREATE INDEX idx_tasks_search
  ON tasks USING gin(
    to_tsvector('english', name || ' ' || description)
  );
  ```
  - Estimated: 4 hours

- [ ] **Task 2.1.3**: Create composite indexes
  ```sql
  -- Status + date queries (most common pattern)
  CREATE INDEX idx_experiments_status_date
  ON experiments(status, created_at DESC);

  CREATE INDEX idx_sessions_subject_date
  ON sessions(subject_id, start_time DESC);

  CREATE INDEX idx_trials_session_number
  ON trials(session_id, trial_number);
  ```
  - Estimated: 4 hours

- [ ] **Task 2.1.4**: Implement partial indexes
  ```sql
  -- Active devices only
  CREATE INDEX idx_devices_active
  ON devices(organization_id, last_seen)
  WHERE status = 'online';

  -- Running experiments only
  CREATE INDEX idx_experiments_running
  ON experiments(organization_id, updated_at)
  WHERE status = 'running';
  ```
  - Estimated: 4 hours

- [ ] **Task 2.1.5**: Add GIN indexes for JSONB columns
  ```sql
  -- Hardware configuration search
  CREATE INDEX idx_devices_hardware_config
  ON devices USING gin(hardware_config);

  -- Task parameters search
  CREATE INDEX idx_tasks_parameters
  ON tasks USING gin(parameters);
  ```
  - Estimated: 4 hours

- [ ] **Task 2.1.6**: Benchmark query performance
  - Before/after measurements
  - Document improvements
  - Estimated: 6 hours

**Validation**
- [ ] Query plans show index usage
- [ ] p95 query latency < 50ms
- [ ] Index maintenance overhead acceptable

### 2.2 TimescaleDB Hypertable Configuration

#### Objectives
- Convert telemetry tables to hypertables
- Implement automatic partitioning
- Configure data retention policies
- Set up continuous aggregates

#### Tasks

- [ ] **Task 2.2.1**: Create hypertable migration
  ```sql
  -- Convert telemetry table to hypertable
  SELECT create_hypertable(
    'telemetry',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
  );
  ```
  - Estimated: 4 hours

- [ ] **Task 2.2.2**: Configure compression policies
  ```sql
  -- Compress data older than 7 days
  ALTER TABLE telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'time DESC'
  );

  SELECT add_compression_policy('telemetry', INTERVAL '7 days');
  ```
  - Estimated: 4 hours

- [ ] **Task 2.2.3**: Implement data retention policies
  ```sql
  -- Drop raw data after 30 days
  SELECT add_retention_policy('telemetry', INTERVAL '30 days');

  -- Keep aggregates for 1 year
  SELECT add_retention_policy('telemetry_hourly', INTERVAL '1 year');
  ```
  - Estimated: 4 hours

- [ ] **Task 2.2.4**: Create continuous aggregates
  ```sql
  -- 1-minute aggregates for real-time dashboards
  CREATE MATERIALIZED VIEW telemetry_1min
  WITH (timescaledb.continuous) AS
  SELECT
    time_bucket('1 minute', time) AS bucket,
    device_id,
    metric,
    avg(value) as avg_value,
    max(value) as max_value,
    min(value) as min_value
  FROM telemetry
  GROUP BY bucket, device_id, metric;

  SELECT add_continuous_aggregate_policy('telemetry_1min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute'
  );
  ```
  - Estimated: 8 hours

- [ ] **Task 2.2.5**: Update application queries
  - Use continuous aggregates for dashboards
  - Optimize time-range queries
  - Estimated: 8 hours

**Validation**
- [ ] Hypertable creation successful
- [ ] Compression working (verify compression ratio)
- [ ] Retention policies deleting old data
- [ ] Continuous aggregates refreshing

### 2.3 Connection Pooling Optimization

#### Objectives
- Optimize PgBouncer configuration
- Implement connection pool monitoring
- Tune pool sizes per workload

#### Tasks

- [ ] **Task 2.3.1**: Update PgBouncer configuration
  ```ini
  # infrastructure/pgbouncer/pgbouncer-dev.ini
  [databases]
  lics_dev = host=postgres-dev port=5432 dbname=lics_dev

  [pgbouncer]
  pool_mode = transaction
  max_client_conn = 100
  default_pool_size = 20
  min_pool_size = 5
  reserve_pool_size = 5
  reserve_pool_timeout = 3
  max_db_connections = 50
  ```
  - Estimated: 4 hours

- [ ] **Task 2.3.2**: Add connection pool metrics
  - Monitor pool exhaustion
  - Track connection wait times
  - Alert on pool saturation
  - Estimated: 4 hours

- [ ] **Task 2.3.3**: Implement connection retry logic
  ```python
  # app/core/database.py
  async def get_connection_with_retry(max_retries=3):
      for attempt in range(max_retries):
          try:
              return await pool.acquire()
          except PoolExhaustedError:
              if attempt == max_retries - 1:
                  raise
              await asyncio.sleep(0.1 * (2 ** attempt))
  ```
  - Estimated: 4 hours

**Validation**
- [ ] No connection pool exhaustion under load
- [ ] Connection acquisition < 10ms p95
- [ ] Proper connection recycling

### Phase 2 Deliverables

**Database**
- ✅ Advanced indexes deployed
- ✅ TimescaleDB hypertables configured
- ✅ Connection pooling optimized
- ✅ Query performance improved

**Migrations**
- ✅ Index creation migration
- ✅ Hypertable conversion migration
- ✅ Continuous aggregates migration

**Monitoring**
- ✅ Query performance metrics
- ✅ Index usage statistics
- ✅ Connection pool metrics

**Documentation**
- ✅ Database optimization guide
- ✅ TimescaleDB usage patterns
- ✅ Query optimization guidelines

---

## Phase 3: SLI/SLO & Enhanced Monitoring (Week 5-6)

### Priority: HIGH
### Duration: 2 weeks
### Prerequisites: Phases 1-2 complete

### 3.1 SLI (Service Level Indicator) Implementation

#### Objectives
- Implement SLI metrics from Documentation.md Section 13.1
- Track availability, latency, error rate, throughput
- Create baseline measurements

#### Tasks

- [ ] **Task 3.1.1**: Implement SLI metrics collection
  ```python
  # File: services/backend/app/core/sli_metrics.py
  from prometheus_client import Histogram, Counter, Gauge

  # Availability SLI
  http_requests_total = Counter(
      'http_requests_total',
      'Total HTTP requests',
      ['method', 'endpoint', 'status']
  )

  # Latency SLI
  http_request_duration_seconds = Histogram(
      'http_request_duration_seconds',
      'HTTP request latency',
      ['method', 'endpoint'],
      buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
  )

  # Error Rate SLI
  http_requests_errors_total = Counter(
      'http_requests_errors_total',
      'Total HTTP errors',
      ['method', 'endpoint', 'error_type']
  )

  # Throughput SLI
  http_requests_per_second = Gauge(
      'http_requests_per_second',
      'HTTP requests per second',
      ['endpoint']
  )
  ```
  - Estimated: 6 hours

- [ ] **Task 3.1.2**: Add SLI middleware
  ```python
  # File: services/backend/app/middleware/sli_middleware.py
  @app.middleware("http")
  async def sli_middleware(request: Request, call_next):
      start_time = time.time()

      response = await call_next(request)

      duration = time.time() - start_time

      # Record SLI metrics
      http_request_duration_seconds.labels(
          method=request.method,
          endpoint=request.url.path
      ).observe(duration)

      http_requests_total.labels(
          method=request.method,
          endpoint=request.url.path,
          status=response.status_code
      ).inc()

      return response
  ```
  - Estimated: 4 hours

- [ ] **Task 3.1.3**: Configure Prometheus scraping
  ```yaml
  # infrastructure/monitoring/prometheus-dev.yml
  scrape_configs:
    - job_name: 'lics-backend-sli'
      scrape_interval: 10s
      metrics_path: /metrics
      static_configs:
        - targets: ['backend-dev:8000']
  ```
  - Estimated: 2 hours

**Validation**
- [ ] All SLI metrics visible in Prometheus
- [ ] Metrics accurately reflect system behavior
- [ ] No performance impact from metrics collection

### 3.2 SLO (Service Level Objective) Definition & Alerting

#### Objectives
- Define SLOs per service (from Documentation.md Section 13.1)
- Implement error budget tracking
- Create SLO violation alerts

#### Tasks

- [ ] **Task 3.2.1**: Define SLO targets
  ```python
  # File: infrastructure/monitoring/slo-definitions.yml
  services:
    api_gateway:
      availability: 0.999  # 99.9%
      latency_p95: 50      # 50ms
      error_rate: 0.001    # 0.1%

    core_backend:
      availability: 0.995  # 99.5%
      latency_p95: 200     # 200ms
      error_rate: 0.005    # 0.5%

    websocket:
      availability: 0.990  # 99.0%
      latency_p95: 100     # 100ms
      error_rate: 0.010    # 1.0%
  ```
  - Estimated: 4 hours

- [ ] **Task 3.2.2**: Create SLO alert rules
  ```yaml
  # File: infrastructure/monitoring/prometheus/rules/slo-alerts.yml
  groups:
    - name: slo_violations
      interval: 30s
      rules:
        # API Gateway Availability SLO
        - alert: APIGatewayAvailabilitySLOViolation
          expr: |
            (
              sum(rate(http_requests_total{job="kong",status=~"2..|3.."}[5m]))
              /
              sum(rate(http_requests_total{job="kong"}[5m]))
            ) < 0.999
          for: 5m
          labels:
            severity: page
            slo: availability
            service: api_gateway
          annotations:
            summary: "API Gateway availability below 99.9% SLO"
            description: "Current availability: {{ $value | humanizePercentage }}"

        # Backend Latency SLO
        - alert: BackendLatencySLOViolation
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket{job="lics-backend-dev"}[5m])) by (le)
            ) > 0.200
          for: 5m
          labels:
            severity: warning
            slo: latency
            service: core_backend
          annotations:
            summary: "Backend p95 latency above 200ms SLO"
            description: "Current p95 latency: {{ $value }}s"

        # Error Rate SLO
        - alert: ErrorRateSLOViolation
          expr: |
            (
              sum(rate(http_requests_total{job="lics-backend-dev",status=~"5.."}[5m]))
              /
              sum(rate(http_requests_total{job="lics-backend-dev"}[5m]))
            ) > 0.005
          for: 5m
          labels:
            severity: critical
            slo: error_rate
            service: core_backend
          annotations:
            summary: "Error rate above 0.5% SLO"
            description: "Current error rate: {{ $value | humanizePercentage }}"
  ```
  - Estimated: 8 hours

- [ ] **Task 3.2.3**: Implement error budget tracking
  ```python
  # File: services/backend/app/core/error_budget.py
  from datetime import datetime, timedelta

  class ErrorBudgetTracker:
      def __init__(self, slo_target: float, window_days: int = 30):
          self.slo_target = slo_target
          self.window_days = window_days

      async def calculate_error_budget(self) -> dict:
          """Calculate remaining error budget"""
          total_requests = await self.get_total_requests()
          failed_requests = await self.get_failed_requests()

          actual_availability = 1 - (failed_requests / total_requests)
          error_budget_used = (self.slo_target - actual_availability) / (1 - self.slo_target)

          return {
              "slo_target": self.slo_target,
              "actual_availability": actual_availability,
              "error_budget_remaining": 1 - error_budget_used,
              "error_budget_used_percent": error_budget_used * 100
          }
  ```
  - Estimated: 8 hours

- [ ] **Task 3.2.4**: Create error budget API endpoint
  ```python
  # GET /api/v1/health/error-budget
  {
    "api_gateway": {
      "slo_target": 0.999,
      "actual_availability": 0.9995,
      "error_budget_remaining": 0.50,
      "error_budget_used_percent": 50.0
    }
  }
  ```
  - Estimated: 4 hours

**Validation**
- [ ] SLO alerts trigger correctly
- [ ] Error budget calculations accurate
- [ ] Alert notifications working (Alertmanager)

### 3.3 Enhanced Grafana Dashboards

#### Objectives
- Create comprehensive monitoring dashboards
- Visualize SLI/SLO metrics
- Add error budget tracking

#### Tasks

- [ ] **Task 3.3.1**: Create SLI/SLO Overview Dashboard
  ```json
  {
    "title": "LICS SLI/SLO Overview",
    "panels": [
      {
        "title": "Availability (by service)",
        "targets": [{
          "expr": "sum(rate(http_requests_total{status=~\"2..|3..\"}[5m])) by (job) / sum(rate(http_requests_total[5m])) by (job)"
        }]
      },
      {
        "title": "p95 Latency (by service)",
        "targets": [{
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le))"
        }]
      },
      {
        "title": "Error Budget Remaining",
        "type": "gauge"
      }
    ]
  }
  ```
  - File: `infrastructure/monitoring/grafana/dashboards/slo-overview.json`
  - Estimated: 8 hours

- [ ] **Task 3.3.2**: Create Service Dependency Health Dashboard
  - Visualize dependency tree
  - Show health propagation
  - Highlight failure impacts
  - File: `infrastructure/monitoring/grafana/dashboards/dependency-health.json`
  - Estimated: 6 hours

- [ ] **Task 3.3.3**: Create Performance Metrics Dashboard
  - Request throughput
  - Response time percentiles (p50, p95, p99)
  - Error rates by endpoint
  - Database query performance
  - File: `infrastructure/monitoring/grafana/dashboards/performance.json`
  - Estimated: 6 hours

- [ ] **Task 3.3.4**: Create Capacity Planning Dashboard
  - Resource utilization trends
  - Growth projections
  - Scaling recommendations
  - File: `infrastructure/monitoring/grafana/dashboards/capacity.json`
  - Estimated: 6 hours

**Validation**
- [ ] All dashboards load without errors
- [ ] Metrics display real-time data
- [ ] Drill-down functionality works

### 3.4 Business Metrics Implementation

#### Objectives
- Track business-level metrics (from Documentation.md Section 13.1)
- Monitor user engagement and system usage
- Enable data-driven decisions

#### Tasks

- [ ] **Task 3.4.1**: Implement business metrics
  ```python
  # File: services/backend/app/core/business_metrics.py
  from prometheus_client import Gauge, Counter, Histogram

  # Active Experiments
  active_experiments = Gauge(
      'lics_active_experiments_total',
      'Number of active experiments',
      ['organization_id']
  )

  # Device Utilization
  device_utilization = Gauge(
      'lics_device_utilization_ratio',
      'Device utilization ratio',
      ['device_type', 'organization_id']
  )

  # Data Collection Rate
  data_points_collected = Counter(
      'lics_data_points_collected_total',
      'Total data points collected',
      ['experiment_id', 'metric_type']
  )

  # Task Success Rate
  task_success_rate = Histogram(
      'lics_task_success_rate',
      'Task success rate distribution',
      ['task_type'],
      buckets=[0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
  )

  # User Engagement
  user_actions = Counter(
      'lics_user_actions_total',
      'User actions performed',
      ['action_type', 'user_role']
  )
  ```
  - Estimated: 4 hours

- [ ] **Task 3.4.2**: Add business metric collection points
  - Track experiment lifecycle events
  - Monitor device usage patterns
  - Record user interactions
  - Estimated: 8 hours

- [ ] **Task 3.4.3**: Create business metrics dashboard
  - KPIs and trends
  - Usage analytics
  - Performance insights
  - Estimated: 6 hours

**Validation**
- [ ] Business metrics updating in real-time
- [ ] Dashboard shows meaningful insights
- [ ] Metrics correlate with actual usage

### Phase 3 Deliverables

**Monitoring**
- ✅ SLI metrics implemented
- ✅ SLO targets defined and monitored
- ✅ Error budget tracking operational
- ✅ Alert rules configured

**Dashboards**
- ✅ SLI/SLO overview dashboard
- ✅ Service dependency health dashboard
- ✅ Performance metrics dashboard
- ✅ Business metrics dashboard
- ✅ Capacity planning dashboard

**Alerting**
- ✅ SLO violation alerts
- ✅ Error budget depletion alerts
- ✅ Performance degradation alerts

**Documentation**
- ✅ SLI/SLO definitions documented
- ✅ Runbook for SLO violations
- ✅ Dashboard usage guide

---

## Phase 4: Kubernetes & Infrastructure as Code (Week 7-9)

### Priority: HIGH
### Duration: 3 weeks
### Prerequisites: Phases 1-3 complete

### 4.1 Kubernetes Manifests Creation

#### Objectives
- Create production-ready Kubernetes manifests
- Implement proper resource management
- Configure health checks and auto-scaling

#### Directory Structure
```
infrastructure/kubernetes/
├── base/
│   ├── namespace.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── configmap.yaml
│   ├── frontend/
│   ├── postgres/
│   ├── redis/
│   ├── kong/
│   └── monitoring/
├── overlays/
│   ├── development/
│   ├── staging/
│   └── production/
└── kustomization.yaml
```

#### Tasks

- [ ] **Task 4.1.1**: Create base namespace
  ```yaml
  # File: infrastructure/kubernetes/base/namespace.yaml
  apiVersion: v1
  kind: Namespace
  metadata:
    name: lics-prod
    labels:
      app: lics
      environment: production
  ```
  - Estimated: 2 hours

- [ ] **Task 4.1.2**: Backend deployment manifest
  ```yaml
  # File: infrastructure/kubernetes/base/backend/deployment.yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: lics-backend
    namespace: lics-prod
  spec:
    replicas: 3
    selector:
      matchLabels:
        app: lics-backend
    template:
      metadata:
        labels:
          app: lics-backend
          version: v1
      spec:
        containers:
        - name: backend
          image: ghcr.io/lics/backend:latest
          ports:
          - containerPort: 8000
            name: http
          - containerPort: 8001
            name: websocket
          env:
          - name: DATABASE_URL
            valueFrom:
              secretKeyRef:
                name: lics-secrets
                key: database-url
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2000m
              memory: 4Gi
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
  ```
  - Estimated: 8 hours

- [ ] **Task 4.1.3**: Backend service manifest
  ```yaml
  # File: infrastructure/kubernetes/base/backend/service.yaml
  apiVersion: v1
  kind: Service
  metadata:
    name: lics-backend
    namespace: lics-prod
  spec:
    selector:
      app: lics-backend
    ports:
    - name: http
      port: 8000
      targetPort: 8000
    - name: websocket
      port: 8001
      targetPort: 8001
    type: ClusterIP
  ```
  - Estimated: 2 hours

- [ ] **Task 4.1.4**: HorizontalPodAutoscaler
  ```yaml
  # File: infrastructure/kubernetes/base/backend/hpa.yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: lics-backend-hpa
    namespace: lics-prod
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: lics-backend
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
    behavior:
      scaleDown:
        stabilizationWindowSeconds: 300
        policies:
        - type: Percent
          value: 50
          periodSeconds: 60
      scaleUp:
        stabilizationWindowSeconds: 60
        policies:
        - type: Percent
          value: 100
          periodSeconds: 30
  ```
  - Estimated: 6 hours

- [ ] **Task 4.1.5**: Frontend deployment and service
  - Similar structure to backend
  - Configure CDN integration
  - Estimated: 6 hours

- [ ] **Task 4.1.6**: PostgreSQL StatefulSet
  ```yaml
  # File: infrastructure/kubernetes/base/postgres/statefulset.yaml
  apiVersion: apps/v1
  kind: StatefulSet
  metadata:
    name: postgres
    namespace: lics-prod
  spec:
    serviceName: postgres
    replicas: 1
    selector:
      matchLabels:
        app: postgres
    template:
      spec:
        containers:
        - name: postgres
          image: timescale/timescaledb-ha:pg15-latest
          volumeMounts:
          - name: postgres-data
            mountPath: /home/postgres/pgdata
    volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 100Gi
        storageClassName: fast-ssd
  ```
  - Estimated: 8 hours

- [ ] **Task 4.1.7**: Kong API Gateway deployment
  - Kong deployment manifest
  - Kong service and ingress
  - Estimated: 6 hours

- [ ] **Task 4.1.8**: Monitoring stack (Prometheus, Grafana)
  - Prometheus StatefulSet
  - Grafana deployment
  - Service monitors
  - Estimated: 8 hours

- [ ] **Task 4.1.9**: Create Kustomize overlays
  ```yaml
  # File: infrastructure/kubernetes/overlays/production/kustomization.yaml
  apiVersion: kustomize.config.k8s.io/v1beta1
  kind: Kustomization

  bases:
  - ../../base

  namespace: lics-prod

  replicas:
  - name: lics-backend
    count: 5

  images:
  - name: ghcr.io/lics/backend
    newTag: v1.2.3

  configMapGenerator:
  - name: lics-config
    literals:
    - ENVIRONMENT=production
    - DEBUG=false
  ```
  - Development overlay
  - Staging overlay
  - Production overlay
  - Estimated: 6 hours

**Validation**
- [ ] All manifests apply without errors
- [ ] Pods start successfully
- [ ] Health checks pass
- [ ] Auto-scaling works

### 4.2 Terraform Infrastructure

#### Objectives
- Define infrastructure as code
- Provision cloud resources
- Enable reproducible deployments

#### Tasks

- [ ] **Task 4.2.1**: Create Terraform module structure
  ```
  infrastructure/terraform/
  ├── modules/
  │   ├── kubernetes/
  │   │   ├── main.tf
  │   │   ├── variables.tf
  │   │   └── outputs.tf
  │   ├── database/
  │   ├── networking/
  │   └── monitoring/
  ├── environments/
  │   ├── dev/
  │   ├── staging/
  │   └── prod/
  └── main.tf
  ```
  - Estimated: 4 hours

- [ ] **Task 4.2.2**: Kubernetes cluster module
  ```hcl
  # File: infrastructure/terraform/modules/kubernetes/main.tf
  resource "aws_eks_cluster" "lics" {
    name     = var.cluster_name
    role_arn = aws_iam_role.cluster.arn
    version  = "1.28"

    vpc_config {
      subnet_ids              = var.subnet_ids
      endpoint_private_access = true
      endpoint_public_access  = true
    }

    enabled_cluster_log_types = ["api", "audit", "authenticator"]
  }

  resource "aws_eks_node_group" "lics" {
    cluster_name    = aws_eks_cluster.lics.name
    node_group_name = "lics-nodes"
    node_role_arn   = aws_iam_role.node.arn
    subnet_ids      = var.subnet_ids

    scaling_config {
      desired_size = 3
      max_size     = 10
      min_size     = 2
    }

    instance_types = ["t3.xlarge"]
  }
  ```
  - Estimated: 12 hours

- [ ] **Task 4.2.3**: Database module (RDS/Cloud SQL)
  ```hcl
  # File: infrastructure/terraform/modules/database/main.tf
  resource "aws_db_instance" "lics" {
    identifier           = "lics-postgres"
    engine              = "postgres"
    engine_version      = "15.4"
    instance_class      = "db.t3.large"
    allocated_storage   = 100
    storage_encrypted   = true

    multi_az            = true
    backup_retention_period = 7
    backup_window       = "03:00-04:00"
    maintenance_window  = "mon:04:00-mon:05:00"

    vpc_security_group_ids = [aws_security_group.db.id]
    db_subnet_group_name   = aws_db_subnet_group.lics.name
  }
  ```
  - Estimated: 8 hours

- [ ] **Task 4.2.4**: Networking module
  ```hcl
  # VPC, subnets, security groups, load balancers
  resource "aws_vpc" "lics" {
    cidr_block           = "10.0.0.0/16"
    enable_dns_hostnames = true
    enable_dns_support   = true
  }

  resource "aws_subnet" "public" {
    count                   = 3
    vpc_id                  = aws_vpc.lics.id
    cidr_block              = "10.0.${count.index}.0/24"
    availability_zone       = data.aws_availability_zones.available.names[count.index]
    map_public_ip_on_launch = true
  }
  ```
  - Estimated: 10 hours

- [ ] **Task 4.2.5**: Monitoring module
  - Provision managed Prometheus
  - Set up log aggregation
  - Configure alerting
  - Estimated: 6 hours

- [ ] **Task 4.2.6**: Environment-specific configurations
  ```hcl
  # File: infrastructure/terraform/environments/prod/main.tf
  module "kubernetes" {
    source = "../../modules/kubernetes"

    cluster_name = "lics-prod"
    node_count   = 5
    node_type    = "t3.xlarge"
  }

  module "database" {
    source = "../../modules/database"

    instance_class = "db.r5.2xlarge"
    multi_az       = true
  }
  ```
  - Development environment
  - Staging environment
  - Production environment
  - Estimated: 6 hours

- [ ] **Task 4.2.7**: State management
  ```hcl
  # File: infrastructure/terraform/backend.tf
  terraform {
    backend "s3" {
      bucket         = "lics-terraform-state"
      key            = "prod/terraform.tfstate"
      region         = "us-east-1"
      encrypt        = true
      dynamodb_table = "lics-terraform-locks"
    }
  }
  ```
  - Estimated: 4 hours

**Validation**
- [ ] Terraform plan succeeds
- [ ] Infrastructure provisions correctly
- [ ] State management works
- [ ] No drift detected

### Phase 4 Deliverables

**Kubernetes**
- ✅ Complete manifest set for all services
- ✅ Kustomize overlays for all environments
- ✅ Auto-scaling configurations
- ✅ Resource limits and requests defined

**Terraform**
- ✅ Modular infrastructure code
- ✅ Multi-environment support
- ✅ State management configured
- ✅ Security best practices implemented

**CI/CD Integration**
- ✅ Automated deployment pipelines
- ✅ Infrastructure validation
- ✅ Drift detection

**Documentation**
- ✅ Infrastructure architecture diagrams
- ✅ Deployment procedures
- ✅ Disaster recovery plans

---

## Phase 5: Blue-Green Deployment & Error Handling (Week 10-11)

### Priority: MEDIUM
### Duration: 2 weeks
### Prerequisites: Phase 4 complete

### 5.1 Blue-Green Deployment Pipeline

#### Objectives
- Implement zero-downtime deployments
- Automated rollback on failures
- Traffic switching with validation

#### Tasks

- [ ] **Task 5.1.1**: Create deployment workflow
  ```yaml
  # File: .github/workflows/deploy-blue-green.yml
  name: Blue-Green Deployment

  on:
    push:
      branches: [main]

  jobs:
    deploy-green:
      runs-on: ubuntu-latest
      steps:
        - name: Build and push green deployment
          run: |
            docker build -t ghcr.io/lics/backend:green .
            docker push ghcr.io/lics/backend:green

        - name: Deploy to Kubernetes (green)
          run: |
            kubectl apply -f k8s/backend-green.yaml

        - name: Wait for green deployment
          run: |
            kubectl rollout status deployment/lics-backend-green

        - name: Run smoke tests
          run: |
            ./scripts/smoke-test.sh http://backend-green-svc:8000

    switch-traffic:
      needs: deploy-green
      runs-on: ubuntu-latest
      steps:
        - name: Gradual traffic shift
          run: |
            # 10% to green
            kubectl patch svc lics-backend --patch '{"spec":{"selector":{"version":"green","weight":"10"}}}'
            sleep 300

            # 50% to green
            kubectl patch svc lics-backend --patch '{"spec":{"selector":{"weight":"50"}}}'
            sleep 300

            # 100% to green
            kubectl patch svc lics-backend --patch '{"spec":{"selector":{"version":"green"}}}'

        - name: Monitor error rates
          run: |
            ERROR_RATE=$(curl -s prometheus:9090/api/v1/query?query=error_rate | jq '.data.result[0].value[1]')
            if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
              echo "Error rate too high, rolling back"
              ./scripts/rollback.sh
              exit 1
            fi

    cleanup-blue:
      needs: switch-traffic
      runs-on: ubuntu-latest
      steps:
        - name: Remove blue deployment
          run: |
            kubectl delete deployment lics-backend-blue
  ```
  - Estimated: 12 hours

- [ ] **Task 5.1.2**: Create traffic switching script
  ```bash
  # File: tools/deployment/traffic-switch.sh
  #!/bin/bash

  GREEN_SERVICE="lics-backend-green"
  BLUE_SERVICE="lics-backend-blue"

  # Health check green deployment
  if ! curl -f "http://${GREEN_SERVICE}:8000/health"; then
    echo "Green deployment unhealthy"
    exit 1
  fi

  # Gradual traffic shift
  for weight in 10 25 50 75 100; do
    kubectl patch svc lics-backend \
      --patch "{\"spec\":{\"selector\":{\"version\":\"green\",\"weight\":\"${weight}\"}}}"

    echo "Shifted ${weight}% traffic to green"
    sleep 300  # 5 minute soak

    # Check error rates
    ERROR_RATE=$(curl prometheus:9090/api/v1/query?query=error_rate_5m)
    if [ "$ERROR_RATE" -gt "0.01" ]; then
      echo "Error rate exceeded threshold, rolling back"
      ./rollback.sh
      exit 1
    fi
  done
  ```
  - Estimated: 6 hours

- [ ] **Task 5.1.3**: Implement rollback automation
  ```bash
  # File: tools/deployment/rollback.sh
  #!/bin/bash

  echo "Rolling back to blue deployment"

  # Immediate traffic switch to blue
  kubectl patch svc lics-backend \
    --patch '{"spec":{"selector":{"version":"blue"}}}'

  # Remove failed green deployment
  kubectl delete deployment lics-backend-green

  # Alert team
  curl -X POST https://slack.webhook.url \
    -d '{"text":"🚨 Deployment rolled back due to errors"}'
  ```
  - Estimated: 4 hours

- [ ] **Task 5.1.4**: Add deployment validation tests
  - Smoke tests
  - Integration tests
  - Performance baseline checks
  - Estimated: 8 hours

**Validation**
- [ ] Blue-green deployment works end-to-end
- [ ] Gradual traffic shift functional
- [ ] Automatic rollback on errors
- [ ] Zero downtime during deployment

### 5.2 Standardized Error Response Format

#### Objectives
- Implement error format from Documentation.md Section 20
- Consistent error codes and messages
- Structured error logging

#### Tasks

- [ ] **Task 5.2.1**: Create error response schema
  ```python
  # File: services/backend/app/schemas/errors.py
  from pydantic import BaseModel
  from typing import Optional, Dict, Any

  class ErrorDetail(BaseModel):
      field: str
      message: str
      type: str

  class ErrorResponse(BaseModel):
      code: str
      message: str
      details: Optional[Dict[str, Any]] = None
      trace_id: str

      class Config:
          json_schema_extra = {
              "example": {
                  "code": "VALIDATION_ERROR",
                  "message": "Request validation failed",
                  "details": {
                      "validation_errors": [
                          {
                              "field": "email",
                              "message": "Invalid email format",
                              "type": "value_error.email"
                          }
                      ]
                  },
                  "trace_id": "123e4567-e89b-12d3-a456-426614174000"
              }
          }
  ```
  - Estimated: 4 hours

- [ ] **Task 5.2.2**: Update exception handlers
  ```python
  # File: services/backend/app/middleware/error_handler.py
  @app.exception_handler(HTTPException)
  async def http_exception_handler(request: Request, exc: HTTPException):
      correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

      error_response = ErrorResponse(
          code=get_error_code(exc.status_code),
          message=exc.detail,
          trace_id=correlation_id
      )

      return JSONResponse(
          status_code=exc.status_code,
          content={"error": error_response.dict()},
          headers={"X-Correlation-ID": correlation_id}
      )
  ```
  - Estimated: 6 hours

- [ ] **Task 5.2.3**: Create error code taxonomy
  ```python
  # File: services/backend/app/core/error_codes.py
  ERROR_CODES = {
      # Client Errors (4xx)
      400: "BAD_REQUEST",
      401: "UNAUTHORIZED",
      403: "FORBIDDEN",
      404: "NOT_FOUND",
      409: "CONFLICT",
      422: "VALIDATION_ERROR",
      429: "RATE_LIMIT_EXCEEDED",

      # Server Errors (5xx)
      500: "INTERNAL_SERVER_ERROR",
      502: "BAD_GATEWAY",
      503: "SERVICE_UNAVAILABLE",
      504: "GATEWAY_TIMEOUT"
  }

  # Business logic errors
  BUSINESS_ERROR_CODES = {
      "DEVICE_OFFLINE": "Device is currently offline",
      "EXPERIMENT_RUNNING": "Cannot modify running experiment",
      "INSUFFICIENT_PERMISSIONS": "User lacks required permissions"
  }
  ```
  - Estimated: 4 hours

- [ ] **Task 5.2.4**: Integrate Sentry error tracking
  ```python
  # File: services/backend/app/core/error_tracking.py
  import sentry_sdk
  from sentry_sdk.integrations.fastapi import FastApiIntegration

  sentry_sdk.init(
      dsn=settings.SENTRY_DSN,
      integrations=[FastApiIntegration()],
      traces_sample_rate=0.1,
      environment=settings.ENVIRONMENT
  )
  ```
  - Estimated: 4 hours

**Validation**
- [ ] All errors follow standard format
- [ ] Error codes consistent across endpoints
- [ ] Sentry integration capturing errors

### 5.3 Recovery Procedures & Runbooks

#### Objectives
- Document failure scenarios
- Create automated recovery scripts
- Establish incident response playbooks

#### Tasks

- [ ] **Task 5.3.1**: Create runbook directory structure
  ```
  docs/runbooks/
  ├── database-failure.md
  ├── redis-failure.md
  ├── mqtt-broker-failure.md
  ├── service-degradation.md
  ├── deployment-rollback.md
  └── data-recovery.md
  ```
  - Estimated: 2 hours

- [ ] **Task 5.3.2**: Database failure runbook
  ```markdown
  # Database Failure Recovery

  ## Detection
  - Alert: PostgreSQL down
  - Symptoms: 503 errors, connection refused

  ## Immediate Actions
  1. Check database status: `kubectl get pods -l app=postgres`
  2. Check logs: `kubectl logs postgres-0`
  3. Verify backups available

  ## Recovery Steps
  1. If pod crashed: `kubectl delete pod postgres-0`
  2. If data corrupted: Restore from backup
  3. If disk full: Expand PVC

  ## Post-Recovery
  - Verify data integrity
  - Run health checks
  - Document incident
  ```
  - Estimated: 8 hours

- [ ] **Task 5.3.3**: Automated recovery scripts
  ```bash
  # File: tools/recovery/auto-recover-database.sh
  #!/bin/bash

  # Detect database failure
  if ! pg_isready -h $DB_HOST; then
    echo "Database unhealthy, attempting recovery"

    # Restart pod
    kubectl delete pod postgres-0

    # Wait for recovery
    kubectl wait --for=condition=Ready pod/postgres-0 --timeout=300s

    # Verify recovery
    if pg_isready -h $DB_HOST; then
      echo "Database recovered successfully"
      # Alert team
      send_alert "Database recovered automatically"
    else
      echo "Recovery failed, manual intervention required"
      # Page on-call
      page_oncall "Database recovery failed"
    fi
  fi
  ```
  - Estimated: 12 hours

**Validation**
- [ ] Runbooks comprehensive and clear
- [ ] Recovery scripts tested in staging
- [ ] Incident response procedures documented

### Phase 5 Deliverables

**Deployment**
- ✅ Blue-green deployment pipeline operational
- ✅ Automated rollback on failures
- ✅ Traffic switching with validation
- ✅ Deployment monitoring

**Error Handling**
- ✅ Standardized error response format
- ✅ Error code taxonomy implemented
- ✅ Sentry integration active
- ✅ Structured error logging

**Recovery**
- ✅ Comprehensive runbooks created
- ✅ Automated recovery scripts
- ✅ Incident response playbooks
- ✅ Disaster recovery tested

**Documentation**
- ✅ Deployment guide updated
- ✅ Error handling documentation
- ✅ Recovery procedures documented

---

## Phase 6: Performance Testing & Capacity Planning (Week 12)

### Priority: MEDIUM
### Duration: 1 week
### Prerequisites: Phases 1-5 complete

### 6.1 Performance Testing Framework

#### Objectives
- Establish performance baselines
- Identify bottlenecks
- Validate scalability

#### Tasks

- [ ] **Task 6.1.1**: Set up K6 load testing
  ```javascript
  // File: tools/performance/load-test.js
  import http from 'k6/http';
  import { check, sleep } from 'k6';
  import { Rate } from 'k6/metrics';

  const errorRate = new Rate('errors');

  export let options = {
    stages: [
      { duration: '2m', target: 50 },   // Ramp-up to 50 users
      { duration: '5m', target: 50 },   // Stay at 50 users
      { duration: '2m', target: 100 },  // Ramp to 100 users
      { duration: '5m', target: 100 },  // Stay at 100 users
      { duration: '2m', target: 200 },  // Spike to 200 users
      { duration: '5m', target: 200 },  // Maintain spike
      { duration: '5m', target: 0 },    // Ramp down
    ],
    thresholds: {
      'http_req_duration': ['p(95)<200'],  // 95% < 200ms
      'http_req_failed': ['rate<0.01'],    // Error rate < 1%
      'errors': ['rate<0.1'],
    },
  };

  export default function() {
    // Test various endpoints
    let endpoints = [
      '/api/v1/devices',
      '/api/v1/experiments',
      '/api/v1/tasks'
    ];

    endpoints.forEach(endpoint => {
      let res = http.get(`http://localhost:8080${endpoint}`, {
        headers: { 'Authorization': `Bearer ${__ENV.TOKEN}` }
      });

      check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 200ms': (r) => r.timings.duration < 200,
      });

      errorRate.add(res.status !== 200);
    });

    sleep(1);
  }
  ```
  - Estimated: 8 hours

- [ ] **Task 6.1.2**: Create performance test suite
  - API endpoint tests
  - Database query tests
  - WebSocket connection tests
  - File upload tests
  - Estimated: 12 hours

- [ ] **Task 6.1.3**: Integrate into CI/CD
  ```yaml
  # .github/workflows/performance-test.yml
  name: Performance Testing

  on:
    schedule:
      - cron: '0 2 * * *'  # Daily at 2 AM
    workflow_dispatch:

  jobs:
    load-test:
      runs-on: ubuntu-latest
      steps:
        - name: Run K6 load test
          run: k6 run tools/performance/load-test.js

        - name: Check thresholds
          run: |
            if [ $? -ne 0 ]; then
              echo "Performance thresholds exceeded"
              # Alert team
              exit 1
            fi
  ```
  - Estimated: 4 hours

- [ ] **Task 6.1.4**: Performance regression detection
  - Compare against baselines
  - Alert on degradation
  - Estimated: 6 hours

**Validation**
- [ ] Load tests run successfully
- [ ] Thresholds met under load
- [ ] No memory leaks detected

### 6.2 Capacity Planning

#### Objectives
- Project resource needs
- Plan for growth
- Optimize costs

#### Tasks

- [ ] **Task 6.2.1**: Resource utilization analysis
  - CPU/Memory trends
  - Storage growth rates
  - Network bandwidth usage
  - Estimated: 6 hours

- [ ] **Task 6.2.2**: Growth projection model
  ```python
  # File: tools/capacity/growth-projection.py
  import pandas as pd
  from sklearn.linear_model import LinearRegression

  def project_capacity(historical_data, months_ahead=12):
      """Project resource needs based on historical data"""
      # Fit linear regression model
      model = LinearRegression()
      model.fit(historical_data['months'], historical_data['usage'])

      # Project future usage
      future_months = range(len(historical_data), len(historical_data) + months_ahead)
      projections = model.predict(future_months)

      return projections
  ```
  - Estimated: 8 hours

- [ ] **Task 6.2.3**: Capacity planning dashboard
  - Current vs. projected usage
  - Scaling recommendations
  - Cost projections
  - Estimated: 6 hours

**Validation**
- [ ] Resource projections align with trends
- [ ] Scaling recommendations actionable
- [ ] Cost estimates accurate

### Phase 6 Deliverables

**Testing**
- ✅ K6 load testing framework
- ✅ Performance test suite
- ✅ CI/CD integration
- ✅ Regression detection

**Planning**
- ✅ Resource utilization analysis
- ✅ Growth projection model
- ✅ Capacity planning dashboard

**Documentation**
- ✅ Performance testing guide
- ✅ Baseline metrics documented
- ✅ Capacity planning procedures

---

## Implementation Timeline Summary

| Phase | Duration | Start | End | Key Deliverables |
|-------|----------|-------|-----|------------------|
| **Phase 1**: API Gateway & Resilience | 2 weeks | Week 1 | Week 2 | Kong Gateway, Circuit Breakers, Dependency Matrix |
| **Phase 2**: Database Optimization | 2 weeks | Week 3 | Week 4 | Indexes, TimescaleDB, Connection Pooling |
| **Phase 3**: SLI/SLO & Monitoring | 2 weeks | Week 5 | Week 6 | SLI Metrics, SLO Alerts, Dashboards |
| **Phase 4**: Kubernetes & Terraform | 3 weeks | Week 7 | Week 9 | K8s Manifests, Terraform Modules, IaC |
| **Phase 5**: Deployment & Errors | 2 weeks | Week 10 | Week 11 | Blue-Green Pipeline, Error Standards, Runbooks |
| **Phase 6**: Performance & Capacity | 1 week | Week 12 | Week 12 | Load Testing, Capacity Planning |

**Total Duration**: 12 weeks (3 months)

---

## Success Criteria

### Technical Metrics
- [ ] API response time p95 < 200ms (99% of requests)
- [ ] System uptime > 99.9% (measured monthly)
- [ ] Error rate < 0.1% (measured by SLO)
- [ ] All circuit breakers operational
- [ ] Zero production incidents during deployment
- [ ] Database query performance improved by 50%

### Implementation Metrics
- [ ] All Kubernetes manifests created and tested
- [ ] Terraform provisions infrastructure successfully
- [ ] Blue-green deployment working in production
- [ ] SLO alerts firing correctly
- [ ] Performance tests integrated in CI/CD
- [ ] 100% service coverage by circuit breakers

### Documentation Metrics
- [ ] All runbooks created and tested
- [ ] Architecture diagrams updated
- [ ] API documentation complete
- [ ] Deployment guides written
- [ ] Team training completed

### Business Metrics
- [ ] Zero downtime deployments
- [ ] Reduced incident response time by 75%
- [ ] Infrastructure costs optimized by 20%
- [ ] Developer productivity increased

---

## Risk Management

### High-Risk Items

**1. API Gateway Migration**
- **Risk**: Service disruption during migration
- **Impact**: HIGH - Could cause complete outage
- **Mitigation**:
  - Gradual rollout with feature flags
  - Parallel run (direct + gateway) for 1 week
  - Extensive testing in staging
  - Rollback plan ready
- **Contingency**: Keep direct backend access as fallback

**2. Database Schema Changes**
- **Risk**: Data loss or downtime during TimescaleDB conversion
- **Impact**: CRITICAL - Data loss unacceptable
- **Mitigation**:
  - Full backup before migration
  - Test in staging environment first
  - Scheduled maintenance window
  - Rehearse migration process
- **Contingency**: Restore from backup, postpone migration

**3. Kubernetes Deployment**
- **Risk**: Complex orchestration, potential failures
- **Impact**: HIGH - Production stability at risk
- **Mitigation**:
  - Start with non-production environments
  - Gradual service migration
  - Automated rollbacks
  - Comprehensive monitoring
- **Contingency**: Maintain VM-based deployment as fallback

### Medium-Risk Items

**1. Circuit Breaker Misconfiguration**
- **Risk**: Cascading failures or unnecessary degradation
- **Impact**: MEDIUM - Service availability affected
- **Mitigation**:
  - Conservative failure thresholds initially
  - Gradual tuning based on metrics
  - Extensive monitoring
- **Contingency**: Disable circuit breakers if causing issues

**2. Performance Testing Reveals Issues**
- **Risk**: System can't handle expected load
- **Impact**: MEDIUM - Delays deployment
- **Mitigation**:
  - Early performance testing
  - Incremental optimization
  - Identify bottlenecks systematically
- **Contingency**: Scale horizontally to meet demands

**3. Infrastructure Costs**
- **Risk**: Cloud costs exceed budget
- **Impact**: MEDIUM - Financial impact
- **Mitigation**:
  - Cost estimation before provisioning
  - Use spot/preemptible instances
  - Right-sizing resources
  - Cost monitoring and alerts
- **Contingency**: Scale down non-critical environments

### Low-Risk Items

**1. Documentation Gaps**
- **Risk**: Team confusion, slower onboarding
- **Impact**: LOW - Productivity impact
- **Mitigation**: Continuous documentation during implementation
- **Contingency**: Knowledge transfer sessions

**2. Monitoring Dashboard Complexity**
- **Risk**: Dashboards too complex to use
- **Impact**: LOW - Reduced effectiveness
- **Mitigation**: User testing, iterative design
- **Contingency**: Simplify dashboards based on feedback

---

## Resource Requirements

### Development Team

**Core Team (Full-time)**
- 1 DevOps Engineer (Kubernetes, Terraform, Kong, CI/CD)
- 1 Backend Engineer (Circuit breakers, database, metrics)
- 1 Site Reliability Engineer (Monitoring, SLI/SLO, runbooks)

**Part-time Support**
- 0.5 Frontend Engineer (Integration updates)
- 0.5 QA Engineer (Testing, validation)
- 0.25 Technical Writer (Documentation)

**Timeline**: 12 weeks

### Infrastructure

**Development Environment**
- Kubernetes cluster (3 nodes, t3.large)
- PostgreSQL (db.t3.large)
- Redis (cache.t3.medium)
- Estimated cost: $500/month

**Staging Environment**
- Kubernetes cluster (3 nodes, t3.xlarge)
- PostgreSQL (db.t3.xlarge)
- Redis (cache.t3.large)
- Estimated cost: $1,000/month

**Production (Post-implementation)**
- Kubernetes cluster (5-10 nodes, t3.2xlarge)
- PostgreSQL (db.r5.2xlarge, multi-AZ)
- Redis (cache.r5.large, cluster mode)
- Estimated cost: $5,000/month

### Tools & Services

**Required**
- Kong API Gateway (open-source)
- Terraform Cloud (free tier or team plan)
- GitHub Actions minutes (included in plan)
- Docker Hub or GHCR (free for public)

**Optional but Recommended**
- Sentry (error tracking) - $26/month
- PagerDuty (incident management) - $21/user/month
- DataDog (enhanced monitoring) - $15/host/month

### Training & Knowledge Transfer

- Kubernetes training: 2 days
- Terraform workshops: 1 day
- SLI/SLO practices: 1 day
- Blue-green deployment demo: 0.5 days

---

## Quality Assurance

### Code Quality Standards

**Pre-merge Requirements**
- [ ] All tests passing (unit, integration, E2E)
- [ ] Code coverage > 80%
- [ ] Linting checks pass
- [ ] Security scan clean
- [ ] Performance benchmarks met
- [ ] Peer review approved

### Testing Strategy

**Unit Tests**
- Circuit breaker functionality
- Error response formatting
- Business logic validation
- Target: 80% coverage

**Integration Tests**
- API Gateway routing
- Service communication
- Database operations
- Circuit breaker integration

**E2E Tests**
- User workflows
- Deployment pipelines
- Rollback procedures
- Recovery scenarios

**Performance Tests**
- Load testing (K6)
- Stress testing
- Endurance testing
- Scalability testing

**Security Tests**
- Dependency scanning
- Container vulnerability scanning
- Infrastructure security audit
- Penetration testing (external)

### Validation Gates

**Phase Completion Criteria**
Each phase must meet:
- [ ] All tasks completed
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Stakeholder review approved
- [ ] Metrics showing improvement

**Production Deployment Gates**
Before deploying to production:
- [ ] All phases complete
- [ ] Performance tests passing
- [ ] Security audit passed
- [ ] Disaster recovery tested
- [ ] Runbooks validated
- [ ] Team training completed
- [ ] Rollback plan tested

---

## Monitoring & Feedback

### Weekly Progress Reviews

**Agenda**
- Completed tasks review
- Blockers and issues
- Upcoming week planning
- Risk assessment update
- Budget review

**Participants**
- Development team
- Product owner
- Stakeholders

### Key Performance Indicators (KPIs)

**Development KPIs**
- Tasks completed vs. planned
- Code review turnaround time
- Test coverage trend
- Bug discovery rate
- Deployment frequency

**System KPIs**
- API response time (p50, p95, p99)
- Error rate
- Uptime percentage
- Resource utilization
- Cost per request

### Continuous Improvement

**Feedback Mechanisms**
- Daily standups
- Weekly retrospectives
- Monthly architecture reviews
- Quarterly planning sessions

**Adaptation Process**
- Identify improvement areas
- Propose changes
- Implement and measure
- Iterate based on results

---

## Post-Implementation

### Maintenance Plan

**Weekly Tasks**
- Review monitoring dashboards
- Check SLO compliance
- Update runbooks as needed
- Security patch review

**Monthly Tasks**
- Performance analysis
- Capacity planning review
- Cost optimization review
- Incident retrospectives

**Quarterly Tasks**
- Architecture review
- Technology refresh evaluation
- Training updates
- Disaster recovery drill

### Knowledge Transfer

**Documentation Deliverables**
- Architecture overview
- Deployment procedures
- Runbooks and playbooks
- Troubleshooting guides
- Best practices

**Training Sessions**
- System architecture (2 hours)
- Deployment process (2 hours)
- Incident response (2 hours)
- Monitoring and alerts (2 hours)

### Continuous Evolution

**Technology Radar**
- Evaluate new tools and practices
- Plan incremental improvements
- Stay current with industry trends
- Contribute to open-source

**Innovation Budget**
- 20% time for experimentation
- POCs for new technologies
- Conference attendance
- Knowledge sharing

---

## Appendix A: Configuration Templates

### Kong Configuration Example

```yaml
# infrastructure/kong/kong-dev.yml
_format_version: "3.0"
_transform: true

services:
  - name: lics-backend
    url: http://backend-dev:8000
    retries: 3
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000

    routes:
      - name: api-v1
        paths:
          - /api/v1
        strip_path: false
        preserve_host: false
        protocols:
          - http
          - https

    plugins:
      # Rate Limiting
      - name: rate-limiting
        config:
          minute: 100
          hour: 1000
          policy: redis
          fault_tolerant: true
          hide_client_headers: false
          redis:
            host: redis-dev
            port: 6379
            database: 0

      # JWT Authentication
      - name: jwt
        config:
          secret_is_base64: false
          run_on_preflight: false
          claims_to_verify:
            - exp

      # CORS
      - name: cors
        config:
          origins:
            - http://localhost:3000
            - https://localhost:3000
          methods:
            - GET
            - POST
            - PUT
            - PATCH
            - DELETE
            - OPTIONS
          headers:
            - Accept
            - Authorization
            - Content-Type
          exposed_headers:
            - X-Correlation-ID
            - X-RateLimit-Limit
            - X-RateLimit-Remaining
          credentials: true
          max_age: 3600

      # Prometheus Metrics
      - name: prometheus
        config:
          per_consumer: true
          status_code_metrics: true
          latency_metrics: true
          bandwidth_metrics: true

      # Request Transformer
      - name: request-transformer
        config:
          add:
            headers:
              - X-Gateway: Kong
```

### Kubernetes HPA Example

```yaml
# infrastructure/kubernetes/base/backend/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: lics-backend-hpa
  namespace: lics-prod
  labels:
    app: lics-backend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: lics-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    # CPU-based scaling
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # Memory-based scaling
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # Custom metric: HTTP requests per second
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"

  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
        - type: Pods
          value: 1
          periodSeconds: 60
      selectPolicy: Min

    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 30
        - type: Pods
          value: 2
          periodSeconds: 30
      selectPolicy: Max
```

---

## Appendix B: Checklist

### Pre-Implementation Checklist

- [ ] Stakeholder approval obtained
- [ ] Budget allocated
- [ ] Team assembled
- [ ] Development environment ready
- [ ] Staging environment provisioned
- [ ] Access credentials configured
- [ ] Git repository prepared
- [ ] CI/CD pipeline functional

### Phase Completion Checklists

**Phase 1 Checklist**
- [ ] Kong API Gateway deployed
- [ ] All routes configured
- [ ] Rate limiting working
- [ ] JWT validation functional
- [ ] Circuit breakers implemented
- [ ] Dependency matrix created
- [ ] Health checks updated
- [ ] Documentation complete

**Phase 2 Checklist**
- [ ] Database indexes created
- [ ] TimescaleDB hypertables configured
- [ ] Compression policies active
- [ ] Retention policies set
- [ ] Connection pooling optimized
- [ ] Query performance improved
- [ ] Migrations tested
- [ ] Documentation updated

**Phase 3 Checklist**
- [ ] SLI metrics implemented
- [ ] SLO targets defined
- [ ] Alert rules configured
- [ ] Error budget tracking active
- [ ] Dashboards created
- [ ] Business metrics implemented
- [ ] Documentation complete

**Phase 4 Checklist**
- [ ] Kubernetes manifests created
- [ ] Kustomize overlays configured
- [ ] Terraform modules implemented
- [ ] Infrastructure provisioned
- [ ] Auto-scaling configured
- [ ] State management working
- [ ] Documentation complete

**Phase 5 Checklist**
- [ ] Blue-green deployment working
- [ ] Rollback automation tested
- [ ] Error format standardized
- [ ] Sentry integration active
- [ ] Runbooks created
- [ ] Recovery scripts tested
- [ ] Documentation complete

**Phase 6 Checklist**
- [ ] K6 tests created
- [ ] Performance baselines established
- [ ] CI/CD integration complete
- [ ] Capacity planning model created
- [ ] Dashboard operational
- [ ] Documentation complete

### Production Deployment Checklist

- [ ] All phases complete
- [ ] Tests passing (unit, integration, E2E)
- [ ] Performance tests passing
- [ ] Security audit passed
- [ ] Disaster recovery tested
- [ ] Runbooks validated
- [ ] Team training completed
- [ ] Rollback plan tested
- [ ] Stakeholder approval
- [ ] Communication plan ready
- [ ] Monitoring alerts configured
- [ ] On-call rotation established

---

## Appendix C: Glossary

**API Gateway**: Centralized entry point for all API requests, providing routing, authentication, rate limiting, and monitoring.

**Blue-Green Deployment**: Deployment strategy where two identical production environments (blue and green) exist, allowing zero-downtime updates by switching traffic between them.

**Circuit Breaker**: Design pattern that prevents cascading failures by stopping calls to failing services and providing fallback mechanisms.

**Error Budget**: The maximum amount of time a system can fail without violating its SLO, used to balance reliability and development velocity.

**Horizontal Pod Autoscaler (HPA)**: Kubernetes component that automatically scales the number of pods based on observed CPU, memory, or custom metrics.

**Hypertable**: TimescaleDB's abstraction for time-series data that automatically partitions data into chunks for better performance.

**Infrastructure as Code (IaC)**: Managing infrastructure through code and version control rather than manual processes.

**Kustomize**: Tool for customizing Kubernetes manifests without modifying the original files.

**Service Level Indicator (SLI)**: A quantitative measure of a service's behavior (e.g., latency, error rate, availability).

**Service Level Objective (SLO)**: A target value or range for an SLI over a specific time period.

**StatefulSet**: Kubernetes workload API object for managing stateful applications that require persistent storage and stable network identities.

---

## Document Control

**Version History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-24 | LICS Team | Initial refactoring plan created |

**Approval**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Technical Lead | | | |
| Product Owner | | | |
| DevOps Lead | | | |

**Next Review Date**: 2025-11-07 (2 weeks)

---

**End of Refactoring Plan**

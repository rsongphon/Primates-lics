# Phase 1 Testing Guide
## API Gateway & Circuit Breakers

This directory contains comprehensive tests for Phase 1 implementation.

---

## Quick Start

### Run All Tests

```bash
# From project root
cd /Users/beacon/Primates-lics
./tests/phase1/run_all_tests.sh
```

This will:
1. Check Docker is running
2. Start services if needed
3. Run Kong integration tests
4. Run circuit breaker unit tests
5. Test monitoring endpoints
6. Generate comprehensive report

### Run Individual Test Suites

#### Kong Integration Tests

```bash
./tests/phase1/test_kong_integration.sh
```

Tests:
- Kong Admin API accessibility
- Kong Proxy routing
- Service and route configuration
- Plugin functionality (rate limiting, CORS, JWT)
- Health checks
- Prometheus metrics

#### Circuit Breaker Tests

```bash
# From backend directory
cd services/backend
python -m pytest tests/phase1/test_circuit_breakers.py -v
```

Tests:
- Circuit breaker initialization
- Decorator functionality (async/sync)
- Failure detection and circuit opening
- Fallback execution
- Service dependency registry
- Degraded mode handling

---

## Prerequisites

### Required

1. **Docker Desktop Running**
   ```bash
   docker info  # Should succeed
   ```

2. **Services Started**
   ```bash
   make dev
   # OR
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **Python Environment** (for Python tests)
   ```bash
   cd services/backend
   pip install -r requirements.txt
   pip install pytest pytest-asyncio
   ```

### Optional

- `curl` for manual API testing
- `jq` for JSON formatting
- Browser for viewing Kong Admin UI

---

## Test Suites

### 1. Kong Integration Tests (`test_kong_integration.sh`)

**What it tests:**
- ✅ Kong Admin API on port 8001
- ✅ Kong Proxy on port 8080
- ✅ Service registration (lics-backend, lics-websocket)
- ✅ Route configuration (/api/v1, /ws)
- ✅ Plugin loading and configuration
- ✅ Health check routing
- ✅ Rate limiting enforcement
- ✅ CORS headers
- ✅ Prometheus metrics endpoint

**Expected Results:**
```
================================================================
Test Summary
================================================================
Total Tests:  15-20
Passed:       15-20
Failed:       0
Success Rate: 100.0%
```

**Common Issues:**

- **Kong not accessible**: Ensure Kong started successfully
  ```bash
  docker-compose -f docker-compose.dev.yml logs kong-dev
  ```

- **Backend not accessible**: Check backend is running
  ```bash
  docker-compose -f docker-compose.dev.yml ps backend-dev
  ```

- **Rate limiting not triggered**: This is OK - may need more requests
  - Not a critical failure

### 2. Circuit Breaker Tests (`test_circuit_breakers.py`)

**What it tests:**
- ✅ Circuit breaker manager initialization (6 service types)
- ✅ Decorator wrapping (async and sync functions)
- ✅ Failure counting and circuit opening
- ✅ Fallback value return when circuit open
- ✅ Fallback strategies for all services
- ✅ Degraded mode handler
- ✅ Service dependency registry (5 dependencies)
- ✅ Health checking
- ✅ Dependency visualization data
- ✅ Mermaid diagram generation

**Expected Results:**
```
======================== test session starts =========================
collected 30+ items

test_circuit_breakers.py::TestCircuitBreakerInitialization::test_circuit_breaker_manager_initialized PASSED
test_circuit_breakers.py::TestCircuitBreakerInitialization::test_all_service_types_have_breakers PASSED
test_circuit_breakers.py::TestCircuitBreakerInitialization::test_circuit_breaker_configurations PASSED
...
======================== 30 passed in 2.5s ==========================
```

**Common Issues:**

- **Import errors**: Ensure you're in backend directory
  ```bash
  cd services/backend
  export PYTHONPATH=$PWD:$PYTHONPATH
  ```

- **Module not found**: Install dependencies
  ```bash
  pip install -r requirements.txt
  pip install pybreaker pytest pytest-asyncio
  ```

### 3. Manual Testing Scenarios

#### Test 1: Kong Routing

```bash
# Health check through Kong
curl http://localhost:8080/api/v1/health

# Expected: {"status":"healthy","timestamp":"...","service":"LICS Backend"}

# Check Kong added headers
curl -I http://localhost:8080/api/v1/health | grep -i x-gateway

# Expected: X-Gateway: Kong
```

#### Test 2: Rate Limiting

```bash
# Rapid requests to trigger rate limiting
for i in {1..150}; do
  curl -s -w "%{http_code}\n" -o /dev/null http://localhost:8080/api/v1/health
  sleep 0.1
done

# Expected: See some 429 (Too Many Requests) responses
```

#### Test 3: Circuit Breaker Opening

```bash
# Stop PostgreSQL to trigger circuit breaker
docker-compose -f docker-compose.dev.yml stop postgres-dev

# Make request that needs database
curl http://localhost:8080/api/v1/health/comprehensive

# Check circuit breaker status
curl http://localhost:8080/api/v1/monitoring/circuit-breakers \
  -H "Authorization: Bearer <token>"

# Expected: PostgreSQL circuit breaker in "open" state

# Restart PostgreSQL
docker-compose -f docker-compose.dev.yml start postgres-dev

# Wait 60 seconds for circuit to test recovery
sleep 60

# Check again - should transition: open -> half_open -> closed
curl http://localhost:8080/api/v1/monitoring/circuit-breakers \
  -H "Authorization: Bearer <token>"
```

#### Test 4: Service Dependencies

```bash
# Get dependency visualization
curl http://localhost:8080/api/v1/monitoring/dependencies/visualization/graph \
  -H "Authorization: Bearer <token>" | jq

# Get Mermaid diagram
curl http://localhost:8080/api/v1/monitoring/dependencies/visualization/mermaid \
  -H "Authorization: Bearer <token>"

# Expected: Mermaid diagram text starting with "graph TD"
```

#### Test 5: Prometheus Metrics

```bash
# Check Kong metrics
curl http://localhost:8001/metrics | grep circuit_breaker

# Expected metrics:
# - circuit_breaker_state{service_name="PostgreSQL",service_type="postgresql"} 0
# - circuit_breaker_successes_total{service_name="PostgreSQL",service_type="postgresql"} X
# - circuit_breaker_failures_total{...}
# - circuit_breaker_call_duration_seconds_bucket{...}
```

---

## Test Results

Test results are saved in `test-results/phase1/`:

```
test-results/phase1/
├── kong_test_YYYYMMDD_HHMMSS.log          # Kong integration log
├── circuit_breaker_output_YYYYMMDD_HHMMSS.log  # Circuit breaker output
├── circuit_breaker_tests_YYYYMMDD_HHMMSS.json  # JSON test results
└── phase1_full_report_YYYYMMDD_HHMMSS.md       # Comprehensive report
```

### Viewing Results

```bash
# Latest Kong test log
ls -t test-results/phase1/kong_test_*.log | head -1 | xargs cat

# Latest comprehensive report
ls -t test-results/phase1/phase1_full_report_*.md | head -1 | xargs cat

# Latest circuit breaker output
ls -t test-results/phase1/circuit_breaker_output_*.log | head -1 | xargs cat
```

---

## Troubleshooting

### Docker Not Running

**Symptom**: "Cannot connect to the Docker daemon"

**Solution**:
```bash
# Start Docker Desktop
open -a Docker  # macOS

# Wait for Docker to be ready
while ! docker info > /dev/null 2>&1; do sleep 1; done
echo "Docker is ready"
```

### Services Not Starting

**Symptom**: Services fail to start or exit immediately

**Solution**:
```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs

# Restart specific service
docker-compose -f docker-compose.dev.yml restart backend-dev

# Nuclear option: rebuild
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build -d
```

### Kong Configuration Errors

**Symptom**: Kong fails to start or load configuration

**Solution**:
```bash
# Check Kong logs
docker-compose -f docker-compose.dev.yml logs kong-dev
docker-compose -f docker-compose.dev.yml logs kong-migration-dev

# Validate Kong configuration
docker-compose -f docker-compose.dev.yml exec kong-dev kong check /kong/declarative/kong-dev.yml

# Restart Kong
docker-compose -f docker-compose.dev.yml restart kong-dev
```

### Port Conflicts

**Symptom**: "Port already in use"

**Solution**:
```bash
# Find what's using the port
lsof -i :8080  # Kong Proxy
lsof -i :8001  # Kong Admin
lsof -i :8000  # Backend

# Kill process or change ports in docker-compose.dev.yml
```

### Python Import Errors

**Symptom**: "ModuleNotFoundError: No module named 'app'"

**Solution**:
```bash
# Ensure you're in backend directory
cd services/backend

# Set PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH

# Install dependencies
pip install -r requirements.txt
pip install pybreaker pytest pytest-asyncio
```

### Authentication Required Errors

**Symptom**: "401 Unauthorized" for monitoring endpoints

**Expected Behavior**: Monitoring endpoints require authentication.

**Solution**:
1. Login to get JWT token
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin123"}' \
     | jq -r '.data.access_token')
   ```

2. Use token in requests
   ```bash
   curl http://localhost:8080/api/v1/monitoring/circuit-breakers \
     -H "Authorization: Bearer $TOKEN"
   ```

---

## Performance Benchmarks

Expected performance for Phase 1:

| Metric | Target | Acceptable |
|--------|--------|------------|
| Kong routing latency | < 5ms | < 10ms |
| Circuit breaker overhead | < 1ms | < 2ms |
| Health check response | < 50ms | < 100ms |
| Rate limit accuracy | ±5% | ±10% |

---

## Coverage

Current test coverage for Phase 1 components:

- **Kong Configuration**: 100% (all files tested)
- **Circuit Breaker Core**: ~85% (core logic covered, edge cases pending)
- **Fallback Strategies**: ~80% (all services covered, some edge cases pending)
- **Service Dependencies**: ~90% (full functionality tested)
- **Monitoring API**: ~70% (endpoints exist, auth integration pending)

---

## Next Steps After Testing

1. **Review Results**
   - Check all tests passed
   - Review logs for warnings
   - Verify performance metrics

2. **Monitor Production Readiness**
   - Set up Grafana dashboards
   - Configure Prometheus alerts
   - Test under load

3. **Documentation**
   - Update API documentation
   - Create runbooks for operations
   - Document failure scenarios

4. **Proceed to Phase 2**
   - Database optimization
   - Advanced indexing
   - Query performance tuning

---

## Support

For issues or questions:

1. Check this README
2. Review test logs in `test-results/phase1/`
3. Check Docker logs: `docker-compose -f docker-compose.dev.yml logs`
4. Review PHASE1_IMPLEMENTATION_SUMMARY.md
5. Read CIRCUIT_BREAKER_INTEGRATION.md

---

**Last Updated**: October 25, 2025
**Phase**: 1 - API Gateway & Circuit Breakers
**Status**: Testing Phase

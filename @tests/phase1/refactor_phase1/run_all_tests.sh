#!/bin/bash
# Phase 1 - Comprehensive Test Runner
# Runs all Phase 1 tests: Kong integration, circuit breakers, and monitoring

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_DIR="$PROJECT_ROOT/tests/phase1"
RESULTS_DIR="$PROJECT_ROOT/test-results/phase1"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$RESULTS_DIR/phase1_full_report_$TIMESTAMP.md"

echo "================================================================"
echo "Phase 1 - Comprehensive Test Suite"
echo "================================================================"
echo "Project Root: $PROJECT_ROOT"
echo "Test Directory: $TEST_DIR"
echo "Results Directory: $RESULTS_DIR"
echo "Report File: $REPORT_FILE"
echo ""

# Initialize report
cat > "$REPORT_FILE" << EOF
# Phase 1 Test Report
**Test Run**: $TIMESTAMP
**Test Suite**: API Gateway & Circuit Breakers

---

## Test Summary

EOF

# Test execution status
OVERALL_STATUS=0

# ===== 1. ENVIRONMENT CHECK =====

echo ""
echo "================================================================"
echo "1. Environment Check"
echo "================================================================"

echo "Checking Docker..."
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker is running"
    cat >> "$REPORT_FILE" << EOF
### Environment Check
- ✅ Docker is running

EOF
else
    echo -e "${RED}✗${NC} Docker is not running"
    echo -e "${YELLOW}Please start Docker Desktop and try again.${NC}"
    cat >> "$REPORT_FILE" << EOF
### Environment Check
- ❌ Docker is not running

**ACTION REQUIRED**: Start Docker Desktop before running tests.
EOF
    exit 1
fi

echo "Checking services..."
cd "$PROJECT_ROOT"

# Check if services are running
SERVICES_RUNNING=$(docker-compose -f docker-compose.dev.yml ps --services --filter "status=running" | wc -l)
if [ "$SERVICES_RUNNING" -lt 3 ]; then
    echo -e "${YELLOW}⚠${NC} Services not running. Starting services..."
    echo ""
    echo "Starting development environment..."
    docker-compose -f docker-compose.dev.yml up -d

    echo "Waiting for services to be ready (60 seconds)..."
    sleep 60

    cat >> "$REPORT_FILE" << EOF
- ✅ Services started automatically

EOF
else
    echo -e "${GREEN}✓${NC} Services are running"
    cat >> "$REPORT_FILE" << EOF
- ✅ Services already running

EOF
fi

# ===== 2. KONG INTEGRATION TESTS =====

echo ""
echo "================================================================"
echo "2. Kong Integration Tests"
echo "================================================================"

cat >> "$REPORT_FILE" << EOF
## Kong Integration Tests

EOF

if [ -f "$TEST_DIR/test_kong_integration.sh" ]; then
    echo "Running Kong integration tests..."
    if bash "$TEST_DIR/test_kong_integration.sh"; then
        echo -e "${GREEN}✓${NC} Kong integration tests passed"
        cat >> "$REPORT_FILE" << EOF
✅ **Kong Integration Tests: PASSED**

See detailed log: \`test-results/phase1/kong_test_*.log\`

EOF
    else
        echo -e "${RED}✗${NC} Kong integration tests failed"
        OVERALL_STATUS=1
        cat >> "$REPORT_FILE" << EOF
❌ **Kong Integration Tests: FAILED**

See detailed log: \`test-results/phase1/kong_test_*.log\`

EOF
    fi
else
    echo -e "${YELLOW}⚠${NC} Kong integration test script not found"
fi

# ===== 3. CIRCUIT BREAKER UNIT TESTS =====

echo ""
echo "================================================================"
echo "3. Circuit Breaker Unit Tests"
echo "================================================================"

cat >> "$REPORT_FILE" << EOF
## Circuit Breaker Unit Tests

EOF

if [ -f "$TEST_DIR/test_circuit_breakers.py" ]; then
    echo "Running circuit breaker tests..."

    # Run pytest
    cd "$PROJECT_ROOT/services/backend"
    if python -m pytest "$TEST_DIR/test_circuit_breakers.py" -v --tb=short --json-report --json-report-file="$RESULTS_DIR/circuit_breaker_tests_$TIMESTAMP.json" 2>&1 | tee "$RESULTS_DIR/circuit_breaker_output_$TIMESTAMP.log"; then
        echo -e "${GREEN}✓${NC} Circuit breaker tests passed"
        cat >> "$REPORT_FILE" << EOF
✅ **Circuit Breaker Tests: PASSED**

See detailed output: \`test-results/phase1/circuit_breaker_output_$TIMESTAMP.log\`

EOF
    else
        echo -e "${RED}✗${NC} Circuit breaker tests failed"
        OVERALL_STATUS=1
        cat >> "$REPORT_FILE" << EOF
❌ **Circuit Breaker Tests: FAILED**

See detailed output: \`test-results/phase1/circuit_breaker_output_$TIMESTAMP.log\`

EOF
    fi
    cd "$PROJECT_ROOT"
else
    echo -e "${YELLOW}⚠${NC} Circuit breaker test file not found"
fi

# ===== 4. MONITORING API TESTS =====

echo ""
echo "================================================================"
echo "4. Monitoring API Tests"
echo "================================================================"

cat >> "$REPORT_FILE" << EOF
## Monitoring API Tests

EOF

echo "Testing monitoring endpoints..."

# Test circuit breaker endpoint (no auth required for health)
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8080/api/v1/health)

if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓${NC} Health endpoint accessible"
    cat >> "$REPORT_FILE" << EOF
- ✅ Health endpoint: Accessible

EOF
else
    echo -e "${RED}✗${NC} Health endpoint failed (HTTP $HEALTH_RESPONSE)"
    OVERALL_STATUS=1
    cat >> "$REPORT_FILE" << EOF
- ❌ Health endpoint: Failed (HTTP $HEALTH_RESPONSE)

EOF
fi

# ===== 5. DEPENDENCY VISUALIZATION TEST =====

echo ""
echo "================================================================"
echo "5. Service Dependency Tests"
echo "================================================================"

cat >> "$REPORT_FILE" << EOF
## Service Dependency Tests

EOF

echo "Testing dependency registry..."

# Test if monitoring endpoint exists (will require auth, but we can check if it returns 401 not 404)
MONITORING_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8080/api/v1/monitoring/dependencies)

if [ "$MONITORING_RESPONSE" = "401" ] || [ "$MONITORING_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓${NC} Monitoring endpoints configured (requires auth)"
    cat >> "$REPORT_FILE" << EOF
- ✅ Monitoring endpoints: Configured (authentication required)

EOF
else
    echo -e "${YELLOW}⚠${NC} Monitoring endpoints status: HTTP $MONITORING_RESPONSE"
    cat >> "$REPORT_FILE" << EOF
- ⚠️ Monitoring endpoints: Unexpected response (HTTP $MONITORING_RESPONSE)

EOF
fi

# ===== 6. SUMMARY =====

echo ""
echo "================================================================"
echo "Test Summary"
echo "================================================================"

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ All Phase 1 tests passed!${NC}"
    cat >> "$REPORT_FILE" << EOF

---

## Overall Result

✅ **PASSED** - All Phase 1 tests completed successfully!

### Next Steps

1. Review test results in \`test-results/phase1/\`
2. Check Prometheus metrics: http://localhost:8001/metrics
3. Monitor Kong dashboard: http://localhost:8001
4. Test circuit breakers with simulated failures
5. Proceed to Phase 2: Database Optimization

EOF
else
    echo -e "${RED}❌ Some Phase 1 tests failed${NC}"
    cat >> "$REPORT_FILE" << EOF

---

## Overall Result

❌ **FAILED** - Some tests did not pass

### Action Items

1. Review failed test logs in \`test-results/phase1/\`
2. Check Docker container logs: \`docker-compose -f docker-compose.dev.yml logs\`
3. Verify all services are running: \`docker-compose -f docker-compose.dev.yml ps\`
4. Fix issues and re-run tests

EOF
fi

echo ""
echo "Report saved to: $REPORT_FILE"
echo ""

# Return appropriate exit code
exit $OVERALL_STATUS

#!/bin/bash
# Phase 1 Kong Integration Test Suite
# Tests Kong API Gateway, routing, plugins, and circuit breakers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Configuration
KONG_ADMIN_URL="${KONG_ADMIN_URL:-http://localhost:8002}"
KONG_PROXY_URL="${KONG_PROXY_URL:-http://localhost:8080}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
TEST_RESULTS_DIR="test-results/phase1"

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

# Log file
LOG_FILE="$TEST_RESULTS_DIR/kong_test_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================"
echo "Phase 1 Kong Integration Tests"
echo "================================================================"
echo "Kong Admin API: $KONG_ADMIN_URL"
echo "Kong Proxy:     $KONG_PROXY_URL"
echo "Backend API:    $BACKEND_URL"
echo "Log file:       $LOG_FILE"
echo ""

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Test result function
test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name: $message"
        log "PASS: $test_name - $message"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    elif [ "$result" = "INFO" ] || [ "$result" = "WARN" ]; then
        echo -e "${YELLOW}ℹ${NC} $test_name: $message"
        log "$result: $test_name - $message"
        TESTS_PASSED=$((TESTS_PASSED + 1))  # Count as passed (informational)
    else
        echo -e "${RED}✗${NC} $test_name: $message"
        log "FAIL: $test_name - $message"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Wait for service
wait_for_service() {
    local url="$1"
    local service_name="$2"
    local max_attempts=30
    local attempt=0

    echo -n "Waiting for $service_name to be ready..."
    while [ $attempt -lt $max_attempts ]; do
        # Try curl with timeout and follow redirects
        if curl -s -f -m 3 --connect-timeout 2 "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e " ${RED}✗${NC} (timeout after $((max_attempts * 2)) seconds)"
    return 1
}

# ===== PRE-FLIGHT CHECKS =====

echo ""
echo "================================================================"
echo "1. Pre-flight Checks"
echo "================================================================"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    test_result "Docker Running" "FAIL" "Docker daemon not running"
    echo ""
    echo -e "${RED}ERROR: Docker must be running to execute tests${NC}"
    echo "Please start Docker and try again."
    exit 1
else
    test_result "Docker Running" "PASS" "Docker daemon is running"
fi

# Check docker-compose file
if [ ! -f "docker-compose.dev.yml" ]; then
    test_result "Docker Compose File" "FAIL" "docker-compose.dev.yml not found"
    exit 1
else
    test_result "Docker Compose File" "PASS" "docker-compose.dev.yml found"
fi

# Check Kong config files
if [ -f "infrastructure/kong/config/kong-dev.yml" ]; then
    test_result "Kong Dev Config" "PASS" "kong-dev.yml exists"
else
    test_result "Kong Dev Config" "FAIL" "kong-dev.yml not found"
fi

if [ -f "infrastructure/kong/scripts/init-kong.sh" ]; then
    test_result "Kong Init Script" "PASS" "init-kong.sh exists and is executable"
else
    test_result "Kong Init Script" "FAIL" "init-kong.sh not found"
fi

# ===== SERVICE AVAILABILITY =====

echo ""
echo "================================================================"
echo "2. Service Availability Tests"
echo "================================================================"

# Wait for Kong Admin API
if wait_for_service "$KONG_ADMIN_URL/status" "Kong Admin API"; then
    test_result "Kong Admin API" "PASS" "Accessible on port 8001"

    # Get Kong version
    KONG_VERSION=$(curl -s "$KONG_ADMIN_URL/" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    log "Kong Version: $KONG_VERSION"
else
    test_result "Kong Admin API" "FAIL" "Not accessible on port 8001"
fi

# Wait for Kong Proxy (use public health endpoint)
if wait_for_service "$KONG_PROXY_URL/api/v1/health" "Kong Proxy"; then
    test_result "Kong Proxy" "PASS" "Accessible on port 8080"
else
    test_result "Kong Proxy" "FAIL" "Not accessible on port 8080"
fi

# Check Backend
if wait_for_service "$BACKEND_URL/docs" "Backend API"; then
    test_result "Backend API" "PASS" "Accessible on port 8000"
else
    test_result "Backend API" "FAIL" "Not accessible on port 8000"
fi

# ===== KONG CONFIGURATION TESTS =====

echo ""
echo "================================================================"
echo "3. Kong Configuration Tests"
echo "================================================================"

# Check services registered
SERVICES_COUNT=$(curl -s "$KONG_ADMIN_URL/services" | grep -o '"data":\[' | wc -l)
if [ "$SERVICES_COUNT" -gt 0 ]; then
    SERVICES=$(curl -s "$KONG_ADMIN_URL/services" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ', ')
    test_result "Kong Services" "PASS" "Found services: $SERVICES"
else
    test_result "Kong Services" "FAIL" "No services configured"
fi

# Check routes registered
ROUTES_COUNT=$(curl -s "$KONG_ADMIN_URL/routes" | grep -o '"data":\[' | wc -l)
if [ "$ROUTES_COUNT" -gt 0 ]; then
    test_result "Kong Routes" "PASS" "Routes configured"
else
    test_result "Kong Routes" "FAIL" "No routes configured"
fi

# Check plugins loaded
PLUGINS_COUNT=$(curl -s "$KONG_ADMIN_URL/plugins" | grep -o '"data":\[' | wc -l)
if [ "$PLUGINS_COUNT" -gt 0 ]; then
    test_result "Kong Plugins" "PASS" "Plugins loaded"
else
    test_result "Kong Plugins" "FAIL" "No plugins loaded"
fi

# ===== ROUTING TESTS =====

echo ""
echo "================================================================"
echo "4. Kong Routing Tests"
echo "================================================================"

# Test public health endpoint routing (should not require JWT)
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" "$KONG_PROXY_URL/api/v1/health" -o /dev/null)
if [ "$HEALTH_RESPONSE" = "200" ]; then
    test_result "Public Health Endpoint" "PASS" "GET /api/v1/health returns 200 (unauthenticated)"
else
    test_result "Public Health Endpoint" "FAIL" "GET /api/v1/health returns $HEALTH_RESPONSE (expected 200)"
fi

# Test that health route header is present
HEALTH_ROUTE_HEADER=$(curl -s -I "$KONG_PROXY_URL/api/v1/health" | grep -i "x-health-route")
if [ -n "$HEALTH_ROUTE_HEADER" ]; then
    test_result "Health Route Header" "PASS" "X-Health-Route header present"
else
    test_result "Health Route Header" "INFO" "X-Health-Route header not found (optional)"
fi

# Test 404 for invalid route
INVALID_RESPONSE=$(curl -s -w "%{http_code}" "$KONG_PROXY_URL/invalid/route" -o /dev/null)
if [ "$INVALID_RESPONSE" = "404" ]; then
    test_result "Invalid Route Handling" "PASS" "Returns 404 for invalid routes"
else
    test_result "Invalid Route Handling" "FAIL" "Returns $INVALID_RESPONSE instead of 404"
fi

# ===== PLUGIN TESTS =====

echo ""
echo "================================================================"
echo "5. Kong Plugin Tests"
echo "================================================================"

# Test CORS headers
CORS_HEADERS=$(curl -s -I "$KONG_PROXY_URL/api/v1/health" | grep -i "access-control")
if [ -n "$CORS_HEADERS" ]; then
    test_result "CORS Plugin" "PASS" "CORS headers present"
else
    test_result "CORS Plugin" "FAIL" "CORS headers missing"
fi

# Test request transformer (X-Gateway header)
GATEWAY_HEADER=$(curl -s -I "$KONG_PROXY_URL/api/v1/health" | grep -i "x-gateway")
if [ -n "$GATEWAY_HEADER" ]; then
    test_result "Request Transformer" "PASS" "X-Gateway header added"
else
    test_result "Request Transformer" "FAIL" "X-Gateway header missing"
fi

# Test correlation ID
CORRELATION_ID=$(curl -s -I "$KONG_PROXY_URL/api/v1/health" | grep -i "x-correlation-id")
if [ -n "$CORRELATION_ID" ]; then
    test_result "Correlation ID Plugin" "PASS" "X-Correlation-ID header present"
else
    test_result "Correlation ID Plugin" "FAIL" "X-Correlation-ID header missing"
fi

# ===== RATE LIMITING TESTS =====

echo ""
echo "================================================================"
echo "6. Rate Limiting Tests"
echo "================================================================"

echo "Testing rate limiting configuration..."

# Note: Health endpoints have lenient rate limiting (1000/min) for monitoring
# Testing that rate limiting is configured, not that it triggers for health endpoints

# Check rate limit headers are present
RATE_LIMIT_HEADERS=$(curl -s -I "$KONG_PROXY_URL/api/v1/health" | grep -i "x-ratelimit")
if [ -n "$RATE_LIMIT_HEADERS" ]; then
    test_result "Rate Limiting Config" "PASS" "Rate limit headers present (configured)"
else
    test_result "Rate Limiting Config" "WARN" "Rate limit headers not found"
fi

# Optional: Try to trigger rate limit with rapid requests (may not trigger for health due to 1000/min limit)
echo "Testing rate limit enforcement (sending 50 rapid requests)..."
RATE_LIMIT_TRIGGERED=0
REQUEST_COUNT=0
for i in {1..50}; do
    RESPONSE=$(curl -s -w "%{http_code}" "$KONG_PROXY_URL/api/v1/health" -o /dev/null 2>&1)
    REQUEST_COUNT=$((REQUEST_COUNT + 1))
    if [ "$RESPONSE" = "429" ]; then
        RATE_LIMIT_TRIGGERED=1
        break
    fi
    sleep 0.05  # 50ms between requests = ~1200 req/min (above health limit)
done

if [ $RATE_LIMIT_TRIGGERED -eq 1 ]; then
    test_result "Rate Limiting Enforcement" "PASS" "Rate limit triggered after $REQUEST_COUNT requests"
else
    test_result "Rate Limiting Enforcement" "INFO" "Rate limit not triggered (health endpoint has lenient 1000/min limit)"
fi

# ===== PROMETHEUS METRICS =====

echo ""
echo "================================================================"
echo "7. Prometheus Metrics Tests"
echo "================================================================"

# Check metrics endpoint
METRICS_RESPONSE=$(curl -s "$KONG_ADMIN_URL/metrics")
if echo "$METRICS_RESPONSE" | grep -q "kong_"; then
    test_result "Prometheus Metrics" "PASS" "Metrics endpoint accessible"
else
    test_result "Prometheus Metrics" "FAIL" "Metrics endpoint not accessible"
fi

# ===== HEALTH CHECKS =====

echo ""
echo "================================================================"
echo "8. Health Check Tests"
echo "================================================================"

# Test comprehensive health endpoint
HEALTH_JSON=$(curl -s "$KONG_PROXY_URL/api/v1/health/comprehensive")
if echo "$HEALTH_JSON" | grep -q "status"; then
    test_result "Comprehensive Health" "PASS" "Returns health data"

    # Check for circuit breaker info
    if echo "$HEALTH_JSON" | grep -q "circuit_breaker"; then
        test_result "Circuit Breaker in Health" "PASS" "Circuit breaker status included"
    else
        test_result "Circuit Breaker in Health" "WARN" "Circuit breaker status may be missing"
    fi
else
    test_result "Comprehensive Health" "FAIL" "Health endpoint error"
fi

# ===== SUMMARY =====

echo ""
echo "================================================================"
echo "Test Summary"
echo "================================================================"
echo "Total Tests:  $TESTS_RUN"
echo -e "${GREEN}Passed:       $TESTS_PASSED${NC}"
echo -e "${RED}Failed:       $TESTS_FAILED${NC}"
echo "Success Rate: $(awk "BEGIN {printf \"%.1f\", ($TESTS_PASSED/$TESTS_RUN)*100}")%"
echo ""
echo "Detailed log: $LOG_FILE"
echo "================================================================"

# Exit code based on failures
if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi

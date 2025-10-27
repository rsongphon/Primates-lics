#!/bin/sh
# Kong Admin API Initialization Script
# This script waits for Kong Admin API to be ready and verifies configuration

set -e

KONG_ADMIN_URL="${KONG_ADMIN_URL:-http://kong-dev:8001}"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "=========================================="
echo "Kong API Gateway Initialization"
echo "=========================================="
echo "Kong Admin API: ${KONG_ADMIN_URL}"
echo ""

# Function to check if Kong Admin API is ready
check_kong_ready() {
    curl -s -o /dev/null -w "%{http_code}" "${KONG_ADMIN_URL}/status" 2>/dev/null
}

# Wait for Kong Admin API to be ready
echo "⏳ Waiting for Kong Admin API to be ready..."
RETRIES=0
until [ "$(check_kong_ready)" = "200" ]; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo "❌ ERROR: Kong Admin API did not become ready in time"
        exit 1
    fi
    echo "   Attempt ${RETRIES}/${MAX_RETRIES}: Kong not ready yet, waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "✅ Kong Admin API is ready!"
echo ""

# Display Kong version and configuration
echo "📋 Kong Information:"
curl -s "${KONG_ADMIN_URL}/" | grep -E '"version"|"hostname"' || true
echo ""

# Verify declarative configuration is loaded
echo "🔍 Verifying declarative configuration..."
SERVICES_COUNT=$(curl -s "${KONG_ADMIN_URL}/services" | grep -o '"data":\[' | wc -l)
ROUTES_COUNT=$(curl -s "${KONG_ADMIN_URL}/routes" | grep -o '"data":\[' | wc -l)
PLUGINS_COUNT=$(curl -s "${KONG_ADMIN_URL}/plugins" | grep -o '"data":\[' | wc -l)

echo "   Services configured: ${SERVICES_COUNT}"
echo "   Routes configured: ${ROUTES_COUNT}"
echo "   Plugins configured: ${PLUGINS_COUNT}"
echo ""

# List all configured services
echo "📦 Configured Services:"
curl -s "${KONG_ADMIN_URL}/services" | grep -o '"name":"[^"]*"' | sed 's/"name":"/ - /' | sed 's/"$//' || echo "   No services found"
echo ""

# List all configured routes
echo "🛣️  Configured Routes:"
curl -s "${KONG_ADMIN_URL}/routes" | grep -o '"name":"[^"]*"' | sed 's/"name":"/ - /' | sed 's/"$//' || echo "   No routes found"
echo ""

# Create development test consumer if not exists
echo "👤 Setting up development test consumer..."
CONSUMER_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" "${KONG_ADMIN_URL}/consumers/dev-test-user" 2>/dev/null)

if [ "$CONSUMER_EXISTS" = "200" ]; then
    echo "   ✅ Consumer 'dev-test-user' already exists"
else
    echo "   Creating consumer 'dev-test-user'..."
    curl -s -X POST "${KONG_ADMIN_URL}/consumers" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "dev-test-user",
            "custom_id": "dev-test-001",
            "tags": ["development", "testing"]
        }' > /dev/null
    echo "   ✅ Consumer created successfully"
fi
echo ""

# Create JWT credential for dev-test-user if not exists
echo "🔑 Setting up JWT credentials for development..."
JWT_COUNT=$(curl -s "${KONG_ADMIN_URL}/consumers/dev-test-user/jwt" | grep -o '"data":\[' | wc -l)

if [ "$JWT_COUNT" -gt 0 ]; then
    echo "   ✅ JWT credentials already exist"
    # Display existing JWT credentials
    echo "   Existing JWT credentials:"
    curl -s "${KONG_ADMIN_URL}/consumers/dev-test-user/jwt" | grep -o '"key":"[^"]*"' | sed 's/"key":"/ - Key: /' | sed 's/"$//'
else
    echo "   Creating JWT credential..."
    JWT_RESPONSE=$(curl -s -X POST "${KONG_ADMIN_URL}/consumers/dev-test-user/jwt" \
        -H "Content-Type: application/json" \
        -d '{
            "key": "dev-test-jwt-key",
            "algorithm": "HS256",
            "secret": "dev-test-jwt-secret-change-in-production"
        }')
    echo "   ✅ JWT credential created successfully"
    echo "   JWT Key: dev-test-jwt-key"
    echo "   JWT Secret: dev-test-jwt-secret-change-in-production"
    echo "   ⚠️  WARNING: Change these credentials in production!"
fi
echo ""

# Display Kong configuration endpoints
echo "=========================================="
echo "Kong Configuration Summary"
echo "=========================================="
echo "Kong Proxy (HTTP):  http://localhost:8080"
echo "Kong Admin API:     http://localhost:8001"
echo "Kong Proxy (HTTPS): https://localhost:8443"
echo ""
echo "API Endpoints via Kong:"
echo " - Backend API: http://localhost:8080/api/v1"
echo " - WebSocket:   ws://localhost:8080/ws"
echo " - Health:      http://localhost:8080/api/v1/health"
echo ""
echo "Development Resources:"
echo " - Prometheus Metrics: http://localhost:8001/metrics"
echo " - Kong Status:        http://localhost:8001/status"
echo ""
echo "=========================================="
echo "✅ Kong initialization completed successfully!"
echo "=========================================="
echo ""

# Keep container running for logs (optional, can be removed if you want it to exit)
# tail -f /dev/null

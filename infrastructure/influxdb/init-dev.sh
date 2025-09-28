#!/bin/bash

# LICS InfluxDB Development Initialization Script
# This script sets up InfluxDB buckets and retention policies for development

set -e

echo "🔧 Initializing LICS InfluxDB for development..."

# Wait for InfluxDB to be ready
echo "⏳ Waiting for InfluxDB to be ready..."
until influx ping > /dev/null 2>&1; do
  sleep 2
done

echo "✅ InfluxDB is ready"

# Set environment variables for influx CLI
export INFLUX_TOKEN=${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}
export INFLUX_ORG=${DOCKER_INFLUXDB_INIT_ORG}
export INFLUX_HOST="http://localhost:8086"

echo "📦 Creating development buckets and retention policies..."

# Create additional buckets for different data types (shorter retention for dev)
influx bucket create --name system-metrics-dev --retention 24h --description "System performance metrics (dev)" || echo "Bucket 'system-metrics-dev' already exists"
influx bucket create --name device-logs-dev --retention 2d --description "Device log data (dev)" || echo "Bucket 'device-logs-dev' already exists"
influx bucket create --name experiment-data-dev --retention 7d --description "Experiment telemetry data (dev)" || echo "Bucket 'experiment-data-dev' already exists"
influx bucket create --name video-analytics-dev --retention 1d --description "Video analysis metadata (dev)" || echo "Bucket 'video-analytics-dev' already exists"
influx bucket create --name test-data --retention 1h --description "Test data for development" || echo "Bucket 'test-data' already exists"

echo "🔑 Creating development tokens..."
# Create tokens for different services in development
influx auth create \
  --org ${DOCKER_INFLUXDB_INIT_ORG} \
  --description "Backend Service Token (Dev)" \
  --read-buckets \
  --write-buckets \
  --read-dashboards || echo "Backend token may already exist"

influx auth create \
  --org ${DOCKER_INFLUXDB_INIT_ORG} \
  --description "Edge Agent Token (Dev)" \
  --write-bucket ${DOCKER_INFLUXDB_INIT_BUCKET} \
  --write-bucket experiment-data-dev \
  --write-bucket system-metrics-dev || echo "Edge agent token may already exist"

echo "📊 Generating sample data for development..."

# Generate some sample telemetry data for testing
cat << 'EOF' | influx write --bucket ${DOCKER_INFLUXDB_INIT_BUCKET} --precision s
device_telemetry,device_id=dev-rpi-001,metric=temperature value=23.5 $(date +%s)
device_telemetry,device_id=dev-rpi-001,metric=humidity value=45.2 $(date +%s)
device_telemetry,device_id=dev-rpi-002,metric=temperature value=24.1 $(date +%s)
device_telemetry,device_id=dev-rpi-002,metric=humidity value=43.8 $(date +%s)
system_health,service=backend,host=localhost cpu_usage=15.5,memory_usage=512 $(date +%s)
system_health,service=redis,host=localhost cpu_usage=5.2,memory_usage=128 $(date +%s)
EOF

echo "📈 Sample data inserted"

echo "🎯 Creating development monitoring tasks..."

# Create a simple development monitoring task
cat << 'EOF' | influx task create
option task = {name: "dev-health-check", every: 1m}

from(bucket: "system-metrics-dev")
  |> range(start: -1m)
  |> filter(fn: (r) => r._measurement == "health")
  |> count()
  |> map(fn: (r) => ({r with _value: if r._value > 0 then "healthy" else "needs_attention"}))
  |> to(bucket: "system-metrics-dev")
EOF

echo "🧹 Creating aggressive cleanup for development..."

# More aggressive cleanup for development
cat << 'EOF' | influx task create
option task = {name: "dev-cleanup", every: 1h}

from(bucket: "test-data")
  |> range(start: -2h, stop: -1h)
  |> drop()
EOF

echo "🚀 InfluxDB development initialization completed!"
echo "📋 Development Summary:"
echo "   - Organization: ${DOCKER_INFLUXDB_INIT_ORG}"
echo "   - Main bucket: ${DOCKER_INFLUXDB_INIT_BUCKET} (retention: ${DOCKER_INFLUXDB_INIT_RETENTION})"
echo "   - System metrics: system-metrics-dev (retention: 24h)"
echo "   - Device logs: device-logs-dev (retention: 2d)"
echo "   - Experiment data: experiment-data-dev (retention: 7d)"
echo "   - Video analytics: video-analytics-dev (retention: 1d)"
echo "   - Test data: test-data (retention: 1h)"
echo "   - Sample telemetry data: generated"
echo "   - Development tokens: created"
echo "   - Aggressive cleanup: enabled"
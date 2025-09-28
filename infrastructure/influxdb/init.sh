#!/bin/bash

# LICS InfluxDB Production Initialization Script
# This script sets up InfluxDB buckets and retention policies for production

set -e

echo "🔧 Initializing LICS InfluxDB for production..."

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

echo "📦 Creating additional buckets and retention policies..."

# Create additional buckets for different data types
influx bucket create --name system-metrics --retention 7d --description "System performance metrics" || echo "Bucket 'system-metrics' already exists"
influx bucket create --name device-logs --retention 30d --description "Device log data" || echo "Bucket 'device-logs' already exists"
influx bucket create --name experiment-data --retention 90d --description "Experiment telemetry data" || echo "Bucket 'experiment-data' already exists"
influx bucket create --name video-analytics --retention 14d --description "Video analysis metadata" || echo "Bucket 'video-analytics' already exists"

echo "🔑 Creating read-only token for Grafana..."
# Create a read-only token for Grafana
influx auth create \
  --org ${DOCKER_INFLUXDB_INIT_ORG} \
  --description "Grafana Read-Only Token" \
  --read-buckets \
  --read-dashboards \
  --read-tasks \
  --read-telegrafs \
  --read-users \
  --read-variables \
  --read-scrapers \
  --read-secrets \
  --read-labels \
  --read-views \
  --read-documents || echo "Grafana token may already exist"

echo "📊 Creating tasks for data downsampling..."

# Create a task for downsampling telemetry data
cat << 'EOF' | influx task create
option task = {name: "downsample-telemetry", every: 1h}

from(bucket: "telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "device_telemetry")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> to(bucket: "telemetry-1m", org: "${DOCKER_INFLUXDB_INIT_ORG}")
EOF

echo "📝 Creating retention policies..."

# The main buckets already have retention policies set via environment variables
# Additional cleanup task for old data
cat << 'EOF' | influx task create
option task = {name: "cleanup-old-logs", every: 24h}

from(bucket: "device-logs")
  |> range(start: -31d, stop: -30d)
  |> drop()
EOF

echo "🎯 Setting up monitoring checks..."

# Create a simple monitoring task
cat << 'EOF' | influx task create
option task = {name: "health-check", every: 5m}

from(bucket: "system-metrics")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "health")
  |> count()
  |> map(fn: (r) => ({r with _value: if r._value > 0 then "healthy" else "unhealthy"}))
  |> to(bucket: "system-metrics")
EOF

echo "🚀 InfluxDB production initialization completed!"
echo "📋 Summary:"
echo "   - Organization: ${DOCKER_INFLUXDB_INIT_ORG}"
echo "   - Main bucket: ${DOCKER_INFLUXDB_INIT_BUCKET} (retention: ${DOCKER_INFLUXDB_INIT_RETENTION})"
echo "   - System metrics: system-metrics (retention: 7d)"
echo "   - Device logs: device-logs (retention: 30d)"
echo "   - Experiment data: experiment-data (retention: 90d)"
echo "   - Video analytics: video-analytics (retention: 14d)"
echo "   - Downsampling tasks: enabled"
echo "   - Health monitoring: enabled"
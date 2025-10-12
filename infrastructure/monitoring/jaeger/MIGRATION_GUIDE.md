# Jaeger v1 to v2 Migration Guide

## Overview
This document describes the migration from Jaeger v1 to Jaeger v2 completed for the LICS project.

## What Changed

### Jaeger Version Upgrade
- **Before**: `jaegertracing/all-in-one:latest` (Jaeger v1, Docker Hub)
- **After**: `cr.jaegertracing.io/jaegertracing/jaeger:2.11.0` (Jaeger v2)

**Note**: Jaeger v2 uses a different container registry (`cr.jaegertracing.io`) instead of Docker Hub.

**Available v2 Versions**: v2.2.0 through v2.11.0 (as of October 2025)
- To use latest stable: `cr.jaegertracing.io/jaegertracing/jaeger:2.11.0`
- To track a major version: Use specific tags like `2.11.0`, `2.10.0`, etc.
- To pull the image: `docker pull cr.jaegertracing.io/jaegertracing/jaeger:2.11.0`

### Architecture Changes
Jaeger v2 is a complete rewrite built on top of the OpenTelemetry Collector framework:
- Single unified binary instead of multiple binaries (agent, collector, query, ingester)
- YAML-based configuration (v1 used environment variables)
- Native OTLP support (OpenTelemetry Protocol)
- Better performance and resource usage

## Why Migrate?
- **End-of-Life**: Jaeger v1 reaches end-of-life on December 31, 2025
- **Better Integration**: Native OpenTelemetry support
- **Simplified Architecture**: One binary with one config file
- **Improved Performance**: Built on proven OTel Collector framework
- **Future-Proof**: OpenTelemetry is the future of observability

## Configuration Files

### Development
- **Config**: `infrastructure/monitoring/jaeger/jaeger-v2-dev-config.yml`
- **Features**:
  - Memory storage with 100,000 trace limit
  - Debug logging for development
  - CORS enabled for local development
  - All legacy protocols enabled for compatibility

### Production
- **Config**: `infrastructure/monitoring/jaeger/jaeger-v2-config.yml`
- **Features**:
  - Memory storage with 500,000 trace limit
  - Info-level logging
  - JSON log format
  - Optimized batch processing

### Storage Options
Currently using memory storage. For production scale, consider:
- **Badger**: Local disk storage (good for small-medium scale)
- **Cassandra**: Distributed storage (high scale)
- **Elasticsearch**: Full-text search capabilities
- **PostgreSQL**: Relational storage option

## Docker Compose Changes

### Ports Exposed
All endpoints are now available:
- **16686**: Jaeger UI (web interface)
- **4317**: OTLP gRPC (v2 native protocol)
- **4318**: OTLP HTTP (v2 native protocol)
- **14268**: Jaeger HTTP collector (legacy)
- **14250**: Jaeger gRPC collector (legacy)
- **6831/udp**: Jaeger thrift compact (legacy)
- **6832/udp**: Jaeger thrift binary (legacy)
- **9411**: Zipkin compatibility
- **13133**: Health check endpoint

### Health Check
New health check using native endpoint:
```yaml
healthcheck:
  test: ["CMD", "wget", "--spider", "-q", "http://localhost:13133"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

## OpenTelemetry Collector Changes

### Updated Configuration
The OTel Collector now uses **OTLP exclusively** for sending traces to Jaeger v2:
- **Removed**: Legacy Jaeger exporter (port 14250)
- **Added**: OTLP exporter as primary (port 4317)
- **Benefit**: Native protocol support, better performance

### Configuration Location
- `infrastructure/monitoring/otel/otel-collector-config.yml`

## Testing the Migration

### 1. Stop Existing Services
```bash
docker-compose -f docker-compose.dev.yml down
```

### 2. Remove Old Jaeger Data (optional)
```bash
docker volume rm lics_jaeger_data
```

### 3. Start Services
```bash
make dev
# or
docker-compose -f docker-compose.dev.yml up -d
```

### 4. Verify Jaeger UI
Open http://localhost:16686 in your browser

### 5. Check Health
```bash
curl http://localhost:13133
```

### 6. Test Trace Collection
If you have instrumented services, they should automatically send traces to the new Jaeger v2 instance via the OpenTelemetry Collector.

## Backward Compatibility

All legacy Jaeger protocols are still supported:
- Jaeger Thrift (compact and binary)
- Jaeger gRPC (port 14250)
- Jaeger HTTP (port 14268)
- Zipkin format (port 9411)

This ensures existing instrumentation continues to work during migration.

## Next Steps (Optional)

### 1. Add Backend Tracing
Instrument the FastAPI backend with OpenTelemetry:
```python
# Add to requirements.txt
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-fastapi>=0.41b0
opentelemetry-exporter-otlp-proto-grpc>=1.20.0
```

### 2. Configure Persistent Storage
Update configuration files to use Badger, Cassandra, or Elasticsearch for production.

### 3. Add Sampling Strategies
Configure adaptive sampling to reduce trace volume in production.

### 4. Set Up Alerts
Create alerts for trace latency, error rates, and service health.

## Rollback Plan

If issues occur, rollback is simple:

1. **Revert docker-compose files**:
   ```bash
   git checkout HEAD -- docker-compose.dev.yml docker-compose.yml
   ```

2. **Revert OTel Collector config**:
   ```bash
   git checkout HEAD -- infrastructure/monitoring/otel/otel-collector-config.yml
   ```

3. **Restart services**:
   ```bash
   docker-compose -f docker-compose.dev.yml down
   docker-compose -f docker-compose.dev.yml up -d
   ```

## Resources

- [Jaeger v2 Documentation](https://www.jaegertracing.io/docs/next-release-v2/)
- [Migration Guide (Official)](https://www.jaegertracing.io/docs/next-release-v2/migration/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger v2 Configuration Reference](https://www.jaegertracing.io/docs/next-release-v2/configuration/)

## Support

For issues or questions:
- Check Jaeger logs: `docker-compose -f docker-compose.dev.yml logs -f jaeger`
- Check OTel Collector logs: `docker-compose -f docker-compose.yml logs -f otel-collector`
- Review configuration files in `infrastructure/monitoring/jaeger/`

## Migration Completed
- ✅ Jaeger v2 configuration files created
- ✅ Docker Compose files updated (dev and production)
- ✅ OpenTelemetry Collector optimized for v2
- ✅ Documentation updated
- ✅ Health checks configured
- ✅ Backward compatibility maintained

**Migration Date**: October 12, 2025
**Migrated By**: Songphon
**Jaeger Version**: v2.11.0 (released Oct 2, 2025)
**Docker Image**: `cr.jaegertracing.io/jaegertracing/jaeger:2.11.0`

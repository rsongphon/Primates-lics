#!/usr/bin/env python3
"""
LICS Unified Health Check Script

Comprehensive health monitoring for all LICS services.
This script can be run independently during Phase 1 before the backend is fully implemented.

Usage:
    python unified-health-check.py [--format json|text] [--services service1,service2]
"""

import argparse
import asyncio
import json
import time
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

import aiohttp
import asyncpg
import redis.asyncio as redis
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class UnifiedHealthChecker:
    """Comprehensive health checker for all LICS services."""

    def __init__(self):
        self.session = None
        self.results = []

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_database_services(self) -> List[Dict[str, Any]]:
        """Check all database services."""
        results = []

        # PostgreSQL check
        postgres_result = await self.check_postgresql()
        results.append(postgres_result)

        # Redis check
        redis_result = await self.check_redis()
        results.append(redis_result)

        return results

    async def check_postgresql(self) -> Dict[str, Any]:
        """Check PostgreSQL database health."""
        result = {
            "service": "PostgreSQL",
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors": []
        }

        start_time = time.time()
        try:
            conn = await asyncpg.connect(
                "postgresql://lics:lics123@localhost:5432/lics"
            )

            # Basic connectivity test
            version = await conn.fetchval("SELECT version()")

            # Check TimescaleDB extension
            timescaledb_query = """
                SELECT extname FROM pg_extension WHERE extname = 'timescaledb'
            """
            timescale_ext = await conn.fetchval(timescaledb_query)

            # Get connection stats
            connections = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity"
            )

            # Get database size
            db_size = await conn.fetchval(
                "SELECT pg_database_size('lics')"
            )

            # Check if there are any hypertables (TimescaleDB specific)
            hypertables_query = """
                SELECT count(*) FROM timescaledb_information.hypertables
            """
            try:
                hypertables_count = await conn.fetchval(hypertables_query)
            except:
                hypertables_count = 0

            await conn.close()

            result.update({
                "status": "healthy",
                "details": {
                    "version": version.split(' ')[0] + ' ' + version.split(' ')[1] if version else "unknown",
                    "timescaledb_enabled": bool(timescale_ext),
                    "active_connections": connections,
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / 1024 / 1024, 2) if db_size else 0,
                    "hypertables_count": hypertables_count
                }
            })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "errors": [str(e)]
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis cache health."""
        result = {
            "service": "Redis",
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors": []
        }

        start_time = time.time()
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)

            # Basic connectivity test
            pong = await r.ping()

            # Get Redis info
            info = await r.info()

            # Test basic operations
            await r.set("lics:health_check", "ok", ex=60)
            health_value = await r.get("lics:health_check")

            await r.aclose()

            result.update({
                "status": "healthy" if pong and health_value == "ok" else "unhealthy",
                "details": {
                    "version": info.get("redis_version"),
                    "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                    "memory_peak_mb": round(info.get("used_memory_peak", 0) / 1024 / 1024, 2),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses")
                }
            })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "errors": [str(e)]
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    async def check_http_service(self, service_name: str, url: str, expected_status: int = 200) -> Dict[str, Any]:
        """Check HTTP-based service health."""
        result = {
            "service": service_name,
            "status": "unknown",
            "response_time_ms": 0,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors": []
        }

        start_time = time.time()
        try:
            async with self.session.get(url) as response:
                response_text = await response.text()

                if response.status == expected_status:
                    result.update({
                        "status": "healthy",
                        "details": {
                            "url": url,
                            "status_code": response.status,
                            "response_size": len(response_text)
                        }
                    })
                else:
                    result.update({
                        "status": "unhealthy",
                        "details": {
                            "url": url,
                            "status_code": response.status,
                            "expected_status": expected_status
                        },
                        "errors": [f"Unexpected status code: {response.status}"]
                    })

        except Exception as e:
            result.update({
                "status": "unhealthy",
                "errors": [str(e)]
            })

        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        return result

    async def check_all_services(self, services_filter: List[str] = None) -> Dict[str, Any]:
        """Check all services health."""
        start_time = time.time()

        all_services = {
            "postgresql": self.check_postgresql,
            "redis": self.check_redis,
            "prometheus": lambda: self.check_http_service("Prometheus", "http://localhost:9090/-/healthy"),
            "grafana": lambda: self.check_http_service("Grafana", "http://localhost:3001/api/health"),
            "influxdb": lambda: self.check_http_service("InfluxDB", "http://localhost:8086/health"),
            "loki": lambda: self.check_http_service("Loki", "http://localhost:3100/ready"),
            "alertmanager": lambda: self.check_http_service("Alertmanager", "http://localhost:9093/-/healthy"),
            "jaeger": lambda: self.check_http_service("Jaeger", "http://localhost:16686/api/services"),
            "minio": lambda: self.check_http_service("MinIO", "http://localhost:9000/minio/health/live"),
        }

        # Filter services if specified
        if services_filter:
            all_services = {k: v for k, v in all_services.items() if k in services_filter}

        # Run all health checks concurrently
        tasks = []
        service_names = []

        for service_name, check_func in all_services.items():
            tasks.append(check_func())
            service_names.append(service_name)

        service_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        services = []
        healthy_count = 0
        total_count = len(service_results)

        for i, result in enumerate(service_results):
            if isinstance(result, Exception):
                services.append({
                    "service": service_names[i],
                    "status": "error",
                    "errors": [str(result)],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                services.append(result)
                if result["status"] == "healthy":
                    healthy_count += 1

        # Determine overall status
        if healthy_count == total_count:
            overall_status = "healthy"
        elif healthy_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_response_time_ms": int((time.time() - start_time) * 1000),
            "summary": {
                "total_services": total_count,
                "healthy_services": healthy_count,
                "unhealthy_services": total_count - healthy_count,
                "health_percentage": round((healthy_count / total_count) * 100, 1) if total_count > 0 else 0
            },
            "services": services,
            "system_info": {
                "lics_version": "1.0.0-alpha",
                "phase": "Phase 1 - Foundation Setup",
                "environment": "development"
            }
        }

    def format_text_output(self, results: Dict[str, Any]) -> str:
        """Format results as human-readable text."""
        output = []
        output.append("=" * 60)
        output.append("LICS System Health Check Report")
        output.append("=" * 60)
        output.append(f"Overall Status: {results['overall_status'].upper()}")
        output.append(f"Timestamp: {results['timestamp']}")
        output.append(f"Total Response Time: {results['total_response_time_ms']}ms")
        output.append("")

        # Summary
        summary = results['summary']
        output.append("Summary:")
        output.append(f"  Total Services: {summary['total_services']}")
        output.append(f"  Healthy: {summary['healthy_services']}")
        output.append(f"  Unhealthy: {summary['unhealthy_services']}")
        output.append(f"  Health Percentage: {summary['health_percentage']}%")
        output.append("")

        # Service details
        output.append("Service Details:")
        output.append("-" * 40)

        for service in results['services']:
            status_symbol = "✓" if service['status'] == 'healthy' else "✗"
            output.append(f"{status_symbol} {service['service']:<15} [{service['status'].upper()}] ({service.get('response_time_ms', 0)}ms)")

            if service.get('details'):
                for key, value in service['details'].items():
                    output.append(f"    {key}: {value}")

            if service.get('errors'):
                for error in service['errors']:
                    output.append(f"    ERROR: {error}")

            output.append("")

        output.append("=" * 60)
        return "\n".join(output)


async def main():
    parser = argparse.ArgumentParser(description='LICS Unified Health Check')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--services', type=str,
                       help='Comma-separated list of services to check')
    parser.add_argument('--output', type=str,
                       help='Output file path (default: stdout)')

    args = parser.parse_args()

    # Parse services filter
    services_filter = None
    if args.services:
        services_filter = [s.strip() for s in args.services.split(',')]

    try:
        async with UnifiedHealthChecker() as checker:
            results = await checker.check_all_services(services_filter)

            # Format output
            if args.format == 'json':
                output = json.dumps(results, indent=2)
            else:
                output = checker.format_text_output(results)

            # Write output
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output)
                print(f"Health check results written to: {args.output}")
            else:
                print(output)

            # Exit with appropriate code
            if results['overall_status'] == 'healthy':
                sys.exit(0)
            elif results['overall_status'] == 'degraded':
                sys.exit(1)
            else:
                sys.exit(2)

    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())
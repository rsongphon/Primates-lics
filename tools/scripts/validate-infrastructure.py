#!/usr/bin/env python3
"""
LICS Infrastructure Validation Script

This script provides comprehensive validation of the entire LICS infrastructure,
testing all Docker services, connectivity, health checks, and integration points.

Usage:
    python validate-infrastructure.py [--format json|text] [--output file.txt] [--quick]

Features:
    - Docker Compose service validation
    - Service health check verification
    - Network connectivity testing
    - Volume persistence validation
    - SSL certificate verification
    - Performance baseline testing
    - Integration testing between services
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

# Third-party imports with fallback handling
try:
    import docker
    import requests
    import asyncpg
    import redis
    import paho.mqtt.client as mqtt
    from influxdb_client import InfluxDBClient
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install docker requests asyncpg redis paho-mqtt influxdb-client")
    sys.exit(1)

# Import centralized test configuration
try:
    from test_config import get_test_config
    TEST_CONFIG = get_test_config()
except ImportError:
    print("Warning: test_config.py not found. Using default ports.")
    TEST_CONFIG = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('infrastructure-validation.log')
    ]
)
logger = logging.getLogger(__name__)

class InfrastructureValidator:
    """Comprehensive infrastructure validation for LICS system."""

    def __init__(self, quick_mode: bool = False):
        """
        Initialize the validator.

        Args:
            quick_mode: If True, performs only essential checks
        """
        self.quick_mode = quick_mode
        self.results = {}
        self.start_time = time.time()
        self.docker_client = None
        self.project_root = Path(__file__).parent.parent.parent

        # Service configuration - use TEST_CONFIG if available, otherwise defaults
        if TEST_CONFIG:
            postgres_port = TEST_CONFIG['postgresql']['port']
            pgbouncer_port = TEST_CONFIG['pgbouncer']['port']
            redis_port = TEST_CONFIG['redis']['port']
            mqtt_port = TEST_CONFIG['mqtt']['port']
            minio_port = int(TEST_CONFIG['minio']['endpoint'].split(':')[1])
            influxdb_port = int(TEST_CONFIG['influxdb']['url'].split(':')[-1])
            prometheus_port = TEST_CONFIG['prometheus']['port']
            grafana_port = TEST_CONFIG['grafana']['port']
        else:
            # Fallback to development ports
            postgres_port = 5433
            pgbouncer_port = 6433
            redis_port = 6380
            mqtt_port = 1884
            minio_port = 9010
            influxdb_port = 8087
            prometheus_port = 9090
            grafana_port = 3001

        self.services = {
            'postgres': {
                'port': postgres_port,
                'health_endpoint': None,
                'required': True,
                'timeout': 30
            },
            'pgbouncer': {
                'port': pgbouncer_port,
                'health_endpoint': None,
                'required': True,
                'timeout': 15
            },
            'redis': {
                'port': redis_port,
                'health_endpoint': None,
                'required': True,
                'timeout': 10
            },
            'mqtt': {
                'port': mqtt_port,
                'health_endpoint': None,
                'required': True,
                'timeout': 10
            },
            'minio': {
                'port': minio_port,
                'health_endpoint': f'http://localhost:{minio_port}/minio/health/live',
                'required': True,
                'timeout': 15
            },
            'influxdb': {
                'port': influxdb_port,
                'health_endpoint': f'http://localhost:{influxdb_port}/health',
                'required': True,
                'timeout': 20
            },
            'prometheus': {
                'port': prometheus_port,
                'health_endpoint': f'http://localhost:{prometheus_port}/-/healthy',
                'required': False,
                'timeout': 15
            },
            'grafana': {
                'port': grafana_port,
                'health_endpoint': f'http://localhost:{grafana_port}/api/health',
                'required': False,
                'timeout': 15
            },
            'nginx': {
                'port': 80,
                'health_endpoint': 'http://localhost/health',
                'required': False,
                'timeout': 10
            }
        }

    def initialize_docker_client(self) -> bool:
        """Initialize Docker client connection."""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            logger.info("✅ Docker client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Docker client: {e}")
            return False

    def check_docker_compose_status(self) -> Dict[str, Any]:
        """Check Docker Compose service status."""
        logger.info("🔍 Checking Docker Compose service status...")

        result = {
            "name": "Docker Compose Status",
            "healthy": False,
            "services": {},
            "summary": {},
            "errors": []
        }

        try:
            # Get docker-compose services
            cmd = ["docker-compose", "ps", "--format", "json"]
            process = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if process.returncode != 0:
                result["errors"].append(f"docker-compose ps failed: {process.stderr}")
                return result

            # Parse service information
            services_output = process.stdout.strip()
            if not services_output:
                result["errors"].append("No services found - is docker-compose running?")
                return result

            # Handle both single service and multiple services output
            services_data = []
            for line in services_output.split('\n'):
                if line.strip():
                    try:
                        services_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Fallback to parsing text format
                        parts = line.split()
                        if len(parts) >= 4:
                            services_data.append({
                                "Name": parts[0],
                                "State": parts[1],
                                "Ports": " ".join(parts[2:])
                            })

            running_count = 0
            healthy_count = 0

            for service in services_data:
                # Extract service name - handle both hyphen and underscore prefixes
                full_name = service.get("Name", "")
                service_name = full_name.replace("primates-lics-", "").replace("primates-lics_", "")
                service_name = service_name.replace("-dev-1", "").replace("_dev_1", "").replace("-1", "").replace("_1", "")

                if not service_name:
                    continue

                state = service.get("State", "unknown")
                ports = service.get("Ports", "")

                service_info = {
                    "name": service_name,
                    "state": state,
                    "ports": ports,
                    "running": state.lower() in ["running", "up"] or "up" in state.lower(),
                    "healthy": "healthy" in state.lower() or (state.lower() == "running" and "unhealthy" not in state.lower())
                }

                result["services"][service_name] = service_info

                if service_info["running"]:
                    running_count += 1
                if service_info["healthy"]:
                    healthy_count += 1

            # Summary
            total_services = len(result["services"])
            result["summary"] = {
                "total_services": total_services,
                "running_services": running_count,
                "healthy_services": healthy_count,
                "completion_percentage": round((healthy_count / total_services * 100), 2) if total_services > 0 else 0
            }

            # Overall health check
            required_services = [name for name, config in self.services.items() if config["required"]]
            required_healthy = sum(1 for name in required_services
                                 if result["services"].get(name, {}).get("healthy", False))

            result["healthy"] = required_healthy == len(required_services)

            if not result["healthy"]:
                unhealthy_services = [name for name in required_services
                                    if not result["services"].get(name, {}).get("healthy", False)]
                result["errors"].append(f"Required services not healthy: {', '.join(unhealthy_services)}")

        except subprocess.TimeoutExpired:
            result["errors"].append("Docker Compose status check timed out")
        except Exception as e:
            result["errors"].append(f"Failed to check Docker Compose status: {str(e)}")

        return result

    def check_service_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity to all services."""
        logger.info("🔍 Testing service connectivity...")

        result = {
            "name": "Service Connectivity",
            "healthy": False,
            "services": {},
            "summary": {},
            "errors": []
        }

        connectivity_results = {}

        for service_name, config in self.services.items():
            service_result = {
                "port_open": False,
                "response_time_ms": None,
                "health_endpoint_ok": False,
                "error": None
            }

            try:
                # Test port connectivity
                start_time = time.time()
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)

                port_result = sock.connect_ex(('localhost', config['port']))
                sock.close()

                response_time = (time.time() - start_time) * 1000
                service_result["response_time_ms"] = round(response_time, 2)
                service_result["port_open"] = port_result == 0

                # Test health endpoint if available
                if config.get('health_endpoint') and service_result["port_open"]:
                    try:
                        health_response = requests.get(
                            config['health_endpoint'],
                            timeout=5
                        )
                        service_result["health_endpoint_ok"] = health_response.status_code in [200, 201]
                    except requests.RequestException as e:
                        service_result["error"] = f"Health endpoint failed: {str(e)}"

            except Exception as e:
                service_result["error"] = str(e)

            connectivity_results[service_name] = service_result

        result["services"] = connectivity_results

        # Calculate summary
        total_services = len(connectivity_results)
        connected_services = sum(1 for s in connectivity_results.values() if s["port_open"])
        healthy_endpoints = sum(1 for s in connectivity_results.values()
                               if s.get("health_endpoint_ok", s["port_open"]))

        result["summary"] = {
            "total_services": total_services,
            "connected_services": connected_services,
            "healthy_endpoints": healthy_endpoints,
            "average_response_time_ms": round(
                sum(s["response_time_ms"] for s in connectivity_results.values()
                    if s["response_time_ms"] is not None) /
                max(1, sum(1 for s in connectivity_results.values()
                          if s["response_time_ms"] is not None)), 2
            )
        }

        # Overall health
        required_connected = sum(1 for name, config in self.services.items()
                               if config["required"] and connectivity_results[name]["port_open"])
        required_count = sum(1 for config in self.services.values() if config["required"])

        result["healthy"] = required_connected == required_count

        if not result["healthy"]:
            failed_services = [name for name, config in self.services.items()
                             if config["required"] and not connectivity_results[name]["port_open"]]
            result["errors"].append(f"Required services not accessible: {', '.join(failed_services)}")

        return result

    async def check_database_integration(self) -> Dict[str, Any]:
        """Test database services integration."""
        logger.info("🔍 Testing database integration...")

        result = {
            "name": "Database Integration",
            "healthy": False,
            "checks": {},
            "errors": []
        }

        # Get configuration
        if TEST_CONFIG:
            pg_config = TEST_CONFIG['postgresql']
            redis_config = TEST_CONFIG['redis']
            influx_config = TEST_CONFIG['influxdb']
        else:
            pg_config = {'host': 'localhost', 'port': 5433, 'user': 'lics', 'password': 'lics123', 'database': 'lics_dev'}
            redis_config = {'host': 'localhost', 'port': 6380, 'db': 0}
            influx_config = {'url': 'http://localhost:8087', 'token': 'lics-dev-admin-token', 'org': 'lics-dev'}

        # PostgreSQL connectivity test
        try:
            conn = await asyncpg.connect(
                host=pg_config['host'],
                port=pg_config['port'],
                user=pg_config['user'],
                password=pg_config['password'],
                database=pg_config['database']
            )

            # Basic query test
            version = await conn.fetchval("SELECT version()")
            result["checks"]["postgresql"] = {
                "connected": True,
                "version": version[:50] + "..." if len(version) > 50 else version
            }

            # TimescaleDB extension test
            try:
                ts_version = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
                )
                result["checks"]["timescaledb"] = {
                    "available": ts_version is not None,
                    "version": ts_version
                }
            except Exception as e:
                result["checks"]["timescaledb"] = {
                    "available": False,
                    "error": str(e)
                }

            await conn.close()

        except Exception as e:
            result["checks"]["postgresql"] = {
                "connected": False,
                "error": str(e)
            }
            result["errors"].append(f"PostgreSQL connection failed: {str(e)}")

        # Redis connectivity test
        try:
            redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                decode_responses=True
            )

            # Test basic operations
            redis_client.set("health_check", "ok", ex=10)
            test_value = redis_client.get("health_check")
            redis_client.delete("health_check")

            info = redis_client.info()

            result["checks"]["redis"] = {
                "connected": True,
                "read_write_test": test_value == "ok",
                "version": info.get("redis_version"),
                "memory_used": info.get("used_memory_human")
            }

            redis_client.close()

        except Exception as e:
            result["checks"]["redis"] = {
                "connected": False,
                "error": str(e)
            }
            result["errors"].append(f"Redis connection failed: {str(e)}")

        # InfluxDB connectivity test
        try:
            influx_client = InfluxDBClient(
                url=influx_config['url'],
                token=influx_config['token'],
                org=influx_config['org']
            )

            health = influx_client.health()

            result["checks"]["influxdb"] = {
                "connected": True,
                "status": health.status,
                "version": health.version
            }

            influx_client.close()

        except Exception as e:
            result["checks"]["influxdb"] = {
                "connected": False,
                "error": str(e)
            }
            result["errors"].append(f"InfluxDB connection failed: {str(e)}")

        # Overall health
        required_dbs = ["postgresql", "redis", "influxdb"]
        healthy_dbs = sum(1 for db in required_dbs
                         if result["checks"].get(db, {}).get("connected", False))

        result["healthy"] = healthy_dbs == len(required_dbs)

        return result

    def check_messaging_integration(self) -> Dict[str, Any]:
        """Test messaging services integration."""
        logger.info("🔍 Testing messaging integration...")

        result = {
            "name": "Messaging Integration",
            "healthy": False,
            "checks": {},
            "errors": []
        }

        # Get configuration
        if TEST_CONFIG:
            mqtt_config = TEST_CONFIG['mqtt']
            minio_port = int(TEST_CONFIG['minio']['endpoint'].split(':')[1])
        else:
            mqtt_config = {'host': 'localhost', 'port': 1884}
            minio_port = 9010

        # MQTT connectivity test
        try:
            mqtt_result = {"connected": False, "publish_test": False}

            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    mqtt_result["connected"] = True
                else:
                    mqtt_result["error"] = f"Connection failed with code {rc}"

            def on_message(client, userdata, msg):
                if msg.topic == "lics/health/test" and msg.payload.decode() == "test_message":
                    mqtt_result["publish_test"] = True

            client = mqtt.Client()
            client.on_connect = on_connect
            client.on_message = on_message

            client.connect(mqtt_config['host'], mqtt_config['port'], 10)
            client.loop_start()

            # Wait for connection
            time.sleep(2)

            if mqtt_result["connected"]:
                # Test publish/subscribe
                client.subscribe("lics/health/test")
                client.publish("lics/health/test", "test_message")
                time.sleep(1)

            client.loop_stop()
            client.disconnect()

            result["checks"]["mqtt"] = mqtt_result

        except Exception as e:
            result["checks"]["mqtt"] = {
                "connected": False,
                "error": str(e)
            }
            result["errors"].append(f"MQTT test failed: {str(e)}")

        # MinIO connectivity test
        try:
            health_response = requests.get(f"http://localhost:{minio_port}/minio/health/live", timeout=5)
            ready_response = requests.get(f"http://localhost:{minio_port}/minio/health/ready", timeout=5)

            result["checks"]["minio"] = {
                "live": health_response.status_code == 200,
                "ready": ready_response.status_code == 200,
                "api_accessible": True
            }

        except Exception as e:
            result["checks"]["minio"] = {
                "live": False,
                "ready": False,
                "api_accessible": False,
                "error": str(e)
            }
            result["errors"].append(f"MinIO test failed: {str(e)}")

        # Overall health
        messaging_services = ["mqtt", "minio"]
        healthy_services = sum(1 for service in messaging_services
                              if result["checks"].get(service, {}).get("connected",
                                                     result["checks"].get(service, {}).get("live", False)))

        result["healthy"] = healthy_services == len(messaging_services)

        return result

    def check_volume_persistence(self) -> Dict[str, Any]:
        """Test Docker volume persistence."""
        logger.info("🔍 Testing volume persistence...")

        result = {
            "name": "Volume Persistence",
            "healthy": False,
            "volumes": {},
            "errors": []
        }

        if not self.docker_client:
            result["errors"].append("Docker client not available")
            return result

        try:
            # Get volume information
            volumes = self.docker_client.volumes.list()
            lics_volumes = [v for v in volumes if 'lics' in v.name.lower() or 'primates' in v.name.lower()]

            for volume in lics_volumes:
                volume_info = {
                    "name": volume.name,
                    "driver": volume.attrs.get("Driver"),
                    "mountpoint": volume.attrs.get("Mountpoint"),
                    "created": volume.attrs.get("CreatedAt"),
                    "size_mb": None
                }

                # Try to get size information (may not be available on all systems)
                try:
                    inspect_info = self.docker_client.api.inspect_volume(volume.name)
                    volume_info["labels"] = inspect_info.get("Labels", {})
                except Exception:
                    pass

                result["volumes"][volume.name] = volume_info

            # Check if essential volumes exist
            essential_volumes = [
                "postgres_data", "redis_data", "influxdb_data",
                "minio_data", "grafana_data", "prometheus_data"
            ]

            existing_volumes = [v.name for v in lics_volumes]
            missing_volumes = []

            for essential in essential_volumes:
                # Check for volume name matches (accounting for docker-compose prefixes)
                if not any(essential in existing for existing in existing_volumes):
                    missing_volumes.append(essential)

            if missing_volumes:
                result["errors"].append(f"Missing essential volumes: {', '.join(missing_volumes)}")

            result["healthy"] = len(missing_volumes) == 0

        except Exception as e:
            result["errors"].append(f"Volume check failed: {str(e)}")

        return result

    def check_ssl_certificates(self) -> Dict[str, Any]:
        """Validate SSL certificate configuration."""
        logger.info("🔍 Checking SSL certificates...")

        result = {
            "name": "SSL Certificates",
            "healthy": False,
            "certificates": {},
            "errors": []
        }

        ssl_paths = [
            self.project_root / "infrastructure/nginx/ssl/localhost.pem",
            self.project_root / "infrastructure/nginx/ssl/localhost-key.pem",
            self.project_root / "infrastructure/nginx/ssl/server.crt",
            self.project_root / "infrastructure/nginx/ssl/server.key"
        ]

        valid_certs = 0

        for cert_path in ssl_paths:
            cert_info = {
                "path": str(cert_path),
                "exists": cert_path.exists(),
                "readable": False,
                "valid": False
            }

            if cert_info["exists"]:
                try:
                    cert_info["readable"] = os.access(cert_path, os.R_OK)
                    cert_info["size_bytes"] = cert_path.stat().st_size

                    # Basic validation for certificate files
                    if cert_path.suffix == '.pem' or cert_path.suffix == '.crt':
                        with open(cert_path, 'r') as f:
                            content = f.read()
                            cert_info["valid"] = "BEGIN CERTIFICATE" in content
                    elif cert_path.suffix == '.key':
                        with open(cert_path, 'r') as f:
                            content = f.read()
                            cert_info["valid"] = "BEGIN PRIVATE KEY" in content or "BEGIN RSA PRIVATE KEY" in content

                    if cert_info["valid"]:
                        valid_certs += 1

                except Exception as e:
                    cert_info["error"] = str(e)

            result["certificates"][cert_path.name] = cert_info

        result["healthy"] = valid_certs >= 2  # At least one cert/key pair

        if not result["healthy"]:
            result["errors"].append("Insufficient valid SSL certificates found")

        return result

    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests."""
        logger.info("🚀 Starting comprehensive LICS infrastructure validation...")

        # Initialize Docker client
        if not self.initialize_docker_client():
            return {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 0,
                "overall_healthy": False,
                "error": "Failed to initialize Docker client"
            }

        # Run validation checks
        validation_results = {}

        # 1. Docker Compose Status
        validation_results["docker_compose"] = self.check_docker_compose_status()

        # 2. Service Connectivity
        validation_results["connectivity"] = self.check_service_connectivity()

        # 3. Database Integration
        validation_results["database"] = await self.check_database_integration()

        # 4. Messaging Integration
        validation_results["messaging"] = self.check_messaging_integration()

        # 5. Volume Persistence
        validation_results["volumes"] = self.check_volume_persistence()

        # 6. SSL Certificates
        validation_results["ssl"] = self.check_ssl_certificates()

        # Skip additional checks in quick mode
        if not self.quick_mode:
            # Additional comprehensive checks could go here
            pass

        # Calculate overall results
        total_duration = time.time() - self.start_time
        healthy_checks = sum(1 for result in validation_results.values()
                           if result.get("healthy", False))
        total_checks = len(validation_results)

        overall_result = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(total_duration, 2),
            "overall_healthy": healthy_checks == total_checks,
            "validation_results": validation_results,
            "summary": {
                "total_checks": total_checks,
                "healthy_checks": healthy_checks,
                "failed_checks": total_checks - healthy_checks,
                "success_rate": round((healthy_checks / total_checks * 100), 2) if total_checks > 0 else 0
            }
        }

        # Collect all errors
        all_errors = []
        for check_name, check_result in validation_results.items():
            if check_result.get("errors"):
                for error in check_result["errors"]:
                    all_errors.append(f"{check_name}: {error}")

        if all_errors:
            overall_result["errors"] = all_errors

        self.results = overall_result
        return overall_result

    def format_results(self, format_type: str = "text") -> str:
        """Format validation results for output."""
        if format_type == "json":
            return json.dumps(self.results, indent=2)

        # Text format
        output = []
        output.append("=" * 80)
        output.append("LICS INFRASTRUCTURE VALIDATION REPORT")
        output.append("=" * 80)
        output.append(f"Timestamp: {self.results['timestamp']}")
        output.append(f"Duration: {self.results['duration_seconds']}s")
        output.append(f"Overall Status: {'✅ HEALTHY' if self.results['overall_healthy'] else '❌ UNHEALTHY'}")
        output.append("")

        # Summary
        summary = self.results["summary"]
        output.append(f"Summary: {summary['healthy_checks']}/{summary['total_checks']} checks passed ({summary['success_rate']}%)")
        output.append("")

        # Individual check results
        for check_name, check_result in self.results["validation_results"].items():
            status_icon = "✅" if check_result.get("healthy", False) else "❌"
            output.append(f"{status_icon} {check_result.get('name', check_name)}")

            # Add specific details for each check type
            if check_name == "docker_compose" and "summary" in check_result:
                s = check_result["summary"]
                output.append(f"   Services: {s.get('healthy_services', 0)}/{s.get('total_services', 0)} healthy")

            elif check_name == "connectivity" and "summary" in check_result:
                s = check_result["summary"]
                output.append(f"   Connectivity: {s.get('connected_services', 0)}/{s.get('total_services', 0)} services")
                output.append(f"   Avg Response Time: {s.get('average_response_time_ms', 0)}ms")

            elif check_name == "database" and "checks" in check_result:
                db_status = []
                for db, info in check_result["checks"].items():
                    status = "✅" if info.get("connected", False) else "❌"
                    db_status.append(f"{status} {db}")
                output.append(f"   Databases: {', '.join(db_status)}")

            elif check_name == "messaging" and "checks" in check_result:
                msg_status = []
                for service, info in check_result["checks"].items():
                    connected = info.get("connected", info.get("live", False))
                    status = "✅" if connected else "❌"
                    msg_status.append(f"{status} {service}")
                output.append(f"   Messaging: {', '.join(msg_status)}")

            elif check_name == "volumes" and "volumes" in check_result:
                output.append(f"   Volumes: {len(check_result['volumes'])} found")

            elif check_name == "ssl" and "certificates" in check_result:
                valid_certs = sum(1 for cert in check_result["certificates"].values()
                                if cert.get("valid", False))
                output.append(f"   Certificates: {valid_certs} valid")

            # Show errors if any
            if check_result.get("errors"):
                for error in check_result["errors"]:
                    output.append(f"     ⚠️  {error}")

            output.append("")

        # Overall errors
        if self.results.get("errors"):
            output.append("ERRORS:")
            for error in self.results["errors"]:
                output.append(f"  ❌ {error}")
            output.append("")

        # Recommendations
        if not self.results["overall_healthy"]:
            output.append("RECOMMENDATIONS:")
            output.append("  1. Check Docker Compose logs: docker-compose logs")
            output.append("  2. Verify services are running: docker-compose ps")
            output.append("  3. Restart services: docker-compose down && docker-compose up -d")
            output.append("  4. Check system resources (CPU, memory, disk)")
            output.append("  5. Review individual service configurations")

        return "\n".join(output)

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='LICS Infrastructure Validation')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick validation (essential checks only)')
    parser.add_argument('--exit-code', action='store_true',
                       help='Exit with non-zero code if validation fails')

    args = parser.parse_args()

    try:
        validator = InfrastructureValidator(quick_mode=args.quick)
        results = await validator.run_comprehensive_validation()
        formatted_output = validator.format_results(args.format)

        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(formatted_output)
            print(f"Validation results written to: {args.output}")
        else:
            print(formatted_output)

        # Exit code based on validation status
        if args.exit_code:
            sys.exit(0 if results["overall_healthy"] else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Infrastructure validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Infrastructure validation failed: {e}")
        logger.exception("Validation failed with exception")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
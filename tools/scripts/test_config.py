#!/usr/bin/env python3
"""
LICS Test Configuration

Centralized configuration for all test scripts with environment-aware settings.
Automatically detects whether to use development or production port mappings.

Usage:
    from test_config import get_test_config

    config = get_test_config()
    postgres_port = config['postgresql']['port']
"""

import os
from typing import Dict, Any, Literal

# Environment detection
def detect_environment() -> Literal['development', 'production']:
    """
    Detect the current environment based on environment variables or running services.

    Returns:
        'development' or 'production'
    """
    # Check if explicitly set
    env = os.getenv('LICS_ENVIRONMENT', '').lower()
    if env in ['development', 'dev']:
        return 'development'
    elif env in ['production', 'prod']:
        return 'production'

    # Default to development for local testing
    # In production, LICS_ENVIRONMENT should always be set
    return 'development'


# Development environment configuration (Docker Compose dev mapped ports)
DEVELOPMENT_CONFIG = {
    'environment': 'development',

    'postgresql': {
        'host': 'localhost',
        'port': 5433,  # Mapped from container port 5432
        'user': 'lics',
        'password': 'lics123',
        'database': 'lics_dev'
    },

    'pgbouncer': {
        'host': 'localhost',
        'port': 6433,  # Mapped from container port 6432
        'user': 'lics',
        'password': 'lics123',
        'database': 'lics_dev'
    },

    'redis': {
        'host': 'localhost',
        'port': 6380,  # Mapped from container port 6379
        'db': 0,
        'password': None
    },

    'mqtt': {
        'host': 'localhost',
        'port': 1884,  # Mapped from container port 1883
        'websocket_port': 9003,  # Mapped from container port 9001
        'username': None,
        'password': None,
        'timeout': 10
    },

    'minio': {
        'endpoint': 'localhost:9010',  # Mapped from container port 9000
        'console_endpoint': 'localhost:9011',  # Mapped from container port 9001
        'access_key': 'lics-dev-admin',
        'secret_key': 'lics-dev-minio-password-2024',
        'secure': False
    },

    'influxdb': {
        'url': 'http://localhost:8087',  # Mapped from container port 8086
        'token': 'lics-dev-admin-token',
        'org': 'lics-dev',
        'bucket': 'telemetry-dev'
    },

    'prometheus': {
        'host': 'localhost',
        'port': 9090,
        'health_endpoint': 'http://localhost:9090/-/healthy'
    },

    'grafana': {
        'host': 'localhost',
        'port': 3001,  # Mapped from container port 3000
        'health_endpoint': 'http://localhost:3001/api/health',
        'username': 'admin',
        'password': 'admin123'
    },

    'jaeger': {
        'host': 'localhost',
        'ui_port': 16686,
        'health_endpoint': 'http://localhost:13133'
    },

    'alertmanager': {
        'host': 'localhost',
        'port': 9093,
        'health_endpoint': 'http://localhost:9093/-/healthy'
    },

    'loki': {
        'host': 'localhost',
        'port': 3100,
        'health_endpoint': 'http://localhost:3100/ready'
    }
}


# Production environment configuration (direct container ports)
PRODUCTION_CONFIG = {
    'environment': 'production',

    'postgresql': {
        'host': 'localhost',
        'port': 5432,
        'user': 'lics',
        'password': os.getenv('POSTGRES_PASSWORD', 'lics123'),
        'database': 'lics'
    },

    'pgbouncer': {
        'host': 'localhost',
        'port': 6432,
        'user': 'lics',
        'password': os.getenv('POSTGRES_PASSWORD', 'lics123'),
        'database': 'lics'
    },

    'redis': {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': os.getenv('REDIS_PASSWORD', None)
    },

    'mqtt': {
        'host': 'localhost',
        'port': 1883,
        'websocket_port': 9001,
        'username': os.getenv('MQTT_USERNAME', None),
        'password': os.getenv('MQTT_PASSWORD', None),
        'timeout': 10
    },

    'minio': {
        'endpoint': 'localhost:9000',
        'console_endpoint': 'localhost:9001',
        'access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        'secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        'secure': False
    },

    'influxdb': {
        'url': 'http://localhost:8086',
        'token': os.getenv('INFLUXDB_TOKEN', 'lics-admin-token-change-in-production'),
        'org': 'lics',
        'bucket': 'telemetry'
    },

    'prometheus': {
        'host': 'localhost',
        'port': 9090,
        'health_endpoint': 'http://localhost:9090/-/healthy'
    },

    'grafana': {
        'host': 'localhost',
        'port': 3000,
        'health_endpoint': 'http://localhost:3000/api/health',
        'username': 'admin',
        'password': os.getenv('GRAFANA_PASSWORD', 'admin')
    },

    'jaeger': {
        'host': 'localhost',
        'ui_port': 16686,
        'health_endpoint': 'http://localhost:13133'
    },

    'alertmanager': {
        'host': 'localhost',
        'port': 9093,
        'health_endpoint': 'http://localhost:9093/-/healthy'
    },

    'loki': {
        'host': 'localhost',
        'port': 3100,
        'health_endpoint': 'http://localhost:3100/ready'
    }
}


def get_test_config(environment: str = None) -> Dict[str, Any]:
    """
    Get test configuration for the specified environment.

    Args:
        environment: 'development' or 'production'. If None, auto-detects.

    Returns:
        Dictionary with configuration for all services
    """
    if environment is None:
        environment = detect_environment()

    if environment == 'development':
        return DEVELOPMENT_CONFIG.copy()
    elif environment == 'production':
        return PRODUCTION_CONFIG.copy()
    else:
        raise ValueError(f"Invalid environment: {environment}. Must be 'development' or 'production'")


def get_service_config(service_name: str, environment: str = None) -> Dict[str, Any]:
    """
    Get configuration for a specific service.

    Args:
        service_name: Name of the service (e.g., 'postgresql', 'redis', 'mqtt')
        environment: 'development' or 'production'. If None, auto-detects.

    Returns:
        Dictionary with service-specific configuration

    Raises:
        KeyError: If service_name is not found in configuration
    """
    config = get_test_config(environment)

    if service_name not in config:
        raise KeyError(f"Service '{service_name}' not found in configuration. "
                      f"Available services: {', '.join(config.keys())}")

    return config[service_name]


def print_config_summary(environment: str = None):
    """
    Print a summary of the current test configuration.

    Args:
        environment: 'development' or 'production'. If None, auto-detects.
    """
    config = get_test_config(environment)

    print(f"╔══════════════════════════════════════════════════════════════════════════════╗")
    print(f"║  LICS Test Configuration Summary                                              ║")
    print(f"╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"\nEnvironment: {config['environment'].upper()}\n")

    print("Service Endpoints:")
    print("-" * 80)

    services = [
        ('PostgreSQL', config['postgresql']['host'], config['postgresql']['port']),
        ('PgBouncer', config['pgbouncer']['host'], config['pgbouncer']['port']),
        ('Redis', config['redis']['host'], config['redis']['port']),
        ('MQTT', config['mqtt']['host'], config['mqtt']['port']),
        ('MinIO', config['minio']['endpoint'].split(':')[0],
         config['minio']['endpoint'].split(':')[1]),
        ('InfluxDB', config['influxdb']['url'].replace('http://', '').replace('https://', '').split(':')[0],
         config['influxdb']['url'].split(':')[-1]),
        ('Prometheus', config['prometheus']['host'], config['prometheus']['port']),
        ('Grafana', config['grafana']['host'], config['grafana']['port']),
        ('Jaeger UI', config['jaeger']['host'], config['jaeger']['ui_port']),
        ('Alertmanager', config['alertmanager']['host'], config['alertmanager']['port']),
        ('Loki', config['loki']['host'], config['loki']['port'])
    ]

    for service, host, port in services:
        print(f"  {service:15} {host}:{port}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    """Command-line interface for configuration inspection."""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--production':
            print_config_summary('production')
        elif sys.argv[1] == '--development':
            print_config_summary('development')
        elif sys.argv[1] == '--service' and len(sys.argv) > 2:
            service_name = sys.argv[2]
            env = 'development' if '--development' in sys.argv else None
            try:
                config = get_service_config(service_name, env)
                print(f"\n{service_name.upper()} Configuration:")
                print("-" * 40)
                for key, value in config.items():
                    print(f"  {key}: {value}")
            except KeyError as e:
                print(f"Error: {e}")
                sys.exit(1)
        else:
            print("Usage:")
            print("  python test_config.py [--development | --production]")
            print("  python test_config.py --service <service_name> [--development]")
            print("\nExamples:")
            print("  python test_config.py --development")
            print("  python test_config.py --service postgresql")
            print("  python test_config.py --service redis --development")
            sys.exit(1)
    else:
        print_config_summary()

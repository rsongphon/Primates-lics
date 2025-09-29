"""
LICS Backend Logging Configuration

Structured logging with JSON format, correlation IDs, and comprehensive
logging setup following Documentation.md Section 13.2 patterns.
"""

import json
import logging
import logging.config
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import uvicorn
from fastapi import Request
from pythonjsonlogger import jsonlogger

from app.core.config import settings


class CorrelationFilter(logging.Filter):
    """
    Logging filter to add correlation ID to log records.

    The correlation ID is stored in context variables and automatically
    added to all log records within the same request context.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record."""
        # Get correlation ID from context or generate a new one
        correlation_id = getattr(_correlation_context, 'correlation_id', None)
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        record.correlation_id = correlation_id
        return True


class RequestFilter(logging.Filter):
    """
    Logging filter to add request information to log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request information to log record."""
        # Get request information from context if available
        request_info = getattr(_correlation_context, 'request_info', {})

        record.method = request_info.get('method', '')
        record.url = request_info.get('url', '')
        record.user_agent = request_info.get('user_agent', '')
        record.remote_addr = request_info.get('remote_addr', '')

        return True


class LICSJSONFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for LICS logging.

    Provides structured JSON logs with consistent format and
    additional metadata for monitoring and debugging.
    """

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['service'] = 'lics-backend'
        log_record['version'] = settings.APP_VERSION
        log_record['environment'] = settings.ENVIRONMENT

        # Add level name in lowercase
        log_record['level'] = record.levelname.lower()

        # Add module information
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id

        # Add request information if available
        if hasattr(record, 'method') and record.method:
            log_record['request'] = {
                'method': record.method,
                'url': record.url,
                'user_agent': record.user_agent,
                'remote_addr': record.remote_addr
            }

        # Add exception information if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None
            }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Create a copy to avoid modifying the original record
        record_copy = logging.makeLogRecord(record.__dict__)
        return super().format(record_copy)


class TextFormatter(logging.Formatter):
    """
    Simple text formatter for development and debugging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as text."""
        # Add correlation ID to the message if available
        correlation_id = getattr(record, 'correlation_id', '')
        correlation_prefix = f"[{correlation_id[:8]}] " if correlation_id else ""

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        # Build the log message
        level = record.levelname
        module = f"{record.module}:{record.lineno}"
        message = record.getMessage()

        formatted_message = f"{timestamp} {level:8} {correlation_prefix}{module:20} {message}"

        # Add exception information if present
        if record.exc_info:
            formatted_message += f"\n{self.formatException(record.exc_info)}"

        return formatted_message


# Context storage for correlation ID and request information
class CorrelationContext:
    """Thread-local storage for correlation ID and request context."""

    def __init__(self):
        self.correlation_id: Optional[str] = None
        self.request_info: Dict[str, Any] = {}


_correlation_context = CorrelationContext()


@contextmanager
def correlation_context(correlation_id: str, request_info: Optional[Dict[str, Any]] = None):
    """
    Context manager to set correlation ID and request information.

    Args:
        correlation_id: Unique correlation ID for the request
        request_info: Optional request information dictionary
    """
    old_correlation_id = _correlation_context.correlation_id
    old_request_info = _correlation_context.request_info.copy()

    try:
        _correlation_context.correlation_id = correlation_id
        _correlation_context.request_info = request_info or {}
        yield
    finally:
        _correlation_context.correlation_id = old_correlation_id
        _correlation_context.request_info = old_request_info


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return _correlation_context.correlation_id


def extract_request_info(request: Request) -> Dict[str, Any]:
    """
    Extract relevant information from FastAPI request.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with request information
    """
    return {
        'method': request.method,
        'url': str(request.url),
        'user_agent': request.headers.get('user-agent', ''),
        'remote_addr': request.client.host if request.client else ''
    }


def setup_logging() -> None:
    """
    Set up logging configuration for the LICS backend.

    Configures both JSON and text formatters based on settings,
    adds correlation and request filters, and sets up proper
    log levels and handlers.
    """
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create formatters
    if settings.LOG_FORMAT.lower() == 'json':
        formatter = LICSJSONFormatter()
    else:
        formatter = TextFormatter()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationFilter())
    console_handler.addFilter(RequestFilter())

    # Create file handler if specified
    handlers = [console_handler]
    if settings.LOG_FILE:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_SIZE,
            backupCount=settings.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(CorrelationFilter())
        file_handler.addFilter(RequestFilter())
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format='%(message)s'  # Format is handled by the custom formatters
    )

    # Configure specific loggers
    loggers = {
        'uvicorn': logging.INFO,
        'uvicorn.error': logging.INFO,
        'uvicorn.access': logging.WARNING if not settings.DEBUG else logging.INFO,
        'fastapi': logging.INFO,
        'sqlalchemy.engine': logging.WARNING if not settings.DEBUG else logging.INFO,
        'sqlalchemy.pool': logging.WARNING,
        'alembic': logging.INFO,
        'redis': logging.WARNING,
        'pika': logging.WARNING,  # MQTT
        'minio': logging.WARNING,
        'influxdb_client': logging.WARNING,
    }

    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True

    # Suppress noisy loggers in production
    if settings.is_production():
        logging.getLogger('uvicorn.access').setLevel(logging.ERROR)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Configure Uvicorn logging
class UvicornFormatter(logging.Formatter):
    """Custom formatter for Uvicorn logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format Uvicorn log records."""
        if settings.LOG_FORMAT.lower() == 'json':
            # Convert to JSON format
            log_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'level': record.levelname.lower(),
                'service': 'lics-backend',
                'component': 'uvicorn',
                'message': record.getMessage()
            }
            return json.dumps(log_data)
        else:
            # Use text format
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            return f"{timestamp} {record.levelname:8} uvicorn          {record.getMessage()}"


def configure_uvicorn_logging():
    """Configure Uvicorn logging to match our logging format."""
    # Configure Uvicorn access log format
    if settings.LOG_FORMAT.lower() == 'json':
        uvicorn_formatter = UvicornFormatter()
    else:
        uvicorn_formatter = UvicornFormatter()

    # Apply formatter to Uvicorn loggers
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            handler.setFormatter(uvicorn_formatter)


# Performance logging helpers
class PerformanceLogger:
    """Helper class for performance logging."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @contextmanager
    def log_execution_time(self, operation: str, **kwargs):
        """
        Context manager to log execution time of operations.

        Args:
            operation: Name of the operation being timed
            **kwargs: Additional context to include in the log
        """
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.logger.info(
                f"Operation completed: {operation}",
                extra={
                    'operation': operation,
                    'execution_time_ms': round(execution_time * 1000, 2),
                    **kwargs
                }
            )


# Initialize logging on module import
setup_logging()
# LICS Backend

[![Backend CI](https://github.com/rsongphon/Primates-lics/workflows/Backend%20CI/badge.svg)](https://github.com/rsongphon/Primates-lics/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

The LICS backend is a high-performance REST API built with FastAPI, providing comprehensive laboratory instrument control and experiment management capabilities.

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.104+
- **Language**: Python 3.11+
- **Database**: PostgreSQL with TimescaleDB extension
- **Cache**: Redis
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Task Queue**: Celery with Redis broker
- **Authentication**: JWT with refresh tokens
- **Validation**: Pydantic v2
- **WebSocket**: FastAPI WebSocket support
- **MQTT**: Paho MQTT client
- **Monitoring**: Prometheus metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with TimescaleDB
- Redis 7+
- Poetry (recommended) or pip

### Development Setup

1. **Clone and navigate**
   ```bash
   cd services/backend
   ```

2. **Install dependencies**
   ```bash
   # Using Poetry (recommended)
   poetry install

   # Or using pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Database Setup**
   ```bash
   # Run migrations
   alembic upgrade head

   # Seed development data (optional)
   python scripts/seed_data.py
   ```

5. **Start development server**
   ```bash
   # Using Poetry
   poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   # Or using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **API Documentation**
   ```
   http://localhost:8000/docs (Swagger UI)
   http://localhost:8000/redoc (ReDoc)
   ```

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lics
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# Authentication
JWT_SECRET=your-super-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# MQTT
MQTT_BROKER_URL=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Object Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=8001

# Development
DEBUG=true
LOG_LEVEL=INFO
```

## 📁 Project Structure

```
services/backend/
├── app/                    # Main application package
│   ├── api/               # API routes
│   │   ├── v1/            # API version 1
│   │   │   ├── devices.py     # Device endpoints
│   │   │   ├── experiments.py # Experiment endpoints
│   │   │   ├── auth.py        # Authentication
│   │   │   └── ...
│   │   └── dependencies.py    # Route dependencies
│   ├── core/              # Core functionality
│   │   ├── config.py      # Configuration
│   │   ├── database.py    # Database setup
│   │   ├── security.py    # Security utilities
│   │   └── cache.py       # Caching layer
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py        # User model
│   │   ├── device.py      # Device model
│   │   └── ...
│   ├── schemas/           # Pydantic schemas
│   │   ├── user.py        # User schemas
│   │   ├── device.py      # Device schemas
│   │   └── ...
│   ├── services/          # Business logic
│   │   ├── device_service.py
│   │   ├── experiment_service.py
│   │   └── ...
│   ├── tasks/             # Celery tasks
│   │   ├── device_tasks.py
│   │   ├── data_processing.py
│   │   └── ...
│   ├── utils/             # Utility functions
│   ├── websocket/         # WebSocket handlers
│   └── main.py            # FastAPI application
├── alembic/               # Database migrations
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
└── pyproject.toml         # Poetry configuration
```

## 🛡️ API Design

### RESTful Endpoints

The API follows RESTful conventions:

```
GET    /api/v1/devices                    # List devices
POST   /api/v1/devices                    # Create device
GET    /api/v1/devices/{device_id}        # Get device
PUT    /api/v1/devices/{device_id}        # Update device
DELETE /api/v1/devices/{device_id}        # Delete device
POST   /api/v1/devices/{device_id}/command # Send command
```

### Request/Response Format

```python
# Request Schema
class DeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: DeviceType
    capabilities: Dict[str, Any]
    location: Optional[str] = None

# Response Schema
class DeviceResponse(BaseModel):
    id: UUID
    name: str
    type: DeviceType
    status: DeviceStatus
    capabilities: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

### Error Handling

Standardized error responses:

```python
{
    "detail": {
        "code": "DEVICE_NOT_FOUND",
        "message": "Device with ID 123 not found",
        "type": "validation_error"
    }
}
```

## 🗄️ Database

### Models

We use SQLAlchemy 2.0 with async support:

```python
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    status = Column(String, default="offline")
    capabilities = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add device table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### TimescaleDB Integration

For time-series data:

```python
# Create hypertable for telemetry data
CREATE TABLE telemetry (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL,
    metric VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION,
    tags JSONB
);

SELECT create_hypertable('telemetry', 'time');
```

## 🔐 Authentication & Authorization

### JWT Authentication

```python
from app.core.security import create_access_token, verify_token

# Create token
token = create_access_token(data={"sub": user.email})

# Verify token
@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"user": current_user.email}
```

### Role-Based Access Control

```python
from app.core.security import require_roles

@router.post("/admin-only")
@require_roles(["admin"])
async def admin_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": "Admin access granted"}
```

## 📨 Background Tasks

### Celery Configuration

```python
# app/tasks/celery_app.py
from celery import Celery

celery_app = Celery(
    "lics",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/1",
    include=["app.tasks.device_tasks", "app.tasks.data_processing"]
)

# Task example
@celery_app.task
def process_telemetry_data(device_id: str, data: dict):
    # Process device telemetry
    pass
```

### Running Celery

```bash
# Start worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info

# Monitor tasks
celery -A app.tasks.celery_app flower
```

## 🔗 MQTT Integration

### MQTT Client

```python
import paho.mqtt.client as mqtt
from app.core.config import settings

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        client.subscribe("devices/+/telemetry")

    def on_message(self, client, userdata, msg):
        # Handle incoming telemetry
        pass
```

## 🌐 WebSocket

### Real-time Communication

```python
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Process WebSocket message
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print(f"Client disconnected from device {device_id}")
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_devices.py

# Run integration tests
pytest tests/integration/

# Run tests in parallel
pytest -n auto
```

### Test Structure

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_device():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/devices", json={
            "name": "Test Device",
            "type": "sensor",
            "capabilities": {}
        })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Device"
```

### Database Testing

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.device import Device

@pytest.mark.asyncio
async def test_device_crud():
    async with AsyncSession() as session:
        device = Device(name="Test Device", type="sensor")
        session.add(device)
        await session.commit()

        assert device.id is not None
        assert device.name == "Test Device"
```

## 📊 Monitoring

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

# Custom metrics
api_requests_total = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
api_request_duration = Histogram('api_request_duration_seconds', 'API request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    api_requests_total.labels(method=request.method, endpoint=request.url.path).inc()
    api_request_duration.observe(duration)

    return response
```

### Health Checks

```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "mqtt": check_mqtt_health()
        }
    }
```

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Settings

```python
# app/core/config.py
class Settings(BaseSettings):
    debug: bool = False
    log_level: str = "INFO"
    database_pool_size: int = 20
    redis_connection_pool_size: int = 50

    class Config:
        env_file = ".env"
```

## 📚 API Documentation

The API is automatically documented with OpenAPI/Swagger:

- Interactive docs: `/docs`
- Alternative docs: `/redoc`
- OpenAPI schema: `/openapi.json`

### Custom Documentation

```python
@router.post("/devices",
    summary="Create a new device",
    description="Register a new device in the system",
    response_model=DeviceResponse,
    status_code=201
)
async def create_device(device: DeviceCreate):
    """
    Create a new device with the following information:

    - **name**: Device name (required)
    - **type**: Device type (sensor, actuator, etc.)
    - **capabilities**: Device capabilities as JSON object
    """
    pass
```

## 🤝 Contributing

1. Follow PEP 8 style guidelines
2. Write comprehensive tests
3. Update API documentation
4. Use type hints throughout
5. Follow the established project structure

See the main [Contributing Guide](../../CONTRIBUTING.md) for more details.

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
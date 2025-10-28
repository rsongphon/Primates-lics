# LICS Test Suite

This directory contains the centralized test infrastructure for the LICS (Lab Instrument Control System) project.

## Directory Structure

```
@tests/
├── README.md                           # This file
├── pytest.ini                         # Global pytest configuration
├── jest.config.js                      # Jest configuration for frontend tests
├── jest.setup.js                       # Jest setup with mocks and globals
├── conftest.py                         # Global pytest fixtures and configuration
│
├── unit/                              # Unit tests
│   ├── backend/                       # Backend unit tests
│   │   ├── test_routes.py             # API route registration tests
│   │   ├── simple_circuit_breaker_test.py  # Simple circuit breaker tests
│   │   └── [copied from services/backend/tests/unit/]
│   ├── frontend/                      # Frontend unit tests
│   │   └── __tests__/                 # Jest test files
│   │       ├── components/            # React component tests
│   │       ├── stores/                # Zustand store tests
│   │       ├── utils/                 # Utility function tests
│   │       └── validation/            # Schema validation tests
│   └── edge-agent/                    # Edge agent unit tests
│
├── integration/                       # Integration tests
│   ├── api/                          # API integration tests
│   ├── database/                     # Database integration tests
│   ├── messaging/                    # Message queue integration tests
│   └── websocket/                    # WebSocket integration tests
│
├── e2e/                              # End-to-end tests
│   └── playwright/                  # Playwright E2E tests
│
├── performance/                      # Performance and load tests
│   ├── api-load-test.js             # K6 API load test
│   ├── k6/                          # Additional K6 scripts
│   └── circuit_breaker_performance.py  # Circuit breaker performance tests
│
├── circuit-breaker/                  # Circuit breaker specialized tests
│   ├── test_circuit_breaker_system.py    # System-wide circuit breaker tests
│   ├── test_circuit_breaker_validation.py  # Circuit breaker validation tests
│   ├── test_circuit_breaker_performance.py # Performance tests
│   └── README.md                    # Circuit breaker testing guide
│
├── phase1/                          # Phase 1 manual tests
│   ├── refactor_phase1/            # Phase 1 refactor test suite
│   │   ├── test_plan.md
│   │   ├── test_circuit_breakers.py
│   │   ├── run_all_tests.sh
│   │   └── README.md
│   └── README.md                    # Phase 1 testing guide
│
├── phase2/                          # Phase 2 manual tests
│   └── README.md                    # Phase 2 testing guide
│
├── security/                        # Security tests
│   ├── authentication/              # Authentication security tests
│   ├── authorization/               # Authorization tests
│   └── vulnerability/               # Vulnerability tests
│
├── fixtures/                        # Test data and fixtures
│   ├── sample_data.json
│   ├── mock_responses.json
│   └── database_seeds.sql
│
├── utils/                           # Test utilities and helpers
│   ├── test_config.py              # Test configuration management
│   ├── helpers.py                  # Test helper functions
│   ├── mocks.py                    # Mock objects and utilities
│   └── setup/                      # Setup utilities
│
└── config/                          # Test configurations
    ├── docker-compose.test.yml     # Test environment Docker setup
    ├── environments/               # Environment-specific configs
    │   ├── development.json
    │   ├── testing.json
    │   └── production.json
    └── database/                   # Database test configurations
        └── test_db_config.json
```

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run specific service tests
make test-backend      # Backend unit tests
make test-frontend     # Frontend unit tests
make test-edge-agent   # Edge agent tests

# Run integration tests
make test-integration

# Run tests with coverage
make test-coverage

# Run performance tests
make performance-test
```

### Backend Tests (Python/Pytest)

```bash
# Run all backend tests from @tests/
cd @tests && pytest -c pytest.ini

# Run specific test categories
cd @tests && pytest -c pytest.ini unit/backend/
cd @tests && pytest -c pytest.ini integration/
cd @tests && pytest -c pytest.ini security/

# Run with coverage
cd @tests && pytest -c pytest.ini --cov=services/backend/app --cov-report=html

# Run specific test file
cd @tests && pytest -c pytest.ini unit/backend/test_routes.py
```

### Frontend Tests (JavaScript/Jest)

```bash
# Run all frontend tests from @tests/
cd @tests && npx jest --config jest.config.js

# Run specific test files
cd @tests && npx jest --config jest.config.js unit/frontend/__tests__/components/

# Run with coverage
cd @tests && npx jest --config jest.config.js --coverage

# Run in watch mode
cd @tests && npx jest --config jest.config.js --watch
```

### Circuit Breaker Tests

```bash
# Run circuit breaker system tests
cd @tests && python circuit-breaker/test_circuit_breaker_system.py

# Run circuit breaker validation tests
cd @tests && python circuit-breaker/test_circuit_breaker_validation.py

# Run circuit breaker performance tests
cd @tests && python circuit-breaker/test_circuit_breaker_performance.py
```

### Performance Tests

```bash
# Run K6 load tests
k6 run @tests/performance/api-load-test.js

# Run circuit breaker performance tests
cd @tests && python performance/circuit_breaker_performance.py
```

### Phase Tests

```bash
# Phase 1 tests
make test-phase1-full

# Phase 2 tests
make test-phase2-full
```

## Test Configuration

### Backend (pytest.ini)

- **Test Path**: Points to `@tests/` directory
- **Coverage**: Configured for `services/backend/app`
- **Coverage Threshold**: 80%
- **Markers**: unit, integration, security, performance, slow, auth, rbac

### Frontend (jest.config.js)

- **Test Environment**: jsdom
- **Frontend Directory**: `../services/frontend/`
- **Test Patterns**: Finds tests in `unit/frontend/__tests__/` and `unit/frontend/**/*.{test,spec}.{js,ts,tsx}`
- **Coverage Threshold**: 80% lines, 70% branches/functions

## Container-Based Testing

Since LICS uses Docker-first development, tests are designed to run inside containers:

```bash
# Run backend tests in container
docker-compose -f docker-compose.dev.yml exec backend-dev pytest

# Run frontend tests in container
docker-compose -f docker-compose.dev.yml exec frontend-dev npm test

# Run tests using dev-cli.sh
./tools/dev-cli.sh pytest
./tools/dev-cli.sh test
```

## Test Categories

### Unit Tests
- Fast, isolated tests for individual functions and components
- Located in `unit/backend/`, `unit/frontend/`, `unit/edge-agent/`
- Use mocks for external dependencies

### Integration Tests
- Test interactions between services
- Located in `integration/` subdirectories
- Use real services or test containers

### End-to-End Tests
- Full user workflow testing
- Located in `e2e/playwright/`
- Uses real browser automation

### Performance Tests
- Load testing and benchmarking
- Located in `performance/`
- Uses K6 for load testing, custom scripts for specialized tests

### Security Tests
- Authentication, authorization, and vulnerability testing
- Located in `security/`
- Tests for common security issues

## Writing New Tests

### Backend Unit Tests

```python
# @tests/unit/backend/test_example.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_example_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/example")
    assert response.status_code == 200
```

### Frontend Unit Tests

```typescript
// @tests/unit/frontend/__tests__/components/Example.test.tsx
import { render, screen } from '@testing-library/react'
import { Example } from '@/components/Example'

describe('Example Component', () => {
  it('renders correctly', () => {
    render(<Example />)
    expect(screen.getByText('Example')).toBeInTheDocument()
  })
})
```

### Integration Tests

```python
# @tests/integration/test_api_integration.py
import pytest
import requests

def test_api_integration():
    response = requests.get('http://localhost:8000/api/v1/health')
    assert response.status_code == 200
```

## Test Data Management

- **Fixtures**: Located in `fixtures/` directory
- **Database Seeds**: Use `fixtures/database_seeds.sql`
- **Mock Data**: Use `fixtures/mock_responses.json`
- **Configuration**: Use `config/environments/` for environment-specific data

## CI/CD Integration

All tests are integrated into the GitHub Actions workflow:

- **Unit Tests**: Run on every push
- **Integration Tests**: Run on pull requests
- **E2E Tests**: Run on main branch
- **Performance Tests**: Run nightly
- **Security Tests**: Run on security scan events

## Troubleshooting

### Backend Tests
- Ensure PostgreSQL and Redis are running
- Check environment variables in `@tests/utils/test_config.py`
- Verify database migrations are up to date

### Frontend Tests
- Ensure Node.js dependencies are installed
- Check Jest configuration paths
- Verify frontend environment variables

### Integration Tests
- Ensure all required services are running
- Check Docker containers are healthy
- Verify network connectivity between services

### Performance Tests
- Ensure sufficient system resources
- Check K6 installation and configuration
- Monitor system performance during tests

## Contributing

When adding new tests:

1. Place them in the appropriate category directory
2. Follow existing naming conventions
3. Add appropriate test markers for pytest
4. Update this README if adding new test types
5. Ensure tests pass in CI/CD pipeline
6. Add documentation for complex test scenarios

## Test Results and Reports

- **Coverage Reports**: Generated in `htmlcov/` directory
- **Test Results**: JSON outputs in `test-results/` directory
- **Performance Reports**: HTML reports in `test-results/reports/`
- **Phase Test Reports**: Comprehensive markdown and HTML reports

For more detailed information on specific test types, see the README files in respective subdirectories.
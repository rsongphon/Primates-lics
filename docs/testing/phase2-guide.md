# Phase 2 - Backend Core Development Testing Guide

**Version**: 1.0
**Date**: 2025-10-13
**Scope**: Backend Development - FastAPI Application, Authentication, Domain Models, RESTful APIs, WebSocket, Background Tasks

---

## Table of Contents
1. [Setup Instructions](#setup-instructions)
2. [Automated Testing](#automated-testing)
3. [Manual Testing Procedures](#manual-testing-procedures)
4. [Expected Outcomes](#expected-outcomes)
5. [Test Results Recording](#test-results-recording)
6. [Troubleshooting](#troubleshooting)

---

## 1. Setup Instructions

### Prerequisites - Docker Development Environment

**⚠️ Important**: All services run in Docker containers. Do NOT run services locally.

```bash
# Start complete development environment
make dev
```

This single command starts:
- Backend API (http://localhost:8000) with auto-reload
- PostgreSQL + TimescaleDB (localhost:5433)
- Redis (localhost:6380)
- MQTT broker (localhost:1884)
- MinIO object storage (http://localhost:9011)
- All development tools (PgAdmin, Redis Commander, MailHog, Jaeger)

**Verify services are running**:
```bash
# Check all containers
docker-compose -f docker-compose.dev.yml ps

# Expected output: All services should show "Up" status
```

### Database Setup

**Note**: For detailed migration documentation, see `docs/DATABASE_MIGRATIONS.md`

**Initialize database and run migrations**:
```bash
# Run migrations inside backend container (recommended method)
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py migrate

# Verify migration status
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py current

# Alternative: Direct alembic commands (after container rebuild)
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head

# Seed database with test data (optional)
docker-compose -f docker-compose.dev.yml exec backend-dev python -m app.core.seeds
```

### Test Dependencies

Test dependencies are already installed in the Docker container. To verify or rebuild:
```bash
# Rebuild backend container if needed
docker-compose -f docker-compose.dev.yml up --build backend-dev

# Verify pytest inside container
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --version
```

### Environment Configuration

Environment variables are configured in `docker-compose.dev.yml`. No manual `.env.test` file needed.

---

## 2. Automated Testing

> **📖 Verbose Debugging Guide**: For comprehensive documentation on verbose and debug modes, see [VERBOSE_DEBUGGING_GUIDE.md](./VERBOSE_DEBUGGING_GUIDE.md)

### 2.0 Automated Manual Test Suite (NEW)

**Purpose**: Complete automation of all manual test procedures from Section 3

The Phase 2 Manual Test Suite provides 100% automation coverage of manual testing procedures, allowing for:
- Rapid validation of backend functionality
- Consistent, repeatable testing across environments
- Automated test execution in CI/CD pipelines
- Detailed step-by-step validation matching manual procedures

#### Quick Start - Run All Tests

```bash
# Run all automated manual tests with complete workflow (tests + reports)
make test-phase2-full

# Run all tests with verbose output (recommended for development)
make test-phase2-manual-verbose

# Run all tests with debug output (shows all HTTP requests/responses)
make test-phase2-manual-debug

# Run all tests and save JSON results (minimal output)
make test-phase2-manual
```

**What This Tests**: All 125 test cases from Section 3 (Application, Authentication, Domain Models, APIs, WebSocket, Celery)

**Expected Execution Time**: 15-20 minutes

**Output Files**:
- 📄 **JSON Results**: `test-results/phase2_manual_TIMESTAMP.json`
  - Machine-readable test results with full details
  - Used as input for report generation
  - Compatible with CI/CD pipelines

- 📝 **Markdown Report**: `test-results/reports/phase2_report_TIMESTAMP.md`
  - Human-readable report matching testing guide template
  - Includes system configuration, test results, and recommendations
  - Perfect for documentation and review

- 🌐 **HTML Report**: `test-results/reports/phase2_report_TIMESTAMP.html`
  - Interactive dashboard with color-coded results
  - Expandable test steps and error details
  - Executive summary with statistics
  - Professional formatting with charts

**Automatic Report Generation**:
```bash
# Complete workflow: Run tests + Generate markdown + Generate HTML
make test-phase2-full

# Generate reports from existing JSON results
make generate-test-report INPUT=test-results/phase2_manual_20251016_120000.json

# Direct report generation
python3 tools/scripts/generate-test-report.py \
    --input test-results/phase2_manual_20251016_120000.json \
    --format both \
    --output test-results/reports/phase2_report.md
```

#### Verbose and Debug Modes

All automated tests now support enhanced verbosity for debugging:

| Mode | Flag | Shows | Use When |
|------|------|-------|----------|
| **Standard** | (default) | Minimal output, saves JSON | CI/CD, quick validation |
| **Verbose** | `--verbose` or `-v` | Test steps, timing, pass/fail status | Development, debugging |
| **Debug** | `--debug` or `-d` | All HTTP requests/responses, detailed tracing | Investigating failures |

**Examples**:
```bash
# Verbose: See test progress and steps
python3 tools/scripts/test-phase2-manual.py --verbose
make test-phase2-manual-verbose

# Debug: See all HTTP interactions
python3 tools/scripts/test-phase2-manual.py --debug
make test-phase2-manual-debug

# Specific test with debug output
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --debug
make test-phase2-manual-tc-debug TC=TC-AUTH-001
```

**Verbose Output Example**:
```
[12:34:56.789] [INFO] Running TC-AUTH-001: User Registration
[12:34:56.790] [STEP]   → Creating test user
[12:34:56.801] [PASS]   ✓ User created successfully (11ms)
[12:34:56.802] [STEP]   → Validating email format
[12:34:56.805] [PASS]   ✓ Email validation passed (3ms)
[12:34:56.806] [PASS] ✓ TC-AUTH-001 completed in 0.02s
```

**Debug Output Example** (includes HTTP details):
```
[12:34:56.790] [DEBUG] → POST http://localhost:8000/api/v1/auth/register
[12:34:56.790] [DEBUG]   Request Body: {
  "email": "testuser@example.com",
  "password": "TestPassword123!",
  ...
}
[12:34:56.800] [DEBUG] ← Status: 201 (10ms)
[12:34:56.800] [DEBUG]   Response: {
  "id": "uuid-here",
  "email": "testuser@example.com",
  ...
}
```

> **📖 Complete Documentation**: See [VERBOSE_DEBUGGING_GUIDE.md](./VERBOSE_DEBUGGING_GUIDE.md) for comprehensive verbose/debug documentation

#### Run Specific Test Cases

```bash
# List all available test cases
make test-phase2-list

# Run specific test case
make test-phase2-manual-tc TC=TC-APP-001    # FastAPI Server Startup
make test-phase2-manual-tc TC=TC-AUTH-001   # User Registration
make test-phase2-manual-tc TC=TC-API-001    # Organizations API - List
make test-phase2-manual-tc TC=TC-WS-001     # WebSocket Connection
```

#### Run Tests by Category

Run specific test categories independently for faster, targeted validation. **All category commands now automatically generate markdown and HTML reports:**

```bash
# Application Foundation tests (5 tests, ~1 minute)
make test-phase2-app
# → Generates: phase2_app_TIMESTAMP.json + markdown + HTML reports

# Authentication & Authorization tests (20 tests, ~3-4 minutes)
make test-phase2-auth
# → Generates: phase2_auth_TIMESTAMP.json + markdown + HTML reports

# Core Domain Models tests (15 tests, ~2-3 minutes)
make test-phase2-domain
# → Generates: phase2_domain_TIMESTAMP.json + markdown + HTML reports

# RESTful API Implementation tests (40 tests, ~6-8 minutes)
make test-phase2-api
# → Generates: phase2_api_TIMESTAMP.json + markdown + HTML reports

# WebSocket and Real-time Features tests (20 tests, ~3-4 minutes)
make test-phase2-websocket
# → Generates: phase2_websocket_TIMESTAMP.json + markdown + HTML reports

# Background Tasks and Scheduling tests (25 tests, ~4-5 minutes)
make test-phase2-celery
# → Generates: phase2_celery_TIMESTAMP.json + markdown + HTML reports
```

**Use Cases**:
- **Focused Development**: Test only the component you're working on
- **Faster Feedback**: Get results in minutes instead of 15-20 minutes
- **Debugging**: Isolate issues to specific test categories
- **CI/CD Optimization**: Run categories in parallel for faster builds
- **Professional Reports**: Each category gets its own markdown and HTML dashboard

#### Quick Validation

For rapid validation during development:

```bash
# Quick validation - Run 8 core tests from each category (~2 minutes)
make test-phase2-quick

# Smoke tests - Run 2 critical tests only (~30 seconds)
make test-phase2-smoke
```

**Quick Validation Tests**:
- TC-APP-001, TC-APP-002 (Application Foundation)
- TC-AUTH-001, TC-AUTH-002 (Authentication)
- TC-API-001, TC-API-004 (RESTful API)
- TC-WS-001 (WebSocket)
- TC-CELERY-001 (Background Tasks)

**Smoke Tests**:
- TC-APP-001 (FastAPI Server Startup)
- TC-AUTH-001 (User Registration)

#### Generate Reports from Existing Results

**Using Make Command** (Recommended):
```bash
# Show available test results (both Phase 1 and Phase 2)
make generate-test-report
# This will list available JSON files if INPUT not specified

# Generate report from specific Phase 2 results
make generate-test-report INPUT=test-results/phase2_manual_20251016_120000.json

# The command automatically generates both Markdown and HTML formats
```

**Using Python Script Directly** (Advanced):
```bash
# Generate both Markdown and HTML reports
python3 tools/scripts/generate-test-report.py \
    --input test-results/phase2_manual_20251016_120000.json \
    --format both \
    --output test-results/reports/phase2_report.md

# Generate only HTML report
python3 tools/scripts/generate-test-report.py \
    --input test-results/phase2_manual_20251016_120000.json \
    --format html \
    --output test-results/reports/phase2_report.html

# Generate only Markdown report
python3 tools/scripts/generate-test-report.py \
    --input test-results/phase2_manual_20251016_120000.json \
    --format markdown \
    --output test-results/reports/phase2_report.md
```

**Report Features**:
- ✅ **Automatic Phase Detection**: Script detects Phase 1 or Phase 2 from JSON structure
- 📊 **Executive Summary**: Success rate, test counts, duration
- 🏗️ **System Configuration**: OS, Docker version, resources
- 📋 **Test Results by Category**: Organized by functional area
- ⚠️ **Failed Test Details**: Error messages and failed steps
- 💡 **Recommendations**: Next steps based on test results
- 🎨 **Professional Formatting**: Color-coded, responsive HTML design

#### Available Test Cases

The automated suite includes all 125 manual test cases:

**Application Foundation Tests** (Section 3.1)
- `TC-APP-001`: FastAPI Server Startup
- `TC-APP-002`: Database Connection
- `TC-APP-003`: Health Check Endpoints
- `TC-APP-004`: API Versioning
- `TC-APP-005`: Repository Pattern Implementation

**Authentication & Authorization Tests** (Section 3.2)
- `TC-AUTH-001`: User Registration
- `TC-AUTH-002`: User Login
- `TC-AUTH-003`: JWT Token Validation
- `TC-AUTH-004`: Invalid Token Handling
- `TC-AUTH-005`: Token Refresh
- `TC-AUTH-006`: Password Change
- `TC-AUTH-007`: Password Reset Request
- `TC-AUTH-008`: Password Reset Confirmation
- `TC-AUTH-009`: RBAC - Role Creation
- `TC-AUTH-010`: RBAC - Permission Assignment
- `TC-AUTH-011`: RBAC - Permission Enforcement
- `TC-AUTH-012`: Multi-Factor Authentication Setup
- `TC-AUTH-013`: MFA Login Flow
- `TC-AUTH-014`: Session Management
- `TC-AUTH-015`: User Profile Update
- `TC-AUTH-016`: Email Verification
- `TC-AUTH-017`: Account Lockout
- `TC-AUTH-018`: Logout
- `TC-AUTH-019`: Concurrent Sessions
- `TC-AUTH-020`: Admin User Management

**Core Domain Models Tests** (Section 3.3)
- `TC-DOMAIN-001`: Organization CRUD
- `TC-DOMAIN-002`: Device Registration
- `TC-DOMAIN-003`: Device Status Updates
- `TC-DOMAIN-004`: Device Telemetry
- `TC-DOMAIN-005`: Experiment Creation
- `TC-DOMAIN-006`: Experiment Lifecycle
- `TC-DOMAIN-007`: Participant (Primate) Management
- `TC-DOMAIN-008`: Participant Welfare Checks
- `TC-DOMAIN-009`: Task Definition Creation
- `TC-DOMAIN-010`: Task Execution
- `TC-DOMAIN-011`: Data Collection
- `TC-DOMAIN-012`: Multi-Tenancy Isolation
- `TC-DOMAIN-013`: Soft Delete
- `TC-DOMAIN-014`: Pagination and Filtering
- `TC-DOMAIN-015`: Audit Trail

**RESTful API Implementation Tests** (Section 3.4)
- `TC-API-001` to `TC-API-040`: Complete API endpoint testing
  - Organizations API (List, Statistics)
  - Devices API (List, Create, Update, Delete, Heartbeat, Telemetry)
  - Experiments API (List, Create, Start, Pause, Resume, Complete, Cancel)
  - Tasks API (List, Create, Update, Publish, Clone, Execute)
  - Participants API (List, Create, Update, Welfare Checks)
  - Error Handling (400, 401, 403, 404, 422, 500)
  - Rate Limiting, CORS, Performance

**WebSocket and Real-time Features Tests** (Section 3.5)
- `TC-WS-001` to `TC-WS-020`: WebSocket functionality
  - Connection, Authentication, Room Subscriptions
  - Device Events (Telemetry, Status, Heartbeat)
  - Experiment Events (State Changes, Progress, Data Collection)
  - Task Events (Execution Started, Progress, Completed)
  - Notification Events (User, Organization)
  - Reconnection, Permission Checks, Multi-client Support

**Background Tasks and Scheduling Tests** (Section 3.6)
- `TC-CELERY-001` to `TC-CELERY-025`: Celery task system
  - Worker Startup, Beat Scheduler
  - Data Processing Tasks (Experiment, Telemetry)
  - Notification Tasks (Email, Webhook, WebSocket)
  - Report Generation Tasks
  - Maintenance Tasks (Cleanup, Cache, Backup)
  - Task Patterns (Retry, Priority, Chaining, Groups, Revocation)
  - Monitoring (Flower, Prometheus Metrics)

#### Test Report Formats

**JSON Format** (Machine-readable):
```json
{
  "timestamp": "2025-10-16T12:00:00",
  "duration_seconds": 1200.5,
  "summary": {
    "total_tests": 125,
    "passed_tests": 118,
    "failed_tests": 2,
    "skipped_tests": 5,
    "success_rate": 94.40
  },
  "test_cases": {
    "TC-APP-001": {
      "name": "FastAPI Server Startup",
      "objective": "Validate FastAPI Server Startup functionality in Application Foundation",
      "passed": true,
      "duration_seconds": 0.053,
      "steps": [
        {
          "number": 1,
          "description": "Backend health check",
          "expected": "Step should complete successfully",
          "actual": "Status: 200, Response: {'status': 'healthy'}",
          "passed": true,
          "duration_ms": 5.2,
          "error": null
        }
      ],
      "category": "Application Foundation",
      "skipped": false,
      "error_message": null
    },
    "TC-AUTH-001": {...},
    "TC-DOMAIN-001": {...}
  }
}
```

**Markdown Format** (Human-readable report):
```markdown
# Phase 2 - Backend Core Development Test Execution

**Date**: 2025-10-16

## Tester Information
- **Name**: Automated Test Suite
- **Role**: Continuous Integration
- **Environment**: Development (Docker Containerized)

## System Configuration
- **OS**: Darwin 24.6.0
- **Docker Version**: Docker version 20.10.x
- **Available RAM**: 16.0 GB
- **Available Disk**: 250.0 GB

## Test Environment Status
- [x] Backend API running (http://localhost:8000)
- [x] PostgreSQL + TimescaleDB connected
- [x] Redis connected
- [x] MQTT broker operational
- [x] All services healthy

## Automated Test Results

### Application Foundation
- [✅] **TC-APP-001**: FastAPI Server Startup
  - Objective: Validate FastAPI Server Startup functionality
  - Duration: 0.05s
  - **Pass Rate**: 100.0% (5/5 tests passing)

### Authentication & Authorization
- [✅] **TC-AUTH-001**: User Registration
  - Objective: Validate User Registration functionality
  - Duration: 0.15s
...

## Performance Benchmarks
- **API Response Time (p95)**: 45.2 ms (target: < 200ms) ✅
- **WebSocket Latency**: 12.3 ms (target: < 50ms) ✅
- **Database Query Time (p95)**: 32.1 ms (target: < 100ms) ✅

## Overall Assessment
- **Test Pass Rate**: 94.4% (118/125 tests passed)
- **Critical Failures**: 2 (Target: 0)
- **Recommendation**: **PASS WITH CONDITIONS** - Minor issues detected

## Sign-off
- **Test Date**: 2025-10-16 12:00:00
- **Test Duration**: 1200.5s
- **Approval**: PASS WITH CONDITIONS
```

**HTML Format** (Interactive dashboard):
- 🎨 **Professional Design**: Gradient headers, card layouts, responsive grid
- 🟢 **Color-Coded Results**: Green (passed), red (failed), yellow (warning)
- 📊 **Executive Summary**: Large stat cards with key metrics
- 📋 **Test Details**: Expandable sections for each test category
- 🔍 **Step-by-Step View**: Individual test steps with timing
- ⚠️ **Error Highlighting**: Failed tests with error messages in red boxes
- 📈 **Performance Metrics**: Real-time performance data display
- 💡 **Smart Recommendations**: Context-aware suggestions based on results
- 📱 **Mobile Responsive**: Works on all screen sizes

**Sample HTML Features**:
```html
<!-- Executive Summary Dashboard -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-value">94.4%</div>
    <div class="stat-label">Success Rate</div>
  </div>
  ...
</div>

<!-- Color-Coded Test Results -->
<div class="test-case passed">
  <h3>✅ TC-AUTH-001: User Registration</h3>
  <p><strong>Duration:</strong> 0.15s</p>
  <div class="test-steps">
    <div class="step passed">
      ✅ Step 1: Creating test user
    </div>
  </div>
</div>
```

#### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run Phase 2 Automated Tests
  run: |
    make dev-detached
    sleep 60  # Wait for services to initialize

    # Run database migrations
    docker-compose -f docker-compose.dev.yml exec -T backend-dev alembic upgrade head

    # Run automated tests
    make test-phase2-full

- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: phase2-test-results
    path: test-results/

- name: Comment PR with Results
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const results = JSON.parse(fs.readFileSync('test-results/phase2_manual_latest.json'));
      const body = `## Phase 2 Test Results\n\n` +
        `✅ Passed: ${results.summary.passed_tests}\n` +
        `❌ Failed: ${results.summary.failed_tests}\n` +
        `⊘ Skipped: ${results.summary.skipped_tests}\n` +
        `📊 Success Rate: ${results.summary.success_rate}%`;
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: body
      });
```

#### Troubleshooting Automated Tests

**Issue**: Tests fail with "Backend not accessible"
```bash
# Solution: Ensure backend container is running
docker-compose -f docker-compose.dev.yml ps backend-dev
make dev

# Check backend logs
docker-compose -f docker-compose.dev.yml logs -f backend-dev
```

**Issue**: Tests timeout waiting for database
```bash
# Solution: Run migrations first (recommended method)
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py migrate

# Or use direct alembic (after container rebuild)
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head

# Verify database connection
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev -c "SELECT 1"
```

**Issue**: Authentication tests fail
```bash
# Solution: Ensure all dependencies are installed in backend container
docker-compose -f docker-compose.dev.yml exec backend-dev pip list | grep -E "(fastapi|pydantic|jose)"

# Rebuild backend if needed
docker-compose -f docker-compose.dev.yml up --build backend-dev
```

**Issue**: WebSocket tests fail with connection errors
```bash
# Solution: Verify WebSocket port is accessible
curl -I http://localhost:8001

# Check if backend is listening on WebSocket port
docker-compose -f docker-compose.dev.yml exec backend-dev netstat -tulpn | grep 8001
```

**Issue**: Celery tests fail with worker not found
```bash
# Solution: Start Celery worker
docker-compose -f docker-compose.dev.yml up -d celery-worker celery-beat

# Verify worker status
docker-compose -f docker-compose.dev.yml logs -f celery-worker
```

**Issue**: Missing Python dependencies
```bash
# Solution: Install required packages
pip install aiohttp websockets redis asyncpg

# Or use the backend container environment
docker-compose -f docker-compose.dev.yml exec backend-dev pip install -r requirements.txt
```

**Issue**: Tests fail with import errors
```bash
# Solution: Run tests from project root
cd /Users/beacon/Primates-lics
python3 tools/scripts/test-phase2-manual.py --verbose
```

#### Advantages Over Manual Testing

✅ **Speed**: 15-20 minutes vs 8+ hours manual testing
✅ **Consistency**: Same steps executed every time
✅ **Coverage**: Tests all 125 test cases automatically
✅ **Repeatability**: Can run multiple times per day
✅ **CI/CD Integration**: Automated validation in pipelines
✅ **Detailed Reports**: HTML dashboards with drill-down capabilities
✅ **Early Detection**: Catch regressions before production
✅ **Historical Comparison**: Track improvement over time
✅ **Parallel Execution**: Multiple test categories can run concurrently
✅ **No Human Error**: Eliminates manual testing mistakes

#### Known Limitations

✅ **Full Implementation**: All 125 test cases fully implemented and operational
⚠️ **Backend Dependency**: Requires fully operational backend with all services
⚠️ **Database State**: Tests may interfere with each other if not properly isolated
⚠️ **Real-time Testing**: WebSocket tests require stable network conditions
⚠️ **Celery Dependency**: Background task tests require Celery workers running

---

### 2.1 Running All Tests Inside Docker Container

**Basic Commands** (run from project root):
```bash
# Run all backend tests (standard output)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest

# Run tests with verbose output
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -v

# Run tests with very verbose output (recommended for debugging)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv
```

**Enhanced Verbose Commands** for debugging:
```bash
# Show print statements (capture=no)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -s

# Show local variables on failure
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --showlocals

# Show DEBUG level logs
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --log-cli-level=DEBUG

# Long traceback format (full details)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --tb=long

# Short traceback format (concise errors)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --tb=short

# RECOMMENDED: Maximum debugging information
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv -s --showlocals --log-cli-level=DEBUG --tb=long
```

**Expected Output**:
```
PASS  tests/unit/test_security.py ........................... [ 46 passed ]
PASS  tests/unit/test_domain_models.py ...................... [ 25 passed ]
PASS  tests/unit/test_background_tasks.py ................... [ 40 passed ]
PASS  tests/integration/test_auth_endpoints.py .............. [ 60 passed ]
PASS  tests/integration/test_rbac_endpoints.py .............. [ 30 passed ]
PASS  tests/integration/test_celery_workflow.py ............. [ 25 passed ]
PASS  tests/security/test_security_vulnerabilities.py ....... [ 20 passed ]

========= 246 passed in 45.23s =========
```

**Verbose Output Example** (`-vv`):
```
tests/unit/test_security.py::TestPasswordHashing::test_hash_password PASSED [ 1%]
tests/unit/test_security.py::TestPasswordHashing::test_verify_password_correct PASSED [ 2%]
tests/unit/test_security.py::TestPasswordHashing::test_verify_password_wrong PASSED [ 3%]
tests/unit/test_security.py::TestJWT::test_create_access_token PASSED [ 4%]
...
```

**Debug Output Example** (with `--log-cli-level=DEBUG`):
```
tests/unit/test_security.py::TestPasswordHashing::test_hash_password
-------------------------------- live log call ---------------------------------
DEBUG    app.core.security:security.py:45 Hashing password with bcrypt
DEBUG    app.core.security:security.py:52 Password hashed successfully
PASSED                                                               [ 1%]
```

### 2.2 Running Specific Test Suites

**Unit Tests Only**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/
```

**Integration Tests Only**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/integration/
```

**Security Tests Only**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/security/
```

**Specific Test File**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/test_security.py -v
```

**Specific Test Class**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/test_security.py::TestPasswordHashing -v
```

**Specific Test Function**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/test_security.py::TestPasswordHashing::test_verify_password_correct -v
```

### 2.3 Coverage Report

**Generate Coverage Inside Container**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --cov=app --cov-report=html
```

**Expected Coverage** (Target: >80%):
```
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
app/core/security.py                      150      5    97%
app/core/database.py                      100      8    92%
app/models/auth.py                        200     15    92%
app/models/domain.py                      350     30    91%
app/services/auth.py                      250     20    92%
app/api/v1/auth.py                        180     15    92%
app/api/v1/devices.py                     200     20    90%
app/websocket/server.py                   150     15    90%
app/tasks/celery_app.py                   120     10    92%
-----------------------------------------------------------
TOTAL                                    2500    200    92%
```

**View HTML Coverage Report**:
```bash
# Copy coverage report from container to local machine
docker cp $(docker-compose -f docker-compose.dev.yml ps -q backend-dev):/app/htmlcov ./backend-coverage-report

# Open in browser
open backend-coverage-report/index.html
```

### 2.4 Shell Script Testing

**Phase 2 Comprehensive Test**:
```bash
cd services/backend

# Standard output
./test_phase2.sh

# Verbose mode (detailed progress for each test)
./test_phase2.sh --verbose
./test_phase2.sh -v

# Debug mode (bash command tracing with set -x)
./test_phase2.sh --debug
./test_phase2.sh -d

# Show help
./test_phase2.sh --help
```

**Component-Specific Tests** (all support `--verbose` and `--debug`):
```bash
# Authentication system test
./test_auth.sh                  # Standard
./test_auth.sh --verbose        # Verbose
./test_auth.sh --debug          # Debug

# Domain models test
./test_domain.sh --verbose

# API endpoints test
./test_api.sh --debug

# WebSocket test
./test_websocket.sh --verbose

# Background tasks test
./test_background_tasks.sh --debug
```

**Verbose Shell Script Output Example**:
```
======================================================
   PHASE 2 COMPREHENSIVE TEST
   Backend Core Development (Weeks 3-4)
======================================================

[INFO] Verbose mode enabled

### TEST 1: Project Structure & Base Configuration

[STEP] Checking core files existence...
✓ app/main.py exists
  → Lines: 245
✓ app/core/config.py exists
  → Lines: 156
✓ app/core/security.py exists
  → Lines: 198
...
```

**Debug Shell Script Output Example** (with bash tracing):
```
+ echo 'Checking core files existence...'
Checking core files existence...
+ for file in "${files[@]}"
+ '[' -f app/main.py ']'
+ echo '✓ app/main.py exists'
✓ app/main.py exists
+ wc -l
+ lines=245
+ echo '  → Lines: 245'
  → Lines: 245
...
```

### 2.5 Watch Mode for Development

**Run tests in watch mode inside container**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --watch
```

**Run with pytest-watch**:
```bash
docker-compose -f docker-compose.dev.yml exec backend-dev ptw
```

---

## 3. Manual Testing Procedures

### 3.1 Week 3 Day 1-2: FastAPI Application Foundation

#### TC-APP-001: FastAPI Server Startup
**Steps**:
1. Start backend container: `make dev`
2. Check logs: `docker-compose -f docker-compose.dev.yml logs -f backend-dev`
3. Access API docs: http://localhost:8000/docs

**Expected Outcome**:
- ✅ Backend starts without errors
- ✅ Swagger UI accessible
- ✅ "Application startup complete" in logs
- ✅ Exit code: 0

**Actual Outcome**: ________________

---

#### TC-APP-002: Database Connection
**Steps**:
1. Open terminal in backend container
2. Run: `docker-compose -f docker-compose.dev.yml exec backend-dev python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"`
3. Check for errors

**Expected Outcome**:
- ✅ No connection errors
- ✅ Database connection successful
- ✅ TimescaleDB extension available

**Actual Outcome**: ________________

---

#### TC-APP-003: Health Check Endpoints
**Steps**:
1. Open browser or use curl
2. Test: `curl http://localhost:8000/api/v1/health`
3. Test: `curl http://localhost:8000/api/v1/health/database`
4. Test: `curl http://localhost:8000/api/v1/health/redis`

**Expected Outcome**:
- ✅ `/api/v1/health` returns 200 with status "healthy"
- ✅ `/api/v1/health/database` returns PostgreSQL status
- ✅ `/api/v1/health/redis` returns Redis status

**Actual Outcome**: ________________

---

#### TC-APP-004: API Versioning
**Steps**:
1. Check API structure in browser: http://localhost:8000/docs
2. Verify all endpoints start with `/api/v1/`
3. Check for version header in responses

**Expected Outcome**:
- ✅ All endpoints prefixed with `/api/v1/`
- ✅ Proper API versioning structure
- ✅ OpenAPI documentation shows version 1.0.0

**Actual Outcome**: ________________

---

#### TC-APP-005: Repository Pattern Implementation
**Steps**:
1. Review code structure in `app/repositories/`
2. Check base repository pattern
3. Verify CRUD operations

**Expected Outcome**:
- ✅ Base repository with generic CRUD methods
- ✅ Domain-specific repositories extend base
- ✅ Async SQLAlchemy 2.0 patterns used
- ✅ Proper transaction management

**Actual Outcome**: ________________

---

### 3.2 Week 3 Day 3-4: Authentication & Authorization

#### TC-AUTH-001: User Registration
**Steps**:
1. Open Swagger UI: http://localhost:8000/docs
2. Navigate to POST `/api/v1/auth/register`
3. Enter test data:
```json
{
  "email": "testuser@example.com",
  "username": "testuser",
  "password": "TestPassword123!",
  "first_name": "Test",
  "last_name": "User",
  "organization_id": "org-uuid-here"
}
```
4. Execute request

**Expected Outcome**:
- ✅ Status code: 201 Created
- ✅ User object returned with ID
- ✅ Password not included in response
- ✅ User stored in database

**Actual Outcome**: ________________

---

#### TC-AUTH-002: User Login
**Steps**:
1. POST `/api/v1/auth/login`
2. Enter credentials:
```json
{
  "email": "testuser@example.com",
  "password": "TestPassword123!"
}
```
3. Execute request

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Returns `access_token`, `refresh_token`, `token_type`
- ✅ Token type is "bearer"
- ✅ User object included in response

**Actual Outcome**: ________________

---

#### TC-AUTH-003: JWT Token Validation
**Steps**:
1. Login to get access token
2. Try accessing protected endpoint: GET `/api/v1/auth/me`
3. Include header: `Authorization: Bearer {access_token}`

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Current user information returned
- ✅ Token validated successfully

**Actual Outcome**: ________________

---

#### TC-AUTH-004: Invalid Token Handling
**Steps**:
1. Try accessing protected endpoint with invalid token
2. Header: `Authorization: Bearer invalid_token_here`

**Expected Outcome**:
- ✅ Status code: 401 Unauthorized
- ✅ Error message: "Could not validate credentials"
- ✅ No user data returned

**Actual Outcome**: ________________

---

#### TC-AUTH-005: Token Refresh
**Steps**:
1. Login to get `refresh_token`
2. POST `/api/v1/auth/refresh`
3. Body:
```json
{
  "refresh_token": "refresh_token_here"
}
```

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ New `access_token` returned
- ✅ New `refresh_token` returned
- ✅ Old tokens invalidated

**Actual Outcome**: ________________

---

#### TC-AUTH-006: Password Change
**Steps**:
1. Login to get access token
2. POST `/api/v1/auth/change-password`
3. Include auth header
4. Body:
```json
{
  "current_password": "TestPassword123!",
  "new_password": "NewPassword456!",
  "confirm_password": "NewPassword456!"
}
```

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Password updated in database
- ✅ Can login with new password
- ✅ Cannot login with old password

**Actual Outcome**: ________________

---

#### TC-AUTH-007: Password Reset Request
**Steps**:
1. POST `/api/v1/auth/request-password-reset`
2. Body:
```json
{
  "email": "testuser@example.com"
}
```

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Reset token generated
- ✅ Email sent (check MailHog: http://localhost:8025)

**Actual Outcome**: ________________

---

#### TC-AUTH-008: Password Reset Confirmation
**Steps**:
1. Get reset token from email/logs
2. POST `/api/v1/auth/confirm-password-reset`
3. Body:
```json
{
  "token": "reset_token_here",
  "new_password": "ResetPassword789!",
  "confirm_password": "ResetPassword789!"
}
```

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Password reset successfully
- ✅ Can login with new password

**Actual Outcome**: ________________

---

#### TC-AUTH-009: RBAC - Role Creation
**Steps**:
1. Login as admin user
2. POST `/api/v1/rbac/roles`
3. Body:
```json
{
  "name": "Researcher",
  "description": "Research staff role",
  "permissions": ["experiments:read", "experiments:write"]
}
```

**Expected Outcome**:
- ✅ Status code: 201 Created
- ✅ Role created with permissions
- ✅ Role ID returned

**Actual Outcome**: ________________

---

#### TC-AUTH-010: RBAC - Permission Assignment
**Steps**:
1. Create or get user ID
2. POST `/api/v1/rbac/users/{user_id}/roles`
3. Body:
```json
{
  "role_ids": ["role-uuid-1", "role-uuid-2"]
}
```

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Roles assigned to user
- ✅ User has combined permissions from all roles

**Actual Outcome**: ________________

---

#### TC-AUTH-011: RBAC - Permission Enforcement
**Steps**:
1. Login as user with limited permissions
2. Try accessing endpoint requiring different permission
3. Example: Try deleting device without "devices:delete" permission

**Expected Outcome**:
- ✅ Status code: 403 Forbidden
- ✅ Error message: "Insufficient permissions"
- ✅ Operation blocked

**Actual Outcome**: ________________

---

#### TC-AUTH-012: Multi-Factor Authentication Setup
**Steps**:
1. Login with valid credentials
2. POST `/api/v1/auth/mfa/enable`
3. Scan QR code with authenticator app

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ MFA secret returned
- ✅ QR code data provided
- ✅ Backup codes generated

**Actual Outcome**: ________________

---

#### TC-AUTH-013: MFA Login Flow
**Steps**:
1. Login with email/password
2. System prompts for TOTP code
3. Enter 6-digit code from authenticator app

**Expected Outcome**:
- ✅ Status code: 200 OK (after TOTP)
- ✅ Tokens issued after MFA verification
- ✅ Invalid TOTP code rejected

**Actual Outcome**: ________________

---

#### TC-AUTH-014: Session Management
**Steps**:
1. Login to create session
2. GET `/api/v1/auth/sessions`
3. Check active sessions

**Expected Outcome**:
- ✅ List of active sessions returned
- ✅ Session details: device, IP, last activity
- ✅ Can revoke sessions

**Actual Outcome**: ________________

---

#### TC-AUTH-015: User Profile Update
**Steps**:
1. Login to get access token
2. PUT `/api/v1/auth/profile`
3. Body:
```json
{
  "first_name": "Updated",
  "last_name": "Name",
  "timezone": "America/New_York"
}
```

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Profile updated in database
- ✅ Updated user object returned

**Actual Outcome**: ________________

---

#### TC-AUTH-016: Email Verification
**Steps**:
1. Register new user
2. Check email verification status
3. POST `/api/v1/auth/verify-email` with token

**Expected Outcome**:
- ✅ Verification email sent
- ✅ Token valid for 24 hours
- ✅ Email marked as verified after confirmation

**Actual Outcome**: ________________

---

#### TC-AUTH-017: Account Lockout
**Steps**:
1. Attempt login with wrong password 5 times
2. Try logging in with correct password

**Expected Outcome**:
- ✅ Account locked after 5 failed attempts
- ✅ Error message: "Account is locked"
- ✅ Lockout duration: 30 minutes

**Actual Outcome**: ________________

---

#### TC-AUTH-018: Logout
**Steps**:
1. Login to get access token
2. POST `/api/v1/auth/logout`
3. Include auth header

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Token blacklisted in Redis
- ✅ Cannot use token after logout

**Actual Outcome**: ________________

---

#### TC-AUTH-019: Concurrent Sessions
**Steps**:
1. Login from browser A
2. Login from browser B (different device)
3. Verify both sessions active

**Expected Outcome**:
- ✅ Multiple sessions allowed
- ✅ Each session has unique token
- ✅ Both sessions functional

**Actual Outcome**: ________________

---

#### TC-AUTH-020: Admin User Management
**Steps**:
1. Login as admin
2. GET `/api/v1/rbac/users`
3. Update user status: `PATCH /api/v1/rbac/users/{user_id}`

**Expected Outcome**:
- ✅ Admin can list all users
- ✅ Admin can activate/deactivate users
- ✅ Admin can assign roles
- ✅ Regular users cannot access these endpoints

**Actual Outcome**: ________________

---

### 3.3 Week 3 Day 5: Core Domain Models

#### TC-DOMAIN-001: Organization CRUD
**Steps**:
1. POST `/api/v1/organizations` - Create organization
2. GET `/api/v1/organizations` - List organizations
3. GET `/api/v1/organizations/{id}` - Get single organization
4. PUT `/api/v1/organizations/{id}` - Update organization
5. DELETE `/api/v1/organizations/{id}` - Delete organization

**Expected Outcome**:
- ✅ All CRUD operations work
- ✅ Proper validation on inputs
- ✅ Multi-tenancy enforced
- ✅ Organization settings persist

**Actual Outcome**: ________________

---

#### TC-DOMAIN-002: Device Registration
**Steps**:
1. POST `/api/v1/devices`
2. Body:
```json
{
  "name": "Lab Cage 1",
  "device_type": "raspberry_pi",
  "hardware_version": "4B",
  "software_version": "1.0.0",
  "organization_id": "org-uuid",
  "capabilities": {
    "camera": true,
    "rfid_reader": true,
    "feeder": true
  }
}
```

**Expected Outcome**:
- ✅ Status code: 201 Created
- ✅ Device ID assigned
- ✅ Device registered in database
- ✅ Initial status: "offline"

**Actual Outcome**: ________________

---

#### TC-DOMAIN-003: Device Status Updates
**Steps**:
1. POST `/api/v1/devices/{id}/heartbeat`
2. PATCH `/api/v1/devices/{id}/status`
3. Body: `{"status": "online"}`

**Expected Outcome**:
- ✅ Heartbeat updates `last_seen` timestamp
- ✅ Status changes from offline → online → busy → offline
- ✅ Status transitions validated

**Actual Outcome**: ________________

---

#### TC-DOMAIN-004: Device Telemetry
**Steps**:
1. POST `/api/v1/devices/{id}/telemetry`
2. Body:
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 60.5,
  "temperature": 42.3,
  "disk_usage": 35.0
}
```

**Expected Outcome**:
- ✅ Telemetry data stored
- ✅ Timestamp recorded
- ✅ Can query telemetry history

**Actual Outcome**: ________________

---

#### TC-DOMAIN-005: Experiment Creation
**Steps**:
1. POST `/api/v1/experiments`
2. Body:
```json
{
  "name": "Visual Discrimination Task",
  "description": "Testing color discrimination",
  "protocol": {...},
  "device_id": "device-uuid",
  "state": "draft"
}
```

**Expected Outcome**:
- ✅ Experiment created
- ✅ Initial state: "draft"
- ✅ Protocol schema validated
- ✅ Device association verified

**Actual Outcome**: ________________

---

#### TC-DOMAIN-006: Experiment Lifecycle
**Steps**:
1. Create experiment (state: draft)
2. POST `/api/v1/experiments/{id}/start` (draft → running)
3. POST `/api/v1/experiments/{id}/pause` (running → paused)
4. POST `/api/v1/experiments/{id}/resume` (paused → running)
5. POST `/api/v1/experiments/{id}/complete` (running → completed)

**Expected Outcome**:
- ✅ All state transitions work
- ✅ Invalid transitions rejected
- ✅ Timestamps recorded for each state change
- ✅ State history tracked

**Actual Outcome**: ________________

---

#### TC-DOMAIN-007: Participant (Primate) Management
**Steps**:
1. POST `/api/v1/participants`
2. Body:
```json
{
  "species": "rhesus_macaque",
  "identifier": "RM-001",
  "rfid_tag": "ABC123456789",
  "date_of_birth": "2020-01-15",
  "sex": "male",
  "training_level": "intermediate"
}
```

**Expected Outcome**:
- ✅ Primate registered
- ✅ RFID tag unique constraint
- ✅ Species validation
- ✅ Age calculated automatically

**Actual Outcome**: ________________

---

#### TC-DOMAIN-008: Participant Welfare Checks
**Steps**:
1. POST `/api/v1/participants/{id}/welfare-checks`
2. Body:
```json
{
  "weight": 8.5,
  "health_status": "healthy",
  "notes": "Active and alert",
  "checked_by": "user-uuid"
}
```

**Expected Outcome**:
- ✅ Welfare check recorded
- ✅ Weight tracking over time
- ✅ Health status updates
- ✅ IACUC compliance tracking

**Actual Outcome**: ________________

---

#### TC-DOMAIN-009: Task Definition Creation
**Steps**:
1. POST `/api/v1/tasks`
2. Body:
```json
{
  "name": "Fixation Task",
  "category": "cognitive",
  "version": "1.0.0",
  "definition": {
    "nodes": [...],
    "edges": [...]
  },
  "result_schema": {...}
}
```

**Expected Outcome**:
- ✅ Task definition saved
- ✅ JSON schema validated
- ✅ Version control working
- ✅ Can be assigned to experiments

**Actual Outcome**: ________________

---

#### TC-DOMAIN-010: Task Execution
**Steps**:
1. POST `/api/v1/tasks/{id}/execute`
2. Body:
```json
{
  "experiment_id": "exp-uuid",
  "participant_id": "primate-uuid",
  "device_id": "device-uuid"
}
```

**Expected Outcome**:
- ✅ Task execution started
- ✅ Execution record created
- ✅ Progress tracked
- ✅ Results collected

**Actual Outcome**: ________________

---

#### TC-DOMAIN-011: Data Collection
**Steps**:
1. During task execution, device sends trial results
2. POST `/api/v1/experiments/{id}/data`
3. Verify data stored in database

**Expected Outcome**:
- ✅ Trial data stored
- ✅ Timestamp recorded
- ✅ Associated with correct experiment
- ✅ Result schema validated

**Actual Outcome**: ________________

---

#### TC-DOMAIN-012: Multi-Tenancy Isolation
**Steps**:
1. Login as User A (Organization 1)
2. Create device
3. Login as User B (Organization 2)
4. Try to access User A's device

**Expected Outcome**:
- ✅ User B cannot see User A's devices
- ✅ Status code: 404 Not Found (not 403 to avoid information leak)
- ✅ Organization isolation enforced

**Actual Outcome**: ________________

---

#### TC-DOMAIN-013: Soft Delete
**Steps**:
1. Create a device
2. DELETE `/api/v1/devices/{id}`
3. Try to GET the deleted device
4. Check database: device has `deleted_at` timestamp

**Expected Outcome**:
- ✅ Device marked as deleted (not physically removed)
- ✅ GET returns 404
- ✅ Can restore if needed
- ✅ Soft delete implemented

**Actual Outcome**: ________________

---

#### TC-DOMAIN-014: Pagination and Filtering
**Steps**:
1. Create 25 devices
2. GET `/api/v1/devices?page=1&page_size=10`
3. GET `/api/v1/devices?page=2&page_size=10`
4. GET `/api/v1/devices?status=online&device_type=raspberry_pi`

**Expected Outcome**:
- ✅ Pagination works correctly
- ✅ Total count returned
- ✅ Filtering by multiple fields works
- ✅ Performance acceptable

**Actual Outcome**: ________________

---

#### TC-DOMAIN-015: Audit Trail
**Steps**:
1. Create/update/delete entities
2. Check `created_at`, `updated_at`, `created_by`, `updated_by` fields
3. Verify timestamps accurate

**Expected Outcome**:
- ✅ All entities have audit fields
- ✅ Timestamps auto-populated
- ✅ User associations tracked
- ✅ Can query by date ranges

**Actual Outcome**: ________________

---

### 3.4 Week 4 Day 1-2: RESTful API Implementation

#### TC-API-001: Organizations API - List
**Steps**:
1. GET `/api/v1/organizations`
2. Include auth header

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Array of organizations returned
- ✅ Pagination metadata included
- ✅ Only user's organization(s) visible

**Actual Outcome**: ________________

---

#### TC-API-002: Organizations API - Statistics
**Steps**:
1. GET `/api/v1/organizations/{id}/statistics`

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Returns: device count, experiment count, user count
- ✅ Accurate statistics

**Actual Outcome**: ________________

---

#### TC-API-003: Devices API - List with Filters
**Steps**:
1. GET `/api/v1/devices?status=online`
2. GET `/api/v1/devices?device_type=raspberry_pi`
3. GET `/api/v1/devices?organization_id=org-uuid`

**Expected Outcome**:
- ✅ Filters work correctly
- ✅ Multiple filters can be combined
- ✅ Empty result set handled gracefully

**Actual Outcome**: ________________

---

#### TC-API-004: Devices API - Create
**Steps**:
1. POST `/api/v1/devices`
2. Include all required fields

**Expected Outcome**:
- ✅ Status code: 201 Created
- ✅ Location header with resource URL
- ✅ Created device returned in response

**Actual Outcome**: ________________

---

#### TC-API-005: Devices API - Update
**Steps**:
1. PUT `/api/v1/devices/{id}`
2. Update name and configuration

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ Changes persisted in database
- ✅ Updated entity returned

**Actual Outcome**: ________________

---

#### TC-API-006: Devices API - Delete
**Steps**:
1. DELETE `/api/v1/devices/{id}`

**Expected Outcome**:
- ✅ Status code: 204 No Content
- ✅ Device soft-deleted
- ✅ Cannot retrieve deleted device

**Actual Outcome**: ________________

---

#### TC-API-007: Devices API - Heartbeat
**Steps**:
1. POST `/api/v1/devices/{id}/heartbeat`

**Expected Outcome**:
- ✅ Status code: 200 OK
- ✅ `last_seen` timestamp updated
- ✅ Device status may change to online

**Actual Outcome**: ________________

---

#### TC-API-008: Devices API - Telemetry Collection
**Steps**:
1. POST `/api/v1/devices/{id}/telemetry`
2. Include metrics: CPU, memory, temperature

**Expected Outcome**:
- ✅ Status code: 201 Created
- ✅ Telemetry data stored
- ✅ Can query telemetry history

**Actual Outcome**: ________________

---

#### TC-API-009: Devices API - Get Telemetry
**Steps**:
1. GET `/api/v1/devices/{id}/telemetry?start_date=2025-01-01&end_date=2025-12-31`

**Expected Outcome**:
- ✅ Time-series data returned
- ✅ Date range filtering works
- ✅ Aggregation options available

**Actual Outcome**: ________________

---

#### TC-API-010: Experiments API - List
**Steps**:
1. GET `/api/v1/experiments`

**Expected Outcome**:
- ✅ All accessible experiments returned
- ✅ Pagination works
- ✅ Filter by state, device, date

**Actual Outcome**: ________________

---

#### TC-API-011: Experiments API - Create
**Steps**:
1. POST `/api/v1/experiments`
2. Include protocol and device assignment

**Expected Outcome**:
- ✅ Status code: 201 Created
- ✅ Experiment ID generated
- ✅ Initial state: "draft"

**Actual Outcome**: ________________

---

#### TC-API-012: Experiments API - Start
**Steps**:
1. POST `/api/v1/experiments/{id}/start`

**Expected Outcome**:
- ✅ State changes: draft → running
- ✅ Start timestamp recorded
- ✅ Cannot start already running experiment

**Actual Outcome**: ________________

---

#### TC-API-013: Experiments API - Pause
**Steps**:
1. POST `/api/v1/experiments/{id}/pause`

**Expected Outcome**:
- ✅ State changes: running → paused
- ✅ Pause timestamp recorded
- ✅ Can resume later

**Actual Outcome**: ________________

---

#### TC-API-014: Experiments API - Resume
**Steps**:
1. POST `/api/v1/experiments/{id}/resume`

**Expected Outcome**:
- ✅ State changes: paused → running
- ✅ Resume timestamp recorded

**Actual Outcome**: ________________

---

#### TC-API-015: Experiments API - Complete
**Steps**:
1. POST `/api/v1/experiments/{id}/complete`

**Expected Outcome**:
- ✅ State changes: running → completed
- ✅ Completion timestamp recorded
- ✅ Cannot modify completed experiment

**Actual Outcome**: ________________

---

#### TC-API-016: Experiments API - Cancel
**Steps**:
1. POST `/api/v1/experiments/{id}/cancel`

**Expected Outcome**:
- ✅ State changes to cancelled
- ✅ Can cancel from any state except completed
- ✅ Cancellation reason recorded

**Actual Outcome**: ________________

---

#### TC-API-017: Experiments API - Participant Assignment
**Steps**:
1. POST `/api/v1/experiments/{id}/participants`
2. Body: `{"participant_id": "primate-uuid"}`

**Expected Outcome**:
- ✅ Participant assigned to experiment
- ✅ Association tracked
- ✅ Can have multiple participants

**Actual Outcome**: ________________

---

#### TC-API-018: Experiments API - Data Collection
**Steps**:
1. POST `/api/v1/experiments/{id}/data`
2. Submit trial results

**Expected Outcome**:
- ✅ Data stored
- ✅ Timestamp recorded
- ✅ Associated with experiment and participant

**Actual Outcome**: ________________

---

#### TC-API-019: Tasks API - List
**Steps**:
1. GET `/api/v1/tasks`

**Expected Outcome**:
- ✅ All accessible tasks returned
- ✅ Filter by category, version, published status

**Actual Outcome**: ________________

---

#### TC-API-020: Tasks API - Create
**Steps**:
1. POST `/api/v1/tasks`
2. Include task definition JSON

**Expected Outcome**:
- ✅ Task created
- ✅ JSON schema validated
- ✅ Version assigned

**Actual Outcome**: ________________

---

#### TC-API-021: Tasks API - Update
**Steps**:
1. PUT `/api/v1/tasks/{id}`

**Expected Outcome**:
- ✅ Task updated
- ✅ Version incremented if published
- ✅ Old version preserved

**Actual Outcome**: ________________

---

#### TC-API-022: Tasks API - Publish
**Steps**:
1. POST `/api/v1/tasks/{id}/publish`

**Expected Outcome**:
- ✅ Task marked as published
- ✅ Available in marketplace
- ✅ Cannot modify published task (must create new version)

**Actual Outcome**: ________________

---

#### TC-API-023: Tasks API - Clone
**Steps**:
1. POST `/api/v1/tasks/{id}/clone`

**Expected Outcome**:
- ✅ New task created as copy
- ✅ New ID assigned
- ✅ Version reset to 1.0.0

**Actual Outcome**: ________________

---

#### TC-API-024: Tasks API - Execute
**Steps**:
1. POST `/api/v1/tasks/{id}/execute`
2. Include device and participant

**Expected Outcome**:
- ✅ Task execution started
- ✅ Execution record created
- ✅ Device receives task definition

**Actual Outcome**: ________________

---

#### TC-API-025: Tasks API - Execution History
**Steps**:
1. GET `/api/v1/tasks/{id}/executions`

**Expected Outcome**:
- ✅ All executions returned
- ✅ Includes status, results, timestamps
- ✅ Pagination works

**Actual Outcome**: ________________

---

#### TC-API-026: Participants API - List
**Steps**:
1. GET `/api/v1/participants`

**Expected Outcome**:
- ✅ All primates returned
- ✅ Filter by species, training level, status

**Actual Outcome**: ________________

---

#### TC-API-027: Participants API - Create
**Steps**:
1. POST `/api/v1/participants`
2. Include species, RFID, demographics

**Expected Outcome**:
- ✅ Primate registered
- ✅ RFID tag unique
- ✅ Status: "active"

**Actual Outcome**: ________________

---

#### TC-API-028: Participants API - Update
**Steps**:
1. PUT `/api/v1/participants/{id}`

**Expected Outcome**:
- ✅ Primate information updated
- ✅ Training level can be changed
- ✅ History preserved

**Actual Outcome**: ________________

---

#### TC-API-029: Participants API - Welfare Check
**Steps**:
1. POST `/api/v1/participants/{id}/welfare-checks`

**Expected Outcome**:
- ✅ Welfare check recorded
- ✅ Weight, health status tracked
- ✅ IACUC compliance verified

**Actual Outcome**: ________________

---

#### TC-API-030: Participants API - Experiment History
**Steps**:
1. GET `/api/v1/participants/{id}/experiments`

**Expected Outcome**:
- ✅ All experiments for this primate
- ✅ Includes performance data
- ✅ Learning curve visible

**Actual Outcome**: ________________

---

#### TC-API-031: Participants API - Session Limits
**Steps**:
1. Try to start more sessions than daily limit
2. Check welfare alert

**Expected Outcome**:
- ✅ Session limit enforced
- ✅ Error message displayed
- ✅ Welfare alert generated

**Actual Outcome**: ________________

---

#### TC-API-032: API Error Handling - 400 Bad Request
**Steps**:
1. Send invalid data to endpoint
2. Example: Missing required field

**Expected Outcome**:
- ✅ Status code: 400
- ✅ Error message describes issue
- ✅ Validation errors listed

**Actual Outcome**: ________________

---

#### TC-API-033: API Error Handling - 401 Unauthorized
**Steps**:
1. Try accessing protected endpoint without token

**Expected Outcome**:
- ✅ Status code: 401
- ✅ Error message: "Not authenticated"

**Actual Outcome**: ________________

---

#### TC-API-034: API Error Handling - 403 Forbidden
**Steps**:
1. Try accessing resource without permission

**Expected Outcome**:
- ✅ Status code: 403
- ✅ Error message: "Insufficient permissions"

**Actual Outcome**: ________________

---

#### TC-API-035: API Error Handling - 404 Not Found
**Steps**:
1. Try accessing non-existent resource

**Expected Outcome**:
- ✅ Status code: 404
- ✅ Error message: "Resource not found"

**Actual Outcome**: ________________

---

#### TC-API-036: API Error Handling - 422 Unprocessable Entity
**Steps**:
1. Send data with validation errors

**Expected Outcome**:
- ✅ Status code: 422
- ✅ Detailed validation errors returned

**Actual Outcome**: ________________

---

#### TC-API-037: API Error Handling - 500 Internal Server Error
**Steps**:
1. Trigger server error (disconnect database)
2. Try API request

**Expected Outcome**:
- ✅ Status code: 500
- ✅ Generic error message (no stack trace)
- ✅ Error logged for debugging

**Actual Outcome**: ________________

---

#### TC-API-038: API Rate Limiting
**Steps**:
1. Make 100 requests to same endpoint rapidly
2. Check if rate limit kicks in

**Expected Outcome**:
- ✅ After threshold, returns 429 Too Many Requests
- ✅ Retry-After header included
- ✅ Rate limit resets after time window

**Actual Outcome**: ________________

---

#### TC-API-039: API CORS Headers
**Steps**:
1. Make OPTIONS request to endpoint
2. Check response headers

**Expected Outcome**:
- ✅ Access-Control-Allow-Origin present
- ✅ Access-Control-Allow-Methods includes GET, POST, PUT, DELETE
- ✅ Access-Control-Allow-Headers includes Authorization

**Actual Outcome**: ________________

---

#### TC-API-040: API Performance
**Steps**:
1. Time 100 sequential API requests
2. Measure average response time

**Expected Outcome**:
- ✅ Average response time < 200ms
- ✅ No memory leaks
- ✅ Connection pool stable

**Actual Outcome**: ________________

---

### 3.5 Week 4 Day 3-4: WebSocket and Real-time Features

#### TC-WS-001: WebSocket Connection
**Steps**:
1. Use Socket.IO client to connect
2. URL: `ws://localhost:8001`
3. Include JWT token in auth header

**Expected Outcome**:
- ✅ Connection successful
- ✅ Status: "connected"
- ✅ Handshake complete

**Actual Outcome**: ________________

---

#### TC-WS-002: WebSocket Authentication
**Steps**:
1. Try connecting without token
2. Try connecting with invalid token
3. Connect with valid token

**Expected Outcome**:
- ✅ No token: Connection rejected
- ✅ Invalid token: Connection rejected
- ✅ Valid token: Connection accepted

**Actual Outcome**: ________________

---

#### TC-WS-003: Room Subscription - Device
**Steps**:
1. Connect to WebSocket
2. Emit: `{"event": "subscribe", "room": "device:device-uuid"}`

**Expected Outcome**:
- ✅ Subscription confirmed
- ✅ Joined device room
- ✅ Receives device events

**Actual Outcome**: ________________

---

#### TC-WS-004: Room Subscription - Experiment
**Steps**:
1. Connect to WebSocket
2. Emit: `{"event": "subscribe", "room": "experiment:exp-uuid"}`

**Expected Outcome**:
- ✅ Subscription confirmed
- ✅ Joined experiment room
- ✅ Receives experiment events

**Actual Outcome**: ________________

---

#### TC-WS-005: Room Subscription - Organization
**Steps**:
1. Connect to WebSocket
2. Emit: `{"event": "subscribe", "room": "organization:org-uuid"}`

**Expected Outcome**:
- ✅ Subscription confirmed
- ✅ Receives org-wide events

**Actual Outcome**: ________________

---

#### TC-WS-006: Device Telemetry Events
**Steps**:
1. Subscribe to device room
2. Device sends telemetry via API
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `device:telemetry`
- ✅ Payload includes metrics
- ✅ Real-time (< 100ms latency)

**Actual Outcome**: ________________

---

#### TC-WS-007: Device Status Events
**Steps**:
1. Subscribe to device room
2. Update device status via API
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `device:status_changed`
- ✅ Payload includes old and new status
- ✅ Timestamp included

**Actual Outcome**: ________________

---

#### TC-WS-008: Device Heartbeat Events
**Steps**:
1. Subscribe to device room
2. Device sends heartbeat
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `device:heartbeat`
- ✅ Real-time indicator updates

**Actual Outcome**: ________________

---

#### TC-WS-009: Experiment State Change Events
**Steps**:
1. Subscribe to experiment room
2. Change experiment state via API (start/pause/complete)
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `experiment:state_changed`
- ✅ Payload includes old and new state
- ✅ All subscribers notified

**Actual Outcome**: ________________

---

#### TC-WS-010: Experiment Progress Events
**Steps**:
1. Subscribe to experiment room
2. Submit trial data
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `experiment:progress`
- ✅ Payload includes completion percentage
- ✅ Real-time progress bar updates

**Actual Outcome**: ________________

---

#### TC-WS-011: Experiment Data Collected Events
**Steps**:
1. Subscribe to experiment room
2. Device submits trial results
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `experiment:data_collected`
- ✅ Payload includes trial summary
- ✅ Dashboard updates in real-time

**Actual Outcome**: ________________

---

#### TC-WS-012: Task Execution Started Events
**Steps**:
1. Subscribe to task room
2. Start task execution via API
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `task:execution_started`
- ✅ Payload includes execution ID
- ✅ UI shows task as running

**Actual Outcome**: ________________

---

#### TC-WS-013: Task Execution Progress Events
**Steps**:
1. Subscribe to task room
2. Task sends progress updates
3. Wait for WebSocket events

**Expected Outcome**:
- ✅ Event received: `task:execution_progress`
- ✅ Payload includes percentage
- ✅ Progress bar updates

**Actual Outcome**: ________________

---

#### TC-WS-014: Task Execution Completed Events
**Steps**:
1. Subscribe to task room
2. Task completes
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `task:execution_completed`
- ✅ Payload includes results
- ✅ UI shows completion

**Actual Outcome**: ________________

---

#### TC-WS-015: Notification Events - User
**Steps**:
1. Subscribe to user notifications room
2. Trigger notification (experiment complete, alert, etc.)
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `notification:user`
- ✅ Notification displayed in UI
- ✅ Unread count updates

**Actual Outcome**: ________________

---

#### TC-WS-016: Notification Events - Organization
**Steps**:
1. Subscribe to organization room
2. Admin sends org-wide notification
3. Wait for WebSocket event

**Expected Outcome**:
- ✅ Event received: `notification:organization`
- ✅ All org members notified

**Actual Outcome**: ________________

---

#### TC-WS-017: WebSocket Reconnection
**Steps**:
1. Connect to WebSocket
2. Disconnect network
3. Reconnect network
4. Check if connection re-establishes

**Expected Outcome**:
- ✅ Automatic reconnection attempted
- ✅ Exponential backoff implemented
- ✅ Subscriptions restored after reconnect

**Actual Outcome**: ________________

---

#### TC-WS-018: WebSocket Permission Check
**Steps**:
1. Connect as User A
2. Try subscribing to User B's private room

**Expected Outcome**:
- ✅ Subscription denied
- ✅ Error message: "Insufficient permissions"
- ✅ Security enforced

**Actual Outcome**: ________________

---

#### TC-WS-019: Multiple Connections
**Steps**:
1. Connect from browser A
2. Connect from browser B (same user)
3. Verify both receive events

**Expected Outcome**:
- ✅ Both connections active
- ✅ Both receive events
- ✅ No conflicts

**Actual Outcome**: ________________

---

#### TC-WS-020: WebSocket Disconnect
**Steps**:
1. Connect to WebSocket
2. Manually disconnect
3. Check cleanup

**Expected Outcome**:
- ✅ Connection closed gracefully
- ✅ Subscriptions cleaned up
- ✅ No memory leaks

**Actual Outcome**: ________________

---

### 3.6 Week 4 Day 5: Background Tasks and Scheduling

#### TC-CELERY-001: Celery Worker Startup
**Steps**:
1. Start Celery workers: `docker-compose -f docker-compose.dev.yml up -d celery-worker`
2. Check logs: `docker-compose -f docker-compose.dev.yml logs -f celery-worker`

**Expected Outcome**:
- ✅ Workers start successfully
- ✅ Connected to Redis broker
- ✅ Registered tasks visible in logs

**Actual Outcome**: ________________

---

#### TC-CELERY-002: Celery Beat Scheduler
**Steps**:
1. Start Celery Beat: `docker-compose -f docker-compose.dev.yml up -d celery-beat`
2. Check logs for scheduled tasks

**Expected Outcome**:
- ✅ Scheduler starts successfully
- ✅ Periodic tasks listed
- ✅ Schedule adhered to

**Actual Outcome**: ________________

---

#### TC-CELERY-003: Task - Process Experiment Data
**Steps**:
1. Trigger task: `process_experiment_data.delay(experiment_id)`
2. Monitor execution in Flower: http://localhost:5555

**Expected Outcome**:
- ✅ Task queued
- ✅ Task executed
- ✅ Status: SUCCESS
- ✅ Data aggregated correctly

**Actual Outcome**: ________________

---

#### TC-CELERY-004: Task - Process Device Telemetry
**Steps**:
1. Trigger task: `process_device_telemetry.delay(device_id)`
2. Check InfluxDB for stored data

**Expected Outcome**:
- ✅ Telemetry processed
- ✅ Data stored in InfluxDB
- ✅ Batch processing working

**Actual Outcome**: ________________

---

#### TC-CELERY-005: Task - Cleanup Old Data
**Steps**:
1. Trigger task: `cleanup_old_data.delay()`
2. Check database for deleted records

**Expected Outcome**:
- ✅ Old data removed (>90 days)
- ✅ Recent data preserved
- ✅ Cleanup stats logged

**Actual Outcome**: ________________

---

#### TC-CELERY-006: Task - Send Email Notification
**Steps**:
1. Trigger task: `send_email_notification.delay(user_id, subject, body)`
2. Check MailHog: http://localhost:8025

**Expected Outcome**:
- ✅ Email sent successfully
- ✅ Visible in MailHog inbox
- ✅ Content correct

**Actual Outcome**: ________________

---

#### TC-CELERY-007: Task - Send Webhook Notification
**Steps**:
1. Set up webhook endpoint
2. Trigger task: `send_webhook_notification.delay(url, payload)`
3. Verify webhook received

**Expected Outcome**:
- ✅ HTTP POST sent to webhook URL
- ✅ Payload correct
- ✅ Retry on failure

**Actual Outcome**: ________________

---

#### TC-CELERY-008: Task - Send WebSocket Notification
**Steps**:
1. Connect WebSocket client
2. Trigger task: `send_websocket_notification.delay(user_id, message)`
3. Verify WebSocket event received

**Expected Outcome**:
- ✅ WebSocket event emitted
- ✅ User receives notification
- ✅ Real-time delivery

**Actual Outcome**: ________________

---

#### TC-CELERY-009: Task - Generate Experiment Report
**Steps**:
1. Trigger task: `generate_experiment_report.delay(experiment_id, format="pdf")`
2. Check MinIO for generated file

**Expected Outcome**:
- ✅ Report generated
- ✅ Stored in MinIO bucket
- ✅ Download link provided

**Actual Outcome**: ________________

---

#### TC-CELERY-010: Task - Generate Participant Progress Report
**Steps**:
1. Trigger task: `generate_participant_progress_report.delay(primate_id)`
2. Check report contents

**Expected Outcome**:
- ✅ Learning curve calculated
- ✅ Performance metrics included
- ✅ Charts generated

**Actual Outcome**: ________________

---

#### TC-CELERY-011: Task - Export Data to Storage
**Steps**:
1. Trigger task: `export_data_to_storage.delay(experiment_id, format="csv")`
2. Check MinIO for exported file

**Expected Outcome**:
- ✅ Data exported
- ✅ CSV format correct
- ✅ All data included

**Actual Outcome**: ________________

---

#### TC-CELERY-012: Task - Cleanup Expired Sessions
**Steps**:
1. Create expired session
2. Trigger task: `cleanup_expired_sessions.delay()`
3. Verify session removed

**Expected Outcome**:
- ✅ Expired sessions deleted from DB
- ✅ Expired sessions removed from Redis
- ✅ Active sessions preserved

**Actual Outcome**: ________________

---

#### TC-CELERY-013: Task - Refresh Cache Warmup
**Steps**:
1. Clear Redis cache
2. Trigger task: `refresh_cache_warmup.delay()`
3. Check Redis for cached data

**Expected Outcome**:
- ✅ Frequently accessed data cached
- ✅ Cache keys set correctly
- ✅ TTL set appropriately

**Actual Outcome**: ________________

---

#### TC-CELERY-014: Task - Backup Database
**Steps**:
1. Trigger task: `backup_database_incremental.delay()`
2. Check backup storage

**Expected Outcome**:
- ✅ Backup created
- ✅ Stored in MinIO
- ✅ Backup file readable

**Actual Outcome**: ________________

---

#### TC-CELERY-015: Task - Update Device Status
**Steps**:
1. Stop sending heartbeats for device
2. Wait for task: `update_device_status.delay()`
3. Check device status

**Expected Outcome**:
- ✅ Device marked offline after timeout
- ✅ Heartbeat monitoring working
- ✅ Status change logged

**Actual Outcome**: ________________

---

#### TC-CELERY-016: Task Retry Mechanism
**Steps**:
1. Trigger task that fails temporarily
2. Monitor retry attempts in Flower

**Expected Outcome**:
- ✅ Task retried automatically
- ✅ Exponential backoff applied
- ✅ Max retries respected
- ✅ Eventually succeeds or fails permanently

**Actual Outcome**: ________________

---

#### TC-CELERY-017: Task Priority Queues
**Steps**:
1. Queue high priority task
2. Queue low priority task
3. Monitor execution order

**Expected Outcome**:
- ✅ High priority task executed first
- ✅ Queue routing working
- ✅ Priority respected

**Actual Outcome**: ________________

---

#### TC-CELERY-018: Task Chaining
**Steps**:
1. Chain tasks: `process_data.apply_async().then(generate_report.s())`
2. Monitor execution

**Expected Outcome**:
- ✅ First task completes
- ✅ Second task starts automatically
- ✅ Data passed between tasks

**Actual Outcome**: ________________

---

#### TC-CELERY-019: Task Groups
**Steps**:
1. Execute task group: `group([task1.s(), task2.s(), task3.s()])()`
2. Monitor parallel execution

**Expected Outcome**:
- ✅ All tasks executed in parallel
- ✅ Results collected
- ✅ Performance improved

**Actual Outcome**: ________________

---

#### TC-CELERY-020: Task Revocation
**Steps**:
1. Start long-running task
2. Revoke task: `celery_app.control.revoke(task_id)`
3. Monitor task status

**Expected Outcome**:
- ✅ Task terminated
- ✅ Status: REVOKED
- ✅ Cleanup performed

**Actual Outcome**: ________________

---

#### TC-CELERY-021: Flower Monitoring UI
**Steps**:
1. Open Flower: http://localhost:5555
2. Login: admin / admin123
3. Browse tasks, workers, queues

**Expected Outcome**:
- ✅ Flower accessible
- ✅ Real-time task monitoring
- ✅ Worker statistics visible
- ✅ Can inspect task details

**Actual Outcome**: ________________

---

#### TC-CELERY-022: Prometheus Metrics
**Steps**:
1. Access metrics: `curl http://localhost:8000/api/v1/health/metrics`
2. Check for Celery metrics

**Expected Outcome**:
- ✅ Task execution counters present
- ✅ Task duration histograms present
- ✅ Queue size metrics present
- ✅ Metrics format correct (Prometheus)

**Actual Outcome**: ________________

---

#### TC-CELERY-023: Periodic Task - Cleanup
**Steps**:
1. Wait for scheduled cleanup task to run
2. Check logs and results

**Expected Outcome**:
- ✅ Task runs on schedule (e.g., daily at 2 AM)
- ✅ Cleanup performed
- ✅ Next run scheduled

**Actual Outcome**: ________________

---

#### TC-CELERY-024: Periodic Task - Analytics
**Steps**:
1. Wait for scheduled analytics task
2. Check generated analytics

**Expected Outcome**:
- ✅ Task runs on schedule (e.g., hourly)
- ✅ Analytics computed
- ✅ Data updated

**Actual Outcome**: ________________

---

#### TC-CELERY-025: Task Monitoring API
**Steps**:
1. GET `/api/v1/background-tasks/status/{task_id}`
2. GET `/api/v1/background-tasks/active`
3. GET `/api/v1/background-tasks/stats`

**Expected Outcome**:
- ✅ Task status retrieved
- ✅ Active tasks listed
- ✅ Queue statistics available

**Actual Outcome**: ________________

---

## 4. Expected Outcomes Summary

### 4.1 Automated Test Results

| Test Suite | Expected Pass Rate | Coverage Target | Test Count |
|------------|-------------------|-----------------|------------|
| Unit Tests - Security | 100% (46/46 tests) | 97% | 46 |
| Unit Tests - Models | 100% (25/25 tests) | 92% | 25 |
| Unit Tests - Background Tasks | 100% (40/40 tests) | 92% | 40 |
| Integration - Auth Endpoints | 100% (60/60 tests) | 90% | 60 |
| Integration - RBAC | 100% (30/30 tests) | 90% | 30 |
| Integration - Celery | 100% (25/25 tests) | 88% | 25 |
| Security Tests | 100% (20/20 tests) | N/A | 20 |
| **Total** | **100% (246/246 tests)** | **>92% overall** | **246** |

### 4.2 Manual Test Results

| Category | Test Cases | Expected Pass Rate |
|----------|-----------|-------------------|
| Application Foundation | 5 | 100% (5/5) |
| Authentication & Authorization | 20 | 100% (20/20) |
| Core Domain Models | 15 | 100% (15/15) |
| RESTful API Implementation | 40 | 100% (40/40) |
| WebSocket & Real-time | 20 | 100% (20/20) |
| Background Tasks (Celery) | 25 | 100% (25/25) |
| **Total** | **125** | **100% (125/125)** |

### 4.3 Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| API Response Time (p95) | < 200ms | Locust/K6 load testing |
| API Response Time (p99) | < 500ms | Locust/K6 load testing |
| WebSocket Latency | < 50ms | Custom timing tests |
| Database Query Time (p95) | < 100ms | PostgreSQL logs |
| Background Task Processing | < 5s (simple tasks) | Celery monitoring |
| Concurrent API Connections | 1,000+ | Load testing |
| WebSocket Concurrent Connections | 10,000+ | Socket.IO stress test |

### 4.4 Code Quality Metrics

| Metric | Target | Tool |
|--------|--------|------|
| Test Coverage | >80% | pytest-cov |
| Code Complexity (Cyclomatic) | <10 per function | radon |
| Code Duplication | <3% | pylint |
| Security Vulnerabilities | 0 critical/high | bandit, safety |
| Type Coverage | >90% | mypy |
| Linting Score | 9.0+/10.0 | pylint |

---

## 5. Test Results Recording

### Test Execution Log Template

```markdown
## Test Execution - [Date]

### Tester Information
- Name: ________________
- Role: ________________
- Environment: Development / Staging / Production

### System Configuration
- Backend API: Running / Stopped
- PostgreSQL: Connected / Disconnected
- Redis: Connected / Disconnected
- MQTT: Connected / Disconnected
- Celery Workers: Running / Stopped
- Celery Beat: Running / Stopped

### Test Results

#### Automated Tests
- [ ] All unit tests passing (111/111)
- [ ] All integration tests passing (115/115)
- [ ] All security tests passing (20/20)
- [ ] Coverage > 80%
- Issues found: ________________

#### Manual Tests
- [ ] Application Foundation (5/5)
- [ ] Authentication & Authorization (20/20)
- [ ] Core Domain Models (15/15)
- [ ] RESTful API Implementation (40/40)
- [ ] WebSocket & Real-time (20/20)
- [ ] Background Tasks (25/25)
- Issues found: ________________

### Performance Tests
- [ ] API response time < 200ms (p95)
- [ ] WebSocket latency < 50ms
- [ ] Database queries < 100ms (p95)
- [ ] Load test passed (1000+ concurrent)
- Issues found: ________________

### Bugs/Issues Discovered
1. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________
2. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________
3. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________

### Sign-off
- Tester Signature: ________________
- Date: ________________
- Approval: Pass / Fail / Pass with Conditions
- Notes: ________________
```

---

## 6. Troubleshooting

### Issue: Backend Container Won't Start

**Symptoms**:
- Container exits immediately
- Import errors in logs

**Solutions**:
```bash
# Rebuild backend container
docker-compose -f docker-compose.dev.yml up --build backend-dev

# Check Python dependencies
docker-compose -f docker-compose.dev.yml exec backend-dev pip list

# If dependencies missing
docker-compose -f docker-compose.dev.yml exec backend-dev pip install -r requirements.txt
```

---

### Issue: Database Connection Failed

**Symptoms**:
- "Connection refused" errors
- Backend can't connect to PostgreSQL

**Solutions**:
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.dev.yml ps postgres-dev

# View PostgreSQL logs
docker-compose -f docker-compose.dev.yml logs -f postgres-dev

# Restart PostgreSQL
docker-compose -f docker-compose.dev.yml restart postgres-dev

# Connect to PostgreSQL directly
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev
```

---

### Issue: Alembic Migration Errors

**Symptoms**:
- Migration fails
- "Table already exists" errors
- "No 'script_location' key found in configuration"

**Solutions**:
```bash
# Method 1: Using manage.py (recommended)
# Check current migration status
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py current

# View migration history
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py history

# Downgrade and re-apply
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py downgrade -r -1
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py migrate

# Method 2: Direct alembic commands (requires container rebuild first)
# Rebuild container to create alembic.ini symlink
docker-compose -f docker-compose.dev.yml up --build backend-dev

# Then use direct commands
docker-compose -f docker-compose.dev.yml exec backend-dev alembic current
docker-compose -f docker-compose.dev.yml exec backend-dev alembic history
docker-compose -f docker-compose.dev.yml exec backend-dev alembic stamp head
docker-compose -f docker-compose.dev.yml exec backend-dev alembic downgrade -1
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head

# Method 3: Explicit path (works without rebuild)
docker-compose -f docker-compose.dev.yml exec backend-dev alembic -c infrastructure/database/alembic.ini upgrade head
```

---

### Issue: Redis Connection Failed

**Symptoms**:
- Caching not working
- Session data not persisted

**Solutions**:
```bash
# Check Redis status
docker-compose -f docker-compose.dev.yml ps redis-dev

# Test Redis connection
docker-compose -f docker-compose.dev.yml exec redis-dev redis-cli ping

# View Redis logs
docker-compose -f docker-compose.dev.yml logs -f redis-dev

# Restart Redis
docker-compose -f docker-compose.dev.yml restart redis-dev
```

---

### Issue: WebSocket Connection Failed

**Symptoms**:
- Real-time updates not working
- Connection refused on port 8001

**Solutions**:
```bash
# Check if backend is listening on port 8001
docker-compose -f docker-compose.dev.yml exec backend-dev netstat -tulpn | grep 8001

# View backend logs for WebSocket errors
docker-compose -f docker-compose.dev.yml logs -f backend-dev | grep -i websocket

# Restart backend
docker-compose -f docker-compose.dev.yml restart backend-dev

# Test WebSocket connection with wscat
npm install -g wscat
wscat -c ws://localhost:8001
```

---

### Issue: Celery Workers Not Processing Tasks

**Symptoms**:
- Tasks stuck in "PENDING" state
- No task execution

**Solutions**:
```bash
# Check Celery worker status
docker-compose -f docker-compose.dev.yml ps celery-worker

# View Celery worker logs
docker-compose -f docker-compose.dev.yml logs -f celery-worker

# Restart workers
docker-compose -f docker-compose.dev.yml restart celery-worker

# Check Redis (broker) connection
docker-compose -f docker-compose.dev.yml exec redis-dev redis-cli ping

# Purge task queues (CAUTION: deletes all pending tasks)
docker-compose -f docker-compose.dev.yml exec backend-dev celery -A app.tasks.celery_app purge
```

---

### Issue: Tests Fail with Import Errors

**Symptoms**:
- `ModuleNotFoundError` during test execution
- Import paths incorrect

**Solutions**:
```bash
# Verify PYTHONPATH
docker-compose -f docker-compose.dev.yml exec backend-dev python -c "import sys; print('\\n'.join(sys.path))"

# Install test dependencies
docker-compose -f docker-compose.dev.yml exec backend-dev pip install pytest pytest-asyncio pytest-cov httpx

# Clear Python cache
docker-compose -f docker-compose.dev.yml exec backend-dev find . -type d -name __pycache__ -exec rm -r {} +
docker-compose -f docker-compose.dev.yml exec backend-dev find . -type f -name '*.pyc' -delete

# Restart container
docker-compose -f docker-compose.dev.yml restart backend-dev
```

---

### Issue: Coverage Report Not Generated

**Symptoms**:
- `htmlcov/` directory not created
- Coverage data missing

**Solutions**:
```bash
# Run tests with coverage explicitly
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --cov=app --cov-report=html --cov-report=term

# Check for .coverage file
docker-compose -f docker-compose.dev.yml exec backend-dev ls -la .coverage

# Generate HTML report manually
docker-compose -f docker-compose.dev.yml exec backend-dev coverage html

# Copy report to local machine
docker cp $(docker-compose -f docker-compose.dev.yml ps -q backend-dev):/app/htmlcov ./backend-coverage
```

---

### Issue: MQTT Broker Connection Failed

**Symptoms**:
- Devices can't connect to MQTT
- "Connection refused" on port 1883

**Solutions**:
```bash
# Check MQTT broker status
docker-compose -f docker-compose.dev.yml ps mqtt-dev

# View MQTT logs
docker-compose -f docker-compose.dev.yml logs -f mqtt-dev

# Test MQTT connection
docker-compose -f docker-compose.dev.yml exec mqtt-dev mosquitto_sub -h localhost -t "test/#"

# Restart MQTT broker
docker-compose -f docker-compose.dev.yml restart mqtt-dev
```

---

## 7. Next Steps After Testing

### If All Tests Pass ✅

1. **Document Edge Cases**: Record any edge cases discovered during testing
2. **Update Test Coverage**: Address any gaps in test coverage
3. **Performance Baseline**: Establish performance baselines for future comparison
4. **Proceed to Phase 3**: Ready for Frontend Development (Next.js application)
5. **Knowledge Transfer**: Document lessons learned and best practices

---

### If Tests Fail ❌

1. **Categorize Failures**: Group failures by severity (Critical/High/Medium/Low)
2. **Create GitHub Issues**: Create detailed issue for each failure with:
   - Test case ID
   - Expected vs. actual outcome
   - Steps to reproduce
   - Logs and screenshots
   - Suggested fix (if known)
3. **Prioritize Fixes**: Focus on critical and high severity issues first
4. **Fix and Retest**: Apply fixes and re-run affected tests
5. **Regression Testing**: Ensure fixes don't break other functionality
6. **Do NOT Proceed**: Do not start Phase 3 until all critical/high issues resolved

---

## Appendix A: Quick Reference Commands

### All commands run inside Docker containers:

**Start development environment**:
```bash
make dev
```

**Backend testing**:
```bash
# Run all automated Phase 2 tests
make test-phase2-full                    # Full test suite with reports
make test-phase2-manual                  # All 125 tests
make test-phase2-manual-verbose          # With detailed output

# Run tests by category (faster, targeted testing + auto reports)
make test-phase2-app                     # Application Foundation (5 tests) → Reports
make test-phase2-auth                    # Authentication (20 tests) → Reports
make test-phase2-domain                  # Domain Models (15 tests) → Reports
make test-phase2-api                     # RESTful APIs (40 tests) → Reports
make test-phase2-websocket               # WebSocket (20 tests) → Reports
make test-phase2-celery                  # Background Tasks (25 tests) → Reports

# Quick validation
make test-phase2-quick                   # 8 core tests (~2 min)
make test-phase2-smoke                   # 2 critical tests (~30 sec)

# Run specific test case
make test-phase2-manual-tc TC=TC-AUTH-001

# List all available test cases
make test-phase2-list

# Run all unit/integration tests (pytest)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest

# Run with coverage
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --cov=app --cov-report=html

# Run specific test file
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/test_security.py -v

# Run specific test class
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/test_security.py::TestPasswordHashing -v

# Watch mode
docker-compose -f docker-compose.dev.yml exec backend-dev ptw
```

**Database operations**:
```bash
# Run migrations - Using manage.py (recommended)
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py migrate
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py current
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py create -m "description" --autogenerate

# Run migrations - Direct alembic (after container rebuild)
docker-compose -f docker-compose.dev.yml exec backend-dev alembic upgrade head
docker-compose -f docker-compose.dev.yml exec backend-dev alembic current
docker-compose -f docker-compose.dev.yml exec backend-dev alembic revision --autogenerate -m "description"

# Database management operations
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py backup
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py validate
docker-compose -f docker-compose.dev.yml exec backend-dev python /infrastructure/database/manage.py init

# Direct PostgreSQL access
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev

# Redis CLI
docker-compose -f docker-compose.dev.yml exec redis-dev redis-cli
```

**Service management**:
```bash
# View logs
docker-compose -f docker-compose.dev.yml logs -f backend-dev
docker-compose -f docker-compose.dev.yml logs -f celery-worker

# Restart services
docker-compose -f docker-compose.dev.yml restart backend-dev
docker-compose -f docker-compose.dev.yml restart postgres-dev

# Stop all services
docker-compose -f docker-compose.dev.yml down

# Clean slate (removes volumes)
docker-compose -f docker-compose.dev.yml down -v

# Get shell in container
docker-compose -f docker-compose.dev.yml exec backend-dev bash
```

**Celery operations**:
```bash
# Start worker
docker-compose -f docker-compose.dev.yml up -d celery-worker

# Start beat scheduler
docker-compose -f docker-compose.dev.yml up -d celery-beat

# Purge all tasks (CAUTION)
docker-compose -f docker-compose.dev.yml exec backend-dev celery -A app.tasks.celery_app purge

# Inspect active tasks
docker-compose -f docker-compose.dev.yml exec backend-dev celery -A app.tasks.celery_app inspect active

# View registered tasks
docker-compose -f docker-compose.dev.yml exec backend-dev celery -A app.tasks.celery_app inspect registered
```

**API testing with curl**:
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}'

# Protected endpoint (replace TOKEN)
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN"

# Create device (replace TOKEN)
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Device","device_type":"raspberry_pi"}'
```

**Monitoring**:
```bash
# Open Swagger docs
open http://localhost:8000/docs

# Open Flower (Celery monitoring)
open http://localhost:5555

# Open MailHog (email testing)
open http://localhost:8025

# Open PgAdmin (database GUI)
open http://localhost:5050

# Open Jaeger (distributed tracing)
open http://localhost:16686
```

---

## Appendix B: Test Data

### Valid Test Credentials
```json
{
  "email": "testuser@example.com",
  "username": "testuser",
  "password": "TestPassword123!",
  "organization": "Test Lab (ID: org-uuid)"
}

{
  "email": "admin@example.com",
  "username": "admin",
  "password": "AdminPassword123!",
  "role": "Admin"
}
```

### Mock Device Data
```json
{
  "name": "Lab Cage 1",
  "device_type": "raspberry_pi",
  "hardware_version": "4B",
  "software_version": "1.0.0",
  "status": "online",
  "capabilities": {
    "camera": true,
    "rfid_reader": true,
    "feeder": true,
    "speaker": true,
    "touchscreen": true
  }
}
```

### Mock Experiment Data
```json
{
  "name": "Visual Discrimination Task",
  "description": "Testing color discrimination in rhesus macaques",
  "protocol": {...},
  "state": "draft",
  "device_id": "device-uuid",
  "participant_ids": ["primate-uuid-1"]
}
```

### Mock Primate Data
```json
{
  "species": "rhesus_macaque",
  "identifier": "RM-001",
  "rfid_tag": "ABC123456789",
  "date_of_birth": "2020-01-15",
  "sex": "male",
  "weight": 8.5,
  "training_level": "intermediate",
  "health_status": "healthy"
}
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-13
**Next Review**: After Phase 3 completion

---

*This comprehensive testing guide ensures thorough validation of all Phase 2 (Backend Core Development) features before proceeding to Phase 3 (Frontend Development). All tests should be executed in the Docker development environment for consistency and reproducibility.*

# Verbose Debugging Guide for Phase 2 Testing

**Version**: 1.0
**Date**: 2025-10-16
**Purpose**: Comprehensive guide for running Phase 2 tests with verbose and debug output

---

## Overview

All Phase 2 automated tests now support **verbose** and **debug** modes to provide detailed output for troubleshooting and understanding test execution. This guide explains how to use these modes effectively.

---

## 1. Verbose vs Debug Modes

### Verbose Mode (`--verbose` or `-v`)
Shows test execution progress with:
- ✅ Test case name and category
- 📝 Each test step as it runs
- ⏱️ Timing for each step (milliseconds)
- ✅/❌ Pass/fail status for each step
- 📊 Summary with total duration

**Use when**: You want to see what's happening without overwhelming detail

### Debug Mode (`--debug` or `-d`)
Shows everything in verbose mode PLUS:
- 🔵 HTTP request details (method, URL, body)
- 🔴 HTTP response details (status, body, timing)
- 🔧 Internal function calls and operations
- 🔍 Data transformations and validations
- 🕐 Precise timestamps for each operation

**Use when**: Tests are failing and you need to see exact API interactions

---

## 2. Python Test Script Options

### 2.1 Basic Commands

```bash
# Standard run (minimal output, saves JSON)
python3 tools/scripts/test-phase2-manual.py

# Verbose mode (show test steps)
python3 tools/scripts/test-phase2-manual.py --verbose
python3 tools/scripts/test-phase2-manual.py -v

# Debug mode (show all HTTP requests/responses)
python3 tools/scripts/test-phase2-manual.py --debug
python3 tools/scripts/test-phase2-manual.py -d

# Run specific test case with verbose
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --verbose

# Run specific test case with debug
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --debug

# List all available test cases
python3 tools/scripts/test-phase2-manual.py --list

# Save output to specific file
python3 tools/scripts/test-phase2-manual.py --verbose --output my-results.json
```

### 2.2 Verbose Output Example

```
[12:34:56.789] [INFO]
Running TC-APP-001: FastAPI Server Startup

[12:34:56.790] [STEP]   → Backend health check
[12:34:56.795] [PASS]   ✓ Backend health check (5ms)

[12:34:56.796] [STEP]   → Swagger UI accessible
[12:34:56.801] [PASS]   ✓ Swagger UI accessible (5ms)

[12:34:56.802] [STEP]   → OpenAPI schema available
[12:34:56.810] [PASS]   ✓ OpenAPI schema available (8ms)

[12:34:56.811] [PASS] ✓ TC-APP-001 completed in 0.02s
```

### 2.3 Debug Output Example

```
[12:34:56.790] [DEBUG] → GET http://localhost:8000/api/v1/health
[12:34:56.795] [DEBUG] ← Status: 200 (5ms)
[12:34:56.795] [DEBUG]   Response: {
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-16T12:34:56.795Z"
}

[12:34:56.796] [DEBUG] → GET http://localhost:8000/docs
[12:34:56.801] [DEBUG] ← Status: 200 (5ms)

[12:34:56.802] [DEBUG] → GET http://localhost:8000/openapi.json
[12:34:56.810] [DEBUG] ← Status: 200 (8ms)
[12:34:56.810] [DEBUG]   Response: {
  "openapi": "3.0.0",
  "info": "LICS API"
}
```

---

## 3. Make Commands

### 3.1 Automated Test Suite Commands

```bash
# Run all 125 tests (standard output)
make test-phase2-manual

# Run all 125 tests (verbose - shows steps)
make test-phase2-manual-verbose

# Run all 125 tests (debug - shows HTTP requests)
make test-phase2-manual-debug

# Run specific test case (verbose)
make test-phase2-manual-tc TC=TC-AUTH-001

# Run specific test case (debug)
make test-phase2-manual-tc-debug TC=TC-AUTH-001

# Complete workflow (tests + reports, verbose)
make test-phase2-full
```

### 3.2 Category-Specific Tests (All Include Verbose by Default)

```bash
# Application Foundation (5 tests)
make test-phase2-app

# Authentication & Authorization (20 tests)
make test-phase2-auth

# Core Domain Models (15 tests)
make test-phase2-domain

# RESTful API Implementation (40 tests)
make test-phase2-api

# WebSocket & Real-time Features (20 tests)
make test-phase2-websocket

# Background Tasks & Scheduling (25 tests)
make test-phase2-celery
```

**Note**: All category-specific commands automatically run with `--verbose` flag

### 3.3 Quick Validation Tests

```bash
# Quick validation (8 core tests, ~2 minutes)
make test-phase2-quick

# Smoke tests (2 critical tests, ~30 seconds)
make test-phase2-smoke
```

Both run with verbose output by default.

---

## 4. Pytest Commands (Unit/Integration Tests)

### 4.1 Standard Pytest Verbosity

```bash
# Inside Docker container
docker-compose -f docker-compose.dev.yml exec backend-dev pytest

# Verbose output (-v)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -v

# Very verbose output (-vv)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv

# Show print statements (-s)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -s

# Show local variables on failure (--showlocals)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --showlocals

# Long traceback format (--tb=long)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --tb=long

# Short traceback format (--tb=short)
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --tb=short
```

### 4.2 Debug Logging

```bash
# Show DEBUG level logs
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --log-cli-level=DEBUG

# Show INFO level logs
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --log-cli-level=INFO

# Combine with verbose output
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv -s --log-cli-level=DEBUG

# With coverage and verbose
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --cov=app --cov-report=html -vv
```

### 4.3 Recommended Debug Command

For maximum debugging information:

```bash
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv -s --showlocals --log-cli-level=DEBUG --tb=long
```

This shows:
- Very verbose test output (`-vv`)
- Print statements (`-s`)
- Local variable values on failure (`--showlocals`)
- DEBUG level logs (`--log-cli-level=DEBUG`)
- Full tracebacks (`--tb=long`)

---

## 5. Shell Script Testing

### 5.1 test_phase2.sh Commands

```bash
# Standard output
cd services/backend
./test_phase2.sh

# Verbose mode
./test_phase2.sh --verbose
./test_phase2.sh -v

# Debug mode (bash tracing with set -x)
./test_phase2.sh --debug
./test_phase2.sh -d

# Show help
./test_phase2.sh --help
```

### 5.2 Component-Specific Scripts

All component scripts support the same flags:

```bash
# Authentication tests
./test_auth.sh --verbose

# Domain models tests
./test_domain.sh --debug

# API endpoints tests
./test_api.sh -v

# WebSocket tests
./test_websocket.sh -d

# Background tasks tests
./test_background_tasks.sh --verbose
```

---

## 6. Color-Coded Output

All verbose/debug modes use color coding for better readability:

| Color | Meaning | Used For |
|-------|---------|----------|
| 🔵 Blue | Information | Test names, section headers |
| 🟢 Green | Success | Passed tests, successful steps |
| 🔴 Red | Failure | Failed tests, errors |
| 🟡 Yellow | Warning/Info | Steps, progress indicators |
| ⚪ Gray | Debug | Timestamps, debug messages |
| 🟣 Magenta | Special | Highlights, important notices |
| 🔷 Cyan | Step | Individual test steps |

### Color Output Example

```
[12:34:56.789] [INFO] Running TC-AUTH-001: User Registration
[12:34:56.790] [STEP]   → Creating test user
[12:34:56.795] [DEBUG] → POST http://localhost:8000/api/v1/auth/register
[12:34:56.800] [DEBUG] ← Status: 201 (5ms)
[12:34:56.801] [PASS]   ✓ User created successfully (11ms)
```

---

## 7. Output Redirection and Logging

### 7.1 Save Output to File

```bash
# Save verbose output to file
make test-phase2-manual-verbose 2>&1 | tee test-output.log

# Save debug output to file
python3 tools/scripts/test-phase2-manual.py --debug 2>&1 | tee debug-output.log

# Save pytest output to file
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv 2>&1 | tee pytest-output.log
```

### 7.2 Filter Output

```bash
# Show only failures
make test-phase2-manual-verbose 2>&1 | grep -E "FAIL|ERROR"

# Show only HTTP requests
python3 tools/scripts/test-phase2-manual.py --debug 2>&1 | grep -E "→|←"

# Show timing information
make test-phase2-manual-verbose 2>&1 | grep "ms)"
```

---

## 8. Troubleshooting with Verbose Output

### 8.1 Test Failures

**Problem**: Test fails but reason unclear

**Solution**:
```bash
# Run with debug to see exact API interaction
make test-phase2-manual-tc-debug TC=TC-AUTH-001

# Or directly with Python script
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --debug
```

**What to look for**:
- HTTP status codes (should be 200, 201, etc.)
- Request body format (check JSON structure)
- Response error messages
- Timing issues (timeouts)

### 8.2 Connection Issues

**Problem**: Cannot connect to backend

**Solution**:
```bash
# Check backend is running
docker-compose -f docker-compose.dev.yml ps backend-dev

# View backend logs
docker-compose -f docker-compose.dev.yml logs -f backend-dev

# Test with debug mode
python3 tools/scripts/test-phase2-manual.py --tc TC-APP-001 --debug
```

**What to look for in debug output**:
- Connection refused errors
- Timeout messages
- Incorrect URLs or ports

### 8.3 Authentication Issues

**Problem**: Token-related test failures

**Solution**:
```bash
# Run authentication tests with debug
make test-phase2-auth 2>&1 | tee auth-debug.log

# Or specific auth test
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-002 --debug
```

**What to look for**:
- Token generation (should see access_token and refresh_token in response)
- Token format (should be "Bearer" type)
- Token expiry issues
- Invalid credentials

### 8.4 Database Issues

**Problem**: Database connection or query failures

**Solution**:
```bash
# Run database tests with debug
docker-compose -f docker-compose.dev.yml exec backend-dev pytest tests/unit/test_database.py -vv -s --log-cli-level=DEBUG

# Check database connection manually
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev -c "SELECT 1"

# Run app test with debug
python3 tools/scripts/test-phase2-manual.py --tc TC-APP-002 --debug
```

**What to look for**:
- Connection strings
- Migration status
- Query errors
- Timeout issues

---

## 9. Performance Analysis

### 9.1 Timing Information

Verbose mode shows timing for each step:

```bash
# Run with verbose to see step timing
python3 tools/scripts/test-phase2-manual.py --verbose | grep "ms)"

# Example output:
#   ✓ Backend health check (5ms)
#   ✓ Database connection (12ms)
#   ✓ Authentication (23ms)
```

### 9.2 Slow Test Identification

```bash
# Find tests taking >1 second
make test-phase2-manual-verbose 2>&1 | grep -E "[0-9]{4,}ms|[1-9][0-9]*\.[0-9]*s"

# With pytest, show slowest 10 tests
docker-compose -f docker-compose.dev.yml exec backend-dev pytest --durations=10 -vv
```

---

## 10. Best Practices

### 10.1 When to Use Each Mode

| Situation | Recommended Mode | Command Example |
|-----------|-----------------|-----------------|
| Quick validation | Standard | `make test-phase2-smoke` |
| Development testing | Verbose | `make test-phase2-manual-verbose` |
| Debugging failures | Debug | `make test-phase2-manual-debug` |
| CI/CD pipelines | Standard + JSON | `make test-phase2-manual` |
| Performance analysis | Verbose | `make test-phase2-manual-verbose` |
| Investigating API issues | Debug | `python3 tools/scripts/test-phase2-manual.py --debug` |

### 10.2 Output Management

```bash
# For long test runs, save output
make test-phase2-manual-verbose 2>&1 | tee "test-run-$(date +%Y%m%d-%H%M%S).log"

# For debugging specific issues
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --debug 2>&1 | tee auth-debug.log

# Keep last 10 test logs only
ls -t test-run-*.log | tail -n +11 | xargs rm -f
```

### 10.3 Reading Debug Output

1. **Start with test case header**: Shows which test is running
2. **Follow the steps**: Each step shows progress
3. **Check HTTP interactions**: Look at request/response pairs
4. **Verify status codes**: 200/201 = success, 4xx/5xx = issues
5. **Examine timing**: Unusually slow operations indicate problems
6. **Read error messages**: Full stack traces in debug mode

---

## 11. Integration with CI/CD

### 11.1 GitHub Actions Example

```yaml
- name: Run Phase 2 Tests (Verbose in CI)
  run: |
    make dev-detached
    sleep 60

    # Run migrations
    docker-compose -f docker-compose.dev.yml exec -T backend-dev alembic upgrade head

    # Run tests with verbose output and generate reports
    make test-phase2-full

- name: Upload Test Results and Reports
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: phase2-test-results
    path: |
      test-results/phase2_manual_*.json
      test-results/reports/phase2_report_*.md
      test-results/reports/phase2_report_*.html

- name: Comment PR with Results
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const glob = require('glob');

      // Find latest result file
      const files = glob.sync('test-results/phase2_manual_*.json');
      if (files.length === 0) return;

      const latestFile = files.sort().pop();
      const results = JSON.parse(fs.readFileSync(latestFile));

      // Read markdown report for PR comment
      const reportFiles = glob.sync('test-results/reports/phase2_report_*.md');
      const latestReport = reportFiles.sort().pop();
      const reportContent = fs.readFileSync(latestReport, 'utf8');

      // Post comment with summary
      const body = `## Phase 2 Test Results\n\n` +
        `✅ Passed: ${results.summary.passed_tests}\n` +
        `❌ Failed: ${results.summary.failed_tests}\n` +
        `⊘ Skipped: ${results.summary.skipped_tests}\n` +
        `📊 Success Rate: ${results.summary.success_rate}%\n` +
        `⏱️ Duration: ${results.duration_seconds}s\n\n` +
        `<details>\n<summary>📋 Full Report</summary>\n\n` +
        reportContent +
        `\n</details>`;

      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: body
      });
```

### 11.2 Debug Failed CI Runs

When CI fails:

1. Download test artifacts (JSON + logs)
2. Review verbose output for exact failure point
3. Reproduce locally with debug mode:
   ```bash
   python3 tools/scripts/test-phase2-manual.py --tc <FAILED_TEST> --debug
   ```
4. Fix issue and re-run locally before pushing

---

## 12. Quick Reference

### Command Cheat Sheet

```bash
# VERBOSE MODE (shows steps)
make test-phase2-manual-verbose                    # All tests
make test-phase2-manual-tc TC=TC-AUTH-001          # Specific test
python3 tools/scripts/test-phase2-manual.py -v     # Direct script

# DEBUG MODE (shows HTTP)
make test-phase2-manual-debug                      # All tests
make test-phase2-manual-tc-debug TC=TC-AUTH-001    # Specific test
python3 tools/scripts/test-phase2-manual.py -d     # Direct script

# PYTEST VERBOSE
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv -s --log-cli-level=DEBUG

# SHELL SCRIPT VERBOSE
./test_phase2.sh --verbose                         # Verbose mode
./test_phase2.sh --debug                           # Debug mode

# SAVE OUTPUT
make test-phase2-manual-verbose 2>&1 | tee test.log
```

### Flags Summary

| Flag | Short | Mode | Shows |
|------|-------|------|-------|
| `--verbose` | `-v` | Verbose | Test steps, timing |
| `--debug` | `-d` | Debug | HTTP requests, responses, detailed tracing |
| `--list` | - | - | Available test cases |
| `--tc TC-XXX-001` | - | - | Run specific test case |
| `--output FILE` | - | - | Save JSON results to file |

---

**Document Version**: 1.0
**Last Updated**: 2025-10-16
**Applies To**: Phase 2 - Backend Core Development Testing

For questions or issues with verbose/debug modes, refer to the main [PHASE2_TESTING_GUIDE.md](./PHASE2_TESTING_GUIDE.md) or create an issue in the repository.

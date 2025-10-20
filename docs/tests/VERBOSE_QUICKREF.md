# Phase 2 Verbose Testing - Quick Reference

**Last Updated**: 2025-10-16

Quick reference for running Phase 2 tests with verbose/debug output.

---

## 🎯 Quick Commands

### Python Automated Test Suite

```bash
# All 125 tests - Verbose (recommended)
make test-phase2-manual-verbose

# All 125 tests - Debug (HTTP details)
make test-phase2-manual-debug

# Specific test - Verbose
make test-phase2-manual-tc TC=TC-AUTH-001

# Specific test - Debug
make test-phase2-manual-tc-debug TC=TC-AUTH-001

# Direct script usage
python3 tools/scripts/test-phase2-manual.py --verbose
python3 tools/scripts/test-phase2-manual.py --debug
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 -d
```

### Pytest (Unit/Integration Tests)

```bash
# Maximum debugging
docker-compose -f docker-compose.dev.yml exec backend-dev \
  pytest -vv -s --showlocals --log-cli-level=DEBUG --tb=long

# Quick verbose
docker-compose -f docker-compose.dev.yml exec backend-dev pytest -vv

# With logs
docker-compose -f docker-compose.dev.yml exec backend-dev \
  pytest -vv --log-cli-level=DEBUG
```

### Shell Scripts

```bash
cd services/backend

# Verbose
./test_phase2.sh --verbose

# Debug (bash tracing)
./test_phase2.sh --debug

# Component tests
./test_auth.sh --verbose
./test_api.sh --debug
```

### Category Tests (All Verbose by Default)

```bash
make test-phase2-app        # Application Foundation (5 tests)
make test-phase2-auth       # Authentication (20 tests)
make test-phase2-domain     # Domain Models (15 tests)
make test-phase2-api        # RESTful APIs (40 tests)
make test-phase2-websocket  # WebSocket (20 tests)
make test-phase2-celery     # Background Tasks (25 tests)
```

---

## 🔍 When to Use Each Mode

| Situation | Use This | Command |
|-----------|----------|---------|
| **Quick validation** | Standard | `make test-phase2-smoke` |
| **Development work** | Verbose | `make test-phase2-manual-verbose` |
| **Test failing** | Debug | `make test-phase2-manual-debug` |
| **API not working** | Debug | `python3 tools/scripts/test-phase2-manual.py --tc TC-API-001 -d` |
| **Auth issues** | Debug | `make test-phase2-manual-tc-debug TC=TC-AUTH-002` |
| **Pytest failing** | Verbose + Logs | `pytest -vv --log-cli-level=DEBUG` |
| **Shell script debug** | Debug | `./test_phase2.sh --debug` |

---

## 📊 Output Comparison

### Standard Output
```
✓ PASS | TC-AUTH-001 | User Registration (0.15s)
```

### Verbose Output
```
[12:34:56.789] [INFO] Running TC-AUTH-001: User Registration
[12:34:56.790] [STEP]   → Creating test user
[12:34:56.801] [PASS]   ✓ User created successfully (11ms)
[12:34:56.802] [STEP]   → Validating email format
[12:34:56.805] [PASS]   ✓ Email validation passed (3ms)
[12:34:56.806] [PASS] ✓ TC-AUTH-001 completed in 0.02s
```

### Debug Output
```
[12:34:56.789] [INFO] Running TC-AUTH-001: User Registration
[12:34:56.790] [STEP]   → Creating test user
[12:34:56.790] [DEBUG] → POST http://localhost:8000/api/v1/auth/register
[12:34:56.790] [DEBUG]   Request Body: {
  "email": "testuser@example.com",
  "password": "TestPassword123!",
  "username": "testuser"
}
[12:34:56.800] [DEBUG] ← Status: 201 (10ms)
[12:34:56.800] [DEBUG]   Response: {
  "id": "uuid-here",
  "email": "testuser@example.com",
  "created_at": "2025-10-16T12:34:56Z"
}
[12:34:56.801] [PASS]   ✓ User created successfully (11ms)
```

---

## 🎨 Color Legend

- 🔵 **Blue** - Test names, section headers
- 🟢 **Green** - Success, passed tests
- 🔴 **Red** - Failures, errors
- 🟡 **Yellow** - Steps, warnings, info
- ⚪ **Gray** - Timestamps, debug details
- 🔷 **Cyan** - Individual test steps

---

## 💾 Save Output to File

```bash
# Save verbose output
make test-phase2-manual-verbose 2>&1 | tee test-run.log

# Save debug output
python3 tools/scripts/test-phase2-manual.py --debug 2>&1 | tee debug.log

# With timestamp
make test-phase2-manual-verbose 2>&1 | tee "test-$(date +%Y%m%d-%H%M%S).log"

# Pytest to file
docker-compose -f docker-compose.dev.yml exec backend-dev \
  pytest -vv --log-cli-level=DEBUG 2>&1 | tee pytest-debug.log
```

---

## 🔧 Common Debugging Patterns

### Test Fails - Find Out Why
```bash
# Run with debug to see exact API response
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --debug
```

### Check HTTP Status Codes
```bash
# Debug mode shows all HTTP interactions
make test-phase2-manual-debug 2>&1 | grep "Status:"
```

### Find Slow Tests
```bash
# Verbose shows timing for each step
make test-phase2-manual-verbose 2>&1 | grep "ms)"
```

### Authentication Issues
```bash
# Debug auth tests specifically
make test-phase2-auth 2>&1 | tee auth-debug.log
# Then search for "401" or "403" errors
```

### Database Connection Issues
```bash
# Run app foundation tests with debug
python3 tools/scripts/test-phase2-manual.py --tc TC-APP-002 --debug
```

---

## 📖 Full Documentation

- **Comprehensive Guide**: [VERBOSE_DEBUGGING_GUIDE.md](./VERBOSE_DEBUGGING_GUIDE.md)
- **Phase 2 Testing Guide**: [PHASE2_TESTING_GUIDE.md](./PHASE2_TESTING_GUIDE.md)

---

## 🚀 Best Practice Workflow

1. **Start with smoke test** (30 seconds):
   ```bash
   make test-phase2-smoke
   ```

2. **If issues found, run verbose** (~2 minutes):
   ```bash
   make test-phase2-quick
   ```

3. **For specific failures, use debug**:
   ```bash
   make test-phase2-manual-tc-debug TC=<failing-test>
   ```

4. **Save output for investigation**:
   ```bash
   python3 tools/scripts/test-phase2-manual.py --tc <test> --debug 2>&1 | tee issue.log
   ```

5. **Check specific HTTP interactions** in the log file

---

**Remember**:
- `--verbose` (-v) = See what's happening
- `--debug` (-d) = See EVERYTHING that's happening

Use verbose for understanding, debug for troubleshooting!

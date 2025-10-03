# Phase 3 Week 5 - Comprehensive Testing Guide

**Version**: 1.0
**Date**: 2025-10-03
**Scope**: Frontend Development - Next.js Application Foundation, State Management, Authentication Flow

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

### Prerequisites
```bash
# Ensure all services are running
make dev

# Or individually:
docker-compose up -d postgres redis mqtt minio
cd services/backend && uvicorn app.main:app --reload
cd services/frontend && npm run dev
```

### Install Test Dependencies
```bash
cd services/frontend

# Install testing libraries
npm install --save-dev \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  jest \
  jest-environment-jsdom \
  jest-canvas-mock \
  @types/jest

# Verify installation
npm list @testing-library/react
```

### Environment Configuration
Create `.env.test` in `services/frontend/`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8001
NODE_ENV=test
```

---

## 2. Automated Testing

### 2.1 Running All Tests

**Command**:
```bash
cd services/frontend
npm test
```

**Expected Output**:
```
PASS  __tests__/validation/auth-schemas.test.ts
PASS  __tests__/validation/password-strength.test.ts
PASS  __tests__/stores/auth-store.test.ts
PASS  __tests__/components/LoginForm.test.tsx

Test Suites: 4 passed, 4 total
Tests:       52 passed, 52 total
Snapshots:   0 total
Time:        8.234 s
```

### 2.2 Running Specific Test Suites

**Validation Tests Only**:
```bash
npm test -- __tests__/validation
```

**Store Tests Only**:
```bash
npm test -- __tests__/stores
```

**Component Tests Only**:
```bash
npm test -- __tests__/components
```

### 2.3 Coverage Report

**Generate Coverage**:
```bash
npm test -- --coverage
```

**Expected Coverage** (Target: >80%):
```
File                                    | % Stmts | % Branch | % Funcs | % Lines
----------------------------------------|---------|----------|---------|--------
lib/validation/auth-schemas.ts          |   100   |   100    |   100   |   100
lib/validation/password-strength.ts     |   95    |   90     |   100   |   95
lib/stores/auth-store.ts                |   88    |   85     |   90    |   88
components/features/auth/LoginForm.tsx  |   92    |   88     |   95    |   92
```

**View HTML Coverage Report**:
```bash
open coverage/lcov-report/index.html
```

### 2.4 Watch Mode for Development

**Run tests in watch mode**:
```bash
npm test -- --watch
```

**Usage**:
- Press `a` to run all tests
- Press `p` to filter by filename pattern
- Press `t` to filter by test name pattern
- Press `q` to quit

---

## 3. Manual Testing Procedures

### 3.1 Application Foundation Testing

#### TC-AF-001: Next.js Compilation
**Steps**:
1. Open terminal in `services/frontend/`
2. Run: `npm run typecheck`
3. Observe output

**Expected Outcome**:
- ✅ No TypeScript errors
- ✅ Output: "Found 0 errors"
- ✅ Exit code: 0

**Actual Outcome**: ________________

---

#### TC-AF-002: Tailwind CSS Configuration
**Steps**:
1. Run: `npm run dev`
2. Open browser: http://localhost:3000
3. Inspect any button element
4. Check computed styles

**Expected Outcome**:
- ✅ Tailwind classes applied correctly
- ✅ Custom theme colors visible (--primary, --background, etc.)
- ✅ Dark mode toggle works (if implemented)

**Actual Outcome**: ________________

---

#### TC-AF-003: Shadcn/ui Components
**Steps**:
1. Navigate to login page: http://localhost:3000/login
2. Inspect button, input, and card components
3. Check component styling and interactivity

**Expected Outcome**:
- ✅ Button component renders with correct styling
- ✅ Input component has focus states
- ✅ Card component has proper shadows and borders
- ✅ All Shadcn/ui components functional

**Actual Outcome**: ________________

---

#### TC-AF-004: Layout Components
**Steps**:
1. Navigate to dashboard (after login): http://localhost:3000/dashboard
2. Observe Header, Sidebar, and MainShell
3. Toggle sidebar (if applicable)
4. Check responsive behavior (resize browser)

**Expected Outcome**:
- ✅ Header displays with logo and navigation
- ✅ Sidebar appears on left (or collapsible)
- ✅ MainShell wraps content correctly
- ✅ Mobile drawer works on small screens
- ✅ Footer displays at bottom

**Actual Outcome**: ________________

---

### 3.2 State Management Testing

#### TC-SM-001: API Client Request Interceptor
**Steps**:
1. Open browser DevTools → Network tab
2. Log in with valid credentials
3. Make any API request (e.g., fetch devices)
4. Inspect request headers

**Expected Outcome**:
- ✅ `Authorization: Bearer <token>` header present
- ✅ Token matches stored access token
- ✅ Request sent to http://localhost:8000

**Actual Outcome**: ________________

---

#### TC-SM-002: API Client Response Interceptor (401 Handling)
**Steps**:
1. Log in successfully
2. Manually expire access token (DevTools → Application → sessionStorage → set old token)
3. Make API request
4. Observe behavior

**Expected Outcome**:
- ✅ API returns 401
- ✅ Client attempts token refresh automatically
- ✅ New access token obtained
- ✅ Original request retried with new token
- ✅ OR user logged out if refresh fails

**Actual Outcome**: ________________

---

#### TC-SM-003: Auth Store - Remember Me (localStorage)
**Steps**:
1. Navigate to login page
2. Enter credentials: test@example.com / ValidPass123!
3. **Check** "Remember Me" checkbox
4. Click "Sign In"
5. Open DevTools → Application → Local Storage
6. Verify token storage

**Expected Outcome**:
- ✅ `access_token` in localStorage
- ✅ `refresh_token` in localStorage
- ✅ `rememberMe: true` in Zustand persist storage
- ✅ Tokens persist after browser close/reopen

**Actual Outcome**: ________________

---

#### TC-SM-004: Auth Store - Session Only (sessionStorage)
**Steps**:
1. Log out if logged in
2. Navigate to login page
3. Enter credentials: test@example.com / ValidPass123!
4. **Uncheck** "Remember Me" checkbox
5. Click "Sign In"
6. Open DevTools → Application → Session Storage
7. Verify token storage

**Expected Outcome**:
- ✅ `access_token` in sessionStorage
- ✅ `refresh_token` in sessionStorage
- ✅ NO tokens in localStorage
- ✅ Tokens cleared after browser close

**Actual Outcome**: ________________

---

#### TC-SM-005: Auth Store - Auto Token Refresh
**Steps**:
1. Log in with Remember Me = true
2. Wait 5-10 minutes (or manually reduce token expiry for testing)
3. Observe network activity in DevTools

**Expected Outcome**:
- ✅ Token refresh timer started on login
- ✅ Automatic refresh request sent 5 minutes before expiry
- ✅ New tokens stored in storage
- ✅ User remains authenticated

**Actual Outcome**: ________________

---

#### TC-SM-006: React Query - Data Fetching
**Steps**:
1. Log in successfully
2. Navigate to /dashboard
3. Open DevTools → Network tab
4. Observe API requests

**Expected Outcome**:
- ✅ User data fetched: GET /api/v1/auth/me
- ✅ Devices fetched: GET /api/v1/devices (if applicable)
- ✅ Data cached in React Query
- ✅ Stale time: 5 minutes for static data, 10 seconds for dynamic

**Actual Outcome**: ________________

---

#### TC-SM-007: WebSocket Connection
**Steps**:
1. Log in successfully
2. Open DevTools → Console
3. Check for WebSocket connection logs
4. Trigger device status update from backend (if possible)

**Expected Outcome**:
- ✅ WebSocket connects to ws://localhost:8001
- ✅ JWT token sent during handshake
- ✅ Connection status: "connected"
- ✅ Real-time events received and logged
- ✅ Auto-reconnect on disconnection

**Actual Outcome**: ________________

---

### 3.3 Authentication Flow Testing

#### TC-AF-LOGIN-001: Successful Login
**Steps**:
1. Navigate to http://localhost:3000/login
2. Enter:
   - Email: `test@example.com`
   - Password: `ValidPass123!`
   - Remember Me: Checked
3. Click "Sign In"

**Expected Outcome**:
- ✅ Success toast notification appears
- ✅ Redirected to /dashboard
- ✅ User info displayed in header
- ✅ Logout button visible
- ✅ Protected routes accessible

**Actual Outcome**: ________________

---

#### TC-AF-LOGIN-002: Invalid Credentials
**Steps**:
1. Navigate to http://localhost:3000/login
2. Enter:
   - Email: `test@example.com`
   - Password: `WrongPassword123!`
3. Click "Sign In"

**Expected Outcome**:
- ✅ Error toast notification: "Invalid credentials"
- ✅ User remains on login page
- ✅ Form inputs cleared or retain values (design choice)
- ✅ No redirect occurs

**Actual Outcome**: ________________

---

#### TC-AF-LOGIN-003: Form Validation
**Steps**:
1. Navigate to http://localhost:3000/login
2. Enter invalid email: `not-an-email`
3. Click "Sign In"

**Expected Outcome**:
- ✅ Inline error message: "Invalid email address"
- ✅ Email field highlighted with red border
- ✅ No API request sent
- ✅ Form submission blocked

**Steps (continued)**:
4. Fix email: `test@example.com`
5. Leave password empty
6. Click "Sign In"

**Expected Outcome**:
- ✅ Email error cleared
- ✅ Password error: "Password is required"
- ✅ Password field highlighted with red border

**Actual Outcome**: ________________

---

#### TC-AF-LOGIN-004: Password Visibility Toggle
**Steps**:
1. Navigate to http://localhost:3000/login
2. Enter password: `SecretPass123!`
3. Observe password field (should show dots/asterisks)
4. Click "Show Password" icon/button
5. Observe password field

**Expected Outcome**:
- ✅ Initially: password hidden (type="password")
- ✅ After toggle: password visible (type="text")
- ✅ Click again: password hidden again
- ✅ Icon changes between "eye" and "eye-slash"

**Actual Outcome**: ________________

---

#### TC-AF-REGISTER-001: Multi-Step Registration (Step 1)
**Steps**:
1. Navigate to http://localhost:3000/register
2. Observe Step 1: Account Creation
3. Enter:
   - Email: `newuser@example.com`
   - Password: `short` (weak password)
4. Observe password strength indicator

**Expected Outcome**:
- ✅ Step indicator shows "1/3"
- ✅ Password strength: WEAK (red bar)
- ✅ Feedback: "Use at least 8 characters"
- ✅ "Next" button disabled until valid

**Steps (continued)**:
5. Change password to: `StrongPass123!@#`
6. Observe password strength
7. Enter confirm password: `StrongPass123!@#`
8. Click "Next"

**Expected Outcome**:
- ✅ Password strength: STRONG (green bar)
- ✅ Feedback: Empty or "Excellent password"
- ✅ "Next" button enabled
- ✅ Advances to Step 2

**Actual Outcome**: ________________

---

#### TC-AF-REGISTER-002: Multi-Step Registration (Step 2)
**Steps**:
1. From Step 2 (Profile Information)
2. Enter:
   - First Name: `John`
   - Last Name: `Doe`
   - Phone: `+1234567890` (optional)
3. Click "Next"

**Expected Outcome**:
- ✅ Step indicator shows "2/3"
- ✅ "Back" button enabled
- ✅ "Next" button enabled when fields valid
- ✅ Advances to Step 3
- ✅ Previous data retained (can navigate back)

**Actual Outcome**: ________________

---

#### TC-AF-REGISTER-003: Multi-Step Registration (Step 3)
**Steps**:
1. From Step 3 (Organization Setup)
2. Select: "Create new organization"
3. Enter Organization Name: `My Research Lab`
4. Click "Create Account"

**Expected Outcome**:
- ✅ Step indicator shows "3/3"
- ✅ "Create Account" button visible
- ✅ Loading spinner appears during submission
- ✅ Success: Redirected to /dashboard
- ✅ Error: Toast notification with error message

**Actual Outcome**: ________________

---

#### TC-AF-REGISTER-004: Multi-Step Registration (Join Organization)
**Steps**:
1. From Step 3 (Organization Setup)
2. Select: "Join existing organization"
3. Enter Join Code: `ABC123XYZ`
4. Click "Create Account"

**Expected Outcome**:
- ✅ Join code field appears
- ✅ Organization name field hidden
- ✅ Validation: Join code required
- ✅ Account created with organization association

**Actual Outcome**: ________________

---

#### TC-AF-MIDDLEWARE-001: Protected Routes
**Steps**:
1. Log out if logged in (or open incognito window)
2. Attempt to access: http://localhost:3000/dashboard

**Expected Outcome**:
- ✅ Redirected to /login
- ✅ URL shows: /login?return=/dashboard
- ✅ After login: Redirected back to /dashboard

**Actual Outcome**: ________________

---

#### TC-AF-MIDDLEWARE-002: Auth Routes (Already Logged In)
**Steps**:
1. Log in successfully
2. Attempt to access: http://localhost:3000/login

**Expected Outcome**:
- ✅ Redirected to /dashboard
- ✅ Cannot access login page while authenticated
- ✅ Same behavior for /register

**Actual Outcome**: ________________

---

#### TC-AF-LOGOUT-001: Logout Flow
**Steps**:
1. Log in successfully
2. Navigate to dashboard
3. Click user dropdown in header
4. Click "Logout"

**Expected Outcome**:
- ✅ Loading spinner appears ("Logging out...")
- ✅ Success toast: "Logged out successfully"
- ✅ Redirected to /login
- ✅ Tokens cleared from storage (localStorage + sessionStorage)
- ✅ User state cleared
- ✅ Protected routes inaccessible

**Actual Outcome**: ________________

---

### 3.4 Integration Testing

#### TC-INT-001: Full Authentication Workflow
**Steps**:
1. Start from logged out state
2. Navigate to /login
3. Log in with valid credentials
4. Verify dashboard loads
5. Make API request (e.g., fetch devices)
6. Trigger WebSocket event (if possible)
7. Log out
8. Verify logged out state

**Expected Outcome**:
- ✅ All steps complete without errors
- ✅ State transitions correctly
- ✅ API requests authenticated
- ✅ WebSocket connects/disconnects properly
- ✅ Clean logout

**Actual Outcome**: ________________

---

#### TC-INT-002: Token Refresh During Active Session
**Steps**:
1. Log in with Remember Me = true
2. Use application normally for 10-15 minutes
3. Monitor network activity
4. Observe automatic token refresh

**Expected Outcome**:
- ✅ Token refresh occurs before expiry
- ✅ No interruption to user experience
- ✅ All API requests continue to work
- ✅ New tokens stored successfully

**Actual Outcome**: ________________

---

#### TC-INT-003: Offline/Online State Handling
**Steps**:
1. Log in successfully
2. Open DevTools → Network tab
3. Set throttling to "Offline"
4. Attempt API request
5. Set throttling back to "Online"

**Expected Outcome**:
- ✅ Offline state detected
- ✅ User notified of offline status (toast/banner)
- ✅ Queued requests retry when online
- ✅ WebSocket reconnects automatically

**Actual Outcome**: ________________

---

## 4. Expected Outcomes Summary

### 4.1 Automated Test Results

| Test Suite | Expected Pass Rate | Coverage Target |
|------------|-------------------|-----------------|
| Validation Schemas | 100% (18/18 tests) | 100% |
| Password Strength | 100% (21/21 tests) | 95% |
| Auth Store | 100% (18/18 tests) | 88% |
| Login Form | 100% (24/24 tests) | 92% |
| **Total** | **100% (81/81 tests)** | **>80%** |

### 4.2 Manual Test Results

| Category | Test Cases | Expected Pass Rate |
|----------|-----------|-------------------|
| Application Foundation | 4 | 100% (4/4) |
| State Management | 7 | 100% (7/7) |
| Authentication Flow | 9 | 100% (9/9) |
| Integration | 3 | 100% (3/3) |
| **Total** | **23** | **100% (23/23)** |

### 4.3 Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| First Contentful Paint (FCP) | < 1.5s | Lighthouse |
| Largest Contentful Paint (LCP) | < 2.5s | Lighthouse |
| Time to Interactive (TTI) | < 3.5s | Lighthouse |
| Bundle Size (Frontend) | < 500KB | `npm run build` |
| TypeScript Compilation | < 10s | `npm run typecheck` |

### 4.4 Accessibility Standards

| Standard | Target | Validation Tool |
|----------|--------|-----------------|
| WCAG 2.1 Level AA | 100% | axe DevTools |
| Keyboard Navigation | All interactive elements | Manual testing |
| Screen Reader Support | Proper ARIA labels | NVDA/VoiceOver |
| Color Contrast Ratio | 4.5:1 (normal text) | Lighthouse |

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
- Frontend Dev Server: Running / Stopped
- Database: Connected / Disconnected
- Redis: Connected / Disconnected
- MQTT: Connected / Disconnected

### Test Results

#### Automated Tests
- [ ] All tests passing (81/81)
- [ ] Coverage > 80%
- [ ] No failing tests
- Issues found: ________________

#### Manual Tests
- [ ] Application Foundation (4/4)
- [ ] State Management (7/7)
- [ ] Authentication Flow (9/9)
- [ ] Integration (3/3)
- Issues found: ________________

### Bugs/Issues Discovered
1. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________
2. Issue ID: ______ | Severity: Critical/High/Medium/Low | Description: ________________

### Sign-off
- Tester Signature: ________________
- Date: ________________
- Approval: Pass / Fail / Pass with Conditions
```

---

## 6. Troubleshooting

### Issue: Tests Fail to Run

**Symptoms**:
- `npm test` throws errors
- "Cannot find module" errors

**Solutions**:
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Clear Jest cache
npm test -- --clearCache

# Verify Jest config
cat jest.config.js
```

---

### Issue: Backend API Not Responding

**Symptoms**:
- API requests fail with network errors
- Connection refused errors

**Solutions**:
```bash
# Check backend status
curl http://localhost:8000/api/v1/health

# Restart backend
cd services/backend
uvicorn app.main:app --reload

# Check database connection
docker-compose ps postgres
```

---

### Issue: WebSocket Connection Fails

**Symptoms**:
- WebSocket connection errors in console
- Real-time updates not working

**Solutions**:
```bash
# Check WebSocket server
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8001

# Verify WebSocket port
docker-compose ps | grep 8001

# Check MQTT broker
docker-compose logs mqtt
```

---

### Issue: Tokens Not Persisting

**Symptoms**:
- User logged out after page refresh
- Tokens not in storage

**Solutions**:
1. Check browser storage settings (allow cookies/localStorage)
2. Verify domain/path settings in token storage
3. Check Zustand persist middleware configuration
4. Inspect DevTools → Application → Storage

---

### Issue: Form Validation Not Working

**Symptoms**:
- Validation errors not displaying
- Forms submit with invalid data

**Solutions**:
1. Check Zod schema imports
2. Verify react-hook-form configuration
3. Check error message rendering logic
4. Inspect form state in React DevTools

---

## 7. Next Steps After Testing

### If All Tests Pass ✅
1. Document any edge cases discovered
2. Update test coverage for gaps
3. Proceed to Phase 3 Week 6 (Core UI Components)
4. Create testing baseline for future sprints

### If Tests Fail ❌
1. Categorize failures by severity (Critical/High/Medium/Low)
2. Create GitHub issues for each failure
3. Prioritize fixes based on blocking impact
4. Retest after fixes applied
5. Do NOT proceed to Week 6 until all critical issues resolved

---

## Appendix A: Test Data

### Valid Test Credentials
```
Email: test@example.com
Password: ValidPass123!
Organization: Test Lab (ID: org-123)
```

### Mock Device Data
```
Device ID: device-123
Device Name: Test Device
Device Type: raspberry_pi
Status: online
```

### Mock Experiment Data
```
Experiment ID: exp-123
Experiment Name: Test Experiment
State: draft
```

---

## Appendix B: Quick Reference Commands

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- LoginForm.test.tsx

# Watch mode
npm test -- --watch

# Update snapshots
npm test -- -u

# Run tests in CI mode
npm test -- --ci --coverage --maxWorkers=2
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-03
**Next Review**: After Phase 3 Week 6 completion

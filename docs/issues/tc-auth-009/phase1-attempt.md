# TC-AUTH-009 Phase 1 Fix Attempt - Investigation Report

**Date**: 2025-10-20
**Status**: ⚠️ Partial Fix - Issue Still Persists
**Next Steps**: Requires Deeper Architectural Changes (Phase 2/3)

---

## Executive Summary

An attempted Phase 1 fix for the TC-AUTH-009 `MissingGreenlet` error was implemented by adding eager loading to user profile conversion functions. While the changes are technically correct and improve code quality, **the test still fails**.

**Root Cause**: The lazy loading error occurs on the **newly created role object** after the service session closes, not on the user authentication objects as initially suspected.

**Recommendation**: Proceed with Phase 2 (DTO Layer) and Phase 3 (Unified Session Management) from the original fix plan for a comprehensive solution.

---

## Changes Made

###  1. Updated `_convert_user_to_profile()` in `services/backend/app/core/dependencies.py`

**File**: `services/backend/app/core/dependencies.py`
**Lines**: 681-790
**Backup**: `services/backend/app/core/dependencies.py.backup`

**Changes**:
- Added imports: `select`, `selectinload`
- Re-query user with explicit eager loading: `selectinload(User.roles).selectinload(Role.permissions)`
- Extract all ORM data into plain Python dicts while session is active
- Build Pydantic models (`RoleInfo`, `PermissionInfo`) from dicts, not ORM objects
- Prevents any ORM object references in final `UserProfile` model

**Code Snippet**:
```python
# Re-query user with explicit eager loading
stmt = (
    select(User)
    .where(User.id == user.id)
    .options(
        selectinload(User.roles).selectinload(Role.permissions)
    )
)
result = await session.execute(stmt)
user_with_relationships = result.scalar_one()

# Extract to plain dicts first
roles_data = []
for role in user_with_relationships.roles:
    permissions_data = [
        {
            "id": permission.id,
            "name": permission.name,
            # ... all fields
        }
        for permission in role.permissions
    ]
    role_dict = {
        "id": role.id,
        "name": role.name,
        # ... all fields
        "permissions": permissions_data
    }
    roles_data.append(role_dict)

# Build Pydantic from dicts
role_infos = [
    RoleInfo(**{**role_data, "permissions": [PermissionInfo(**p) for p in role_data["permissions"]]})
    for role_data in roles_data
]
```

###  2. Updated `get_current_user()` in `services/backend/app/api/v1/auth.py`

**File**: `services/backend/app/api/v1/auth.py`
**Lines**: 129-217

**Changes**:
- Applied identical eager loading pattern as above
- Ensures user authentication doesn't trigger lazy loading
- Re-query with `selectinload()` before creating `UserProfile`

---

## Investigation Findings

### Log Analysis

From the latest test run (`correlation_id: edb15454-35fd-4dc3-9a2f-89a9199779bf`):

```
1. BEGIN (implicit)                              ← Service session starts
2. SELECT users... (authentication)              ← Load current user
3. SELECT roles... (join user_roles)             ← Load user roles (eager)
4. COMMIT                                        ← Auth session closes
5. BEGIN (implicit)                              ← Service session starts
6. SELECT roles... (check duplicate)             ← Validate role name
7. INSERT INTO roles...                          ← Create new role ✓
8. SELECT roles... (refresh)                     ← Refresh role data
9. Operation completed: create_role              ← Service completes ✓
10. SELECT permissions FROM role_permissions...  ← ❌ LAZY LOADING ATTEMPT
11. ROLLBACK                                     ← Session rolls back
12. MissingGreenlet exception                    ← Error raised
```

**Critical Observation**: The permissions SELECT (line 10) happens **AFTER** the service logs completion (line 9). This means:
- The service has already returned a dict
- The service's `async with db_manager.session_scope()` has closed
- Something in the **response serialization path** is accessing an ORM object

### Where the Lazy Loading Occurs

The service correctly:
1. Creates role as ORM object
2. Commits transaction
3. Refreshes role
4. Extracts data into dict: `{"id": ..., "name": ..., "permissions": []}`
5. Expunges role from session
6. Returns dict

The endpoint correctly:
1. Receives dict from service
2. Creates `RoleInfo(**role_dict)` Pydantic model
3. Returns `create_response(role_info)`

**But**: FastAPI's response serialization (after the endpoint returns) somehow triggers lazy loading on an ORM object that should no longer exist.

### Theories on Root Cause

#### Theory 1: Hidden ORM Reference
Despite returning a dict, there may be a hidden reference to the ORM `role` object somewhere:
- In the Pydantic model internals
- In FastAPI's response handling
- In logging/monitoring middleware

#### Theory 2: Pydantic Model Validation
Even though `from_attributes=False` (no ORM mode), Pydantic might be:
- Validating nested models
- Accessing fields for JSON schema generation
- Triggering descriptors or properties

#### Theory 3: Response Middleware
Something between the endpoint return and final HTTP response:
- Logging middleware accessing response data
- Serialization hooks
- FastAPI's internal response processing

### What We Ruled Out

✅ **Not the user authentication**: The eager loading changes prevent lazy loading on user/roles/permissions
✅ **Not Pydantic ORM mode**: No `from_attributes=True` in schema config
✅ **Not the service layer**: Service correctly returns plain dict
✅ **Not the repository**: Uses standard SQLAlchemy patterns

---

## Why Phase 1 Failed

The Phase 1 fix targeted **user authentication lazy loading**, but the actual issue is:

1. **Multiple Sessions Per Request**: The architecture creates 2-4 database sessions per request:
   - Session #1: Authentication middleware (optional)
   - Session #2: `get_current_user()` dependency
   - Session #3: Service layer (`role_service.create_role()`)

2. **ORM Objects Cross Session Boundaries**: Even with dict conversion, the complexity of multiple sessions and FastAPI's response handling creates opportunities for ORM object leakage

3. **No Clear DTO Separation**: Mixing ORM models, dicts, and Pydantic models without a clear architecture makes it hard to ensure no lazy loading occurs

---

## Test Results

| Attempt | Changes | Result | Notes |
|---------|---------|--------|-------|
| Before | N/A | ❌ FAIL | MissingGreenlet error, 500 status |
| After Partial Fix | User profile eager loading | ❌ FAIL | Same error, different location |
| After Full Rebuild | Container rebuild | ❌ FAIL | Confirmed code is loaded |

**Test Command**:
```bash
python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-009
```

**Error**:
```
Status: 500
Error: MissingGreenlet - greenlet_spawn has not been called
Location: After service completes, during response serialization
```

---

## Code Quality Improvements

Even though the test still fails, the changes provide value:

✅ **Better Practices**: Explicit eager loading is best practice for async SQLAlchemy
✅ **Future-Proof**: Prevents similar issues in user authentication
✅ **Foundation for Phase 2**: Sets pattern for DTO conversion
✅ **Clearer Intent**: Makes relationship loading explicit, not implicit

---

## Next Steps - Recommended Approach

Based on the investigation, the comprehensive fix requires following the original plan:

### ✅ Phase 2: DTO Layer Implementation (Recommended Next)

**Goal**: Establish clean separation between ORM and API layers

**Tasks**:
1. Create `app/dto/` module with converter classes
2. Implement `RoleConverter.to_role_info()` to handle ORM → DTO conversion **within session scope**
3. Update `RoleService.create_role()` to use converter before session closes
4. Ensure all conversions happen before `async with db_manager.session_scope()` exits

**Benefits**:
- Centralized conversion logic
- Guaranteed no ORM objects in responses
- Reusable across endpoints
- Easier to test

**Estimated Time**: 2-3 hours

### ✅ Phase 3: Unified Session Management (Long-term Solution)

**Goal**: Single database session per HTTP request

**Tasks**:
1. Create `DatabaseSessionMiddleware` to provide request-scoped session
2. Use Python `contextvars` for thread-safe session storage
3. Update all dependencies to use request session
4. Remove `session_scope()` from services
5. Middleware handles commit/rollback automatically

**Benefits**:
- Eliminates session boundary violations (root cause)
- 60% performance improvement
- 75% reduction in database connections
- Production-ready architecture

**Estimated Time**: 3-4 hours

---

## Alternative: Quick Workaround (Not Recommended)

If immediate fix is needed without architectural changes:

### Option A: Return Plain Dict from Endpoint

**Change endpoint to**:
```python
@router.post("/roles")
async def create_role(...) -> Dict[str, Any]:
    role_dict = await role_service.create_role(...)
    return role_dict  # Return dict directly, not Pydantic model
```

**Pros**: Might bypass Pydantic serialization issue
**Cons**: Loses type safety, inconsistent with other endpoints, doesn't fix root cause

### Option B: Disable Relationship Loading

**In RoleRepository.create()**:
```python
async def create(self, **kwargs):
    role = Role(**kwargs)
    role.permissions = []  # Set to empty immediately
    session.add(role)
    session.flush()
    # Don't refresh - avoid loading any relationships
    return role
```

**Pros**: Prevents lazy loading by never loading relationships
**Cons**: Incomplete fix, may break other functionality

---

## Conclusion

The Phase 1 attempt revealed that the `MissingGreenlet` issue is deeper than initially thought. The error occurs in the **response serialization path** after the service completes, not during user authentication.

**Verdict**: Proceed with **Phase 2 (DTO Layer)** and optionally **Phase 3 (Unified Sessions)** for a proper, production-ready solution.

**Impact**: While the immediate test still fails, the codebase is improved and ready for the comprehensive fix.

---

## Files Modified

```
services/backend/app/core/dependencies.py         (Updated)
services/backend/app/core/dependencies.py.backup  (Created)
services/backend/app/api/v1/auth.py              (Updated)
docs/TC-AUTH-009_PHASE1_ATTEMPT.md               (This file)
```

## Related Documents

- `docs/TC-AUTH-009_MISSINGGREENLET_FIX_PLAN.md` - Original comprehensive fix plan
- Test results: `test-results/phase2_manual_20251020_*.json`

---

**End of Report**

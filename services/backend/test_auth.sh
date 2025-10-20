#!/bin/bash

echo "=== AUTHENTICATION & AUTHORIZATION DEEP TEST ==="
echo ""

echo "### JWT Implementation"
grep -n "create_access_token\|create_refresh_token\|verify_token" app/core/security.py | head -10
echo ""

echo "### Password Hashing"
grep -n "hash_password\|verify_password\|argon2" app/core/security.py | head -5
echo ""

echo "### RBAC Models"
echo "User model:"
grep -n "class User" app/models/auth.py
echo ""
echo "Role model:"
grep -n "class Role" app/models/auth.py
echo ""
echo "Permission model:"
grep -n "class Permission" app/models/auth.py
echo ""

echo "### Authentication Endpoints"
grep -n "@router\." app/api/v1/auth.py | head -10
echo ""

echo "### Middleware"
echo "Authentication middleware:"
grep -n "class\|async def" app/middleware/auth.py | head -10
echo ""
echo "Rate limiting middleware:"
grep -n "class\|async def" app/middleware/rate_limiting.py | head -5


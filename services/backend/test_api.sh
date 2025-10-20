#!/bin/bash

echo "=== API ENDPOINTS DEEP TEST ==="
echo ""

echo "### Organizations API"
grep "@router\." app/api/v1/organizations.py | nl
echo ""

echo "### Devices API"
grep "@router\." app/api/v1/devices.py | nl
echo ""

echo "### Experiments API"
grep "@router\." app/api/v1/experiments.py | nl
echo ""

echo "### Tasks API"  
grep "@router\." app/api/v1/tasks.py | nl
echo ""

echo "### Participants API"
grep "@router\." app/api/v1/participants.py | nl
echo ""

echo "### Total Endpoint Count"
total=0
for file in app/api/v1/*.py; do
    count=$(grep -c "@router\." "$file" 2>/dev/null || echo 0)
    total=$((total + count))
done
echo "Total API endpoints across all routers: $total"


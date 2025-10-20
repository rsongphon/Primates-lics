#!/bin/bash

echo "=== DOMAIN MODELS DEEP TEST ==="
echo ""

echo "### Core Domain Models"
echo "Device model:"
grep -n "^class Device" app/models/domain.py
echo ""
echo "Experiment model:"
grep -n "^class Experiment" app/models/domain.py
echo ""
echo "Task model:"
grep -n "^class Task\|^class TaskDefinition\|^class TaskExecution" app/models/domain.py
echo ""
echo "Primate model:"
grep -n "^class Primate" app/models/domain.py
echo ""

echo "### Enums"
echo "Device related:"
grep -n "class.*Enum" app/models/domain.py | head -5
echo ""

echo "### Schemas Count"
echo "Device schemas:"
grep -n "^class.*Schema" app/schemas/devices.py | wc -l
echo "Experiment schemas:"
grep -n "^class.*Schema" app/schemas/experiments.py | wc -l
echo "Task schemas:"
grep -n "^class.*Schema" app/schemas/tasks.py | wc -l
echo ""

echo "### Repositories"
echo "Device repository:"
grep -n "^class.*Repository" app/repositories/domain.py | head -3
echo ""

echo "### Services"
echo "Services implemented:"
grep -n "^class.*Service" app/services/domain.py


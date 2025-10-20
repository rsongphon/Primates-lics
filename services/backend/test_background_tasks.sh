#!/bin/bash

echo "=== PHASE 2 WEEK 4 DAY 5: BACKGROUND TASKS AND SCHEDULING TEST ==="
echo ""

echo "### 1. Celery Configuration"
if [ -f "app/tasks/celery_app.py" ]; then
    lines=$(wc -l < "app/tasks/celery_app.py")
    echo "✓ app/tasks/celery_app.py ($lines lines)"
    
    echo "  Queue configuration:"
    grep -E "task_routes|task_queues" app/tasks/celery_app.py | head -5
    
    echo "  Celery Beat schedule:"
    grep -c "beat_schedule" app/tasks/celery_app.py
else
    echo "✗ app/tasks/celery_app.py MISSING"
fi

echo ""
echo "### 2. Data Processing Tasks"
if [ -f "app/tasks/data_processing.py" ]; then
    lines=$(wc -l < "app/tasks/data_processing.py")
    tasks=$(grep -c "@celery_app.task" "app/tasks/data_processing.py" 2>/dev/null || echo "0")
    echo "✓ app/tasks/data_processing.py ($lines lines, $tasks tasks)"
    echo "  Tasks:"
    grep "@celery_app.task" app/tasks/data_processing.py -A 1 | grep "^def" | sed 's/def /  - /'
else
    echo "✗ app/tasks/data_processing.py MISSING"
fi

echo ""
echo "### 3. Notification Tasks"
if [ -f "app/tasks/notifications.py" ]; then
    lines=$(wc -l < "app/tasks/notifications.py")
    tasks=$(grep -c "@celery_app.task" "app/tasks/notifications.py" 2>/dev/null || echo "0")
    echo "✓ app/tasks/notifications.py ($lines lines, $tasks tasks)"
    echo "  Tasks:"
    grep "@celery_app.task" app/tasks/notifications.py -A 1 | grep "^def" | sed 's/def /  - /'
else
    echo "✗ app/tasks/notifications.py MISSING"
fi

echo ""
echo "### 4. Report Generation Tasks"
if [ -f "app/tasks/reports.py" ]; then
    lines=$(wc -l < "app/tasks/reports.py")
    tasks=$(grep -c "@celery_app.task" "app/tasks/reports.py" 2>/dev/null || echo "0")
    echo "✓ app/tasks/reports.py ($lines lines, $tasks tasks)"
    echo "  Tasks:"
    grep "@celery_app.task" app/tasks/reports.py -A 1 | grep "^def" | sed 's/def /  - /'
else
    echo "✗ app/tasks/reports.py MISSING"
fi

echo ""
echo "### 5. Maintenance Tasks"
if [ -f "app/tasks/maintenance.py" ]; then
    lines=$(wc -l < "app/tasks/maintenance.py")
    tasks=$(grep -c "@celery_app.task" "app/tasks/maintenance.py" 2>/dev/null || echo "0")
    echo "✓ app/tasks/maintenance.py ($lines lines, $tasks tasks)"
    echo "  Tasks:"
    grep "@celery_app.task" app/tasks/maintenance.py -A 1 | grep "^def" | sed 's/def /  - /'
else
    echo "✗ app/tasks/maintenance.py MISSING"
fi

echo ""
echo "### 6. Metrics Integration"
if [ -f "app/tasks/metrics.py" ]; then
    lines=$(wc -l < "app/tasks/metrics.py")
    echo "✓ app/tasks/metrics.py ($lines lines)"
    echo "  Prometheus metrics:"
    grep -E "Counter|Gauge|Histogram" app/tasks/metrics.py | head -5
else
    echo "✗ app/tasks/metrics.py MISSING"
fi

echo ""
echo "### 7. Task Monitoring API"
if [ -f "app/api/v1/tasks_monitoring.py" ]; then
    lines=$(wc -l < "app/api/v1/tasks_monitoring.py")
    endpoints=$(grep -c "@router\." "app/api/v1/tasks_monitoring.py" 2>/dev/null || echo "0")
    echo "✓ app/api/v1/tasks_monitoring.py ($lines lines, $endpoints endpoints)"
    echo "  Monitoring endpoints:"
    grep "@router\." app/api/v1/tasks_monitoring.py | sed 's/@router\./  - /'
else
    echo "✗ app/api/v1/tasks_monitoring.py MISSING"
fi

echo ""
echo "### 8. Total Background Tasks Count"
total=0
for file in app/tasks/*.py; do
    if [ -f "$file" ] && [ "$(basename $file)" != "__init__.py" ]; then
        count=$(grep -c "@celery_app.task" "$file" 2>/dev/null || echo 0)
        total=$((total + count))
    fi
done
echo "Total background tasks implemented: $total"

echo ""
echo "=== BACKGROUND TASKS TEST COMPLETE ==="

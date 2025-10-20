#!/bin/bash

echo "=== WEBSOCKET IMPLEMENTATION DEEP TEST ==="
echo ""

echo "### WebSocket Server Configuration"
grep -n "sio = socketio.AsyncServer\|socketio.AsyncServer" app/websocket/server.py | head -3
echo ""

echo "### Namespaces"
ls -1 app/websocket/handlers/ 2>/dev/null || echo "Handlers directory not found"
echo ""

echo "### Device Handlers"
grep -n "^async def\|^def" app/websocket/handlers/device_handlers.py | head -10
echo ""

echo "### Experiment Handlers"
grep -n "^async def\|^def" app/websocket/handlers/experiment_handlers.py | head -10
echo ""

echo "### Task Handlers"
grep -n "^async def\|^def" app/websocket/handlers/task_handlers.py | head -10
echo ""

echo "### Notification Handlers"
grep -n "^async def\|^def" app/websocket/handlers/notification_handlers.py | head -10
echo ""

echo "### WebSocket Emitters"
ls -la app/websocket/emitters.py 2>/dev/null && echo "Emitters module exists" || echo "Emitters module not found"
echo ""

echo "### Event Types"
if [ -f app/websocket/events.py ]; then
    grep -n "^class\|^def" app/websocket/events.py | head -10
else
    echo "Events module not found"
fi


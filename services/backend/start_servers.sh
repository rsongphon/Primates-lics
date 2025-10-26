#!/bin/bash
# Combined server startup script for LICS Backend
# Starts both HTTP API server (port 8000) and WebSocket server (port 8001)

set -e

echo "🚀 Starting LICS Backend Services..."

# Function to start a server in the background
start_server() {
    local name=$1
    local command=$2
    local port=$3

    echo "📍 Starting $name on port $port..."
    $command > "/app/logs/${name,,}.log" 2>&1 &
    local pid=$!
    echo "✅ $name started with PID $pid"
    echo $pid > "/app/logs/${name,,}.pid"

    # Wait a bit for the server to start
    sleep 2

    # Check if the server is actually running
    if kill -0 $pid 2>/dev/null; then
        echo "✅ $name is running successfully"
    else
        echo "❌ $name failed to start"
        exit 1
    fi
}

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Start HTTP API server (port 8000)
start_server "HTTP-Server" "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" "8000"

# Start WebSocket server (port 8001)
start_server "WebSocket-Server" "python run_websocket_server.py" "8001"

echo ""
echo "🎉 All LICS Backend Services started successfully!"
echo "📡 HTTP API: http://localhost:8000"
echo "🔌 WebSocket: ws://localhost:8001/socket.io"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Server PIDs:"
cat /app/logs/*.pid
echo ""
echo "🔍 Watching logs (Ctrl+C to stop)..."
echo ""

# Function to handle shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."

    # Kill all server processes
    for pidfile in /app/logs/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if kill -0 $pid 2>/dev/null; then
                echo "🔌 Stopping server with PID $pid..."
                kill $pid
                rm "$pidfile"
            fi
        fi
    done

    echo "✅ All servers stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Monitor the servers and show logs
tail -f /app/logs/*.log
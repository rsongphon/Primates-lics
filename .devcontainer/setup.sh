#!/bin/bash
set -e

echo "🚀 Setting up LICS development environment..."

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Test database connection
echo "🔍 Testing database connection..."
until pg_isready -h postgres -p 5432 -U lics; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done
echo "✅ Database connected"

# Test Redis connection
echo "🔍 Testing Redis connection..."
until redis-cli -h redis ping; do
  echo "Waiting for Redis..."
  sleep 2
done
echo "✅ Redis connected"

# Set up Git safe directory
echo "🔧 Configuring Git..."
git config --global --add safe.directory /workspace

# Install Python dependencies for backend
echo "📦 Installing backend dependencies..."
cd /workspace/services/backend
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Install Python dependencies for edge agent
echo "📦 Installing edge agent dependencies..."
cd /workspace/services/edge-agent
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Install Node.js dependencies for frontend
echo "📦 Installing frontend dependencies..."
cd /workspace/services/frontend
if [ ! -d "node_modules" ]; then
  npm install
fi

# Run database migrations
echo "🗄️ Running database migrations..."
cd /workspace/infrastructure/database
source /workspace/services/backend/venv/bin/activate
alembic upgrade head
deactivate

# Create .env file if it doesn't exist
echo "⚙️ Setting up environment configuration..."
cd /workspace
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "✅ Created .env file from .env.example"
fi

# Set up pre-commit hooks
echo "🪝 Setting up Git hooks..."
cd /workspace
if [ -f "tools/scripts/setup-git-hooks.sh" ]; then
  bash tools/scripts/setup-git-hooks.sh
fi

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "📚 Quick Start Commands:"
echo "  make dev              # Start all development services"
echo "  make dev-frontend     # Start frontend only"
echo "  make dev-backend      # Start backend only"
echo "  make test             # Run all tests"
echo ""
echo "🔗 Service URLs (once started):"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000/docs"
echo "  WebSocket: ws://localhost:8001"
echo "  Grafana:   http://localhost:3001"
echo ""

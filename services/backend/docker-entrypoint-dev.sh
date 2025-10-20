#!/bin/bash
# Development entrypoint script for LICS Backend
# Creates necessary symlinks for Alembic configuration

set -e

echo "🔧 Setting up development environment..."

# Create symlink to alembic.ini if it doesn't exist
if [ ! -e /app/alembic.ini ] && [ -f /infrastructure/database/alembic.ini ]; then
    echo "📝 Creating alembic.ini symlink..."
    ln -sf /infrastructure/database/alembic.ini /app/alembic.ini
    echo "✅ Alembic configuration linked"
fi

# Execute the main command
echo "🚀 Starting backend service..."
exec "$@"

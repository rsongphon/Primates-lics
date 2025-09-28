# Multi-stage build for Edge Agent Service
# Optimized for Raspberry Pi and ARM64 deployment
# Based on Documentation.md Section 7.1 - Edge Agent Design

# Build stage with full toolchain
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage with minimal image
FROM python:3.11-slim as runner

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/edgeuser/.local/bin:$PATH"
ENV EDGE_ENVIRONMENT=production

# Install runtime dependencies for hardware access
RUN apt-get update && apt-get install -y \
    curl \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash edgeuser

# Add user to gpio group for hardware access (will be available on Raspberry Pi)
RUN groupadd -f gpio && usermod -a -G gpio edgeuser

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/edgeuser/.local

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/data /app/logs /app/config

# Change ownership to non-root user
RUN chown -R edgeuser:edgeuser /app

# Switch to non-root user
USER edgeuser

# Expose port for local API
EXPOSE 8080

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Volume for persistent data
VOLUME ["/app/data", "/app/logs", "/app/config"]

# Start the edge agent
CMD ["python", "src/main.py"]
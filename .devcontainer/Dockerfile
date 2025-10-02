FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    # Build essentials
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    # Python dependencies
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    # Node.js (will be supplemented by feature)
    curl \
    # Database clients
    postgresql-client \
    libpq-dev \
    # Redis client
    redis-tools \
    # MQTT client
    mosquitto-clients \
    # SSL/TLS
    ca-certificates \
    openssl \
    # Development tools
    git \
    vim \
    nano \
    htop \
    jq \
    wget \
    unzip \
    # Networking tools
    netcat \
    iputils-ping \
    dnsutils \
    # Docker CLI (for docker-in-docker)
    apt-transport-https \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Install Python package managers
RUN python3 -m pip install --upgrade pip setuptools wheel \
    && pip3 install poetry pipenv

# Install global Node.js tools
RUN npm install -g \
    pnpm \
    yarn \
    typescript \
    ts-node \
    nodemon \
    prettier \
    eslint

# Install development utilities
RUN pip3 install \
    black \
    ruff \
    mypy \
    pytest \
    pytest-cov \
    ipython \
    ipdb

# Create workspace directory
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace

# Switch to vscode user
USER vscode

# Set up bash aliases
RUN echo 'alias ll="ls -lah"' >> /home/vscode/.bashrc \
    && echo 'alias dc="docker-compose"' >> /home/vscode/.bashrc \
    && echo 'alias pytest="python -m pytest"' >> /home/vscode/.bashrc \
    && echo 'alias python="python3"' >> /home/vscode/.bashrc \
    && echo 'export PATH="/workspace/tools/scripts:$PATH"' >> /home/vscode/.bashrc

WORKDIR /workspace

CMD ["sleep", "infinity"]

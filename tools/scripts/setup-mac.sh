#!/bin/bash

# LICS macOS Development Environment Setup Script
# This script sets up the development environment for LICS on macOS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check macOS version
check_macos_version() {
    log_info "Checking macOS version..."
    macos_version=$(sw_vers -productVersion)
    log_info "macOS version: $macos_version"

    # Check if macOS version is compatible (10.15+)
    if [[ "$(echo "$macos_version 10.15" | tr " " "\n" | sort -V | head -n1)" != "10.15" ]]; then
        log_error "macOS 10.15 (Catalina) or later is required. You have $macos_version"
        exit 1
    fi

    log_success "macOS version is compatible"
}

# Install Xcode Command Line Tools
install_xcode_tools() {
    log_info "Checking for Xcode Command Line Tools..."

    if ! xcode-select -p &> /dev/null; then
        log_info "Installing Xcode Command Line Tools..."
        xcode-select --install

        # Wait for installation to complete
        until xcode-select -p &> /dev/null; do
            log_info "Waiting for Xcode Command Line Tools installation to complete..."
            sleep 5
        done
        log_success "Xcode Command Line Tools installed"
    else
        log_success "Xcode Command Line Tools already installed"
    fi
}

# Install Homebrew
install_homebrew() {
    log_info "Checking for Homebrew..."

    if ! command_exists brew; then
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ $(uname -m) == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        log_success "Homebrew installed"
    else
        log_success "Homebrew already installed"
        log_info "Updating Homebrew..."
        brew update
    fi
}

# Install Docker Desktop
install_docker() {
    log_info "Checking for Docker..."

    if ! command_exists docker; then
        log_info "Installing Docker Desktop..."
        brew install --cask docker

        log_warning "Docker Desktop has been installed but needs to be started manually"
        log_warning "Please start Docker Desktop from Applications and complete the setup"
        log_warning "You may need to restart this script after Docker is running"

        # Wait for user to start Docker
        read -p "Press Enter after Docker Desktop is running and you've completed the setup..."

        # Wait for Docker to be ready
        log_info "Waiting for Docker to be ready..."
        while ! docker system info >/dev/null 2>&1; do
            log_info "Docker is not ready yet, waiting..."
            sleep 5
        done

        log_success "Docker Desktop installed and running"
    else
        log_success "Docker already installed"

        # Check if Docker is running
        if ! docker system info >/dev/null 2>&1; then
            log_warning "Docker is installed but not running. Please start Docker Desktop"
            read -p "Press Enter after Docker Desktop is running..."
        fi
    fi
}

# Install Docker Compose
install_docker_compose() {
    log_info "Checking for Docker Compose..."

    if ! command_exists docker-compose; then
        log_info "Installing Docker Compose..."
        brew install docker-compose
        log_success "Docker Compose installed"
    else
        log_success "Docker Compose already installed"
    fi
}

# Install Node.js and npm
install_nodejs() {
    log_info "Checking for Node.js..."

    if ! command_exists node; then
        log_info "Installing Node.js via Homebrew..."
        brew install node@20

        # Add Node.js to PATH
        echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zprofile
        export PATH="/opt/homebrew/opt/node@20/bin:$PATH"

        log_success "Node.js installed"
    else
        node_version=$(node --version)
        log_success "Node.js already installed (version: $node_version)"

        # Check if Node version is compatible (18+)
        major_version=$(echo "$node_version" | cut -d'.' -f1 | sed 's/v//')
        if [ "$major_version" -lt 18 ]; then
            log_warning "Node.js version $node_version is older than recommended (18+)"
            log_info "Consider upgrading: brew upgrade node"
        fi
    fi
}

# Install Python
install_python() {
    log_info "Checking for Python..."

    if ! command_exists python3; then
        log_info "Installing Python..."
        brew install python@3.11

        # Add Python to PATH
        echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
        export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"

        log_success "Python installed"
    else
        python_version=$(python3 --version)
        log_success "Python already installed ($python_version)"

        # Check if Python version is compatible (3.11+)
        python_major=$(python3 -c "import sys; print(sys.version_info.major)")
        python_minor=$(python3 -c "import sys; print(sys.version_info.minor)")

        if [ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]; then
            log_warning "Python version is older than recommended (3.11+)"
            log_info "Consider upgrading: brew upgrade python"
        fi
    fi

    # Install pip and essential Python packages
    log_info "Installing/upgrading pip and essential packages..."
    python3 -m pip install --upgrade pip setuptools wheel
}

# Install mkcert for local SSL
install_mkcert() {
    log_info "Checking for mkcert..."

    if ! command_exists mkcert; then
        log_info "Installing mkcert..."
        brew install mkcert
        brew install nss  # For Firefox support

        log_info "Setting up mkcert..."
        mkcert -install

        log_success "mkcert installed and configured"
    else
        log_success "mkcert already installed"
    fi
}

# Install Git (latest version)
install_git() {
    log_info "Checking for Git..."

    if ! command_exists git; then
        log_info "Installing Git..."
        brew install git
        log_success "Git installed"
    else
        git_version=$(git --version)
        log_success "Git already installed ($git_version)"

        # Check if we should upgrade Git
        current_version=$(git --version | cut -d' ' -f3)
        if brew outdated git >/dev/null 2>&1; then
            log_info "Newer version of Git available. Consider upgrading: brew upgrade git"
        fi
    fi
}

# Install additional development tools
install_dev_tools() {
    log_info "Installing additional development tools..."

    # Essential tools for development
    tools=(
        "curl"          # HTTP client
        "wget"          # File downloader
        "jq"            # JSON processor
        "tree"          # Directory tree viewer
        "htop"          # Process viewer
        "watch"         # Command execution monitor
        "postgresql"    # PostgreSQL client tools
        "redis"         # Redis client tools
    )

    for tool in "${tools[@]}"; do
        if ! command_exists "$tool"; then
            log_info "Installing $tool..."
            brew install "$tool"
        else
            log_success "$tool already installed"
        fi
    done
}

# Install VS Code (optional)
install_vscode() {
    if ! command_exists code; then
        read -p "Would you like to install Visual Studio Code? (y/N): " install_vscode_choice
        if [[ $install_vscode_choice =~ ^[Yy]$ ]]; then
            log_info "Installing Visual Studio Code..."
            brew install --cask visual-studio-code

            # Install useful extensions
            log_info "Installing useful VS Code extensions..."
            code --install-extension ms-python.python
            code --install-extension ms-vscode.vscode-typescript-next
            code --install-extension bradlc.vscode-tailwindcss
            code --install-extension ms-vscode.vscode-json
            code --install-extension redhat.vscode-yaml
            code --install-extension ms-vscode-remote.remote-containers

            log_success "Visual Studio Code installed with extensions"
        fi
    else
        log_success "Visual Studio Code already installed"
    fi
}

# Set up environment variables
setup_environment() {
    log_info "Setting up environment variables..."

    # Create .zshrc if it doesn't exist
    if [ ! -f ~/.zshrc ]; then
        touch ~/.zshrc
    fi

    # Add LICS development environment variables
    cat >> ~/.zshrc << 'EOF'

# LICS Development Environment
export LICS_DEV_MODE=true
export COMPOSE_PROJECT_NAME=lics
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Python development
export PYTHONPATH="${PYTHONPATH}:$(pwd)/services/backend:$(pwd)/services/edge-agent"

# Node.js development
export NODE_ENV=development

# Development aliases
alias lics-start="docker-compose -f docker-compose.dev.yml up"
alias lics-stop="docker-compose -f docker-compose.dev.yml down"
alias lics-logs="docker-compose -f docker-compose.dev.yml logs -f"
alias lics-clean="docker-compose -f docker-compose.dev.yml down -v --remove-orphans"

EOF

    log_success "Environment variables configured"
}

# Generate SSL certificates
generate_ssl_certificates() {
    log_info "Generating SSL certificates for local development..."

    # Create SSL directory
    mkdir -p infrastructure/nginx/ssl

    # Generate certificates for local development
    cd infrastructure/nginx/ssl
    mkcert -key-file localhost-key.pem -cert-file localhost.pem localhost 127.0.0.1 ::1 *.localhost

    # Copy certificates with expected names
    cp localhost.pem server.crt
    cp localhost-key.pem server.key

    cd ../../..

    log_success "SSL certificates generated"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."

    # Check all required tools
    tools_check=(
        "docker:Docker"
        "docker-compose:Docker Compose"
        "node:Node.js"
        "npm:npm"
        "python3:Python"
        "pip3:pip"
        "git:Git"
        "mkcert:mkcert"
        "curl:curl"
        "jq:jq"
    )

    all_good=true

    for tool_check in "${tools_check[@]}"; do
        tool=$(echo "$tool_check" | cut -d':' -f1)
        name=$(echo "$tool_check" | cut -d':' -f2)

        if command_exists "$tool"; then
            version=$($tool --version 2>/dev/null | head -n1 || echo "installed")
            log_success "$name: $version"
        else
            log_error "$name is not installed or not in PATH"
            all_good=false
        fi
    done

    # Check Docker is running
    if docker system info >/dev/null 2>&1; then
        log_success "Docker is running"
    else
        log_error "Docker is not running"
        all_good=false
    fi

    if $all_good; then
        log_success "All tools are installed and working!"
        return 0
    else
        log_error "Some tools are missing or not working properly"
        return 1
    fi
}

# Main setup function
main() {
    echo "=================================="
    echo "LICS macOS Development Setup"
    echo "=================================="
    echo ""

    log_info "Starting macOS development environment setup..."

    # Check if running on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is for macOS only"
        exit 1
    fi

    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi

    # Run setup steps
    check_macos_version
    install_xcode_tools
    install_homebrew
    install_git
    install_docker
    install_docker_compose
    install_nodejs
    install_python
    install_mkcert
    install_dev_tools
    install_vscode
    setup_environment
    generate_ssl_certificates

    echo ""
    echo "=================================="
    log_success "macOS setup completed!"
    echo "=================================="
    echo ""

    # Verify installation
    if verify_installation; then
        echo ""
        log_info "Next steps:"
        echo "1. Restart your terminal or run: source ~/.zshrc"
        echo "2. Navigate to your LICS project directory"
        echo "3. Copy .env.example to .env and configure as needed"
        echo "4. Run: make install (to install project dependencies)"
        echo "5. Run: make dev (to start development environment)"
        echo ""
        log_success "You're ready to start developing with LICS!"
    else
        log_warning "Setup completed with some issues. Please check the error messages above."
        exit 1
    fi
}

# Handle script interruption
trap 'log_error "Setup interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"
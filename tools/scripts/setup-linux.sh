#!/bin/bash

# LICS Linux Development Environment Setup Script
# This script sets up the development environment for LICS on Linux distributions

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

# Global variables
DISTRO=""
PACKAGE_MANAGER=""
INSTALL_CMD=""
UPDATE_CMD=""

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect Linux distribution
detect_distro() {
    log_info "Detecting Linux distribution..."

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        log_info "Detected distribution: $PRETTY_NAME"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
        log_info "Detected Red Hat based distribution"
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
        log_info "Detected Debian based distribution"
    else
        log_error "Cannot detect Linux distribution"
        exit 1
    fi

    # Set package manager based on distribution
    case $DISTRO in
        ubuntu|debian|pop|mint)
            PACKAGE_MANAGER="apt"
            INSTALL_CMD="apt-get install -y"
            UPDATE_CMD="apt-get update"
            ;;
        fedora|rhel|centos|rocky|almalinux)
            if command_exists dnf; then
                PACKAGE_MANAGER="dnf"
                INSTALL_CMD="dnf install -y"
                UPDATE_CMD="dnf update -y"
            else
                PACKAGE_MANAGER="yum"
                INSTALL_CMD="yum install -y"
                UPDATE_CMD="yum update -y"
            fi
            ;;
        arch|manjaro|endeavouros)
            PACKAGE_MANAGER="pacman"
            INSTALL_CMD="pacman -S --noconfirm"
            UPDATE_CMD="pacman -Syu --noconfirm"
            ;;
        opensuse*|sles)
            PACKAGE_MANAGER="zypper"
            INSTALL_CMD="zypper install -y"
            UPDATE_CMD="zypper update -y"
            ;;
        *)
            log_error "Unsupported distribution: $DISTRO"
            exit 1
            ;;
    esac

    log_success "Package manager: $PACKAGE_MANAGER"
}

# Check if running as root or with sudo
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is not recommended for development setup."
        SUDO=""
    elif command_exists sudo; then
        log_info "Using sudo for privileged operations"
        SUDO="sudo"
    else
        log_error "This script requires root privileges or sudo access"
        exit 1
    fi
}

# Update package repository
update_packages() {
    log_info "Updating package repository..."
    $SUDO $UPDATE_CMD
    log_success "Package repository updated"
}

# Install essential packages
install_essentials() {
    log_info "Installing essential packages..."

    case $PACKAGE_MANAGER in
        apt)
            $SUDO $INSTALL_CMD \
                curl \
                wget \
                git \
                build-essential \
                software-properties-common \
                apt-transport-https \
                ca-certificates \
                gnupg \
                lsb-release \
                unzip \
                tree \
                htop \
                jq \
                vim \
                nano
            ;;
        dnf|yum)
            $SUDO $INSTALL_CMD \
                curl \
                wget \
                git \
                gcc \
                gcc-c++ \
                make \
                unzip \
                tree \
                htop \
                jq \
                vim \
                nano \
                dnf-plugins-core
            ;;
        pacman)
            $SUDO $INSTALL_CMD \
                curl \
                wget \
                git \
                base-devel \
                unzip \
                tree \
                htop \
                jq \
                vim \
                nano
            ;;
        zypper)
            $SUDO $INSTALL_CMD \
                curl \
                wget \
                git \
                gcc \
                gcc-c++ \
                make \
                unzip \
                tree \
                htop \
                jq \
                vim \
                nano
            ;;
    esac

    log_success "Essential packages installed"
}

# Install Docker
install_docker() {
    log_info "Checking for Docker..."

    if command_exists docker; then
        log_success "Docker already installed"
        docker --version
    else
        log_info "Installing Docker..."

        case $PACKAGE_MANAGER in
            apt)
                # Add Docker GPG key
                curl -fsSL https://download.docker.com/linux/$DISTRO/gpg | $SUDO gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

                # Add Docker repository
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$DISTRO $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null

                # Update and install
                $SUDO apt-get update
                $SUDO $INSTALL_CMD docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;

            dnf)
                # Add Docker repository
                $SUDO dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
                $SUDO $INSTALL_CMD docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;

            yum)
                # Add Docker repository
                $SUDO yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                $SUDO $INSTALL_CMD docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                ;;

            pacman)
                $SUDO $INSTALL_CMD docker docker-compose
                ;;

            zypper)
                $SUDO $INSTALL_CMD docker docker-compose
                ;;
        esac

        # Start and enable Docker
        $SUDO systemctl start docker
        $SUDO systemctl enable docker

        # Add current user to docker group
        $SUDO usermod -aG docker $USER

        log_success "Docker installed"
        log_warning "You need to log out and back in for Docker group membership to take effect"
    fi
}

# Install Docker Compose (standalone)
install_docker_compose() {
    log_info "Checking for Docker Compose..."

    if command_exists docker-compose; then
        log_success "Docker Compose already installed"
        docker-compose --version
    else
        log_info "Installing Docker Compose..."

        # Install latest version
        DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)
        $SUDO curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        $SUDO chmod +x /usr/local/bin/docker-compose

        log_success "Docker Compose installed"
    fi
}

# Install Node.js and npm
install_nodejs() {
    log_info "Checking for Node.js..."

    if command_exists node; then
        node_version=$(node --version)
        log_success "Node.js already installed (version: $node_version)"

        # Check if Node version is compatible (18+)
        major_version=$(echo "$node_version" | cut -d'.' -f1 | sed 's/v//')
        if [ "$major_version" -lt 18 ]; then
            log_warning "Node.js version $node_version is older than recommended (18+)"
        fi
    else
        log_info "Installing Node.js..."

        case $PACKAGE_MANAGER in
            apt)
                # Install NodeSource repository
                curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash -
                $SUDO $INSTALL_CMD nodejs
                ;;

            dnf|yum)
                # Install NodeSource repository
                curl -fsSL https://rpm.nodesource.com/setup_20.x | $SUDO bash -
                $SUDO $INSTALL_CMD nodejs npm
                ;;

            pacman)
                $SUDO $INSTALL_CMD nodejs npm
                ;;

            zypper)
                $SUDO $INSTALL_CMD nodejs20 npm20
                ;;
        esac

        log_success "Node.js installed"
    fi
}

# Install Python
install_python() {
    log_info "Checking for Python..."

    if command_exists python3; then
        python_version=$(python3 --version)
        log_success "Python already installed ($python_version)"

        # Check if Python version is compatible (3.11+)
        python_major=$(python3 -c "import sys; print(sys.version_info.major)")
        python_minor=$(python3 -c "import sys; print(sys.version_info.minor)")

        if [ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]; then
            log_warning "Python version is older than recommended (3.11+)"
        fi
    else
        log_info "Installing Python..."

        case $PACKAGE_MANAGER in
            apt)
                $SUDO $INSTALL_CMD python3 python3-pip python3-venv python3-dev
                ;;

            dnf|yum)
                $SUDO $INSTALL_CMD python3 python3-pip python3-venv python3-devel
                ;;

            pacman)
                $SUDO $INSTALL_CMD python python-pip
                ;;

            zypper)
                $SUDO $INSTALL_CMD python3 python3-pip python3-venv python3-devel
                ;;
        esac

        log_success "Python installed"
    fi

    # Install/upgrade pip and essential packages
    log_info "Installing/upgrading pip and essential packages..."
    python3 -m pip install --user --upgrade pip setuptools wheel
}

# Install mkcert for local SSL
install_mkcert() {
    log_info "Checking for mkcert..."

    if command_exists mkcert; then
        log_success "mkcert already installed"
    else
        log_info "Installing mkcert..."

        # Download and install mkcert
        MKCERT_VERSION=$(curl -s https://api.github.com/repos/FiloSottile/mkcert/releases/latest | jq -r .tag_name)
        ARCH=$(uname -m)
        case $ARCH in
            x86_64) ARCH="amd64" ;;
            aarch64) ARCH="arm64" ;;
            armv7l) ARCH="arm" ;;
        esac

        curl -L "https://github.com/FiloSottile/mkcert/releases/download/${MKCERT_VERSION}/mkcert-${MKCERT_VERSION}-linux-${ARCH}" -o mkcert
        $SUDO mv mkcert /usr/local/bin/mkcert
        $SUDO chmod +x /usr/local/bin/mkcert

        # Install root CA
        mkcert -install

        log_success "mkcert installed and configured"
    fi
}

# Install PostgreSQL client tools
install_postgresql_client() {
    log_info "Installing PostgreSQL client tools..."

    case $PACKAGE_MANAGER in
        apt)
            $SUDO $INSTALL_CMD postgresql-client
            ;;
        dnf|yum)
            $SUDO $INSTALL_CMD postgresql
            ;;
        pacman)
            $SUDO $INSTALL_CMD postgresql-libs
            ;;
        zypper)
            $SUDO $INSTALL_CMD postgresql
            ;;
    esac

    log_success "PostgreSQL client tools installed"
}

# Install Redis client tools
install_redis_client() {
    log_info "Installing Redis client tools..."

    case $PACKAGE_MANAGER in
        apt)
            $SUDO $INSTALL_CMD redis-tools
            ;;
        dnf|yum)
            $SUDO $INSTALL_CMD redis
            ;;
        pacman)
            $SUDO $INSTALL_CMD redis
            ;;
        zypper)
            $SUDO $INSTALL_CMD redis
            ;;
    esac

    log_success "Redis client tools installed"
}

# Install VS Code (optional)
install_vscode() {
    if ! command_exists code; then
        read -p "Would you like to install Visual Studio Code? (y/N): " install_vscode_choice
        if [[ $install_vscode_choice =~ ^[Yy]$ ]]; then
            log_info "Installing Visual Studio Code..."

            case $PACKAGE_MANAGER in
                apt)
                    # Add Microsoft GPG key and repository
                    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | $SUDO gpg --dearmor -o /usr/share/keyrings/microsoft-archive-keyring.gpg
                    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/repos/code stable main" | $SUDO tee /etc/apt/sources.list.d/vscode.list > /dev/null
                    $SUDO apt-get update
                    $SUDO $INSTALL_CMD code
                    ;;

                dnf)
                    $SUDO rpm --import https://packages.microsoft.com/keys/microsoft.asc
                    echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" | $SUDO tee /etc/yum.repos.d/vscode.repo > /dev/null
                    $SUDO $INSTALL_CMD code
                    ;;

                yum)
                    $SUDO rpm --import https://packages.microsoft.com/keys/microsoft.asc
                    echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" | $SUDO tee /etc/yum.repos.d/vscode.repo > /dev/null
                    $SUDO $INSTALL_CMD code
                    ;;

                pacman)
                    # VS Code is available in AUR
                    if command_exists yay; then
                        yay -S --noconfirm visual-studio-code-bin
                    elif command_exists paru; then
                        paru -S --noconfirm visual-studio-code-bin
                    else
                        log_warning "AUR helper not found. Install yay or paru first, then run: yay -S visual-studio-code-bin"
                    fi
                    ;;

                zypper)
                    $SUDO rpm --import https://packages.microsoft.com/keys/microsoft.asc
                    $SUDO zypper addrepo https://packages.microsoft.com/yumrepos/vscode vscode
                    $SUDO $INSTALL_CMD code
                    ;;
            esac

            log_success "Visual Studio Code installed"
        fi
    else
        log_success "Visual Studio Code already installed"
    fi
}

# Set up environment variables
setup_environment() {
    log_info "Setting up environment variables..."

    # Determine shell and config file
    if [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    else
        SHELL_CONFIG="$HOME/.bashrc"
    fi

    # Create config file if it doesn't exist
    touch "$SHELL_CONFIG"

    # Add LICS development environment variables
    cat >> "$SHELL_CONFIG" << 'EOF'

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

    log_success "Environment variables configured in $SHELL_CONFIG"
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

# Configure firewall (if needed)
configure_firewall() {
    log_info "Checking firewall configuration..."

    if command_exists ufw; then
        # Ubuntu/Debian firewall
        log_info "Configuring UFW firewall..."
        $SUDO ufw allow 3000/tcp comment "LICS Frontend"
        $SUDO ufw allow 8000/tcp comment "LICS Backend API"
        $SUDO ufw allow 8001/tcp comment "LICS WebSocket"
        log_success "UFW firewall configured"
    elif command_exists firewall-cmd; then
        # CentOS/RHEL/Fedora firewall
        log_info "Configuring firewalld..."
        $SUDO firewall-cmd --permanent --add-port=3000/tcp
        $SUDO firewall-cmd --permanent --add-port=8000/tcp
        $SUDO firewall-cmd --permanent --add-port=8001/tcp
        $SUDO firewall-cmd --reload
        log_success "firewalld configured"
    else
        log_info "No supported firewall detected, skipping firewall configuration"
    fi
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

    # Check Docker is running (may need manual start)
    if systemctl is-active --quiet docker; then
        log_success "Docker service is running"
    else
        log_warning "Docker service is not running. Start it with: sudo systemctl start docker"
    fi

    if $all_good; then
        log_success "All tools are installed!"
        return 0
    else
        log_error "Some tools are missing or not working properly"
        return 1
    fi
}

# Main setup function
main() {
    echo "=================================="
    echo "LICS Linux Development Setup"
    echo "=================================="
    echo ""

    log_info "Starting Linux development environment setup..."

    # Check if running on Linux
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "This script is for Linux only"
        exit 1
    fi

    # Run setup steps
    detect_distro
    check_privileges
    update_packages
    install_essentials
    install_docker
    install_docker_compose
    install_nodejs
    install_python
    install_mkcert
    install_postgresql_client
    install_redis_client
    install_vscode
    setup_environment
    generate_ssl_certificates
    configure_firewall

    echo ""
    echo "=================================="
    log_success "Linux setup completed!"
    echo "=================================="
    echo ""

    # Verify installation
    if verify_installation; then
        echo ""
        log_info "Next steps:"
        echo "1. Log out and back in (for Docker group membership)"
        echo "2. Restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
        echo "3. Start Docker service: sudo systemctl start docker"
        echo "4. Navigate to your LICS project directory"
        echo "5. Copy .env.example to .env and configure as needed"
        echo "6. Run: make install (to install project dependencies)"
        echo "7. Run: make dev (to start development environment)"
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
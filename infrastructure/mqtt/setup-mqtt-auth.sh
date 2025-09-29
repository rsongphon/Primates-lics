#!/bin/bash

# LICS MQTT Authentication Setup Script
# Creates users and passwords for MQTT broker authentication

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASSWORD_FILE="${SCRIPT_DIR}/passwords.txt"
TEMP_PASSWORD_FILE="${PASSWORD_FILE}.tmp"
LOG_FILE="${SCRIPT_DIR}/mqtt-auth-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if mosquitto_passwd is available
check_dependencies() {
    log "Checking dependencies..."

    if ! command -v mosquitto_passwd &> /dev/null; then
        error "mosquitto_passwd command not found. Please install mosquitto-clients."
        error "  Ubuntu/Debian: sudo apt-get install mosquitto-clients"
        error "  CentOS/RHEL: sudo yum install mosquitto"
        error "  macOS: brew install mosquitto"
        exit 1
    fi

    success "Dependencies check passed"
}

# Generate secure random password
generate_password() {
    local length=${1:-16}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Create or update user password
create_user() {
    local username="$1"
    local password="$2"
    local description="$3"

    log "Creating/updating user: $username ($description)"

    # Create password file if it doesn't exist
    if [ ! -f "$PASSWORD_FILE" ]; then
        touch "$PASSWORD_FILE"
        chmod 600 "$PASSWORD_FILE"
    fi

    # Add or update user
    mosquitto_passwd -b "$PASSWORD_FILE" "$username" "$password"

    if [ $? -eq 0 ]; then
        success "User $username created/updated successfully"
        echo "  Username: $username"
        echo "  Password: $password"
        echo "  Description: $description"
        echo ""
    else
        error "Failed to create/update user $username"
        return 1
    fi
}

# Remove user from password file
remove_user() {
    local username="$1"

    if [ ! -f "$PASSWORD_FILE" ]; then
        warning "Password file does not exist"
        return 1
    fi

    log "Removing user: $username"
    mosquitto_passwd -D "$PASSWORD_FILE" "$username"

    if [ $? -eq 0 ]; then
        success "User $username removed successfully"
    else
        error "Failed to remove user $username"
        return 1
    fi
}

# List all users in password file
list_users() {
    log "Listing MQTT users..."

    if [ ! -f "$PASSWORD_FILE" ]; then
        warning "Password file does not exist"
        return 1
    fi

    echo "Current MQTT users:"
    cut -d: -f1 "$PASSWORD_FILE" | while read username; do
        echo "  - $username"
    done
}

# Setup default users for LICS
setup_default_users() {
    log "Setting up default LICS MQTT users..."

    # Backup existing password file
    if [ -f "$PASSWORD_FILE" ]; then
        cp "$PASSWORD_FILE" "${PASSWORD_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        warning "Backed up existing password file"
    fi

    # Generate secure passwords
    local backend_password=$(generate_password 24)
    local admin_password=$(generate_password 16)
    local device_password=$(generate_password 20)
    local monitor_password=$(generate_password 16)

    # Create users
    create_user "lics-backend" "$backend_password" "Backend service user"
    create_user "lics-admin" "$admin_password" "Administrative user"
    create_user "lics-device-template" "$device_password" "Template for device users"
    create_user "lics-monitor" "$monitor_password" "Monitoring and health checks"

    # Create environment file with passwords
    local env_file="${SCRIPT_DIR}/mqtt-credentials.env"
    cat > "$env_file" << EOF
# LICS MQTT Credentials
# Generated on: $(date)
#
# IMPORTANT: Keep this file secure and do not commit to version control!
# Add this file to .gitignore

# Backend service credentials
MQTT_BACKEND_USERNAME=lics-backend
MQTT_BACKEND_PASSWORD=$backend_password

# Admin credentials
MQTT_ADMIN_USERNAME=lics-admin
MQTT_ADMIN_PASSWORD=$admin_password

# Device template credentials (use for new devices)
MQTT_DEVICE_TEMPLATE_USERNAME=lics-device-template
MQTT_DEVICE_TEMPLATE_PASSWORD=$device_password

# Monitoring credentials
MQTT_MONITOR_USERNAME=lics-monitor
MQTT_MONITOR_PASSWORD=$monitor_password
EOF

    chmod 600 "$env_file"
    success "Credentials saved to: $env_file"

    # Create .gitignore entry
    local gitignore_file="${SCRIPT_DIR}/.gitignore"
    if [ ! -f "$gitignore_file" ]; then
        cat > "$gitignore_file" << EOF
# MQTT Authentication Files
passwords.txt
mqtt-credentials.env
*.backup.*
mqtt-auth-setup.log
EOF
        success "Created .gitignore file"
    fi
}

# Create device user with specific device ID
create_device_user() {
    local device_id="$1"

    if [ -z "$device_id" ]; then
        error "Device ID is required"
        echo "Usage: $0 create-device <device_id>"
        return 1
    fi

    local username="lics-device-${device_id}"
    local password=$(generate_password 20)

    create_user "$username" "$password" "Device user for $device_id"

    # Add to device credentials file
    local device_env="${SCRIPT_DIR}/device-credentials.env"
    echo "# Device: $device_id" >> "$device_env"
    echo "MQTT_${device_id^^}_USERNAME=$username" >> "$device_env"
    echo "MQTT_${device_id^^}_PASSWORD=$password" >> "$device_env"
    echo "" >> "$device_env"

    chmod 600 "$device_env"
    success "Device credentials appended to: $device_env"
}

# Validate password file
validate_passwords() {
    log "Validating password file..."

    if [ ! -f "$PASSWORD_FILE" ]; then
        error "Password file does not exist"
        return 1
    fi

    # Check file permissions
    local perms=$(stat -c "%a" "$PASSWORD_FILE" 2>/dev/null || stat -f "%A" "$PASSWORD_FILE" 2>/dev/null)
    if [ "$perms" != "600" ] && [ "$perms" != "0600" ]; then
        warning "Password file permissions are not 600. Current: $perms"
        log "Fixing permissions..."
        chmod 600 "$PASSWORD_FILE"
    fi

    # Validate file format
    local line_count=0
    while IFS=: read -r username hash; do
        line_count=$((line_count + 1))

        if [ -z "$username" ] || [ -z "$hash" ]; then
            error "Invalid format at line $line_count"
            return 1
        fi

        # Check username format
        if [[ ! "$username" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            warning "Username '$username' contains invalid characters"
        fi

        # Check if hash looks valid (mosquitto uses $6$ for SHA-512)
        if [[ ! "$hash" =~ ^\$6\$ ]]; then
            warning "Password hash for '$username' may be invalid"
        fi

    done < "$PASSWORD_FILE"

    success "Validated $line_count users in password file"
}

# Show usage information
show_usage() {
    echo "LICS MQTT Authentication Setup Script"
    echo ""
    echo "Usage: $0 [command] [arguments]"
    echo ""
    echo "Commands:"
    echo "  setup                    - Setup default LICS users"
    echo "  create <user> <pass>     - Create or update a user"
    echo "  remove <user>           - Remove a user"
    echo "  create-device <id>      - Create device-specific user"
    echo "  list                    - List all users"
    echo "  validate                - Validate password file"
    echo "  help                    - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 create myuser mypassword"
    echo "  $0 create-device rpi-001"
    echo "  $0 remove baduser"
    echo "  $0 list"
}

# Main execution
main() {
    # Create log file
    touch "$LOG_FILE"

    log "LICS MQTT Authentication Setup Script started"
    log "Script directory: $SCRIPT_DIR"
    log "Password file: $PASSWORD_FILE"

    # Check dependencies first
    check_dependencies

    case "${1:-setup}" in
        setup)
            setup_default_users
            validate_passwords
            ;;
        create)
            if [ $# -ne 3 ]; then
                error "Usage: $0 create <username> <password>"
                exit 1
            fi
            create_user "$2" "$3" "Custom user"
            ;;
        remove)
            if [ $# -ne 2 ]; then
                error "Usage: $0 remove <username>"
                exit 1
            fi
            remove_user "$2"
            ;;
        create-device)
            if [ $# -ne 2 ]; then
                error "Usage: $0 create-device <device_id>"
                exit 1
            fi
            create_device_user "$2"
            ;;
        list)
            list_users
            ;;
        validate)
            validate_passwords
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac

    log "MQTT authentication setup completed"
}

# Run main function with all arguments
main "$@"
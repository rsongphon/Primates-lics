#!/bin/bash

# Cron-based Database Maintenance Scheduler
# This script sets up automated maintenance tasks via cron

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $*${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $*${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $*${NC}"
}

log_error() {
    echo -e "${RED}❌ $*${NC}"
}

# Check if running as root (needed for system cron)
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_info "Running as root - can install system-wide cron jobs"
        return 0
    else
        log_info "Running as user - will install user cron jobs"
        return 1
    fi
}

# Install cron jobs
install_cron_jobs() {
    local is_root=$1
    local cron_file

    if [ "$is_root" -eq 0 ]; then
        # System-wide cron jobs
        cron_file="/etc/cron.d/lics-database-maintenance"
        log_info "Installing system-wide cron jobs to $cron_file"

        cat > "$cron_file" << EOF
# LICS Database Maintenance Cron Jobs
# Generated on $(date)

# Environment variables
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash

# Daily cleanup at 2:00 AM
0 2 * * * root cd $PROJECT_ROOT && $SCRIPT_DIR/cleanup.sh quick >> /var/log/lics-maintenance.log 2>&1

# Weekly maintenance on Sunday at 3:00 AM
0 3 * * 0 root cd $PROJECT_ROOT && $SCRIPT_DIR/cleanup.sh maintenance >> /var/log/lics-maintenance.log 2>&1

# Monthly full cleanup on 1st day at 4:00 AM
0 4 1 * * root cd $PROJECT_ROOT && $SCRIPT_DIR/cleanup.sh full >> /var/log/lics-maintenance.log 2>&1

# Python maintenance script daily at 2:30 AM
30 2 * * * root cd $PROJECT_ROOT && python3 $SCRIPT_DIR/maintenance.py --tasks health_check cleanup_old_data >> /var/log/lics-maintenance.log 2>&1

# Python maintenance script weekly on Sunday at 3:30 AM
30 3 * * 0 root cd $PROJECT_ROOT && python3 $SCRIPT_DIR/maintenance.py >> /var/log/lics-maintenance.log 2>&1
EOF

        chmod 644 "$cron_file"
        log_success "System cron jobs installed"

    else
        # User cron jobs
        log_info "Installing user cron jobs"

        # Create temporary cron file
        local temp_cron=$(mktemp)

        # Get existing cron jobs
        crontab -l 2>/dev/null > "$temp_cron" || true

        # Remove any existing LICS maintenance jobs
        sed -i '/# LICS Database Maintenance/,/^$/d' "$temp_cron" 2>/dev/null || true
        sed -i '/lics.*maintenance/d' "$temp_cron" 2>/dev/null || true

        # Add new cron jobs
        cat >> "$temp_cron" << EOF

# LICS Database Maintenance Cron Jobs
# Generated on $(date)

# Daily cleanup at 2:00 AM
0 2 * * * cd $PROJECT_ROOT && $SCRIPT_DIR/cleanup.sh quick >> $PROJECT_ROOT/logs/maintenance.log 2>&1

# Weekly maintenance on Sunday at 3:00 AM
0 3 * * 0 cd $PROJECT_ROOT && $SCRIPT_DIR/cleanup.sh maintenance >> $PROJECT_ROOT/logs/maintenance.log 2>&1

# Monthly full cleanup on 1st day at 4:00 AM
0 4 1 * * cd $PROJECT_ROOT && $SCRIPT_DIR/cleanup.sh full >> $PROJECT_ROOT/logs/maintenance.log 2>&1

# Python maintenance script daily at 2:30 AM
30 2 * * * cd $PROJECT_ROOT && python3 $SCRIPT_DIR/maintenance.py --tasks health_check cleanup_old_data >> $PROJECT_ROOT/logs/maintenance.log 2>&1

EOF

        # Install the cron jobs
        if crontab "$temp_cron"; then
            log_success "User cron jobs installed"
        else
            log_error "Failed to install user cron jobs"
            rm -f "$temp_cron"
            return 1
        fi

        rm -f "$temp_cron"
    fi

    # Ensure log directory exists
    mkdir -p "$PROJECT_ROOT/logs"

    # Restart cron service if running as root
    if [ "$is_root" -eq 0 ]; then
        if command -v systemctl &> /dev/null; then
            systemctl reload cron 2>/dev/null || systemctl reload crond 2>/dev/null || true
        elif command -v service &> /dev/null; then
            service cron reload 2>/dev/null || service crond reload 2>/dev/null || true
        fi
    fi
}

# Remove cron jobs
remove_cron_jobs() {
    local is_root=$1

    if [ "$is_root" -eq 0 ]; then
        # Remove system-wide cron jobs
        local cron_file="/etc/cron.d/lics-database-maintenance"
        if [ -f "$cron_file" ]; then
            rm -f "$cron_file"
            log_success "System cron jobs removed"
        else
            log_warn "No system cron jobs found"
        fi
    else
        # Remove user cron jobs
        local temp_cron=$(mktemp)

        if crontab -l 2>/dev/null > "$temp_cron"; then
            # Remove LICS maintenance jobs
            sed -i '/# LICS Database Maintenance/,/^$/d' "$temp_cron" 2>/dev/null || true
            sed -i '/lics.*maintenance/d' "$temp_cron" 2>/dev/null || true

            if crontab "$temp_cron"; then
                log_success "User cron jobs removed"
            else
                log_error "Failed to remove user cron jobs"
            fi
        else
            log_warn "No user cron jobs found"
        fi

        rm -f "$temp_cron"
    fi
}

# List current cron jobs
list_cron_jobs() {
    local is_root=$1

    if [ "$is_root" -eq 0 ]; then
        # List system-wide cron jobs
        local cron_file="/etc/cron.d/lics-database-maintenance"
        if [ -f "$cron_file" ]; then
            log_info "System cron jobs:"
            cat "$cron_file"
        else
            log_warn "No system cron jobs found"
        fi
    else
        # List user cron jobs
        log_info "User cron jobs:"
        if crontab -l 2>/dev/null | grep -A 10 -B 2 "LICS Database Maintenance"; then
            log_success "Found LICS maintenance jobs"
        else
            log_warn "No LICS maintenance jobs found in user crontab"
        fi
    fi
}

# Test cron jobs
test_cron_jobs() {
    log_info "Testing maintenance scripts..."

    # Test cleanup script
    if [ -x "$SCRIPT_DIR/cleanup.sh" ]; then
        log_info "Testing cleanup script..."
        if "$SCRIPT_DIR/cleanup.sh" quick; then
            log_success "Cleanup script test passed"
        else
            log_error "Cleanup script test failed"
            return 1
        fi
    else
        log_error "Cleanup script not found or not executable"
        return 1
    fi

    # Test Python maintenance script
    if [ -f "$SCRIPT_DIR/maintenance.py" ]; then
        log_info "Testing Python maintenance script..."
        if cd "$PROJECT_ROOT" && python3 "$SCRIPT_DIR/maintenance.py" --config-check; then
            log_success "Python maintenance script test passed"
        else
            log_error "Python maintenance script test failed"
            return 1
        fi
    else
        log_error "Python maintenance script not found"
        return 1
    fi

    log_success "All maintenance scripts tested successfully"
}

# Create systemd timer (alternative to cron)
create_systemd_timer() {
    if ! command -v systemctl &> /dev/null; then
        log_error "systemctl not available - cannot create systemd timers"
        return 1
    fi

    if [ "$EUID" -ne 0 ]; then
        log_error "Root privileges required to create systemd timers"
        return 1
    fi

    log_info "Creating systemd timer for database maintenance..."

    # Create service file
    cat > /etc/systemd/system/lics-db-maintenance.service << EOF
[Unit]
Description=LICS Database Maintenance
After=docker.service postgresql.service

[Service]
Type=oneshot
User=root
WorkingDirectory=$PROJECT_ROOT
ExecStart=$SCRIPT_DIR/cleanup.sh maintenance
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Create timer file
    cat > /etc/systemd/system/lics-db-maintenance.timer << EOF
[Unit]
Description=Run LICS Database Maintenance Daily
Requires=lics-db-maintenance.service

[Timer]
OnCalendar=daily
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Reload systemd and enable timer
    systemctl daemon-reload
    systemctl enable lics-db-maintenance.timer
    systemctl start lics-db-maintenance.timer

    log_success "Systemd timer created and started"
    systemctl status lics-db-maintenance.timer --no-pager
}

# Show help
show_help() {
    cat << EOF
LICS Database Maintenance Cron Scheduler

Usage: $0 [COMMAND]

Commands:
  install     - Install cron jobs for automated maintenance
  remove      - Remove installed cron jobs
  list        - List current LICS maintenance cron jobs
  test        - Test maintenance scripts
  systemd     - Create systemd timer (root only, alternative to cron)

Examples:
  $0 install      # Install cron jobs
  $0 list         # Show current jobs
  $0 test         # Test scripts
  $0 remove       # Remove cron jobs

Scheduled Tasks:
  - Daily (2:00 AM): Quick cleanup (logs)
  - Weekly (Sunday 3:00 AM): Database maintenance
  - Monthly (1st day 4:00 AM): Full cleanup
  - Daily (2:30 AM): Health checks
  - Weekly (Sunday 3:30 AM): Comprehensive maintenance

EOF
}

# Main function
main() {
    local command="${1:-help}"
    local is_root=1

    if check_root; then
        is_root=0
    fi

    case "$command" in
        "install")
            install_cron_jobs $is_root
            ;;
        "remove")
            remove_cron_jobs $is_root
            ;;
        "list")
            list_cron_jobs $is_root
            ;;
        "test")
            test_cron_jobs
            ;;
        "systemd")
            create_systemd_timer
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
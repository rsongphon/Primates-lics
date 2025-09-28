#!/bin/bash

# Database Cleanup and Maintenance Script
# Automated cleanup procedures for LICS database infrastructure

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs/database"
LOG_FILE="${LOG_DIR}/cleanup-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
    echo -e "${BLUE}ℹ️  $*${NC}"
}

log_warn() {
    log "WARN" "$@"
    echo -e "${YELLOW}⚠️  $*${NC}"
}

log_error() {
    log "ERROR" "$@"
    echo -e "${RED}❌ $*${NC}"
}

log_success() {
    log "SUCCESS" "$@"
    echo -e "${GREEN}✅ $*${NC}"
}

# Check if running in Docker
is_docker() {
    [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null || false
}

# Check if services are running
check_services() {
    log_info "Checking database services status..."

    if is_docker; then
        # Running inside Docker container
        log_info "Running inside Docker container"
        return 0
    else
        # Check Docker Compose services
        if ! command -v docker-compose &> /dev/null; then
            log_error "docker-compose not found. Please install Docker Compose."
            return 1
        fi

        cd "$PROJECT_ROOT"

        # Check if services are running
        local services=("postgres" "redis" "influxdb")
        for service in "${services[@]}"; do
            if docker-compose ps "$service" | grep -q "Up"; then
                log_success "$service is running"
            else
                log_warn "$service is not running"
            fi
        done
    fi
}

# PostgreSQL maintenance
postgres_maintenance() {
    log_info "Starting PostgreSQL maintenance..."

    local db_url="${DATABASE_URL:-postgresql://lics:lics123@localhost:5432/lics}"

    if is_docker; then
        # Running inside container
        local psql_cmd="psql $db_url"
    else
        # Running on host, use Docker
        local psql_cmd="docker-compose exec -T postgres psql -U lics -d lics"
    fi

    # VACUUM and ANALYZE
    log_info "Running VACUUM ANALYZE on critical tables..."

    local tables=("organizations" "users" "devices" "experiments" "tasks")
    for table in "${tables[@]}"; do
        if $psql_cmd -c "\\dt $table" &>/dev/null; then
            log_info "VACUUM ANALYZE $table..."
            if $psql_cmd -c "VACUUM ANALYZE $table;" &>>"$LOG_FILE"; then
                log_success "VACUUM ANALYZE completed for $table"
            else
                log_warn "VACUUM ANALYZE failed for $table"
            fi
        else
            log_warn "Table $table does not exist, skipping"
        fi
    done

    # Update statistics
    log_info "Updating table statistics..."
    if $psql_cmd -c "ANALYZE;" &>>"$LOG_FILE"; then
        log_success "Statistics updated"
    else
        log_error "Failed to update statistics"
    fi

    # Check for bloated indexes
    log_info "Checking for bloated indexes..."
    $psql_cmd -c "
        SELECT schemaname, tablename, indexname,
               pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_stat_user_indexes
        WHERE idx_scan < 100
        AND pg_relation_size(indexrelid) > 1024 * 1024
        ORDER BY pg_relation_size(indexrelid) DESC
        LIMIT 10;
    " &>>"$LOG_FILE"

    log_success "PostgreSQL maintenance completed"
}

# Redis maintenance
redis_maintenance() {
    log_info "Starting Redis maintenance..."

    if is_docker; then
        local redis_cmd="redis-cli"
    else
        local redis_cmd="docker-compose exec -T redis redis-cli"
    fi

    # Get memory info
    log_info "Checking Redis memory usage..."
    local memory_info=$($redis_cmd info memory 2>/dev/null || echo "failed")
    if [ "$memory_info" != "failed" ]; then
        echo "$memory_info" | grep -E "(used_memory_human|used_memory_peak_human|mem_fragmentation_ratio)" >> "$LOG_FILE"
        log_success "Redis memory info collected"
    else
        log_warn "Failed to get Redis memory info"
    fi

    # Cleanup expired keys
    log_info "Triggering expired key cleanup..."
    if $redis_cmd eval "return redis.call('scan', 0, 'count', 1000)" 0 &>/dev/null; then
        log_success "Redis cleanup triggered"
    else
        log_warn "Redis cleanup failed"
    fi

    log_success "Redis maintenance completed"
}

# InfluxDB maintenance
influxdb_maintenance() {
    log_info "Starting InfluxDB maintenance..."

    local influx_url="${INFLUXDB_URL:-http://localhost:8086}"
    local influx_token="${INFLUXDB_TOKEN:-lics-admin-token-change-in-production}"
    local influx_org="${INFLUXDB_ORG:-lics}"

    if is_docker; then
        local influx_cmd="influx"
    else
        local influx_cmd="docker-compose exec -T influxdb influx"
    fi

    # Check health
    log_info "Checking InfluxDB health..."
    if $influx_cmd ping &>>"$LOG_FILE"; then
        log_success "InfluxDB is healthy"
    else
        log_warn "InfluxDB health check failed"
        return 1
    fi

    # List buckets and their retention policies
    log_info "Checking bucket retention policies..."
    if command -v curl &>/dev/null; then
        curl -s -H "Authorization: Token $influx_token" \
             "$influx_url/api/v2/buckets?org=$influx_org" | \
             grep -o '"name":"[^"]*"' >> "$LOG_FILE" 2>/dev/null || true
    fi

    log_success "InfluxDB maintenance completed"
}

# Log file cleanup
log_cleanup() {
    log_info "Starting log file cleanup..."

    # Cleanup old log files (older than 30 days)
    local log_dirs=("$PROJECT_ROOT/logs" "$PROJECT_ROOT/data/logs")

    for log_dir in "${log_dirs[@]}"; do
        if [ -d "$log_dir" ]; then
            log_info "Cleaning up logs in $log_dir..."

            # Find and remove old log files
            local deleted_count=0
            while IFS= read -r -d '' file; do
                if [ -f "$file" ] && [ "$(stat -c %Y "$file")" -lt "$(date -d '30 days ago' +%s)" ]; then
                    rm -f "$file"
                    ((deleted_count++))
                fi
            done < <(find "$log_dir" -name "*.log*" -type f -print0 2>/dev/null)

            log_success "Deleted $deleted_count old log files from $log_dir"
        fi
    done
}

# Data retention cleanup
data_retention_cleanup() {
    log_info "Starting data retention cleanup..."

    local db_url="${DATABASE_URL:-postgresql://lics:lics123@localhost:5432/lics}"

    if is_docker; then
        local psql_cmd="psql $db_url"
    else
        local psql_cmd="docker-compose exec -T postgres psql -U lics -d lics"
    fi

    # Cleanup old audit logs (if table exists)
    log_info "Cleaning up old audit logs..."
    $psql_cmd -c "
        DO \$\$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'audit_logs') THEN
                DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '90 days';
                RAISE NOTICE 'Audit logs cleanup completed';
            END IF;
        END
        \$\$;
    " &>>"$LOG_FILE"

    # Cleanup old session data (if table exists)
    log_info "Cleaning up old session data..."
    $psql_cmd -c "
        DO \$\$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_sessions') THEN
                DELETE FROM user_sessions WHERE last_accessed < NOW() - INTERVAL '30 days';
                RAISE NOTICE 'Session data cleanup completed';
            END IF;
        END
        \$\$;
    " &>>"$LOG_FILE"

    log_success "Data retention cleanup completed"
}

# Backup verification
verify_backups() {
    log_info "Verifying recent backups..."

    local backup_dir="${PROJECT_ROOT}/backups"
    if [ -d "$backup_dir" ]; then
        local recent_backups=$(find "$backup_dir" -name "*.sql" -mtime -7 | wc -l)
        if [ "$recent_backups" -gt 0 ]; then
            log_success "Found $recent_backups recent backup(s)"
        else
            log_warn "No recent backups found in the last 7 days"
        fi
    else
        log_warn "Backup directory not found: $backup_dir"
    fi
}

# Performance monitoring
performance_check() {
    log_info "Running performance checks..."

    local db_url="${DATABASE_URL:-postgresql://lics:lics123@localhost:5432/lics}"

    if is_docker; then
        local psql_cmd="psql $db_url"
    else
        local psql_cmd="docker-compose exec -T postgres psql -U lics -d lics"
    fi

    # Check slow queries (if pg_stat_statements is available)
    log_info "Checking for slow queries..."
    $psql_cmd -c "
        SELECT CASE
            WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')
            THEN 'pg_stat_statements available'
            ELSE 'pg_stat_statements not available'
        END AS status;
    " &>>"$LOG_FILE"

    # Check table sizes
    log_info "Checking table sizes..."
    $psql_cmd -c "
        SELECT schemaname, tablename,
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 10;
    " &>>"$LOG_FILE"

    log_success "Performance check completed"
}

# Main cleanup function
run_cleanup() {
    local cleanup_type="${1:-full}"

    log_info "Starting database cleanup (type: $cleanup_type)..."
    log_info "Log file: $LOG_FILE"

    case "$cleanup_type" in
        "quick")
            check_services
            log_cleanup
            ;;
        "maintenance")
            check_services
            postgres_maintenance
            redis_maintenance
            influxdb_maintenance
            ;;
        "data")
            check_services
            data_retention_cleanup
            log_cleanup
            ;;
        "full")
            check_services
            postgres_maintenance
            redis_maintenance
            influxdb_maintenance
            data_retention_cleanup
            log_cleanup
            verify_backups
            performance_check
            ;;
        *)
            log_error "Unknown cleanup type: $cleanup_type"
            echo "Usage: $0 [quick|maintenance|data|full]"
            exit 1
            ;;
    esac

    log_success "Database cleanup completed successfully!"
    log_info "Check log file for details: $LOG_FILE"
}

# Script help
show_help() {
    cat << EOF
LICS Database Cleanup Script

Usage: $0 [TYPE]

Cleanup Types:
  quick       - Log cleanup only (fast)
  maintenance - Database maintenance tasks (VACUUM, etc.)
  data        - Data retention cleanup
  full        - All cleanup tasks (default)

Examples:
  $0              # Run full cleanup
  $0 quick        # Quick log cleanup
  $0 maintenance  # Database maintenance only

Environment Variables:
  DATABASE_URL    - PostgreSQL connection URL
  REDIS_URL       - Redis connection URL
  INFLUXDB_URL    - InfluxDB connection URL
  INFLUXDB_TOKEN  - InfluxDB access token
  INFLUXDB_ORG    - InfluxDB organization

EOF
}

# Main script execution
main() {
    case "${1:-}" in
        "-h"|"--help"|"help")
            show_help
            exit 0
            ;;
        *)
            run_cleanup "${1:-full}"
            ;;
    esac
}

# Run main function with all arguments
main "$@"
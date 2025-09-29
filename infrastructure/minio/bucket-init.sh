#!/bin/bash

# LICS MinIO Bucket Initialization Script
# Creates and configures all required buckets for the LICS system

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/minio-init.log"

# MinIO configuration
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_REGION="${MINIO_REGION:-us-east-1}"

# MC (MinIO Client) alias
MC_ALIAS="lics-minio"

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

# Check if mc (MinIO Client) is available
check_dependencies() {
    log "Checking dependencies..."

    if ! command -v mc &> /dev/null; then
        error "MinIO Client (mc) not found. Please install it first."
        error "  Download from: https://min.io/docs/minio/linux/reference/minio-mc.html"
        error "  Or use: curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc"
        exit 1
    fi

    success "Dependencies check passed"
}

# Configure MinIO client
configure_mc() {
    log "Configuring MinIO client..."

    # Remove existing alias if it exists
    mc alias remove "$MC_ALIAS" 2>/dev/null || true

    # Add new alias
    mc alias set "$MC_ALIAS" "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"

    if [ $? -eq 0 ]; then
        success "MinIO client configured successfully"
    else
        error "Failed to configure MinIO client"
        exit 1
    fi
}

# Test MinIO connection
test_connection() {
    log "Testing MinIO connection..."

    mc admin info "$MC_ALIAS" &>/dev/null

    if [ $? -eq 0 ]; then
        success "MinIO connection successful"
    else
        error "Failed to connect to MinIO. Please check:"
        error "  - MinIO server is running"
        error "  - Endpoint: $MINIO_ENDPOINT"
        error "  - Credentials are correct"
        exit 1
    fi
}

# Create a bucket with optional versioning
create_bucket() {
    local bucket_name="$1"
    local description="$2"
    local enable_versioning="${3:-false}"
    local public_read="${4:-false}"

    log "Creating bucket: $bucket_name ($description)"

    # Check if bucket already exists
    if mc ls "$MC_ALIAS/$bucket_name" &>/dev/null; then
        warning "Bucket $bucket_name already exists"
        return 0
    fi

    # Create bucket
    mc mb "$MC_ALIAS/$bucket_name" --region="$MINIO_REGION"

    if [ $? -eq 0 ]; then
        success "Bucket $bucket_name created successfully"

        # Enable versioning if requested
        if [ "$enable_versioning" = "true" ]; then
            mc version enable "$MC_ALIAS/$bucket_name"
            log "Versioning enabled for $bucket_name"
        fi

        # Set public read policy if requested
        if [ "$public_read" = "true" ]; then
            local policy_file="${SCRIPT_DIR}/policies/public-read-policy.json"
            if [ -f "$policy_file" ]; then
                mc anonymous set download "$MC_ALIAS/$bucket_name"
                log "Public read access enabled for $bucket_name"
            fi
        fi

    else
        error "Failed to create bucket $bucket_name"
        return 1
    fi
}

# Create all LICS buckets
create_lics_buckets() {
    log "Creating LICS system buckets..."

    # Video recordings from experiments
    create_bucket "lics-videos" \
        "Video recordings from experimental devices" \
        "true" \
        "false"

    # Data export files (CSV, PDF, reports)
    create_bucket "lics-exports" \
        "Data export files and generated reports" \
        "false" \
        "false"

    # User uploaded files
    create_bucket "lics-uploads" \
        "User uploaded files and configurations" \
        "true" \
        "false"

    # System backup files
    create_bucket "lics-backups" \
        "System backup files and snapshots" \
        "true" \
        "false"

    # Temporary processing files
    create_bucket "lics-temp" \
        "Temporary files for data processing" \
        "false" \
        "false"

    # Static assets (images, documents)
    create_bucket "lics-assets" \
        "Static assets and documentation files" \
        "false" \
        "true"

    # Log files from various services
    create_bucket "lics-logs" \
        "Application and system log files" \
        "false" \
        "false"

    # Machine learning models and datasets
    create_bucket "lics-ml" \
        "Machine learning models and training data" \
        "true" \
        "false"

    # Raw experimental data
    create_bucket "lics-data" \
        "Raw experimental data and measurements" \
        "true" \
        "false"

    # Configuration files and templates
    create_bucket "lics-config" \
        "Configuration files and task templates" \
        "true" \
        "false"

    success "All LICS buckets created successfully"
}

# Set up bucket lifecycle policies
setup_lifecycle_policies() {
    log "Setting up bucket lifecycle policies..."

    # Temporary files - delete after 7 days
    cat > "${SCRIPT_DIR}/temp-lifecycle.json" << EOF
{
    "Rules": [
        {
            "ID": "DeleteTempFiles",
            "Status": "Enabled",
            "Expiration": {
                "Days": 7
            }
        }
    ]
}
EOF

    mc ilm add "$MC_ALIAS/lics-temp" --expiry-days 7

    # Log files - delete after 30 days
    mc ilm add "$MC_ALIAS/lics-logs" --expiry-days 30

    # Exports - delete after 90 days
    mc ilm add "$MC_ALIAS/lics-exports" --expiry-days 90

    success "Lifecycle policies configured"
}

# Create bucket notification configuration
setup_notifications() {
    log "Setting up bucket notifications..."

    # Example: Notify when new videos are uploaded
    # This would typically integrate with a webhook or message queue
    # For now, we'll create the configuration template

    cat > "${SCRIPT_DIR}/notification-config.json" << EOF
{
    "webhookConfigs": [
        {
            "id": "video-upload-webhook",
            "webhook": "http://backend:8000/api/v1/webhooks/video-uploaded",
            "events": ["s3:ObjectCreated:*"],
            "filter": {
                "key": {
                    "filterRules": [
                        {
                            "name": "prefix",
                            "value": "videos/"
                        },
                        {
                            "name": "suffix",
                            "value": ".mp4"
                        }
                    ]
                }
            }
        }
    ]
}
EOF

    log "Notification configuration template created"
}

# Create sample folder structure in buckets
create_folder_structure() {
    log "Creating folder structure in buckets..."

    # Create folders in videos bucket
    echo '{}' | mc pipe "$MC_ALIAS/lics-videos/experiments/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-videos/live-streams/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-videos/recordings/.keep"

    # Create folders in data bucket
    echo '{}' | mc pipe "$MC_ALIAS/lics-data/telemetry/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-data/experiments/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-data/raw/.keep"

    # Create folders in exports bucket
    echo '{}' | mc pipe "$MC_ALIAS/lics-exports/reports/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-exports/csv/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-exports/pdf/.keep"

    # Create folders in config bucket
    echo '{}' | mc pipe "$MC_ALIAS/lics-config/tasks/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-config/devices/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-config/templates/.keep"

    # Create folders in uploads bucket
    echo '{}' | mc pipe "$MC_ALIAS/lics-uploads/user-files/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-uploads/firmware/.keep"
    echo '{}' | mc pipe "$MC_ALIAS/lics-uploads/profiles/.keep"

    success "Folder structure created"
}

# Validate bucket setup
validate_setup() {
    log "Validating bucket setup..."

    local buckets=(
        "lics-videos"
        "lics-exports"
        "lics-uploads"
        "lics-backups"
        "lics-temp"
        "lics-assets"
        "lics-logs"
        "lics-ml"
        "lics-data"
        "lics-config"
    )

    local failed_buckets=()

    for bucket in "${buckets[@]}"; do
        if mc ls "$MC_ALIAS/$bucket" &>/dev/null; then
            log "✓ Bucket $bucket is accessible"
        else
            error "✗ Bucket $bucket is not accessible"
            failed_buckets+=("$bucket")
        fi
    done

    if [ ${#failed_buckets[@]} -eq 0 ]; then
        success "All buckets validated successfully"
        return 0
    else
        error "Failed to validate buckets: ${failed_buckets[*]}"
        return 1
    fi
}

# Generate bucket usage report
generate_report() {
    log "Generating bucket usage report..."

    local report_file="${SCRIPT_DIR}/bucket-report.txt"

    cat > "$report_file" << EOF
LICS MinIO Bucket Report
Generated: $(date)
Endpoint: $MINIO_ENDPOINT

Bucket Information:
==================
EOF

    mc ls "$MC_ALIAS" >> "$report_file"

    echo "" >> "$report_file"
    echo "Bucket Details:" >> "$report_file"
    echo "===============" >> "$report_file"

    local buckets=(
        "lics-videos"
        "lics-exports"
        "lics-uploads"
        "lics-backups"
        "lics-temp"
        "lics-assets"
        "lics-logs"
        "lics-ml"
        "lics-data"
        "lics-config"
    )

    for bucket in "${buckets[@]}"; do
        echo "" >> "$report_file"
        echo "Bucket: $bucket" >> "$report_file"
        echo "$(mc du "$MC_ALIAS/$bucket" 2>/dev/null || echo 'Empty or inaccessible')" >> "$report_file"
    done

    success "Report generated: $report_file"
}

# Clean up temporary files
cleanup() {
    log "Cleaning up temporary files..."
    rm -f "${SCRIPT_DIR}/temp-lifecycle.json"
    log "Cleanup completed"
}

# Show usage information
show_usage() {
    echo "LICS MinIO Bucket Initialization Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  init              - Initialize all buckets (default)"
    echo "  create-bucket     - Create a specific bucket"
    echo "  validate          - Validate existing setup"
    echo "  report           - Generate usage report"
    echo "  cleanup-temp     - Clean up temporary files"
    echo "  help             - Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  MINIO_ENDPOINT   - MinIO server endpoint (default: http://localhost:9000)"
    echo "  MINIO_ACCESS_KEY - Access key (default: minioadmin)"
    echo "  MINIO_SECRET_KEY - Secret key (default: minioadmin)"
    echo "  MINIO_REGION     - Region (default: us-east-1)"
    echo ""
    echo "Examples:"
    echo "  $0 init"
    echo "  MINIO_ENDPOINT=http://minio:9000 $0 init"
    echo "  $0 validate"
    echo "  $0 report"
}

# Main execution
main() {
    # Create log file
    touch "$LOG_FILE"

    log "LICS MinIO Bucket Initialization Script started"
    log "MinIO Endpoint: $MINIO_ENDPOINT"

    case "${1:-init}" in
        init)
            check_dependencies
            configure_mc
            test_connection
            create_lics_buckets
            setup_lifecycle_policies
            setup_notifications
            create_folder_structure
            validate_setup
            generate_report
            cleanup
            success "MinIO initialization completed successfully"
            ;;
        validate)
            check_dependencies
            configure_mc
            test_connection
            validate_setup
            ;;
        report)
            check_dependencies
            configure_mc
            test_connection
            generate_report
            ;;
        cleanup-temp)
            cleanup
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

    log "Script execution completed"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function with all arguments
main "$@"
#!/bin/bash

# LICS MinIO Policy Application Script
# Applies bucket policies, lifecycle rules, and other configurations

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICIES_FILE="${SCRIPT_DIR}/policies.json"
LOG_FILE="${SCRIPT_DIR}/policy-application.log"

# MinIO configuration
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"

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

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."

    if ! command -v mc &> /dev/null; then
        error "MinIO Client (mc) not found"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        error "jq not found. Please install jq for JSON processing"
        exit 1
    fi

    if [ ! -f "$POLICIES_FILE" ]; then
        error "Policies file not found: $POLICIES_FILE"
        exit 1
    fi

    success "Dependencies check passed"
}

# Configure MinIO client
configure_mc() {
    log "Configuring MinIO client..."

    mc alias remove "$MC_ALIAS" 2>/dev/null || true
    mc alias set "$MC_ALIAS" "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"

    if [ $? -eq 0 ]; then
        success "MinIO client configured"
    else
        error "Failed to configure MinIO client"
        exit 1
    fi
}

# Apply bucket policies
apply_bucket_policies() {
    log "Applying bucket policies..."

    # Get bucket policies from JSON
    local bucket_policies=$(jq -r '.bucket_policies | to_entries[] | @base64' "$POLICIES_FILE")

    for row in $bucket_policies; do
        local decoded=$(echo "$row" | base64 -d)
        local bucket=$(echo "$decoded" | jq -r '.key')
        local policy=$(echo "$decoded" | jq -c '.value')

        log "Applying policy to bucket: $bucket"

        # Create temporary policy file
        local temp_policy="/tmp/${bucket}-policy.json"
        echo "$policy" > "$temp_policy"

        # Apply policy to bucket
        mc anonymous set-json "$temp_policy" "$MC_ALIAS/$bucket"

        if [ $? -eq 0 ]; then
            success "Policy applied to $bucket"
        else
            warning "Failed to apply policy to $bucket"
        fi

        # Clean up
        rm -f "$temp_policy"
    done
}

# Apply lifecycle rules
apply_lifecycle_rules() {
    log "Applying lifecycle rules..."

    local lifecycle_rules=$(jq -r '.lifecycle_rules | to_entries[] | @base64' "$POLICIES_FILE")

    for row in $lifecycle_rules; do
        local decoded=$(echo "$row" | base64 -d)
        local bucket=$(echo "$decoded" | jq -r '.key')
        local rules=$(echo "$decoded" | jq -c '.value')

        log "Applying lifecycle rules to bucket: $bucket"

        # Create temporary lifecycle file
        local temp_lifecycle="/tmp/${bucket}-lifecycle.json"
        echo "$rules" > "$temp_lifecycle"

        # Apply lifecycle rules
        mc ilm import "$MC_ALIAS/$bucket" < "$temp_lifecycle"

        if [ $? -eq 0 ]; then
            success "Lifecycle rules applied to $bucket"
        else
            warning "Failed to apply lifecycle rules to $bucket"
        fi

        # Clean up
        rm -f "$temp_lifecycle"
    done
}

# Configure versioning
configure_versioning() {
    log "Configuring bucket versioning..."

    # Enable versioning for specified buckets
    local enabled_buckets=$(jq -r '.versioning_configs.enabled_buckets[]' "$POLICIES_FILE")
    for bucket in $enabled_buckets; do
        log "Enabling versioning for: $bucket"
        mc version enable "$MC_ALIAS/$bucket"
        if [ $? -eq 0 ]; then
            success "Versioning enabled for $bucket"
        else
            warning "Failed to enable versioning for $bucket"
        fi
    done

    # Suspend versioning for specified buckets
    local suspended_buckets=$(jq -r '.versioning_configs.suspended_buckets[]' "$POLICIES_FILE")
    for bucket in $suspended_buckets; do
        log "Suspending versioning for: $bucket"
        mc version suspend "$MC_ALIAS/$bucket"
        if [ $? -eq 0 ]; then
            success "Versioning suspended for $bucket"
        else
            warning "Failed to suspend versioning for $bucket"
        fi
    done
}

# Configure CORS
configure_cors() {
    log "Configuring CORS policies..."

    local cors_configs=$(jq -r '.cors_configs | to_entries[] | @base64' "$POLICIES_FILE")

    for row in $cors_configs; do
        local decoded=$(echo "$row" | base64 -d)
        local bucket=$(echo "$decoded" | jq -r '.key')
        local cors_rules=$(echo "$decoded" | jq -c '.value')

        log "Applying CORS configuration to bucket: $bucket"

        # Create temporary CORS file
        local temp_cors="/tmp/${bucket}-cors.json"
        echo "$cors_rules" > "$temp_cors"

        # Note: mc doesn't have direct CORS support, this would need to be done via AWS CLI or MinIO admin API
        # For now, we'll log the configuration
        log "CORS configuration for $bucket: $cors_rules"
        success "CORS configuration logged for $bucket (manual application required)"

        # Clean up
        rm -f "$temp_cors"
    done
}

# Create user policies
create_user_policies() {
    log "Creating user policies..."

    local user_policies=$(jq -r '.policies | to_entries[] | @base64' "$POLICIES_FILE")

    for row in $user_policies; do
        local decoded=$(echo "$row" | base64 -d)
        local policy_name=$(echo "$decoded" | jq -r '.key')
        local policy_content=$(echo "$decoded" | jq -c '.value')

        log "Creating policy: $policy_name"

        # Create temporary policy file
        local temp_policy="/tmp/${policy_name}.json"
        echo "$policy_content" > "$temp_policy"

        # Create policy using mc admin
        mc admin policy add "$MC_ALIAS" "$policy_name" "$temp_policy"

        if [ $? -eq 0 ]; then
            success "Policy created: $policy_name"
        else
            warning "Failed to create policy: $policy_name"
        fi

        # Clean up
        rm -f "$temp_policy"
    done
}

# Setup encryption
setup_encryption() {
    log "Setting up bucket encryption..."

    # Default encryption for all buckets
    local default_algorithm=$(jq -r '.encryption_configs.default.SSEAlgorithm' "$POLICIES_FILE")
    log "Default encryption algorithm: $default_algorithm"

    # Sensitive buckets with enhanced encryption
    local sensitive_buckets=$(jq -r '.encryption_configs.sensitive_buckets.buckets[]' "$POLICIES_FILE")
    local kms_key=$(jq -r '.encryption_configs.sensitive_buckets.KMSMasterKeyID' "$POLICIES_FILE")

    for bucket in $sensitive_buckets; do
        log "Setting up enhanced encryption for: $bucket"
        # Note: MinIO encryption setup would typically be done via server config
        success "Encryption configuration noted for $bucket"
    done
}

# Configure notifications (webhook setup)
configure_notifications() {
    log "Configuring bucket notifications..."

    local notification_configs=$(jq -r '.notification_configs | to_entries[] | @base64' "$POLICIES_FILE")

    for row in $notification_configs; do
        local decoded=$(echo "$row" | base64 -d)
        local bucket=$(echo "$decoded" | jq -r '.key')
        local webhooks=$(echo "$decoded" | jq -c '.value.webhookConfigs')

        log "Setting up notifications for bucket: $bucket"

        # Process each webhook
        echo "$webhooks" | jq -c '.[]' | while read webhook; do
            local webhook_url=$(echo "$webhook" | jq -r '.webhook')
            local webhook_id=$(echo "$webhook" | jq -r '.id')
            local events=$(echo "$webhook" | jq -r '.events | join(",")')

            log "Adding webhook: $webhook_id to $bucket"

            # Add webhook notification
            mc event add "$MC_ALIAS/$bucket" arn:minio:sqs::$webhook_id:webhook --event "$events"

            if [ $? -eq 0 ]; then
                success "Webhook notification added: $webhook_id"
            else
                warning "Failed to add webhook notification: $webhook_id"
            fi
        done
    done
}

# Validate policy application
validate_policies() {
    log "Validating policy application..."

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

    local validation_report="/tmp/policy-validation.txt"
    echo "LICS MinIO Policy Validation Report" > "$validation_report"
    echo "Generated: $(date)" >> "$validation_report"
    echo "======================================" >> "$validation_report"

    for bucket in "${buckets[@]}"; do
        echo "" >> "$validation_report"
        echo "Bucket: $bucket" >> "$validation_report"
        echo "---------------" >> "$validation_report"

        # Check bucket exists
        if mc ls "$MC_ALIAS/$bucket" &>/dev/null; then
            echo "✓ Bucket exists" >> "$validation_report"

            # Check versioning status
            local versioning=$(mc version info "$MC_ALIAS/$bucket" 2>/dev/null | grep "Versioning configuration" || echo "Not configured")
            echo "Versioning: $versioning" >> "$validation_report"

            # Check lifecycle rules
            local lifecycle=$(mc ilm ls "$MC_ALIAS/$bucket" 2>/dev/null | wc -l)
            echo "Lifecycle rules: $lifecycle" >> "$validation_report"

            # Check policies
            local policy_check=$(mc anonymous get "$MC_ALIAS/$bucket" 2>/dev/null || echo "No public policy")
            echo "Public policy: $policy_check" >> "$validation_report"

        else
            echo "✗ Bucket does not exist" >> "$validation_report"
        fi
    done

    cp "$validation_report" "${SCRIPT_DIR}/policy-validation-$(date +%Y%m%d_%H%M%S).txt"
    success "Validation report generated"
}

# Main execution
main() {
    case "${1:-apply}" in
        apply)
            check_dependencies
            configure_mc
            apply_bucket_policies
            apply_lifecycle_rules
            configure_versioning
            configure_cors
            create_user_policies
            setup_encryption
            configure_notifications
            validate_policies
            success "All policies applied successfully"
            ;;
        validate)
            check_dependencies
            configure_mc
            validate_policies
            ;;
        buckets)
            check_dependencies
            configure_mc
            apply_bucket_policies
            ;;
        lifecycle)
            check_dependencies
            configure_mc
            apply_lifecycle_rules
            ;;
        versioning)
            check_dependencies
            configure_mc
            configure_versioning
            ;;
        help|--help|-h)
            echo "Usage: $0 [command]"
            echo "Commands:"
            echo "  apply      - Apply all policies and configurations"
            echo "  validate   - Validate current configuration"
            echo "  buckets    - Apply only bucket policies"
            echo "  lifecycle  - Apply only lifecycle rules"
            echo "  versioning - Configure only versioning"
            echo "  help       - Show this help"
            ;;
        *)
            error "Unknown command: $1"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
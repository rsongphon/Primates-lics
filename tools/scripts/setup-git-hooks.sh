#!/bin/bash
# Setup Git hooks for LICS project
# This script copies the Git hooks to the local .git/hooks directory

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}  LICS Git Hooks Setup${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo
}

# Check if we're in the right directory
check_directory() {
    if [ ! -f "Plan.md" ] || [ ! -f "Documentation.md" ]; then
        print_error "This script must be run from the LICS repository root"
        exit 1
    fi

    if [ ! -d ".git" ]; then
        print_error "This is not a Git repository"
        exit 1
    fi
}

# Setup individual hook
setup_hook() {
    local hook_name="$1"
    local hook_file="tools/scripts/git-hooks/$hook_name"
    local target_file=".git/hooks/$hook_name"

    if [ -f "$hook_file" ]; then
        print_info "Setting up $hook_name hook..."
        cp "$hook_file" "$target_file"
        chmod +x "$target_file"
        print_success "$hook_name hook installed"
    else
        print_warning "$hook_name hook file not found at $hook_file"
    fi
}

# Create git hooks directory structure
create_hooks_directory() {
    print_info "Creating git hooks directory structure..."
    mkdir -p tools/scripts/git-hooks
    print_success "Directory structure created"
}

# Copy existing hooks to the tools directory for version control
copy_existing_hooks() {
    print_info "Copying Git hooks to version control..."

    if [ -f ".git/hooks/pre-commit" ]; then
        cp ".git/hooks/pre-commit" "tools/scripts/git-hooks/pre-commit"
        print_success "pre-commit hook copied to tools/scripts/git-hooks/"
    fi

    if [ -f ".git/hooks/commit-msg" ]; then
        cp ".git/hooks/commit-msg" "tools/scripts/git-hooks/commit-msg"
        print_success "commit-msg hook copied to tools/scripts/git-hooks/"
    fi

    if [ -f ".git/hooks/pre-push" ]; then
        cp ".git/hooks/pre-push" "tools/scripts/git-hooks/pre-push"
        print_success "pre-push hook copied to tools/scripts/git-hooks/"
    fi
}

# Install hooks from tools directory
install_hooks() {
    print_info "Installing Git hooks..."

    # List of hooks to install
    hooks=("pre-commit" "commit-msg" "pre-push")

    for hook in "${hooks[@]}"; do
        setup_hook "$hook"
    done
}

# Verify hooks installation
verify_hooks() {
    print_info "Verifying hook installation..."

    hooks=("pre-commit" "commit-msg" "pre-push")
    all_installed=true

    for hook in "${hooks[@]}"; do
        if [ -x ".git/hooks/$hook" ]; then
            print_success "$hook hook is installed and executable"
        else
            print_error "$hook hook is missing or not executable"
            all_installed=false
        fi
    done

    if [ "$all_installed" = true ]; then
        print_success "All Git hooks are properly installed"
    else
        print_error "Some Git hooks are missing"
        exit 1
    fi
}

# Show usage information
show_usage() {
    echo "Git Hooks Setup for LICS"
    echo
    echo "This script sets up Git hooks for the LICS project to ensure code quality"
    echo "and consistent commit message formatting."
    echo
    echo "Hooks included:"
    echo "  • pre-commit  - Runs linting and formatting checks before commit"
    echo "  • commit-msg  - Validates commit message format (Conventional Commits)"
    echo "  • pre-push    - Performs additional checks before pushing"
    echo
    echo "Usage:"
    echo "  $0 [options]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verify   Verify that hooks are installed correctly"
    echo "  -f, --force    Force reinstall hooks even if they exist"
    echo
}

# Main execution
main() {
    local force_install=false
    local verify_only=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--verify)
                verify_only=true
                shift
                ;;
            -f|--force)
                force_install=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    print_header

    check_directory

    if [ "$verify_only" = true ]; then
        verify_hooks
        exit 0
    fi

    # Check if hooks already exist
    if [ "$force_install" = false ]; then
        if [ -f ".git/hooks/pre-commit" ] || [ -f ".git/hooks/commit-msg" ] || [ -f ".git/hooks/pre-push" ]; then
            print_warning "Git hooks already exist"
            read -p "Do you want to overwrite them? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Setup cancelled"
                exit 0
            fi
        fi
    fi

    create_hooks_directory
    copy_existing_hooks
    install_hooks
    verify_hooks

    echo
    print_success "Git hooks setup completed successfully!"
    echo
    print_info "The following hooks are now active:"
    echo "  • pre-commit: Validates code quality before commits"
    echo "  • commit-msg: Ensures commit messages follow Conventional Commits"
    echo "  • pre-push: Performs additional checks before pushing"
    echo
    print_info "To disable a hook temporarily, rename it in .git/hooks/"
    print_info "To share hooks with the team, commit changes in tools/scripts/git-hooks/"
    echo
}

# Run main function with all arguments
main "$@"
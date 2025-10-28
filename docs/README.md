# LICS Documentation

Welcome to the central documentation hub for the **Lab Instrument Control System (LICS)**. This documentation is organized to help you quickly find the information you need.

## 📚 Documentation Structure

### 🚀 [Project Overview & Planning](./project/)
- **[Project Overview](./project/overview.md)** - Complete system documentation and architecture
- **[Implementation Plan](./project/implementation-plan.md)** - Detailed development roadmap
- **[Refactoring Plan](./project/refactoring-plan.md)** - Architecture improvement strategy
- **[Project README](./project/project-README.md)** - Main project information
- **[Known Issues](./project/known-issues.md)** - Current issues and tracking

### 🏗️ [Architecture Documentation](./architecture/)
- **[Messaging Architecture](./architecture/messaging-architecture.md)** - Event-driven communication patterns
- **[Diagrams](./architecture/diagrams/)** - System architecture diagrams (coming soon)

### 🛠️ [Development Guides](./development/)
- **[Setup Guide](./development/setup.md)** - Development environment setup
- **[Containerized Development](./development/containerized-development.md)** - Docker-based development workflow
- **[Git Workflow](./development/git-workflow.md)** - Version control and contribution process
- **[Database Migrations](./development/database-migrations.md)** - Database changes and management
- **[Troubleshooting](./development/troubleshooting.md)** - Common issues and solutions

### 🚀 [Implementation Documentation](./implementation/)
#### Phase 1: Foundation
- **[Implementation Summary](./implementation/phase1/implementation-summary.md)** - Phase 1 completion details
- **[Completion Report](./implementation/phase1/completion-report.md)** - Phase 1 final report

#### Phase 2: Database & Performance
- **[Circuit Breaker Summary](./implementation/phase2/circuit-breaker-summary.md)** - Circuit breaker implementation
- **[Integration Notes](./implementation/phase2/integration-notes.md)** - Circuit breaker integration guide

#### Phase 3: Monitoring & SLI/SLO (Future)
- Documentation for Phase 3 implementation

### 🧪 [Testing Documentation](./testing/)
- **[Comprehensive Testing Guide](./testing/comprehensive-guide.md)** - Complete testing strategy
- **[Phase 1 Testing Guide](./testing/phase1-guide.md)** - Foundation phase testing
- **[Phase 2 Testing Guide](./testing/phase2-guide.md)** - Database phase testing
- **[Phase 3 Week 5 Testing Guide](./testing/phase3-week5-guide.md)** - Week 5 specific testing
- **[Manual Instructions](./testing/manual-instructions/phase2-manual-instructions.md)** - Manual testing procedures
- **[Report Generation](./testing/report-generation/phase2-report-generation.md)** - Test report generation
- **[Debugging Guide](./testing/debugging/verbose-debugging.md)** - Troubleshooting tests
- **[Quick Reference](./testing/quick-reference/verbose-quickref.md)** - Quick testing commands

### 🐛 [Issue Tracking](./issues/)
- **[TC-AUTH-009](./issues/tc-auth-009/)** - Authentication issue tracking
  - **[Fix Plan](./issues/tc-auth-009/fix-plan.md)** - Resolution strategy
  - **[Phase 1 Attempt](./issues/tc-auth-009/phase1-attempt.md)** - Initial implementation attempt

### 📊 [Reports & Archives](./reports/)
- **[Phase 1 Reports](./reports/phase1/)** - Phase 1 test reports and summaries
- **[Test Reports Archive](./reports/test-reports/)** - Historical test reports

### 📝 [Templates](./templates/)
- **[Pull Request Template](./templates/pull-request.md)** - GitHub PR template
- **[Development Templates](./templates/development/)** - Development document templates (coming soon)

## 🚀 Quick Start

1. **New to the project?** Start with [Project Overview](./project/overview.md)
2. **Setting up development?** Follow [Setup Guide](./development/setup.md)
3. **Understanding the architecture?** Read [Architecture Documentation](./architecture/)
4. **Need to test something?** Check [Testing Guides](./testing/)
5. **Found an issue?** See [Known Issues](./project/known-issues.md) or create a PR using the [template](./templates/pull-request.md)

## 📖 Additional Documentation

- **Service-specific documentation** can be found in each service directory:
  - [Backend Documentation](../../services/backend/README.md)
  - [Frontend Documentation](../../services/frontend/README.md)
  - [Edge Agent Documentation](../../services/edge-agent/README.md)

- **Infrastructure documentation** is located in the [infrastructure](../../infrastructure/) directory

## 🔗 Related Resources

- **Main Project README** (for quick overview): [Project README](./project/project-README.md)
- **CLAUDE.md** (for AI assistants): [../CLAUDE.md](../CLAUDE.md)
- **Testing Infrastructure**: [../tests/README.md](../tests/README.md)

---

**Note**: This documentation is continuously evolving. If you find outdated information or missing content, please create an issue or submit a pull request.

Last updated: October 28, 2025
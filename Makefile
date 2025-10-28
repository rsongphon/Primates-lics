# LICS Project Makefile
# Provides common development tasks and workflows

.PHONY: help install test build clean lint format docker-build docker-up docker-down deploy setup-dev-env setup-mac setup-linux setup-windows setup-ssl ssl-install-ca ssl-clean ssl-verify dev-https dev-stop dev-clean test-comprehensive test-comprehensive-quick test-comprehensive-benchmark test-comprehensive-stress test-comprehensive-parallel test-infrastructure test-infrastructure-quick test-database test-database-benchmark test-database-stress test-messaging test-messaging-benchmark test-messaging-load test-system-integration test-system-integration-parallel test-phase1-manual test-phase1-manual-verbose test-phase1-manual-tc test-phase1-list test-phase2-manual test-phase2-manual-verbose test-phase2-manual-tc test-phase2-list test-phase2-full test-phase2-app test-phase2-auth test-phase2-domain test-phase2-api test-phase2-websocket test-phase2-celery test-phase2-quick test-phase2-smoke generate-test-report test-phase1-full health-check health-check-database health-check-messaging health-check-continuous performance-test performance-baseline test-report test-report-continuous validate-all validate-quick validate-performance validate-stress

# Default target
.DEFAULT_GOAL := help

# Colors for output
YELLOW := \033[0;33m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

# Project configuration
PROJECT_NAME := lics
VERSION := $(shell grep -m1 version package.json 2>/dev/null | awk -F: '{ print $$2 }' | sed 's/[", ]//g' || echo "1.0.0")
DOCKER_REGISTRY := ghcr.io/rsongphon
CURRENT_DIR := $(shell pwd)

## Help
help: ## Display this help screen
	@echo "$(YELLOW)LICS Development Commands$(NC)"
	@echo ""
	@grep -h -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Services:$(NC) frontend, backend, edge-agent"
	@echo "$(YELLOW)Environments:$(NC) dev, staging, prod"

## Installation
install: ## Install all dependencies
	@echo "$(YELLOW)Installing dependencies for all services...$(NC)"
	@$(MAKE) install-frontend
	@$(MAKE) install-backend
	@$(MAKE) install-edge-agent
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

install-frontend: ## Install frontend dependencies
	@echo "$(YELLOW)Installing frontend dependencies...$(NC)"
	cd services/frontend && npm ci

install-backend: ## Install backend dependencies
	@echo "$(YELLOW)Installing backend dependencies...$(NC)"
	cd services/backend && pip install -r requirements.txt -r requirements-dev.txt

install-edge-agent: ## Install edge agent dependencies
	@echo "$(YELLOW)Installing edge agent dependencies...$(NC)"
	cd services/edge-agent && pip install -r requirements.txt -r requirements-dev.txt

## Development
dev: ## Start all services in development mode (Ctrl+C to stop and cleanup)
	@echo "$(YELLOW)Starting development environment...$(NC)"
	@mkdir -p logs
	@echo "$(YELLOW)Logs will be saved to: logs/dev-$(shell date +%Y%m%d-%H%M%S).log$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop and cleanup all services$(NC)"
	@trap 'echo "\n$(YELLOW)Stopping and cleaning up services...$(NC)"; docker-compose -f docker-compose.dev.yml down; echo "$(GREEN)✓ Services stopped and cleaned up$(NC)"; exit 0' INT TERM; \
	docker-compose -f docker-compose.dev.yml up --build 2>&1 | tee logs/dev-$(shell date +%Y%m%d-%H%M%S).log

dev-detached: ## Start all services in detached mode with logs
	@echo "$(YELLOW)Starting development environment in detached mode...$(NC)"
	@mkdir -p logs
	@echo "$(YELLOW)Logs will be saved to: logs/dev-detached-$(shell date +%Y%m%d-%H%M%S).log$(NC)"
	@docker-compose -f docker-compose.dev.yml up --build -d > logs/dev-detached-$(shell date +%Y%m%d-%H%M%S).log 2>&1
	@echo "$(GREEN)✓ Services started in background$(NC)"
	@echo "$(YELLOW)View logs with: docker-compose -f docker-compose.dev.yml logs -f$(NC)"
	@echo "$(YELLOW)Stop with: make dev-stop$(NC)"
	@echo "$(YELLOW)Or check: logs/dev-detached-*.log$(NC)"

dev-stop: ## Stop development environment
	@echo "$(YELLOW)Stopping development environment...$(NC)"
	@docker-compose -f docker-compose.dev.yml down
	@echo "$(GREEN)✓ Development environment stopped$(NC)"

dev-clean: ## Stop and remove all volumes (WARNING: destroys data)
	@echo "$(RED)WARNING: This will remove all development data!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Stopping and cleaning up...$(NC)"; \
		docker-compose -f docker-compose.dev.yml down -v; \
		echo "$(GREEN)✓ Development environment cleaned$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

dev-frontend: ## Start frontend development server
	@echo "$(YELLOW)Starting frontend development server...$(NC)"
	cd services/frontend && npm run dev

dev-backend: ## Start backend development server
	@echo "$(YELLOW)Starting backend development server...$(NC)"
	cd services/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-edge-agent: ## Start edge agent in development mode
	@echo "$(YELLOW)Starting edge agent...$(NC)"
	cd services/edge-agent && python src/main.py --debug

## Testing
test: ## Run all tests
	@echo "$(YELLOW)Running all tests...$(NC)"
	@$(MAKE) test-frontend
	@$(MAKE) test-backend
	@$(MAKE) test-edge-agent
	@echo "$(GREEN)✓ All tests completed$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd tests && npx jest --config jest.config.js

test-backend: ## Run backend tests
	@echo "$(YELLOW)Running backend tests...$(NC)"
	cd tests && pytest -c pytest.ini

test-edge-agent: ## Run edge agent tests
	@echo "$(YELLOW)Running edge agent tests...$(NC)"
	cd services/edge-agent && pytest

test-coverage: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	cd services/frontend && npm run test:coverage
	cd tests && pytest -c pytest.ini --cov=services/backend/app --cov-report=html
	cd services/edge-agent && pytest --cov=src --cov-report=html

test-integration: ## Run integration tests
	@echo "$(YELLOW)Running integration tests...$(NC)"
	cd tests && pytest -c pytest.ini integration/

test-e2e: ## Run end-to-end tests
	@echo "$(YELLOW)Running E2E tests...$(NC)"
	cd services/frontend && npm run test:e2e

## Comprehensive System Testing
test-comprehensive: ## Run comprehensive system validation (all tests)
	@echo "$(YELLOW)Running comprehensive system validation...$(NC)"
	python3 tools/scripts/run-comprehensive-tests.py --suite all --mode standard
	@echo "$(GREEN)✓ Comprehensive testing completed$(NC)"

test-comprehensive-quick: ## Run quick comprehensive validation (essential tests only)
	@echo "$(YELLOW)Running quick comprehensive validation...$(NC)"
	python3 tools/scripts/run-comprehensive-tests.py --suite all --mode quick
	@echo "$(GREEN)✓ Quick comprehensive testing completed$(NC)"

test-comprehensive-benchmark: ## Run comprehensive testing with performance benchmarks
	@echo "$(YELLOW)Running comprehensive testing with benchmarks...$(NC)"
	python3 tools/scripts/run-comprehensive-tests.py --suite all --mode benchmark
	@echo "$(GREEN)✓ Benchmark testing completed$(NC)"

test-comprehensive-stress: ## Run comprehensive stress testing
	@echo "$(YELLOW)Running comprehensive stress testing...$(NC)"
	python3 tools/scripts/run-comprehensive-tests.py --suite all --mode stress
	@echo "$(GREEN)✓ Stress testing completed$(NC)"

test-comprehensive-parallel: ## Run comprehensive tests in parallel
	@echo "$(YELLOW)Running comprehensive tests in parallel...$(NC)"
	python3 tools/scripts/run-comprehensive-tests.py --suite all --mode standard --parallel
	@echo "$(GREEN)✓ Parallel comprehensive testing completed$(NC)"

test-infrastructure: ## Validate Docker infrastructure and services
	@echo "$(YELLOW)Validating infrastructure...$(NC)"
	python3 tools/scripts/validate-infrastructure.py --format text
	@echo "$(GREEN)✓ Infrastructure validation completed$(NC)"

test-infrastructure-quick: ## Quick infrastructure validation
	@echo "$(YELLOW)Running quick infrastructure validation...$(NC)"
	python3 tools/scripts/validate-infrastructure.py --quick --format text
	@echo "$(GREEN)✓ Quick infrastructure validation completed$(NC)"

test-database: ## Test all database services comprehensively
	@echo "$(YELLOW)Testing database services...$(NC)"
	python3 tools/scripts/test-database-suite.py --test all --format text
	@echo "$(GREEN)✓ Database testing completed$(NC)"

test-database-benchmark: ## Benchmark database performance
	@echo "$(YELLOW)Benchmarking database performance...$(NC)"
	python3 tools/scripts/test-database-suite.py --test all --benchmark --format text
	@echo "$(GREEN)✓ Database benchmarking completed$(NC)"

test-database-stress: ## Stress test database services
	@echo "$(YELLOW)Stress testing database services...$(NC)"
	python3 tools/scripts/test-database-suite.py --test all --benchmark --stress --format text
	@echo "$(GREEN)✓ Database stress testing completed$(NC)"

test-messaging: ## Test all messaging services comprehensively
	@echo "$(YELLOW)Testing messaging services...$(NC)"
	python3 tools/scripts/test-messaging-suite.py --test all --format text
	@echo "$(GREEN)✓ Messaging testing completed$(NC)"

test-messaging-benchmark: ## Benchmark messaging performance
	@echo "$(YELLOW)Benchmarking messaging performance...$(NC)"
	python3 tools/scripts/test-messaging-suite.py --test all --benchmark --format text
	@echo "$(GREEN)✓ Messaging benchmarking completed$(NC)"

test-messaging-load: ## Load test messaging services
	@echo "$(YELLOW)Load testing messaging services...$(NC)"
	python3 tools/scripts/test-messaging-suite.py --test all --benchmark --load-test --format text
	@echo "$(GREEN)✓ Messaging load testing completed$(NC)"

test-system-integration: ## Run end-to-end system integration tests
	@echo "$(YELLOW)Running system integration tests...$(NC)"
	python3 tools/scripts/test-system-integration.py --format text
	@echo "$(GREEN)✓ System integration testing completed$(NC)"

test-system-integration-parallel: ## Run system integration tests in parallel
	@echo "$(YELLOW)Running system integration tests in parallel...$(NC)"
	python3 tools/scripts/test-system-integration.py --parallel --format text
	@echo "$(GREEN)✓ Parallel system integration testing completed$(NC)"

## Phase 1 Manual Test Automation
test-phase1-manual: ## Run all Phase 1 manual tests (automated)
	@echo "$(YELLOW)Running automated Phase 1 manual test suite...$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase1-manual-suite.py --test all --format json --output test-results/phase1_manual_$(shell date +%Y%m%d_%H%M%S).json
	@echo "$(GREEN)✓ Phase 1 manual tests completed$(NC)"

test-phase1-manual-verbose: ## Run Phase 1 manual tests with verbose output
	@echo "$(YELLOW)Running automated Phase 1 manual test suite (verbose)...$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase1-manual-suite.py --test all --format text --verbose
	@echo "$(GREEN)✓ Phase 1 manual tests completed$(NC)"

test-phase1-manual-tc: ## Run specific Phase 1 test case (usage: make test-phase1-manual-tc TC=TC-INFRA-001)
	@if [ -z "$(TC)" ]; then \
		echo "$(RED)Please specify test case: make test-phase1-manual-tc TC=TC-INFRA-001$(NC)"; \
		python3 tools/scripts/test-phase1-manual-suite.py --list-tests; \
		exit 1; \
	fi
	@echo "$(YELLOW)Running Phase 1 test case: $(TC)$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase1-manual-suite.py --test $(TC) --format text --verbose
	@echo "$(GREEN)✓ Test case $(TC) completed$(NC)"

test-phase1-list: ## List all available Phase 1 test cases
	@echo "$(YELLOW)Available Phase 1 Test Cases:$(NC)"
	@python3 tools/scripts/test-phase1-manual-suite.py --list-tests

generate-test-report: ## Generate formatted test report from JSON results (usage: make generate-test-report INPUT=results.json)
	@if [ -z "$(INPUT)" ]; then \
		echo "$(RED)Please specify input file: make generate-test-report INPUT=test-results/phase*_manual_*.json$(NC)"; \
		echo "$(YELLOW)Available Phase 1 results:$(NC)"; \
		ls -lt test-results/phase1_manual_*.json 2>/dev/null | head -3 || echo "  No Phase 1 results found"; \
		echo ""; \
		echo "$(YELLOW)Available Phase 2 results:$(NC)"; \
		ls -lt test-results/phase2_manual_*.json 2>/dev/null | head -3 || echo "  No Phase 2 results found"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Generating test report from $(INPUT)...$(NC)"
	@mkdir -p test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	REPORT_BASE="test-results/reports/report_$${TIMESTAMP}"; \
	python3 tools/scripts/generate-test-report.py --input $(INPUT) --format both --output $${REPORT_BASE}.md; \
	echo "$(GREEN)✓ Test report generated$(NC)"; \
	echo "  📝 Markdown: $${REPORT_BASE}.md"; \
	echo "  🌐 HTML:     $${REPORT_BASE}.html"

clean-test-reports: ## Remove all test reports from test-results/reports directory
	@echo "$(YELLOW)Cleaning test reports...$(NC)"
	@if [ -d "test-results/reports" ]; then \
		rm -rf test-results/reports/*; \
		echo "$(GREEN)✓ Test reports cleaned$(NC)"; \
	else \
		echo "$(YELLOW)No reports directory found (test-results/reports)$(NC)"; \
	fi

test-phase1-full: ## Run Phase 1 tests and generate reports (complete workflow)
	@echo "$(YELLOW)Starting complete Phase 1 test workflow...$(NC)"
	@mkdir -p test-results test-results/reports
	@RESULT_FILE="test-results/phase1_manual_$(shell date +%Y%m%d_%H%M%S).json"; \
	REPORT_BASE="test-results/reports/phase1_report_$(shell date +%Y%m%d_%H%M%S)"; \
	echo "$(YELLOW)Step 1/2: Running automated tests...$(NC)"; \
	python3 tools/scripts/test-phase1-manual-suite.py --test all --format json --output $${RESULT_FILE} --verbose || true; \
	echo "$(YELLOW)Step 2/2: Generating reports...$(NC)"; \
	python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
	echo ""; \
	echo "$(GREEN)✓ Complete Phase 1 test workflow finished$(NC)"; \
	echo ""; \
	echo "$(YELLOW)Generated Files:$(NC)"; \
	echo "  JSON Results:  $${RESULT_FILE}"; \
	echo "  Markdown Report: $${REPORT_BASE}.md"; \
	echo "  HTML Report:   $${REPORT_BASE}.html"; \
	echo ""; \
	echo "$(YELLOW)Open HTML report:$(NC)"; \
	echo "  open $${REPORT_BASE}.html"

## Phase 2 Manual Test Automation
test-phase2-manual: ## Run all Phase 2 manual tests (automated - 125 tests)
	@echo "$(YELLOW)Running automated Phase 2 manual test suite (125 tests)...$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase2-manual.py --output test-results/phase2_manual_$(shell date +%Y%m%d_%H%M%S).json
	@echo "$(GREEN)✓ Phase 2 manual tests completed$(NC)"

test-phase2-manual-verbose: ## Run Phase 2 manual tests with verbose output (shows steps)
	@echo "$(YELLOW)Running automated Phase 2 manual test suite (verbose)...$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase2-manual.py --verbose --output test-results/phase2_manual_$(shell date +%Y%m%d_%H%M%S).json
	@echo "$(GREEN)✓ Phase 2 manual tests completed$(NC)"

test-phase2-manual-debug: ## Run Phase 2 manual tests with debug output (shows all HTTP requests/responses)
	@echo "$(YELLOW)Running automated Phase 2 manual test suite (debug mode)...$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase2-manual.py --debug --output test-results/phase2_manual_$(shell date +%Y%m%d_%H%M%S).json
	@echo "$(GREEN)✓ Phase 2 manual tests completed$(NC)"

test-phase2-manual-tc: ## Run specific Phase 2 test case (usage: make test-phase2-manual-tc TC=TC-AUTH-001)
	@if [ -z "$(TC)" ]; then \
		echo "$(RED)Please specify test case: make test-phase2-manual-tc TC=TC-AUTH-001$(NC)"; \
		python3 tools/scripts/test-phase2-manual.py --list; \
		exit 1; \
	fi
	@echo "$(YELLOW)Running Phase 2 test case: $(TC) (verbose)$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase2-manual.py --tc $(TC) --verbose
	@echo "$(GREEN)✓ Test case $(TC) completed$(NC)"

test-phase2-manual-tc-debug: ## Run specific Phase 2 test case with debug output (usage: make test-phase2-manual-tc-debug TC=TC-AUTH-001)
	@if [ -z "$(TC)" ]; then \
		echo "$(RED)Please specify test case: make test-phase2-manual-tc-debug TC=TC-AUTH-001$(NC)"; \
		python3 tools/scripts/test-phase2-manual.py --list; \
		exit 1; \
	fi
	@echo "$(YELLOW)Running Phase 2 test case: $(TC) (debug mode)$(NC)"
	@mkdir -p test-results
	python3 tools/scripts/test-phase2-manual.py --tc $(TC) --debug
	@echo "$(GREEN)✓ Test case $(TC) completed$(NC)"

test-phase2-list: ## List all available Phase 2 test cases (125 total)
	@echo "$(YELLOW)Available Phase 2 Test Cases:$(NC)"
	@python3 tools/scripts/test-phase2-manual.py --list

test-phase2-full: ## Run Phase 2 tests and generate markdown + HTML reports (complete workflow)
	@echo "$(YELLOW)Starting complete Phase 2 test workflow...$(NC)"
	@mkdir -p test-results test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	RESULT_FILE="test-results/phase2_manual_$${TIMESTAMP}.json"; \
	REPORT_BASE="test-results/reports/phase2_report_$${TIMESTAMP}"; \
	echo "$(YELLOW)Step 1/2: Running automated Phase 2 tests (125 tests)...$(NC)"; \
	python3 tools/scripts/test-phase2-manual.py --verbose --output $${RESULT_FILE} || true; \
	echo ""; \
	echo "$(YELLOW)Step 2/2: Generating test reports (Markdown + HTML)...$(NC)"; \
	python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
	echo ""; \
	echo "$(GREEN)================================================================$(NC)"; \
	echo "$(GREEN)✓ Complete Phase 2 test workflow finished successfully$(NC)"; \
	echo "$(GREEN)================================================================$(NC)"; \
	echo ""; \
	echo "$(YELLOW)Generated Files:$(NC)"; \
	echo "  📄 JSON Results:     $${RESULT_FILE}"; \
	echo "  📝 Markdown Report:  $${REPORT_BASE}.md"; \
	echo "  🌐 HTML Report:      $${REPORT_BASE}.html"; \
	echo ""; \
	echo "$(YELLOW)Quick Actions:$(NC)"; \
	echo "  View Markdown: cat $${REPORT_BASE}.md"; \
	echo "  Open HTML:     open $${REPORT_BASE}.html"; \
	echo ""; \
	echo "$(YELLOW)Reports saved to:$(NC) test-results/reports/"

## Phase 2 Category-Specific Tests
test-phase2-app: ## Run Phase 2 Application Foundation tests (5 tests) with reports
	@echo "$(YELLOW)Running Application Foundation tests (5 tests)...$(NC)"
	@mkdir -p test-results test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	RESULT_FILE="test-results/phase2_app_$${TIMESTAMP}.json"; \
	REPORT_BASE="test-results/reports/phase2_app_report_$${TIMESTAMP}"; \
	echo "$(YELLOW)Step 1/2: Running tests...$(NC)"; \
	python3 tools/scripts/test-phase2-manual.py --category app --verbose --output $${RESULT_FILE} || true; \
	echo ""; \
	echo "$(YELLOW)Step 2/2: Generating test reports...$(NC)"; \
	python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
	echo ""; \
	echo "$(GREEN)✓ Application Foundation tests completed$(NC)"; \
	echo ""; \
	echo "$(YELLOW)Generated Files:$(NC)"; \
	echo "  📄 JSON:     $${RESULT_FILE}"; \
	echo "  📝 Markdown: $${REPORT_BASE}.md"; \
	echo "  🌐 HTML:     $${REPORT_BASE}.html"

test-phase2-auth: ## Run Phase 2 Authentication tests (20 tests) with reports
	@echo "$(YELLOW)Running Authentication & Authorization tests (20 tests)...$(NC)"
	@mkdir -p test-results test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	RESULT_FILE="test-results/phase2_auth_$${TIMESTAMP}.json"; \
	REPORT_BASE="test-results/reports/phase2_auth_report_$${TIMESTAMP}"; \
	echo "$(YELLOW)Step 1/2: Running tests...$(NC)"; \
	python3 tools/scripts/test-phase2-manual.py --category auth --verbose --output $${RESULT_FILE} || true; \
	echo ""; \
	echo "$(YELLOW)Step 2/2: Generating test reports...$(NC)"; \
	python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
	echo ""; \
	echo "$(GREEN)✓ Authentication tests completed$(NC)"; \
	echo ""; \
	echo "$(YELLOW)Generated Files:$(NC)"; \
	echo "  📄 JSON:     $${RESULT_FILE}"; \
	echo "  📝 Markdown: $${REPORT_BASE}.md"; \
	echo "  🌐 HTML:     $${REPORT_BASE}.html"

test-phase2-domain: ## Run Phase 2 Domain Model tests (15 tests) with reports
	@echo "$(YELLOW)Running Core Domain Models tests (15 tests)...$(NC)"
	@mkdir -p test-results test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	RESULT_FILE="test-results/phase2_domain_$${TIMESTAMP}.json"; \
	REPORT_BASE="test-results/reports/phase2_domain_report_$${TIMESTAMP}"; \
	echo "$(YELLOW)Step 1/2: Running tests...$(NC)"; \
	python3 tools/scripts/test-phase2-manual.py --category domain --verbose --output $${RESULT_FILE} || true; \
	echo ""; \
	echo "$(YELLOW)Step 2/2: Generating test reports...$(NC)"; \
	python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
	echo ""; \
	echo "$(GREEN)✓ Domain Model tests completed$(NC)"; \
	echo ""; \
	echo "$(YELLOW)Generated Files:$(NC)"; \
	echo "  📄 JSON:     $${RESULT_FILE}"; \
	echo "  📝 Markdown: $${REPORT_BASE}.md"; \
	echo "  🌐 HTML:     $${REPORT_BASE}.html"

test-phase2-api: ## Run Phase 2 RESTful API tests (40 tests) with reports
	@echo "$(YELLOW)Running RESTful API Implementation tests (40 tests)...$(NC)"
	@mkdir -p test-results test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	RESULT_FILE="test-results/phase2_api_$${TIMESTAMP}.json"; \
	REPORT_BASE="test-results/reports/phase2_api_report_$${TIMESTAMP}"; \
	echo "$(YELLOW)Step 1/2: Running tests...$(NC)"; \
	python3 tools/scripts/test-phase2-manual.py --category api --verbose --output $${RESULT_FILE} && \
	( \
		echo ""; \
		echo "$(YELLOW)Step 2/2: Generating test reports...$(NC)"; \
		python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
		echo ""; \
		echo "$(GREEN)✓ RESTful API tests completed$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Generated Files:$(NC)"; \
		echo "  📄 JSON:     $${RESULT_FILE}"; \
		echo "  📝 Markdown: $${REPORT_BASE}.md"; \
		echo "  🌐 HTML:     $${REPORT_BASE}.html" \
	) || ( \
		echo "$(RED)❌ Tests failed or backend not accessible$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Note: Make sure the backend is running with: make dev-detached$(NC)"; \
		echo "$(YELLOW)Or check backend status with: docker-compose -f docker-compose.dev.yml ps backend-dev$(NC)" \
	)

test-phase2-websocket: ## Run Phase 2 WebSocket tests (20 tests) with reports
	@echo "$(YELLOW)Running WebSocket and Real-time Features tests (20 tests)...$(NC)"
	@mkdir -p test-results test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	RESULT_FILE="test-results/phase2_websocket_$${TIMESTAMP}.json"; \
	REPORT_BASE="test-results/reports/phase2_websocket_report_$${TIMESTAMP}"; \
	echo "$(YELLOW)Step 1/2: Running tests...$(NC)"; \
	python3 tools/scripts/test-phase2-manual.py --category websocket --verbose --output $${RESULT_FILE} && \
	( \
		echo ""; \
		echo "$(YELLOW)Step 2/2: Generating test reports...$(NC)"; \
		python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
		echo ""; \
		echo "$(GREEN)✓ WebSocket tests completed$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Generated Files:$(NC)"; \
		echo "  📄 JSON:     $${RESULT_FILE}"; \
		echo "  📝 Markdown: $${REPORT_BASE}.md"; \
		echo "  🌐 HTML:     $${REPORT_BASE}.html" \
	) || ( \
		echo "$(RED)❌ Tests failed or backend not accessible$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Note: Make sure the backend is running with: make dev-detached$(NC)"; \
		echo "$(YELLOW)Or check backend status with: docker-compose -f docker-compose.dev.yml ps backend-dev$(NC)" \
	)

test-phase2-celery: ## Run Phase 2 Background Tasks tests (25 tests) with reports
	@echo "$(YELLOW)Running Background Tasks and Scheduling tests (25 tests)...$(NC)"
	@mkdir -p test-results test-results/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	RESULT_FILE="test-results/phase2_celery_$${TIMESTAMP}.json"; \
	REPORT_BASE="test-results/reports/phase2_celery_report_$${TIMESTAMP}"; \
	echo "$(YELLOW)Step 1/2: Running tests...$(NC)"; \
	python3 tools/scripts/test-phase2-manual.py --category celery --verbose --output $${RESULT_FILE} && \
	( \
		echo ""; \
		echo "$(YELLOW)Step 2/2: Generating test reports...$(NC)"; \
		python3 tools/scripts/generate-test-report.py --input $${RESULT_FILE} --format both --output $${REPORT_BASE}.md; \
		echo ""; \
		echo "$(GREEN)✓ Background Tasks tests completed$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Generated Files:$(NC)"; \
		echo "  📄 JSON:     $${RESULT_FILE}"; \
		echo "  📝 Markdown: $${REPORT_BASE}.md"; \
		echo "  🌐 HTML:     $${REPORT_BASE}.html" \
	) || ( \
		echo "$(RED)❌ Tests failed or backend not accessible$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Note: Make sure the backend is running with: make dev-detached$(NC)"; \
		echo "$(YELLOW)Or check backend status with: docker-compose -f docker-compose.dev.yml ps backend-dev$(NC)" \
	)

## Phase 2 Quick Validation
test-phase2-quick: ## Run quick Phase 2 validation (core tests only) with verbose output
	@echo "$(YELLOW)Running quick Phase 2 validation (verbose)...$(NC)"
	@mkdir -p test-results
	@echo "Testing Application Foundation..."
	@python3 tools/scripts/test-phase2-manual.py --tc TC-APP-001 --verbose || true
	@python3 tools/scripts/test-phase2-manual.py --tc TC-APP-002 --verbose || true
	@echo "Testing Authentication..."
	@python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --verbose || true
	@python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-002 --verbose || true
	@echo "Testing API..."
	@python3 tools/scripts/test-phase2-manual.py --tc TC-API-001 --verbose || true
	@python3 tools/scripts/test-phase2-manual.py --tc TC-API-004 --verbose || true
	@echo "Testing WebSocket..."
	@python3 tools/scripts/test-phase2-manual.py --tc TC-WS-001 --verbose || true
	@echo "Testing Celery..."
	@python3 tools/scripts/test-phase2-manual.py --tc TC-CELERY-001 --verbose || true
	@echo "$(GREEN)✓ Quick Phase 2 validation completed$(NC)"

test-phase2-smoke: ## Run Phase 2 smoke tests (fastest validation) with verbose output
	@echo "$(YELLOW)Running Phase 2 smoke tests (verbose)...$(NC)"
	@mkdir -p test-results
	@python3 tools/scripts/test-phase2-manual.py --tc TC-APP-001 --verbose || true
	@python3 tools/scripts/test-phase2-manual.py --tc TC-AUTH-001 --verbose || true
	@echo "$(GREEN)✓ Phase 2 smoke tests completed$(NC)"

## Health Monitoring
health-check: ## Check overall system health
	@echo "$(YELLOW)Checking system health...$(NC)"
	python3 infrastructure/monitoring/database/health_check.py --format text
	@echo ""
	python3 infrastructure/monitoring/messaging-health-check.py --format json
	@echo "$(GREEN)✓ Health check completed$(NC)"

health-check-database: ## Check database services health
	@echo "$(YELLOW)Checking database health...$(NC)"
	python3 infrastructure/monitoring/database/health_check.py --format text
	@echo "$(GREEN)✓ Database health check completed$(NC)"

health-check-messaging: ## Check messaging services health
	@echo "$(YELLOW)Checking messaging health...$(NC)"
	python3 infrastructure/monitoring/messaging-health-check.py --format json
	@echo "$(GREEN)✓ Messaging health check completed$(NC)"

health-check-continuous: ## Run continuous health monitoring
	@echo "$(YELLOW)Starting continuous health monitoring...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	python3 infrastructure/monitoring/messaging-health-check.py --continuous --interval 60

## Performance Testing
performance-test: ## Run performance tests with K6
	@echo "$(YELLOW)Running performance tests...$(NC)"
	k6 run tests/performance/api-load-test.js
	@echo "$(GREEN)✓ Performance testing completed$(NC)"

performance-baseline: ## Establish performance baselines
	@echo "$(YELLOW)Establishing performance baselines...$(NC)"
	@$(MAKE) test-comprehensive-benchmark
	@echo "$(GREEN)✓ Performance baselines established$(NC)"

## Test Reporting
test-report: ## Generate comprehensive test report with HTML dashboard
	@echo "$(YELLOW)Generating comprehensive test report...$(NC)"
	python3 tools/scripts/run-comprehensive-tests.py --suite all --mode standard --format html
	@echo "$(GREEN)✓ Test report generated$(NC)"

test-report-continuous: ## Run continuous testing with reports
	@echo "$(YELLOW)Starting continuous testing with reporting...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	python3 tools/scripts/run-comprehensive-tests.py --suite all --mode standard --continuous --interval 3600

## Validation Commands (Combined Testing)
validate-all: ## Complete system validation (infrastructure + database + messaging + integration)
	@echo "$(YELLOW)Starting complete system validation...$(NC)"
	@$(MAKE) test-comprehensive
	@echo "$(GREEN)✓ Complete system validation finished$(NC)"

validate-quick: ## Quick system validation (essential checks only)
	@echo "$(YELLOW)Starting quick system validation...$(NC)"
	@$(MAKE) test-comprehensive-quick
	@echo "$(GREEN)✓ Quick system validation finished$(NC)"

validate-performance: ## Complete performance validation
	@echo "$(YELLOW)Starting performance validation...$(NC)"
	@$(MAKE) test-comprehensive-benchmark
	@$(MAKE) performance-test
	@echo "$(GREEN)✓ Performance validation finished$(NC)"

validate-stress: ## Complete stress testing validation
	@echo "$(YELLOW)Starting stress testing validation...$(NC)"
	@$(MAKE) test-comprehensive-stress
	@echo "$(GREEN)✓ Stress testing validation finished$(NC)"

## Code Quality
lint: ## Run linting for all services
	@echo "$(YELLOW)Running linting...$(NC)"
	@$(MAKE) lint-frontend
	@$(MAKE) lint-backend
	@$(MAKE) lint-edge-agent
	@echo "$(GREEN)✓ Linting completed$(NC)"

lint-frontend: ## Run frontend linting
	cd services/frontend && npm run lint

lint-backend: ## Run backend linting
	cd services/backend && ruff check . && black --check .

lint-edge-agent: ## Run edge agent linting
	cd services/edge-agent && ruff check . && black --check .

format: ## Format code for all services
	@echo "$(YELLOW)Formatting code...$(NC)"
	@$(MAKE) format-frontend
	@$(MAKE) format-backend
	@$(MAKE) format-edge-agent
	@echo "$(GREEN)✓ Code formatting completed$(NC)"

format-frontend: ## Format frontend code
	cd services/frontend && npm run format

format-backend: ## Format backend code
	cd services/backend && black . && ruff --fix .

format-edge-agent: ## Format edge agent code
	cd services/edge-agent && black . && ruff --fix .

typecheck: ## Run type checking
	@echo "$(YELLOW)Running type checks...$(NC)"
	cd services/frontend && npm run type-check
	cd services/backend && mypy .
	cd services/edge-agent && mypy .

## Building
build: ## Build all services
	@echo "$(YELLOW)Building all services...$(NC)"
	@$(MAKE) build-frontend
	@$(MAKE) build-backend
	@$(MAKE) build-edge-agent
	@echo "$(GREEN)✓ All services built$(NC)"

build-frontend: ## Build frontend for production
	cd services/frontend && npm run build

build-backend: ## Build backend package
	cd services/backend && python -m build

build-edge-agent: ## Build edge agent package
	cd services/edge-agent && python -m build

## Docker
docker-build: ## Build all Docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-build-frontend: ## Build frontend Docker image
	docker build -t $(DOCKER_REGISTRY)/lics-frontend:$(VERSION) services/frontend

docker-build-backend: ## Build backend Docker image
	docker build -t $(DOCKER_REGISTRY)/lics-backend:$(VERSION) services/backend

docker-build-edge-agent: ## Build edge agent Docker image
	docker build -t $(DOCKER_REGISTRY)/lics-edge-agent:$(VERSION) services/edge-agent

docker-up: ## Start all services with Docker Compose
	@echo "$(YELLOW)Starting services with Docker Compose...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"

docker-down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-clean: ## Clean Docker resources
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	docker system prune -f
	docker volume prune -f

## Database
db-migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	cd services/backend && alembic upgrade head

db-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	cd services/backend && alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys data)
	@echo "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd services/backend && alembic downgrade base && alembic upgrade head; \
	fi

db-seed: ## Seed database with test data
	@echo "$(YELLOW)Seeding database...$(NC)"
	cd services/backend && python scripts/seed_data.py

## Infrastructure
infra-plan: ## Plan infrastructure changes
	@echo "$(YELLOW)Planning infrastructure changes...$(NC)"
	cd infrastructure/terraform/environments/dev && terraform plan

infra-apply: ## Apply infrastructure changes
	@echo "$(YELLOW)Applying infrastructure changes...$(NC)"
	cd infrastructure/terraform/environments/dev && terraform apply

infra-destroy: ## Destroy infrastructure (WARNING: destroys resources)
	@echo "$(RED)WARNING: This will destroy infrastructure!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd infrastructure/terraform/environments/dev && terraform destroy; \
	fi

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(YELLOW)Deploying to Kubernetes...$(NC)"
	kubectl apply -k infrastructure/kubernetes/overlays/dev/

k8s-status: ## Show Kubernetes deployment status
	kubectl get pods,svc,ingress -n lics-dev

## Security
security-scan: ## Run security scans
	@echo "$(YELLOW)Running security scans...$(NC)"
	# Frontend security scan
	cd services/frontend && npm audit --audit-level=moderate
	# Backend security scan
	cd services/backend && safety check
	# Infrastructure security scan
	cd infrastructure && checkov -d terraform/

secrets-encrypt: ## Encrypt secrets (requires sops)
	@echo "$(YELLOW)Encrypting secrets...$(NC)"
	find . -name "secrets*.yaml" -not -path "./.git/*" -exec sops -e -i {} \;

secrets-decrypt: ## Decrypt secrets (requires sops)
	@echo "$(YELLOW)Decrypting secrets...$(NC)"
	find . -name "secrets*.yaml" -not -path "./.git/*" -exec sops -d -i {} \;

## Maintenance
clean: ## Clean build artifacts and dependencies
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	# Frontend
	cd services/frontend && rm -rf .next node_modules
	# Backend
	cd services/backend && rm -rf build dist *.egg-info __pycache__ .pytest_cache
	# Edge Agent
	cd services/edge-agent && rm -rf build dist *.egg-info __pycache__ .pytest_cache
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

update-deps: ## Update all dependencies
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	cd services/frontend && npm update
	cd services/backend && pip-tools compile --upgrade requirements.in
	cd services/edge-agent && pip-tools compile --upgrade requirements.in

git-hooks-install: ## Install Git hooks
	@echo "$(YELLOW)Installing Git hooks...$(NC)"
	./tools/scripts/setup-git-hooks.sh

git-hooks-verify: ## Verify Git hooks installation
	./tools/scripts/setup-git-hooks.sh --verify

## Development Environment Setup
setup-dev-env: ## Run OS-specific development environment setup
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "$(YELLOW)Running macOS setup...$(NC)"; \
		./tools/scripts/setup-mac.sh; \
	elif [ "$$(uname)" = "Linux" ]; then \
		echo "$(YELLOW)Running Linux setup...$(NC)"; \
		./tools/scripts/setup-linux.sh; \
	elif [ "$$(uname -o 2>/dev/null)" = "Cygwin" ] || [ "$$(uname -o 2>/dev/null)" = "Msys" ]; then \
		echo "$(YELLOW)Running Windows setup...$(NC)"; \
		powershell.exe -ExecutionPolicy Bypass -File tools/scripts/setup-windows.ps1; \
	else \
		echo "$(RED)Unsupported operating system: $$(uname)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Development environment setup completed$(NC)"

setup-mac: ## Run macOS-specific setup
	@echo "$(YELLOW)Running macOS setup...$(NC)"
	./tools/scripts/setup-mac.sh

setup-linux: ## Run Linux-specific setup
	@echo "$(YELLOW)Running Linux setup...$(NC)"
	./tools/scripts/setup-linux.sh

setup-windows: ## Run Windows-specific setup
	@echo "$(YELLOW)Running Windows setup...$(NC)"
	powershell.exe -ExecutionPolicy Bypass -File tools/scripts/setup-windows.ps1

## SSL Certificate Management
setup-ssl: ## Generate SSL certificates for local development
	@echo "$(YELLOW)Setting up SSL certificates...$(NC)"
	./tools/scripts/setup-ssl.sh
	@echo "$(GREEN)✓ SSL certificates generated$(NC)"

ssl-install-ca: ## Install mkcert Certificate Authority
	@echo "$(YELLOW)Installing mkcert Certificate Authority...$(NC)"
	@if command -v mkcert >/dev/null 2>&1; then \
		mkcert -install; \
		echo "$(GREEN)✓ mkcert CA installed$(NC)"; \
	else \
		echo "$(RED)mkcert is not installed. Run 'make setup-dev-env' first$(NC)"; \
		exit 1; \
	fi

ssl-clean: ## Remove generated SSL certificates
	@echo "$(YELLOW)Cleaning SSL certificates...$(NC)"
	rm -rf infrastructure/nginx/ssl/*.pem infrastructure/nginx/ssl/*.crt infrastructure/nginx/ssl/*.key
	rm -rf infrastructure/certificates/*/
	@echo "$(GREEN)✓ SSL certificates cleaned$(NC)"

ssl-verify: ## Verify SSL certificate configuration
	@echo "$(YELLOW)Verifying SSL certificates...$(NC)"
	@if [ -f "infrastructure/nginx/ssl/localhost.pem" ]; then \
		echo "$(GREEN)✓ SSL certificates found$(NC)"; \
		openssl x509 -in infrastructure/nginx/ssl/localhost.pem -text -noout | grep -A1 "Subject Alternative Name" || true; \
	else \
		echo "$(RED)✗ SSL certificates not found. Run 'make setup-ssl' first$(NC)"; \
		exit 1; \
	fi

## HTTPS Development
dev-https: ## Start development environment with HTTPS
	@echo "$(YELLOW)Starting HTTPS development environment...$(NC)"
	@$(MAKE) ssl-verify
	COMPOSE_FILE=docker-compose.dev.yml:docker-compose.ssl.yml docker-compose up --build

## Documentation
docs-build: ## Build documentation
	@echo "$(YELLOW)Building documentation...$(NC)"
	# Add documentation build commands here

docs-serve: ## Serve documentation locally
	@echo "$(YELLOW)Serving documentation...$(NC)"
	# Add documentation serve commands here

## Release
version-bump: ## Bump version (usage: make version-bump VERSION=1.2.3)
	@if [ -z "$(VERSION)" ]; then echo "$(RED)Please provide VERSION: make version-bump VERSION=1.2.3$(NC)"; exit 1; fi
	@echo "$(YELLOW)Bumping version to $(VERSION)...$(NC)"
	# Update version in relevant files
	sed -i.bak 's/"version": ".*"/"version": "$(VERSION)"/' package.json || true
	rm -f package.json.bak

release: ## Create a release
	@echo "$(YELLOW)Creating release...$(NC)"
	@echo "$(RED)Please use GitHub releases or your CI/CD pipeline$(NC)"

## Health Checks
health-check-services: ## Check service health
	@echo "$(YELLOW)Checking service health...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)Backend unhealthy$(NC)"
	@curl -f http://localhost:3000 || echo "$(RED)Frontend unhealthy$(NC)"

status: ## Show project status
	@echo "$(YELLOW)LICS Project Status$(NC)"
	@echo "Version: $(VERSION)"
	@echo "Services:"
	@docker-compose ps 2>/dev/null || echo "  Docker Compose not running"
	@echo "Git status:"
	@git status --porcelain | head -5
## Containerized Development
.PHONY: container-help container-shell container-dev container-stop container-logs container-clean

container-help: ## Show containerized development help
	@echo "$(YELLOW)Containerized Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  1. Open in VS Code and select 'Reopen in Container' OR"
	@echo "  2. Run: make container-dev"
	@echo ""
	@echo "$(GREEN)Available Commands:$(NC)"
	@./tools/dev-cli.sh help

container-shell: ## Open bash shell in dev container
	@./tools/dev-cli.sh shell

container-dev: ## Start all services in containers
	@echo "$(YELLOW)Starting containerized development environment...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo ""
	@echo "$(YELLOW)Application:$(NC)"
	@echo "  Frontend:      http://localhost:3000"
	@echo "  Backend API:   http://localhost:8000/docs"
	@echo "  WebSocket:     ws://localhost:8001"
	@echo ""
	@echo "$(YELLOW)Monitoring Stack:$(NC)"
	@echo "  Grafana:       http://localhost:3001 (admin/admin123)"
	@echo "  Prometheus:    http://localhost:9090"
	@echo "  Alertmanager:  http://localhost:9093"
	@echo "  Loki:          http://localhost:3100"
	@echo "  Jaeger:        http://localhost:16686"
	@echo ""
	@echo "$(YELLOW)Development Tools:$(NC)"
	@echo "  PgAdmin:       http://localhost:5050"
	@echo "  Redis Cmd:     http://localhost:8081"
	@echo "  MinIO Console: http://localhost:9011"
	@echo "  MailHog:       http://localhost:8025"
	@echo ""
	@echo "Get a shell: make container-shell"
	@echo "View logs:   make container-logs"

container-stop: ## Stop all containers
	@echo "$(YELLOW)Stopping containers...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

container-logs: ## View container logs
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

container-clean: ## Stop containers and remove volumes
	@echo "$(RED)WARNING: This will remove all container data!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v; \
		echo "$(GREEN)✓ Containers and volumes removed$(NC)"; \
	fi

container-rebuild: ## Rebuild all containers
	@echo "$(YELLOW)Rebuilding containers...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
	@echo "$(GREEN)✓ Rebuild complete$(NC)"

# Container-based development commands using dev-cli.sh
container-npm: ## Run npm command (usage: make container-npm ARGS="install axios")
	@./tools/dev-cli.sh npm $(ARGS)

container-pip: ## Run pip command (usage: make container-pip ARGS="install requests")
	@./tools/dev-cli.sh pip $(ARGS)

container-pytest: ## Run pytest in container
	@./tools/dev-cli.sh pytest $(ARGS)

container-alembic: ## Run alembic in container (usage: make container-alembic ARGS="upgrade head")
	@./tools/dev-cli.sh alembic $(ARGS)

container-test: ## Run all tests in containers
	@./tools/dev-cli.sh test

container-format: ## Format code in container
	@./tools/dev-cli.sh format

container-lint: ## Lint code in container
	@./tools/dev-cli.sh lint


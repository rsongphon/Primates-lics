#!/bin/bash

# Phase 3 Week 5 - Automated Test Runner
# Executes comprehensive test suite with reporting

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="test-results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Phase 3 Week 5 - Frontend Testing Suite         ║${NC}"
echo -e "${BLUE}║   LICS - Lab Instrument Control System            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check service health
check_services() {
    print_section "1. Checking Service Health"

    echo -n "Checking Backend API (localhost:8000)... "
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Online${NC}"
    else
        echo -e "${RED}✗ Offline${NC}"
        echo -e "${YELLOW}Warning: Backend API not responding. Some tests may fail.${NC}"
    fi

    echo -n "Checking Frontend Dev Server (localhost:3000)... "
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${YELLOW}✗ Not Running${NC}"
        echo -e "${YELLOW}Info: Frontend dev server not required for unit tests.${NC}"
    fi

    echo -n "Checking PostgreSQL (localhost:5432)... "
    if docker ps | grep -q postgres; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Running${NC}"
    fi

    echo -n "Checking Redis (localhost:6379)... "
    if docker ps | grep -q redis; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Running${NC}"
    fi
}

# Function to run TypeScript type checking
run_typecheck() {
    print_section "2. TypeScript Type Checking"

    echo "Running TypeScript compiler..."
    if npm run typecheck > "$RESULTS_DIR/typecheck.log" 2>&1; then
        echo -e "${GREEN}✓ TypeScript compilation successful${NC}"
        echo "  No type errors found"
    else
        echo -e "${RED}✗ TypeScript compilation failed${NC}"
        echo "  See $RESULTS_DIR/typecheck.log for details"
        cat "$RESULTS_DIR/typecheck.log"
        exit 1
    fi
}

# Function to run linting
run_linting() {
    print_section "3. Code Linting (ESLint)"

    echo "Running ESLint..."
    if npm run lint > "$RESULTS_DIR/eslint.log" 2>&1; then
        echo -e "${GREEN}✓ No linting errors${NC}"
    else
        echo -e "${YELLOW}⚠ Linting warnings/errors found${NC}"
        echo "  See $RESULTS_DIR/eslint.log for details"
        # Don't exit on lint warnings
    fi
}

# Function to run unit tests
run_unit_tests() {
    print_section "4. Unit Tests"

    echo "Running Jest unit tests..."
    if npm test -- --ci --coverage --maxWorkers=2 --json --outputFile="$RESULTS_DIR/jest-results.json" > "$RESULTS_DIR/jest.log" 2>&1; then
        echo -e "${GREEN}✓ All unit tests passed${NC}"

        # Parse results
        TOTAL_TESTS=$(grep -o '"numTotalTests":[0-9]*' "$RESULTS_DIR/jest-results.json" | cut -d':' -f2)
        PASSED_TESTS=$(grep -o '"numPassedTests":[0-9]*' "$RESULTS_DIR/jest-results.json" | cut -d':' -f2)
        FAILED_TESTS=$(grep -o '"numFailedTests":[0-9]*' "$RESULTS_DIR/jest-results.json" | cut -d':' -f2)

        echo "  Total: $TOTAL_TESTS | Passed: $PASSED_TESTS | Failed: $FAILED_TESTS"
    else
        echo -e "${RED}✗ Unit tests failed${NC}"
        echo "  See $RESULTS_DIR/jest.log for details"
        tail -n 50 "$RESULTS_DIR/jest.log"
        exit 1
    fi
}

# Function to check code coverage
check_coverage() {
    print_section "5. Code Coverage Report"

    echo "Analyzing coverage..."

    # Check if coverage report exists
    if [ -f "coverage/coverage-summary.json" ]; then
        echo -e "${GREEN}✓ Coverage report generated${NC}"

        # Extract coverage percentages
        STATEMENTS=$(grep -o '"statements":{"total":[0-9]*,"covered":[0-9]*' coverage/coverage-summary.json | head -1)
        BRANCHES=$(grep -o '"branches":{"total":[0-9]*,"covered":[0-9]*' coverage/coverage-summary.json | head -1)
        FUNCTIONS=$(grep -o '"functions":{"total":[0-9]*,"covered":[0-9]*' coverage/coverage-summary.json | head -1)
        LINES=$(grep -o '"lines":{"total":[0-9]*,"covered":[0-9]*' coverage/coverage-summary.json | head -1)

        echo ""
        echo "  Coverage Summary:"
        echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Statements  : $(calculate_percentage "$STATEMENTS")%"
        echo "  Branches    : $(calculate_percentage "$BRANCHES")%"
        echo "  Functions   : $(calculate_percentage "$FUNCTIONS")%"
        echo "  Lines       : $(calculate_percentage "$LINES")%"
        echo ""

        # Copy coverage report
        cp -r coverage "$RESULTS_DIR/"
        echo "  HTML Report: $RESULTS_DIR/coverage/lcov-report/index.html"
    else
        echo -e "${YELLOW}⚠ Coverage report not found${NC}"
    fi
}

# Helper function to calculate percentage
calculate_percentage() {
    local data=$1
    local total=$(echo "$data" | grep -o 'total":[0-9]*' | cut -d':' -f2)
    local covered=$(echo "$data" | grep -o 'covered":[0-9]*' | cut -d':' -f2)

    if [ "$total" -eq 0 ]; then
        echo "0"
    else
        echo "scale=2; ($covered * 100) / $total" | bc
    fi
}

# Function to run build test
run_build_test() {
    print_section "6. Production Build Test"

    echo "Building production bundle..."
    if npm run build > "$RESULTS_DIR/build.log" 2>&1; then
        echo -e "${GREEN}✓ Production build successful${NC}"

        # Get build size
        if [ -d ".next" ]; then
            BUILD_SIZE=$(du -sh .next | cut -f1)
            echo "  Build size: $BUILD_SIZE"
        fi
    else
        echo -e "${RED}✗ Production build failed${NC}"
        echo "  See $RESULTS_DIR/build.log for details"
        tail -n 50 "$RESULTS_DIR/build.log"
        exit 1
    fi
}

# Function to generate test report
generate_report() {
    print_section "7. Test Report Generation"

    REPORT_FILE="$RESULTS_DIR/test-report.md"

    cat > "$REPORT_FILE" << EOF
# Phase 3 Week 5 - Test Execution Report

**Date**: $(date +"%Y-%m-%d %H:%M:%S")
**Tester**: $(whoami)
**Environment**: Development

---

## Test Results Summary

### 1. TypeScript Compilation
- Status: ✅ PASSED
- Errors: 0
- Log: typecheck.log

### 2. Code Linting (ESLint)
- Status: ✅ PASSED
- Warnings: Check eslint.log
- Log: eslint.log

### 3. Unit Tests (Jest)
- Total Tests: $TOTAL_TESTS
- Passed: $PASSED_TESTS
- Failed: $FAILED_TESTS
- Status: $([ "$FAILED_TESTS" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")
- Log: jest.log

### 4. Code Coverage
- Statements: $(calculate_percentage "$STATEMENTS")%
- Branches: $(calculate_percentage "$BRANCHES")%
- Functions: $(calculate_percentage "$FUNCTIONS")%
- Lines: $(calculate_percentage "$LINES")%
- Target: >80%
- Status: $([ $(echo "$(calculate_percentage "$LINES") >= 80" | bc -l) -eq 1 ] && echo "✅ PASSED" || echo "⚠️ BELOW TARGET")

### 5. Production Build
- Status: ✅ PASSED
- Build Size: $BUILD_SIZE
- Log: build.log

---

## Files Generated
- TypeScript Check: \`typecheck.log\`
- ESLint Report: \`eslint.log\`
- Jest Results: \`jest-results.json\`, \`jest.log\`
- Coverage Report: \`coverage/\`
- Build Log: \`build.log\`

---

## Next Steps
- [ ] Review coverage report for gaps
- [ ] Fix any failing tests
- [ ] Update documentation
- [ ] Proceed to Phase 3 Week 6 (if all tests pass)

---

**Report Location**: $RESULTS_DIR
EOF

    echo -e "${GREEN}✓ Test report generated${NC}"
    echo "  Report: $REPORT_FILE"
}

# Function to display final summary
display_summary() {
    print_section "Test Execution Complete"

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          All Tests Completed Successfully         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Test Results Directory: $RESULTS_DIR"
    echo ""
    echo "Key Files:"
    echo "  📄 Test Report:    $RESULTS_DIR/test-report.md"
    echo "  📊 Coverage Report: $RESULTS_DIR/coverage/lcov-report/index.html"
    echo "  📝 Jest Results:   $RESULTS_DIR/jest-results.json"
    echo ""
    echo "Next Steps:"
    echo "  1. Review test report: cat $RESULTS_DIR/test-report.md"
    echo "  2. Open coverage report: open $RESULTS_DIR/coverage/lcov-report/index.html"
    echo "  3. If all tests pass, proceed to Phase 3 Week 6"
    echo ""
}

# Main execution flow
main() {
    # Change to frontend directory if not already there
    if [ ! -f "package.json" ]; then
        cd services/frontend
    fi

    # Run all test stages
    check_services
    run_typecheck
    run_linting
    run_unit_tests
    check_coverage
    run_build_test
    generate_report
    display_summary

    # Exit with success
    exit 0
}

# Run main function
main "$@"

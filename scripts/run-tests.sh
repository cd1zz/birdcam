#!/bin/bash
# Run all BirdCam tests with colored output and summary

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counter for test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test file
run_test() {
    local test_file=$1
    local test_name=$2
    
    echo -e "\n${BLUE}Running ${test_name}...${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN}✓ ${test_name} passed${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ ${test_name} failed${NC}"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
}

# Main test execution
echo -e "${YELLOW}BirdCam Test Suite${NC}"
echo "=================================="
echo "Running all unit tests..."

# Check if we're in the project root
if [ ! -f "requirements.processor.txt" ] && [ ! -f "requirements.capture.txt" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo "Installing test dependencies..."
    pip install -r tests/requirements.txt
fi

# Run unit tests
echo -e "\n${YELLOW}Unit Tests${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Auth tests
run_test "tests/test_auth_service.py" "Auth Service Tests"
run_test "tests/test_utils_auth.py" "Auth Utils Tests"

# API tests (if they exist)
if [ -d "tests/api" ]; then
    echo -e "\n${YELLOW}API Tests${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    for test_file in tests/api/test_*.py; do
        if [ -f "$test_file" ]; then
            test_name=$(basename "$test_file" .py | sed 's/test_//' | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
            run_test "$test_file" "$test_name Tests"
        fi
    done
fi

# UI tests (if they exist)
if [ -d "tests/ui" ]; then
    echo -e "\n${YELLOW}UI Tests${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    for test_file in tests/ui/test_*.py; do
        if [ -f "$test_file" ]; then
            test_name=$(basename "$test_file" .py | sed 's/test_//' | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
            run_test "$test_file" "$test_name Tests"
        fi
    done
fi

# Summary
echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Test Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Total test suites run: ${TOTAL_TESTS}"
echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"

# Generate coverage report if all tests passed
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${YELLOW}Generating coverage report...${NC}"
    pytest --cov=. --cov-report=html --cov-report=term-missing \
           --cov-config=.coveragerc \
           tests/test_*.py \
           2>/dev/null || echo "Coverage report generation skipped (pytest-cov not installed)"
fi

# Exit with appropriate code
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "\n${RED}Some tests failed. Please fix the issues before proceeding.${NC}"
    exit 1
else
    echo -e "\n${GREEN}All tests passed! 🎉${NC}"
    exit 0
fi
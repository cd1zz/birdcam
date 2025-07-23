#!/bin/bash

set -e

echo "[TEST] Starting comprehensive test suite..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
BACKEND_RESULT=0
FRONTEND_RESULT=0
E2E_RESULT=0
API_VALIDATION_RESULT=0
INTEGRATION_RESULT=0

# Backend Python tests
echo -e "\n${YELLOW}[TEST] Running backend Python tests...${NC}"

# Check if .venv exists and activate it
if [ -d ".venv" ]; then
    echo "[TEST] Activating Python virtual environment..."
    source .venv/bin/activate
fi

# Add current directory to PYTHONPATH so modules can be imported
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}."

# Run tests with timeout to prevent stalling, skip unimplemented cross-camera tests
if pytest --cov=. --cov-report=html --cov-report=term --timeout=30 -k "not cross_camera"; then
    echo -e "${GREEN}[TEST] Backend tests passed!${NC}"
else
    echo -e "${RED}[TEST] Backend tests failed!${NC}"
    BACKEND_RESULT=1
fi

# Frontend unit tests
echo -e "\n${YELLOW}[TEST] Running frontend unit tests...${NC}"
cd web-ui
if npm run test -- --run; then
    echo -e "${GREEN}[TEST] Frontend unit tests passed!${NC}"
else
    echo -e "${RED}[TEST] Frontend unit tests failed!${NC}"
    FRONTEND_RESULT=1
fi

# Frontend E2E tests (only if not in CI or if explicitly requested)
if [ "$RUN_E2E" = "true" ] || [ "$CI" != "true" ]; then
    echo -e "\n${YELLOW}[TEST] Running E2E tests...${NC}"
    if npx playwright install --with-deps && npm run test:e2e; then
        echo -e "${GREEN}[TEST] E2E tests passed!${NC}"
    else
        echo -e "${RED}[TEST] E2E tests failed!${NC}"
        E2E_RESULT=1
    fi
else
    echo -e "\n${YELLOW}[TEST] Skipping E2E tests in CI (set RUN_E2E=true to run)${NC}"
fi

cd ..

# API Route Validation
echo -e "\n${YELLOW}[TEST] Running API route validation...${NC}"
if python3 scripts/validate_api_routes.py > /tmp/api_validation.log 2>&1; then
    echo -e "${GREEN}[TEST] API route validation completed!${NC}"
    # Check if there are any missing routes
    if grep -q "Missing in backend: 0" /tmp/api_validation.log; then
        echo -e "${GREEN}[TEST] All frontend routes have backend implementations!${NC}"
    else
        echo -e "${YELLOW}[TEST] Warning: Some frontend routes are missing backend implementations${NC}"
        grep -A 20 "Frontend routes without backend implementation" /tmp/api_validation.log || true
        # Don't fail the test suite for this yet, just warn
    fi
else
    echo -e "${RED}[TEST] API route validation failed!${NC}"
    cat /tmp/api_validation.log
    API_VALIDATION_RESULT=1
fi

# Frontend Integration Tests (if backend is running)
if curl -s http://localhost:5001/api/status > /dev/null 2>&1 || curl -s http://localhost:5000/api/status > /dev/null 2>&1; then
    echo -e "\n${YELLOW}[TEST] Backend is running, executing integration tests...${NC}"
    cd web-ui
    if npm run test:integration; then
        echo -e "${GREEN}[TEST] Integration tests passed!${NC}"
    else
        echo -e "${RED}[TEST] Integration tests failed!${NC}"
        INTEGRATION_RESULT=1
    fi
    cd ..
else
    echo -e "\n${YELLOW}[TEST] Skipping integration tests (backend not running)${NC}"
fi

# Summary
echo -e "\n${YELLOW}[TEST] Test Summary:${NC}"
echo -e "Backend tests: $([ $BACKEND_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"
echo -e "Frontend tests: $([ $FRONTEND_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"
echo -e "API validation: $([ $API_VALIDATION_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"
if curl -s http://localhost:5001/api/status > /dev/null 2>&1 || curl -s http://localhost:5000/api/status > /dev/null 2>&1; then
    echo -e "Integration tests: $([ $INTEGRATION_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"
fi
if [ "$RUN_E2E" = "true" ] || [ "$CI" != "true" ]; then
    echo -e "E2E tests: $([ $E2E_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${RED}FAILED${NC}")"
fi

# Exit with failure if any tests failed
if [ $BACKEND_RESULT -ne 0 ] || [ $FRONTEND_RESULT -ne 0 ] || [ $E2E_RESULT -ne 0 ] || [ $API_VALIDATION_RESULT -ne 0 ] || [ $INTEGRATION_RESULT -ne 0 ]; then
    exit 1
fi

echo -e "\n${GREEN}[TEST] All tests passed!${NC}"
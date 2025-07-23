#!/bin/bash

echo "[E2E] Starting E2E tests..."
echo "[E2E] Please make sure your web app is running at http://localhost:5173"
echo ""

# Check if .env.test exists
if [ ! -f .env.test ]; then
    echo "[ERROR] .env.test file not found!"
    echo "Please create .env.test with your test credentials:"
    echo "  E2E_USERNAME=your_username"
    echo "  E2E_PASSWORD=your_password"
    exit 1
fi

# Load test credentials (skip comments)
export $(grep -v '^#' .env.test | xargs)

# Check if credentials are set
if [ -z "$E2E_USERNAME" ] || [ -z "$E2E_PASSWORD" ]; then
    echo "[ERROR] Test credentials not set in .env.test!"
    exit 1
fi

echo "[E2E] Using test user: $E2E_USERNAME"

# Run only the basic auth test first to verify setup
# Use headless mode since we're on a server without display
# Make sure the app knows about the backend URL
VITE_PROCESSING_SERVER=http://localhost:8091 npx playwright test e2e/auth.spec.ts

echo ""
echo "[E2E] If auth test passed, run all tests with:"
echo "  npx playwright test"
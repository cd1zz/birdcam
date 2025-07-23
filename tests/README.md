# BirdCam Test Framework

This document describes the test framework and testing practices for the BirdCam project.

## Overview

BirdCam uses a multi-layered testing approach with separate frameworks for backend (Python) and frontend (React/TypeScript) testing.

## Backend Tests (Python/Pytest)

### Structure

```
tests/
├── conftest.py           # Central test configuration and fixtures
├── requirements.txt      # Test dependencies
├── api/
│   └── test_api_validation.py    # API endpoint health tests
├── discovery/
│   └── api_discover.py           # Flask route discovery utility
└── ui/
    └── test_ui_api_mapping.py    # UI-API integration tests
```

### Running Backend Tests

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/api/test_api_validation.py

# Run tests matching a pattern
pytest -k "test_api"

# Run with coverage
pytest --cov=.
```

### Test Configuration

The backend tests use a test-specific environment configuration:

1. **Environment Setup**: Tests copy `.env.processor` to `.env.test` and override settings
   - If `.env.processor` doesn't exist, tests will use `config/examples/.env.processor.example`
   - Tests can be run from any directory thanks to automatic path resolution
2. **Test Database**: Uses SQLite in `tests/tmp/storage/`
3. **Mock Services**: Uses dummy implementations to avoid real API calls and database operations

### Key Fixtures (conftest.py)

- `setup_test_env`: Session-scoped fixture that configures the test environment
- `flask_app`: Creates a test Flask application with mock services
- `client`: Flask test client for making HTTP requests

### Mock Classes

- `DummyModelManager`: Mocks the AI model manager
- `DummyProcessingService`: Mocks video processing service
- `DummyRepo`: Mocks database repositories

## Frontend Tests (React/TypeScript)

### Structure

```
web-ui/
├── src/
│   ├── components/
│   │   └── *.test.tsx           # Component unit tests
│   ├── services/
│   │   └── *.test.ts            # Service unit tests
│   └── test/
│       └── setup.ts             # Global test setup
├── e2e/
│   ├── auth.spec.ts             # Authentication E2E tests
│   ├── detections.spec.ts       # Detection features E2E tests
│   ├── live-feeds.spec.ts       # Camera feed E2E tests
│   └── admin.spec.ts            # Admin panel E2E tests
├── vitest.config.ts             # Unit test configuration
└── playwright.config.ts         # E2E test configuration
```

### Running Frontend Tests

```bash
cd web-ui

# Run unit tests (watch mode)
npm test

# Run all tests (unit + integration)
npm run test:all

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test UserProfile.test.tsx

# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui

# Run E2E tests on specific browser
npm run test:e2e -- --project=chromium
```

### Test Types

1. **Unit Tests** (Vitest)
   - Component tests using React Testing Library
   - Service and utility function tests
   - Fast, isolated tests with mocked dependencies

2. **Integration Tests** (Vitest)
   - API client integration tests
   - Tests real HTTP calls against mock servers
   - File pattern: `*.integration.test.ts`

3. **E2E Tests** (Playwright)
   - Full user flow tests
   - Tests against running application
   - Multi-browser and mobile viewport testing

### E2E Test Setup

1. Create `.env.test` in web-ui directory:
   ```bash
   E2E_USERNAME=test_user
   E2E_PASSWORD=test_password
   ```

2. Ensure the application is running:
   ```bash
   # Terminal 1: Run backend
   python ai_processor/main.py

   # Terminal 2: Run frontend
   cd web-ui && npm run dev
   ```

3. Run E2E tests:
   ```bash
   cd web-ui
   ./run-e2e-tests.sh  # Or npm run test:e2e
   ```

## Test Data and Mocks

### Backend Mocks
- OpenCV (`cv2`) is mocked to avoid installation requirements
- All external services return static test data
- File operations use temporary test directories

### Frontend Mocks
- `window.matchMedia` - Media query support
- `IntersectionObserver` - Viewport intersection API
- API responses - Mocked with MSW or manual mocks
- Browser APIs - localStorage, sessionStorage

## Best Practices

### Writing Backend Tests

```python
def test_api_endpoint(client):
    """Test that endpoint returns expected status."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
```

### Writing Frontend Unit Tests

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

test('component renders correctly', async () => {
  const user = userEvent.setup()
  render(<MyComponent />)
  
  await user.click(screen.getByRole('button'))
  expect(screen.getByText('Success')).toBeInTheDocument()
})
```

### Writing E2E Tests

```typescript
import { test, expect } from '@playwright/test'

test('user can view detections', async ({ page }) => {
  await page.goto('/detections')
  await expect(page.locator('h1')).toContainText('Detections')
  await expect(page.locator('.detection-grid')).toBeVisible()
})
```

## Coverage Requirements

- Backend: Aim for >80% coverage on critical paths
- Frontend: Focus on user-facing features and error handling
- E2E: Cover main user workflows and critical paths

## Continuous Integration

Tests are designed to run in CI environments:
- Backend tests run without GPU/camera dependencies
- Frontend tests run in headless mode
- E2E tests can run against staging environments

## Troubleshooting

### Common Issues

1. **Import Errors (cv2)**
   - Already handled by mock in conftest.py
   - If persists, check Python path configuration

2. **Test Database Issues**
   - Delete `tests/tmp/` directory and retry
   - Check file permissions

3. **E2E Test Failures**
   - Ensure application is running on expected ports
   - Check `.env.test` credentials
   - Run with `--headed` flag to see browser

4. **Frontend Test Timeouts**
   - Increase timeout in test: `test.setTimeout(30000)`
   - Check for unresolved promises
   - Verify mock data is complete

### Debug Mode

```bash
# Backend tests with debugging
pytest -v -s --pdb

# Frontend tests with debugging
npm test -- --no-coverage --watch

# E2E tests with UI
npm run test:e2e:ui
```

## Adding New Tests

1. **Backend**: Create test file in appropriate directory under `tests/`
2. **Frontend Unit**: Add `*.test.tsx` next to component
3. **Frontend E2E**: Add `*.spec.ts` in `web-ui/e2e/`

Remember to:
- Follow existing naming conventions
- Use appropriate fixtures and utilities
- Mock external dependencies
- Test both success and error cases
- Keep tests focused and isolated
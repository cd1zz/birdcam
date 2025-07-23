# Testing Guide

This document describes the comprehensive testing strategy for the BirdCam project, covering backend API tests, frontend unit tests, and end-to-end tests.

## Overview

The project uses a multi-layered testing approach:
- **Backend**: Python tests using pytest
- **Frontend**: React component tests using Vitest and React Testing Library
- **E2E**: Full system tests using Playwright

## Backend Testing

### Running Tests

```bash
# Run all backend tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_motion_event_broadcaster.py

# Run tests matching pattern
pytest -k "test_camera"

# Run only unit or integration tests
pytest tests/unit/
pytest tests/integration/
```

### Test Structure

```
tests/
├── unit/              # Fast, isolated unit tests
├── integration/       # Tests with database/filesystem
└── requirements.txt   # Testing dependencies
```

### Writing Backend Tests

```python
# Example unit test
def test_camera_detection(mock_camera):
    camera = CameraManager()
    result = camera.detect_motion(mock_frame)
    assert result.confidence > 0.8
```

## Frontend Testing

### Setup

The frontend uses Vitest for unit testing and Playwright for E2E testing.

### Running Frontend Tests

```bash
cd web-ui

# Run unit tests
npm test

# Run tests in watch mode
npm run test

# Run with UI
npm run test:ui

# Generate coverage report
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui
```

### Test Examples

#### Component Test (Vitest)
```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DetectionGrid } from './DetectionGrid'

test('displays detection cards', async () => {
  const detections = [/* mock data */]
  render(<DetectionGrid detections={detections} />)
  
  expect(screen.getAllByRole('img')).toHaveLength(detections.length)
})
```

#### E2E Test (Playwright)
```typescript
import { test, expect } from '@playwright/test'

test('user can login', async ({ page }) => {
  await page.goto('/login')
  await page.fill('input[name="username"]', 'testuser')
  await page.fill('input[name="password"]', 'password')
  await page.click('button[type="submit"]')
  
  await expect(page).toHaveURL('/')
})
```

## API Testing

The API endpoints are tested through integration tests that verify:
- Authentication flows
- CRUD operations
- Error handling
- Response formats

### Key Test Files

- `tests/integration/test_api_endpoints.py` - Main API test suite
- `src/api/client.test.ts` - Frontend API client tests

## Running All Tests

Use the comprehensive test script:

```bash
# Run all tests (backend, frontend, E2E)
./scripts/test-all.sh

# Skip E2E tests (useful in CI)
CI=true ./scripts/test-all.sh

# Force E2E tests in CI
RUN_E2E=true ./scripts/test-all.sh
```

## Continuous Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Scheduled nightly builds

GitHub Actions workflow runs:
1. Backend tests (multiple Python versions)
2. Frontend unit tests
3. E2E tests
4. Integration tests

## Test Coverage

- Backend: Aim for >80% coverage
- Frontend: Aim for >70% coverage
- Critical paths must have 100% coverage

View coverage reports:
- Backend: `open htmlcov/index.html`
- Frontend: `open web-ui/coverage/index.html`

## Pre-commit Hooks

Install pre-commit hooks to run tests before commits:

```bash
pip install pre-commit
pre-commit install
```

This runs:
- Python linting (ruff)
- Frontend linting (ESLint)
- Unit tests
- Code formatting

## Best Practices

1. **Write tests first** - TDD approach for new features
2. **Keep tests fast** - Mock external dependencies
3. **Test behavior, not implementation** - Focus on outcomes
4. **Use descriptive names** - Test names should explain what they verify
5. **Isolate tests** - Each test should be independent
6. **Clean up** - Always clean up test data/state

## Debugging Tests

### Backend
```bash
# Run with verbose output
pytest -vv

# Run with debugging
pytest --pdb

# Show print statements
pytest -s
```

### Frontend
```bash
# Debug specific test
npm run test -- --grep "should display camera feed"

# Run Playwright in debug mode
npm run test:e2e:debug
```

## Performance Testing

For load testing the API:
```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/performance/locustfile.py
```

## Security Testing

Security considerations in tests:
- Never commit real credentials
- Use environment variables for sensitive data
- Test authentication and authorization
- Verify input validation
- Check for SQL injection vulnerabilities

## Troubleshooting

### Common Issues

1. **Tests fail locally but pass in CI**
   - Check environment variables
   - Verify database state
   - Look for timing issues

2. **Flaky E2E tests**
   - Add explicit waits
   - Check for race conditions
   - Verify test isolation

3. **Coverage not updating**
   - Clear coverage cache: `rm -rf .coverage htmlcov/`
   - Reinstall dependencies

## Contributing

When adding new features:
1. Write tests first
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update this documentation if needed
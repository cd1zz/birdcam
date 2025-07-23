// Test environment setup for E2E tests
export const TEST_USERS = {
  admin: {
    username: process.env.E2E_ADMIN_USER || 'admin',
    password: process.env.E2E_ADMIN_PASS || 'admin123'
  },
  viewer: {
    username: process.env.E2E_VIEWER_USER || 'viewer',
    password: process.env.E2E_VIEWER_PASS || 'viewer123'
  }
}

export const TEST_CONFIG = {
  baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
  apiURL: process.env.E2E_API_URL || 'http://localhost:8000',
  defaultTimeout: 30000,
  retries: process.env.CI ? 2 : 0
}
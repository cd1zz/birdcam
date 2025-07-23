import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('user can login and logout', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login')

    // Fill in login form
    await page.fill('input[name="username"]', process.env.E2E_USERNAME || 'testuser')
    await page.fill('input[name="password"]', process.env.E2E_PASSWORD || 'testpass')
    
    // Submit form
    await page.click('button[type="submit"]')

    // Wait for navigation to dashboard
    await page.waitForURL('/')
    
    // Verify user is logged in by checking for logout button
    await expect(page.getByRole('button', { name: 'Logout' }).first()).toBeVisible()

    // Logout
    await page.getByRole('button', { name: 'Logout' }).first().click()
    
    // Should redirect to login
    await page.waitForURL('/login')
    await expect(page.getByRole('heading', { name: 'Bird Detection System' })).toBeVisible()
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[name="username"]', 'wronguser')
    await page.fill('input[name="password"]', 'wrongpass')
    await page.click('button[type="submit"]')

    // Should show error message
    await expect(page.locator('text=Invalid username or password')).toBeVisible()
    
    // Should stay on login page
    await expect(page).toHaveURL('/login')
  })

  test('protected routes redirect to login', async ({ page }) => {
    // Try to access protected route without authentication
    await page.goto('/detections')
    
    // Should redirect to login
    await page.waitForURL('/login')
    await expect(page.getByRole('heading', { name: 'Bird Detection System' })).toBeVisible()
  })

  test('remembers redirect after login', async ({ page }) => {
    // Try to access protected route
    await page.goto('/analytics')
    
    // Should redirect to login
    await page.waitForURL('/login')
    
    // Login
    await page.fill('input[name="username"]', process.env.E2E_USERNAME || 'testuser')
    await page.fill('input[name="password"]', process.env.E2E_PASSWORD || 'testpass')
    await page.click('button[type="submit"]')
    
    // Should redirect back to analytics after login
    await page.waitForURL('/analytics')
  })
})
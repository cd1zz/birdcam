import { test, expect } from '@playwright/test'

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    // Set longer timeout for login
    test.setTimeout(30000)
    
    // Login as admin
    await page.goto('/login')
    
    // Wait for login form to be ready
    await page.waitForSelector('input[name="username"]', { state: 'visible' })
    
    await page.fill('input[name="username"]', process.env.E2E_ADMIN_USERNAME || 'admin')
    await page.fill('input[name="password"]', process.env.E2E_ADMIN_PASSWORD || 'adminpass')
    await page.click('button[type="submit"]')
    
    // Wait for either success (redirect to /) or error message
    await Promise.race([
      page.waitForURL('/'),
      page.waitForSelector('text=Invalid username or password', { timeout: 5000 })
    ])
    
    // Verify we're logged in
    const url = page.url()
    if (!url.endsWith('/')) {
      throw new Error(`Login failed - still on ${url}`)
    }
  })

  test('admin can access admin panel', async ({ page }) => {
    await page.goto('/admin')
    
    // Should see admin panel with tabs
    await expect(page.locator('h1:has-text("Admin Panel")')).toBeVisible()
    
    // Check for tab buttons
    await expect(page.locator('button:has-text("Users")')).toBeVisible()
    await expect(page.locator('button:has-text("Motion Detection")')).toBeVisible()
    await expect(page.locator('button:has-text("System Settings")')).toBeVisible()
  })

  test('can manage users', async ({ page }) => {
    await page.goto('/admin')
    
    // Click on Users tab
    await page.click('button:has-text("Users")')
    
    // Wait for users table
    await page.waitForSelector('table')
    
    // Should see user list
    await expect(page.locator('th:has-text("Username")')).toBeVisible()
    await expect(page.locator('th:has-text("Role")')).toBeVisible()
    
    // Click add user button
    await page.click('button:has-text("Add User")')
    
    // Wait for form to appear
    await page.waitForSelector('input[placeholder="Username"]')
    
    // Fill new user form
    await page.fill('input[placeholder="Username"]', 'newtestuser')
    await page.fill('input[placeholder="Password"]', 'newpass123')
    await page.selectOption('select', 'viewer')
    
    // Submit form
    await page.click('button:has-text("Create")')
    
    // New user should appear in list
    await expect(page.locator('td:has-text("newtestuser")')).toBeVisible({ timeout: 10000 })
  })

  test('can update system settings', async ({ page }) => {
    await page.goto('/admin')
    
    // Click on System Settings tab
    await page.click('button:has-text("System Settings")')
    
    // Wait for settings form
    await page.waitForSelector('h3:has-text("Detection Settings")')
    
    // Update detection confidence
    const confidenceInput = page.locator('input[type="number"]').filter({ hasText: /Confidence Threshold/ })
    await confidenceInput.fill('0.7')
    
    // Update retention days for detections
    const retentionInput = page.locator('div:has-text("Retention Days (Detections)") input[type="number"]').first()
    await retentionInput.fill('45')
    
    // Save settings
    await page.click('button:has-text("Save Settings")')
    
    // Should see success notification
    await expect(page.locator('.notification-success, [role="alert"]')).toBeVisible({ timeout: 10000 })
  })

  test('can view system status', async ({ page }) => {
    await page.goto('/admin')
    
    // Should see system status metrics
    await expect(page.locator('text=Disk Usage')).toBeVisible()
    await expect(page.locator('text=CPU Usage')).toBeVisible()
    await expect(page.locator('text=Memory Usage')).toBeVisible()
    await expect(page.locator('text=Active Cameras')).toBeVisible()
  })

  test('non-admin cannot access admin panel', async ({ page }) => {
    // Logout and login as viewer
    await page.click('button:has-text("Logout")').first()
    await page.waitForURL('/login')
    
    await page.fill('input[name="username"]', process.env.E2E_USERNAME || 'viewer')
    await page.fill('input[name="password"]', process.env.E2E_PASSWORD || 'viewerpass')
    await page.click('button[type="submit"]')
    await page.waitForURL('/')
    
    // Try to access admin panel
    await page.goto('/admin')
    
    // Should show access denied message
    await expect(page.locator('text=Access Denied')).toBeVisible()
    await expect(page.locator('text=You do not have permission to access this page')).toBeVisible()
  })

  test('can delete user', async ({ page }) => {
    await page.goto('/admin')
    
    // Click on Users tab
    await page.click('button:has-text("Users")')
    
    // Wait for users table
    await page.waitForSelector('table')
    
    // Find a test user row (not the current admin)
    const userRow = page.locator('tr').filter({ hasText: 'testviewer' }).first()
    
    // Click delete button
    await userRow.locator('button:has-text("Delete")').click()
    
    // Confirm deletion in the dialog
    await page.click('button:has-text("Yes, delete")')
    
    // User should be removed from list
    await expect(page.locator('td:has-text("testviewer")')).not.toBeVisible({ timeout: 10000 })
  })

  test('can edit user role', async ({ page }) => {
    await page.goto('/admin')
    
    // Click on Users tab
    await page.click('button:has-text("Users")')
    
    // Wait for users table
    await page.waitForSelector('table')
    
    // Find a viewer user
    const userRow = page.locator('tr').filter({ hasText: 'viewer' }).first()
    
    // Find and click the role dropdown in that row
    const roleSelect = userRow.locator('select')
    await roleSelect.selectOption('admin')
    
    // Role should be updated immediately
    await expect(userRow.locator('td:has-text("admin")')).toBeVisible({ timeout: 10000 })
  })
})
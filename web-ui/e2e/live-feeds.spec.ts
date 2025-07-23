import { test, expect } from '@playwright/test'

test.describe('Live Camera Feeds', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass')
    await page.click('button[type="submit"]')
    await page.waitForURL('/')
  })

  test('displays camera feeds', async ({ page }) => {
    await page.goto('/live')
    
    // Wait for camera feeds to load
    await page.waitForSelector('.camera-feed', { timeout: 10000 })
    
    // Should show multiple camera feeds
    const cameraFeeds = await page.locator('.camera-feed').count()
    expect(cameraFeeds).toBeGreaterThan(0)
    
    // Each feed should have a camera name
    const firstFeed = page.locator('.camera-feed').first()
    await expect(firstFeed.locator('h3')).toContainText(/Camera/)
  })

  test('can toggle between stream and snapshot mode', async ({ page }) => {
    await page.goto('/live')
    await page.waitForSelector('.camera-feed')
    
    const firstFeed = page.locator('.camera-feed').first()
    
    // Click snapshot mode button
    await firstFeed.locator('button:has-text("Snapshot")').click()
    
    // Verify image src changed to snapshot
    const img = firstFeed.locator('img')
    await expect(img).toHaveAttribute('src', /snapshot/)
    
    // Switch back to stream
    await firstFeed.locator('button:has-text("Stream")').click()
    await expect(img).toHaveAttribute('src', /stream/)
  })

  test('can enter fullscreen mode', async ({ page }) => {
    await page.goto('/live')
    await page.waitForSelector('.camera-feed')
    
    const firstFeed = page.locator('.camera-feed').first()
    
    // Click fullscreen button
    await firstFeed.locator('button[aria-label="Enter fullscreen"]').click()
    
    // Verify fullscreen mode (checking for fullscreen class or element)
    // Note: Actual fullscreen API might not work in headless mode
    await expect(firstFeed).toHaveClass(/fullscreen/)
  })

  test('shows recording indicator for active cameras', async ({ page }) => {
    await page.goto('/live')
    await page.waitForSelector('.camera-feed')
    
    // Look for recording indicators
    const recordingBadges = page.locator('.bg-red-500:has-text("REC")')
    
    // At least one camera should be recording
    await expect(recordingBadges.first()).toBeVisible()
  })

  test('handles camera errors gracefully', async ({ page }) => {
    await page.goto('/live')
    
    // Simulate network error by blocking image requests
    await page.route('**/api/proxy/cameras/*/stream', route => route.abort())
    
    await page.waitForSelector('.camera-feed')
    
    // Should show error message
    await expect(page.locator('text=Failed to load camera feed').first()).toBeVisible()
    
    // Should have retry button
    await expect(page.locator('button:has-text("Retry")').first()).toBeVisible()
  })
})
import { test, expect } from '@playwright/test'

test.describe('Wildlife Detections', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass')
    await page.click('button[type="submit"]')
    await page.waitForURL('/')
  })

  test('displays detection grid', async ({ page }) => {
    await page.goto('/detections')
    
    // Wait for detections to load
    await page.waitForSelector('[data-testid="detection-card"]', { timeout: 10000 })
    
    // Should show detection cards
    const detectionCards = await page.locator('[data-testid="detection-card"]').count()
    expect(detectionCards).toBeGreaterThan(0)
  })

  test('can filter detections by date', async ({ page }) => {
    await page.goto('/detections')
    await page.waitForSelector('[data-testid="detection-card"]')
    
    // Get initial count
    const initialCount = await page.locator('[data-testid="detection-card"]').count()
    
    // Set date filter
    await page.fill('input[name="start_date"]', '2025-01-01')
    await page.fill('input[name="end_date"]', '2025-01-15')
    await page.click('button:has-text("Apply Filters")')
    
    // Wait for filtered results
    await page.waitForTimeout(1000)
    
    // Count should be different (likely less)
    const filteredCount = await page.locator('[data-testid="detection-card"]').count()
    expect(filteredCount).toBeLessThanOrEqual(initialCount)
  })

  test('can filter by species', async ({ page }) => {
    await page.goto('/detections')
    await page.waitForSelector('[data-testid="detection-card"]')
    
    // Select bird filter
    await page.selectOption('select[name="species"]', 'bird')
    await page.click('button:has-text("Apply Filters")')
    
    // Wait for filtered results
    await page.waitForTimeout(1000)
    
    // All results should contain bird
    const cards = page.locator('[data-testid="detection-card"]')
    const count = await cards.count()
    
    for (let i = 0; i < count; i++) {
      await expect(cards.nth(i)).toContainText(/bird/i)
    }
  })

  test('can open video modal', async ({ page }) => {
    await page.goto('/detections')
    await page.waitForSelector('[data-testid="detection-card"]')
    
    // Click first detection card
    await page.locator('[data-testid="detection-card"]').first().click()
    
    // Video modal should open
    await expect(page.locator('[data-testid="video-modal"]')).toBeVisible()
    
    // Should contain video element
    await expect(page.locator('video')).toBeVisible()
    
    // Close modal
    await page.click('button[aria-label="Close"]')
    await expect(page.locator('[data-testid="video-modal"]')).not.toBeVisible()
  })

  test('shows confidence badges with colors', async ({ page }) => {
    await page.goto('/detections')
    await page.waitForSelector('[data-testid="detection-card"]')
    
    // Check for confidence badges
    const highConfidenceBadge = page.locator('.bg-green-100').first()
    const mediumConfidenceBadge = page.locator('.bg-yellow-100').first()
    
    // At least one should be visible
    const hasHighConfidence = await highConfidenceBadge.isVisible().catch(() => false)
    const hasMediumConfidence = await mediumConfidenceBadge.isVisible().catch(() => false)
    
    expect(hasHighConfidence || hasMediumConfidence).toBeTruthy()
  })

  test('can download detection video', async ({ page }) => {
    await page.goto('/detections')
    await page.waitForSelector('[data-testid="detection-card"]')
    
    // Set up download promise before clicking
    const downloadPromise = page.waitForEvent('download')
    
    // Click download button on first detection
    await page.locator('[data-testid="detection-card"]').first().hover()
    await page.locator('button[aria-label="Download"]').first().click()
    
    // Wait for download
    const download = await downloadPromise
    
    // Verify download
    expect(download.suggestedFilename()).toMatch(/\.(mp4|avi|mov)$/)
  })

  test('pagination works correctly', async ({ page }) => {
    await page.goto('/detections')
    await page.waitForSelector('[data-testid="detection-card"]')
    
    // Check if pagination exists
    const paginationExists = await page.locator('.pagination').isVisible().catch(() => false)
    
    if (paginationExists) {
      // Click next page
      await page.click('button[aria-label="Next page"]')
      
      // Wait for new results to load
      await page.waitForTimeout(1000)
      
      // Should still have detection cards
      await expect(page.locator('[data-testid="detection-card"]').first()).toBeVisible()
    }
  })
})
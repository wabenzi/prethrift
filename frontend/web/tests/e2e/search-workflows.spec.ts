import { test, expect } from '@playwright/test';

test.describe('Prethrift Search User Workflows', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');

    // Wait for the app to load
    await page.waitForLoadState('networkidle');
  });

  test('Complete text search workflow', async ({ page }) => {
    // Test user journey: Search for vintage jeans

    // 1. User sees search interface
    await expect(page.locator('[data-testid="search-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="search-button"]')).toBeVisible();

    // 2. User types search query
    await page.fill('[data-testid="search-input"]', 'blue wide leg jeans with stars');

    // 3. User submits search
    await page.click('[data-testid="search-button"]');

    // 4. User sees loading state
    await expect(page.locator('[data-testid="search-loading"]')).toBeVisible();

    // 5. User sees search results
    await page.waitForSelector('[data-testid="search-results"]', { timeout: 10000 });
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();

    // 6. User sees specific result
    await expect(page.locator('text=Wide-Leg Star Appliqué Jeans')).toBeVisible();

    // 7. User sees search statistics
    await expect(page.locator('[data-testid="search-stats"]')).toContainText('results found');
    await expect(page.locator('[data-testid="search-time"]')).toContainText('ms');

    // 8. User clicks on a result
    await page.click('[data-testid="result-item"]:first-child');

    // 9. User sees item details
    await expect(page.locator('[data-testid="item-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="item-title"]')).toBeVisible();
    await expect(page.locator('[data-testid="item-image"]')).toBeVisible();
  });

  test('Visual similarity search workflow', async ({ page }) => {
    // Test user journey: Upload image for visual search

    // 1. User switches to image search mode
    await page.click('[data-testid="search-type-image"]');
    await expect(page.locator('[data-testid="image-upload-area"]')).toBeVisible();

    // 2. User uploads an image
    const imageFile = '../../design/images/baggy-jeans.jpeg';
    await page.setInputFiles('[data-testid="image-upload-input"]', imageFile);

    // 3. User sees image preview
    await expect(page.locator('[data-testid="image-preview"]')).toBeVisible();

    // 4. User submits visual search
    await page.click('[data-testid="visual-search-button"]');

    // 5. User sees loading state
    await expect(page.locator('[data-testid="visual-search-loading"]')).toBeVisible();

    // 6. User sees similarity results
    await page.waitForSelector('[data-testid="similarity-results"]', { timeout: 15000 });
    await expect(page.locator('[data-testid="similarity-results"]')).toBeVisible();

    // 7. User sees similarity scores
    const similarityScores = page.locator('[data-testid="similarity-score"]');
    await expect(similarityScores.first()).toBeVisible();

    // 8. User finds similar items
    const similarItems = page.locator('[data-testid="similar-item"]');
    const similarCount = await similarItems.count();
    expect(similarCount).toBeGreaterThan(0);
  });

  test('Hybrid search with filters workflow', async ({ page }) => {
    // Test user journey: Search with text + filters

    // 1. User opens filters panel
    await page.click('[data-testid="filters-toggle"]');
    await expect(page.locator('[data-testid="filters-panel"]')).toBeVisible();

    // 2. User applies category filter
    await page.selectOption('[data-testid="category-filter"]', 'pants');

    // 3. User applies color filter
    await page.selectOption('[data-testid="color-filter"]', 'blue');

    // 4. User applies price range
    await page.fill('[data-testid="price-min"]', '50');
    await page.fill('[data-testid="price-max"]', '100');

    // 5. User enters search query
    await page.fill('[data-testid="search-input"]', 'casual denim');

    // 6. User submits hybrid search
    await page.click('[data-testid="search-button"]');

    // 7. User sees filtered results
    await page.waitForSelector('[data-testid="search-results"]');

    // 8. User verifies filters are applied
    const results = page.locator('[data-testid="result-item"]');
    const resultCount = await results.count();
    expect(resultCount).toBeGreaterThan(0);

    // 9. User sees applied filters indicator
    await expect(page.locator('[data-testid="active-filters"]')).toContainText('pants');
    await expect(page.locator('[data-testid="active-filters"]')).toContainText('blue');

    // 10. User removes a filter
    await page.click('[data-testid="remove-filter-pants"]');

    // 11. Results update automatically
    await page.waitForSelector('[data-testid="search-results"]');
    await expect(page.locator('[data-testid="active-filters"]')).not.toContainText('pants');
  });

  test('Search suggestions and autocomplete workflow', async ({ page }) => {
    // Test user journey: Using search suggestions

    // 1. User starts typing
    await page.fill('[data-testid="search-input"]', 'blue');

    // 2. User sees suggestions dropdown
    await page.waitForSelector('[data-testid="search-suggestions"]');
    await expect(page.locator('[data-testid="search-suggestions"]')).toBeVisible();

    // 3. User sees multiple suggestions
    const suggestions = page.locator('[data-testid="suggestion-item"]');
    const suggestionCount = await suggestions.count();
    expect(suggestionCount).toBeGreaterThan(0);

    // 4. User clicks on a suggestion
    await page.click('[data-testid="suggestion-item"]:first-child');

    // 5. Search input is filled with suggestion
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).not.toHaveValue('blue');

    // 6. Search is automatically triggered
    await page.waitForSelector('[data-testid="search-results"]');
  });

  test('Error handling and recovery workflow', async ({ page }) => {
    // Test user journey: Handling search errors

    // 1. User searches with invalid query (mock error)
    await page.route('**/api/search**', route => {
      route.fulfill({ status: 500, body: 'Search service unavailable' });
    });

    await page.fill('[data-testid="search-input"]', 'test query');
    await page.click('[data-testid="search-button"]');

    // 2. User sees error message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('service unavailable');

    // 3. User tries again (restore normal behavior)
    await page.unroute('**/api/search**');
    await page.click('[data-testid="retry-search"]');

    // 4. Search works normally
    await page.waitForSelector('[data-testid="search-results"]');
    await expect(page.locator('[data-testid="error-message"]')).not.toBeVisible();
  });

  test('Mobile responsive search workflow', async ({ page }) => {
    // Test on mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // 1. User sees mobile-optimized interface
    await expect(page.locator('[data-testid="mobile-search-input"]')).toBeVisible();

    // 2. User opens mobile filters
    await page.click('[data-testid="mobile-filters-button"]');
    await expect(page.locator('[data-testid="mobile-filters-modal"]')).toBeVisible();

    // 3. User applies filters on mobile
    await page.selectOption('[data-testid="mobile-category-filter"]', 'dress');
    await page.click('[data-testid="apply-mobile-filters"]');

    // 4. User searches on mobile
    await page.fill('[data-testid="mobile-search-input"]', 'summer dress');
    await page.click('[data-testid="mobile-search-button"]');

    // 5. User sees mobile-optimized results
    await page.waitForSelector('[data-testid="mobile-results-grid"]');
    const mobileResults = page.locator('[data-testid="mobile-result-card"]');
    const mobileResultCount = await mobileResults.count();
    expect(mobileResultCount).toBeGreaterThan(0);
  });

  test('Performance and user experience workflow', async ({ page }) => {
    // Test search performance and UX

    // 1. Measure search response time
    const startTime = Date.now();

    await page.fill('[data-testid="search-input"]', 'graphic tshirt');
    await page.click('[data-testid="search-button"]');

    await page.waitForSelector('[data-testid="search-results"]');
    const endTime = Date.now();
    const searchTime = endTime - startTime;

    // 2. Verify search is fast (under 3 seconds)
    expect(searchTime).toBeLessThan(3000);

    // 3. Verify loading states are shown
    await page.fill('[data-testid="search-input"]', 'another query');
    await page.click('[data-testid="search-button"]');

    // Should see loading immediately
    await expect(page.locator('[data-testid="search-loading"]')).toBeVisible();

    // 4. Verify results are accessible
    await page.waitForSelector('[data-testid="search-results"]');

    // Check keyboard navigation
    await page.keyboard.press('Tab');
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // 5. Verify images load properly
    const images = page.locator('[data-testid="result-image"]');
    const firstImage = images.first();
    await expect(firstImage).toBeVisible();

    // Wait for image to load
    await page.waitForLoadState('networkidle');
  });

  test('Multi-step search refinement workflow', async ({ page }) => {
    // Test user journey: Iterative search refinement

    // 1. User performs initial broad search
    await page.fill('[data-testid="search-input"]', 'vintage');
    await page.click('[data-testid="search-button"]');

    await page.waitForSelector('[data-testid="search-results"]');
    const initialResults = page.locator('[data-testid="result-item"]');
    const initialCount = await initialResults.count();

    // 2. User refines search with more specific terms
    await page.fill('[data-testid="search-input"]', 'vintage blue jeans');
    await page.click('[data-testid="search-button"]');

    await page.waitForSelector('[data-testid="search-results"]');
    const refinedResults = page.locator('[data-testid="result-item"]');
    const refinedCount = await refinedResults.count();

    // 3. User should see fewer, more relevant results
    expect(refinedCount).toBeLessThanOrEqual(initialCount);

    // 4. User clicks "Find Similar" on a result
    await page.click('[data-testid="find-similar-button"]:first-child');

    // 5. User sees similarity-based results
    await page.waitForSelector('[data-testid="similarity-results"]');
    await expect(page.locator('[data-testid="similarity-results"]')).toBeVisible();

    // 6. User goes back to text search
    await page.click('[data-testid="back-to-search"]');
    await expect(page.locator('[data-testid="search-input"]')).toBeVisible();
  });
});

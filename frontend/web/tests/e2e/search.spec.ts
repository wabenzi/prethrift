import { test, expect } from '@playwright/test';

test.describe('Prethrift Search Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('Enhanced text search functionality', async ({ page }) => {
    // Test the search input and results
    const searchInput = page.locator('[data-testid="search-input"]');
    const searchButton = page.locator('[data-testid="search-button"]');

    await searchInput.fill('blue wide leg jeans');
    await searchButton.click();

    // Wait for results to load
    await page.waitForSelector('[data-testid="search-results"]');

    // Check that results contain expected items
    const results = page.locator('[data-testid="search-result-item"]');
    await expect(results).toHaveCount.greaterThan(0);

    // Verify specific result appears
    await expect(page.locator('text=Wide-Leg Star Appliqué Jeans')).toBeVisible();
  });

  test('Visual similarity search', async ({ page }) => {
    // Test image upload functionality
    const imageUpload = page.locator('[data-testid="image-upload"]');
    const fileInput = page.locator('input[type="file"]');

    // Upload test image (you'd need to add test images)
    await fileInput.setInputFiles('../../design/images/baggy-jeans.jpeg');

    // Wait for similarity results
    await page.waitForSelector('[data-testid="similarity-results"]');

    const similarItems = page.locator('[data-testid="similar-item"]');
    await expect(similarItems).toHaveCount.greaterThan(0);
  });

  test('Hybrid search with filters', async ({ page }) => {
    // Test combining text search with filters
    const searchInput = page.locator('[data-testid="search-input"]');
    const categoryFilter = page.locator('[data-testid="category-filter"]');
    const colorFilter = page.locator('[data-testid="color-filter"]');

    await searchInput.fill('summer dress');
    await categoryFilter.selectOption('dresses');
    await colorFilter.selectOption('blue');

    const searchButton = page.locator('[data-testid="search-button"]');
    await searchButton.click();

    await page.waitForSelector('[data-testid="search-results"]');

    // Verify filtered results
    const results = page.locator('[data-testid="search-result-item"]');
    await expect(results).toHaveCount.greaterThan(0);

    // Check that results match filters
    const firstResult = results.first();
    await expect(firstResult).toContainText('dress');
  });

  test('Search performance and responsiveness', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"]');
    const searchButton = page.locator('[data-testid="search-button"]');

    // Measure search response time
    const startTime = Date.now();

    await searchInput.fill('graphic tshirt');
    await searchButton.click();

    await page.waitForSelector('[data-testid="search-results"]');

    const endTime = Date.now();
    const responseTime = endTime - startTime;

    // Expect search to complete within reasonable time
    expect(responseTime).toBeLessThan(2000); // 2 seconds

    // Verify loading states
    await expect(page.locator('[data-testid="search-loading"]')).toBeHidden();
  });

  test('Search result interaction and navigation', async ({ page }) => {
    // Test clicking on search results
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('queen tshirt');

    const searchButton = page.locator('[data-testid="search-button"]');
    await searchButton.click();

    await page.waitForSelector('[data-testid="search-results"]');

    // Click on first result
    const firstResult = page.locator('[data-testid="search-result-item"]').first();
    await firstResult.click();

    // Verify navigation to detail page
    await expect(page).toHaveURL(/.*\/item\/.*/ );

    // Verify item details are displayed
    await expect(page.locator('[data-testid="item-title"]')).toBeVisible();
    await expect(page.locator('[data-testid="item-image"]')).toBeVisible();
  });

  test('Search autocomplete and suggestions', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"]');

    // Type partial query
    await searchInput.fill('blue');

    // Wait for suggestions to appear
    await page.waitForSelector('[data-testid="search-suggestions"]');

    const suggestions = page.locator('[data-testid="suggestion-item"]');
    await expect(suggestions).toHaveCount.greaterThan(0);

    // Click on a suggestion
    const firstSuggestion = suggestions.first();
    await firstSuggestion.click();

    // Verify search input is filled with suggestion
    await expect(searchInput).toHaveValue.not('blue');

    // Verify search results load
    await page.waitForSelector('[data-testid="search-results"]');
  });
});

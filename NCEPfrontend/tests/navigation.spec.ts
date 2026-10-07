import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

test.describe('Navigation and Layouts', () => {

  test('Sidebar toggle works on mobile', async ({ page }) => {
    // This test should run on a mobile viewport
    test.skip(page.viewportSize()?.width! > 768, 'Test only applies to mobile viewports');
    
    await loginAs(page, 'patient');
    await page.goto('/patient/dashboard');
    
    // Find the hamburger menu button
    const menuBtn = page.locator('button').filter({ has: page.locator('svg.lucide-menu, svg.lucide-align-justify') }).first();
    
    if (await menuBtn.isVisible()) {
      await menuBtn.click();
      
      // Wait for the sidebar to be visible
      const sidebar = page.locator('aside').first();
      await expect(sidebar).toBeVisible();
      
      // Close it (either by clicking a backdrop or close button)
      const closeBtn = page.locator('button').filter({ has: page.locator('svg.lucide-x') }).first();
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
        await expect(sidebar).not.toBeVisible();
      }
    }
  });

  test('Logout cleans up session and navigates to login', async ({ page }) => {
    await loginAs(page, 'doctor');
    await page.goto('/doctor/dashboard');
    
    // Find logout button in sidebar
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout"), button:has-text("Sign Out")').first();
    await logoutBtn.click();
    
    await expect(page).toHaveURL(/.*\/login/);
    
    // Verify session is cleared by trying to go back
    await page.goto('/doctor/dashboard');
    await expect(page).toHaveURL(/.*\/login/);
  });

});

import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

test.describe('Form validations and submissions', () => {

  test('Login form requires email and password', async ({ page }) => {
    await page.goto('/login');
    await page.waitForTimeout(1000);
    await page.click('button[type="submit"]');
    
    // Check for native validation or custom validation messages
    // We expect the form not to submit and stay on the login page
    expect(page.url()).toContain('/login');
    
    // Try invalid credentials
    await page.fill('input[type="email"]', 'wrong@example.com');
    await page.fill('input[type="password"]', 'badpass');
    await page.locator('input[type="password"]').press('Enter');
    
    const errorMsg = page.locator('.text-error').first();
    await expect(errorMsg).toBeVisible();
    await expect(errorMsg).toContainText('Invalid');
  });

  test('Doctor can submit an ECG upload form', async ({ page }) => {
    await loginAs(page, 'doctor');
    await page.click('[aria-label="Toggle navigation"]');
    await page.click('a[href="/doctor/ecg-upload"]');
    await page.waitForURL('**/doctor/ecg-upload');
    
    // Fill out the form
    // Wait for form to be visible
    await page.waitForSelector('form');
    // Find the select element by label or just the first select
    await page.locator('select').first().selectOption({ index: 1 });
    await page.locator('input[type="date"]').fill('2026-07-12');
    
    // Create a dummy file buffer to upload
    await page.setInputFiles('input[type="file"]', {
      name: 'test-ecg.dat',
      mimeType: 'text/plain',
      buffer: Buffer.from('dummy data')
    });
    
    await page.locator('input[type="date"]').press('Enter');
    
    // Wait for the success toast or state
    await page.waitForTimeout(2000); // Give the mock upload time to finish
  });

});

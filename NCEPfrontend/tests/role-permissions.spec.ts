import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

test.describe('Role Permissions & Route Isolation', () => {

  test('Patient cannot access doctor dashboard', async ({ page }) => {
    await loginAs(page, 'patient');
    await page.goto('/doctor/dashboard');
    await expect(page.locator('body')).toContainText('Access Denied');
  });

  test('Doctor cannot access admin dashboard', async ({ page }) => {
    await loginAs(page, 'doctor');
    await page.goto('/admin/dashboard');
    await expect(page.locator('body')).toContainText('Access Denied');
  });

  test('Admin cannot access superadmin dashboard', async ({ page }) => {
    await loginAs(page, 'admin');
    await page.goto('/superadmin/dashboard');
    await expect(page.locator('body')).toContainText('Access Denied');
  });

  test('Unauthenticated user cannot access patient dashboard', async ({ page }) => {
    await page.goto('/patient/dashboard');
    // It should redirect to /login
    await expect(page).toHaveURL(/.*\/login/);
  });

});

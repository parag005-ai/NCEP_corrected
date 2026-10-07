import { expect, type Page, type BrowserContext } from '@playwright/test';

type Role = 'patient' | 'doctor' | 'admin' | 'superadmin';

export async function loginAs(page: Page, role: Role) {
  await page.goto('/login');
  // Wait for React to hydrate so the onSubmit event listener is attached
  await page.waitForTimeout(1000);
  
  let email = '';
  let password = '';

  switch (role) {
    case 'patient':
      email = process.env.E2E_PATIENT_EMAIL || 'patient@ncep.demo';
      password = process.env.E2E_PATIENT_PASSWORD || 'password';
      break;
    case 'doctor':
      email = process.env.E2E_DOCTOR_EMAIL || 'doctor@ncep.demo';
      password = process.env.E2E_DOCTOR_PASSWORD || 'password';
      break;
    case 'admin':
      email = process.env.E2E_ADMIN_EMAIL || 'admin@ncep.demo';
      password = process.env.E2E_ADMIN_PASSWORD || 'password';
      break;
    case 'superadmin':
      email = process.env.E2E_SUPERADMIN_EMAIL || 'superadmin@ncep.demo';
      password = process.env.E2E_SUPERADMIN_PASSWORD || 'password';
      break;
  }

  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  
  // Submit the form
  await page.click('button[type="submit"]');

  // Verify redirection is complete by checking for the dashboard element
  await page.waitForURL(new RegExp(`/${role}/dashboard`), { timeout: 10000 });
  await page.waitForLoadState('networkidle');
  
  // Wait for the auth session to persist
  await page.waitForTimeout(1000);
}

export async function getStorageStateForRole(page: Page, role: Role, path: string) {
  await loginAs(page, role);
  await page.context().storageState({ path });
}

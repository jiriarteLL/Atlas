// Smoke E2E: Maestro portal login + navegación post-login.
// Corre dentro del container mcr.microsoft.com/playwright:v1.49.0-jammy
// conectado a la red maestro-network → resuelve hostnames maestro-portal y maestro-api.

import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const PORTAL = process.env.PORTAL_URL || 'http://maestro-portal:8081';
const API    = process.env.API_URL    || 'http://maestro-api:8080';
// Defaults alineados con DemoPoSeeder (DEC-025). Override via env vars si se siembra otra cosa.
const EMAIL  = process.env.E2E_EMAIL || 'po@maestro.local';
const PASS   = process.env.E2E_PASS  || 'MaestroPO2026!';
const OUT    = '/out';

if (!EMAIL || !PASS) {
  console.error('[FATAL] E2E_EMAIL y E2E_PASS son obligatorios.');
  process.exit(2);
}

mkdirSync(OUT, { recursive: true });

const results = [];
const step = (name, status, data = {}) => {
  results.push({ name, status, ...data });
  console.log(`[${status.toUpperCase()}] ${name}${data.detail ? ' — ' + data.detail : ''}`);
};

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext();

// El portal usa VITE_API_BASE_URL=/api (relativo) y Vite proxy /api -> maestro-api:8080.
// No hace falta interceptar requests: todo va a través de maestro-portal:8081.

const page = await ctx.newPage();
const consoleErrors = [];
page.on('pageerror', (e) => consoleErrors.push(String(e)));
page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()));

try {
  // 1. Portal carga
  const resp = await page.goto(PORTAL + '/login', { waitUntil: 'networkidle', timeout: 15000 });
  step('portal_loads', resp?.ok() ? 'pass' : 'fail', { status: resp?.status() });
  await page.screenshot({ path: `${OUT}/01_login_page.png`, fullPage: true });

  // 2. Campos visibles
  const emailVisible = await page.locator('input#email').isVisible();
  const passVisible  = await page.locator('input#password').isVisible();
  step('login_form_visible', (emailVisible && passVisible) ? 'pass' : 'fail',
       { detail: `email=${emailVisible} password=${passVisible}` });

  // 3. Rellenar y submit
  await page.fill('input#email', EMAIL);
  await page.fill('input#password', PASS);
  await page.screenshot({ path: `${OUT}/02_filled.png`, fullPage: true });

  const loginRespPromise = page.waitForResponse(
    (r) => r.url().includes('/api/auth/login'),
    { timeout: 15000 }
  );
  await page.click('button[type=submit]');
  const loginResp = await loginRespPromise;
  step('login_post', loginResp.status() === 200 ? 'pass' : 'fail',
       { status: loginResp.status(), url: loginResp.url() });

  // 4. Navegó a "/" y obtuvo token
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 10000 }).catch(() => {});
  const currentUrl = page.url();
  const token = await page.evaluate(() => localStorage.getItem('maestro.access_token'));
  step('post_login_redirect', !currentUrl.endsWith('/login') ? 'pass' : 'fail', { detail: currentUrl });
  step('token_stored', (token && token.length > 100) ? 'pass' : 'fail', { detail: `len=${token?.length ?? 0}` });
  await page.screenshot({ path: `${OUT}/03_after_login.png`, fullPage: true });

  // 5. Ir a una pantalla admin (Usuarios)
  await page.goto(PORTAL + '/admin/users', { waitUntil: 'networkidle' }).catch(() => {});
  const bodyText = await page.locator('body').innerText();
  step('admin_users_reachable', bodyText.toLowerCase().includes('admin maestro') ? 'pass' : 'warn',
       { detail: bodyText.slice(0, 200).replace(/\n/g, ' | ') });
  await page.screenshot({ path: `${OUT}/04_admin_users.png`, fullPage: true });

  // 6. Logout
  await page.goto(PORTAL + '/login').catch(() => {});
  await page.screenshot({ path: `${OUT}/05_back_to_login.png`, fullPage: true });

  step('no_console_errors', consoleErrors.length === 0 ? 'pass' : 'warn',
       { detail: consoleErrors.slice(0, 3).join(' || ') });
} catch (err) {
  step('fatal', 'fail', { detail: String(err).slice(0, 300) });
  try { await page.screenshot({ path: `${OUT}/ERROR.png`, fullPage: true }); } catch {}
} finally {
  await browser.close();
}

writeFileSync(`${OUT}/results.json`, JSON.stringify(results, null, 2));
const failed = results.filter((r) => r.status === 'fail').length;
console.log(`\n=== RESUMEN: ${results.length} steps, ${failed} fail ===`);
process.exit(failed > 0 ? 1 : 0);

// Optional UI verification with Playwright available through NODE_PATH or local packages.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    await page.goto('http://127.0.0.1:8080');
    await page.getByLabel('Identifiant', { exact: true }).fill('operator');
    await page.getByLabel('Mot de passe', { exact: true }).fill(
      fs.readFileSync(path.join(process.cwd(), '.secrets/demo_password'), 'utf8').trim(),
    );
    await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
    await page.getByRole('heading', { name: 'Supervision et reprise autonome' }).waitFor();
    await page.getByText('Service rétabli et paiement vérifié', { exact: true }).first().waitFor();
    fs.mkdirSync('output/evidence', { recursive: true });
    await page.screenshot({ path: 'output/evidence/dashboard.png', fullPage: true });
    await page.getByRole('button', { name: 'Consulter les procédures' }).click();
    await page.getByText(/Réponse RAG/).waitFor({ timeout: 100000 });
    if (errors.length) throw new Error(errors.join('\n'));
    await page.screenshot({ path: 'output/evidence/dashboard-rag.png', fullPage: true });
    fs.writeFileSync('output/evidence/browser.json', JSON.stringify({
      passed: true, scope: 'Chromium headless, login, incidents and RAG response', errors,
    }, null, 2));
    console.log('PASS: browser login, recovered incident, RAG response, no JavaScript errors.');
  } finally { await browser.close(); }
})().catch(e => { console.error(e.message); process.exitCode = 1; });

// UI smoke test: Indore heatwave -> approve -> MP challan, and a second visitor sees none of it.
// Usage: NODE_PATH=/path/to/node_modules node scripts/smoke_ui.cjs [base_url] [screenshot_dir]
const { chromium } = require('playwright');

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const SHOTS = process.argv[3] || '';

function check(cond, msg) {
  if (!cond) { console.error('FAIL:', msg); process.exitCode = 1; throw new Error(msg); }
  console.log('ok  -', msg);
}

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  try {
    const a = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await a.newPage();
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    page.on('dialog', d => d.accept());
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });

    await page.click('#btnRegionIdr');
    await page.click('#scenarioHeat');
    await page.waitForTimeout(2500);
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/proj_indore_heat_dashboard.png` });

    const approve = page.locator('button', { hasText: 'Approve & Reserve Stock' }).first();
    await approve.waitFor({ timeout: 15000 });
    await approve.scrollIntoViewIfNeeded();
    await approve.click();
    await page.locator('#challanModal:not(.hidden)').waitFor({ timeout: 15000 });
    check((await page.textContent('#challanStateBadge')).trim() === 'MP', 'challan state badge is MP');
    check((await page.textContent('#modalChallanId')).startsWith('CHALLAN-MP-'), 'challan id is an MP challan');
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/proj_indore_challan.png` });

    await page.click('#challanModal button:has-text("Close"), #challanModal [onclick*="closeModal"]').catch(() => page.evaluate(() => closeModal()));
    await page.waitForFunction(() => document.getElementById('valueTransfers').textContent.trim() === '1', null, { timeout: 10000 });
    check(!/^₹0$/.test((await page.textContent('#valueSavedInr')).trim()), 'rupees panel shows a saving after the approval');
    if (SHOTS) { await page.locator('#valuePanel').scrollIntoViewIfNeeded(); await page.screenshot({ path: `${SHOTS}/proj_indore_value_panel.png` }); }

    const logA = await page.evaluate(() => fetch('/api/audit-log?region=indore&limit=100').then(r => r.json()));
    check(logA.some(e => e.event_type.includes('APPROV') || e.event_type.includes('CONSIGNMENT')), 'visitor A audit chain records the approval');
    const verifyA = await page.evaluate(() => fetch('/api/audit-log/verify?region=indore').then(r => r.json()));
    check(verifyA.valid === true, 'visitor A audit chain verifies');

    const b = await browser.newContext();
    const pageB = await b.newPage();
    pageB.on('pageerror', e => errors.push('B: ' + String(e)));
    await pageB.goto(BASE + '/', { waitUntil: 'networkidle' });
    const logB = await pageB.evaluate(() => fetch('/api/audit-log?region=indore&limit=100').then(r => r.json()));
    check(logB.length === 1 && logB[0].event_type === 'GENESIS', 'visitor B audit chain is untouched');
    const recsB = await pageB.evaluate(() => fetch('/api/recommendations?region=indore&scenario=heat').then(r => r.json()));
    check(recsB.length > 0 && recsB.every(r => r.status !== 'APPROVED'), 'visitor B sees no approvals');
    // A visitor who never picks Conditions (no ?scenario=) must not leak approvals either
    const cA = await a.newPage();
    await cA.goto(BASE + '/api/health');
    const plainA = await cA.evaluate(() => fetch('/api/recommendations?region=lucknow').then(r => r.json()));
    const ok = await cA.evaluate(id => fetch('/api/approve-transfer', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({recommendation_id: id})}).then(r => r.status), plainA[0].id);
    check(ok === 200, 'visitor A approves with no Conditions picked');
    const plainB = await pageB.evaluate(() => fetch('/api/recommendations?region=lucknow').then(r => r.json()));
    check(plainB.every(r => r.status !== 'APPROVED'), 'visitor B (no Conditions) sees none of A\'s approvals');

    check(errors.length === 0, 'no console errors' + (errors.length ? ': ' + errors.join(' | ') : ''));
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e.message); process.exitCode = 1; });

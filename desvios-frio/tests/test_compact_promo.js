const { chromium } = require('playwright-core');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  const rawData = JSON.parse(fs.readFileSync(__dirname + '/dashboard_data.json', 'utf8'));
  const seenSkus = new Set();
  rawData.promo_rows.forEach(p => { if (p.semIni != null && p.semFin != null) seenSkus.add(p.sku); });
  const targetSku = String(Array.from(seenSkus)[0]);

  await page.evaluate((sku) => {
    const sel = document.getElementById('skuSelect');
    const opt = Array.from(sel.options).find(o => o.value === sku);
    if (opt) { sel.value = sku; sel.dispatchEvent(new Event('change')); }
  }, targetSku);
  await page.waitForTimeout(400);

  const bandCountWeekly = await page.$$eval('#lineChart rect[stroke-dasharray="2,2"]', els => els.length);
  console.log('promo bands (weekly, SKU filtered):', bandCountWeekly);
  const chipCountWeekly = await page.$$eval('#promoInlineSummary .promo-chip', els => els.length);
  console.log('promo chips (weekly):', chipCountWeekly);

  await page.click('#compactMonthBtn');
  await page.waitForTimeout(400);

  const bandCountMonthly = await page.$$eval('#lineChart rect[stroke-dasharray="2,2"]', els => els.length);
  console.log('promo bands (monthly, SKU filtered, expect >0):', bandCountMonthly);
  const chipCountMonthly = await page.$$eval('#promoInlineSummary .promo-chip', els => els.length);
  console.log('promo chips (monthly, expect same as weekly):', chipCountMonthly);

  console.log('errors:', errors);
  await browser.close();
})();

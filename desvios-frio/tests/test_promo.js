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

  // --- promo table exists and has rows (no SKU filter = all promos) ---
  const rowCountText = await page.$eval('#promoRowCount', el => el.textContent);
  console.log('promo row count (no filter):', rowCountText);
  const bodyRowsAll = await page.$$eval('#promoTableBody tr', els => els.length);
  console.log('rendered rows (no filter):', bodyRowsAll);
  const kpiText = await page.$eval('#promoKpiRow', el => el.textContent);
  console.log('promo KPI row text:', kpiText.replace(/\s+/g, ' ').trim());

  // --- filter by status ---
  await page.selectOption('#promoStatusSelect', 'Aceptado');
  await page.waitForTimeout(200);
  const rowCountAceptado = await page.$eval('#promoRowCount', el => el.textContent);
  console.log('promo row count (Aceptado only):', rowCountAceptado);
  await page.selectOption('#promoStatusSelect', '');

  // --- sort by Efecto Sell Out ---
  await page.click('#promoTable th[data-key="effSellout"]');
  await page.waitForTimeout(200);
  const firstRowEff = await page.$eval('#promoTableBody tr:first-child', el => el.children[8].textContent);
  console.log('top row effSellout after sort (desc):', firstRowEff);

  // --- filter to a specific SKU that has promos, check chart bands appear ---
  const rawData = JSON.parse(fs.readFileSync(__dirname + '/dashboard_data.json', 'utf8'));
  const seenSkus = new Set();
  rawData.promo_rows.forEach(p => { if (p.semIni != null && p.semFin != null) seenSkus.add(p.sku); });
  const promoSkus = Array.from(seenSkus).slice(0, 5);
  console.log('sample promo SKUs with resolved weeks:', promoSkus);

  if (promoSkus.length) {
    const targetSku = String(promoSkus[0]);
    // reset cascade selects first
    await page.selectOption('#catSelect', { index: 0 }).catch(() => {});
    await page.selectOption('#skuSelect', targetSku).catch(async () => {
      // skuSelect may be cascade-filtered; try setting value directly via evaluate
      await page.evaluate((sku) => {
        const sel = document.getElementById('skuSelect');
        const opt = Array.from(sel.options).find(o => o.value === sku);
        if (opt) { sel.value = sku; sel.dispatchEvent(new Event('change')); }
      }, targetSku);
    });
    await page.waitForTimeout(400);
    const skuSelectValue = await page.$eval('#skuSelect', el => el.value);
    console.log('skuSelect value after selecting promo SKU:', skuSelectValue);

    const bandCount = await page.$$eval('#lineChart rect[stroke-dasharray="2,2"]', els => els.length);
    console.log('promo bands drawn on chart for filtered SKU:', bandCount);
    const promoLabelCount = await page.$$eval('#lineChart text', els => els.filter(e => e.textContent.startsWith('PROMO')).length);
    console.log('PROMO labels on chart:', promoLabelCount);

    const filteredRowCount = await page.$eval('#promoRowCount', el => el.textContent);
    console.log('promo table row count for filtered SKU:', filteredRowCount);
  }

  console.log('errors:', errors);
  await browser.close();
})();

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

  // --- promo calendar panel starts hidden ---
  const panelDisplayBefore = await page.$eval('#promoPanel', el => getComputedStyle(el).display);
  console.log('promo panel display before toggle (expect none):', panelDisplayBefore);
  const inlineSummaryBefore = await page.$eval('#promoInlineSummary', el => getComputedStyle(el).display);
  console.log('inline promo summary display with no SKU filter (expect none):', inlineSummaryBefore);

  // --- open the panel via the toggle button ---
  await page.click('#togglePromoPanelBtn');
  await page.waitForTimeout(300);
  const panelDisplayAfter = await page.$eval('#promoPanel', el => getComputedStyle(el).display);
  console.log('promo panel display after toggle (expect flex/block, not none):', panelDisplayAfter);
  const btnLabel = await page.$eval('#togglePromoPanelBtn', el => el.textContent);
  console.log('toggle button label after opening:', btnLabel);

  const rowCountText = await page.$eval('#promoRowCount', el => el.textContent);
  console.log('promo row count (no filter):', rowCountText);
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

  // --- close the panel again ---
  await page.click('#togglePromoPanelBtn');
  await page.waitForTimeout(200);
  const panelDisplayClosed = await page.$eval('#promoPanel', el => getComputedStyle(el).display);
  console.log('promo panel display after closing again (expect none):', panelDisplayClosed);

  // --- filter to a specific SKU that has promos: chart bands + inline chips should appear ---
  const rawData = JSON.parse(fs.readFileSync(__dirname + '/dashboard_data.json', 'utf8'));
  const seenSkus = new Set();
  rawData.promo_rows.forEach(p => { if (p.semIni != null && p.semFin != null) seenSkus.add(p.sku); });
  const promoSkus = Array.from(seenSkus).slice(0, 5);
  console.log('sample promo SKUs with resolved weeks:', promoSkus);

  if (promoSkus.length) {
    const targetSku = String(promoSkus[0]);
    await page.selectOption('#catSelect', { index: 0 }).catch(() => {});
    await page.evaluate((sku) => {
      const sel = document.getElementById('skuSelect');
      const opt = Array.from(sel.options).find(o => o.value === sku);
      if (opt) { sel.value = sku; sel.dispatchEvent(new Event('change')); }
    }, targetSku);
    await page.waitForTimeout(400);
    const skuSelectValue = await page.$eval('#skuSelect', el => el.value);
    console.log('skuSelect value after selecting promo SKU:', skuSelectValue);

    const bandCount = await page.$$eval('#lineChart rect[stroke-dasharray="2,2"]', els => els.length);
    console.log('promo bands drawn on chart for filtered SKU:', bandCount);
    const promoLabelCount = await page.$$eval('#lineChart text', els => els.filter(e => e.textContent.startsWith('PROMO')).length);
    console.log('PROMO labels on chart:', promoLabelCount);

    const bandTitle = await page.$eval('#lineChart rect[stroke-dasharray="2,2"] title', el => el.textContent).catch(() => null);
    console.log('first band tooltip (should include Efecto Sell Out/In):', bandTitle);

    const inlineSummaryDisplay = await page.$eval('#promoInlineSummary', el => getComputedStyle(el).display);
    console.log('inline promo summary display with SKU filtered (expect flex):', inlineSummaryDisplay);
    const chipCount = await page.$$eval('#promoInlineSummary .promo-chip', els => els.length);
    console.log('inline promo chips rendered:', chipCount);
    const firstChipText = await page.$eval('#promoInlineSummary .promo-chip', el => el.textContent).catch(() => null);
    console.log('first chip text:', firstChipText);

    // panel should STILL be hidden by default even with a SKU filtered
    const panelStillHidden = await page.$eval('#promoPanel', el => getComputedStyle(el).display);
    console.log('promo panel display with SKU filtered, panel not opened (expect none):', panelStillHidden);

    // clicking "+N más" (if present) should open the full panel
    const moreBtnExists = await page.$('#promoInlineSummary .promo-chip-more');
    if (moreBtnExists) {
      await page.click('#promoInlineSummary .promo-chip-more');
      await page.waitForTimeout(400);
      const panelAfterMoreClick = await page.$eval('#promoPanel', el => getComputedStyle(el).display);
      console.log('promo panel display after clicking "+N más" (expect not none):', panelAfterMoreClick);
    } else {
      console.log('no "+N más" button (few enough promos to fit) — skipping that check');
    }
  }

  console.log('errors:', errors);
  await browser.close();
})();

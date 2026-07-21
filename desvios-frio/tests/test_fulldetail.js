const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const titles = await page.$$eval('.panel-title', els => els.map(e => e.textContent));
  console.log('panel order:\n' + titles.join('\n'));

  // No filter: should be capped and show a warning
  const rowCountNoFilter = await page.$eval('#fullDetailRowCount', el => el.textContent);
  console.log('row count (no filter):', rowCountNoFilter);
  const kpisNoFilter = await page.$$eval('#fullDetailKpiRow .kpi', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('kpis (no filter):', kpisNoFilter);
  const rowsRenderedNoFilter = await page.$$eval('#fullDetailTableBody tr', trs => trs.length);
  console.log('rows rendered (no filter, should be capped at 1500):', rowsRenderedNoFilter);

  // Filter down to a single SKU
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(200);
  const skuOpts = await page.$$eval('#skuSelect option', els => els.map(e => e.value).filter(Boolean));
  console.log('sku options for category:', skuOpts.slice(0,5));
  if (skuOpts.length) {
    await page.selectOption('#skuSelect', skuOpts[0]);
    await page.waitForTimeout(300);
    const rowCountSku = await page.$eval('#fullDetailRowCount', el => el.textContent);
    console.log('row count (1 SKU):', rowCountSku);
    const firstRows = await page.$$eval('#fullDetailTableBody tr', trs => trs.slice(0,3).map(tr => tr.textContent.replace(/\s+/g,' ').trim()));
    console.log('first rows (1 sku):\n' + firstRows.join('\n'));
  }

  // reset then test sort click
  await page.click('#resetBtn');
  await page.waitForTimeout(300);
  await page.click('#fullDetailTable th[data-key="fcst"]');
  await page.waitForTimeout(200);
  const afterSort = await page.$$eval('#fullDetailTableBody tr', trs => trs.slice(0,3).map(tr => tr.textContent.replace(/\s+/g,' ').trim()));
  console.log('after sort by fcst desc:\n' + afterSort.join('\n'));

  // test with weeksRangeSelect narrowed
  await page.selectOption('#weeksRangeSelect', '8');
  await page.waitForTimeout(300);
  const rowCount8w = await page.$eval('#fullDetailRowCount', el => el.textContent);
  console.log('row count (last 8 weeks, no other filter):', rowCount8w);

  console.log('errors:', errors);
  await browser.close();
})();

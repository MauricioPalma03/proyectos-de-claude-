const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const mesOpts = await page.$$eval('#riskMesSelect option', els => els.map(e => e.textContent));
  console.log('mes options count:', mesOpts.length, 'last:', mesOpts[mesOpts.length-1]);
  const defaultVal = await page.$eval('#riskMesSelect', el => el.value);
  console.log('default selected index:', defaultVal, '-> should be last month');

  const kpis = await page.$$eval('#riskKpiRow .kpi', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('KPI tiles (default, no filter):\n' + kpis.join('\n'));

  // change month to a mid-year one with likely YoY data (e.g. index for "Julio 2025")
  const julIdx = await page.$$eval('#riskMesSelect option', els => els.findIndex(e => e.textContent === 'Julio 2025'));
  console.log('Julio 2025 option index (value):', julIdx);
  await page.selectOption('#riskMesSelect', String(julIdx));
  await page.waitForTimeout(200);
  const kpisJul25 = await page.$$eval('#riskKpiRow .kpi', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('KPI tiles (Julio 2025 selected):\n' + kpisJul25.join('\n'));

  // back to default, apply category filter
  await page.selectOption('#riskMesSelect', String(mesOpts.length - 1));
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(300);
  const kpisFiltered = await page.$$eval('#riskKpiRow .kpi', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('KPI tiles (category filtered):\n' + kpisFiltered.join('\n'));

  console.log('errors:', errors);
  await browser.close();
})();

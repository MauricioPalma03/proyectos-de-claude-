const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const kpis = await page.$$eval('#riskKpiRow .kpi', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('risk KPI tiles (no filter):', kpis);

  const liqSub = await page.$eval('#liqHistSub', el => el.textContent);
  console.log('liqHistSub (no filter):', liqSub);

  const barCount = await page.$$eval('#liqHistChart rect', els => els.length);
  console.log('liqHist bar count:', barCount);

  // apply a category filter and re-check
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(300);
  const kpisFiltered = await page.$$eval('#riskKpiRow .kpi', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('risk KPI tiles (1 category filtered):', kpisFiltered);
  const liqSubFiltered = await page.$eval('#liqHistSub', el => el.textContent);
  console.log('liqHistSub (filtered):', liqSubFiltered);

  console.log('errors:', errors);
  await browser.close();
})();

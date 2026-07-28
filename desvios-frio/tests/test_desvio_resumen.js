const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  const semanaValue = await page.$eval('#desvioSemanaSelect', el => el.value);
  console.log('default semana selected (should be last CLOSED week):', semanaValue);

  const kpiText = await page.$eval('#desvioHeadlineKpis', el => el.innerText.replace(/\s+/g, ' ').trim());
  console.log('headline KPIs:', kpiText);

  const marcaTileCount = await page.$$eval('#desvioMarcaGrid .mini-tile', els => els.length);
  const subcatTileCount = await page.$$eval('#desvioSubcatGrid .mini-tile', els => els.length);
  const cadenaTileCount = await page.$$eval('#desvioCadenaGrid .mini-tile', els => els.length);
  console.log('tile counts -> marca:', marcaTileCount, '| subcat:', subcatTileCount, '| cadena:', cadenaTileCount);

  const firstMarcaTile = await page.$eval('#desvioMarcaGrid .mini-tile', el => el.innerText.replace(/\s+/g, ' ')).catch(() => null);
  console.log('first (worst) marca tile:', firstMarcaTile);

  // change the semana selector and confirm it re-renders
  await page.selectOption('#desvioSemanaSelect', { index: 5 });
  await page.waitForTimeout(300);
  const kpiTextAfter = await page.$eval('#desvioHeadlineKpis', el => el.innerText.replace(/\s+/g, ' ').trim());
  console.log('headline KPIs after changing semana:', kpiTextAfter);
  console.log('changed:', kpiText !== kpiTextAfter);

  // apply a category filter and confirm the panel updates too
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(300);
  const kpiTextFiltered = await page.$eval('#desvioHeadlineKpis', el => el.innerText.replace(/\s+/g, ' ').trim());
  console.log('headline KPIs after category filter:', kpiTextFiltered);

  // confirm old panels/ids are gone
  const oldPanelGone1 = await page.$('#cadenaReviewList');
  const oldPanelGone2 = await page.$('#fullDetailTable');
  console.log('old cadenaReviewList element gone:', oldPanelGone1 === null);
  console.log('old fullDetailTable element gone:', oldPanelGone2 === null);

  // confirm "Todos los SKU" and "Resumen Ejecutivo" panels still work (spot check)
  const skuTableRows = await page.$$eval('#tableBody tr', els => els.length);
  console.log('Todos los SKU rows still rendering:', skuTableRows > 0);

  console.log('errors:', errors);
  await browser.close();
})();

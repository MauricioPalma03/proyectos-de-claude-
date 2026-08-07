const { chromium } = require('playwright-core');

async function openCadenaPanel(page) {
  const isOpen = await page.$eval('#cadenaFilterPanel', el => getComputedStyle(el).display !== 'none');
  if (!isOpen) await page.click('#cadenaFilterBtn');
  await page.waitForTimeout(200);
}

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  // --- default: "Todas las cadenas" ---
  const btnLabelDefault = await page.$eval('#cadenaFilterBtn', el => el.textContent);
  console.log('default label:', btnLabelDefault);
  const kpiDefault = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('KPI row (default, all cadenas):', kpiDefault);

  // --- open panel, uncheck Walmart -> "Todas menos Walmart" ---
  await page.click('#cadenaFilterBtn');
  await page.waitForTimeout(200);
  await page.click('[data-cadena="Walmart"]');
  await page.waitForTimeout(300);
  const btnLabelExclWalmart = await page.$eval('#cadenaFilterBtn', el => el.textContent);
  console.log('label after unchecking Walmart:', btnLabelExclWalmart);
  const kpiExclWalmart = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('KPI row (excl. Walmart):', kpiExclWalmart);

  // --- also uncheck "Industrial Y Food Service" -> "Todas menos Walmart, Industrial Y Food Service" ---
  await page.click('[data-cadena="Industrial Y Food Service"]');
  await page.waitForTimeout(300);
  const btnLabelExcl2 = await page.$eval('#cadenaFilterBtn', el => el.textContent);
  console.log('label after unchecking Walmart + Industrial:', btnLabelExcl2);
  const kpiExcl2 = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('KPI row (excl. 2 cadenas):', kpiExcl2);

  // --- filter tag reflects the cadena selection ---
  const filterTag = await page.$eval('#filterTag', el => el.textContent);
  console.log('filterTag text:', filterTag);

  // --- verify chart also updates (fewer tons than default) ---
  const chartStatSolicitado = await page.$eval('#statAvgSolicitado', el => el.textContent);
  console.log('Prom. Solicitado (excl. 2 cadenas):', chartStatSolicitado);

  // --- "Todos los SKU" table still populates with aggregated multi-cadena rows ---
  const skuRowCount = await page.$eval('#rowCount', el => el.textContent);
  console.log('Todos los SKU row count (excl. 2 cadenas):', skuRowCount);
  const firstRowFcst = await page.$eval('#tableBody tr:first-child td:nth-child(5)', el => el.textContent).catch(() => null);
  console.log('first row FCST cell (should be a number, not NaN):', firstRowFcst);

  // --- click "Ninguna" -> 0 cadenas selected, no data ---
  await openCadenaPanel(page);
  await page.click('#cadenaSelectNoneBtn');
  await page.waitForTimeout(300);
  const btnLabelNone = await page.$eval('#cadenaFilterBtn', el => el.textContent);
  console.log('label after "Ninguna":', btnLabelNone);
  const kpiNone = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('KPI row (ninguna cadena, expect all zeros):', kpiNone);

  // --- click "Todas" -> back to default ---
  await page.click('#cadenaSelectAllBtn');
  await page.waitForTimeout(300);
  const btnLabelBack = await page.$eval('#cadenaFilterBtn', el => el.textContent);
  console.log('label after "Todas":', btnLabelBack);
  const kpiBack = await page.$eval('#kpiRow', el => el.innerText.replace(/\n/g, ' | '));
  console.log('KPI row (back to all, should match original):', kpiBack, '| matches original:', kpiBack === kpiDefault);

  // --- Resumen de Desvío panel also respects multi-cadena (spot check via Por Cadena grid) ---
  await openCadenaPanel(page);
  await page.click('[data-cadena="Walmart"]');
  await page.waitForTimeout(300);
  const cadenaTileNames = await page.$$eval('#desvioCadenaGrid .mini-tile .mt-name', els => els.map(e => e.textContent));
  console.log('Resumen de Desvío -> Por Cadena tiles shown (Walmart excluded, should NOT include Walmart):', cadenaTileNames);

  // reset to all for cleanliness
  await openCadenaPanel(page);
  await page.click('#cadenaSelectAllBtn');

  console.log('errors:', errors);
  await browser.close();
})();

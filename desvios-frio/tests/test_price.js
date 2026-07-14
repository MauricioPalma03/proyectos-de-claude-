const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const priceDefault = await page.$eval('#statAvgPrecio', el => el.textContent);
  console.log('precio promedio (todo histórico):', priceDefault);

  // filter to a specific SKU to check per-SKU price
  await page.fill('#searchInput', '30001042');
  await page.waitForTimeout(400);
  const priceAfterSearch = await page.$eval('#statAvgPrecio', el => el.textContent);
  console.log('precio promedio (SKU 30001042):', priceAfterSearch);
  await page.fill('#searchInput', '');
  await page.waitForTimeout(300);

  // test month window: últimas 8 semanas
  await page.selectOption('#weeksRangeSelect', '8');
  await page.waitForTimeout(400);
  const priceAfter8w = await page.$eval('#statAvgPrecio', el => el.textContent);
  console.log('precio promedio (últimas 8 semanas):', priceAfter8w);

  // test category filter
  await page.selectOption('#weeksRangeSelect', '0');
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(400);
  const priceAfterCat = await page.$eval('#statAvgPrecio', el => el.textContent);
  console.log('precio promedio (categoría filtrada):', priceAfterCat);

  await page.screenshot({ path: 'screenshot_price_tile.png', clip: { x: 100, y: 330, width: 1250, height: 420 } });

  console.log('errors:', errors);
  await browser.close();
})();

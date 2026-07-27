const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const ids = ['statWowSellout2', 'statWowSellout', 'statWowDes2', 'statWowDes'];
  for (const id of ids) {
    const val = await page.$eval('#' + id, el => el.textContent);
    const title = await page.$eval('#' + id + 'Box', el => el.title);
    console.log(`${id}: ${val} | title: ${title}`);
  }

  // filter to 1 SKU
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(200);
  const skuOpts = await page.$$eval('#skuSelect option', els => els.map(e => e.value).filter(Boolean));
  await page.selectOption('#skuSelect', skuOpts[0]);
  await page.waitForTimeout(300);
  console.log('--- 1 SKU filtered ---');
  for (const id of ids) {
    const val = await page.$eval('#' + id, el => el.textContent);
    console.log(`${id}: ${val}`);
  }

  console.log('errors:', errors);
  await browser.close();
})();

const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const val = await page.$eval('#statWowSellout', el => el.textContent);
  const title = await page.$eval('#statWowSelloutBox', el => el.title);
  console.log('WoW Sell Out (no filter):', val, '| title:', title);

  // filter to a single SKU with likely sellout data
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(200);
  const skuOpts = await page.$$eval('#skuSelect option', els => els.map(e => e.value).filter(Boolean));
  await page.selectOption('#skuSelect', skuOpts[0]);
  await page.waitForTimeout(300);
  const valSku = await page.$eval('#statWowSellout', el => el.textContent);
  const titleSku = await page.$eval('#statWowSelloutBox', el => el.title);
  console.log('WoW Sell Out (1 SKU filtered):', valSku, '| title:', titleSku);

  // check it stays stable when narrowing the weeksRangeSelect display window (shouldn't change,
  // since it's based on the full underlying series, not the display window)
  await page.click('#resetBtn');
  await page.waitForTimeout(200);
  const valBefore = await page.$eval('#statWowSellout', el => el.textContent);
  await page.selectOption('#weeksRangeSelect', '8');
  await page.waitForTimeout(300);
  const valAfter = await page.$eval('#statWowSellout', el => el.textContent);
  console.log('WoW Sell Out before narrowing range:', valBefore, '| after (últimas 8 semanas):', valAfter, '(should be same)');

  console.log('errors:', errors);
  await browser.close();
})();

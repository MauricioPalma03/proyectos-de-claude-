const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  const subtitle = await page.$eval('#subtitleText', el => el.textContent);
  console.log('subtitle (SKU count):', subtitle);

  for (const sku of ['30001828', '30001829', '30002286']) {
    const found = await page.evaluate((s) => {
      const sel = document.getElementById('skuSelect');
      return Array.from(sel.options).some(o => o.value === s);
    }, sku);
    console.log(`SKU ${sku} selectable in skuSelect:`, found);
  }

  console.log('errors:', errors);
  await browser.close();
})();

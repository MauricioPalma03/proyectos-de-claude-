const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const order = await page.$$eval('.panel-title', els => els.map(e => e.textContent));
  console.log('panel order:\n' + order.join('\n'));

  // sanity: interact with weeksRangeSelect (now inside the moved panel) to confirm still works
  await page.selectOption('#weeksRangeSelect', 'w2');
  await page.waitForTimeout(300);
  const pathD = await page.$eval('#lineChart path', el => (el.getAttribute('d').match(/[ML]/g)||[]).length);
  console.log('points after selecting w2:', pathD);

  console.log('errors:', errors);
  await browser.close();
})();

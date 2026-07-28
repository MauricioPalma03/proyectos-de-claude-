const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  console.log('subtitle:', await page.$eval('#subtitleText', el => el.textContent));
  console.log('riskSub (stock snapshot date):', await page.$eval('#riskSub', el => el.textContent));
  console.log('kpiRow:', (await page.$eval('#kpiRow', el => el.innerText)).replace(/\n/g, ' | '));

  await browser.close();
  console.log('errors:', errors);
})();

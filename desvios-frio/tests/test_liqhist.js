const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  await page.locator('#liqHistChart').scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const sub = await page.$eval('#liqHistSub', el => el.textContent);
  console.log('liq hist sub:', sub);

  const barCount = await page.$$eval('#liqHistChart rect', els => els.length);
  console.log('bar count (expect ~19 months):', barCount);

  const box = await page.locator('#liqHistChart').boundingBox();
  await page.mouse.move(box.x + box.width * 0.3, box.y + 100, { steps: 5 });
  await page.waitForTimeout(200);
  console.log('tooltip:\n', await page.$eval('#liqHistTooltip', el => el.innerText));

  await page.screenshot({ path: 'screenshot_liqhist.png', clip: { x: 100, y: 380, width: 1000, height: 350 } });

  // apply category filter and confirm it updates
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(400);
  const subAfter = await page.$eval('#liqHistSub', el => el.textContent);
  console.log('liq hist sub after category filter:', subAfter);

  console.log('errors:', errors);
  await browser.close();
})();

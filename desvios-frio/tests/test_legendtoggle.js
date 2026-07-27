const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const countBars = async () => page.$$eval('#lineChart rect[fill-opacity]', els => els.length);
  const countPaths = async () => page.$$eval('#lineChart path[stroke-dasharray], #lineChart path:not([stroke-dasharray])', els => els.length);

  const barsBefore = await countBars();
  console.log('bars before toggle (all visible):', barsBefore);

  // toggle off "quebrados"
  await page.click('[data-series="quebrados"]');
  await page.waitForTimeout(200);
  const offClass = await page.$eval('[data-series="quebrados"]', el => el.classList.contains('off'));
  console.log('quebrados legend has .off class:', offClass);
  const barsAfterQuebradosOff = await countBars();
  console.log('bars after hiding quebrados:', barsAfterQuebradosOff, '(should be ~1/3 less than', barsBefore, ')');

  // toggle off sellin (line)
  await page.click('[data-series="sellin"]');
  await page.waitForTimeout(200);
  const pathsAfterSellinOff = await page.$$eval('#lineChart path', els => els.map(p => p.getAttribute('stroke')));
  console.log('remaining line path strokes after hiding sellin:', pathsAfterSellinOff.length);

  // toggle off precio
  await page.click('[data-series="precio"]');
  await page.waitForTimeout(200);
  const priceLabelCount = await page.$$eval('#lineChart text', els => els.filter(e => e.textContent.startsWith('$')).length);
  console.log('price $ labels after hiding precio (should be 0):', priceLabelCount);

  // re-enable quebrados
  await page.click('[data-series="quebrados"]');
  await page.waitForTimeout(200);
  const barsReEnabled = await countBars();
  console.log('bars after re-enabling quebrados:', barsReEnabled);

  console.log('errors:', errors);
  await browser.close();
})();

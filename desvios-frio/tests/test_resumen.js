const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  const titles = await page.$$eval('.panel-title', els => els.map(e => e.textContent));
  console.log('panel order:\n' + titles.join('\n'));

  const items = await page.$$eval('#resumenEjecutivoList > div', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('items count:', items.length);
  items.forEach((it, i) => console.log(`${i+1}. ${it}`));

  // apply a filter and confirm resumen stays unchanged (unfiltered by design)
  const before = items[0];
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(300);
  const itemsAfter = await page.$$eval('#resumenEjecutivoList > div', els => els.map(e => e.textContent.replace(/\s+/g,' ').trim()));
  console.log('unchanged after filter?', itemsAfter[0] === before);

  console.log('errors:', errors);
  await browser.close();
})();

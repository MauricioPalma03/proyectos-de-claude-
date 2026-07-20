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

  const sub = await page.$eval('#seasonalSub', el => el.textContent);
  console.log('sub:', sub);

  const rowCount = await page.$$eval('#seasonalTableBody tr', trs => trs.length);
  console.log('rows:', rowCount);

  const firstRows = await page.$$eval('#seasonalTableBody tr', trs => trs.slice(0, 5).map(tr => tr.textContent.replace(/\s+/g, ' ').trim()));
  console.log('first rows:\n' + firstRows.join('\n'));

  // sort by clicking "Salto %" header again (toggle) then a different header
  await page.click('#seasonalTable th[data-key="desPct"]');
  await page.waitForTimeout(200);
  const afterSortDesPct = await page.$$eval('#seasonalTableBody tr', trs => trs.slice(0, 3).map(tr => tr.textContent.replace(/\s+/g, ' ').trim()));
  console.log('after sort by desPct:\n' + afterSortDesPct.join('\n'));

  // test with a category filter applied
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(300);
  const rowsAfterFilter = await page.$$eval('#seasonalTableBody tr', trs => trs.length);
  const subAfterFilter = await page.$eval('#seasonalSub', el => el.textContent);
  console.log('rows after category filter:', rowsAfterFilter, '| sub:', subAfterFilter);

  console.log('errors:', errors);
  await browser.close();
})();

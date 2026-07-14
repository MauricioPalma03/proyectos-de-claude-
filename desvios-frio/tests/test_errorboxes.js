const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  // check initial: boxes wrap hidden
  const wrapDisplay1 = await page.$eval('#errorBoxesWrap', el => getComputedStyle(el).display);
  console.log('initial errorBoxesWrap display:', wrapDisplay1);

  // toggle error checkbox
  await page.check('#errorToggle');
  await page.waitForTimeout(500);
  const wrapDisplay2 = await page.$eval('#errorBoxesWrap', el => getComputedStyle(el).display);
  console.log('after check errorBoxesWrap display:', wrapDisplay2);

  const boxCount = await page.$$eval('#errorBoxesRow > div', els => els.length);
  console.log('box count:', boxCount);

  const firstBoxes = await page.$$eval('#errorBoxesRow > div', els => els.slice(0, 5).map(e => e.innerText.replace(/\n/g,' | ')));
  console.log('first boxes:', firstBoxes);

  // check chart height didn't blow up (no big empty space)
  const svgHeight = await page.$eval('#lineChart', el => el.getAttribute('height'));
  console.log('svg height with error checked:', svgHeight);

  // uncheck
  await page.uncheck('#errorToggle');
  await page.waitForTimeout(500);
  const wrapDisplay3 = await page.$eval('#errorBoxesWrap', el => getComputedStyle(el).display);
  const rowHtmlAfterUncheck = await page.$eval('#errorBoxesRow', el => el.innerHTML.length);
  console.log('after uncheck display:', wrapDisplay3, 'row html length:', rowHtmlAfterUncheck);

  // change filters and re-check toggle to verify wiring through applyGlobalFilter
  await page.check('#errorToggle');
  await page.selectOption('#catSelect', { index: 1 });
  await page.waitForTimeout(500);
  const boxCountAfterFilter = await page.$$eval('#errorBoxesRow > div', els => els.length);
  console.log('box count after category filter:', boxCountAfterFilter);

  // change weeksRangeSelect
  await page.selectOption('#weeksRangeSelect', '8');
  await page.waitForTimeout(500);
  const boxCountAfter8 = await page.$$eval('#errorBoxesRow > div', els => els.length);
  console.log('box count after last-8-weeks:', boxCountAfter8);

  await page.screenshot({ path: 'screenshot_errorboxes.png', fullPage: false });

  console.log('console/page errors:', errors);
  await browser.close();
})();

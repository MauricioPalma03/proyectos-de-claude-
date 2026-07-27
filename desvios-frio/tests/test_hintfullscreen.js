const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);
  await page.$eval('#weeklyPanel', el => el.scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(200);

  const getHitRectBox = async () => page.evaluate(() => {
    const svg = document.getElementById('lineChart');
    const rect = svg.querySelector('rect[fill="transparent"]');
    const b = rect.getBoundingClientRect();
    return { x: b.x, y: b.y, w: b.width, h: b.height };
  });

  // --- hint before/after enabling compare mode ---
  const hintBefore = await page.$eval('#toolHint', el => el.style.display);
  console.log('hint display before enabling:', hintBefore);
  await page.click('#compareModeBtn');
  await page.waitForTimeout(200);
  const hint1 = await page.$eval('#toolHint', el => el.textContent);
  console.log('hint after enabling compare mode:', hint1);

  let hb = await getHitRectBox();
  await page.mouse.click(hb.x + hb.w * 0.25, hb.y + hb.h * 0.4);
  await page.waitForTimeout(200);
  const hint2 = await page.$eval('#toolHint', el => el.textContent);
  console.log('hint after 1st click:', hint2);

  await page.mouse.click(hb.x + hb.w * 0.75, hb.y + hb.h * 0.4);
  await page.waitForTimeout(300);
  const hint3 = await page.$eval('#toolHint', el => el.textContent);
  console.log('hint after 2nd click:', hint3);
  const boxDisplay = await page.$eval('#compareResultBox', el => el.style.display);
  console.log('compareResultBox display:', boxDisplay);

  // switch to draw mode hint
  await page.click('#drawModeBtn');
  await page.waitForTimeout(200);
  const hint4 = await page.$eval('#toolHint', el => el.textContent);
  console.log('hint after enabling draw mode:', hint4);

  // turn off
  await page.click('#drawModeBtn');
  await page.waitForTimeout(200);
  const hintOff = await page.$eval('#toolHint', el => el.style.display);
  console.log('hint display after disabling all tools:', hintOff);

  // --- fullscreen chart height ---
  const svgHeightBefore = await page.$eval('#lineChart', el => el.getAttribute('height'));
  console.log('svg height before fullscreen:', svgHeightBefore);
  await page.click('#fullscreenBtn');
  await page.waitForTimeout(500);
  const svgHeightAfter = await page.$eval('#lineChart', el => el.getAttribute('height'));
  console.log('svg height in fullscreen (viewport 1000px tall):', svgHeightAfter);

  console.log('errors:', errors);
  await browser.close();
})();

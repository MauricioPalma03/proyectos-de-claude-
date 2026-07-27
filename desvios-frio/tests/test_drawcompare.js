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

  // --- Draw mode ---
  await page.click('#drawModeBtn');
  await page.waitForTimeout(200);
  const drawActive = await page.$eval('#drawModeBtn', el => el.classList.contains('active'));
  console.log('draw mode active:', drawActive);

  let hb = await getHitRectBox();
  const x1 = hb.x + hb.w * 0.3, y1 = hb.y + hb.h * 0.6;
  const x2 = hb.x + hb.w * 0.6, y2 = hb.y + hb.h * 0.3;
  await page.mouse.move(x1, y1);
  await page.mouse.down();
  await page.mouse.move((x1 + x2) / 2, (y1 + y2) / 2, { steps: 5 });
  await page.mouse.move(x2, y2, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  const lineCount = await page.$$eval('#lineChart line[stroke-width="2"]', els => els.length);
  console.log('freehand lines drawn:', lineCount);
  const clearBtnVisible = await page.$eval('#clearDrawingsBtn', el => el.style.display);
  console.log('clear drawings btn display:', clearBtnVisible);

  // second line
  hb = await getHitRectBox();
  await page.mouse.move(hb.x + hb.w * 0.1, hb.y + hb.h * 0.5);
  await page.mouse.down();
  await page.mouse.move(hb.x + hb.w * 0.25, hb.y + hb.h * 0.2, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  const lineCount2 = await page.$$eval('#lineChart line[stroke-width="2"]', els => els.length);
  console.log('freehand lines after 2nd draw:', lineCount2);

  // switching to compare mode should keep drawings, deactivate draw mode
  await page.click('#compareModeBtn');
  await page.waitForTimeout(200);
  const drawStillActive = await page.$eval('#drawModeBtn', el => el.classList.contains('active'));
  console.log('draw mode still active after switching to compare:', drawStillActive);
  const lineCountAfterSwitch = await page.$$eval('#lineChart line[stroke-width="2"]', els => els.length);
  console.log('freehand lines still visible after switching to compare mode:', lineCountAfterSwitch);

  // --- Compare mode with enriched table ---
  hb = await getHitRectBox();
  await page.mouse.click(hb.x + hb.w * 0.25, hb.y + hb.h * 0.4);
  await page.waitForTimeout(200);
  await page.mouse.click(hb.x + hb.w * 0.75, hb.y + hb.h * 0.4);
  await page.waitForTimeout(300);
  const boxText = await page.$eval('#compareResultBox', el => el.textContent.replace(/\s+/g, ' ').trim());
  console.log('compareResultBox text:\n' + boxText);
  const badgeCount = await page.$$eval('#lineChart rect[rx="4"]', els => els.length);
  console.log('on-chart % badge count:', badgeCount);

  // fullscreen: drawings + compare state should survive the redraw
  await page.click('#fullscreenBtn');
  await page.waitForTimeout(500);
  const lineCountFullscreen = await page.$$eval('#lineChart line[stroke-width="2"]', els => els.length);
  const badgeCountFullscreen = await page.$$eval('#lineChart rect[rx="4"]', els => els.length);
  console.log('freehand lines in fullscreen:', lineCountFullscreen, '| badges in fullscreen:', badgeCountFullscreen);
  await page.click('#fullscreenBtn');
  await page.waitForTimeout(300);

  // clear drawings
  await page.click('#clearDrawingsBtn');
  await page.waitForTimeout(200);
  const lineCountAfterClear = await page.$$eval('#lineChart line[stroke-width="2"]', els => els.length);
  console.log('freehand lines after clear:', lineCountAfterClear);

  // clear comparison
  await page.click('#clearCompareBtn');
  await page.waitForTimeout(200);
  const boxHiddenAfterClear = await page.$eval('#compareResultBox', el => el.style.display);
  console.log('compareResultBox display after clear:', boxHiddenAfterClear);

  console.log('errors:', errors);
  await browser.close();
})();

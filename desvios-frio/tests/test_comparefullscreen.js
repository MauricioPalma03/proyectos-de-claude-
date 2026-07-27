const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1200);

  // --- Fullscreen test ---
  await page.click('#fullscreenBtn');
  await page.waitForTimeout(400);
  const isFullscreen = await page.$eval('#weeklyPanel', el => el.classList.contains('panel-fullscreen'));
  console.log('fullscreen active:', isFullscreen);
  const btnText = await page.$eval('#fullscreenBtn', el => el.textContent);
  console.log('fullscreen btn text:', btnText);
  // ESC should exit
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  const isFullscreenAfterEsc = await page.$eval('#weeklyPanel', el => el.classList.contains('panel-fullscreen'));
  console.log('fullscreen active after ESC:', isFullscreenAfterEsc);

  // --- Compare mode test ---
  await page.click('#compareModeBtn');
  await page.waitForTimeout(200);
  const compareActive = await page.$eval('#compareModeBtn', el => el.classList.contains('active'));
  console.log('compare mode active:', compareActive);

  const svgBox = await page.$eval('#lineChart', el => { const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
  console.log('svg bbox:', svgBox);

  // Click two points inside the chart area (left third and right third horizontally, mid height)
  const wrapBox = await page.$eval('.chart-wrap', el => el.getBoundingClientRect());
  await page.mouse.click(wrapBox.x + wrapBox.width * 0.25, wrapBox.y + wrapBox.height * 0.4);
  await page.waitForTimeout(200);
  await page.mouse.click(wrapBox.x + wrapBox.width * 0.75, wrapBox.y + wrapBox.height * 0.4);
  await page.waitForTimeout(300);

  const boxVisible = await page.$eval('#compareResultBox', el => el.style.display);
  console.log('compareResultBox display:', boxVisible);
  const boxText = await page.$eval('#compareResultBox', el => el.textContent.replace(/\s+/g,' ').trim());
  console.log('compareResultBox text:', boxText);

  const circleCount = await page.$$eval('#lineChart circle[r="5"]', els => els.length);
  console.log('compare marker circles:', circleCount);

  // clear comparison
  await page.click('#clearCompareBtn');
  await page.waitForTimeout(200);
  const boxHiddenAfterClear = await page.$eval('#compareResultBox', el => el.style.display);
  console.log('compareResultBox display after clear:', boxHiddenAfterClear);

  console.log('errors:', errors);
  await browser.close();
})();

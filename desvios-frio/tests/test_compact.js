const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  const countBars = async () => page.$$eval('#lineChart rect[fill-opacity]', els => els.length);
  const countXLabels = async () => page.$$eval('#lineChart text', els => els.filter(e => /^\d{2}-S\d{2}$|^[A-ZÁÉÍÓÚa-záéíóú]+ \d{4}$/.test(e.textContent.trim())).map(e => e.textContent));

  const barsWeekly = await countBars();
  console.log('bars in weekly view:', barsWeekly);

  // --- toggle compact by month ---
  await page.click('#compactMonthBtn');
  await page.waitForTimeout(400);
  const btnActive = await page.$eval('#compactMonthBtn', el => el.classList.contains('active'));
  const btnLabel = await page.$eval('#compactMonthBtn', el => el.textContent);
  console.log('compactMonthBtn active:', btnActive, '| label:', btnLabel);

  const barsMonthly = await countBars();
  console.log('bars in monthly view (expect much fewer than weekly):', barsMonthly);

  const xLabels = await countXLabels();
  console.log('x-axis labels sample (expect month names):', xLabels.slice(0, 6));

  // hover to check tooltip shows a month label
  const box = await page.evaluate(() => {
    const svg = document.getElementById('lineChart');
    const rect = svg.querySelector('rect[fill="transparent"]');
    const b = rect.getBoundingClientRect();
    return { x: b.x, y: b.y, w: b.width, h: b.height };
  });
  await page.mouse.move(box.x + box.w * 0.5, box.y + box.h * 0.5);
  await page.waitForTimeout(200);
  const tooltipTitle = await page.$eval('#lineTooltip .t-title', el => el.textContent).catch(() => null);
  console.log('tooltip title while hovering (expect a month name):', tooltipTitle);

  // --- compare mode should work on monthly points ---
  await page.click('#compareModeBtn');
  await page.waitForTimeout(200);
  await page.mouse.click(box.x + box.w * 0.2, box.y + box.h * 0.4);
  await page.waitForTimeout(200);
  const hint1 = await page.$eval('#toolHint', el => el.textContent);
  console.log('hint after 1st click in monthly compare mode:', hint1);
  await page.mouse.click(box.x + box.w * 0.7, box.y + box.h * 0.4);
  await page.waitForTimeout(300);
  const compareBoxVisible = await page.$eval('#compareResultBox', el => getComputedStyle(el).display);
  console.log('compareResultBox display after 2nd click (expect not none):', compareBoxVisible);
  const compareBoxText = await page.$eval('#compareResultBox', el => el.textContent.slice(0, 200));
  console.log('compareResultBox text sample:', compareBoxText.replace(/\s+/g, ' '));

  // --- forecast checkbox should be inapplicable in monthly mode ---
  await page.click('#forecastToggle');
  await page.waitForTimeout(300);
  const forecastNoteVisible = await page.$eval('#forecastNote', el => getComputedStyle(el).display);
  console.log('forecastNote display with forecast checked in monthly mode (expect inline, i.e. not applicable):', forecastNoteVisible);
  await page.click('#forecastToggle');

  // --- toggle back to weekly ---
  await page.click('#compactMonthBtn');
  await page.waitForTimeout(400);
  const barsBackToWeekly = await countBars();
  console.log('bars after toggling back to weekly (should roughly match original):', barsBackToWeekly, 'vs original', barsWeekly);
  const btnLabelAfter = await page.$eval('#compactMonthBtn', el => el.textContent);
  console.log('compactMonthBtn label after toggling off:', btnLabelAfter);

  console.log('errors:', errors);
  await browser.close();
})();

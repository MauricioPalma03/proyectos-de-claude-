const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  // --- default: week mode ---
  const modeWeekActive = await page.$eval('#desvioModeWeekBtn', el => el.classList.contains('active'));
  console.log('week mode active by default:', modeWeekActive);
  const semanaValue = await page.$eval('#desvioSemanaSelect', el => el.value);
  console.log('default period (week):', semanaValue);

  const kpiTextWeek = await page.$eval('#desvioHeadlineKpis', el => el.innerText.replace(/\s+/g, ' ').trim());
  console.log('headline KPIs (week):', kpiTextWeek);

  // --- switch to month mode ---
  await page.click('#desvioModeMonthBtn');
  await page.waitForTimeout(300);
  const modeMonthActive = await page.$eval('#desvioModeMonthBtn', el => el.classList.contains('active'));
  const modeWeekStillActive = await page.$eval('#desvioModeWeekBtn', el => el.classList.contains('active'));
  console.log('month mode active:', modeMonthActive, '| week btn no longer active:', !modeWeekStillActive);
  const mesValue = await page.$eval('#desvioSemanaSelect', el => el.value);
  console.log('default period (month):', mesValue);
  const optionsLookLikeMonths = await page.$$eval('#desvioSemanaSelect option', els => els.slice(0, 3).map(e => e.value));
  console.log('sample month options:', optionsLookLikeMonths);

  const kpiTextMonth = await page.$eval('#desvioHeadlineKpis', el => el.innerText.replace(/\s+/g, ' ').trim());
  console.log('headline KPIs (month):', kpiTextMonth);

  // --- verify month totals are >= week totals (month aggregates multiple weeks) ---
  const fcstWeek = parseFloat(kpiTextWeek.match(/FCST ([\d.,]+)/)[1].replace(/\./g, '').replace(',', '.'));
  const fcstMonth = parseFloat(kpiTextMonth.match(/FCST ([\d.,]+)/)[1].replace(/\./g, '').replace(',', '.'));
  console.log('FCST week:', fcstWeek, '| FCST month:', fcstMonth, '| month >= week:', fcstMonth >= fcstWeek);

  // --- verify sort order is by volume (fcst descending), not by deviation ---
  const marcaTiles = await page.$$eval('#desvioMarcaGrid .mini-tile', els => els.map(el => {
    const title = el.getAttribute('title');
    const fcstMatch = title.match(/FCST ([\d.,]+) t/);
    return fcstMatch ? parseFloat(fcstMatch[1].replace(/\./g, '').replace(',', '.')) : null;
  }));
  const isSortedDesc = marcaTiles.every((v, i) => i === 0 || marcaTiles[i - 1] >= v);
  console.log('marca tiles sorted by FCST volume descending:', isSortedDesc, marcaTiles.slice(0, 5));

  // --- verify 5% threshold coloring ---
  const tileColors = await page.$$eval('#desvioMarcaGrid .mini-tile .mt-val', els => els.map(e => ({
    text: e.textContent.trim(), color: getComputedStyle(e).color,
  })));
  console.log('first few marca tile colors:', tileColors.slice(0, 6));

  // --- switch back to week mode ---
  await page.click('#desvioModeWeekBtn');
  await page.waitForTimeout(300);
  const backToWeek = await page.$eval('#desvioSemanaSelect', el => el.value);
  console.log('back to week mode, period:', backToWeek, '(should match original 26-S30 style label)');

  console.log('errors:', errors);
  await browser.close();
})();

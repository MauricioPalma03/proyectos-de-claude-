const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('file://' + __dirname + '/dashboard_frio.html');
  await page.waitForTimeout(1500);

  const rowCountBefore = await page.$eval('#fullDetailRowCount', el => el.textContent);
  console.log('row count before any alert:', rowCountBefore);
  const noteBefore = await page.$eval('#fullDetailAlertNote', el => getComputedStyle(el).display);
  console.log('alert note display before (expect none):', noteBefore);

  // --- 1-week alert ---
  await page.click('#alertWeekBtn');
  await page.waitForTimeout(300);
  const activeAfter1 = await page.$eval('#alertWeekBtn', el => el.classList.contains('active'));
  console.log('alertWeekBtn active:', activeAfter1);
  const rowCount1w = await page.$eval('#fullDetailRowCount', el => el.textContent);
  console.log('row count with 1-week alert:', rowCount1w);
  const noteText1 = await page.$eval('#fullDetailAlertNote', el => el.textContent);
  console.log('alert note text (1w):', noteText1);

  // verify every visible row's des% pill is actually >=40pp from 100
  const desPcts1w = await page.$$eval('#fullDetailTableBody tr', rows => rows.map(r => {
    const pill = r.children[10].querySelector('.pill');
    return pill ? pill.textContent : null;
  }).filter(Boolean));
  const violating1w = desPcts1w.filter(t => {
    const v = parseFloat(t.replace('%', '').replace(',', '.'));
    return Math.abs(v - 100) < 40;
  });
  console.log('rows shown (1w):', desPcts1w.length, '| rows violating the 40pp threshold:', violating1w.length, violating1w.slice(0, 5));

  // --- switch to 2-week alert ---
  await page.click('#alertWeek2Btn');
  await page.waitForTimeout(300);
  const activeAfter2 = await page.$eval('#alertWeek2Btn', el => el.classList.contains('active'));
  const stillActive1 = await page.$eval('#alertWeekBtn', el => el.classList.contains('active'));
  console.log('alertWeek2Btn active:', activeAfter2, '| alertWeekBtn still active (expect false):', stillActive1);
  const rowCount2w = await page.$eval('#fullDetailRowCount', el => el.textContent);
  console.log('row count with 2-week alert:', rowCount2w);
  const noteText2 = await page.$eval('#fullDetailAlertNote', el => el.textContent);
  console.log('alert note text (2w):', noteText2);

  // check semana column shows a combined "A→B" label for at least one row
  const semanaLabels = await page.$$eval('#fullDetailTableBody tr td:nth-child(2)', els => els.map(e => e.textContent).filter(t => t.trim()));
  console.log('sample semana labels (2w mode, expect some "X→Y"):', semanaLabels.slice(0, 5));

  const desPcts2w = await page.$$eval('#fullDetailTableBody tr', rows => rows.map(r => {
    const pill = r.children[10].querySelector('.pill');
    return pill ? pill.textContent : null;
  }).filter(Boolean));
  const violating2w = desPcts2w.filter(t => {
    const v = parseFloat(t.replace('%', '').replace(',', '.'));
    return Math.abs(v - 100) < 40;
  });
  console.log('rows shown (2w):', desPcts2w.length, '| rows violating threshold:', violating2w.length);

  // --- toggle off ---
  await page.click('#alertWeek2Btn');
  await page.waitForTimeout(300);
  const noteAfterOff = await page.$eval('#fullDetailAlertNote', el => getComputedStyle(el).display);
  console.log('alert note display after turning off (expect none):', noteAfterOff);
  const rowCountAfterOff = await page.$eval('#fullDetailRowCount', el => el.textContent);
  console.log('row count after turning off (should match original):', rowCountAfterOff, '(original was:', rowCountBefore, ')');

  console.log('errors:', errors);
  await browser.close();
})();
